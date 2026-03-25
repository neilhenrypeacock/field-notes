"""
Scraper: ITV Anglia farming news
Source: itv.com/news/anglia (HTML scrape)
Returns: list of article dicts
Note: ITV blocks automated requests — returns [] gracefully.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "ITV Anglia"
NEWS_URL = "https://www.itv.com/news/anglia/topic/farming"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
FARMING_TERMS = [
    "farm", "farming", "arable", "wheat", "barley", "livestock", "nfu",
    "crop", "harvest", "soil", "agriculture", "rural",
]


def scrape():
    # type: () -> List[dict]
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        # ITV news uses article cards with h3 headings
        cards = soup.select("article") or soup.select("[data-testid='article-card']")
        for card in cards[:20]:
            try:
                heading = card.find(["h2", "h3", "h4"])
                if not heading:
                    continue
                link_tag = card.find("a")
                title = heading.get_text(strip=True)
                url = ""
                if link_tag and link_tag.get("href"):
                    url = link_tag["href"]
                    if url.startswith("/"):
                        url = "https://www.itv.com" + url
                if not title:
                    continue
                para = card.find("p")
                summary = para.get_text(strip=True)[:400] if para else ""
                combined = (title + " " + summary).lower()
                if not any(t in combined for t in FARMING_TERMS):
                    continue
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "date": "",
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
