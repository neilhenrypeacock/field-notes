"""
Scraper: Defra Farming Blog RSS feed.
Outputs: data/defra_blog.json
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, save_data

logger = logging.getLogger("field_notes.defra_blog")

FEED_URL = "https://defrafarming.blog.gov.uk/feed/"
DAYS_BACK = 8


def _text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text[:500]


def _parse_date(entry) -> "str | None":
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def scrape() -> dict:
    logger.info("Fetching Defra blog feed: %s", FEED_URL)
    feed = feedparser.parse(FEED_URL)

    if feed.bozo and not feed.entries:
        logger.error("Failed to parse Defra blog feed: %s", feed.bozo_exception)
        return {"error": True, "message": str(feed.bozo_exception)}

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    entries = []

    for entry in feed.entries:
        pub_str = _parse_date(entry)
        if pub_str:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            if pub_dt < cutoff:
                continue

        content_html = ""
        if hasattr(entry, "content") and entry.content:
            content_html = entry.content[0].value
        elif hasattr(entry, "summary"):
            content_html = entry.summary

        tags = [t.term for t in getattr(entry, "tags", [])]

        entries.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "author": entry.get("author", ""),
            "published": pub_str,
            "summary": _text_from_html(content_html),
            "tags": tags,
        })

    logger.info("Found %d Defra blog entries in last %d days", len(entries), DAYS_BACK)
    return {
        "source": "Defra Farming Blog",
        "feed_url": FEED_URL,
        "entries": entries,
        "count": len(entries),
    }


if __name__ == "__main__":
    archive_current("defra_blog.json")
    data = scrape()
    save_data("defra_blog.json", data)
    print(f"Saved {data.get('count', 0)} entries")
