# 🎓 H1B JOB SCRAPER - MASTER PROMPT

## Copy this ENTIRE prompt into Antigravity Kit (One Chat Session)

---

```
/create

Build a complete H1B Job Scraper system with an emotional, hopeful UI. This is for international graduates seeking their American dream. The interface should feel like graduation day - caps thrown in the air, hope for the future.

═══════════════════════════════════════════════════════════════════════════════
PART 1: PROJECT VISION & EMOTIONAL DESIGN
═══════════════════════════════════════════════════════════════════════════════

TARGET USER: International students/graduates searching for H1B-sponsoring jobs
EMOTION TO EVOKE: Hope, celebration, new beginnings (like graduation day)
FEELING: "Your American dream starts here"

UI DESIGN REQUIREMENTS:
- Background: Warm light brown/cream (#F5E6D3, #E8D5C4) - like parchment, diplomas
- Text: Deep black (#1A1A1A) for readability, warm brown (#5D4037) for accents
- Accent colors: Gold (#D4AF37) for success states, Navy (#1E3A5A) for buttons
- Hero section: Background image of graduates throwing caps in the air at a college campus
- Animations:
  - On page load: Graduation caps floating up animation
  - On new job found: Confetti burst animation
  - On successful scrape: Cap throw micro-animation
- Typography:
  - Headlines: Playfair Display (elegant, academic)
  - Body: Inter (clean, modern)
- Cards: Soft shadows, rounded corners (16px), cream backgrounds
- Icons: Custom graduation-themed (🎓 for jobs, 🌟 for matches, 🇺🇸 for H1B sponsors)

UI PAGES:
1. Landing/Dashboard - Hero with "Your H1B Journey Starts Here"
2. Companies List - Grid of H1B sponsors with logos
3. Jobs Feed - Real-time job cards with match scores
4. Scrape Status - Live progress with celebration animations
5. Settings - Configure scraping preferences

═══════════════════════════════════════════════════════════════════════════════
PART 2: COMPLETE TECHNICAL ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

TECH STACK:
- Backend: Python 3.11+, FastAPI, Playwright (async), SQLite
- Frontend: Next.js 14, Tailwind CSS, Framer Motion (animations)
- Background Jobs: APScheduler or Celery

PROJECT STRUCTURE:
```
h1b_job_scraper/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # All configuration
│   │   └── companies.json           # 150+ H1B sponsor companies
│   ├── stealth/
│   │   ├── __init__.py
│   │   ├── browser.py               # Stealth Playwright browser
│   │   └── fingerprint.py           # Anti-detection JavaScript
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py              # SQLite operations
│   │   └── models.py                # Pydantic models
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── date_finder.py           # 5-layer date extraction
│   │   ├── h1b_detector.py          # Sponsorship detection
│   │   ├── job_parser.py            # HTML/JSON parsing
│   │   └── deduplicator.py          # SHA-256 + similarity
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract base scraper
│   │   ├── greenhouse.py            # Greenhouse API + fallback
│   │   ├── lever.py                 # Lever scraper
│   │   ├── workday.py               # Workday scraper (complex)
│   │   ├── ashby.py                 # Ashby scraper
│   │   └── generic.py               # Universal fallback
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── routes/
│   │   │   ├── jobs.py              # Job endpoints
│   │   │   ├── companies.py         # Company endpoints
│   │   │   ├── scraper.py           # Scraper control endpoints
│   │   │   └── stats.py             # Statistics endpoints
│   │   └── websocket.py             # Real-time updates
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── jobs.py                  # Scheduled scraping tasks
│   ├── run.py                       # CLI entry point
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Landing/Dashboard
│   │   ├── jobs/page.tsx            # Jobs feed
│   │   ├── companies/page.tsx       # Companies grid
│   │   ├── scraper/page.tsx         # Scraper status
│   │   └── settings/page.tsx        # Settings
│   ├── components/
│   │   ├── ui/                      # Shared UI components
│   │   ├── JobCard.tsx              # Individual job card
│   │   ├── CompanyCard.tsx          # Company card with logo
│   │   ├── GraduationHero.tsx       # Hero with cap animation
│   │   ├── ConfettiAnimation.tsx    # Celebration effects
│   │   ├── ScraperProgress.tsx      # Live scraping status
│   │   └── H1BIndicator.tsx         # Sponsorship badge
│   ├── lib/
│   │   ├── api.ts                   # API client
│   │   └── websocket.ts             # WebSocket connection
│   ├── styles/
│   │   └── globals.css              # Custom styles + animations
│   ├── public/
│   │   └── images/
│   │       └── graduation-bg.jpg    # Hero background
│   ├── tailwind.config.js
│   ├── package.json
│   └── next.config.js
└── README.md
```

═══════════════════════════════════════════════════════════════════════════════
PART 3: BACKEND IMPLEMENTATION DETAILS
═══════════════════════════════════════════════════════════════════════════════

### config/settings.py
```python
"""
Complete configuration for H1B Job Scraper
"""
from pathlib import Path
from typing import List, Dict

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
for d in [DATA_DIR, LOGS_DIR]:
    d.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "jobs.db"

