# Field Notes: East Anglia

Weekly AI-powered farming intelligence newsletter for East Anglian farmers.

## Reference files — always keep updated

| File | Purpose | When to update |
|---|---|---|
| `CLAUDE.md` | Technical reference for Claude Code | When anything structural changes (scrapers, config, infra, design) |
| `CLAUDE_CHAT.md` | Context for Claude Chat | When project status, pending tasks, or setup changes |
| `LESSONS.md` | Self-learning log | After every failure, fix, or unexpected behaviour |

**Rule:** At the end of any session where something changed, broke, or was fixed — update all three files. Add new lessons at the top of LESSONS.md under today's date.

## Project location

```
/Users/neilpeacock/Projects/fieldnotes/
```

## How to run

```bash
cd /Users/neilpeacock/Projects/fieldnotes

# Generate newsletter (loads data → calls Claude AI → outputs HTML + plain text)
.venv/bin/python newsletter/generate.py

# Send draft to neil@neilpeacock.co.uk
.venv/bin/python newsletter/send.py

# Run a specific scraper manually
.venv/bin/python scrapers/norwich_livestock.py
```

## Preview server

`.claude/launch.json` at `/Users/neilpeacock/Projects/fieldnotes/.claude/launch.json`
Starts `python3 -m http.server 7654` serving `newsletter/output/`. Use the Claude Code preview tool with server name `newsletter-preview`.

## Project structure

```
field-notes/
├── .env                        # API keys and config (never commit)
├── .env.example                # Template
├── requirements.txt            # Python deps (pinned)
├── run_newsletter.sh           # Cron: generate + send (Monday 5am UTC)
├── run_scrapers.sh             # Cron: all 13 scrapers (Sunday 8pm UTC)
├── run_daily_check.sh          # Cron: RSS monitor (daily 6am UTC)
├── scrapers/
│   ├── base.py                 # Shared: HTTP session (1–2s polite delay, 3 retries), save_data(), archive_current()
│   ├── ahdb_grain.py           # Feed wheat, milling wheat, feed barley — UK Corn Returns Excel + UK average
│   ├── ahdb_livestock.py       # Pig SPP, milk farmgate, beef deadweight, egg prices, poultry note
│   ├── ahdb_feed.py            # Feed commodity prices (Excel export API)
│   ├── ahdb_fertiliser.py      # Fertiliser prices
│   ├── met_office.py           # Weather forecast — 7-day Open-Meteo (Met Office DataPoint optional)
│   ├── defra_blog.py           # DEFRA news/announcements
│   ├── govuk_schemes.py        # Government farming schemes (Atom feed)
│   ├── local_news.py           # East Anglia farming news (RSS only — EDP blocks scraping)
│   ├── machinery_auctions.py   # Cheffins machinery auction listings
│   ├── events.py               # Local farming events (fetches og:description per event URL)
│   ├── jobs.py                 # Farmers Weekly East of England jobs
│   ├── land_listings.py        # Brown & Co land/property listings
│   └── norwich_livestock.py    # Norwich Livestock Market weekly sale report (regex-parsed)
├── data/                       # JSON output from scrapers
│   ├── *.json                  # Current week's scraped data
│   ├── norwich_livestock.json  # Norwich Market: cattle head/avg, lamb sections by weight class
│   ├── issue_number.json       # {"current": N} — auto-increments on every generate run
│   ├── community_events.json   # Manually curated local events (Neil updates weekly — can be [])
│   ├── tech_watch.json         # Manually curated tech/enterprise item (Neil updates weekly)
│   ├── from_the_soil.json      # 52 rotating ~100-word narratives — no manual update needed
│   └── previous/               # Last week's data for week-on-week price comparisons
├── newsletter/
│   ├── generate.py             # Main orchestrator: loads data → AI → HTML + plain text
│   ├── send.py                 # Resend API sender (draft or broadcast mode)
│   ├── template.html           # v2 HTML email template (640px, Playfair + Source Sans 3)
│   ├── template_plain.txt      # Plain-text fallback template
│   ├── assets/                 # 15 watercolour SVGs (fn_illustration_01–12b.svg + map banner)
│   └── output/                 # Generated field_notes_YYYY_MM_DD.html + .txt
├── prompts/                    # 13 AI prompt files (one per section)
├── monitor/
│   └── daily_check.py          # RSS checker: Defra Blog + GOV.UK Schemes feeds
├── logs/
│   ├── ai_usage.json           # Last 200 Claude API calls with token counts
│   └── send_log.json           # Send history (mode, Resend ID, recipients)
└── web/
    ├── assets/                 # 15 SVGs served from domain (mirrors newsletter/assets/)
    └── index.html              # Landing page
```

