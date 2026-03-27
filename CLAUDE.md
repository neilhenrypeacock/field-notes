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

## Architecture overview

The project has 5 distinct systems:

| System | Entry point | What it does |
|---|---|---|
| **Scraper pipeline** | `run_scrapers.sh` | 14 scheduled scrapers + prefilter → JSON data |
| **Newsletter pipeline** | `run_newsletter.sh` | 15 AI calls → HTML/TXT → Resend |
| **Social media pipeline** | `social/run_sunday.py` | 7 Facebook posts/week with 2-gate AI verification |
| **Admin dashboard** | `admin_server.py` (port 7657) | AI-assisted section editing + post review UI |
| **Web layer** | `web/` + `worker/` | Landing page, sign-up, Cloudflare Worker, thank-you |

## How to run

```bash
cd /Users/neilpeacock/Projects/fieldnotes

# Generate newsletter (loads data → calls Claude AI → outputs HTML + plain text)
.venv/bin/python newsletter/generate.py

# Send draft to neil@neilpeacock.co.uk
.venv/bin/python newsletter/send.py

# Run a specific scraper manually
.venv/bin/python scrapers/norwich_livestock.py

# Run the full Sunday social pipeline (update prompt → generate posts → interactive review)
.venv/bin/python social/run_sunday.py

# Start the admin dashboard (serves on localhost:7657)
.venv/bin/python admin_server.py
```

## Preview server

`.claude/launch.json` at `/Users/neilpeacock/Projects/fieldnotes/.claude/launch.json`
Starts `python3 -m http.server 7654` serving `newsletter/output/`. Use the Claude Code preview tool with server name `newsletter-preview`.

## Project structure

