#!/usr/bin/env python3
"""
Staffing Agency Job Scraper & Processor
Targets direct agency portals (JobDiva, Bullhorn, etc.) for high-speed application generation.
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# Import core logic from existing script
import sys
sys.path.append(os.path.dirname(__file__))

# Import classes and functions from the main script
from job_auto_apply_internet import (
    Job, IterationResult, AuditLogger,
    ai_clean_jd, generate_resume_json_deepseek, render_resume_from_template,
    evaluate_resume_with_gemini, compile_latex_to_pdf, save_job_package,
    build_folder_name, trim_jd_smart, slugify,
    should_skip_job, ai_check_relevance,  # ADD MISSING FILTERS
    MAX_ITERATIONS, APPROVAL_THRESHOLD,  # ADD CONSTANTS
    DEEPSEEK_MODEL, GEMINI_MODEL
)

from openai import OpenAI
from google import genai

# ============================================================================
# Agency Scrapers
# ============================================================================

def login_to_jobdiva(page, username, password):
    """
    Login to JobDiva portal
    Returns: True if successful, False otherwise
    """
    try:
        print(f"🔐 Logging into JobDiva...")
        
        # Navigate to JobDiva portal (company-specific URL)
        portal_url = "https://www2.jobdiva.com/portal/?a=z1jdnwvsl6ckfah57w51w0ybh73vlo09791ws6svfl6o610e858y169jdhdqs4jb&compid=-1#/"
        page.goto(portal_url, wait_until="networkidle", timeout=60000)
        
        # Wait a bit for the page to fully load
        time.sleep(2)
        
        # Check if already logged in
        if "myjobs" in page.url.lower() or page.locator(".user-name, .user-profile").count() > 0:
            print(f"   ✓ Already logged in")
            return True
        
        # Look for login form (try multiple selectors)
        if page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i]").count() > 0:
            page.fill("input[type='email'], input[name='email'], input[placeholder*='email' i]", username)
            page.fill("input[type='password'], input[name='password']", password)
            
            # Click login button
            page.click("button[type='submit'], input[type='submit'], button:has-text('Sign In'), button:has-text('Log In')")
            
            # Wait for navigation
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(2)
            
            # Verify login success
            if "myjobs" in page.url.lower() or page.locator(".user-name, .user-profile, .dashboard").count() > 0:
                print(f"   ✓ Logged in successfully")
                return True
            else:
                print(f"   ⚠️ Login may have succeeded, continuing...")
                return True  # Optimistic - proceed anyway
        else:
            # No login form found, might already be at dashboard
            print(f"   ✓ No login required (already authenticated)")
            return True
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False

def parse_jobdiva_date(date_str):
    """
    Parse JobDiva date string to datetime
    Handles formats like: "2 days ago", "1 hour ago", "Feb 13, 2026"
    """
    from datetime import datetime, timedelta
    
    date_str = date_str.lower().strip()
    now = datetime.now()
    
    # Handle relative dates
    if "hour" in date_str or "minute" in date_str or "just now" in date_str:
        return now
    elif "day" in date_str:
        days_match = re.search(r'(\d+)\s*day', date_str)
        if days_match:
            days = int(days_match.group(1))
            return now - timedelta(days=days)
    elif "week" in date_str:
        weeks_match = re.search(r'(\d+)\s*week', date_str)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return now - timedelta(weeks=weeks)
    
    # Handle absolute dates (e.g., "Feb 13, 2026")
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except:
        pass
    
    # Default to now if parsing fails
    return now

def is_job_fresh(posted_date_str, hours=48):
    """
    Check if job was posted within last N hours
    """
    from datetime import datetime, timedelta
    
    posted_date = parse_jobdiva_date(posted_date_str)
    cutoff = datetime.now() - timedelta(hours=hours)
    return posted_date >= cutoff

# REPLACED BY UNIVERSAL AI EXTRACTOR

def ai_extract_job_details(raw_page_text, page_url, user_query, deepseek_client):
    """
    Universal AI Extractor: Converts raw page text into structured job data.
    Analyzes content for: Title, JD, Date, Email, Location, Compensation, and Semantic Relevance.
    """
    prompt = f"""You are a professional JOB DATA EXTRACTOR & MATCHING EXPERT. Your task is to analyze a job portal page and determine if it matches a candidate's goal.

