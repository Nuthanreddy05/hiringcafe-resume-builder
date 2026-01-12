from ai_selector import AISelector
import json

# Initialize
print("🚀 Initializing AI Selector (Groq Mode)...")
ai = AISelector()

# Mock Profile for testing
profile = {
    "first_name": "Nuthan",
    "last_name": "Reddy",
    "experience": [
        {"title": "Full Stack Developer", "company": "Albertsons", "duration": "2 years"},
        {"title": "Software Engineer", "company": "ValueLabs", "duration": "2 years"}
    ],
    "skills": ["React", "Python", "Django", "PostgreSQL", "AWS"],
    "summary": "Full Stack Developer with 4 years of experience building scalable web applications."
}

# Test questions
questions = [
    "Why are you interested in this role?",
    "Tell us about a project you're proud of",
    "What makes you a good fit for this position?"
]

# Generate answers
for q in questions:
    print(f"\n❓ Q: {q}")
    answer = ai.generate_answer(q, profile)
    print(f"🤖 A: {answer}")
    print("-" * 60)
