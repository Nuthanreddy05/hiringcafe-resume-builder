def handle_greenhouse(page: Page, profile: Dict[str, Any], resume_path: Path, submit: bool = False, context_text: str = "") -> str:
    """Fill Greenhouse application form sequentially (1-by-1) for human-like behavior."""
    print("      🟢 Detected: Greenhouse (Sequential Mode)")
    
    custom_answers = profile.get("custom_question_answers", {})
    
    # Locate all question fields (Greenhouse standard is div.field)
    fields = page.locator("div.field").all()
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
                # Determine Answer
                answer = "Yes" # Default safe
                
                # Logic Mapping
                if "sponsorship" in label_lower: answer = "No" # Or profile logic
                elif "authorized" in label_lower: answer = "Yes"
                elif "relocat" in label_lower: answer = "No" # FORCE NEGATIVE for Relocation
                elif "gender" in label_lower: answer = profile.get("demographics", {}).get("gender", "Male")
                elif "race" in label_lower: answer = profile.get("demographics", {}).get("race", "Asian")
                elif "veteran" in label_lower: answer = profile.get("demographics", {}).get("veteran", "I am not")
                elif "disability" in label_lower: answer = profile.get("demographics", {}).get("disability", "No")
                elif "privacy" in label_lower or "policy" in label_lower: answer = "Yes" # Agreement
                else: 
                     # Use AI or Profile default
                     pass
                
                # Click logic
                print(f"      ⚛️  React-Select: '{label_text}' -> '{answer}'")
                human_click(page, react_control)
                page.wait_for_timeout(500)
                # Find option (using the global matcher from before)
                option = page.locator(f"div[role='option']:has-text('{answer}'), div[class*='option']:has-text('{answer}')").first
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
                elif "phone" in label_lower: answer = profile["phone"]
                elif "linkedin" in label_lower: answer = profile.get("linkedin", "")
                elif "website" in label_lower or "portfolio" in label_lower: answer = profile.get("portfolio", "")
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

    # Final "Submit" button handling
    if submit:
        submit_btn = page.locator("#submit_app").first
        if submit_btn.count() > 0:
            human_click(page, submit_btn)
            return "Submitted"
            
    # Verification Pause
    print("      👀 Paused for manual review (Sequential Mode).")
    input("      Press Enter to finish...") 
    
    return "Ready for Review"
