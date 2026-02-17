#!/usr/bin/env python3
import os
import json
import requests
import re
from pathlib import Path
from datetime import datetime
from difflib import get_close_matches

# Load env variables
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

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
JOBS_DIR = Path.home() / 'Desktop' / 'Google Auto'
CLASSIFIED_EMAILS = Path(__file__).parent / "ai_classified_emails.json"

def call_deepseek_analysis(prompt):
    """Call DeepSeek API for technical analysis"""
    if not DEEPSEEK_API_KEY:
        return {"error": "API Key missing"}

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert Technical Recruiter and ATS Optimization Engine. Your goal is to analyze job application mismatches between resumes and JDs."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        return json.loads(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        return {"error": str(e)}

def get_job_folders():
    """Get all processed job folders from Desktop"""
    folders = []
    for item in JOBS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith(('_', '.')):
            meta_path = item / 'meta.json'
            if meta_path.exists():
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                        meta['path'] = item
                        folders.append(meta)
                except: pass
    return folders

def fuzzy_match_company(company_name, folders):
    """Match email company name with local folder metadata"""
    # Try exact match first
    for folder in folders:
        if company_name.lower() in folder.get('company', '').lower() or folder.get('company', '').lower() in company_name.lower():
            return folder
    
    # Try fuzzy match on folder names
    folder_names = [f['path'].name for f in folders]
    matches = get_close_matches(company_name, folder_names, n=1, cutoff=0.5)
    if matches:
        for folder in folders:
            if folder['path'].name == matches[0]:
                return folder
    return None

