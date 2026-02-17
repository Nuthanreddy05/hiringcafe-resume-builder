#!/usr/bin/env python3
"""
Multi-Slide Job Application Analytics Dashboard
Interactive slideshow with detailed analytics
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

JOBS_DIR = Path.home() / "Desktop" / "Google Auto"

def load_all_data():
    """Load all data sources"""
    
    # Load enhanced AI results
    enhanced_file = Path(__file__).parent / "ai_classified_emails_enhanced.json"
    ai_file = Path(__file__).parent / "ai_classified_emails.json"
    file_to_load = enhanced_file if enhanced_file.exists() else ai_file
    
    with open(file_to_load) as f:
        ai_data = json.load(f)
    
    # Load job folders
    jobs = []
    for folder in JOBS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        
        meta_file = folder / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    meta['folder_name'] = folder.name
                    meta['created_date'] = datetime.fromtimestamp(folder.stat().st_ctime).isoformat()
                    jobs.append(meta)
            except:
                pass
    
    return ai_data, jobs

def calculate_response_times(ai_data, jobs):
    """Calculate response times for confirmations and rejections"""
    
    response_data = {
        'confirmations': [],
        'rejections': []
    }
    
    # Map companies to applied dates
    company_apply_dates = {}
    for job in jobs:
        company = job.get('company', '').lower()
        created = job.get('created_date', '')
        if company and created:
            company_apply_dates[company] = created
    
    # Calculate confirmation response times
    for conf in ai_data.get('confirmations', []):
        company = conf.get('company', '').lower()
        conf_date = conf.get('date', '')
        
        if company in company_apply_dates:
            apply_date = datetime.fromisoformat(company_apply_dates[company])
            confirm_date = datetime.fromisoformat(conf_date)
            hours_diff = (confirm_date - apply_date).total_seconds() / 3600
            
            response_data['confirmations'].append({
                'company': conf.get('company'),
                'applied': apply_date.strftime('%Y-%m-%d'),
                'confirmed': confirm_date.strftime('%Y-%m-%d'),
                'hours': round(hours_diff, 1)
            })
    
    # Calculate rejection response times
    for rej in ai_data.get('rejections', []):
        company = rej.get('company', '').lower()
        rej_date = rej.get('date', '')
        
        if company in company_apply_dates:
            apply_date = datetime.fromisoformat(company_apply_dates[company])
            reject_date = datetime.fromisoformat(rej_date)
            hours_diff = (reject_date - apply_date).total_seconds() / 3600
            
            response_data['rejections'].append({
                'company': rej.get('company'),
                'applied': apply_date.strftime('%Y-%m-%d'),
                'rejected': reject_date.strftime('%Y-%m-%d'),
                'reason': rej.get('reason', ''),
                'hours': round(hours_diff, 1)
            })
    
    return response_data

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

def generate_html(ai_data, jobs, response_times):
    """Generate multi-slide dashboard HTML"""
    
    total = len(jobs)
    confirmed = len(ai_data['confirmations'])
    rejected = len(ai_data['rejections'])
    interviewed = len(ai_data['interviews'])
    pending = total - confirmed - rejected
    
    # Calculate ATS stats
    ats_stats = defaultdict(lambda: {'total': 0, 'confirmed': 0, 'rejected': 0, 'avg_confirm_hours': []})
    
    for job in jobs:
        platform = detect_platform(job.get('apply_url', ''))
        ats_stats[platform]['total'] += 1
    
    for conf in response_times['confirmations']:
        # Match to job to get platform
        for job in jobs:
            if conf['company'].lower() in job.get('company', '').lower():
                platform = detect_platform(job.get('apply_url', ''))
                ats_stats[platform]['confirmed'] += 1
                ats_stats[platform]['avg_confirm_hours'].append(conf['hours'])
                break
    
    for rej in response_times['rejections']:
        for job in jobs:
            if rej['company'].lower() in job.get('company', '').lower():
                platform = detect_platform(job.get('apply_url', ''))
                ats_stats[platform]['rejected'] += 1
                break
    
    # Get pending companies
    confirmed_companies = {c['company'].lower() for c in ai_data['confirmations']}
    rejected_companies = {r['company'].lower() for r in ai_data['rejections']}
    
    pending_jobs = []
    for job in jobs:
        company = job.get('company', '').lower()
        if company not in confirmed_companies and company not in rejected_companies:
            pending_jobs.append(job)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Application Analytics Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            overflow: hidden;
        }}
        
        .slideshow-container {{
            height: 100vh;
            position: relative;
        }}
        
        .slide {{
            display: none;
            height: 100vh;
            padding: 40px;
            overflow-y: auto;
        }}
        
        .slide.active {{
            display: block;
        }}
        
        .slide-header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        
        .slide-title {{
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .slide-subtitle {{
            font-size: 18px;
            opacity: 0.9;
        }}
        
        /* Navigation */
        .nav-container {{
            position: fixed;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 20px;
            z-index: 1000;
        }}
        
        .nav-btn {{
            background: rgba(255,255,255,0.9);
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .nav-btn:hover {{
            background: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .slide-indicator {{
            position: fixed;
            top: 30px;
            right: 40px;
            color: white;
            font-size: 20px;
            font-weight: 600;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .stat-number {{
            font-size: 72px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            font-size: 18px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Table Styles */
        .data-table {{
            background: white;
            border-radius: 20px;
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .table-title {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 20px;
            color: #1f2937;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #374151;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        tr:hover {{
            background: #f9fafb;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge-pending {{ background: #fef3c7; color: #92400e; }}
        .badge-interview {{ background: #fef08a; color: #854d0e; }}
        
        .total {{ color: #667eea; }}
        .confirmed {{ color: #10b981; }}
        .rejected {{ color: #ef4444; }}
        .interviewed {{ color: #f59e0b; }}
        .pending {{ color: #6b7280; }}
    </style>
</head>
<body>
    <div class="slideshow-container">
        <div class="slide-indicator">Slide <span id="current-slide">1</span> / 4</div>
        
        <!-- Slide 1: Overview -->
        <div class="slide active">
            <div class="slide-header">
                <h1 class="slide-title">📊 Application Overview</h1>
                <p class="slide-subtitle">Complete Statistics</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number total">{total}</div>
                    <div class="stat-label">Total Applied</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number confirmed">{confirmed}</div>
                    <div class="stat-label">Confirmed</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number rejected">{rejected}</div>
                    <div class="stat-label">Rejected</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number interviewed">{interviewed}</div>
                    <div class="stat-label">Interviews</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number pending">{pending}</div>
                    <div class="stat-label">Pending</div>
                </div>
            </div>
        </div>
        
        <!-- Slide 2: Pending Companies -->
        <div class="slide">
            <div class="slide-header">
                <h1 class="slide-title">⏳ Pending & Active</h1>
                <p class="slide-subtitle">Companies waiting for response • Interviews in progress</p>
            </div>
            
            <div class="data-table">
                <div class="table-title">Pending Companies ({len(pending_jobs)})</div>
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Position</th>
                            <th>Applied Date</th>
                            <th>Days Waiting</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_pending_rows(pending_jobs, ai_data['interviews'])}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Slide 3: Rejections -->
        <div class="slide">
            <div class="slide-header">
                <h1 class="slide-title">❌ Rejections Analysis</h1>
                <p class="slide-subtitle">Applied vs Rejected Timeline</p>
            </div>
            
            <div class="data-table">
                <div class="table-title">Rejection Timeline ({len(response_times['rejections'])})</div>
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Applied</th>
                            <th>Rejected</th>
                            <th>Response Time</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_rejection_rows(response_times['rejections'])}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Slide 4: ATS Performance -->
        <div class="slide">
            <div class="slide-header">
                <h1 class="slide-title">🏢 ATS Performance</h1>
                <p class="slide-subtitle">Platform approval rates & response times</p>
            </div>
            
            <div class="data-table">
                <div class="table-title">Platform Analytics</div>
                <table>
                    <thead>
                        <tr>
                            <th>Platform</th>
                            <th>Total Apps</th>
                            <th>Confirmed</th>
                            <th>Rejected</th>
                            <th>Confirm Rate</th>
                            <th>Avg Response</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_ats_rows(ats_stats)}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="nav-container">
            <button class="nav-btn" onclick="changeSlide(-1)">← Previous</button>
            <button class="nav-btn" onclick="changeSlide(1)">Next →</button>
        </div>
    </div>
    
    <script>
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        
        function showSlide(n) {{
            slides[currentSlide].classList.remove('active');
            currentSlide = (n + slides.length) % slides.length;
            slides[currentSlide].classList.add('active');
            document.getElementById('current-slide').textContent = currentSlide + 1;
        }}
        
        function changeSlide(direction) {{
            showSlide(currentSlide + direction);
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowLeft') changeSlide(-1);
            if (e.key === 'ArrowRight') changeSlide(1);
        }});
    </script>
</body>
</html>"""
    
    return html

