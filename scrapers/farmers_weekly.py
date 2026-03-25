"""
Scraper: Farmers Weekly
Source: fwi.co.uk/news (HTML scrape — RSS feed not available)
Returns: list of article dicts
Note: Partly paywalled — scraping headlines and summaries from news index only.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Farmers Weekly"
NEWS_URL = "https://www.fwi.co.uk/news"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape():
    # type: () -> List[dict]
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        # FW renders article titles as <h2> without direct <a> wrapping;
        # links appear as sibling/parent elements. Strategy: find all <a href>
        # pointing into /news/..., skip category/nav links (all-caps text).
        seen_urls = set()
        for a in soup.find_all("a", href=True):
            try:
                href = a["href"]
                if not href.startswith("/news/"):
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 15:
                    continue
                # Skip category/nav labels (all caps like "FARM POLICY", "CRIME")
                if title == title.upper():
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                url = "https://www.fwi.co.uk" + href
                articles.append({
                    "title": title,
                    "summary": "",
                    "url": url,
                    "date": "",
                    "source": SOURCE,
                    "tier": "national",
                    "category": "news",
                })
                if len(articles) >= 20:
                    break
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
