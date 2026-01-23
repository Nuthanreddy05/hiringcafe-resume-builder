# 🤖 JobRight AI Scraper & Automation

A modular, authenticated scraper for JobRight.ai (and extensible for other platforms).
Designed for enterprise-grade automation with session persistence, error handling, and component modularity.

## 📂 Project Structure

```
job_automation/
├── core/                   # Core logic (Auth, Scraper Base, Models)
├── scrapers/               # Source-specific implementation (JobRight)
├── config/                 # Credentials and settings
├── scripts/                # Executable scripts
├── utils/                  # Helpers
└── .sessions/              # Saved browser sessions (ignored by git)
```

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration
Copy the example credentials file and edit it:
```bash
cp config/credentials.yaml.example config/credentials.yaml
# Edit config/credentials.yaml with your JobRight email/password
```

### 3. Authentication (One-Time Setup)
Run this interactive script to log in and save your session:
```bash
python3 scripts/setup_jobright_auth.py
```
*   This will open a browser, log you in, and save your session cookies to `.sessions/`.
*   Future runs will use this saved session automatically.
*   **Note:** If you use Google/LinkedIn login, you may need to approve 2FA manually in the browser window.

### 4. Run the Scraper
```bash
python3 scripts/scrape_jobright.py --start_url "https://jobright.ai/jobs/recommend" --max_jobs 10
```
*   **--headless**: Run without opening a visible browser.
*   **--max_jobs N**: Limit number of jobs to scrape.

## 🛠️ Features
*   **Authentication:** Supports Email, Google, and LinkedIn login.
*   **Session Persistence:** Logs in once, reuses session cookies for speed and stealth.
*   **Auto-Sort:** Automatically switches view to "Most Recent" where possible.
*   **Robust Selectors:** Uses multi-strategy DOM extraction to handle dynamic JobRight updates.
*   **Modular:** Easy to add `HiringCafe` or `LinkedIn` scrapers using the Factory pattern.

## ⚠️ Troubleshooting
*   **"Login Failed":** re-run `setup_jobright_auth.py` without `--headless` to see what's happening.
*   **"0 Jobs Found":** The DOM might have changed. Check `scrapers/jobright_scraper.py` selectors.
