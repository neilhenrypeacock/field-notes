"""
social/schedule_posts.py
========================
Run automatically every morning at 06:50 via cron job.
Checks if any approved post is scheduled for today and posts it.

What it does:
1. Reads scheduled_posts.json
2. Finds any approved post scheduled for today at the right time
3. Posts it to the Facebook page via the Graph API
4. Immediately posts the first comment (rotating signup line)
5. Auto-shares to relevant Facebook groups if high value
6. Marks the post as posted in scheduled_posts.json
7. Emails Neil if anything fails

Cron job to add (run: crontab -e):
    50 6 * * * cd /Users/neilpeacock/Projects/fieldnotes && .venv/bin/python social/schedule_posts.py >> social/data/cron.log 2>&1

Usage (manual):
    .venv/bin/python social/schedule_posts.py
    .venv/bin/python social/schedule_posts.py --dry-run   (preview without posting)
    .venv/bin/python social/schedule_posts.py --force-all (post all approved posts now)
"""

import sys
import json
import time
import random
import logging
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path("/Users/neilpeacock/Projects/fieldnotes/.env"), override=True)

from social.config import (
    FB_PAGE_ID,
    FB_PAGE_ACCESS_TOKEN,
    FB_API_BASE,
    SCHEDULED_FILE,
    COMMENTS_FILE,
    GROUPS_FILE,
    POST_HISTORY,
    NEWSLETTER_URL,
    NOTIFICATION_EMAIL,
    GROUP_POST_MIN_CONFIDENCE,
    GROUP_POST_DELAY_SECONDS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M"
)
logger = logging.getLogger(__name__)

DRY_RUN = "--dry-run" in sys.argv
FORCE_ALL = "--force-all" in sys.argv


# ── Facebook API helpers ───────────────────────────────────────────────────

def post_to_page(message: str) -> str:
    """
    Post a message to the Facebook page.
    Returns the post ID on success, raises on failure.
    """
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would post to page:\n{message[:100]}...")
        return "dry_run_post_id"

    url = f"{FB_API_BASE}/{FB_PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "id" not in data:
        raise ValueError(f"Facebook API returned no post ID: {data}")

    post_id = data["id"]
    logger.info(f"✓ Posted to page — post ID: {post_id}")
    return post_id


def post_comment(post_id: str, comment: str) -> str:
    """
    Post the first comment on a published post.
    Returns comment ID on success.
    """
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would post comment: {comment}")
        return "dry_run_comment_id"

    url = f"{FB_API_BASE}/{post_id}/comments"
    payload = {
        "message": comment,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    comment_id = data.get("id", "unknown")
    logger.info(f"✓ First comment posted — ID: {comment_id}")
    return comment_id


def share_to_group(group_id: str, message: str) -> Optional[str]:
    """
    Share a post to a Facebook group.
    Returns post ID on success, None on failure.
    """
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would share to group {group_id}")
        return "dry_run_group_post_id"

    url = f"{FB_API_BASE}/{group_id}/feed"
    payload = {
        "message": message,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }
    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        post_id = data.get("id")
        logger.info(f"✓ Shared to group {group_id} — ID: {post_id}")
        return post_id
    except Exception as e:
        logger.warning(f"⚠ Group share failed for {group_id}: {e}")
        return None


# ── Rotating first comment ─────────────────────────────────────────────────

def get_next_comment() -> str:
    """
    Pick the next first comment from the rotating bank.
    Avoids comments used in the last 7 days.
    Updates recently_used in first_comments.json.
    """
    with open(COMMENTS_FILE) as f:
        data = json.load(f)

    all_comments    = data["comments"]
    recently_used   = data.get("recently_used", [])
    cooldown_days   = data.get("cooldown_days", 7)

    # Clean up old entries from recently_used
    cutoff = datetime.now().timestamp() - (cooldown_days * 86400)
    recently_used = [r for r in recently_used if r["timestamp"] > cutoff]

    used_texts = {r["comment"] for r in recently_used}
    available  = [c for c in all_comments if c not in used_texts]

    # If we've used everything recently, reset (shouldn't happen with 20 options)
    if not available:
        logger.warning("All comments used recently — resetting pool")
        available = all_comments
        recently_used = []

    chosen = random.choice(available)

    # Record usage
    recently_used.append({
        "comment":   chosen,
        "timestamp": datetime.now().timestamp(),
        "date":      datetime.now().strftime("%Y-%m-%d")
    })
    data["recently_used"] = recently_used

    with open(COMMENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return chosen


# ── Group sharing ──────────────────────────────────────────────────────────

def get_eligible_groups(section: str, confidence: str) -> list:
    """Return list of group configs eligible for sharing this post."""
    with open(GROUPS_FILE) as f:
        config = json.load(f)

    # Check minimum confidence level
    confidence_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_required = confidence_order.get(GROUP_POST_MIN_CONFIDENCE, 2)
    post_confidence = confidence_order.get(confidence, 1)

    if post_confidence < min_required:
        logger.info(f"Post confidence {confidence} below group minimum {GROUP_POST_MIN_CONFIDENCE} — skipping groups")
        return []

    eligible = []
    for group in config["groups"]:
        if not group.get("active", False):
            continue
        if "REPLACE_WITH_GROUP_ID" in group.get("group_id", ""):
            continue
        if section in group.get("post_sections", []):
            eligible.append(group)

    return eligible


def handle_group_sharing(post: dict, post_text: str):
    """Share post to eligible groups with delay between each."""
    if not post.get("high_value"):
        return

    section    = post.get("actual_section", post.get("section", ""))
    confidence = post.get("verification", {}).get("confidence", "LOW")
    groups     = get_eligible_groups(section, confidence)

    if not groups:
        return

    logger.info(f"Sharing to {len(groups)} group(s)...")

    # Add newsletter CTA to group post
    group_message = (
        f"{post_text}\n\n"
        f"— Field Notes: East Anglia\n"
        f"Free weekly newsletter for Norfolk, Suffolk & Cambridgeshire farmers\n"
        f"{NEWSLETTER_URL}"
    )

    for group in groups:
        share_to_group(group["group_id"], group_message)
        if not DRY_RUN:
            time.sleep(GROUP_POST_DELAY_SECONDS)


# ── Post history ───────────────────────────────────────────────────────────

def save_to_history(post: dict, fb_post_id: str):
    """Archive a successfully posted item to post_history/."""
    POST_HISTORY.mkdir(exist_ok=True)
    filename = f"{post['date']}_{post['section']}.json"
    record = {
        **post,
        "fb_post_id": fb_post_id,
        "posted_at":  datetime.now().isoformat(),
    }
    with open(POST_HISTORY / filename, "w") as f:
        json.dump(record, f, indent=2)


# ── Email notification ─────────────────────────────────────────────────────

def send_failure_email(subject: str, body: str):
    """
    Send a failure notification email using the Resend API.
    Falls back to logging if email can't be sent.
    """
    try:
        import os, requests as req
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            logger.error(f"Email not sent (no RESEND_API_KEY): {subject}")
            return

        req.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from":    "Field Notes Bot <hello@fieldnoteseastanglia.co.uk>",
                "to":      [NOTIFICATION_EMAIL],
                "subject": f"[Field Notes Social] {subject}",
                "text":    body,
            },
            timeout=10
        )
        logger.info(f"Failure notification sent to {NOTIFICATION_EMAIL}")
    except Exception as e:
        logger.error(f"Could not send failure email: {e}")


