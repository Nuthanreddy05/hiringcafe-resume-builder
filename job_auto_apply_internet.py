#!/usr/bin/env python3
"""
HiringCafe Job Application Automation with DeepSeek + Gemini Dual-Model System

WORKFLOW:
1. Scrape jobs from HiringCafe search page
2. Click each job -> Navigate to career page -> Scrape full JD + apply URL
3. Trim JD to essential content
4. DeepSeek writes tailored resume
5. Gemini evaluates quality (0-100 score)
6. Iterate until approved (score >= 85) or max iterations (3)
7. Compile best LaTeX to PDF
8. Save package: <company>_<job_id>/NuthanReddy.pdf + metadata

Usage:
    export DEEPSEEK_API_KEY="sk-..."
    export GEMINI_API_KEY="AIzaSy..."
    
    python job_auto_apply.py \
      --start_url "https://hiring.cafe/?searchState=..." \
      --max_jobs 10 \
      --headless

Requirements:
    pip install playwright google-genai openai
    playwright install chromium
    brew install tectonic
"""

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import requests

from playwright.sync_api import sync_playwright, BrowserContext
from google import genai
from openai import OpenAI
# Removed: from job_auto_submit import submit_single_job (obsolete - using decoupled batch)
import jinja2



# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    def __init__(self, job_id: str, company: str, output_root: Path, enabled: bool = False):
        self.enabled = enabled
        if not enabled:
            return
            
        # Create clear audit folder structure
        clean_company = re.sub(r'[^\w\-]', '_', company).lower()
        self.audit_dir = output_root / "_AUDIT" / f"{clean_company}_{job_id}"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        print(f"   🔍 Audit Mode: Logging to {self.audit_dir}")

    def log(self, filename: str, content: str):
        """Save a step artifact to the audit folder"""
        if not self.enabled:
            return
        try:
            path = self.audit_dir / filename
            path.write_text(str(content), encoding="utf-8")
        except Exception as e:
            print(f"      ⚠️ Failed to save audit log {filename}: {e}")

# ============================================================================
# Configuration
# ============================================================================

DEEPSEEK_MODEL = "deepseek-chat"
GEMINI_MODEL = "gemini-2.5-pro"
MAX_ITERATIONS = 5
APPROVAL_THRESHOLD = 85


# ============================================================================
# Data Models
# ============================================================================


def extract_folder_info_with_ai(url: str, title: str) -> dict:
    """Use DeepSeek to extract clean company name and job ID"""
    import json
    from openai import OpenAI
    
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    
    prompt = f"""Extract folder components from job URL.
URL: {url}
Title: {title}

Return ONLY JSON: {{"company": "lowercase_name", "job_id": "clean_id"}}
Remove prefixes like R-, JR, REQ- from job_id."""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100
        )
        # Strip markdown code fences if present
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            # Remove ```json and ``` markers
            content = content.replace('```json', '').replace('```', '').strip()
        result = json.loads(content)
        return {"company": result.get("company", "unknown"), "job_id": result.get("job_id", "unknown")}
    except:
        import hashlib
        return {"company": "unknown", "job_id": hashlib.md5(url.encode()).hexdigest()[:8]}


@dataclass
class Job:
    """Job posting with metadata"""
    url: str
    title: str
    company: str
    description: str
    apply_url: str
    job_id: str = ""


import jinja2

@dataclass
class IterationResult:
    """Single resume generation attempt"""
    iteration: int
    resume_json: dict
    latex_content: str
    gemini_score: int
    gemini_feedback: str
    model_used: str = "deepseek"
    approved: bool = False


# ============================================================================
# Utility Functions
# ============================================================================

def check_sponsorship_viability(description: str) -> bool:
    """Returns False if job explicitly denies sponsorship."""
    description = description.lower()
    
    # Phrases that instantly disqualify
    # Phrases that instantly disqualify
    # Use Global Strict Patterns extended with local specifics if needed
    blocklist = CITIZENSHIP_PATTERNS + [
        "security clearance required",
        "active clearance",
        "polygraph",
        "US citizen", # Catch casual mentions
        "U.S. Citizen"
    ]
    
    for phrase in blocklist:
        # Check if phrase is regex (contains special chars) or just string
        # To be safe, treat all as regex or substring search
        # Since CITIZENSHIP_PATTERNS are regex, we MUST use re.search
        if re.search(phrase, description, re.IGNORECASE):
            return False
            
    return True


def trim_jd_smart(jd_text):
    """Section-based extraction with hard blocklists"""
    import re
    
    # HARD BLOCKLIST: Remove entire sections with these headings
    drop_sections = [
        # Company marketing
        r'about (us|the company|our company|freese|cognizant|google|wipro|bayer|starbucks|netjets|boston scientific|zynga|cassaday)',
        r'our (culture|mission|values|story)',
        r'why (work for|join)',
        r'we are (committed to|transforming|proud)',
        r'level up your career',
        r'founded in \d{4}',
        r'downloaded over.*billion',
        r'manages approximately.*billion',
        r'recognized for.*barron.*forbes',
        r'fastest growing compan',
        
        # Compensation & Benefits SECTIONS
        r'benefits:?\s*$', r'perks:?\s*$',
        r'what we offer( you)?:?',
        r'what.?s in it for you:?',
        r'compensation details?:?',
        r'salary description:?',
        r'how .* supports you',
        r'comprehensive benefits',
        r'world-class benefits',
        
        # Legal & Compliance
        r'equal employment opportunity', r'eeo policy', r'eeo statement',
        r'equal opportunity employer',
        r'e-verify', r'e verify',
        r'privacy policy', r'applicant privacy', r'do not sell',
        r'accommodations for applicants',
        r'drug/alcohol policy', r'recruitment fraud',
        r'without regard to race',
        r'arrest or conviction records',
        r'fair chance act',
        r'at-will position',
        r'right to modify.*compensation',
        r'position is for an existing vacancy',
        
        # Application UI
        r'apply (now|for this job|with indeed)',
        r'application form',
        r'save job', r'email job', r'create alert',
        r'first name\*', r'last name\*', r'resume/cv\*',
        r'indicates a required field',
        r'attach.*dropbox.*google drive',
        r'what is your expected salary',
        
        # Site chrome/navigation
        r'similar jobs', r'view all jobs', r'job alerts', r'follow us',
        r'powered by', r'recaptcha', r'©', r'all rights reserved',
        r'privacy policy.*terms of service',
        r'back to (all )?jobs', r'return to list',
        r'share this opening',
        
        # Screening/Other
        r'background screening.*clearinghouse',
        r'application deadline.*days',
        r'work arrangement:?.*hybrid',
        r'scam.*phishing'
    ]
    
    # KEEP SECTIONS: Priority extraction
    keep_sections = [
        r'responsibilities', r'what you.ll do', r'duties', r'how you.ll contribute',
        r'requirements', r'qualifications', r'minimum qualifications',
        r'preferred qualifications', r'preferred', r'nice to have',
        r'experience', r'education', r'skills', r'technical skills',
        r'what it takes', r'what you need', r'about you',
        r'tools', r'technologies', r'tech stack'
    ]
    
    # Split into lines
    lines = jd_text.split('\n')
    
    # Step 1: Remove sections with DROP headings
    filtered_lines = []
    skip_section = False
    skip_lines = 0
    
    for i, line in enumerate(lines):
        # Skip if in skip mode
        if skip_lines > 0:
            skip_lines -= 1
            continue
        
        line_lower = line.lower().strip()
        
        # Check if line is a DROP section heading
        is_drop_heading = any(re.search(pattern, line_lower) for pattern in drop_sections)
        
        if is_drop_heading:
            # Skip this line and next 3 (section content)
            skip_lines = 3
            skip_section = True
            continue
        
        # Reset skip if we hit a KEEP heading
        is_keep_heading = any(re.search(pattern, line_lower) for pattern in keep_sections)
        if is_keep_heading:
            skip_section = False
        
        # Keep line if not in skip mode
        if not skip_section:

            # Filter out inline junk (salary, benefits details, form fields)
            junk_patterns = [
                # Salary/Pay patterns (comprehensive)
                r'\$[0-9,]+\s*-\s*\$[0-9,]+',
                r'pay range.*\$[0-9,]+.*\$[0-9,]+.*per (year|hour)',
                r'salary.*\$[0-9,]+.*-.*\$[0-9,]+',
                r'minimum salary:.*\$',
                r'maximum salary:.*\$',
                r'anticipated compensation',
                r'compensation.*commensurate',
                r'expected to be between.*\$[0-9,]+',
                
                # Benefits details
                r'medical.*dental.*vision',
                r'401\(k\)',
                r'paid time off.*parental leave',
                r'employee benefits offered',
                r'annual bonus target',
                r'variable compensation',
                r'long-term incentives',
                r'subject to plan eligibility',
                r'total compensation.*may.*include',
                
                # Application form fields
                r'select\.\.\.',
                r'accepted file types:',
                r'autofill with',
            ]
            
            if any(re.search(pat, line_lower) for pat in junk_patterns):
                continue
            
            filtered_lines.append(line)

    
    # Step 2: Extract KEEP sections if they exist
    extracted = []
    in_keep_section = False
    
    for line in filtered_lines:
        line_lower = line.lower().strip()
        
        # Check if this is a KEEP section heading
        is_keep = any(re.search(pattern, line_lower) for pattern in keep_sections)
        
        if is_keep:
            in_keep_section = True
            extracted.append(line)
        elif in_keep_section:
            # Keep content under KEEP sections
            # Stop if we hit a DROP heading or empty section
            is_drop = any(re.search(pattern, line_lower) for pattern in drop_sections)
            if is_drop:
                in_keep_section = False
            elif len(line.strip()) > 20:  # Real content
                extracted.append(line)
    
    # If we extracted KEEP sections, use that; otherwise use filtered
    result_lines = extracted if extracted else filtered_lines
    
    # Step 3: Deduplicate repeated lines
    seen = set()
    deduped = []
    for line in result_lines:
        normalized = line.strip().lower()
        if normalized and normalized not in seen and len(line.strip()) > 15:
            seen.add(normalized)
            deduped.append(line)
    
    # Step 4: Final cleanup - remove obvious junk
    junk_keywords = ['copyright', '© 20', 'all rights reserved', 'powered by', 
                     'workday, inc', 'privacy policy', 'terms of service',
                     'follow us on', 'contact us', 'investor relations']
    
    final = []
    for line in deduped:
        line_lower = line.lower()
        if not any(kw in line_lower for kw in junk_keywords):
            final.append(line)
    
    trimmed = '\n'.join(final)
    return trimmed[:5000] if len(trimmed) > 5000 else trimmed

