"""
Newsletter generator: loads all scraped data, calls Claude per section,
assembles HTML and plain-text newsletter, saves to newsletter/output/.
"""

import base64
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from string import Template
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FILTERED_DIR = BASE_DIR / "scrapers" / "filtered"
PROMPTS_DIR = BASE_DIR / "prompts"
TEMPLATE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = TEMPLATE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
ISSUE_FILE = DATA_DIR / "issue_number.json"
ASSETS_DIR = TEMPLATE_DIR / "assets"
ASSETS_BASE_URL = os.getenv("ASSETS_BASE_URL", "").rstrip("/")

# Illustration filename mapping: template variable → SVG filename
ILLUSTRATIONS = {
    "banner_map":        "fn_map_east_anglia_banner.svg",
    "illus_glance":      "fn_illustration_01_at_a_glance.svg",
    "illus_markets":     "fn_illustration_02_markets.svg",
    "illus_costs":       "fn_illustration_03_input_costs.svg",
    "illus_margins":     "fn_illustration_04_margin_watch.svg",
    "illus_livestock":   "fn_illustration_04b_livestock.svg",
    "illus_schemes":     "fn_illustration_05_schemes.svg",
    "illus_weather":     "fn_illustration_06_weather.svg",
    "illus_land":        "fn_illustration_07_land.svg",
    "illus_jobs":        "fn_illustration_08_jobs.svg",
    "illus_machinery":   "fn_illustration_09_machinery.svg",
    "illus_regulatory":  "fn_illustration_10_regulatory.svg",
    "illus_events":      "fn_illustration_11_events.svg",
    "illus_read":        "fn_illustration_12_one_good_read.svg",
    "illus_tech_watch":  "fn_illustration_12b_tech_watch.svg",
}

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("field_notes.generate")

AI_MODEL = "claude-sonnet-4-5"
AI_MAX_TOKENS = 600

# Colour constants for price tables
GREEN = "#2e7d32"
RED = "#c62828"
GREY = "#666666"

# Reusable HR divider for within-cluster section separators (email-safe table row)
SIMPLE_HR = (
    '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">'
    '<tr><td style="padding-top:24px;"></td></tr>'
    '<tr><td style="height:1px;background-color:#e8e2d6;font-size:0;line-height:0;" height="1">&nbsp;</td></tr>'
    '</table>'
)


# ──────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────

def _get_next_issue_number() -> int:
    n = 1
    if ISSUE_FILE.exists():
        try:
            n = json.loads(ISSUE_FILE.read_text()).get("current", 0) + 1
        except Exception:
            pass
    ISSUE_FILE.write_text(json.dumps({"current": n}))
    return n


def _load_illustrations() -> dict:
    """Return dict of template-var → image src for each illustration.

    If ASSETS_BASE_URL is set, uses HTTPS URLs (email-safe, no Gmail stripping).
    Otherwise falls back to base64 data URIs (works in local preview only).
    """
    result = {}
    for var, filename in ILLUSTRATIONS.items():
        if ASSETS_BASE_URL:
            result[var] = f"{ASSETS_BASE_URL}/{filename}"
        else:
            path = ASSETS_DIR / filename
            if path.exists():
                b64 = base64.b64encode(path.read_bytes()).decode("ascii")
                result[var] = f"data:image/svg+xml;base64,{b64}"
            else:
                logger.warning("Missing illustration: %s", filename)
                result[var] = ""
    return result


def load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        logger.warning("Missing data file: %s", filename)
        return {"error": True, "message": f"Data file {filename} not found"}
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        logger.error("Failed to load %s: %s", filename, exc)
        return {"error": True, "message": str(exc)}


def load_filtered(name):
    # type: (str) -> list
    """Load scrapers/filtered/{name}.json items list. Returns [] if absent or empty."""
    path = FILTERED_DIR / "{}.json".format(name)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        items = data if isinstance(data, list) else data.get("items", [])
        return items if isinstance(items, list) else []
    except Exception:
        return []


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        return f"Summarise the {name} data for East Anglian farmers. Be concise and practical."
    return path.read_text().strip()


# ──────────────────────────────────────────────
# AI summary
# ──────────────────────────────────────────────

SHARED_CONTEXT = (
    "You are writing a section of 'Field Notes: East Anglia', a free weekly farming "
    "intelligence newsletter for professional arable and mixed farmers in Norfolk, Suffolk, "
    "and Cambridgeshire.\n\n"
    "ABOUT THE DATA YOU ARE RECEIVING:\n"
    "All data passed to you has been scraped directly from official, verified sources: "
    "AHDB, Met Office, GOV.UK, and other authoritative bodies. Every number you receive "
    "is real and current. Do not hedge, qualify, or second-guess any figure you have "
    "been given. Treat all data as authoritative fact.\n\n"
    "ABOUT YOUR READERS:\n"
    "Experienced farming professionals who want facts, numbers, and practical "
    "implications — not general explanations, not hedging, not reassurance. "
    "Use farming-specific language where appropriate: ex-farm, delivered, p/kg dwt, "
    "£/t, week-on-week.\n\n"
    "WRITING RULES:\n"
    "- Be concise and direct. Lead with the most important fact.\n"
    "- Write specifically for an East Anglian arable farmer growing wheat, barley "
    "and oilseed rape in Norfolk, Suffolk or Cambridgeshire.\n"
    "- Lead with local East Anglian information where it exists.\n"
    "- If data is national rather than region-specific, say so in a single clause "
    "and explain why it is relevant to farms in this region.\n"
    "- Never use phrases like: \"appears to\", \"may reflect\", \"seems to suggest\", "
    "\"could indicate\", \"it is possible that\", or any other hedging language.\n"
    "- State what happened. State the number. State the implication if it is "
    "mathematically derivable from the data. Stop.\n"
    "- Do not editorialize. Do not advise. Do not presume to know the farmer's "
    "situation. Let the numbers speak.\n\n"
    "IF YOU HAVE NO DATA:\n"
    "If you have received no usable data for this section, output exactly this "
    "one sentence: \"No data available for this section this week.\" "
    "Then output your confidence JSON. Do not pad, infer, speculate, or fill space.\n\n"
    "CONFIDENCE SCORE — output this JSON on the final line of every response, "
    "on its own line, with no other text before or after it on that line:\n"
    "{{\"confidence\": 0.0, \"reason\": \"\", \"data_gaps\": []}}\n"
    "Score rules:\n"
    "- 0.9 to 1.0 — all expected data fields were received and are complete\n"
    "- 0.6 to 0.8 — some fields missing but enough data to write a useful section\n"
    "- 0.3 to 0.5 — data was thin, partial, or only one field available\n"
    "- 0.0 to 0.2 — no usable data received for this section\n"
    "The confidence score reflects DATA COMPLETENESS ONLY. "
    "Never score low because you are uncertain about market interpretation or "
    "because prices moved unexpectedly. That is analysis, not a data quality issue. "
    "Score what you received, not what you think about it.\n\n"
    "Today's date: {date}.\n\n"
)


