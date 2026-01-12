import time
import random
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
PROFILE_PATH = "profile.json"
RESUME_PATH = "TEST_GREENHOUSE/Job1/NuthanReddy.pdf" # Adjusted path
TEST_URL = "https://job-boards.greenhouse.io/alma/jobs/8369573002"

# --- MOCK AI (Day 1) ---
def mock_ai_answer(question_text, profile):
    """Heuristic logic to answer screening questions without API."""
    q = question_text.lower()
    
    # Sponsorship / Visa
    if "sponsorship" in q or "visa" in q:
        if "not" in q or "don't" in q: return "Yes" # "Do you NOT need?"
        return "No" # "Do you need?"
    if "authorized" in q or "legally" in q: return "Yes"
    
    # Demographics
    if "veteran" in q: return "I am not a protected veteran"
    if "disability" in q: return "No, I do not have a disability"
    if "gender" in q: return profile.get("gender", "Male")
    if "race" in q: return profile.get("race", "Asian")
    
    # Agreements
    if "agree" in q or "certify" in q: return "Yes"
    
    # Salary
    if "salary" in q or "compensation" in q: return profile.get("salary_expectation", "Negotiable")
    
    return "Yes" # Safe fallback

def mock_ai_select(label_text, options, profile):
    """Heuristic logic to pick dropdown option."""
    label = label_text.lower()
    target = ""
    
    if "gender" in label: target = profile.get("gender", "Male")
    elif "race" in label: target = profile.get("race", "Asian")
    elif "veteran" in label: target = "not" # "I am not..."
    elif "disability" in label: target = "No"
    elif "location" in label: target = "Dallas"
    elif "hear" in label: target = "LinkedIn"
    
    # Fuzzy match
    for opt in options:
        if target.lower() in opt.lower():
            return opt
    return options[0] # Fallback to first

# --- HUMAN HELPERS ---
def human_type(locator, text):
    locator.click()
    time.sleep(random.uniform(0.1, 0.3))
    locator.fill(text) # Fill is safer than type for long text initially
    time.sleep(random.uniform(0.1, 0.3))

def human_click(page, locator):
    locator.scroll_into_view_if_needed()
    time.sleep(random.uniform(0.3, 0.7))
    locator.click()

# --- MAIN LOGIC ---
def apply_to_greenhouse_job(url, profile, resume_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"🚀 Navigating to: {url}")
        page.goto(url)
        time.sleep(2)
        
        # 1. Basic Info
        print("📝 Filling Basic Info...")
        try:
            page.get_by_label("First Name").fill(profile["first_name"])
            page.get_by_label("Last Name").fill(profile["last_name"])
            page.get_by_label("Email").fill(profile["email"])
            page.get_by_label("Phone").fill(profile["phone"])
        except Exception as e:
            print(f"⚠️ Basic Info Error: {e}")

        # 2. Resume Upload
        print("📄 Uploading Resume...")
        resume_input = page.locator("#resume") # Specific ID
        if resume_input.count() > 0:
            resume_input.set_input_files(str(resume_path))
            time.sleep(2) # Wait for parse
        
        # 3. Dynamic Fields & Dropdowns
        print("🧠 Handling Questions...")
        fields = page.locator("div.field").all()
        
        for field in fields:
            label = field.locator("label").first
            if label.count() == 0: continue
            label_text = label.inner_text().strip()
            
            # React-Select Dropdown
            control = field.locator("div[class*='control']").first
            if control.count() > 0:
                print(f"  dropdown: {label_text}")
                human_click(page, control)
                time.sleep(0.5)
                
                # Get options
                options_loc = page.locator("div[class*='menu'] div[class*='option']")
                options = options_loc.all_inner_texts()
                if options:
                    choice = mock_ai_select(label_text, options, profile)
                    print(f"    -> Selecting: {choice}")
                    # Click option
                    opt_loc = options_loc.filter(has_text=choice).first
                    if opt_loc.count() > 0:
                        opt_loc.click()
                    else:
                        control.click() # Close if fail
                continue
                
            # Text/Textarea Questions
            inp = field.locator("input[type='text'], textarea").first
            if inp.count() > 0 and not inp.input_value():
                answer = mock_ai_answer(label_text, profile)
                print(f"  typing: {label_text} -> {answer}")
                human_type(inp, answer)

        # 4. Safety Brake
        print("\n🛑 PAUSED FOR VERIFICATION")
        input("Press Enter to SUBMIT application...")
        
        # 5. Submit
        print("🚀 Clicking Submit...")
        submit_btn = page.locator("#submit_app, #submit_application, button:has-text('Submit Application')").first
        if submit_btn.count() > 0:
            human_click(page, submit_btn)
            print("✅ Submitted!")
            time.sleep(5)
        else:
            print("⚠️ Submit button not found!")
        
        browser.close()

if __name__ == "__main__":
    if not Path(PROFILE_PATH).exists():
        print("❌ Profile not found")
        exit()
        
    profile = json.loads(Path(PROFILE_PATH).read_text())
    apply_to_greenhouse_job(TEST_URL, profile, RESUME_PATH)
