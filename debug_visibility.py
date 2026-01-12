from playwright.sync_api import sync_playwright
import time

def debug_vis():
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

            # Find Visa Control
            lbl = page.locator("label:has-text('sponsorship')").first
            wrapper = lbl.locator("xpath=..")
            # Try specific class 'select__control'
            control = wrapper.locator(".select__control").first
            
            if control.count() > 0:
                print("🖱️ Clicking Visa Control...")
                control.scroll_into_view_if_needed()
                control.click()
                time.sleep(2)
                
                # Check Options
                all_opts = page.locator("[role='option']").all()
                print(f"Total Options: {len(all_opts)}")
                
                print("--- Analysis of first 5 options ---")
                for i, opt in enumerate(all_opts[:5]):
                    text = opt.inner_text()
                    box = opt.bounding_box()
                    visi = opt.is_visible()
                    print(f"Opt {i}: '{text}' | Visible: {visi} | Box: {box}")
                    
                    # If Box exists but Visible is False, why?
                    if box and not visi:
                         print(f"   Hidden Reason: {opt.evaluate('el => { return { opacity: getComputedStyle(el).opacity, display: getComputedStyle(el).display, visibility: getComputedStyle(el).visibility } }')}")

            browser.disconnect()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_vis()