# ── Find today's post ──────────────────────────────────────────────────────

def find_todays_posts(posts: list) -> list:
    """Return approved posts scheduled for today that haven't been posted yet."""
    today     = datetime.now().strftime("%Y-%m-%d")
    now_hour  = datetime.now().hour
    now_min   = datetime.now().minute

    due = []
    for post in posts:
        if post.get("posted"):       continue
        if not post.get("approved"): continue
        if post.get("status") in ("blocked", "skipped"): continue
        if post.get("date") != today: continue

        # Check if it's time to post (within 10 minute window)
        scheduled_hour, scheduled_min = map(int, post["time"].split(":"))
        if now_hour == scheduled_hour and abs(now_min - scheduled_min) <= 10:
            due.append(post)
        elif FORCE_ALL:
            due.append(post)

    return due


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if DRY_RUN:
        logger.info("=== DRY RUN MODE — nothing will be posted ===")

    if not SCHEDULED_FILE.exists():
        logger.error("No scheduled_posts.json found. Run generate_posts.py first.")
        sys.exit(1)

    with open(SCHEDULED_FILE) as f:
        data = json.load(f)

    posts = data["posts"]
    due   = find_todays_posts(posts)

    if not due:
        logger.info(f"No posts due at this time ({datetime.now().strftime('%H:%M')})")
        return

    logger.info(f"Found {len(due)} post(s) to publish")

    for post in due:
        label = f"{post['day']} {post['time']} — {post['label']}"
        logger.info(f"Publishing: {label}")

        try:
            post_text = post["post_text"]
            if not post_text:
                raise ValueError("post_text is empty")

            # 1. Post to page
            fb_post_id = post_to_page(post_text)

            # 2. Post first comment immediately
            if not DRY_RUN:
                time.sleep(3)  # Brief pause before comment
            comment = get_next_comment()
            post_comment(fb_post_id, comment)

            # 3. Share to groups if high value
            handle_group_sharing(post, post_text)

            # 4. Mark as posted
            post["posted"]       = True
            post["posted_at"]    = datetime.now().isoformat()
            post["fb_post_id"]   = fb_post_id
            post["comment_used"] = comment

            # 5. Save to history
            save_to_history(post, fb_post_id)

            logger.info(f"✓ Complete: {label}")

        except Exception as e:
            error_msg = f"Failed to post: {label}\nError: {e}"
            logger.error(error_msg)

            # Mark as failed
            post["posted"]       = False
            post["post_error"]   = str(e)
            post["error_at"]     = datetime.now().isoformat()

            # Email Neil
            send_failure_email(
                subject=f"Post failed: {label}",
                body=(
                    f"A scheduled Facebook post failed to publish.\n\n"
                    f"Post: {label}\n"
                    f"Error: {e}\n\n"
                    f"Post text:\n{post.get('post_text', 'N/A')[:500]}\n\n"
                    f"Check social/data/scheduled_posts.json and retry manually if needed."
                )
            )

    # Save updated statuses
    with open(SCHEDULED_FILE, "w") as f:
        json.dump(data, f, indent=2)

    posted_count = sum(1 for p in due if p.get("posted"))
    failed_count = len(due) - posted_count
    logger.info(f"Done. Posted: {posted_count}, Failed: {failed_count}")


if __name__ == "__main__":
    main()
