import sys
import os
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from playwright.sync_api import sync_playwright
from job_automation.scrapers.jobright_authenticator import JobRightAuthenticator
from job_automation.core.auth.credential_manager import CredentialManager

def main():
    print("🚀 DEBUGGING DOM STRUCTURE")
    
    # Load credentials
    cred_manager = CredentialManager(credentials_file=Path("job_automation/config/credentials.yaml"))
    credentials = cred_manager.get_credentials('jobright')
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        session_file = Path("job_automation/.sessions/jobright_session.json")
        
        if session_file.exists():
            context = browser.new_context(storage_state=str(session_file))
        else:
            print("No session found! Authenticating...")
            context = browser.new_context()
            auth = JobRightAuthenticator(context, credentials, Path("job_automation/.sessions"))
            if not auth.authenticate():
                print("Auth failed")
                return

        page = context.new_page()
        page.goto("https://jobright.ai/jobs/recommend", wait_until="domcontentloaded")
        time.sleep(5) # Wait for React hydration
        
        # Scroll a bit
        page.mouse.wheel(0, 1000)
        time.sleep(2)
        
        # Dump HTML
        print("\n--- HTML DUMP START ---")
        # Dump only the body or a relevant container to avoid too much noise
        # We look for the main app container usually
        html_content = page.content()
        # Truncate to first 50kb or filter for 'job' keyword proximity if possible, 
        # but full dump (controlled) is safer.
        print(html_content[:50000]) # Print first 50k chars
        print("\n--- HTML DUMP END ---\n")
        
        # Also print simplified structure
        print("--- EXTRACTED STRUCTURE ---")
        inputs = page.evaluate("""() => {
             const result = [];
             // Get all divs with classes
             document.querySelectorAll('div[class]').forEach(div => {
                 if (div.className.includes('job') || div.className.includes('card')) {
                     result.push(`<div class="${div.className}"> ... </div>`);
                 }
             });
             // Get all links
             document.querySelectorAll('a[href]').forEach(a => {
                  result.push(`<a href="${a.href}">${a.innerText}</a>`);
             });
             return result.slice(0, 50); // Just first 50
        }""")
        for i in inputs:
            print(i)
            
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