def get_ai_summary(section: str, data: dict, extra_context: str = "") -> str:
    if data.get("error"):
        return f"<em>Data unavailable this week.</em>"

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt_body = load_prompt(section)
    today_str = date.today().strftime("%-d %B %Y")
    context = SHARED_CONTEXT.format(date=today_str) + extra_context
    full_prompt = f"{context}{prompt_body}\n\nDATA:\n{json.dumps(data, indent=2)}"

    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            messages=[{"role": "user", "content": full_prompt}],
        )
        text = message.content[0].text.strip()
        # Strip trailing confidence JSON line added by SHARED_CONTEXT instruction
        text = re.sub(r'\n\{"confidence":[^}]+\}\s*$', '', text).strip()
        # Log token usage
        _log_usage(section, message.usage)
        return text
    except anthropic.APIError as exc:
        logger.error("AI call failed for section '%s': %s", section, exc)
        return f"<em>[Section unavailable — AI generation failed]</em>"


def _log_usage(section: str, usage) -> None:
    log_path = BASE_DIR / "logs" / "ai_usage.json"
    record = {
        "section": section,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text())
        except Exception:
            pass
    existing.append(record)
    log_path.write_text(json.dumps(existing[-200:], indent=2))  # keep last 200 records


# ──────────────────────────────────────────────
# HTML helpers
# ──────────────────────────────────────────────

def _change_colour(change) -> str:
    if change is None:
        return GREY
    return GREEN if change > 0 else (RED if change < 0 else GREY)


def _change_str(change, unit="") -> str:
    if change is None:
        return "N/A"
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}{unit}"


def _arrow_str(change, unit="") -> str:
    """Change value with ▲/▼ arrow prefix."""
    if change is None:
        return "N/A"
    arrow = "&#9650;" if change > 0 else ("&#9660;" if change < 0 else "")
    sign = "+" if change > 0 else ""
    return f"{arrow} {sign}{change:.2f}{unit}".strip()


def build_price_table_html(rows: list[dict], unit_label: str = "£/t") -> str:
    """Build an HTML price table from a list of price dicts.
    If any row has uk_average_price, a UK Avg column is added."""
    if not rows:
        return ""
    show_uk_avg = any(r.get("uk_average_price") is not None for r in rows)
    uk_avg_th = ('<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;'
                 'font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">UK Avg</th>'
                 if show_uk_avg else "")
    html = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
        'style="border-collapse:collapse;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:13px;border:1px solid #e8e2d6;border-radius:6px;overflow:hidden;">'
        '<thead><tr style="background-color:#1b3a2d;">'
        '<th style="text-align:left;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Commodity</th>'
        '<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">This Week</th>'
        '<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Last Week</th>'
        '<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Change</th>'
        + uk_avg_th +
        '</tr></thead><tbody>'
    )
    for i, row in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#faf8f4"
        is_last = i == len(rows) - 1
        border = "" if is_last else "border-bottom:1px solid #eee8e0;"
        price = row.get("spot_price") or row.get("price")
        prev = row.get("prev_week_price") or row.get("prev_month_price")
        change = row.get("change")
        uk_avg = row.get("uk_average_price")
        colour = _change_colour(change)
        price_str = f"&#163;{price:.2f}/{unit_label}" if price is not None else "&#8212;"
        prev_str = f"&#163;{prev:.2f}/{unit_label}" if prev is not None else "&#8212;"
        change_display = _arrow_str(change)
        uk_avg_td = ""
        if show_uk_avg:
            uk_avg_str = f"&#163;{uk_avg:.2f}/{unit_label}" if uk_avg is not None else "&#8212;"
            uk_avg_td = f'<td style="text-align:right;{border}padding:10px 14px;color:#888;">{uk_avg_str}</td>'

        html += (
            f'<tr style="background-color:{bg};">'
            f'<td style="{border}padding:10px 14px;color:#333;">{row.get("commodity") or row.get("product", "")}</td>'
            f'<td style="text-align:right;{border}padding:10px 14px;color:#333;font-weight:700;">{price_str}</td>'
            f'<td style="text-align:right;{border}padding:10px 14px;color:#888;">{prev_str}</td>'
            f'<td style="text-align:right;{border}padding:10px 14px;color:{colour};font-weight:700;">{change_display}</td>'
            + uk_avg_td +
            f'</tr>'
        )
    html += "</tbody></table>"
    return html


def build_price_table_livestock_html(livestock: dict) -> str:
    """Build an HTML price table for the Livestock & Dairy section."""
    rows = []
    pig = livestock.get("pig_prices", {})
    milk = livestock.get("milk_prices", {})
    eggs = livestock.get("egg_prices", {})
    beef = livestock.get("beef_prices", {})

    def _row(commodity, price_key, unit, data):
        price = data.get("price")
        prev = data.get("prev_week_price") or data.get("prev_period_price")
        change = data.get("change")
        if price is None or data.get("error"):
            return None
        return {"commodity": f"{commodity} ({unit})", "spot_price": price, "prev_week_price": prev, "change": change}

    poultry = livestock.get("poultry_prices", {})
    for r in [
        _row("Pig SPP", "price", "p/kg dwt", pig),
        _row("Milk farmgate", "price", "ppl", milk),
        _row("Beef deadweight", "price", "p/kg dwt", beef),
        _row("Eggs", "price", "p/doz", eggs),
        _row("Poultry", "price", "p/kg", poultry),
    ]:
        if r:
            rows.append(r)

    if not rows:
        return ""

    html = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
        'style="border-collapse:collapse;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:13px;border:1px solid #e8e2d6;border-radius:6px;overflow:hidden;">'
        '<thead><tr style="background-color:#1b3a2d;">'
        '<th style="text-align:left;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Commodity</th>'
        '<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Price</th>'
        '<th style="text-align:right;padding:10px 14px;color:#ffffff;font-weight:600;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Change</th>'
        '</tr></thead><tbody>'
    )
    for i, row in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#faf8f4"
        is_last = i == len(rows) - 1
        border = "" if is_last else "border-bottom:1px solid #eee8e0;"
        price = row.get("spot_price")
        change = row.get("change")
        colour = _change_colour(change)
        price_str = f"{price:.2f}" if price is not None else "&#8212;"
        change_display = _arrow_str(change)
        html += (
            f'<tr style="background-color:{bg};">'
            f'<td style="{border}padding:10px 14px;color:#333;">{row.get("commodity", "")}</td>'
            f'<td style="text-align:right;{border}padding:10px 14px;color:#333;font-weight:700;">{price_str}</td>'
            f'<td style="text-align:right;{border}padding:10px 14px;color:{colour};font-weight:700;">{change_display}</td>'
            f'</tr>'
        )
    html += "</tbody></table>"
    return html


