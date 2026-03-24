"""
Scraper: Norwich Livestock Market weekly sale report.
Source: https://www.norwichlivestockmarket.com/reports
Outputs: data/norwich_livestock.json
"""

import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.norwich_livestock")

BASE_URL = "https://www.norwichlivestockmarket.com"
REPORTS_URL = f"{BASE_URL}/reports"


def _get_latest_report_url() -> Optional[str]:
    resp = get(REPORTS_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/component/content/article/" in href and "report" in href.lower():
            return BASE_URL + href if not href.startswith("http") else href
    return None


def _parse_number(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text, re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except (ValueError, IndexError):
            pass
    return None


def _parse_report(url: str) -> dict:
    resp = get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text(" ", strip=True)

    result = {"url": url, "raw_summary": text[:500]}

    # Sale date — find the h3 containing a day/month pattern
    for el in soup.find_all("h3"):
        t = el.get_text(strip=True)
        if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|\d{1,2}/\d{1,2})\b", t, re.I):
            result["sale_date_text"] = t
            break

    # Total cattle head: "168 Store and Breeding Cattle"
    m = re.search(r"(\d+)\s+Store(?:\s+and\s+Breeding)?\s+Cattle", text, re.I)
    if m:
        result["cattle_total_head"] = int(m.group(1))

    # Store cattle average: "average overall was a whopping £1,640" or "average was £1640"
    m = re.search(r"average[^£]*£\s*([\d,]+)", text, re.I)
    if m:
        try:
            result["store_cattle_avg_gbp"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    # Sheep total: "SHEEP (950)"
    m = re.search(r"SHEEP\s*\((\d+)\)", text, re.I)
    if m:
        result["sheep_total_head"] = int(m.group(1))

    # Lamb sections — extract averages for each weight class
    # Patterns vary: "STANDARD LAMBS (92)", "LAMBS (70)", "MEDIUM LAMBS (201)"
    # Line format: "CATEGORY (N) ppkg_lo TO ppkg_hi AV ppkg_av [£lo TO £hi AV £av]"
    lamb_sections = {}
    # Ordered by specificity to avoid "HEAVY" matching "HEAVY +"
    for category, key in [
        ("PRIME HOGGS", "prime_hoggs"),
        ("HEAVY \\+ LAMBS", "heavy_plus"),
        ("HEAVY LAMBS", "heavy"),
        ("MEDIUM LAMBS", "medium"),
        ("STANDARD LAMBS", "standard"),
        ("(?<!MEDIUM )(?<!HEAVY )(?<!STANDARD )LAMBS", "standard"),  # bare "LAMBS"
    ]:
        # Single pattern capturing head, ppkg_av, and optional £_av in one shot
        pat = (
            rf"(?<![A-Z]){category}\s*\((\d+)\)"      # category (head)
            rf"\s+[\d.]+\s+TO\s+[\d.]+\s+AV\s+([\d.]+)"  # ppkg range + av
            rf"(?:\s+£[\d.]+\s+TO\s+£[\d.]+\s+AV\s+£?([\d.]+))?"  # optional £ range + av
        )
        m = re.search(pat, text, re.I)
        if m and key not in lamb_sections:
            entry = {"head": int(m.group(1)), "avg_ppkg": float(m.group(2))}
            if m.group(3):
                entry["avg_gbp"] = float(m.group(3))
            lamb_sections[key] = entry

    if lamb_sections:
        result["lambs"] = lamb_sections

    # Cull ewes average
    m = re.search(r"CULL\s+EWES[^A-Z]*av\s+£([\d.]+)", text, re.I)
    if m:
        result["cull_ewe_avg_gbp"] = float(m.group(1))

    # Store hoggs average
    m = re.search(r"STORE\s+HOGGS[^A-Z]*av\s+£([\d.]+)", text, re.I)
    if m:
        result["store_hogg_avg_gbp"] = float(m.group(1))

    return result


def scrape() -> dict:
    logger.info("Fetching latest Norwich Livestock Market report")
    url = _get_latest_report_url()
    if not url:
        logger.warning("No report URL found on Norwich Livestock Market site")
        return {"error": True, "message": "No report URL found"}

    logger.info("Fetching report: %s", url)
    report = _parse_report(url)
    report["source"] = "Norwich Livestock Market"
    report["source_url"] = REPORTS_URL
    logger.info(
        "Parsed: cattle=%s head avg=£%s, sheep=%s head",
        report.get("cattle_total_head"),
        report.get("store_cattle_avg_gbp"),
        report.get("sheep_total_head"),
    )
    return report


if __name__ == "__main__":
    archive_current("norwich_livestock.json")
    data = scrape()
    save_data("norwich_livestock.json", data)
    import json
    print(json.dumps(data, indent=2))
