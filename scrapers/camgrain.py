"""
Scraper: Camgrain — farmer-owned grain co-operative
Source: camgrain.co.uk/news (HTML scrape)
Returns: list of article dicts
Mainly harvest and storage period — returns [] gracefully off-season.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "Camgrain"
NEWS_URL = "https://www.camgrain.co.uk/news"
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

        # Camgrain uses .postTitle divs containing h3 > a
        cards = soup.select(".postTitle") or soup.select("article") or soup.select(".post")
        for card in cards[:10]:
            try:
                heading = card.find(["h2", "h3", "h4"])
                if not heading:
                    continue
                link_tag = heading.find("a") or card.find("a")
                title = heading.get_text(strip=True)
                url = ""
                if link_tag and link_tag.get("href"):
                    url = link_tag["href"]
                    if not url.startswith("http"):
                        url = "https://www.camgrain.co.uk" + url
                if not title or not url:
                    continue
                # Skip nav items
                if title.lower() in ("about", "news", "contact", "members", "home"):
                    continue
                para = card.find("p")
                summary = para.get_text(strip=True)[:400] if para else ""
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "date": "",
                    "source": SOURCE,
                    "tier": "local",
                    "category": "markets",
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
