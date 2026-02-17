#!/usr/bin/env python3
"""Show which companies sent interview invitations"""

import os
import sys
from pathlib import Path
from gmail_helper import get_gmail_service
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import re

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

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def extract_company(sender):
    """Extract company name from sender"""
    sender_lower = sender.lower()
    
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        common = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                  'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs']
        if domain not in common:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply']:
            name = re.sub(r'\s+at\s+', ' ', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+\-.*$', '', name)
            return name.strip()
    
    return "Unknown"

print("=" * 80)
print("🌟 INTERVIEW INVITATIONS FROM GMAIL")
print("=" * 80)

if not GMAIL_USER or not GMAIL_PASSWORD:
    print("\n❌ Gmail credentials not found")
    sys.exit(1)

mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
if not mail:
    print("\n❌ Failed to connect to Gmail")
    sys.exit(1)

mail.select("inbox")

interview_keywords = [
    'SUBJECT "interview"',
    'SUBJECT "schedule"',
    'SUBJECT "next steps"',
    'SUBJECT "phone screen"',
    'SUBJECT "technical interview"'
]

interviews = []
seen_ids = set()

print("\n🔍 Searching Gmail for interview-related emails...\n")

for keyword in interview_keywords:
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
                            
                            subject_header = decode_header(msg["Subject"])[0]
                            subject = subject_header[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                            
                            sender = msg.get("From", "")
                            date_str = msg.get("Date", "")
                            
                            try:
                                email_date = parsedate_to_datetime(date_str)
                            except:
                                email_date = None
                            
                            company = extract_company(sender)
                            
                            interviews.append({
                                "company": company,
                                "subject": subject,
                                "sender": sender,
                                "date": email_date
                            })
                except:
                    continue
    except:
        continue

mail.close()
mail.logout()

print(f"✅ Found {len(interviews)} interview-related emails\n")
print("=" * 80)
print("📋 INTERVIEW INVITATIONS DETAILS")
print("=" * 80)

if not interviews:
    print("\n❌ No interview invitations found")
else:
    interviews.sort(key=lambda x: x["date"] if x["date"] else "", reverse=True)
    
    for idx, interview in enumerate(interviews, 1):
        print(f"\n{idx}. 🌟 {interview['company']}")
        print(f"   Subject: {interview['subject']}")
        print(f"   From: {interview['sender']}")
        if interview['date']:
            print(f"   Date: {interview['date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   {'-' * 76}")

print("\n" + "=" * 80)
print(f"📊 SUMMARY: {len(interviews)} companies sent interview invitations")
print("=" * 80)
