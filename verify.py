"""
social/verify.py
================
Three-gate verification system for all Facebook posts.

Gate 1 — Data validation
    Checks raw scraper data before it reaches Claude.
    Validates ranges, freshness, required fields.
    Blocks bad data from ever becoming a post.

Gate 2 — AI cross-check
    After Claude writes a post, a second Claude call
    reads both the raw data and the finished post and
    checks every number, every direction, every source claim.
    Blocks posts with mismatched numbers automatically.
    Flags low-confidence posts for extra review.

Both gates write results to a VerificationResult object
that the review screen uses to display the full picture.
"""

import json
import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path("/Users/neilpeacock/farm/field-notes/.env"))

from config import (
    VALIDATION_FILE,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    MAX_TOKENS_VERIFY,
    BLOCK_ON_NUMBER_MISMATCH,
    FLAG_ON_LOW_CONFIDENCE,
)

logger = logging.getLogger(__name__)


# ── Result objects ─────────────────────────────────────────────────────────

@dataclass
class Gate1Result:
    passed: bool
    warnings: list = field(default_factory=list)   # flagged but not blocked
    errors: list   = field(default_factory=list)   # blocked
    checks: list   = field(default_factory=list)   # all checks run

    def summary(self) -> str:
        if self.passed and not self.warnings:
            return "✓ PASS — all data checks passed"
        elif self.passed and self.warnings:
            return f"⚠ PASS WITH WARNINGS — {len(self.warnings)} warning(s)"
        else:
            return f"✗ BLOCKED — {len(self.errors)} error(s)"


@dataclass
class Gate2Result:
    passed: bool
    confidence: str = "MEDIUM"          # HIGH / MEDIUM / LOW
    number_mismatch: bool = False
    direction_error: bool = False
    invented_content: bool = False
    source_accurate: bool = True
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        if self.passed and self.confidence == "HIGH":
            return "✓ PASS (HIGH confidence) — all numbers verified"
        elif self.passed and self.confidence == "MEDIUM":
            return "✓ PASS (MEDIUM confidence) — numbers correct, some context inferred"
        elif not self.passed:
            reasons = []
            if self.number_mismatch:   reasons.append("number mismatch")
            if self.direction_error:   reasons.append("wrong direction")
            if self.invented_content:  reasons.append("invented content")
            return f"✗ BLOCKED — {', '.join(reasons)}"
        else:
            return f"⚠ FLAGGED (LOW confidence) — review carefully"


@dataclass
class VerificationResult:
    gate1: Gate1Result
    gate2: Optional[Gate2Result] = None
    blocked: bool = False
    flagged: bool = False
    block_reason: str = ""

    def status_line(self) -> str:
        if self.blocked:
            return f"🔴 BLOCKED — {self.block_reason}"
        elif self.flagged:
            return "🟡 FLAGGED — review carefully before approving"
        else:
            return "🟢 READY TO SCHEDULE"


# ── Gate 1: Data validation ────────────────────────────────────────────────

def run_gate1(section: str, data: dict) -> Gate1Result:
    """
    Validate raw scraper data against plausible ranges and freshness rules.
    Returns a Gate1Result — blocked if any hard errors, warned if soft issues.
    """
    with open(VALIDATION_FILE) as f:
        config = json.load(f)

    result = Gate1Result(passed=True)

    # ── Check 1: Required fields present ──────────────────────────────────
    required = config["required_fields_by_section"].get(section, [])
    for field_name in required:
        if field_name not in data or data[field_name] is None:
            result.errors.append(
                f"Required field '{field_name}' is missing or None"
            )
            result.passed = False
        else:
            result.checks.append(f"✓ Required field '{field_name}' present")

    # ── Check 2: Price ranges ──────────────────────────────────────────────
    price_ranges = config["price_ranges"]
    for field_name, value in data.items():
        if field_name in price_ranges and value is not None:
            rule = price_ranges[field_name]
            try:
                numeric = float(str(value).replace("£", "").replace(",", "").strip())
                if numeric < rule["min"] or numeric > rule["max"]:
                    result.errors.append(
                        f"{rule['label']}: {value} {rule['unit']} is outside "
                        f"plausible range ({rule['min']}–{rule['max']} {rule['unit']}). "
                        f"This may be a scraper error — check source before overriding."
                    )
                    result.passed = False
                else:
                    result.checks.append(
                        f"✓ {rule['label']}: {value} {rule['unit']} within range"
                    )
            except (ValueError, TypeError):
                result.warnings.append(
                    f"Could not validate '{field_name}' — value '{value}' is not numeric"
                )

    # ── Check 3: Weather ranges ────────────────────────────────────────────
    weather_ranges = config["weather_ranges"]
    for field_name, value in data.items():
        if field_name in weather_ranges and value is not None:
            rule = weather_ranges[field_name]
            try:
                numeric = float(value)
                if numeric < rule["min"] or numeric > rule["max"]:
                    result.errors.append(
                        f"{rule['label']}: {value} {rule['unit']} is outside "
                        f"plausible range ({rule['min']}–{rule['max']} {rule['unit']})"
                    )
                    result.passed = False
                else:
                    result.checks.append(
                        f"✓ {rule['label']}: {value} {rule['unit']} within range"
                    )
            except (ValueError, TypeError):
                result.warnings.append(
                    f"Could not validate weather field '{field_name}'"
                )

    # ── Check 4: Data freshness ────────────────────────────────────────────
    max_age = config["staleness_rules"]["max_data_age_days"]
    if "data_date" in data and data["data_date"]:
        try:
            if isinstance(data["data_date"], str):
                data_date = datetime.fromisoformat(data["data_date"])
            else:
                data_date = data["data_date"]
            age_days = (datetime.now() - data_date).days
            if age_days > max_age:
                result.warnings.append(
                    f"Data is {age_days} days old (max recommended: {max_age} days). "
                    f"Check if a fresher source is available."
                )
            else:
                result.checks.append(f"✓ Data freshness: {age_days} day(s) old")
        except (ValueError, TypeError):
            result.warnings.append("Could not parse data_date — freshness not checked")
    else:
        result.warnings.append("No data_date provided — staleness cannot be verified")

    # ── Check 5: Empty data guard ──────────────────────────────────────────
    non_meta_keys = [k for k in data.keys()
                     if k not in ("data_date", "source", "section", "raw")]
    if not non_meta_keys:
        result.errors.append("Data object is empty — scraper may have returned nothing")
        result.passed = False
    else:
        result.checks.append(f"✓ Data object has {len(non_meta_keys)} field(s)")

    return result


