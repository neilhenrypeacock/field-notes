"""
Scraper: AHDB GB Fertiliser Price Series (direct Excel download).
Data is monthly — skips re-download if current data is less than 6 days old.
Outputs: data/ahdb_fertiliser.json
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, download_excel, load_data, save_data

logger = logging.getLogger("field_notes.ahdb_fertiliser")

EXCEL_URL = (
    "https://projectblue.blob.core.windows.net/media/Default/Market%20Intelligence/"
    "GBFertiliserPriceSeries.xlsx"
)

SHEET_NAME = "GB Fertiliser Price Series "
HEADER_ROW_MARKER = "Month"  # cell value that marks the header row

# Layout: col0=None, col1=date, col2=AN-UK, col3=arrow, col4=AN-import,
#         col5=arrow, col6=Urea, col7=arrow, col8=UAN, col9=arrow,
#         col10=MOP, col11=arrow, col12=DAP, col13=arrow, col14=TSP
COLUMN_MAP = {
    2: "AN – UK produced (34.5%N)",
    4: "AN – imported (34.5%N)",
    6: "Granular Urea (46%N)",
    8: "UAN (30%N)",
    10: "Muriate of Potash (MOP)",
    12: "DAP",
    14: "TSP",
}
DATE_COL = 1  # col1 holds the month datetime


def _parse_rows(ws) -> tuple:
    """Return (header_cols, data_rows) from the wide price sheet."""
    all_rows = list(ws.iter_rows(values_only=True))
    header_idx = None
    for i, row in enumerate(all_rows):
        for col in range(min(4, len(row))):
            if row[col] and str(row[col]).strip() == HEADER_ROW_MARKER:
                header_idx = i
                break
        if header_idx is not None:
            break

    if header_idx is None:
        return [], []

    data_rows = []
    for row in all_rows[header_idx + 1:]:
        if not row or len(row) < 2:
            continue
        # Find the date cell — it should be a datetime
        date_val = row[DATE_COL] if len(row) > DATE_COL else None
        if not isinstance(date_val, datetime):
            continue
        data_rows.append(row)
    return all_rows[header_idx], data_rows


def scrape() -> dict:
    # Skip if data is fresh (< 6 days old)
    existing = load_data("ahdb_fertiliser.json")
    if existing.get("last_updated") and not existing.get("error"):
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            existing["last_updated"].replace("Z", "+00:00")
        )
        if age < timedelta(days=6):
            logger.info("Fertiliser data is %d hours old — skipping re-download", age.seconds // 3600)
            return existing

    logger.info("Downloading AHDB fertiliser Excel: %s", EXCEL_URL)
    try:
        buf = download_excel(EXCEL_URL)
        wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
        ws = wb[SHEET_NAME]
    except Exception as exc:
        logger.error("Failed to download/parse fertiliser Excel: %s", exc)
        return {"error": True, "message": str(exc)}

    _header, data_rows = _parse_rows(ws)
    if len(data_rows) < 1:
        return {"error": True, "message": "Could not find data rows in fertiliser Excel"}

    latest = data_rows[-1]
    prev = data_rows[-2] if len(data_rows) >= 2 else None
    latest_date = latest[DATE_COL].strftime("%Y-%m-%d")

    prices = []
    for col_idx, product_label in COLUMN_MAP.items():
        if col_idx >= len(latest):
            continue
        try:
            price = float(latest[col_idx])
        except (ValueError, TypeError):
            continue
        prev_price = None
        if prev and col_idx < len(prev):
            try:
                prev_price = float(prev[col_idx])
            except (ValueError, TypeError):
                pass
        change = round(price - prev_price, 2) if prev_price is not None else None
        prices.append({
            "product": product_label,
            "unit": "£/tonne",
            "price": round(price, 2),
            "prev_month_price": round(prev_price, 2) if prev_price else None,
            "change": change,
            "data_date": latest_date,
        })

    data_date = latest_date

    logger.info("Extracted %d fertiliser price series", len(prices))
    return {
        "source": "AHDB GB Fertiliser Price Series",
        "excel_url": EXCEL_URL,
        "frequency": "monthly",
        "data_date": data_date,
        "prices": prices,
    }


if __name__ == "__main__":
    archive_current("ahdb_fertiliser.json")
    data = scrape()
    save_data("ahdb_fertiliser.json", data)
    if not data.get("error"):
        for p in data.get("prices", []):
            chg = f"{p['change']:+.2f}" if p["change"] is not None else "N/A"
            print(f"  {p['product']}: £{p['price']:.2f}/t ({chg} mom)")
