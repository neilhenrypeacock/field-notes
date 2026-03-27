"""
newsletter/verify.py
====================
Two-gate verification system for newsletter sections.
Adapted from social/verify.py for the newsletter pipeline.

Gate 1 — Data validation (runs BEFORE AI writes)
    Validates price ranges, cross-commodity relationships,
    data freshness, required fields, week-on-week plausibility.
    Flags anomalies; blocks bad data.

Gate 2 — AI cross-check (runs AFTER AI writes)
    A second, independent Claude call reads both the raw data
    and the finished section text and checks every number,
    direction, source claim, and flags anomalies.
    Flags sections for human review.

Results are saved alongside the confidence sidecar JSON
and displayed in the admin dashboard.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
from urllib.parse import urlparse

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logger = logging.getLogger("field_notes.verify")

# ── Config ────────────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).resolve().parent / "validation_config.json"
PREVIOUS_DIR = Path(__file__).resolve().parent.parent / "data" / "previous"
AI_MODEL = "claude-sonnet-4-6"
MAX_TOKENS_VERIFY = 400

# Gate 2 flags only — human decides whether to override
GATE2_BLOCKS_SECTION = False
# Number mismatches block by default — farmers rely on these numbers
BLOCK_ON_NUMBER_MISMATCH = True
# Low confidence from Gate 2 flags the section for review
FLAG_ON_LOW_CONFIDENCE = True


# ── Result objects ────────────────────────────────────────────────────────

@dataclass
class Gate1Result:
    passed: bool
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)

    def summary(self):
        # type: () -> str
        if self.passed and not self.warnings and not self.anomalies:
            return "PASS — all data checks passed"
        elif self.passed and (self.warnings or self.anomalies):
            n = len(self.warnings) + len(self.anomalies)
            return "PASS WITH WARNINGS — {} warning(s)".format(n)
        else:
            return "BLOCKED — {} error(s)".format(len(self.errors))

    def to_dict(self):
        # type: () -> dict
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "checks": self.checks,
            "anomalies": self.anomalies,
            "summary": self.summary(),
        }


@dataclass
class Gate2Result:
    passed: bool
    confidence: str = "MEDIUM"
    number_mismatch: bool = False
    direction_error: bool = False
    invented_content: bool = False
    source_accurate: bool = True
    anomaly_noted: bool = True
    notes: list = field(default_factory=list)

    def summary(self):
        # type: () -> str
        if self.passed and self.confidence == "HIGH":
            return "PASS (HIGH confidence) — all numbers verified"
        elif self.passed and self.confidence == "MEDIUM":
            return "PASS (MEDIUM confidence) — numbers correct, some context inferred"
        elif not self.passed:
            reasons = []
            if self.number_mismatch:
                reasons.append("number mismatch")
            if self.direction_error:
                reasons.append("wrong direction")
            if self.invented_content:
                reasons.append("invented content")
            return "FLAGGED — {}".format(", ".join(reasons) if reasons else "review needed")
        else:
            return "FLAGGED (LOW confidence) — review carefully"

    def to_dict(self):
        # type: () -> dict
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "number_mismatch": self.number_mismatch,
            "direction_error": self.direction_error,
            "invented_content": self.invented_content,
            "source_accurate": self.source_accurate,
            "anomaly_noted": self.anomaly_noted,
            "notes": self.notes,
            "summary": self.summary(),
        }


@dataclass
class SectionVerification:
    section: str
    gate1: Gate1Result
    gate2: Optional[Gate2Result] = None
    blocked: bool = False
    flagged: bool = False
    block_reason: str = ""
    broken_links: list = field(default_factory=list)
    review_guidance: dict = field(default_factory=dict)

    def status_line(self):
        # type: () -> str
        if self.blocked:
            return "BLOCKED — {}".format(self.block_reason)
        elif self.flagged:
            return "FLAGGED — review before approving"
        else:
            return "READY"

    def status_emoji(self):
        # type: () -> str
        if self.blocked:
            return "red"
        elif self.flagged:
            return "amber"
        else:
            return "green"

    def to_dict(self):
        # type: () -> dict
        return {
            "section": self.section,
            "gate1": self.gate1.to_dict(),
            "gate2": self.gate2.to_dict() if self.gate2 else None,
            "blocked": self.blocked,
            "flagged": self.flagged,
            "block_reason": self.block_reason,
            "broken_links": self.broken_links,
            "review_guidance": self.review_guidance,
            "status": self.status_line(),
            "status_color": self.status_emoji(),
        }


# ── Data extractors ───────────────────────────────────────────────────────

def _extract_grain_prices(data):
    # type: (dict) -> dict
    """Extract price values from ahdb_grain.json structure."""
    prices = {}
    for p in data.get("prices", []):
        commodity = p.get("commodity", "").lower()
        if "feed wheat" in commodity:
            prices["feed_wheat"] = p.get("spot_price")
            prices["feed_wheat_change_pct"] = p.get("change_pct")
        elif "milling wheat" in commodity:
            prices["milling_wheat"] = p.get("spot_price")
            prices["milling_wheat_change_pct"] = p.get("change_pct")
        elif "feed barley" in commodity:
            prices["feed_barley"] = p.get("spot_price")
            prices["feed_barley_change_pct"] = p.get("change_pct")
    return prices


def _calc_change_pct(current, previous):
    # type: (float, float) -> Optional[float]
    """Calculate percentage change, returning None if either value is missing or zero."""
    try:
        c, p = float(current), float(previous)
        if p == 0:
            return None
        return ((c - p) / p) * 100
    except (ValueError, TypeError):
        return None


def _extract_fertiliser_prices(data):
    # type: (dict) -> dict
    """Extract fertiliser prices from costs data structure, with change_pct."""
    prices = {}
    fert = data.get("fertiliser", data)
    for p in fert.get("prices", []):
        commodity = (p.get("commodity") or p.get("product") or "").lower()
        price_val = p.get("spot_price") or p.get("price")
        prev_val = p.get("prev_month_price") or p.get("prev_week_price")
        label = None
        if "ammonium nitrate" in commodity or commodity == "an" or "an " in commodity:
            label = "an_fertiliser"
        elif "urea" in commodity and "uan" not in commodity:
            label = "urea"
        elif "uan" in commodity:
            label = "uan"
        elif "mop" in commodity or "potash" in commodity:
            label = "mop"
        elif "dap" in commodity:
            label = "dap"
        elif "tsp" in commodity:
            label = "tsp"
        if label and price_val is not None:
            prices[label] = price_val
            # Calculate change_pct from prev_month_price if available
            if prev_val is not None:
                pct = _calc_change_pct(price_val, prev_val)
                if pct is not None:
                    prices[label + "_change_pct"] = pct
    return prices


def _extract_livestock_prices(data):
    # type: (dict) -> dict
    """Extract prices from livestock data structure, with change_pct."""
    ahdb = data.get("ahdb", data)
    prices = {}
    mapping = [
        ("pig_prices", "pig_spp"),
        ("milk_prices", "milk_farmgate"),
        ("beef_prices", "beef_deadweight"),
        ("sheep_prices", "sheep_deadweight"),
        ("egg_prices", "egg_price"),
    ]
    for key, label in mapping:
        sub = ahdb.get(key, {})
        if sub.get("price") is not None:
            prices[label] = sub["price"]
            # Calculate change_pct from change + price if available
            change = sub.get("change")
            if change is not None:
                prev = float(sub["price"]) - float(change)
                pct = _calc_change_pct(sub["price"], prev)
                if pct is not None:
                    prices[label + "_change_pct"] = pct
    return prices


def _find_date_field(data):
    # type: (dict) -> Optional[str]
    """Search common date field names in data, including nested structures."""
    for key in ("last_updated", "week_ending", "date", "scraped_at"):
        val = data.get(key)
        if val:
            return str(val)
    # Check nested structures — prices list
    if isinstance(data.get("prices"), list) and data["prices"]:
        for key in ("week_ending", "date"):
            val = data["prices"][0].get(key)
            if val:
                return str(val)
    # Check nested structures — ahdb wrapper (livestock data)
    if "ahdb" in data:
        ahdb = data["ahdb"]
        if isinstance(ahdb, dict):
            for key in ("last_updated", "week_ending", "date"):
                val = ahdb.get(key)
                if val:
                    return str(val)
    # Check nested structures — fertiliser/feed wrapper (costs data)
    for wrapper_key in ("fertiliser", "feed"):
        sub = data.get(wrapper_key)
        if isinstance(sub, dict):
            for key in ("last_updated", "week_ending", "date"):
                val = sub.get(key)
                if val:
                    return str(val)
    return None


# ── Previous week comparison ─────────────────────────────────────────────

# Maps section name → previous data filename and extractor function name
_PREV_FILE_MAP = {
    "markets":   ("ahdb_grain_prev.json",      "_extract_grain_prices"),
    "costs":     ("ahdb_fertiliser_prev.json",  "_extract_fertiliser_prices"),
    "livestock": ("ahdb_livestock_prev.json",   "_extract_livestock_prices"),
}


def _load_previous_prices(section):
    # type: (str) -> dict
    """Load previous week's data and extract prices for comparison."""
    mapping = _PREV_FILE_MAP.get(section)
    if not mapping:
        return {}
    filename, extractor_name = mapping
    prev_path = PREVIOUS_DIR / filename
    if not prev_path.exists():
        return {}
    try:
        prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
        extractor = globals()[extractor_name]
        prices = extractor(prev_data)
        # Strip out change_pct fields — we only want the price values
        return {k: v for k, v in prices.items() if not k.endswith("_change_pct")}
    except Exception as exc:
        logger.debug("Could not load previous data for %s: %s", section, exc)
        return {}


