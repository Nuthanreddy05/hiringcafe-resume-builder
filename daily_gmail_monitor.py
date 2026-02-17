#!/usr/bin/env python3
"""
Daily Gmail Monitor - Check for new job application responses
Run this daily via cron or manually
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
from gmail_helper import get_gmail_service
import email
from email.header import decode_header
import re

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
TRACKER_FILE = Path(__file__).parent / "application_tracker.json"

def load_tracker():
    """Load existing tracker data"""
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {"applications": {}, "last_check": None}

def save_tracker(data):
    """Save tracker data"""
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def check_new_emails():
    """Check for new application emails"""
    print(f"\n📧 Checking Gmail: {GMAIL_USER}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("❌ Failed to connect to Gmail")
        return []
    
    # Load tracker
    tracker = load_tracker()
    seen_subjects = set(app["subject"] for app in tracker["applications"].values())
    
    try:
        mail.select("inbox")
        
        # Search for emails from last 2 days
        since_date = (datetime.now()).strftime("%d-%b-%Y")
        search_query = f'(SINCE {since_date} (OR SUBJECT "application" SUBJECT "thank you" SUBJECT "received"))'
        
        status, messages = mail.search(None, search_query)
        
        if status != "OK":
            print("❌ Search failed")
            return []
        
        email_ids = messages[0].split()
        print(f"   Found {len(email_ids)} emails to check")
        
        new_applications = []
        
        for e_id in reversed(email_ids[-20:]):  # Check last 20
            try:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get subject
                        subject_header = decode_header(msg["Subject"])[0]
                        subject = subject_header[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                        
                        # Skip if already seen
                        if subject in seen_subjects:
                            continue
                        
                        # Get details
                        sender = msg.get("From", "")
                        date_str = msg.get("Date", "")
                        
                        # Extract company
                        company = extract_company(sender, subject)
                        
                        # Get body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors='ignore')
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode(errors='ignore')
                        
                        app_data = {
                            "company": company,
                            "subject": subject,
                            "sender": sender,
                            "date": date_str,
                            "body_preview": body[:200],
                            "checked_at": datetime.now().isoformat()
                        }
                        
                        new_applications.append(app_data)
                        
            except Exception as e:
                print(f"   ⚠️  Error processing email: {e}")
                continue
        
        return new_applications
        
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass

def extract_company(sender, subject):
    """Extract company name from sender or subject"""
    sender_lower = sender.lower()
    
    # Try email domain
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        if domain not in ['gmail', 'noreply', 'no-reply', 'donotreply', 'mail', 'greenhouse', 'smartrecruiters', 'icims']:
            return domain.replace('-', ' ').title()
    
    # Try sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'no reply', 'noreply']:
            return name
    
    return "Unknown"

def main():
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("❌ Gmail credentials not found in .env file")
        return
    
    print("=" * 60)
    print("📋 DAILY APPLICATION MONITOR")
    print("=" * 60)
    
    # Check for new emails
    new_apps = check_new_emails()
    
    if not new_apps:
        print("\n✅ No new application emails found")
        return
    
    print(f"\n🎉 Found {len(new_apps)} NEW application emails!")
    print("\n" + "=" * 60)
    
    # Load and update tracker
    tracker = load_tracker()
    
    for idx, app in enumerate(new_apps, 1):
        app_id = f"{app['company']}_{datetime.now().timestamp()}"
        tracker["applications"][app_id] = app
        
        print(f"\n{idx}. {app['company']}")
        print(f"   📧 {app['subject']}")
        print(f"   📅 {app['date']}")
        print(f"   👤 {app['sender']}")
    
    tracker["last_check"] = datetime.now().isoformat()
    save_tracker(tracker)
    
    print("\n" + "=" * 60)
    print(f"💾 Tracker updated: {TRACKER_FILE}")
    print(f"📊 Total applications tracked: {len(tracker['applications'])}")

if __name__ == "__main__":
    main()
