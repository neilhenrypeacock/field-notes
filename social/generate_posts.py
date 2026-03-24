"""
social/generate_posts.py
========================
Run every Sunday evening to generate the week's 7 Facebook posts.

What it does:
1. Runs all relevant scrapers to get fresh data
2. Reads the master prompt from data/post_prompt.txt
3. Calls Claude to write each post (one API call per post)
4. Runs Gate 1 + Gate 2 verification on every post
5. Saves all results to data/scheduled_posts.json
6. Prints a clear summary to your terminal

Usage:
    .venv/bin/python social/generate_posts.py

After running, check the output then run:
    .venv/bin/python social/review_posts.py
"""

import sys
import json
import logging
import importlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

# Load .env from main project
load_dotenv(Path("/Users/neilpeacock/Projects/fieldnotes/.env"), override=True)

# Add scrapers to path
sys.path.insert(0, str(Path("/Users/neilpeacock/Projects/fieldnotes")))

from social.config import (
    WEEKLY_SCHEDULE,
    PROMPT_FILE,
    SCHEDULED_FILE,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    MAX_TOKENS_POST,
    SECTION_HASHTAGS,
    SECTION_TAGS,
    HIGH_VALUE_SECTIONS,
    SCRAPERS_DIR,
)
from social.verify import verify_post, VerificationResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Scraper map ────────────────────────────────────────────────────────────
# Maps section names to scraper modules and the function to call.
# Each scraper should return a dict of data.

SCRAPER_MAP = {
    "markets":            ("scrapers.ahdb_grain",      "scrape"),
    "inputs":             ("scrapers.ahdb_feed",        "scrape"),
    "schemes":            ("scrapers.govuk_schemes",    "scrape"),
    "news":               ("scrapers.defra_blog",       "scrape"),
    "land":               ("scrapers.land_listings",    "scrape"),
    "jobs":               ("scrapers.jobs",             "scrape"),
    "machinery":          ("scrapers.machinery_auctions","scrape"),
    "livestock":          ("scrapers.ahdb_livestock",   "scrape"),
    "land_jobs_machinery": None,  # handled specially — picks best of land/jobs/machinery
    "monday_newsletter":  None,   # handled specially — no scraper needed
}


# ── Run a scraper ──────────────────────────────────────────────────────────

def run_scraper(section: str) -> Optional[dict]:
    """Run the scraper for a given section. Returns dict or None on failure."""
    if SCRAPER_MAP.get(section) is None:
        return {}  # Special sections handled elsewhere

    module_path, func_name = SCRAPER_MAP[section]
    try:
        module = importlib.import_module(module_path)
        scrape_fn = getattr(module, func_name)
        data = scrape_fn()
        if data:
            logger.info(f"✓ Scraped {section}")
            return data
        else:
            logger.warning(f"⚠ Scraper returned empty data for {section}")
            return None
    except Exception as e:
        logger.error(f"✗ Scraper failed for {section}: {e}")
        return None


def run_land_jobs_machinery_scraper() -> tuple[str, dict]:
    """
    For Saturday's post, pick the most interesting of land/jobs/machinery.
    Returns (section_name, data).
    """
    candidates = {}
    for s in ["land", "jobs", "machinery"]:
        try:
            module_path, func_name = SCRAPER_MAP[s]
            module = importlib.import_module(module_path)
            data = getattr(module, func_name)()
            if data:
                candidates[s] = data
        except Exception as e:
            logger.warning(f"Could not scrape {s}: {e}")

    # Prefer land if it has listings, then machinery, then jobs
    for preferred in ["land", "machinery", "jobs"]:
        if preferred in candidates and candidates[preferred]:
            return preferred, candidates[preferred]

    # Fallback to whatever we got
    if candidates:
        section = list(candidates.keys())[0]
        return section, candidates[section]

    return "land", {}


# ── Load master prompt ─────────────────────────────────────────────────────

def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


# ── Get newsletter headlines for Monday post ───────────────────────────────

def get_newsletter_headlines() -> list[str]:
    """
    Read the most recently generated newsletter and extract 3 headlines.
    Falls back to placeholder text if no newsletter found.
    """
    newsletter_dir = Path("/Users/neilpeacock/Projects/fieldnotes/newsletter/output")
    txt_files = sorted(newsletter_dir.glob("*.txt"), reverse=True)

    if not txt_files:
        logger.warning("No newsletter .txt files found — using placeholder headlines")
        return [
            "Grain prices and what they mean for East Anglia this week",
            "Latest scheme and grant opportunities open now",
            "East Anglia 5-day weather outlook"
        ]

    latest = txt_files[0]
    try:
        content = latest.read_text(encoding="utf-8")
        # Extract the first substantive line from each major section
        headlines = []
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        # Look for lines that look like section summaries (not headers, not empty)
        for line in lines:
            if (len(line) > 40 and len(line) < 200
                    and not line.startswith("#")
                    and not line.startswith("---")
                    and ("£" in line or any(
                        kw in line.lower() for kw in
                        ["wheat", "price", "scheme", "weather", "grant", "forecast"]
                    ))):
                headlines.append(line[:120])
                if len(headlines) == 3:
                    break

        if len(headlines) >= 2:
            logger.info(f"✓ Extracted {len(headlines)} headlines from {latest.name}")
            return headlines[:3]
    except Exception as e:
        logger.warning(f"Could not extract headlines from newsletter: {e}")

    return [
        "This week's grain prices and market context",
        "Active scheme and grant deadlines this week",
        "East Anglia 5-day forecast and fieldwork outlook"
    ]


