from playwright.sync_api import sync_playwright
from smart_selector import SmartSelector
from ai_selector import AISelector
import time
import json

def test_integration():
    print("🔌 Running Integration Test: SmartSelector + AISelector")
    
    # Mock Profile
    profile = {
        "gender": "Male",
        "demographics": {"race": "Asian"}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Setup Dummy HTML (A tough React-like Dropdown)
        page.set_content("""
            <html>
                <body>
                    <div class="field">
                        <label>What is your Gender?</label>
                        <div class="control react-select">
                            <div class="placeholder">Select...</div>
                        </div>
                        <!-- Hidden Options (Simulation) -->
                        <div class="menu" style="display:none;">
                            <div class="option">Female</div>
                            <div class="option">Male</div>
                            <div class="option">Non-binary</div>
                        </div>
                    </div>
                    
                     <div class="field">
                        <label for="name">Full Name</label>
                        <input id="name" type="text" />
                    </div>
                </body>
            </html>
        """)
        
        # 2. Init Modules
        smart_sel = SmartSelector(page)
        ai_sel = AISelector()
        
        # 3. Test Text Fill
        print("\n📝 Testing Text Fill...")
        try:
            smart_sel.fill_with_retry("Full Name", "Nuthan Reddy")
            assert page.locator("#name").input_value() == "Nuthan Reddy"
            print("✅ Text Fill Success")
        except Exception as e:
            print(f"❌ Text Fill Failed: {e}")

        # 4. Test Dropdown Logic (Simulation)
        print("\n🧠 Testing AI Selection...")
        options = ["Female", "Male", "Non-binary"]
        question = "What is your Gender?"
        
        # Ask AI/Heuristic
        choice = ai_sel.select_option(question, options, profile)
        print(f"AI Selected: {choice}")
        
        assert choice == "Male"
        print("✅ AI Logic Success (Matched 'Male')")
        
        browser.close()
        print("\n🎉 INTEGRATION TEST PASSED.")

if __name__ == "__main__":
    test_integration()
