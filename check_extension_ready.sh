#!/bin/bash
# Quick verification script - Run this to check if everything is ready

echo "🔍 CHROME EXTENSION READINESS CHECK"
echo "===================================="
echo ""

# Check 1: Extension Files
echo "1️⃣  Checking Chrome Extension Files..."
if [ -d "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/chrome-extension" ]; then
    echo "   ✅ Extension folder exists"
    if [ -f "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/chrome-extension/manifest.json" ]; then
        echo "   ✅ manifest.json found"
    else
        echo "   ❌ manifest.json missing!"
    fi
    if [ -f "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/chrome-extension/content-scripts/dropdown-filler.js" ]; then
        echo "   ✅ dropdown-filler.js found (NEW)"
    else
        echo "   ❌ dropdown-filler.js missing!"
    fi
else
    echo "   ❌ Extension folder not found!"
fi
echo ""

# Check 2: Jobs Folder
echo "2️⃣  Checking Job Folders..."
JOB_DIR="/Users/nuthanreddyvaddireddy/Desktop/Google Auto"
if [ -d "$JOB_DIR" ]; then
    JOB_COUNT=$(ls "$JOB_DIR" | grep -v "^_" | grep -v "^\.DS_Store" | wc -l | tr -d ' ')
    echo "   ✅ Jobs folder exists: $JOB_DIR"
    echo "   ✅ Found $JOB_COUNT job folders"
else
    echo "   ❌ Jobs folder not found!"
fi
echo ""

# Check 3: Native Messaging
echo "3️⃣  Checking Native Messaging Setup..."
if [ -f "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/chrome-extension/native-messaging/folder_reader.py" ]; then
    echo "   ✅ folder_reader.py exists"
    # Check if it has the correct path
    if grep -q "/Users/nuthanreddyvaddireddy/Desktop/Google Auto" "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/chrome-extension/native-messaging/folder_reader.py"; then
        echo "   ✅ Configured for correct job folder path"
    else
        echo "   ⚠️  Warning: May have wrong path configured"
    fi
else
    echo "   ❌ folder_reader.py missing!"
fi

NATIVE_HOST_PATH="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.smartjobapply.folder_reader.json"
if [ -f "$NATIVE_HOST_PATH" ]; then
    echo "   ✅ Native host already installed"
else
    echo "   ⏭️  Native host NOT installed (run install script)"
fi
echo ""

# Check 4: Sample Job
echo "4️⃣  Checking Sample Job Data..."
SAMPLE_JOB=$(ls "$JOB_DIR" 2>/dev/null | grep -v "^_" | grep -v "^\.DS_Store" | head -1)
if [ -n "$SAMPLE_JOB" ]; then
    echo "   ✅ Sample job: $SAMPLE_JOB"
    if [ -f "$JOB_DIR/$SAMPLE_JOB/apply_url.txt" ]; then
        URL=$(cat "$JOB_DIR/$SAMPLE_JOB/apply_url.txt" | head -1)
        echo "   ✅ URL: ${URL:0:60}..."
    fi
    if [ -f "$JOB_DIR/$SAMPLE_JOB/NuthanReddy.pdf" ]; then
        echo "   ✅ Resume: NuthanReddy.pdf exists"
    else
        echo "   ❌ Resume missing in this folder!"
    fi
else
    echo "   ❌ No jobs found!"
fi
echo ""

# Summary
echo "===================================="
echo "📋 SUMMARY"
echo "===================================="
echo ""
echo "✅ = Ready"
echo "⏭️  = Action needed"
echo "❌ = Problem found"
echo ""
echo "NEXT STEPS:"
echo "1. If native host shows ⏭️ , run:"
echo "   cd ~/Desktop/CERTIFICATES/google/chrome-extension/native-messaging"
echo "   ./install_native_host.sh"
echo ""
echo "2. Load extension in Chrome:"
echo "   chrome://extensions/"
echo "   → Enable Developer Mode"
echo "   → Load unpacked"
echo "   → Select: ~/Desktop/CERTIFICATES/google/chrome-extension"
echo ""
echo "3. Test on a job URL from:"
echo "   cat '$JOB_DIR/$SAMPLE_JOB/apply_url.txt'"
echo ""