**INPUTS:**
- **USER GOAL/QUERY:** "{user_query}"
- **PAGE URL:** {page_url} (May contain title/ID hints)
- **PAGE TEXT:** 
{raw_page_text[:12000]}  # Slightly more context

**EXTRACTION RULES:**
1. **TITLE**: Find the actual job title. Ignore UI noise. Use URL hints if available.
2. **DESCRIPTION**: Extract full cleaned JD. Keep requirements and stack.
4. **RECRUITER EMAIL & NAME**: Extract specific contact person's name and email if present.
5. **LOCATION & COMPENSATION**: Extract city/state and pay info.

**RELEVANCE & MATCHING RULES:**
- **IS_RELEVANT**: Evaluate if this role matches the USER GOAL. 
  - Be SEMANTIC, not literal. If the goal is "Software Engineer", an "AI Architect" or "Full Stack Developer" is a MATCH.
  - Reject only if the domain is truly wrong (Sales, HR, Marketing) or if the job is purely administrative.
- **BLOCKERS**: Skip if "Citizenship required", "Security Clearance required", or "Sponsorship not available".
- **EXPERIENCE_CAP**: 6+ years is a SKIP. 0-5 years is OK. (The candidate has ~5 years of experience).
- **SENIORITY**: Mid-level or Lead roles are OK if they fit the 5-year range. Skip "Architect" or "Staff" if they require 10+ years.

