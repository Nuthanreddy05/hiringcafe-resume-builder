import sqlite3
import os

# DB is in the root directory where we run commands
DB_PATH = "career_portal_data.db"

BAD_KEYWORDS = [
    "Survey", "Insight", "Report", "Article", "Trends", "Podcast", "Webcast", 
    "Video", "Perspective", "Outlook", "Guide", "Update", "Alert", "Launch"
]

def clean_ey():
    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Count Total EY
    c.execute("SELECT count(*) FROM jobs WHERE company LIKE '%EY%'")
    total = c.fetchone()[0]
    print(f"Total EY Entries: {total}")
    
    # 2. Identify Garbage
    garbage_ids = []
    c.execute("SELECT id, title, url FROM jobs WHERE company LIKE '%EY%'")
    rows = c.fetchall()
    
    for rid, title, url in rows:
        # Check title for bad keywords
        if any(bad in title for bad in BAD_KEYWORDS):
            garbage_ids.append(rid)
            print(f"  🗑 Marking Garbage: {title[:50]}...")
            continue
            
        # Check simplistic URLs that aren't jobs if applicable
        # (Heuristic: EY jobs often have specific ID patterns or subdomains, but let's stick to content for now)
        
    print(f"Found {len(garbage_ids)} garbage entries.")
    
    if garbage_ids:
        # 3. Delete
        placeholders = ','.join('?' for _ in garbage_ids)
        c.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", garbage_ids)
        conn.commit()
        print("✅ Deleted garbage entries.")
    else:
        print("Clean.")

    conn.close()

if __name__ == "__main__":
    clean_ey()
