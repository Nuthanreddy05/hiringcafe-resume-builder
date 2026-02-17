"""
Configuration settings for the job scraper.
Adjust these values based on your needs.
"""
import os
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "jobs_output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_PATH = DATA_DIR / "jobs.db"

# =============================================================================
# SCRAPING SETTINGS
# =============================================================================
SCRAPING = {
    # Delays (in seconds) - BE POLITE!
    "min_delay_between_requests": 2,      # Minimum seconds between requests
    "max_delay_between_requests": 5,      # Maximum seconds between requests
    "page_load_timeout": 60,              # Timeout for page loads (seconds)
    "element_wait_timeout": 30,           # Timeout waiting for elements

    # Concurrency
    "max_concurrent_scrapers": 3,         # Max companies to scrape in parallel
    "max_jobs_per_company": 500,          # Safety limit per company

    # Retries
    "max_retries": 3,                     # Retry failed scrapes
    "retry_delay_base": 2,                # Base delay for exponential backoff

    # Browser settings
    "headless": True,                     # Run browser in headless mode
    "browser_type": "chromium",           # chromium, firefox, or webkit
}

# =============================================================================
# PROXY SETTINGS (Optional - for heavy scraping)
# =============================================================================
PROXY = {
    "enabled": False,                     # Set True to use proxies
    "rotation_strategy": "per_company",   # per_request, per_company, or per_domain
    "proxies": [
        # Add your proxies here:
        # "http://user:pass@proxy1.com:8080",
        # "http://user:pass@proxy2.com:8080",
    ],
    "test_url": "https://httpbin.org/ip", # URL to test proxy health
}

# =============================================================================
# H1B DETECTION SETTINGS
# =============================================================================
H1B_DETECTION = {
    # Keywords that STRONGLY indicate NO sponsorship
    "no_sponsor_keywords": [
        "must be authorized to work",
        "without sponsorship",
        "will not sponsor",
        "not sponsor",
        "no sponsorship",
        "cannot sponsor",
        "unable to sponsor",
        "u.s. citizen",
        "us citizen",
        "permanent resident only",
        "green card required",
        "security clearance required",  # Usually means US citizen only
    ],

    # Keywords that MIGHT indicate sponsorship available
    "sponsor_keywords": [
        "visa sponsorship available",
        "will sponsor",
        "sponsorship available",
        "h1b",
        "h-1b",
        "immigration support",
        "work visa",
    ],

    # Confidence thresholds
    "high_confidence_threshold": 0.8,
    "low_confidence_threshold": 0.3,
}

# =============================================================================
# JOB RELEVANCE FILTERS
# =============================================================================
JOB_FILTERS = {
    # Job titles that indicate tech roles (case-insensitive)
    "relevant_title_keywords": [
        "software", "engineer", "developer", "programming", "backend", "frontend",
        "full stack", "fullstack", "full-stack", "devops", "sre", "site reliability",
        "data scientist", "data engineer", "machine learning", "ml engineer",
        "ai engineer", "artificial intelligence", "deep learning",
        "data analyst", "business intelligence", "analytics",
        "cloud engineer", "infrastructure", "platform engineer",
        "security engineer", "cybersecurity", "application security",
        "mobile developer", "ios developer", "android developer",
        "qa engineer", "test engineer", "sdet", "automation engineer",
        "python", "java", "golang", "rust", "javascript", "typescript",
    ],

    # Job titles to EXCLUDE (not tech roles)
    "exclude_title_keywords": [
        "recruiter", "talent acquisition", "hr ", "human resources",
        "sales", "account executive", "account manager", "customer success",
        "marketing", "content writer", "copywriter", "graphic designer",
        "legal", "counsel", "attorney", "paralegal",
        "finance", "accountant", "controller", "bookkeeper",
        "office manager", "executive assistant", "receptionist",
    ],
}

# =============================================================================
# DEDUPLICATION SETTINGS
# =============================================================================
DEDUPLICATION = {
    "hash_fields": ["title", "company", "location", "description_preview"],
    "description_preview_length": 200,    # First N chars for hashing
    "similarity_threshold": 0.85,         # Jobs with >85% similarity = duplicate
    "grace_period_days": 3,               # Days before marking job as inactive
}

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================
OUTPUT = {
    "create_folders": True,               # Create folder per job for applications
    "include_job_description": True,      # Save full JD as text file
    "include_direct_link": True,          # Save apply link
    "daily_summary": True,                # Generate daily summary report
    "formats": ["json", "csv"],           # Output formats
}

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOGGING = {
    "level": "INFO",                      # DEBUG, INFO, WARNING, ERROR
    "file_logging": True,                 # Log to file
    "console_logging": True,              # Log to console
    "log_rotation_days": 30,              # Keep logs for N days
}

# =============================================================================
# ATS PLATFORM DETECTION
# =============================================================================
ATS_PATTERNS = {
    "greenhouse": [
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "/gh_jid=",
    ],
    "lever": [
        "jobs.lever.co",
        "lever.co/",
    ],
    "workday": [
        "myworkdayjobs.com",
        "wd1.myworkdayjobs.com",
        "wd3.myworkdayjobs.com",
        "wd5.myworkdayjobs.com",
    ],
    "ashby": [
        "jobs.ashbyhq.com",
        "ashbyhq.com",
    ],
    "bamboohr": [
        "bamboohr.com/careers",
    ],
    "smartrecruiters": [
        "jobs.smartrecruiters.com",
    ],
    "icims": [
        "careers-",
        "icims.com",
    ],
}

# =============================================================================
# USER AGENTS (Rotated to avoid detection)
# =============================================================================
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
