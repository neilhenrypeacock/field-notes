# Lessons Learned

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
