import re
from urllib.parse import urlparse, parse_qs

def extract_job_title_diagnostic(url, page_text):
    """
    Improved title extraction logic for verification.
    """
    print(f"DEBUG: Processing URL: {url}")
    
    # 1. Try URL parameters (highest priority)
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    title_from_url = query_params.get('jobtitle', [None])[0]
    
    if title_from_url:
        # Decode URL encoding (e.g., + to space)
        title_from_url = title_from_url.replace('+', ' ')
        print(f"✓ Found title in URL: {title_from_url}")
        return title_from_url

    # 2. Try refined page text scan (fallback)
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    
    # Common UI terms to skip
    ui_keywords = (
        'Search', 'My', 'Home', 'Profile', 'Create', 'Log', 'Language', 
        'Register', 'Sign', 'Welcome', 'Portal', 'Help', 'Navigation'
    )
    
    for line in lines[:20]:
        # Filter: 15-100 chars, no UI keywords at start, not too many special chars
        if (len(line) > 10 and len(line) < 100 and 
            not line.startswith(ui_keywords) and
            not any(btn in line for btn in ['Details', 'Apply', 'Submit'])):
            print(f"✓ Found title in page text: {line}")
            return line
            
    return "Unknown Job Title"

# --- TEST CASES ---

# Test Case 1: Real JobDiva structure with query param
url1 = "https://www2.jobdiva.com/portal/?a=z1jdnwvsl6ckfah57w51w0ybh73vlo09791ws6svfl6o610e858y169jdhdqs4jb&compid=-1#/jobs/27448462?jobtitle=Employee+Benefits+Trainer+%2F+Open+Enrollment+Expert"
page_text1 = """
Register With Us
My Profile
Log In
Employee Benefits Trainer / Open Enrollment Expert
Position Type: Contractor
Compensation: $60/hr
"""

print("\n--- Test Case 1: URL Parameter Priority ---")
title1 = extract_job_title_diagnostic(url1, page_text1)
assert "Employee Benefits Trainer" in title1
print(f"FINAL TITLE: {title1}")

# Test Case 2: URL missing param, fallback to text scan
url2 = "https://www2.jobdiva.com/portal/#/jobs/12345"
page_text2 = """
Welcome to the Portal
Register With Us
Search Jobs
Senior Software Engineer (Python/AWS)
Location: New York
Responsibilities: Build awesome things.
"""

print("\n--- Test Case 2: Fallback to Refined Text Scan ---")
title2 = extract_job_title_diagnostic(url2, page_text2)
assert "Senior Software Engineer" in title2
print(f"FINAL TITLE: {title2}")