```
fieldnotes/
├── .env                          # API keys and config (never commit)
├── .env.example                  # Template
├── requirements.txt              # Python deps (pinned)
├── run_newsletter.sh             # Cron: generate + send (Monday 12:30pm UTC)
├── run_scrapers.sh               # Cron: 14 scrapers + prefilter (Sunday 8pm UTC)
├── run_daily_check.sh            # Cron: RSS monitor (daily 6am UTC)
├── admin_server.py               # Local admin server (port 7657) — see Admin section
├── generate_brand_svgs.py        # One-off: generate profile_picture + facebook_cover SVGs/PNGs
├── keywords.txt                  # Keyword filter: Tier A (+3), Tier B (+1), Tier C (-5)
│
├── scrapers/
│   ├── base.py                   # Shared: HTTP session, save_data(), archive_current()
│   ├── utils.py                  # load_keywords(), score_article()
│   │
│   │   ── 14 SCHEDULED SCRAPERS (run_scrapers.sh) ──
│   ├── ahdb_grain.py             # UK Corn Returns Excel — EA + UK avg prices
│   ├── ahdb_livestock.py         # Pig SPP, milk, beef, eggs, poultry
│   ├── ahdb_feed.py              # Feed commodity prices (Excel API)
│   ├── ahdb_fertiliser.py        # Fertiliser prices
│   ├── met_office.py             # Weather — 7-day Open-Meteo (DataPoint optional)
│   ├── defra_blog.py             # Defra Farming Blog RSS
│   ├── govuk_schemes.py          # GOV.UK Find Funding Atom feed
│   ├── norwich_livestock.py      # Norwich Livestock Market (regex-parsed)
│   ├── land_listings.py          # Brown & Co + Savills + Strutt & Parker
│   ├── jobs.py                   # Farmers Weekly East of England jobs
│   ├── local_news.py             # EA farming news (RSS + HTML, keyword-filtered)
│   ├── events.py                 # RNAA, Norfolk FWAG, Agri-TechE events
│   ├── machinery_auctions.py     # Cheffins auction listings + FETF window
│   ├── ea_alerts.py              # EA Flood Monitoring API alerts
│   │
│   │   ── 22 PREFILTER SCRAPERS (run by prefilter.py) ──
│   │   EA-local: anglia_farmer.py, ea_bylines.py, nfu_east.py, itv_anglia.py,
│   │             british_sugar.py, camgrain.py, water_resources_east.py, events_extended.py
│   │   National: farmers_weekly.py, farmers_guardian.py, farmers_guide.py, agriland.py,
│   │             farming_uk.py, farming_monthly.py, cpm.py, aafarmer.py
│   │   Specialist: frontier_ag.py, aic.py, nffn.py, chap.py, ukagritech.py, agrifunder.py
│   │
│   └── filtered/                 # Output from prefilter.py (11 category buckets)
│       ├── news.json             # Scored/filtered news articles (max 20)
│       ├── markets.json, policy.json, agritech.json, reads.json
│       ├── events_attend.json, events_online.json
│       ├── land.json, jobs.json, machinery.json, weather.json
│
├── data/                         # JSON from scheduled scrapers + manual curation
│   ├── ahdb_grain.json           # Feed wheat, milling wheat, feed barley (EA + UK avg)
│   ├── ahdb_livestock.json       # Pig SPP, milk, beef, sheep/lamb dwt, eggs, poultry
│   ├── ahdb_feed.json            # Feed commodity prices
│   ├── ahdb_fertiliser.json      # Fertiliser prices (AN, Urea, UAN, MOP, DAP, TSP)
│   ├── met_office.json           # 7-day weather forecast
│   ├── defra_blog.json           # Defra blog posts (8-day window)
│   ├── govuk_schemes.json        # GOV.UK schemes (change-tracked)
│   ├── norwich_livestock.json    # Norwich Market: cattle + lamb sections by weight
│   ├── land_listings.json        # Property listings (max 20, EA only)
│   ├── jobs.json                 # FW Jobs (max 15, East of England)
│   ├── local_news.json           # EA news (fallback if filtered/news.json missing)
│   ├── events.json               # Events (fallback if filtered/events_*.json missing)
│   ├── machinery_auctions.json   # Cheffins sales + FETF window check
│   ├── ea_alerts.json            # EA Flood Monitoring alerts (injected into weather prompt)
│   ├── fuel.json                 # Red diesel price — Neil updates manually
│   ├── sugar_beet.json           # British Sugar contract — Neil updates manually
│   ├── issue_number.json         # {"current": N} — auto-increments on every generate run
│   ├── community_events.json     # Manually curated local events (can be [])
│   ├── tech_watch.json           # Manually curated editor's pick (Neil updates weekly)
│   ├── from_the_soil.json        # 52 pre-written ~100-word narratives (rotates by issue %)
│   └── previous/                 # Last week's data for week-on-week price comparisons
│
├── newsletter/
│   ├── generate.py               # Main orchestrator: loads data → 15 AI calls + verification → HTML + TXT
│   ├── verify.py                 # 2-gate verification: Gate 1 (data validation) + Gate 2 (AI cross-check)
│   ├── validation_config.json    # Price ranges, cross-commodity rules, freshness thresholds
│   ├── prefilter.py              # Runs 22 article scrapers, scores+routes → scrapers/filtered/
│   ├── send.py                   # Resend sender — draft or broadcast mode
│   ├── template.html             # HTML email template (640px, Playfair + Source Sans 3)
│   ├── template_plain.txt        # Plain-text fallback template
│   ├── assets/                   # 15 watercolour SVGs (section illustrations + map banner)
│   └── output/                   # Generated field_notes_YYYY_MM_DD.html + .txt + _confidence.json
│
├── prompts/                      # 13 AI prompt files (one per section)
│
├── social/                       # Facebook post pipeline — see Social section
│   ├── config.py                 # Settings: schedule, model, FB API, hashtags
│   ├── generate_posts.py         # Orchestrator: scrape → AI write → verify → save
│   ├── post_generator.py         # AI post generation logic
│   ├── verify.py                 # 2-gate verification (confidence + number accuracy)
│   ├── review_posts.py           # Interactive CLI review session
│   ├── schedule_posts.py         # Posts approved items at scheduled times
│   ├── run_sunday.py             # Single command: update_prompt → generate → review
│   ├── run.py                    # Cron script (every ~3 days) — posts approved items
│   ├── update_prompt.py          # Researches best practices, proposes prompt improvements
│   ├── facebook_client.py        # Facebook Graph API v19.0 wrapper
│   ├── buffer_client.py          # Buffer API alternative
│   ├── scraper_reader.py         # Reads scraped data for post context
│   ├── digest_email.py           # Sends digest notification email
│   ├── cron_setup.sh             # Installs cron (dynamic path detection)
│   └── data/                     # scheduled_posts.json, post_prompt.txt, history/
│
├── monitor/
│   └── daily_check.py            # Daily RSS check: Defra Blog + GOV.UK Schemes → changelog.json
│
├── logs/
│   ├── ai_usage.json             # Last 200 Claude API calls (section, tokens, timestamp)
│   └── send_log.json             # Send history (mode, Resend ID, recipients)
│
├── web/
│   ├── assets/                   # 15 SVGs served from domain (mirrors newsletter/assets/)
│   ├── index.html                # Landing page (sign-up, sources, For You sections)
│   ├── admin.html                # Admin dashboard UI (served by admin_server.py)
│   └── thankyou.html             # Post-signup page (confirmation + 8-chapter EA history)
│
└── worker/
    ├── index.js                  # Cloudflare Worker: /subscribe + /update-profile
    └── wrangler.toml             # Worker config — deployed to neil-675.workers.dev
```

