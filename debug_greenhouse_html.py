from playwright.sync_api import sync_playwright
import time
from pathlib import Path

# Target URL (Alma job from logs)
URL = "https://job-boards.greenhouse.io/alma/jobs/8369573002"

def main():
    print(f"🚀 Launching Debugger for: {URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Headful to see
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        
        print("   🔗 Navigating...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(5) # Wait for JS to hydrate dropdowns
        
        # Save HTML
        content = page.content()
        out_file = Path("greenhouse_debug.html")
        out_file.write_text(content, encoding="utf-8")
        
        print(f"   💾 Saved HTML to {out_file.absolute()}")
        print("   ✅ Done. You can close this.")
        
        browser.close()

if __name__ == "__main__":
    main()
