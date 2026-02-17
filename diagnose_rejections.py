#!/usr/bin/env python3
"""
Gmail Rejection Email Diagnostic Tool
Shows actual email subjects and snippets to understand rejection patterns
"""

import os
import sys
from pathlib import Path
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta

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

def get_email_preview(msg):
    """Get preview of email body"""
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
    
    # Return first 500 chars
    return body[:500] if body else ""

def scan_for_rejections():
    """Scan Gmail and show potential rejection emails"""
    
    print("=" * 80)
    print("🔍 GMAIL REJECTION EMAIL DIAGNOSTIC")
    print("=" * 80)
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("\n❌ Gmail credentials not found")
        return
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("\n❌ Failed to connect to Gmail")
        return
    
    mail.select("inbox")
    
    cutoff = datetime.now() - timedelta(days=30)
    cutoff_str = cutoff.strftime("%d-%b-%Y")
    
    # Very broad search - anything that might be a rejection
    search_patterns = [
        f'SINCE {cutoff_str} SUBJECT "application"',
        f'SINCE {cutoff_str} SUBJECT "position"',
        f'SINCE {cutoff_str} SUBJECT "opportunity"',
        f'SINCE {cutoff_str} SUBJECT "thank"',
        f'SINCE {cutoff_str} SUBJECT "update"',
        f'SINCE {cutoff_str} SUBJECT "status"'
    ]
    
    all_emails = []
    seen_ids = set()
    
    print(f"\n📅 Searching last 30 days (since {cutoff.strftime('%Y-%m-%d')})")
    print(f"🔍 Using broad search patterns to find ALL possible emails...\n")
    
    for pattern in search_patterns:
        try:
            status, messages = mail.search(None, pattern)
            
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
                                    if email_date.tzinfo:
                                        email_date = email_date.replace(tzinfo=None)
                                except:
                                    continue
                                
                                if email_date < cutoff:
                                    continue
                                
                                # Get body preview
                                body_preview = get_email_preview(msg)
                                
                                all_emails.append({
                                    "subject": subject,
                                    "sender": sender,
                                    "date": email_date,
                                    "preview": body_preview
                                })
                    
                    except:
                        continue
        except:
            continue
    
    mail.close()
    mail.logout()
    
    print(f"✅ Found {len(all_emails)} total job-related emails from last 30 days\n")
    
    # Sort by date
    all_emails.sort(key=lambda x: x["date"], reverse=True)
    
    # Display for manual review
    print("=" * 80)
    print("📧 ALL JOB-RELATED EMAILS (Last 30 Days)")
    print("=" * 80)
    print("\nPlease review these and identify which are rejections:\n")
    
    for idx, email_info in enumerate(all_emails, 1):
        print(f"\n{'=' * 80}")
        print(f"EMAIL #{idx}")
        print(f"{'=' * 80}")
        print(f"📅 Date: {email_info['date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"📧 From: {email_info['sender']}")
        print(f"📝 Subject: {email_info['subject']}")
        print(f"\n💬 Preview:")
        print("-" * 80)
        print(email_info['preview'])
        print("-" * 80)
        
        # Ask user
        print(f"\n🤔 Is this a REJECTION email? Let me analyze...")
        
        # Show my detection
        combined = (email_info['subject'] + " " + email_info['preview']).lower()
        
        likely_rejection = any(phrase in combined for phrase in [
            'not moving forward',
            'not selected',
            'not be selected',
            'position filled',
            'position has been filled',
            'decided to pursue',
            'other candidates',
            'not the right fit',
            'not a match',
            'regret to inform',
            'will not be',
            'unable to offer',
            'thank you for your interest',
            'keep your resume on file',
            'future opportunities'
        ])
        
        likely_confirmation = any(phrase in combined for phrase in [
            'thank you for applying',
            'received your application',
            'application received',
            'successfully submitted'
        ])
        
        likely_interview = any(phrase in combined for phrase in [
            'interview',
            'schedule',
            'next steps',
            'phone screen'
        ])
        
        if likely_rejection:
            print("🔴 MY DETECTION: Likely REJECTION")
        elif likely_interview:
            print("🟢 MY DETECTION: Likely INTERVIEW")
        elif likely_confirmation:
            print("🟡 MY DETECTION: Likely CONFIRMATION")
        else:
            print("⚪ MY DETECTION: UNKNOWN/OTHER")
    
    # Save to file
    output_file = Path(__file__).parent / "gmail_diagnostic_output.txt"
    with open(output_file, 'w') as f:
        f.write("GMAIL REJECTION DIAGNOSTIC - ALL EMAILS\n")
        f.write("=" * 80 + "\n\n")
        
        for idx, email_info in enumerate(all_emails, 1):
            f.write(f"\nEMAIL #{idx}\n")
            f.write(f"Date: {email_info['date']}\n")
            f.write(f"From: {email_info['sender']}\n")
            f.write(f"Subject: {email_info['subject']}\n")
            f.write(f"Preview:\n{email_info['preview']}\n")
            f.write("\n" + "=" * 80 + "\n")
    
    print("\n\n" + "=" * 80)
    print("✅ DIAGNOSTIC COMPLETE!")
    print("=" * 80)
    print(f"\n📄 Full output saved: {output_file}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the emails above")
    print(f"   2. Tell me which detection failed")
    print(f"   3. I'll update the rejection patterns")
    print(f"   4. Re-run analysis with correct detection")
    print("=" * 80)

if __name__ == "__main__":
    scan_for_rejections()
