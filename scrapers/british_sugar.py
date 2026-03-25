"""
Scraper: British Sugar
Source: britishsugar.co.uk/media/news (HTML scrape)
Returns: list of article dicts
Particularly important Sep–Mar campaign season.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "British Sugar"
NEWS_URL = "https://www.britishsugar.co.uk/media/news"
HEADERS = {"User-Agent": "FieldNotes/1.0 (East Anglia farming newsletter)"}


def scrape():
    # type: () -> List[dict]
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        # Try common article/card patterns
        cards = (
            soup.select("article")
            or soup.select(".news-item")
            or soup.select(".card")
            or soup.select(".media-item")
        )
        if not cards:
            # Fallback: find all links containing /news/ or /media/
            links = soup.find_all("a", href=re.compile(r"/(news|media)/"))
            for link in links[:15]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href.startswith("/"):
                    href = "https://www.britishsugar.co.uk" + href
                if title and href:
                    articles.append({
                        "title": title,
                        "summary": "",
                        "url": href,
                        "date": "",
                        "source": SOURCE,
                        "tier": "local",
                        "category": "news",
                    })
            return articles

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
                        url = "https://www.britishsugar.co.uk" + url
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
