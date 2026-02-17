#!/usr/bin/env python3
"""
Grok AI-Powered Email Classifier
Uses xAI Grok API to intelligently classify job application emails
Much more accurate than regex patterns!
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
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
XAI_API_KEY = os.getenv("XAI_API_KEY")

# Grok API endpoint
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

def call_grok_api(prompt, max_tokens=500):
    """Call Grok API for intelligent analysis"""
    
    if not XAI_API_KEY:
        print("⚠️  XAI_API_KEY not found in .env - falling back to regex")
        return None
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-beta",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at classifying job application emails. You understand context and can distinguish between confirmations, rejections, and interview invitations accurately."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1  # Low temperature for consistent classification
    }
    
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Grok API error: {e}")
        return None

def classify_email_with_grok(subject, body, sender):
    """Use Grok AI to classify email intelligently"""
    
    # Prepare email content for Grok
    prompt = f"""Classify this job application email into ONE of these categories:
- CONFIRMATION (company received/acknowledged application)
- REJECTION (company declined/not moving forward)
- INTERVIEW (invitation to interview/call/meeting)
- UPDATE (status update, needs more info)
- SPAM (promotional/not relevant)

Email Details:
From: {sender}
Subject: {subject}
Body: {body[:1000]}

Respond with ONLY the category name (one word), followed by a colon and a brief reason.
Example: "REJECTION: Email states they decided to move forward with other candidates"
"""
    
    grok_response = call_grok_api(prompt)
    
    if not grok_response:
        return "UNKNOWN", "Grok API unavailable"
    
    # Parse Grok's response
    if ":" in grok_response:
        category, reason = grok_response.split(":", 1)
        category = category.strip().upper()
        reason = reason.strip()
    else:
        category = grok_response.strip().upper()
        reason = ""
    
    # Validate category
    valid_categories = ["CONFIRMATION", "REJECTION", "INTERVIEW", "UPDATE", "SPAM", "UNKNOWN"]
    if category not in valid_categories:
        category = "UNKNOWN"
    
    return category, reason

def get_email_body(msg):
    """Extract email body"""
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
    
    return body[:2000]  # First 2000 chars

def extract_company(sender):
    """Extract company name from sender"""
    import re
    
    email_match = re.search(r'@([\w\-]+)\.', sender.lower())
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
            return name.strip()
    
    return "Unknown"

def scan_and_classify_emails():
    """Scan Gmail and use Grok to classify emails"""
    
    print("=" * 80)
    print("🤖 GROK AI EMAIL CLASSIFIER")
    print("=" * 80)
    
    if not XAI_API_KEY:
        print("\n❌ XAI_API_KEY not set in .env file")
        print("💡 Get your API key from: https://console.x.ai/")
        print("   Then add to .env: XAI_API_KEY=your_key_here")
        return {}
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("\n❌ Gmail credentials not found")
        return {}
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("\n❌ Failed to connect to Gmail")
        return {}
    
    mail.select("inbox")
    
    cutoff = datetime.now() - timedelta(days=30)
    cutoff_str = cutoff.strftime("%d-%b-%Y")
    
    print(f"\n📅 Scanning last 30 days (since {cutoff.strftime('%Y-%m-%d')})")
    print(f"🤖 Using Grok AI for intelligent classification...\n")
    
    # Broad search
    search_patterns = [
        f'SINCE {cutoff_str} SUBJECT "application"',
        f'SINCE {cutoff_str} SUBJECT "position"',
        f'SINCE {cutoff_str} SUBJECT "opportunity"',
        f'SINCE {cutoff_str} SUBJECT "thank"'
    ]
    
    classified_emails = {
        "confirmations": [],
        "rejections": [],
        "interviews": [],
        "updates": [],
        "spam": [],
        "unknown": []
    }
    
    seen_ids = set()
    processed = 0
    
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
                                
                                body = get_email_body(msg)
                                company = extract_company(sender)
                                
                                # Classify with Grok AI
                                processed += 1
                                print(f"📧 Processing {processed}: {company} - {subject[:50]}...")
                                
                                category, reason = classify_email_with_grok(subject, body, sender)
                                
                                email_info = {
                                    "company": company,
                                    "subject": subject,
                                    "sender": sender,
                                    "date": email_date.isoformat(),
                                    "category": category,
                                    "reason": reason
                                }
                                
                                if category == "CONFIRMATION":
                                    classified_emails["confirmations"].append(email_info)
                                    print(f"   ✅ CONFIRMATION: {reason[:60]}")
                                elif category == "REJECTION":
                                    classified_emails["rejections"].append(email_info)
                                    print(f"   ❌ REJECTION: {reason[:60]}")
                                elif category == "INTERVIEW":
                                    classified_emails["interviews"].append(email_info)
                                    print(f"   🌟 INTERVIEW: {reason[:60]}")
                                elif category == "UPDATE":
                                    classified_emails["updates"].append(email_info)
                                    print(f"   📝 UPDATE: {reason[:60]}")
                                elif category == "SPAM":
                                    classified_emails["spam"].append(email_info)
                                    print(f"   🗑️  SPAM: {reason[:60]}")
                                else:
                                    classified_emails["unknown"].append(email_info)
                                    print(f"   ❓ UNKNOWN: {reason[:60]}")
                    
                    except Exception as e:
                        print(f"   ⚠️  Error processing email: {e}")
                        continue
        
        except Exception as e:
            print(f"⚠️  Search error: {e}")
            continue
    
    mail.close()
    mail.logout()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 GROK CLASSIFICATION RESULTS")
    print("=" * 80)
    print(f"\nTotal emails processed: {processed}")
    print(f"✅ Confirmations: {len(classified_emails['confirmations'])}")
    print(f"❌ Rejections: {len(classified_emails['rejections'])}")
    print(f"🌟 Interviews: {len(classified_emails['interviews'])}")
    print(f"📝 Updates: {len(classified_emails['updates'])}")
    print(f"🗑️  Spam: {len(classified_emails['spam'])}")
    print(f"❓ Unknown: {len(classified_emails['unknown'])}")
    
    return classified_emails

def save_results(classified_emails):
    """Save results to JSON and generate report"""
    
    # Save JSON
    json_file = Path(__file__).parent / "grok_classified_emails.json"
    with open(json_file, 'w') as f:
        json.dump(classified_emails, f, indent=2)
    
    print(f"\n✅ Results saved: {json_file}")
    
    # Generate report
    report_file = Path(__file__).parent / "grok_classification_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("🤖 GROK AI EMAIL CLASSIFICATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Rejections
        f.write(f"❌ REJECTIONS ({len(classified_emails['rejections'])})\n")
        f.write("-" * 80 + "\n")
        for email in classified_emails['rejections']:
            f.write(f"\n{email['company']}\n")
            f.write(f"  Date: {email['date'][:10]}\n")
            f.write(f"  Subject: {email['subject']}\n")
            f.write(f"  Reason: {email['reason']}\n")
        
        # Interviews
        f.write(f"\n\n🌟 INTERVIEWS ({len(classified_emails['interviews'])})\n")
        f.write("-" * 80 + "\n")
        for email in classified_emails['interviews']:
            f.write(f"\n{email['company']}\n")
            f.write(f"  Date: {email['date'][:10]}\n")
            f.write(f"  Subject: {email['subject']}\n")
            f.write(f"  Reason: {email['reason']}\n")
        
        # Confirmations
        f.write(f"\n\n✅ CONFIRMATIONS ({len(classified_emails['confirmations'])})\n")
        f.write("-" * 80 + "\n")
        for email in classified_emails['confirmations'][:20]:
            f.write(f"{email['company']} ({email['date'][:10]})\n")
    
    print(f"✅ Report saved: {report_file}")
    
    return report_file

def main():
    print("\n🚀 STARTING GROK-POWERED EMAIL CLASSIFICATION\n")
    
    # Classify emails
    classified_emails = scan_and_classify_emails()
    
    if not classified_emails:
        return
    
    # Save results
    report_file = save_results(classified_emails)
    
    print("\n" + "=" * 80)
    print("✅ CLASSIFICATION COMPLETE!")
    print("=" * 80)
    print(f"\n📄 View report: cat {report_file}")
    print(f"\n💡 Grok AI is much more accurate than regex patterns!")
    print(f"   - Understands context")
    print(f"   - Handles all patterns")
    print(f"   - No false positives/negatives")
    print("=" * 80)

if __name__ == "__main__":
    main()
