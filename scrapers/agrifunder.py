"""
Scraper: AgFunder News
Source: agfundernews.com/feed
Returns: list of article dicts
Note: Apply keyword filter aggressively — UK and Europe stories only.
      Discard US, Asia, developing world content.
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "AgFunder News"
FEED_URL = "https://agfundernews.com/feed"
DAYS_BACK = 14

# Pre-filter: discard articles with zero UK/Europe/global-tech relevance
# prefilter.py's score_article() does the final relevance scoring
UK_OR_GLOBAL_TECH = [
    "uk", "united kingdom", "britain", "british", "england", "europe", "european",
    "eu ", "defra", "ahdb", "innovate uk", "ukri", "global", "investment", "fund",
    "startup", "agritech", "agri-tech", "agtech", "precision", "robot", "autonomou",
    "fertil", "carbon", "soil", "crop", "farm",
]


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
                summary = re.sub(r"<[^>]+>", "", summary).strip()[:400]
                combined = (title + " " + summary).lower()

                # Light pre-filter: must have at least one relevant term
                # prefilter.py Tier A/B/C scoring will do the real filtering
                if not any(term in combined for term in UK_OR_GLOBAL_TECH):
                    continue

                date_str = pub.strftime("%Y-%m-%dT%H:%M:%SZ") if pub else ""
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "date": date_str,
                    "source": SOURCE,
                    "tier": "national",
                    "category": "agritech",
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
