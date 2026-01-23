import sys
import os
import argparse
import json
from pathlib import Path

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from job_automation.core.llm_client import LLMClient
from job_automation.core.resume_generator import ResumeGenerator
from job_automation.core.models import Job

def main():
    parser = argparse.ArgumentParser(description="Generate Resumes from Scraped JSON")
    # Aligning with "Google Auto" database
    default_in = str(Path.home() / "Desktop" / "Google Auto")
    parser.add_argument("--input_dir", default=default_in, help="Directory containing job folders")
    parser.add_argument("--base_resume", default="resume.json", help="Path to base resume JSON")
    parser.add_argument("--limit", type=int, default=0, help="0 = All jobs")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    base_resume_path = Path(args.base_resume)
    
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        sys.exit(1)
        
    if not base_resume_path.exists():
        print(f"❌ Base resume not found: {base_resume_path}")
        sys.exit(1)
        
    # Initialize Core Components
    try:
        llm = LLMClient()
        generator = ResumeGenerator(llm, input_dir, base_resume_path)
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        sys.exit(1)
        
    # Scan for jobs
    job_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    print(f"📂 Found {len(job_dirs)} job folders in {input_dir}")
    
    count = 0
    for job_dir in job_dirs:
        if args.limit > 0 and count >= args.limit:
            break
            
        details_file = job_dir / "details.json"
        if not details_file.exists():
            continue
            
        # Skip if already generated (Optional, but good for resume)
        if (job_dir / "resume.pdf").exists():
            print(f"⏩  Skipping {job_dir.name} (resume.pdf exists)")
            continue
            
        # Load Job
        try:
            data = json.loads(details_file.read_text())
            job = Job(**data)
        except Exception as e:
            print(f"⚠️  Skipping invalid job file {details_file}: {e}")
            continue
            
        # Process
        success = generator.process_complete_workflow(job)
        if success:
            count += 1
            print(f"✅ Completed {job.title} (#{count})")
        else:
            print(f"❌ Failed {job.title}")
            
    print(f"\n🎉 Generation Complete. Processed {count} jobs.")

if __name__ == "__main__":
    main()
