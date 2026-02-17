#!/bin/bash
# Setup Daily Gmail Monitoring with Cron
# This will check Gmail every day at 9 AM for new job application responses

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/daily_gmail_monitor.py"
LOG_FILE="$SCRIPT_DIR/gmail_monitor.log"

echo "🔧 Gmail Daily Monitor Setup"
echo "=============================="
echo ""
echo "This will add a cron job to run daily at 9 AM"
echo "Script: $MONITOR_SCRIPT"
echo "Logs: $LOG_FILE"
echo ""

# Create cron command
CRON_CMD="0 9 * * * cd $SCRIPT_DIR && /usr/bin/python3 $MONITOR_SCRIPT >> $LOG_FILE 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$MONITOR_SCRIPT"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "$MONITOR_SCRIPT"
    echo ""
    read -p "Remove and re-add? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing
        crontab -l 2>/dev/null | grep -v "$MONITOR_SCRIPT" | crontab -
        echo "✓ Removed existing cron job"
    else
        echo "❌ Cancelled"
        exit 0
    fi
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "📋 Current cron jobs:"
crontab -l
echo ""
echo "=============================="
echo "✨ Setup Complete!"
echo "=============================="
echo ""
echo "The script will run daily at 9 AM and check your Gmail for:"
echo "  • New application confirmation emails"
echo "  • Company responses"
echo "  • Updates to existing applications"
echo ""
echo "Manual commands:"
echo "  • Run now:       python3 $MONITOR_SCRIPT"
echo "  • View dashboard: python3 $SCRIPT_DIR/application_dashboard.py"
echo "  • View logs:     tail -f $LOG_FILE"
echo "  • Remove cron:   crontab -e  (then delete the line)"
echo ""
