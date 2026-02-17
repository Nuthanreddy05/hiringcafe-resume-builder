#!/usr/bin/env python3
"""
Last 30 Days Job Application Analysis
Focused analysis for automated applications only (Jan 5 - Feb 4, 2026)

Answers:
1. Which portals work best?
2. Why are we getting rejected?
3. Are we applying too late?
4. Is it the resume quality?
5. What's the root cause of failures?
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime

# Load env
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

from gmail_helper import get_gmail_service

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def detect_platform(url):
    """Detect ATS platform"""
    if not url:
        return "Unknown"
    url_lower = url.lower()
    if "greenhouse" in url_lower:
        return "Greenhouse"
    elif "lever.co" in url_lower:
        return "Lever"
    elif "workday" in url_lower or "myworkdayjobs" in url_lower:
        return "Workday"
    elif "ashbyhq" in url_lower:
        return "Ashby"
    elif "icims" in url_lower:
        return "iCIMS"
    else:
        return "Custom/Direct"

def extract_company(sender, subject=""):
    """Extract company from email"""
    sender_lower = sender.lower()
    
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        skip = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs', 'outlook']
        if domain not in skip:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip().strip('"')
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply']:
            name = re.sub(r'^.+\s+at\s+', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+\-.*$', '', name)
            return name.strip()
    
    return "Unknown"

def is_rejection_email(subject, body):
    """Check if email is a rejection"""
    combined = (subject + " " + (body or "")).lower()
    
    rejection_patterns = [
        r'not\s+(be\s+)?moving\s+forward',
        r'(decided|chosen)\s+to\s+(pursue|move\s+forward\s+with)\s+other',
        r'position\s+(has\s+been\s+)?filled',
        r'not\s+(be\s+)?selected',
        r'will\s+not\s+(be\s+)?(pursuing|proceeding)',
        r'unable\s+to\s+(offer|extend)',
        r'regret\s+to\s+inform',
        r'unfortunately.*not\s+(a\s+)?(match|fit)',
        r'no\s+longer\s+considering',
        r'thank\s+you.*interest.*however',
        r'other\s+candidates.*better'
    ]
    
    return any(re.search(p, combined, re.IGNORECASE) for p in rejection_patterns)

def get_email_body_snippet(msg):
    """Extract first 1000 chars of email body"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        except:
            pass
    return body[:1000]

