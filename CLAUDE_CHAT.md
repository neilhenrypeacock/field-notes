# Field Notes: East Anglia — Project Knowledge File

_Upload this file to the Claude.ai Project. Update it at the end of any session where something changes._

---

## IDENTITY

**Name:** Field Notes: East Anglia
**Type:** Weekly AI-powered email newsletter
**Stack:** Python 3.9, Anthropic Claude API (`claude-sonnet-4-6`), Resend email API, Cloudflare Worker
**Status:** Fully functional. Domain live. Broadcasting not yet done. First live send pending.
**Purpose:** A free weekly farming intelligence briefing for East Anglian farmers. Saves ~2 hours of scrolling per week. Covers everything: grain prices, input costs, livestock markets, weather, grants, jobs, land, machinery, events.

---

## THE AUDIENCE

East Anglian farmers — primarily arable (wheat, barley, OSR, sugar beet), some mixed and livestock. Norfolk, Suffolk, Cambridgeshire. They are:
- Time-poor and practically minded
- Fluent in farming units (£/t, p/kg dwt, ppl, ex-farm, delivered)
- Distrustful of anything that feels like marketing or generalism
- They want numbers, deadlines, and "what does this mean for my margin this week"

---

## PRODUCT VISION

A trusted weekly briefing that eventually becomes a subscription product (free + paid tier). The AI handles all data aggregation and first-draft writing. Neil manages the pipeline, curates quality, and updates a few JSON files weekly.

---

## ARCHITECTURE (5 SYSTEMS)

| System | Entry point | What it does |
|---|---|---|
| Scraper pipeline | `run_scrapers.sh` | 14 scheduled scrapers + 22 prefilter scrapers → JSON data |
| Newsletter pipeline | `run_newsletter.sh` | 15 AI calls + 2-gate verification → HTML/TXT → Resend |
| Social media pipeline | `social/run_sunday.py` | 7 Facebook posts/week with 2-gate AI verification |
| Admin dashboard | `admin_server.py` (port 7657) | AI-assisted section editing + post review UI |
| Web layer | `web/` + `worker/` | Landing page, sign-up, Cloudflare Worker, thank-you |

---

## WEEKLY WORKFLOW

### Sunday evening
1. Run `run_scrapers.sh` — 14 scrapers write `data/*.json`, then prefilter.py scores/routes 22 more scrapers into `scrapers/filtered/`
2. Run `social/run_sunday.py` — generates 7 Facebook posts, review and approve in CLI

### Monday 12:30pm (cron)
1. `run_newsletter.sh` → `generate.py` (15 AI calls) → `send.py` (draft or live)

### Neil updates weekly (before Sunday scrape)
- `data/tech_watch.json` — `{headline, body, url, source}`
- `data/community_events.json` — `[{title, organiser, date_start, location, url, description}]` or `[]`
- `data/fuel.json` — red diesel price
- `data/sugar_beet.json` — British Sugar contract data (if campaign season)

---

## FULL TECH STACK

| Component | Version/Detail |
|---|---|
| Python | 3.9 (macOS) — no `str \| None` syntax, use `Optional[str]` |
| anthropic | Claude Sonnet 4.6 (`claude-sonnet-4-6`) — newsletter, social, admin all use this |
| resend | 2.26.0 — draft + broadcast modes |
| requests | 2.32.5 — HTTP session with polite delay + retry |
| beautifulsoup4 | 4.14.3 — HTML parsing |
| lxml | 5.3.0 — HTML parser for BeautifulSoup |
| feedparser | 6.0.11 — RSS/Atom feeds |
| openpyxl | 3.1.5 — .xlsx parsing |
| xlrd | 2.0.1 — .xls parsing (pig SPP data) |
| python-dotenv | 1.0.1 — .env loading |
| Template engine | `string.Template.safe_substitute()` — leaves `{{unsubscribe_url}}` for Resend |
| Email provider | Resend |
| Worker | Cloudflare Worker (`worker/index.js`) at `neil-675.workers.dev` |
| Domain | `fieldnoteseastanglia.co.uk` (Namecheap) — DNS verified 24 March 2026 |
| Asset hosting | `https://fieldnoteseastanglia.co.uk/assets` |

---

## WHERE EVERYTHING LIVES

```
/Users/neilpeacock/Projects/fieldnotes/    Main project (all code, data, web)
```

---

## FILE STRUCTURE

