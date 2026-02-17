# Job Scraper Architecture - Complete Execution Prompt

**Use this prompt in Antigravity Kit, Claude Code, or Cursor to build the complete system.**

---

## 🎯 MASTER PROMPT (Copy this entire section)

```
You are building a production-grade job scraper for H1B-sponsoring companies. Build the COMPLETE system following this architecture EXACTLY.

## PROJECT STRUCTURE
Create this exact folder structure:
```
job_scraper/
├── config/
│   ├── __init__.py
│   ├── settings.py           # All configuration constants
│   └── companies.json        # List of companies to scrape
├── scrapers/
│   ├── __init__.py
│   ├── base.py               # Abstract base scraper class
│   ├── greenhouse.py         # Greenhouse ATS scraper
│   ├── lever.py              # Lever ATS scraper
│   ├── workday.py            # Workday ATS scraper
│   ├── ashby.py              # Ashby ATS scraper
│   └── generic.py            # Fallback generic scraper
├── extractors/
│   ├── __init__.py
│   ├── date_finder.py        # Extract posting dates (JSON-LD, meta, text)
│   ├── h1b_detector.py       # Detect H1B sponsorship likelihood
│   ├── job_parser.py         # Parse job details from HTML
│   └── deduplicator.py       # Hash-based duplicate detection
├── stealth/
│   ├── __init__.py
│   ├── browser.py            # Stealth Playwright browser
│   └── fingerprint.py        # Anti-detection scripts
├── storage/
│   ├── __init__.py
│   ├── database.py           # SQLite operations
│   └── models.py             # Data models (Job, Company)
├── output/
│   ├── __init__.py
│   └── formatter.py          # Generate apply-ready output
├── run.py                    # Main CLI entry point
├── scheduler.py              # Background job scheduler
├── requirements.txt
└── README.md
```

## FILE 1: config/settings.py
```python
"""Configuration settings for the job scraper."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "jobs_output"

# Create directories
for d in [DATA_DIR, LOGS_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "jobs.db"

# Scraping settings
SCRAPING = {
    "min_delay": 2,
    "max_delay": 5,
    "page_timeout": 60,
    "max_concurrent": 3,
    "max_retries": 3,
    "headless": True,
}

# H1B keywords
H1B_NO_SPONSOR = [
    "must be authorized to work", "without sponsorship", "will not sponsor",
    "no sponsorship", "cannot sponsor", "u.s. citizen", "permanent resident only",
    "green card required", "security clearance required",
]
H1B_SPONSOR = [
    "visa sponsorship available", "will sponsor", "h1b", "h-1b", "immigration support",
]

# Job filter keywords
TECH_KEYWORDS = [
    "software", "engineer", "developer", "backend", "frontend", "full stack",
    "devops", "sre", "data scientist", "data engineer", "machine learning",
    "ml engineer", "ai engineer", "cloud engineer", "python", "java", "golang",
]

EXCLUDE_KEYWORDS = [
    "recruiter", "sales", "marketing", "hr ", "legal", "finance", "accountant",
]

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ATS detection patterns
ATS_PATTERNS = {
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
    "lever": ["jobs.lever.co", "lever.co"],
    "workday": ["myworkdayjobs.com"],
    "ashby": ["jobs.ashbyhq.com", "ashbyhq.com"],
}
```

## FILE 2: stealth/browser.py
Create a StealthBrowser class with:
- Playwright async browser with headless Chrome
- Random user agent rotation from USER_AGENTS list
- Random viewport size (1920±100 x 1080±50)
- Inject stealth JavaScript to mask:
  - navigator.webdriver = undefined
  - Fake chrome.runtime object
  - Fake plugins array (3-5 plugins)
  - Canvas fingerprint noise (add 0.01 random offset to fillText)
  - WebGL vendor/renderer masking ("Intel Inc.", "Intel Iris OpenGL Engine")
- Methods:
  - async start() - launch browser
  - async new_page() - create page with stealth headers
  - async goto(page, url) - navigate with random delay
  - async human_delay(min, max) - random sleep
  - async scroll_to_bottom(page) - load infinite scroll content
  - async close() - cleanup

## FILE 3: storage/database.py
SQLite database with these tables:

```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    careers_url TEXT NOT NULL,
    ats_type TEXT,
    priority INTEGER DEFAULT 5,
    h1b_sponsor BOOLEAN DEFAULT 1,
    last_scraped TIMESTAMP,
    active BOOLEAN DEFAULT 1
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    title TEXT NOT NULL,
    location TEXT,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    description TEXT,
    requirements TEXT,
    job_url TEXT UNIQUE,
    job_id TEXT,
    posted_date DATE,
    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    department TEXT,
    employment_type TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    remote_type TEXT,
    h1b_status TEXT,
    h1b_confidence REAL,
    h1b_snippet TEXT,
    content_hash TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_relevant BOOLEAN DEFAULT 1,
    match_score REAL
);

CREATE TABLE scrape_logs (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jobs_found INTEGER,
    jobs_new INTEGER,
    jobs_updated INTEGER,
    errors TEXT,
    duration_seconds REAL
);

CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_hash ON jobs(content_hash);
CREATE INDEX idx_jobs_posted ON jobs(posted_date);
```

Methods needed:
- save_company(company_data) -> id
- save_job(job_data) -> id (upsert by job_url)
- get_job_by_hash(hash) -> job or None
- get_companies_to_scrape() -> list of companies due for scraping
- mark_job_inactive(job_id)
- log_scrape(company_id, stats)

## FILE 4: extractors/date_finder.py
Extract posting date using 5-layer fallback:

```python
def find_posting_date(html: str, url: str) -> Optional[date]:
    """
    Try these sources in order:
    1. JSON-LD structured data: Look for <script type="application/ld+json">
       Parse JSON, find "datePosted" field
    2. Meta tags: <meta property="article:published_time">
       <meta name="date"> <meta name="publish-date">
    3. Data attributes: data-posted-date, data-publish-date, data-date
    4. Microdata: itemprop="datePosted"
    5. Text patterns: regex for "Posted: MM/DD/YYYY", "Posted X days ago",
       "X hours ago", common date formats

    Return parsed date or None if not found.
    """
```

## FILE 5: extractors/h1b_detector.py
Detect H1B sponsorship likelihood:

```python
def detect_h1b_status(description: str, company_h1b_history: bool = True) -> dict:
    """
    Returns:
    {
        "status": "sponsors" | "does_not_sponsor" | "unknown",
        "confidence": 0.0-1.0,
        "snippet": "matching text snippet",
        "reason": "why this classification"
    }

    Logic:
    1. Search for NO_SPONSOR keywords -> status="does_not_sponsor", high confidence
    2. Search for SPONSOR keywords -> status="sponsors", high confidence
    3. If company historically sponsors H1B -> status="unknown" but boost confidence
    4. Default -> status="unknown", low confidence
    """
```

## FILE 6: extractors/deduplicator.py
Hash-based deduplication:

```python
import hashlib

def generate_content_hash(job: dict) -> str:
    """
    Create SHA-256 hash from: title + company + location + first 200 chars of description
    Normalize: lowercase, strip whitespace, remove special chars
    """
    content = f"{job['title']}|{job['company']}|{job['location']}|{job['description'][:200]}"
    content = content.lower().strip()
    return hashlib.sha256(content.encode()).hexdigest()

def is_duplicate(new_hash: str, db) -> bool:
    """Check if hash exists in database."""
    return db.get_job_by_hash(new_hash) is not None

def calculate_similarity(text1: str, text2: str) -> float:
    """Jaccard similarity for detecting near-duplicates."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0
