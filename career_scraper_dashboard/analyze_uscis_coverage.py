import json
import os

# Load USCIS List
with open("career_scraper_dashboard/uscis_h1b_top_list.json", "r") as f:
    uscis_list = json.load(f)

# Load Current Dashboard List
with open("career_scraper_dashboard/companies.json", "r") as f:
    dashboard_list = json.load(f)

# Normalize names for comparison (simple lower case check)
dashboard_names = {c["name"].lower().split("(")[0].strip() for c in dashboard_list}
uscis_names = {c["name"].lower().split("(")[0].strip() for c in uscis_list}

missing_from_dashboard = []
for c in uscis_list:
    clean_name = c["name"].lower().split("(")[0].strip()
    if clean_name not in dashboard_names:
        missing_from_dashboard.append(c["name"])

print(f"Total USCIS Top Targets: {len(uscis_list)}")
print(f"Total Current Dashboard Targets: {len(dashboard_list)}")
print(f"Missing High-Value Targets ({len(missing_from_dashboard)}):")
for m in missing_from_dashboard:
    print(f" - {m}")