```
fieldnotes/
├── admin_server.py               Local admin server (port 7657)
├── generate_brand_svgs.py        One-off: regenerate brand SVGs/PNGs
├── keywords.txt                  Keyword filter tiers (A/B/C)
├── run_newsletter.sh             Cron Monday 12:30pm: generate + send
├── run_scrapers.sh               Cron Sunday 8pm: scrapers + prefilter
├── run_daily_check.sh            Cron daily 6am: RSS monitor
│
├── scrapers/
│   ├── base.py                   Shared HTTP session, save_data(), archive_current()
│   ├── utils.py                  load_keywords(), score_article()
│   ├── [14 scheduled scrapers]   ahdb_grain, met_office, defra_blog, govuk_schemes,
│   │                             ahdb_fertiliser, ahdb_livestock, norwich_livestock,
│   │                             ahdb_feed, land_listings, jobs, local_news,
│   │                             events, machinery_auctions, ea_alerts
│   ├── [22 prefilter scrapers]   anglia_farmer, ea_bylines, nfu_east, itv_anglia,
│   │                             british_sugar, camgrain, water_resources_east,
│   │                             events_extended, farmers_weekly, farmers_guardian,
│   │                             farmers_guide, agriland, farming_uk, farming_monthly,
│   │                             cpm, aafarmer, frontier_ag, aic, nffn, chap,
│   │                             ukagritech, agrifunder
│   └── filtered/                 Scored/routed output (11 category JSON files)
│
├── data/
│   ├── [13 scraper outputs]      ahdb_grain, ahdb_livestock, ahdb_feed, ahdb_fertiliser,
│   │                             met_office, defra_blog, govuk_schemes, norwich_livestock,
│   │                             land_listings, jobs, local_news, events, machinery_auctions
│   ├── ea_alerts.json            EA Flood Monitoring alerts
│   ├── fuel.json                 Red diesel — Neil updates manually
│   ├── sugar_beet.json           British Sugar contract — Neil updates manually
│   ├── issue_number.json         {"current": N}
│   ├── community_events.json     Local events — Neil updates weekly
│   ├── tech_watch.json           Editor's pick — Neil updates weekly
│   ├── from_the_soil.json        52 pre-written narratives (rotates by issue %)
│   └── previous/                 Last week's data for week-on-week comparisons
│
├── newsletter/
│   ├── generate.py               Orchestrator: 15 AI calls + 2-gate verification → HTML + TXT
│   ├── verify.py                 2-gate verification (Gate 1: data rules, Gate 2: AI cross-check)
│   ├── validation_config.json    Price ranges, cross-commodity rules, freshness thresholds
│   ├── prefilter.py              22-scraper scoring pipeline → scrapers/filtered/
│   ├── send.py                   Resend sender (draft or broadcast)
│   ├── template.html             HTML email (640px, v2 design)
│   ├── template_plain.txt        Plain-text fallback
│   ├── assets/                   15 watercolour SVGs
│   └── output/                   Generated .html + .txt + _confidence.json (with verification)
│
├── prompts/                      13 AI prompt files (one per section)
│
├── social/
│   ├── config.py                 Settings: schedule, model, FB API, hashtags
│   ├── generate_posts.py         Main: scrape → write → verify → save
│   ├── run_sunday.py             Full Sunday workflow in one command
│   ├── review_posts.py           Interactive CLI review
│   ├── schedule_posts.py         Posts approved items at scheduled times
│   ├── run.py                    Cron script for posting
│   ├── update_prompt.py          Prompt improvement researcher
│   ├── verify.py                 2-gate AI verification
│   ├── facebook_client.py        Facebook Graph API v19.0
│   ├── buffer_client.py          Buffer API alternative
│   ├── cron_setup.sh             Install cron (dynamic path detection)
│   └── data/                     scheduled_posts.json, post_prompt.txt, history/
│
├── monitor/
│   └── daily_check.py            Daily RSS monitor → changelog.json
│
├── web/
│   ├── assets/                   15 SVGs served from domain
│   ├── index.html                Landing page (both forms → Worker endpoint)
│   ├── admin.html                Admin dashboard UI
│   └── thankyou.html             Post-signup page + 8-chapter EA history
│
└── worker/
    ├── index.js                  Cloudflare Worker: subscribe + update-profile
    └── wrangler.toml             Worker config
```

---

## HOW THE NEWSLETTER PIPELINE WORKS

### Step 1 — Scrapers (Sunday 8pm, run_scrapers.sh)
14 scrapers run in priority order + prefilter.py. Each scraper:
1. `archive_current()` — copies current JSON to `data/previous/`
2. Fetches live data
3. `save_data()` — atomically writes `data/*.json` with `last_updated`