def slugify(s: str, max_len: int = 80) -> str:
    """Convert to filesystem-safe slug"""
    s = s.strip().lower()
    s = re.sub(r"[\s/|]+", "_", s)
    s = re.sub(r"[^a-z0-9_+-]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len]


def safe_text(s: str) -> str:
    """Normalize whitespace"""
    return re.sub(r"\s+", " ", s).strip()


def now_stamp() -> str:
    """Timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ============================================================================
# Job ID Extraction
# ============================================================================

def extract_job_id(text: str) -> str:
    """Extract Job ID or Requisition ID"""
    if not text:
        return ""
    patterns = [
        r"\bJob ID\s*:?\s*#?\s*([A-Za-z0-9_-]+)\b",
        r"\bRequisition\s+(?:ID|#)\s*:?\s*([A-Za-z0-9_-]+)\b",
        r"\bReq\.?\s*#?\s*:?\s*([A-Za-z0-9_-]+)\b",
        r"\bPosting\s+(?:ID|#)\s*:?\s*([A-Za-z0-9_-]+)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def extract_job_id_from_url(url: str) -> str:
    """Extract ID from URL path"""
    if not url:
        return ""
    # Try common patterns
    patterns = [
        r"/jobs?/(\d+)",
        r"/job/([A-Za-z0-9_-]+)",
        r"/careers?/(\d+)",
        r"/apply/(\d+)",
        r"/viewjob/([A-Za-z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    # Fallback: last segment
    return url.rstrip("/").split("/")[-1]


def build_job_id(job: Job) -> str:
    """Build job ID from multiple sources"""
    job_id = (
        extract_job_id(job.description) or
        extract_job_id(job.title) or
        extract_job_id_from_url(job.apply_url) or
        extract_job_id_from_url(job.url) or
        now_stamp()
    )
    return slugify(job_id)[:30]


def build_folder_name(job: Job) -> str:
    """Generate clean folder name using AI"""
    info = extract_folder_info_with_ai(job.apply_url, job.title)
    return f"{info['company']}_{info['job_id']}"


# ============================================================================
# Job Filtering
# ============================================================================

CLEARANCE_PATTERNS = [
    r"\bts/sci\b", r"\btop secret\b", r"\bsecret clearance\b",
    r"\bsecurity clearance\b", r"\bactive clearance\b", r"\bpolygraph\b",
    r"\bsci\b.*\beligibil", r"\bsensitive compartmented information\b",
]
SPECIALIZED_JOB_PATTERNS = [
    # Bioinformatics/Medical/Research
    r"\bbioinformatics\b", r"\bgenomics\b", r"\bcancer biology\b",
    # Hardware/Embedded/Physical Engineering
    r"\bembedded\s+software\b", r"\bfirmware\b",
    r"\bmechanical\s+engineer\b", r"\bcivil\s+engineer\b",
    r"\benvironmental\s+engineer\b", r"\bstructural\s+engineer\b",
    r"\bnuclear\s+engineer\b", r"\bprocurement\s+engineer\b",
    r"\bmanufacturing\s+engineer\b", r"\belectrical\s+engineer\b",
    r"\bcorrosion\b", r"\bpipeline\s+integrity\b",
    r"\bvhdl\b", r"\bverilog\b", r"\bfpga\b",
]

# Configuration
JOB_URL = 'https://hiring.cafe/?searchState=%7B%22dateFetchedPastNDays%22%3A2%2C%22sortBy%22%3A%22date%22%2C%22jobTitleQuery%22%3A%22%28%5C%22software+engineer%5C%22+OR+%5C%22software+developer%5C%22+OR+%5C%22software+development+engineer%5C%22+OR+%5C%22backend+engineer%5C%22+OR+%5C%22frontend+engineer%5C%22+OR+%5C%22front+end+engineer%5C%22+OR+%5C%22full+stack+engineer%5C%22+OR+%5C%22devops+engineer%5C%22++OR+%5C%22data+scientist%5C%22+OR+%5C%22data+engineer%5C%22+OR+%5C%22machine+learning+engineer%5C%22+OR+%5C%22ml+engineer%5C%22+OR+%5C%22ai+engineer%5C%22%29%22%2C%22securityClearances%22%3A%5B%22None%22%2C%22Other%22%5D%2C%22roleYoeRange%22%3A%5B0%2C4%5D%2C%22seniorityLevel%22%3A%5B%22No+Prior+Experience+Required%22%2C%22Entry+Level%22%2C%22Mid+Level%22%5D%2C%22commitmentTypes%22%3A%5B%22Full+Time%22%2C%22Part+Time%22%2C%22Contract%22%2C%22Temporary%22%2C%22Seasonal%22%2C%22Volunteer%22%5D%2C%22departments%22%3A%5B%22Engineering%22%2C%22Software+Development%22%2C%22Information+Technology%22%2C%22Data+and+Analytics%22%5D%2C%22usaGovPref%22%3A%22exclude%22%2C%22excludedIndustries%22%3A%5B%22educational+organizations%22%5D%2C%22isNonProfit%22%3A%22forprofit%22%2C%22roleTypes%22%3A%5B%22Individual+Contributor%22%5D%7D'

CITIZENSHIP_PATTERNS = [
    r"\bu\.?s\.?\s*citizen\b", r"\bus citizens?\s*only\b",
    r"\bcitizenship required\b", r"\bno sponsorship\b",
    r"\bno visa sponsorship\b",
    r"\bwithout\s+(?:company\s+)?sponsorship\b",
    r"\bwill not sponsor\b",
    r"\bnot eligible for(?:.*\b)?sponsorship\b",
    r"not able to offer.*sponsorship",
]

INDUSTRY_EXCLUSION_PATTERNS = [
    r"\bnatural gas\b", r"\boil\s*&\s*gas\b", r"\bpetroleum\b",
    r"\bbiotech(?:nology)?\b", r"\bpharmaceutical\b",
]


def should_skip_job(title: str, description: str) -> Tuple[bool, str]:
    """Check if job should be skipped"""
    txt = f"{title}\n{description}".lower()
    
    # Check for specialized jobs (bio/mechanical/embedded/civil)
    for pat in SPECIALIZED_JOB_PATTERNS:
        if re.search(pat, txt, re.IGNORECASE):
            return True, "⊗ SKIPPED: Specialized field (bio/mechanical/embedded/civil)"
            
    # Check for Industry Exclusions (Natural Gas, Biotech, etc)
    for pat in INDUSTRY_EXCLUSION_PATTERNS:
        if re.search(pat, txt, re.IGNORECASE):
            return True, f"⊗ SKIPPED: Excluded Industry ({pat})"
    
    for pat in CLEARANCE_PATTERNS:
        if re.search(pat, txt, re.IGNORECASE):
            return True, "Requires security clearance/polygraph"
    
    for pat in CITIZENSHIP_PATTERNS:
        if re.search(pat, txt, re.IGNORECASE):
            return True, "Citizenship/sponsorship restriction"
    
    return False, ""


# ============================================================================
# Description Cleaning & Trimming
# ============================================================================

def clean_description(raw: str) -> str:
    """Remove UI noise from scraped text"""
    if not raw:
        return ""
    
    lines = [safe_text(x) for x in raw.splitlines() if safe_text(x)]
    
    blacklist = [
        "hiringcafe", "switch to ai", "log in", "sign in", "save search",
        "clear filters", "show all jobs", "talent network", "cookie",
    ]
    
    lines = [x for x in lines if not any(b in x.lower() for b in blacklist) and len(x) > 2]
    
    # Remove consecutive duplicates
    deduped = []
    prev = None
    for x in lines:
        if x != prev:
            deduped.append(x)
        prev = x
    
    text = "\n".join(deduped)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def trim_job_description(text: str) -> str:
    """Trim JD to core content (responsibilities + qualifications)"""
    if not text:
        return ""
    
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    
    # Find start of real JD
    starts = [
        "responsibilities", "what you'll do", "what you will do",
        "required qualifications", "qualifications", "requirements",
        "about the role", "job description", "position overview",
    ]
    low = t.lower()
    start_idx = None
    for key in starts:
        i = low.find(key)
        if i != -1:
            start_idx = i
            break
    if start_idx:
        t = t[start_idx:]
    
    # Cut off boilerplate
    cutoffs = [
        "equal opportunity employer", "eoe", "disability/veterans",
        "benefits include", "benefits package", "we offer",
        "background check", "privacy notice", "pay transparency",
        "about company", "company overview", "all qualified applicants",
    ]
    low2 = t.lower()
    cut_idx = None
    for key in cutoffs:
        i = low2.find(key)
        if i != -1 and i > 1500:
            cut_idx = i
            break
    if cut_idx:
        t = t[:cut_idx]
    
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    
    # Cap at 6000 chars for token efficiency
    if len(t) > 8000:
        t = t[:8000] + "\n\n[TRIMMED FOR LENGTH]"
    
    return t


def normalize_tech_terms(text: str) -> str:
    """Fix common recruiter typos and normalize casing"""
    replacements = {
        r"\bjava script\b": "JavaScript",
        r"\breact[\s\.]?js\b": "React",
        r"\bnode[\s\.]?js\b": "Node.js",
        r"\bgit\b": "Git",
        r"\baws\b": "AWS",
        r"\bazur\b": "Azure", # Typos like 'Azur'
        r"\bkuber.*?s\b": "Kubernetes", # ubernetes
        r"\bdocker\b": "Docker",
        r"\bci\s*/\s*cd\b": "CI/CD",
        r"\bpostgres\b": "PostgreSQL",
    }
    for pat, rep in replacements.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    return text


def clean_jd_smart(text: str) -> str:
    """
    Smart cleaning to fix typos and formatting.
    SOFT SKILLS ARE PRESERVED (User Request).
    """
    if not text: return ""

    # 1. Normalize Typos
    text = normalize_tech_terms(text)

    # 2. Parentheses Cleaning (Remove ONLY examples)
    # Target: (e.g. x, y), (i.e. x), (such as x)
    # We use a non-greedy match inside parens
    text = re.sub(r"\((?:e\.g\.|i\.e\.|such as|including)\b.*?\)", "", text, flags=re.IGNORECASE)

    # 3. Smart Line Filtering
    lines = text.splitlines()
    out_lines = []
    
    # Soft skill triggers
    soft_triggers = [
        "communication", "interpersonal", "organizational", "detail oriented",
        "team player", "self-starter", "motivated", "fast-paced", "written and verbal",
    ]
    
    # Tech keywords to SAVE a line (if found in a soft skill line)
    tech_saviors = [
        "Agile", "Scrum", "Jira", "SDLC", "AWS", "Azure", "GCP", "Python", 
        "Java", "React", "Angular", "API", "SQL", "NoSQL", "Git", "CI/CD",
        "Docker", "Kubernetes", "Linux", "TDD", "OOP"
    ]
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            out_lines.append(line)
            continue
            
        # Check if line is "Soft Skill" heavy
        is_soft = any(trigger in line_clean.lower() for trigger in soft_triggers)
        
        if is_soft:
            # SAVIOR CHECK: Look for tech keywords (DISABLED: Keep all soft skills)
            # if any(tech in line_clean for tech in tech_saviors):
            #    saved = True
            saved = True # ALWAYS SAVE soft skills per user request
            
            # 2. Capital Letter Check (Simple Heuristic: Capitalized word > 2 chars in middle of sentence)
            # e.g. "Experience with React is good" -> React is cap.
            words = line_clean.split()
            if len(words) > 1:
                # check words starting from index 1 (skip first word "Strong", "Excellent")
                for w in words[1:]:
                    # Check if Title Case (and not just "I" or "A") and len > 2
                    if w[0].isupper() and len(w) > 2 and w.lower() not in ["excellent", "strong", "good", "proven", "ability"]:
                        saved = True
                        break
            
            if saved:
                out_lines.append(line) # Keep it, it has gems
            else:
                pass # Drop it, it's just fluff
        else:
            out_lines.append(line)
            
    return "\n".join(out_lines)


# ============================================================================
# Apply URL Resolution
# ============================================================================

def is_bad_apply_url(u: str) -> bool:
    """Check if URL is invalid"""
    if not u:
        return True
    u = u.strip().lower()
    return (
        u.startswith("mailto:") or
        u.startswith("javascript:") or
        "reddit.com" in u or
        "hiring.cafe" in u or
        "google.com/search" in u
    )


def score_apply_url(u: str) -> int:
    """Score URL likelihood of being real apply link"""
    if not u or is_bad_apply_url(u):
        return -10000
    
    u = u.strip().lower()
    score = 0
    
    # ATS providers get high score
    ats = [
        "greenhouse.io", "lever.co", "workday", "icims.com", "taleo.net",
        "smartrecruiters.com", "jobvite.com", "successfactors", "oraclecloud.com",
        "adp.com", "myworkdayjobs.com", "bamboohr.com",
    ]
    if any(k in u for k in ats):
        score += 100
    
    if any(k in u for k in ["careers", "/careers", "jobs", "/jobs", "apply", "/apply"]):
        score += 30
    
    if u.startswith("http"):
        score += 5
    
    return score


def resolve_apply_url_via_click(context: BrowserContext, job_url: str) -> str:
    """Click Apply button and capture final URL"""
    page = context.new_page()
    try:
        page.set_default_timeout(30000)
        page.goto(job_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Find Apply button/link
        selectors = [
            "a:has-text('Apply')", "button:has-text('Apply')",
            "a:has-text('Apply Now')", "button:has-text('Apply Now')",
            "a:has-text('Apply now')", "button:has-text('Apply now')",
            "a.apply-button", "button.apply-button",
        ]
        
        apply_el = None
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.count() > 0:
                apply_el = loc
                break
        
        if not apply_el:
            return ""
        
        # Try popup first
        try:
            with page.expect_popup(timeout=8000) as popup:
                apply_el.click()
            p2 = popup.value
            p2.wait_for_load_state("domcontentloaded")
            p2.wait_for_timeout(2000)
            final_url = p2.url
            p2.close()
            return final_url
        except Exception:
            pass
        
        # Try same-tab navigation
        try:
            with page.expect_navigation(timeout=12000):
                apply_el.click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            return page.url
        except Exception:
            return ""
    
    finally:
        try:
            page.close()
        except Exception:
            pass


# ============================================================================
# Full JD Scraping from Career Page
# ============================================================================

def scrape_full_jd_from_career_page(context: BrowserContext, career_url: str) -> str:
    """Scrape complete JD from career/ATS page"""
    if not career_url or is_bad_apply_url(career_url):
        return ""
    
    page = context.new_page()
    page.set_default_timeout(40000)
    
    def click_expand(text: str) -> bool:
        """Click expand/show more buttons"""
        for sel in [f"button:has-text('{text}')", f"a:has-text('{text}')"]:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=2000)
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                pass
        return False
    
    def collect_text() -> str:
        """Collect text from page and iframes"""
        texts = []
        
        # Main page
        try:
            texts.append(page.evaluate("() => document.body ? document.body.innerText : ''") or "")
        except Exception:
            pass
        
        try:
            texts.append(page.inner_text("body"))
        except Exception:
            pass
        
        # Iframes
        try:
            for fr in page.frames:
                if fr == page.main_frame:
                    continue
                try:
                    texts.append(fr.evaluate("() => document.body ? document.body.innerText : ''") or "")
                except Exception:
                    pass
        except Exception:
            pass
        
        return max(texts, key=len, default="")
    
    try:
        # Attempt to scrape career page directly
        # try:
        # page.wait_for_load_state("networkidle", timeout=12000)
        # except Exception:
        # pass
        
        # page.wait_for_timeout(2000)
        
        # Handle ADP-specific UI
        # if "workforcenow.adp.com" in career_url:
        # click_expand("V2")
        # click_expand("Simplify")
        
        # Expand hidden content
        for label in ["Show more", "Read more", "See more", "View more", "More", "Expand"]:
            click_expand(label)
        
        # Scroll to trigger lazy loading
        best = ""
        stable = 0
        for _ in range(15):
            try:
                page.mouse.wheel(0, 1500)
            except Exception:
                pass
            page.wait_for_timeout(500)
            
            current = collect_text()
            if len(current) > len(best):
                best = current
                stable = 0
            else:
                stable += 1
            
            if stable >= 3:
                break
        
        return clean_description(best)
    
    except Exception as e:
        print(f"      ✗ Career page scrape failed: {e}")
        return ""
    finally:
        try:
            page.close()
        except Exception:
            pass


# ============================================================================
# Job Scraping from HiringCafe
# ============================================================================

def collect_job_links(start_url: str, max_jobs: int, headless: bool = True) -> List[str]:
    """Collect job links from HiringCafe search page"""
    print(f"\n📋 Collecting job links from HiringCafe...")
    links = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(40000)
        
        page.goto(start_url, wait_until="domcontentloaded")
        print("   ⏳ Waiting for page to load...")
        time.sleep(3)
        
        # Scroll to load more jobs
        print("   ⏳ Scrolling to load all jobs...")
        for i in range(15):
            page.mouse.wheel(0, 2000)
            time.sleep(0.6)
        
        # Extract job links
        anchors = page.locator("a[href*='/viewjob/']")
        count = anchors.count()
        print(f"   ✓ Found {count} job links on page")
        
        for i in range(count):
            href = anchors.nth(i).get_attribute("href") or ""
            if "/viewjob/" not in href:
                continue
            if href.startswith("/"):
                href = "https://hiring.cafe" + href
            if href.startswith("https://hiring.cafe/viewjob/"):
                links.append(href)
        
        context.close()
        browser.close()
    
    # Deduplicate
    seen = set()
    unique = []
    for u in links:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    
    result = unique[:max_jobs]
    print(f"   ✓ Returning {len(result)} unique job links\n")
    return result


def fetch_job_from_hiringcafe(context: BrowserContext, job_url: str, deepseek_client: OpenAI) -> Optional[Job]:
    """
    1. Open HiringCafe viewjob page
    2. Click Apply -> Get career page URL
    3. Scrape full JD from career page
    4. Return Job with full JD + apply URL
    """
    page = context.new_page()
    page.set_default_timeout(35000)
    
    try:
        print(f"   📄 Opening: {job_url}")
        page.goto(job_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # 1. Scrape JD from HiringCafe (Safer)
        full_jd = ""
        try:
            main = page.locator("main").first
            if main.count() > 0:
                full_jd = clean_description(main.inner_text())
            else:
                full_jd = clean_description(page.inner_text("body"))
        except Exception:
            full_jd = ""
        
        print(f"      ✓ HiringCafe JD: {len(full_jd)} chars")

        # Extract title
        title = ""
        try:
            h1 = page.locator("h1").first
            if h1.count() > 0:
                title = safe_text(h1.inner_text())
        except Exception:
            pass
        if not title:
            title = safe_text(page.title())
        
        # Extract company
        company = ""
        try:
            candidates = page.locator("a").all_inner_texts()
            for t in candidates[:50]:
                t2 = safe_text(t)
                if not t2 or t2.lower() in ["hiringcafe", "apply", "view job", "back"]:
                    continue
                if 2 <= len(t2) <= 50 and not re.search(r"\b(remote|hybrid|onsite)\b", t2.lower()):
                    company = t2
                    break
        except Exception:
            pass
        
        # Extract from title if empty/generic
        if not company or company.lower() in ['join our community', 'unknowncompany']:
            if " at " in title:
                company = title.split(" at ")[-1].strip()
                if "(" in company:
                    company = company.split("(")[0].strip()
        
        if not company:
            company = "UnknownCompany"
        
        print(f"      📌 Title: {title}")
        print(f"      🏢 Company: {company}")
        
        # Resolve career page URL by clicking Apply
        apply_url = resolve_apply_url_via_click(context, job_url)
        
        if not apply_url or is_bad_apply_url(apply_url):
            print(f"      ⚠️  No valid apply URL found, falling back to scan")
            try:
                hrefs = page.locator("a[href]").evaluate_all("els => els.map(e => e.href)")
                scored = [(score_apply_url(h), h) for h in hrefs]
                scored.sort(reverse=True)
                if scored and scored[0][0] > 0:
                    apply_url = scored[0][1]
            except Exception:
                pass
        
        if not apply_url or is_bad_apply_url(apply_url):
            apply_url = job_url
        
        print(f"      🔗 Career page: {apply_url}")
        
        # We prefer HiringCafe JD to avoid bot detection on career page
        if not full_jd or len(full_jd) < 300:
             # Fallback: Scrape FULL JD from career page ONLY if needed
            print(f"      ⚠️  HiringCafe JD too short, scraping career page...")
            if apply_url != job_url and not is_bad_apply_url(apply_url):
                full_jd = scrape_full_jd_from_career_page(context, apply_url)
        
        if not full_jd:
            print(f"      ✗ Failed to extract JD")
            return None
        
        print(f"      ✓ Final JD: {len(full_jd)} chars")
        
        job = Job(
            url=job_url,
            title=title[:120],
            company=company[:80],
            description=full_jd,
            apply_url=apply_url,
        )
        
        
        # v18.0: SIMPLIFIED FEEDBACK LOOP
        # We removed the separate "Feasibility" and "Strategist" layers.
        # Logic is now handled entirely by the Writer Prompt + Strict Evaluator Feedback Loop.
        
        # Check if should skip (Legacy Relevance Check)
        rel_result = ai_check_relevance(full_jd, deepseek_client)
        is_relevant = rel_result.get("relevant", True)
        reason = rel_result.get("reason", "Unknown")
        # is_relevant = True
        # reason = "Forced for testing"
        if not is_relevant:
            print(f"   ⊗ SKIPPED: {reason}")
            return None
        
        return job
    
    except Exception as e:
        print(f"      ✗ Error fetching job: {e}")
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


# ============================================================================
# DeepSeek + Gemini Dual-Model System
# ============================================================================



def log_trace(path: Path, step_name: str, content: str):
    """Log detailed workflow step to file"""
    if not path: return
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n[{timestamp}] {step_name}\n{'='*80}\n{content}\n")

def ai_clean_jd(jd_text, deepseek_client):
    """
    Layer 1: Clean JD while preserving 100% of ATS-critical keywords
    
    STRATEGY:
    - ATS systems score resumes by counting keyword matches
    - We must preserve EVERY skill (hard + soft) for maximum ATS score
    - Remove only marketing fluff that adds no scoring value
    - Keep sponsorship mentions for Layer 2 to evaluate
    """
    
    prompt = f"""You are an ATS keyword extraction expert. Your job is to clean this job description while preserving EVERY keyword that an Applicant Tracking System would score.

**CRITICAL - PRESERVE 100% OF THESE:**

1. **HARD SKILLS** (Programming languages, frameworks, tools, technologies):
   Examples: Python, Java, AWS, Docker, React, SQL, MongoDB, Git, CI/CD, Kubernetes

2. **SOFT SKILLS** (ATS scores these heavily):
   - Communication: Written, Verbal, Active Listening, Presentation
   - Leadership: Mentoring, Coaching, Team Lead, Influence, Delegation
   - Collaboration: Cross-functional, Teamwork, Stakeholder Management
   - Problem-Solving: Analytical, Critical Thinking, Troubleshooting, Debugging
   - Adaptability: Fast-paced, Agile, Flexible, Growth Mindset
   - Organization: Time Management, Prioritization, Multi-tasking
   - Initiative: Self-starter, Proactive, Ownership, Accountability
   - Attention to Detail, Quality-focused, Process Improvement

3. **EXPERIENCE REQUIREMENTS:**
   - Years of experience (e.g., "3+ years", "5-7 years")
   - Education (Bachelor's, Master's, degree requirements)
   - Certifications (AWS Certified, PMP, etc.)

4. **JOB RESPONSIBILITIES:**
   - ALL duties and responsibilities
   - Day-to-day tasks
   - Project types

5. **QUALIFICATIONS:**
   - Required skills
   - Preferred/nice-to-have skills
   - Domain knowledge

6. **WORK CONTEXT** (Important for matching):
   - Work authorization/sponsorship mentions (keep verbatim - don't interpret)
   - Security clearance mentions
   - Travel requirements
   - Work location/remote policy

**REMOVE ONLY:**
- Company history/About Us marketing text
- "Why join us" / company culture fluff
- Office perks (free lunch, gym, happy hours)
- Detailed benefits descriptions (401k details, insurance plans)
- EEO statements (except work authorization sentences)
- Application instructions (how to apply)

**OUTPUT FORMAT:**
Return cleaned JD with structure:
[Any work authorization/sponsorship statements if present]

**Responsibilities:**
[Bullet list of all responsibilities]

**Required Skills/Tools/Languages:**
[Comprehensive list - hard AND soft skills]

**Preferred Qualifications:**
[Nice-to-have skills]

**Experience Requirements:**
[Years, education, certifications]

**Example Input:**
"About Us: We're a leading fintech company... [3 paragraphs]
Responsibilities: Build scalable APIs, collaborate with product teams, mentor junior developers...
Requirements: 5+ years Python, AWS, strong communication skills, Bachelor's degree
Benefits: 401k matching, health insurance... [2 paragraphs]"

**Example Output:**
**Responsibilities:** Build scalable APIs, collaborate with product teams, mentor junior developers

**Required Skills:** Python, AWS, communication skills, collaboration, mentoring

**Experience Requirements:** 5+ years of experience, Bachelor's degree

---
Job Description to Clean:
{jd_text}"""

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"      ⚠️  AI cleaning failed: {e}")
        return jd_text


def ai_check_relevance(clean_jd, deepseek_client):
    """
    Layer 2: Filter out non-software/data jobs AND sponsorship blockers
    
    STRATEGY:
    - Only process jobs we can actually apply to (software/data domain)
    - Only process jobs that will sponsor (or don't mention restrictions)
    - Reduce wasted processing on irrelevant jobs
    - Two separate checks: domain fit + work authorization
    """
    
    prompt = f"""You are a job relevance filter for a SOFTWARE/DATA ENGINEERING candidate. Evaluate if this job is relevant and if there are any blocking work authorization issues.

**PART 1: DOMAIN RELEVANCE CHECK**

✅ **KEEP these jobs (Software/Data domains):**
- Software Engineering: Backend, Frontend, Full-stack, Mobile, Web
- Data Engineering: ETL/ELT, Data Pipelines, Data Warehousing
- DevOps/SRE/Platform Engineering: CI/CD, Cloud Infrastructure, Kubernetes
- Machine Learning/AI Engineering: ML Models, NLP, Computer Vision
- Cloud Engineering: AWS, Azure, GCP architecture and services
- API Development: REST, GraphQL, Microservices
- Database Engineering: SQL, NoSQL, Database Administration
- QA/Test Automation: Test frameworks, automation engineering

ANY tech stack is acceptable: Python, Java, C#, JavaScript, Go, Rust, etc.

❌ **SKIP these jobs (Wrong domains):**
- Hardware/Embedded: Firmware, FPGA, Circuit Design, PCB
- Non-Software Engineering: Civil, Mechanical, Electrical, Chemical Engineering
- Pure Science: Research Scientist, Lab Technician (unless ML/Data Science)
- Energy/Resource Industries: Oil & Gas, Natural Gas, Petroleum operations
- Biotech/Pharma: Drug discovery, Clinical trials (unless software role)
- Manual Labor/Trades: Construction, Manufacturing Operations
- Sales/Marketing: Unless "Sales Engineer" or "Marketing Data Analyst"
- IT Support/Help Desk: Desktop support, Level 1 support (unless DevOps)

**PART 2: WORK AUTHORIZATION CHECK**

❌ **BLOCKING - SKIP if EXPLICITLY states:**
Hard blocks:
- "Sponsorship not available"
- "Will not sponsor" / "Cannot sponsor"
- "No visa sponsorship"
- "US Citizenship required" / "Must be US Citizen"
- "Must be authorized to work without sponsorship"
- "Green Card required"
- "Security clearance required" / "Active clearance required"
- "Polygraph required"
- "Graduation date after August 2025" / "Must graduate in 2026" / "Class of 2026" (SKIP FUTURE GRADS)

✅ **OK - KEEP if:**
- No mention of sponsorship/citizenship (MOST JOBS - this is fine!)
- "Sponsorship available" / "Will sponsor"
- Only mentions "work authorization" in EEO statement
- Only mentions "citizenship" in non-discrimination clause

**CRITICAL:** If there's NO mention of sponsorship at all, that means it's FINE. Absence of restriction = OK to apply.

**EXAMPLES:**

Example 1 - KEEP:
"We're seeking a Senior Software Engineer with 5+ years Python experience..."
[No sponsorship mention]
→ KEEP: Software domain + No restrictions mentioned

Example 2 - SKIP:
"Looking for Firmware Engineer... Security clearance required"
→ SKIP: Wrong domain (embedded) + Clearance required

Example 3 - SKIP:
"Data Engineer needed. US Citizenship required."
→ SKIP: Wrong domain but citizenship restriction

Example 4 - KEEP:
"Backend Engineer... We do not discriminate based on citizenship or national origin"
→ KEEP: Software domain + EEO statement is NOT a restriction

Example 5 - KEEP:
"Machine Learning Engineer... visa sponsorship available for qualified candidates"
→ KEEP: ML domain + Sponsorship available

---
Job Description to Evaluate:
{clean_jd}

**OUTPUT FORMAT (JSON):**
{{
  "relevant": true/false,
  "reason": "Brief explanation (e.g., 'Software engineering role with Python/AWS - relevant' or 'Embedded firmware role - wrong domain')",
  "blocking_issue": null or "citizenship" or "clearance" or "wrong_domain"
}}

Be very careful: Only mark blocking_issue if EXPLICITLY stated. If unsure, keep the job."""

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Clean markdown JSON block if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
                
            import json
            parsed = json.loads(result)
            
            # Determine if we should skip
            if not parsed.get("relevant", True):
                return {"relevant": False, "reason": parsed.get("reason", "Not relevant"), "blocking_issue": parsed.get("blocking_issue")}
            
            if parsed.get("blocking_issue"):
                 return {"relevant": False, "reason": f"Blocking issue: {parsed['blocking_issue']} - {parsed.get('reason', '')}", "blocking_issue": parsed.get("blocking_issue")}
                
            return {"relevant": True, "reason": parsed.get("reason", "Relevant and no restrictions")}
            
        except json.JSONDecodeError:
            # Fallback: if can't parse, be conservative and keep the job
            print(f"      ⚠️  Could not parse relevance JSON, keeping job by default")
            return {"relevant": True, "reason": "Could not parse response - keeping job"}
            
    except Exception as e:
        print(f"      ⚠️  Relevance check failed: {e}")
        return {"relevant": True, "reason": f"Check failed, keeping job: {e}"}




# v18.0: STRATEGY FUNCTIONS REMOVED
# The Strategy Logic is now embedded directly in the Writer Prompts and Evaluator Feedback Loop.
# This keeps the pipeline purely iterative.



def escape_latex_special_chars(text: str) -> str:
    """Escape LaTeX special characters AND convert Markdown bold to LaTeX.
    
    Strategy:
    1. Convert Markdown bold to LaTeX \textbf{...}
    2. Escape special characters (%, $, &, _, #) ONLY if they are not already escaped.
    """
    if not isinstance(text, str):
        return text

    if "**" in text:
        text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)

    # 1b. ALLOW raw \textbf{...} if AI outputs it (User Request)
    # We must ensure we don't escape the leading \ of \textbf
    # But we DO need to escape other backslashes. 
    # Current strategy: We escape all special chars, but use negative lookbehind for \.
    
    # 2. Escape special chars using Negative Lookbehind to avoid double-escaping
    # Values to escape: % $ & # _ { }
    # Note: excluding { } for now as they are used in \textbf{}
    
    chars_to_escape = ['%', '$', '&', '#', '_']
    for char in chars_to_escape:
        # Replace char with \char, BUT ONLY if it's not preceded by \
        # regex: (?<!\\)%
        pattern = f"(?<!\\\\){re.escape(char)}"
        text = re.sub(pattern, f"\\\\{char}", text)

    # Handle special cases
    # ^ -> \textasciicircum{}
    text = text.replace('^', '\\textasciicircum{}')
    # ~ -> \textasciitilde{} (be careful of URLs? Assuming text content)
    text = text.replace('~', '\\textasciitilde{}')
    
    # We DO NOT escape { } \ because we just added them for \textbf and we assume commands are valid.
    # If the user has literal { } they might break, but that's rare in resume content compared to % and $.
    
    return text

def recursive_escape(data):
    if isinstance(data, dict):
        return {k: recursive_escape(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_escape(v) for v in data]
    elif isinstance(data, str):
        return escape_latex_special_chars(data)
    else:
        return data

def apply_bolding_to_metrics(data):
    """
    Recursively wraps metrics (%, $) in \textbf{} for LaTeX.
    Expects input strings to be ALREADY escaped (e.g. 25\%).
    """
    if isinstance(data, dict):
        return {k: apply_bolding_to_metrics(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [apply_bolding_to_metrics(v) for v in data]
    elif isinstance(data, str):
        # Regex to find:
        # 1. Percentages: 25\% or 25.5\% (Note: recursive_escape adds \)
        # 2. Money: \$50K, \$100, \$1.5M
        # 3. Large Numbers: 10TB, 50GB (Optional, but user mentioned 10TB)
        # We target strict patterns to avoid false positives.
        
        # Pattern groups:
        # Group 1: Percentages (e.g. 25\% or 30\%)
        # Group 2: Money (e.g. \$50K)
        # Group 3: Data Sizes (e.g. 10TB) - Added per prompt example
        
        # Note: In regex, matching a Literal backslash requires checks.
        
        def bold_repl(match):
            val = match.group(0)
            # Avoid double bolding if AI already did it
            if "textbf" in val: return val
            
            # Additional check: If the match is inside an existing \textbf{...}, skip it.
            # This is hard with regex alone, but 'textbf' check above catches the immediate inner match.
            # If the input string is "\textbf{25\%}", the regex might match "25\%".
            # We need to rely on the fact that if we search recursively, we might hit it.
            
            return f"\\textbf{{{val}}}"

        # Improved Pattern:
        # We use a negative lookbehind/lookahead strategy or just simple exclusion
        # But for safety, let's keep it simple: If the string ALREADY has \textbf, do not touch it.
        if "\\textbf" in data:
            return data
            
        pattern = r'(\d+(?:\.\d+)?\\%)|(\\\$\d+(?:,\d+)*(?:\.\d+)?[KkMmBb]?)|(\d+(?:\.\d+)?[TGMgK]B)'
        
        return re.sub(pattern, bold_repl, data)
    else:
        return data

def render_resume_from_template(template_path: str, json_data: dict) -> str:
    """Render the Jinja2 LaTeX template with JSON data (Escaping LaTeX chars)"""
    try:
        # Pre-process JSON to escape chars
        safe_json = recursive_escape(json_data)
        
        # Apply Bolding Logic Programmatically (User Requirement: Percentage Pop)
        # RE-ENABLED: Fallback for when AI Writer output fails to include \textbf{}
        styled_json = apply_bolding_to_metrics(safe_json)
        # styled_json = safe_json
        
        env = jinja2.Environment(
            block_start_string='{%',
            block_end_string='%}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='((*',
            comment_end_string='*))',
            loader=jinja2.FileSystemLoader(os.path.dirname(template_path))
        )
        template = env.get_template(os.path.basename(template_path))
        return template.render(**styled_json)
    except Exception as e:
        raise RuntimeError(f"Template rendering failed: {e}")



def generate_resume_json_deepseek(
    deepseek_client: OpenAI,
    base_resume_json: str, # Passed as string of JSON
    resume_prompt: str,
    job: Job,
    cleaned_jd: str,
    trace_path: Optional[Path] = None,
    audit_logger: Optional['AuditLogger'] = None,
) -> dict:
    """Use DeepSeek to generate tailored resume CONTENT (JSON only)"""
    
    # [v2.0 Logic] Calculate Soft Skills Ratio
    soft_skills = ["communication", "collaboration", "teamwork", "leadership", "mentoring", "ownership", "problem-solving"]
    soft_count = sum(1 for s in soft_skills if s in cleaned_jd.lower())
    total_words = len(cleaned_jd.split())
    # Heuristic: Approximate keyword density
    soft_ratio = str(round(soft_count / (total_words * 0.05 + 1), 2)) # Normalized ratio
    
    prompt = f"""{resume_prompt}

JOB INFORMATION:
Title: {job.title}
Company: {job.company}
Soft Skills Ratio: {soft_ratio} (>0.1 suggests higher weight)

JOB DESCRIPTION (trimmed):
{cleaned_jd}

BASE RESUME JSON:
{base_resume_json}

### v17.0 STRATEGIC BLUEPRINT (EXECUTE THIS):
{json.dumps(job.strategy, indent=2) if hasattr(job, 'strategy') else "No Strategy Provided."}
"""

    if trace_path:
        log_trace(trace_path, "DeepSeek JSON GENERATION Prompt", prompt)
    
    if audit_logger:
        audit_logger.log("05_writer_prompt.txt", prompt)

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={ "type": "json_object" } # DeepSeek supports this
        )
        
        content = response.choices[0].message.content.strip()
        
        # Cleanup markdown if present
        if "```" in content:
             content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL | re.IGNORECASE)

        json_data = json.loads(content)
        
        if trace_path:
            log_trace(trace_path, "DeepSeek JSON GENERATION Output", json.dumps(json_data, indent=2))
        
        if audit_logger:
            audit_logger.log("06_generated_content.json", json.dumps(json_data, indent=2))
             
        return json_data
    
    except Exception as e:
        print(f"      ❌ DeepSeek Generation Failed: {e}")
        # Fallback: return empty dict or try to parse partial
        return {}


def evaluate_resume_with_gemini(
    gemini_client: genai.Client,
    resume_latex: str,
    job: Job,
    cleaned_jd: str,
    prompt_template: str,
    trace_path: Optional[Path] = None,
    audit_logger: Optional['AuditLogger'] = None,
) -> Tuple[int, str, bool]:
    """Use Gemini to evaluate resume quality and provide feedback"""
    
    # Inject dynamic values into template
    current_date = datetime.now().strftime("%B %Y")
    prompt = prompt_template.replace("{current_date}", current_date)
    
    # Construct the full prompt context
    full_prompt = f"""
{prompt}

*** RESUME TO EVALUATE (LaTeX Source) ***
{resume_latex}

*** JOB DESCRIPTION ***
{cleaned_jd}
"""

    try:
        if audit_logger:
            audit_logger.log("07_evaluation_prompt.md", full_prompt)
            
        print(f"      -> Sending to Gemini ({GEMINI_MODEL})...")
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.2, # Low temperature for strict evaluation
            )
        )
        
        evaluation_text = response.text
        
        if audit_logger:
            audit_logger.log("08_evaluation_raw_response.md", evaluation_text)


        # Parse JSON Response (v2.0 Evaluator)
        print(f"      🔍 RAW GEMINI RESPONSE: {evaluation_text[:200]}...")
        
        try:
            # Clean possible markdown code blocks
            clean_json = evaluation_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            
            parsed = json.loads(clean_json.strip())
            
            # v2.0 Logic: 'overall_score'
            score = parsed.get("overall_score")
            
            # Fallback: 'score'
            if score is None:
                score = parsed.get("score", 0)
                
            # Handle "85/100" strings
            if isinstance(score, str):
                if "/" in score:
                    score = int(score.split("/")[0])
                else:
                    score = int(float(score))
                    
            score = int(score) if score is not None else 0
            
            # Parse Status
            approved = score >= APPROVAL_THRESHOLD
            
            return score, evaluation_text, approved

        except json.JSONDecodeError:
            print(f"      ⚠️ JSON Decode Failed. Falling back to Regex.")
            # Fallback to Regex for safety
            score_match = re.search(r'"overall_score":\s*(\d+)', evaluation_text)
            if not score_match:
                score_match = re.search(r'"score":\s*(\d+)', evaluation_text)
            
            score = int(score_match.group(1)) if score_match else 0
            approved = score >= APPROVAL_THRESHOLD
            return score, evaluation_text, approved

        
    except Exception as e:
        print(f"      ❌ Gemini Evaluation Failed: {e}")
        return 0, f"Evaluation failed: {e}", False


# ============================================================================
# LaTeX Compilation
# ============================================================================

def sanitize_latex(tex: str) -> str:
    """Clean LaTeX to reduce compile errors"""
    if not tex:
        return tex
    
    # Keep only from \documentclass
    i = tex.find("\\documentclass")
    if i != -1:
        tex = tex[i:]
    
    # Escape unescaped ampersands (outside tabular)
    lines = tex.splitlines()
    out_lines = []
    in_tabular = False
    
    for line in lines:
        if re.search(r"\\begin\{(tabular|array|align)", line):
            in_tabular = True
        if re.search(r"\\end\{(tabular|array|align)", line):
            in_tabular = False
        
        if not in_tabular:
            line = re.sub(r"(?<!\\)&", r"\\&", line)
        
        out_lines.append(line)
    
    return "\n".join(out_lines)


def compile_latex_to_pdf(latex_content: str, output_dir: Path, output_name: str = "NuthanReddy") -> Optional[Path]:
    """Compile LaTeX to PDF using tectonic"""
    
    latex_content = sanitize_latex(latex_content)
    
    build_dir = output_dir / "_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    
    tex_file = build_dir / f"{output_name}.tex"
    tex_file.write_text(latex_content, encoding="utf-8")
    
    print(f"\n   🔨 Compiling LaTeX to PDF...")
    
    cmd = [
        "tectonic",
        "-X", "compile",
        "--untrusted",
        str(tex_file),
        "--outdir", str(build_dir),
        "--keep-logs",
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"      ✗ Compilation failed:")
            print(f"      STDERR: {result.stderr[:500]}")
            return None
        
        pdf_file = build_dir / f"{output_name}.pdf"
        if not pdf_file.exists():
            print(f"      ✗ PDF not found at {pdf_file}")
            return None
        
        print(f"      ✓ PDF compiled successfully")
        return pdf_file
    
    except subprocess.TimeoutExpired:
        print(f"      ✗ Compilation timeout")
        return None
    except Exception as e:
        print(f"      ✗ Compilation error: {e}")
        return None


# ============================================================================
# Package Saving
# ============================================================================

def save_job_package(
    output_root: Path,
    job: Job,
    cleaned_jd: str,
    best_iteration: IterationResult,
    all_iterations: List[IterationResult],
    pdf_path: Path,
) -> Path:
    """Save complete job application package"""
    
    folder_name = build_folder_name(job)
    package_dir = output_root / folder_name
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n   💾 Saving package to: {folder_name}/")
    
    # 1. Save JD
    (package_dir / "JD.txt").write_text(cleaned_jd, encoding="utf-8")
    
    # 2. Save apply URL
    (package_dir / "apply_url.txt").write_text(job.apply_url + "\n", encoding="utf-8")
    
    # 3. Save best resume LaTeX
    (package_dir / "resume.tex").write_text(best_iteration.latex_content, encoding="utf-8")
    
    # 4. Save meta.json (CRITICAL for Chrome Extension Sync)
    # This file matches what folder_reader.py expects, making the job instantly visible in the extension
    meta_content = {
        "company": job.company,
        "title": job.title,
        "job_url": job.url,
        "apply_url": job.apply_url,
        "resume_text": best_iteration.resume_json.get("summary", "")[:500], # Preview
        "status": "generated", # Initial status
        "created_at": str(datetime.now())
    }
    (package_dir / "meta.json").write_text(json.dumps(meta_content, indent=2), encoding="utf-8")
    print(f"      ✓ Synced to Chrome Extension (meta.json created)")

    # 5. Copy PDF as NuthanReddy.pdf
    final_pdf = package_dir / "NuthanReddy.pdf"
    final_pdf.write_bytes(pdf_path.read_bytes())
    
    # 5. Save metadata
    metadata = {
        "job_url": job.url,
        "apply_url": job.apply_url,
        "title": job.title,
        "company": job.company,
        "job_id": build_job_id(job),
        "scraped_at": datetime.now().isoformat(),
        "best_iteration": best_iteration.iteration,
        "best_score": best_iteration.gemini_score,
        "total_iterations": len(all_iterations),
        "models_used": {
            "writer": DEEPSEEK_MODEL,
            "evaluator": GEMINI_MODEL,
        }
    }
    (package_dir / "meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    # 6. Save all iterations log
    iterations_log = []
    for it in all_iterations:
        iterations_log.append({
            "iteration": it.iteration,
            "score": it.gemini_score,
            "feedback": it.gemini_feedback,
            "latex_length": len(it.latex_content),
        })
    (package_dir / "iterations.json").write_text(json.dumps(iterations_log, indent=2), encoding="utf-8")
    
    print(f"      ✓ Saved: JD.txt, apply_url.txt, resume.tex, NuthanReddy.pdf, meta.json, iterations.json")
    
    return package_dir


# ============================================================================
# Main Orchestration
# ============================================================================

def main_hiringcafe():
    parser = argparse.ArgumentParser(
        description="HiringCafe Job Application Automation with DeepSeek + Gemini"
    )
    import csv
    # job_aggregator is imported at top of file, no need to import here again if it was in lines 1-1400.
    # But just in case:
    try:
        import job_aggregator
    except ImportError:
        pass # Assuming unused if running scrape_full_jd logic inline

    parser.add_argument("--start_url", required=True, help="HiringCafe search URL with filters")
    parser.add_argument("--max_jobs", type=int, default=5, help="Maximum jobs to process")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--out_dir", default=str(Path.home() / "Desktop" / "Google Auto"), help="Output directory")
    parser.add_argument("--profile", default="profile.json", help="Path to profile.json for auto-submission")
    parser.add_argument("--base_resume", default="base_resume.tex", help="Base LaTeX resume template")
    parser.add_argument("--resume_prompt", default="resume_json_prompt_v3.txt", help="Resume customization instructions (JSON mode)")
    parser.add_argument("--evaluator_prompt", default="resume_evaluator_prompt_v3.txt", help="Evaluator instructions")
    parser.add_argument("--iteration_prompt", default="resume_iteration_prompt_v3.txt", help="Iteration instructions (JSON mode)")
    parser.add_argument("--resume_template", default="resume_template.tex", help="Jinja2 LaTeX template")
    parser.add_argument("--audit", action="store_true", help="Enable visual audit mode")
    
    args = parser.parse_args()
    
    # Load .env manually
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    try:
                        key, val = line.strip().split("=", 1)
                        os.environ[key] = val.strip("'").strip('"')
                    except: pass

    # Validate API keys
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ ERROR: DEEPSEEK_API_KEY not set")
        return
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY not set")
        return
    
    # Initialize API clients
    deepseek_client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    profile_path = Path(args.profile)
    if not profile_path.exists():
         print(f"❌ ERROR: Profile not found: {profile_path}")
         return
    
    with open(profile_path) as f:
        profile = json.load(f)

    # Load Files
    base_resume_path = Path(args.base_resume)
    resume_prompt_path = Path(args.resume_prompt)
    evaluator_prompt_path = Path(args.evaluator_prompt)
    template_path = str(Path(args.resume_template).resolve())
    
    if not base_resume_path.exists():
        print(f"❌ ERROR: Base resume not found: {base_resume_path}")
        return
        
    if not resume_prompt_path.exists():
        print(f"❌ ERROR: Resume prompt not found: {resume_prompt_path}")
        return

    if not evaluator_prompt_path.exists():
        print(f"❌ ERROR: Evaluator prompt not found: {evaluator_prompt_path}")
        return

    base_resume_tex = base_resume_path.read_text(encoding="utf-8")
    resume_prompt = resume_prompt_path.read_text(encoding="utf-8")
    evaluator_prompt = evaluator_prompt_path.read_text(encoding="utf-8")
    
    output_root = Path(args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    
    # Print configuration
    print("=" * 80)
    print("🚀 HIRINGCAFE JOB APPLICATION AUTOMATION")
    print("=" * 80)
    print(f"Start URL:      {args.start_url}")
    print(f"Max jobs:       {args.max_jobs}")
    print(f"Output dir:     {output_root.resolve()}")
    print(f"Writer model:   {DEEPSEEK_MODEL}")
    print(f"Evaluator:      {GEMINI_MODEL}")
    print(f"Approval score: {APPROVAL_THRESHOLD}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print(f"Headless:       {args.headless}")
    print(f"Evaluator Prompt: {args.evaluator_prompt}")
    print("=" * 80)
    
    # Step 1: Collect job links
    job_links = collect_job_links(args.start_url, args.max_jobs, args.headless)
    
    if not job_links:
        print("\n❌ No job links found. Check your HiringCafe URL.")
        return
    
    # [FIX] Reverse link order (Oldest -> Newest)
    job_links.reverse()
    
    processed = 0
    skipped = 0
    failed = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        
        for idx, job_url in enumerate(job_links, 1):
            print("\n" + "=" * 80)
            print(f"🔍 JOB {idx}/{len(job_links)}")
            print("=" * 80)
            print(f"URL: {job_url}")
            
            try:
                # Fetch job
                job = fetch_job_from_hiringcafe(context, job_url, deepseek_client)
                if not job:
                    skipped += 1
                    continue

                # Setup folders
                folder_name = build_folder_name(job)
                job_output_dir = output_root / folder_name
                job_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Check duplication
                if (job_output_dir / "NuthanReddy.pdf").exists():
                    print(f"   ⏩ SKIPPING: Already processed ({folder_name})")
                    processed += 1
                    continue

                trace_path = job_output_dir / "workflow_trace.txt"
                audit_logger = AuditLogger(job.job_id, job.company, output_root, args.audit)
                
                # Log Raw
                audit_logger.log("01_raw_scraped_data.json", json.dumps(job.__dict__, default=str, indent=2))
                audit_logger.log("02_extracted_jd_raw.txt", job.description)
                
                # Clean JD
                # Clean JD
                trimmed_jd = trim_job_description(job.description)
                trimmed_jd = clean_jd_smart(trimmed_jd)
                print(f"   ✂️  Trimmed JD: {len(trimmed_jd)} chars")

                print(f"   🤖 AI cleaning JD...")
                try:
                    cleaned_jd = ai_clean_jd(trimmed_jd, deepseek_client)
                    print(f"   ✓ Cleaned: {len(trimmed_jd)} -> {len(cleaned_jd)} chars")
                    audit_logger.log("03_jd_cleaning_report.md", f"BEFORE: {len(trimmed_jd)}\nAFTER: {len(cleaned_jd)}\n\n{cleaned_jd}")
                except Exception as e:
                    print(f"   ⚠️  AI cleaning failed: {e}")
                    cleaned_jd = trimmed_jd

                # Relevance check
                audit_logger.log("04_relevance.md", "Skipping explicit relevance check to ensure High Recall.")
                
                # Iteration Loop
                all_iterations = []
                best_iteration = None
                feedback = None 
                current_resume_json = {}

                for i in range(1, MAX_ITERATIONS + 1):
                    print(f"\n   ⚙️  Iteration {i}/{MAX_ITERATIONS}")
                    current_prompt = resume_prompt
                    
                    if feedback:
                        print(f"      Use previous draft + feedback")
                        
                        iteration_prompt_path = Path(args.iteration_prompt)
                        if iteration_prompt_path.exists():
                            # Load dynamic iteration prompt from file
                            base_iter_prompt = iteration_prompt_path.read_text(encoding="utf-8")
                            current_prompt = (
                                base_iter_prompt + 
                                "\n\n--- PREVIOUS DRAFT JSON ---\n" +
                                json.dumps(best_iteration['resume_data'] if best_iteration else current_resume_json, indent=2) +
                                "\n\n--- FEEDBACK ---\n" + 
                                str(feedback) + 
                                "\n\nINSTRUCTION: Refine based on feedback."
                            )
                        else:
                            # Fallback to legacy logic
                            current_prompt = (
                                resume_prompt + 
                                "\n\n--- PREVIOUS DRAFT JSON ---\n" +
                                json.dumps(best_iteration['resume_data'] if best_iteration else current_resume_json, indent=2) +
                                "\n\n--- FEEDBACK ---\n" + 
                                str(feedback) + 
                                "\n\nINSTRUCTION: Refine based on feedback."
                            )
                    
                    try:
                        # Generate JSON
                        resume_data = generate_resume_json_deepseek(
                            deepseek_client,
                            base_resume_tex, # Use base resume texture as context
                            current_prompt,
                            job,
                            cleaned_jd,
                            trace_path,
                            audit_logger
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
                            evaluator_prompt, # PASS TEMPLATE HERE
                            trace_path,
                            audit_logger
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
                    pdf_path = compile_latex_to_pdf(best_iteration.latex_content, output_root, "NuthanReddy")
                    if pdf_path:
                        save_job_package(output_root, job, cleaned_jd, best_iteration, all_iterations, pdf_path)
                        print(f"   ✅ Processed: {job.title}")
                        processed += 1
                        print("\n   🚀 Ready for Batch Execution")
                        print(f"      Run: python loader.py --source '{output_root}'")
                    else:
                        print("   ❌ PDF Compile failed")
                        failed += 1
                else:
                    print("   ❌ Failed to generate any valid resume")
                    failed += 1
                    
            except Exception as e:
                print(f"   ❌ Job failed: {e}")
                failed += 1
                continue
                
        context.close()
        browser.close()
    
    # Summary
    print(f"\n✅ Processed: {processed}, ❌ Failed: {failed}")

def main():
    import sys
    # Only using HiringCafe mode for consistency verification
    main_hiringcafe()

if __name__ == "__main__":
    main()
