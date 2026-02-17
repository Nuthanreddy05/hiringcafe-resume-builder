#!/usr/bin/env python3
"""
AI Email Classifier using DeepSeek API
Faster and higher rate limits than Groq
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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek API endpoint
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek_api(prompt, max_tokens=300):
    """Call DeepSeek API"""
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  DEEPSEEK_API_KEY not found")
        return None
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You classify job application emails. Respond with ONLY the category and brief reason."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️  API error: {e}")
        return None

def classify_email_with_ai(subject, body, sender):
    """Use AI to classify email"""
    
    prompt = f"""Classify this job email:
CONFIRMATION, REJECTION, INTERVIEW, UPDATE, or SPAM

From: {sender}
Subject: {subject}
Body: {body[:800]}

Format: "CATEGORY: reason"
Example: "REJECTION: States moving forward with other candidates"
"""
    
    ai_response = call_deepseek_api(prompt)
    
    if not ai_response:
        return "UNKNOWN", "API unavailable"
    
    if ":" in ai_response:
        parts = ai_response.split(":", 1)
        category = parts[0].strip().upper()
        reason = parts[1].strip() if len(parts) > 1 else ""
    else:
        category = ai_response.strip().upper()
        reason = ""
    
    valid = ["CONFIRMATION", "REJECTION", "INTERVIEW", "UPDATE", "SPAM", "UNKNOWN"]
    if category not in valid:
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
    
    return body[:1500]

def extract_company(sender):
    """Extract company from sender"""
    import re
    
    email_match = re.search(r'@([\w\-]+)\.', sender.lower())
    if email_match:
        domain = email_match.group(1)
        skip = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs', 'outlook', 'no-reply']
        if domain not in skip:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip().strip('"')
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply']:
            name = re.sub(r'^.+\s+at\s+', '', name, flags=re.IGNORECASE)
            return name.strip()
    
    return "Unknown"

def scan_and_classify():
    """Scan Gmail and classify with DeepSeek AI"""
    
    print("=" * 80)
    print("🤖 DEEPSEEK AI EMAIL CLASSIFIER")
    print("=" * 80)
    
    if not DEEPSEEK_API_KEY:
        print("\n❌ DEEPSEEK_API_KEY not set")
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
    
    print(f"\n📅 Last 30 days (since {cutoff.strftime('%Y-%m-%d')})")
    print(f"🤖 Using DeepSeek AI...\n")
    
    search_patterns = [
        f'SINCE {cutoff_str} SUBJECT "application"',
        f'SINCE {cutoff_str} SUBJECT "position"',
        f'SINCE {cutoff_str} SUBJECT "thank"',
        f'SINCE {cutoff_str} SUBJECT "interview"',
        f'SINCE {cutoff_str} SUBJECT "schedule"'
    ]
    
    results = {
        "confirmations": [],
        "rejections": [],
        "interviews": [],
        "updates": [],
        "spam": []
    }
    
    seen = set()
    count = 0
    
    for pattern in search_patterns:
        try:
            status, messages = mail.search(None, pattern)
            
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
                                
                                if email_date < cutoff:
                                    continue
                                
                                body = get_email_body(msg)
                                company = extract_company(sender)
                                
                                count += 1
                                print(f"📧 {count}: {company[:30]} - {subject[:40]}...")
                                
                                category, reason = classify_email_with_ai(subject, body, sender)
                                
                                email_info = {
                                    "company": company,
                                    "subject": subject,
                                    "sender": sender,
                                    "date": email_date.isoformat(),
                                    "category": category,
                                    "reason": reason
                                }
                                
                                if category == "CONFIRMATION":
                                    results["confirmations"].append(email_info)
                                    print(f"   ✅ CONFIRMATION")
                                elif category == "REJECTION":
                                    results["rejections"].append(email_info)
                                    print(f"   ❌ REJECTION: {reason[:50]}")
                                elif category == "INTERVIEW":
                                    results["interviews"].append(email_info)
                                    print(f"   🌟 INTERVIEW: {reason[:50]}")
                                elif category == "UPDATE":
                                    results["updates"].append(email_info)
                                    print(f"   📝 UPDATE")
                                else:
                                    results["spam"].append(email_info)
                    
                    except Exception as e:
                        continue
        
        except Exception as e:
            continue
    
    mail.close()
    mail.logout()
    
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(f"Total: {count}")
    print(f"✅ Confirmations: {len(results['confirmations'])}")
    print(f"❌ Rejections: {len(results['rejections'])}")
    print(f"🌟 Interviews: {len(results['interviews'])}")
    print(f"📝 Updates: {len(results['updates'])}")
    
    return results

def save_results(results):
    """Save results"""
    
    json_file = Path(__file__).parent / "ai_classified_emails.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Saved: {json_file}")
    
    report_file = Path(__file__).parent / "ai_classification_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("🤖 DEEPSEEK AI CLASSIFICATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"❌ REJECTIONS ({len(results['rejections'])})\n")
        f.write("-" * 80 + "\n")
        for e in results['rejections']:
            f.write(f"\n{e['company']}\n")
            f.write(f"  Date: {e['date'][:10]}\n")
            f.write(f"  Subject: {e['subject']}\n")
            f.write(f"  Reason: {e['reason']}\n")
        
        f.write(f"\n\n🌟 INTERVIEWS ({len(results['interviews'])})\n")
        f.write("-" * 80 + "\n")
        for e in results['interviews']:
            f.write(f"\n{e['company']}\n")
            f.write(f"  Subject: {e['subject']}\n")
            f.write(f"  Date: {e['date'][:10]}\n")
            f.write(f"  Reason: {e['reason']}\n")
    
    print(f"✅ Report: {report_file}")
    return report_file

def main():
    print("\n🚀 STARTING DEEPSEEK AI CLASSIFICATION\n")
    
    results = scan_and_classify()
    
    if results:
        save_results(results)
        
        print("\n" + "=" * 80)
        print("✅ DONE! DeepSeek AI completed successfully! 🎯")
        print("=" * 80)

if __name__ == "__main__":
    main()
