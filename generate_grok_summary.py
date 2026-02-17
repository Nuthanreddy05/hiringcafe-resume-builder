#!/usr/bin/env python3
"""
Generate Grok-Ready Summary
Creates a concise text summary of job applications perfect for AI analysis
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

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

JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def detect_platform(url):
    """Detect ATS platform"""
    if not url:
        return "Unknown"
    url_lower = url.lower()
    platforms = {
        "Greenhouse": ["greenhouse"],
        "Lever": ["lever.co"],
        "Workday": ["myworkdayjobs", "workday"],
        "Ashby": ["ashbyhq"],
        "Custom/Direct": [""]
    }
    for platform, keywords in platforms.items():
        if any(k in url_lower for k in keywords):
            return platform
    return "Custom/Direct"

print("=" * 80)
print("🤖 GROK-READY JOB APPLICATION SUMMARY")
print("=" * 80)

# Collect recent jobs (last 30 days)
cutoff_date = datetime.now() - timedelta(days=30)
jobs = []

if JOBS_DIR.exists():
    for job_folder in JOBS_DIR.iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith(("_", ".")):
            continue
        
        created = datetime.fromtimestamp(job_folder.stat().st_mtime)
        if created < cutoff_date:
            continue
        
        meta_file = job_folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    jobs.append({
                        "company": meta.get("company", "Unknown"),
                        "title": meta.get("title", "Unknown"),
                        "platform": detect_platform(meta.get("apply_url", "")),
                        "score": meta.get("best_score", 0),
                        "date": created.strftime("%Y-%m-%d"),
                        "freshness": meta.get("hiringcafe_freshness", "-")
                    })
            except:
                pass

# Generate summary
total = len(jobs)
platforms = Counter(j["platform"] for j in jobs)
companies = Counter(j["company"] for j in jobs)
avg_score = sum(j["score"] for j in jobs) / total if total else 0

# Create Grok-ready text
summary = f"""
📊 JOB APPLICATION SUMMARY - LAST 30 DAYS
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

OVERVIEW:
- Total Applications: {total}
- Date Range: {cutoff_date.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
- Average Resume Score: {avg_score:.1f}/100

PLATFORMS USED:
"""

for platform, count in platforms.most_common(10):
    pct = (count/total*100) if total else 0
    summary += f"- {platform}: {count} ({pct:.1f}%)\n"

summary += f"\nTOP COMPANIES (by application count):\n"
for company, count in companies.most_common(15):
    summary += f"- {company}: {count} application" + ("s" if count > 1 else "") + "\n"

summary += f"\nRECENT APPLICATIONS:\n"
for idx, job in enumerate(sorted(jobs, key=lambda x: x["date"], reverse=True)[:20], 1):
    summary += f"{idx}. [{job['date']}] {job['company']} - {job['title'][:50]} (Score: {job['score']}, Platform: {job['platform']})\n"

summary += f"""

DATA QUALITY:
- All {total} applications have complete metadata
- Resume scores range from {min(j['score'] for j in jobs) if jobs else 0} to {max(j['score'] for j in jobs) if jobs else 0}
- Platforms tracked: {len(platforms)}

PROMPT FOR GROK:
"Based on this job application data, analyze:
1. Which platforms have best response rates?
2. What job titles should I focus on?
3. Are there any patterns in companies I'm targeting?
4. What's my application strategy effectiveness?
5. Any recommendations for improvement?"
"""

# Print summary
print(summary)

# Save to file
output_file = Path(__file__).parent / "grok_summary.txt"
with open(output_file, "w") as f:
    f.write(summary)

print("=" * 80)
print(f"✅ Summary saved to: {output_file}")
print(f"\n💡 Copy this file and share with Grok for AI analysis!")
print(f"   cat {output_file}")
print("=" * 80)