def generate_pending_rows(pending_jobs, interviews):
    """Generate pending companies table rows"""
    interview_companies = {i['company'].lower() for i in interviews}
    
    rows = []
    for job in sorted(pending_jobs, key=lambda x: x.get('created_date', ''), reverse=True)[:50]:
        company = job.get('company', 'Unknown')
        title = job.get('title', 'N/A')
        created = job.get('created_date', '')
        
        if created:
            created_date = datetime.fromisoformat(created)
            days_waiting = (datetime.now() - created_date).days
            applied_str = created_date.strftime('%Y-%m-%d')
        else:
            days_waiting = 0
            applied_str = 'N/A'
        
        # Check if interview in progress
        if company.lower() in interview_companies:
            status = '<span class="status-badge badge-interview">🌟 Interview</span>'
        else:
            status = '<span class="status-badge badge-pending">⏳ Pending</span>'
        
        rows.append(f"""
            <tr>
                <td><strong>{company}</strong></td>
                <td>{title[:50]}</td>
                <td>{applied_str}</td>
                <td>{days_waiting} days</td>
                <td>{status}</td>
            </tr>
        """)
    
    return ''.join(rows)

def generate_rejection_rows(rejections):
    """Generate rejection table rows"""
    rows = []
    for rej in sorted(rejections, key=lambda x: x['rejected'], reverse=True)[:30]:
        hours = rej['hours']
        if hours < 24:
            response_time = f"{hours}h"
        else:
            response_time = f"{hours/24:.1f} days"
        
        rows.append(f"""
            <tr>
                <td><strong>{rej['company']}</strong></td>
                <td>{rej['applied']}</td>
                <td>{rej['rejected']}</td>
                <td>{response_time}</td>
                <td style="max-width: 300px">{rej.get('reason', '')[:80]}</td>
            </tr>
        """)
    
    return ''.join(rows)

