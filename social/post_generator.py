"""
post_generator.py — Generate a Facebook post from a raw news item via Claude API.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs" / "ai_usage.json"

AI_MODEL = "claude-haiku-4-5"
AI_MAX_TOKENS = 200

PROMPT_TEMPLATE = """\
You are writing a short Facebook post for Field Notes: East Anglia, \
a free weekly intelligence briefing for farmers in Norfolk, Suffolk \
and Cambridgeshire.

The audience is professional farmers and land managers. Tone: direct, \
factual, no fluff. Lead with the most important number or fact. \
2-3 sentences maximum. End with the source URL. Maximum 2 hashtags: \
#EastAnglia and one relevant topic tag.

Here is the raw news item:
[HEADLINE]: {headline}
[SUMMARY]: {summary}
[SOURCE]: {url}

Write the Facebook post now. No preamble, just the post.\
"""

logger = logging.getLogger("field_notes.social.post_generator")


def _log_usage(input_tokens: int, output_tokens: int) -> None:
    record = {
        "section": "social_post",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    existing = []
    if LOG_FILE.exists():
        try:
            existing = json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    existing.append(record)
    LOG_FILE.write_text(json.dumps(existing[-200:], indent=2))


def generate_post(headline: str, summary: str, url: str) -> Optional[str]:
    """
    Call Claude to write a Facebook post for the given item.
    Returns the post text, or None if the API call fails.
    """
    prompt = PROMPT_TEMPLATE.format(headline=headline, summary=summary, url=url)

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        _log_usage(message.usage.input_tokens, message.usage.output_tokens)
        logger.info(
            "Generated post (%d out tokens) for: %s",
            message.usage.output_tokens,
            headline[:60],
        )
        return text
    except anthropic.APIError as exc:
        logger.error("Claude API error for '%s': %s", headline[:60], exc)
        return None
    except KeyError:
        logger.error("ANTHROPIC_API_KEY not set")
        return None
