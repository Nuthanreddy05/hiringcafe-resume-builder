#!/usr/bin/env python3
"""
Deep Content Analysis of Rejections
Uses DeepSeek AI to compare Resume vs JD and determine *why* it was rejected.
Correlates with ATS platform and Rejection Timing.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

# Load env for API key
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "DEEPSEEK_API_KEY" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")

load_env()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

JOBS_DIR = Path.home() / 'Desktop' / 'Google Auto'

def get_job_details(folder_name):
    """Load JD and Resume content"""
    folder = JOBS_DIR / folder_name
    
    jd_file = folder / 'JD.txt'
    resume_file = folder / 'resume.tex'
    
    if not jd_file.exists() or not resume_file.exists():
        return None, None
        
    return jd_file.read_text(errors='ignore'), resume_file.read_text(errors='ignore')

def analyze_with_ai(company, title, platform, timing, reason, jd, resume):
    """Ask DeepSeek to analyze why it was rejected"""
    
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) and Technical Recruiter.
    Analyze this rejected job application to find the likely cause.
    
    CONTEXT:
    - Company: {company}
    - Role: {title}
    - ATS Platform: {platform}
    - Time to Reject: {timing} (Fast = keyword mismatch, Slow = human review)
    - Rejection Email Reason: "{reason}"
    
    JOB DESCRIPTION (Excerpt):
    {jd[:2000]}...
    
    RESUME (Excerpt):
    {resume[:3000]}...
    
    TASK:
    Analyze the gap between the JD and Resume. Why was this rejected?
    
    Provide a JSON response with:
    1. "primary_cause": One of [Keywords, Experience Gap, Location/Visa, Overqualified, Formatting, Unknown]
    2. "score": 0-100 match score estimate
    3. "missing_keywords": List of top 3 missing hard skills found in JD but not Resume
    4. "analysis": 1-sentence explanation of the specific mismatch
    
    Response format: JSON only.
    """
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error analyzing {company}: {e}")
        return None

def main():
    print("🧠 STARTING DEEP CONTENT ANALYSIS OF REJECTIONS...")
    print("=" * 80)
    
    # Needs the mapped rejections file from previous step
    # Or matches them again. Let's use rejection_details.json if it exists (it was saving it in previous script, but script failed/was fixed?) 
    # Let's match fresh to be safe.
    
    with open('ai_classified_emails_enhanced.json') as f:
        emails = json.load(f)
        
    # Get all job folders
    all_jobs = []
    for folder in JOBS_DIR.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            meta = folder / 'meta.json'
            if meta.exists():
                try:
                    with open(meta) as f:
                        m = json.load(f)
                        m['folder'] = folder.name
                        all_jobs.append(m)
                except:
                    pass

    # Match and Analyze
    analyzed_count = 0
    results = []
    
    print(f"{'COMPANY':<20} | {'PLATFORM':<12} | {'TIME':<10} | {'CAUSE':<15} | {'MISSING KEYS'}")
    print("-" * 100)
    
    for rej in emails['rejections']: # Limit to first 15 for speed if many
        if analyzed_count >= 15: break
        
        # Match to folder
        matched_job = None
        for job in all_jobs:
            if job.get('company', '').lower() in rej['company'].lower() or \
               rej['company'].lower() in job.get('company', '').lower():
                matched_job = job
                break
        
        if not matched_job:
            continue
            
        # Get Platform
        url = matched_job.get('apply_url', '').lower()
        if 'greenhouse' in url: platform = 'Greenhouse'
        elif 'lever' in url: platform = 'Lever'
        elif 'ashby' in url: platform = 'Ashby'
        elif 'workday' in url: platform = 'Workday'
        else: platform = 'Custom'
        
        # Get Timing
        try:
            applied = datetime.fromisoformat(matched_job.get('scraped_at'))
            rejected = datetime.fromisoformat(rej['date'])
            hours = (rejected - applied).total_seconds() / 3600
            if hours < 24: timing = f"{hours:.1f}h (Fast)"
            else: timing = f"{hours/24:.1f}d (Slow)"
        except:
            timing = "Unknown"
            
        # Get Files
        jd, resume = get_job_details(matched_job['folder'])
        if not jd or not resume:
            continue
            
        # Analyze
        analysis_json = analyze_with_ai(
            matched_job.get('company'), 
            matched_job.get('title'), 
            platform, 
            timing, 
            rej.get('reason', ''),
            jd, 
            resume
        )
        
        if analysis_json:
            try:
                data = json.loads(analysis_json)
                print(f"{rej['company'][:20]:<20} | {platform:<12} | {timing:<10} | {data['primary_cause']:<15} | {', '.join(data['missing_keywords'][:3])}")
                results.append({
                    "company": rej['company'],
                    "platform": platform,
                    "timing": timing,
                    "analysis": data
                })
                analyzed_count += 1
            except:
                print(f"Failed to parse analysis for {rej['company']}")

    # Save detailed report
    with open('deep_rejection_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print("=" * 100)
    print(f"✅ Analyzed {analyzed_count} rejections deeply.")

if __name__ == "__main__":
    main()
