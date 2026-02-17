import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

# DB Configuration
DB_NAME = "jobs.db"

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to current directory
            self.db_path = Path.cwd() / DB_NAME
        else:
            self.db_path = Path(db_path)
            
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Companies Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            domain TEXT,
            career_page_url TEXT,
            ats_provider TEXT, -- 'greenhouse', 'lever', 'workday', 'custom'
            source TEXT, -- 'top_150_h1b', 'fortune_500'
            h1b_count_2024 INTEGER DEFAULT 0,
            last_scraped_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Jobs Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            description TEXT,
            location TEXT,
            posted_date_visible TEXT,
            posted_date_hidden TEXT, -- Extracted from JSON-LD/Metadata
            is_citizenship_required BOOLEAN DEFAULT 0,
            sponsorship_available BOOLEAN DEFAULT 1, -- Default true until proven false
            status TEXT DEFAULT 'new', -- 'new', 'applied', 'rejected', 'skipped'
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')

        # Scraping Logs
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraping_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            target_type TEXT, -- 'company', 'discovery'
            target_name TEXT,
            status TEXT, -- 'success', 'failed', 'blocked'
            jobs_found INTEGER,
            logs TEXT
        )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # --- Company Methods ---

    def add_company(self, name, url, source, h1b_count=0):
        """Add or update a company."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO companies (name, career_page_url, source, h1b_count_2024, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                career_page_url = excluded.career_page_url,
                h1b_count_2024 = excluded.h1b_count_2024,
                source = excluded.source
            ''', (name, url, source, h1b_count, datetime.now()))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error adding company {name}: {e}")
            return None
        finally:
            conn.close()

    def get_companies_to_scrape(self, limit=10):
        """Get companies that haven't been scraped recently, prioritized by H1B count."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Logic: 
        # 1. Sort by last_scraped_at ASC (scrape oldest first)
        # 2. Sort by h1b_count_2024 DESC (prioritize aggressive hirers)
        # We'll prioritize H1B count first as per user request for "Recent Sponsors"
        cursor.execute('''
        SELECT id, name, career_page_url, ats_provider 
        FROM companies 
        ORDER BY last_scraped_at ASC, h1b_count_2024 DESC
        LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "url": r[2], "ats": r[3]} for r in rows]

    def update_company_scrape_timestamp(self, company_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE companies SET last_scraped_at = ? WHERE id = ?', (datetime.now(), company_id))
        conn.commit()
        conn.close()

    # --- Job Methods ---

    def add_job(self, job_data):
        """
        Add a job if it doesn't exist.
        job_data: {company_id, title, url, description, location, posted_date_visible, posted_date_hidden, is_citizenship_required, sponsorship_available}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO jobs (
                company_id, title, url, description, location, 
                posted_date_visible, posted_date_hidden, 
                is_citizenship_required, sponsorship_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
            ''', (
                job_data['company_id'], job_data['title'], job_data['url'], 
                job_data.get('description', ''), job_data.get('location', 'Unknown'),
                job_data.get('posted_date_visible'), job_data.get('posted_date_hidden'),
                job_data.get('is_citizenship_required', False), job_data.get('sponsorship_available', True)
            ))
            conn.commit()
            return cursor.rowcount > 0 # Returns True if inserted
        except Exception as e:
            logging.error(f"Error adding job {job_data.get('url')}: {e}")
            return False
        finally:
            conn.close()

    # --- Log Methods ---

    def log_scrape(self, target_name, status, jobs_found, logs=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO scraping_logs (target_name, status, jobs_found, logs)
        VALUES (?, ?, ?, ?)
        ''', (target_name, status, jobs_found, logs))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Test Init
    db = DatabaseManager()
    print(f"Database initialized at {db.db_path}")
    
    # Test Add Company
    db.add_company("Test Corp", "https://test.com/jobs", "manual", h1b_count=100)
    print("Added Test Corp")
    
    # Test Get
    companies = db.get_companies_to_scrape()
    print(f"Companies to scrape: {companies}")