```

## FILE 7: scrapers/base.py
Abstract base class for all scrapers:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseScraper(ABC):
    def __init__(self, browser, company: dict):
        self.browser = browser
        self.company = company
        self.jobs = []

    @abstractmethod
    async def discover_job_urls(self) -> List[str]:
        """Find all job listing URLs from the careers page."""
        pass

    @abstractmethod
    async def scrape_job_page(self, url: str) -> Dict[str, Any]:
        """Extract job details from a single job page."""
        pass

    async def scrape_all(self) -> List[Dict]:
        """Main entry point: discover URLs then scrape each."""
        urls = await self.discover_job_urls()
        for url in urls:
            try:
                job = await self.scrape_job_page(url)
                if job:
                    self.jobs.append(job)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        return self.jobs
```

## FILE 8: scrapers/greenhouse.py
Greenhouse-specific scraper:

```python
class GreenhouseScraper(BaseScraper):
    """
    Greenhouse has a public API! Use it when possible:
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

    Returns JSON with all jobs including:
    - title, location.name, content (HTML description), updated_at

    Fallback to HTML scraping if API fails:
    - Job cards: div[data-job-id], .opening, .job-post
    - Title: .job-title, h3
    - Location: .location, .job-location
    - Link: a[data-job-id]
    """

    async def discover_job_urls(self) -> List[str]:
        # Try API first
        board_token = self.extract_board_token(self.company['careers_url'])
        if board_token:
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
            # Fetch JSON, return list of job URLs

        # Fallback to HTML
        # Navigate to careers page, find all job links

    async def scrape_job_page(self, url: str) -> Dict:
        # If using API, data is already available
        # If HTML, parse the job detail page
```

