"""
Pre-filter pipeline stage.
Runs all new article scrapers, scores and routes output, writes to scrapers/filtered/.
Also adapts existing data/local_news.json and data/events.json into filtered format.

Run before generate.py:
    .venv/bin/python newsletter/prefilter.py
"""
import importlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.utils import load_keywords, score_article

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("field_notes.prefilter")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FILTERED_DIR = BASE_DIR / "scrapers" / "filtered"
FILTERED_DIR.mkdir(parents=True, exist_ok=True)

CAPS = {
    "markets": 15,
    "news": 20,
    "policy": 10,
    "agritech": 8,
    "weather": 1,
    "land": 10,
    "jobs": 10,
    "machinery": 10,
    "events_attend": 15,
    "events_online": 10,
    "reads": 5,
}

MAJOR_NATIONAL_SOURCES = {
    "Farmers Weekly",
    "Farmers Guardian",
    "Farming UK",
    "Agriland UK",
    "Farmers Guide",
    "Farming Monthly",
    "Crop Production Magazine",
    "Frontier Agriculture",
}

# Tier 2 national sources: specialist orgs that publish high-quality national
# farming news. Articles from these pass if they score >= 1 (same as Tier 1).
NATIONAL_SOURCES_TIER2 = {
    "AIC",
    "NFFN",
    "CHAP",
    "AA Farmer",
    "Agronomist & Arable Farmer",
    "Agri-TechE",
    "UK AgriTech",
    "Agrifunder",
}

# How many slots (of 20) to reserve for nationally important stories
NATIONAL_RESERVED_SLOTS = 5

# All new article scrapers to call. Each returns list[dict].
NEW_SCRAPERS = [
    # EA local
    "scrapers.anglia_farmer",
    "scrapers.nfu_east",
    "scrapers.itv_anglia",
    "scrapers.british_sugar",
    "scrapers.ea_bylines",
    # National trade press
    "scrapers.farmers_weekly",
    "scrapers.farmers_guardian",
    "scrapers.farmers_guide",
    "scrapers.agriland",
    "scrapers.farming_uk",
    "scrapers.farming_monthly",
    # Specialist / crop focus
    "scrapers.frontier_ag",
    "scrapers.cpm",
    "scrapers.aafarmer",
    # Policy
    "scrapers.aic",
    "scrapers.nffn",
    # Agri-tech
    "scrapers.ukagritech",
    "scrapers.chap",
    "scrapers.agrifunder",
    # Water & environment
    "scrapers.water_resources_east",
    "scrapers.camgrain",
    # Events extended
    "scrapers.events_extended",
]


def _call_scraper(module_path):
    # type: (str) -> List[dict]
    """Import and call scrape() on a scraper module. Returns [] on any failure."""
    try:
        mod = importlib.import_module(module_path)
        result = mod.scrape()
        return result if isinstance(result, list) else []
    except Exception as exc:
        logger.warning("Scraper %s failed: %s", module_path, exc)
        return []


def _load_json(filename):
    # type: (str) -> dict
    """Load a data/*.json file, return {} on failure."""
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _adapt_local_news(data):
    # type: (dict) -> List[dict]
    """Convert data/local_news.json format to list of standard article dicts."""
    articles = data.get("articles", [])
    result = []
    for a in articles:
        result.append({
            "title": a.get("title", ""),
            "summary": a.get("summary", ""),
            "url": a.get("url", ""),
            "date": a.get("published", ""),
            "published": a.get("published", ""),
            "source": a.get("source", "Local News"),
            "tier": "national",
            "category": "news",
        })
    return result


def _adapt_events(data):
    # type: (dict) -> List[dict]
    """Convert data/events.json format to list of event dicts with category field."""
    events = data.get("events", [])
    ONLINE_SIGNALS = ["online", "virtual", "webinar", "zoom", "teams", "livestream"]
    EA_TERMS = [
        "norfolk", "suffolk", "cambridgeshire", "essex", "hertfordshire",
        "bedfordshire", "norwich", "ipswich", "cambridge", "ely",
    ]
    result = []
    for ev in events:
        location = ev.get("location", "").lower()
        title_lower = ev.get("title", "").lower()
        combined = title_lower + " " + location
        if any(sig in combined for sig in ONLINE_SIGNALS):
            category = "events_online"
        elif any(ea in location for ea in EA_TERMS):
            category = "events_attend"
        else:
            # Events from events.py are RNAA/Norfolk FWAG/Agri-TechE — default attend
            category = "events_attend"
        adapted = dict(ev)
        adapted["category"] = category
        adapted["tier"] = "local" if category == "events_attend" else "national"
        adapted["source"] = ev.get("organiser", "Events")
        adapted["_score"] = 6  # Legacy events always pass — curated sources
        result.append(adapted)
    return result


