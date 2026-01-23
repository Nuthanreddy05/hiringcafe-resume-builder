import json
import os
import requests
import time
from urllib.parse import urlparse

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
H1B_FILE = os.path.join(BASE_DIR, "career_scraper_dashboard", "uscis_h1b_top_list.json")
EXISTING_COMPANIES_FILE = os.path.join(BASE_DIR, "career_scraper_dashboard", "companies.json")

# 1. Manual Overrides from Web Search
MANUAL_URLS = {
    "Amazon": "https://www.amazon.jobs/en/",
    "Accenture": "https://www.accenture.com/us-en/careers",
    "Apple": "https://www.apple.com/careers/us/",
    "Google": "https://careers.google.com/",
    "Microsoft Corporation": "https://careers.microsoft.com/",
    "Microsoft": "https://careers.microsoft.com/",
    "Intel Corporation": "https://www.intel.com/content/www/us/en/jobs/careers-at-intel.html",
    "Qualcomm": "https://www.qualcomm.com/company/careers",
    "Salesforce": "https://www.salesforce.com/company/careers/",
    "Tesla": "https://www.tesla.com/careers",
    "Walmart": "https://careers.walmart.com/",
    "IBM": "https://www.ibm.com/careers",
    "Tata Consultancy Services": "https://www.tcs.com/careers",
    "Tata Consultancy Services (TCS)": "https://www.tcs.com/careers",
    "Infosys": "https://www.infosys.com/careers/",
    "Deloitte": "https://www2.deloitte.com/us/en/careers.html",
    "Deloitte Consulting": "https://www2.deloitte.com/us/en/careers.html",
    "Ernst & Young (EY)": "https://www.ey.com/en_us/careers",
    "EY": "https://www.ey.com/en_us/careers",
    "KPMG": "https://www.kpmg.us/careers/",
    "PricewaterhouseCoopers": "https://www.pwc.com/us/en/careers.html",
    "PriceWaterhouseCoopers": "https://www.pwc.com/us/en/careers.html",
    "Capgemini": "https://www.capgemini.com/careers/",
    "Cognizant Technology Solutions": "https://careers.cognizant.com/global/en",
    "Wipro": "https://careers.wipro.com/",
    "Wipro Limited": "https://careers.wipro.com/",
    "HCL America": "https://www.hcltech.com/careers",
    "Tech Mahindra": "https://www.techmahindra.com/en-us/people-and-careers/",
    "JPMorgan Chase": "https://careers.jpmorganchase.com/",
    "J.P. Morgan Chase": "https://careers.jpmorganchase.com/",
    "Goldman Sachs": "https://www.goldmansachs.com/careers/",
    "Goldman Sachs Group": "https://www.goldmansachs.com/careers/",
    "Bank of America": "https://careers.bankofamerica.com/",
    "Citigroup": "https://careers.citigroup.com/",
    "Citigroup Inc.": "https://careers.citigroup.com/",
    "Morgan Stanley": "https://www.morganstanley.com/careers/",
    "Wells Fargo": "https://www.wellsfargojobs.com/",
    "Meta": "https://www.metacareers.com/",
    "Meta (Facebook)": "https://www.metacareers.com/",
    "Uber": "https://www.uber.com/us/en/careers/",
    "Airbnb": "https://careers.airbnb.com/",
    "DoorDash": "https://careers.doordash.com/",
    "Wayfair": "https://www.aboutwayfair.com/careers",
    "NVIDIA": "https://www.nvidia.com/en-us/about-nvidia/careers/",
    "Adobe": "https://www.adobe.com/careers.html",
    "Adobe Systems Incorporated": "https://www.adobe.com/careers.html",
    "Oracle": "https://careers.oracle.com/",
    "Cisco": "https://www.cisco.com/c/en/us/about/careers.html",
    "Cisco Systems, Inc.": "https://www.cisco.com/c/en/us/about/careers.html"
}

def clean_name(name):
    # Remove Inc., Corp, etc for cleaner guessing
    return name.lower().replace(" inc.", "").replace(" corporation", "").replace(" group", "").replace(" limited", "").replace("technologies", "").strip()

def probe_url(url):
    try:
        r = requests.head(url, timeout=3, allow_redirects=True)
        if r.status_code == 200:
            return r.url
        # Try getting if head fails (some servers block HEAD)
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            return r.url
    except:
        pass
    return None

def discover():
    # Load H1B List
    with open(H1B_FILE, 'r') as f:
        h1b_list = json.load(f)

    # Load Existing Companies
    with open(EXISTING_COMPANIES_FILE, 'r') as f:
        existing_list = json.load(f)
        
    # Create Map of Existing URLs
    existing_map = {}
    for c in existing_list:
        existing_map[c['name'].lower()] = c['url']
        # Also map short names if possible?
        
    updated_list = []
    
    print(f"Processing {len(h1b_list)} companies...")
    
    for company in h1b_list:
        name = company['name']
        found_url = None
        
        # 1. Checks Manual Overrides
        if name in MANUAL_URLS:
            found_url = MANUAL_URLS[name]
            print(f"✅ {name}: Found in Manual List")
            
        # 2. Check Existing Companies.json
        elif name.lower() in existing_map:
            found_url = existing_map[name.lower()]
            print(f"✅ {name}: Found in Validated Map")
            
        # 3. Heuristic Probing
        if not found_url:
            cleaned = clean_name(name).replace(" ", "")
            candidates = [
                f"https://www.{cleaned}.com/careers",
                f"https://careers.{cleaned}.com/",
                f"https://www.{cleaned}.com/jobs"
            ]
            
            print(f"❓ {name}: Probing...")
            for url in candidates:
                real_url = probe_url(url)
                if real_url:
                    found_url = real_url
                    print(f"  -> Found: {found_url}")
                    break
            
            if not found_url:
                print(f"  ❌ Could not guess for {name}")

        company['url'] = found_url if found_url else "Unknown"
        updated_list.append(company)
        
        # Rate limit probing
        if not found_url: 
            time.sleep(0.5) 

    # Save
    with open(H1B_FILE, 'w') as f:
        json.dump(updated_list, f, indent=4)
        
    print(f"\nDone. Updated {H1B_FILE}")

if __name__ == "__main__":
    discover()