## .env keys

```
ANTHROPIC_API_KEY=       # console.anthropic.com
RESEND_API_KEY=          # resend.com/api-keys
MET_OFFICE_API_KEY=      # optional, falls back to Open-Meteo
RESEND_AUDIENCE_ID=      # set when sending to live audience
FROM_EMAIL=              # Field Notes <hello@fieldnoteseastanglia.co.uk>
NEWSLETTER_ENV=draft     # change to 'live' for broadcast sends
DRAFT_EMAIL=             # neil@neilpeacock.co.uk
ASSETS_BASE_URL=         # https://fieldnoteseastanglia.co.uk/assets
LOG_LEVEL=INFO
```

## Domain & email

- Domain: `fieldnoteseastanglia.co.uk` (Namecheap) — **DNS verified 24 March 2026**
- Sending: Resend — domain verified ✓
- `FROM_EMAIL=Field Notes <hello@fieldnoteseastanglia.co.uk>`
- Icons: served from `https://fieldnoteseastanglia.co.uk/assets` (switched from GitHub CDN)
- `ASSETS_BASE_URL=https://fieldnoteseastanglia.co.uk/assets`

## Cost per newsletter

- Anthropic API (~$0.18): 13 Claude Sonnet calls, ~1k tokens in / 600 tokens out each
- Resend: free up to 3,000 subscribers/month
- Domain: ~£8/yr

## Template variables (full list)

**Content:** `$date_display`, `$issue_number`, `$preview_text`, `$at_a_glance`, `$markets_summary`, `$price_table_grain`, `$costs_summary`, `$price_table_fertiliser`, `$margin_watch`, `$livestock_summary`, `$price_table_livestock`, `$norwich_market`, `$schemes_grants`, `$weather_summary`, `$weather_table`, `$events`, `$event_cards`, `$land_property`, `$jobs`, `$machinery`, `$tech_watch`, `$regulatory`, `$one_good_read`, `$from_the_soil`, `$unsubscribe_url`

**Illustrations (HTTPS URLs when `ASSETS_BASE_URL` set; base64 data URIs for local preview):** `$banner_map`, `$illus_glance`, `$illus_markets`, `$illus_costs`, `$illus_margins`, `$illus_livestock`, `$illus_schemes`, `$illus_weather`, `$illus_land`, `$illus_jobs`, `$illus_machinery`, `$illus_tech_watch`, `$illus_regulatory`, `$illus_events`, `$illus_read`

## Section order (template.html)

1. At a Glance (`#glance`)
2. Markets (`#markets`) — grain price table with optional UK Avg column
3. Costs (`#costs`) — fertiliser price table
4. Margin Watch (`#margins`) — gold badge, gold-bordered box
5. Livestock & Dairy (`#livestock`) — AHDB price table + Norwich Market table + reader CTA
6. Schemes & Grants (`#schemes`) — JustFarm CTA after AI text
7. Weather (`#weather`) — 7-day colour-coded table
8. Community & Events (`#events`) — AI intro + event cards + YANA strip
9. Land & Property (`#land`)
10. Jobs (`#jobs`)
11. Machinery & Auctions (`#machinery`)
12. Tech Watch (`#tech-watch`) — manually curated, no AI call
13. Regulatory & Health (`#regulatory`)
14. One Good Read (`#read`) — gold badge, warm box
15. From the Soil (`#from-the-soil`) — gold top border, italic serif, rotates by issue number

## v2 Design system (template.html)

