import re
import sys
sys.path.append('.')
from job_auto_apply_internet import CITIZENSHIP_PATTERNS, INDUSTRY_EXCLUSION_PATTERNS, should_skip_job, check_sponsorship_viability

# The exact JD text from user
jd_text = """
This role is for one of the Weekday's clients

Min Experience: 3 years

Location: Bay Area

JobType: full-time

We are seeking a Founding Software Engineer to help build the core agentic AI engine of our product. You will work directly with the founders and CTO to design and ship AI systems that perform real-world tasks end-to-end. This is not a research or model-tuning role—the focus is on building reliable, production-grade AI workflows that solve concrete problems for customers.

You will work on how AI agents plan, execute, and verify complex, messy real-world processes. Audit workflows provide an ideal domain for AI agents, allowing you to define new best practices for agentic software.

This is an early, high-ownership role. You will shape core product architecture, influence how AI agents behave, and help define how enterprise software is built going forward. You should be excited about working closely with users, iterating rapidly, and shipping features that are used immediately.

Requirements

Interview Process

Our interview process reflects how we work. We value practical problem solving, product thinking, and building reliable systems in ambiguous environments. The process is designed to be efficient, respectful of your time, and focused on real work rather than abstract puzzles.

Phone Screen

A short, informal conversation with a founder to discuss your background, goals, and the product vision.
Opportunity to ask questions and determine mutual fit.
Remote Technical Screen (1 hour)

A hands-on session focused on solving practical problems.
You may work through a small feature or system similar to what you would build in the role.
Language-agnostic; production stack includes Python, SQL, and React. You may use your preferred tools, including AI coding assistants.
Onsite Interview (Half Day)

Collaboration with founders on realistic, end-to-end feature-building exercises.
Focus on problem solving, product judgment, and shipping high-impact work.
Time to discuss roadmap, culture, and daily work expectations.
Timing and Logistics

The full process typically takes 1–2 weeks.
We accommodate candidates with competing offers or tight timelines.
Why This Role Matters
You will help define the future of agentic AI software, building systems that allow users to describe their goals and let AI handle execution. This role offers the chance to work directly with founders, take ownership of core architecture, and build production-grade AI systems used in real-world workflows from day one.

Skills

Applied AI Engineer
Full-stack software development
Building production-grade agentic AI systems
Designing and shipping core AI engine features
"""

title = "Founding Software Engineer"

print("=" * 60)
print("🔍 DEBUGGING FALSE POSITIVE")
print("=" * 60)

# Test 1: Check CITIZENSHIP_PATTERNS
print("\n--- Testing CITIZENSHIP_PATTERNS ---")
jd_lower = jd_text.lower()
for pat in CITIZENSHIP_PATTERNS:
    match = re.search(pat, jd_lower, re.IGNORECASE)
    if match:
        print(f"❌ MATCH FOUND: Pattern '{pat}' matched: '{match.group()}'")
        # Show context around the match
        start = max(0, match.start() - 50)
        end = min(len(jd_lower), match.end() + 50)
        print(f"   Context: ...{jd_lower[start:end]}...")
    else:
        print(f"✅ No match: {pat}")

# Test 2: Check INDUSTRY_EXCLUSION_PATTERNS
print("\n--- Testing INDUSTRY_EXCLUSION_PATTERNS ---")
for pat in INDUSTRY_EXCLUSION_PATTERNS:
    match = re.search(pat, jd_lower, re.IGNORECASE)
    if match:
        print(f"❌ MATCH FOUND: Pattern '{pat}' matched: '{match.group()}'")
    else:
        print(f"✅ No match: {pat}")

# Test 3: Run should_skip_job
print("\n--- Testing should_skip_job() ---")
skip, reason = should_skip_job(title, jd_text)
print(f"Result: skip={skip}, reason='{reason}'")

# Test 4: Run check_sponsorship_viability
print("\n--- Testing check_sponsorship_viability() ---")
viable = check_sponsorship_viability(jd_text)
print(f"Result: viable={viable}")

if not viable:
    print("⚠️  This is the source of the false positive!")
