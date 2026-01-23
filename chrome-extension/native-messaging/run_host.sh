#!/bin/bash
# Chrome Native Messaging Wrapper Script
# Fixes PATH issues in Chrome's restrictive environment

PYTHON_PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_SCRIPT="$SCRIPT_DIR/folder_reader.py"

# Debug Logging
# CRITICAL: Do NOT redirect stdout (fd 1) to a file, Chrome reads it!
# Redirect stderr (fd 2) to log for debugging
exec 2>>/tmp/wrapper_log.txt

echo "Starting Wrapper Script at $(date)" >&2
echo "User: $(whoami)" >&2
echo "Path: $PYTHON_PATH" >&2

# Check if Python exists
if [ ! -x "$PYTHON_PATH" ]; then
    echo "ERROR: Python path is invalid!" >&2
    exit 1
fi

# Execute the Python script
# -u for unbuffered binary stdout
"$PYTHON_PATH" -u "$TARGET_SCRIPT"
