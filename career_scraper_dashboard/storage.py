import sqlite3
import hashlib
from datetime import datetime
import os

DB_NAME = "career_portal_data.db"

def get_connection():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            location TEXT,
            status TEXT DEFAULT 'NEW',
            posted_date TEXT,          -- Scraped date or "Unknown"
            funding_info TEXT,         -- E.g. "Series C ($100M)"
            category TEXT,             -- E.g. "AI Startup", "H1B Giant"
            content_hash TEXT,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def compute_hash(text):
    """Generate a hash for job description content to detect changes."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def add_job(company, title, url, location, content_raw, posted_date="Unknown", funding_info="", category=""):
    """
    Add a new job or update an existing one.
    Returns: 'NEW', 'EXISTS', or 'REPOSTED'
    """
    conn = get_connection()
    c = conn.cursor()
    
    current_hash = compute_hash(f"{title}{location}{content_raw}")
    
    # Check if URL exists
    c.execute("SELECT id, content_hash FROM jobs WHERE url = ?", (url,))
    row = c.fetchone()
    
    if row:
        job_id, existing_hash = row
        # Always update metadata (category/funding) to backfill existing jobs
        c.execute("""
            UPDATE jobs 
            SET last_seen = ?, category = ?, funding_info = ?, posted_date = ? 
            WHERE id = ?
        """, (datetime.now(), category, funding_info, posted_date, job_id))
        
        if existing_hash != current_hash:
            c.execute("UPDATE jobs SET content_hash = ? WHERE id = ?", (current_hash, job_id))
            conn.commit()
            conn.close()
            return "REPOSTED"
        
        conn.commit()
        conn.close()
        return "EXISTS"
    
    # Insert new job
    c.execute("""
        INSERT INTO jobs (company, title, url, location, posted_date, funding_info, category, content_hash, first_seen, last_seen) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company, title, url, location, posted_date, funding_info, category, current_hash, datetime.now(), datetime.now()))
    conn.commit()
    conn.close()
    return "NEW"

def get_all_jobs():
    """Fetch all jobs for the dashboard."""
    conn = get_connection()
    jobs = conn.execute("SELECT * FROM jobs ORDER BY first_seen DESC").fetchall()
    conn.close()
    return jobs

def get_stats():
    """Get simple stats for the dashboard sidebar."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    new_today = conn.execute("SELECT COUNT(*) FROM jobs WHERE date(first_seen) = date('now')").fetchone()[0]
    conn.close()
    return {"total": total, "new_today": new_today}

if __name__ == "__main__":
    init_db()
    print(f"Database {DB_NAME} initialized.")
