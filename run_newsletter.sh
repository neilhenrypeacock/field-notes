#!/bin/bash
# Generates and sends the newsletter. Called by cron Monday morning.
# Cron: 0 5 * * 1 (BST: 0 4 * * 1)
# Set NEWSLETTER_ENV=draft in .env to review before live send.

set -e
cd "$(dirname "$0")"
source .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/newsletter_$(date +%Y%m%d).log"

echo "====== Field Notes newsletter run: $(date) ======" >> "$LOG_FILE"

echo "--- Generating newsletter ---" >> "$LOG_FILE"
if python newsletter/generate.py >> "$LOG_FILE" 2>&1; then
    echo "--- Generate: OK ---" >> "$LOG_FILE"
else
    echo "--- Generate: FAILED ---" >> "$LOG_FILE"
    exit 1
fi

echo "--- Sending newsletter ---" >> "$LOG_FILE"
if python newsletter/send.py >> "$LOG_FILE" 2>&1; then
    echo "--- Send: OK ---" >> "$LOG_FILE"
else
    echo "--- Send: FAILED ---" >> "$LOG_FILE"
    exit 1
fi

echo "====== Newsletter run complete: $(date) ======" >> "$LOG_FILE"
echo "Newsletter sent. Log: $LOG_FILE"
