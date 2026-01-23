import json
import os

PATH = "career_scraper_dashboard/companies.json"

def update():
    with open(PATH, 'r') as f:
        data = json.load(f)
        
    count = 0
    for c in data:
        if "EY" in c['name'] or "Ernst & Young" in c['name']:
            c['url'] = "https://ey.jobs"
            # Tag it so monitor uses smart scraper? 
            # monitor.py currently checks "EY" in name, so no extra tag needed.
            print(f"Updated {c['name']} -> https://ey.jobs")
            count += 1
            
    with open(PATH, 'w') as f:
        json.dump(data, f, indent=4)
        print(f"Saved {count} updates.")

if __name__ == "__main__":
    update()