- Container: 640px max-width, `background:#f2f0eb`, white inner content area, 44px horizontal padding
- Fonts: Playfair Display (masthead + Margin Watch label only), Source Sans 3 (body/badges/labels), Source Serif 4 (editorial prose sections) — all via Google Fonts `@import`
- Dark green `#1b3a2d`: section badge backgrounds, table headers, link colour, CTA buttons
- Gold `#d4a853`: Margin Watch + One Good Read badges; hero subtitle; From the Soil divider
- Lighter green `#263f32`: legend strip below hero; forward banner
- Dividers: `◆ ◆ ◆` (tracked caps, `#c4b99a`) on `#f7f5f0` background, flanked by 1px `#e0dbd0` rules
- Section badges: full-width `background-color:#1b3a2d`, `border-radius:4px`, `padding:14px 20px 14px 12px`, 36×36px SVG icon + 12px white uppercase label
- Price table headers: `background-color:#1b3a2d`, white text; change column: ▲ `#2e7d32` / ▼ `#c62828` / N/A `#666`
- Weather table rows: green `#f0f7f2` (<30% rain), gold `#fdf8ee` (30–60%), red `#fdf2f2` (≥60%)
- Data Sources strip: `#f7f5f0`, two-column layout, all 13 sources linked
- Forward banner: `#263f32`, Playfair gold "Forward this email — it's free."

## Key technical notes

- Python 3.9 — no `str | None` union syntax, use `Optional[str]` from `typing`
- `string.Template.safe_substitute()` — intentional; leaves `{{unsubscribe_url}}` for Resend to fill
- Issue number auto-increments on every generate run — reset `data/issue_number.json` if inflated by testing (currently at 18 as of 23 March 2026 — reset before live send)
- AHDB grain: UK Corn Returns Excel (Azure Blob), Sheet "Spot", Eastern region row + UK average row
- AHDB feed: Excel export API requires `M/d/yyyy h:mm:ss AM` date format (not dd/mm/yyyy)
- AHDB pig SPP: `.xls` format (xlrd), wide layout — price at non_empty[1], change at non_empty[2]
- AHDB milk: sheet "UK average farmgate price", col1=date, col2=price
- AHDB beef/eggs/poultry: scraped via `_find_excel_url()` page-scraping helper (resilient to URL changes)
- FW Jobs: `li.lister__item` cards, filtered to East of England; `[Apply →](URL)` links inline in AI output
- Brown & Co: `/services/rural/property-search`, card class `card--property-listing`
- EDP/EADT block direct scraping — `local_news.py` uses RSS feeds only
- Met Office DataPoint optional — falls back to Open-Meteo (no key needed), `forecast_days=7`
- Norwich Livestock Market (`norwichlivestockmarket.com/reports`): Joomla CMS, reports at `/component/content/article/8-reports/…`. Regex-parses narrative text for cattle head/avg and lamb sections (STANDARD/MEDIUM/HEAVY/HEAVY+/PRIME HOGGS). Reports can lag by several weeks.
- Illustrations: HTTPS URLs when `ASSETS_BASE_URL` set (email-safe); base64 fallback for local preview. Gmail strips `data:image/svg+xml;base64,...` — always send with ASSETS_BASE_URL.
- Currently serving icons from GitHub: `raw.githubusercontent.com/neilhenrypeacock/field-notes-assets/main`
- Sources cited **inline** in AI text as `[Label](URL)` — `_apply_inline_md()` converts to `<a>` tags
- `_build_section_sources()` and `_source_links_html()` removed — no footer source lines exist
- `text_to_html()`: `## heading` → bold green `<p>`; `**bold**` → `<strong>`; `*italic*` → `<em>`; bullets → `<ul>` (blank lines between bullets do NOT close `<ul>`)
- `_apply_inline_md()`: `[text](url)` → `<a href style="color:#1b3a2d">`; `**bold**` → `<strong>`; `*italic*` → `<em>`
- `build_price_table_html()`: shows optional "UK Avg" column when `uk_average_price` present in grain data
- `build_price_table_livestock_html()`: 5-row table — pig SPP / milk / beef / eggs / poultry
- `build_norwich_market_html()`: compact 3-column table (type / entry / average) for Norwich Market data
- `build_event_cards_html()`: builds styled event cards from merged events.json + community_events.json; strips leading title repetition from og:description
- `community_events.json` can be `[]` — handled by `isinstance(result, list)` check; safe if Neil hasn't added events
- One Good Read: AI links title inline as `[Article Title](URL)` — no separate URL line needed
- Tech Watch: no AI call — loaded directly from `data/tech_watch.json`; Neil updates weekly
- From the Soil: no AI call — `items[issue_number % 52]` from `data/from_the_soil.json`; 52 ~100-word narrative stories
- events.py: `_fetch_description(url)` fetches each event page for `og:description` — do NOT pass `timeout=` kwarg to `get()` (base.get() sets its own 15s timeout; duplicate kwarg causes TypeError)
- NEVER set `FROM_EMAIL` in shell — `<>` breaks zsh. Always edit `.env` directly.
- Preview browser: `window.location` JS changes don't persist between `preview_eval` calls — use `window.scrollTo()` to navigate to sections