Then `prefilter.py` imports 22 additional scrapers, scores each article (Tier A +3, B +1, C -5), caps by category (news 20, markets 15, events_attend 15, etc.), writes to `scrapers/filtered/`.

### Step 2 — Generate (Monday 12:30pm, run_newsletter.sh)
`generate.py` orchestrates:
1. Load 16+ data JSONs — prefers `scrapers/filtered/` over `data/` for news and events
2. Load tech_watch, from_the_soil directly (no AI)
3. Make 15 Claude Sonnet 4.6 calls (13 sections + this_week_hooks + fieldwork_verdict)
4. Build HTML price tables, weather table, event cards, job cards
5. Conditionally include/exclude events, land, machinery, tech watch, regulatory sections
6. Substitute variables into `template.html` using `string.Template.safe_substitute()`
7. Save to `newsletter/output/`
8. Increment `data/issue_number.json`

### Step 3 — Send (run_newsletter.sh, immediately after generate)
- `NEWSLETTER_ENV=draft` → email to `DRAFT_EMAIL` only
- `NEWSLETTER_ENV=live` → broadcast to `RESEND_AUDIENCE_ID`

Subject: `Field Notes: East Anglia | Monday {date} — {first bullet of At a Glance}`

---

## SOCIAL MEDIA PIPELINE

Generates 7 Facebook posts/week. Sunday workflow (manual):
```
.venv/bin/python social/run_sunday.py
```
1. `update_prompt.py` — researches best practices, proposes prompt improvements
2. `generate_posts.py` — reads scraped data, writes 7 posts with 2-gate AI verification
   - Gate 1: confidence check (LOW → flagged, not blocked)
   - Gate 2: number accuracy (mismatch → auto-blocked)
3. `review_posts.py` — interactive CLI: approve / edit / block / get alternative (or use admin dashboard — see below)

Posts are then scheduled via `social/schedule_posts.py` (cron via `social/cron_setup.sh`).

**Digest email:** After generating, `digest_email.py` sends a summary to `DIGEST_EMAIL` via SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`).

---

## ALL 15 NEWSLETTER SECTIONS

### 1. At a Glance
- **Data:** All scraped data combined
- **AI output:** Exactly 3 bullets, max 25 words each. Mix of sectors. Verb or number first.

### 2. Markets — What You're Selling
- **Data:** `ahdb_grain.json` + optional `sugar_beet.json` (if updated within 14 days)
- **AI output:** Lead with biggest movement. Eastern price first. 120 words max.
- **Table:** Commodity / This Week / Last Week / Change / UK Avg (optional)

### 3. Costs — What You're Paying
- **Data:** `ahdb_fertiliser.json` + `ahdb_feed.json` + optional `fuel.json`
- **AI output:** Fertiliser + feed + red diesel movements. 100 words max.
- **Table:** Fertiliser prices

### 4. Margin Watch
- **Data:** Wheat price + fertiliser
- **AI output:** Factual only. Wheat price, key input costs, indicative margin. NO advice. 3–4 sentences.
- **Rendered:** Gold badge, gold-bordered box, traffic light dot

### 5. Livestock & Dairy
- **Data:** `ahdb_livestock.json` + `norwich_livestock.json`
- **AI output:** All sectors. 120 words max.
- **Tables:** AHDB 5-row table + Norwich Market table
- **CTA:** "Email us with your prices"

### 6. Schemes & Grants
- **Data:** `govuk_schemes.json` + `defra_blog.json`
- **AI output:** SFI, CS, capital grants, deadlines. 130 words max.
- **CTA:** JustFarm link (hardcoded in template)

### 7. Weather
- **Data:** `met_office.json` + optional `ea_alerts.json`
- **AI output:** Fieldwork verdict: spraying window? Drilling? Frost? Rain? 40–50 words.
- **Also:** Fieldwork verdict box (traffic light) + 7-day table

### 8. Community & Events
- **Data:** `scrapers/filtered/events_attend.json` + `filtered/events_online.json` + `community_events.json`
- **AI output:** 1–2 sentence intro, 40 words max. Does NOT list events.
- **Also:** Python-built event cards + YANA strip

### 9. Land & Property
- **Data:** `land_listings.json`
- **AI output:** EA only. Total acreage, standouts, price-per-acre. 90 words max.

### 10. Jobs
- **Data:** `jobs.json`
- **AI output:** JSON: `[{title, employer, location, why, url}]` — 3–5 roles
- **Rendered:** Job cards with inline Apply links

### 11. Machinery & Auctions
- **Data:** `machinery_auctions.json`
- **AI output:** Sale names, dates, context. 60 words max.

### 12. Tech Watch
- **Data:** `data/tech_watch.json` — Neil updates weekly
- **AI call:** None — loaded directly
- **Format:** Headline (bold green) + body + source link

### 13. Regulatory & Health
- **Data:** `defra_blog.json` + `local_news.json`
- **AI output:** Disease alerts, NVZ, pesticides, HSE. 100 words max. Returns "SKIP" if nothing to report.

### 14. One Good Read
- **Data:** `local_news.json` + At a Glance context (to avoid duplicating top stories)
- **AI output:** `[Article Title](URL)` — publication — one-sentence reason. 50 words max.

### 15. From the Soil
- **Data:** `data/from_the_soil.json` — 52 pre-written narratives
- **AI call:** None — `items[issue_number % 52]`
- **Rendered:** Gold top border, italic Source Serif 4

---

## DESIGN SYSTEM

### Colours
| Token | Hex | Role |
|---|---|---|
| Dark green | `#1b3a2d` | Section badges, table headers, links, CTA buttons |
| Gold | `#d4a853` | Margin Watch + One Good Read badges, hero subtitle, From the Soil divider |
| Lighter green | `#263f32` | Legend strip, forward banner |
| Page bg | `#f2f0eb` | Outer email background |
| Warm white | `#ffffff` | Content area |
| Divider bg | `#f7f5f0` | Section dividers, data sources |
| Body text | `#333333` | Standard paragraphs |
| Green signal | `#2e7d32` | Price increase, low-rain rows |
| Red signal | `#c62828` | Price decrease, high-rain rows |

