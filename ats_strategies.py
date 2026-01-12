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
        self.smart_wait(page)
        
        # Taleo often uses iframes.
        frame_match = None
        if page.frames:
            for frame in page.frames:
                if "taleo" in frame.url or "content" in frame.name:
                    if frame.locator("a.masterlink:has-text('Apply')").count() > 0:
                        frame_match = frame
                        break
        
        if frame_match:
            logger.info("   ✅ Found Apply in Taleo iframe")
            btn = frame_match.locator("a.masterlink:has-text('Apply')").first
            btn.click()
            time.sleep(3)
        
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
        # Taleo filling logic (often involves clicking 'Save and Continue')
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
        # Fuzzy match apply button
        keywords = ["Match", "Apply", "Start Application"]
        for k in keywords:
            btn = page.locator(f"button:has-text('{k}'), a:has-text('{k}')").first
            if btn.count() > 0 and btn.is_visible():
                self.human.move_and_click(btn)
                time.sleep(3)
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
        return GenericStrategy(humanizer)
