
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from job_automation.utils.text_utils import trim_jd_smart, check_sponsorship_viability, clean_jd_smart

def test_hybrid_cleaning():
    print("🧪 Testing Hybrid Cleaning Logic...\n")

    # Test Case 1: Sponsorship Blocking
    print("--- Test 1: Sponsorship Blocking ---")
    bad_jd = """
    Senior Software Engineer - Backend Systems
    
    About Us
    We are a company that loves to do great things for the world and we are hiring.
    We have been around for many years and are very successful.
    
    Requirements
    - Experience with Python and Java for backend development is required for this role.
    - Must have at least 5 years of experience in distributed systems.
    - US Citizen Only due to the nature of the work ensuring clearance protocols.
    
    Benefits
    - We offer great pizza and parties every Friday for all employees.
    """
    
    trimmed = trim_jd_smart(bad_jd)
    is_safe, reason = check_sponsorship_viability(trimmed)
    print(f"Original Length: {len(bad_jd)}")
    print(f"Trimmed Length: {len(trimmed)}")
    print(f"Safe? {is_safe}")
    print(f"Reason: {reason}")
    print(f"Trimmed Content Preview: {trimmed[:100]}...")
    
    if not is_safe and "Citizenship" in reason:
        print("✅ PASS: Correctly blocked US Citizen Only job.")
    else:
        print("❌ FAIL: Did not block restricted job.")

    # Test Case 2: Marketing Fluff Removal
    print("\n--- Test 2: Marketing Fluff Removal ---")
    fluffy_jd = """
    Lead Product Designer
    
    About Us
    We are a global leader in innovation and we are transforming the industry.
    Our mission is to change the world through technology and design.
    
    Responsibilities
    - You will be responsible for designing user interfaces that are intuitive and beautiful.
    - collaborate with engineering times to implement designs using modern web technologies.
    
    Benefits
    - Comprehensive health and dental insurance for you and your family.
    - Unlimited Paid Time Off and flexible working hours.
    
    Equal Employment Opportunity
    We are an equal opportunity employer and value diversity at our company.
    """
    
    trimmed = trim_jd_smart(fluffy_jd)
    print(f"Trimmed Content:\n{trimmed}")
    
    if "About Us" not in trimmed and "Benefits" not in trimmed and "designing user interfaces" in trimmed:
        print("✅ PASS: Removed 'About Us' and 'Benefits', kept 'Responsibilities'.")
    else:
        print("❌ FAIL: Fluff removal failed.")

if __name__ == "__main__":
    test_hybrid_cleaning()