## Pipeline flow

### Sunday evening
1. `run_scrapers.sh` runs 14 scheduled scrapers in priority order, then `newsletter/prefilter.py`
2. 13 core scrapers write to `data/*.json`; `ea_alerts.py` writes to `data/ea_alerts.json`
3. `prefilter.py` imports 22 article scrapers, scores with keyword tiers (A +3, B +1, C -5), routes into 11 category buckets (caps: news 20, markets 15, events_attend 15, etc.), writes to `scrapers/filtered/`
4. `social/run_sunday.py` (manual) — `update_prompt.py` → `generate_posts.py` → `review_posts.py`

### Monday 12:30pm
1. `run_newsletter.sh` → `newsletter/generate.py` → `newsletter/send.py`
2. `generate.py` loads 16+ JSON files; prefers `scrapers/filtered/news.json` over `data/local_news.json`, and `filtered/events_*.json` over `data/events.json`; makes 15 Claude Sonnet 4.6 calls; writes HTML + TXT to `newsletter/output/`
3. `send.py` sends draft (or broadcast if `NEWSLETTER_ENV=live`)

### Daily 6am
`run_daily_check.sh` → `monitor/daily_check.py` monitors Defra Blog + GOV.UK RSS → `monitor/changelog.json`

### Social posting (every ~3 days via cron)
`social/run.py` posts Facebook-approved items at scheduled times via Facebook Graph API / Buffer

## .env keys

```
ANTHROPIC_API_KEY=        # console.anthropic.com
RESEND_API_KEY=           # resend.com/api-keys
MET_OFFICE_API_KEY=       # optional — falls back to Open-Meteo
RESEND_AUDIENCE_ID=       # Resend audience ID for broadcast sends
FROM_EMAIL=               # Field Notes <hello@fieldnoteseastanglia.co.uk>
NEWSLETTER_ENV=draft      # change to 'live' for broadcast sends
DRAFT_EMAIL=              # neil@neilpeacock.co.uk
ASSETS_BASE_URL=          # https://fieldnoteseastanglia.co.uk/assets
LOG_LEVEL=INFO
FACEBOOK_PAGE_ID=         # Facebook page ID (social pipeline)
FACEBOOK_PAGE_ACCESS_TOKEN=  # Facebook page access token (social pipeline)
DIGEST_EMAIL=             # Email address to receive post-generation digest (social pipeline)
SMTP_HOST=                # SMTP host for digest emails (social/digest_email.py)
SMTP_USER=                # SMTP username
SMTP_PASS=                # SMTP password
```