# ── Gate 2: AI cross-check ─────────────────────────────────────────────────

def run_gate2(post_text: str, raw_data: dict, section: str) -> Gate2Result:
    """
    Ask Claude to verify the finished post against the raw source data.
    A second, independent Claude call — not the same one that wrote the post.
    Returns a Gate2Result with pass/fail and detailed findings.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    verification_prompt = f"""You are a data accuracy checker for a farming newsletter.

A post has been written for Facebook. Your job is to verify it against the raw source data.
Be precise and strict. Farmers make financial decisions based on these numbers.

RAW SOURCE DATA:
{json.dumps(raw_data, indent=2, default=str)}

FINISHED POST TEXT:
{post_text}

Answer each question with YES or NO, then one sentence of explanation.

1. NUMBERS_MATCH: Does every number in the post appear correctly in the source data?
2. DIRECTION_CORRECT: Are all directions (up/down/higher/lower/rising/falling) correct?
3. SOURCE_ACCURATE: Is the source attribution in the post accurate?
4. INVENTED_CONTENT: Does the post state anything not supported by the source data?
5. CONFIDENCE: Rate your overall confidence: HIGH, MEDIUM, or LOW

HIGH = every number verbatim from source, direction correct, nothing invented
MEDIUM = numbers correct but some context reasonably inferred
LOW = any uncertainty about numbers, direction, or claims

Respond in this exact format:
NUMBERS_MATCH: [YES/NO] — [explanation]
DIRECTION_CORRECT: [YES/NO] — [explanation]
SOURCE_ACCURATE: [YES/NO] — [explanation]
INVENTED_CONTENT: [YES/NO] — [explanation]
CONFIDENCE: [HIGH/MEDIUM/LOW] — [explanation]"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS_VERIFY,
            messages=[{"role": "user", "content": verification_prompt}]
        )
        reply = response.content[0].text
        return _parse_gate2_response(reply)

    except Exception as e:
        logger.error(f"Gate 2 API call failed: {e}")
        # If we can't verify, flag it — don't silently pass
        result = Gate2Result(passed=False, confidence="LOW")
        result.notes.append(f"Gate 2 API call failed: {e}. Manual review required.")
        return result


def _parse_gate2_response(reply: str) -> Gate2Result:
    """Parse Claude's structured Gate 2 response into a Gate2Result."""
    result = Gate2Result(passed=True)
    lines = reply.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("NUMBERS_MATCH:"):
            answer = "YES" in line.upper().split("—")[0]
            if not answer:
                result.number_mismatch = True
                result.notes.append(line)
                if BLOCK_ON_NUMBER_MISMATCH:
                    result.passed = False

        elif line.startswith("DIRECTION_CORRECT:"):
            answer = "YES" in line.upper().split("—")[0]
            if not answer:
                result.direction_error = True
                result.notes.append(line)
                result.passed = False

        elif line.startswith("SOURCE_ACCURATE:"):
            answer = "YES" in line.upper().split("—")[0]
            result.source_accurate = answer
            if not answer:
                result.notes.append(line)
                result.passed = False

        elif line.startswith("INVENTED_CONTENT:"):
            # YES means invented content WAS found — that's bad
            answer = "YES" in line.upper().split("—")[0]
            if answer:
                result.invented_content = True
                result.notes.append(line)
                result.passed = False

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


# ── Combined verification ──────────────────────────────────────────────────

def verify_post(section: str, raw_data: dict, post_text: str) -> VerificationResult:
    """
    Run both gates and return a combined VerificationResult.
    Used by generate_posts.py after each post is written.
    """
    # Gate 1
    gate1 = run_gate1(section, raw_data)

    if not gate1.passed:
        return VerificationResult(
            gate1=gate1,
            blocked=True,
            block_reason=f"Gate 1 failed: {'; '.join(gate1.errors)}"
        )

    # Gate 2 — only runs if Gate 1 passes
    gate2 = run_gate2(post_text, raw_data, section)

    # Strip the CONFIDENCE line from the post text before storing
    clean_post = re.sub(r'\nCONFIDENCE:.*$', '', post_text, flags=re.MULTILINE).strip()

    blocked = not gate2.passed
    flagged = gate2.confidence == "LOW" and not blocked

    block_reason = ""
    if blocked:
        reasons = []
        if gate2.number_mismatch:  reasons.append("number mismatch in post")
        if gate2.direction_error:  reasons.append("wrong direction stated")
        if gate2.invented_content: reasons.append("invented content found")
        if not gate2.source_accurate: reasons.append("source incorrectly attributed")
        block_reason = f"Gate 2 failed: {'; '.join(reasons)}"

    return VerificationResult(
        gate1=gate1,
        gate2=gate2,
        blocked=blocked,
        flagged=flagged,
        block_reason=block_reason,
    )