def analyze_rejections():
    """Phase 1: Analyze Rejected Applications"""
    print("\n🚀 PHASE 1: ANALYZING REJECTIONS")
    print("=" * 60)
    
    if not CLASSIFIED_EMAILS.exists():
        print("❌ Error: ai_classified_emails.json not found.")
        return []

    with open(CLASSIFIED_EMAILS) as f:
        data = json.load(f)
    
    rejections = data.get('rejections', [])
    folders = get_job_folders()
    
    results = []
    
    # Track companies we've already analyzed in this run to avoid duplicates
    analyzed_companies = set()
    
    for rej in rejections:
        original_company = rej.get('company', 'Unknown')
        subject = rej.get('subject', '')
        
        # Refine company name if it's a generic ATS domain
        company = original_company
        generic_names = ['us', 'eu', 'ashbyhq', 'greenhouse', 'lever', 'talent acquisition', 'notifications', 'myworkday', 'workflow']
        if company.lower() in generic_names or len(company) <= 2:
            # Try to extract from subject
            # Patterns like "Application update: [Company]", "Regarding your application to [Company]", "[Company] Application"
            patterns = [
                r"to ([\w\s&]+)", 
                r"from ([\w\s&]+)", 
                r"at ([\w\s&]+)", 
                r": ([\w\s&]+) Application",
                r"^([\w\s&]+) Application"
            ]
            for p in patterns:
                m = re.search(p, subject, re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    if extracted.lower() not in generic_names:
                        company = extracted
                        break
        
        if company in analyzed_companies: continue
        
        print(f"🔍 Analyzing: {company} (Original: {original_company})...")
        
        match = fuzzy_match_company(company, folders)
        if not match:
            # Try matching with parts of the subject if still not found
            print(f"   ⚠️  No direct folder match. Retrying with subject-based matching...")
            for folder in folders:
                folder_co = folder.get('company', '').lower()
                if folder_co and folder_co in subject.lower():
                    match = folder
                    break
        
        if not match:
            print(f"   ❌ Skipping: No local folder found for {company}.")
            continue
            
        jd_path = match['path'] / 'JD.txt'
        resume_path = match['path'] / 'resume.tex'
        
        if not jd_path.exists() or not resume_path.exists():
            print(f"   ⚠️  Missing files in {match['path'].name}. Skipping.")
            continue
            
        jd_text = jd_path.read_text(errors='ignore')
        resume_text = resume_path.read_text(errors='ignore')
        
        prompt = f"""
Analyze this REJECTED application. Compare the tailored Resume against the JD to find why it was rejected.

COMPANY: {match.get('company')}
ROLE: {match.get('title')}
REJECTION EMAIL SUBJECT: "{subject}"
REJECTION EMAIL REASON: "{rej.get('reason', 'None provided')}"

JOB DESCRIPTION (Excerpt):
{jd_text[:2800]}

RESUME (Excerpt):
{resume_text[:3800]}

ANALYSIS REQUIREMENTS:
Provide a JSON object with:
1. "keywords_missing": List of top 3 hard skills in JD missing from resume.
2. "experience_gap": Evaluation of YoE or tech stack mismatch.
3. "ats_match_score": 0-100 estimate.
4. "rejection_type": "Automated Filter" (if rejected within 48h) or "Human Review" (if rejected later).
5. "action_item": One specific improvement for the base profile.
"""
        analysis = call_deepseek_analysis(prompt)
        results.append({
            "company": company,
            "role": match.get('title'),
            "status": "REJECTED",
            "analysis": analysis,
            "applied_date": match.get('scraped_at'),
            "rejected_date": rej.get('date')
        })
        analyzed_companies.add(company)
        print(f"   ✅ Analysis Complete.")
        
        # Limit rejections to top 15 for speed in first report
        if len(results) >= 15:
            print("\n⏳ Reached 15 rejections. Moving to Phase 2...")
            break

    return results

def analyze_ghosts():
    """Phase 2: Analyze Ghosted Applications (Applied > 5 days ago, no reply)"""
    print("\n🚀 PHASE 2: ANALYZING GHOSTED JOBS")
    print("=" * 60)
    
    folders = get_job_folders()
    with open(CLASSIFIED_EMAILS) as f:
        data = json.load(f)
        
    responses = data.get('confirmations', []) + data.get('rejections', []) + data.get('interviews', [])
    responded_companies = [r.get('company', '').lower() for r in responses]
    
    ghosts = []
    now = datetime.now()
    
    for folder in folders:
        applied_at_str = folder.get('scraped_at')
        if not applied_at_str: continue
        
        try:
            applied_at = datetime.fromisoformat(applied_at_str)
        except: continue
        
        days_passed = (now - applied_at).days
        
        # If applied more than 5 days ago and no response found
        if days_passed > 5:
            responded = False
            for resp in responded_companies:
                if resp in folder.get('company', '').lower() or folder.get('company', '').lower() in resp:
                    responded = True
                    break
            
            if not responded:
                ghosts.append(folder)

    results = []
    for ghost in ghosts:
        company = ghost.get('company')
        print(f"👻 Analyzing Ghosted: {company}...")
        
        jd_path = ghost['path'] / 'JD.txt'
        resume_path = ghost['path'] / 'resume.tex'
        
        if not jd_path.exists() or not resume_path.exists(): continue
        
        jd_text = jd_path.read_text(errors='ignore')
        resume_text = resume_path.read_text(errors='ignore')
        
        prompt = f"""
Analyze this GHOSTED application (Applied > 5 days ago, no response). 
Determine why the recruiter or ATS might have ignored this application.

COMPANY: {company}
ROLE: {ghost.get('title')}

JOB DESCRIPTION (Excerpt):
{jd_text[:2500]}

RESUME (Excerpt):
{resume_text[:3500]}

ANALYSIS REQUIREMENTS:
Provide a JSON object with:
1. "keywords_missing": List of top 3 hard skills in JD missing from resume.
2. "ghost_reason": Why it was likely ignored (Overqualified, Missing Skill, Saturation, etc).
3. "ats_match_score": 0-100 estimate.
4. "action_item": One specific improvement for future similar roles.
"""
        analysis = call_deepseek_analysis(prompt)
        results.append({
            "company": company,
            "role": ghost.get('title'),
            "status": "GHOSTED",
            "analysis": analysis,
            "applied_date": ghost.get('scraped_at')
        })
        print(f"   ✅ Analysis Complete.")
        
    return results

def save_report(results, filename="application_analysis_report.md"):
    """Generate Markdown Report"""
    content = f"# Application Status & Depth Analysis (DeepSeek AI)\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    content += "## 📊 Executive Summary\n"
    total = len(results)
    rejections = len([r for r in results if r['status'] == "REJECTED"])
    ghosts = len([r for r in results if r['status'] == "GHOSTED"])
    content += f"- Total Analyzed: {total}\n"
    content += f"- Rejections: {rejections}\n"
    content += f"- Ghosted: {ghosts}\n\n"
    
    content += "## ❌ Phase 1: Rejection Analysis\n"
    for res in [r for r in results if r['status'] == "REJECTED"]:
        content += f"### {res['company']} - {res['role']}\n"
        content += f"- **Date Applied**: {res['applied_date'][:10]}\n"
        content += f"- **Date Rejected**: {res['rejected_date'][:10]}\n"
        a = res['analysis']
        content += f"- **ATS Match Score**: `{a.get('ats_match_score', 'N/A')}%`\n"
        content += f"- **Missing Keywords**: {', '.join(a.get('keywords_missing', []))}\n"
        content += f"- **Type**: {a.get('rejection_type')}\n"
        content += f"- **Gap**: {a.get('experience_gap')}\n"
        content += f"- **Action**: {a.get('action_item')}\n\n"
        
    content += "## 👻 Phase 2: Ghosted Analysis\n"
    for res in [r for r in results if r['status'] == "GHOSTED"]:
        content += f"### {res['company']} - {res['role']}\n"
        content += f"- **Date Applied**: {res['applied_date'][:10]}\n"
        a = res['analysis']
        content += f"- **ATS Match Score**: `{a.get('ats_match_score', 'N/A')}%`\n"
        content += f"- **Likely Ghost Reason**: {a.get('ghost_reason')}\n"
        content += f"- **Missing Keywords**: {', '.join(a.get('keywords_missing', []))}\n"
        content += f"- **Action**: {a.get('action_item')}\n\n"

    Path(filename).write_text(content)
    print(f"\n📄 Report saved to: {filename}")

if __name__ == "__main__":
    # Sequence: Rejections first, then Ghosts
    rejection_results = analyze_rejections()
    ghost_results = analyze_ghosts()
    
    save_report(rejection_results + ghost_results)