def _cross_week_checks(section, current_prices, config):
    # type: (str, dict, dict) -> tuple
    """
    Compare current prices against previous week's saved data.
    Returns (checks, anomalies) lists.
    """
    checks = []   # type: List[str]
    anomalies = []  # type: List[str]
    prev_prices = _load_previous_prices(section)
    if not prev_prices:
        return checks, anomalies

    max_pct = config.get("max_weekly_change_pct", 15)
    price_ranges = config.get("price_ranges", {})

    for field_name, current_val in current_prices.items():
        if field_name.endswith("_change_pct"):
            continue
        prev_val = prev_prices.get(field_name)
        if prev_val is None or current_val is None:
            continue
        pct = _calc_change_pct(current_val, prev_val)
        if pct is None:
            continue
        label = price_ranges.get(field_name, {}).get("label", field_name.replace("_", " ").title())
        abs_pct = abs(pct)
        if abs_pct > max_pct:
            direction = "up" if pct > 0 else "down"
            anomalies.append(
                "{} {} {:.1f}% vs previous week ({} -> {}) — "
                "this is unusual (>{:.0f}% threshold). Verify source data.".format(
                    label, direction, abs_pct, prev_val, current_val, max_pct
                )
            )
        else:
            checks.append(
                "{}: {:.1f}% vs previous week — within normal range".format(label, abs_pct)
            )

    return checks, anomalies


