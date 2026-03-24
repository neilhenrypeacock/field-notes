"""
social/update_prompt.py
=======================
Weekly self-improvement script. Run every Sunday before generate_posts.py.

What it does:
1. Uses Claude with web_search to research:
   - Facebook algorithm changes in the last 30 days
   - What's working for UK farming/agricultural pages
   - Any changes to links, hashtags, post length best practices
   - Newsletter growth tactics for niche audiences
   - East Anglia / UK farming social media trends

2. Reads your current post_prompt.txt

3. Asks Claude to compare what it found against the current prompt
   and propose specific, justified improvements

4. If improvements are found:
   - Saves the proposed new prompt to data/post_prompt_draft.txt
   - Archives the current prompt with a datestamp
   - Prints a clear diff of what changed and why
   - Emails a summary to neil@neilpeacock.co.uk

5. If no meaningful changes needed:
   - Prints "No changes needed this week"

To approve a proposed update:
    .venv/bin/python social/update_prompt.py --approve

To reject (do nothing — post_prompt.txt stays unchanged):
    Just don't run --approve

Usage:
    .venv/bin/python social/update_prompt.py           # Research + propose
    .venv/bin/python social/update_prompt.py --approve # Apply draft to live
    .venv/bin/python social/update_prompt.py --history # Show past updates
"""

import sys
import json
import shutil
import difflib
import logging
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
load_dotenv(Path("/Users/neilpeacock/Projects/fieldnotes/.env"), override=True)

