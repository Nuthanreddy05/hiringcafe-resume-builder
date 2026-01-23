from job_auto_apply_internet import should_skip_job, check_sponsorship_viability, clean_jd_smart

def run_tests():
    print("🧪 Running Filter Tests...\n")
    
    # Test Cases for Source Filtering (should_skip_job)
    source_tests = [
        ("Valid Software Job", "Software Engineer Python", False),
        ("Natural Gas Job", "Senior Engineer Natural Gas", True),
        ("Biotech Job", "Research Scientist Biotech", True),
        ("Sponsorship Denied", "Developer. No visa sponsorship available.", True),
        ("Citizenship Req", "Must be US Citizen.", True),
        ("Embedded Systems", "Embedded Firmware Engineer", True),
    ]
    
    print("--- 1. Source Filter (should_skip_job) ---")
    pass_cnt = 0
    for name, desc, expected_skip in source_tests:
        skipped, reason = should_skip_job("Test Role", desc)
        status = "✅ PASS" if skipped == expected_skip else "❌ FAIL"
        print(f"{status} [{name}] Skipped? {skipped} (Expected: {expected_skip}) -> {reason}")
        if skipped == expected_skip: pass_cnt += 1
        
    # Test Cases for Process Filtering (check_sponsorship_viability)
    # This function returns FALSE if sponsorship is denied (i.e., NOT viable)
    process_tests = [
        ("Clean Job", "We love diversity.", True),
        ("Explicit Denial", "We will not sponsor visas.", False),
        ("Casual Denial", "No sponsorship.", False),
        ("Citizen Only", "U.S. Citizens only.", False),
    ]
    
    print("\n--- 2. Process Filter (check_sponsorship_viability) ---")
    for name, desc, expected_viable in process_tests:
        is_viable = check_sponsorship_viability(desc)
        status = "✅ PASS" if is_viable == expected_viable else "❌ FAIL"
        print(f"{status} [{name}] Viable? {is_viable} (Expected: {expected_viable})")
        if is_viable == expected_viable: pass_cnt += 1

    # Test Cases for Cleaning (Soft Skill Preservation)
    clean_tests = [
        ("Soft Skills", "Must be a team player with good communication.", "team player"),
    ]
    
    print("\n--- 3. Cleaning (Soft Skills) ---")
    for name, raw, keyword in clean_tests:
        cleaned = clean_jd_smart(raw)
        has_kw = keyword in cleaned
        status = "✅ PASS" if has_kw else "❌ FAIL"
        print(f"{status} [{name}] Kept '{keyword}'? {has_kw}")
        if has_kw: pass_cnt += 1

    total = len(source_tests) + len(process_tests) + len(clean_tests)
    print(f"\n📊 Result: {pass_cnt}/{total} Passed")

if __name__ == "__main__":
    run_tests()