## Domain & email

- Domain: `fieldnoteseastanglia.co.uk` (Namecheap) — DNS verified 24 March 2026
- Sending: Resend — domain verified ✓
- `FROM_EMAIL=Field Notes <hello@fieldnoteseastanglia.co.uk>`
- Icons served from `https://fieldnoteseastanglia.co.uk/assets`
- `ASSETS_BASE_URL=https://fieldnoteseastanglia.co.uk/assets`

## Cost per newsletter

- Anthropic API (~$0.25-0.30): 15 Claude Sonnet 4.6 writing calls + up to 13 Gate 2 verification calls
- Resend: free up to 3,000 subscribers/month
- Domain: ~£8/yr
- Cloudflare Worker: free tier (100k requests/day)

## Newsletter template variables (full list)

**Metadata:** `$date_display`, `$issue_number`, `$reading_time`, `$preview_text`, `$subscribe_url`, `$unsubscribe_url`

**Navigation/hooks:** `$this_week_hooks`

**Weather:** `$weather_summary`, `$fieldwork_verdict`, `$verdict_bg_color`, `$verdict_border_color`, `$verdict_label_color`, `$weather_table`

**Markets:** `$markets_summary`, `$price_table_grain`

**Costs:** `$costs_summary`, `$price_table_fertiliser`

**Margin Watch:** `$margin_watch`, `$margin_dot_color`

**At a Glance:** `$at_a_glance`

**Livestock:** `$livestock_summary`, `$price_table_livestock`, `$norwich_market`

**Schemes:** `$schemes_grants`

**Conditional cluster:** `$community_cluster_html` (events, land, jobs, machinery, tech watch — conditionally rendered)

**Regulatory:** `$section_regulatory` (conditionally rendered)

**Other:** `$one_good_read`, `$from_the_soil`

**Illustrations (HTTPS URLs when `ASSETS_BASE_URL` set; base64 for local preview):**
`$banner_map`, `$illus_glance`, `$illus_markets`, `$illus_costs`, `$illus_margins`, `$illus_livestock`, `$illus_schemes`, `$illus_weather`, `$illus_land`, `$illus_jobs`, `$illus_machinery`, `$illus_tech_watch`, `$illus_regulatory`, `$illus_events`, `$illus_read`

## Section order (template.html)

1. Hero + metadata
2. Legend strip
3. Share strip + This Week hooks
4. **At a Glance** (`#glance`)
5. **Weather** (`#weather`) — fieldwork verdict (traffic light box) + 7-day table
6. **Markets** (`#markets`) — grain price table with optional UK Avg column
7. **Costs** (`#costs`) — fertiliser price table
8. **Margin Watch** (`#margins`) — gold badge + traffic light dot
9. **Livestock & Dairy** (`#livestock`) — AHDB price table + Norwich Market table + reader CTA
10. **Schemes & Grants** (`#schemes`) — JustFarm CTA after AI text
11. **Community cluster** (conditional: events, land, jobs, machinery, tech watch)
12. **Regulatory & Health** (`#regulatory`) — conditional, skipped if nothing to report
13. **One Good Read** (`#read`) — gold badge, warm box
14. **From the Soil** (`#from-the-soil`) — gold top border, italic serif, rotates by issue number
15. Forward banner + footer

## AI calls per newsletter run (15 total)

