import sys
import os
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from playwright.sync_api import sync_playwright

def main():
    print("🚀 DEBUGGING SORT INTERACTION")
    session_file = Path("job_automation/.sessions/jobright_session.json")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Headless but we will screenshot
        context = browser.new_context(storage_state=str(session_file))
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        
        page.goto("https://jobright.ai/jobs/recommend", wait_until="domcontentloaded")
        time.sleep(5)
        
        # 1. Find and Click Sorter
        # The user mentioned "Recommended" is visible.
        sorter = page.locator('.ant-select, .index_jobs-recommend-sorter__AhkIK').filter(has_text="Recommended").first
        if not sorter.is_visible():
             # Fallback
             sorter = page.locator('.index_jobs-recommend-sorter__AhkIK').first
        
        if sorter.is_visible():
            print("✓ Found Sorter. Clicking...")
            sorter.click()
            time.sleep(2) # Wait for animation
            
            # 2. Capture Screenshot to see what's happening
            page.screenshot(path="job_automation/sort_debug.png")
            print("📸 Screenshot saved to job_automation/sort_debug.png")
            
            # 3. Dump all text content of the body to finding the options
            # This is a crude but effective way to see if "Newest" or "Date" exists in the DOM
            body_text = page.inner_text("body")
            print("\n--- BODY TEXT DUMP (Searching for sort options) ---")
            # Look for lines that might be sort options
            lines = [l for l in body_text.split('\n') if len(l) < 20]
            print(lines)
            
            # 4. Try to find the specific dropdown
            dropdown = page.locator('.ant-select-dropdown')
            if dropdown.count() > 0:
                print(f"\nDropdown Text: {dropdown.all_inner_texts()}")
            else:
                print("\n⚠️ No .ant-select-dropdown found in DOM")
                
        else:
            print("✗ Sorter NOT found or not visible")
            
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