**OUTPUT FORMAT (JSON ONLY):**
{{
  "title": "Clean Job Title",
  "description": "Full cleaned JD text",
  "posted_date": "Date or 'Unknown'",
  "recruiter_name": "Recruiter Name or null",
  "recruiter_email": "Email or null",
  "location": "Job location",
  "compensation": "Salary info or null",
  "is_relevant": true/false,
  "relevance_reason": "Brief explanation of why it fits the goal",
  "blocking_issue": null or "citizenship" or "clearance" or "experience" or "domain"
}}"""

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse JSON
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
            
        import json
        extracted = json.loads(result)
        
        # Basic validation
        if not extracted.get("title") or extracted["title"].lower() in ["register with us", "jobdiva portal"]:
             extracted["title"] = "Unknown Job Title"
             
        return extracted
        
    except Exception as e:
        print(f"      ⚠️ Universal extraction failed: {e}")
        return {
            "title": "Extraction Failed",
            "description": raw_page_text[:1000],
            "posted_date": "Unknown",
            "is_relevant": True,
            "relevance_reason": f"AI error: {e}",
            "blocking_issue": None
        }

def scrape_jobdiva_authenticated(page, deepseek_client, query="Software Engineer", max_jobs=5, hours_limit=48):
    """
    Scrape jobs from authenticated JobDiva portal
    Follows portal navigation: Mitchell Martin IT -> Search Jobs -> Details
    """
    print(f"🔍 [JobDiva] Navigating portal to find jobs...")
    
    # Wait for page to be fully loaded
    time.sleep(3)
    
    try:
        # Step 1: Click on "Mitchell Martin Information Technology"
        print(f"   Step 1: Looking for 'Mitchell Martin Information Technology'...")
        it_category_selectors = [
            "text='Mitchell Martin Information Technology'",
            "text=/Mitchell Martin.*Information Technology/i",
            "a:has-text('Information Technology')",
            "button:has-text('Information Technology')",
            "*:has-text('Mitchell Martin Information Technology')"
        ]
        
        clicked = False
        for selector in it_category_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"   ✓ Found IT category, clicking...")
                    page.locator(selector).first.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(2)
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print(f"   ⚠️ Could not find IT category link, trying to proceed anyway...")
        
        # Step 2: Click "Search Jobs" button
        print(f"   Step 2: Looking for 'Search Jobs' button...")
        search_button_selectors = [
            "button:has-text('Search Jobs')",
            "text='Search Jobs'",
            "input[value='Search Jobs']",
            "a:has-text('Search')",
            "*:has-text('Search Jobs')"
        ]
        
        clicked = False
        for selector in search_button_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"   ✓ Found Search Jobs button, clicking...")
                    page.locator(selector).first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    time.sleep(5)  # Longer wait for job results to load
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print(f"   ⚠️ Could not find Search Jobs button, trying to extract from current page...")
        
    except Exception as e:
        print(f"   ⚠️ Navigation error: {e}, trying to extract from current page...")
    
    # Step 3: Extract job listings
    print(f"   Step 3: Extracting job listings...")
    job_links = []
    
    # Find all Details buttons on the page
    # We'll filter UI elements after clicking by checking page content
    details_buttons = page.locator("button:has-text('Details'), a:has-text('Details')").all()
    print(f"   ✓ Found {len(details_buttons)} Details buttons")
    
    if len(details_buttons) == 0:
        print(f"   ❌ No Details buttons found")
        return []
    
    # Click each Details button to get full job info
    for idx, details_btn in enumerate(details_buttons[:max_jobs * 2], 1):
        try:
            print(f"   Processing job {idx}...")
            
            # Click Details button directly
            details_btn.click(timeout=5000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            
            # Extract job info from details page
            page_text = page.locator("body").inner_text()
            lines = [l.strip() for l in page_text.split('\n') if l.strip()]
            
            # NEW: Universal AI Extraction Strategy
            # Use AI to get all details at once from raw page content
            print(f"      🤖 AI universal extraction...")
            extracted_data = ai_extract_job_details(page_text, page.url, query, deepseek_client)
            
            title = extracted_data.get("title", f"Job {idx}")
            jd_text = extracted_data.get("description", page_text)
            posted_date = extracted_data.get("posted_date", "Unknown")
            
            # Use AI relevance/blocker signals directly
            if not extracted_data.get("is_relevant", True):
                blocking_issue = extracted_data.get("blocking_issue", "domain")
                reason = extracted_data.get("relevance_reason", "Not relevant")
                print(f"      ⏩ SKIP: {reason} (issue: {blocking_issue})")
                page.go_back()
                time.sleep(1)
                continue

            print(f"      ✓ {title[:50]}...")
            print(f"      ✓ Date: {posted_date}")
            
            # Check freshness if date was found
            if posted_date != "Unknown" and not is_job_fresh(posted_date, hours_limit):
                print(f"      ⏩ SKIP: {title[:40]}... (old: {posted_date})")
                page.go_back()
                time.sleep(1)
                continue
            
            # Filter by query (title check)
            # Literal query match removed - AI now handles semantic matching
            
            job_url = page.url
            
            # Find Apply URL
            apply_url = job_url
            if page.locator("button:has-text('Apply'), a:has-text('Apply')").count() > 0:
                apply_el = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
                href = apply_el.get_attribute("href")
                if href:
                    apply_url = href if href.startswith("http") else f"https://www2.jobdiva.com{href}"
            
            job_links.append({
                "url": job_url,
                "title": title,
                "company": "Mitchell Martin",
                "posted_date": posted_date,
                "description": jd_text,
                "apply_url": apply_url,
                "recruiter_email": extracted_data.get("recruiter_email"),
                "recruiter_name": extracted_data.get("recruiter_name"),
                "location": extracted_data.get("location"),
                "compensation": extracted_data.get("compensation")
            })
            
            print(f"      ✓ Extracted {len(jd_text)} chars of JD")
            
            # Go back to list
            page.go_back()
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            
            if len(job_links) >= max_jobs:
                break
                
        except Exception as e:
            print(f"      ⚠️  Error processing job {idx}: {str(e)[:60]}")
            try:
                page.go_back(timeout=3000)
                time.sleep(1)
            except:
                pass
            continue
    
    return job_links



def scrape_mitchell_martin(context, query="Software", max_jobs=5):
    """Scrape mitchellmartin.com/jobs"""
    print(f"🔍 [Mitchell Martin] Searching for '{query}'...")
    page = context.new_page()
    url = f"https://www.mitchellmartin.com/?s={query}"
    page.goto(url, wait_until="networkidle")
    
    # Wait for posts to load (FIXED: use article.et_pb_post instead of article.post)
    page.wait_for_selector("article.et_pb_post", timeout=10000)
    
    posts = page.locator("article.et_pb_post").all()
    job_links = []
    
    for post in posts[:max_jobs]:
        try:
            title_el = post.locator("h2.entry-title a")
            title = title_el.inner_text().strip()
            link = title_el.get_attribute("href")
            
            # Extract date
            meta = post.locator("p.post-meta").inner_text()
            # Format usually: by | Feb 6, 2026
            date_match = re.search(r'\|\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})', meta)
            posted_date = date_match.group(1) if date_match else "Unknown"
            
            print(f"   found: {title} ({posted_date})")
            
            job_links.append({
                "url": link,
                "title": title,
                "company": "Mitchell Martin",
                "posted_date": posted_date
            })
        except Exception as e:
            print(f"   ⚠️ Error parsing post: {e}")
            
    page.close()
    return job_links


def fetch_agency_job_details(context, job_link_data):
    """Visit the job page and extract full JD + Apply URL"""
    url = job_link_data["url"]
    print(f"📖 Fetching JD: {url}")
    
    page = context.new_page()
    page.goto(url, wait_until="networkidle")
    
    # JD is in .et_pb_post_content (Divi theme structure)
    jd_el = page.locator(".et_pb_post_content")
    jd_raw = jd_el.inner_text()
    
    # Find Apply URL (JobDiva)
    apply_btn = page.locator("a.et_pb_button")
    apply_url = ""
    for btn in apply_btn.all():
        href = btn.get_attribute("href")
        if "jobdiva" in href.lower() or "apply" in href.lower():
            apply_url = href
            break
            
    if not apply_url:
        apply_url = url # Fallback
        
    job = Job(
        url=url,
        title=job_link_data["title"],
        company=job_link_data["company"],
        description=jd_raw,
        apply_url=apply_url,
        recruiter_name=job_link_data.get("recruiter_name", ""),
        recruiter_email=job_link_data.get("recruiter_email", "")
    )
    
    page.close()
    return job


# ============================================================================
# Email Draft & Recruiter Functions
# ============================================================================

def extract_recruiter_email(jd_text):
    """
    Extract recruiter email from job description
    Returns: email string or None
    """
    # Common email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, jd_text)
    
    if emails:
        # Filter out common no-reply emails
        filtered = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'donotreply', 'no-reply'])]
        if filtered:
            return filtered[0]
    
    return None

def generate_recruiter_email_draft(deepseek_client, job, resume_data, recruiter_email):
    """
    Generate personalized email draft for recruiter outreach
    """
    # Extract key info from resume
    summary = resume_data.get('summary', '')
    experience_years = "5+"  # Default from resume
    key_skills = []
    
    if 'skills' in resume_data:
        skills_section = resume_data['skills']
        if isinstance(skills_section, dict):
            for category, skills_list in skills_section.items():
                if isinstance(skills_list, list):
                    # Extract string values only
                    for skill in skills_list[:3]:
                        if isinstance(skill, str):
                            key_skills.append(skill)
                        elif isinstance(skill, dict) and 'name' in skill:
                            key_skills.append(skill['name'])
        elif isinstance(skills_section, list):
            for skill in skills_section[:5]:
                if isinstance(skill, str):
                    key_skills.append(skill)
                elif isinstance(skill, dict) and 'name' in skill:
                    key_skills.append(skill['name'])
    
    key_skills_str = ", ".join(key_skills[:5]) if key_skills else "Python, SQL, AWS, Machine Learning"
    
    # Clean recruiter name for greeting (use first name if possible)
    recruiter_first_name = "there"
    if job.recruiter_name:
        parts = job.recruiter_name.split()
        if parts:
            recruiter_first_name = parts[0].replace(',', '').strip()

    prompt = f"""Generate a high-confidence, conversational outreach email to a recruiter at Mitchell Martin. You MUST follow this exact framework to produce an "Optimized Recruiter Email".

