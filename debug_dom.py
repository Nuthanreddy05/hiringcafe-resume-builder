from playwright.sync_api import sync_playwright

def inspect_dom():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            if not browser.contexts:
                print("❌ No contexts found.")
                return
            context = browser.contexts[0]
            context = browser.contexts[0]
            page = None
            for p in context.pages:
                if "greenhouse.io" in p.url:
                    page = p
                    break
            
            if not page:
                print("❌ No Greenhouse tab found.")
                # Fallback to last page just in case
                if context.pages:
                    page = context.pages[-1]
                    print(f"Fallback to: {page.url}")
                else:
                    return

            print(f"📄 Inspecting: {page.url}")
            
            # Target Country specifically
            country_label = page.locator("label").filter(has_text="Country").first
            if country_label.count() > 0:
                print("\n--- FOUND COUNTRY LABEL ---")
                parent = country_label.locator("xpath=..")
                print(parent.evaluate("el => el.outerHTML"))
            else:
                print("❌ 'Country' label not found")

            # Target Visa specifically
            visa_label = page.locator("label").filter(has_text="Visa").first
            if visa_label.count() > 0:
                print("\n--- FOUND VISA LABEL ---")
                parent = visa_label.locator("xpath=..")
                print(parent.evaluate("el => el.outerHTML"))
            else:
                print("❌ 'Visa' label not found")
            
            browser.disconnect()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_dom()
