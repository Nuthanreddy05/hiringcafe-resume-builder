
import json
import re
from pathlib import Path
from datetime import datetime

OUTPUT_ROOT = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")

def backfill():
    print(f"🚀 Starting Backfill for {OUTPUT_ROOT}")
    count = 0
    
    for job_dir in OUTPUT_ROOT.iterdir():
        if job_dir.is_dir() and not job_dir.name.startswith('.'):
            # Check for details.json
            details_path = job_dir / "details.json"
            resume_path = job_dir / "resume.json"
            meta_path = job_dir / "meta.json"
            
            if details_path.exists() and not meta_path.exists():
                try:
                    # Load Data
                    details = json.loads(details_path.read_text())
                    
                    resume_text = ""
                    if resume_path.exists():
                        resume_data = json.loads(resume_path.read_text())
                        resume_text = resume_data.get("summary", "")[:500]
                    
                    # Create Meta Content
                    meta_content = {
                        "company": details.get("company", "Unknown"),
                        "title": details.get("title", "Unknown"),
                        "job_url": details.get("url", ""),
                        "apply_url": details.get("apply_url", ""),
                        "resume_text": resume_text,
                        "status": "generated",
                        "created_at": str(datetime.now())
                    }
                    
                    # Save
                    meta_path.write_text(json.dumps(meta_content, indent=2), encoding="utf-8")
                    print(f"✅ Created meta.json for: {job_dir.name}")
                    count += 1
                    
                except Exception as e:
                    print(f"❌ Failed processing {job_dir.name}: {e}")
            elif meta_path.exists():
                print(f"⏭️  Skipping (Exists): {job_dir.name}")

    print(f"\n🎉 Backfill Complete! Updated {count} jobs.")

if __name__ == "__main__":
    backfill()
