"""
social/config.py
================
Shared settings used across all social scripts.
Edit this file to change the weekly schedule, posting times,
or any global behaviour. No need to touch the other scripts.
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────

BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
PROMPT_FILE     = DATA_DIR / "post_prompt.txt"
PROMPT_DRAFT    = DATA_DIR / "post_prompt_draft.txt"
PROMPT_HISTORY  = DATA_DIR / "prompt_history"
COMMENTS_FILE   = DATA_DIR / "first_comments.json"
GROUPS_FILE     = DATA_DIR / "facebook_groups.json"
VALIDATION_FILE = DATA_DIR / "validation_config.json"
SCHEDULED_FILE  = DATA_DIR / "scheduled_posts.json"
POST_HISTORY    = DATA_DIR / "post_history"

# Path to the main project (scrapers live here)
PROJECT_ROOT = Path("/Users/neilpeacock/Projects/fieldnotes")
SCRAPERS_DIR = PROJECT_ROOT / "scrapers"  # Reserved for future use

# ── Weekly posting schedule ────────────────────────────────────────────────
# Each entry maps a day + time to a newsletter section.
# 'monday_newsletter' is a special type — uses the Monday template.
# Times are 24hr format, UK local time (GMT/BST — cron handles this).

WEEKLY_SCHEDULE = [
    {
        "day":     "Monday",
        "time":    "07:00",
        "section": "monday_newsletter",
        "label":   "Newsletter launch post"
    },
    {
        "day":     "Tuesday",
        "time":    "07:00",
        "section": "markets",
        "label":   "Grain & commodity prices"
    },
    {
        "day":     "Wednesday",
        "time":    "19:00",
        "section": "schemes",
        "label":   "Schemes & grants"
    },
    {
        "day":     "Thursday",
        "time":    "07:00",
        "section": "inputs",
        "label":   "Input costs"
    },
    {
        "day":     "Friday",
        "time":    "07:00",
        "section": "news",
        "label":   "Farming news & regulatory"
    },
    {
        "day":     "Saturday",
        "time":    "08:00",
        "section": "land_jobs_machinery",
        "label":   "Land, jobs or machinery"
    },
]

# ── Facebook API ───────────────────────────────────────────────────────────

FB_PAGE_ID           = os.getenv("FACEBOOK_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FB_API_VERSION       = "v19.0"
FB_API_BASE          = f"https://graph.facebook.com/{FB_API_VERSION}"

# ── Newsletter ─────────────────────────────────────────────────────────────

NEWSLETTER_URL       = "fieldnoteseastanglia.co.uk"
DRAFT_EMAIL          = os.getenv("DRAFT_EMAIL", "neil@neilpeacock.co.uk")
NOTIFICATION_EMAIL   = "neil@neilpeacock.co.uk"

# ── Anthropic API ──────────────────────────────────────────────────────────

ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL         = "claude-sonnet-4-20250514"
MAX_TOKENS_POST      = 600
MAX_TOKENS_VERIFY    = 400
MAX_TOKENS_RESEARCH  = 2000

# ── Verification thresholds ────────────────────────────────────────────────

# Gate 2: if Claude returns LOW confidence, flag the post (don't block)
# Gate 2: number mismatches flag only — Gate 2 never blocks a post automatically.
# Gate 2 can only flag for human review. The human makes the final call.
BLOCK_ON_NUMBER_MISMATCH = False
FLAG_ON_LOW_CONFIDENCE   = True
GATE2_BLOCKS_POST        = False   # set True only if you want Gate 2 to hard-block

# ── Prompt updater ─────────────────────────────────────────────────────────

# How different does the new prompt need to be before we propose an update?
# 0.0 = propose any change / 1.0 = never propose changes
PROMPT_CHANGE_THRESHOLD = 0.1

# How many weeks of research to keep in prompt history
PROMPT_HISTORY_WEEKS = 12

# ── Growth settings ────────────────────────────────────────────────────────

# Sections that qualify as "high value" for group sharing + share hooks
HIGH_VALUE_SECTIONS = ["markets", "schemes", "news", "inputs"]

# Minimum confidence level required for group auto-posting
# Options: "HIGH", "MEDIUM", "LOW"
GROUP_POST_MIN_CONFIDENCE = "HIGH"

# Delay between group posts to avoid Facebook rate limiting
GROUP_POST_DELAY_SECONDS = 30

# ── Organisations to tag by section ───────────────────────────────────────

SECTION_TAGS = {
    "markets":   "@AHDBcereals",
    "inputs":    "@AHDB",
    "schemes":   "@DefraGovUK",
    "news":      "@DefraGovUK",
    "land":      "",
    "jobs":      "@FarmersWeekly",
    "machinery": "",
    "livestock": "@AHDB",
}

# ── Section to hashtag mapping ─────────────────────────────────────────────

SECTION_HASHTAGS = {
    "markets":            "#GrainMarkets",
    "inputs":             "#InputCosts",
    "schemes":            "#FarmingSchemes",
    "news":               "#FarmPolicy",
    "land":               "#FarmlandUK",
    "jobs":               "#FarmPolicy",
    "machinery":          "#FarmlandUK",
    "livestock":          "#Livestock",
    "monday_newsletter":  "#Farming",
    "land_jobs_machinery":"#FarmlandUK",
}
