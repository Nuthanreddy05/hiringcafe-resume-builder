from abc import ABC, abstractmethod
import time
import logging

logger = logging.getLogger("ATS_Strategies")

class BaseApplicationStrategy(ABC):
    """Abstract Strategy for applying to jobs."""
    
    def __init__(self, humanizer):
        self.human = humanizer
    
    @abstractmethod
    def navigate_to_apply(self, page, job):
        """Navigate to form, clicking 'Apply' if needed. Return True if form is ready."""
        pass
    
    @abstractmethod
    def fill_form_fields(self, page, job, ai_selector, profile):
        """Fill all identified fields."""
        pass
    
    def smart_wait(self, page):
        """Wait for network idle + human pause."""
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except: pass
        self.human.pause("reading")

class GreenhouseStrategy(BaseApplicationStrategy):
    """Strategy for Greenhouse (Tier 1 - Easy)."""
    
    def navigate_to_apply(self, page, job):
        # 1. Look for Apply Button
        apply_btn = page.locator("[aria-label='Apply'], #apply_button, a:has-text('Apply for this job')").first
        
        if apply_btn.count() > 0 and apply_btn.is_visible():
            logger.info("   ✅ Found Apply button (Greenhouse)")
            self.human.move_and_click(apply_btn)
            time.sleep(2) # Wait for modal
            
            # Modal Check
            if page.locator("[role='dialog'], #application_form").count() > 0:
                logger.info("   ✅ Modal/Form loaded.")
                return True
        else:
            # Maybe form is already there (Single page)
            if page.locator("input[name*='name']").count() > 0:
                logger.info("   ✅ Form already visible.")
                return True
                
        return False

    def fill_form_fields(self, page, job, ai_selector, profile):
        # Greenhouse standard form filling
        # Implementation will be similar to previous generic logic but scoped
        pass

class TaleoStrategy(BaseApplicationStrategy):
    """Strategy for Taleo (Tier 2 - iframe/redirect)."""
    
    def navigate_to_apply(self, page, job):
        logger.info("   🔍 Taleo: Waiting for button to render (Extended Wait)...")
        # Taleo is SLOW. Wait 5 seconds (User Config).
        time.sleep(5)
        
        # Scroll down (Taleo often hides button below fold)
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(1)
        except: pass

        self.smart_wait(page)
        
        # Taleo often uses iframes.
        frame_match = None
        if page.frames:
            for frame in page.frames:
                # Check frame URL or Name
                if "taleo" in str(frame.url) or "content" in str(frame.name):
                    try:
                        # Try finding button in frame
                        if frame.locator("a.masterlink:has-text('Apply')").count() > 0:
                            frame_match = frame
                            break
                    except: continue
        
        if frame_match:
            logger.info("   ✅ Found Apply in Taleo iframe")
            try:
                btn = frame_match.locator("a.masterlink:has-text('Apply')").first
                btn.click()
                time.sleep(3)
                return True
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to click iframe button: {e}")
        
        # Try finding button in main page (after scroll)
        selectors = [
             "#hqj-apply-button",
             "a[id*='apply']",
             "a.navbar-nav-link:has-text('Apply')",
             "span:has-text('Apply Now')",
             "button:has-text('Apply Now')",
             ".taleo-apply-button",
             "a:has-text('Apply')"
        ]
        
        for sel in selectors:
            if page.locator(sel).count() > 0:
                logger.info(f"   ✅ Found Taleo button: {sel}")
                self.human.move_and_click(page.locator(sel).first)
                time.sleep(3)
                break

        # Taleo puts you in a wizard.
        # Check for "Login" or "New User"
        if page.locator("input[id*='user'], input[id*='User']").count() > 0:
            logger.warning("   ⚠️ Taleo Login Wall detected.")
            print("\n🚨 TALEO AUTH REQUIRED 🚨")
            print("1. Please log in or click 'New User' manually.")
            print("2. Navigate until you see the 'Resume Upload' or 'Candidate Profile' screen.")
            input("   Press Enter when ready to continue...")
            return True
            
        return True

    def fill_form_fields(self, page, job, ai_selector, profile):
        pass

