
import re

def escape_latex_special_chars(text: str) -> str:
    """Copy of the function from job_auto_apply.py to test logic"""
    if not isinstance(text, str):
        return text

    # 1. Convert Markdown bold (**text**) to LaTeX (\textbf{text})
    if "**" in text:
        text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)

    # 2. Escape special chars using Negative Lookbehind to avoid double-escaping
    chars_to_escape = ['%', '$', '&', '#', '_']
    for char in chars_to_escape:
        # Regex: (?<!\\)%
        pattern = f"(?<!\\\\){re.escape(char)}"
        text = re.sub(pattern, f"\\\\{char}", text)

    return text

def run_tests():
    test_cases = [
        ("Improved by 18%", "Improved by 18\\%"),
        ("Revenue $45K", "Revenue \\$45K"),
        ("Use **XGBoost** model", "Use \\textbf{XGBoost} model"),
        ("Already \\textbf{Bold}", "Already \\textbf{Bold}"),
        ("Mixed: **15%** gain", "Mixed: \\textbf{15\\%} gain"),
        ("Escaped: 18\\% already", "Escaped: 18\\% already"),
        ("Complex: **$5K** savings", "Complex: \\textbf{\\$5K} savings"),
    ]

    print("Running Tests...\n")
    failed = False
    for input_str, expected in test_cases:
        result = escape_latex_special_chars(input_str)
        if result == expected:
            print(f"✅ PASS: '{input_str}' -> '{result}'")
        else:
            print(f"❌ FAIL: '{input_str}'\n   Expected: '{expected}'\n   Got:      '{result}'")
            failed = True
    
    if failed:
        print("\nSUMMARY: FAILURES DETECTED")
    else:
        print("\nSUMMARY: ALL PASSED")

if __name__ == "__main__":
    run_tests()