# Scraping Configuration
SCRAPING = {
    "min_delay": 2,                    # Minimum seconds between requests
    "max_delay": 5,                    # Maximum seconds between requests
    "page_timeout": 60,                # Page load timeout
    "element_timeout": 30,             # Element wait timeout
    "max_concurrent": 3,               # Max parallel scrapers
    "max_retries": 3,                  # Retry failed scrapes
    "headless": True,                  # Run browser headless
}

# H1B Detection Keywords
H1B_NO_SPONSOR = [
    "must be authorized to work in the united states",
    "without sponsorship",
    "will not sponsor",
    "does not sponsor",
    "cannot sponsor",
    "unable to sponsor",
    "no sponsorship",
    "u.s. citizen",
    "us citizen only",
    "permanent resident only",
    "green card required",
    "security clearance required",
    "itar restricted",
    "us persons only",
]

H1B_SPONSOR = [
    "visa sponsorship available",
    "visa sponsorship provided",
    "will sponsor",
    "h1b",
    "h-1b",
    "immigration sponsorship",
    "work visa sponsorship",
    "sponsorship for the right candidate",
]

# Tech Job Keywords (for relevance filtering)
TECH_KEYWORDS = [
    "software", "engineer", "developer", "programming", "backend", "frontend",
    "full stack", "fullstack", "full-stack", "devops", "sre", "site reliability",
    "data scientist", "data engineer", "data analyst", "machine learning",
    "ml engineer", "ai engineer", "artificial intelligence", "deep learning",
    "cloud engineer", "cloud architect", "infrastructure", "platform engineer",
    "security engineer", "cybersecurity", "appsec", "devsecops",
    "mobile developer", "ios", "android", "react native", "flutter",
    "qa engineer", "sdet", "test automation", "quality assurance",
    "python", "java", "golang", "rust", "javascript", "typescript",
    "kubernetes", "docker", "aws", "gcp", "azure", "terraform",
]

# Exclude these roles
EXCLUDE_KEYWORDS = [
    "recruiter", "talent acquisition", "hr ", "human resources",
    "sales", "account executive", "business development", "bdm",
    "marketing", "content", "copywriter", "social media",
    "legal", "counsel", "attorney", "paralegal",
    "finance", "accountant", "controller", "bookkeeper",
    "office manager", "administrative", "receptionist", "executive assistant",
]

