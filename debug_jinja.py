import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def escape_latex(text):
    if not isinstance(text, str): return text
    if "**" in text:
        text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
    chars = ['%', '$', '&', '#', '_']
    for char in chars:
        pattern = f"(?<!\\\\){re.escape(char)}"
        text = re.sub(pattern, f"\\\\{char}", text)
    return text

def recursive_escape(data):
    if isinstance(data, dict):
        return {k: recursive_escape(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_escape(v) for v in data]
    elif isinstance(data, str):
        return escape_latex(data)
    else:
        return data

# Load JSON
# Use Absolute Path to match default behavior
root_dir = Path.home() / "Desktop" / "Google Auto"
json_path = root_dir / "696dd891350cf4380314a57c" / "resume.json"

if not json_path.exists():
    print(f"File not found: {json_path}")
    # Try finding one that exists
    import sys
    files = list(root_dir.glob("*/resume.json"))
    if not files: 
        print("No resume.json found")
        sys.exit(1)
    json_path = files[0]

print(f"Loading {json_path}")
data = json.loads(json_path.read_text())

# Escape
escaped_data = recursive_escape(data)
print("Keys in data:", list(escaped_data.keys()))

# Load Template
template_path = Path("resume_template.tex")
if not template_path.exists():
    print("Template not found in root")
    sys.exit(1)

env = Environment(
    loader=FileSystemLoader("."),
    block_start_string='{%',
    block_end_string='%}',
    variable_start_string='{{',
    variable_end_string='}}',
    autoescape=False,
)
template = env.get_template("resume_template.tex")

# Render
output = template.render(**escaped_data)

# Check
if "{{- role_albertsons -}}" in output:
    print("❌ FAILURE: Tag {{- role_albertsons -}} NOT replaced")
elif "{{ role_albertsons }}" in output:
    print("❌ FAILURE: Tag {{ role_albertsons }} NOT replaced")
else:
    print("✅ SUCCESS: Tags replaced.")
    print("First 200 chars:")
    print(output[:200])

# Check for unescaped underscores in keywords
print("\nChecking for unescaped underscores...")
if "_" in output and "\\_" not in output:
    print("⚠️  Warning: Underscores found, might trigger LaTeX error if not math mode.")
