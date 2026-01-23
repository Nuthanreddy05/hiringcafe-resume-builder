import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path("job_automation/.sessions/jobright_session.json")
TARGET_JOB_URL = "https://jobright.ai/jobs/info/696f161f82817106e976465e" # Barclays ID

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        # Load Session
        if SESSION_FILE.exists():
            print("Loading session...")
            with open(SESSION_FILE, 'r') as f:
                state = json.load(f)
                context.add_cookies(state["cookies"])
        else:
            print("❌ No session file found. Please run pipeline to auth first.")
            return

        page = context.new_page()
        
        print(f"Navigating to: {TARGET_JOB_URL}")
        page.goto(TARGET_JOB_URL)
        page.wait_for_timeout(5000)
        
        # Dump Source
        content = page.content()
        Path("source_dump.html").write_text(content, encoding="utf-8")
        print("✅ Saved 'source_dump.html'")
        
        # Extract Scripts (Hydration Data)
        print("\n--- Inspecting hydration/JSON ---")
        scripts = page.locator("script").all()
        for i, s in enumerate(scripts):
            txt = s.inner_text()
            if "applyUrl" in txt or "originalUrl" in txt or "redirect" in txt or "job" in txt[:50].lower():
                print(f"SCRIPT [{i}]: Length {len(txt)}")
                print(txt[:500] + "...") # Preview
                
        # Inspect Button Attributes
        print("\n--- Inspecting Apply Button ---")
        btn = page.locator('a, button').filter(has_text=re.compile(r"Apply|Start", re.I)).first
        if btn.count() > 0:
            print(f"Button OuterHTML: {btn.evaluate('el => el.outerHTML')}")
            # Check event listeners? escaping my capabilities here, but outerHTML often reveals data attributes
        
        browser.close()

if __name__ == "__main__":
    run()
