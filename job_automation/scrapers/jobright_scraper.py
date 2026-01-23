import time
import re
from typing import List, Optional
from playwright.sync_api import BrowserContext, Page
from pathlib import Path
from job_automation.core.base_scraper import BaseScraper
from job_automation.core.models import Job
from job_automation.utils.text_utils import safe_text, clean_description
from job_automation.scrapers.jobright_authenticator import JobRightAuthenticator

class JobRightScraper(BaseScraper):
    """
    JobRight AI Scraper implementation with Authentication.
    """
    
    def __init__(self, context: BrowserContext, config: dict):
        super().__init__(context, config)
        
        # Initialize authenticator
        credentials = config.get('credentials', {})
        session_dir = Path(config.get('session_dir', 'job_automation/.sessions'))
        
        self.authenticator = JobRightAuthenticator(context, credentials, session_dir)
        
        # Authenticate before scraping
        # We allow a 'skip_auth' flag for testing or if manually handled externally
        if not config.get('skip_auth', False):
            if not self.authenticator.authenticate():
                raise RuntimeError("Failed to authenticate with JobRight")
    
    def get_source_name(self) -> str:
        return "jobright"
    
    def collect_job_links(self, start_url: str, max_jobs: int) -> List[str]:
        """
        Collect job links (requires authentication).
        """
        # Verify still authenticated
        page = self.context.new_page()
        if not self.authenticator.verify_authenticated(page):
            print("   ⚠️  Session expired, re-authenticating...")
            page.close()
            if not self.authenticator.authenticate():
                raise RuntimeError("Re-authentication failed")
            page = self.context.new_page()
        
        try:
            print(f"\n📋 Collecting job links from JobRight...")
            
            # Navigate to recommend/search page (already authenticated)
            page.goto(start_url, wait_until="domcontentloaded")
            time.sleep(3)
            # Apply Sort: Most Recent
            self._apply_sort(page, "Most Recent")
            
            # Infinite scroll logic (reused from previous implementation)
            collected_data = {} # Map URL -> Metadata
            scroll_attempts = 0
            max_scrolls = 20
            
            while len(collected_data) < max_jobs and scroll_attempts < max_scrolls:
                # Extract links AND metadata
                new_items = page.evaluate("""
                    () => {
                        const items = [];
                        
                        // Strategy: Iterate over cards to get link AND time
                        const cards = document.querySelectorAll('.index_job-card__AsPKC, [class*="job-card"]');
                        
                        cards.forEach(card => {
                            let url = "";
                            let time = "";
                            
                            // 1. Get URL (either from A tag or ID)
                            const link = card.querySelector('a');
                            if (link && link.href) {
                                url = link.href;
                            } else if (card.id && card.id.length > 10) {
                                url = `https://jobright.ai/jobs/info/${card.id}`;
                            }
                            
                            // 2. Get Time (Look for text like "1 hour ago", "Just now", etc)
                            // Usually it's in a specific span or div. 
                            // Based on debug dumps, it is often free text in the card header.
                            // We'll grab the first few lines of text or specific class if known.
                            // User provided copy-paste shows "3 hours ago" at top.
                            if (card.innerText) {
                                const lines = card.innerText.split('\\n');
                                // Simple heuristic: First line often contains time or "New"
                                // Or look for time patterns
                                time = lines.find(l => l.match(/ago|minute|hour|day|Just now/i)) || "";
                            }
                            
                            if (url) {
                                items.push({url, time});
                            }
                        });

                        return items;
                    }
                """)
                
                # Update collection
                for item in new_items:
                    if item['url'] not in collected_data:
                        collected_data[item['url']] = item
                
                print(f"      Scroll {scroll_attempts+1}: Found {len(collected_data)} unique jobs so far")
                
                if len(collected_data) >= max_jobs:
                    break
                
                page.mouse.wheel(0, 3000)
                time.sleep(1.0)
                scroll_attempts += 1
            
            # Save metadata for fetch_job_details to use
            self.job_metadata = collected_data
            return list(collected_data.keys())[:max_jobs]
            
        except Exception as e:
            print(f"   ❌ Error collecting links: {e}")
            return []
        finally:
            page.close()

    def _apply_sort(self, page: Page, sort_text: str):
        """
        Apply sorting filter (e.g. 'Most Recent').
        """
        print(f"   Refining results: Sorting by '{sort_text}'...")
        try:
            # 1. Open Sort Dropdown
            # Try to find the dropdown by looking for the "Recommended" text which is likely the default value
            dropdown_trigger = page.locator('.ant-select-selector').filter(has_text="Recommended").first
            if not dropdown_trigger.is_visible():
                # Fallback: Just look for the specific sorter class
                dropdown_trigger = page.locator('.index_jobs-recommend-sorter__AhkIK .ant-select-selector').first
            
            # If we are already sorted correctly, the trigger itself will say "Most Recent"
            current_selection = page.locator('.ant-select-selection-item').filter(has_text=sort_text)
            if current_selection.count() > 0 and current_selection.is_visible():
                 print(f"      ✓ Sort by '{sort_text}' already active.")
                 return

            if dropdown_trigger.count() > 0:
                print("      → Opening sort dropdown...")
                dropdown_trigger.click()
                page.wait_for_timeout(1000)
                
                # 2. Click the option
                # Use get_by_text which is robust against class name changes
                # We specifically look for the option in the dropdown layer
                option = page.locator('.ant-select-dropdown').get_by_text(sort_text, exact=True).first
                if not option.is_visible():
                     # Fallback partial match if exact fails
                     option = page.locator('.ant-select-dropdown').get_by_text(sort_text).first
                     
                if option.is_visible():
                    # Capture state PRE-sort
                    pre_sort_job = page.locator('.index_job-card__AsPKC, [class*="job-card"]').first
                    pre_text = pre_sort_job.inner_text()[:20] if pre_sort_job.count() else ""
                    
                    option.click()
                    print(f"      ✓ Clicked '{sort_text}'")
                    
                    # 3. Verify Change (Strict Mode)
                    print(f"      ⏳ Waiting for list to update (Old: '{pre_text}')...")
                    # Wait for 10 seconds max for the content to change
                    for _ in range(20):
                        page.wait_for_timeout(500)
                        current_job = page.locator('.index_job-card__AsPKC, [class*="job-card"]').first
                        if current_job.count() == 0: continue # Loading state
                        
                        current_text = current_job.inner_text()[:20]
                        if current_text != pre_text:
                            print(f"      ✅ Content updated! (New: '{current_text}')")
                            page.wait_for_timeout(1000) # Settle
                            return
                    
                    print(f"      ⚠️ Warning: validation sort timeout. List might not have changed.")
                else:
                    print(f"      ⚠️ Option '{sort_text}' not found in dropdown")
                    # Debug: print available
                    all_ops = page.locator('.ant-select-item-option-content').all_inner_texts()
                    print(f"         Available: {all_ops}")
            else:
                print(f"      ⚠️ Sort dropdown not found")
        except Exception as e:
            print(f"      ⚠️ Failed to apply sort: {e}")

    
    def fetch_job_details(self, job_url: str) -> Optional[Job]:
        """
        Fetch details for a single job page on JobRight.
        """
        page = self.context.new_page()
        page.set_default_timeout(35000)
        
        try:
            print(f"   📄 Opening: {job_url}")
            page.goto(job_url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Specific to JobRight detailed View
            title_sel = '.index_job-title__sStdA, h1, [role="heading"]'
            company_sel = '.index_company-name__RXcIy, [class*="company-name"]'
            
            # Extract basic text first
            job_data = page.evaluate("""
                () => {
                    const getText = (s) => document.querySelector(s)?.innerText.trim() || "";
                    const title = getText('.index_job-title__sStdA') || getText('h1');
                    const company = getText('.index_company-name__RXcIy') || getText('[class*="company"]');
                    const description = document.querySelector('main')?.innerText || document.body.innerText;
                    return { title, company, description };
                }
            """)

            title = safe_text(job_data.get('title', 'Unknown Title'))
            company = safe_text(job_data.get('company', 'Unknown Company'))
            description = clean_description(job_data.get('description', ''))

            # --- RESOLVE APPLY URL (CLICK & CAPTURE) ---
            apply_url = job_url # Default
            
            try:
                # Find the Apply/Original Link button (Prioritize 'Original Job Post')
                apply_btn = page.locator('a, button, div[role="button"]') \
                    .filter(has_text=re.compile(r"Original Job Post|Apply|Start Application", re.I)) \
                    .first
                
                resolved_url = None
                
                if apply_btn.count() > 0 and apply_btn.is_visible():
                    # 1. Try to get HREF first
                    href = apply_btn.get_attribute("href")
                    if href:
                        if href.startswith('/'): href = "https://jobright.ai" + href
                        print(f"      🔗 Found Link: {href}")
                        resolved_url = href
                    
                    # 2. Extract Direct URL from Hydration Data (Deep Research via Python Regex)
                    # We use Python regex on page content because it's more robust than traversing unpredictable JS objects
                    # We use Python regex on page content because it's more robust than traversing unpredictable JS objects
                    page_content = page.content()
                    
                    # Pattern 1: originalUrl":"http..."
                    match = re.search(r'"originalUrl":"(https?://[^"]+)"', page_content)
                    if not match:
                        # Pattern 2: applyLink":"http..."
                        match = re.search(r'"applyLink":"(https?://[^"]+)"', page_content)
                    
                    direct_url = match.group(1) if match else None
                    
                    if direct_url and "jobright.ai" not in direct_url:
                        # Decode potential unicode escapes (e.g. \u0026 -> &)
                        direct_url = direct_url.encode().decode('unicode_escape')
                        print(f"      💎 Found Direct URL in Source: {direct_url}")
                        resolved_url = direct_url
                        should_resolve = False # Skip Click
                    else:
                        print("      ⚠️ Direct URL not found in Source or is Internal. Falling back to Click...")
                        should_resolve = not href or "apply" in href.lower()
                    
                    if should_resolve:
                        print("      🖱️  Resolving URL via Click...")
                        initial_url = page.url
                        initial_pages_count = len(page.context.pages)
                        
                        # 1. Setup Network Listener (Capture outgoing requests)
                        captured_urls = []
                        def capture_request(request):
                            if request.url not in captured_urls:
                                captured_urls.append(request.url)
                        
                        page.on("request", capture_request)
                        
                        # 2. Click (Try Force then JS)
                        try:
                            # Attempt clean click
                            apply_btn.click(timeout=3000, force=True)
                        except:
                            print("      ⚠️ Standard click failed, trying JS Click...")
                            apply_btn.evaluate("e => e.click()")
                        
                        # 3. Wait for Action (Navigation or New Tab or Network)
                        page.wait_for_timeout(3000)
                        
                        # Cleanup listener
                        page.remove_listener("request", capture_request)
                        
                        # 3. Check for New Tab (Robust)
                        current_pages = page.context.pages
                        if len(current_pages) > initial_pages_count:
                            # New tab opened!
                            new_page = current_pages[-1]
                            print(f"      ↪  New Tab Detected: {new_page.url}")
                            
                            try:
                                # Handle about:blank by waiting
                                if new_page.url == "about:blank":
                                    print("      ⏳ Waiting for about:blank to redirect...")
                                    new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                                else:
                                    new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                                
                                resolved_url = new_page.url
                                print(f"      ↪  Resolved (New Tab): {resolved_url}")
                                new_page.close()
                            except Exception as e:
                                resolved_url = new_page.url   # Capture whatever we have
                                print(f"      ↪  Resolved (New Tab - Timeout/Error): {resolved_url} ({e})")
                                try: new_page.close()
                                except: pass
                                
                        # 4. Check for Same-Tab Navigation
                        elif page.url != initial_url:
                             resolved_url = page.url
                             print(f"      ↪  Resolved (Same Tab): {resolved_url}")
                        
                        else:
                             # 5. Check Network Requests (Intercepted Redirects)
                             print(f"      INFO: Captured {len(captured_urls)} network requests.")
                             network_url = None
                             for u in captured_urls:
                                 # Skip internal/assets
                                 if "jobright.ai" in u or "localhost" in u: continue
                                 if any(ext in u.lower() for ext in ['.js', '.css', '.png', '.jpg', '.woff', '.json']): continue
                                 
                                 print(f"      🔍 Inspecting Request: {u}")
                                 network_url = u
                                 break # Take the first external request
                             
                             if network_url:
                                 resolved_url = network_url
                                 print(f"      ↪  Resolved (Network Sniff): {resolved_url}")
                             
                             else:
                                 # 6. Last Resort: Scan DOM for new links
                                 print("      ⚠️ Nav failed. Scanning for new external links...")
                                 external_link = page.evaluate("""() => {
                                     const allLinks = Array.from(document.querySelectorAll('a[href^="http"]'));
                                     const external = allLinks.find(a => !a.href.includes('jobright.ai') && !a.href.includes('localhost'));
                                     return external ? external.href : null;
                                 }""")
                                 if external_link:
                                     print(f"      ↪  Found External Link in DOM: {external_link}")
                                     resolved_url = external_link

                
                if resolved_url:
                    apply_url = resolved_url
                else:
                    # Fallback JS extraction
                    js_href = page.evaluate("""() => {
                        const a = Array.from(document.querySelectorAll('a')).find(e => e.innerText.match(/Original Job Post|Apply|Start Application/i));
                        return a ? a.href : "";
                    }""")
                    if js_href: apply_url = js_href

            except Exception as e:
                print(f"      ⚠️ URL Resolution Error: {e}")


            
            # --- FILTERING: Skip Easy Apply / Aggregators ---
            # User request: Skip "Open SASS" (Likely 'Open Source' or specific aggregators?), LinkedIn, Indeed.
            # Rationale: These are "Time Waste" to generate PDFs for.
            skip_domains = ["linkedin.com", "indeed.com", "ziprecruiter.com", "glassdoor.com"]
            if any(d in apply_url.lower() for d in skip_domains):
                print(f"      ⏭️  Skipping Job: Easy Apply/Aggregator link ({apply_url})")
                return None
                
            # Retrieve metadata (Posted Time)
            posted_at = ""
            if hasattr(self, 'job_metadata') and job_url in self.job_metadata:
                posted_at = self.job_metadata[job_url].get('time', '')
            
            print(f"      📌 Title: {title}")
            print(f"      🏢 Company: {company}")
            print(f"      🔗 Apply: {apply_url}")
            print(f"      🕒 Posted: {posted_at}")
            
            if not description or len(description) < 100:
                print("      ⚠️ Description too short, skipping.")
                return None
            
            return Job(
                url=job_url,
                title=title,
                company=company,
                description=description,
                apply_url=apply_url,
                source="jobright",
                posted_at=posted_at
            )

        except Exception as e:
            print(f"      ❌ Error fetching details: {e}")
            self.jobs_failed += 1
            return None
        finally:
            page.close()
