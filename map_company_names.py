#!/usr/bin/env python3
"""
Company Name Mapper
Extracts real company names from emails and job folders
"""

import os
import json
import re
from pathlib import Path
from difflib import SequenceMatcher

JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def extract_company_from_subject(subject):
    """Extract company name from email subject"""
    
    # Common patterns
    patterns = [
        r'(?:at|with|to|from)\s+([A-Z][A-Za-z\s&]+?)(?:\s+-|\s+\||$)',
        r'^([A-Z][A-Za-z\s&]+?)\s+(?:Job|Application|Interview|Position)',
        r'interview\s+(?:with|at)\s+([A-Z][A-Za-z\s&]+)',
        r'application\s+(?:to|at)\s+([A-Z][A-Za-z\s&]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up
            company = re.sub(r'\s+(Inc|LLC|Corp|Ltd|Team)\.?$', '', company, flags=re.IGNORECASE)
            return company
    
    return None

def get_all_companies_from_folders():
    """Get all company names from job folders"""
    companies = {}
    
    if not JOBS_DIR.exists():
        return companies
    
    for folder in JOBS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        
        meta_file = folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    company = meta.get("company", "")
                    if company:
                        companies[company.lower()] = company
            except:
                pass
    
    return companies

def fuzzy_match_company(email_company, known_companies):
    """Fuzzy match email company to known companies"""
    
    email_lower = email_company.lower()
    
    # Direct match
    if email_lower in known_companies:
        return known_companies[email_lower]
    
    # Partial match
    for known_key, known_name in known_companies.items():
        if email_lower in known_key or known_key in email_lower:
            return known_name
    
    # Fuzzy match
    best_match = None
    best_score = 0.6  # Threshold
    
    for known_key, known_name in known_companies.items():
        score = SequenceMatcher(None, email_lower, known_key).ratio()
        if score > best_score:
            best_score = score
            best_match = known_name
    
    return best_match

def enhance_email_data(ai_results):
    """Enhance email data with proper company names"""
    
    print("🔍 Extracting company names from job folders...")
    known_companies = get_all_companies_from_folders()
    print(f"Found {len(known_companies)} companies in job folders")
    
    print("\n🔄 Mapping emails to companies...")
    
    enhanced = {
        "confirmations": [],
        "rejections": [],
        "interviews": [],
        "updates": []
    }
    
    for category in ['confirmations', 'rejections', 'interviews', 'updates']:
        for email in ai_results.get(category, []):
            # Try to extract from subject first
            subject_company = extract_company_from_subject(email['subject'])
            
            if subject_company:
                # Try to match to known companies
                matched = fuzzy_match_company(subject_company, known_companies)
                if matched:
                    email['company'] = matched
                else:
                    email['company'] = subject_company
            else:
                # Try to match current company name
                current = email.get('company', 'Unknown')
                matched = fuzzy_match_company(current, known_companies)
                if matched:
                    email['company'] = matched
            
            enhanced[category].append(email)
    
    return enhanced

def main():
    print("\n🏢 COMPANY NAME MAPPER\n")
    print("=" * 60)
    
    # Load AI results
    ai_file = Path(__file__).parent / "ai_classified_emails.json"
    
    if not ai_file.exists():
        print("❌ No AI classification data found")
        return
    
    with open(ai_file) as f:
        ai_results = json.load(f)
    
    # Enhance with proper company names
    enhanced = enhance_email_data(ai_results)
    
    # Save enhanced version
    enhanced_file = Path(__file__).parent / "ai_classified_emails_enhanced.json"
    with open(enhanced_file, 'w') as f:
        json.dump(enhanced, f, indent=2)
    
    print(f"\n✅ Enhanced data saved: {enhanced_file}")
    
    # Show some examples
    print("\n📊 Sample Enhanced Companies:")
    print("=" * 60)
    for interview in enhanced['interviews'][:5]:
        print(f"✨ {interview['company']}")
        print(f"   Subject: {interview['subject'][:60]}...")
        print()

if __name__ == "__main__":
    main()
