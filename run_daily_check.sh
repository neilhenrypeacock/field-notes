#!/bin/bash
# Runs the daily RSS monitor for urgent Defra/scheme changes.
# Cron: 0 6 * * * (BST: 0 5 * * *)

set -e
cd "$(dirname "$0")"
source .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/monitor.log"

echo "--- Daily check: $(date) ---" >> "$LOG_FILE"
python monitor/daily_check.py >> "$LOG_FILE" 2>&1
echo "--- Done ---" >> "$LOG_FILE"
