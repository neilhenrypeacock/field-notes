"""
Scraper: Nature Friendly Farming Network (NFFN)
Source: nffn.org.uk/news/ (HTML scrape — no working RSS)
Returns: list of article dicts
SFI and agri-environment scheme developments.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Nature Friendly Farming Network"
NEWS_URL = "https://www.nffn.org.uk/news/"
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
        for card in cards[:15]:
            try:
                heading = card.find(["h2", "h3", "h4"])
                if not heading:
                    continue
                link_tag = heading.find("a") or card.find("a")
                title = heading.get_text(strip=True)
                url = ""
                if link_tag and link_tag.get("href"):
                    url = link_tag["href"]
                    if url.startswith("/"):
                        url = "https://www.nffn.org.uk" + url
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
                    "tier": "national",
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