# User Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# ATS Platform Detection
ATS_PATTERNS = {
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io", "grnh.se"],
    "lever": ["jobs.lever.co", "lever.co"],
    "workday": ["myworkdayjobs.com", "wd1.myworkdayjobs", "wd3.myworkdayjobs", "wd5.myworkdayjobs"],
    "ashby": ["jobs.ashbyhq.com", "ashbyhq.com"],
    "bamboohr": ["bamboohr.com/careers"],
    "smartrecruiters": ["jobs.smartrecruiters.com"],
    "icims": ["careers-", "icims.com"],
    "taleo": ["taleo.net"],
}
```

### stealth/browser.py
```python
"""
Stealth Browser with comprehensive anti-detection
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config.settings import SCRAPING, USER_AGENTS

class StealthBrowser:
    """
    Playwright browser with all anti-bot detection bypasses:
    - WebDriver flag masking
    - Canvas fingerprint noise
    - WebGL vendor/renderer spoofing
    - Plugin and language mocking
    - Random delays and human-like behavior
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def start(self) -> None:
        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ]

        proxy_config = {"server": self.proxy} if self.proxy else None

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            proxy=proxy_config,
        )

        await self._create_stealth_context()

    async def _create_stealth_context(self) -> None:
        user_agent = random.choice(USER_AGENTS)
        width = 1920 + random.randint(-100, 100)
        height = 1080 + random.randint(-50, 50)

        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": width, "height": height},
            locale="en-US",
            timezone_id=random.choice(["America/New_York", "America/Los_Angeles", "America/Chicago"]),
        )

        # Inject stealth scripts
        await self.context.add_init_script(self._get_stealth_script())

    def _get_stealth_script(self) -> str:
        return """
        // 1. Mask WebDriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        delete Navigator.prototype.webdriver;

        // 2. Mock Chrome runtime
        window.chrome = { runtime: {}, loadTimes: () => ({}), csi: () => ({}) };

        // 3. Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (n) => plugins.find(p => p.name === n);
                return plugins;
            }
        });

        // 4. Mock languages
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

        // 5. Mock hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

        // 6. Canvas fingerprint noise
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png') {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 2);
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            return originalToDataURL.apply(this, arguments);
        };

        // 7. WebGL vendor/renderer masking
        const getParameterProxy = new Proxy(WebGLRenderingContext.prototype.getParameter, {
            apply: (target, thisArg, args) => {
                if (args[0] === 37445) return 'Intel Inc.';
                if (args[0] === 37446) return 'Intel Iris OpenGL Engine';
                return Reflect.apply(target, thisArg, args);
            }
        });
        WebGLRenderingContext.prototype.getParameter = getParameterProxy;

        console.log('🕵️ Stealth mode activated');
        """

    async def new_page(self) -> Page:
        if not self.context:
            await self.start()

        page = await self.context.new_page()
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        })
        return page

    async def goto(self, page: Page, url: str, wait_until: str = "domcontentloaded") -> bool:
        try:
            await self.human_delay(0.5, 1.5)
            response = await page.goto(url, wait_until=wait_until, timeout=SCRAPING["page_timeout"] * 1000)

            if not response or response.status in [403, 429, 503]:
                return False

            await self.human_delay(1, 2)
            await self._simulate_human(page)
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            return False

    async def _simulate_human(self, page: Page) -> None:
        for _ in range(random.randint(2, 4)):
            await page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
            await self.human_delay(0.3, 0.8)

    async def human_delay(self, min_s: float = None, max_s: float = None) -> None:
        min_s = min_s or SCRAPING["min_delay"]
        max_s = max_s or SCRAPING["max_delay"]
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def scroll_to_bottom(self, page: Page, max_scrolls: int = 10) -> None:
        for _ in range(max_scrolls):
            prev = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.human_delay(1, 2)
            curr = await page.evaluate("document.body.scrollHeight")
            if curr == prev:
                break

    async def close(self) -> None:
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()
```

### storage/database.py
```python
"""
SQLite database for jobs, companies, and scrape logs
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from config.settings import DATABASE_PATH

class Database:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    careers_url TEXT NOT NULL,
                    ats_type TEXT DEFAULT 'generic',
                    priority INTEGER DEFAULT 5,
                    h1b_sponsor BOOLEAN DEFAULT 1,
                    logo_url TEXT,
                    last_scraped TIMESTAMP,
                    jobs_count INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    first_seen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    department TEXT,
                    employment_type TEXT,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    remote_type TEXT,
                    h1b_status TEXT DEFAULT 'unknown',
                    h1b_confidence REAL DEFAULT 0.5,
                    h1b_snippet TEXT,
                    content_hash TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_relevant BOOLEAN DEFAULT 1,
                    match_score REAL DEFAULT 0,
                    is_new BOOLEAN DEFAULT 1,
                    is_repost BOOLEAN DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS scrape_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER REFERENCES companies(id),
                    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success',
                    jobs_found INTEGER DEFAULT 0,
                    jobs_new INTEGER DEFAULT 0,
                    jobs_updated INTEGER DEFAULT 0,
                    jobs_removed INTEGER DEFAULT 0,
                    errors TEXT,
                    duration_seconds REAL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(content_hash);
                CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(posted_date);
                CREATE INDEX IF NOT EXISTS idx_jobs_h1b ON jobs(h1b_status);
                CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
            """)
            conn.commit()

    def save_company(self, data: Dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO companies (name, careers_url, ats_type, priority, h1b_sponsor, logo_url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    careers_url = excluded.careers_url,
                    ats_type = excluded.ats_type,
                    priority = excluded.priority
                RETURNING id
            """, (data['name'], data['careers_url'], data.get('ats_type', 'generic'),
                  data.get('priority', 5), data.get('h1b_sponsor', True), data.get('logo_url')))
            conn.commit()
            return cursor.fetchone()[0]

    def get_companies_to_scrape(self, limit: int = None) -> List[Dict]:
        with self._get_connection() as conn:
            query = "SELECT * FROM companies WHERE active = 1 ORDER BY priority DESC, last_scraped ASC"
            if limit:
                query += f" LIMIT {limit}"
            return [dict(row) for row in conn.execute(query)]

    def save_job(self, data: Dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO jobs (
                    company_id, title, location, location_city, location_state, location_country,
                    description, requirements, job_url, job_id, posted_date, department,
                    employment_type, salary_min, salary_max, remote_type, h1b_status,
                    h1b_confidence, h1b_snippet, content_hash, is_relevant, match_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    scraped_date = CURRENT_TIMESTAMP,
                    is_active = 1
                RETURNING id
            """, (
                data.get('company_id'), data.get('title'), data.get('location'),
                data.get('location_city'), data.get('location_state'), data.get('location_country'),
                data.get('description'), data.get('requirements'), data.get('job_url'),
                data.get('job_id'), data.get('posted_date'), data.get('department'),
                data.get('employment_type'), data.get('salary_min'), data.get('salary_max'),
                data.get('remote_type'), data.get('h1b_status', 'unknown'),
                data.get('h1b_confidence', 0.5), data.get('h1b_snippet'),
                data.get('content_hash'), data.get('is_relevant', True), data.get('match_score', 0)
            ))
            conn.commit()
            return cursor.fetchone()[0]

    def get_job_by_hash(self, content_hash: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE content_hash = ?", (content_hash,)).fetchone()
            return dict(row) if row else None

    def get_recent_jobs(self, limit: int = 50, h1b_only: bool = False) -> List[Dict]:
        with self._get_connection() as conn:
            query = """
                SELECT j.*, c.name as company_name, c.logo_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.is_active = 1 AND j.is_relevant = 1
            """
            if h1b_only:
                query += " AND j.h1b_status != 'does_not_sponsor'"
            query += " ORDER BY j.scraped_date DESC LIMIT ?"
            return [dict(row) for row in conn.execute(query, (limit,))]

    def log_scrape(self, company_id: int, stats: Dict) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO scrape_logs (company_id, status, jobs_found, jobs_new, jobs_updated, errors, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, stats.get('status', 'success'), stats.get('jobs_found', 0),
                  stats.get('jobs_new', 0), stats.get('jobs_updated', 0),
                  stats.get('errors'), stats.get('duration_seconds')))
            conn.execute("UPDATE companies SET last_scraped = CURRENT_TIMESTAMP, jobs_count = ? WHERE id = ?",
                        (stats.get('jobs_found', 0), company_id))
            conn.commit()

    def get_stats(self) -> Dict:
        with self._get_connection() as conn:
            return {
                "total_companies": conn.execute("SELECT COUNT(*) FROM companies WHERE active = 1").fetchone()[0],
                "total_jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0],
                "h1b_friendly_jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND h1b_status = 'sponsors'").fetchone()[0],
                "new_today": conn.execute("SELECT COUNT(*) FROM jobs WHERE DATE(scraped_date) = DATE('now')").fetchone()[0],
            }
