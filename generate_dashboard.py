#!/usr/bin/env python3
"""
Job Application Dashboard Generator
Creates interactive HTML dashboard showing complete application analytics
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
import re

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
GMAIL_USER = os.getenv("GMAIL_USER", "")

def collect_all_data():
    """Collect all job and confirmation data with proper Gmail matching"""
    print("📊 Collecting application data...")
    
    jobs = []
    
    if not JOBS_DIR.exists():
        print(f"❌ Directory not found: {JOBS_DIR}")
        return []
    
    # Calculate cutoff date (30 days ago)
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=30)
    
    print(f"   Filtering to jobs from last 30 days (since {cutoff_date.strftime('%Y-%m-%d')})")
    
    # Collect all job folders
    for job_folder in JOBS_DIR.iterdir():
        if not job_folder.is_dir() or job_folder.name.startswith("_") or job_folder.name.startswith("."):
            continue
        
        created = datetime.fromtimestamp(job_folder.stat().st_mtime)
        
        # FILTER: Only include jobs from last 30 days
        if created < cutoff_date:
            continue
        
        job_data = {
            "folder": job_folder.name,
            "created": created
        }
        
        # Read meta.json
        meta_file = job_folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    job_data.update({
                        "company": meta.get("company", "Unknown"),
                        "title": meta.get("title", "Unknown"),
                        "apply_url": meta.get("apply_url", ""),
                        "scraped_at": meta.get("scraped_at", ""),
                        "discovered_at": meta.get("discovered_at", ""),
                        "freshness": meta.get("hiringcafe_freshness", ""),
                        "score": meta.get("best_score", 0),
                        "platform": detect_platform(meta.get("apply_url", ""))
                    })
            except:
                pass
        
        jobs.append(job_data)
    
    print(f"✅ Collected {len(jobs)} jobs from last 30 days")
    
    # Get Gmail confirmations AND interviews (FILTERED TO RECENT)
    print("📧 Checking Gmail for confirmations and interviews (last 30 days only)...")
    confirmations, interviews = get_gmail_data(cutoff_date)
    
    print(f"   Found {len(confirmations)} confirmations (recent)")
    print(f"   Found {len(interviews)} interview invitations (recent)")
    
    # Match confirmations to jobs
    matched_count = 0
    interview_count = 0
    
    for job in jobs:
        company = job.get("company", "").lower()
        company_clean = re.sub(r'[^a-z0-9]', '', company)
        
        job["confirmed"] = False
        job["interviewed"] = False
        job["confirmation_date"] = None
        job["interview_date"] = None
        
        # Check confirmations
        for conf_company, conf_data in confirmations.items():
            conf_clean = re.sub(r'[^a-z0-9]', '', conf_company.lower())
            
            # Fuzzy matching - if either contains the other
            if (company_clean in conf_clean or conf_clean in company_clean) and len(company_clean) > 3:
                job["confirmed"] = True
                job["confirmation_date"] = conf_data.get("date", "")
                matched_count += 1
                break
        
        # Check interviews
        for int_company, int_data in interviews.items():
            int_clean = re.sub(r'[^a-z0-9]', '', int_company.lower())
            
            if (company_clean in int_clean or int_clean in company_clean) and len(company_clean) > 3:
                job["interviewed"] = True
                job["interview_date"] = int_data.get("date", "")
                interview_count += 1
                break
    
    print(f"✅ Matched {matched_count} confirmations to recent jobs")
    print(f"✅ Matched {interview_count} interviews to recent jobs")
    
    return jobs

def get_gmail_data(cutoff_date=None):
    """Get confirmations and interview invitations from Gmail (optionally filtered by date)"""
    from gmail_helper import get_gmail_service
    import email
    from email.header import decode_header
    from email.utils import parsedate_to_datetime
    
    GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    
    confirmations = {}
    interviews = {}
    
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("   ⚠️  Gmail credentials not found, skipping email matching")
        return confirmations, interviews
    
    try:
        mail = get_gmail_service(GMAIL_USER, GMAIL_PASSWORD)
        if not mail:
            return confirmations, interviews
        
        mail.select("inbox")
        
        # Build search query with date filter if provided
        date_filter = ""
        if cutoff_date:
            # Gmail IMAP date format: DD-Mon-YYYY
            date_str = cutoff_date.strftime("%d-%b-%Y")
            date_filter = f' SINCE {date_str}'
        
        # Search for application confirmations
        confirmation_keywords = [
            'SUBJECT "application"',
            'SUBJECT "thank you"',
            'SUBJECT "received"',
            'SUBJECT "confirmation"'
        ]
        
        seen_ids = set()
        
        for keyword in confirmation_keywords:
            try:
                # Add date filter to search
                search_query = keyword + date_filter if date_filter else keyword
                status, messages = mail.search(None, search_query)
                
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
                                    
                                    try:
                                        email_date = parsedate_to_datetime(date_str)
                                        if email_date.tzinfo is not None:
                                            email_date = email_date.replace(tzinfo=None)
                                    except:
                                        email_date = None
                                    
                                    company = extract_company_from_email(sender, subject)
                                    
                                    if company and company.lower() not in confirmations:
                                        confirmations[company.lower()] = {
                                            "company": company,
                                            "subject": subject,
                                            "date": email_date
                                        }
                        except:
                            continue
            except:
                continue
        
        # Search for interview invitations
        interview_keywords = [
            'SUBJECT "interview"',
            'SUBJECT "schedule"',
            'SUBJECT "next steps"',
            'SUBJECT "phone screen"',
            'SUBJECT "technical interview"'
        ]
        
        seen_ids = set()
        
        for keyword in interview_keywords:
            try:
                # Add date filter to search
                search_query = keyword + date_filter if date_filter else keyword
                status, messages = mail.search(None, search_query)
                
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
                                    
                                    try:
                                        email_date = parsedate_to_datetime(date_str)
                                        if email_date.tzinfo is not None:
                                            email_date = email_date.replace(tzinfo=None)
                                    except:
                                        email_date = None
                                    
                                    company = extract_company_from_email(sender, subject)
                                    
                                    if company and company.lower() not in interviews:
                                        interviews[company.lower()] = {
                                            "company": company,
                                            "subject": subject,
                                            "date": email_date
                                        }
                        except:
                            continue
            except:
                continue
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"   ⚠️  Gmail error: {e}")
    
    return confirmations, interviews

def extract_company_from_email(sender, subject):
    """Extract company name from email sender or subject"""
    # Try sender domain first
    sender_lower = sender.lower()
    
    email_match = re.search(r'@([\w\-]+)\.', sender_lower)
    if email_match:
        domain = email_match.group(1)
        common = ['gmail', 'noreply', 'mail', 'greenhouse', 'lever', 'smartrecruiters', 
                  'icims', 'workday', 'recruiting', 'talent', 'hire', 'jobs']
        if domain not in common:
            return domain.replace('-', ' ').replace('_', ' ').title()
    
    # Try sender name
    name_match = re.search(r'^([^<@]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.lower() not in ['do not reply', 'noreply', 'no-reply']:
            # Clean up common patterns
            name = re.sub(r'\s+at\s+', ' ', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+\-.*$', '', name)
            return name.strip()
    
    return "Unknown"

def detect_platform(url):
    """Detect ATS platform from URL"""
    if not url:
        return "Unknown"
    
    url_lower = url.lower()
    platforms = {
        "Greenhouse": ["greenhouse"],
        "Lever": ["lever.co"],
        "Workday": ["myworkdayjobs", "workday"],
        "iCIMS": ["icims"],
        "SmartRecruiters": ["smartrecruiters"],
        "Taleo": ["taleo"],
        "Ashby": ["ashbyhq"],
        "BambooHR": ["bamboohr"],
        "Paylocity": ["paylocity"],
        "Oracle": ["oraclecloud"],
        "ADP": ["adp.com"],
    }
    
    for platform, keywords in platforms.items():
        if any(k in url_lower for k in keywords):
            return platform
    
    return "Custom/Direct"

def generate_dashboard_html(jobs):
    """Generate interactive HTML dashboard"""
    
    total_jobs = len(jobs)
    confirmed = sum(1 for j in jobs if j.get("confirmed"))
    interviewed = sum(1 for j in jobs if j.get("interviewed"))
    pending = total_jobs - confirmed
    
    # Stats
    platforms = Counter(j.get("platform", "Unknown") for j in jobs)
    companies = Counter(j.get("company", "Unknown") for j in jobs)
    
    # Timeline data
    jobs_by_date = defaultdict(int)
    for j in jobs:
        date = j.get("created").strftime("%Y-%m-%d") if j.get("created") else "Unknown"
        jobs_by_date[date] += 1
    
    # Top positions
    positions = Counter(j.get("title", "Unknown") for j in jobs)
    
    # Platform stats with confirmation rates
    platform_stats = defaultdict(lambda: {"total": 0, "confirmed": 0, "interviewed": 0})
    for j in jobs:
        platform = j.get("platform", "Unknown")
        platform_stats[platform]["total"] += 1
        if j.get("confirmed"):
            platform_stats[platform]["confirmed"] += 1
        if j.get("interviewed"):
            platform_stats[platform]["interviewed"] += 1
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Application Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-value {{
            font-size: 3rem;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-sub {{
            font-size: 0.85rem;
            color: #999;
            margin-top: 5px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .chart-card h3 {{
            margin-bottom: 20px;
            color: #333;
        }}
        
        .table-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: #f7f7f7;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        tr:hover {{
            background: #f9f9f9;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .status-interviewed {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .status-confirmed {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-pending {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .platform-tag {{
            display: inline-block;
            padding: 3px 10px;
            background: #e9ecef;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #495057;
        }}
        
        .score {{
            font-weight: bold;
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Job Application Dashboard</h1>
            <p class="subtitle">Complete Analytics & Tracking</p>
            <p class="subtitle" style="font-size: 0.9rem; margin-top: 5px;">
                Email: {GMAIL_USER if GMAIL_USER else 'Not configured'}
            </p>
        </header>
        
        <!-- Key Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Applications</div>
                <div class="stat-value">{total_jobs}</div>
                <div class="stat-sub">Jobs processed</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Interviews</div>
                <div class="stat-value" style="color: #17a2b8;">{interviewed}</div>
                <div class="stat-sub">{interviewed/total_jobs*100 if total_jobs else 0:.1f}% interview rate 🌟</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Confirmed</div>
                <div class="stat-value" style="color: #28a745;">{confirmed}</div>
                <div class="stat-sub">{confirmed/total_jobs*100 if total_jobs else 0:.1f}% response rate</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Pending</div>
                <div class="stat-value" style="color: #ffc107;">{pending}</div>
                <div class="stat-sub">{pending/total_jobs*100 if total_jobs else 0:.1f}% awaiting response</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">ATS Platforms</div>
                <div class="stat-value">{len(platforms)}</div>
                <div class="stat-sub">Different systems</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 Applications Over Time</h3>
                <canvas id="timelineChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3>🏢 Top ATS Platforms</h3>
                <canvas id="platformChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3>✅ Platform Performance</h3>
                <canvas id="performanceChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3>💼 Top Companies</h3>
                <canvas id="companyChart"></canvas>
            </div>
        </div>
        
        <!-- Detailed Table -->
        <div class="table-card">
            <h3>📋 All Applications</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Company</th>
                        <th>Position</th>
                        <th>Platform</th>
                        <th>Applied</th>
                        <th>Freshness</th>
                        <th>Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows
    sorted_jobs = sorted(jobs, key=lambda x: x.get("created", datetime.min), reverse=True)
    for idx, job in enumerate(sorted_jobs, 1):
        # Priority: Interviewed > Confirmed > Pending
        if job.get("interviewed"):
            status = "interviewed"
            status_text = "🌟 Interview"
        elif job.get("confirmed"):
            status = "confirmed"
            status_text = "✅ Confirmed"
        else:
            status = "pending"
            status_text = "⏳ Pending"
        
        applied_date = job.get("created").strftime("%b %d, %Y") if job.get("created") else "Unknown"
        freshness = job.get("freshness", "-")
        score = job.get("score", 0)
        
        html += f"""
                    <tr>
                        <td>{idx}</td>
                        <td><strong>{job.get('company', 'Unknown')}</strong></td>
                        <td>{job.get('title', 'Unknown')[:50]}</td>
                        <td><span class="platform-tag">{job.get('platform', 'Unknown')}</span></td>
                        <td>{applied_date}</td>
                        <td>{freshness}</td>
                        <td><span class="score">{score}</span></td>
                        <td><span class="status-badge status-{status}">{status_text}</span></td>
                    </tr>
