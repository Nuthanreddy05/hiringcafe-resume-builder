#!/bin/bash
# Monitor job scraping progress in real-time

echo "📊 JOB SCRAPING MONITOR"
echo "======================"
echo ""

# Find the latest log file
LATEST_LOG=$(ls -t job_scrape_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ No log file found!"
    echo "Looking for: job_scrape_*.log"
    exit 1
fi

echo "📝 Log file: $LATEST_LOG"
echo ""

# Check if process is running
if pgrep -f "job_auto_apply_internet.py" > /dev/null; then
    echo "✅ Scraping process is RUNNING"
    PID=$(pgrep -f "job_auto_apply_internet.py")
    echo "🔢 Process ID: $PID"
else
    echo "⏸️  Scraping process has FINISHED or STOPPED"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 PROGRESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count processed jobs
PROCESSED=$(ls ~/Desktop/Google\ Auto/ 2>/dev/null | grep -v "^_" | grep -v "^\.DS_Store" | wc -l | tr -d ' ')
echo "📁 Total jobs in folder: $PROCESSED"

# Show recent activity from log (last 30 lines)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RECENT ACTIVITY (last 30 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -30 "$LATEST_LOG"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 COMMANDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Watch live: tail -f $LATEST_LOG"
echo "Stop process: pkill -f job_auto_apply_internet.py"
echo "Check again: ./monitor_scraping.sh"
echo ""
