import time
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import random
import sys
import os

# Ensure we can import sibling modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import discovery
import storage

import re

KEYWORDS = ["Software", "Engineer", "Developer", "Data", "Scientist", "Machine Learning", "Research", "Product"]
# separate handling for AI to enforce word boundary
EXCLUDE_TERMS = ["skip to main content", "login", "sign up", "privacy policy", "terms", "careers home", "read more"]

def is_relevant(text):
    text_lower = text.lower()
    
    # 1. Check Keywords
    has_keyword = any(k.lower() in text_lower for k in KEYWORDS)
    
    # 2. Check "AI" with word boundary
    has_ai = re.search(r'\b(ai|ml)\b', text_lower)
    
    if not (has_keyword or has_ai):
        return False
        
    # 3. Check Exclusions
    if any(ex in text_lower for ex in EXCLUDE_TERMS):
        return False
        
    return True

def get_posted_date(soup):
    """Attempt to extract posted date from common meta tags or HTML structure."""
    try:
        # 1. Meta Tags (Standard)
        meta_date = soup.find("meta", {"itemprop": "datePosted"}) or \
                    soup.find("meta", {"property": "article:published_time"})
        if meta_date:
            return meta_date.get("content", "").split("T")[0]

        # 2. JSON-LD (Google Jobs Schema)
        import json
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if 'datePosted' in data:
                    return data['datePosted'].split("T")[0]
            except: 
                pass

        # 3. Visible Text Heuristics (e.g. "Posted 2 days ago")
        # limit to short strings
        # (Simplified for v1)
        
        return "Unknown"
    except:
        return "Unknown"

def scrape_greenhouse(company, url, category, funding):
    """Specific scraper for Greenhouse boards."""
    try:
        print(f"  Scraping {company} (Greenhouse)...")
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Failed: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Greenhouse listings usually in <div class="opening"> or <a> tags with specific classes
        # This is a generic robust attempt
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if not href or not text:
                continue
                
            # Filter by keywords
            if is_relevant(text):
                full_url = urljoin(url, href)
                
                full_url = urljoin(url, href)
                
                # --- DEEP SCRAPE FOR "HIDDEN" DATE ---
                try:
                    job_resp = requests.get(full_url, headers=headers, timeout=5)
                    job_soup = BeautifulSoup(job_resp.text, 'html.parser')
                    extracted_date = get_posted_date(job_soup)
                    date_str = extracted_date if extracted_date != "Unknown" else datetime.datetime.now().strftime("%Y-%m-%d")
                    time.sleep(1) 
                except:
                    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

                # Save to DB
                status = storage.add_job(
                    company, 
                    text, 
                    full_url, 
                    "Unknown", 
                    text,
                    posted_date=date_str, # Using discovery date as proxy for now
                    funding_info=funding,
                    category=category
                )
                print(f"    Found: {text[:40]}... -> {status}")

    except Exception as e:
        print(f"  ❌ Error scraping {company}: {e}")

def scrape_generic(company, url, category, funding):
    """Generic fallback scraper."""
    try:
        print(f"  Scraping {company} (Generic)...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and text and is_relevant(text):
                full_url = urljoin(url, href)
                full_url = urljoin(url, href)
                
                # --- DEEP SCRAPE FOR "HIDDEN" DATE ---
                # User Requirement: Extract date from the page source (JSON-LD/Meta)
                try:
                    job_resp = requests.get(full_url, headers=headers, timeout=5)
                    job_soup = BeautifulSoup(job_resp.text, 'html.parser')
                    extracted_date = get_posted_date(job_soup)
                    date_str = extracted_date if extracted_date != "Unknown" else datetime.datetime.now().strftime("%Y-%m-%d")
                    time.sleep(1) # Polite delay for deep scrape
                except:
                    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                
                status = storage.add_job(
                    company, 
                    text, 
                    full_url, 
                    "Unknown", 
                    text,
                    posted_date=date_str,
                    funding_info=funding,
                    category=category
                )
                print(f"    Found: {text[:40]}... -> {status}")

    except Exception as e:
        print(f"  ❌ Error scraping {company}: {e}")

def run_cycle():
    """Run one full scraping cycle."""
    print("\n--- Starting Scraping Cycle ---")
    targets = discovery.get_targets()
    random.shuffle(targets) # Mix it up to avoid patterns
    
    for target in targets:
        company = target['name']
        url = target['url']
        ats = target.get('ats', 'custom')
        funding = target.get('funding', '')
        category = target.get('category', '')
        
    except Exception as e:
        print(f"  ❌ Error scraping {company}: {e}")

def scrape_smart(company, url, category, funding):
    """Uses LLM-based smart scraper for complex sites."""
    try:
        from smart_scraper import scrape_with_ai
        jobs = scrape_with_ai(url, company)
        
        for job in jobs:
            title = job.get('title', 'Unknown')
            job_url = job.get('url', 'Unknown')
            date_str = job.get('date', 'Unknown')
            
            # Resolve relative URLs
            if job_url.startswith('/'):
                 job_url = urljoin(url, job_url)
                 
            status = storage.add_job(
                company, 
                title, 
                job_url, 
                job.get('location', 'Unknown'), 
                f"{title} {job.get('type','')}",
                posted_date=date_str,
                funding_info=funding,
                category=category
            )
            print(f"    AI Found: {title[:40]}... -> {status}")
            
    except Exception as e:
        print(f"  ❌ Smart Scrape Error for {company}: {e}")

def run_cycle():
    """Run one full scraping cycle."""
    print("\n--- Starting Scraping Cycle ---")
    targets = discovery.get_targets()
    random.shuffle(targets) # Mix it up to avoid patterns
    
    for target in targets:
        company = target['name']
        url = target['url']
        ats = target.get('ats', 'custom')
        funding = target.get('funding', '')
        category = target.get('category', '')
        
        # Route EY to Smart Scraper
        if "EY" in company or "Ernst & Young" in company:
            scrape_smart(company, url, category, funding)
        elif ats == 'greenhouse':
            scrape_greenhouse(company, url, category, funding)
        else:
            scrape_generic(company, url, category, funding)
            
        time.sleep(random.uniform(2, 5)) # Polite delay

if __name__ == "__main__":
    storage.init_db()
    print("Monitor initialized. Press Ctrl+C to stop.")
    while True:
        run_cycle()
        print("Sleeping for 10 minutes...")
        time.sleep(600)
