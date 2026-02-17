"""
Submission Tracking System
Prevents duplicate applications and tracks submission status
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Optional
import hashlib

class SubmissionTracker:
    """Track which jobs have been submitted to prevent duplicates."""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.db_file = workspace_dir / "submissions_database.json"
        self.db = self._load_database()
    
    def generate_job_id(self, company: str, job_title: str, apply_url: str) -> str:
        """Generate unique ID for a job."""
        # Use URL as primary identifier
        url_hash = hashlib.md5(apply_url.encode()).hexdigest()[:12]
        return f"{company}_{url_hash}"
    
    def is_already_submitted(self, job_id: str) -> bool:
        """Check if job has already been submitted."""
        return job_id in self.db and self.db[job_id].get('status') == 'submitted'
    
    def mark_as_submitted(self, job_id: str, job_info: Dict, confirmation_email: Optional[str] = None):
        """
        Mark a job as successfully submitted.
        
        Args:
            job_id: Unique job identifier
            job_info: Job details (company, title, url, etc.)
            confirmation_email: Email confirmation text if available
        """
        self.db[job_id] = {
            'company': job_info.get('company', ''),
            'job_title': job_info.get('job_title', ''),
            'apply_url': job_info.get('apply_url', ''),
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat(),
            'confirmation_email': confirmation_email,
            'job_folder': job_info.get('job_folder', '')
        }
        
        self._save_database()
        print(f"✅ Marked as SUBMITTED: {job_info.get('company')} - {job_info.get('job_title')}")
    
    def mark_as_failed(self, job_id: str, job_info: Dict, error: str):
        """Mark a job as failed (to retry later)."""
        self.db[job_id] = {
            'company': job_info.get('company', ''),
            'job_title': job_info.get('job_title', ''),
            'apply_url': job_info.get('apply_url', ''),
            'status': 'failed',
            'failed_at': datetime.now().isoformat(),
            'error': error,
            'job_folder': job_info.get('job_folder', '')
        }
        
        self._save_database()
    
    def get_submission_stats(self) -> Dict:
        """Get statistics about submissions."""
        total = len(self.db)
        submitted = sum(1 for j in self.db.values() if j.get('status') == 'submitted')
        failed = sum(1 for j in self.db.values() if j.get('status') == 'failed')
        
        return {
            'total': total,
            'submitted': submitted,
            'failed': failed,
            'success_rate': submitted / total if total > 0 else 0
        }
    
    def get_submitted_jobs(self) -> list:
        """Get list of all submitted jobs."""
        return [
            {
                'job_id': job_id,
                **job_data
            }
            for job_id, job_data in self.db.items()
            if job_data.get('status') == 'submitted'
        ]
    
    def _load_database(self) -> Dict:
        """Load submission database."""
        if self.db_file.exists():
            return json.loads(self.db_file.read_text())
        return {}
    
    def _save_database(self):
        """Save submission database."""
        self.db_file.write_text(json.dumps(self.db, indent=2))


def check_before_applying(job_folder: Path, tracker: SubmissionTracker) -> bool:
    """
    Check if job should be applied to.
    
    Returns:
        True if should apply, False if already submitted
    """
    # Read job info
    url_file = job_folder / "apply_url.txt"
    meta_file = job_folder / "meta.json"
    
    if not url_file.exists():
        return False
    
    apply_url = url_file.read_text().strip()
    
    # Try to get company and title
    company = "Unknown"
    job_title = "Unknown"
    
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            company = meta.get('company', company)
            job_title = meta.get('title', job_title)
        except:
            pass
    
    # Generate job ID
    job_id = tracker.generate_job_id(company, job_title, apply_url)
    
    # Check if already submitted
    if tracker.is_already_submitted(job_id):
        print(f"⏭️  SKIPPING: Already submitted to {company} - {job_title}")
        return False
    
    return True


def mark_job_submitted(job_folder: Path, tracker: SubmissionTracker, 
                       confirmation_email: Optional[str] = None):
    """Mark job as successfully submitted."""
    url_file = job_folder / "apply_url.txt"
    meta_file = job_folder / "meta.json"
    
    apply_url = url_file.read_text().strip()
    
    company = "Unknown"
    job_title = "Unknown"
    
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            company = meta.get('company', company)
            job_title = meta.get('title', job_title)
        except:
            pass
    
    job_id = tracker.generate_job_id(company, job_title, apply_url)
    
    job_info = {
        'company': company,
        'job_title': job_title,
        'apply_url': apply_url,
        'job_folder': str(job_folder)
    }
    
    tracker.mark_as_submitted(job_id, job_info, confirmation_email)
    
    # Also mark in the job folder itself
    status_file = job_folder / "submission_status.json"
    status_file.write_text(json.dumps({
        'status': 'submitted',
        'submitted_at': datetime.now().isoformat(),
        'job_id': job_id
    }, indent=2))


# Integration example for job_auto_submit.py:
"""
from submission_tracker import SubmissionTracker, check_before_applying, mark_job_submitted

# At start
tracker = SubmissionTracker(Path("Google Auto Internet"))

# Before processing each job
for job_folder in all_jobs:
    # CHECK IF ALREADY SUBMITTED
    if not check_before_applying(job_folder, tracker):
        continue  # Skip this job
    
    # Process the job...
    status = apply_to_job(job_folder)
    
    # After successful submission
    if status == "Submitted":
        mark_job_submitted(job_folder, tracker)
        
        # Optionally check email for confirmation
        # confirmation = check_email_for_confirmation(company_name)
        # if confirmation:
        #     mark_job_submitted(job_folder, tracker, confirmation)
"""


# Email verification helper
def parse_confirmation_email(email_text: str) -> Optional[Dict]:
    """
    Parse confirmation email to verify submission.
    
    Returns:
        {company, job_title, confirmation_code} if found, None otherwise
    """
    # Common patterns in confirmation emails
    patterns = [
        r"application.*received",
        r"thank you.*applying",
        r"confirmation.*\d+",
        r"reference.*number.*\d+",
    ]
    
    # This would need full email parsing logic
    # For now, just check if it looks like a confirmation
    email_lower = email_text.lower()
    
    if any(pattern in email_lower for pattern in ["application received", "thank you for applying"]):
        return {
            'confirmed': True,
            'email_snippet': email_text[:200]
        }
    
    return None