# ── Write a post with Claude ───────────────────────────────────────────────

def generate_post(
    section: str,
    raw_data: dict,
    master_prompt: str,
    used_formats: list,
    used_ctas: list,
    week_number: int
) -> Optional[str]:
    """
    Call Claude to write a single Facebook post.
    Passes the master prompt, the raw data, and context about
    what formats/CTAs have already been used this week.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hashtag = SECTION_HASHTAGS.get(section, "#Farming")
    org_tag = SECTION_TAGS.get(section, "")

    # Build the data prompt
    if section == "monday_newsletter":
        headlines = get_newsletter_headlines()
        data_prompt = f"""SECTION: monday_newsletter

This is the Monday newsletter announcement post.
Use the Monday template from the prompt exactly.
Insert these 3 actual headlines from this week's newsletter:
1. {headlines[0]}
2. {headlines[1]}
3. {headlines[2] if len(headlines) > 2 else 'East Anglia weather outlook and fieldwork forecast'}

Hashtags to use: #EastAnglia #Farming"""
    else:
        data_prompt = f"""SECTION: {section}

RAW DATA FROM SCRAPER:
{json.dumps(raw_data, indent=2, default=str)}

HASHTAGS TO USE: #EastAnglia {hashtag}
ORG TAG (include if relevant): {org_tag if org_tag else 'none'}

FORMATS ALREADY USED THIS WEEK: {', '.join(used_formats) if used_formats else 'none yet'}
CTA PHRASES ALREADY USED THIS WEEK: {', '.join(used_ctas) if used_ctas else 'none yet'}
WEEK NUMBER (for variation): {week_number}

Do not use a format or CTA that has already been used this week.
Choose the most appropriate format for this data type."""

    full_prompt = f"{master_prompt}\n\n{'='*60}\n\nYOUR TASK:\n\n{data_prompt}"

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS_POST,
            messages=[{"role": "user", "content": full_prompt}]
        )
        post_text = response.content[0].text.strip()
        logger.info(f"✓ Generated post for {section}")
        return post_text

    except Exception as e:
        logger.error(f"✗ Post generation failed for {section}: {e}")
        return None


# ── Calculate posting dates for this week ─────────────────────────────────

