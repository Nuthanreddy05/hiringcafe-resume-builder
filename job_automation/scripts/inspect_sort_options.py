import sys
import os
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from playwright.sync_api import sync_playwright

def main():
    print("🚀 INSPECTING SORT OPTIONS")
    session_file = Path("job_automation/.sessions/jobright_session.json")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(session_file))
        page = context.new_page()
        
        page.goto("https://jobright.ai/jobs/recommend", wait_until="domcontentloaded")
        time.sleep(5)
        
        # Find the sorter
        sorter = page.locator('.index_jobs-recommend-sorter__AhkIK, .ant-select').first
        if sorter.is_visible():
            print("✓ Found Sorter Dropdown")
            sorter.click()
            time.sleep(1)
            
            # List options (Ant Design renders dropdowns at body root)
            # Wait for dropdown to be visible
            page.wait_for_selector('.ant-select-dropdown', state='visible')
            
            # Select all options inside the dropdown
            options = page.locator('.ant-select-dropdown .ant-select-item-option-content').all_inner_texts()
            print(f"Available Options: {options}")
        else:
            print("✗ Sorter NOT found")
            
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
