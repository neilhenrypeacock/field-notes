"""
Scraper: Water Resources East
Source: waterresourceseast.co.uk/news (HTML scrape)
Returns: list of article dicts
Fenland drainage, irrigation, abstraction. May publish infrequently.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Water Resources East"
NEWS_URL = "https://wre.org.uk/news/"
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
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        cards = (
            soup.select("article")
            or soup.select(".post")
            or soup.select(".news-item")
            or soup.select(".entry")
        )
        for card in cards[:10]:
            try:
                # wre.org.uk cards have no headings — first <a> link is the title
                link_tag = card.find("a", href=True)
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                url = link_tag.get("href", "")
                if url.startswith("/"):
                    url = "https://wre.org.uk" + url
                if not title:
                    continue
                para = card.find("p")
                summary = para.get_text(strip=True)[:400] if para else ""
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "date": "",
                    "source": SOURCE,
                    "tier": "regional",
                    "category": "policy",
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
