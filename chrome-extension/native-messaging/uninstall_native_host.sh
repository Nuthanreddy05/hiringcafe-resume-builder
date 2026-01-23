#!/bin/bash

HOST_NAME="com.smartjobapply.folder_reader"
HOST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
MANIFEST_TARGET="$HOST_DIR/$HOST_NAME.json"

if [ -f "$MANIFEST_TARGET" ]; then
    rm "$MANIFEST_TARGET"
    echo "✅ Removed Host Manifest: $MANIFEST_TARGET"
else
    echo "⚠️ Host Manifest NOT found (Already removed?)"
fi

echo "🗑️ Uninstall Complete."
