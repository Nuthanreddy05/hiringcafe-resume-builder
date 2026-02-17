#!/usr/bin/env python3
"""
Analyze rejections by examining resume quality, JD matching, and timing
"""

import json
from pathlib import Path
from datetime import datetime

jobs_dir = Path.home() / 'Desktop' / 'Google Auto'

# Load rejection data
with open('ai_classified_emails_enhanced.json') as f:
    emails = json.load(f)

# Get all job folders
all_jobs = []
for folder in jobs_dir.iterdir():
    if not folder.is_dir() or folder.name.startswith(('_', '.')):
        continue
    
    meta_file = folder / 'meta.json'
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                meta = json.load(f)
                meta['folder_path'] = str(folder)
                meta['folder_name'] = folder.name
                all_jobs.append(meta)
        except:
            pass

# Match rejections to jobs
rejection_analysis = []

for rej_email in emails['rejections']:
    company_email = rej_email['company'].lower()
    subject = rej_email.get('subject', '').lower()
    
    # Find matching job
    best_match = None
    
    for job in all_jobs:
        job_company = job.get('company', '').lower()
        
        if company_email in job_company or job_company in company_email or job_company in subject:
            best_match = job
            break
    
    if best_match:
        folder = Path(best_match['folder_path'])
        
        # Check files
        jd_file = folder / 'jd.txt'
        resume_tex = folder / 'resume.tex'
        resume_pdf = folder / 'resume.pdf'
        
        # Get timing
        applied = best_match.get('scraped_at', '')
        rejected = rej_email['date']
        
        if applied:
            apply_dt = datetime.fromisoformat(applied)
            reject_dt = datetime.fromisoformat(rejected)
            hours_to_reject = (reject_dt - apply_dt).total_seconds() / 3600
        else:
            hours_to_reject = 0
        
        # Read files
        jd_content = jd_file.read_text() if jd_file.exists() else ""
        resume_content = resume_tex.read_text() if resume_tex.exists() else ""
        
        # Platform
        url = best_match.get('apply_url', '').lower()
        if 'greenhouse' in url:
            platform = 'Greenhouse'
        elif 'lever' in url:
            platform = 'Lever'
        elif 'ashby' in url:
            platform = 'Ashby'
        elif 'workday' in url:
            platform = 'Workday'
        else:
            platform = 'Custom/Direct'
        
        rejection_analysis.append({
            'company': best_match.get('company'),
            'title': best_match.get('title'),
            'platform': platform,
            'applied_date': applied,
            'rejected_date': rejected,
            'hours_to_reject': hours_to_reject,
            'has_jd': jd_file.exists(),
            'has_resume': resume_tex.exists(),
            'has_pdf': resume_pdf.exists(),
            'jd_length': len(jd_content.split()),
            'resume_length': len(resume_content.split()),
            'rejection_reason': rej_email.get('reason', ''),
            'folder': folder.name
        })

# Print analysis
print('🔍 RESUME & JD QUALITY ANALYSIS FOR REJECTIONS')
print('=' * 90)

for idx, rej in enumerate(rejection_analysis, 1):
    print(f'\n{idx}. {rej["company"]}')
    print('-' * 90)
    print(f'Position: {rej["title"][:70]}')
    print()
    
    # Files status
    check_jd = "✅" if rej["has_jd"] else "❌"
    check_resume = "✅" if rej["has_resume"] else "❌"
    check_pdf = "✅" if rej["has_pdf"] else "❌"
    
    print('📄 FILES:')
    print(f'  JD: {check_jd} ({rej["jd_length"]} words)')
    print(f'  Resume: {check_resume} ({rej["resume_length"]} words)')
    print(f'  PDF: {check_pdf}')
    print()
    
    # Timing
    print('⏱️  TIMING:')
    if rej['applied_date']:
        print(f'  Applied: {rej["applied_date"][:16]}')
        print(f'  Rejected: {rej["rejected_date"][:16]}')
        hours = rej['hours_to_reject']
        if hours < 1:
            print(f'  ⚡ INSTANT REJECT: {hours*60:.0f} minutes')
        elif hours < 24:
            print(f'  ⚡ FAST REJECT: {hours:.1f} hours')
        else:
            print(f'  ⏰ Time: {hours/24:.1f} days')
    print()
    
    print(f'🏢 Platform: {rej["platform"]}')
    print(f'❌ Reason: {rej["rejection_reason"][:100]}')

# Summary stats
print('\n' + '=' * 90)
print('📊 SUMMARY STATISTICS')
print('=' * 90)

instant_rejects = [r for r in rejection_analysis if r['hours_to_reject'] < 1]
fast_rejects = [r for r in rejection_analysis if 1 <= r['hours_to_reject'] < 24]
slow_rejects = [r for r in rejection_analysis if r['hours_to_reject'] >= 24]

print(f'\n⏱️  TIMING BREAKDOWN:')
print(f'  Instant (<1h): {len(instant_rejects)} ({len(instant_rejects)/len(rejection_analysis)*100:.1f}%)')
print(f'  Fast (1-24h): {len(fast_rejects)} ({len(fast_rejects)/len(rejection_analysis)*100:.1f}%)')
print(f'  Slow (>24h): {len(slow_rejects)} ({len(slow_rejects)/len(rejection_analysis)*100:.1f}%)')

# Platform breakdown
from collections import Counter
platforms = Counter(r['platform'] for r in rejection_analysis)
print(f'\n🏢 PLATFORM BREAKDOWN:')
for platform, count in platforms.most_common():
    print(f'  {platform}: {count} ({count/len(rejection_analysis)*100:.1f}%)')

# File completeness
missing_resume = [r for r in rejection_analysis if not r['has_resume']]
missing_pdf = [r for r in rejection_analysis if not r['has_pdf']]

print(f'\n📄 FILE STATUS:')
print(f'  Missing Resume: {len(missing_resume)}')
print(f'  Missing PDF: {len(missing_pdf)}')

if missing_resume:
    print(f'\n⚠️  APPLICATIONS WITHOUT RESUME:')
    for r in missing_resume[:5]:
        print(f'    - {r["company"]}')

# Save
with open('rejection_details.json', 'w') as f:
    json.dump(rejection_analysis, f, indent=2)

print(f'\n✅ Analyzed {len(rejection_analysis)} of {len(emails["rejections"])} rejections')
print('📊 Detailed data saved to rejection_details.json')
