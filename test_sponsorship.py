
import re

# 1. The Regex Logic (Copied from my proposed fix)
CITIZENSHIP_PATTERNS = [
    r"\bu\.?s\.?\s*citizen\b", r"\bus citizens?\s*only\b",
    r"\bcitizenship required\b", r"\bno sponsorship\b",
    r"\bno visa sponsorship\b",
    r"\bwithout\s+(?:company\s+)?sponsorship\b",
    r"\bwill not sponsor\b",
    r"\bnot eligible for(?:.*\b)?sponsorship\b",
    r"not able to offer.*sponsorship", # The new line I added
]

def check_sponsorship_viability(description: str) -> bool:
    """Returns False if job explicitly denies sponsorship."""
    description = description.lower()
    
    for phrase in CITIZENSHIP_PATTERNS:
        if re.search(phrase, description, re.IGNORECASE):
            print(f"MATCHED REGEX: {phrase}")
            return False
            
    return True

test_cases = [
    # 1. Anomali (Expected: Fail)
    """This position is not eligible for employment visa sponsorship. The successful candidate must not now, or in the future, require visa sponsorship to work in the US.""",
    
    # 2. LinkedIn (Expected: Pass?)
    """LinkedIn is the worlds largest professional network... Equal Opportunity Statement... Pay Transparency Policy Statement... Global Data Privacy Notice... Does not mention sponsorship exclusion.""",

    # 3. Waymo (Expected: Pass?)
    """Waymo is an autonomous driving technology company... In this hybrid role you will report to a Technical Lead... We prefer MS or PhD... Waymo employees are also eligible... Salary Range...""",
    
    # 4. Tricky Case (US Citizen / Clearance)
    """Must be a US Citizen due to government contract requirements.""",
    
    # 5. Clean Case
    """We sponsor H1B visas for qualified candidates."""
]

print(f"🔍 Testing {len(test_cases)} cases for Sponsorship Viability:\n")
for i, text in enumerate(test_cases, 1):
    is_viable = check_sponsorship_viability(text)
    flag_present = "SPONSORSHIP_DENIAL" in text # Simulation of AI flag
    
    status = "✅ PASS" if is_viable and not flag_present else "⛔ FAIL"
    reason = []
    if not is_viable: reason.append("Regex Match")
    if flag_present: reason.append("AI Flag")
    
    print(f"Case {i}: {status} (Reason: {', '.join(reason) if reason else 'None'})")
    # print(f"Preview: {text[:50]}...")
    print("-" * 40)
