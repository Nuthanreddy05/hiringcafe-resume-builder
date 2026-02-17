#!/usr/bin/env python3
"""
Gmail Email Classifier - Complete Job Application Lifecycle Tracker
Scans Gmail and classifies ALL job-related emails into:
- Confirmations (application received)
- Rejections (not moving forward)
- Interviews (screening, phone, onsite)
-Pending (no status update)
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
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

def extract_company(sender, subject):
    """Extract company name from email"""
    sender_lower = sender.lower()
    
    # Try domain
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        skip = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs', 'outlook', 'no-reply']
        if domain not in skip:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    # Try sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip().strip('"')
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply', 'donotreply']:
            # Clean patterns
            name = re.sub(r'^.+\s+at\s+', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+\-.*$', '', name)
            name = re.sub(r'\s+\|.*$', '', name)
            return name.strip()
    
    return "Unknown"

def classify_email(subject, body, sender):
    """Classify email as confirmation, rejection, or interview"""
    
    subject_lower = subject.lower()
    body_lower = body.lower() if body else ""
    combined = subject_lower + " " + body_lower
    
    # REJECTION patterns (highest priority - check first!)
    rejection_patterns = [
        r'not\s+(be\s+)?moving\s+forward',
        r'(decided|chosen)\s+to\s+(pursue|move\s+forward\s+with)\s+other',
        r'position\s+(has\s+been\s+)?filled',
        r'not\s+(be\s+)?selected',
        r'will\s+not\s+(be\s+)?(pursuing|proceeding)',
        r'unable\s+to\s+(offer|extend)',
        r'regret\s+to\s+inform',
        r'unfortunately.*not\s+(a\s+)?(match|fit)',
        r'declined.*application',
        r'no\s+longer\s+considering',
        r'thank\s+you.*interest.*however',
        r'we.*moving\s+in\s+a\s+different\s+direction',
        r'will\s+keep.*on\s+file',
        r'other\s+candidates.*better\s+(match|fit)',
        r'appreciate.*interest.*not\s+(the\s+)?right\s+fit'
    ]
    
    for pattern in rejection_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            # Extract rejection reason
            reason = extract_rejection_reason(body if body else subject)
            return "rejection", reason
    
    # INTERVIEW patterns
    interview_patterns = [
        r'(schedule|scheduling)\s+(a|an|your)\s+(interview|call|meeting|conversation)',
        r'would\s+like\s+to\s+(schedule|speak|chat|interview)',
        r'invite\s+(you\s+)?(to|for)\s+(a|an)\s+(interview|call|screen)',
        r'next\s+steps',
        r'phone\s+(screen|interview)',
        r'video\s+(interview|call)',
        r'technical\s+(interview|assessment|challenge)',
        r'interview\s+(with|for)',
        r'calendly',
        r'zoom\s+meeting',
        r'available\s+(for|to)\s+(a|an)\s+(call|interview)',
        r'recruiter\s+(screen|call)'
    ]
    
    for pattern in interview_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            # Determine interview type
            if 'technical' in combined:
                interview_type = "technical"
            elif 'phone' in combined or 'screen' in combined:
                interview_type = "phone_screen"
            elif 'onsite' in combined or 'in-person' in combined:
                interview_type = "onsite"
            elif 'video' in combined or 'zoom' in combined:
                interview_type = "video"
            else:
                interview_type = "general"
            
            return "interview", interview_type
    
    # CONFIRMATION patterns
    confirmation_patterns = [
        r'thank\s+you\s+for\s+(your\s+)?(application|applying)',
        r'(we\s+)?received\s+your\s+application',
        r'application\s+(has\s+been\s+)?received',
        r'confirm(ed)?\s+(receipt|your\s+application)',
        r'successfully\s+submitted',
        r'appreciate\s+your\s+(interest|application)',
        r'acknowledg(e|ing)\s+your\s+application'
    ]
    
    for pattern in confirmation_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            return "confirmation", None
    
    return "unknown", None

def extract_rejection_reason(text):
    """Extract why the application was rejected"""
    if not text:
        return "unspecified"
    
    text_lower = text.lower()
    
    # Reason patterns
    if 'more qualified' in text_lower or 'better match' in text_lower:
        return "More qualified candidates"
    elif 'requirements' in text_lower and ('not meet' in text_lower or 'do not match' in text_lower):
        return "Requirements not met"
    elif 'position filled' in text_lower or 'position has been filled' in text_lower:
        return "Position already filled"
    elif 'location' in text_lower or 'relocate' in text_lower:
        return "Location mismatch"
    elif 'sponsor' in text_lower or 'visa' in text_lower or 'work authorization' in text_lower:
        return "Visa/sponsorship issue"
    elif 'different direction' in text_lower:
        return "Different direction"
    elif 'experience' in text_lower:
        return "Experience level"
    else:
        return "General rejection"

def get_email_body(msg):
    """Extract plain text body from email"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
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
            body = ""
    
    return body[:2000]  # First 2000 chars for classification

