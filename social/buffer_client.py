"""
buffer_client.py — Queue posts to Buffer API v1 for the Facebook Page channel.

Scheduling: posts spaced 6 hours apart, starting at 09:00 UTC the next day,
capped at 20:00 UTC (next slot rolls to following day 09:00).
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

BUFFER_API_BASE = "https://api.bufferapp.com/1"

logger = logging.getLogger("field_notes.social.buffer_client")

# Slot times in UTC hours; posts are placed into the next available slot
_SLOT_HOURS = [9, 15]


def _next_slot(after: datetime) -> datetime:
    """
    Return the next available posting slot (UTC) strictly after `after`.
    Slots are at 09:00 and 15:00 UTC. If both today's slots are past,
    advance to the following day.
    """
    candidate = after.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    for _ in range(10):  # guard against infinite loop
        for hour in _SLOT_HOURS:
            slot = candidate.replace(hour=hour)
            if slot > after:
                return slot
        # Both slots for this day are past — advance to next day
        candidate = (candidate + timedelta(days=1)).replace(hour=0)
    # Fallback: tomorrow 09:00
    return (after + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)


def queue_post(
    post_text: str,
    after_dt: Optional[datetime] = None,
    dry_run: bool = False,
) -> dict:
    """
    Queue a single post to the Buffer Facebook channel.

    Args:
        post_text: The full text of the post (already generated).
        after_dt:  Schedule after this datetime (UTC). Defaults to now.
                   Pass the return value of the previous call's scheduled_at
                   to chain posts 6 hours apart.
        dry_run:   If True, compute the slot but don't call the Buffer API.

    Returns:
        {
            "success": bool,
            "update_id": str | None,
            "scheduled_at": datetime (UTC),
            "scheduled_at_str": str (ISO 8601),
        }
    """
    if after_dt is None:
        after_dt = datetime.now(timezone.utc)

    slot = _next_slot(after_dt)
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%SZ")

    if dry_run:
        logger.info("[dry-run] Would queue post at %s", slot_str)
        return {
            "success": True,
            "update_id": None,
            "scheduled_at": slot,
            "scheduled_at_str": slot_str,
        }

    access_token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    channel_id = os.environ.get("BUFFER_FACEBOOK_CHANNEL_ID", "")

    if not access_token or not channel_id:
        logger.error("BUFFER_ACCESS_TOKEN or BUFFER_FACEBOOK_CHANNEL_ID not set")
        return {
            "success": False,
            "update_id": None,
            "scheduled_at": slot,
            "scheduled_at_str": slot_str,
        }

    payload = {
        "profile_ids[]": channel_id,
        "text": post_text,
        "scheduled_at": slot_str,
        "access_token": access_token,
    }

    try:
        resp = requests.post(
            f"{BUFFER_API_BASE}/updates/create.json",
            data=payload,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        updates = result.get("updates", [])
        update_id = updates[0].get("id") if updates else result.get("id")
        logger.info("Queued to Buffer: update_id=%s at %s", update_id, slot_str)
        return {
            "success": True,
            "update_id": update_id,
            "scheduled_at": slot,
            "scheduled_at_str": slot_str,
        }
    except requests.RequestException as exc:
        logger.error("Buffer API error: %s", exc)
        return {
            "success": False,
            "update_id": None,
            "scheduled_at": slot,
            "scheduled_at_str": slot_str,
        }
