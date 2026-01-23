# 🧪 Testing Guide

Follow these steps to verify the JobRight Scraper implementation.

## Phase 1: Authentication Verification
1.  **Configure Credentials:** Ensure `config/credentials.yaml` has valid data.
2.  **Run Setup:** `python3 scripts/setup_jobright_auth.py`
3.  **Verify:**
    *   Browser should open.
    *   Script should type email/password.
    *   Should see "✅ SUCCESS! Authentication completed."
    *   Should see file `job_automation/.sessions/jobright_session.json` created.

## Phase 2: Session Loading
1.  **Run Scraper (Headful):** `python3 scripts/scrape_jobright.py --max_jobs 1`
2.  **Verify:**
    *   Browser opens.
    *   You are ALREADY logged in (no login screen).
    *   Console says: `📂 Loading saved session...`
    *   Console says: `✓ Session loaded successfully`.

## Phase 3: Data Extraction
1.  **Run Scraper (Headless):** `python3 scripts/scrape_jobright.py --max_jobs 5 --headless`
2.  **Verify Output:**
    *   Should list 5 jobs.
    *   Each job should have a Title and Company.
    *   Console says: `✅ Scraped 5 jobs from JobRight`.

## Phase 4: Sorting Logic
1.  **Run Scraper:** `python3 scripts/scrape_jobright.py --max_jobs 2`
2.  **Watch Browser:**
    *   Script should click the "Sorter" dropdown (usually top right).
    *   Script should select "Recent".
    *   Page should update.

## Troubleshooting
*   If **Login Fails**: Check `scripts/setup_jobright_auth.py` selectors. JobRight might have changed button IDs.
*   If **Sorting Fails**: The dropdown text might differ ("Newest" vs "Recent"). Update `_apply_sort` in `scrapers/jobright_scraper.py`.
