import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
H1B_FILE = os.path.join(BASE_DIR, "career_scraper_dashboard", "uscis_h1b_top_list.json")
COMPANIES_FILE = os.path.join(BASE_DIR, "career_scraper_dashboard", "companies.json")

def sync():
    with open(H1B_FILE, 'r') as f:
        h1b_list = json.load(f)
        
    with open(COMPANIES_FILE, 'r') as f:
        companies = json.load(f)
        
    # Create valid map
    existing_companies = {c['name']: c for c in companies}
    
    added_count = 0
    updated_count = 0
    
    for h1b in h1b_list:
        name = h1b['name']
        url = h1b.get('url')
        
        if not url or url == "Unknown" or "hugedomains" in url:
            continue
            
        category = "H1B Sponsor Top 100"
        industry = h1b.get('industry', 'Unknown')
        
        # Check if exists
        if name in existing_companies:
            # Update category/URL if needed?
            # Prefer existing URL if it was manual? No, prefer discovered if existing was generic?
            # Let's trust existing manual entries in companies.json if they exist.
            # But we can tag them as H1B Sponsor.
            pass 
        else:
            # Add new
            new_entry = {
                "name": name,
                "url": url,
                "ats": "custom", # Default to Generic Scraper
                "category": category,
                "funding": f"H1B Rank #{h1b.get('rank', '?')}"
            }
            companies.append(new_entry)
            added_count += 1
            print(f"Added {name} -> {url}")
            
    with open(COMPANIES_FILE, 'w') as f:
        json.dump(companies, f, indent=4)
        
    print(f"Sync Complete. Added {added_count} new companies.")

if __name__ == "__main__":
    sync()
