"""
Scraper: NFU East Anglia
Source: nfuonline.com/regions/east-anglia/ (HTML scrape)
Returns: list of article dicts
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "NFU East Anglia"
NEWS_URL = "https://www.nfuonline.com/regions/east-anglia/"
HEADERS = {"User-Agent": "FieldNotes/1.0 (East Anglia farming newsletter)"}


def scrape():
    # type: () -> List[dict]
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        # NFU uses card patterns — try several selectors
        cards = (
            soup.select("article")
            or soup.select(".card")
            or soup.select(".listing-item")
            or soup.select(".news-item")
        )

        for card in cards[:15]:
            try:
                link_tag = card.find("a")
                if not link_tag:
                    continue
                url = link_tag.get("href", "")
                if url.startswith("/"):
                    url = "https://www.nfuonline.com" + url

                # NFU cards use <p> for title text, not headings
                heading = card.find(["h2", "h3", "h4"])
                if heading:
                    title = heading.get_text(strip=True)
                else:
                    title = link_tag.get_text(strip=True)

                if not title or not url:
                    continue

                # Summary: second <p> if present
                paras = card.find_all("p")
                summary = paras[1].get_text(strip=True)[:400] if len(paras) > 1 else (
                    paras[0].get_text(strip=True)[:400] if paras else ""
                )

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
