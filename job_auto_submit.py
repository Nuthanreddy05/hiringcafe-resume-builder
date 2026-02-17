#!/usr/bin/env python3
"""
Job Auto-Submitter
Iterates through generated job folders and applies to supported ATS (Greenhouse, Lever, Workday).

Usage:
    python job_auto_submit.py --jobs_dir ./application_packages --profile profile.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import gmail_helper

from playwright.sync_api import sync_playwright, Page, Locator
from submission_tracker import SubmissionTracker, check_before_applying, mark_job_submitted
from openai import OpenAI
import random
import numpy as np
from playwright_stealth.stealth import Stealth
import re
import time


# ============================================================================
# Stealth & Human Input Helpers
# ============================================================================

def human_sleep(min_ms=500, max_ms=1000):
    time.sleep(random.randint(min_ms, max_ms) / 1000)

def human_type(locator: Locator, text: str):
    """Types text with random delays between key presses."""
    if not text: return
    try:
        # Ensure field is ready
        locator.scroll_into_view_if_needed()
        locator.wait_for(state="visible", timeout=5000)
        
        # Click to focus
        locator.click()
        time.sleep(0.2)
        
        # Clear existing text
        locator.fill("")  # Fastest way to clear
        time.sleep(0.1)
       
        # Type text
        locator.press_sequentially(text, delay=random.randint(30, 80))
        
        # Verify it actually filled
        actual_value = locator.input_value()
        if actual_value != text:
            # Press_sequentially failed, use fill as backup
            locator.fill(text)
            
    except Exception as e:
        # Fallback to simple fill
        try:
            locator.fill(text)
        except Exception as e2:
            print(f"      ❌ Failed to fill field: {str(e2)[:50]}")

def get_bezier_curve(p0, p1, p2, p3):
    """Generates points for a Bezier curve."""
    t = np.linspace(0, 1, num=50) # 50 steps
    points = []
    for i in t:
        x = (1-i)**3*p0[0] + 3*(1-i)**2*i*p1[0] + 3*(1-i)*i**2*p2[0] + i**3*p3[0]
        y = (1-i)**3*p0[1] + 3*(1-i)**2*i*p1[1] + 3*(1-i)*i**2*p2[1] + i**3*p3[1]
        points.append((x, y))
    return points

def human_click(page: Page, locator: Locator):
    """Moves mouse in a curve to the element and clicks."""
    try:
        # Get target bounding box
        box = locator.bounding_box()
        if not box:
            locator.click(force=True) # Fallback
            return

        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        
        # Add random offset within the element
        offset_x = random.uniform(-box["width"]/4, box["width"]/4)
        offset_y = random.uniform(-box["height"]/4, box["height"]/4)
        target_x += offset_x
        target_y += offset_y

        # Start position (current mouse pos)
        # Note: Playwright doesn't expose current mouse pos easily in sync API 
        # without tracking. We'll assume start is (0,0) or last known.
        # Ideally we would track it, but for now we just move.
        
        # Simpler approach: built-in mouse.move with steps if we don't have start pos
        # But to do bezier we need start.
        # Let's just use page.mouse.move with steps for now (simulates linearity speed at least)
        # To do true bezier, we'd need to know where we are.
        
        # "Stealth" library might handle this? No, it handles headers.
        
        # Simplified Human Move:
        # 1. Move to a random point "near" the target first
        # 2. Then move to target
        
        page.mouse.move(target_x, target_y, steps=random.randint(10, 25))
        page.wait_for_timeout(random.randint(50, 200))
        page.mouse.down()
        page.wait_for_timeout(random.randint(20, 100))
        page.mouse.up()
        
    except Exception as e:
        # print(f"      ⚠️  Human Click Error: {e}")
        locator.click(force=True)

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("⚠️  DEEPSEEK_API_KEY not set. text generation will fail.")

# ============================================================================
# AI Question Answering
# ============================================================================

def answer_question_with_ai(question: str, context: str, custom_answers: Optional[Dict[str, str]] = None) -> str:
    """
    Uses DeepSeek to answer application questions based on JD + Resume + Profile.
    """
    q_lower = question.lower()
    
    # 0. Check User-Defined Custom Answers (Highest Priority)
    if custom_answers:
        for keyword, answer in custom_answers.items():
            if keyword.lower() in q_lower:
                print(f"      🎯 Custom Answer Matched ('{keyword}'): {answer}")
                return answer

    # Quick filter for simple questions to save API calls
    
    # Load comprehensive profile if available
    complete_profile_path = Path(__file__).parent / "complete_profile.json"
    complete_profile = {}
    if complete_profile_path.exists():
        try:
            with open(complete_profile_path) as f:
                complete_profile = json.load(f)
        except:
            pass
    
    # SALARY QUESTIONS - Use user's expectations
    if any(word in q_lower for word in ['salary', 'compensation', 'pay expectations', 'expected salary', 'salary range']):
        return "$100,000 - $120,000"
    
    # SPECIFIC LOCATION QUESTIONS - User is NOT in these regions
    if any(region in q_lower for region in ['spain', 'portugal', 'cyprus', 'poland', 'serbia', 'georgia', 'armenia', 'turkey']):
        if 'located' in q_lower or 'are you' in q_lower:
            return "No"
    
    # LANGUAGE QUESTIONS - User doesn't speak Russian
    if 'russian' in q_lower and ('speak' in q_lower or 'fluently' in q_lower):
        return "No"
    
    # PHONE NUMBER - If asking for phone itself, not yes/no
    if q_lower.strip() in ['phone', 'phone number'] or (q_lower.startswith('phone') and '?' not in q_lower):
        return ""  # Let system handle from profile
    
    # ============================================================
    # SPONSORSHIP - ALWAYS ANSWER "NO" (Strategic for screening)
    # ============================================================
    if "sponsorship" in q_lower or "visa sponsorship" in q_lower:
        # All variations: "Do you need", "Will you require", "Do you now or in the future"
        return "No"
    
    # WORK AUTHORIZATION - Professional answer
    if "authorized" in q_lower or "legally" in q_lower:
        if "united states" in q_lower or "us" in q_lower or "work" in q_lower:
            return complete_profile.get("work_authorization", {}).get("professional_answer_authorized", 
                "Yes, I am currently authorized to work in the United States.")
    
    # VISA STATUS - If specifically asked (rare)
    if "visa status" in q_lower or "immigration status" in q_lower or "f1" in q_lower or "opt" in q_lower:
        return complete_profile.get("work_authorization", {}).get("visa_status_if_asked", 
            "Authorized to work in the United States")
    
    # ============================================================
    # DEMOGRAPHIC QUESTIONS (EEO - Equal Employment Opportunity)
    # ============================================================
    
    # GENDER
    if "gender" in q_lower:
        return "Male"
    
    # RACE/ETHNICITY
    if "race" in q_lower or "ethnicity" in q_lower:
        if "hispanic" in q_lower or "latino" in q_lower:
            return "No"
        return "Asian"
    
    # MILITARY/VETERAN STATUS
    if "veteran" in q_lower or "military" in q_lower:
        return "I am not a protected veteran"
    
    # DISABILITY
    if "disability" in q_lower or "disabled" in q_lower:
        return "No"
    
    # LOCATION/CITY (for dropdown selection)
    if ("city" in q_lower or "location" in q_lower) and ("where" in q_lower or "select" in q_lower or "drop" in q_lower):
        # Try common variations
        if "arlington" in context.lower():
            return "Arlington"
        return "Dallas"  # Fallback
    
    # START DATE
    if "start" in q_lower and ("date" in q_lower or "available" in q_lower or "when" in q_lower):
        return complete_profile.get("availability", {}).get("start_date_professional", 
            "I am available to start within one week of receiving and accepting an offer")
    # Strict heuristics for user specific rules
    # 1. Past Employment at TARGET company (User only worked at Albertsons/ValueLabs)
    # PitchBook/Morningstar specific check
    if any(k in q_lower for k in ["worked for us", "worked for this company", "pitchbook", "morningstar", "employment with"]):
        return "No"
    
    # 2. Relocation (User is "comfortable with any option, like yes")
    if "relocat" in q_lower or "onsite" in q_lower or "financial assistance" in q_lower:
        return "Yes"
        
    # 3. Agreements
    if any(k in q_lower for k in ["agree", "policy", "privacy", "terms", "acknowledge"]):
        return "Yes"
        
    # 4. Identity
    if "race" in q_lower:
        return "Asian"
    
    # 5. Preferred Name (Text Field)
    if "preferred" in q_lower and "name" in q_lower:
        return "Nuthan"
    
    # 6. Start Date
    if "start" in q_lower and "date" in q_lower and "available" in q_lower:
        return "January 20, 2026"
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "Yes" # Default fallback
    
    prompt = f"""
    You are a professional software engineer candidate applying for a job.
    Question: "{question}"
    
    CONTEXT (JD, Resume, Profile):
    {context}
    
    INSTRUCTIONS:
    1. Answer as if you are the candidate (First person "I").
    2. Be EXTREMELY LOGICAL and professional. Write like a "smart friend" helping out - confident but grounded.
    3. Use the CANDIDATE PROFILE & WORK EXPERIENCE data strictly. 
       - If asked about Salary, use the "Preferred Salary" from context.
       - If asked about Start Date, use the "Available Start Date" from context.
       - If asked about Address/Location, use the "Address" from context.
       - If asked about "Current Employer", use "Albertsons Companies".
       - If asked about "Previous Employer", use "ValueLabs".
    4. CRITICAL FACT EXTRACTION RULE:
       - If the question asks for "Company Name", "Employer", "Job Title", or "Dates", OUTPUT ONLY THE VALUE.
       - DO NOT write full sentences like "I am currently employed at...". 
       - Correct Example: "Albertsons Companies"
       - Incorrect Example: "My current company is Albertsons Companies."
    5. For open-ended questions (e.g., "Why this job?", "Future goals"):
       - Connect the JD requirements to the Resume experience.
       - Suggest wanting to "grow with the team", "implement high-quality code", and "improve data processes".
    6. Output ONLY the answer text. No "Here is the answer:" prefix.
    """
    
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful, logical assistant for job applications. You extract facts precisely."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"      ⚠️  AI Answer Error: {e}")
        return "I am very interested in this role and believe my skills in software engineering make me a strong candidate."

        return "I am very interested in this role and believe my skills in software engineering make me a strong candidate."

        return "I am very interested in this role and believe my skills in software engineering make me a strong candidate."

def validate_and_fix_form(page: Page, profile: Dict[str, Any], context_text: str) -> bool:
    """
    Scans for empty REQUIRED inputs and attempts to AUTO-FIX them.
    Returns True if valid (or fixed), False if manual intervention needed.
    """
    print("      🔎 VALIDATING & FIXING FORM...")
    page.wait_for_timeout(1000)
    
    issues_found = False
    
    # helper to fix
    def attempt_fix(element, label_text):
        print(f"      🔧 Auto-Fixing: {label_text}...")
        try:
            # 1. Answer with AI/Profile Logic
            answer = ""
            label_lower = label_text.lower()
            
            # Quick profile lookups
            if "phone" in label_lower: answer = profile["phone"]
            elif "email" in label_lower: answer = profile["email"]
            elif "first" in label_lower: answer = profile["first_name"]
            elif "last" in label_lower: answer = profile["last_name"]
            elif "linkedin" in label_lower: answer = profile.get("linkedin", "")
            elif "website" in label_lower: answer = profile.get("linkedin", "")
            elif "city" in label_lower: answer = "New York, NY"
            else:
                 # Fallback to AI
                 answer = answer_question_with_ai(label_text, context_text)
            
            if answer:
                print(f"      Typing Fix: {answer}")
                human_type(element, answer)
                return True
        except Exception as e:
            print(f"      ❌ Fix Failed: {e}")
        return False

    # 1. Check Standard Inputs with 'required' attribute
    req_inputs = page.locator("input[required], select[required], textarea[required]").all()
    for el in req_inputs:
        try:
            if not el.is_visible(): continue
            val = el.input_value()
            if not val:
                 # Get Label
                 label_txt = "Unknown Field"
                 id_val = el.get_attribute("id")
                 if id_val:
                     lbl = page.locator(f"label[for='{id_val}']").first
                     if lbl.count() > 0: label_txt = lbl.inner_text().strip()
                 
                 print(f"      ⚠️  MISSING REQUIRED: {label_txt}")
                 
                 # ATTEMPT FIX
                 fixed = attempt_fix(el, label_txt)
                 
                 # Re-check
                 if not el.input_value():
                     el.scroll_into_view_if_needed()
                     page.evaluate("el => el.style.border = '3px solid red'", el)
                     issues_found = True
        except: pass

    # 2. Check by Label Text (Visual Check for *)
    labels_with_star = page.locator("label:has-text('*')").all()
    for lbl in labels_with_star:
        try:
            if not lbl.is_visible(): continue
            txt = lbl.inner_text().strip()
            
            field_div = lbl.locator("xpath=..") 
            inp = field_div.locator("input, select, textarea").first
            
            if field_div.locator("div[class*='control']").count() > 0:
                 # React Select - Hard to auto-fix generically without complex logic
                 # For now, just flag it
                 has_val = field_div.locator("div[class*='singleValue']").count() > 0
                 if not has_val:
                     print(f"      ⚠️  MISSING REQUIRED (Dropdown): {txt}")
                     field_div.scroll_into_view_if_needed()
                     page.evaluate("el => el.style.border = '3px solid red'", field_div.locator("div[class*='control']").first)
                     issues_found = True
            elif inp.count() > 0:
                if not inp.input_value():
                    print(f"      ⚠️  MISSING REQUIRED: {txt}")
                    
                    # ATTEMPT FIX
                    attempt_fix(inp, txt)
                    
                    if not inp.input_value():
                        inp.scroll_into_view_if_needed()
                        page.evaluate("el => el.style.border = '3px solid red'", inp)
                        issues_found = True
                    
        except: pass
        
    if issues_found:
        print("      🛑 VALIDATION FAILED. Auto-fix could not resolve all fields.")
        return False
        
    print("      ✅ Validation Passed (Auto-Fix applied where needed).")
    return True

def handle_greenhouse(page: Page, profile: Dict[str, Any], resume_path: Path, submit: bool = False, context_text: str = "", batch: bool = False) -> str:
    """Fill Greenhouse application form sequentially (1-by-1) for human-like behavior."""
    print("      🟢 Detected: Greenhouse (Sequential Mode)")
    
    # STEP 1: Click "Apply" button if on job description page
    print("      🔍 Looking for Apply button...")
    apply_button_selectors = [
        "#submit_app",
        "a#apply_button",
        "button:has-text('Apply for this job')",
        "a:has-text('Apply for this job')",
        ".application-button",
        "[data-mapped='application-button']"
    ]
    
    for selector in apply_button_selectors:
        apply_btn = page.locator(selector).first
        if apply_btn.count() > 0 and apply_btn.is_visible():
            print(f"      ✅ Found Apply button: {selector}")
            human_click(page, apply_btn)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)  # Wait for form to load
            break
    
    custom_answers = profile.get("custom_question_answers", {})
    
    # Locate all question fields
    # Strategy 1: Standard 'div.field'
    fields = page.locator("div.field").all()
    
    # Strategy 2: Question IDs (e.g. question_123)
    if not fields:
        print("      ⚠️  div.field not found. Trying div[id^='question']...")
        fields = page.locator("div[id^='question']").all()
        
    # Strategy 3: Labels (Parent Container) - Ultimate Fallback
    if not fields:
         print("      ⚠️  Still no fields. Trying all <label> parents...")
         labels = page.locator("label").all()
         # Unique parents only
         seen_parents = set()
         fields = []
         for lbl in labels:
             parent = lbl.locator("xpath=..")
             # Verify it's not empty/hidden
             if parent.is_visible():
                  fields.append(parent)
                  
    print(f"      📋 Found {len(fields)} fields. Processing 1-by-1...")
    
    for i, field in enumerate(fields):
        try:
            # 1. Scroll & Wait (Human Pacing)
            field.scroll_into_view_if_needed()
            time.sleep(1) # 1 second delay per user request
            
            # 2. Identify Label
            label_el = field.locator("label").first
            if label_el.count() == 0: continue
            
            label_text = label_el.inner_text().strip()
            label_lower = label_text.lower()
            if not label_text: continue
            
            # print(f"      Processing Field {i+1}: {label_text[:40]}...")

            # 3. Determine Field Type & Handle
            
            # --- A. Attachments (Resume/Cover Letter) ---
            if "resume" in label_lower or "cv" in label_lower or "cover letter" in label_lower:
                file_input = field.locator("input[type='file']").first
                if file_input.count() > 0:
                    current_val = file_input.input_value()
                    if not current_val:
                        print(f"      📄 Uploading Resume for: {label_text}")
                        file_input.set_input_files(str(resume_path))
                        time.sleep(1)
                continue

            # --- B. Dropdowns (React-Select or Standard) ---
            # Check for React-Select specific containers first
            # "control" class is typical for React-Select
            react_control = field.locator("div[class*='control'], div[class*='indicator']").first
            
            # Exclude standard inputs if they happen to live in a 'control' div (rare but possible)
            is_react = False
            if react_control.count() > 0:
                # Confirm it looks like a dropdown trigger
                if field.locator("div[class*='singleValue']").count() > 0 or field.locator("div[class*='placeholder']").count() > 0:
                    is_react = True
            
            if is_react:
                # Use improved AI answer function
                answer = answer_question_with_ai(label_text, context_text)
                
                # Override for specific patterns that need structured answers
                if "country" in label_lower and answer.lower() in ["yes", "no"]:
                    answer = "United States"
                elif "gender" in label_lower:
                    answer = profile.get("gender", "Male")
                elif "race" in label_lower:
                    answer = profile.get("race", "Asian")
                elif "veteran" in label_lower:
                    answer = profile.get("veteran", "I am not a protected veteran")
                elif "disability" in label_lower:
                    answer = profile.get("disability", "No, I do not have a disability")
                
                # Click logic
                print(f"      ⚛️  React-Select: '{label_text}' -> '{answer}'")
                human_click(page, react_control)
                page.wait_for_timeout(500)
                # Find option (using starts-with or contains for robustness)
                # "No" might be "No, I do not..."
                option = page.locator(f"div[role='option']:has-text('{answer}'), div[class*='option']:has-text('{answer}')").first
                
                # If short answer 'No'/'Yes', try exact first to avoid 'None' matching 'No'
                if answer in ["Yes", "No"]:
                     # Try strict starts-with first
                     opt_strict = page.locator(f"div[role='option']").filter(has_text=re.compile(f"^{answer}", re.IGNORECASE)).first
                     if opt_strict.count() > 0: option = opt_strict
                
                if option.count() > 0:
                    human_click(page, option)
                else:
                    print(f"      ⚠️  Option '{answer}' not found for {label_text}")
                    # Try closing
                    human_click(page, react_control)
                continue

            # --- C. Standard Inputs (Text / Email / Phone) ---
            input_el = field.locator("input[type='text'], input[type='email'], input[type='tel']").first
            if input_el.count() > 0 and input_el.is_visible():
                val = input_el.input_value()
                if val: continue # Already filled
                
                answer = ""
                # Map fields
                if "first" in label_lower and "name" in label_lower: answer = profile["first_name"]
                elif "last" in label_lower and "name" in label_lower: answer = profile["last_name"]
                elif "full" in label_lower and "name" in label_lower: answer = f"{profile['first_name']} {profile['last_name']}"
                elif "email" in label_lower: answer = profile["email"]
                elif "phone" in label_lower: answer = profile["phone"]  # Re-enabled
                elif "linkedin" in label_lower: answer = profile.get("linkedin", "")
                elif "website" in label_lower or "portfolio" in label_lower: answer = profile.get("portfolio") or profile.get("linkedin", "")
                elif "city" in label_lower: answer = "New York, NY" # Default or profile
                elif "company" in label_lower or "employer" in label_lower: answer = "Google" # Current
                
                if not answer:
                   # Fallback to AI
                   print(f"      🧠 AI Thinking: {label_text}")
                   answer = answer_question_with_ai(label_text, context_text)
                
                print(f"      ⌨️  Typing: {label_text} -> {answer}")
                human_type(input_el, answer)
                continue
                
            # --- D. Checkboxes ---
            checkbox = field.locator("input[type='checkbox']").first
            if checkbox.count() > 0:
                 if not checkbox.is_checked():
                     # Default to YES for consent/privacy
                     print(f"      ✅ Checking: {label_text}")
                     human_click(page, checkbox)
                 continue

        except Exception as e:
            print(f"      ⚠️  Error on field {i}: {e}")
            continue

    # UNIVERSAL RESUME UPLOAD - Multiple Strategies
    print("      📄 Looking for resume upload...")
    upload_success = False
    
    # Strategy 1: Try visible "Attach" or "Upload Resume" buttons first
    attach_buttons = page.locator("button:has-text('Attach'), a:has-text('Attach Resume'), button:has-text('Upload')").all()
    for btn in attach_buttons:
        if "resume" in btn.inner_text().lower() or btn.inner_text().strip() == "Attach":
            try:
                print(f"      🔘 Clicking: {btn.inner_text()}")
                human_click(page, btn)
                page.wait_for_timeout(1000)
                break
            except:
                pass
    
    # Strategy 2: Find all file inputs and try each
    file_inputs = page.locator("input[type='file']").all()
    print(f"      🔍 Found {len(file_inputs)} file input(s)")
    
    for idx, file_input in enumerate(file_inputs):
        try:
            # Check if this is a resume field (not cover letter)
            input_id = file_input.get_attribute("id") or ""
            input_name = file_input.get_attribute("name") or ""
            
            # Skip cover letter inputs
            if "cover" in input_id.lower() or "cover" in input_name.lower():
                print(f"      ⏭️  Skipping cover letter input")
                continue
            
            print(f"      📎 Attempting upload on input #{idx+1}...")
            file_input.set_input_files(str(resume_path))
            print(f"      ✅ Resume uploaded: {resume_path.name}")
            upload_success = True
            page.wait_for_timeout(2000)
            break
        except Exception as e:
            print(f"      ⚠️  Upload attempt #{idx+1} failed: {str(e)[:50]}")
            continue
    
    if not upload_success:
        print(f"      ⚠️  No resume upload field found (may upload later in flow)")


    # Run Validation
    is_valid = validate_and_fix_form(page, profile, context_text)
    if not is_valid:
        print("      ⚠️  Form has missing fields. Pausing for manual fix.")
        submit = False # Force manual mode

    # Final "Submit" button handling
    if submit:
        submit_btn = page.locator("#submit_app").first
        if submit_btn.count() > 0:
            human_click(page, submit_btn)
            return "Submitted"
            
    # Verification Pause (skip in batch mode)
    if not batch:
        print("      👀 Paused for manual review (Sequential Mode).")
        input("      Press Enter to finish...") 
    else:
        print("      ⏭️  Batch mode: Auto-proceeding to next job")
    
    return "Ready for Review"



def handle_workday(page: Page, profile: Dict[str, Any], resume_path: Path, submit: bool = False, context_text: str = "") -> str:
    """Fill Workday application form (Account Creation + Verification + Hybrid Upload)"""
    print("      🔵 Detected: Workday")

    # 1. Apply Button Strategy
    # Workday "Apply" buttons can be tricky (Apply, Apply Manually, etc.)
    print("      🖱️  Looking for Apply button...")
    applied = False
    for selector in [
        "button[data-automation-id='job-application-apply-button']", 
        "button:has-text('Apply')", 
        "a[data-automation-id='job-application-apply-button']",
        "div[data-automation-id='job-application-apply-div']"
    ]:
        if page.locator(selector).count() > 0:
            try:
                # Often "Apply" opens a modal or dropdown with "Apply Manually" vs "Autofill"
                human_click(page, page.locator(selector).first)
                page.wait_for_timeout(2000)
                
                # Check for "Apply Manually" sub-option
                manual_btn = page.locator("a:has-text('Apply Manually'), button:has-text('Apply Manually')")
                if manual_btn.count() > 0 and manual_btn.is_visible():
                     human_click(page, manual_btn.first)
                     page.wait_for_timeout(2000)
                
                applied = True
                break
            except: pass
            
    if not applied:
        print("      ⚠️  Could not find/click Apply. check if already logged in?")

    # 2. Account Creation / Sign In Check
    # We assume we need to create an account for each new Workday instance
    page.wait_for_timeout(3000)
    
    # Check if we are on Sign In / Create Account page
    if page.locator("text=Sign In").count() > 0 or page.locator("text=Create Account").count() > 0:
        
        # Check if we can just create account directly
        create_account_btn = page.locator("button:has-text('Create Account'), a:has-text('Create Account')").first
        
        if create_account_btn.count() > 0:
            print("      🆕 Clicking 'Create Account'...")
            human_click(page, create_account_btn)
            page.wait_for_timeout(2000)
            
            # Fill Create Account Form
            try:
                 print("      📝 Filling Account Details...")
                 # Email
                 email_input = page.locator("input[type='email'], input[data-automation-id='email'], input[aria-label='Email Address']").first
                 human_type(email_input, profile["email"])
                 
                 # Password
                 # Use a strong default. Workday requires: Upper, Lower, Number, Special.
                 pwd = profile.get("default_password", "ChangeMe123!@#") 
                 
                 # Find password inputs. Usually there is "Password" and "Verify Password"
                 pwd_inputs = page.locator("input[type='password']")
                 if pwd_inputs.count() >= 2:
                     human_type(pwd_inputs.nth(0), pwd)
                     human_type(pwd_inputs.nth(1), pwd)
                 elif pwd_inputs.count() == 1:
                     human_type(pwd_inputs.first, pwd)
                     
                 # Checkbox "I agree" (sometimes present)
                 cb = page.locator("input[type='checkbox']").first
                 if cb.count() > 0 and not cb.is_checked():
                      human_click(page, cb)
                      
                 page.wait_for_timeout(1000)
                 
                 # Submit Creation
                 create_submit = page.locator("button:has-text('Create Account'), button:has-text('Submit'), button[data-automation-id='createAccountButton']").first
                 human_click(page, create_submit)
                 
                 # 3. Verification Logic (Crucial for Workday)
                 print("      ⏳ Waiting for potential Verification (OTP)...")
                 page.wait_for_timeout(5000) 
                 
                 # Check if we are stuck on a "Verify" screen
                 # Look for "Enter Code", "Verification Code", etc.
                 verify_text = page.locator("text=Verification Code, text=Enter Code")
                 if verify_text.count() > 0:
                     print("      � Verification detected. Polling Gmail for 60s...")
                     
                     gu = os.getenv("GMAIL_USER")
                     gp = os.getenv("GMAIL_APP_PASSWORD")
                     
                     if gu and gp:
                         # Poll Gmail using helper
                         code_data = gmail_helper.check_for_verification_email(gu, gp, wait_seconds=60)
                         
                         if code_data and code_data["type"] == "code":
                             code = code_data["value"]
                             print(f"      ✅ Generated Code: {code}")
                             
                             # Find Code Input
                             code_input = page.locator("input[type='text'], input[type='tel'], input[aria-label='Code']").last
                             human_type(code_input, code)
                             
                             # Submit Verify
                             verify_btn = page.locator("button:has-text('Verify'), button:has-text('Submit')").first
                             human_click(page, verify_btn)
                             page.wait_for_timeout(3000)
                         else:
                             print("      ⚠️  No code found in Gmail. Manual intervention needed.")
                             # Do NOT return here, user might do it manually
                     else:
                         print("      ⚠️  No GMAIL env vars. Cannot auto-verify.")

            except Exception as e:
                print(f"      ⚠️  Account Creation Error: {e}")

    # 4. Resume Upload (Hybrid Strategy)
    # Once logged in, Workday usually asks for Resume upload first to parse properties
    print("      📄 Looking for Resume Upload...")
    page.wait_for_timeout(2000)
    
    # Try finding the file input. It's often hidden, with a label "Select File" or "Upload"
    try:
        # Check if we are on the upload page?
        # Often has text "Resume/CV" or "Quick Apply"
        
        # Locate file input
        file_input = page.locator("input[type='file']").first
        if file_input.count() > 0:
             print("      📤 Uploading PDF: " + str(resume_path.name))
             file_input.set_input_files(str(resume_path))
             
             # Workday takes time to parse and populate
             print("      ⏳ Waiting 5s for Workday Parser...")
             time.sleep(5)
             
             # Sometimes need to click "Continue" or "Next" to trigger parsing
             next_btn = page.locator("button[data-automation-id='bottom-navigation-next-button'], button:has-text('Next'), button:has-text('Continue')").first
             if next_btn.count() > 0 and next_btn.is_visible():
                  # human_click(page, next_btn) # Risk: Might skip review if parsing was fast
                  pass
        else:
            print("      ⚠️  Resume input not found (Maybe already uploaded?)")

    except Exception as e:
         print(f"      ⚠️  Resume Upload Error: {e}")

    # 5. Hybrid Pause
    # At this point, Resume is uploaded. Workday has parsed it. 
    # The fields (jobs, education) are likely populated but messy.
    # We DO NOT want to bot-fill them and create errors.
    
    if not submit: # If headless/auto-submit is FALSE
        print("\n" + "="*60)
        print("      🛑 WORKDAY HYBRID PAUSE")
        print("      To ensure 100% accuracy, relying on Workday's parser.")
        print("      ACTION: Please check the browser window.")
        print("      1. Verify parsed Resume data.")
        print("      2. Click 'Next' through the wizard.")
        print("      3. Submit manually.")
        print("="*60 + "\n")
        
        return "Paused for Manual Review (Hybrid)"

    # If --submit is true (Headless/Full Auto), we try to click through
    # This is risky for Workday but implemented for completeness
    try:
         print("      🚀 Attempting Auto-Submit (Risky)...")
         # Click Next repeatedly until "Submit" appears
         for i in range(5):
             next_btn = page.locator("button[data-automation-id='bottom-navigation-next-button']").first
             if next_btn.count() > 0 and next_btn.is_visible():
                 human_click(page, next_btn)
                 page.wait_for_timeout(2000)
             else:
                 break
         
         # Check for Review/Submit
         submit_btn = page.locator("button[data-automation-id='bottom-navigation-submit-button']").first
         if submit_btn.count() > 0:
              human_click(page, submit_btn)
              return "Submitted (Automated)"
              
    except Exception as e:
        pass

    return "Ready for Review (Workday Hybrid)"


def handle_taleo(page: Page, profile: Dict, resume_path: Path, submit: bool = False, context_text: str = "") -> str:
    """
    Automated handler for Taleo ATS.
    Creates account (or logs in), fills fields, uploads resume.
    """
    print("   🏢 Taleo ATS detected - Starting automation...")
    
    try:
        # Wait for page to load
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        
        # Step 0: Check if we're on a job description page (not application form yet)
        print("   🔍 Looking for Apply button...")
        
        # Common Taleo "Apply" button selectors (comprehensive list)
        apply_selectors = [
            # Text-based detection (most common)
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "input[value*='Apply']",
            
            # Attribute-based
            "a[title*='Apply']",
            "button[title*='Apply']",
            "a[aria-label*='Apply']",
            "button[aria-label*='Apply']",
            
            # Class and ID based
            "a.btn:has-text('Apply')",
            "#applybtn",
            ".apply-button",
            ".applyBtn",
            "a[href*='apply']",
            "button[id*='apply']",
            "a[id*='apply']",
            
            # Taleo-specific
            "span.pbButton:has-text('Apply')",
            "a.jobGlobalApplyButton",
            "input[name='apply']"
        ]
        
        apply_clicked = False
        for selector in apply_selectors:
            try:
                apply_btn = page.locator(selector).first
                if apply_btn.count() > 0 and apply_btn.is_visible():
                    print(f"   🎯 Found Apply button (selector: {selector[:30]}...), clicking...")
                    human_click(page, apply_btn)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(3)
                    apply_clicked = True
                    print("      ✅ Navigated to application form")
                    break
            except Exception as e:
                continue
        
        if not apply_clicked:
            print("      ℹ️  No Apply button found (might already be on application form)")
            # Try to detect if we're actually on login/application page
            if page.locator("input[type='email'], input[type='password'], textarea").count() > 0:
                print("      ✓ Detected form fields, proceeding with application")

        
        # Step 1: Check if already logged in or need to create account
        print("   📝 Checking login status...")
        
        # Look for "Apply as Guest" or "New User" button
        guest_btn = page.locator("text=/Apply as Guest/i").first
        new_user_btn = page.locator("text=/New User/i").first
        login_btn = page.locator("text=/Login|Sign In/i").first
        
        # Check if there's a login form (returning user)
        username_field = page.locator("input[name*='user'], input[name*='email'], input[id*='user']").first
        password_field = page.locator("input[type='password']").first
        
        if username_field.count() > 0 and password_field.count() > 0:
            print("   🔐 Logging in with existing account...")
            taleo_email = profile.get('taleo_email', 'nuthanreddy001@gmail.com')
            taleo_password = profile.get('taleo_password', '#Include789')
            
            human_type(username_field, taleo_email)
            human_type(password_field, taleo_password)
            
            login_submit = page.locator("button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign In')").first
            if login_submit.count() > 0:
                human_click(page, login_submit)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                print("      ✅ Logged in successfully")
        
        elif guest_btn.count() > 0 and guest_btn.is_visible():
            print("   👤 Applying as guest...")
            human_click(page, guest_btn)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
        elif new_user_btn.count() > 0 and new_user_btn.is_visible():
            print("   🆕 Creating new account...")
            human_click(page, new_user_btn)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            
            # Fill registration form if present
            email_field = page.locator("input[type='email'], input[name*='email'], input[id*='email']").first
            if email_field.count() > 0:
                # Use specific Taleo email
                taleo_email = profile.get('taleo_email', 'nuthanreddy001@gmail.com')
                human_type(email_field, taleo_email)
                print(f"      📧 Email: {taleo_email}")
                
            # Use specific Taleo password
            pwd_field = page.locator("input[type='password']").first
            if pwd_field.count() > 0:
                taleo_password = profile.get('taleo_password', '#Include789')
                human_type(pwd_field, taleo_password)
                print("      🔒 Password: ********")
                
            # Confirm password if required
            pwd_confirm = page.locator("input[type='password']").nth(1)
            if pwd_confirm.count() > 0 and pwd_confirm.is_visible():
                human_type(pwd_confirm, taleo_password)
                
            # Submit registration
            submit_reg = page.locator("button[type='submit'], input[type='submit']").first
            if submit_reg.count() > 0:
                human_click(page, submit_reg)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
        
        # Step 2: Fill application form
        print("   ✍️  Filling application fields...")
        
        # Common Taleo fields
        fields_to_fill = {
            "firstName": profile.get("first_name", ""),
            "lastName": profile.get("last_name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "city": profile.get("city", "Dallas"),
            "state": profile.get("state", "TX"),
            "zip": profile.get("zip", "75001"),
            "country": profile.get("country", "United States"),
            "linkedin": profile.get("linkedin", "https://www.linkedin.com/in/nuthan-reddy-vaddi-reddy/"),
            "salary": profile.get("salary_expectations", "100000-120000"),
        }
        
        filled_count = 0
        for field_name, value in fields_to_fill.items():
            if not value:
                continue
                
            # Try multiple selectors
            selectors = [
                f"input[name*='{field_name}']",
                f"input[id*='{field_name}']",
                f"input[placeholder*='{field_name}']",
            ]
            
            # Add field-specific selectors
            if field_name == "salary":
                selectors.extend([
                    "input[name*='salary']",
                    "input[name*='compensation']",
                    "input[name*='expected']",
                    "input[id*='salary']",
                    "input[id*='compensation']",
                    "input[placeholder*='salary']",
                    "textarea[name*='salary']",
                ])
            elif field_name == "linkedin":
                selectors.extend([
                    "input[name*='linkedin']",
                    "input[name*='LinkedIn']",
                    "input[id*='linkedin']",
                    "input[placeholder*='LinkedIn']",
                ])

            
            for selector in selectors:
                field = page.locator(selector).first
                if field.count() > 0 and field.is_visible():
                    try:
                        human_type(field, str(value))
                        filled_count += 1
                        time.sleep(0.5)
                        break
                    except:
                        pass
        
        print(f"      ✅ Filled {filled_count} fields")
        
        # Step 3: Upload Resume
        print("   📄 Uploading resume...")
        
        # Look for file upload field (including hidden ones)
        file_inputs = page.locator("input[type='file']").all()
        uploaded = False
        
        for idx, file_input in enumerate(file_inputs):
            try:
                # Try to upload even if not visible (some file inputs are hidden)
                file_input.set_input_files(str(resume_path))
                print(f"      ✅ Resume uploaded: {resume_path.name}")
                uploaded = True
                time.sleep(2)
                break
            except Exception as e:
                # Try clicking nearby label/button to reveal file input
                try:
                    parent = page.locator(f"input[type='file']:nth-child({idx + 1})").locator("xpath=ancestor::div[1]").first
                    upload_btn = parent.locator("button, a, label").first
                    if upload_btn.count() > 0:
                        human_click(page, upload_btn)
                        time.sleep(1)
                        # Try upload again
                        file_input.set_input_files(str(resume_path))
                        print(f"      ✅ Resume uploaded: {resume_path.name}")
                        uploaded = True
                        break
                except:
                    pass
                    
        if not uploaded:
            print(f"      ⚠️  Resume upload: No file input found or upload failed")
            print(f"      📂 Resume available at: {resume_path}")
        
        # Step 4: Answer common questions
        print("   💬 Answering screening questions...")
        
        # Work authorization
        auth_fields = page.locator("text=/authorized to work/i").all()
        for field in auth_fields[:3]:  # Limit to first 3
            try:
                parent = field.locator("xpath=ancestor::div[contains(@class, 'question') or contains(@class, 'field')]").first
                yes_option = parent.locator("text=/yes/i, input[value='Yes']").first
                if yes_option.count() > 0:
                    human_click(page, yes_option)
                    time.sleep(0.5)
            except:
                pass
        
        # Sponsorship
        sponsor_fields = page.locator("text=/sponsorship/i, text=/visa/i").all()
        for field in sponsor_fields[:3]:
            try:
                parent = field.locator("xpath=ancestor::div[contains(@class, 'question') or contains(@class, 'field')]").first
                no_option = parent.locator("text=/no/i, input[value='No']").first
                if no_option.count() > 0:
                    human_click(page, no_option)
                    time.sleep(0.5)
            except:
                pass
        
        # Step 5: AI-Powered Custom Questions
        print("   🤖 Using AI for custom questions...")
        
        # Find all text areas (essay questions like "Why interested?")
        textareas = page.locator("textarea").all()
        ai_answers = 0
        
        for textarea in textareas[:5]:  # Limit to first 5
            try:
                if not textarea.is_visible():
                    continue
                
                # Find the question label
                label = textarea.locator("xpath=preceding::label[1]").first
                if label.count() == 0:
                    # Try finding nearby text
                    parent = textarea.locator("xpath=ancestor::div[1]").first
                    label = parent.locator("label, legend, span").first
                
                if label.count() > 0:
                    question_text = label.inner_text()
                    
                    # Use AI to answer
                    print(f"      💬 Question: {question_text[:60]}...")
                    answer = answer_question_with_ai(question_text, context_text)
                    
                    # Type the answer
                    human_type(textarea, answer)
                    ai_answers += 1
                    time.sleep(1)
            except Exception as e:
                print(f"      ⚠️  Textarea error: {e}")
        
        print(f"      ✅ AI answered {ai_answers} custom questions")
        
        # Step 6: AI-Powered Dropdown Selection
        print("   🎯 AI selecting dropdowns...")
        
        # Find dropdowns (years of experience, etc.)
        selects = page.locator("select").all()
        dropdown_selected = 0
        
        for select in selects[:10]:  # Check first 10 dropdowns
            try:
                if not select.is_visible():
                    continue
                
                # Skip if already selected
                current_value = select.evaluate("el => el.value")
                if current_value and current_value != "":
                    continue
                
                # Find the question for this dropdown
                label = select.locator("xpath=preceding::label[1]").first
                if label.count() == 0:
                    parent = select.locator("xpath=ancestor::div[1]").first
                    label = parent.locator("label, legend").first
                
                if label.count() > 0:
                    question_text = label.inner_text()
                    
                    # Get all options
                    options = select.locator("option").all()
                    option_texts = [opt.inner_text() for opt in options if opt.inner_text().strip()]
                    
                    if len(option_texts) <= 1:  # Skip if no real options
                        continue
                    
                    # Use AI to select best option
                    print(f"      🔽 Dropdown: {question_text[:40]}...")
                    
                    ai_prompt = f"""
