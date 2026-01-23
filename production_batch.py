"""
Production Batch Processor with Full ATS Support
Supports: Greenhouse, Lever, Workday, Taleo, SmartRecruiters, Ashby, BambooHR + Generic
"""

import logging
import time
import random
import json
import argparse
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from database import JobManager
from humanizer import Humanizer
from ai_selector import AISelector
from ats_handlers import ATSDetector
from ats_strategies import StrategyFactory

logger = logging.getLogger("ProductionBatch")
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
PROFILE_PATH = "profile.json"

class ProductionBatcher:
    def __init__(self, headless=False):
        self.db = JobManager()
        self.ai = AISelector()
        self.headless = headless
        
        # Load Profile
        if Path(PROFILE_PATH).exists():
            self.profile = json.loads(Path(PROFILE_PATH).read_text())
        else:
            self.profile = {}
            logger.warning("⚠️ Profile not found, AI will lack context")
            
        logger.info("🤖 Production Batcher Initialized (Strategic Mode).")

    def run_batch(self, limit=1):
        """Run batch execution with Persistent Browser Mode."""
        pending = self.db.get_pending_jobs(limit=limit)
        
        logger.info(f"📦 Batch Start: Processing {len(pending)} jobs...")
        if not pending:
            logger.info("📭 No pending jobs found.")
            return

        # LAUNCH BROWSER (Persistent & Stealthy)
        # This fixes "This browser or app may not be secure"
        user_data_path = Path("browser_profile").absolute()
        playwright = sync_playwright().start()
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
        
        # Use persistent context instead of browser + new_context
        # specific to bypassing Google and remembering sessions
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_path),
            headless=self.headless,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", # FORCE REAL CHROME
            args=args,
            ignore_default_args=["--enable-automation"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Stealth Patch
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for job in pending:
            try:
                self.db.update_status(job['id'], "processing")
                
                # NEW TAB for each job
                page = context.new_page()
                logger.info(f"🚀 Processing Job {job['id']} in new tab...")
                
                # Process logic
                self.process_job_strategic(page, job)
                
                print(f"\n✅ Job {job['id']} completed (Tab Open)")
                
            except Exception as e:
                logger.error(f"❌ Job {job['id']} Failed: {str(e)}")
                self.db.update_status(job['id'], "failed", str(e))
                try:
                    page.screenshot(path=f"debug_screenshots/failed_{job['id']}.png")
                except: passed

        print("\n🏁 Batch Complete.")
        print("ℹ️  Browser tabs have been left OPEN for your inspection.")
        try:
            input("🔴 Press Enter to close browser and exit (or Ctrl+C to keep open)...")
        except: pass
        
        context.close()
        playwright.stop()

    def process_job_strategic(self, page, job):
        """Process job using Strategy Pattern."""
        # 1. Navigate
        page.goto(job['url'])
        
        # 2. Initialize Humanizer & Strategy
        human = Humanizer(page)
        strategy = StrategyFactory.get_strategy(job['url'], human)
        logger.info(f"   🏗️ Strategy Selected: {strategy.__class__.__name__}")
        
        # 3. Strategy: Navigate/Auth
        if strategy.navigate_to_apply(page, job):
            # 4. Strategy: Fill Form
            self._fill_form_generic(page, job, human)
            
            self.db.update_status(job['id'], "filled")
            logger.info(f"✅ Job {job['id']} Processed Successfully.")
        else:
            raise Exception("Strategy failed to reach application form")

    def _fill_form_generic(self, page, job, human):
        """Generic Field Filling (Legacy Logic - to be migrated)."""
        # Scrape Context
        handler = ATSDetector.get_handler(job['url'])
        role, desc = handler.scrape_context(page)
        
        # Re-using the ROBUST generic filler logic
        self.robust_fill(page, role, desc, human, job)

    def robust_fill(self, page, role, desc, human, job):
        logger.info("   📝 Starting Robust Form Fill...")
        
        # 0. Resume Upload (Generic)
        resume_path = job.get('resume_path')
        if resume_path:
             try:
                file_input = page.locator("input[type='file']").first
                if file_input.count() > 0:
                    logger.info(f"   📂 Uploading Resume: {resume_path}")
                    file_input.set_input_files(resume_path)
                    time.sleep(2)
             except Exception as e:
                 logger.warning(f"   ⚠️ Resume Upload Failed: {e}")

        # 1. Try filling by Label (Standard)
        labels = page.locator("label").all()
        for label in labels:
            try:
                field_text = label.inner_text()
                
                # Check for input ID
                label_for = label.get_attribute("for")
                if label_for:
                    field = page.locator(f"#{label_for}").first
                else:
                    # Try looking inside the label
                    field = label.locator("input, select, textarea").first
                    if field.count() == 0:
                        # Try sibling
                        field = label.locator("xpath=following-sibling::*[1]").first
                
                if field.count() > 0 and field.is_visible():
                     self._fill_field_smart(field, field_text, human)
            except: continue

        # 2. Try filling by Placeholder (Common in modern UIs)
        inputs = page.locator("input:visible, textarea:visible").all()
        for inp in inputs:
            try:
                # Skip if already filled
                if inp.input_value(): continue
                
                placeholder = inp.get_attribute("placeholder")
                if placeholder:
                    self._fill_field_smart(inp, placeholder, human)
                    
                aria = inp.get_attribute("aria-label")
                if aria:
                    self._fill_field_smart(inp, aria, human)
            except: continue

        # 3. Hybrid Question Handling (Rule-Based + AI)
        self._answer_questions_hybrid(page, job, human)
            
    def _answer_questions_hybrid(self, page, job, human):
        """
        Hybrid Approach:
        1. STRICT RULES for Compliance/Legal (Auth, Sponsorship, Relatives, Location).
        2. AI (Groq) for Screening Questions (Why interested, Experience, etc).
        """
        # A. Strictly Defined Rules (Compliance/Logistics) - "Basic Code"
        rules = [
            # WORK AUTHORIZATION (Broad Patterns)
            ("authorized", "Yes", "radio"),
            ("work in the us", "Yes", "radio"),
            ("work in us", "Yes", "radio"),
            ("work in the united states", "Yes", "radio"),
            ("legally allowed to work", "Yes", "radio"),
            ("eligible to work", "Yes", "radio"),
            ("work eligibility", "Yes", "radio"),
            ("legal right to work", "Yes", "radio"),
            ("employment eligibility", "Yes", "radio"),
            ("permit", "No", "radio"), # Do you need a permit? No.

            # SPONSORSHIP (Broad Patterns)
            ("sponsorship", "No", "radio"),
            ("require sponsorship", "No", "radio"),
            ("need sponsorship", "No", "radio"),
            ("will you now or in the future require", "No", "radio"),
            ("immigration sponsorship", "No", "radio"),

            # BASIC COMPLIANCE
            ("worked here", "No", "radio"),             # Have you worked here before?
            ("relative", "No", "radio"),                # Any relatives?
            ("employed", "No", "radio"),                # Previously employed?
            ("contract", "No", "radio"),                # Gov contract?
            ("terms", "checkbox", "checkbox"),
            ("privacy", "checkbox", "checkbox"),
            ("consent", "checkbox", "checkbox"),
            
            # LOGISTICS
            ("on-site", "Yes", "radio"),
            ("location", "Yes", "radio"),
            ("commute", "Yes", "radio"),
            ("relocate", "Yes", "radio"),
        ]
            ("terms", "checkbox", "checkbox"),          # Terms of Service
            ("privacy", "checkbox", "checkbox"),        # Privacy Policy
            ("on-site", "Yes", "radio"),                # Comfortable with on-site?
            ("location", "Yes", "radio"),               # Comfortable with location?
            ("commute", "Yes", "radio"),                # Comfortable with commute?
            ("relocate", "Yes", "radio"),               # Willing to relocate?
        ]
        
        # Apply Rules (Radios/Checkboxes)
        for keyword, target_answer, q_type in rules:
            try:
                # Find all text elements matching keyword
                elements = page.get_by_text(re.compile(keyword, re.IGNORECASE)).all()
                for el in elements:
                    if not el.is_visible(): continue
                    
                    # Search nearby for the answer
                    container = el.locator("xpath=..")
                    found = False
                    for _ in range(4): # Search up 4 levels
                        if q_type == "checkbox":
                            box = container.locator("input[type='checkbox']").first
                            if box.count() > 0:
                                if not box.is_checked(): human.move_and_click(box)
                                logger.info(f"   ✅ [Rule] Checked box for '{keyword}'")
                                found = True
                                break
                        else: # Radio/Button
                            # Look for label/span/div with target answer
                            option = container.locator(f"label:has-text('{target_answer}'), span:has-text('{target_answer}'), div:has-text('{target_answer}'), button:has-text('{target_answer}')").first
                            if option.count() > 0 and option.is_visible():
                                human.move_and_click(option)
                                logger.info(f"   ✅ [Rule] Answered '{target_answer}' for '{keyword}'")
                                found = True
                                break
                        container = container.locator("xpath=..")
                    if found: break 
            except: continue

        # B. AI Screening Questions (Textareas/Inputs) that were NOT filled by Basic Rules
        # Find all unfilled textareas or text inputs that look like questions
        all_inputs = page.locator("textarea:visible, input[type='text']:visible").all()
        
        handler = ATSDetector.get_handler(job['url'])
        job_context = handler.scrape_context(page) # (role, desc)
        context_dict = {"title": job_context[0], "description": job_context[1], "company": job.get("company", "")}

        for inp in all_inputs:
            try:
                if inp.input_value(): continue # Skip if filled
                
                # Get label/question text
                q_text = ""
                # Try getting label
                id_attr = inp.get_attribute("id")
                if id_attr:
                    label = page.locator(f"label[for='{id_attr}']").first
                    if label.count() > 0:
                        q_text = label.inner_text()
                
                if not q_text:
                     # Try placeholder
                     q_text = inp.get_attribute("placeholder") or ""
                     
                if not q_text:
                    # Try aria-label
                     q_text = inp.get_attribute("aria-label") or ""
                     
                if len(q_text) < 5: continue # Too short to be a question
                
                # Filter out basic fields (Name, Email, etc) which should have been caught by regex
                skip_keywords = ["name", "email", "phone", "linkedin", "website", "city", "state", "zip", "address"]
                if any(k in q_text.lower() for k in skip_keywords): continue

                logger.info(f"   🧠 [AI] Generating answer for: '{q_text}'...")
                
                # CALL AI
                answer = self.ai.generate_answer(q_text, self.profile, context_dict)
                if answer:
                    human.type_like_human(inp, answer)
                    logger.info("      -> AI Answered.")
                    
            except Exception as e:
                # logger.warning(f"AI Fill Error: {e}")
                pass

    def _fill_field_smart(self, field, text, human):
        """Determine value from text and fill."""
        val = self._get_field_value(text)
        if val:
            try:
                tag = field.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    human.select_dropdown(field, val)
                    logger.info(f"   ✅ Selected '{val}' for '{text}'")
                    return

                # Check if it's a checkbox/radio (Skip here, handled in _answer_questions_hybrid)
                type_attr = field.get_attribute("type")
                if type_attr in ["checkbox", "radio"]:
                    return 

                # Autocomplete Handling
                human.type_like_human(field, val)
                time.sleep(0.5)
                # If it's location implies autocomplete, press Enter or Down+Enter
                if "location" in text.lower() or "city" in text.lower():
                     field.press("Enter")
                
                logger.info(f"   ✅ Filled '{val}' for '{text}'")
            except Exception as e:
                pass

    def _get_field_value(self, field_text):
        if not field_text: return None
        text = field_text.lower().strip()
        
        # Name
        if "first name" in text: return self.profile.get("first_name", "Nuthan Reddy")
        if "last name" in text: return self.profile.get("last_name", "Vaddireddy")
        if "full name" in text: return f"{self.profile.get('first_name', 'Nuthan Reddy')} {self.profile.get('last_name', 'Vaddireddy')}"
        if text == "name": return f"{self.profile.get('first_name', 'Nuthan Reddy')} {self.profile.get('last_name', 'Vaddireddy')}"
        if "name" in text and "user" not in text and "project" not in text: return f"{self.profile.get('first_name', 'Nuthan Reddy')} {self.profile.get('last_name', 'Vaddireddy')}"
        
        # Contact
        if "email" in text: return self.profile.get("email", "nuthanreddy001@gmail.com")
        if "phone" in text or "mobile" in text: return self.profile.get("phone", "+16824065646")
        
        # Links
        if "linkedin" in text: return "https://www.linkedin.com/in/nuthan-reddy-vaddi-reddy/"
        if "github" in text: return self.profile.get("github", "https://github.com/nuthan-reddy")
        if "portfolio" in text or "website" in text: return self.profile.get("portfolio", "")
        
        # Location
        if "address" in text and "email" not in text: return self.profile.get("address", "")
        if "city" in text: return self.profile.get("city", "Irving")
        if "state" in text: return self.profile.get("state", "Texas")
        if "zip" in text or "postal" in text: return self.profile.get("zip", "75063")
        if "location" in text: return "Dallas, TX"
        
        # Questions (Text input fallback)
        if "salary" in text or "compensation" in text: return "Open"
        
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1, help="Number of jobs to process")
    args = parser.parse_args()
    
    batcher = ProductionBatcher(headless=False)
    batcher.run_batch(limit=args.limit)
