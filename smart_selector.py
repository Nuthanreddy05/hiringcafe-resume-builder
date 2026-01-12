import time
import random
from playwright.sync_api import Page, Locator

class SelectorNotFoundError(Exception):
    pass

class FillValidationError(Exception):
    pass

class SmartSelector:
    """
    Robust element finder using multi-strategy fallback logic.
    Architectural Pattern: "Graceful Degradation"
    """
    
    def __init__(self, page: Page):
        self.page = page

    def find(self, field_name: str, field_type: str = "input"):
        """
        Generic finder using multiple strategies.
        Args:
            field_name: "email", "first name", "resume", etc.
            field_type: "input", "button", "file"
        """
        field_lower = field_name.lower()
        
        # Define strategies in order of preference
        strategies = []
        
        # 1. Exact ID (Best for stability if consistent)
        id_slug = field_name.replace(" ", "_").replace(" ", "-").lower()
        strategies.append(lambda: self.page.locator(f"#{id_slug}"))
        strategies.append(lambda: self.page.locator(f"#{field_name}"))
        
        # 2. Explicit Label (Accessibility standard)
        strategies.append(lambda: self.page.get_by_label(field_name, exact=False))
        
        # 3. Attributes (Name, API Hooks)
        if field_type == "input":
            strategies.append(lambda: self.page.locator(f"input[name='{field_name}']"))
            strategies.append(lambda: self.page.locator(f"input[name*='{id_slug}']"))
            strategies.append(lambda: self.page.locator(f"input[type='{field_name}']")) # e.g. type='email'
            
        # 4. Placeholder (Visual fallback)
        if field_type == "input":
             strategies.append(lambda: self.page.get_by_placeholder(field_name, exact=False))
             
        # 5. Text (Buttons/Links)
        if field_type == "button":
            strategies.append(lambda: self.page.get_by_role("button", name=field_name))
            strategies.append(lambda: self.page.locator(f"button:has-text('{field_name}')"))
            
        # Execute Strategies
        for i, strategy in enumerate(strategies):
            try:
                element = strategy()
                # Check existance/visibility
                if element.count() > 0 and element.first.is_visible():
                    return element.first
            except:
                continue
                
        raise SelectorNotFoundError(f"Could not find '{field_name}' after {len(strategies)} strategies")

    def fill_with_retry(self, field_name: str, value: str, max_retries: int = 3):
        """Robust fill with retries and verification."""
        for attempt in range(max_retries):
            try:
                element = self.find(field_name, "input")
                element.scroll_into_view_if_needed()
                element.fill(value)
                
                # Validation (React forms)
                time.sleep(0.1) 
                actual = element.input_value()
                if actual != value:
                    raise FillValidationError(f"Expected '{value}', got '{actual}'")
                    
                return True
            except (SelectorNotFoundError, FillValidationError, Exception) as e:
                print(f"    ⚠️ Fill Attempt {attempt+1} Error ({field_name}): {e}")
                time.sleep(2 ** attempt) # Exponential backoff
        
        print(f"    ❌ Failed to fill '{field_name}' after {max_retries} attempts.")
        return False

# Test Stub
if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("""
            <html>
                <body>
                    <label for="user_email">Email Address</label>
                    <input id="user_email" type="email" />
                    
                    <button>Submit Application</button>
                </body>
            </html>
        """)
        
        selector = SmartSelector(page)
        
        # Test 1: By Label
        print("Testing Email (Label)...")
        found = selector.find("Email Address")
        print(f"Found: {found}")
        
        # Test 2: By Type
        print("Testing Email (Type)...")
        found = selector.find("email") 
        print(f"Found: {found}")
        
        # Test 3: Button
        print("Testing Button...")
        found = selector.find("Submit Application", "button")
        print(f"Found: {found}")
        
        browser.close()
