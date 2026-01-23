import sys
import json
import os
import struct

# Test Config
FOLDER_PATH = "/Users/nuthanreddyvaddireddy/Desktop/Google Auto/adp_605387"
ACTION = "update_status"
NEW_STATUS = "applied"

def test_manual_update():
    """Simulate what folder_reader.py does internally."""
    print(f"Testing manual update on: {FOLDER_PATH}")
    
    if not os.path.exists(FOLDER_PATH):
        print("ERROR: Folder does not exist!")
        return

    status_file = os.path.join(FOLDER_PATH, ".status.json")
    print(f"Writing to: {status_file}")
    
    try:
        content = {
            "status": NEW_STATUS,
            "method": "test_script"
        }
        with open(status_file, 'w') as f:
            json.dump(content, f, indent=2)
        print("SUCCESS: Wrote status file manually.")
    except Exception as e:
        print(f"ERROR: Failed to write file: {e}")

def test_via_native_host():
    """Send message to folder_reader.py via stdin."""
    msg = {
        "action": ACTION,
        "folder_path": FOLDER_PATH,
        "status": NEW_STATUS
    }
    
    json_msg = json.dumps(msg)
    encoded_msg = json_msg.encode('utf-8')
    length = len(encoded_msg)
    
    # Run the script via subprocess to simulate Chrome
    import subprocess
    
    # Assume folder_reader.py is in current dir or specific path
    script_path = "chrome-extension/native-messaging/folder_reader.py"
    
    print(f"Sending message to {script_path}...")
    
    try:
        # Popen with pipe stdin/stdout
        p = subprocess.Popen(
            ['python3', script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Send length (4 bytes) + Content
        header = struct.pack('@I', length) # Native messaging length prefix
        
        input_data = header + encoded_msg
        
        stdout, stderr = p.communicate(input=input_data, timeout=5)
        
        print("\n--- STDOUT (Raw) ---")
        print(stdout)
        
        print("\n--- STDERR ---")
        print(stderr.decode('utf-8'))
        
        # Parse output
        if len(stdout) >= 4:
            resp_len = struct.unpack('@I', stdout[:4])[0]
            resp_json = stdout[4:4+resp_len]
            print("\n--- REDECODED JSON ---")
            print(resp_json.decode('utf-8'))
            
    except Exception as e:
        print(f"Subprocess Error: {e}")

if __name__ == "__main__":
    # 1. Test basic write permissions first
    test_manual_update()
    print("-" * 30)
    # 2. Test full integration
    test_via_native_host()
