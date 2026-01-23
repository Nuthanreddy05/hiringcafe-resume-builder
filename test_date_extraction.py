import sys
import os
import requests
from bs4 import BeautifulSoup
sys.path.append("career_scraper_dashboard")
import monitor

def test(url):
    print(f"Testing {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Test 1: Page Level Date
        date = monitor.get_posted_date(soup)
        print(f"Page Level Date: {date}")
        
        # Test 2: Find a job link and deep scrape it
        print("Looking for job links...")
        found_job = False
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Heuristic for job link
            if "/job/" in href or "careers" in href:
                full_url = requests.compat.urljoin(url, href)
                print(f"  > Deep Scraping: {full_url}")
                try:
                    jr = requests.get(full_url, headers=headers, timeout=5)
                    jsoup = BeautifulSoup(jr.text, 'html.parser')
                    jdate = monitor.get_posted_date(jsoup)
                    print(f"    > Extracted Date: {jdate}")
                    if jdate != "Unknown":
                        print("    ✅ SUCCESS: Hidden Date Found!")
                        found_job = True
                        break
                except Exception as e:
                    print(f"    Error: {e}")
        
        if not found_job:
            print("No valid job links with dates found in first few attempts.")
            
    except Exception as e:
        print(f"Error accessing {url}: {e}")

if __name__ == "__main__":
    # Default to Amazon or similar if not provided
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.amazon.jobs/en/" 
    test(url)
