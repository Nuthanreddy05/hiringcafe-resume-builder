import re
from pathlib import Path

def test():
    try:
        content = Path("source_dump.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        print("❌ source_dump.html not found. Cannot verify regex extraction.")
        return

    print(f"Loaded source_dump.html ({len(content)} bytes)")

    # The regex from jobright_scraper.py
    regex_pattern = r'"originalUrl":"(https?://[^"]+)"'
    print(f"Testing Regex: {regex_pattern}")

    match = re.search(regex_pattern, content)
    if match:
        url = match.group(1)
        print(f"✅ Regex MATCHED!")
        print(f"   URLs found: {url}")
        # Test decoding
        decoded = url.encode().decode('unicode_escape')
        print(f"   Decoded: {decoded}")
    else:
        print("❌ Regex DID NOT MATCH.")
        # Try to find it manually to see why
        snippet = "originalUrl"
        idx = content.find(snippet)
        if idx != -1:
            print(f"   'originalUrl' found at index {idx}. Context:")
            print(content[idx:idx+100])
        else:
            print("   'originalUrl' string NOT found in content (file might be different?)")

if __name__ == "__main__":
    test()
