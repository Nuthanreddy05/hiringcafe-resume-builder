
import os
import json
import argparse
from pathlib import Path
from database import JobManager
from ats_handlers import ATSDetector

from security_validator import SecurityValidator

def scan_and_load(source_dir: str):
    """
    Scans source_dir for job folders and loads them into the DB with SECURITY VALIDATION.
    """
    source_path = Path(source_dir).expanduser().resolve()
    
    # Security: Validate Source Path
    is_valid, reason = SecurityValidator.validate_folder_path(source_path)
    if not is_valid:
        print(f"❌ Security Error: Source path invalid - {reason}")
        return

    if not source_path.exists():
        print(f"❌ Source directory not found: {source_path}")
        return

    print(f"📂 Scanning: {source_path}")
    
    db = JobManager()
    count = 0
    skipped_count = 0
    
    # Sort folders by modification time (Newest -> Oldest)
    # Newest folders get inserted FASTEST (Lower IDs) if we process sequentially.
    try:
        folders = sorted([f for f in source_path.iterdir() if f.is_dir()], key=lambda f: f.stat().st_mtime, reverse=True)
    except Exception as e:
        print(f"⚠️ Sorting failed, falling back to default order: {e}")
        folders = [f for f in source_path.iterdir() if f.is_dir()]

    # Iterate sorted folders
    for folder in folders:         
        # Skip processed/special folders
        if folder.name.startswith("[DONE]") or folder.name.startswith("FAILED") or folder.name.startswith("_"):
             continue

        # Security: Validate Subfolder Path
        is_valid, reason = SecurityValidator.validate_folder_path(folder)
        if not is_valid:
            print(f"   🚨 Skipping Unsafe Folder {folder.name}: {reason}")
            skipped_count += 1
            continue

        # Check for PDF
        resume_pdf = folder / "NuthanReddy.pdf"
        if not resume_pdf.exists():
            continue
            
        # Get Job Meta
        url = ""
        company = SecurityValidator.sanitize_text(folder.name.split('_')[0])
        job_id = folder.name
        role = None
        
        # 1. Try meta.json (Best)
        meta_file = folder / "meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                raw_url = meta.get("apply_url") or meta.get("job_url", "")
                url = raw_url.strip()
                company = SecurityValidator.sanitize_text(meta.get("company", company))
                # job_id = meta.get("job_id", folder.name) <-- GARBAGE SOURCE
                # Always trust folder name for ID
                job_id = folder.name
                role = SecurityValidator.sanitize_text(meta.get("role") or meta.get("title"))
            except Exception as e:
                print(f"   ⚠️ Internal meta.json error {folder.name}: {e}")
                
        # 2. Fallback to apply_url.txt
        if not url:
            url_file = folder / "apply_url.txt"
            if url_file.exists():
                url = url_file.read_text().strip()
                
        if not url:
            print(f"   ⚠️ Skipping {folder.name}: No URL found")
            skipped_count += 1
            continue
            
        # Get Cover Letter (Optional)
        cover_letter_path = folder / "cover_letter.txt"
        cover_letter_text = ""
        if cover_letter_path.exists():
            try:
                cover_letter_text = cover_letter_path.read_text().strip()
                print(f"   📄 Cover Letter found: {len(cover_letter_text)} chars")
            except: pass
            
        # SECURITY CRITICAL: Validate URL
        is_valid, reason = SecurityValidator.validate_url(url)
        if not is_valid:
            print(f"   🛡️ BLOCKED Malicious URL in {folder.name}: {reason}")
            skipped_count += 1
            continue

        # Detect ATS
        ats_type = "generic"
        try:
            detector = ATSDetector.get_handler(url)
            handler_name = detector.__class__.__name__
            if "Greenhouse" in handler_name: ats_type = "greenhouse"
            elif "Lever" in handler_name: ats_type = "lever"
            elif "Ashby" in handler_name: ats_type = "ashby"
            elif "Taleo" in handler_name: ats_type = "taleo"
            elif "Workday" in handler_name: ats_type = "workday"
            elif "SmartRecruiters" in handler_name: ats_type = "smartrecruiters"
        except:
            pass
        
        # Insert into DB
        print(f"   ➕ Loading: {job_id} ({ats_type})")
        success = db.add_job(
            job_id=job_id,
            url=url,
            company=company,
            resume_path=str(resume_pdf),
            folder_path=str(folder),
            ats_type=ats_type,
            cover_letter=cover_letter_text
        )
        if success:
            count += 1
        else:
            skipped_count += 1
            
    print(f"✅ Scanning Complete. Loaded {count} jobs. Skipped/Blocked {skipped_count}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load generated job packages into DB")
    parser.add_argument("--source", required=True, help="Directory containing job folders")
    args = parser.parse_args()
    
    scan_and_load(args.source)