def scan_gmail_for_job_emails():
    """Scan entire Gmail inbox for job-related emails"""
    
    print("=" * 80)
    print("📧 GMAIL EMAIL CLASSIFIER - SCANNING ALL JOB EMAILS")
    print("=" * 80)
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("\n❌ Gmail credentials not found")
        return {}
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("\n❌ Failed to connect to Gmail")
        return {}
    
    mail.select("inbox")
    
    # Search for ALL job-related emails
    search_patterns = [
        'SUBJECT "application"',
        'SUBJECT "thank you"',
        'SUBJECT "received"',
        'SUBJECT "interview"',
        'SUBJECT "schedule"',
        'SUBJECT "position"',
        'SUBJECT "opportunity"',
        'SUBJECT "rejected"',
        'SUBJECT "not selected"',
        'SUBJECT "not moving forward"'
    ]
    
    all_emails = {
        "confirmations": [],
        "rejections": [],
        "interviews": [],
        "unknown": []
    }
    
    seen_ids = set()
    total_scanned = 0
    
    print(f"\n🔍 Scanning with {len(search_patterns)} search patterns...\n")
    
    for pattern in search_patterns:
        try:
            status, messages = mail.search(None, pattern)
            
            if status == "OK":
                email_ids = messages[0].split()
                
                for e_id in email_ids:
                    if e_id in seen_ids:
                        continue
                    seen_ids.add(e_id)
                    total_scanned += 1
                    
                    if total_scanned % 50 == 0:
                        print(f"   Processed {total_scanned} emails...")
                    
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
                                
                                # Get email body
                                body = get_email_body(msg)
                                
                                # Classify
                                category, extra_info = classify_email(subject, body, sender)
                                
                                company = extract_company(sender, subject)
                                
                                email_info = {
                                    "company": company,
                                    "subject": subject,
                                    "sender": sender,
                                    "date": email_date.isoformat() if email_date else None,
                                    "category": category
                                }
                                
                                if category == "rejection":
                                    email_info["rejection_reason"] = extra_info
                                    all_emails["rejections"].append(email_info)
                                elif category == "interview":
                                    email_info["interview_type"] = extra_info
                                    all_emails["interviews"].append(email_info)
                                elif category == "confirmation":
                                    all_emails["confirmations"].append(email_info)
                                else:
                                    all_emails["unknown"].append(email_info)
                    
                    except Exception as e:
                        continue
        
        except Exception as e:
            continue
    
    mail.close()
    mail.logout()
    
    # Sort by date
    for category in all_emails:
        all_emails[category].sort(key=lambda x: x["date"] if x["date"] else "", reverse=True)
    
    # Print summary
    print(f"\n✅ Scanned {total_scanned} emails")
    print(f"\n📊 CLASSIFICATION RESULTS:")
    print(f"   Confirmations: {len(all_emails['confirmations'])}")
    print(f"   Rejections: {len(all_emails['rejections'])}")
    print(f"   Interviews: {len(all_emails['interviews'])}")
    print(f"   Unknown: {len(all_emails['unknown'])}")
    
    return all_emails

def save_results(all_emails):
    """Save classified emails to JSON"""
    output_file = Path(__file__).parent / "emails_classified.json"
    
    with open(output_file, 'w') as f:
        json.dump(all_emails, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    return output_file

def generate_summary_report(all_emails):
    """Generate human-readable summary"""
    report_file = Path(__file__).parent / "email_classification_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("📧 EMAIL CLASSIFICATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Confirmations
        f.write(f"✅ APPLICATION CONFIRMATIONS ({len(all_emails['confirmations'])})\n")
        f.write("-" * 80 + "\n")
        for email in all_emails['confirmations'][:20]:
            f.write(f"\n{email['company']}\n")
            f.write(f"  Subject: {email['subject']}\n")
            f.write(f"  Date: {email['date']}\n")
        
        # Rejections
        f.write(f"\n\n❌ REJECTIONS ({len(all_emails['rejections'])})\n")
        f.write("-" * 80 + "\n")
        
        # Group by reason
        by_reason = defaultdict(list)
        for email in all_emails['rejections']:
            reason = email.get('rejection_reason', 'unspecified')
            by_reason[reason].append(email)
        
        for reason, emails in by_reason.items():
            f.write(f"\n{reason}: {len(emails)} rejections\n")
            for email in emails[:5]:
                f.write(f"  - {email['company']} ({email['date'][:10] if email['date'] else 'unknown'})\n")
        
        # Interviews
        f.write(f"\n\n🌟 INTERVIEWS ({len(all_emails['interviews'])})\n")
        f.write("-" * 80 + "\n")
        for email in all_emails['interviews']:
            f.write(f"\n{email['company']} - {email.get('interview_type', 'general')}\n")
            f.write(f"  Subject: {email['subject']}\n")
            f.write(f"  Date: {email['date']}\n")
        
        # Summary stats
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("📊 SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Confirmations: {len(all_emails['confirmations'])}\n")
        f.write(f"Total Rejections: {len(all_emails['rejections'])}\n")
        f.write(f"Total Interviews: {len(all_emails['interviews'])}\n")
        
        if all_emails['rejections']:
            total_rej = len(all_emails['rejections'])
            f.write(f"\nTop Rejection Reasons:\n")
            for reason, emails in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                pct = len(emails) / total_rej * 100
                f.write(f"  {reason}: {len(emails)} ({pct:.1f}%)\n")
    
    print(f"✅ Summary report saved to: {report_file}")
    return report_file

def main():
    print("\n🚀 STARTING EMAIL CLASSIFICATION\n")
    
    # Scan Gmail
    all_emails = scan_gmail_for_job_emails()
    
    if not all_emails:
        print("\n❌ No emails found or error occurred")
        return
    
    # Save results
    json_file = save_results(all_emails)
    
    # Generate report
    report_file = generate_summary_report(all_emails)
    
    print("\n" + "=" * 80)
    print("✅ CLASSIFICATION COMPLETE!")
    print("=" * 80)
    print(f"\n📄 Structured data: {json_file}")
    print(f"📄 Summary report: {report_file}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review: cat {report_file}")
    print(f"   2. Use data to enrich job folders")
    print(f"   3. Update dashboard with lifecycle tracking")
    print("=" * 80)

if __name__ == "__main__":
    main()
