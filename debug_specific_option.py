from playwright.sync_api import sync_playwright
import time

def debug_yes():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            # Find page
            page = None
            for p_obj in context.pages:
                if "greenhouse.io" in p_obj.url:
                    page = p_obj
                    break
            if not page: return
            
            print(f"📄 Page: {page.url}")

            # Click Visa Control again to be sure
            lbl = page.locator("label:has-text('sponsorship')").first
            wrapper = lbl.locator("xpath=..")
            control = wrapper.locator(".select__control").first
            if control.count() > 0:
                control.click()
                time.sleep(1)

            # Find 'Yes'
            # Look for exact text 'Yes' or 'No'
            # Filter by visibility
            yes_opts = page.locator("div:text-is('Yes'), div:text-is('No')").all()
            
            print(f"Found {len(yes_opts)} elements with exact text 'Yes' or 'No'")
            
            for el in yes_opts:
                if el.is_visible():
                    print("\n--- VISIBLE 'Yes/No' FOUND ---")
                    print(f"OuterHTML: {el.evaluate('el => el.outerHTML')}")
                    print(f"Parent Class: {el.evaluate('el => el.parentElement.className')}")
                    print(f"Role: {el.get_attribute('role')}")

            browser.disconnect()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_yes()