def get_posting_dates() -> dict:
    """
    Given today (Sunday), calculate the actual date for each day of the week.
    Returns dict mapping day name → date string.
    """
    today = datetime.now()
    # Find Monday of this coming week
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)

    day_map = {
        "Monday":    monday,
        "Tuesday":   monday + timedelta(days=1),
        "Wednesday": monday + timedelta(days=2),
        "Thursday":  monday + timedelta(days=3),
        "Friday":    monday + timedelta(days=4),
        "Saturday":  monday + timedelta(days=5),
        "Sunday":    monday + timedelta(days=6),
    }
    return {day: dt.strftime("%Y-%m-%d") for day, dt in day_map.items()}


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("FIELD NOTES: EAST ANGLIA — SUNDAY POST GENERATION")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%A %d %B %Y, %H:%M')}\n")

    master_prompt = load_prompt()
    posting_dates = get_posting_dates()
    week_number = datetime.now().isocalendar()[1]

    posts = []
    used_formats = []
    used_ctas    = []
    blocked_count = 0
    flagged_count = 0

    for slot in WEEKLY_SCHEDULE:
        section = slot["section"]
        day     = slot["day"]
        time    = slot["time"]
        label   = slot["label"]
        post_date = posting_dates[day]

        print(f"── {day} {time} | {label} ──")

        # ── Step 1: Get data ───────────────────────────────────────────────
        if section == "monday_newsletter":
            raw_data = {"section": "monday_newsletter"}
            actual_section = "monday_newsletter"
        elif section == "land_jobs_machinery":
            actual_section, raw_data = run_land_jobs_machinery_scraper()
        else:
            actual_section = section
            raw_data = run_scraper(section)

        if raw_data is None:
            print(f"   🔴 BLOCKED — scraper returned no data\n")
            posts.append({
                "day":      day,
                "date":     post_date,
                "time":     time,
                "section":  section,
                "label":    label,
                "status":   "blocked",
                "block_reason": "Scraper returned no data",
                "post_text": None,
                "first_comment": None,
                "verification": None,
                "approved":  False,
                "posted":    False,
                "high_value": False,
            })
            blocked_count += 1
            continue

        # ── Step 2: Gate 1 validation ──────────────────────────────────────
        if section != "monday_newsletter":
            gate1 = __import__("social.verify", fromlist=["run_gate1"]).run_gate1(
                actual_section, raw_data
            )
            if not gate1.passed:
                print(f"   🔴 BLOCKED (Gate 1) — {'; '.join(gate1.errors)}\n")
                posts.append({
                    "day":      day,
                    "date":     post_date,
                    "time":     time,
                    "section":  section,
                    "label":    label,
                    "status":   "blocked",
                    "block_reason": f"Gate 1: {'; '.join(gate1.errors)}",
                    "post_text": None,
                    "first_comment": None,
                    "verification": {"gate1_errors": gate1.errors},
                    "approved":  False,
                    "posted":    False,
                    "high_value": False,
                })
                blocked_count += 1
                continue
            if gate1.warnings:
                print(f"   ⚠ Gate 1 warnings: {'; '.join(gate1.warnings)}")

        # ── Step 3: Generate post ──────────────────────────────────────────
        post_text = generate_post(
            actual_section, raw_data, master_prompt,
            used_formats, used_ctas, week_number
        )

        if not post_text:
            print(f"   🔴 BLOCKED — post generation failed\n")
            blocked_count += 1
            continue

        # ── Step 4: Gate 2 verification ────────────────────────────────────
        if section != "monday_newsletter":
            verification = verify_post(actual_section, raw_data, post_text)
        else:
            # Monday post has no numeric data to verify
            from social.verify import Gate1Result, Gate2Result, VerificationResult
            verification = VerificationResult(
                gate1=Gate1Result(passed=True),
                gate2=Gate2Result(passed=True, confidence="HIGH"),
                blocked=False,
                flagged=False,
            )

        if verification.blocked:
            print(f"   🔴 BLOCKED (Gate 2) — {verification.block_reason}\n")
            blocked_count += 1
            posts.append({
                "day":         day,
                "date":        post_date,
                "time":        time,
                "section":     section,
                "label":       label,
                "status":      "blocked",
                "block_reason": verification.block_reason,
                "post_text":   post_text,
                "first_comment": None,
                "verification": {
                    "gate1_checks":   verification.gate1.checks,
                    "gate1_warnings": verification.gate1.warnings,
                    "gate1_errors":   verification.gate1.errors,
                    "gate2_notes":    verification.gate2.notes if verification.gate2 else [],
                    "confidence":     verification.gate2.confidence if verification.gate2 else "UNKNOWN",
                },
                "approved":    False,
                "posted":      False,
                "high_value":  False,
            })
            continue

        # ── Step 5: Track format + CTA to avoid repeats ───────────────────
        if "FORMAT A" in post_text: used_formats.append("FORMAT A")
        elif "FORMAT B" in post_text: used_formats.append("FORMAT B")
        elif "FORMAT C" in post_text: used_formats.append("FORMAT C")
        elif "FORMAT D" in post_text: used_formats.append("FORMAT D")

        # Extract CTA phrase (last line before hashtags)
        lines = [l.strip() for l in post_text.split("\n") if l.strip()]
        for line in reversed(lines):
            if "link in comments" in line.lower() or "link below" in line.lower():
                used_ctas.append(line[:50])
                break

        is_high_value = actual_section in HIGH_VALUE_SECTIONS
        is_flagged    = verification.flagged

        if is_flagged:
            flagged_count += 1
            print(f"   🟡 FLAGGED (low confidence) — review carefully")

        status = "flagged" if is_flagged else "ready"
        print(f"   🟢 Ready — {verification.gate2.confidence if verification.gate2 else 'N/A'} confidence")

        posts.append({
            "day":         day,
            "date":        post_date,
            "time":        time,
            "section":     section,
            "actual_section": actual_section,
            "label":       label,
            "status":      status,
            "block_reason": "",
            "post_text":   post_text,
            "raw_data":    {k: str(v) for k, v in raw_data.items()},
            "first_comment": None,  # assigned at schedule time from rotating bank
            "verification": {
                "gate1_checks":   verification.gate1.checks,
                "gate1_warnings": verification.gate1.warnings,
                "gate1_errors":   verification.gate1.errors,
                "gate2_notes":    verification.gate2.notes if verification.gate2 else [],
                "gate2_summary":  verification.gate2.summary() if verification.gate2 else "",
                "confidence":     verification.gate2.confidence if verification.gate2 else "UNKNOWN",
                "status_line":    verification.status_line(),
            },
            "high_value":  is_high_value,
            "approved":    False,
            "posted":      False,
            "generated_at": datetime.now().isoformat(),
        })
        print()

    # ── Save to scheduled_posts.json ──────────────────────────────────────
    with open(SCHEDULED_FILE, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "posts": posts}, f, indent=2)

    # ── Summary ───────────────────────────────────────────────────────────
    ready   = sum(1 for p in posts if p["status"] in ("ready", "flagged"))
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
    print(f"  Posts ready:   {ready}")
    print(f"  Posts flagged: {flagged_count} (need extra review)")
    print(f"  Posts blocked: {blocked_count} (will not be published)")
    print(f"\n  Saved to: social/data/scheduled_posts.json")
    print(f"\n  Next step:")
    print(f"  .venv/bin/python social/review_posts.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