def scan_emails_last_30_days():
    """Scan Gmail for last 30 days only"""
    
    print("=" * 80)
    print("📧 SCANNING GMAIL - LAST 30 DAYS ONLY")
    print("=" * 80)
    
    cutoff = datetime.now() - timedelta(days=30)
    cutoff_str = cutoff.strftime("%d-%b-%Y")
    
    print(f"\n📅 Date range: {cutoff.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("\n❌ Gmail credentials not found")
        return {}
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("\n❌ Failed to connect to Gmail")
        return {}
    
    mail.select("inbox")
    
    emails_data = {
        "confirmations": [],
        "rejections": [],
        "interviews": []
    }
    
    # Search patterns with date filter
    patterns = {
        "confirmations": [
            f'SINCE {cutoff_str} SUBJECT "thank you"',
            f'SINCE {cutoff_str} SUBJECT "received"',
            f'SINCE {cutoff_str} SUBJECT "application"'
        ],
        "rejections": [
            f'SINCE {cutoff_str} SUBJECT "not selected"',
            f'SINCE {cutoff_str} SUBJECT "not moving forward"',
            f'SINCE {cutoff_str} SUBJECT "position filled"'
        ],
        "interviews": [
            f'SINCE {cutoff_str} SUBJECT "interview"',
            f'SINCE {cutoff_str} SUBJECT "schedule"',
            f'SINCE {cutoff_str} SUBJECT "next steps"'
        ]
    }
    
    for category, searches in patterns.items():
        seen = set()
        
        for search in searches:
            try:
                status, messages = mail.search(None, search)
                
                if status == "OK":
                    email_ids = messages[0].split()
                    
                    for e_id in email_ids:
                        if e_id in seen:
                            continue
                        seen.add(e_id)
                        
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
                                    
                                    try:
                                        email_date = parsedate_to_datetime(date_str)
                                        if email_date.tzinfo:
                                            email_date = email_date.replace(tzinfo=None)
                                    except:
                                        continue
                                    
                                    # Skip if before cutoff
                                    if email_date < cutoff:
                                        continue
                                    
                                    body = get_email_body_snippet(msg)
                                    company = extract_company(sender, subject)
                                    
                                    # Verify rejection
                                    if category == "rejections":
                                        if not is_rejection_email(subject, body):
                                            continue  # Skip false positives
                                    
                                    emails_data[category].append({
                                        "company": company,
                                        "subject": subject,
                                        "date": email_date.isoformat(),
                                        "sender": sender,
                                        "body_snippet": body[:200]
                                    })
                        
                        except:
                            continue
            except:
                continue
    
    mail.close()
    mail.logout()
    
    print(f"\n✅ Found (last 30 days):")
    print(f"   Confirmations: {len(emails_data['confirmations'])}")
    print(f"   Rejections: {len(emails_data['rejections'])}")
    print(f"   Interviews: {len(emails_data['interviews'])}")
    
    return emails_data

def load_job_folders():
    """Load all job folders from last 30 days"""
    
    print("\n" + "=" * 80)
    print("📁 LOADING JOB FOLDERS")
    print("=" * 80)
    
    cutoff = datetime.now() - timedelta(days=30)
    jobs = []
    
    if not JOBS_DIR.exists():
        print(f"\n❌ Directory not found: {JOBS_DIR}")
        return []
    
    for folder in JOBS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        
        created = datetime.fromtimestamp(folder.stat().st_mtime)
        if created < cutoff:
            continue
        
        meta_file = folder / "meta.json"
        if not meta_file.exists():
            continue
        
        try:
            with open(meta_file) as f:
                meta = json.load(f)
            
            jobs.append({
                "folder": folder.name,
                "company": meta.get("company", "Unknown"),
                "title": meta.get("title", "Unknown"),
                "platform": detect_platform(meta.get("apply_url", "")),
                "score": meta.get("best_score", 0),
                "discovered_at": meta.get("discovered_at"),
                "scraped_at": meta.get("scraped_at"),
                "created": created,
                "apply_url": meta.get("apply_url", "")
            })
        except:
            continue
    
    print(f"\n✅ Loaded {len(jobs)} job folders from last 30 days")
    return jobs

def match_emails_to_jobs(emails_data, jobs):
    """Match email events to job applications"""
    
    print("\n" + "=" * 80)
    print("🎯 MATCHING EMAILS TO JOBS")
    print("=" * 80)
    
    for job in jobs:
        company = job["company"].lower()
        company_clean = re.sub(r'[^a-z0-9]', '', company)
        
        job["status"] = "Pending"
        job["confirmed_at"] = None
        job["rejected_at"] = None
        job["interviewed_at"] = None
        
        # Check confirmations
        for email in emails_data["confirmations"]:
            email_company = re.sub(r'[^a-z0-9]', '', email["company"].lower())
            if (company_clean in email_company or email_company in company_clean) and len(company_clean) > 2:
                job["confirmed_at"] = email["date"]
                job["status"] = "Confirmed"
                break
        
        # Check rejections
        for email in emails_data["rejections"]:
            email_company = re.sub(r'[^a-z0-9]', '', email["company"].lower())
            if (company_clean in email_company or email_company in company_clean) and len(company_clean) > 2:
                job["rejected_at"] = email["date"]
                job["status"] = "Rejected"
                job["rejection_snippet"] = email["body_snippet"]
                break
        
        # Check interviews
        for email in emails_data["interviews"]:
            email_company = re.sub(r'[^a-z0-9]', '', email["company"].lower())
            if (company_clean in email_company or email_company in company_clean) and len(company_clean) > 2:
                job["interviewed_at"] = email["date"]
                job["status"] = "Interviewed"
                break
    
    status_counts = Counter(j["status"] for j in jobs)
    print(f"\n✅ Status breakdown:")
    for status, count in status_counts.most_common():
        print(f"   {status}: {count}")
    
    return jobs

def analyze_results(jobs):
    """Comprehensive analysis of results"""
    
    print("\n" + "=" * 80)
    print("📊 ANALYSIS: WHAT'S WORKING & WHAT'S NOT")
    print("=" * 80)
    
    report = []
    
    # 1. Portal Performance
    report.append("\n🎯 PLATFORM PERFORMANCE\n" + "-" * 80)
    
    by_platform = defaultdict(list)
    for job in jobs:
        by_platform[job["platform"]].append(job)
    
    for platform, platform_jobs in sorted(by_platform.items(), key=lambda x: len(x[1]), reverse=True):
        total = len(platform_jobs)
        confirmed = sum(1 for j in platform_jobs if j["status"] == "Confirmed")
        rejected = sum(1 for j in platform_jobs if j["status"] == "Rejected")
        interviewed = sum(1 for j in platform_jobs if j["status"] == "Interviewed")
        pending = sum(1 for j in platform_jobs if j["status"] == "Pending")
        
        conf_rate = (confirmed / total * 100) if total else 0
        rej_rate = (rejected / total * 100) if total else 0
        int_rate = (interviewed / total * 100) if total else 0
        
        report.append(f"\n{platform}: {total} applications")
        report.append(f"  ✅ Confirmed: {confirmed} ({conf_rate:.1f}%)")
        report.append(f"  ❌ Rejected: {rejected} ({rej_rate:.1f}%)")
        report.append(f"  🌟 Interviewed: {interviewed} ({int_rate:.1f}%)")
        report.append(f"  ⏳ Pending: {pending}")
    
    # 2. Rejection Analysis
    rejected_jobs = [j for j in jobs if j["status"] == "Rejected"]
    
    if rejected_jobs:
        report.append("\n\n❌ REJECTION ANALYSIS\n" + "-" * 80)
        report.append(f"\nTotal Rejections: {len(rejected_jobs)}")
        
        # Time to rejection
        times_to_rejection = []
        for job in rejected_jobs:
            if job.get("confirmed_at") and job.get("rejected_at"):
                confirmed = datetime.fromisoformat(job["confirmed_at"])
                rejected = datetime.fromisoformat(job["rejected_at"])
                hours = (rejected - confirmed).total_seconds() / 3600
                times_to_rejection.append(hours)
        
        if times_to_rejection:
            avg_hours = sum(times_to_rejection) / len(times_to_rejection)
            report.append(f"Average time to rejection: {avg_hours/24:.1f} days ({avg_hours:.0f} hours)")
            
            fast = sum(1 for h in times_to_rejection if h < 24)
            medium = sum(1 for h in times_to_rejection if 24 <= h < 168)
            slow = sum(1 for h in times_to_rejection if h >= 168)
            
            report.append(f"\nRejection Speed:")
            report.append(f"  < 24h (ATS auto-filter): {fast}")
            report.append(f"  1-7 days (human review): {medium}")
            report.append(f"  > 7 days (final round): {slow}")
    
    # 3. Application Speed Analysis
    report.append("\n\n⚡ APPLICATION SPEED IMPACT\n" + "-" * 80)
    
    speed_analysis = []
    for job in jobs:
        if job.get("discovered_at") and job.get("scraped_at"):
            discovered = datetime.fromisoformat(job["discovered_at"])
            scraped = datetime.fromisoformat(job["scraped_at"])
            hours_to_apply = (scraped - discovered).total_seconds() / 3600
            
            speed_analysis.append({
                "job": job,
                "hours": hours_to_apply
            })
    
    if speed_analysis:
        fast_apps = [s for s in speed_analysis if s["hours"] < 12]
        slow_apps = [s for s in speed_analysis if s["hours"] >= 12]
        
        if fast_apps:
            fast_int = sum(1 for s in fast_apps if s["job"]["status"] == "Interviewed")
            fast_rate = (fast_int / len(fast_apps) * 100) if fast_apps else 0
            report.append(f"\nApplied < 12h: {len(fast_apps)} apps, {fast_int} interviews ({fast_rate:.1f}%)")
        
        if slow_apps:
            slow_int = sum(1 for s in slow_apps if s["job"]["status"] == "Interviewed")
            slow_rate = (slow_int / len(slow_apps) * 100) if slow_apps else 0
            report.append(f"Applied ≥ 12h: {len(slow_apps)} apps, {slow_int} interviews ({slow_rate:.1f}%)")
    
    # 4. Resume Quality Correlation
    report.append("\n\n📝 RESUME QUALITY vs SUCCESS\n" + "-" * 80)
    
    high_score = [j for j in jobs if j["score"] >= 90]
    mid_score = [j for j in jobs if 70 <= j["score"] < 90]
    low_score = [j for j in jobs if j["score"] < 70]
    
    for group, label in [(high_score, "Score 90+"), (mid_score, "Score 70-89"), (low_score, "Score < 70")]:
        if group:
            interviewed = sum(1 for j in group if j["status"] == "Interviewed")
            int_rate = (interviewed / len(group) * 100) if group else 0
            report.append(f"\n{label}: {len(group)} apps, {interviewed} interviews ({int_rate:.1f}%)")
    
    return "\n".join(report)

def save_report(analysis, jobs):
    """Save analysis report"""
    
    output_file = Path(__file__).parent / "30_day_analysis_report.txt"
    
    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("📊 30-DAY JOB APPLICATION ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n")
        f.write(analysis)
        
        # Add raw data
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("📋 DETAILED DATA\n")
        f.write("-" * 80 + "\n")
        
        for job in sorted(jobs, key=lambda x: x.get("rejected_at") or x.get("confirmed_at") or "9999", reverse=True):
            f.write(f"\n{job['company']} - {job['title'][:50]}\n")
            f.write(f"  Platform: {job['platform']}\n")
            f.write(f"  Status: {job['status']}\n")
            f.write(f"  Score: {job['score']}\n")
            if job.get("confirmed_at"):
                f.write(f"  Confirmed: {job['confirmed_at'][:10]}\n")
            if job.get("rejected_at"):
                f.write(f"  Rejected: {job['rejected_at'][:10]}\n")
    
    print(f"\n✅ Report saved: {output_file}")
    return output_file

def main():
    print("\n🚀 STARTING 30-DAY ANALYSIS\n")
    
    # 1. Scan emails
    emails_data = scan_emails_last_30_days()
    
    # 2. Load job folders
    jobs = load_job_folders()
    
    # 3. Match
    jobs = match_emails_to_jobs(emails_data, jobs)
    
    # 4. Analyze
    analysis = analyze_results(jobs)
    
    # 5. Save
    report_file = save_report(analysis, jobs)
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)
    print(analysis)
    print("\n" + "=" * 80)
    print(f"\n📄 Full report: {report_file}")
    print(f"\n💡 Review: cat {report_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
