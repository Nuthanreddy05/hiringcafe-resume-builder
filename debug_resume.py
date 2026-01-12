
import sys
from playwright.sync_api import sync_playwright
import re

def debug_resume(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Stealth
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"   🔍 Inspecting: {url}")
        
        try:
            page.goto(url)
            page.wait_for_timeout(3000)
            
            print("\n   [Form Detection]")
            for sel in ["input[name*='name']", "input[type='email']", "input[type='file']"]:
                 count = page.locator(sel).count()
                 print(f"      - '{sel}': {count}")
                 
            print("\n   [Apply Button Detection]")
            # Broad scan for anything "Apply"
            apply_candidates = page.locator("a, button, div.btn, input[type='submit']").filter(has_text=re.compile("apply", re.IGNORECASE)).all()
            print(f"      - Potential 'Apply' elements found: {len(apply_candidates)}")
            
            for i, el in enumerate(apply_candidates[:5]): # Show top 5
                try:
                    txt = el.inner_text().strip().replace("\n", " ")
                    html = el.evaluate("el => el.outerHTML")
                    print(f"      [{i}] Text: '{txt}' | HTML: {html[:150]}...")
                except: pass

            print("\n   [Resume Input Detection]")
            for sel in ["#resume", "input[name='resume']", "#s3_upload_for_resume", "[data-ui='resume-upload-input']", "input[type='file']"]:
                count = page.locator(sel).count()
                print(f"      - '{sel}': {count}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_resume.py <url>")
    else:
        debug_resume(sys.argv[1])