| # | Section | Prompt file | Max tokens |
|---|---|---|---|
| 1 | At a Glance | `prompts/at_a_glance.txt` | 600 |
| 2 | Markets | `prompts/markets.txt` | 600 |
| 3 | Costs | `prompts/costs.txt` | 600 |
| 4 | Margin Watch | `prompts/margin_watch.txt` | 600 |
| 5 | Livestock & Dairy | `prompts/livestock.txt` | 600 |
| 6 | Schemes & Grants | `prompts/schemes_grants.txt` | 600 |
| 7 | Weather | `prompts/weather.txt` | 600 |
| 8 | Events | `prompts/events.txt` | 600 |
| 9 | Land & Property | `prompts/land_property.txt` | 600 |
| 10 | Jobs | `prompts/jobs.txt` | 600 (JSON output) |
| 11 | Machinery | `prompts/machinery.txt` | 600 |
| 12 | Regulatory | `prompts/regulatory.txt` | 600 |
| 13 | One Good Read | `prompts/one_good_read.txt` | 600 |
| 14 | This Week Hooks | inline prompt | 120 |
| 15 | Fieldwork Verdict | inline prompt | 80 |

Tech Watch and From the Soil have no AI call — loaded directly from JSON.

## Newsletter verification system

Each section goes through 2-gate verification adapted from `social/verify.py`:

**Gate 1 — Data validation (before AI writes):**
- Price ranges (codified in `newsletter/validation_config.json`)
- Cross-commodity rules (e.g. milling wheat should > feed wheat)
- Week-on-week plausibility from change_pct fields (>15% change flags)
- Cross-week comparison vs `data/previous/` saved data (Check 7)
- Data freshness (max 10 days)
- Required fields per section

**Gate 2 — AI cross-check (after AI writes):**
- Independent Claude call verifies numbers (±2%), directions, sources, invented content
- Checks for unmentioned anomalies in the data
- Returns HIGH/MEDIUM/LOW confidence with notes
- Cost: ~£0.05-0.10 extra per run (up to 13 additional short Claude calls)

**Link verification (after AI writes):**
- Extracts URLs from AI text (markdown links + bare URLs)
- HEAD-checks each link; retries with GET on 405
- Skips known bot-blocking domains (`ahdb.org.uk`, `projectblue.blob.core.windows.net`)
- Broken links flag the section and appear in review guidance

**Actionable review guidance:**
- `REVIEW_LINKS` dict maps each section to verified human-clickable URLs
- `build_review_guidance()` generates numbered action items for flagged sections
- Actions are tied to specific anomalies (e.g. "milling wheat below feed wheat — check AHDB link below")
- Admin dashboard shows "Review Checklist" panel with clickable verify links

**Behaviour:**
- Gate 1 anomalies → section flagged (amber), not blocked
- Gate 2 issues → section flagged for human review (`GATE2_BLOCKS_SECTION = False`)
- Number mismatches → blocked by default (`BLOCK_ON_NUMBER_MISMATCH = True`)
- Broken links → section flagged (amber)
- Results saved to confidence sidecar (`*_confidence.json`) and shown in admin dashboard
- Admin dashboard section list shows verification status dots (green/amber/red)
- Clicking a section shows Gate 1 anomalies, Gate 2 notes, review checklist with verify links

## Prefilter national news balance

- `MAJOR_NATIONAL_SOURCES` (8 pubs): score ≥1 passes through
- `NATIONAL_SOURCES_TIER2` (8 specialist orgs): score ≥1 passes through
- News bucket reserves 5 of 20 slots for nationally important stories
- Tier B keywords expanded with policy terms (APR, bovine TB, food security, etc.)

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
- Fieldwork verdict box: traffic light — green `#f0f7f2` / gold `#fdf8ee` / red `#fdf2f2` depending on forecast severity
- Margin dot: green `#2e7d32` if >£180/t, gold `#d4a853` if £160–180/t, red `#c62828` if <£160/t
- Forward banner: `#263f32`, Playfair gold "Forward this email — it's free."

## Social media pipeline (social/)

Generates 7 Facebook posts per week. Run Sunday evening before the newsletter sends.

**Weekly schedule** (UK local time):
- Monday 07:00 — Newsletter launch post
- Tuesday 07:00 — Grain & commodity prices
- Wednesday 07:30 — Weather outlook
- Wednesday 19:00 — Schemes & grants
- Thursday 07:00 — Input costs
- Friday 07:00 — Farming news & regulatory
- Saturday 08:00 — Land, jobs or machinery

