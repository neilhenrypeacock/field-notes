"""
Newsletter sender: delivers the generated newsletter via Resend.
NEWSLETTER_ENV=draft → sends only to DRAFT_EMAIL
NEWSLETTER_ENV=live  → creates and sends a broadcast to the full audience
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import resend
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("field_notes.send")

resend.api_key = os.environ["RESEND_API_KEY"]


def _find_latest_output() -> tuple[str, str]:
    """Find the most recently generated HTML and plain text files."""
    html_files = sorted(OUTPUT_DIR.glob("field_notes_*.html"), reverse=True)
    txt_files = sorted(OUTPUT_DIR.glob("field_notes_*.txt"), reverse=True)
    if not html_files:
        raise FileNotFoundError(f"No newsletter output found in {OUTPUT_DIR}")
    html = html_files[0].read_text()
    txt = txt_files[0].read_text() if txt_files else ""
    logger.info("Using output: %s", html_files[0].name)
    return html, txt


def _build_subject(html: str) -> str:
    """Build the newsletter subject line."""
    today = date.today()
    day = today.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_str = today.strftime(f"%-d{suffix} %B %Y")
    return f"Field Notes: East Anglia — w/c {date_str}"


def send_draft(html: str, txt: str, subject: str) -> None:
    """Send to DRAFT_EMAIL only."""
    draft_email = os.environ.get("DRAFT_EMAIL")
    if not draft_email:
        raise ValueError("DRAFT_EMAIL not set in .env")

    from_email = os.getenv("FROM_EMAIL", "Field Notes <hello@fieldnotes.co.uk>")
    logger.info("Sending DRAFT to %s", draft_email)

    result = resend.Emails.send({
        "from": from_email,
        "to": [draft_email],
        "subject": f"[DRAFT] {subject}",
        "html": html,
        "text": txt,
    })
    logger.info("Draft sent. Resend ID: %s", result.get("id"))
    _log_send("draft", subject, result.get("id"), [draft_email])


def send_broadcast(html: str, txt: str, subject: str) -> None:
    """Create and send a Resend broadcast to the full audience."""
    audience_id = os.environ.get("RESEND_AUDIENCE_ID")
    if not audience_id:
        raise ValueError("RESEND_AUDIENCE_ID not set in .env")

    from_email = os.getenv("FROM_EMAIL", "Field Notes <hello@fieldnotes.co.uk>")
    logger.info("Creating broadcast to audience %s", audience_id)

    broadcast = resend.Broadcasts.create({
        "audience_id": audience_id,
        "from": from_email,
        "subject": subject,
        "html": html,
        "text": txt,
        "name": f"Field Notes {date.today().isoformat()}",
    })
    broadcast_id = broadcast.get("id")
    logger.info("Broadcast created: %s", broadcast_id)

    send_result = resend.Broadcasts.send(broadcast_id)
    logger.info("Broadcast sent: %s", send_result)
    _log_send("broadcast", subject, broadcast_id, [f"audience:{audience_id}"])


def _log_send(mode: str, subject: str, send_id: str, recipients: list) -> None:
    log_path = LOG_DIR / "send_log.json"
    record = {
        "mode": mode,
        "subject": subject,
        "id": send_id,
        "recipients": recipients,
        "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text())
        except Exception:
            pass
    existing.append(record)
    log_path.write_text(json.dumps(existing, indent=2))


def send() -> None:
    env = os.getenv("NEWSLETTER_ENV", "draft")
    html, txt = _find_latest_output()
    subject = _build_subject(html)

    logger.info("Newsletter mode: %s | Subject: %s", env.upper(), subject)

    if env == "live":
        send_broadcast(html, txt, subject)
    else:
        send_draft(html, txt, subject)


if __name__ == "__main__":
    required = ["RESEND_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)
    send()
