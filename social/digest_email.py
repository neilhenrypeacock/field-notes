"""
digest_email.py — Send a plain-text digest of queued posts via SMTP.
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import List

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("field_notes.social.digest_email")


def _build_body(queued: List[dict]) -> str:
    """
    queued is a list of dicts:
      {post_text, scheduled_at_str, source, url, headline}
    """
    n = len(queued)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"Posts queued: {n}",
        f"Generated: {now_str}",
        "",
    ]
    for i, item in enumerate(queued, 1):
        lines += [
            "---",
            f"POST {i} — {item.get('scheduled_at_str', 'TBC')}",
            f"Source: {item.get('source', '')}",
            "",
            item.get("post_text", ""),
            item.get("url", ""),
            "",
        ]
    lines += [
        "---",
        "Field Notes: East Anglia — social pipeline",
        "fieldnoteseastanglia.co.uk",
    ]
    return "\n".join(lines)


def send_digest(queued: List[dict], dry_run: bool = False) -> bool:
    """
    Send a digest email listing all queued posts.

    Args:
        queued:  List of queued post dicts (post_text, scheduled_at_str, source, url).
        dry_run: If True, print the email to stdout instead of sending.

    Returns:
        True if sent (or dry-run), False on error.
    """
    n = len(queued)
    subject = f"Field Notes: East Anglia \u2014 {n} post{'s' if n != 1 else ''} queued"
    body = _build_body(queued)

    if dry_run:
        print("\n" + "=" * 60)
        print(f"DIGEST EMAIL (dry-run)")
        print(f"Subject: {subject}")
        print("=" * 60)
        print(body)
        print("=" * 60 + "\n")
        return True

    to_addr = os.environ.get("DIGEST_EMAIL", "")
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_addr = smtp_user or "hello@fieldnoteseastanglia.co.uk"

    if not to_addr or not smtp_host:
        logger.error("DIGEST_EMAIL or SMTP_HOST not set — skipping digest email")
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"Field Notes <{from_addr}>"
    msg["To"] = to_addr

    try:
        # Port 465 = SSL, port 587 = STARTTLS (default)
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_addr], msg.as_string())
        logger.info("Digest email sent to %s (%d posts)", to_addr, n)
        return True
    except Exception as exc:
        logger.error("Failed to send digest email: %s", exc)
        return False
