"""
scraper_reader.py — Extract postable items from scraped data files.
Reads from data/*.json and deduplicates against social/posted.json.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOCIAL_DIR = Path(__file__).resolve().parent
POSTED_FILE = SOCIAL_DIR / "posted.json"

AHDB_GRAIN_URL = "https://ahdb.org.uk/cereals-oilseeds/uk-corn-returns"
AHDB_LIVESTOCK_URL = "https://ahdb.org.uk/dairy/uk-farmgate-milk-prices"
GOVUK_SCHEMES_URL = "https://www.gov.uk/find-funding-for-land-or-farms"

logger = logging.getLogger("field_notes.social.scraper_reader")


def _load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        logger.warning("Could not read %s: %s", filename, exc)
        return {}


def _load_posted() -> Dict[str, dict]:
    if not POSTED_FILE.exists():
        return {}
    try:
        return json.loads(POSTED_FILE.read_text())
    except Exception:
        return {}


def save_posted(posted: Dict[str, dict]) -> None:
    """Write updated posted.json atomically."""
    tmp = POSTED_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(posted, indent=2, ensure_ascii=False))
    tmp.replace(POSTED_FILE)


def _already_posted(url: str, posted: Dict[str, dict]) -> bool:
    return url in posted


def _items_from_defra_blog(posted: Dict[str, dict]) -> List[dict]:
    data = _load_json("defra_blog.json")
    items = []
    for entry in data.get("entries", [])[:5]:
        url = entry.get("url", "")
        if not url or _already_posted(url, posted):
            continue
        items.append({
            "headline": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "url": url,
            "source": "Defra Farming Blog",
        })
        if len(items) >= 2:
            break
    return items


def _items_from_local_news(posted: Dict[str, dict]) -> List[dict]:
    data = _load_json("local_news.json")
    items = []
    for article in data.get("articles", [])[:6]:
        url = article.get("url", "")
        if not url or _already_posted(url, posted):
            continue
        items.append({
            "headline": article.get("title", ""),
            "summary": article.get("summary", ""),
            "url": url,
            "source": article.get("source", "Local News"),
        })
        if len(items) >= 2:
            break
    return items


def _items_from_govuk_schemes(posted: Dict[str, dict]) -> List[dict]:
    data = _load_json("govuk_schemes.json")
    items = []
    candidates = data.get("new_this_week", []) + data.get("updated_this_week", [])
    for entry in candidates[:4]:
        url = entry.get("url", "")
        if not url or _already_posted(url, posted):
            continue
        status = entry.get("status", "updated")
        summary = f"Scheme {status} on GOV.UK: {entry.get('title', '')}."
        items.append({
            "headline": entry.get("title", ""),
            "summary": summary,
            "url": url,
            "source": "GOV.UK Farming Schemes",
        })
        if len(items) >= 1:
            break
    return items


def _items_from_grain(posted: Dict[str, dict]) -> List[dict]:
    data = _load_json("ahdb_grain.json")
    prices = data.get("prices", [])
    if not prices:
        return []
    url = AHDB_GRAIN_URL
    if _already_posted(url, posted):
        return []
    lines = []
    for p in prices:
        change = p.get("change", 0.0)
        arrow = "up" if change > 0 else ("down" if change < 0 else "unchanged")
        lines.append(
            f"{p['commodity']}: £{p['spot_price']:.1f}/t ({change:+.1f}, {arrow})"
        )
    week_ending = data.get("week_ending", "")
    headline = f"East Anglia grain prices w/e {week_ending}"
    summary = "; ".join(lines) + "."
    return [{
        "headline": headline,
        "summary": summary,
        "url": url,
        "source": "AHDB UK Corn Returns",
    }]


def _items_from_norwich_livestock(posted: Dict[str, dict]) -> List[dict]:
    data = _load_json("norwich_livestock.json")
    cattle = data.get("cattle_total_head", 0)
    sheep = data.get("sheep_total_head", 0)
    if not cattle and not sheep:
        return []
    url = data.get("source_url", "https://www.norwichlivestockmarket.com/reports")
    if _already_posted(url, posted):
        return []
    sale_date = data.get("sale_date_text", "")
    headline = f"Norwich Livestock Market — {sale_date}"
    parts = []
    if cattle:
        parts.append(f"{cattle} cattle")
    if sheep:
        lambs = data.get("lambs", {})
        heavy = lambs.get("heavy", {})
        avg = heavy.get("avg_ppkg")
        avg_str = f" (heavy avg {avg:.0f}p/kg)" if avg else ""
        parts.append(f"{sheep} sheep/lambs{avg_str}")
    summary = "Through the ring: " + " and ".join(parts) + "."
    return [{
        "headline": headline,
        "summary": summary,
        "url": url,
        "source": "Norwich Livestock Market",
    }]


def get_unposted_items(max_items: int = 6) -> List[dict]:
    """
    Return up to max_items postable items not yet in posted.json.
    Priority: defra blog → local news → govuk schemes → grain prices → norwich market.
    """
    posted = _load_posted()
    items: List[dict] = []

    for fn in [
        _items_from_defra_blog,
        _items_from_local_news,
        _items_from_govuk_schemes,
        _items_from_grain,
        _items_from_norwich_livestock,
    ]:
        try:
            batch = fn(posted)
            items.extend(batch)
        except Exception as exc:
            logger.error("Error reading from %s: %s", fn.__name__, exc)
        if len(items) >= max_items:
            break

    logger.info("Found %d unposted items", len(items))
    return items[:max_items]
