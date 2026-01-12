
import os
import json
import argparse
from pathlib import Path
from database import JobManager
from ats_handlers import ATSDetector

def scan_and_load(source_dir: str):
    """
    Scans source_dir for job folders and loads them into the DB.
    Expected structure:
      source_dir/
        <company>_<job_id>/
          NuthanReddy.pdf
          apply_url.txt
          meta.json (optional but preferred)
    """
    source_path = Path(source_dir).resolve()
    if not source_path.exists():
        print(f"❌ Source directory not found: {source_path}")
        return

    print(f"📂 Scanning: {source_path}")
    
    db = JobManager()
    count = 0
    updated = 0
    
    # Iterate immediate subdirectories
    for folder in source_path.iterdir():
        if not folder.is_dir():
            continue
            
        # Check for PDF
        resume_pdf = folder / "NuthanReddy.pdf"
        if not resume_pdf.exists():
            # Try finding any PDF if NuthanReddy.pdf missing? 
            # Sticking to strict convention for now to avoid junk.
            continue
            
        # Get Job Meta
        url = ""
        company = ""
        job_id = folder.name
        
        # 1. Try meta.json (Best)
        meta_file = folder / "meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                url = meta.get("apply_url") or meta.get("job_url", "")
                company = meta.get("company", "")
                job_id = meta.get("job_id", folder.name)
            except Exception as e:
                print(f"   ⚠️ Internal meta.json error {folder.name}: {e}")
                
        # 2. Fallback to apply_url.txt
        if not url:
            url_file = folder / "apply_url.txt"
            if url_file.exists():
                url = url_file.read_text().strip()
                
        if not url:
            print(f"   ⚠️ Skipping {folder.name}: No URL found")
            continue
            
        # Detect ATS
        ats_type = "generic"
        detector = ATSDetector.get_handler(url)
        # Map handler class to type string
        handler_name = detector.__class__.__name__
        if "Greenhouse" in handler_name: ats_type = "greenhouse"
        elif "Lever" in handler_name: ats_type = "lever"
        elif "Ashby" in handler_name: ats_type = "ashby"
        
        # Insert into DB
        print(f"   ➕ Loading: {job_id} ({ats_type})")
        # Use str() for paths to avoid Path objects in DB binding if generic
        success = db.add_job(
            job_id=job_id,
            url=url,
            company=company,
            resume_path=str(resume_pdf),
            folder_path=str(folder),
            ats_type=ats_type
        )
        if success:
            count += 1
            
    print(f"✅ Scanning Complete. Loaded/Updated {count} jobs.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load generated job packages into DB")
    parser.add_argument("--source", required=True, help="Directory containing job folders")
    args = parser.parse_args()
    
    scan_and_load(args.source)