class SmartRecruitersStrategy(BaseApplicationStrategy):
    """Strategy for SmartRecruiters."""
    
    def navigate_to_apply(self, page, job):
        self.smart_wait(page)
        
        # SmartRecruiters uses "I'm interested"
        selectors = [
            "button:has-text('I\\'m interested')",
            "button[aria-label='Submit your application']",
            "button:has-text('Apply Now')",
            ".apply-button",
            "button.button--primary"
        ]
        
        for sel in selectors:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible():
                logger.info(f"   ✅ Found SmartRecruiters button: {sel}")
                self.human.move_and_click(btn)
                time.sleep(2)
                
                # Check for modal
                if page.locator("st-modal-content").count() > 0:
                     logger.info("   ✅ Modal detected")
                     
                return True
                
        return False

    def fill_form_fields(self, page, job, ai_selector, profile):
        pass

class WorkdayStrategy(BaseApplicationStrategy):
    """Strategy for Workday (Tier 3 - Auth/Wizards)."""
    
    def navigate_to_apply(self, page, job):
        self.smart_wait(page)
        
        # Check if already logged in? 
        # Workday usually has "Sign In" or "Apply" which triggers Sign In.
        
        apply_btn = page.locator("[data-automation-id='jobApplicationButton']").first
        if apply_btn.count() > 0:
            logger.info("   ✅ Found Workday Apply Button")
            self.human.move_and_click(apply_btn)
            time.sleep(3)
        
        # Auth Check
        if page.locator("[data-automation-id='loginPageComponent']").count() > 0:
            logger.warning("   ⚠️ Workday Login Wall.")
            print("\n🚨 WORKDAY AUTH REQUIRED 🚨")
            print("1. Log in or create an account.")
            print("2. Navigate to the 'My Experience' or 'Resume' section.")
            input("   Press Enter when ready to continue...")
            return True
        
        return True

    def fill_form_fields(self, page, job, ai_selector, profile):
        # Workday Wizard Navigation
        # This requires loop: fill -> next -> fill -> next
        pass

class GenericStrategy(BaseApplicationStrategy):
    """Fallback for everything else."""
    
    def navigate_to_apply(self, page, job):
        # 1. Check if form is ALREADY visible (e.g. deep link)
        if page.locator("input[type='text'], input[type='email']").count() > 2:
            logger.info("   ✅ Form inputs detected directly.")
            return True

        # 2. Fuzzy match apply button
        keywords = ["Match", "Apply", "Start Application", "Submit"]
        for k in keywords:
            btn = page.locator(f"button:has-text('{k}'), a:has-text('{k}')").first
            if btn.count() > 0 and btn.is_visible():
                logger.info(f"   ✅ Found Generic Apply button: {k}")
                self.human.move_and_click(btn)
                time.sleep(3)
                
                # Verify click worked (modal or new page)?
                return True
                
        # 3. Final Fallback: Look for inputs again (maybe they appeared?)
        if page.locator("input[type='text'], input[type='email']").count() > 1:
            logger.info("   ✅ Form detected after check.")
            return True

        return False

    def fill_form_fields(self, page, job, ai_selector, profile):
        pass

class StrategyFactory:
    @staticmethod
    def get_strategy(url, humanizer):
        u = url.lower()
        if "greenhouse" in u: return GreenhouseStrategy(humanizer)
        if "taleo" in u: return TaleoStrategy(humanizer)
        if "workday" in u: return WorkdayStrategy(humanizer)
        if "smartrecruiters" in u: return SmartRecruitersStrategy(humanizer)
        if "ashby" in u: return GenericStrategy(humanizer) # Ashby often handled by generic or specialized later
        if "lever" in u: return GenericStrategy(humanizer) # Lever usually easier
        return GenericStrategy(humanizer)