**Sunday workflow:**
```bash
.venv/bin/python social/run_sunday.py
# Or skip research: .venv/bin/python social/run_sunday.py --skip-research
```

**How it works:**
1. `update_prompt.py` — researches current best practices, proposes prompt edits
2. `generate_posts.py` — reads scraped data, writes 7 posts (one per section), runs 2-gate verification on each
3. Gate 1: confidence check (LOW confidence → flagged)
4. Gate 2: number accuracy check (mismatch → blocked automatically)
5. `review_posts.py` — interactive CLI: approve / block / edit / get alternative per post
6. `schedule_posts.py` (cron) — posts approved items at scheduled times via Facebook API

**Model:** `claude-sonnet-4-6` (set in `social/config.py`)

**Cron install:** `bash social/cron_setup.sh` (dynamically detects project root)

## Admin dashboard

Local-only. Start with `.venv/bin/python admin_server.py` (port 7657). Open `http://localhost:7657/admin`.

No password — local-only server, no auth needed.

**Two-tab UI:**
- **Newsletter tab** — renders latest generated HTML, click any section to open AI chat panel. Ask questions or say "update copy" to rewrite a section while preserving HTML structure. "Regenerate newsletter" button re-runs `generate.py`. **Confidence bar** above the preview shows colored chips for every AI section — green (≥0.9), amber (0.75–0.9), red (<0.75) — with reasons. Loaded from `newsletter/output/*_confidence.json` sidecar written by `generate.py`.
- **Facebook Posts tab** — collapsible **Strategy & Growth Playbook** panel at top (schedule, target groups, messaging, metrics). Post cards from `social/data/scheduled_posts.json`. Per-post actions: approve, remove approval, edit (inline textarea), investigate (AI explains why blocked), get alternative. **"▸ Details" toggle** on each post reveals full verification panel: data used, Gate 1 checks/warnings/errors, Gate 2 summary. **"Generate posts"** re-runs `social/generate_posts.py`. **"Approve all ready"** bulk-approves all non-blocked, unposted posts in one click.

**Model used:** `claude-sonnet-4-6`

## Web layer (web/)

### index.html — landing page
- Both signup forms POST to `https://field-notes-subscribe.neil-675.workers.dev/subscribe`
- No hardcoded audience IDs — Worker holds Resend credentials via Wrangler secrets
- Meta copy: "Free · Every Monday lunchtime"

### thankyou.html — post-signup page
- Confirmation + optional profile form (first name + role → POSTs to Worker `/update-profile`)
- 8-chapter East Anglia farming history narrative with scroll-reveal animation

### admin.html — dashboard UI
Served by `admin_server.py`. Not standalone.

## Cloudflare Worker (worker/)

**Deployed at:** `https://field-notes-subscribe.neil-675.workers.dev`

| Endpoint | What it does |
|---|---|
| `POST /subscribe` | Create Resend contact → send welcome email → redirect to /thankyou.html?e=email |
| `POST /update-profile` | Upsert Resend contact + save {email, first_name, role} to Cloudflare KV |

**Secrets (set via `wrangler secret put`):** `RESEND_API_KEY`, `RESEND_AUDIENCE_ID`

**CORS:** allows `fieldnoteseastanglia.co.uk` and `*.workers.dev`

## Manually curated files (Neil updates weekly)

| File | Format | Notes |
|---|---|---|
| `data/tech_watch.json` | `{headline, body, url, source}` | Editor's pick — no AI call |
| `data/community_events.json` | `[{title, organiser, date_start, location, url, description}]` or `[]` | Merged with events.py output |
| `data/fuel.json` | red diesel price | Injected into costs prompt |
| `data/sugar_beet.json` | British Sugar contract year, base price, factory dates | Injected into markets prompt if updated within 14 days |

## Key technical notes