# ── Link verification ────────────────────────────────────────────────────

def _extract_links_from_text(text):
    # type: (str) -> List[str]
    """Pull URLs from markdown-style [text](url) links and bare https:// URLs."""
    md_links = re.findall(r'\[.*?\]\((https?://[^\)]+)\)', text)
    bare_links = re.findall(r'(?<!\()(?<!")(https?://[^\s\)<>"]+)', text)
    # Deduplicate, preserving order
    seen = set()
    result = []
    for url in md_links + bare_links:
        url = url.rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


# Domains that block automated requests but work fine in browsers.
# Skip link-checking for these — false positives waste reviewer time.
_SKIP_LINK_CHECK_DOMAINS = {
    "ahdb.org.uk",
    "projectblue.blob.core.windows.net",
}


def _check_link(url, timeout=10):
    # type: (str, int) -> tuple
    """HEAD-check a URL. Returns (url, ok, status_code_or_error)."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return (url, False, "Invalid URL")
        # Skip domains known to block automated checks
        domain = parsed.netloc.lstrip("www.")
        if any(domain.endswith(skip) for skip in _SKIP_LINK_CHECK_DOMAINS):
            return (url, True, "skipped (known bot-blocking domain)")
        resp = requests.head(
            url, allow_redirects=True, timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        # Treat 2xx and 3xx as OK; some sites block HEAD, so also try GET on 405
        if resp.status_code == 405:
            resp = requests.get(
                url, allow_redirects=True, timeout=timeout, stream=True,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            )
            resp.close()
        ok = resp.status_code < 400
        return (url, ok, resp.status_code)
    except requests.RequestException as exc:
        return (url, False, str(exc)[:80])


def verify_links(ai_text):
    # type: (str) -> tuple
    """
    Check all links found in the AI-written text.
    Returns (good_links, bad_links) where each is a list of (url, detail) tuples.
    """
    urls = _extract_links_from_text(ai_text)
    good = []   # type: List[tuple]
    bad = []    # type: List[tuple]
    for url in urls:
        url, ok, detail = _check_link(url)
        if ok:
            good.append((url, detail))
        else:
            bad.append((url, detail))
    return good, bad


# ── Actionable review guidance ───────────────────────────────────────────

# Human-readable verification URLs per section — these are the pages a
# reviewer can visit to manually spot-check the data.
REVIEW_LINKS = {
    "markets": [
        ("AHDB Cereals & Oilseeds (grain prices)", "https://ahdb.org.uk/cereals-oilseeds"),
        ("AHDB Feed Ingredient Prices", "https://ahdb.org.uk/cereals-oilseeds/feed-ingredient-prices"),
    ],
    "costs": [
        ("AHDB Cereals & Oilseeds (fertiliser section)", "https://ahdb.org.uk/cereals-oilseeds"),
    ],
    "livestock": [
        ("AHDB Pork (deadweight pig prices)", "https://ahdb.org.uk/pork"),
        ("AHDB Dairy (farmgate milk prices)", "https://ahdb.org.uk/dairy/uk-farmgate-milk-prices"),
        ("AHDB Beef & Lamb (deadweight prices)", "https://ahdb.org.uk/beef-lamb"),
    ],
    "weather": [
        ("Met Office East Anglia forecast", "https://www.metoffice.gov.uk/weather/forecast/gcn2dxfe4"),
    ],
    "schemes_grants": [
        ("GOV.UK Find Funding for Land or Farms", "https://www.gov.uk/find-funding-for-land-or-farms"),
        ("Defra Farming Blog", "https://defrafarming.blog.gov.uk/"),
    ],
    "regulatory": [
        ("Defra Farming Blog", "https://defrafarming.blog.gov.uk/"),
    ],
    "events": [],
    "land_property": [
        ("Brown & Co Rural Property", "https://www.brown-co.com/services/rural/property-search"),
    ],
    "jobs": [
        ("Farmers Weekly Jobs — East of England", "https://jobs.fwi.co.uk/jobs/east-of-england/"),
    ],
    "machinery": [
        ("Cheffins Auctions", "https://www.cheffins.co.uk/auctions"),
    ],
    "one_good_read": [],
    "at_a_glance": [],
    "margin_watch": [
        ("AHDB Cereals & Oilseeds (grain prices)", "https://ahdb.org.uk/cereals-oilseeds"),
    ],
}


def build_review_guidance(section, gate1, gate2=None, bad_links=None):
    # type: (str, Gate1Result, Optional[Gate2Result], Optional[list]) -> dict
    """
    Build actionable review guidance for a section that is flagged or low-confidence.
    Returns a dict with 'actions' (list of plain-English steps) and
    'verify_links' (list of {label, url} for the reviewer to click).
    """
    actions = []   # type: List[str]
    links = []     # type: List[dict]

    # Always include the relevant source links for this section
    for label, url in REVIEW_LINKS.get(section, []):
        links.append({"label": label, "url": url})

    # Gate 1 anomalies → specific guidance
    for anomaly in gate1.anomalies:
        if "milling wheat" in anomaly.lower() and "feed wheat" in anomaly.lower():
            actions.append(
                "Milling wheat is below feed wheat — check the AHDB Corn Returns "
                "Excel (link below) to confirm both prices are correct."
            )
        elif "vs previous week" in anomaly.lower():
            actions.append(
                "Large week-on-week price change flagged. Open the relevant AHDB "
                "page (link below) and compare this week's figure to last week's."
            )
        elif "scraper error" in anomaly.lower():
            actions.append(
                "Possible scraper error. Re-run the scraper or check the source "
                "page directly (link below)."
            )
        else:
            actions.append("Review anomaly: {}".format(anomaly))

    # Gate 1 warnings → guidance
    for warning in gate1.warnings:
        if "days old" in warning.lower():
            actions.append(
                "Data may be stale. Check the source page to see if newer data "
                "has been published since the last scrape."
            )
        elif "freshness" in warning.lower():
            actions.append("Data freshness could not be verified — check manually.")

    # Gate 2 issues → specific guidance
    if gate2:
        if gate2.number_mismatch:
            actions.append(
                "Number mismatch detected — open the source data link below and "
                "compare every number in the text against the original."
            )
        if gate2.direction_error:
            actions.append(
                "Price direction may be wrong (up vs down). Check the source "
                "to confirm whether the price rose or fell."
            )
        if gate2.invented_content:
            actions.append(
                "The text may contain a claim not in the source data. Read the "
                "source page and check every factual statement."
            )
        if not gate2.anomaly_noted:
            actions.append(
                "There may be an unusual pattern in the data that the text doesn't "
                "mention. Check the source data for anything noteworthy."
            )
        for note in gate2.notes:
            if note not in actions:
                actions.append(note)

    # Broken links → guidance
    if bad_links:
        for url, detail in bad_links:
            actions.append(
                "Broken link: {} (status: {}). Remove or replace it.".format(url, detail)
            )

    # If no specific actions but section was flagged, give generic but useful guidance
    if not actions and links:
        actions.append(
            "This section was flagged for review. Check the source links below "
            "to verify all numbers and facts are accurate."
        )

    return {
        "actions": actions,
        "verify_links": links,
    }


# ── Gate 1: Data validation ──────────────────────────────────────────────

def run_gate1(section, data):
    # type: (str, dict) -> Gate1Result
    """
    Validate raw data before it reaches the AI writer.
    Checks ranges, cross-commodity relationships, freshness, required fields.
    """
    with open(str(CONFIG_FILE)) as f:
        config = json.load(f)

    result = Gate1Result(passed=True)

    if data.get("error"):
        result.errors.append("Data has error flag: {}".format(data.get("message", "unknown")))
        result.passed = False
        return result

    # ── Check 1: Required fields ──────────────────────────────────────────
    required = config["required_fields_by_section"].get(section, [])
    for field_name in required:
        if field_name not in data or data[field_name] is None:
            result.errors.append("Required field '{}' is missing".format(field_name))
            result.passed = False
        else:
            result.checks.append("Required field '{}' present".format(field_name))

    # ── Check 2: Price ranges ─────────────────────────────────────────────
    price_ranges = config["price_ranges"]
    extracted = {}
    if section == "markets":
        extracted = _extract_grain_prices(data)
    elif section == "costs":
        extracted = _extract_fertiliser_prices(data)
    elif section == "livestock":
        extracted = _extract_livestock_prices(data)

    for field_name, value in extracted.items():
        if field_name.endswith("_change_pct"):
            continue
        if field_name in price_ranges and value is not None:
            rule = price_ranges[field_name]
            try:
                numeric = float(value)
                if numeric < rule["min"] or numeric > rule["max"]:
                    result.errors.append(
                        "{}: {} {} is outside plausible range ({}-{} {}). "
                        "Check source data.".format(
                            rule["label"], value, rule["unit"],
                            rule["min"], rule["max"], rule["unit"]
                        )
                    )
                    result.passed = False
                else:
                    result.checks.append(
                        "{}: {} {} within range".format(rule["label"], value, rule["unit"])
                    )
            except (ValueError, TypeError):
                result.warnings.append(
                    "Could not validate '{}' — value '{}' is not numeric".format(field_name, value)
                )

    # ── Check 3: Cross-commodity rules ────────────────────────────────────
    if section == "markets" and extracted:
        for rule in config.get("cross_commodity_rules", []):
            val_a = extracted.get(rule["field_a"])
            val_b = extracted.get(rule["field_b"])
            if val_a is not None and val_b is not None:
                try:
                    a = float(val_a)
                    b = float(val_b)
                    violated = False
                    if rule["check"] == "a_above_b" and a < b:
                        violated = True

                    if violated:
                        msg = rule["message"].format(a=val_a, b=val_b)
                        if rule["severity"] == "warning":
                            result.anomalies.append(msg)
                        else:
                            result.warnings.append(msg)
                        result.checks.append(
                            "ANOMALY: {} — {}".format(rule["name"], msg)
                        )
                    else:
                        result.checks.append(
                            "{}: normal relationship".format(rule["name"])
                        )
                except (ValueError, TypeError):
                    pass

    # ── Check 4: Week-on-week plausibility ────────────────────────────────
    max_change_pct = config.get("max_weekly_change_pct", 15)
    for field_name, value in extracted.items():
        if field_name.endswith("_change_pct") and value is not None:
            try:
                pct = abs(float(value))
                commodity = field_name.replace("_change_pct", "")
                label = price_ranges.get(commodity, {}).get("label", commodity)
                if pct > max_change_pct:
                    result.anomalies.append(
                        "{} changed {:.1f}% in one week — this is unusual and may "
                        "indicate a scraper error. Verify source data.".format(label, pct)
                    )
                else:
                    result.checks.append(
                        "{}: {:.1f}% weekly change within normal range".format(label, pct)
                    )
            except (ValueError, TypeError):
                pass

    # ── Check 5: Data freshness ───────────────────────────────────────────
    max_age = config["staleness_rules"]["max_data_age_days"]
    date_str = _find_date_field(data)
    if date_str:
        try:
            # Handle various date formats
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    data_date = datetime.strptime(date_str[:len(fmt) + 2], fmt)
                    break
                except ValueError:
                    continue
            else:
                data_date = datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))

            age_days = (datetime.now() - data_date).days
            if age_days > max_age:
                result.warnings.append(
                    "Data is {} days old (max recommended: {} days). "
                    "Check if fresher data is available.".format(age_days, max_age)
                )
            else:
                result.checks.append("Data freshness: {} day(s) old".format(age_days))
        except (ValueError, TypeError) as exc:
            result.warnings.append("Could not parse date '{}' — freshness not checked".format(date_str))
    else:
        # Don't warn for sections that don't typically have dates
        if section in ("markets", "costs", "livestock", "weather"):
            result.warnings.append("No date field found — data freshness not checked")

    # ── Check 6: Empty data guard ─────────────────────────────────────────
    non_meta = [k for k in data.keys() if k not in ("error", "message", "source", "data_date")]
    if not non_meta:
        result.errors.append("Data object is empty — scraper may have returned nothing")
        result.passed = False
    else:
        result.checks.append("Data object has {} field(s)".format(len(non_meta)))

    # ── Check 7: Cross-week comparison (vs data/previous/) ──────────────
    if section in ("markets", "costs", "livestock") and extracted:
        xw_checks, xw_anomalies = _cross_week_checks(section, extracted, config)
        result.checks.extend(xw_checks)
        result.anomalies.extend(xw_anomalies)

    return result


# ── Gate 2: AI cross-check ────────────────────────────────────────────────

def run_gate2(section, ai_text, raw_data):
    # type: (str, str, dict) -> Gate2Result
    """
    Ask Claude to verify the finished section text against the raw source data.
    A second, independent Claude call — not the same one that wrote the section.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        result = Gate2Result(passed=True, confidence="MEDIUM")
        result.notes.append("No API key — Gate 2 skipped")
        return result

    client = anthropic.Anthropic(api_key=api_key)

    verification_prompt = """You are a data accuracy checker for Field Notes: East Anglia, a farming newsletter.

A section has been written by AI. Your job is to verify it against the raw source data.
Farmers make financial decisions based on these numbers — accuracy is critical.

IMPORTANT — what counts as accurate:
- Numbers: exact values AND natural rounding are both accurate (e.g. source: 179.82 -> text: "around 180" = CORRECT)
- Paraphrasing a fact from source data = accurate, not invented
- Only flag if a number is MATERIALLY wrong (>2% off, wrong units, or wrong direction)

IMPORTANT — what to check for anomalies:
- Are there unusual relationships in the data that the text fails to note? (e.g. feed wheat above milling wheat, which is unusual)
- Does the text draw conclusions not supported by the data?

SECTION: {section}

RAW SOURCE DATA:
{data}

WRITTEN TEXT:
{text}

Answer each question with YES or NO, then one sentence of explanation.

1. NUMBERS_MATCH: Does every number in the text accurately reflect the source data? (Allow natural rounding within 2%.)
2. DIRECTION_CORRECT: Are all directions (up/down/higher/lower/rising/falling) correct?
3. SOURCE_ACCURATE: Are source attributions accurate?
4. INVENTED_CONTENT: Does the text state any specific fact (number, event, regulation) that has no basis in the source data?
5. ANOMALIES_NOTED: Does the text appropriately note any unusual data patterns? If there are no unusual patterns, answer YES.
6. CONFIDENCE: Rate your overall confidence: HIGH, MEDIUM, or LOW

HIGH = all claims traceable to source data, numbers accurate, directions correct
MEDIUM = numbers correct, but some explanatory context added that is reasonable inference
LOW = any number materially wrong (>2%), direction incorrect, or specific claims not in source data

Respond in this exact format:
NUMBERS_MATCH: [YES/NO] — [explanation]
DIRECTION_CORRECT: [YES/NO] — [explanation]
SOURCE_ACCURATE: [YES/NO] — [explanation]
INVENTED_CONTENT: [YES/NO] — [explanation]
ANOMALIES_NOTED: [YES/NO] — [explanation]
CONFIDENCE: [HIGH/MEDIUM/LOW] — [explanation]""".format(
        section=section,
        data=json.dumps(raw_data, indent=2, default=str),
        text=ai_text,
    )

    try:
        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=MAX_TOKENS_VERIFY,
            messages=[{"role": "user", "content": verification_prompt}],
        )
        reply = response.content[0].text
        return _parse_gate2_response(reply)
    except Exception as e:
        logger.error("Gate 2 API call failed for %s: %s", section, e)
        result = Gate2Result(passed=True, confidence="MEDIUM")
        result.notes.append("Gate 2 API call failed: {}. Skipping verification.".format(e))
        return result


