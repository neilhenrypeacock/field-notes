"""
social/review_posts.py
======================
Your Sunday evening review interface.

Displays each post with its full verification card so you can
see exactly what data was used, where it came from, and whether
the AI's post matches it. You sign off with full information.

Usage:
    # Review all posts interactively
    .venv/bin/python social/review_posts.py

    # Approve all ready posts in one go (skips flagged ones for manual review)
    .venv/bin/python social/review_posts.py --approve-all

    # After reviewing, approve everything you've okayed
    .venv/bin/python social/review_posts.py --approve
"""

import sys
import json
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path("/Users/neilpeacock/farm/field-notes/.env"))

from social.config import SCHEDULED_FILE


# ── Terminal colours ───────────────────────────────────────────────────────

class C:
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def bold(s):   return f"{C.BOLD}{s}{C.RESET}"
def green(s):  return f"{C.GREEN}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def red(s):    return f"{C.RED}{s}{C.RESET}"
def dim(s):    return f"{C.DIM}{s}{C.RESET}"


# ── Load and save scheduled posts ─────────────────────────────────────────

def load_posts() -> dict:
    with open(SCHEDULED_FILE) as f:
        return json.load(f)

def save_posts(data: dict):
    with open(SCHEDULED_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Render a verification card ─────────────────────────────────────────────

def render_verification_card(post: dict, index: int, total: int):
    """Print the full verification card for a post."""
    v = post.get("verification", {})
    section = post.get("actual_section", post.get("section", "unknown"))

    print("\n" + "━"*62)
    print(bold(f"POST {index} OF {total}  —  {post['day']} {post['time']}"))
    print(bold(f"Topic: {post['label']}"))
    print("━"*62)

    # Status banner
    status = post["status"]
    if status == "blocked":
        print(red(f"\n🔴 BLOCKED — {post.get('block_reason', 'unknown reason')}"))
        print(dim("This post will not be published.\n"))
        return False

    elif status == "flagged":
        print(yellow(f"\n🟡 FLAGGED — low confidence. Review every number carefully.\n"))
    else:
        print(green(f"\n🟢 {v.get('status_line', 'READY TO SCHEDULE')}\n"))

    # Data used
    raw = post.get("raw_data", {})
    if raw and section != "monday_newsletter":
        print(bold("DATA USED:"))
        for key, val in raw.items():
            if key not in ("section", "raw", "data_date") and val not in (None, "", "None"):
                print(f"  {key}: {val}")
        if raw.get("data_date"):
            print(f"  Data date: {raw['data_date']}")
        print()

    # Gate 1 summary
    checks   = v.get("gate1_checks", [])
    warnings = v.get("gate1_warnings", [])
    errors   = v.get("gate1_errors", [])

    if section != "monday_newsletter":
        print(bold("GATE 1 — DATA VALIDATION:"))
        for c in checks:
            print(f"  {green(c)}")
        for w in warnings:
            print(f"  {yellow('⚠ ' + w)}")
        for e in errors:
            print(f"  {red('✗ ' + e)}")
        print()

    # Gate 2 summary
    g2_summary = v.get("gate2_summary", "")
    g2_notes   = v.get("gate2_notes", [])
    confidence = v.get("confidence", "UNKNOWN")

    if section != "monday_newsletter":
        print(bold("GATE 2 — AI VERIFICATION:"))
        if confidence == "HIGH":
            print(f"  {green(g2_summary)}")
        elif confidence == "MEDIUM":
            print(f"  {yellow(g2_summary)}")
        else:
            print(f"  {yellow(g2_summary)}")
        for note in g2_notes:
            print(f"  {yellow('⚠ ' + note)}")
        print()

    # The post itself
    print(bold("POST TEXT:"))
    print("─"*62)
    post_text = post.get("post_text", "")
    # Wrap long lines for readability
    for line in post_text.split("\n"):
        if len(line) > 60:
            wrapped = textwrap.fill(line, width=60, subsequent_indent="  ")
            print(wrapped)
        else:
            print(line)
    print("─"*62)

    # First comment preview
    print(dim("\nFIRST COMMENT (assigned at schedule time):"))
    print(dim("  One of the rotating signup variations from first_comments.json"))

    # High value / group sharing note
    if post.get("high_value"):
        print(yellow("\n⭐ HIGH VALUE — will be auto-shared to relevant Facebook groups"))

    return True


# ── Interactive review ─────────────────────────────────────────────────────

def interactive_review(data: dict):
    """Walk through each post one by one for review."""
    posts = data["posts"]
    total = len(posts)
    reviewable = [p for p in posts if p["status"] != "blocked"]

    if not reviewable:
        print(red("\nNo posts to review — all were blocked during generation."))
        print("Run generate_posts.py again after checking your scrapers.\n")
        return

    print(f"\n{bold('FIELD NOTES: EAST ANGLIA — POST REVIEW')}")
    print(f"Generated: {data.get('generated_at', 'unknown')}")
    print(f"Posts to review: {len(reviewable)} of {total}")
    print(f"\nFor each post:")
    print(f"  ENTER     → approve as-is")
    print(f"  e / edit  → open the JSON file to edit this post manually")
    print(f"  s / skip  → drop this post (won't be published this week)")
    print(f"  q / quit  → stop here, save progress\n")

    approved_count = 0
    skipped_count  = 0

    for i, post in enumerate(posts, 1):
        is_viewable = render_verification_card(post, i, total)

        if not is_viewable:
            # Blocked post — nothing to do
            input(dim("\n  Press ENTER to continue..."))
            continue

        while True:
            try:
                choice = input(f"\n  [{i}/{total}] Approve / Edit / Skip / Quit: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n\nReview interrupted. Progress saved.")
                break

            if choice in ("", "a", "approve"):
                post["approved"] = True
                post["approved_at"] = datetime.now().isoformat()
                approved_count += 1
                print(green("  ✓ Approved"))
                break

            elif choice in ("e", "edit"):
                print(f"\n  Open this file and edit the post_text for post {i}:")
                print(f"  {SCHEDULED_FILE}")
                print(f"  Look for: \"{post['day']} {post['time']} {post['label']}\"")
                print(f"  After editing, come back and press ENTER to approve.")
                # Reload in case they edited it
                input("  Press ENTER when done editing... ")
                data = load_posts()
                posts = data["posts"]
                post = posts[i-1]
                post["approved"] = True
                post["approved_at"] = datetime.now().isoformat()
                post["manually_edited"] = True
                approved_count += 1
                print(green("  ✓ Approved (manually edited)"))
                break

            elif choice in ("s", "skip"):
                post["status"] = "skipped"
                post["approved"] = False
                skipped_count += 1
                print(yellow("  ↷ Skipped — this post will not be published"))
                break

            elif choice in ("q", "quit"):
                print("\nReview paused. Run review_posts.py again to continue.")
                save_posts(data)
                sys.exit(0)

            else:
                print("  Type ENTER to approve, 'e' to edit, 's' to skip, 'q' to quit")

        save_posts(data)

    # Summary
    print("\n" + "="*62)
    print(bold("REVIEW COMPLETE"))
    print("="*62)
    print(f"  Approved: {approved_count}")
    print(f"  Skipped:  {skipped_count}")
    blocked = sum(1 for p in posts if p["status"] == "blocked")
    print(f"  Blocked:  {blocked} (not publishable)")
    print(f"\n  Approved posts will be scheduled automatically")
    print(f"  by the cron job running schedule_posts.py each morning.")
    print("="*62 + "\n")


# ── Approve-all mode ───────────────────────────────────────────────────────

def approve_all(data: dict):
    """Approve all ready posts, skip flagged ones for manual review."""
    posts = data["posts"]
    approved = 0
    needs_review = 0

    for post in posts:
        if post["status"] == "ready" and not post["approved"]:
            post["approved"] = True
            post["approved_at"] = datetime.now().isoformat()
            approved += 1
        elif post["status"] == "flagged":
            print(yellow(f"  ⚠ Skipping flagged post: {post['day']} {post['time']} {post['label']}"))
            needs_review += 1

    save_posts(data)
    print(green(f"\n✓ Approved {approved} posts."))
    if needs_review:
        print(yellow(f"⚠ {needs_review} flagged post(s) need manual review."))
        print("  Run without --approve-all to review them individually.")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if not SCHEDULED_FILE.exists():
        print(red("\nNo scheduled_posts.json found."))
        print("Run generate_posts.py first.\n")
        sys.exit(1)

    data = load_posts()

    if "--approve-all" in sys.argv:
        approve_all(data)
    elif "--approve" in sys.argv:
        # Just mark everything that was already reviewed as approved
        approve_all(data)
    else:
        interactive_review(data)


if __name__ == "__main__":
    main()
