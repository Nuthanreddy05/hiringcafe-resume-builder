import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from playwright.sync_api import sync_playwright
from job_automation.core.auth.credential_manager import CredentialManager
from job_automation.scrapers.jobright_authenticator import JobRightAuthenticator

def main():
    parser = argparse.ArgumentParser(description="Setup JobRight Authentication")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--session-dir", default="job_automation/.sessions", help="Session storage directory")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🔧 JOBRIGHT AUTHENTICATION SETUP")
    print("="*80)
    
    # Load credentials
    try:
        cred_file = Path("job_automation/config/credentials.yaml")
        if not cred_file.exists():
            print(f"❌ Error: {cred_file} not found.")
            print("   Please copy 'config/credentials.yaml.example' to 'config/credentials.yaml' and fill it in.")
            return

        cred_manager = CredentialManager(credentials_file=cred_file)
        credentials = cred_manager.get_credentials('jobright')
        
        print(f"\n📋 Login method: {credentials.get('method', 'email')}")
        
        # Validate credentials
        cred_manager.validate_credentials('jobright', credentials.get('method', 'email'))
        print(f"✓ Credentials validated")
        
    except Exception as e:
        print(f"❌ {e}")
        return
    
    # Launch browser
    print("\n   Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        
        # Create authenticator
        authenticator = JobRightAuthenticator(
            context=context,
            credentials=credentials,
            session_dir=Path(args.session_dir)
        )
        
        # Attempt authentication
        print(f"\n🔐 Attempting login...")
        success = authenticator.authenticate()
        
        if success:
            print(f"\n✅ SUCCESS! Authentication completed.")
            print(f"📁 Session saved to: {authenticator.session_file}")
            print(f"\n💡 You can now run scraping with saved session:")
            print(f"   python3 job_automation/scripts/scrape_jobright.py --use-session")
        else:
            print(f"\n✗ FAILED! Could not authenticate.")
            print(f"   Please check your credentials in config/credentials.yaml")
        
        # Wait for user input before closing to allow debugging
        print("\n   Press Enter to close the browser...")
        input()
        
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
