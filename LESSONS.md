# Lessons Learned

---

## 27 March 2026 (verification enhancements)

### Cross-week comparison catches scraper errors
Week-on-week plausibility checking (>15% change = flag) using `data/previous/` files catches a category of error that single-week validation misses: a scraper returning last month's data, a decimal point shift, or a unit change. Comparing current prices against the previous week's saved data adds a cheap, high-value sanity check. Important: the cross-week check uses the SAME extractors as the in-week check — no code duplication.

### AHDB blocks automated link checks (404 on GET/HEAD)
Most ahdb.org.uk subpages return 404 to automated requests regardless of User-Agent. The pages work fine in browsers. Solution: maintain a `_SKIP_LINK_CHECK_DOMAINS` set and bypass link checking for known bot-blocking domains. False "broken link" alerts waste reviewer time and erode trust in the verification system.

### Review guidance must be actionable, not vague
"Check the source" is useless — the reviewer needs clickable links to the exact page where they can verify the data. Built a `REVIEW_LINKS` mapping with verified-working URLs for each section, and `build_review_guidance()` generates numbered action items tied to specific anomalies. The reviewer sees "1. Milling wheat is below feed wheat — check the AHDB Corn Returns Excel (link below)" with a clickable link, not "search for AHDB grain prices."

---

## 27 March 2026 (accuracy & verification)

### Confidence score ≠ accuracy check
The original confidence scoring only measured data completeness ("did I get the data?"), not accuracy ("is the output correct?"). It explicitly said "never score low because prices moved unexpectedly." This meant anomalies like feed wheat being more expensive than milling wheat (unusual market inversion) were never flagged. Lesson: self-reported confidence from the writer AI is not a substitute for an independent verification step.

### Two-gate verification catches what self-scoring misses
Adapted the social pipeline's 2-gate system for the newsletter. Gate 1 runs codified market rules (cross-commodity relationships, plausible ranges, week-on-week plausibility) BEFORE the AI writes. Gate 2 runs an independent AI call AFTER writing to cross-check numbers, directions, and sources. Gate 1 immediately caught the milling/feed wheat inversion on first test.

### Cross-commodity rules must be warnings, not blocks
Milling wheat below feed wheat IS unusual but CAN happen (e.g. surplus in milling grade, tight feed supply). So it's a warning (amber flag) not a block (red). The farmer-editor makes the final call. Blocking would have suppressed a genuine data point.

### AHDB page URLs break periodically
The beef-and-lamb/prices-and-markets page returned 404 during testing. The `_find_excel_url()` pattern is resilient (page-scrapes for links rather than hardcoding URLs), but the page itself needs to exist. Sheep scraper follows the same pattern — it will work once the page is accessible. Graceful error handling (returns `{"error": "..."}`) means the newsletter still generates with whatever data IS available.

### National news needs reserved slots, not just scoring
Pure score-ranked sorting means 20 local NFU meeting posts crowd out nationally important policy stories (inheritance tax reform, bird flu alerts). Reserving 5 of 20 news slots for nationally important stories ensures the farmer sees both local and national news that affects their business.

---

## 23 March 2026 (strategy session)

### Send time: Monday 12:30pm lunchtime beats 5am
Monday 5am competes with nothing but the farmer is already out the door. Monday lunch is a natural break — phone in hand, either in the cab or at the kitchen table. Decided: **Monday 12:30pm UTC**. Changes needed: `run_newsletter.sh` cron `0 5 * * 1` → `30 12 * * 1` and `web/index.html` hero-meta copy.

### Landing page: map in map-strip section, not just ghosted in hero
The map SVG (`fn_map_east_anglia_banner.svg`) is most impactful as a clearly visible section on the parchment background (`#f2f0eb`) between sources and the "for you" section. Used at 320px width / 0.88 opacity. The ghost-in-hero at 7% opacity still works well as a background texture but the explicit map strip establishes geographic identity strongly.

### Landing page form: audience_id placeholder must be replaced before go-live
`web/index.html` has `value="YOUR_RESEND_AUDIENCE_ID"` in both sign-up forms. This must be replaced with the actual `RESEND_AUDIENCE_ID` from `.env` before the page is published. Also confirm the Resend signup endpoint (`https://resend.com/subscribe`) is the correct URL for your plan type.