## FILE 9: scrapers/lever.py
Lever-specific scraper:

```python
class LeverScraper(BaseScraper):
    """
    Lever selectors:
    - Job cards: .posting, .posting-title
    - Title: .posting-title, h5
    - Location: .posting-categories .location, .workplaceTypes
    - Team: .posting-categories .team
    - Link: .posting-title a, .posting-apply a

    Lever pages are mostly static HTML, easy to scrape.
    """
```

## FILE 10: scrapers/workday.py
Workday-specific scraper (most complex):

```python
class WorkdayScraper(BaseScraper):
    """
    Workday is a heavy SPA. Challenges:
    - Dynamic IDs that change
    - Multiple domains (wd1, wd3, wd5.myworkdayjobs.com)
    - Requires waiting for specific elements

    Selectors (may vary):
    - Job cards: [data-automation-id="jobResults"] li
    - Title: [data-automation-id="jobTitle"]
    - Location: [data-automation-id="locations"]
    - Load more: [data-automation-id="loadMoreButton"]

    Strategy:
    1. Wait for job list to load (networkidle)
    2. Click "Load More" until no more jobs
    3. Extract all job links
    4. Visit each job page
    """
```

## FILE 11: scrapers/generic.py
Fallback generic scraper:

```python
class GenericScraper(BaseScraper):
    """
    Universal selectors to try:

    Job list containers:
    - [class*="job"], [class*="career"], [class*="position"], [class*="opening"]
    - ul.jobs, ol.jobs, div.jobs-list
    - [data-job], [data-position]

    Job titles:
    - h1, h2, h3, h4 with job-related classes
    - .job-title, .position-title, .role-title

    Locations:
    - .location, .job-location, [class*="location"]
    - Icons next to location (often has location icon before text)

    Links:
    - a[href*="/job"], a[href*="/career"], a[href*="/position"]
    - a[href*="/apply"]

    Strategy: Try each selector until one returns results.
    """
```

## FILE 12: extractors/job_parser.py
Parse job details from HTML:

```python
from bs4 import BeautifulSoup

def parse_job_html(html: str, url: str) -> dict:
    """
    Extract all job fields from HTML.

    Returns:
    {
        "title": str,
        "location": str,
        "location_city": str,
        "location_state": str,
        "location_country": str,
        "description": str,
        "requirements": str,
        "department": str,
        "employment_type": str,  # Full-time, Contract, etc.
        "salary_min": int,
        "salary_max": int,
        "remote_type": str,  # Remote, Hybrid, Onsite
        "job_url": str,
        "job_id": str,
    }
    """
    soup = BeautifulSoup(html, 'lxml')

    # Title: try multiple selectors
    title = None
    for sel in ['h1.job-title', 'h1', '.posting-title', '[data-automation-id="jobTitle"]']:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # Location: parse city, state, country
    # Description: main content area
    # Requirements: look for "Requirements", "Qualifications" sections
    # Remote: look for "Remote", "Hybrid", "On-site" keywords
    # Salary: regex for "$XXX,XXX - $XXX,XXX" patterns
```

## FILE 13: output/formatter.py
Generate apply-ready output:

```python
def create_job_folder(job: dict, output_dir: Path):
    """
    Create folder structure:
    output_dir/
    └── CompanyName_JobTitle_Date/
        ├── job_details.json       # All job data
        ├── job_description.txt    # Full JD text
        ├── apply_link.txt         # Direct application URL
        └── notes.txt              # Empty file for your notes
    """

def generate_daily_summary(jobs: list, output_dir: Path):
    """
    Create daily_summary_YYYY-MM-DD.md with:
    - Total jobs scraped
    - New jobs found
    - Jobs by company
    - Jobs by H1B status
    - Top matches by relevance score
    """

def export_to_csv(jobs: list, filepath: Path):
    """Export jobs to CSV for spreadsheet use."""
```

## FILE 14: run.py
Main CLI entry point:

