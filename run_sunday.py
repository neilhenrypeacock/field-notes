"""
social/run_sunday.py
====================
One command. Runs the entire Sunday workflow in the correct order.

What it does:
1. Runs update_prompt.py  — researches best practices, proposes prompt improvements
2. Runs generate_posts.py — scrapes data, writes and verifies all 7 posts
3. Runs review_posts.py   — launches your interactive review session

After this script completes and you've approved posts in the review,
the cron job running schedule_posts.py handles the rest automatically
Monday through Saturday.

Usage:
    cd /Users/neilpeacock/farm/field-notes
    .venv/bin/python social/run_sunday.py

Optional flags:
    --skip-research   Skip the prompt update research (saves ~30 seconds)
    --dry-run         Generate and review posts but don't schedule anything
"""

import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PYTHON = ".venv/bin/python"
SKIP_RESEARCH = "--skip-research" in sys.argv


def run(script: str, description: str, extra_args: list = None):
    """Run a script and handle errors clearly."""
    args = [PYTHON, script] + (extra_args or [])
    print(f"\n{'─'*60}")
    print(f"STEP: {description}")
    print(f"{'─'*60}\n")

    result = subprocess.run(args, cwd="/Users/neilpeacock/farm/field-notes")

    if result.returncode != 0:
        print(f"\n⚠ {description} finished with warnings or errors.")
        print(f"  Check the output above and decide whether to continue.")
        choice = input("\n  Continue anyway? [y/N]: ").strip().lower()
        if choice != "y":
            print("\nSunday run stopped. Fix the issue and run again.\n")
            sys.exit(1)


def main():
    print("\n" + "="*60)
    print("FIELD NOTES: EAST ANGLIA — SUNDAY PIPELINE")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print(f"\nThis will:")
    if not SKIP_RESEARCH:
        print(f"  1. Research Facebook best practices + propose prompt updates")
    print(f"  {'2' if not SKIP_RESEARCH else '1'}. Generate this week's 7 posts")
    print(f"  {'3' if not SKIP_RESEARCH else '2'}. Launch your review session")
    print(f"\nEstimated time: {'3–5' if not SKIP_RESEARCH else '2–3'} minutes\n")

    input("Press ENTER to start, or Ctrl+C to cancel...\n")

    # ── Step 1: Prompt research ────────────────────────────────────────────
    if not SKIP_RESEARCH:
        run(
            "social/update_prompt.py",
            "Weekly prompt research + self-improvement"
        )

        # Ask if they want to apply any proposed changes before generating
        from pathlib import Path
        draft_path = Path("social/data/post_prompt_draft.txt")
        if draft_path.exists():
            print("\n📋 A prompt update has been proposed.")
            print("   Check your email for the summary, or view the diff at:")
            print("   social/data/post_prompt_draft.txt\n")
            choice = input("   Apply the update before generating posts? [y/N]: ").strip().lower()
            if choice == "y":
                run(
                    "social/update_prompt.py",
                    "Applying prompt update",
                    extra_args=["--approve"]
                )
            else:
                print("   Keeping current prompt — draft saved for later.\n")

    # ── Step 2: Generate posts ─────────────────────────────────────────────
    run(
        "social/generate_posts.py",
        "Generating this week's 7 posts"
    )

    # ── Step 3: Review ─────────────────────────────────────────────────────
    run(
        "social/review_posts.py",
        "Your review session"
    )

    # ── Done ───────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("SUNDAY PIPELINE COMPLETE")
    print("="*60)
    print(f"  Finished: {datetime.now().strftime('%H:%M')}")
    print(f"\n  Approved posts will be published automatically")
    print(f"  Monday–Saturday by the cron job.")
    print(f"\n  To check cron is set up:")
    print(f"  crontab -l")
    print(f"\n  If not set up yet, add this line with: crontab -e")
    print(f"  50 6 * * * cd /Users/neilpeacock/farm/field-notes && .venv/bin/python social/schedule_posts.py >> social/data/cron.log 2>&1")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
