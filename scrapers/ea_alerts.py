"""
Scraper: Environment Agency flood and drought alerts for East Anglia.
Uses the EA Flood Monitoring API (free, no key required).
Outputs: data/ea_alerts.json
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.ea_alerts")

EA_FLOODS_URL = "https://environment.data.gov.uk/flood-monitoring/id/floods"

# Counties to include — Lincolnshire covers the Fens shared with Cambridgeshire
EA_COUNTIES = {"norfolk", "suffolk", "cambridgeshire", "lincolnshire"}


def _county_match(alert: dict) -> bool:
    """Return True if this alert is in an East Anglian county."""
    flood_area = alert.get("floodArea", {})
    county = flood_area.get("county", "")
    description = alert.get("description", "")
    area_name = flood_area.get("label", "")
    combined = f"{county} {description} {area_name}".lower()
    return any(c in combined for c in EA_COUNTIES)


def scrape() -> dict:
    logger.info("Fetching EA flood alerts: %s", EA_FLOODS_URL)
    try:
        resp = get(EA_FLOODS_URL, params={"_limit": "50"})
        data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch EA flood alerts: %s", exc)
        return {"error": True, "message": str(exc), "alerts": [], "drought_status": None}

    items = data.get("items", [])
    logger.info("EA API returned %d flood items total", len(items))

    ea_alerts = []
    for item in items:
        if not _county_match(item):
            continue
        flood_area = item.get("floodArea", {})
        ea_alerts.append({
            "severity": item.get("severityLevel", item.get("severity", "Unknown")),
            "severity_label": item.get("severityLevel", ""),
            "area": flood_area.get("label", item.get("description", "")),
            "county": flood_area.get("county", ""),
            "message": item.get("message", ""),
            "raised": item.get("timeRaised", ""),
            "url": item.get("floodAreaID", ""),
        })

    logger.info("Found %d EA alerts for East Anglia", len(ea_alerts))
    return {
        "alerts": ea_alerts,
        "total_uk_alerts": len(items),
        "drought_status": None,  # EA drought API is separate — not implemented
    }


if __name__ == "__main__":
    archive_current("ea_alerts.json")
    data = scrape()
    save_data("ea_alerts.json", data)
    if data.get("error"):
        print(f"ERROR: {data.get('message')}")
    else:
        print(f"EA alerts: {len(data['alerts'])} active in East Anglia (of {data['total_uk_alerts']} UK-wide)")
        for a in data["alerts"]:
            print(f"  [{a['severity']}] {a['area']} — {a['county']}")