### Subscriber growth: personal outreach before automation
First 200 subscribers come from personal effort — showing up, direct ask. NFU branches and Facebook farming groups are highest-leverage because each touchpoint can reach hundreds of exactly the right people. Farming communities are tight; word of mouth compounds fast once the product is genuinely useful.

---

## 23 March 2026 (email feedback pass)

### Gmail strips base64 data URIs in `<img>` tags
Gmail and most email clients block `<img src="data:image/svg+xml;base64,...">` images entirely. The fix is to host SVG files at an HTTPS URL. Pattern: `ASSETS_BASE_URL` env var — when set, `_load_illustrations()` returns HTTPS URLs; when blank, falls back to base64 for local preview. SVG files go in `web/assets/` to be served by the web server. Always use HTTPS-hosted images for email delivery.

### Inline source citations: `_apply_inline_md()` already handles it
When moving from footer source links to inline `[Label](URL)` citations in AI text, no new code was needed — `_apply_inline_md()` already converts `[text](url)` to `<a href>`. The change was purely: (1) remove `_build_section_sources()` and `_source_links_html()`, (2) update prompts to instruct AI to cite inline, (3) remove `$sources_*` placeholders from template. ~100 lines removed, simpler system.

### One Good Read: inline title link replaces URL-on-last-line pattern
Old pattern: AI outputs URL on last line; generate.py strips it and uses for footer source. New pattern: AI links the title inline as `[Article Title](URL)` — no parsing needed, no URL stripping, no footer line. Much simpler. Update `prompts/one_good_read.txt` accordingly.

### Event cards: build from data, not AI
Structured event cards (title + date/location + button) should be built directly from `events.json` + `community_events.json` data via `build_event_cards_html()`. AI writes only a 1–2 sentence intro. This gives consistent card formatting that the AI cannot produce reliably, and decouples the visual structure from the text generation.

### community_events.json can be empty list `[]`
If Neil hasn't added any community events, the file is `[]`. Load with `load_json()` and check `isinstance(result, list)` before merging with scraped events. The empty case must produce no cards without erroring.

---

## 23 March 2026

### AHDB livestock scrapers — page-scraping beats hardcoded Azure URLs
AHDB publishes beef, eggs, and poultry Excel files via Azure Blob Storage with periodically-rotating URLs. Do NOT hardcode these URLs. Instead, scrape the AHDB product page to find the current `.xlsx`/`.xls` link dynamically (`_find_excel_url()` helper). This is resilient to URL changes and matches the existing pattern used by ahdb_grain.py.

### One Good Read URL was always wrong
The `_build_section_sources()` function was defaulting to `news["articles"][0].url` regardless of which article the AI actually recommended. Fix: the AI prompt instructs it to output the URL on the last line; `generate.py` now parses that URL from the AI output, strips it from the display text, and uses it for `sources_read`. Always check source link logic when adding new sections.

### Python 3.9 — no `str | None` syntax
The production server runs Python 3.9. Use `Optional[str]` from `typing`, not `str | None` union syntax. This will silently cause a `SyntaxError` at runtime. Add `from typing import Optional` at the top of any file that needs it.

### Blank lines in AI output were breaking bullet groups
The `text_to_html()` function was closing `<ul>` on every blank line. AI models often put blank lines between consecutive bullets. Fix: only close the `<ul>` when non-bullet content is encountered, not on blank lines. Test this by checking if multi-paragraph AI responses render bullets correctly.

### Moving large HTML blocks: use a Python script, not the Edit tool
When the `Edit` tool would create a temporary duplicate state (e.g. inserting a section before deleting it from its old position), use a Bash Python script to do the move atomically. Write the script inline, run it once, verify, delete. Much safer than multi-step edits on large files.

### Fertiliser URL was wrong from the start
The fertiliser source URL in template.html pointed to `ahdb.org.uk/dairy/fertiliser-prices` (dairy!). It should be `ahdb.org.uk/cereals-oilseeds/fertiliser-prices`. Always verify AHDB URLs — the subdomain path is not always obvious.

### `string.Template.safe_substitute()` is intentional — don't switch to `substitute()`
Using `safe_substitute()` means unknown variables (like `{{unsubscribe_url}}` which Resend fills at send time) pass through as-is. If you switch to `substitute()`, it will raise a `KeyError` on any unrecognised variable. This is load-bearing behaviour.

### Issue number increments on every `generate.py` run
Not idempotent. If you run `generate.py` for testing, the issue counter goes up. Manually reset `data/issue_number.json` `{"current": N}` if the count drifts during development.