### Typography
| Font | Use |
|---|---|
| Playfair Display | Masthead, Margin Watch label, forward banner |
| Source Sans 3 | Body, labels, badges, At a Glance, Events, Jobs, Tech Watch |
| Source Serif 4 | Markets, Costs, Margin Watch, Livestock, Schemes, Weather, Land, Machinery, Regulatory, One Good Read, From the Soil |

---

## BUSINESS LOGIC

### Shared AI context (injected into every call)
> "You are writing a section of 'Field Notes: East Anglia', a free weekly farming intelligence newsletter for professional arable and mixed farmers in Norfolk, Suffolk, and Cambridgeshire. Readers are experienced farming professionals who want facts, numbers, and practical implications — not general explanations or hedging. Use farming-specific language where appropriate (ex-farm, delivered, p/kg dwt, £/t, week-on-week). Be concise and direct. Today's date: {date}."

### Tone rules
- Facts and numbers first — never hedge, never speculate
- No advice — never "consider selling", "you should", "we recommend"
- Farming units always — `p/kg dwt`, `ppl`, `p/doz`, `£/t ex-farm`
- East Anglia specificity — Norfolk poultry/eggs, north Norfolk dairy, pig sector, sugar beet, malting barley
- Inline citations only — `[Label](URL)`, 1–2 words, one per source per section

### Markdown rendering pipeline
`text_to_html(text)`:
- `## heading` → `<p style="font-weight:700;color:#1b3a2d;">`
- Bullets → `<ul><li>` (blank lines do NOT close `<ul>`)
- Paragraphs → `<p style="margin:0 0 10px;">`

`_apply_inline_md(text)`:
- `[text](url)` → `<a href="url" style="color:#1b3a2d;text-decoration:underline;">`
- `**bold**` → `<strong>`, `*italic*` → `<em>`

---

## CURRENT STATUS (27 March 2026)

| Area | Status |
|---|---|
| All 14 scheduled scrapers | Working |
| 22 prefilter scrapers | Working — routed to scrapers/filtered/ |
| Newsletter generation | Fully working — 15 AI sections + 2-gate verification |
| Newsletter verification | NEW — Gate 1 (data rules) + Gate 2 (AI cross-check) per section |
| Sheep/lamb deadweight | NEW — added to ahdb_livestock.py scraper + livestock table |
| National news balance | NEW — Tier 2 sources + 5 reserved national slots in news bucket |
| Email sending | Working — drafts to neil@neilpeacock.co.uk |
| Domain | Verified ✓ — `fieldnoteseastanglia.co.uk` |
| FROM_EMAIL | `Field Notes <hello@fieldnoteseastanglia.co.uk>` ✓ |
| Icons/assets | Served from `https://fieldnoteseastanglia.co.uk/assets` ✓ |
| Cloudflare Worker | Deployed — subscribe + welcome email + profile update |
| Social media pipeline | Built and ready for first run |
| Admin dashboard | Working — AI chat + verification display + full post review |
| Issue counter | At 1 (reset) |
| NEWSLETTER_ENV | `draft` — broadcast not yet tested |
| Live subscribers | Not yet |

