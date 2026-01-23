from smart_scraper import scrape_with_ai
import json

# EY Career Page (from discovery or manual)
# Note: EY often redirects or uses dynamic content. Let's try the URL we discovered or a known one.
# Re-using the manual one from discover_urls.py: "https://www.ey.com/en_us/careers"
URL = "https://ey.jobs"

print(f"Testing Smart Scraper on: {URL}")
jobs = scrape_with_ai(URL, "EY")

print("\n--- Results ---")
print(json.dumps(jobs, indent=2))
