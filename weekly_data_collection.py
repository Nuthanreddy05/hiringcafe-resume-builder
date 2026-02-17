#!/usr/bin/env python3
"""
Weekly Automated Data Collection
Runs every week to collect job application metrics
NO changes to process - just observe and collect data
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Import our existing tools
sys.path.insert(0, str(Path(__file__).parent))

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

def collect_weekly_metrics():
    """Collect all metrics for the week"""
    
    print("=" * 80)
    print("📊 WEEKLY DATA COLLECTION")
    print(f"Week of: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 80)
    
    # 1. Load AI classification results (run ai_email_classifier.py first)
    ai_results_file = Path(__file__).parent / "ai_classified_emails.json"
    
    if not ai_results_file.exists():
        print("\n⚠️  Run ai_email_classifier.py first to classify emails")
        return None
    
    with open(ai_results_file) as f:
        ai_results = json.load(f)
    
    # 2. Load job folders
    jobs = []
    cutoff = datetime.now() - timedelta(days=7)  # Last 7 days
    
    for folder in JOBS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        
        meta_file = folder / "meta.json"
        if not meta_file.exists():
            continue
        
        try:
            with open(meta_file) as f:
                meta = json.load(f)
            
            created = datetime.fromtimestamp(folder.stat().st_mtime)
            if created < cutoff:
                continue
            
            jobs.append({
                "folder": folder.name,
                "company": meta.get("company", "Unknown"),
                "title": meta.get("title", "Unknown"),
                "platform": detect_platform(meta.get("apply_url", "")),
                "score": meta.get("best_score", 0),
                "discovered_at": meta.get("discovered_at"),
                "scraped_at": meta.get("scraped_at"),
                "hiringcafe_timestamp": meta.get("hiringcafe_timestamp"),
                "created": created.isoformat()
            })
        except:
            continue
    
    # 3. Calculate metrics
    metrics = {
        "week_of": datetime.now().strftime("%Y-%m-%d"),
        "total_applications": len(jobs),
        "confirmations": len(ai_results.get("confirmations", [])),
        "rejections": len(ai_results.get("rejections", [])),
        "interviews": len(ai_results.get("interviews", [])),
        "pending": len(jobs) - len(ai_results.get("confirmations", [])) - len(ai_results.get("rejections", [])),
        
        "by_platform": {},
        "by_score_range": {},
        "by_freshness": {},
        
        "rejection_details": ai_results.get("rejections", []),
        "interview_details": ai_results.get("interviews", [])
    }
    
    # Group by platform
    by_platform = defaultdict(lambda: {"total": 0, "confirmed": 0, "rejected": 0, "interviewed": 0})
    
    for job in jobs:
        platform = job["platform"]
        by_platform[platform]["total"] += 1
    
    # Match rejections to platforms
    for rejection in ai_results.get("rejections", []):
        company = rejection["company"].lower()
        for job in jobs:
            if company in job["company"].lower() or job["company"].lower() in company:
                by_platform[job["platform"]]["rejected"] += 1
                break
    
    # Match confirmations to platforms
    for confirmation in ai_results.get("confirmations", []):
        company = confirmation["company"].lower()
        for job in jobs:
            if company in job["company"].lower() or job["company"].lower() in company:
                by_platform[job["platform"]]["confirmed"] += 1
                break
    
    metrics["by_platform"] = dict(by_platform)
    
    # Group by score
    score_ranges = {
        "90-100": [],
        "80-89": [],
        "70-79": [],
        "below_70": []
    }
    
    for job in jobs:
        score = job["score"]
        if score >= 90:
            score_ranges["90-100"].append(job)
        elif score >= 80:
            score_ranges["80-89"].append(job)
        elif score >= 70:
            score_ranges["70-79"].append(job)
        else:
            score_ranges["below_70"].append(job)
    
    metrics["by_score_range"] = {
        k: len(v) for k, v in score_ranges.items()
    }
    
    # Group by freshness (how old was the job when we applied)
    freshness_groups = {
        "< 12h": [],
        "12-24h": [],
        "24-48h": [],
        "> 48h": []
    }
    
    for job in jobs:
        timestamp = job.get("hiringcafe_timestamp", "")
        if timestamp and "h" in timestamp:
            hours = int(timestamp.replace("h", ""))
            if hours < 12:
                freshness_groups["< 12h"].append(job)
            elif hours < 24:
                freshness_groups["12-24h"].append(job)
            elif hours < 48:
                freshness_groups["24-48h"].append(job)
            else:
                freshness_groups["> 48h"].append(job)
    
    metrics["by_freshness"] = {
        k: len(v) for k, v in freshness_groups.items()
    }
    
    return metrics

def detect_platform(url):
    """Detect ATS platform from URL"""
    if not url:
        return "Unknown"
    url_lower = url.lower()
    if "greenhouse" in url_lower:
        return "Greenhouse"
    elif "lever.co" in url_lower:
        return "Lever"
    elif "workday" in url_lower or "myworkdayjobs" in url_lower:
        return "Workday"
    elif "ashbyhq" in url_lower:
        return "Ashby"
    elif "icims" in url_lower:
        return "iCIMS"
    else:
        return "Custom/Direct"

def save_weekly_data(metrics):
    """Save weekly metrics to historical log"""
    
    # Create history directory
    history_dir = Path(__file__).parent / "weekly_data"
    history_dir.mkdir(exist_ok=True)
    
    # Save this week's data
    week_file = history_dir / f"week_{metrics['week_of']}.json"
    with open(week_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n✅ Saved: {week_file}")
    
    # Generate summary report
    report = []
    report.append("=" * 80)
    report.append(f"WEEKLY DATA COLLECTION - {metrics['week_of']}")
    report.append("=" * 80)
    report.append(f"\nTotal Applications: {metrics['total_applications']}")
    report.append(f"Confirmations: {metrics['confirmations']}")
    report.append(f"Rejections: {metrics['rejections']}")
    report.append(f"Interviews: {metrics['interviews']}")
    report.append(f"Pending: {metrics['pending']}")
    
    report.append("\n" + "-" * 80)
    report.append("BY PLATFORM:")
    for platform, stats in metrics["by_platform"].items():
        report.append(f"\n{platform}:")
        report.append(f"  Total: {stats['total']}")
        report.append(f"  Confirmed: {stats['confirmed']}")
        report.append(f"  Rejected: {stats['rejected']}")
    
    report.append("\n" + "-" * 80)
    report.append("BY SCORE:")
    for range_name, count in metrics["by_score_range"].items():
        report.append(f"  {range_name}: {count}")
    
    report.append("\n" + "-" * 80)
    report.append("BY FRESHNESS:")
    for freshness, count in metrics["by_freshness"].items():
        report.append(f"  {freshness}: {count}")
    
    report_text = "\n".join(report)
    print("\n" + report_text)
    
    # Save report
    report_file = history_dir / f"week_{metrics['week_of']}_report.txt"
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    return report_file

def main():
    print("\n🔬 STARTING WEEKLY DATA COLLECTION (WEEK 1)\n")
    print("📋 PURPOSE: Observe and collect - NO changes to process yet")
    print("⏳ We'll analyze patterns after 2 weeks of data\n")
    
    # Collect metrics
    metrics = collect_weekly_metrics()
    
    if not metrics:
        return
    
    # Save data
    report_file = save_weekly_data(metrics)
    
    print("\n" + "=" * 80)
    print("✅ WEEK 1 DATA COLLECTED!")
    print("=" * 80)
    print(f"\n📊 Data saved to: weekly_data/")
    print(f"📄 Report: {report_file}")
    print(f"\n💡 Next steps:")
    print(f"   1. Continue applying normally this week")
    print(f"   2. Run this script again next week")
    print(f"   3. After 2 weeks, we'll analyze patterns")
    print(f"   4. THEN we'll identify root cause and fix it")
    print("=" * 80)

if __name__ == "__main__":
    main()
