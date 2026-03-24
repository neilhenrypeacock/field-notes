"""
run.py — Main entry point for the Field Notes social media pipeline.

Usage:
    python social/run.py                # normal run (respects 3-day cooldown)
    python social/run.py --dry-run      # print posts, no Facebook/email calls
    python social/run.py --force        # bypass 3-day cooldown
    python social/run.py --send-queued  # post everything in queue.json then clear it
    python social/run.py --dry-run --force
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

# ── Paths ───────────────────────────────────────────────
SOCIAL_DIR = Path(__file__).resolve().parent
BASE_DIR = SOCIAL_DIR.parent
LOGS_DIR = SOCIAL_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "run.log"
LAST_RUN_FILE = SOCIAL_DIR / "last_run.txt"
POSTED_FILE = SOCIAL_DIR / "posted.json"
QUEUE_FILE = SOCIAL_DIR / "queue.json"

COOLDOWN_DAYS = 3

# ── Logging ─────────────────────────────────────────────
_log_level = os.getenv("LOG_LEVEL", "INFO")
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_formatter)

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_formatter)

logging.basicConfig(level=_log_level, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger("field_notes.social.run")

# ── Local imports (after path is set) ───────────────────
sys.path.insert(0, str(BASE_DIR))
from social import scraper_reader, post_generator, facebook_client, digest_email


# ── Cooldown helpers ────────────────────────────────────

def _read_last_run() -> datetime:
    if not LAST_RUN_FILE.exists():
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        ts = LAST_RUN_FILE.read_text().strip()
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _write_last_run() -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LAST_RUN_FILE.write_text(now_str)


# ── Queue helpers ────────────────────────────────────────

def _load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text())
    except Exception:
        return []


def _save_queue(queue: list) -> None:
    tmp = QUEUE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(queue, indent=2, ensure_ascii=False))
    tmp.replace(QUEUE_FILE)


def _clear_queue() -> None:
    _save_queue([])


# ── Send-queued mode ─────────────────────────────────────

def _run_send_queued(dry_run: bool) -> None:
    """Post everything currently in queue.json to Facebook, then clear the queue."""
    queue = _load_queue()
    if not queue:
        logger.info("queue.json is empty — nothing to send.")
        return

    logger.info("send-queued mode: %d item(s) to post", len(queue))
    posted = scraper_reader._load_posted()
    sent = []
    failed = []

    for item in queue:
        headline = item.get("headline", "(no headline)")
        post_text = item.get("post_text", "")
        url = item.get("url", "")

        if not post_text:
            logger.warning("Skipping item with no post_text: %s", headline[:60])
            failed.append(item)
            continue

        if dry_run:
            print(f"\n{'─' * 60}")
            print(f"HEADLINE : {headline}")
            print(f"SOURCE   : {item.get('source', '')}")
            print(f"URL      : {url}")
            print(f"POST:\n{post_text}")
            sent.append(item)
            continue

        try:
            result = facebook_client.post_to_facebook(post_text)
            logger.info(
                "Posted to Facebook: post_id=%s for '%s'",
                result["post_id"],
                headline[:60],
            )
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            posted[url] = {
                "posted_at": now_str,
                "post_text": post_text,
                "source": item.get("source", ""),
                "facebook_post_id": result["post_id"],
                "facebook_url": result["url"],
            }
            sent.append(item)
        except Exception as exc:
            logger.error("Failed to post '%s' to Facebook: %s", headline[:60], exc)
            failed.append(item)

    if not dry_run:
        scraper_reader.save_posted(posted)
        logger.info("Updated posted.json with %d new entries", len(sent))
        # Clear queue only after processing (keep failed items if any)
        if failed:
            logger.warning(
                "%d item(s) failed to post — keeping in queue.json", len(failed)
            )
            _save_queue(failed)
        else:
            _clear_queue()
            logger.info("queue.json cleared.")

    logger.info(
        "send-queued complete: %d sent, %d failed", len(sent), len(failed)
    )


# ── Default mode (generate → save to queue → email digest) ──

def _run_generate(dry_run: bool, force: bool) -> None:
    """Generate posts from scraped data and save to queue.json, then email digest."""

    # 1. Cooldown check
    if not force and not dry_run:
        last_run = _read_last_run()
        elapsed = datetime.now(timezone.utc) - last_run
        if elapsed < timedelta(days=COOLDOWN_DAYS):
            hours_left = (timedelta(days=COOLDOWN_DAYS) - elapsed).total_seconds() / 3600
            logger.info(
                "Last run was %s — cooldown active (%.1fh remaining). Use --force to override.",
                last_run.strftime("%Y-%m-%d %H:%M UTC"),
                hours_left,
            )
            return

    # 2. Get unposted items
    items = scraper_reader.get_unposted_items(max_items=6)
    if not items:
        logger.info("No new items to post — nothing to do.")
        if not dry_run:
            _write_last_run()
        return

    # 3. Generate post text for each item
    queued = []

    for item in items:
        headline = item["headline"]
        logger.info("Processing: %s", headline[:80])

        try:
            post_text = post_generator.generate_post(
                headline=item["headline"],
                summary=item["summary"],
                url=item["url"],
            )
        except Exception as exc:
            logger.error("Post generation failed for '%s': %s", headline[:60], exc)
            continue

        if not post_text:
            logger.warning("Empty post returned for '%s' — skipping", headline[:60])
            continue

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        entry = {
            "id": item["url"],
            "generated_at": now_str,
            "headline": headline,
            "post_text": post_text,
            "source": item["source"],
            "url": item["url"],
        }
        queued.append(entry)

        if dry_run:
            print(f"\n{'─' * 60}")
            print(f"HEADLINE : {headline}")
            print(f"SOURCE   : {item['source']}")
            print(f"URL      : {item['url']}")
            print(f"POST:\n{post_text}")

    if not queued:
        logger.info("No posts successfully generated.")
        if not dry_run:
            _write_last_run()
        return

    # 4. Save to queue.json (only on real run)
    if not dry_run:
        _save_queue(queued)
        logger.info("Saved %d post(s) to queue.json", len(queued))

    # 5. Send digest email — adapt items to the format digest_email expects
    digest_items = [
        {
            "headline": e["headline"],
            "post_text": e["post_text"],
            "scheduled_at_str": e["generated_at"],
            "source": e["source"],
            "url": e["url"],
        }
        for e in queued
    ]
    digest_email.send_digest(digest_items, dry_run=dry_run)

    # 6. Update last_run.txt (only on real run)
    if not dry_run:
        _write_last_run()

    logger.info(
        "=== Generate complete — %d post(s) saved to queue.json ===", len(queued)
    )


# ── Main ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Field Notes: East Anglia — social media pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print posts to terminal; do not call Facebook API or send email",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the 3-day cooldown check",
    )
    parser.add_argument(
        "--send-queued",
        action="store_true",
        help="Post everything in queue.json to Facebook, then clear the queue",
    )
    args = parser.parse_args()
    dry_run = args.dry_run
    force = args.force
    send_queued = args.send_queued

    logger.info(
        "=== Social pipeline start (dry_run=%s, force=%s, send_queued=%s) ===",
        dry_run,
        force,
        send_queued,
    )

    if send_queued:
        _run_send_queued(dry_run=dry_run)
    else:
        _run_generate(dry_run=dry_run, force=force)


if __name__ == "__main__":
    main()