def _score_and_filter(items, keywords):
    # type: (List[dict], dict) -> List[dict]
    """Score items and apply threshold logic. Returns passing items with _score set."""
    passing = []
    for item in items:
        # Events already have _score set — don't re-score
        if "_score" in item:
            passing.append(item)
            continue
        text = "{} {}".format(item.get("title", ""), item.get("summary", ""))
        score = score_article(text, keywords)
        item["_score"] = score

        if score >= 3:
            passing.append(item)
        elif score >= 1 and item.get("source") in MAJOR_NATIONAL_SOURCES:
            item["_national"] = True
            passing.append(item)
        elif score >= 1 and item.get("source") in NATIONAL_SOURCES_TIER2:
            item["_national"] = True
            passing.append(item)
        # score <= 0: discard

    return passing


def _deduplicate(items):
    # type: (List[dict]) -> List[dict]
    """Deduplicate by URL, then by title as fallback."""
    seen_urls = set()
    seen_titles = set()
    result = []
    for item in items:
        url = item.get("url", "").strip()
        title = item.get("title", "").strip().lower()
        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        result.append(item)
    return result


def run():
    # type: () -> None
    logger.info("Pre-filter starting — %s", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    keywords = load_keywords()

    # Collect from all new scrapers
    all_articles = []  # type: List[dict]
    all_events = []    # type: List[dict]

    for module_path in NEW_SCRAPERS:
        items = _call_scraper(module_path)
        if items:
            logger.info("  %s: %d items", module_path.split(".")[-1], len(items))
        # Route events separately
        events = [i for i in items if i.get("category", "").startswith("events_")]
        articles = [i for i in items if not i.get("category", "").startswith("events_")]
        all_articles.extend(articles)
        all_events.extend(events)

    # Adapt legacy scrapers
    local_news_data = _load_json("local_news.json")
    legacy_articles = _adapt_local_news(local_news_data)
    logger.info("  local_news.json: %d articles", len(legacy_articles))
    all_articles.extend(legacy_articles)

    events_data = _load_json("events.json")
    legacy_events = _adapt_events(events_data)
    logger.info("  events.json: %d events", len(legacy_events))
    all_events.extend(legacy_events)

    # Deduplicate before scoring
    all_articles = _deduplicate(all_articles)
    all_events = _deduplicate(all_events)

    # Score and filter articles
    scored_articles = _score_and_filter(all_articles, keywords)
    # Events are scored separately (already have _score from legacy adapter)
    scored_events_attend = [e for e in all_events if e.get("category") == "events_attend"]
    scored_events_online = [e for e in all_events if e.get("category") == "events_online"]

    # Route articles into category buckets
    buckets = {k: [] for k in CAPS}  # type: Dict[str, List[dict]]
    for item in scored_articles:
        cat = item.get("category", "news")
        if cat in buckets:
            buckets[cat].append(item)
        elif cat not in ("events_attend", "events_online"):
            buckets["news"].append(item)

    buckets["events_attend"] = scored_events_attend
    buckets["events_online"] = scored_events_online

    # Sort by score descending, cap, write
    # For the news bucket, reserve slots for nationally important stories
    written = {}
    for cat, items in buckets.items():
        items.sort(key=lambda x: x.get("_score", 0), reverse=True)
        cap = CAPS.get(cat, 20)

        if cat == "news" and len(items) > cap:
            # Partition: local (score >= 3) vs national (score < 3, flagged _national)
            local_items = [a for a in items if a.get("_score", 0) >= 3]
            national_items = [a for a in items if a.get("_score", 0) < 3 and a.get("_national")]
            other_items = [a for a in items if a.get("_score", 0) < 3 and not a.get("_national")]

            # Reserve slots for national, fill rest with local, then other
            national_count = min(NATIONAL_RESERVED_SLOTS, len(national_items))
            local_slots = cap - national_count
            items = local_items[:local_slots] + national_items[:national_count] + other_items
            items = items[:cap]
            logger.info("  news: %d local + %d national reserved", min(local_slots, len(local_items)), national_count)

        items = items[:cap]
        out_path = FILTERED_DIR / "{}.json".format(cat)
        with open(str(out_path), "w") as f:
            json.dump(items, f, indent=2, default=str)
        written[cat] = len(items)
        logger.info("  %s → %d items written", cat, len(items))

    logger.info("Pre-filter complete.")
    return written


if __name__ == "__main__":
    run()
