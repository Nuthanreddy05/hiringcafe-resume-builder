#!/usr/bin/env python3
"""
ATS Platform Performance Analytics
Tracks complete timeline: Job Posted → Resume Generated → Email Confirmed
Analyzes which ATS platforms are fastest and most reliable
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from gmail_helper import get_gmail_service
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime

#Load from .env
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

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def detect_ats_platform(url, sender):
    """Detect ATS platform from URL or email sender"""
    url_lower = url.lower() if url else ""
    sender_lower = sender.lower() if sender else ""
    
    platforms = {
        "Greenhouse": ["greenhouse", "greenhouse-mail"],
        "Lever": ["lever.co", "lever"],
        "Workday": ["myworkdayjobs", "workday"],
        "iCIMS": ["icims", "talent.icims"],
        "SmartRecruiters": ["smartrecruiters"],
        "Taleo": ["taleo.net", "taleo"],
        "Ashby": ["ashbyhq", "jobs.ashbyhq"],
        "BambooHR": ["bamboohr"],
        "JazzHR": ["jazzhr", "applytojob"],
        "Paylocity": ["paylocity", "recruiting.paylocity"],
        "Oracle": ["oraclecloud", "taleo"],
        "ADP": ["adp.com"],
        "UKG": ["ultipro", "ukg"],
        "Bullhorn": ["bullhornstaffing"],
        "Jobvite": ["jobvite"],
        "Custom/Unknown": []
    }
    
    for platform, keywords in platforms.items():
        for keyword in keywords:
            if keyword in url_lower or keyword in sender_lower:
                return platform
    
    return "Custom/Unknown"

def analyze_job_with_timing():
    """Analyze each job with complete timeline"""
    print("\n📊 Analyzing Job Timeline Data...")
    print("=" * 80)
    
    if not JOBS_DIR.exists():
        print(f"❌ Directory not found: {JOBS_DIR}")
        return []
    
    jobs_with_timing = []
    
    for job_folder in JOBS_DIR.iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith("_") or job_folder.name.startswith("."):
            continue
        
        job_timing = {
            "folder_name": job_folder.name,
        }
        
        # 1. Resume Generated Time (folder creation)
        stat = job_folder.stat()
        job_timing["resume_generated_timestamp"] = stat.st_mtime
        job_timing["resume_generated"] = datetime.fromtimestamp(stat.st_mtime)
        
        # 2. Get job metadata
        meta_file = job_folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    job_timing["company"] = meta.get("company", "Unknown")
                    job_timing["title"] = meta.get("title", "Unknown")
                    job_timing["url"] = meta.get("apply_url", "")
                    
                    # 3. Job Posted Date (if captured in meta)
                    if "posted_date" in meta:
                        try:
                            job_timing["job_posted"] = datetime.fromisoformat(meta["posted_date"])
                        except:
                            pass
                    
                    # Detect ATS from URL
                    job_timing["ats_platform"] = detect_ats_platform(job_timing["url"], "")
            except:
                job_timing["company"] = "Unknown"
                job_timing["ats_platform"] = "Unknown"
        
        jobs_with_timing.append(job_timing)
    
    print(f"✅ Analyzed {len(jobs_with_timing)} jobs")
    return jobs_with_timing

def get_gmail_confirmations_with_timing():
    """Get all confirmations with detailed timing"""
    print("\n📧 Fetching Gmail Confirmations...")
    print("=" * 80)
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("❌ Gmail credentials not found")
        return []
    
    mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
    if not mail:
        print("❌ Failed to connect to Gmail")
        return []
    
    confirmations = []
    
    try:
        mail.select("inbox")
        
        keywords = ['SUBJECT "application"', 'SUBJECT "thank you"', 'SUBJECT "received"']
        seen_ids = set()
        
        for keyword in keywords:
            status, messages = mail.search(None, keyword)
            
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
                                
                                # Parse email date
                                try:
                                    email_date = parsedate_to_datetime(date_str)
                                    # Make naive for comparison
                                    if email_date.tzinfo is not None:
                                        email_date = email_date.replace(tzinfo=None)
                                except:
                                    email_date = None
                                
                                company = extract_company(sender, subject)
                                ats_platform = detect_ats_platform("", sender)
                                
                                confirmations.append({
                                    "company": company,
                                    "subject": subject,
                                    "sender": sender,
                                    "confirmation_received": email_date,
                                    "ats_platform": ats_platform
                                })
                    except:
                        continue
        
        print(f"✅ Found {len(confirmations)} confirmations")
        
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass
    
    return confirmations

def extract_company(sender, subject):
    """Extract company name"""
    sender_lower = sender.lower()
    
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        common = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 'icims', 'workday', 'recruiting']
        if domain not in common:
            return domain.replace('-', ' ').title()
    
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'noreply']:
            return name
    
    return "Unknown"

def match_and_calculate_timings(jobs, confirmations):
    """Match jobs with confirmations and calculate time differences"""
    print("\n🔗 Matching Jobs with Confirmations...")
    print("=" * 80)
    
    matched_data = []
    
    for job in jobs:
        job_company = job.get("company", "").lower()
        
        for conf in confirmations:
            conf_company = conf["company"].lower()
            
            # Match by company name
            if job_company in conf_company or conf_company in job_company:
                if conf["confirmation_received"] and job.get("resume_generated"):
                    
                    # Calculate time from resume generated to confirmation
                    time_to_confirm = conf["confirmation_received"] - job["resume_generated"]
                    hours_to_confirm = time_to_confirm.total_seconds() / 3600
                    
                    matched = {
                        "company": job.get("company"),
                        "title": job.get("title"),
                        "ats_platform": job.get("ats_platform") or conf.get("ats_platform"),
                        "resume_generated": job["resume_generated"],
                        "confirmation_received": conf["confirmation_received"],
                        "hours_to_confirm": hours_to_confirm,
                        "days_to_confirm": hours_to_confirm / 24
                    }
                    
                    # If we have posted date, calculate that too
                    if "job_posted" in job:
                        time_to_apply = job["resume_generated"] - job["job_posted"]
                        matched["hours_posted_to_applied"] = time_to_apply.total_seconds() / 3600
                    
                    matched_data.append(matched)
                    break  # Found match, move to next job
    
    print(f"✅ Matched {len(matched_data)} jobs with timing data")
    return matched_data

def analyze_by_platform(matched_data):
    """Analyze performance by ATS platform"""
    print("\n📈 Analyzing ATS Platform Performance...")
    print("=" * 80)
    
    platform_stats = defaultdict(lambda: {
        "count": 0,
        "total_hours": 0,
        "response_times": [],
        "fastest": None,
        "slowest": None
    })
    
    for match in matched_data:
        platform = match["ats_platform"]
        hours = match["hours_to_confirm"]
        
        platform_stats[platform]["count"] += 1
        platform_stats[platform]["total_hours"] += hours
        platform_stats[platform]["response_times"].append(hours)
        
        if platform_stats[platform]["fastest"] is None or hours < platform_stats[platform]["fastest"]:
            platform_stats[platform]["fastest"] = hours
        
        if platform_stats[platform]["slowest"] is None or hours > platform_stats[platform]["slowest"]:
            platform_stats[platform]["slowest"] = hours
    
    # Calculate averages
    for platform, stats in platform_stats.items():
        if stats["count"] > 0:
            stats["avg_hours"] = stats["total_hours"] / stats["count"]
            stats["avg_days"] = stats["avg_hours"] / 24
    
    return dict(platform_stats)

def generate_performance_report(matched_data, platform_stats):
    """Generate comprehensive performance report"""
    print("\n" + "=" * 80)
    print("🎯 ATS PLATFORM PERFORMANCE REPORT")
    print("=" * 80)
    
    if not matched_data:
        print("\n❌ No matched timing data available")
        return
    
    # Overall stats
    total_matched = len(matched_data)
    all_times = [m["hours_to_confirm"] for m in matched_data]
    avg_time = sum(all_times) / len(all_times)
    fastest = min(all_times)
    slowest = max(all_times)
    
    print(f"\n📊 OVERALL STATISTICS")
    print("-" * 80)
    print(f"Total Matched: {total_matched}")
    print(f"Average Response Time: {avg_time:.1f} hours ({avg_time/24:.1f} days)")
    print(f"Fastest Response: {fastest:.1f} hours ({fastest/24:.1f} days)")
    print(f"Slowest Response: {slowest:.1f} hours ({slowest/24:.1f} days)")
    
    # Platform rankings
    print(f"\n🏆 PLATFORM RANKINGS (by average response time)")
    print("-" * 80)
    
    sorted_platforms = sorted(
        platform_stats.items(),
        key=lambda x: x[1]["avg_hours"]
    )
    
    for rank, (platform, stats) in enumerate(sorted_platforms, 1):
        if stats["count"] < 2:  # Skip platforms with only 1 data point
            continue
        
        print(f"\n{rank}. {platform}")
        print(f"   📧 Applications: {stats['count']}")
        print(f"   ⏱️  Avg Response: {stats['avg_hours']:.1f} hours ({stats['avg_days']:.1f} days)")
        print(f"   ⚡ Fastest: {stats['fastest']:.1f} hours")
        print(f"   🐌 Slowest: {stats['slowest']:.1f} hours")
        
        # Speed rating
        if stats["avg_hours"] < 2:
            rating = "🔥 INSTANT"
        elif stats["avg_hours"] < 24:
            rating = "✅ FAST"
        elif stats["avg_hours"] < 72:
            rating = "⏳ MODERATE"
        else:
            rating = "🐌 SLOW"
        
        print(f"   Rating: {rating}")
    
    # Response time distribution
    print(f"\n📊 RESPONSE TIME DISTRIBUTION")
    print("-" * 80)
    
    under_1hr = sum(1 for t in all_times if t < 1)
    under_24hr = sum(1 for t in all_times if t < 24)
    under_3days = sum(1 for t in all_times if t < 72)
    over_3days = sum(1 for t in all_times if t >= 72)
    
    print(f"  Under 1 hour:   {under_1hr:3} ({under_1hr/total_matched*100:.1f}%)")
    print(f"  Under 24 hours: {under_24hr:3} ({under_24hr/total_matched*100:.1f}%)")
    print(f"  Under 3 days:   {under_3days:3} ({under_3days/total_matched*100:.1f}%)")
    print(f"  Over 3 days:    {over_3days:3} ({over_3days/total_matched*100:.1f}%)")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 80)
    
    best_platforms = [p for p, s in sorted_platforms[:3] if s["count"] >= 2]
    if best_platforms:
        print(f"✅ Prioritize these platforms (fastest response):")
        for platform in best_platforms:
            stats = platform_stats[platform]
            print(f"   • {platform} - avg {stats['avg_hours']:.1f}h response")
    
    slow_platforms = [p for p, s in sorted_platforms[-3:] if s["count"] >= 2 and s["avg_hours"] > 48]
    if slow_platforms:
        print(f"\n⚠️  These platforms respond slowly:")
        for platform in slow_platforms:
            stats = platform_stats[platform]
            print(f"   • {platform} - avg {stats['avg_hours']:.1f}h response")
    
    # Save detailed data
    report_file = Path(__file__).parent / "ats_performance_report.json"
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "total_matched": total_matched,
        "overall_avg_hours": avg_time,
        "platform_stats": {k: {kk: vv for kk, vv in v.items() if kk != "response_times"} 
                          for k, v in platform_stats.items()},
        "matched_applications": matched_data[:50]  # First 50
    }
    
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n💾 Detailed report saved: {report_file}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("⏱️  ATS PLATFORM PERFORMANCE ANALYTICS")
    print("=" * 80)
    
    # Step 1: Analyze jobs with timing
    jobs = analyze_job_with_timing()
    
    # Step 2: Get Gmail confirmations with timing
    confirmations = get_gmail_confirmations_with_timing()
    
    # Step 3: Match and calculate timings
    matched_data = match_and_calculate_timings(jobs, confirmations)
    
    # Step 4: Analyze by platform
    platform_stats = analyze_by_platform(matched_data)
    
    # Step 5: Generate report
    generate_performance_report(matched_data, platform_stats)

if __name__ == "__main__":
    main()