**INPUT DATA:**
- Position: {job.title}
- Agency: {job.company} (Mitchell Martin)
- Recruiter Name: {recruiter_first_name}
- Candidate Summary: {summary[:450]}
- Total Experience: {experience_years}+ years

**STRICTURE 3-PARAGRAPH FRAMEWORK:**

1. **Section 1: The Personal Initialization**
   - YOU MUST start the email exactly with: "Hi {recruiter_first_name}, how are you doing? This is Nuthan Reddy"
   - Next, mention: "I saw the {job.title} role you are representing at Mitchell Martin and it caught my eye."
   - Express genuine interest in the role directly.

2. **Section 2: The "Great Fit" Narrative**
   - Start with: "I feel that I am a great fit for this position because I have more than five years of experience and have successfully handled very similar challenges in my previous roles."
   - Follow with a conversational 3-4 sentence paragraph (NO BULLETS) that maps your "proven experience" (from the summary) to the needs of the {job.title} role. 
   - Tell a brief story of "what I've done till now" matching the JD.

3. **Section 3: The Closing & High-Confidence Invite**
   - State: "I've attached my resume below for your review. Since an email can't capture everything, I'm open for a brief call to discuss the details or project information in depth."
   - End with: "Looking forward to hearing from you. Best regards, Nuthan Reddy."

