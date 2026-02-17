#!/usr/bin/env python3
"""
Application Status Dashboard
View all job applications and their status
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

TRACKER_FILE = Path(__file__).parent / "application_tracker.json"
JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def load_tracker():
    """Load tracker data"""
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {"applications": {}, "last_check": None}

def get_all_jobs():
    """Get all jobs from Desktop/Google Auto"""
    if not JOBS_DIR.exists():
        return []
    
    jobs = []
    for job_folder in JOBS_DIR.iterdir():
        if job_folder.is_dir() and not job_folder.name.startswith("_"):
            meta_file = job_folder / "meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                        jobs.append({
                            "folder": job_folder.name,
                            "company": meta.get("company", "Unknown"),
                            "title": meta.get("title", "Unknown"),
                            "platform": meta.get("platform", "Unknown"),
                            "created": job_folder.stat().st_mtime
                        })
                except:
                    pass
    
    return sorted(jobs, key=lambda x: x["created"], reverse=True)

def display_dashboard():
    """Display application status dashboard"""
    
    print("=" * 80)
    print("📊 JOB APPLICATION STATUS DASHBOARD")
    print("=" * 80)
    
    # Load data
    tracker = load_tracker()
    all_jobs = get_all_jobs()
    
    if tracker.get("last_check"):
        last_check = datetime.fromisoformat(tracker["last_check"])
        print(f"\n📧 Last Gmail check: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"📁 Total jobs generated: {len(all_jobs)}")
    print(f"✅ Total confirmations: {len(tracker['applications'])}")
    
    # Stats by platform
    if all_jobs:
        platforms = Counter(job["platform"] for job in all_jobs)
        print(f"\n🏢 Jobs by ATS Platform:")
        for platform, count in platforms.most_common():
            print(f"   {platform}: {count}")
    
    # Recent jobs
    print(f"\n📋 RECENT JOBS (Last 20)")
    print("=" * 80)
    
    for idx, job in enumerate(all_jobs[:20], 1):
        created_date = datetime.fromtimestamp(job["created"]).strftime("%b %d")
        
        # Check if confirmed
        company_lower = job["company"].lower()
        confirmed = any(
            company_lower in app["company"].lower() or company_lower in app["sender"].lower()
            for app in tracker["applications"].values()
        )
        
        status = "✅" if confirmed else "⏳"
        
        print(f"{idx:2}. {status} [{job['platform']:15}] {job['company']:25} - {job['title'][:40]}")
        print(f"     📅 {created_date} | 📁 {job['folder'][:60]}")
    
    # Confirmed applications
    if tracker["applications"]:
        print(f"\n✅ CONFIRMED APPLICATIONS ({len(tracker['applications'])})")
        print("=" * 80)
        
        for idx, (app_id, app) in enumerate(sorted(
            tracker["applications"].items(),
            key=lambda x: x[1].get("checked_at", ""),
            reverse=True
        )[:15], 1):
            print(f"{idx:2}. {app['company']}")
            print(f"     📧 {app['subject']}")
            print(f"     📅 {app['date'][:40]}")
            print()
    
    print("=" * 80)
    print("💡 TIPS:")
    print("  • Run: python3 daily_gmail_monitor.py  (check for new responses)")
    print(f"  • Tracker file: {TRACKER_FILE}")
    print(f"  • Jobs folder: {JOBS_DIR}")
    print("=" * 80)

def main():
    display_dashboard()

if __name__ == "__main__":
    main()
