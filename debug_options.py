from playwright.sync_api import sync_playwright
import time

def inspect_options():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = None
            for p_obj in context.pages:
                if "greenhouse.io" in p_obj.url:
                    page = p_obj
                    break
            
            if not page:
                print("❌ Greenhouse tab not found")
                return

            print(f"📄 Inspecting: {page.url}")
            
            # Target Visa field
            visa_label = page.locator("label:has-text('sponsorship')").first
            if visa_label.count() == 0:
                print("❌ Visa label not found")
                return

            # Find control (Parent -> div.select-shell -> div.select__control)
            wrapper = visa_label.locator("xpath=..")
            control = wrapper.locator("div[class*='control']").first
            
            if control.count() == 0:
                print("❌ Visa Control not found")
                # Fallback: look for select__control anywhere in wrapper
                control = wrapper.locator(".select__control").first
            
                print("🔎 Scanning for options...")
                
                # Check Total vs Visible
                all_roles = page.locator("[role='option']").all()
                visible_roles = page.locator("[role='option']:visible").all()
                
                print(f"Total role='option': {len(all_roles)}")
                print(f"Visible role='option': {len(visible_roles)}")
                
                if len(visible_roles) == 0 and len(all_roles) > 0:
                     print("⚠️ Options exist but are NOT visible.")
                     first = all_roles[0]
                     print(f"First Option HTML: {first.evaluate('el => el.outerHTML')}")
                     print(f"First Option Visibility: {first.is_visible()}")
                     # Check styling
                     print(f"Style Display: {first.evaluate('el => getComputedStyle(el).display')}")
                     print(f"Style Opacity: {first.evaluate('el => getComputedStyle(el).opacity')}")
                elif len(visible_roles) > 0:
                     print(f"Sample Visible: {visible_roles[0].inner_text()}")

            browser.disconnect()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_options()
