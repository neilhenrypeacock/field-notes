"""
Scraper: AHDB grain prices (UK Corn Returns — Eastern region).
Downloads the UK Corn Returns Excel directly from Azure Blob Storage.
Sheet "Spot" contains weekly ex-farm prices by region.
Outputs: data/ahdb_grain.json
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, download_excel, load_data, load_previous, save_data

logger = logging.getLogger("field_notes.ahdb_grain")

CORN_RETURNS_URL = (
    "https://projectblue.blob.core.windows.net/media/Default/MI%20Reports/"
    "D%26A%20Arable/Daily%20and%20Weekly%20Price%20Reports/UK%20Corn%20Returns.xlsx"
)

SHEET_NAME = "Spot"

# 0-based column indices for the Spot sheet (static — known from Excel layout)
COL_MILLING_WHEAT = 6
COL_FEED_WHEAT = 9
COL_FEED_BARLEY = 17
COL_MILLING_OATS = 21

COMMODITIES = [
    ("Feed Wheat", COL_FEED_WHEAT),
    ("Milling Wheat", COL_MILLING_WHEAT),
    ("Feed Barley", COL_FEED_BARLEY),
    ("Milling Oats", COL_MILLING_OATS),
]

# OSR column is discovered dynamically — see _find_col_by_label() in scrape()

# Row labels to search for (case-insensitive, partial match)
REGION_LABEL = "eastern"
CHANGE_LABEL = "change on last week"
WEEK_ENDING_SEARCH_ROWS = 10  # scan this many rows for the week-ending string

# Possible labels for the UK/national average row (try in order)
NATIONAL_LABELS = ["national", "uk average", "gb average", "united kingdom", "uk"]


def _find_row_by_label(rows, label):
    """Find a row index (0-based in rows list) where col0 or col1 contains label."""
    for i, row in enumerate(rows):
        for col in range(min(3, len(row))):
            cell = row[col]
            if cell and label.lower() in str(cell).strip().lower():
                return i
    return None


def _find_row_by_any_label(rows, labels):
    """Find a row matching any of the given labels (tries each in order)."""
    for label in labels:
        idx = _find_row_by_label(rows, label)
        if idx is not None:
            return idx
    return None


def _find_col_by_label(rows, label, search_rows=10):
    """Find 0-based column index in the first search_rows rows matching label."""
    for row in rows[:search_rows]:
        for col_idx, cell in enumerate(row):
            if cell and label.lower() in str(cell).strip().lower():
                return col_idx
    return None


def _safe_float(val):
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


def scrape() -> dict:
    # Skip if data is fresh (< 5 days old — weekly data)
    existing = load_data("ahdb_grain.json")
    if existing.get("last_updated") and not existing.get("error"):
        from datetime import timedelta
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            existing["last_updated"].replace("Z", "+00:00")
        )
        if age < timedelta(days=5):
            logger.info("Grain data is %d hours old — skipping re-download", age.seconds // 3600)
            return existing

    logger.info("Downloading UK Corn Returns Excel: %s", CORN_RETURNS_URL)
    try:
        buf = download_excel(CORN_RETURNS_URL)
        wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
        ws = wb[SHEET_NAME]
    except Exception as exc:
        logger.error("Failed to download/parse Corn Returns Excel: %s", exc)
        return {"error": True, "message": str(exc)}

    all_rows = list(ws.iter_rows(values_only=True))

    # Scan the first several rows for the week-ending string
    import re
    week_ending = None
    for row in all_rows[:WEEK_ENDING_SEARCH_ROWS]:
        for cell in row:
            if isinstance(cell, datetime):
                week_ending = cell.strftime("%Y-%m-%d")
                break
            if cell and "week ending" in str(cell).lower():
                # e.g. "For the week ending: Thursday 12 March 2026"
                m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", str(cell))
                if m:
                    try:
                        week_ending = datetime.strptime(
                            f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                if week_ending is None:
                    m2 = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", str(cell))
                    if m2:
                        week_ending = f"{m2.group(3)}-{m2.group(2).zfill(2)}-{m2.group(1).zfill(2)}"
        if week_ending:
            break

    # Dynamically discover the OSR column (resilient to AHDB Excel layout changes)
    col_osr = _find_col_by_label(all_rows, "oilseed")
    if col_osr is None:
        col_osr = _find_col_by_label(all_rows, "osr")
    if col_osr is not None:
        logger.info("Found oilseed rape column at col %d", col_osr)
    else:
        logger.info("Oilseed rape column not found in Excel — skipping OSR")

    dynamic_commodities = list(COMMODITIES)
    if col_osr is not None:
        dynamic_commodities.append(("Oilseed Rape", col_osr))

    eastern_idx = _find_row_by_label(all_rows, REGION_LABEL)
    change_idx = _find_row_by_label(all_rows, CHANGE_LABEL)
    national_idx = _find_row_by_any_label(all_rows, NATIONAL_LABELS)

    if eastern_idx is None:
        logger.error("Could not find 'Eastern' region row in Corn Returns sheet")
        return {"error": True, "message": "Eastern region row not found in UK Corn Returns"}

    eastern_row = all_rows[eastern_idx]
    change_row = all_rows[change_idx] if change_idx is not None else None
    national_row = all_rows[national_idx] if national_idx is not None else None

    if national_row:
        logger.info("Found UK average row at index %d", national_idx)
    else:
        logger.info("No UK average row found — uk_average_price will be null")

    prices = []
    for commodity, col_idx in dynamic_commodities:
        price = _safe_float(eastern_row[col_idx]) if col_idx < len(eastern_row) else None
        if price is None:
            continue

        change = None
        if change_row and col_idx < len(change_row):
            change = _safe_float(change_row[col_idx])

        prev_price = round(price - change, 2) if change is not None else None
        change_pct = round((change / prev_price) * 100, 2) if change and prev_price else None

        uk_avg = _safe_float(national_row[col_idx]) if national_row and col_idx < len(national_row) else None

        prices.append({
            "commodity": commodity,
            "unit": "£/tonne",
            "spot_price": price,
            "prev_week_price": prev_price,
            "change": change,
            "change_pct": change_pct,
            "uk_average_price": uk_avg,
            "forward_months": [],
        })

    if not prices:
        return {"error": True, "message": "No grain prices extracted from Corn Returns Excel"}

    logger.info(
        "Extracted %d grain prices (Eastern region%s, week ending %s)",
        len(prices),
        " + UK average" if national_row else "",
        week_ending,
    )
    return {
        "source": "AHDB UK Corn Returns (Eastern region)",
        "excel_url": CORN_RETURNS_URL,
        "frequency": "weekly",
        "week_ending": week_ending,
        "prices": prices,
    }


if __name__ == "__main__":
    archive_current("ahdb_grain.json")
    data = scrape()
    save_data("ahdb_grain.json", data)
    if not data.get("error"):
        print(f"Week ending: {data.get('week_ending')}")
        for p in data.get("prices", []):
            chg = f"{p['change']:+.2f}" if p.get("change") is not None else "N/A"
            print(f"  {p['commodity']}: £{p['spot_price']:.2f}/t ({chg} wow)")
    else:
        print(f"ERROR: {data.get('message')}")