- **Python 3.9** — no `str | None` union syntax, use `Optional[str]` from `typing`
- **`string.Template.safe_substitute()`** — intentional; leaves `{{unsubscribe_url}}` for Resend to fill
- **Issue number** auto-increments on every generate run — reset `data/issue_number.json` if inflated by testing
- **Model:** `claude-sonnet-4-6` across all three AI-calling components (generate.py, social/config.py, admin_server.py)
- **AHDB grain:** UK Corn Returns Excel (Azure Blob), Sheet "Spot", Eastern region row + UK average row
- **AHDB feed:** Excel export API requires `M/d/yyyy h:mm:ss AM` date format (not dd/mm/yyyy)
- **AHDB pig SPP:** `.xls` format (xlrd), wide layout — price at non_empty[1], change at non_empty[2]
- **AHDB milk:** sheet "UK average farmgate price", col1=date, col2=price
- **AHDB beef/eggs/poultry/sheep:** scraped via `_find_excel_url()` page-scraping helper (resilient to URL changes)
- **AHDB sheep/lamb SQQ:** deadweight prices from AHDB beef-and-lamb/prices-and-markets page; keywords `["sheep", "lamb", "deadweight", "sqq"]`
- **FW Jobs:** `li.lister__item` cards, filtered to East of England; jobs AI returns JSON, parsed by generate.py
- **land_listings.py:** Brown & Co + Savills parsed; Strutt & Parker returns [] (JS-rendered)
- **EDP/EADT block direct scraping** — `local_news.py` uses RSS feeds only
- **Met Office DataPoint optional** — falls back to Open-Meteo (no key needed), `forecast_days=7`
- **Norwich Livestock Market:** Joomla CMS, reports at `/component/content/article/8-reports/…`. Regex-parses narrative text for cattle head/avg and lamb sections (STANDARD/MEDIUM/HEAVY/HEAVY+/PRIME HOGGS). Reports can lag by several weeks.
- **Prefilter fallback chain:** `scrapers/filtered/news.json` preferred over `data/local_news.json`; `filtered/events_attend.json` + `filtered/events_online.json` preferred over `data/events.json`
- **Illustrations:** HTTPS URLs when `ASSETS_BASE_URL` set (email-safe); base64 fallback for local preview. Gmail strips `data:image/svg+xml;base64,...` — always send with ASSETS_BASE_URL.
- **Sources cited inline** in AI text as `[Label](URL)` — `_apply_inline_md()` converts to `<a>` tags
- **`text_to_html()`:** `## heading` → bold green `<p>`; `**bold**` → `<strong>`; `*italic*` → `<em>`; bullets → `<ul>` (blank lines between bullets do NOT close `<ul>`)
- **`_apply_inline_md()`:** `[text](url)` → `<a href style="color:#1b3a2d">`; `**bold**` → `<strong>`; `*italic*` → `<em>`
- **`build_price_table_html()`:** shows optional "UK Avg" column when `uk_average_price` present in grain data
- **`build_price_table_livestock_html()`:** 6-row table — pig SPP / milk / beef / sheep-lamb dwt / eggs / poultry
- **`build_norwich_market_html()`:** compact 3-column table (type / entry / average)
- **`build_event_cards_html()`:** merges events.json + community_events.json; strips leading title repetition from og:description
- **`community_events.json` can be `[]`** — handled by `isinstance(result, list)` check
- **`ea_alerts.json`:** injected into weather prompt context if present; empty list if no active alerts
- **`fuel.json` and `sugar_beet.json`:** injected conditionally (sugar_beet only if updated within 14 days)
- **Tech Watch:** no AI call — loaded directly from `data/tech_watch.json`
- **From the Soil:** no AI call — `items[issue_number % 52]` from `data/from_the_soil.json`
- **events.py:** `_fetch_description(url)` — do NOT pass `timeout=` kwarg to `get()` (base.get() sets its own 15s timeout; duplicate kwarg causes TypeError)
- **NEVER set `FROM_EMAIL` in shell** — `<>` breaks zsh. Always edit `.env` directly.
- **Preview browser:** `window.location` JS changes don't persist between `preview_eval` calls — use `window.scrollTo()` to navigate to sections
- **Gmail clip limit:** generate.py checks HTML size against 102,400 byte limit; logs warning at >85%
- **Confidence + verification sidecar:** `generate.py` captures confidence JSON from each AI section AND 2-gate verification results, merges them, and writes to `newsletter/output/*_confidence.json`. Each section entry now contains `{confidence, reason, data_gaps, commentary, verification: {gate1, gate2, status, status_color}}`. Admin dashboard section list shows verification-aware dots (green/amber/red) and clicking a section shows anomalies and Gate 2 notes in the chat panel.
- **Newsletter verification:** `newsletter/verify.py` runs Gate 1 (7 checks: required fields, price ranges, cross-commodity rules, week-on-week plausibility, data freshness, empty data guard, cross-week comparison vs data/previous/) before each AI call, then link verification + Gate 2 (AI cross-check) after. Config in `newsletter/validation_config.json`. Flagged sections get actionable review guidance with clickable source links (REVIEW_LINKS dict). AHDB domains are skipped for link checking (bot-blocked).

