"""
Scraper: Anglia Farmer Magazine
Source: angliafarmer.co.uk/feed/
Returns: list of article dicts
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Anglia Farmer"
FEED_URL = "https://www.angliafarmer.co.uk/feed/"
DAYS_BACK = 30


def scrape():
    # type: () -> List[dict]
    try:
        feed = feedparser.parse(FEED_URL)
        if feed.get("bozo") and not feed.entries:
            return []
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=DAYS_BACK)
        articles = []
        for entry in feed.entries:
            try:
                pub = None
                for attr in ("published_parsed", "updated_parsed"):
                    parsed = getattr(entry, attr, None)
                    if parsed:
                        pub = datetime(*parsed[:6], tzinfo=timezone.utc)
                        break
                if pub and pub < cutoff:
                    continue
                title = getattr(entry, "title", "").strip()
                url = getattr(entry, "link", "").strip()
                summary = getattr(entry, "summary", "") or ""
                # Strip HTML tags from summary
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()[:400]
                date_str = pub.strftime("%Y-%m-%dT%H:%M:%SZ") if pub else ""
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "date": date_str,
                    "source": SOURCE,
                    "tier": "local",
                    "category": "news",
                })
            except Exception:
                continue
        return articles
    except Exception:
        return []


if __name__ == "__main__":
    items = scrape()
    print("{}: {} articles".format(SOURCE, len(items)))
    for item in items[:3]:
        print("  {}".format(item["title"]))
