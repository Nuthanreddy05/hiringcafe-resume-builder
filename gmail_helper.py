
import imaplib
import email
import re
import time
from email.header import decode_header
import difflib

def get_gmail_service(user, password):
    """Connect to Gmail IMAP"""
    try:
        # App Passwords often copied with spaces
        password = password.replace(" ", "")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        return mail
    except Exception as e:
        print(f"      ❌ Gmail Login Failed: {e}")
        return None

def check_for_verification_email(user, password, wait_seconds=60, poll_interval=5):
    """
    Poll Gmail for a recent email containing a verification code or link.
    Returns: {"type": "code"|"link", "value": "123456"|"http..."} or None
    """
    mail = get_gmail_service(user, password)
    if not mail:
        return None

    print(f"      📧 Polling Gmail for {wait_seconds}s...")
    
    start_time = time.time()
    while time.time() - start_time < wait_seconds:
        try:
            mail.select("inbox")
            # Search for emails from the last 1 day to be safe, or just UNSEEN
            # specific search: (UNSEEN SUBJECT "Notification" SINCE ...)
            # Let's search all recent UNSEEN
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == "OK":
                email_ids = messages[0].split()
                if email_ids:
                    # Look at the most recent ones
                    latest_ids = email_ids[-3:] 
                    for e_id in reversed(latest_ids):
                        _, msg_data = mail.fetch(e_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject, encoding = decode_header(msg["Subject"])[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(encoding if encoding else "utf-8")
                                
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body = part.get_payload(decode=True).decode()
                                            break
                                else:
                                    body = msg.get_payload(decode=True).decode()
                                
                                # Check heuristics
                                # Keywords: "Verification Code", "Security Code", "Confirm your account", "Workday"
                                if any(k in subject.lower() for k in ["code", "confirm", "verify", "workday", "security"]):
                                    print(f"      📩 Found potential email: {subject}")
                                    
                                    # Regex for 6-digit code
                                    code_match = re.search(r"\b\d{6}\b", body)
                                    if code_match:
                                        return {"type": "code", "value": code_match.group(0)}
                                    
                                    # Regex for Link
                                    # Look for a link wrapped in "Confirm Account" or similar?
                                    # For now, simplistic link finder
                                    # links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                                    # if links:
                                    #    return {"type": "link", "value": links[0]}
                                        
                        # If we processed emails, maybe mark as seen? 
                        # For now, kept logic simple.
                        
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"      ⚠️  Gmail processing error: {e}")
            time.sleep(poll_interval)
            
    return None

def check_for_confirmation_email(user, password, company_name=None, wait_seconds=60, poll_interval=5):
    """
    Poll Gmail for a recent 'Application Received' or 'Thank You' email.
    Returns: True if found, False otherwise.
    """
    mail = get_gmail_service(user, password)
    if not mail:
        return False

    print(f"      📧 Checking Gmail for confirmation ({wait_seconds}s)...")
    
    start_time = time.time()
    seen_ids = set()
    
    # Common subject keywords
    keywords = ["application", "received", "thank you", "confirmation", "applied", "creating your profile"]
    
    while time.time() - start_time < wait_seconds:
        try:
            mail.select("inbox")
            # Search UNSEEN first
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == "OK":
                email_ids = messages[0].split()
                if email_ids:
                    # Look at recent ones
                    latest_ids = email_ids[-5:] 
                    for e_id in reversed(latest_ids):
                        if e_id in seen_ids:
                            continue
                        seen_ids.add(e_id)
                        
                        _, msg_data = mail.fetch(e_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject, encoding = decode_header(msg["Subject"])[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(encoding if encoding else "utf-8")
                                subject = subject.lower()
                                
                                sender = msg.get("From", "").lower()
                                
                                # Check heuristics
                                match = False
                                
                                # 1. Company Name strict match in Subject or Sender
                                if company_name and company_name.lower() in (subject + sender):
                                    if any(k in subject for k in keywords):
                                        match = True
                                        
                                # 2. Loose match if reliable keywords
                                if "application received" in subject or "thank you for applying" in subject:
                                    match = True
                                    
                                if match:
                                    print(f"      📩 CONFIRMED: Found email '{subject}'")
                                    return True
                                        
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"      ⚠️  Gmail check error: {e}")
            time.sleep(poll_interval)
            
    return False
