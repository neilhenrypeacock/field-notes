"""
Scraper: AIC — Agricultural Industries Confederation
Source: agindustries.org.uk (HTML scrape — no global RSS, sector-specific pages)
Returns: list of article dicts
Note: Targets combinable crops and fertiliser sectors — most relevant to EA arable.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SOURCE = "AIC"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
# Combinable crops and fertiliser — most relevant to EA arable farmers
NEWS_URLS = [
    "https://www.agindustries.org.uk/sectors/combinable-crops/news-and-briefings.html",
    "https://www.agindustries.org.uk/sectors/fertiliser/news-and-briefings.html",
]
BASE = "https://www.agindustries.org.uk"


def scrape():
    # type: () -> List[dict]
    articles = []
    seen_urls = set()
    for news_url in NEWS_URLS:
        try:
            resp = requests.get(news_url, headers=HEADERS, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("article") or soup.select(".news-item") or soup.select(".post")
            if not cards:
                # Fallback: find article links
                links = soup.find_all("a", href=re.compile(r"\.(html|htm)$"))
                for link in links[:10]:
                    title = link.get_text(strip=True)
                    url = link.get("href", "")
                    if url.startswith("/"):
                        url = BASE + url
                    if title and url and url not in seen_urls and len(title) > 15:
                        seen_urls.add(url)
                        articles.append({
                            "title": title,
                            "summary": "",
                            "url": url,
                            "date": "",
                            "source": SOURCE,
                            "tier": "national",
                            "category": "policy",
                        })
                continue
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
                        if url.startswith("/"):
                            url = BASE + url
                    if not title or url in seen_urls:
                        continue
                    seen_urls.add(url)
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
        except Exception:
            continue
    return articles


if __name__ == "__main__":
    items = scrape()
    print("{}: {} articles".format(SOURCE, len(items)))
    for item in items[:3]:
        print("  {}".format(item["title"]))