def build_norwich_market_html(market: dict) -> str:
    """Build a single-line Norwich Livestock Market summary with link to full report."""
    if not market or market.get("error"):
        return ""
    lambs = market.get("lambs", {})
    if not lambs and not market.get("cattle_total_head"):
        return ""

    date_text = market.get("sale_date_text", "")
    source_url = market.get("source_url", "https://www.norwichlivestockmarket.com/reports")

    parts = []
    if market.get("cattle_total_head"):
        parts.append(f"store cattle {market['cattle_total_head']} head")

    label_map = {
        "prime_hoggs": "prime hoggs",
        "standard": "std lambs",
        "medium": "med lambs",
        "heavy": "heavy lambs",
        "heavy_plus": "heavy+ lambs",
    }
    for key in ["prime_hoggs", "standard", "medium", "heavy", "heavy_plus"]:
        if key in lambs:
            d = lambs[key]
            gbp = f"£{d['avg_gbp']:.0f}/hd" if d.get("avg_gbp") else ""
            if gbp:
                parts.append(f"{label_map[key]} avg {gbp}")

    if not parts:
        return ""

    summary = " &middot; ".join(parts)
    return (
        f'<p style="margin:0 0 6px;font-family:\'Source Sans 3\',Arial,sans-serif;font-size:12px;'
        f'font-weight:700;color:#1b3a2d;text-transform:uppercase;letter-spacing:0.5px;">'
        f'Norwich Market <span style="font-weight:400;color:#9a8e7d;">&mdash; {date_text}</span></p>'
        f'<p style="margin:0 0 8px;font-family:\'Source Serif 4\',Georgia,serif;font-size:13px;'
        f'font-style:italic;line-height:1.6;color:#555;">{summary}</p>'
        f'<p style="margin:0;"><a href="{source_url}" style="font-family:\'Source Sans 3\',Arial,sans-serif;'
        f'font-size:12px;font-weight:700;color:#1b3a2d;text-decoration:underline;">'
        f'Full market report &#8594;</a></p>'
    )


def build_event_cards_html(events_list: list) -> str:
    """Build styled event cards from a list of event dicts."""
    if not events_list:
        return ""
    cards = []
    for ev in events_list:
        title = ev.get("title", "")
        date_str = ev.get("date_start", "")
        location = ev.get("location") or "Location TBC"
        organiser = ev.get("organiser", "")
        url = ev.get("url", "")
        description = ev.get("description", "")
        try:
            d = datetime.strptime(date_str[:10], "%Y-%m-%d")
            date_formatted = d.strftime("%-d %B")
        except Exception:
            date_formatted = date_str
        meta = " · ".join(filter(None, [date_formatted, location, organiser]))
        card = (
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
            'style="margin:0 0 12px;border:1px solid #e8e2d6;border-radius:6px;overflow:hidden;">'
            '<tr><td style="padding:14px 16px;">'
            f'<p style="margin:0 0 3px;font-family:\'Source Sans 3\',Arial,sans-serif;font-size:14px;'
            f'font-weight:700;color:#1b3a2d;">{title}</p>'
            f'<p style="margin:0 0 6px;font-family:\'Source Sans 3\',Arial,sans-serif;font-size:12px;'
            f'color:#9a8e7d;">{meta}</p>'
        )
        if description:
            # Strip leading title repetition (common in og:description tags)
            if description.lower().startswith(title.lower()):
                description = description[len(title):].lstrip(" :-–—")
            card += (
                f'<p style="margin:0 0 10px;font-family:\'Source Sans 3\',Arial,sans-serif;'
                f'font-size:13px;line-height:1.6;color:#333;">{description}</p>'
            )
        if url:
            card += (
                f'<p style="margin:0;"><a href="{url}" style="display:inline-block;padding:6px 14px;'
                f'background-color:#1b3a2d;color:#ffffff;font-family:\'Source Sans 3\',Arial,sans-serif;'
                f'font-size:12px;font-weight:600;text-decoration:none;border-radius:4px;">'
                f'More info &#8594;</a></p>'
            )
        card += '</td></tr></table>'
        cards.append(card)
    return "\n".join(cards)


