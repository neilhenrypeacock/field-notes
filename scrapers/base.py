"""
Shared base module for all Field Notes scrapers.
Provides HTTP session, retry logic, JSON persistence, and Excel helpers.
"""

import json
import logging
import os
import random
import shutil
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("field_notes")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREVIOUS_DIR = DATA_DIR / "previous"

DATA_DIR.mkdir(exist_ok=True)
PREVIOUS_DIR.mkdir(exist_ok=True)

USER_AGENT = "FieldNotes/1.0 (East Anglia farming newsletter; contact@fieldnotes.co.uk)"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def get(url: str, **kwargs) -> requests.Response:
    """GET with polite delay and retry logic."""
    delay = random.uniform(1.0, 2.0)
    time.sleep(delay)

    for attempt in range(1, 4):
        try:
            response = session.get(url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == 3:
                logger.error("Failed to fetch %s after 3 attempts: %s", url, exc)
                raise
            wait = 2 ** attempt
            logger.warning("Attempt %d failed for %s: %s — retrying in %ds", attempt, url, exc, wait)
            time.sleep(wait)


def download_excel(url: str) -> BytesIO:
    """Download a binary Excel file and return as BytesIO."""
    response = get(url)
    return BytesIO(response.content)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_data(filename: str, data: dict) -> None:
    """Atomically write data to data/filename.json with last_updated timestamp."""
    data["last_updated"] = now_utc()
    target = DATA_DIR / filename
    tmp = DATA_DIR / (filename + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(target)
    logger.info("Saved %s (%d bytes)", target.name, target.stat().st_size)


def load_data(filename: str) -> dict:
    """Load data/filename.json, return {} if not found."""
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_previous(filename: str) -> dict:
    """Load data/previous/{stem}_prev.json, return {} if not found."""
    stem = Path(filename).stem
    path = PREVIOUS_DIR / f"{stem}_prev.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def archive_current(filename: str) -> None:
    """Copy data/filename.json to data/previous/{stem}_prev.json before overwriting."""
    source = DATA_DIR / filename
    if not source.exists():
        return
    stem = Path(filename).stem
    dest = PREVIOUS_DIR / f"{stem}_prev.json"
    shutil.copy2(source, dest)
    logger.info("Archived %s → %s", source.name, dest.name)
