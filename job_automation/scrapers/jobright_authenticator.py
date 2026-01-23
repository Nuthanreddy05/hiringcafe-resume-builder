import time
from playwright.sync_api import Page
from job_automation.core.auth.base_authenticator import BaseAuthenticator

class JobRightAuthenticator(BaseAuthenticator):
    """JobRight-specific authentication implementation"""
    
    def get_source_name(self) -> str:
        return "jobright"
    
    def login(self, page: Page) -> bool:
        """
        Perform JobRight login
        Supports: Email/Password, Google OAuth, LinkedIn OAuth
        """
        try:
            # Navigate to login page
            print(f"      → Navigating to JobRight login...")
            page.goto("https://jobright.ai/login", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Determine login method from credentials
            login_method = self.credentials.get('method', 'email')
            
            if login_method == 'email':
                return self._login_with_email(page)
            elif login_method == 'google':
                return self._login_with_google(page)
            elif login_method == 'linkedin':
                return self._login_with_linkedin(page)
            else:
                raise ValueError(f"Unknown login method: {login_method}")
        
        except Exception as e:
            print(f"      ✗ Login error: {e}")
            return False
    
    def _login_with_email(self, page: Page) -> bool:
        """Login using email and password"""
        print(f"      → Logging in with email...")
        
        email = self.credentials.get('email')
        password = self.credentials.get('password')
        
        if not email or not password:
            raise ValueError("Email and password required for email login")
        
        # Fill email
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
        email_input.fill(email)
        print(f"      ✓ Entered email")
        
        # Fill password
        password_input = page.locator('input[type="password"], input[name="password"]')
        password_input.fill(password)
        print(f"      ✓ Entered password")
        
        # Click login button
        # Use more specific selector to avoid matching search buttons (e.g. "GO")
        login_button = page.locator('button').filter(has_text="Sign in").first
        if not login_button.is_visible():
             login_button = page.locator('button').filter(has_text="Log in").first
        
        if not login_button.is_visible():
             # Fallback for specific class if text fails
             login_button = page.locator('.index_sign-in-button__jjge4')
             
        login_button.click()
        print(f"      ✓ Clicked login button")
        
        # Wait for navigation (redirect after login)
        try:
            page.wait_for_url("**/jobs/**", timeout=15000)
            print(f"      ✓ Redirected to jobs page")
        except:
            # Check if we're on the jobs page by content
            page.wait_for_timeout(3000)
        
        # Verify login success
        return self.verify_authenticated(page)
    
    def _login_with_google(self, page: Page) -> bool:
        """Login using Google OAuth"""
        print(f"      → Logging in with Google...")
        
        # Click "Continue with Google" button
        google_button = page.locator('button:has-text("Google"), a:has-text("Google")')
        
        with page.expect_popup() as popup_info:
            google_button.click()
        
        google_page = popup_info.value
        
        # Fill Google credentials
        email = self.credentials.get('google_email')
        password = self.credentials.get('google_password')
        
        # Google email step
        google_page.locator('input[type="email"]').fill(email)
        google_page.locator('button:has-text("Next")').click()
        google_page.wait_for_timeout(2000)
        
        # Google password step
        google_page.locator('input[type="password"]').fill(password)
        google_page.locator('button:has-text("Next")').click()
        
        # Wait for OAuth redirect back to JobRight
        page.wait_for_url("**/jobs/**", timeout=20000)
        google_page.close()
        
        return self.verify_authenticated(page)
    
    def _login_with_linkedin(self, page: Page) -> bool:
        """Login using LinkedIn OAuth"""
        print(f"      → Logging in with LinkedIn...")
        
        # Click "Continue with LinkedIn" button
        linkedin_button = page.locator('button:has-text("LinkedIn"), a:has-text("LinkedIn")')
        
        with page.expect_popup() as popup_info:
            linkedin_button.click()
        
        linkedin_page = popup_info.value
        
        # Fill LinkedIn credentials
        email = self.credentials.get('linkedin_email')
        password = self.credentials.get('linkedin_password')
        
        linkedin_page.locator('input[name="session_key"]').fill(email)
        linkedin_page.locator('input[name="session_password"]').fill(password)
        linkedin_page.locator('button[type="submit"]').click()
        
        # Handle 2FA if present
        try:
            # Check for verification code input
            if linkedin_page.locator('input[name="pin"]').count() > 0:
                print(f"      ⚠️  2FA detected! Please enter code manually.")
                # Wait for user to enter 2FA code manually
                linkedin_page.wait_for_url("**/feed/**", timeout=60000)
        except:
            pass
        
        # Wait for OAuth redirect back to JobRight
        page.wait_for_url("**/jobs/**", timeout=20000)
        linkedin_page.close()
        
        return self.verify_authenticated(page)
    
    def verify_authenticated(self, page: Page) -> bool:
        """
        Check if we're authenticated by looking for user-specific elements
        """
        try:
            # Navigate to jobs page to verify
            if not page.url.startswith("https://jobright.ai/jobs"):
                page.goto("https://jobright.ai/jobs/recommend", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
            
            # Check for authenticated elements
            # 1. User profile/avatar
            has_profile = page.locator('[class*="profile"], [class*="avatar"], img[alt*="profile"]').count() > 0
            
            # 2. Jobs are visible
            has_jobs = page.locator('[class*="job-card"], [class*="JobCard"]').count() > 0
            
            # 3. No login prompt
            no_login_prompt = page.locator('button:has-text("Sign in"), button:has-text("Log in")').count() == 0
            
            is_authenticated =  has_jobs # relaxed check for now as profiles vary, but jobs being visible vs login wall is key
            
            # More strict check if possible
            if page.url == "https://jobright.ai/login":
                is_authenticated = False

            if is_authenticated:
                print(f"      ✓ Authentication verified")
            else:
                print(f"      ✗ Not authenticated (profile={has_profile}, jobs={has_jobs}, no_login={no_login_prompt})")
            
            return is_authenticated
        
        except Exception as e:
            print(f"      ✗ Verification error: {e}")
            return False