from social.config import (
    PROMPT_FILE,
    PROMPT_DRAFT,
    PROMPT_HISTORY,
    DATA_DIR,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    MAX_TOKENS_RESEARCH,
    NOTIFICATION_EMAIL,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Research prompt ────────────────────────────────────────────────────────

RESEARCH_PROMPT = """You are a social media strategist specialising in UK farming audiences.

Your job is to research current best practices for Facebook posts aimed at 
professional arable farmers in East Anglia, UK — and then review an existing 
post prompt to propose specific improvements.

STEP 1 — RESEARCH (use web search for each of these):

Search for recent information (last 60 days if possible) on:
1. Facebook algorithm changes — any updates to how reach, links, or engagement work
2. What's working for UK agricultural / farming Facebook pages right now
3. Best practices for Facebook post length, format, and structure in 2025/2026
4. Newsletter growth tactics via social media for niche/professional audiences
5. Any changes to how Facebook handles hashtags, external links, or tagging
6. UK farming social media trends — what East Anglian or British farming audiences engage with

STEP 2 — REVIEW THE EXISTING PROMPT:

Here is the current post generation prompt:

{current_prompt}

STEP 3 — PROPOSE IMPROVEMENTS:

Based on your research, identify any specific improvements to the prompt above.

Only propose changes that are:
- Supported by evidence from your research
- Meaningful (would actually change how posts are written)
- Compatible with the farming audience and newsletter-first strategy

For each proposed change, provide:
- WHAT: The specific section or rule to change
- WHY: The research finding that supports the change
- BEFORE: The current wording (quote exactly)
- AFTER: The proposed new wording

If no meaningful changes are needed, say: NO_CHANGES_NEEDED

Then provide the FULL updated prompt text (even if no changes — return the original).
Wrap the full prompt in: ---PROMPT_START--- and ---PROMPT_END---

Always update the version number and date in the VERSION HISTORY section.
Format: v[X.Y] — [date] — [brief description of changes]
"""


# ── Run research ───────────────────────────────────────────────────────────

def run_research(current_prompt: str) -> str:
    """Ask Claude to research best practices and propose prompt improvements."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    filled_prompt = RESEARCH_PROMPT.format(current_prompt=current_prompt)

    logger.info("Researching Facebook best practices (this takes ~30 seconds)...")

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS_RESEARCH,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": filled_prompt}]
    )

    # Extract text from response (may include tool use blocks)
    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text

    return full_text


# ── Extract proposed prompt ────────────────────────────────────────────────

def extract_proposed_prompt(research_output: str) -> tuple[str, bool]:
    """
    Extract the proposed new prompt from Claude's research output.
    Returns (prompt_text, changes_proposed).
    """
    if "NO_CHANGES_NEEDED" in research_output:
        # Still extract the prompt (it'll be the same as current)
        changed = False
    else:
        changed = True

    start_marker = "---PROMPT_START---"
    end_marker   = "---PROMPT_END---"

    start = research_output.find(start_marker)
    end   = research_output.find(end_marker)

    if start == -1 or end == -1:
        logger.warning("Could not find prompt markers in research output")
        return "", False

    prompt_text = research_output[start + len(start_marker):end].strip()
    return prompt_text, changed


# ── Generate diff summary ──────────────────────────────────────────────────

def generate_diff_summary(old_prompt: str, new_prompt: str) -> str:
    """Generate a human-readable summary of what changed."""
    old_lines = old_prompt.splitlines(keepends=True)
    new_lines = new_prompt.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="current prompt",
        tofile="proposed prompt",
        lineterm=""
    ))

    if not diff:
        return "No text differences found."

    # Count changes
    added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

    summary = f"Changes: {added} lines added, {removed} lines removed\n\n"
    summary += "".join(diff[:100])  # First 100 lines of diff
    if len(diff) > 100:
        summary += f"\n... and {len(diff) - 100} more diff lines"

    return summary


# ── Archive current prompt ─────────────────────────────────────────────────

def archive_current_prompt(current_prompt: str):
    """Save current prompt to history with datestamp."""
    PROMPT_HISTORY.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = PROMPT_HISTORY / f"post_prompt_{date_str}.txt"
    archive_path.write_text(current_prompt, encoding="utf-8")
    logger.info(f"Archived current prompt to {archive_path.name}")


# ── Send update email ──────────────────────────────────────────────────────

def send_update_email(research_output: str, diff_summary: str, changes_found: bool):
    """Email Neil a summary of the prompt research findings."""
    try:
        import os, requests as req
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            logger.info("No RESEND_API_KEY — skipping email notification")
            return

        if changes_found:
            subject = f"[Field Notes Social] Prompt update proposed — {datetime.now().strftime('%d %b %Y')}"
            body = (
                f"The weekly prompt research has found improvements to propose.\n\n"
                f"WHAT CHANGED:\n{diff_summary}\n\n"
                f"To apply the update, run:\n"
                f".venv/bin/python social/update_prompt.py --approve\n\n"
                f"To reject, do nothing — post_prompt.txt remains unchanged.\n\n"
                f"FULL RESEARCH OUTPUT:\n{research_output[:3000]}"
            )
        else:
            subject = f"[Field Notes Social] Prompt check — no changes needed — {datetime.now().strftime('%d %b %Y')}"
            body = (
                f"The weekly prompt research found no meaningful improvements needed.\n\n"
                f"Current prompt is up to date.\n\n"
                f"Research summary:\n{research_output[:2000]}"
            )

        req.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from":    "Field Notes Bot <hello@fieldnoteseastanglia.co.uk>",
                "to":      [NOTIFICATION_EMAIL],
                "subject": subject,
                "text":    body,
            },
            timeout=10
        )
        logger.info(f"Research summary emailed to {NOTIFICATION_EMAIL}")
    except Exception as e:
        logger.warning(f"Could not send research email: {e}")


# ── Show history ───────────────────────────────────────────────────────────

def show_history():
    """Print a list of all archived prompts."""
    PROMPT_HISTORY.mkdir(exist_ok=True)
    archives = sorted(PROMPT_HISTORY.glob("post_prompt_*.txt"), reverse=True)

    if not archives:
        print("No prompt history found.")
        return

    print(f"\nPrompt history ({len(archives)} versions):\n")
    for path in archives:
        size = path.stat().st_size
        print(f"  {path.name}  ({size} bytes)")
    print(f"\nTo view one: cat social/data/prompt_history/[filename]\n")


# ── Approve draft ──────────────────────────────────────────────────────────

def approve_draft():
    """Apply the draft prompt to the live prompt file."""
    if not PROMPT_DRAFT.exists():
        print("No draft prompt found. Run update_prompt.py first.\n")
        sys.exit(1)

    current = PROMPT_FILE.read_text(encoding="utf-8")
    draft   = PROMPT_DRAFT.read_text(encoding="utf-8")

    # Archive current before overwriting
    archive_current_prompt(current)

    # Apply
    PROMPT_FILE.write_text(draft, encoding="utf-8")
    PROMPT_DRAFT.unlink()  # Remove draft

    print("\n✓ Prompt updated successfully.")
    print(f"  Previous version archived to social/data/prompt_history/")
    print(f"  New version is live at social/data/post_prompt.txt\n")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if "--history" in sys.argv:
        show_history()
        return

    if "--approve" in sys.argv:
        approve_draft()
        return

    # ── Run research ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("FIELD NOTES: EAST ANGLIA — WEEKLY PROMPT RESEARCH")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%A %d %B %Y')}\n")

    current_prompt = PROMPT_FILE.read_text(encoding="utf-8")

    try:
        research_output = run_research(current_prompt)
    except Exception as e:
        logger.error(f"Research failed: {e}")
        sys.exit(1)

    proposed_prompt, changes_found = extract_proposed_prompt(research_output)

    if not proposed_prompt:
        logger.error("Could not extract proposed prompt from research output")
        print("\nRaw research output saved to: social/data/research_debug.txt")
        (DATA_DIR / "research_debug.txt").write_text(research_output)
        sys.exit(1)

    # ── No changes ────────────────────────────────────────────────────────
    if not changes_found:
        print("✓ No changes needed this week.")
        print("  Current prompt is already up to date with best practices.\n")
        send_update_email(research_output, "", changes_found=False)
        return

    # ── Changes found ──────────────────────────────────────────────────────
    diff_summary = generate_diff_summary(current_prompt, proposed_prompt)

    print("Changes proposed:\n")
    print(diff_summary[:2000])

    # Save draft
    PROMPT_DRAFT.write_text(proposed_prompt, encoding="utf-8")

    # Email summary
    send_update_email(research_output, diff_summary, changes_found=True)

    print("\n" + "="*60)
    print("PROPOSED UPDATE SAVED")
    print("="*60)
    print(f"  Draft saved to: social/data/post_prompt_draft.txt")
    print(f"  Summary emailed to: {NOTIFICATION_EMAIL}")
    print(f"\n  To APPLY the update:")
    print(f"  .venv/bin/python social/update_prompt.py --approve")
    print(f"\n  To REJECT (keep current prompt):")
    print(f"  Do nothing — post_prompt.txt is unchanged")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
