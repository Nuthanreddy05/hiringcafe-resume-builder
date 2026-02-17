#!/usr/bin/env python3
"""
Job Data Enrichment & Interview Matcher
- Finds ALL interview/screening emails from Gmail
- Fixes incorrect company names in meta.json
- Matches interviews to correct job folders
- Updates dashboard with accurate data
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
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

def extract_company_from_url(url):
    """Extract real company name from career page URL"""
    if not url:
        return None
    
    # Parse URL
    parsed = urlparse(url.lower())
    domain = parsed.netloc
    path = parsed.path
    
    # Remove common prefixes
    domain = domain.replace('www.', '').replace('jobs.', '').replace('careers.', '')
    
    # Company-specific patterns
    company_patterns = {
        # ATS platforms - extract from subdomain or path
        'greenhouse.io': lambda d, p: d.split('.')[0] if '.' in d else None,
        'lever.co': lambda d, p: d.split('.')[0] if '.' in d else None,
        'ashbyhq.com': lambda d, p: d.split('.')[0] if '.' in d else None,
        'myworkdayjobs.com': lambda d, p: d.split('.')[0] if '.' in d else None,
        'icims.com': lambda d, p: d.split('.')[0] if '.' in d else None,
    }
    
    # Check if it's an ATS platform
    for platform, extractor in company_patterns.items():
        if platform in domain:
            company = extractor(domain, path)
            if company and company not in ['jobs', 'careers', 'apply']:
                return company.replace('-', ' ').title()
    
    # Direct company domain
    # Extract main domain name
    parts = domain.split('.')
    if len(parts) >= 2:
        company_name = parts[-2]  # e.g., 'google' from 'careers.google.com'
        
        # Filter out common words
        skip = ['jobs', 'careers', 'apply', 'hiring', 'talent', 'recruitment', 'work']
        if company_name not in skip:
            return company_name.replace('-', ' ').title()
    
    return None

def extract_company_from_email_sender(sender):
    """Extract company from email sender"""
    sender_lower = sender.lower()
    
    # Try domain first
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        common = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                  'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs', 'outlook']
        if domain not in common:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    # Try sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply']:
            # Clean patterns like "John at Company" -> "Company"
            name = re.sub(r'^.+\s+at\s+', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+\-.*$', '', name)
            return name.strip()
    
    return None

def find_all_interview_emails():
    """Find ALL emails related to interviews, scheduling, screening"""
    print("=" * 80)
    print("📧 SCANNING GMAIL FOR ALL INTERVIEW/SCREENING EMAILS")
    print("=" * 80)
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("\n❌ Gmail credentials not found")
        return []
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("\n❌ Failed to connect to Gmail")
        return []
    
    mail.select("inbox")
    
    # Comprehensive search keywords for interviews
    keywords = [
        'SUBJECT "interview"',
        'SUBJECT "screening"',
        'SUBJECT "schedule"',
        'SUBJECT "next steps"',
        'SUBJECT "phone screen"',
        'SUBJECT "video call"',
        'SUBJECT "zoom"',
        'SUBJECT "calendly"',
        'SUBJECT "meeting"',
        'SUBJECT "technical assessment"',
        'SUBJECT "coding challenge"',
        'SUBJECT "talk soon"',
        'SUBJECT "availability"'
    ]
    
    interviews = []
    seen_ids = set()
    
    print(f"\n🔍 Searching with {len(keywords)} keyword patterns...\n")
    
    for keyword in keywords:
        try:
            status, messages = mail.search(None, keyword)
            
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
                                
                                # Decode subject
                                subject_header = decode_header(msg["Subject"])[0]
                                subject = subject_header[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                                
                                sender = msg.get("From", "")
                                date_str = msg.get("Date", "")
                                
                                try:
                                    email_date = parsedate_to_datetime(date_str)
                                    if email_date.tzinfo is not None:
                                        email_date = email_date.replace(tzinfo=None)
                                except:
                                    email_date = None
                                
                                company = extract_company_from_email_sender(sender)
                                
                                interviews.append({
                                    "company": company if company else "Unknown",
                                    "subject": subject,
                                    "sender": sender,
                                    "date": email_date,
                                    "keyword": keyword
                                })
                    except Exception as e:
                        continue
        except Exception as e:
            continue
    
    mail.close()
    mail.logout()
    
    # Sort by date
    interviews.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    
    print(f"✅ Found {len(interviews)} interview/screening related emails\n")
    
    return interviews

def analyze_and_fix_job_folders():
    """Analyze all job folders and fix incorrect company names"""
    print("=" * 80)
    print("🔍 ANALYZING JOB FOLDERS & FIXING COMPANY NAMES")
    print("=" * 80)
    
    if not JOBS_DIR.exists():
        print(f"\n❌ Directory not found: {JOBS_DIR}")
        return []
    
    fixed_count = 0
    analysis = []
    
    for job_folder in JOBS_DIR.iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith(("_", ".")):
            continue
        
        meta_file = job_folder / "meta.json"
        if not meta_file.exists():
            continue
        
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            current_company = meta.get("company", "Unknown")
            apply_url = meta.get("apply_url", "")
            
            # Check if company name looks wrong
            wrong_patterns = [
                "join our community",
                "unknown",
                "join",
                "community",
                "career",
                "careers",
                "jobs",
                "apply"
            ]
            
            is_wrong = current_company.lower() in wrong_patterns
            
            # Try to extract real company from URL
            real_company = extract_company_from_url(apply_url)
            
            info = {
                "folder": job_folder.name,
                "current_company": current_company,
                "extracted_company": real_company,
                "needs_fix": is_wrong,
                "url": apply_url,
                "title": meta.get("title", "Unknown"),
                "date": datetime.fromtimestamp(job_folder.stat().st_mtime),
                "meta_file": meta_file
            }
            
            # Fix if needed and real company found
            if is_wrong and real_company:
                meta["company"] = real_company
                with open(meta_file, 'w') as f:
                    json.dump(meta, f, indent=2)
                
                info["fixed"] = True
                info["new_company"] = real_company
                fixed_count += 1
                print(f"✅ Fixed: '{current_company}' → '{real_company}' ({job_folder.name})")
            else:
                info["fixed"] = False
            
            analysis.append(info)
            
        except Exception as e:
            print(f"⚠️  Error processing {job_folder.name}: {e}")
            continue
    
    print(f"\n📊 Analysis Complete:")
    print(f"   Total folders: {len(analysis)}")
    print(f"   Fixed: {fixed_count}")
    
    return analysis

def match_interviews_to_jobs(interviews, job_analysis):
    """Match interview emails to job folders"""
    print("\n" + "=" * 80)
    print("🎯 MATCHING INTERVIEWS TO JOB APPLICATIONS")
    print("=" * 80)
    
    matches = []
    
    for interview in interviews:
        interview_company = interview["company"].lower()
        interview_company_clean = re.sub(r'[^a-z0-9]', '', interview_company)
        
        # Try to match to a job folder
        best_match = None
        
        for job in job_analysis:
            job_company = job.get("new_company", job["current_company"]).lower()
            job_company_clean = re.sub(r'[^a-z0-9]', '', job_company)
            
            # Fuzzy match
            if (interview_company_clean in job_company_clean or 
                job_company_clean in interview_company_clean) and len(interview_company_clean) > 2:
                best_match = job
                break
        
        match_info = {
            "company": interview["company"],
            "subject": interview["subject"],
            "date": interview["date"],
            "matched_folder": best_match["folder"] if best_match else None,
            "job_title": best_match["title"] if best_match else None
        }
        
        matches.append(match_info)
        
        if best_match:
            print(f"✅ {interview['company']} → {best_match['folder']}")
            print(f"   Subject: {interview['subject']}")
            print(f"   Date: {interview['date'].strftime('%Y-%m-%d') if interview['date'] else 'Unknown'}")
        else:
            print(f"⚠️  {interview['company']} → NO MATCH")
            print(f"   Subject: {interview['subject']}")
    
    matched_count = sum(1 for m in matches if m["matched_folder"])
    print(f"\n📊 Matched {matched_count}/{len(matches)} interviews to job folders")
    
    return matches

def generate_report(interviews, job_analysis, matches):
    """Generate comprehensive report"""
    report_file = Path(__file__).parent / "interview_analysis_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("🎯 INTERVIEW & JOB APPLICATION ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Section 1: All Interview Emails
        f.write("📧 ALL INTERVIEW/SCREENING EMAILS FOUND:\n")
        f.write("-" * 80 + "\n")
        for idx, interview in enumerate(interviews, 1):
            f.write(f"\n{idx}. {interview['company']}\n")
            f.write(f"   Subject: {interview['subject']}\n")
            f.write(f"   From: {interview['sender']}\n")
            f.write(f"   Date: {interview['date'].strftime('%Y-%m-%d %H:%M') if interview['date'] else 'Unknown'}\n")
        
        # Section 2: Fixed Company Names
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("🔧 COMPANY NAMES FIXED:\n")
        f.write("-" * 80 + "\n")
        fixed = [j for j in job_analysis if j.get("fixed")]
        for job in fixed:
            f.write(f"\n- {job['folder']}\n")
            f.write(f"  Before: {job['current_company']}\n")
            f.write(f"  After:  {job['new_company']}\n")
        
        # Section 3: Matched Interviews
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("✅ INTERVIEWS MATCHED TO APPLICATIONS:\n")
        f.write("-" * 80 + "\n")
        matched = [m for m in matches if m["matched_folder"]]
        for match in matched:
            f.write(f"\n🌟 {match['company']}\n")
            f.write(f"   Folder: {match['matched_folder']}\n")
            f.write(f"   Position: {match['job_title']}\n")
            f.write(f"   Email Subject: {match['subject']}\n")
            f.write(f"   Date: {match['date'].strftime('%Y-%m-%d') if match['date'] else 'Unknown'}\n")
        
        # Section 4: Unmatched Interviews
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("⚠️  INTERVIEWS NOT MATCHED (might be manual applications):\n")
        f.write("-" * 80 + "\n")
        unmatched = [m for m in matches if not m["matched_folder"]]
        for match in unmatched:
            f.write(f"\n- {match['company']}\n")
            f.write(f"  Subject: {match['subject']}\n")
            f.write(f"  Date: {match['date'].strftime('%Y-%m-%d') if match['date'] else 'Unknown'}\n")
        
        # Summary
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("📊 SUMMARY:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total interview emails found: {len(interviews)}\n")
        f.write(f"Company names fixed: {len(fixed)}\n")
        f.write(f"Interviews matched to folders: {len(matched)}\n")
        f.write(f"Interviews not matched: {len(unmatched)}\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n✅ Report saved to: {report_file}")
    return report_file

def main():
    print("\n🚀 STARTING COMPREHENSIVE JOB DATA ANALYSIS\n")
    
    # Step 1: Find all interview emails
    interviews = find_all_interview_emails()
    
    # Step 2: Analyze and fix job folders
    job_analysis = analyze_and_fix_job_folders()
    
    # Step 3: Match interviews to jobs
    matches = match_interviews_to_jobs(interviews, job_analysis)
    
    # Step 4: Generate report
    report_file = generate_report(interviews, job_analysis, matches)
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"\n📄 Full report: {report_file}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review report: cat {report_file}")
    print(f"   2. Regenerate dashboard: python3 generate_dashboard.py")
    print(f"   3. Check updated company names and interview matches")
    print("=" * 80)

if __name__ == "__main__":
    main()