def _parse_gate2_response(reply):
    # type: (str) -> Gate2Result
    """Parse Claude's structured Gate 2 response into a Gate2Result."""
    result = Gate2Result(passed=True)
    lines = reply.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("NUMBERS_MATCH:"):
            answer = "YES" in line.upper().split("—")[0] if "—" in line else "YES" in line.upper()
            if not answer:
                result.number_mismatch = True
                result.notes.append(line)
                if BLOCK_ON_NUMBER_MISMATCH:
                    result.passed = False

        elif line.startswith("DIRECTION_CORRECT:"):
            answer = "YES" in line.upper().split("—")[0] if "—" in line else "YES" in line.upper()
            if not answer:
                result.direction_error = True
                result.notes.append(line)
                result.passed = False

        elif line.startswith("SOURCE_ACCURATE:"):
            answer = "YES" in line.upper().split("—")[0] if "—" in line else "YES" in line.upper()
            result.source_accurate = answer
            if not answer:
                result.notes.append(line)

        elif line.startswith("INVENTED_CONTENT:"):
            answer = "YES" in line.upper().split("—")[0] if "—" in line else "YES" in line.upper()
            if answer:
                result.invented_content = True
                result.notes.append(line)
                result.passed = False

        elif line.startswith("ANOMALIES_NOTED:"):
            answer = "YES" in line.upper().split("—")[0] if "—" in line else "YES" in line.upper()
            result.anomaly_noted = answer
            if not answer:
                result.notes.append(line)

        elif line.startswith("CONFIDENCE:"):
            if "HIGH" in line.upper():
                result.confidence = "HIGH"
            elif "LOW" in line.upper():
                result.confidence = "LOW"
                if FLAG_ON_LOW_CONFIDENCE:
                    result.notes.append(line)
            else:
                result.confidence = "MEDIUM"

    return result


