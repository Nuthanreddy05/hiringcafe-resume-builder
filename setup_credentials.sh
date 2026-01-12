#!/bin/bash

# 1. Prompt for Gmail User
echo "=================================================================="
echo "🔐  Secure Credential Setup"
echo "=================================================================="
echo "This script will temporarily set your environment variables."
echo "Your password will NOT be shown on screen."
echo "=================================================================="
echo ""

read -p "Enter your Gmail Address (e.g. user@gmail.com): " GMAIL_USER_INPUT

# 2. Prompt for App Password (Hidden)
echo ""
echo "Enter your 16-character Google App Password:"
read -s GMAIL_APP_PASS_INPUT

# 3. Export variables
export GMAIL_USER="nuthanreddy001@gmail.com"
export GMAIL_APP_PASSWORD="myei aato ufna blko"

echo ""
echo "✅ Environment variables set for this session."
echo ""

# 4. Prompt for Default Password update (Optional)
echo "Do you want to update the 'default_password' in profile.json?"
echo "(This is the password used to CREATE new accounts on job sites)"
read -p "[y/N]: " UPDATE_PROFILE

if [[ "$UPDATE_PROFILE" =~ ^[Yy]$ ]]; then
    echo ""
    read -p "Enter new default password for job sites (e.g. Workday123!): " NEW_DEF_PASS
    # Simple sed replacement or python one-liner to update json
    # Using python for safety
    python3 -c "import json; p=json.load(open('profile.json')); p['default_password'] = '$NEW_DEF_PASS'; json.dump(p, open('profile.json', 'w'), indent=4)"
    echo "✅ profile.json updated."
fi

echo ""
echo "🔍 Running diagnostic check..."
python3 check_gmail.py
