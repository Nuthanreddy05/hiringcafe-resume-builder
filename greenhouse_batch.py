import time
import random
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
PROFILE_PATH = "profile.json"
# We will iterate this list in production. For test, we use the same one multiple times.
TEST_URLS = [
    "https://job-boards.greenhouse.io/alma/jobs/8369573002",
    # Add more URLs here
]
RESUME_PATH = "TEST_GREENHOUSE/Job1/NuthanReddy.pdf" 

# --- REUSED LOGIC FROM MVP (Ideally imported, but keeping standalone for clarity) ---
def mock_ai_answer(question_text, profile):
    """Heuristic logic to answer screening questions."""
    q = question_text.lower()
    if "sponsorship" in q or "visa" in q:
        if "not" in q or "don't" in q: return "Yes"
        return "No"
    if "authorized" in q or "legally" in q: return "Yes"
    if "veteran" in q: return "I am not a protected veteran"
    if "disability" in q: return "No, I do not have a disability"
    if "gender" in q: return profile.get("gender", "Male")
    if "race" in q: return profile.get("race", "Asian")
    if "agree" in q or "certify" in q: return "Yes"
    if "salary" in q or "compensation" in q: return profile.get("salary_expectation", "Negotiable")
    return "Yes"

def mock_ai_select(label_text, options, profile):
    """Heuristic logic to pick dropdown option."""
    label = label_text.lower()
    target = ""
    if "gender" in label: target = profile.get("gender", "Male")
    elif "race" in label: target = profile.get("race", "Asian")
    elif "veteran" in label: target = "not"
    elif "disability" in label: target = "No"
    elif "location" in label: target = "Dallas"
    elif "hear" in label: target = "LinkedIn"
    
    for opt in options:
        if target.lower() in opt.lower(): return opt
    return options[0]

def human_type(locator, text):
    locator.click()
    time.sleep(random.uniform(0.1, 0.3))
    locator.fill(text)
    time.sleep(random.uniform(0.1, 0.3))

def human_click(page, locator):
    locator.scroll_into_view_if_needed()
    time.sleep(random.uniform(0.3, 0.7))
    locator.click()

def fill_greenhouse_page(page, url, profile, resume_path):
    print(f"🚀 Processing Tab: {url}")
    page.goto(url)
    time.sleep(2)
    
    # 1. Basic Info
    try:
        page.get_by_label("First Name").fill(profile["first_name"])
        page.get_by_label("Last Name").fill(profile["last_name"])
        page.get_by_label("Email").fill(profile["email"])
        page.get_by_label("Phone").fill(profile["phone"])
    except: pass

    # 2. Resume
    # Note: resume path must be absolute for CDP sometimes, or relative to where script runs
    # We use absolute to be safe
    abs_resume_path = str(Path(resume_path).resolve())
    resume_input = page.locator("#resume")
    if resume_input.count() > 0:
        try:
            resume_input.set_input_files(abs_resume_path)
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Upload Error: {e}")

    # 3. Questions
    fields = page.locator("div.field").all()
    for field in fields:
        label = field.locator("label").first
        if label.count() == 0: continue
        label_text = label.inner_text().strip()
        
        # Dropdowns
        control = field.locator("div[class*='control']").first
        if control.count() > 0:
            human_click(page, control)
            time.sleep(0.5)
            options = page.locator("div[class*='menu'] div[class*='option']").all_inner_texts()
            if options:
                choice = mock_ai_select(label_text, options, profile)
                page.locator(f"div[class*='menu'] div[class*='option']").filter(has_text=choice).first.click()
            continue
            
        # Text
        inp = field.locator("input[type='text'], textarea").first
        if inp.count() > 0 and not inp.input_value():
            answer = mock_ai_answer(label_text, profile)
            human_type(inp, answer)

    print(f"✅ Tab Complete (Ready for Review): {url}")


# --- BATCH RUNNER ---
def run_batch():
    if not Path(PROFILE_PATH).exists():
        print("❌ Profile not found")
        return

    profile = json.loads(Path(PROFILE_PATH).read_text())
    
    print("🔌 Connecting to Chrome (Persistent)...")
    try:
        with sync_playwright() as p:
            # Connect to existing Chrome
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0] # Use the default context
            
            for url in TEST_URLS:
                # Open NEW tab for each job
                page = context.new_page()
                fill_greenhouse_page(page, url, profile, RESUME_PATH)
                # DO NOT CLOSE PAGE
                
            print("\n🏁 BATCH COMPLETE.")
            print("👉 Go to Chrome. You should see open tabs filled out.")
            print("👉 Review and Submit manually.")
            
            # We disconnect, but browser stays open
            browser.disconnect()
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("💡 Did you launch Chrome with '--remote-debugging-port=9222'?")

if __name__ == "__main__":
    run_batch()
