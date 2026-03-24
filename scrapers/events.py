"""
Scraper: Upcoming agricultural events relevant to East Anglia.
Sources: RNAA, Norfolk FWAG, NFU online.
Outputs: data/events.json
"""

import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.events")

SOURCES = [
    {
        "name": "RNAA",
        "url": "https://www.rnaa.org.uk/events/",
    },
    {
        "name": "Norfolk FWAG",
        "url": "https://norfolkfwag.co.uk/events/",
    },
    {
        "name": "Agri-TechE",
        "url": "https://www.agri-tech-e.co.uk/events/",
    },
]

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_event_date(text: str) -> "str | None":
    pattern = r"(\d{1,2})\s+(" + "|".join(MONTH_NAMES.keys()) + r")(?:\s+(\d{4}))?"
    match = re.search(pattern, text, re.I)
    if match:
        day = int(match.group(1))
        month = MONTH_NAMES[match.group(2).lower()]
        year = int(match.group(3)) if match.group(3) else date.today().year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass
    return None


def _fetch_event_detail(url: str) -> "tuple[str, str]":
    """Visit an event page and extract (description, location).

    Returns a tuple of (description_text, location_text), either may be empty.
    """
    if not url:
        return "", ""
    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        page_text = soup.get_text(" ", strip=True)

        # --- Location ---
        location = ""
        # CiviCRM / WordPress Events / Eventbrite class-based lookups
        for cls in ("crm-event-loc-block", "location_block", "tribe-venue", "event-location",
                    "venue", "location", "event-venue"):
            el = soup.find(class_=re.compile(cls, re.I))
            if el:
                loc_candidate = el.get_text(" ", strip=True)
                if 3 < len(loc_candidate) < 100:
                    location = loc_candidate
                    break
        # Look for structured label/value pairs
        if not location:
            for label in soup.find_all(["dt", "th", "strong", "b", "span", "div"]):
                label_text = label.get_text(strip=True).lower().strip(":").strip()
                if label_text in ("venue", "location", "where", "place"):
                    sib = label.find_next_sibling()
                    if sib:
                        loc_candidate = sib.get_text(strip=True)
                        if 3 < len(loc_candidate) < 80:
                            location = loc_candidate
                            break
                    parent = label.parent
                    if parent:
                        dd = parent.find_next("dd")
                        if dd:
                            loc_candidate = dd.get_text(strip=True)
                            if 3 < len(loc_candidate) < 80:
                                location = loc_candidate
                                break
        # Check for "Online" / "Virtual"
        if not location and re.search(r"\b(online|virtual|webinar|zoom|teams)\b", page_text, re.I):
            location = "Online"
        if location:
            location = location[:60].strip()

        # --- Description ---
        description = ""
        meta = soup.find("meta", {"name": "description"}) or soup.find("meta", {"property": "og:description"})
        if meta and meta.get("content"):
            text = meta["content"].strip()
            if len(text) > 20:
                text = text[:200]
                if len(text) == 200:
                    text = text[:text.rfind(" ")].rstrip(" .,;") + "…"
                description = text
        if not description:
            h = soup.find(["h1", "h2"])
            if h:
                for sib in h.find_all_next("p"):
                    text = sib.get_text(" ", strip=True)
                    if len(text) > 40:
                        description = text[:200]
                        break
        if not description:
            for p in soup.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 40:
                    description = text[:200]
                    break
        return description, location
    except Exception:
        pass
    return "", ""


def _scrape_source(name: str, url: str) -> list[dict]:
    logger.info("Fetching %s events: %s", name, url)
    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("Failed to fetch %s events: %s", name, exc)
        return []

    events = []
    # Common event card selectors
    cards = soup.find_all(["article", "li"], class_=re.compile(r"event|news|post", re.I))
    if not cards:
        cards = soup.find_all("article")
    if not cards:
        # Fall back to any div/section with a date pattern
        cards = [el for el in soup.find_all(["div", "section"])
                 if re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
                              el.get_text(), re.I)
                 and len(el.get_text()) > 30][:20]

    for card in cards[:20]:
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        full_text = card.get_text(" ", strip=True)
        date_str = _parse_event_date(full_text)

        # Skip events more than 28 days away or in the past
        if date_str:
            event_date = date.fromisoformat(date_str)
            today = date.today()
            if event_date < today or event_date > today + timedelta(days=56):
                continue

        link_el = card.find("a", href=True)
        href = link_el["href"] if link_el else ""
        if href and not href.startswith("http"):
            base = re.match(r"https?://[^/]+", url)
            href = (base.group(0) if base else "") + href

        # Location: look for common patterns
        location = ""
        loc_patterns = re.findall(r"(?:at|venue|location|where)[:\s]+([A-Z][^,\n]{5,40})", full_text)
        if loc_patterns:
            location = loc_patterns[0].strip()

        description, detail_location = _fetch_event_detail(href) if href else ("", "")
        if not location:
            location = detail_location
        events.append({
            "title": title,
            "organiser": name,
            "date_start": date_str,
            "date_end": date_str,
            "location": location,
            "url": href,
            "description": description,
        })

    logger.info("%s: found %d upcoming events", name, len(events))
    return events


def scrape() -> dict:
    all_events = []
    for source in SOURCES:
        all_events.extend(_scrape_source(source["name"], source["url"]))

    # Sort by date
    all_events.sort(key=lambda e: e.get("date_start") or "9999")

    # Deduplicate by title
    seen = set()
    deduped = []
    for e in all_events:
        if e["title"] not in seen:
            seen.add(e["title"])
            deduped.append(e)

    logger.info("Total events: %d", len(deduped))
    return {
        "sources": [s["name"] for s in SOURCES],
        "events": deduped[:20],
        "count": len(deduped),
        "date_range": "next 56 days",
    }


if __name__ == "__main__":
    archive_current("events.json")
    data = scrape()
    save_data("events.json", data)
    print(f"Found {data['count']} events")
    for e in data["events"][:5]:
        print(f"  {e['date_start']}: {e['title']} ({e['organiser']})")
