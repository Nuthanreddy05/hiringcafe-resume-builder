
import sys
import json
import struct
import subprocess
import os

# Define Paths
import os

# Define Paths
# Testing the INSTALLED wrapper to match Chrome's environment as closely as possible
HOST_SCRIPT = os.path.expanduser("~/Library/Application Support/com.smartjobapply.folder_reader/run_host.sh")

def send_message(proc, message):
    # Encode JSON
    encoded_content = json.dumps(message).encode('utf-8')
    # Pack Length (4 bytes, native order)
    encoded_length = struct.pack('@I', len(encoded_content))
    
    # Write to stdin
    proc.stdin.write(encoded_length)
    proc.stdin.write(encoded_content)
    proc.stdin.flush()

def read_message(proc):
    # Read Length
    raw_length = proc.stdout.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('@I', raw_length)[0]
    
    # Read Content
    message = proc.stdout.read(message_length).decode('utf-8')
    return json.loads(message)

def test_host():
    print(f"🚀 Testing Native Host: {HOST_SCRIPT}")
    
    # Launch Process
    try:
        proc = subprocess.Popen(
            ['python3', HOST_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
    except Exception as e:
        print(f"❌ Failed to launch script: {e}")
        return

    # 1. Test Ping
    print("\n📡 Sending: PING")
    send_message(proc, {"action": "ping"})
    response = read_message(proc)
    print(f"✅ Received: {response}")
    
    if response.get('status') != 'ok':
        print("❌ Ping Failed!")
        proc.terminate()
        return

    # 2. Test Get Jobs
    print("\n📂 Sending: GET JOBS")
    # Path is configurable, but default is ~/Desktop/Google Auto
    # Make sure we point to where the user actually has data
    base_path = "/Users/nuthanreddyvaddireddy/Desktop/Google Auto"
    send_message(proc, {"action": "get_jobs", "base_path": base_path})
    
    response = read_message(proc)
    jobs = response.get('jobs', [])
    print(f"✅ Received {len(jobs)} jobs.")
    
    if len(jobs) > 0:
        print(f"   🔹 Newest: {jobs[0]['company']} (Status: {jobs[0].get('status')})")
        print(f"   🔹 Oldest: {jobs[-1]['company']}")
    elif response.get('error'):
        print(f"❌ Error: {response['error']}")
    else:
        print("⚠️ No jobs found (but no error).")

    # Cleanup
    proc.terminate()
    # Check stderr
    stderr = proc.stderr.read().decode('utf-8')
    if stderr:
        print(f"\n⚠️ STDERR Output:\n{stderr}")

if __name__ == "__main__":
    test_host()
