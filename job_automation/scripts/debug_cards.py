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
    print("🚀 DEBUGGING CARD ATTRIBUTES")
    
    # Load credentials
    cred_manager = CredentialManager(credentials_file=Path("job_automation/config/credentials.yaml"))
    credentials = cred_manager.get_credentials('jobright')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        session_file = Path("job_automation/.sessions/jobright_session.json")
        context = browser.new_context(storage_state=str(session_file)) if session_file.exists() else browser.new_context()

        if not session_file.exists():
            auth = JobRightAuthenticator(context, credentials, Path("job_automation/.sessions"))
            if not auth.authenticate(): return

        page = context.new_page()
        page.goto("https://jobright.ai/jobs/recommend", wait_until="domcontentloaded")
        time.sleep(5) 
        
        print("\n--- JOB CARDS INSPECTION ---")
        
        # Execute JS to find cards and dump their attributes
        cards_info = page.evaluate("""() => {
             const results = [];
             // Selector based on previous dump
             const cards = document.querySelectorAll('.index_job-card__AsPKC, [class*="job-card"]');
             
             cards.forEach((card, index) => {
                 const attrs = {};
                 for (let i = 0; i < card.attributes.length; i++) {
                     const attr = card.attributes[i];
                     attrs[attr.name] = attr.value;
                 }
                 
                 // Also look for react props often stored in keys starting with __react
                 const reactKeys = Object.keys(card).filter(k => k.startsWith('__react'));
                 
                 results.push({
                     index: index,
                     text: card.innerText.substring(0, 50).replace(/\\n/g, ' '),
                     attributes: attrs,
                     reactKeys: reactKeys
                 });
             });
             return results;
        }""")
        
        for card in cards_info:
            print(f"Card {card['index']}: {card['text']}...")
            print(f"   Attributes: {card['attributes']}")
            print(f"   ReactKeys: {card['reactKeys']}")
            print("-" * 40)
            
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
