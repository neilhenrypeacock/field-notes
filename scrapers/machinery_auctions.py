"""
Scraper: Cheffins machinery auction calendar and news.
Note: AuctionMarts (cheffins.auctionmarts.com) blocks non-browser agents.
Uses main Cheffins site only.
Outputs: data/machinery_auctions.json
"""

import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.machinery_auctions")

CALENDAR_URL = "https://www.cheffins.co.uk/machinery-vintage-auctions/auction-calendar.htm"
NEWS_URL = "https://www.cheffins.co.uk/machinery-vintage-auctions/news.htm"

# FETF 2026 window (17 March – 28 April 2026)
FETF_OPEN = date(2026, 3, 17)
FETF_CLOSE = date(2026, 4, 28)
FETF_NOTE = (
    "FETF 2026 is currently open (closes 28 April 2026). "
    "Many items at Cheffins sales are FETF-eligible. "
    "Check eligible items at gov.uk/government/publications/farming-equipment-and-technology-fund-fetf-2026."
)

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date_from_text(text: str) -> "str | None":
    match = re.search(
        r"(\d{1,2})\s+(" + "|".join(MONTH_NAMES.keys()) + r")\s+(\d{4})",
        text,
        re.I,
    )
    if match:
        day = int(match.group(1))
        month = MONTH_NAMES[match.group(2).lower()]
        year = int(match.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass
    return None


def _scrape_calendar() -> list[dict]:
    logger.info("Fetching Cheffins calendar: %s", CALENDAR_URL)
    try:
        resp = get(CALENDAR_URL)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("Calendar fetch failed: %s", exc)
        return []

    sales = []
    # Look for sale cards — typically articles, sections, or divs with date info
    containers = soup.find_all(["article", "section", "div"], limit=100)
    for container in containers:
        text = container.get_text(" ", strip=True)
        if not re.search(r"\d{4}", text):  # Must have a year
            continue
        date_str = _parse_date_from_text(text)
        if not date_str:
            continue
        # Avoid duplicates by checking minimal text length
        if len(text) < 20:
            continue

        title_el = container.find(["h2", "h3", "h4", "strong"])
        title = title_el.get_text(strip=True) if title_el else text[:80]

        link_el = container.find("a", href=True)
        href = link_el["href"] if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.cheffins.co.uk" + href

        # Detect sale type
        sale_type = "General"
        if "vintage" in text.lower():
            sale_type = "Vintage"
        elif "timed" in text.lower():
            sale_type = "Timed Online"
        elif "cambridge" in text.lower() or "machinery" in text.lower():
            sale_type = "Cambridge Machinery Sale"

        sale = {
            "title": title,
            "type": sale_type,
            "starts": date_str,
            "ends": date_str,
            "location": "Cambridge" if "cambridge" in text.lower() else "East Anglia",
            "catalogue_url": href,
        }
        # Avoid duplicates
        if not any(s["title"] == sale["title"] and s["starts"] == sale["starts"] for s in sales):
            sales.append(sale)

    logger.info("Found %d upcoming sales", len(sales))
    return sales[:10]


def _scrape_news() -> list[dict]:
    logger.info("Fetching Cheffins news: %s", NEWS_URL)
    try:
        resp = get(NEWS_URL)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("News fetch failed: %s", exc)
        return []

    results = []
    articles = soup.find_all(["article", "div"], class_=re.compile(r"news|article|post", re.I))[:5]
    for article in articles:
        title_el = article.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link_el = article.find("a", href=True)
        href = link_el["href"] if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.cheffins.co.uk" + href

        snippet_el = article.find("p")
        snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""

        date_text = article.get_text()
        date_str = _parse_date_from_text(date_text)

        results.append({
            "title": title,
            "headline": snippet,
            "url": href,
            "date": date_str,
        })

    return results


def scrape() -> dict:
    upcoming = _scrape_calendar()
    news = _scrape_news()

    today = date.today()
    fetf_note = FETF_NOTE if FETF_OPEN <= today <= FETF_CLOSE else None

    return {
        "source": "Cheffins Machinery Auctions",
        "source_url": CALENDAR_URL,
        "upcoming_sales": upcoming,
        "recent_results": news,
        "fetf_note": fetf_note,
    }


if __name__ == "__main__":
    archive_current("machinery_auctions.json")
    data = scrape()
    save_data("machinery_auctions.json", data)
    print(f"Upcoming sales: {len(data['upcoming_sales'])}")
    for s in data["upcoming_sales"][:3]:
        print(f"  {s['type']}: {s['starts']} — {s['title']}")
    if data["fetf_note"]:
        print("  ** FETF window open **")
