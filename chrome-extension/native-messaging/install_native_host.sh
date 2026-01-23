#!/bin/bash

# Configuration
# Configuration
HOST_NAME="com.smartjobapply.folder_reader"
HOST_ROOT="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
INSTALL_DIR="$HOME/Library/Application Support/com.smartjobapply.folder_reader"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Using wrapper script to handle environment paths
PYTHON_SCRIPT="$SCRIPT_DIR/run_host.sh"
MANIFEST_TEMPLATE="$SCRIPT_DIR/host-manifest.json"
MANIFEST_TARGET="$HOST_ROOT/$HOST_NAME.json"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🚀 Installing SmartJobApply Native Host..."

# 1. Sanity Checks
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: run_host.sh not found at $PYTHON_SCRIPT${NC}"
    exit 1
fi

if [ ! -f "$MANIFEST_TEMPLATE" ]; then
    echo -e "${RED}Error: host-manifest.json template not found at $MANIFEST_TEMPLATE${NC}"
    # We will create a dummy one if Phase 1.5 hasn't run yet, but ideally it should exist
    echo "⚠️  Wait! You need to create host-manifest.json with your Extension ID first."
    echo "    Run this script AFTER Phase 1.5."
    exit 1
fi

# 2. Setup Install Directory
echo "📂 Setting up install directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/folder_reader.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/run_host.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/upload_automation.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/run_host.sh"
chmod +x "$INSTALL_DIR/folder_reader.py"
chmod +x "$INSTALL_DIR/upload_automation.py"

# 3. Create Host Directory if missing
mkdir -p "$HOST_ROOT"

# 4. Copy/Gen Manifest
# Use a temporary file to inject the absolute path
TARGET_BIN="$INSTALL_DIR/run_host.sh"
cat "$MANIFEST_TEMPLATE" | sed "s|PATH_TO_PYTHON_SCRIPT|$TARGET_BIN|g" > "$MANIFEST_TARGET"

if [ -f "$MANIFEST_TARGET" ]; then
    echo -e "${GREEN}✅ Installed Host Manifest to: $MANIFEST_TARGET${NC}"
    echo "   Target Script: $TARGET_BIN"
else
    echo -e "${RED}❌ Failed to write manifest file.${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo "Test command: ./folder_reader.py (Standalone)"