## Current status (23 March 2026)

- All 5 email feedback passes complete (inline sources, hosted icons, event cards, CTAs, From the Soil rewrite)
- 13 scrapers all working including new Norwich Livestock Market scraper
- Issue counter at **20** due to test runs — **reset to correct number before live send**
- Domain DNS verified 24 March 2026 — sending from `hello@fieldnoteseastanglia.co.uk`
- `NEWSLETTER_ENV=draft` — broadcast mode not yet tested
- Icons served from `https://fieldnoteseastanglia.co.uk/assets`
- Sources cited inline in AI text; all footer `$sources_*` placeholders removed
- Event cards: structured HTML cards from `events.json` + `community_events.json`
- Livestock CTA: "Email us with your prices"; Schemes CTA: JustFarm link (hardcoded in template)
- From the Soil: all 52 items are ~100-word narratives with scene → fact → significance structure
- Neil updates weekly: `data/tech_watch.json` and `data/community_events.json`
- `ASSETS_BASE_URL` set to `https://fieldnoteseastanglia.co.uk/assets` ✓

## Landing page (web/index.html) — built 23 March 2026

Single-page sign-up site. Sections in order:
1. **Hero** — dark green `#1b3a2d`, full viewport height, map SVG ghosted at 7% opacity, Playfair "Field Notes / East Anglia" headline, email sign-up form (POST to Resend), topic chips at bottom
2. **Light divider** — `◆ ◆ ◆` on `#f7f5f0`
3. **What's inside** — parchment `#f2f0eb`, 3×2 SVG icon grid (At a Glance / Markets / Weather / Schemes / Margin Watch / Land & Jobs)
4. **Sources** — parchment, inline links to AHDB, Met Office, Defra, GOV.UK, Cheffins, FW Jobs, Brown & Co, Norwich Livestock Market, EDP, Farming UK
5. **Map strip** — parchment, `fn_map_east_anglia_banner.svg` at 320px/opacity 0.88, "Norfolk · Suffolk · Cambridgeshire" label
6. **Dark divider** — `◆ ◆ ◆` on `#1b3a2d`
7. **For you** — dark green, Playfair heading, copy for farmers/agronomists/contractors, "Free, every Monday" pill
8. **Repeat CTA** — dark green, second sign-up form
9. **Footer** — `#263f32`

**TODO before go-live:**
- Replace `YOUR_RESEND_AUDIENCE_ID` in both `<form>` action attributes with actual `RESEND_AUDIENCE_ID` from `.env`
- Confirm Resend signup endpoint URL is correct for your plan
- Update hero-meta copy: "Every Monday at 5am" → "Every Monday lunchtime" (send time decision below)

## Send time decision (23 March 2026)

**Decided: Monday 12:30pm lunchtime.** Rationale:
- Farmers are on a natural break — phone in hand, cab or kitchen
- Competing with far fewer emails than 5am slot
- Monday morning livestock markets (incl. Norwich) may have results by then
- Still clearly "Monday" / week-ahead framing
- Weather forecast more actionable (6 days ahead, not 7)

**Changes needed to implement:**
1. `run_newsletter.sh` cron comment: `0 5 * * 1` → `30 12 * * 1`
2. `web/index.html` hero-meta: "Every Monday at 5am" → "Every Monday lunchtime"
3. Update this file and claudechat.md

## Subscriber growth strategy (23 March 2026)

Priority order:
1. **NFU county branches** — Norfolk, Suffolk, Cambridgeshire — email county secretaries directly
2. **Facebook farming groups** — East Anglian Farming etc. — post sample issue, personal ask
3. **Cheffins auction days** — QR code card; already pulling their data so relationship exists
4. **Young Farmers Clubs** — county federations, digitally active
5. **LinkedIn agronomists** — they're present and will share with farmers they advise
6. **Agricultural colleges** — Easton & Otley, Writtle, Shuttleworth
7. **Norfolk + Suffolk Shows** — badge/card presence
8. **Weekly Twitter/X grain price post** — share price table with `#ukfarming`, drives organic discovery
9. **Public newsletter archive** — SEO for "East Anglia grain prices", "Norfolk farming news"
