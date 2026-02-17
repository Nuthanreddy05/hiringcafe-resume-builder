# Quick Start Prompt for Antigravity Kit

**Copy this ENTIRE prompt and paste into Antigravity Kit or Claude Code:**

---

```
Build a Python job scraper with these exact specifications:

## REQUIREMENTS
- Playwright for browser automation (stealth mode)
- SQLite for storage
- Async/await throughout
- CLI interface

## FOLDER STRUCTURE
```
job_scraper/
├── config/settings.py      # Configuration
├── config/companies.json   # Company list (20 sample companies)
├── stealth/browser.py      # Stealth Playwright browser
├── storage/database.py     # SQLite with companies, jobs, scrape_logs tables
├── extractors/
│   ├── date_finder.py      # Extract dates from JSON-LD, meta tags, text
│   ├── h1b_detector.py     # Detect visa sponsorship status
│   └── deduplicator.py     # SHA-256 content hashing
├── scrapers/
│   ├── base.py             # Abstract base scraper
│   ├── greenhouse.py       # boards-api.greenhouse.io API
│   ├── lever.py            # jobs.lever.co scraper
│   └── generic.py          # Fallback for custom sites
├── output/formatter.py     # Create job folders + CSV export
├── run.py                  # CLI: python run.py --mode=all
└── requirements.txt
```

## KEY FEATURES

### Stealth Browser (stealth/browser.py)
- Mask navigator.webdriver
- Random user agents rotation
- Random viewport (1920±100 x 1080±50)
- Canvas/WebGL fingerprint noise
- 2-5 second delays between requests

### Database Schema (storage/database.py)
```sql
companies: id, name, careers_url, ats_type, priority, h1b_sponsor, last_scraped
jobs: id, company_id, title, location, description, job_url, posted_date,
      h1b_status, h1b_confidence, content_hash, is_active
scrape_logs: id, company_id, scrape_date, jobs_found, jobs_new, errors
```

### H1B Detection (extractors/h1b_detector.py)
NO_SPONSOR keywords: "must be authorized", "without sponsorship", "will not sponsor"
SPONSOR keywords: "visa sponsorship available", "h1b", "will sponsor"
Return: {status: "sponsors"|"does_not_sponsor"|"unknown", confidence: 0-1}

### Date Extraction (extractors/date_finder.py)
5-layer fallback:
1. JSON-LD: <script type="application/ld+json"> → datePosted
2. Meta tags: article:published_time, name="date"
3. Data attributes: data-posted-date
4. Microdata: itemprop="datePosted"
5. Text regex: "Posted: MM/DD/YYYY", "X days ago"

### Greenhouse Scraper (scrapers/greenhouse.py)
Use API when possible: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
Fallback selectors: div[data-job-id], .opening, .job-post

### CLI (run.py)
python run.py --mode=all           # Scrape all companies
python run.py --mode=company --company="Stripe"  # Single company
python run.py --mode=test --limit=3  # Test with 3 companies

## SAMPLE COMPANIES (config/companies.json)
Include these 10 H1B sponsors:
1. Stripe - https://stripe.com/jobs/search
2. Airbnb - https://careers.airbnb.com/positions/
3. Databricks - https://www.databricks.com/company/careers/open-positions
4. Scale AI - https://scale.com/careers
5. Anthropic - https://www.anthropic.com/careers
6. OpenAI - https://openai.com/careers/search
7. Figma - https://www.figma.com/careers/#job-openings
8. Discord - https://discord.com/careers
9. Ramp - https://ramp.com/careers
10. Vercel - https://vercel.com/careers

## OUTPUT
For each job, create:
jobs_output/CompanyName_JobTitle/
├── job_details.json
├── job_description.txt
└── apply_link.txt

## BUILD ORDER
1. config/settings.py + config/companies.json
2. storage/database.py (create tables)
3. stealth/browser.py
4. extractors/ (all 3 files)
5. scrapers/ (base → greenhouse → lever → generic)
6. output/formatter.py
7. run.py
8. Test with: python run.py --mode=test --limit=1

Make each file complete and working. Use try/except everywhere. Log all errors.
```

---

**After it builds, test with:**
```
python run.py --mode=test --limit=1 --company=Anthropic
```