def build_this_week_hooks(at_a_glance_text: str) -> str:
    """Extract 3 short headline hooks from At a Glance bullets via a Claude API call."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = (
        "Given these bullet points from this week's newsletter At a Glance section, "
        "extract a 5–8 word headline from each bullet. "
        "Return exactly 3 headlines separated by ' · ' on a single line. "
        "No intro, no formatting, no markdown, no bullet characters. "
        "Example output: 'Feed barley surges £4.90/t · No spray windows this week · FETF 2026 now open'\n\n"
        f"Bullets:\n{at_a_glance_text}"
    )
    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()
        _log_usage("this_week_hooks", message.usage)
        return result
    except Exception as exc:
        logger.warning("This week hooks call failed: %s", exc)
        # Fallback: first non-empty line stripped of bullet chars
        for line in at_a_glance_text.split("\n"):
            stripped = line.strip().lstrip("•–-* ").strip()
            if stripped:
                return stripped[:80]
        return "This week's briefing"


def build_fieldwork_verdict(weather_data: dict) -> dict:
    """Analyse 7-day forecast and return verdict text + colour variables."""
    days = weather_data.get("days", [])[:7]

    bad_days = sum(
        1 for d in days
        if (d.get("precip_probability_pct") or 0) >= 60 and (d.get("wind_speed_mph") or 0) >= 15
    )

    if bad_days >= 4:
        colours = {
            "verdict_bg_color": "#fdf2f2",
            "verdict_border_color": "#e8c4c4",
            "verdict_label_color": "#c62828",
        }
    elif bad_days >= 2:
        colours = {
            "verdict_bg_color": "#fdf8ee",
            "verdict_border_color": "#e8dcc4",
            "verdict_label_color": "#b8860b",
        }
    else:
        colours = {
            "verdict_bg_color": "#f0f7f2",
            "verdict_border_color": "#c4e0cc",
            "verdict_label_color": "#2e7d32",
        }

    # Build a concise forecast summary for the AI call
    day_lines = []
    for d in days:
        day_lines.append(
            f"{d.get('day_of_week','')}: {d.get('weather_description','')} "
            f"max {d.get('max_temp_c','')}C wind {d.get('wind_speed_mph','')}mph "
            f"rain {d.get('precip_probability_pct','')}%"
        )
    forecast_summary = "\n".join(day_lines)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = (
        "Based on this 7-day weather forecast for East Anglia, write a 1-2 sentence "
        "fieldwork verdict for a farmer. Is there a spray window? Can they drill? "
        "What days are usable? Be specific about days. Use farmer language. "
        "Max 30 words. No intro, no heading.\n\n"
        f"Forecast:\n{forecast_summary}"
    )
    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        verdict_text = message.content[0].text.strip()
        _log_usage("fieldwork_verdict", message.usage)
    except Exception as exc:
        logger.warning("Fieldwork verdict call failed: %s", exc)
        verdict_text = "Check the 7-day table for spray and drilling windows this week."

    return {"fieldwork_verdict": verdict_text, **colours}


def section_has_content(section_name: str, ai_text: str, data: dict) -> bool:
    """Return False when a section should be omitted this week."""
    text_lower = ai_text.lower()
    if section_name == "regulatory":
        if ai_text.strip().upper() == "SKIP":
            return False
        skip_phrases = ["no major", "no significant", "no regulatory changes"]
        return not any(p in text_lower for p in skip_phrases)
    if section_name == "land":
        listings = data.get("listings", [])
        skip_phrases = ["no new listings", "limited activity"]
        return bool(listings) and not any(p in text_lower for p in skip_phrases)
    if section_name == "events":
        return bool(data.get("events")) or bool(data.get("community_events"))
    if section_name == "machinery":
        return bool(data.get("upcoming_sales"))
    return True


def build_job_cards_html(jobs_json_str: str, jobs_data: dict) -> str:
    """Parse JSON job listing from AI and build styled HTML cards.
    Falls back to plain text rendering if JSON parse fails."""
    try:
        jobs_list = json.loads(jobs_json_str)
        if not isinstance(jobs_list, list):
            raise ValueError("not a list")
    except (json.JSONDecodeError, ValueError):
        # Fallback: convert raw jobs from jobs_data directly
        jobs_list = []
        for j in jobs_data.get("jobs", [])[:4]:
            jobs_list.append({
                "title": j.get("title", ""),
                "employer": j.get("employer", ""),
                "location": j.get("location", ""),
                "why": j.get("salary", "") or "See listing for details.",
                "url": j.get("url", ""),
            })

    cards = []
    for job in jobs_list:
        title = job.get("title", "")
        employer = job.get("employer", "")
        location = job.get("location", "")
        why = job.get("why", "")
        url = job.get("url", "")
        meta = " · ".join(filter(None, [employer, location]))
        apply_btn = ""
        if url:
            apply_btn = (
                f'<p style="margin:8px 0 0;">'
                f'<a href="{url}" style="display:inline-block;padding:5px 12px;'
                f'background-color:#1b3a2d;color:#ffffff;'
                f'font-family:\'Source Sans 3\',Arial,sans-serif;font-size:12px;'
                f'font-weight:600;text-decoration:none;border-radius:4px;">Apply &#8594;</a></p>'
            )
        card = (
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
            'style="margin:0 0 10px;border:1px solid #e8e2d6;border-radius:6px;overflow:hidden;">'
            '<tr><td style="padding:12px 16px;">'
            f'<p style="margin:0 0 2px;font-family:\'Source Sans 3\',Arial,sans-serif;'
            f'font-size:14px;font-weight:700;color:#1b3a2d;">{title}</p>'
            f'<p style="margin:0 0 6px;font-family:\'Source Sans 3\',Arial,sans-serif;'
            f'font-size:12px;color:#9a8e7d;">{meta}</p>'
        )
        if why:
            card += (
                f'<p style="margin:0;font-family:\'Source Sans 3\',Arial,sans-serif;'
                f'font-size:13px;line-height:1.5;color:#333;">{why}</p>'
            )
        card += apply_btn + '</td></tr></table>'
        cards.append(card)
    return "\n".join(cards)


def _build_section_badge_html(icon_src: str, label: str, gold: bool = False) -> str:
    """Build a standard section badge (dark green or gold background)."""
    bg = "#d4a853" if gold else "#1b3a2d"
    text_col = "#1b3a2d" if gold else "#ffffff"
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">'
        '<tr>'
        f'<td style="background-color:{bg};border-radius:4px;padding:14px 20px 14px 12px;" valign="middle">'
        '<table cellpadding="0" cellspacing="0" border="0" role="presentation">'
        '<tr>'
        f'<td valign="middle" style="padding-right:8px;">'
        f'<img src="{icon_src}" width="36" height="36" alt="" style="display:block;"></td>'
        f'<td valign="middle">'
        f'<p style="margin:0;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        f'font-size:12px;font-weight:700;color:{text_col};letter-spacing:1.5px;text-transform:uppercase;">'
        f'{label}</p>'
        '</td></tr></table>'
        '</td></tr></table>'
    )


def build_regulatory_section_html(illus: dict, regulatory_html: str) -> str:
    """Build the full regulatory section HTML (with leading HR separator)."""
    badge = _build_section_badge_html(illus.get("illus_regulatory", ""), "Regulatory &amp; Health")
    return (
        SIMPLE_HR
        + '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="regulatory">'
        + '<tr><td style="padding-top:28px;"></td></tr>'
        + '<tr><td>' + badge + '</td></tr>'
        + '<tr><td style="padding-top:18px;"></td></tr>'
        + '<tr><td style="font-family:\'Source Serif 4\',\'Source Sans 3\',Georgia,serif;'
        + 'font-size:14px;line-height:1.75;color:#333333;">'
        + regulatory_html
        + '</td></tr>'
        + '</table>'
    )


def build_community_cluster_html(
    illus: dict,
    events_text_html: str,
    event_cards_html: str,
    events_present: bool,
    land_text_html: str,
    land_present: bool,
    job_cards_html: str,
    jobs_plain_text: str,
    machinery_text_html: str,
    machinery_present: bool,
    tech_watch_html: str,
) -> str:
    """Build the entire community cluster HTML with conditional sections."""

    YANA_STRIP = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
        'style="margin-top:16px;background-color:#f0f7f2;border:1px solid #d4e8d9;border-radius:6px;">'
        '<tr><td style="padding:16px 20px;">'
        '<p style="margin:0 0 4px;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:13px;font-weight:700;color:#1b3a2d;">'
        'Farming can be isolating. You don\'t have to deal with it alone.</p>'
        '<p style="margin:0;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:13px;line-height:1.6;color:#333;">'
        '<strong>YANA</strong> (You Are Not Alone) &mdash; free, confidential support for the '
        'farming community across Norfolk, Suffolk &amp; Cambridgeshire. '
        'Call <strong>0300 323 0400</strong> or visit '
        '<a href="https://www.yanahelp.org" style="color:#1b3a2d;font-weight:600;text-decoration:underline;">'
        'yanahelp.org</a></p>'
        '</td></tr></table>'
    )

    GET_FEATURED_CTA = (
        '<p style="margin:14px 0 0;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:12px;color:#8a7e6d;line-height:1.5;">'
        '<em>Running a farm walk, open day, or community event? Get it featured &mdash; '
        '<a href="mailto:hello@fieldnoteseastanglia.co.uk?subject=Event%20listing" '
        'style="color:#1b3a2d;text-decoration:underline;">email us</a>.</em></p>'
    )

    sections = []

    # Events section (conditional)
    if events_present:
        events_badge = _build_section_badge_html(illus.get("illus_events", ""), "Community &amp; Events")
        events_section = (
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="events">'
            '<tr><td style="padding-top:28px;"></td></tr>'
            '<tr><td>' + events_badge + '</td></tr>'
            '<tr><td style="padding-top:18px;"></td></tr>'
            '<tr><td style="font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
            'font-size:14px;line-height:1.7;color:#333333;">'
            + events_text_html + '</td></tr>'
            '<tr><td style="padding-top:16px;">' + event_cards_html + '</td></tr>'
            '<tr><td>' + YANA_STRIP + '</td></tr>'
            '<tr><td>' + GET_FEATURED_CTA + '</td></tr>'
            '</table>'
        )
        sections.append(events_section)

    # Land section (conditional)
    if land_present:
        land_badge = _build_section_badge_html(illus.get("illus_land", ""), "Land &amp; Property")
        land_section = (
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="land">'
            '<tr><td style="padding-top:28px;"></td></tr>'
            '<tr><td>' + land_badge + '</td></tr>'
            '<tr><td style="padding-top:18px;"></td></tr>'
            '<tr><td style="font-family:\'Source Serif 4\',\'Source Sans 3\',Georgia,serif;'
            'font-size:14px;line-height:1.75;color:#333333;">'
            + land_text_html + '</td></tr>'
            '</table>'
        )
        sections.append(land_section)

    # Jobs section (always shown)
    jobs_badge = _build_section_badge_html(illus.get("illus_jobs", ""), "Jobs &#8212; East of England")
    jobs_section = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="jobs">'
        '<tr><td style="padding-top:28px;"></td></tr>'
        '<tr><td>' + jobs_badge + '</td></tr>'
        '<tr><td style="padding-top:18px;"></td></tr>'
        '<tr><td>' + job_cards_html + '</td></tr>'
        '</table>'
    )
    sections.append(jobs_section)

    # If events were skipped, show YANA strip after jobs
    if not events_present:
        sections.append(YANA_STRIP)

    # Machinery section (conditional)
    if machinery_present:
        machinery_badge = _build_section_badge_html(illus.get("illus_machinery", ""), "Machinery &amp; Auctions")
        machinery_section = (
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="machinery">'
            '<tr><td style="padding-top:28px;"></td></tr>'
            '<tr><td>' + machinery_badge + '</td></tr>'
            '<tr><td style="padding-top:18px;"></td></tr>'
            '<tr><td style="font-family:\'Source Serif 4\',\'Source Sans 3\',Georgia,serif;'
            'font-size:14px;line-height:1.75;color:#333333;">'
            + machinery_text_html + '</td></tr>'
            '</table>'
        )
        sections.append(machinery_section)

    # Tech Watch section (always shown) — with Editor's Pick label
    tech_watch_badge = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">'
        '<tr>'
        '<td style="background-color:#1b3a2d;border-radius:4px;padding:10px 20px 14px 12px;" valign="middle">'
        '<p style="margin:0 0 4px;font-family:\'Source Sans 3\',Arial,sans-serif;font-size:10px;'
        'font-weight:700;color:#d4a853;letter-spacing:1.5px;text-transform:uppercase;">Editor\'s Pick</p>'
        '<table cellpadding="0" cellspacing="0" border="0" role="presentation">'
        '<tr>'
        '<td valign="middle" style="padding-right:8px;">'
        '<img src="' + illus.get("illus_tech_watch", "") + '" width="36" height="36" alt="" style="display:block;"></td>'
        '<td valign="middle">'
        '<p style="margin:0;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:12px;font-weight:700;color:#ffffff;letter-spacing:1.5px;text-transform:uppercase;">'
        'Tech Watch</p>'
        '</td></tr></table>'
        '</td></tr></table>'
    )
    tech_watch_section = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" id="tech-watch">'
        '<tr><td style="padding-top:28px;"></td></tr>'
        '<tr><td>' + tech_watch_badge + '</td></tr>'
        '<tr><td style="padding-top:18px;"></td></tr>'
        '<tr><td style="font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:14px;line-height:1.7;color:#333333;">'
        + tech_watch_html + '</td></tr>'
        '</table>'
    )
    sections.append(tech_watch_section)

    # Join with simple HR dividers
    result = ""
    for i, section in enumerate(sections):
        if i > 0:
            result += SIMPLE_HR
        result += section

    return result


def build_price_table_plain(rows: list[dict], unit_label: str = "£/t") -> str:
    """Build a plain-text price table."""
    if not rows:
        return ""
    lines = [
        f"{'Commodity':<25} {'This Week':>12} {'Last Week':>12} {'Change':>10}",
        "-" * 62,
    ]
    for row in rows:
        name = (row.get("commodity") or row.get("product", ""))[:24]
        price = row.get("spot_price") or row.get("price")
        prev = row.get("prev_week_price") or row.get("prev_month_price")
        change = row.get("change")
        price_str = f"£{price:.2f}" if price is not None else "—"
        prev_str = f"£{prev:.2f}" if prev is not None else "—"
        change_str = _change_str(change)
        lines.append(f"{name:<25} {price_str:>12} {prev_str:>12} {change_str:>10}")
    return "\n".join(lines)


def build_weather_table_html(days: list[dict]) -> str:
    if not days:
        return ""
    html = (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" '
        'style="border-collapse:collapse;font-family:\'Source Sans 3\',Arial,Helvetica,sans-serif;'
        'font-size:12px;border:1px solid #e8e2d6;border-radius:6px;overflow:hidden;">'
        '<thead><tr style="background-color:#1b3a2d;">'
        '<th style="text-align:left;padding:8px 12px;color:#ffffff;font-weight:600;font-size:10px;letter-spacing:0.5px;text-transform:uppercase;">Day</th>'
        '<th style="text-align:left;padding:8px 12px;color:#ffffff;font-weight:600;font-size:10px;letter-spacing:0.5px;text-transform:uppercase;">Conditions</th>'
        '<th style="text-align:right;padding:8px 12px;color:#ffffff;font-weight:600;font-size:10px;letter-spacing:0.5px;text-transform:uppercase;">Max &#176;C</th>'
        '<th style="text-align:right;padding:8px 12px;color:#ffffff;font-weight:600;font-size:10px;letter-spacing:0.5px;text-transform:uppercase;">Wind</th>'
        '<th style="text-align:right;padding:8px 12px;color:#ffffff;font-weight:600;font-size:10px;letter-spacing:0.5px;text-transform:uppercase;">Rain</th>'
        '</tr></thead><tbody>'
    )
    for i, day in enumerate(days[:7]):
        rain_pct = day.get("precip_probability_pct")
        is_last = i == len(days[:7]) - 1
        border = "" if is_last else "border-bottom:1px solid #eee8e0;"

        # Color-code by rain probability
        try:
            rain_val = float(rain_pct) if rain_pct is not None else 50
        except (ValueError, TypeError):
            rain_val = 50

        if rain_val < 30:
            bg = "#f0f7f2"
            day_colour = "#2e7d32"
            rain_colour = "#2e7d32"
        elif rain_val >= 60:
            bg = "#fdf2f2"
            day_colour = "#c62828"
            rain_colour = "#c62828"
        else:
            bg = "#fdf8ee"
            day_colour = "#d4a853"
            rain_colour = "#d4a853"

        day_name = day.get("day_of_week", "")[:3]
        desc = day.get("weather_description", "")
        max_t = day.get("max_temp_c", "&#8212;")
        wind = day.get("wind_speed_mph", "&#8212;")
        rain_display = f"{rain_pct}%" if rain_pct is not None else "&#8212;"

        html += (
            f'<tr style="background-color:{bg};">'
            f'<td style="{border}padding:8px 12px;color:{day_colour};font-weight:700;">{day_name}</td>'
            f'<td style="{border}padding:8px 12px;color:#555;">{desc}</td>'
            f'<td style="text-align:right;{border}padding:8px 12px;">{max_t}</td>'
            f'<td style="text-align:right;{border}padding:8px 12px;">{wind}mph</td>'
            f'<td style="text-align:right;{border}padding:8px 12px;color:{rain_colour};font-weight:600;">{rain_display}</td>'
            f'</tr>'
        )
    html += "</tbody></table>"
    return html


def build_weather_table_plain(days: list[dict]) -> str:
    if not days:
        return ""
    lines = [f"{'Day':<10} {'Conditions':<20} {'Max°C':>6} {'Wind mph':>10} {'Rain%':>6}", "-" * 56]
    for day in days[:7]:
        lines.append(
            f"{day.get('day_of_week','')[:3]:<10} "
            f"{day.get('weather_description','')[:19]:<20} "
            f"{day.get('max_temp_c','—'):>6} "
            f"{day.get('wind_speed_mph','—'):>10} "
            f"{day.get('precip_probability_pct','—'):>5}%"
        )
    return "\n".join(lines)



def _apply_inline_md(text: str) -> str:
    """Convert markdown inline syntax to HTML tags."""
    # Markdown links: [text](url) → <a href="url">text</a>
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        r'<a href="\2" style="color:#1b3a2d;text-decoration:underline;">\1</a>',
        text,
    )
    # Bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\s][^*]*?)\*', r'<em>\1</em>', text)
    return text


def text_to_html(text: str) -> str:
    """Convert plain-text AI output to basic HTML (bullet points, paragraphs)."""
    lines = text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Do not close the list on blank lines — only on real non-bullet content.
            # This groups consecutive bullets even when the AI inserts blank lines between them.
            html_lines.append("")
            continue

        # Heading: ## or ### → bold dark-green paragraph
        if re.match(r'^#+\s', stripped):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            heading_text = re.sub(r'^#+\s+', '', stripped)
            html_lines.append(
                f'<p style="margin:12px 0 4px;font-weight:700;color:#1b3a2d;">'
                f'{_apply_inline_md(heading_text)}</p>'
            )
            continue

        # Bullet: •, –, -, or * (but not **)
        if re.match(r'^([•\-–]|\*(?!\*))\s', stripped):
            if not in_list:
                html_lines.append('<ul style="margin:8px 0;padding-left:20px;">')
                in_list = True
            content = re.sub(r'^([•\-–]|\*(?!\*))\s+', '', stripped)
            html_lines.append(f'<li style="margin-bottom:6px;">{_apply_inline_md(content)}</li>')
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<p style="margin:0 0 10px;">{_apply_inline_md(stripped)}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


# ──────────────────────────────────────────────
# Main assembly
# ──────────────────────────────────────────────

def generate_newsletter() -> tuple[str, str]:
    today = date.today()
    date_display = today.strftime("%-d %B %Y")
    date_slug = today.strftime("%Y_%m_%d")

    issue_number = _get_next_issue_number()
    logger.info("Generating newsletter for %s (Issue #%d)", date_display, issue_number)

    # Tech Watch — manually curated weekly item, no AI call
    tech_watch_data = load_json("tech_watch.json")
    if tech_watch_data and not tech_watch_data.get("error"):
        tw_headline = tech_watch_data.get("headline", "")
        tw_body = tech_watch_data.get("body", "")
        tw_url = tech_watch_data.get("url", "")
        tw_source = tech_watch_data.get("source", "")
        tech_watch_html = (
            f'<p style="margin:0 0 6px;font-weight:700;color:#1b3a2d;">{tw_headline}</p>'
            f'<p style="margin:0 0 8px;">{tw_body}</p>'
        )
        if tw_url:
            tech_watch_html += (
                f'<p style="margin:0;">'
                f'<a href="{tw_url}" style="color:#1b3a2d;font-weight:600;text-decoration:underline;">'
                f'{tw_source or tw_url} &#8594;</a></p>'
            )
        tech_watch_plain = f"{tw_headline}\n\n{tw_body}"
        if tw_url:
            tech_watch_plain += f"\n\n{tw_source}: {tw_url}"
    else:
        tech_watch_html = "<p><em>No Tech Watch item this week.</em></p>"
        tech_watch_plain = "No Tech Watch item this week."

    # From the Soil — rotating library, no AI call
    soil_items = load_json("from_the_soil.json")
    if isinstance(soil_items, list) and soil_items:
        from_the_soil_text = soil_items[issue_number % len(soil_items)]["text"]
    else:
        from_the_soil_text = ""

    # Load all data
    grain = load_json("ahdb_grain.json")
    fertiliser = load_json("ahdb_fertiliser.json")
    livestock = load_json("ahdb_livestock.json")
    norwich_market = load_json("norwich_livestock.json")
    feed = load_json("ahdb_feed.json")
    defra = load_json("defra_blog.json")
    schemes = load_json("govuk_schemes.json")
    weather = load_json("met_office.json")
    land = load_json("land_listings.json")
    jobs = load_json("jobs.json")
    machinery = load_json("machinery_auctions.json")
    # News: prefer filtered output from prefilter.py; fall back to legacy local_news.json
    _news_filtered = load_filtered("news")
    if _news_filtered:
        news = {
            "articles": _news_filtered,
            "sources": list(dict.fromkeys(a.get("source", "") for a in _news_filtered)),
            "count": len(_news_filtered),
        }
    else:
        news = load_json("local_news.json")

    # Events: prefer filtered output; fall back to legacy events.json
    _ev_attend = load_filtered("events_attend")
    _ev_online = load_filtered("events_online")
    if _ev_attend or _ev_online:
        _combined = sorted(
            _ev_attend + _ev_online,
            key=lambda e: e.get("date_start") or "9999",
        )
        events = {"events": _combined, "count": len(_combined), "sources": []}
    else:
        events = load_json("events.json")
    community_events_raw = load_json("community_events.json")
    sugar_beet = load_json("sugar_beet.json")
    fuel = load_json("fuel.json")
    ea_alerts = load_json("ea_alerts.json")
    community_events = community_events_raw if isinstance(community_events_raw, list) else []

    # Combined data for cross-section prompts (At a Glance needs all sectors)
    all_news = {
        "defra_blog": defra,
        "local_news": news,
        "govuk_schemes": schemes,
        "grain": grain,
        "livestock": livestock,
        "weather": weather,
        "machinery": machinery,
    }
    costs_data = {"fertiliser": fertiliser, "feed": feed}
    first_grain = grain.get("prices", [{}])[0] if grain.get("prices") else {}
    margin_data = {
        "wheat_price": first_grain.get("spot_price"),
        "wheat_change": first_grain.get("change"),
        "wheat_change_pct": first_grain.get("change_pct"),
        "fertiliser": fertiliser,
    }
    regulatory_data = {"defra_blog": defra, "local_news": news}

    # Generate AI summaries
    logger.info("Generating AI summaries...")
    at_a_glance_text = get_ai_summary("at_a_glance", all_news)

    # Sugar beet: include as extra context for markets when updated within 14 days
    markets_extra = ""
    if sugar_beet and not sugar_beet.get("error"):
        try:
            sb_updated = datetime.fromisoformat(sugar_beet.get("last_updated", "2000-01-01"))
            if (datetime.now() - sb_updated).days <= 14:
                markets_extra = (
                    "\n\nSugar beet data (include if noteworthy):\n"
                    + json.dumps(sugar_beet, indent=2)
                )
        except Exception:
            pass
    markets_text = get_ai_summary("markets", grain, extra_context=markets_extra)

    # Red diesel: include as extra context for costs when data file is present
    costs_extra = ""
    if fuel and not fuel.get("error"):
        costs_extra = "\n\nRed diesel price data:\n" + json.dumps(fuel, indent=2)
    costs_text = get_ai_summary("costs", costs_data, extra_context=costs_extra)
    margin_text = get_ai_summary("margin_watch", margin_data)
    livestock_text = get_ai_summary("livestock", {"ahdb": livestock, "norwich_market": norwich_market})
    schemes_text = get_ai_summary("schemes_grants", {"schemes": schemes, "defra_blog": defra})
    # EA flood/drought alerts: include as extra context when active alerts exist
    weather_extra = ""
    if ea_alerts and not ea_alerts.get("error") and ea_alerts.get("alerts"):
        weather_extra = (
            "\n\nEnvironment Agency flood/drought alerts for East Anglia:\n"
            + json.dumps(ea_alerts["alerts"], indent=2)
        )
    weather_text = get_ai_summary("weather", weather, extra_context=weather_extra)
    land_text = get_ai_summary("land_property", land)
    jobs_text = get_ai_summary("jobs", jobs)  # returns JSON array
    machinery_text = get_ai_summary("machinery", machinery)
    regulatory_text = get_ai_summary("regulatory", regulatory_data)
    events_text = get_ai_summary("events", {
        "events_attend": _ev_attend or events.get("events", []),
        "events_online": _ev_online,
        "community_events": community_events,
    })
    read_text = get_ai_summary(
        "one_good_read", news,
        extra_context=f"The At a Glance section this week covered:\n{at_a_glance_text}\n\n",
    )

    # Build This Week hooks (14th AI call — short)
    this_week_hooks = build_this_week_hooks(at_a_glance_text)

    # Build Fieldwork Verdict (15th AI call — short)
    fieldwork_dict = build_fieldwork_verdict(weather)

    # Compute margin watch traffic light colour
    wheat_price = first_grain.get("spot_price", 0) or 0
    if wheat_price > 180:
        margin_dot_color = "#2e7d32"
    elif wheat_price >= 160:
        margin_dot_color = "#d4a853"
    else:
        margin_dot_color = "#c62828"

    # Reading time (hardcoded — shorter newsletter after trim)
    reading_time = "3"

    # Subscribe URL
    subscribe_url = "https://fieldnoteseastanglia.co.uk"

    # Build price tables
    grain_prices = grain.get("prices", [])
    fertiliser_prices = fertiliser.get("prices", [])
    weather_days = weather.get("days", [])

    price_table_grain_html = build_price_table_html(grain_prices, "t")
    price_table_fertiliser_html = build_price_table_html(fertiliser_prices, "t")
    price_table_livestock_html = build_price_table_livestock_html(livestock)
    norwich_market_html = build_norwich_market_html(norwich_market)
    weather_table_html = build_weather_table_html(weather_days)

    price_table_grain_plain = build_price_table_plain(grain_prices, "t")
    price_table_fertiliser_plain = build_price_table_plain(fertiliser_prices, "t")
    weather_table_plain = build_weather_table_plain(weather_days)

    all_events_list = events.get("events", []) + community_events
    event_cards_html = build_event_cards_html(all_events_list)

    # Preview text (from at_a_glance, strip bullets)
    preview_lines = [l.strip().lstrip("•").strip() for l in at_a_glance_text.split("\n") if l.strip()]
    preview_text = preview_lines[0][:80] if preview_lines else f"East Anglia farming briefing — {date_display}"

    unsubscribe_url = "{{unsubscribe_url}}"  # Resend fills this at send time

    # Build illustrations dict
    illustrations = _load_illustrations()

    # ── Conditional sections ──
    # Regulatory
    if section_has_content("regulatory", regulatory_text, regulatory_data):
        section_regulatory = build_regulatory_section_html(
            illustrations, text_to_html(regulatory_text)
        )
    else:
        section_regulatory = ""

    # Community cluster conditional flags
    events_combined_data = {"events": events.get("events", []), "community_events": community_events}
    events_present = section_has_content("events", events_text, events_combined_data)
    land_present = section_has_content("land", land_text, land)
    machinery_present = section_has_content("machinery", machinery_text, machinery)

    # Job cards HTML (parsed from JSON AI output)
    job_cards_html = build_job_cards_html(jobs_text, jobs)

    # Plain text jobs (best-effort conversion from JSON)
    try:
        jobs_parsed = json.loads(jobs_text)
        if not isinstance(jobs_parsed, list):
            raise ValueError("not a list")
        jobs_plain_lines = []
        for j in jobs_parsed:
            parts = [f"* {j.get('title','')} at {j.get('employer','')} ({j.get('location','')})"]
            if j.get("why"):
                parts.append(f"  {j['why']}")
            if j.get("url"):
                parts.append(f"  Apply: {j['url']}")
            jobs_plain_lines.append("\n".join(parts))
        jobs_plain = "\n\n".join(jobs_plain_lines)
    except (json.JSONDecodeError, ValueError, AttributeError):
        jobs_plain = jobs_text

    # Community cluster HTML
    community_cluster_html = build_community_cluster_html(
        illus=illustrations,
        events_text_html=text_to_html(events_text),
        event_cards_html=event_cards_html,
        events_present=events_present,
        land_text_html=text_to_html(land_text),
        land_present=land_present,
        job_cards_html=job_cards_html,
        jobs_plain_text=jobs_plain,
        machinery_text_html=text_to_html(machinery_text),
        machinery_present=machinery_present,
        tech_watch_html=tech_watch_html,
    )

    # Plain text regulatory (empty string if skipped)
    regulatory_plain = regulatory_text if section_has_content("regulatory", regulatory_text, regulatory_data) else ""

    # ── HTML VERSION ──
    html_template = (TEMPLATE_DIR / "template.html").read_text()
    html_vars = {
        "date_display": date_display,
        "issue_number": str(issue_number),
        "reading_time": reading_time,
        "preview_text": preview_text,
        "this_week_hooks": this_week_hooks,
        "subscribe_url": subscribe_url,
        "at_a_glance": text_to_html(at_a_glance_text),
        "fieldwork_verdict": fieldwork_dict["fieldwork_verdict"],
        "verdict_bg_color": fieldwork_dict["verdict_bg_color"],
        "verdict_border_color": fieldwork_dict["verdict_border_color"],
        "verdict_label_color": fieldwork_dict["verdict_label_color"],
        "weather_summary": text_to_html(weather_text),
        "weather_table": weather_table_html,
        "markets_summary": text_to_html(markets_text),
        "price_table_grain": price_table_grain_html,
        "costs_summary": text_to_html(costs_text),
        "price_table_fertiliser": price_table_fertiliser_html,
        "margin_watch": text_to_html(margin_text),
        "margin_dot_color": margin_dot_color,
        "livestock_summary": text_to_html(livestock_text),
        "price_table_livestock": price_table_livestock_html,
        "norwich_market": norwich_market_html,
        "from_the_soil": from_the_soil_text,
        "schemes_grants": text_to_html(schemes_text),
        "section_regulatory": section_regulatory,
        "community_cluster_html": community_cluster_html,
        "one_good_read": text_to_html(read_text),
        "unsubscribe_url": unsubscribe_url,
        **illustrations,
    }
    html_output = Template(html_template).safe_substitute(html_vars)

    # ── Gmail size guard ──
    GMAIL_CLIP_LIMIT = 102_400
    html_size = len(html_output.encode("utf-8"))
    if html_size > GMAIL_CLIP_LIMIT:
        logger.error(
            "GMAIL CLIPPING RISK: output is %d bytes (%d over limit). Reduce content.",
            html_size, html_size - GMAIL_CLIP_LIMIT,
        )
    elif html_size > int(GMAIL_CLIP_LIMIT * 0.85):
        logger.warning(
            "Gmail size warning: %d bytes (%.0f%% of clip limit). Getting close.",
            html_size, html_size / GMAIL_CLIP_LIMIT * 100,
        )
    else:
        logger.info("Email size: %d bytes (%.0f%% of Gmail limit)", html_size, html_size / GMAIL_CLIP_LIMIT * 100)

    # ── PLAIN TEXT VERSION ──
    plain_template = (TEMPLATE_DIR / "template_plain.txt").read_text()
    plain_vars = {
        "date_display": date_display,
        "preview_text": preview_text,
        "this_week_hooks": this_week_hooks,
        "fieldwork_verdict": fieldwork_dict["fieldwork_verdict"],
        "at_a_glance": at_a_glance_text,
        "weather_summary": weather_text,
        "weather_table_plain": weather_table_plain,
        "markets_summary": markets_text,
        "price_table_grain_plain": price_table_grain_plain,
        "costs_summary": costs_text,
        "price_table_fertiliser_plain": price_table_fertiliser_plain,
        "margin_watch": margin_text,
        "livestock_summary": livestock_text,
        "from_the_soil": from_the_soil_text,
        "schemes_grants": schemes_text,
        "regulatory": regulatory_plain,
        "events": events_text if events_present else "",
        "land_property": land_text if land_present else "",
        "jobs": jobs_plain,
        "machinery": machinery_text if machinery_present else "",
        "tech_watch": tech_watch_plain,
        "one_good_read": read_text,
        "subscribe_url": subscribe_url,
        "unsubscribe_url": unsubscribe_url,
    }
    plain_output = Template(plain_template).safe_substitute(plain_vars)

    # Save outputs
    html_path = OUTPUT_DIR / f"field_notes_{date_slug}.html"
    plain_path = OUTPUT_DIR / f"field_notes_{date_slug}.txt"
    html_path.write_text(html_output)
    plain_path.write_text(plain_output)

    logger.info("Newsletter saved: %s", html_path)
    logger.info("Plain text saved: %s", plain_path)

    return html_output, plain_output


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)
    html, plain = generate_newsletter()
    print(f"Generated successfully. Output in newsletter/output/")
    print(f"HTML length: {len(html):,} chars | Plain text: {len(plain):,} chars")
