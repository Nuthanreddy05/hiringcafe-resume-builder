import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from playwright.sync_api import sync_playwright
from job_automation.scrapers.scraper_factory import ScraperFactory
from job_automation.core.auth.credential_manager import CredentialManager

def main():
    parser = argparse.ArgumentParser(description="JobRight Scraper with Auth")
    parser.add_argument("--start_url", default="https://jobright.ai/jobs/recommend")
    parser.add_argument("--max_jobs", type=int, default=5)
    parser.add_argument("--headless", action="store_true")
    # Aligning with "Google Auto" database per user request
    default_out = str(Path.home() / "Desktop" / "Google Auto")
    parser.add_argument("--out_dir", default=default_out)
    parser.add_argument("--session-dir", default="job_automation/.sessions")
    parser.add_argument("--force-login", action="store_true", help="Force fresh login (ignore saved session)")
    parser.add_argument("--use-session", action="store_true", help="Implicitly used, kept for compat")
    
    args = parser.parse_args()
    
    print("🚀 JOBRIGHT SCRAPER - AUTHENTICATED MODE")
    print("="*80)
    
    # Load credentials
    try:
        cred_file = Path("job_automation/config/credentials.yaml")
        if not cred_file.exists():
            print(f"⚠️ Credentials file not found at {cred_file}")
            print("   Using UN-AUTHENTICATED mode (might fail)...")
            credentials = {}
        else:
            cred_manager = CredentialManager(credentials_file=cred_file)
            credentials = cred_manager.get_credentials('jobright')
    except Exception as e:
        print(f"⚠️ Warning loading credentials: {e}")
        credentials = {}

    
    # Configure scraper
    config = {
        'credentials': credentials,
        'session_dir': args.session_dir,
        'force_login': args.force_login,
        'skip_auth': False if credentials else True # Skip if no creds
    }
    
    # Create browser with session state if it exists
    session_file = Path(args.session_dir) / "jobright_session.json"
    
    with sync_playwright() as p:
        # Load saved session if available and not forcing fresh login
        if session_file.exists() and not args.force_login:
            print(f"📂 Loading saved session from {session_file}")
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context(storage_state=str(session_file))
        else:
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context()
        
        try:
            # Create scraper (will authenticate automatically if config allows)
            scraper = ScraperFactory.create('jobright', context, config)
            
            # Scrape jobs
            jobs = scraper.scrape_jobs(args.start_url, args.max_jobs)
            
            output_root = Path(args.out_dir)
            output_root.mkdir(parents=True, exist_ok=True)
            
            print(f"\n✅ Scraped {len(jobs)} jobs from JobRight")
            for job in jobs:
                print(f"   - {job.title} at {job.company} (Posted: {job.posted_at})")
                
                # Save to JSON
                # Create a safe ID from URL or title
                safe_id = job.url.split('/')[-1] if 'http' in job.url else str(abs(hash(job.url)))
                job_dir = output_root / f"{safe_id}"
                job_dir.mkdir(parents=True, exist_ok=True)
                
                import json
                from dataclasses import asdict
                
                job_file = job_dir / "details.json"
                try:
                    with open(job_file, 'w') as f:
                        json.dump(asdict(job), f, indent=2)
                    print(f"     💾 Saved to {job_file}")
                except Exception as e:
                    print(f"     ⚠️ Failed to save JSON: {e}")
            
        except RuntimeError as e:
            print(f"\n✗ ERROR: {e}")
            print(f"   Try running: python3 job_automation/scripts/setup_jobright_auth.py")
        except Exception as e:
             print(f"\n✗ UNEXPECTED ERROR: {e}")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
