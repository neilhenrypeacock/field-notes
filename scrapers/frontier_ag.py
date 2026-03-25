"""
Scraper: Frontier Agriculture news
Source: frontierag.co.uk (JS-rendered — returns [] gracefully)
Returns: empty list — site requires JavaScript to load article content
Note: If a feed URL becomes available, add it here and switch to feedparser.
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Frontier Agriculture"
# NOTE: frontierag.co.uk news page is JavaScript-rendered (89 script tags, SPA).
# Plain HTTP scraping returns only nav elements. Returns [] gracefully.
# If RSS feed becomes available at /feed or /rss, update FEED_URL below.
FEED_URL = None  # No RSS available as of March 2026


def scrape():
    # type: () -> List[dict]
    # JS-rendered site — cannot scrape without a headless browser.
    # prefilter.py will still score Frontier Agriculture content from other sources.
    return []


if __name__ == "__main__":
    items = scrape()
    print("{}: {} articles".format(SOURCE, len(items)))
    for item in items[:3]:
        print("  {}".format(item["title"]))
