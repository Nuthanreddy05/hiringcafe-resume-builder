#!/usr/bin/env python3
"""
Gmail Application Tracker
Checks Gmail for job application confirmations and analyzes results
"""

import sys
import os
from gmail_helper import get_gmail_service, check_for_confirmation_email
from datetime import datetime, timedelta
import email
from email.header import decode_header
import re

GMAIL_USER = "nuthanreddy001@gmail.com"
GMAIL_APP_PASSWORD = "uqvm xlxs ofoj iwgy"

def search_application_emails(days_back=7):
    """Search for application confirmation emails"""
    
    print(f"\n📧 Connecting to Gmail: {GMAIL_USER}")
    mail = get_gmail_service(GMAIL_USER, GMAIL_APP_PASSWORD)
    
    if not mail:
        print("❌ Failed to connect to Gmail")
        return []
    
    print("✅ Connected successfully!")
    
    # Calculate date range
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
    
    print(f"\n🔍 Searching for application emails since {since_date}...")
    
    try:
        mail.select("inbox")
        
        # Search for application-related emails
        keywords = [
            'SUBJECT "application"',
            'SUBJECT "thank you"',
            'SUBJECT "received"',
            'SUBJECT "confirmation"',
            'SUBJECT "applied"'
        ]
        
        results = []
        seen_ids = set()
        
        for keyword in keywords:
            search_query = f'(SINCE {since_date} {keyword})'
            status, messages = mail.search(None, search_query)
            
            if status == "OK":
                email_ids = messages[0].split()
                print(f"   Found {len(email_ids)} emails with {keyword}")
                
                for e_id in email_ids:
                    if e_id in seen_ids:
                        continue
                    seen_ids.add(e_id)
                    
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
                                
                                # Get sender
                                sender = msg.get("From", "")
                                
                                # Get date
                                date_str = msg.get("Date", "")
                                
                                # Get body preview
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body = part.get_payload(decode=True).decode(errors='ignore')
                                            break
                                else:
                                    body = msg.get_payload(decode=True).decode(errors='ignore')
                                
                                # Extract company name
                                company = extract_company_name(sender, subject, body)
                                
                                results.append({
                                    "subject": subject,
                                    "sender": sender,
                                    "date": date_str,
                                    "company": company,
                                    "body_preview": body[:200]
                                })
                    except Exception as e:
                        print(f"   ⚠️  Error processing email {e_id}: {e}")
                        continue
        
        return results
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass

def extract_company_name(sender, subject, body):
    """Try to extract company name from email"""
    
    # Common patterns in sender email
    sender_lower = sender.lower()
    
    # Try to extract from email domain
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        # Clean up common domains
        if domain not in ['gmail', 'noreply', 'no-reply', 'donotreply', 'mail', 'email']:
            return domain.replace('-', ' ').title()
    
    # Try to match known companies from subject
    companies = ['lyft', 'thyme care', 'capgemini', 'oracle', 'whatnot', 'paylocity', 
                 'ziff davis', 'heartland', 'blank metal', 'greenhouse', 'lever', 'workday']
    
    for company in companies:
        if company in subject.lower() or company in sender_lower:
            return company.title()
    
    # Fallback to first word in sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        return name_match.group(1).strip()
    
    return "Unknown"

def main():
    print("=" * 60)
    print("📊 JOB APPLICATION TRACKER - Gmail Analysis")
    print("=" * 60)
    
    # Search for emails from last 7 days
    emails = search_application_emails(days_back=7)
    
    if not emails:
        print("\n❌ No application emails found")
        return
    
    print(f"\n✅ Found {len(emails)} application-related emails")
    print("\n" + "=" * 60)
    print("📋 APPLICATION CONFIRMATIONS")
    print("=" * 60)
    
    # Group by company
    by_company = {}
    for email_data in emails:
        company = email_data['company']
        if company not in by_company:
            by_company[company] = []
        by_company[company].append(email_data)
    
    # Display results
    for idx, (company, company_emails) in enumerate(sorted(by_company.items()), 1):
        print(f"\n{idx}. {company} ({len(company_emails)} email(s))")
        for e in company_emails:
            print(f"   📧 Subject: {e['subject']}")
            print(f"   📅 Date: {e['date']}")
            print(f"   👤 From: {e['sender']}")
            print(f"   📝 Preview: {e['body_preview'][:100]}...")
            print()
    
    print("=" * 60)
    print(f"📊 SUMMARY")
    print("=" * 60)
    print(f"Total Companies: {len(by_company)}")
    print(f"Total Emails: {len(emails)}")
    print()
    
    # List companies
    print("Companies that responded:")
    for company in sorted(by_company.keys()):
        print(f"  ✓ {company}")

if __name__ == "__main__":
    main()
