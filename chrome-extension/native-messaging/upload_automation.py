#!/usr/bin/env python3
"""
macOS file upload automation using AppleScript.
Triggered by folder_reader.py when Extension requests resume upload.
"""
import subprocess
import time
import os
import sys

def upload_file_macos(file_path):
    """Upload a file using macOS file picker automation."""
    
    # Verify file exists
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    
    # Get folder path and filename
    folder_path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    # Wait for file dialog to appear (Frontend clicks input, then calls this)
    # We give it a small buffer for the animation
    time.sleep(0.8)
    
    # AppleScript to automate file picker
    applescript = f'''
    tell application "System Events"
        -- Wait for file dialog logic handled by caller delay
        
        -- Open "Go to Folder" dialog (Cmd+Shift+G)
        keystroke "g" using {{command down, shift down}}
        delay 0.5
        
        -- Type folder path
        keystroke "{folder_path}"
        delay 0.3
        
        -- Press Enter to navigate to folder
        keystroke return
        delay 0.8  -- More time for folder to load
        
        -- Type filename to select it
        keystroke "{filename}"
        delay 0.5
        
        -- Press Enter to confirm selection
        keystroke return
        delay 0.5
        
        -- Double check: Press Enter again to close dialog
        keystroke return
        delay 0.2
    end tell
    '''
    
    try:
        # Execute AppleScript
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "File uploaded successfully"}
        else:
            return {"success": False, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Automation timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # For standalone testing
    if len(sys.argv) > 1:
        print(f"Testing upload with: {sys.argv[1]}")
        res = upload_file_macos(sys.argv[1])
        print(res)
    else:
        print("Usage: python3 upload_automation.py /path/to/file.pdf")