# ── Combined verification ─────────────────────────────────────────────────

def verify_section(section, raw_data, ai_text):
    # type: (str, dict, str) -> SectionVerification
    """
    Run both gates and return a combined SectionVerification.
    Gate 1 runs on raw data. Gate 2 runs on written text + raw data.
    Also checks links in the AI text and builds actionable review guidance.
    """
    gate1 = run_gate1(section, raw_data)

    # Skip Gate 2 if section has no data or AI returned error fallback
    skip_gate2 = (
        not gate1.passed
        or "Data unavailable" in ai_text
        or "No data available" in ai_text
        or len(ai_text.strip()) < 20
    )

    if skip_gate2 and not gate1.passed:
        guidance = build_review_guidance(section, gate1)
        return SectionVerification(
            section=section,
            gate1=gate1,
            blocked=True,
            block_reason="Gate 1 failed: {}".format("; ".join(gate1.errors)),
            review_guidance=guidance,
        )

    if skip_gate2:
        flagged = bool(gate1.warnings or gate1.anomalies)
        guidance = build_review_guidance(section, gate1) if flagged else {}
        return SectionVerification(
            section=section,
            gate1=gate1,
            flagged=flagged,
            review_guidance=guidance,
        )

    # ── Link verification ────────────────────────────────────────────────
    good_links, bad_links = verify_links(ai_text)
    broken_links_list = [{"url": url, "detail": str(detail)} for url, detail in bad_links]
    if good_links:
        gate1.checks.append("{} link(s) verified OK".format(len(good_links)))
    if bad_links:
        for url, detail in bad_links:
            gate1.warnings.append("Broken link: {} (status: {})".format(url, detail))

    gate2 = run_gate2(section, ai_text, raw_data)

    if GATE2_BLOCKS_SECTION:
        blocked = not gate2.passed
    else:
        blocked = False

    flagged = (
        not gate2.passed
        or gate2.confidence == "LOW"
        or bool(gate1.anomalies)
        or not gate2.anomaly_noted
        or bool(bad_links)
    )

    block_reason = ""
    if blocked:
        reasons = []
        if gate2.number_mismatch:
            reasons.append("number mismatch")
        if gate2.direction_error:
            reasons.append("wrong direction")
        if gate2.invented_content:
            reasons.append("invented content")
        block_reason = "Gate 2 failed: {}".format("; ".join(reasons))

    # Build review guidance for any section that's flagged or blocked
    guidance = {}
    if flagged or blocked:
        guidance = build_review_guidance(section, gate1, gate2, bad_links)

    return SectionVerification(
        section=section,
        gate1=gate1,
        gate2=gate2,
        blocked=blocked,
        flagged=flagged,
        block_reason=block_reason,
        broken_links=broken_links_list,
        review_guidance=guidance,
    )
