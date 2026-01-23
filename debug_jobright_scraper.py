from playwright.sync_api import sync_playwright
import re
import time

def debug_jobright(url):
    with sync_playwright() as p:
        # Use a persistent context to simulate real user/session if needed
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"📄 Navigating to: {url}")
        page.goto(url)
        page.wait_for_timeout(5000) # Wait for React
        
        # 1. Inspect Title/Company
        print("\n--- DOM Inspection ---")
        title = page.locator('.index_job-title__sStdA, h1, [role="heading"]').first.inner_text()
        print(f"Title: {title}")
        
        company = page.locator('.index_company-name__RXcIy, [class*="company-name"]').first.inner_text()
        print(f"Company: {company}")
        
        # 2. Inspect Apply Button logic (Matching Scraper)
        print("\n--- Apply Button Search (Refined) ---")
        target_btn = page.locator('a, button, div[role="button"]') \
            .filter(has_text=re.compile(r"Apply|Start Application", re.I)) \
            .filter(has_not_text=re.compile(r"Autofill|Easy Apply", re.I)) \
            .first
        
        count = target_btn.count()
        print(f"Found {count} target button(s).")
        
        if count > 0:
            txt = target_btn.inner_text()
            print(f"Target Text: '{txt}'")
        
        # 3. Try Resolve (Robust)
        if target_btn:
            print(f"\n--- Attempting Resolution on Button ---")
            initial_url = page.url
            initial_pages = len(context.pages)
            print(f"Initial URL: {initial_url}, Pages: {initial_pages}")
            
            try:
                # Click without strict expect_popup first to see what happens
                target_btn.click(timeout=3000)
                page.wait_for_timeout(5000) # Wait for action
                
                final_url = page.url
                final_pages = context.pages
                print(f"Final URL: {final_url}, Total Pages: {len(final_pages)}")
                
                # Check for new page
                if len(final_pages) > initial_pages:
                    new_page = final_pages[-1]
                    new_page.wait_for_load_state()
                    print(f"✅ Resolved (New Tab): {new_page.url}")
                elif final_url != initial_url:
                    print(f"✅ Resolved (Same Tab): {final_url}")
                else:
                    print("❌ URL did not change and no new tab opened.")
                    
            except Exception as e:
                print(f"❌ Click/Wait failed: {e}")
                
        browser.close()

if __name__ == "__main__":
    # URL found in previous step
    debug_jobright("https://jobright.ai/jobs/info/696f079282817106e9763c2e")
