"""
facebook_client.py — Post to a Facebook Page using Graph API v18.0.

Reads FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID from .env.
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

logger = logging.getLogger("field_notes.social.facebook_client")


def post_to_facebook(message: str) -> dict:
    """
    Publish a text post to the configured Facebook Page.

    Args:
        message: The full text of the post to publish.

    Returns:
        {
            "post_id": str,
            "url": str,   # https://www.facebook.com/{post_id}
        }

    Raises:
        EnvironmentError: If required env vars are missing.
        requests.HTTPError: If the Graph API returns an error response.
        RuntimeError: If the response is missing the expected post ID.
    """
    access_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.environ.get("FACEBOOK_PAGE_ID", "").strip()

    if not access_token:
        raise EnvironmentError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not set. "
            "Generate a Page Access Token at developers.facebook.com/tools/explorer"
        )
    if not page_id:
        raise EnvironmentError(
            "FACEBOOK_PAGE_ID is not set. "
            "Find your Page ID in Facebook Page Settings."
        )

    endpoint = f"{GRAPH_API_BASE}/{page_id}/feed"
    payload = {
        "message": message,
        "access_token": access_token,
    }

    logger.info("Posting to Facebook Page %s (message length=%d)", page_id, len(message))

    try:
        resp = requests.post(endpoint, data=payload, timeout=15)
    except requests.RequestException as exc:
        raise requests.RequestException(f"Network error calling Facebook Graph API: {exc}") from exc

    if not resp.ok:
        # Surface the Graph API error detail when available
        try:
            error_detail = resp.json().get("error", {})
            msg = error_detail.get("message", resp.text)
            code = error_detail.get("code", resp.status_code)
        except Exception:
            msg = resp.text
            code = resp.status_code
        raise requests.HTTPError(
            f"Facebook Graph API error {code}: {msg}",
            response=resp,
        )

    data = resp.json()
    post_id = data.get("id")
    if not post_id:
        raise RuntimeError(
            f"Facebook Graph API returned no post ID. Full response: {data}"
        )

    post_url = f"https://www.facebook.com/{post_id}"
    logger.info("Published to Facebook: post_id=%s url=%s", post_id, post_url)

    return {
        "post_id": post_id,
        "url": post_url,
    }
