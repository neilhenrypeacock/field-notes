"""
Scraper: Agricultural land listings from East Anglian agents.
Sources: Brown & Co, Savills, Strutt & Parker.
Avoids Rightmove (ToS restricts scraping).
Outputs: data/land_listings.json
"""

import logging
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, load_previous, save_data

logger = logging.getLogger("field_notes.land_listings")

SOURCES = [
    {
        "agent": "Brown & Co",
        "url": "https://www.brown-co.com/services/rural/property-search",
        "base_url": "https://www.brown-co.com",
        # Card: <div class="card card--property card--property-listing">
        # Price: <div class="cp-price h3">, Desc: <div class="cp-desc">, Loc: <div class="cp-loc">
        # Link: <a class="cp-link" href="...">
        "card_class": "card--property-listing",
        "price_class": "cp-price",
        "desc_class": "cp-desc",
        "loc_class": "cp-loc",
        "link_class": "cp-link",
    },
]

# Counties used to filter nationally-listed Savills/Strutt & Parker results to East Anglia only
EA_COUNTIES = {"norfolk", "suffolk", "cambridgeshire", "cambridge", "cambs"}


def _is_east_anglia(text: str) -> bool:
    """Return True if the text mentions an East Anglian county."""
    lower = text.lower()
    return any(county in lower for county in EA_COUNTIES)


def _extract_acreage(text: str) -> "float | None":
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:acres?|ac\b)", text, re.I)
    if match:
        return float(match.group(1))
    return None


def _extract_price(text: str) -> "str | None":
    match = re.search(r"£[\d,]+(?:\.\d{2})?(?:\s*(?:million|m|k))?", text, re.I)
    if match:
        return match.group(0).strip()
    return None


def _price_per_acre(price_str, acreage) -> "int | None":
    if not price_str or not acreage or acreage == 0:
        return None
    num_str = re.sub(r"[£,\s]", "", price_str)
    multiplier = 1
    if "million" in price_str.lower() or num_str.lower().endswith("m"):
        multiplier = 1_000_000
        num_str = num_str.rstrip("mM")
    elif num_str.lower().endswith("k"):
        multiplier = 1_000
        num_str = num_str.rstrip("kK")
    try:
        return int(float(num_str) * multiplier / acreage)
    except ValueError:
        return None


def _scrape_agent(source: dict, prev_urls: set) -> list[dict]:
    agent = source["agent"]
    url = source["url"]
    base_url = source.get("base_url", "")
    logger.info("Scraping %s: %s", agent, url)

    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", agent, exc)
        return []

    listings = []
    cards = soup.find_all("div", class_=source["card_class"])
    if not cards:
        logger.warning("%s: no listing cards found (class=%s)", agent, source["card_class"])

    for card in cards[:20]:
        link_el = card.find("a", class_=source.get("link_class"))
        if not link_el:
            link_el = card.find("a", href=True)
        href = (link_el["href"] if link_el else "").strip()
        if href and not href.startswith("http"):
            href = base_url + href

        price_el = card.find(class_=source.get("price_class"))
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_str = _extract_price(price_text) or (price_text if price_text else None)

        desc_el = card.find(class_=source.get("desc_class"))
        desc = desc_el.get_text(strip=True) if desc_el else ""

        loc_el = card.find(class_=source.get("loc_class"))
        location = loc_el.get_text(strip=True) if loc_el else ""
        # Strip map pin icon text
        location = re.sub(r"^\s*\S*map\S*\s*", "", location, flags=re.I).strip()

        full_text = card.get_text(" ", strip=True)
        acreage = _extract_acreage(full_text)
        title = f"{desc} — {location}" if desc and location else (desc or location or "Land/property")

        is_new = bool(href) and href not in prev_urls

        listings.append({
            "agent": agent,
            "title": title,
            "location": location,
            "acreage": acreage,
            "guide_price": price_str,
            "guide_price_per_acre": _price_per_acre(price_str, acreage),
            "url": href,
            "is_new": is_new,
        })

    logger.info("%s: found %d listings", agent, len(listings))
    return listings


