import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

DB_NAME = "jobs.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Jobs Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            company TEXT,
            title TEXT,
            status TEXT DEFAULT 'pending', -- pending, processing, filled, submitted, failed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            attempts INTEGER DEFAULT 0,
            last_error TEXT,
            filled_data JSON -- Store form state (fields filled so far)
        )
    ''')
    
    # Failed Jobs Table (Dead Letter Queue)
    c.execute('''
        CREATE TABLE IF NOT EXISTS failed_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            error TEXT,
            context TEXT, -- HTML dump or screenshot path
            failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    ''')

        # 2. Check and migrate `job_description`
    try:
        c.execute("SELECT job_description, title FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        print("⚠️ applying migration: adding job_description column")
        c.execute("ALTER TABLE jobs ADD COLUMN job_description TEXT")
        c.execute("ALTER TABLE jobs ADD COLUMN title TEXT")
        conn.commit()

    # 3. Check and migrate `resume_path`, `folder_path`, `ats_type`
    try:
        c.execute("SELECT resume_path FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        print("⚠️ applying migration: adding resume_path, folder_path, ats_type columns")
        c.execute("ALTER TABLE jobs ADD COLUMN resume_path TEXT")
        c.execute("ALTER TABLE jobs ADD COLUMN folder_path TEXT")
        c.execute("ALTER TABLE jobs ADD COLUMN ats_type TEXT")
        conn.commit()
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_NAME}")

class JobManager:
    def __init__(self):
        init_db()
        
    def add_job(self, job_id: str, url: str, company: str = "", resume_path: str = "", folder_path: str = "", ats_type: str = "") -> bool:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO jobs (id, url, company, status, resume_path, folder_path, ats_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, url, company, 'pending', resume_path, folder_path, ats_type)
            )
            # Update if exists (for re-loading)
            c.execute(
                "UPDATE jobs SET resume_path = ?, folder_path = ?, ats_type = ? WHERE id = ?",
                (resume_path, folder_path, ats_type, job_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ DB Error: {e}")
            return False
        finally:
            conn.close()

    def update_job_details(self, job_id: str, role: str, description: str):
        """Update job context after scraping."""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE jobs SET title = ?, job_description = ? WHERE id = ?",
                (role, description, job_id)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ DB Update Error: {e}")
        finally:
            conn.close()

    def get_pending_jobs(self, limit: int = 10):
        conn = get_db_connection()
        try:
            jobs = conn.execute(
                "SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(job) for job in jobs]
        finally:
            conn.close()

    def update_status(self, job_id: str, status: str, error: Optional[str] = None):
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP, attempts = attempts + 1 WHERE id = ?", (status, job_id))
            
            if error:
                c.execute("UPDATE jobs SET last_error = ? WHERE id = ?", (error, job_id))
                c.execute("INSERT INTO failed_jobs (job_id, error) VALUES (?, ?)", (job_id, error))
                
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_job_stats(self):
        conn = get_db_connection()
        try:
            stats = conn.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status").fetchall()
            return {row['status']: row['count'] for row in stats}
        finally:
            conn.close()

if __name__ == "__main__":
    # Test Run
    jm = JobManager()
    
    # Add Test Job
    test_id = "job_123"
    jm.add_job(test_id, "https://greenhouse.io/test", "Test Company")
    print("Added Job.")
    
    # Fetch
    pending = jm.get_pending_jobs()
    print(f"Pending: {len(pending)}")
    
    # Update
    jm.update_status(test_id, "failed", "Selector not found")
    print("Updated Status to Failed.")
    
    # Stats
    print(jm.get_job_stats())