**CRITICAL RULES:**
- PROSE ONLY: Absolutely no bullet points or lists.
- HIGH CONFIDENCE: Do not use "maybe," "soft-sell," or "if not a fit." You ARE the perfect fit.
- NO PLACEHOLDERS: Generate the final text directly.
- TONE: Professional but warm and human.
"""

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        email_body = response.choices[0].message.content.strip()
        
        # Generate subject
        subject = f"Application for {job.title} - Nuthan Reddy"
        
        return {
            "subject": subject,
            "body": email_body,
            "to": recruiter_email or "recruiter@example.com"
        }
        
    except Exception as e:
        print(f"      ⚠️ Email generation failed: {e}")
        # Fallback template
        return {
            "subject": f"Application for {job.title} - Nuthan Reddy",
            "body": f"""Dear {job.recruiter_name or 'Recruiter'},

            I was excited to discover the {job.title} role at {job.company}, as it aligns perfectly with my {experience_years} years of experience in software and data engineering.

            With expertise in {key_skills_str}, I've successfully delivered projects that improved system performance and data processing efficiency. My background in building scalable solutions makes me a strong fit for this position.

            My resume (NuthanReddy.pdf) is attached for your review. Would you be available for a brief call to discuss this opportunity?

            Best regards,
            Nuthan Reddy""",
            "to": recruiter_email or "recruiter@example.com"
        }

def create_gmail_draft(gmail_user, gmail_password, to_email, subject, body, pdf_path):
    """
    Create Gmail draft with resume attachment using IMAP
    """
    import imaplib
    import email
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    import base64
    
    try:
        # Remove spaces from app password
        gmail_password = gmail_password.replace(" ", "")
        
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_password)
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename='NuthanReddy.pdf')
                msg.attach(pdf_attachment)
        
        # Convert to RFC822 format and append to Drafts
        raw_message = msg.as_bytes()
        mail.append('[Gmail]/Drafts', '', imaplib.Time2Internaldate(time.time()), raw_message)
        
        mail.logout()
        return True
        
    except Exception as e:
        print(f"      ⚠️ Gmail draft creation failed: {e}")
        return False

def send_gmail_direct(gmail_user, gmail_password, to_email, subject, body, pdf_path):
    """
    Send Gmail directly with resume attachment using SMTP
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    
    try:
        # Remove spaces from app password
        gmail_password = gmail_password.replace(" ", "")
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename='NuthanReddy.pdf')
                msg.attach(pdf_attachment)
        
        # Send via SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
            
        return True
        
    except Exception as e:
        print(f"      ⚠️ Direct Gmail sending failed: {e}")
        return False


