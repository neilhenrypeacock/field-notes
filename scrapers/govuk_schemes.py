"""
Scraper: GOV.UK Find Funding for Land or Farms (Atom feed).
Detects new and recently-updated schemes for newsletter schemes section.
Outputs: data/govuk_schemes.json
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, load_previous, save_data

logger = logging.getLogger("field_notes.govuk_schemes")

FEED_URL = "https://www.gov.uk/find-funding-for-land-or-farms.atom"
DAYS_BACK = 8


def _parse_updated(entry) -> "str | None":
    parsed = getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def scrape() -> dict:
    logger.info("Fetching GOV.UK schemes feed: %s", FEED_URL)
    feed = feedparser.parse(FEED_URL)

    if feed.bozo and not feed.entries:
        logger.error("Failed to parse GOV.UK schemes feed: %s", feed.bozo_exception)
        return {"error": True, "message": str(feed.bozo_exception)}

    previous = load_previous("govuk_schemes.json")
    prev_ids = {e["id"] for e in previous.get("all_entries", [])}

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    all_entries = []
    new_this_week = []
    updated_this_week = []

    for entry in feed.entries:
        entry_id = entry.get("id", entry.get("link", ""))
        updated_str = _parse_updated(entry)
        record = {
            "id": entry_id,
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "updated": updated_str,
        }
        all_entries.append(record)

        if updated_str:
            updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            if updated_dt >= cutoff:
                if entry_id not in prev_ids:
                    new_this_week.append({**record, "status": "new"})
                else:
                    updated_this_week.append({**record, "status": "updated"})

    logger.info(
        "Total schemes: %d — new: %d, updated: %d",
        len(all_entries), len(new_this_week), len(updated_this_week),
    )
    return {
        "source": "GOV.UK Find Funding for Land or Farms",
        "feed_url": FEED_URL,
        "total_schemes": len(all_entries),
        "new_this_week": new_this_week,
        "updated_this_week": updated_this_week,
        "all_entries": all_entries,
    }


if __name__ == "__main__":
    archive_current("govuk_schemes.json")
    data = scrape()
    save_data("govuk_schemes.json", data)
    print(f"Total: {data.get('total_schemes', 0)}, new: {len(data.get('new_this_week', []))}, updated: {len(data.get('updated_this_week', []))}")