"""
    
    # Close table and add charts JavaScript
    html += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
"""
    
    # Timeline Chart Data
    timeline_labels = sorted(jobs_by_date.keys())
    timeline_data = [jobs_by_date[label] for label in timeline_labels]
    
    html += f"""
        // Timeline Chart
        new Chart(document.getElementById('timelineChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timeline_labels)},
                datasets: [{{
                    label: 'Applications',
                    data: {json.dumps(timeline_data)},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
        
        // Platform Distribution Chart
        new Chart(document.getElementById('platformChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(platforms.keys())[:8])},
                datasets: [{{
                    data: {json.dumps([platforms[k] for k in list(platforms.keys())[:8]])},
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
                    ]
                }}]
            }},
            options: {{
                responsive: true
            }}
        }});
        
        // Platform Performance Chart
        new Chart(document.getElementById('performanceChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps([p for p in platform_stats.keys() if platform_stats[p]['total'] >= 2][:8])},
                datasets: [{{
                    label: 'Confirmed',
                    data: {json.dumps([platform_stats[p]['confirmed'] for p in platform_stats.keys() if platform_stats[p]['total'] >= 2][:8])},
                    backgroundColor: '#28a745'
                }}, {{
                    label: 'Pending',
                    data: {json.dumps([platform_stats[p]['total'] - platform_stats[p]['confirmed'] for p in platform_stats.keys() if platform_stats[p]['total'] >= 2][:8])},
                    backgroundColor: '#ffc107'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{ stacked: true }},
                    y: {{ stacked: true }}
                }}
            }}
        }});
        
        // Top Companies Chart
        new Chart(document.getElementById('companyChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps([c for c, _ in companies.most_common(10)])},
                datasets: [{{
                    label: 'Applications',
                    data: {json.dumps([count for _, count in companies.most_common(10)])},
                    backgroundColor: '#764ba2'
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html

def main():
    print("=" * 80)
    print("📊 JOB APPLICATION DASHBOARD GENERATOR")
    print("=" * 80)
    
    # Collect data
    jobs = collect_all_data()
    
    if not jobs:
        print("\n❌ No job data found")
        return
    
    # Generate dashboard
    print("\n🎨 Generating interactive dashboard...")
    html_content = generate_dashboard_html(jobs)
    
    # Save dashboard
    output_file = Path(__file__).parent / "job_dashboard.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard created: {output_file}")
    print(f"\n💡 Open in browser:")
    print(f"   open {output_file}")
    print(f"\n   or")
    print(f"   file://{output_file.absolute()}")
    
    # Auto-open in browser
    try:
        import webbrowser
        webbrowser.open(f"file://{output_file.absolute()}")
        print("\n🌐 Opening dashboard in browser...")
    except:
        pass

if __name__ == "__main__":
    main()
