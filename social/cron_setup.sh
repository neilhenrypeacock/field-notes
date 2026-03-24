#!/usr/bin/env bash
# cron_setup.sh — Install the Field Notes social media cron job.
#
# Runs social/run.py every 3 days at 06:00 server time.
# The script uses cron day-of-month syntax (*/3) for approximate 3-day spacing;
# the exact 3-day cooldown is enforced by last_run.txt inside run.py.
#
# Usage:
#   bash social/cron_setup.sh
#
# To verify:
#   crontab -l | grep social
#
# To remove:
#   crontab -l | grep -v 'social/run.py' | crontab -

set -euo pipefail

# ── Detect project directory ─────────────────────────────
# Allow override via FIELD_NOTES_DIR env var, otherwise auto-detect
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${FIELD_NOTES_DIR:-$(dirname "$SCRIPT_DIR")}"

PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG="$PROJECT_DIR/social/logs/run.log"

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Python not found at $PYTHON"
    echo "Set FIELD_NOTES_DIR env var or run from within the project directory."
    exit 1
fi

# ── Build cron line ──────────────────────────────────────
# Run at 06:00 on days 1, 4, 7, 10... of the month (every ~3 days)
CRON_LINE="0 6 */3 * * cd \"$PROJECT_DIR\" && \"$PYTHON\" social/run.py >> \"$LOG\" 2>&1"

# ── Install (idempotent: remove old entry first) ─────────
( crontab -l 2>/dev/null | grep -v 'social/run\.py' ; echo "$CRON_LINE" ) | crontab -

echo "Cron job installed for: $PROJECT_DIR"
echo ""
echo "Schedule: 06:00 on days 1, 4, 7, 10, 13, 16, 19, 22, 25, 28 of each month"
echo "Python:   $PYTHON"
echo "Log:      $LOG"
echo ""
echo "To verify:"
echo "  crontab -l | grep social"
echo ""
echo "To test immediately (dry-run):"
echo "  cd \"$PROJECT_DIR\" && \"$PYTHON\" social/run.py --dry-run"
