"""
Scraper: Extended events sources for East Anglia and online farming events.
Sources: East of England Agricultural Society, AHDB events, Frontier Agriculture events
Returns: list of event dicts with category = events_attend or events_online

Complements events.py (RNAA, Norfolk FWAG, Agri-TechE) — do not modify events.py.
"""
import re
import sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

EA_COUNTIES = [
    "norfolk", "suffolk", "cambridgeshire", "essex", "hertfordshire", "bedfordshire",
    "norwich", "ipswich", "cambridge", "peterborough", "ely", "kings lynn",
    "bury st edmunds", "newmarket", "thetford", "fakenham",
]

ONLINE_SIGNALS = ["online", "virtual", "webinar", "zoom", "teams", "livestream"]

SOURCES = [
    {
        "name": "East of England Agricultural Society",
        "url": "https://eastofengland.org.uk/all-events/",
        "type": "attend",
        "base": "https://eastofengland.org.uk",
    },
    {
        "name": "AHDB",
        "url": "https://ahdb.org.uk/events",
        "type": "both",
        "base": "https://ahdb.org.uk",
    },
    {
        "name": "Frontier Agriculture",
        "url": "https://www.frontierag.co.uk/news-events-and-expertise/events/",
        "type": "attend",
        "base": "https://www.frontierag.co.uk",
    },
]


def _is_ea_location(text):
    # type: (str) -> bool
    text_lower = text.lower()
    return any(county in text_lower for county in EA_COUNTIES)


def _is_online(text):
    # type: (str) -> bool
    text_lower = text.lower()
    return any(sig in text_lower for sig in ONLINE_SIGNALS)


def _classify_event(title, location, source_type):
    # type: (str, str, str) -> Optional[str]
    """Return 'events_attend', 'events_online', or None (discard)."""
    combined = (title + " " + location).lower()
    if _is_online(combined):
        return "events_online"
    if source_type == "both":
        if _is_ea_location(combined):
            return "events_attend"
        return "events_online"
    if source_type == "attend":
        if _is_ea_location(combined):
            return "events_attend"
        return None  # Discard non-EA attend events
    return None


def _scrape_source(source):
    # type: (dict) -> List[dict]
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        events = []

        # Look for event cards/list items
        cards = (
            soup.select(".event-item")
            or soup.select(".event")
            or soup.select("article")
            or soup.select("li.lister__item")
            or soup.select(".card")
        )

        for card in cards[:30]:
            try:
                heading = card.find(["h2", "h3", "h4"])
                if not heading:
                    continue
                link_tag = heading.find("a") or card.find("a")
                title = heading.get_text(strip=True)
                if not title:
                    continue

                url = ""
                if link_tag and link_tag.get("href"):
                    url = link_tag["href"]
                    if url.startswith("/"):
                        url = source["base"] + url

                # Location: look for location-related text
                location = ""
                for selector in [".location", ".venue", "[data-location]"]:
                    loc_el = card.select_one(selector)
                    if loc_el:
                        location = loc_el.get_text(strip=True)
                        break
                if not location:
                    # Try to extract from paragraph text
                    para = card.find("p")
                    if para:
                        location = para.get_text(strip=True)[:200]

                # Date extraction
                date_str = ""
                for time_el in card.find_all(["time", "span"], class_=re.compile(r"date|time", re.I)):
                    dt = time_el.get("datetime") or time_el.get_text(strip=True)
                    if dt:
                        date_str = dt[:30]
                        break

                category = _classify_event(title, location, source["type"])
                if not category:
                    continue

                events.append({
                    "title": title,
                    "organiser": source["name"],
                    "date_start": date_str,
                    "date_end": date_str,
                    "location": location,
                    "url": url,
                    "description": location[:200] if location else "",
                    "category": category,
                    "tier": "local" if category == "events_attend" else "national",
                    "source": source["name"],
                })
            except Exception:
                continue
        return events
    except Exception:
        return []


def scrape():
    # type: () -> List[dict]
    all_events = []
    for source in SOURCES:
        try:
            events = _scrape_source(source)
            all_events.extend(events)
        except Exception:
            continue
    return all_events


if __name__ == "__main__":
    items = scrape()
    print("Events extended: {} events".format(len(items)))
    for item in items[:5]:
        print("  [{}] {}".format(item["category"], item["title"]))