```python
import asyncio
import argparse
from datetime import datetime

async def main():
    parser = argparse.ArgumentParser(description='Job Scraper')
    parser.add_argument('--mode', choices=['all', 'company', 'test'], default='all')
    parser.add_argument('--company', help='Single company name')
    parser.add_argument('--limit', type=int, help='Limit companies to scrape')
    parser.add_argument('--headless', type=bool, default=True)
    args = parser.parse_args()

    # Initialize database
    db = Database()

    # Get companies to scrape
    if args.mode == 'company':
        companies = [db.get_company_by_name(args.company)]
    else:
        companies = db.get_companies_to_scrape()
        if args.limit:
            companies = companies[:args.limit]

    # Initialize browser
    async with StealthBrowser(headless=args.headless) as browser:
        for company in companies:
            try:
                # Detect ATS type and get appropriate scraper
                scraper = get_scraper_for_company(company, browser)

                # Scrape all jobs
                jobs = await scraper.scrape_all()

                # Process each job
                for job in jobs:
                    # Check relevance
                    if not is_relevant_job(job):
                        continue

                    # Check H1B status
                    h1b = detect_h1b_status(job['description'])
                    job.update(h1b)

                    # Check duplicate
                    content_hash = generate_content_hash(job)
                    if is_duplicate(content_hash, db):
                        continue

                    # Extract posting date
                    job['posted_date'] = find_posting_date(job.get('html', ''), job['job_url'])

                    # Save to database
                    job['content_hash'] = content_hash
                    db.save_job(job)

                    # Create output folder
                    create_job_folder(job, OUTPUT_DIR)

                # Log scrape
                db.log_scrape(company['id'], {...stats...})

            except Exception as e:
                print(f"Error scraping {company['name']}: {e}")

    # Generate daily summary
    generate_daily_summary(...)

if __name__ == '__main__':
    asyncio.run(main())
```

## FILE 15: requirements.txt
```
playwright>=1.40.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
aiohttp>=3.9.0
python-dateutil>=2.8.0
```

## EXECUTION STEPS:
1. Create all files in the structure above
2. Run: pip install -r requirements.txt
3. Run: playwright install chromium
4. Add companies to config/companies.json
5. Run: python run.py --mode=test --limit=1
6. If test passes: python run.py --mode=all

## IMPORTANT IMPLEMENTATION NOTES:
1. Every async function must use try/except with logging
2. Add random delays (2-5 sec) between ALL requests
3. Rotate user agents for each new page
4. Always close browser on exit (use async context manager)
5. Save partial results - don't lose work if script crashes
6. Log everything - timestamps, URLs, errors, job counts

Build each file completely. Test after creating each scraper. Ask if anything is unclear.
```

---

## 📋 EXECUTION ORDER

When you paste this prompt, tell the agent to:

1. **First**: Create folder structure and `config/settings.py`
2. **Second**: Create `storage/database.py` with SQLite schema
3. **Third**: Create `stealth/browser.py` with all anti-detection
4. **Fourth**: Create extractors (`date_finder.py`, `h1b_detector.py`, `deduplicator.py`, `job_parser.py`)
5. **Fifth**: Create scrapers (`base.py`, `greenhouse.py`, `lever.py`, `workday.py`, `generic.py`)
6. **Sixth**: Create `output/formatter.py`
7. **Seventh**: Create `run.py` CLI
8. **Last**: Create `requirements.txt` and test

---

## 🔄 FOLLOW-UP PROMPTS

After initial build, use these prompts to iterate:

### To test a single company:
```
Run the scraper for Stripe only in test mode. Show me the output.
```

### To fix errors:
```
The scraper failed on [company] with error [error]. Fix the issue.
```

### To add more companies:
```
Add these 20 companies to companies.json: [list]
```

### To improve H1B detection:
```
The H1B detector is giving false positives. Add these patterns to the NO_SPONSOR list: [patterns]
```

### To add proxy support:
```
Add proxy rotation support using this proxy list: [proxies]
```

---

## 📊 VERIFICATION CHECKLIST

After the agent builds everything, verify:

- [ ] All files exist in correct locations
- [ ] `python run.py --help` shows CLI options
- [ ] Database tables created correctly
- [ ] Stealth browser passes bot detection test
- [ ] At least one company scrapes successfully
- [ ] Jobs saved to database
- [ ] Output folders created with job details

---

## 💡 TIPS FOR ANTIGRAVITY KIT

1. **Use `/create` workflow**: `/create job scraper system`
2. **Break into chunks**: If it's too big, split by module
3. **Test incrementally**: After each file, ask to test it
4. **Keep context**: Reference previous files when building new ones

---

**Total estimated tokens for full build: ~15,000-20,000**
**Time to build: 30-60 minutes with a good agent**
