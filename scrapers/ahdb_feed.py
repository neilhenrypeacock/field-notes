"""
Scraper: AHDB UK Feed Ingredient Prices.
Downloads the feed ingredient price export Excel from AHDB.
Date format must be M/d/yyyy h:mm:ss AM for the API to return Excel data.
Outputs: data/ahdb_feed.json
"""

import io
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, load_data, load_previous, save_data, session

logger = logging.getLogger("field_notes.ahdb_feed")

FEED_PAGE = "https://ahdb.org.uk/cereals-oilseeds/feed-ingredient-prices"
FEED_EXPORT_API = "https://ahdb.org.uk/UKFeedPricesExport/API"

# 0-based column indices in the exported Excel (confirmed empirically)
# col0=None, col1=Date, col2=Delivery month, col3..=commodities
COLUMNS_OF_INTEREST = {
    11: "Pelleted Wheat Feed (£/t)",
    12: "Rapemeal 34% (£/t)",
    13: "Soyameal Hi-Pro (£/t)",
    14: "Soyameal Brazilian 48% (£/t)",
}


def _ms_date(dt: datetime) -> str:
    """Format date as M/d/yyyy h:mm:ss AM — required by AHDB export API."""
    return dt.strftime("%-m/%-d/%Y 12:00:00 AM")


def _download_feed_excel() -> "openpyxl.Workbook | None":
    """Download feed ingredient price Excel (6-month window)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(weeks=26)
    try:
        session.get(FEED_PAGE, timeout=15)
        time.sleep(1)
        resp = session.get(
            FEED_EXPORT_API,
            params={
                "id": "61979",
                "currency": "1",
                "timescale": "Weekly",
                "startDate": _ms_date(start),
                "endDate": _ms_date(end),
            },
            headers={"Referer": FEED_PAGE},
            timeout=30,
        )
        resp.raise_for_status()
        if "application/octet-stream" not in resp.headers.get("Content-Type", ""):
            logger.warning("Unexpected content type: %s", resp.headers.get("Content-Type"))
        return openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
    except Exception as exc:
        logger.error("Failed to download feed Excel: %s", exc)
        return None


def scrape() -> dict:
    # Skip if data is fresh (< 5 days old — weekly data)
    existing = load_data("ahdb_feed.json")
    if existing.get("last_updated") and not existing.get("error"):
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            existing["last_updated"].replace("Z", "+00:00")
        )
        if age < timedelta(days=5):
            logger.info("Feed data is %d hours old — skipping re-download", age.seconds // 3600)
            return existing

    logger.info("Downloading AHDB feed ingredient prices Excel")
    wb = _download_feed_excel()
    if wb is None:
        return {"error": True, "message": "Failed to download feed ingredient Excel"}

    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))

    # Group rows by date; for each date collect column values
    # Data rows start at row 6 (index 6): col1=date, col2=delivery_month, col3+=prices
    date_data = {}  # date_str -> {col_idx: price}
    for row in all_rows[6:]:
        if not row or row[1] is None:
            continue
        date_val = row[1]
        if isinstance(date_val, datetime):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            continue
        if date_str not in date_data:
            date_data[date_str] = {}
        for col_idx in COLUMNS_OF_INTEREST:
            if col_idx < len(row) and isinstance(row[col_idx], (int, float)):
                # Take first (nearest delivery) price for this date
                if col_idx not in date_data[date_str]:
                    date_data[date_str][col_idx] = float(row[col_idx])

    if not date_data:
        return {"error": True, "message": "No feed ingredient data found in Excel"}

    sorted_dates = sorted(date_data.keys())
    latest_date = sorted_dates[-1]
    prev_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None

    latest = date_data[latest_date]
    prev = date_data[prev_date] if prev_date else {}

    prev_data = load_previous("ahdb_feed.json")
    prev_map = {p["commodity"]: p for p in prev_data.get("prices", [])}

    prices = []
    for col_idx, label in COLUMNS_OF_INTEREST.items():
        price = latest.get(col_idx)
        if price is None:
            continue
        prev_price = prev.get(col_idx)
        prev_week = prev_map.get(label, {}).get("spot_price")
        effective_prev = prev_week if prev_week is not None else prev_price
        change = round(price - effective_prev, 2) if effective_prev is not None else None
        prices.append({
            "commodity": label,
            "unit": "£/tonne",
            "spot_price": round(price, 2),
            "prev_week_price": round(effective_prev, 2) if effective_prev else None,
            "change": change,
        })

    if not prices:
        return {"error": True, "message": "No feed ingredient prices extracted"}

    logger.info("Extracted %d feed ingredient prices (week ending %s)", len(prices), latest_date)
    return {
        "source": "AHDB UK Feed Ingredient Prices",
        "week_ending": latest_date,
        "prices": prices,
    }


if __name__ == "__main__":
    archive_current("ahdb_feed.json")
    data = scrape()
    save_data("ahdb_feed.json", data)
    if not data.get("error"):
        print(f"Week ending: {data.get('week_ending')}")
        for p in data.get("prices", []):
            chg = f"{p['change']:+.2f}" if p.get("change") is not None else "N/A"
            print(f"  {p['commodity']}: £{p['spot_price']:.2f}/t ({chg} wow)")
    else:
        print(f"ERROR: {data.get('message')}")