## PENDING TASKS

1. **First live send** — set `NEWSLETTER_ENV=live`, confirm `RESEND_AUDIENCE_ID` is set
2. **Set up cron** — `run_scrapers.sh` Sunday 8pm, `run_newsletter.sh` Monday 12:30pm (`30 12 * * 1`)
3. **Social cron** — `bash social/cron_setup.sh`
4. **Issue counter** — confirm at 1 before first real send
5. **Weather API** — optionally add `MET_OFFICE_API_KEY`

---

## KEY TECHNICAL GOTCHAS

1. **Gmail strips base64 `<img>` tags** — always use HTTPS via `ASSETS_BASE_URL`; never send with blank `ASSETS_BASE_URL`
2. **Python 3.9 syntax** — `Optional[str]` not `str | None`
3. **`string.Template.safe_substitute()`** — intentional; preserves `{{unsubscribe_url}}`
4. **Issue number increments every generate run** — not idempotent; reset manually after testing
5. **`FROM_EMAIL` in shell** — `<>` breaks zsh; always set in `.env` directly
6. **`base.get()` sets its own timeout** — never pass `timeout=` kwarg; causes TypeError
7. **AHDB feed API date format** — must be `M/d/yyyy h:mm:ss AM`
8. **AHDB pig SPP** — `.xls` not `.xlsx`; use xlrd; wide sparse layout
9. **AHDB beef/eggs/poultry URLs rotate** — use `_find_excel_url()` helper; don't hardcode Azure blob URLs
10. **EDP/EADT block direct scraping** — `local_news.py` must use RSS only
11. **Norwich Market reports lag** — may be weeks old; scraper picks up latest automatically
12. **`community_events.json` can be `[]`** — `isinstance(result, list)` check before merging
13. **Prefilter fallback chain** — `scrapers/filtered/` preferred; `data/local_news.json` and `data/events.json` are fallbacks only
14. **Blank lines in AI output** — `text_to_html()` does NOT close `<ul>` on blank lines
15. **Admin auth redirect** — password base64-encoded in URL hash for HTTPS→localhost redirect; immediately cleared with `history.replaceState()`

---

## RUNNING COSTS

| Cost | Amount |
|---|---|
| Anthropic API | ~$0.20 per newsletter (15 Sonnet 4.6 calls) |
| Resend | Free up to 3,000 subscribers/month |
| Domain (Namecheap) | ~£8/yr |
| Cloudflare Worker | Free tier |

---

## HOW TO RUN

```bash
cd /Users/neilpeacock/Projects/fieldnotes
source .venv/bin/activate

# Generate newsletter
python newsletter/generate.py

# Send draft
python newsletter/send.py

# Run a single scraper
python scrapers/norwich_livestock.py

# Run all scrapers (as cron would)
bash run_scrapers.sh

# Sunday social pipeline
python social/run_sunday.py

# Admin dashboard
python admin_server.py
```

---

## ABOUT NEIL

- Neil Peacock — building and running this himself
- Technical but not a professional developer — prefers clear explanations over jargon
- Based in East Anglia, farmer's son
- Draft email: neil@neilpeacock.co.uk
- Domain registrar: Namecheap

---

## ADMIN DASHBOARD

Start: `.venv/bin/python admin_server.py` → `http://localhost:7657/admin`
Password: `fieldnotes2026`

### Newsletter tab
- Renders latest generated HTML inline
- **Confidence bar** — colored chips for each AI section (green ≥0.9, amber 0.75–0.9, red <0.75), with reason on hover. Loaded from `newsletter/output/*_confidence.json` sidecar.
- Click any section to open AI chat panel — ask questions or request rewrites
- "Regenerate newsletter" button re-runs `generate.py`

### Facebook Posts tab
- Shows `social/data/scheduled_posts.json`
- Per-post: approve, remove approval, inline edit, investigate (AI explains block), get alternative
- **"▸ Details"** toggle reveals verification panel: data table + Gate 1 checks + Gate 2 summary
- **"Generate posts"** button — re-runs `social/generate_posts.py`
- **"✓ Approve all ready"** button — bulk-approves all non-blocked unposted posts

---

_Last updated: 26 March 2026 — dashboard improvements + confidence visibility + 48hr changes._