## Current status (27 March 2026)

| Area | Status |
|---|---|
| Newsletter pipeline | Fully working — 15 AI sections + 2-gate verification |
| Newsletter verification | NEW — Gate 1 (data validation) + Gate 2 (AI cross-check) per section |
| Sheep/lamb deadweight | NEW — scraper added, row in livestock table |
| National news balance | NEW — Tier 2 sources + 5 reserved national slots |
| 14 scheduled scrapers | All working |
| 22 prefilter scrapers | Working — scored/routed into scrapers/filtered/ |
| Social media pipeline | Built and ready — Facebook posts with 2-gate AI verification |
| Admin dashboard | Working — AI chat + verification display + full post review |
| Domain | `fieldnoteseastanglia.co.uk` verified ✓ |
| FROM_EMAIL | `Field Notes <hello@fieldnoteseastanglia.co.uk>` ✓ |
| Icons/assets | Served from `https://fieldnoteseastanglia.co.uk/assets` ✓ |
| Cloudflare Worker | Deployed at `neil-675.workers.dev` — subscribe + profile update |
| Welcome email | Live — sent by Worker on subscribe |
| Send time | Monday 12:30pm lunchtime (cron `30 12 * * 1`) |
| NEWSLETTER_ENV | `draft` — broadcast not yet sent |
| Issue counter | At 1 (reset from test inflation) |
| Live subscribers | Not yet — need to go live |

## Pending tasks

1. **First live send** — change `NEWSLETTER_ENV=live` in `.env`, confirm `RESEND_AUDIENCE_ID` is set
2. **Set up cron jobs** — `run_scrapers.sh` Sunday 8pm, `run_newsletter.sh` Monday 12:30pm
3. **Social cron** — run `bash social/cron_setup.sh` to install Facebook posting cron
4. **Weather API** — optionally add `MET_OFFICE_API_KEY` for Met Office DataPoint
5. **Issue counter** — reset to 1 before first real issue if inflated by more test runs

## Subscriber growth strategy

Priority order:
1. **NFU county branches** — Norfolk, Suffolk, Cambridgeshire — email county secretaries directly
2. **Facebook farming groups** — East Anglian Farming etc. — post sample issue, personal ask (social pipeline automates weekly posts)
3. **Cheffins auction days** — QR code card; already pulling their data so relationship exists
4. **Young Farmers Clubs** — county federations, digitally active
5. **LinkedIn agronomists** — they're present and will share with farmers they advise
6. **Agricultural colleges** — Easton & Otley, Writtle, Shuttleworth
7. **Norfolk + Suffolk Shows** — badge/card presence
8. **Weekly Twitter/X grain price post** — share price table with `#ukfarming`, drives organic discovery
9. **Public newsletter archive** — SEO for "East Anglia grain prices", "Norfolk farming news"
