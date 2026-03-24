"""
Daily monitor: checks Defra blog and GOV.UK schemes feeds for changes.
Appends detected changes to monitor/changelog.json.
Run daily at 6am via cron.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("field_notes.monitor")

CHANGELOG_PATH = Path(__file__).resolve().parent / "changelog.json"

FEEDS_TO_MONITOR = [
    {
        "name": "Defra Farming Blog",
        "url": "https://defrafarming.blog.gov.uk/feed/",
        "date_field": "published_parsed",
    },
    {
        "name": "GOV.UK Farming Schemes",
        "url": "https://www.gov.uk/find-funding-for-land-or-farms.atom",
        "date_field": "updated_parsed",
    },
]


def _load_changelog() -> dict:
    if not CHANGELOG_PATH.exists():
        return {"last_checked": None, "changes": [], "seen_ids": []}
    try:
        return json.loads(CHANGELOG_PATH.read_text())
    except Exception:
        return {"last_checked": None, "changes": [], "seen_ids": []}


def _save_changelog(data: dict) -> None:
    data["last_checked"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Keep only last 500 changes and 2000 seen IDs
    data["changes"] = data["changes"][-500:]
    data["seen_ids"] = data["seen_ids"][-2000:]
    CHANGELOG_PATH.write_text(json.dumps(data, indent=2))


def _parse_entry_date(entry, date_field: str):
    parsed = getattr(entry, date_field, None)
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def check_feeds() -> list[dict]:
    changelog = _load_changelog()
    seen_ids = set(changelog.get("seen_ids", []))
    new_changes = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)  # slightly over 24h to avoid gaps

    for feed_config in FEEDS_TO_MONITOR:
        name = feed_config["name"]
        url = feed_config["url"]
        date_field = feed_config["date_field"]

        logger.info("Checking %s", name)
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning("%s: feed parse failed", name)
            continue

        for entry in feed.entries:
            entry_id = entry.get("id") or entry.get("link", "")
            entry_date = _parse_entry_date(entry, date_field)

            if entry_id in seen_ids:
                continue

            if entry_date and entry_date < cutoff:
                # Old entry not seen before — add to seen but not to new changes
                seen_ids.add(entry_id)
                continue

            title = entry.get("title", "Untitled")
            url_entry = entry.get("link", "")
            date_str = entry_date.strftime("%Y-%m-%dT%H:%M:%SZ") if entry_date else None

            change = {
                "source": name,
                "type": "new_post" if name == "Defra Farming Blog" else "scheme_update",
                "title": title,
                "url": url_entry,
                "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "published": date_str,
            }
            new_changes.append(change)
            seen_ids.add(entry_id)
            logger.info("NEW: [%s] %s", name, title)

    # Update changelog
    changelog["changes"].extend(new_changes)
    changelog["seen_ids"] = list(seen_ids)
    _save_changelog(changelog)

    logger.info("Daily check complete. %d new items detected.", len(new_changes))
    return new_changes


if __name__ == "__main__":
    changes = check_feeds()
    if changes:
        print(f"Detected {len(changes)} new items:")
        for c in changes:
            print(f"  [{c['source']}] {c['title']}")
    else:
        print("No new items detected.")
