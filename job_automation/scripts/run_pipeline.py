import sys
import os
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from job_automation.scrapers.scraper_factory import ScraperFactory
from job_automation.core.auth.credential_manager import CredentialManager
from job_automation.core.resume_generator import ResumeGenerator
from job_automation.core.llm_client import LLMClient

def main():
    parser = argparse.ArgumentParser(description="JobRight Pipeline: Scrape + Generate")
    parser.add_argument("--start_url", default="https://jobright.ai/jobs/recommend")
    parser.add_argument("--max_jobs", type=int, default=5)
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    
    # Paths
    default_out = str(Path.home() / "Desktop" / "Google Auto")
    parser.add_argument("--out_dir", default=default_out, help="Output directory")
    parser.add_argument("--base_resume", default="base_resume.json", help="Path to base resume JSON")
    parser.add_argument("--session-dir", default="job_automation/.sessions")
    parser.add_argument("--force-login", action="store_true", help="Force fresh login")
    parser.add_argument("--skip_scrape", action="store_true", help="Skip scraping and just generate resumes")
    
    args = parser.parse_args()
    output_root = Path(args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    
    # ==========================================
    # PHASE 1: SCRAPING (Using ScraperFactory)
    # ==========================================
    jobs = []
    
    if not args.skip_scrape:
        print("\n🚀 PHASE 1: SCRAPING JOBS")
        
        # Load Credentials
        try:
            cred_file = Path("job_automation/config/credentials.yaml")
            if cred_file.exists():
                cred_manager = CredentialManager(credentials_file=cred_file)
                credentials = cred_manager.get_credentials('jobright')
            else:
                credentials = {}
        except Exception as e:
            print(f"⚠️ Warning loading credentials: {e}")
            credentials = {}
    
        config = {
            'credentials': credentials,
            'session_dir': args.session_dir,
            'force_login': args.force_login,
            'skip_auth': False if credentials else True
        }
        
        session_file = Path(args.session_dir) / "jobright_session.json"
        
        with sync_playwright() as p:
            # Launch Browser
            if session_file.exists() and not args.force_login:
                print(f"📂 Loading saved session from {session_file}")
                browser = p.chromium.launch(
                    headless=not args.visible,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(storage_state=str(session_file))
            else:
                browser = p.chromium.launch(
                    headless=not args.visible,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context()
                
            try:
                # Create Scraper
                scraper = ScraperFactory.create('jobright', context, config)
                jobs = scraper.scrape_jobs(args.start_url, args.max_jobs)
                print(f"\n✅ Scraped {len(jobs)} jobs")
                
                # Save Jobs
                for job in jobs:
                    # Readable Folder Name
                    import re
                    safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', job.title).strip()
                    safe_company = re.sub(r'[^a-zA-Z0-9_\- ]', '', job.company).strip() or "Unknown"
                    folder_name = f"{safe_company} - {safe_title}"[:60]
                    
                    job_dir = output_root / folder_name
                    job_dir.mkdir(parents=True, exist_ok=True)
                    
                    import json
                    from dataclasses import asdict
                    
                    job_file = job_dir / "details.json"
                    with open(job_file, 'w') as f:
                        json.dump(asdict(job), f, indent=2)
                    print(f"   💾 Saved: {job.title}")
    
            except Exception as e:
                print(f"❌ Scraping Error: {e}")
                sys.exit(1)
            finally:
                context.close()
                browser.close()
    else:
        print("\n⏭️  Skipping Phase 1 (Scraping)...")
        # Load existing jobs for generation
        print("   Loading existing jobs from output directory...")
        import json
        from job_automation.core.models import Job
        
        # Load all job folders
        jobs = []
        for job_dir in output_root.iterdir():
            if job_dir.is_dir():
                details_path = job_dir / "details.json"
                if details_path.exists():
                    try:
                        data = json.loads(details_path.read_text())
                        # Reconstruct Job object (minimal fields needed)
                        # We might need to handle missing fields gracefully
                        job = Job(**data)
                        jobs.append(job)
                    except:
                        pass
        print(f"   📂 Loaded {len(jobs)} existing jobs.")

    if not jobs:
        print("❌ No jobs found. Exiting.")
        sys.exit(1)

    # ==========================================
    # PHASE 2: GENERATION (ResumeGenerator)
    # ==========================================
    print("\n🚀 PHASE 2: GENERATING RESUMES")
    
    base_resume_path = Path(args.base_resume)
    if not base_resume_path.exists():
        if Path("profile.json").exists():
            base_resume_path = Path("profile.json")
            print(f"⚠️  Using fallback base resume: {base_resume_path}")
        else:
            print("❌ Base resume JSON not found (profile.json or resume.json needed).")
            sys.exit(1)
            
    try:
        llm = LLMClient()
        
        # Use JobRight Specialized Prompts by Default for this Pipeline
        project_root = Path(os.getcwd())
        project_root = Path(os.getcwd())
        # User-Specified V3 Prompts (Root Directory)
        jobright_writer = project_root / "resume_json_prompt_v3.txt"
        jobright_evaluator = project_root / "resume_evaluator_prompt_v3.txt"
        jobright_iteration = project_root / "resume_iteration_prompt_v3.txt"
        
        generator = ResumeGenerator(
            llm, 
            output_root, 
            base_resume_path,
            writer_prompt_path=jobright_writer,
            evaluator_prompt_path=jobright_evaluator,
            iteration_prompt_path=jobright_iteration
        )
        
        success_count = 0
        for job in jobs:
            print(f"\n⚡ Generating for: {job.title}")
            try:
                if generator.process_complete_workflow(job):
                    success_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                
        print(f"\n🎉 PIPELINE COMPLETE: {success_count}/{len(jobs)} Resumes Generated.")
        
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