```

### extractors/date_finder.py
```python
"""
5-layer date extraction from job pages
"""
import re
import json
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

def find_posting_date(html: str, url: str = "") -> Optional[datetime]:
    """
    Extract posting date using 5-layer fallback:
    1. JSON-LD structured data (most reliable)
    2. Meta tags
    3. Data attributes
    4. Microdata
    5. Text patterns
    """
    soup = BeautifulSoup(html, 'lxml')

    # Layer 1: JSON-LD
    date = _extract_from_json_ld(soup)
    if date: return date

    # Layer 2: Meta tags
    date = _extract_from_meta(soup)
    if date: return date

    # Layer 3: Data attributes
    date = _extract_from_data_attrs(soup)
    if date: return date

    # Layer 4: Microdata
    date = _extract_from_microdata(soup)
    if date: return date

    # Layer 5: Text patterns
    date = _extract_from_text(soup)
    if date: return date

    return None

def _extract_from_json_ld(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract from JSON-LD structured data"""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0] if data else {}

            # Look for datePosted in JobPosting schema
            date_str = data.get("datePosted") or data.get("publishedAt") or data.get("validThrough")
            if date_str:
                return date_parser.parse(date_str)
        except:
            continue
    return None

def _extract_from_meta(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract from meta tags"""
    meta_names = [
        "article:published_time", "og:published_time", "datePosted",
        "date", "publish-date", "DC.date.issued", "sailthru.date"
    ]

    for name in meta_names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            try:
                return date_parser.parse(tag["content"])
            except:
                continue
    return None

def _extract_from_data_attrs(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract from data-* attributes"""
    data_attrs = ["data-posted-date", "data-publish-date", "data-date", "data-created"]

    for attr in data_attrs:
        element = soup.find(attrs={attr: True})
        if element:
            try:
                return date_parser.parse(element[attr])
            except:
                continue
    return None

def _extract_from_microdata(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract from microdata itemprop"""
    for prop in ["datePosted", "publishDate", "datePublished"]:
        element = soup.find(attrs={"itemprop": prop})
        if element:
            date_str = element.get("content") or element.get("datetime") or element.get_text(strip=True)
            try:
                return date_parser.parse(date_str)
            except:
                continue
    return None

def _extract_from_text(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract from visible text patterns"""
    text = soup.get_text()

    # Pattern: "Posted: January 15, 2025" or "Posted on 01/15/2025"
    patterns = [
        r"posted[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"posted[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"date[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return date_parser.parse(match.group(1))
            except:
                continue

    # Pattern: "Posted X days/hours ago"
    relative_patterns = [
        (r"(\d+)\s+days?\s+ago", lambda d: timedelta(days=int(d))),
        (r"(\d+)\s+hours?\s+ago", lambda h: timedelta(hours=int(h))),
        (r"(\d+)\s+weeks?\s+ago", lambda w: timedelta(weeks=int(w))),
        (r"today", lambda _: timedelta(days=0)),
        (r"yesterday", lambda _: timedelta(days=1)),
    ]

    for pattern, delta_fn in relative_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                delta = delta_fn(match.group(1) if match.groups() else None)
                return datetime.now() - delta
            except:
                continue

    return None
```

### extractors/h1b_detector.py
```python
"""
H1B Sponsorship Detection
"""
import re
from typing import Dict
from config.settings import H1B_NO_SPONSOR, H1B_SPONSOR

def detect_h1b_status(description: str, company_known_sponsor: bool = True) -> Dict:
    """
    Analyze job description for H1B sponsorship indicators.

    Returns:
        {
            "status": "sponsors" | "does_not_sponsor" | "unknown",
            "confidence": 0.0 - 1.0,
            "snippet": "matching text",
            "reason": "explanation"
        }
    """
    if not description:
        return {
            "status": "unknown",
            "confidence": 0.3,
            "snippet": "",
            "reason": "No description available"
        }

    text = description.lower()

    # Check for NO sponsorship indicators first (high priority)
    for keyword in H1B_NO_SPONSOR:
        if keyword in text:
            # Find the snippet
            idx = text.find(keyword)
            start = max(0, idx - 20)
            end = min(len(text), idx + len(keyword) + 20)
            snippet = description[start:end].strip()

            return {
                "status": "does_not_sponsor",
                "confidence": 0.95,
                "snippet": f"...{snippet}...",
                "reason": f"Found exclusion keyword: '{keyword}'"
            }

    # Check for positive sponsorship indicators
    for keyword in H1B_SPONSOR:
        if keyword in text:
            idx = text.find(keyword)
            start = max(0, idx - 20)
            end = min(len(text), idx + len(keyword) + 20)
            snippet = description[start:end].strip()

            return {
                "status": "sponsors",
                "confidence": 0.9,
                "snippet": f"...{snippet}...",
                "reason": f"Found sponsorship keyword: '{keyword}'"
            }

    # No explicit indicators found
    if company_known_sponsor:
        return {
            "status": "unknown",
            "confidence": 0.6,
            "snippet": "",
            "reason": "No explicit mention, but company is known H1B sponsor"
        }

    return {
        "status": "unknown",
        "confidence": 0.4,
        "snippet": "",
        "reason": "No sponsorship information found"
    }
```

### extractors/deduplicator.py
```python
"""
Job Deduplication using SHA-256 hashing and similarity
"""
import hashlib
import re
from typing import Optional

def generate_content_hash(job: dict) -> str:
    """
    Generate SHA-256 hash from job content for deduplication.
    Uses: title + company + location + first 200 chars of description
    """
    title = (job.get('title') or '').lower().strip()
    company = (job.get('company') or job.get('company_name') or '').lower().strip()
    location = (job.get('location') or '').lower().strip()
    desc = (job.get('description') or '')[:200].lower().strip()

    # Normalize: remove special characters, extra whitespace
    content = f"{title}|{company}|{location}|{desc}"
    content = re.sub(r'[^\w\s|]', '', content)
    content = re.sub(r'\s+', ' ', content)

    return hashlib.sha256(content.encode()).hexdigest()

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two texts.
    Returns 0.0 to 1.0 (1.0 = identical)
    """
    if not text1 or not text2:
        return 0.0

    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0

def is_likely_repost(new_job: dict, existing_job: dict, threshold: float = 0.85) -> bool:
    """
    Determine if new job is likely a repost of existing job.
    """
    # Same hash = definite duplicate
    if new_job.get('content_hash') == existing_job.get('content_hash'):
        return True

    # Check title similarity
    title_sim = calculate_similarity(
        new_job.get('title', ''),
        existing_job.get('title', '')
    )

    # Check description similarity
    desc_sim = calculate_similarity(
        new_job.get('description', ''),
        existing_job.get('description', '')
    )

    # Combined score (weighted)
    combined = (title_sim * 0.3) + (desc_sim * 0.7)

    return combined >= threshold
```

### scrapers/base.py
```python
"""
Abstract Base Scraper
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all ATS-specific scrapers"""

    def __init__(self, browser, company: dict, db):
        self.browser = browser
        self.company = company
        self.db = db
        self.jobs: List[Dict] = []
        self.errors: List[Dict] = []

    @abstractmethod
    async def discover_job_urls(self) -> List[str]:
        """Find all job URLs from the careers page."""
        pass

    @abstractmethod
    async def scrape_job_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract job details from a single job page."""
        pass

    async def scrape_all(self) -> List[Dict]:
        """Main entry point: discover URLs, scrape each."""
        logger.info(f"🔍 Starting scrape for {self.company['name']}")

        try:
            urls = await self.discover_job_urls()
            logger.info(f"📋 Found {len(urls)} job URLs")

            for i, url in enumerate(urls):
                try:
                    await self.browser.human_delay(2, 4)
                    job = await self.scrape_job_page(url)

                    if job:
                        job['company'] = self.company['name']
                        job['company_id'] = self.company.get('id')
                        job['job_url'] = url
                        self.jobs.append(job)
                        logger.info(f"✅ [{i+1}/{len(urls)}] {job.get('title', 'Unknown')}")

                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {e}")
                    self.errors.append({"url": url, "error": str(e)})

        except Exception as e:
            logger.error(f"❌ Fatal error for {self.company['name']}: {e}")
            self.errors.append({"url": self.company['careers_url'], "error": str(e)})

        return self.jobs

    def is_relevant_job(self, title: str) -> bool:
        """Check if job title indicates a tech role."""
        from config.settings import TECH_KEYWORDS, EXCLUDE_KEYWORDS

        title_lower = title.lower()

        # Check exclusions first
        for kw in EXCLUDE_KEYWORDS:
            if kw in title_lower:
                return False

        # Check for tech keywords
        for kw in TECH_KEYWORDS:
            if kw in title_lower:
                return True

        return False
```

### scrapers/greenhouse.py
```python
"""
Greenhouse ATS Scraper - Uses API when available
"""
import re
import aiohttp
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper

class GreenhouseScraper(BaseScraper):
    """
    Greenhouse scraper with API-first approach.
    API endpoint: boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
    """

    def __init__(self, browser, company: dict, db):
        super().__init__(browser, company, db)
        self.api_jobs: Dict[str, Dict] = {}  # Cache API results

    def _extract_board_token(self, url: str) -> Optional[str]:
        """Extract board token from Greenhouse URL"""
        patterns = [
            r"boards\.greenhouse\.io/(\w+)",
            r"greenhouse\.io/embed/job_board\?.*for=(\w+)",
            r"/gh/(\w+)/jobs",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def _fetch_from_api(self, token: str) -> List[Dict]:
        """Fetch all jobs from Greenhouse API"""
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('jobs', [])
        return []

    async def discover_job_urls(self) -> List[str]:
        token = self._extract_board_token(self.company['careers_url'])

        if token:
            try:
                api_jobs = await self._fetch_from_api(token)
                urls = []
                for job in api_jobs:
                    url = job.get('absolute_url', '')
                    if url:
                        self.api_jobs[url] = job  # Cache for later
                        urls.append(url)
                return urls
            except Exception as e:
                print(f"API failed, falling back to HTML: {e}")

        # Fallback to HTML scraping
        page = await self.browser.new_page()
        try:
            await self.browser.goto(page, self.company['careers_url'])
            await self.browser.scroll_to_bottom(page)

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            urls = []
            for a in soup.select('a[href*="/jobs/"], a[data-job-id], .opening a'):
                href = a.get('href', '')
                if '/jobs/' in href:
                    if not href.startswith('http'):
                        href = f"https://boards.greenhouse.io{href}"
                    urls.append(href)

            return list(set(urls))
        finally:
            await page.close()

    async def scrape_job_page(self, url: str) -> Optional[Dict]:
        # Check API cache first
        if url in self.api_jobs:
            job = self.api_jobs[url]
            return {
                'title': job.get('title'),
                'location': job.get('location', {}).get('name'),
                'description': job.get('content'),
                'job_id': str(job.get('id')),
                'department': ', '.join([d.get('name', '') for d in job.get('departments', [])]),
                'posted_date': job.get('updated_at'),
            }

        # Fallback to HTML scraping
        page = await self.browser.new_page()
        try:
            await self.browser.goto(page, url)
            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            return {
                'title': soup.select_one('h1, .job-title')?.get_text(strip=True),
                'location': soup.select_one('.location')?.get_text(strip=True),
                'description': soup.select_one('#content, .job-description')?.get_text(strip=True),
            }
        finally:
            await page.close()
```

### api/main.py (FastAPI Backend)
```python
"""
FastAPI Backend for H1B Job Scraper
"""
from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
from storage.database import Database
from stealth.browser import StealthBrowser

app = FastAPI(title="H1B Job Scraper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

@app.get("/api/jobs")
async def get_jobs(limit: int = 50, h1b_only: bool = False):
    """Get recent jobs"""
    return db.get_recent_jobs(limit=limit, h1b_only=h1b_only)

@app.get("/api/companies")
async def get_companies():
    """Get all companies"""
    return db.get_companies_to_scrape()

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    return db.get_stats()

@app.post("/api/scrape/start")
async def start_scrape(background_tasks: BackgroundTasks, company_name: Optional[str] = None):
    """Start scraping in background"""
    background_tasks.add_task(run_scraper, company_name)
    return {"status": "started", "message": "Scraping started in background"}

async def run_scraper(company_name: Optional[str] = None):
    """Background scraping task"""
    # Import and run scraper
    pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    while True:
        await asyncio.sleep(5)
        stats = db.get_stats()
        await websocket.send_json(stats)
```

═══════════════════════════════════════════════════════════════════════════════
PART 4: FRONTEND - EMOTIONAL UI DESIGN
═══════════════════════════════════════════════════════════════════════════════

### tailwind.config.js - Custom Theme
```javascript
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm, hopeful color palette
        cream: {
          50: '#FFFDF8',
          100: '#FDF8EF',
          200: '#F5E6D3',
          300: '#E8D5C4',
          400: '#D4C4B0',
          500: '#C4A77D',
        },
        gold: {
          400: '#E5C158',
          500: '#D4AF37',
          600: '#B8960B',
        },
        navy: {
          500: '#2E4A62',
          600: '#1E3A5A',
          700: '#152D45',
        },
        brown: {
          400: '#8B7355',
          500: '#5D4037',
          600: '#4E342E',
        }
      },
      fontFamily: {
        display: ['Playfair Display', 'serif'],
        body: ['Inter', 'sans-serif'],
      },
      animation: {
        'float-up': 'floatUp 3s ease-out infinite',
        'confetti': 'confetti 1s ease-out forwards',
        'cap-throw': 'capThrow 1.5s ease-out forwards',
      },
      keyframes: {
        floatUp: {
          '0%': { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
          '100%': { transform: 'translateY(-100vh) rotate(720deg)', opacity: 0 },
        },
        confetti: {
          '0%': { transform: 'translateY(0) rotate(0)', opacity: 1 },
          '100%': { transform: 'translateY(100px) rotate(720deg)', opacity: 0 },
        },
        capThrow: {
          '0%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-50px) rotate(180deg)' },
          '100%': { transform: 'translateY(0) rotate(360deg)' },
        }
      }
    },
  },
  plugins: [],
}
```

### app/page.tsx - Landing Page with Graduation Hero
```tsx
'use client';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import GraduationHero from '@/components/GraduationHero';
import StatsCard from '@/components/StatsCard';
import RecentJobs from '@/components/RecentJobs';

export default function Home() {
  const [stats, setStats] = useState({ total_jobs: 0, h1b_friendly_jobs: 0, new_today: 0 });

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats);
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-b from-cream-100 to-cream-200">
      {/* Hero Section */}
      <GraduationHero />

      {/* Stats Section */}
      <section className="max-w-6xl mx-auto px-4 -mt-20 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatsCard
            icon="🎓"
            label="Total Jobs"
            value={stats.total_jobs}
            color="gold"
          />
          <StatsCard
            icon="🇺🇸"
            label="H1B Friendly"
            value={stats.h1b_friendly_jobs}
            color="navy"
          />
          <StatsCard
            icon="✨"
            label="New Today"
            value={stats.new_today}
            color="brown"
          />
        </div>
      </section>

      {/* Recent Jobs */}
      <section className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="font-display text-3xl text-brown-600 mb-8 text-center">
          Your Journey Starts Here
        </h2>
        <RecentJobs />
      </section>
    </main>
  );
}
```

### components/GraduationHero.tsx
```tsx
'use client';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

const GraduationCap = ({ delay }: { delay: number }) => (
  <motion.div
    className="absolute text-4xl"
    initial={{ y: '100vh', x: Math.random() * 100 - 50 + '%', rotate: 0 }}
    animate={{
      y: '-100vh',
      rotate: 720,
      transition: { duration: 4, delay, repeat: Infinity, ease: 'easeOut' }
    }}
  >
    🎓
  </motion.div>
);

export default function GraduationHero() {
  const [caps, setCaps] = useState<number[]>([]);

  useEffect(() => {
    setCaps(Array.from({ length: 15 }, (_, i) => i));
  }, []);

  return (
    <div className="relative h-[70vh] overflow-hidden">
      {/* Background Image - Graduation/Campus */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: 'url(/images/graduation-bg.jpg)',
          filter: 'brightness(0.7)'
        }}
      />

      {/* Warm Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-cream-100/30 to-cream-200/80" />

      {/* Floating Graduation Caps */}
      <div className="absolute inset-0 pointer-events-none">
        {caps.map(i => (
          <GraduationCap key={i} delay={i * 0.3} />
        ))}
      </div>

      {/* Content */}
      <div className="relative h-full flex flex-col items-center justify-center text-center px-4">
        <motion.h1
          className="font-display text-5xl md:text-7xl text-brown-600 mb-4"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          Your American Dream
        </motion.h1>

        <motion.p
          className="font-body text-xl md:text-2xl text-brown-500 mb-8 max-w-2xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          Find H1B-sponsoring companies that believe in your potential.
          Your graduation was just the beginning.
        </motion.p>

        <motion.button
          className="bg-navy-600 hover:bg-navy-700 text-cream-50 font-body font-semibold
                     px-8 py-4 rounded-full text-lg shadow-lg hover:shadow-xl
                     transition-all duration-300"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          Explore Opportunities 🚀
        </motion.button>
      </div>
    </div>
  );
}
```

### components/JobCard.tsx
```tsx
'use client';
import { motion } from 'framer-motion';

interface JobCardProps {
  job: {
    title: string;
    company_name: string;
    location: string;
    h1b_status: string;
    h1b_confidence: number;
    posted_date: string;
    job_url: string;
    remote_type?: string;
  };
  index: number;
}

export default function JobCard({ job, index }: JobCardProps) {
  const h1bColor = {
    sponsors: 'bg-green-100 text-green-800 border-green-300',
    does_not_sponsor: 'bg-red-100 text-red-800 border-red-300',
    unknown: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  }[job.h1b_status] || 'bg-gray-100 text-gray-800';

  return (
    <motion.div
      className="bg-cream-50 rounded-2xl shadow-md hover:shadow-xl transition-shadow
                 duration-300 p-6 border border-cream-300"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={{ y: -4 }}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-display text-xl text-brown-600 mb-1">
            {job.title}
          </h3>
          <p className="font-body text-brown-500">{job.company_name}</p>
        </div>

        {/* H1B Badge */}
        <span className={`px-3 py-1 rounded-full text-sm font-body border ${h1bColor}`}>
          {job.h1b_status === 'sponsors' && '🇺🇸 H1B'}
          {job.h1b_status === 'does_not_sponsor' && '⚠️ No Visa'}
          {job.h1b_status === 'unknown' && '❓ Unknown'}
        </span>
      </div>

      {/* Details */}
      <div className="flex flex-wrap gap-3 mb-4 text-sm text-brown-400">
        <span className="flex items-center gap-1">
          📍 {job.location}
        </span>
        {job.remote_type && (
          <span className="flex items-center gap-1">
            🏠 {job.remote_type}
          </span>
        )}
        <span className="flex items-center gap-1">
          📅 {new Date(job.posted_date).toLocaleDateString()}
        </span>
      </div>

      {/* Action */}
      <a
        href={job.job_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block w-full text-center bg-gold-500 hover:bg-gold-600
                   text-brown-600 font-body font-semibold py-3 rounded-xl
                   transition-colors duration-300"
      >
        Apply Now ✨
      </a>
    </motion.div>
  );
}
```

### components/ConfettiAnimation.tsx
```tsx
'use client';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

interface ConfettiProps {
  trigger: boolean;
}

export default function ConfettiAnimation({ trigger }: ConfettiProps) {
  const [particles, setParticles] = useState<number[]>([]);

  useEffect(() => {
    if (trigger) {
      setParticles(Array.from({ length: 50 }, (_, i) => i));
      setTimeout(() => setParticles([]), 2000);
    }
  }, [trigger]);

  const colors = ['#D4AF37', '#1E3A5A', '#5D4037', '#E5C158', '#F5E6D3'];

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {particles.map(i => (
        <motion.div
          key={i}
          className="absolute w-3 h-3 rounded-full"
          style={{
            backgroundColor: colors[i % colors.length],
            left: `${Math.random() * 100}%`,
            top: '-10px',
          }}
          initial={{ y: 0, opacity: 1, rotate: 0 }}
          animate={{
            y: '100vh',
            opacity: 0,
            rotate: Math.random() * 720 - 360,
          }}
          transition={{
            duration: 2 + Math.random(),
            ease: 'easeOut',
            delay: Math.random() * 0.3,
          }}
        />
      ))}
    </div>
  );
}
```

═══════════════════════════════════════════════════════════════════════════════
PART 5: SAMPLE COMPANIES DATA
═══════════════════════════════════════════════════════════════════════════════

Include these 50 H1B sponsor companies in config/companies.json:

Top Tech (Priority 10):
Google, Meta, Amazon, Apple, Microsoft, Netflix

High-Growth Startups (Priority 9-10):
Stripe, Airbnb, Databricks, Scale AI, Anthropic, OpenAI, Figma, Discord,
Ramp, Vercel, Notion, Plaid, Rippling, Brex, Anduril, SpaceX

Established Tech (Priority 8):
Uber, Lyft, DoorDash, Instacart, Robinhood, Coinbase, Block (Square),
Snowflake, MongoDB, Elastic, Twilio, Okta, Cloudflare

Enterprise (Priority 7):
Salesforce, ServiceNow, Workday, Adobe, Oracle, SAP, VMware

Finance/Fintech (Priority 8):
JPMorgan, Goldman Sachs, Bloomberg, Citadel, Two Sigma, Jane Street

═══════════════════════════════════════════════════════════════════════════════
FINAL INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

1. Build backend first (Python/FastAPI)
2. Build frontend second (Next.js)
3. Use the EXACT color scheme: cream backgrounds, brown text, gold accents, navy buttons
4. The emotional feel should be: HOPE, CELEBRATION, NEW BEGINNINGS
5. Every animation should feel like graduation day - caps in the air, confetti, joy
6. Test with 3 companies first: Anthropic, Stripe, OpenAI
7. Create a README with setup instructions

The target user is an international student who just graduated and is scared about
their visa situation. This app should make them feel hopeful and supported.

Make it beautiful. Make it work. Make them believe in their dreams again.
```

---

## 🚀 USAGE

1. Open Claude Code/Cursor in your project folder
2. Type: `/create`
3. Paste the ENTIRE prompt above
4. Let it build everything
5. Test and refine in the same chat session

**The multi-agent system will automatically apply:**
- @backend-specialist for Python/FastAPI code
- @frontend-specialist for Next.js/React
- @ui-ux-pro-max for the emotional design
- @security-auditor for stealth browser
- @debugger if anything breaks
