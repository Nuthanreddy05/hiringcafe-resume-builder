"""
Integrate Submission Tracker into job_auto_submit.py

This adds duplicate prevention to ensure we never apply to the same job twice.
"""

from pathlib import Path
import sys

# Read the current job_auto_submit.py
script_path = Path("job_auto_submit.py")
content = script_path.read_text()

# Check if submission_tracker is already imported
if "from submission_tracker import" in content:
    print("✅ Submission tracker already integrated")
    sys.exit(0)

# Find the imports section
import_line = "from playwright.sync_api import sync_playwright, Page, Locator"

# Add submission tracker import after playwright import
new_import = """from playwright.sync_api import sync_playwright, Page, Locator
from submission_tracker import SubmissionTracker, check_before_applying, mark_job_submitted"""

content = content.replace(import_line, new_import)

# Find the main loop where jobs are processed
# Look for: for job_folder in Path(jobs_dir).iterdir():

old_loop_start = """    for job_folder in Path(jobs_dir).iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith('_'):
            continue"""

new_loop_start = """    # Initialize submission tracker
    tracker = SubmissionTracker(Path(jobs_dir))
    print(f"📚 Loaded submission database: {len(tracker.db)} entries")
    
    for job_folder in Path(jobs_dir).iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith('_'):
            continue
        
        # CHECK IF ALREADY SUBMITTED
        if not check_before_applying(job_folder, tracker):
            continue  # Skip already submitted jobs"""

content = content.replace(old_loop_start, new_loop_start)

# Find where we handle successful submission
# Look for the user confirmation part
old_confirm = """        if user_confirm.lower() == 'y':
            print(f"      ✅ Success! Application submitted.\")
            status_file.write_text(json.dumps({
                'status': 'submitted',
                'timestamp': datetime.now().isoformat()
            }))"""

new_confirm = """        if user_confirm.lower() == 'y':
            print(f"      ✅ Success! Application submitted.")
            
            # Mark in submission tracker
            mark_job_submitted(job_folder, tracker)
            
            status_file.write_text(json.dumps({
                'status': 'submitted',
                'timestamp': datetime.now().isoformat()
            }))"""

content = content.replace(old_confirm, new_confirm)

# Write back
script_path.write_text(content)
print("✅ Integrated submission tracker into job_auto_submit.py")
print("   - Added import")
print("   - Added duplicate check before processing")
print("   - Added submission marking after success")