Question: {question_text}

Available options:
{chr(10).join(f"- {opt}" for opt in option_texts[:15])}

Based on this context:
{context_text[:2000]}

Select the MOST APPROPRIATE option. Output ONLY the exact option text, nothing else.
"""
                    
                    selected_option = answer_question_with_ai(ai_prompt, "")
                    selected_option = selected_option.strip()
                    
                    # Try to select the option
                    for opt_text in option_texts:
                        if selected_option.lower() in opt_text.lower() or opt_text.lower() in selected_option.lower():
                            select.select_option(label=opt_text)
                            print(f"         ✓ Selected: {opt_text}")
                            dropdown_selected += 1
                            time.sleep(0.5)
                            break
                    
            except Exception as e:
                print(f"      ⚠️  Dropdown error: {e}")
        
        print(f"      ✅ AI selected {dropdown_selected} dropdowns")

        
        print("   ✅ Taleo automation complete!")
        print("   ⏸️  Pausing for manual review...")
        
        return "Ready for Review (Taleo)"
        
    except Exception as e:
        print(f"   ❌ Taleo automation error: {e}")
        print("   📄 Resume available at:", resume_path)
        return "Manual Completion Required (Taleo - Error)"


def handle_custom(page: Page, profile: Dict, resume_path: Path, submit: bool = False, context_text: str = "") -> str:
    """
    Basic handler for custom career portals (MongoDB, SmartRecruiters, etc.)
    Opens the page and pauses for manual completion.
    """
    print("   🌐 Custom career portal detected")
    print("   ⚠️  Custom portal requires manual application")
    print(f"   📄 Resume ready: {resume_path}")
    print("   👉 Please complete the application manually in the browser")
    
    return "Manual Completion Required (Custom)"

def identify_ats(url: str) -> str:
    """Identify ATS from URL"""
    if "boards.greenhouse.io" in url:
        return "greenhouse"
    if "jobs.lever.co" in url:
        return "lever"
    if "workday" in url:
        return "workday"
    if "taleo.net" in url:
        return "taleo"
    if "mongodb.com/careers" in url or "smartrecruiters.com" in url or "ashbyh q.com" in url:
        return "custom"
    return "unknown"


# ============================================================================
# Main Logic
# ============================================================================

def process_job(
    job_dir: Path, 
    profile: Dict[str, Any], 
    context, 
    headless: bool = False,
    submit: bool = False,
    batch: bool = False
):
    """Process a single job folder"""
    
    resume_pdf = job_dir / "NuthanReddy.pdf"
    url_file = job_dir / "apply_url.txt"
    
    if not resume_pdf.exists():
        print(f"   ⚠️  No PDF found in {job_dir.name}")
        return "No PDF"
        
    if not url_file.exists():
        print(f"   ⚠️  No URL file found in {job_dir.name}")
        return "No URL"
        
    url = url_file.read_text().strip()
    if not url:
        return "Empty URL"
        
    ats = identify_ats(url)
    
    
    if ats == "unknown":
        print(f"   ❓ Unknown/Unsupported ATS: {url[:60]}...")
        return False
    
    
    if ats == "workday":
        print(f"   🚧 Workday detected: {url[:60]}...")
        # Fall through to logic below


    # Supported ATS
    print(f"   🔗 Opening {ats}: {url}")
    
    # Load context for AI from JD.txt AND Resume JSON
    context_text = ""
    try:
        jd_file = job_dir / "JD.txt"
        if jd_file.exists():
            context_text += f"\n\nJOB DESCRIPTION:\n{jd_file.read_text()[:6000]}"
            
        # Add Profile Context (Address, Salary, Start Date)
        from datetime import datetime, timedelta
        start_date = (datetime.now() + timedelta(days=10)).strftime("%m/%d/%Y")
        
        context_text += f"\n\nCANDIDATE PROFILE (JSON):\n"
        import json
        context_text += json.dumps(profile, indent=2)
        
        # Explicitly highlight key fields for safety
        context_text += f"\n\nSUMMARY for Quick Reference:\n"
        context_text += f"Name: {profile['first_name']} {profile['last_name']}\n"
        context_text += f"Email: {profile['email']}\n"
        context_text += f"Phone: {profile['phone']}\n"
        context_text += f"Address: {profile.get('address', 'Dallas, TX')}\n"
        context_text += f"Preferred Salary: {profile.get('salary_expectation', 'Negotiable')}\n"
        context_text += f"Available Start Date: {start_date}\n"
        context_text += f"Portfolio: {profile.get('portfolio', '')}\n"
        
        # Add Work Experience (Critical for Forms)
        if "experience" in profile:
            context_text += f"\nWORK EXPERIENCE (Use this strictly):\n"
            for exp in profile["experience"]:
                context_text += f"- Company: {exp.get('company')}\n"
                context_text += f"  Title: {exp.get('title')}\n"
                context_text += f"  Dates: {exp.get('dates')}\n"
                context_text += f"  Description: {exp.get('description')}\n"

        # Try to find Resume content
        # Usually in all_iterations.json or we can parse the tex?
        # Let's try to find 'all_iterations.json' which job_auto_apply_internet saves
        iter_file = job_dir / "all_iterations.json"
        if iter_file.exists():
             import json
             data = json.loads(iter_file.read_text())
             # Get the last iteration's content or summary
             if isinstance(data, list) and len(data) > 0:
                 last_iter = data[-1]
                 # If it has resume_json, dump it
                 if "resume_json" in last_iter:
                     context_text += f"\n\nRESUME CONTENT (For reference):\n{json.dumps(last_iter['resume_json'], indent=2)}"
        else:
            # Fallback to base.json if available
            base_json = job_dir.parent / "base_resume_data.json" # unlikely
            pass
            
    except Exception as e:
        print(f"      ⚠️  Context loading warning: {e}")

    page = context.new_page()
    Stealth().apply_stealth_sync(page) # Apply stealth to the actual job page
    try:
        page.goto(url, wait_until="domcontentloaded")
        
        status = "Failed"
        if ats == "greenhouse":
            status = handle_greenhouse(page, profile, resume_pdf, submit=submit, context_text=context_text, batch=batch)
        elif ats == "lever":
            status = handle_lever(page, profile, resume_pdf, submit=submit, context_text=context_text)
        elif ats == "workday":
            status = handle_workday(page, profile, resume_pdf, submit=submit, context_text=context_text)
        elif ats == "taleo":
            status = handle_taleo(page, profile, resume_pdf, submit=submit, context_text=context_text)
        elif ats == "custom":
            status = handle_custom(page, profile, resume_pdf, submit=submit, context_text=context_text)
            
        print(f"      ℹ️  Status: {status}")
        
        # If not headless and not batch, pause for manual review/submit
        if not headless and not batch:
            print("      👀 Paused for manual review. Check browser window.")
            print("      👉 ACTION REQUIRED: ")
            print("          1. Complete any CAPTHCA or missing fields.")
            print("          2. Click 'Submit Application'.")
            print("          3. WAIT for the 'Thank You' / 'Success' page.")
            print("      \a") 
            
            # Loop until valid input
            while True:
                response = input("      ✅ Did see the 'Thank You' / Success page? (y/n/skip): ").strip().lower()
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                elif response == 'skip':
                    return False
        elif batch:
            print("      ⏭️  Batch mode: Form filled, moving to next job")
            time.sleep(3)  # Brief pause to see the filled form
            return False
        
        # In HEADLESS mode:
        # If we successfully automated it (returned "Submitted"), return True
        if "Submitted" in status:
            return True
            
        return False

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser(description="Auto-Submit Job Applications")
    parser.add_argument("--jobs_dir", required=True, help="Directory with job folders")
    parser.add_argument("--profile", required=True, help="Path to profile.json")
    parser.add_argument("--headless", action="store_true", help="Run headless (default False)")
    parser.add_argument("--submit", action="store_true", help="Actually submit the application (default False)")
    parser.add_argument("--batch", action="store_true", help="Batch mode: fill all jobs without manual pauses")
    
    args = parser.parse_args()
    
    jobs_root = Path(args.jobs_dir)
    profile_path = Path(args.profile)
    
    if not jobs_root.exists():
        print(f"❌ Jobs dir not found: {jobs_root}")
        return
        
    if not profile_path.exists():
        print(f"❌ Profile not found: {profile_path}")
        return
        
    with open(profile_path) as f:
        profile = json.load(f)
        
    print(f"🚀 Starting Auto-Submitter")
    print(f"   Jobs Dir: {jobs_root}")
    print(f"   Profile: {profile['first_name']} {profile['last_name']}")
    print("="*60)
    
    with sync_playwright() as p:
        # Launch options for stealth/evasion
        browser = p.chromium.launch(
            headless=args.headless, 
            slow_mo=50,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        # Use realistic User-Agent and viewport
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/Chicago",
            device_scale_factor=2,
        )
        
        # Mask webdriver property manually (Stealth sync does this too, but good redundancy)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        for job_folder in jobs_root.iterdir():
            if job_folder.is_dir() and not job_folder.name.startswith("_") and not job_folder.name.startswith("."):
                # Skip already done (safety check if user re-running)
                if job_folder.name.startswith("[DONE]") or job_folder.name.endswith("_DONE"):
                    continue

                print(f"\n📂 {job_folder.name}")
                
                # Create page and apply stealth
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                # Pass page to process_job (refactor process_job to accept page or use context inside? process_job creates new page currently)
                # Wait, process_job creates its own page: `page = context.new_page()` at line 986.
                # I should close this page or refactor process_job.
                # Let's simple check process_job.
                page.close() 
                
                # Refactor call: process_job currently takes context.
                success = process_job(job_folder, profile, context, headless=args.headless, submit=args.submit, batch=args.batch)
                
                if success and "Submitted" in str(success):
                    print(f"✅ Job Done: {job_folder.name}")
                    # Rename to mark as done (Suffix _DONE, no brackets)
                    new_name = f"{job_folder.name}_DONE"
                    job_folder.rename(job_folder.parent / new_name)
                    print(f"      ✨ Marked as DONE: {new_name}")
                else:
                    print(f"      ❌ Not finished/skipped. Left as is.")
                
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
