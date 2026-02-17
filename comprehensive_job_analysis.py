#!/usr/bin/env python3
"""
Comprehensive Job Application Analysis
Analyzes job folders, Gmail confirmations, scraping dates, and posting dates
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import re
from gmail_helper import get_gmail_service
import email
from email.header import decode_header

# Load from .env
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")

load_env()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def analyze_job_folders():
    """Analyze all job folders"""
    print("\n📁 Analyzing Job Folders...")
    print("=" * 80)
    
    if not JOBS_DIR.exists():
        print(f"❌ Directory not found: {JOBS_DIR}")
        return []
    
    jobs = []
    folders = list(JOBS_DIR.iterdir())
    
    for job_folder in folders:
        if not job_folder.is_dir() or job_folder.name.startswith("_") or job_folder.name.startswith("."):
            continue
        
        job_data = {
            "folder_name": job_folder.name,
            "created_timestamp": job_folder.stat().st_mtime,
            "created_date": datetime.fromtimestamp(job_folder.stat().st_mtime),
            "has_resume": (job_folder / "NuthanReddy.pdf").exists(),
            "has_meta": (job_folder / "meta.json").exists(),
            "has_url": (job_folder / "apply_url.txt").exists(),
            "has_audit": (job_folder / "_AUDIT").exists()
        }
        
        # Read meta.json if exists
        meta_file = job_folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    job_data.update({
                        "company": meta.get("company", "Unknown"),
                        "title": meta.get("title", "Unknown"),
                        "location": meta.get("location", "Unknown"),
                        "platform": meta.get("platform", "Unknown"),
                        "url": meta.get("apply_url", "Unknown")
                    })
            except Exception as e:
                job_data["meta_error"] = str(e)
        
        # Read apply_url.txt if exists
        url_file = job_folder / "apply_url.txt"
        if url_file.exists():
            try:
                job_data["apply_url"] = url_file.read_text().strip()
            except:
                pass
        
        # Check for audit/scoring data
        audit_dir = job_folder / "_AUDIT"
        if audit_dir.exists():
            try:
                # Look for final score
                final_check = audit_dir / "09_final_package_check.md"
                if final_check.exists():
                    content = final_check.read_text()
                    score_match = re.search(r'Score:\s*(\d+)', content)
                    if score_match:
                        job_data["final_score"] = int(score_match.group(1))
            except:
                pass
        
        jobs.append(job_data)
    
    # Sort by creation date
    jobs.sort(key=lambda x: x["created_timestamp"], reverse=True)
    
    print(f"✅ Found {len(jobs)} job folders")
    return jobs

def analyze_gmail_confirmations():
    """Get all Gmail confirmations"""
    print("\n📧 Analyzing Gmail Confirmations...")
    print("=" * 80)
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("❌ Gmail credentials not found")
        return []
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("❌ Failed to connect to Gmail")
        return []
    
    print("✅ Connected to Gmail")
    
    confirmations = []
    
    try:
        mail.select("inbox")
        
        # Search for application-related emails (last 30 days)
        since_date = (datetime.now()).strftime("%d-%b-%Y")
        
        keywords = ['SUBJECT "application"', 'SUBJECT "thank you"', 'SUBJECT "received"']
        seen_ids = set()
        
        for keyword in keywords:
            search_query = f'({keyword})'
            status, messages = mail.search(None, search_query)
            
            if status == "OK":
                email_ids = messages[0].split()
                
                for e_id in email_ids:
                    if e_id in seen_ids:
                        continue
                    seen_ids.add(e_id)
                    
                    try:
                        _, msg_data = mail.fetch(e_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                subject_header = decode_header(msg["Subject"])[0]
                                subject = subject_header[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                                
                                sender = msg.get("From", "")
                                date_str = msg.get("Date", "")
                                
                                # Try to parse date
                                try:
                                    from email.utils import parsedate_to_datetime
                                    email_date = parsedate_to_datetime(date_str)
                                except:
                                    email_date = None
                                
                                company = extract_company_from_email(sender, subject)
                                
                                confirmations.append({
                                    "company": company,
                                    "subject": subject,
                                    "sender": sender,
                                    "date_str": date_str,
                                    "date": email_date,
                                    "raw_sender": sender
                                })
                    except Exception as e:
                        continue
        
        print(f"✅ Found {len(confirmations)} confirmation emails")
        
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass
    
    return confirmations

def extract_company_from_email(sender, subject):
    """Extract company name from email"""
    sender_lower = sender.lower()
    
    # Extract from domain
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        common_domains = ['gmail', 'noreply', 'no-reply', 'donotreply', 'mail', 'greenhouse', 'smartrecruiters', 'icims', 'lever', 'workday', 'taleo', 'recruiting', 'talent', 'ashbyhq']
        if domain not in common_domains:
            return domain.replace('-', ' ').title()
    
    # Extract from sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'no reply', 'noreply']:
            return name
    
    # Try to find company name in subject
    subject_lower = subject.lower()
    for word in subject_lower.split():
        if len(word) > 4 and word not in ['thank', 'application', 'your', 'interest', 'position']:
            return word.title()
    
    return "Unknown"

def cross_reference_data(jobs, confirmations):
    """Cross-reference jobs with Gmail confirmations"""
    print("\n🔍 Cross-Referencing Data...")
    print("=" * 80)
    
    matched = 0
    unmatched_jobs = []
    unmatched_emails = []
    
    # Match jobs with confirmations
    for job in jobs:
        job["confirmed"] = False
        job_company = job.get("company", "").lower()
        
        for conf in confirmations:
            conf_company = conf["company"].lower()
            conf_sender = conf["sender"].lower()
            
            # Try to match by company name or domain
            if job_company in conf_company or job_company in conf_sender or conf_company in job_company:
                job["confirmed"] = True
                job["confirmation_date"] = conf["date"]
                job["confirmation_subject"] = conf["subject"]
                matched += 1
                break
    
    # Find unmatched
    confirmed_count = sum(1 for j in jobs if j.get("confirmed"))
    unmatched_jobs = [j for j in jobs if not j.get("confirmed")]
    
    # Find confirmations without matching job folder
    job_companies = set(j.get("company", "").lower() for j in jobs)
    for conf in confirmations:
        conf_company = conf["company"].lower()
        found = any(conf_company in jc or jc in conf_company for jc in job_companies if jc)
        if not found:
            unmatched_emails.append(conf)
    
    print(f"✅ Matched: {confirmed_count} jobs with confirmations")
    print(f"⏳ Pending: {len(unmatched_jobs)} jobs (no confirmation yet)")
    print(f"❓ Orphan emails: {len(unmatched_emails)} confirmations (no matching job folder)")
    
    return {
        "matched": confirmed_count,
        "unmatched_jobs": unmatched_jobs,
        "unmatched_emails": unmatched_emails
    }

def generate_report(jobs, confirmations, cross_ref):
    """Generate comprehensive report"""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE ANALYSIS REPORT")
    print("=" * 80)
    
    # Overall stats
    total_jobs = len(jobs)
    total_confirmations = len(confirmations)
    matched = cross_ref["matched"]
    
    print(f"\n📈 OVERALL STATISTICS")
    print("-" * 80)
    print(f"Total Job Folders Created: {total_jobs}")
    print(f"Total Gmail Confirmations: {total_confirmations}")
    print(f"Confirmed Applications: {matched} ({matched/total_jobs*100:.1f}%)")
    print(f"Pending (No Response): {len(cross_ref['unmatched_jobs'])} ({len(cross_ref['unmatched_jobs'])/total_jobs*100:.1f}%)")
    
    # File completeness
    complete_jobs = sum(1 for j in jobs if j["has_resume"] and j["has_meta"] and j["has_url"])
    print(f"\nComplete Job Packages: {complete_jobs}/{total_jobs} ({complete_jobs/total_jobs*100:.1f}%)")
    print(f"  • With Resume: {sum(1 for j in jobs if j['has_resume'])}")
    print(f"  • With Meta JSON: {sum(1 for j in jobs if j['has_meta'])}")
    print(f"  • With URL: {sum(1 for j in jobs if j['has_url'])}")
    print(f"  • With Audit Data: {sum(1 for j in jobs if j['has_audit'])}")
    
    # By platform
    if any("platform" in j for j in jobs):
        platforms = Counter(j.get("platform", "Unknown") for j in jobs)
        print(f"\n🏢 Jobs by ATS Platform:")
        for platform, count in platforms.most_common():
            confirmed_for_platform = sum(1 for j in jobs if j.get("platform") == platform and j.get("confirmed"))
            print(f"  {platform}: {count} jobs ({confirmed_for_platform} confirmed)")
    
    # Timeline analysis
    if jobs:
        oldest = min(jobs, key=lambda x: x["created_timestamp"])
        newest = max(jobs, key=lambda x: x["created_timestamp"])
        
        print(f"\n📅 Timeline:")
        print(f"  First job created: {oldest['created_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Last job created: {newest['created_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Timespan: {(newest['created_date'] - oldest['created_date']).days} days")
    
    # Recent activity
    print(f"\n🔥 Recent Activity (Last 7 Days):")
    recent_jobs = [j for j in jobs if (datetime.now() - j["created_date"]).days <= 7]
    print(f"  Jobs created: {len(recent_jobs)}")
    recent_confirmations = [c for c in confirmations if c["date"] and (datetime.now() - c["date"]).days <= 7]
    print(f"  Confirmations received: {len(recent_confirmations)}")
    
    # Top companies
    if confirmations:
        print(f"\n🏆 Top Responding Companies:")
        company_counts = Counter(c["company"] for c in confirmations)
        for company, count in company_counts.most_common(10):
            print(f"  {company}: {count} confirmations")
    
    # Issues/Failures
    print(f"\n⚠️  POTENTIAL ISSUES:")
    
    incomplete_jobs = [j for j in jobs if not (j["has_resume"] and j["has_meta"] and j["has_url"])]
    if incomplete_jobs:
        print(f"  • {len(incomplete_jobs)} incomplete job packages")
        for job in incomplete_jobs[:5]:
            missing = []
            if not job["has_resume"]: missing.append("resume")
            if not job["has_meta"]: missing.append("meta")
            if not job["has_url"]: missing.append("URL")
            print(f"    - {job['folder_name']}: missing {', '.join(missing)}")
    
    if cross_ref["unmatched_emails"]:
        print(f"  • {len(cross_ref['unmatched_emails'])} confirmations without matching job folder")
        print(f"    (These might be from manually applied jobs)")
        for conf in cross_ref["unmatched_emails"][:5]:
            print(f"    - {conf['company']}: {conf['subject'][:60]}")
    
    # Success metrics
    print(f"\n✅ SUCCESS METRICS:")
    response_rate = (matched / total_jobs * 100) if total_jobs > 0 else 0
    print(f"  Response Rate: {response_rate:.1f}%")
    
    if complete_jobs > 0:
        print(f"  Package Completeness: {complete_jobs/total_jobs*100:.1f}%")
    
    # Save detailed report
    report_file = Path(__file__).parent / "job_analysis_report.json"
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "total_jobs": total_jobs,
        "total_confirmations": total_confirmations,
        "matched": matched,
        "response_rate": response_rate,
        "jobs": jobs[:50],  # First 50 for space
        "confirmations": confirmations[:50],
        "unmatched_jobs": cross_ref["unmatched_jobs"][:20],
        "unmatched_emails": cross_ref["unmatched_emails"][:20]
    }
    
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n💾 Detailed report saved: {report_file}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("🔬 COMPREHENSIVE JOB APPLICATION ANALYSIS")
    print("=" * 80)
    
    # Step 1: Analyze job folders
    jobs = analyze_job_folders()
    
    # Step 2: Analyze Gmail
    confirmations = analyze_gmail_confirmations()
    
    # Step 3: Cross-reference
    cross_ref = cross_reference_data(jobs, confirmations)
    
    # Step 4: Generate report
    generate_report(jobs, confirmations, cross_ref)

if __name__ == "__main__":
    main()