def generate_ats_rows(ats_stats):
    """Generate ATS performance rows"""
    rows = []
    for platform, stats in sorted(ats_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        total = stats['total']
        confirmed = stats['confirmed']
        rejected = stats['rejected']
        
        confirm_rate = (confirmed / total * 100) if total > 0 else 0
        
        if stats['avg_confirm_hours']:
            avg_hours = sum(stats['avg_confirm_hours']) / len(stats['avg_confirm_hours'])
            if avg_hours < 24:
                avg_response = f"{avg_hours:.1f}h"
            else:
                avg_response = f"{avg_hours/24:.1f}d"
        else:
            avg_response = "N/A"
        
        rows.append(f"""
            <tr>
                <td><strong>{platform}</strong></td>
                <td>{total}</td>
                <td class="confirmed">{confirmed}</td>
                <td class="rejected">{rejected}</td>
                <td>{confirm_rate:.1f}%</td>
                <td>{avg_response}</td>
            </tr>
        """)
    
    return ''.join(rows)

def main():
    print("\n🎨 Generating Multi-Slide Dashboard...\n")
    
    # Load data
    ai_data, jobs = load_all_data()
    print(f"Loaded {len(jobs)} jobs and {sum(len(v) for v in ai_data.values())} emails")
    
    # Calculate response times
    response_times = calculate_response_times(ai_data, jobs)
    print(f"Calculated response times for {len(response_times['confirmations'])} confirmations and {len(response_times['rejections'])} rejections")
    
    # Generate HTML
    html = generate_html(ai_data, jobs, response_times)
    
    # Save
    output_file = Path(__file__).parent / "job_dashboard.html"
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Multi-slide dashboard created: {output_file}")
    print("\n📊 Dashboard includes:")
    print("   Slide 1: Overview stats")
    print("   Slide 2: Pending companies & interviews")
    print("   Slide 3: Rejection timeline")
    print("   Slide 4: ATS performance")
    print("\n💡 Use arrow keys or buttons to navigate!")
    print("=" * 60)

if __name__ == "__main__":
    main()