# ============================================================================
# Main Implementation
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Staffing Agency Job Pipeline")
    parser.add_argument("--agency", default="mitchell_martin", help="Agency to scrape (mitchell_martin or jobdiva)")
    parser.add_argument("--query", default="Software", help="Search query")
    parser.add_argument("--max_jobs", type=int, default=5, help="Max jobs to process")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--out_dir", default=str(Path.home() / "Desktop" / "staffing"), help="Output directory")
    parser.add_argument("--use-jobdiva", action="store_true", help="Use authenticated JobDiva portal instead of public sites")
    parser.add_argument("--hours-limit", type=int, default=48, help="Only process jobs posted within last N hours (default: 48)")
    parser.add_argument("--send-email", action="store_true", help="Directly send email instead of creating a draft")
    
    args = parser.parse_args()
    
    # Load environment
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val.strip('"').strip("'")
    
    # Validate API keys
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ ERROR: DEEPSEEK_API_KEY not set")
        return
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY not set")
        return
    
    # Clients
    deepseek_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Paths
    output_root = Path(args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    
    # Load Prompts (using existing versions)
    script_dir = Path(__file__).parent
    resume_prompt = (script_dir / "resume_json_prompt_v3.txt").read_text()
    evaluator_prompt = (script_dir / "resume_evaluator_prompt_v3.txt").read_text()
    template_path = str(script_dir / "resume_template.tex")
    base_resume_tex = (script_dir / "base_resume.tex").read_text()
    
    # Print configuration
    print("=" * 80)
    print("🚀 STAFFING AGENCY JOB APPLICATION AUTOMATION")
    print("=" * 80)
    print(f"Mode:           {'JobDiva Authenticated' if args.use_jobdiva or args.agency == 'jobdiva' else 'Public Scraper'}")
    print(f"Agency:         {args.agency}")
    print(f"Query:          {args.query}")
    print(f"Max jobs:       {args.max_jobs}")
    if args.use_jobdiva or args.agency == "jobdiva":
        print(f"Hours limit:    {args.hours_limit} hours")
    print(f"Output dir:     {output_root.resolve()}")
    print(f"Writer model:   {DEEPSEEK_MODEL}")
    print(f"Evaluator:      {GEMINI_MODEL}")
    print(f"Approval score: {APPROVAL_THRESHOLD}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print("=" * 80)

    processed = 0
    stats = {
        "total": 0,
        "skipped_domain": 0,
        "skipped_senior": 0,
        "skipped_duplicate": 0,
        "failed": 0,
        "submitted": 0
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        
        # Step 1: Collect Jobs
        if args.use_jobdiva or args.agency == "jobdiva":
            # Use authenticated JobDiva portal
            jobdiva_user = os.getenv("JOBDIVA_USERNAME")
            jobdiva_pass = os.getenv("JOBDIVA_PASSWORD")
            
            if not jobdiva_user or not jobdiva_pass:
                print("❌ ERROR: JOBDIVA_USERNAME and JOBDIVA_PASSWORD not set in .env")
                return
            
            # Login to JobDiva
            if not login_to_jobdiva(page, jobdiva_user, jobdiva_pass):
                print("❌ JobDiva login failed. Exiting.")
                return
            
            # Scrape authenticated jobs with 48-hour filter
            job_links = scrape_jobdiva_authenticated(page, deepseek_client, args.query, args.max_jobs, args.hours_limit)
            
        elif args.agency == "mitchell_martin":
            job_links = scrape_mitchell_martin(context, args.query, args.max_jobs)
        else:
            print(f"❌ Agency {args.agency} not implemented.")
            return

        print(f"\n📋 Found {len(job_links)} jobs\n")
        stats["total"] = len(job_links)

        # Step 2: Process
        for idx, job_data in enumerate(job_links, 1):
            print("=" * 80)
            print(f"🔍 JOB {idx}/{len(job_links)}")
            print("=" * 80)
            print(f"URL: {job_data['url']}")
            
            try:
                # Debug: print job_data keys
                print(f"   Job data keys: {list(job_data.keys())}")
                
                # For JobDiva jobs, we already have the description from Details page
                if 'description' in job_data and job_data['description']:
                    print(f"   ✓ Using JobDiva description from Details page ({len(job_data['description'])} chars)")
                    job = Job(
                        url=job_data['url'],
                        title=job_data['title'],
                        company=job_data['company'],
                        description=job_data['description'],
                        apply_url=job_data.get('apply_url', job_data['url']),
                        recruiter_name=job_data.get('recruiter_name', ""),
                        recruiter_email=job_data.get('recruiter_email', "")
                    )
                else:
                    # For Mitchell Martin and other agencies, fetch JD from job page
                    print(f"   Fetching JD from job page...")
                    job = fetch_agency_job_details(context, job_data)
                
                # FILTER 1: Check for hard blockers (citizenship, clearance, specialized fields)
                # TODO: Re-enable when should_skip_job function is defined
                # skip, reason = should_skip_job(job.title, job.description)
                # if skip:
                #     print(f"   {reason}")
                #     continue
                
                # Check duplication
                folder_name = build_folder_name(job)
                if (output_root / folder_name / "NuthanReddy.pdf").exists():
                    print(f"   ⏩ SKIPPING: {folder_name} already exists.")
                    stats["skipped_duplicate"] += 1
                    continue

                # JD Cleaning
                print(f"   ✂️  Trimming JD...")
                trimmed_jd = trim_jd_smart(job.description)
                print(f"   🤖 AI cleaning JD...")
                cleaned_jd = ai_clean_jd(trimmed_jd, deepseek_client)
                print(f"   ✓ Cleaned: {len(job.description)} -> {len(cleaned_jd)} chars")
                
                # Use enriched metadata from Universal AI Extractor (if available)
                recruiter_email = job_data.get("recruiter_email") if isinstance(job_data, dict) else None
                location = job_data.get("location") if isinstance(job_data, dict) else None
                compensation = job_data.get("compensation") if isinstance(job_data, dict) else None
                
                if location: print(f"   📍 Location: {location}")
                if compensation: print(f"   💰 Compensation: {compensation}")
                if recruiter_email: print(f"   📧 Recruiter Email: {recruiter_email}")

                # ============================================================
                # ENABLING RESUME GENERATION (Production Mode)
                # ============================================================
                print(f"   ✅ ALL FILTERS PASSED - Proceeding with Resume Generation")
                
                # ITERATIVE RESUME GENERATION (matching main pipeline)
                all_iterations = []
                best_iteration = None
                current_resume_json = None
                feedback = None
                
                for i in range(1, MAX_ITERATIONS + 1):
                    print(f"\n   ⚙️  Iteration {i}/{MAX_ITERATIONS}")
                    
                    try:
                        # Generate resume
                        resume_data = generate_resume_json_deepseek(
                            deepseek_client, 
                            base_resume_tex, 
                            resume_prompt, 
                            job, 
                            cleaned_jd, 
                            feedback,
                            current_resume_json
                        )
                        current_resume_json = resume_data
                        
                        # Render LaTeX
                        generated_latex = render_resume_from_template(template_path, resume_data)
                        print(f"      ✓ Rendered LaTeX")
                        
                        # Evaluate (Gemini)
                        score, feedback, approved = evaluate_resume_with_gemini(
                            gemini_client,
                            generated_latex,
                            job,
                            cleaned_jd,
                            evaluator_prompt,
                            None,  # trace_path (optional)
                            None   # audit_logger (optional)
                        )
                        print(f"      ⭐ Score: {score}/100")

                        iteration_result = IterationResult(
                            iteration=i,
                            resume_json=resume_data,
                            latex_content=generated_latex,
                            gemini_score=score,
                            gemini_feedback=feedback,
                            approved=approved
                        )
                        all_iterations.append(iteration_result)

                        if approved:
                            print(f"      ✅ APPROVED! Score: {score}")
                            best_iteration = iteration_result
                            break
                        else:
                            print(f"      ❌ Not approved. Score: {score}")
                            # Loop will continue
                            
                    except Exception as e:
                        print(f"      ❌ Iteration failed: {e}")
                        feedback = f"Error: {e}"
                        continue
                
                # Post-Loop Handling
                if not best_iteration and all_iterations:
                     best_iteration = max(all_iterations, key=lambda x: x.gemini_score)
                     print(f"   🏆 Using best iteration: score {best_iteration.gemini_score}")

                if best_iteration:
                    # Compile PDF
                    print(f"\n   🔨 Compiling LaTeX to PDF...")
                    pdf_path = compile_latex_to_pdf(best_iteration.latex_content, output_root, "NuthanReddy")
                    
                    if pdf_path:
                        # Save package
                        package_dir = save_job_package(
                            output_root, 
                            job, 
                            cleaned_jd, 
                            best_iteration, 
                            all_iterations, 
                            pdf_path
                        )
                        
                        # NEW: Generate Email Draft
                        print(f"\n   📧 Generating recruiter email draft...")
                        
                        # Use AI-extracted recruiter info if available
                        recruiter_email = job.recruiter_email
                        if not recruiter_email:
                            recruiter_email = extract_recruiter_email(job.description)
                        
                        if recruiter_email:
                            print(f"      ✓ Using recruiter email: {recruiter_email}")
                        else:
                            print(f"      ⚠️ No recruiter email found, using placeholder")
                            recruiter_email = "recruiter@example.com"
                        
                        # Generate email draft
                        email_draft = generate_recruiter_email_draft(
                            deepseek_client,
                            job,
                            best_iteration.resume_json,
                            recruiter_email
                        )
                        
                        # Save email draft to file
                        email_file = package_dir / "recruiter_email_draft.txt"
                        email_content = f"Subject: {email_draft['subject']}\n\nBody:\n{email_draft['body']}"
                        email_file.write_text(email_content)
                        print(f"      ✓ Saved: recruiter_email_draft.txt")
                        
                        # Send or Draft
                        gmail_user = os.getenv("GMAIL_USER")
                        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
                        
                        if gmail_user and gmail_password:
                            if args.send_email:
                                print(f"   � SENDING email directly to {email_draft['to']}...")
                                success = send_gmail_direct(gmail_user, gmail_password, email_draft['to'], email_draft['subject'], email_draft['body'], pdf_path)
                                if success:
                                    print(f"      ✅ Email SENT successfully!")
                                    stats["submitted"] += 1
                                else:
                                    print(f"      ❌ Email sending FAILED.")
                                    stats["failed"] += 1
                            else:
                                print(f"   📥 Creating Gmail draft for {email_draft['to']}...")
                                success = create_gmail_draft(gmail_user, gmail_password, email_draft['to'], email_draft['subject'], email_draft['body'], pdf_path)
                                if success:
                                    print(f"      ✅ Gmail draft created.")
                                    stats["submitted"] += 1
                                else:
                                    print(f"      ❌ Draft creation FAILED.")
                                    stats["failed"] += 1
                        else:
                            print(f"   ⚠️ Gmail credentials not found, skipping email/draft")
                            stats["failed"] += 1
                        
                        processed += 1
                    else:
                        print(f"   ❌ PDF compilation failed")
                        stats["failed"] += 1
                else:
                    print(f"   ❌ No valid iterations")
                    stats["failed"] += 1
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                stats["failed"] += 1
                import traceback
                traceback.print_exc()

        browser.close()
    
    # Final Summary Report
    print("\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY REPORT")
    print("=" * 80)
    print(f"Total Jobs Found (last {args.hours_limit}h): {stats['total']}")
    print(f"  - Skipped (Duplicate/Exist): {stats['skipped_duplicate']}")
    print(f"  - Skipped (Domain/Role Filter): {stats['skipped_domain'] + stats['skipped_senior']}")
    print(f"  - Failed during processing:   {stats['failed']}")
    print(f"  - Successfully Submitted:     {stats['submitted']}")
    print("=" * 80)
    if args.send_email:
        print("🚀 Status: FULLY AUTONOMOUS (Emails sent)")
    else:
        print("📂 Status: DRAFT MODE (Drafts created)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
