#!/usr/bin/env python3
"""Test script to verify folder_reader.py can read Google Auto Internet folders."""
import json
import sys
import subprocess

# Prepare test message (simulating Chrome extension)
test_message = {"action": "get_jobs"}

# Convert to native messaging format
message_json = json.dumps(test_message).encode('utf-8')
message_length = len(message_json).to_bytes(4, byteorder=sys.byteorder)

# Run folder_reader and send test message
process = subprocess.Popen(
    ['python3', 'chrome-extension/native-messaging/folder_reader.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Send message
process.stdin.write(message_length + message_json)
process.stdin.flush()

# Read response length
response_length_bytes = process.stdout.read(4)
if not response_length_bytes:
    print("❌ No response from folder_reader.py")
    sys.exit(1)

response_length = int.from_bytes(response_length_bytes, byteorder=sys.byteorder)

# Read response
response_json = process.stdout.read(response_length).decode('utf-8')
response = json.loads(response_json)

# Print results
print("✅ Response received!")
print(f"Total jobs found: {len(response.get('jobs', []))}")
print("\nJobs:")
for job in response.get('jobs', [])[:5]:  # Show first 5
    print(f"  - {job['company']}: {job['job_title']}")
    print(f"    Resume: {job.get('resume_path', 'N/A')}")
    print(f"    Apply URL: {job.get('apply_url', 'N/A')[:60]}...")

if len(response.get('jobs', [])) > 5:
    print(f"\n  ... and {len(response['jobs']) - 5} more jobs")

process.terminate()