def _scrape_savills(prev_urls: set) -> list:
    """Scrape Savills farms for sale — all UK, filter to East Anglia in Python."""
    # Savills server-renders this page fully (no JS required)
    url = "https://search.savills.com/list/farms/farms-for-sale/uk"
    agent = "Savills"
    base_url = "https://search.savills.com"
    logger.info("Scraping %s: %s", agent, url)
    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", agent, exc)
        return []

    # Cards: <article class="sv-property-card ...">
    cards = soup.find_all("article", class_="sv-property-card")
    if not cards:
        logger.warning("%s: no sv-property-card articles found — page structure may have changed", agent)
        return []

    listings = []
    for card in cards:
        full_text = card.get_text(" ", strip=True)
        # Filter to East Anglia only (Savills lists nationally)
        if not _is_east_anglia(full_text):
            continue

        # Link: <a class="sv-details__link" href="/property-detail/...">
        link_el = card.find("a", class_="sv-details__link")
        href = (link_el["href"] if link_el else "").strip()
        if href and not href.startswith("http"):
            href = base_url + href

        # Address: sv-details__address1 (property name) + sv-details__address2 (county/postcode)
        addr1_el = card.find(class_="sv-details__address1")
        addr2_el = card.find(class_="sv-details__address2")
        title = addr1_el.get_text(strip=True) if addr1_el else ""
        location = addr2_el.get_text(strip=True) if addr2_el else ""
        if not title:
            title = full_text[:80]

        acreage = _extract_acreage(full_text)
        # Price appears as "Guide price £XXX,XXX" in text — no dedicated class
        price_str = _extract_price(full_text)

        is_new = bool(href) and href not in prev_urls
        listings.append({
            "agent": agent,
            "title": title,
            "location": location,
            "acreage": acreage,
            "guide_price": price_str,
            "guide_price_per_acre": _price_per_acre(price_str, acreage),
            "url": href,
            "is_new": is_new,
        })

    logger.info("%s: found %d East Anglian listings (of %d total)", agent, len(listings), len(cards))
    return listings


def _scrape_strutt_parker(prev_urls: set) -> list:
    """Scrape Strutt & Parker farms, estates & land — filtered to East Anglia.

    Note: struttandparker.com/properties/... is a JavaScript SPA. The page skeleton
    loads (200 OK) but property cards are injected by React. Plain HTTP scraping
    returns an empty shell. Until headless-browser support is added, this returns [].
    """
    url = "https://www.struttandparker.com/properties/estate-farms-and-land"
    agent = "Strutt & Parker"
    base_url = "https://www.struttandparker.com"
    logger.info("Scraping %s: %s", agent, url)
    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", agent, exc)
        return []

    # Try common property card selectors — will be empty on JS-rendered pages
    cards = (
        soup.find_all("article", class_=re.compile(r"property|listing|estate", re.I))
        or soup.find_all("div", class_=re.compile(r"property-card|listing-card|estate-card", re.I))
        or soup.find_all("li", class_=re.compile(r"property|listing", re.I))
    )

    if not cards:
        logger.info(
            "%s: no listing cards found (site is JS-rendered — content requires headless browser). "
            "Returning empty. Use Brown & Co and Savills for land coverage.",
            agent,
        )
        return []

    listings = []
    for card in cards[:20]:
        full_text = card.get_text(" ", strip=True)
        if not _is_east_anglia(full_text):
            continue

        link_el = card.find("a", href=True)
        href = (link_el["href"] if link_el else "").strip()
        if href and not href.startswith("http"):
            href = base_url + href

        heading = (
            card.find(["h2", "h3", "h4"])
            or card.find(class_=re.compile(r"title|heading|address", re.I))
        )
        title = heading.get_text(strip=True) if heading else full_text[:80]

        loc_el = card.find(class_=re.compile(r"address|location|county", re.I))
        location = loc_el.get_text(strip=True) if loc_el else ""

        acreage = _extract_acreage(full_text)
        price_str = _extract_price(full_text)
        is_new = bool(href) and href not in prev_urls
        listings.append({
            "agent": agent,
            "title": title,
            "location": location,
            "acreage": acreage,
            "guide_price": price_str,
            "guide_price_per_acre": _price_per_acre(price_str, acreage),
            "url": href,
            "is_new": is_new,
        })

    logger.info("%s: found %d East Anglian listings", agent, len(listings))
    return listings


def scrape() -> dict:
    previous = load_previous("land_listings.json")
    prev_urls = {l["url"] for l in previous.get("listings", [])}

    all_listings = []
    for source in SOURCES:
        all_listings.extend(_scrape_agent(source, prev_urls))
    all_listings.extend(_scrape_savills(prev_urls))
    all_listings.extend(_scrape_strutt_parker(prev_urls))

    # Cap total at 20 listings (prioritise new listings)
    all_listings.sort(key=lambda x: (not x["is_new"],))
    all_listings = all_listings[:20]

    new_count = sum(1 for l in all_listings if l["is_new"])
    active_sources = list(dict.fromkeys(l["agent"] for l in all_listings)) or ["Brown & Co", "Savills", "Strutt & Parker"]
    logger.info("Total listings: %d, new this week: %d", len(all_listings), new_count)

    return {
        "sources": ["Brown & Co", "Savills", "Strutt & Parker"],
        "active_sources": active_sources,
        "listings": all_listings,
        "total_count": len(all_listings),
        "new_this_week": new_count,
    }


if __name__ == "__main__":
    archive_current("land_listings.json")
    data = scrape()
    save_data("land_listings.json", data)
    print(f"Total: {data['total_count']}, new: {data['new_this_week']}")
    for l in data["listings"][:5]:
        print(f"  {'[NEW] ' if l['is_new'] else ''}{l['agent']}: {l['title']} — {l['guide_price']}")
