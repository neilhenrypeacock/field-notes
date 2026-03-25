"""
Scraper: UK Agri-Tech Centre
Source: ukagritechcentre.com/news (HTML scrape)
Returns: list of article dicts
Grant rounds and innovation funding.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "UK Agri-Tech Centre"
NEWS_URL = "https://www.ukagritechcentre.com/news"
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
            or soup.select(".news-item")
            or soup.select(".card")
            or soup.select(".post")
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
                        url = "https://www.ukagritechcentre.com" + url
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
