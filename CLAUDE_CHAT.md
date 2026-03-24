# Field Notes: East Anglia — Project Knowledge File

_Upload this file to the Claude.ai Project. Update it at the end of any session where something changes._

---

## IDENTITY

**Name:** Field Notes: East Anglia
**Type:** Weekly AI-powered email newsletter
**Stack:** Python 3.9, Anthropic Claude API, Resend email API
**Status:** Fully functional — sending draft issues. Domain DNS pending. Broadcast not yet live.
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

A trusted weekly briefing that eventually becomes a subscription product (free + paid tier). The AI handles all data aggregation and first-draft writing. Neil manages the pipeline, curates quality, and updates two JSON files weekly.

---

## FULL TECH STACK

| Component | Version/Detail |
|---|---|
| Python | 3.9 (macOS) — no `str \| None` syntax, use `Optional[str]` |
| anthropic | 0.84.0 — `claude-sonnet-4-5`, 13 calls per issue |
| resend | 2.26.0 — draft + broadcast modes |
| requests | 2.32.5 — HTTP session with polite delay + retry |
| beautifulsoup4 | 4.14.3 — HTML parsing |
| lxml | 5.3.0 — HTML parser for BeautifulSoup |
| feedparser | 6.0.11 — RSS/Atom feeds |
| openpyxl | 3.1.5 — .xlsx parsing |
| xlrd | 2.0.1 — .xls parsing (pig SPP data) |
| python-dotenv | 1.0.1 — .env loading |
| Template engine | `string.Template.safe_substitute()` — leaves `{{unsubscribe_url}}` for Resend |
| Email provider | Resend (resend.com) |
| Icon hosting | GitHub raw CDN: `neilhenrypeacock/field-notes-assets` (public repo) |
| Domain | `fieldnoteseastanglia.co.uk` (Namecheap) — DNS pending |

---

## WHERE EVERYTHING LIVES

```
/Users/neilpeacock/farm/field-notes/       Main project code
/Users/neilpeacock/Projects/fieldnotes/    Claude reference files (CLAUDE.md, CLAUDE_CHAT.md, LESSONS.md)
```

---

## FILE STRUCTURE

```
field-notes/
├── .env                          API keys + config (never commit)
├── .env.example                  Template
├── requirements.txt              All Python deps, pinned versions
├── run_newsletter.sh             Cron Monday 5am UTC: generate + send
├── run_scrapers.sh               Cron Sunday 8pm UTC: all 13 scrapers
├── run_daily_check.sh            Cron daily 6am UTC: RSS monitor
│
├── scrapers/
│   ├── base.py                   Shared: HTTP session, retry logic, save_data(), archive_current()
│   ├── ahdb_grain.py             UK Corn Returns Excel — feed wheat, milling wheat, feed barley + UK average
│   ├── ahdb_livestock.py         Pig SPP, milk farmgate, beef deadweight, egg prices, poultry
│   ├── ahdb_feed.py              Feed commodity prices (Excel export API)
│   ├── ahdb_fertiliser.py        Fertiliser prices
│   ├── met_office.py             7-day weather via Open-Meteo (Met Office DataPoint optional)
│   ├── defra_blog.py             Defra Farming Blog posts
│   ├── govuk_schemes.py          GOV.UK Farming Schemes Atom feed
│   ├── local_news.py             East Anglia farming news (EDP/EADT RSS only — site blocks scraping)
│   ├── machinery_auctions.py     Cheffins auction listings
│   ├── events.py                 Local farming events + og:description fetch per event
│   ├── jobs.py                   Farmers Weekly East of England jobs
│   ├── land_listings.py          Brown & Co property search listings
│   └── norwich_livestock.py      Norwich Livestock Market weekly sale report
│
├── data/
│   ├── ahdb_grain.json
│   ├── ahdb_livestock.json
│   ├── ahdb_feed.json
│   ├── ahdb_fertiliser.json
│   ├── met_office.json
│   ├── defra_blog.json
│   ├── govuk_schemes.json
│   ├── local_news.json
│   ├── machinery_auctions.json
│   ├── events.json
│   ├── jobs.json
│   ├── land_listings.json
│   ├── norwich_livestock.json
│   ├── issue_number.json         {"current": 18} — resets manually before live send
│   ├── community_events.json     [] or list of event objects (Neil updates weekly)
│   ├── tech_watch.json           {headline, body, url, source} (Neil updates weekly)
│   ├── from_the_soil.json        52 pre-written ~100-word narrative stories
│   └── previous/                 Last week's data for week-on-week comparisons
│
├── newsletter/
│   ├── generate.py               Main orchestrator — loads data, calls AI, builds HTML + plain text
│   ├── send.py                   Resend sender — draft mode or broadcast
│   ├── template.html             HTML email template (640px, table-based, no divs)
│   ├── template_plain.txt        Plain text fallback
│   ├── assets/                   15 watercolour SVGs (source files)
│   └── output/                   Generated field_notes_YYYY_MM_DD.html + .txt
│
├── prompts/                      13 AI prompt files (one per section)
│   ├── at_a_glance.txt
│   ├── markets.txt
│   ├── costs.txt
│   ├── margin_watch.txt
│   ├── livestock.txt
│   ├── schemes_grants.txt
│   ├── weather.txt
│   ├── events.txt
│   ├── land_property.txt
│   ├── jobs.txt
│   ├── machinery.txt
│   ├── regulatory.txt
│   └── one_good_read.txt
│
├── monitor/
│   └── daily_check.py            Daily RSS check for urgent Defra/scheme alerts
│
├── logs/
│   ├── ai_usage.json             Last 200 Claude API calls (section, tokens, timestamp)
│   └── send_log.json             Send history (mode, Resend ID, recipients)
│
└── web/
    ├── assets/                   15 SVGs served from domain (mirrors newsletter/assets/)
    └── index.html                Landing page
```

---

## HOW THE PIPELINE WORKS

### Step 1 — Scrapers (Sunday 8pm, run_scrapers.sh)
13 scrapers run in priority order. Each scraper:
1. Calls `archive_current()` — copies current JSON to `data/previous/` for week-on-week comparisons
2. Fetches live data from its source
3. Calls `save_data()` — atomically writes `data/*.json` with `last_updated` timestamp

`base.py` provides: shared requests Session with polite 1–2s random delay, 3 retries with exponential backoff, 15s timeout, FieldNotes/1.0 user agent.

### Step 2 — Generate (Monday 5am, run_newsletter.sh)
`generate.py` orchestrates:
1. Load all data JSONs
2. Load `tech_watch.json` and `from_the_soil.json` directly (no AI)
3. Make 13 Claude Sonnet API calls (one per section)
4. Build HTML price tables and event cards in Python
5. Substitute all `$variables` into `template.html` using `string.Template.safe_substitute()`
6. Save `newsletter/output/field_notes_YYYY_MM_DD.html` and `.txt`
7. Increment `data/issue_number.json`

### Step 3 — Send (Monday 5am, immediately after generate)
`send.py`:
- `NEWSLETTER_ENV=draft` → `resend.Emails.send()` to `DRAFT_EMAIL` only
- `NEWSLETTER_ENV=live` → `resend.Broadcasts.create()` + `resend.Broadcasts.send()` to full audience

Subject line built from: `Field Notes: East Anglia | Monday 23 March — {first bullet of At a Glance}`

---

## ALL 15 SECTIONS

### 1. At a Glance
- **Data:** All scraped data combined
- **AI output:** Exactly 3 bullets, max 25 words each. Mix of sectors required (markets + weather + policy). Verb or number first. No intro/outro.
- **Rendered:** `text_to_html()` → `<ul><li>` bullets

### 2. Markets — What You're Selling
- **Data:** `ahdb_grain.json` — feed wheat, milling wheat, feed barley (Eastern region + UK average)
- **AI output:** Lead with biggest movement. Eastern price first. Only compare to UK avg if diff >£2/t. Cite `[AHDB](https://ahdb.org.uk/cereals-oilseeds/uk-corn-returns)` inline. 120 words max.
- **Also:** Python-built price table: Commodity / This Week / Last Week / Change / UK Avg (optional)
- **Font:** Source Serif 4

### 3. Costs — What You're Paying
- **Data:** `ahdb_fertiliser.json` + `ahdb_feed.json`
- **AI output:** Fertiliser + feed commodity movements. Note UK national figures once. Cite `[AHDB]` per source inline. 100 words max.
- **Also:** Fertiliser price table
- **Font:** Source Serif 4

### 4. Margin Watch
- **Data:** Wheat price + fertiliser (combined)
- **AI output:** Factual only. State wheat price, key input costs, indicative margin vs EA cost of production (£160–180/t). State positive/negative/tight. NO advice. 3–4 sentences.
- **Rendered:** Gold badge (`#d4a853`), gold-bordered box (`background:#fdf8ee; border-left:4px solid #d4a853`)
- **Font:** Source Serif 4

### 5. Livestock & Dairy
- **Data:** `ahdb_livestock.json` (pig SPP p/kg dwt, milk ppl, beef p/kg dwt, eggs p/doz, poultry) + `norwich_livestock.json`
- **AI output:** Lead with biggest movement. Cover all sectors with data. Cite `[AHDB]` and `[Norwich Market]` inline. 120 words max. Facts only, no advice.
- **Also:** AHDB price table (5 rows: pig / milk / beef / eggs / poultry) + Norwich Market table
- **Norwich Market table:** Type / Entry / Average — rows for store cattle + each lamb weight class (prime hoggs, standard, medium, heavy, heavy+)
- **Hardcoded CTA:** *"Do you have local farm-gate prices to share? Email us — we feature reader data when available."*
- **Font:** Source Serif 4

### 6. Schemes & Grants
- **Data:** `govuk_schemes.json` + `defra_blog.json`
- **AI output:** SFI, CS, capital grants, imminent deadlines. Plain English. Specific payment rates. Bold deadlines. Bullets for multiple items. Cite `[DEFRA](exact_article_URL)` inline. 130 words max.
- **Hardcoded CTA:** *"Not sure which schemes you qualify for? Check your eligibility at JustFarm →"* (https://justfarm.app)
- **Font:** Source Serif 4

### 7. Weather — Your Week Ahead
- **Data:** `met_office.json` — 7-day Open-Meteo forecast
- **AI output:** Answer: Is there a spraying window? Fit for drilling? Frost risk? How much rain? Farmer language (not "precipitation"). Cite `[Met Office]` inline. 100 words max.
- **Also:** 7-day weather table — colour-coded rows by rain probability
- **Font:** Source Serif 4

### 8. Community & Events
- **Data:** `events.json` + `community_events.json`
- **AI output:** 1–2 sentence intro only — set the scene, time of year. Do NOT list events. If no events, direct to rnaa.org.uk / norfolkyfc.co.uk / NFU East Anglia. 40 words max.
- **Also:** Python-built event cards (one per event): title / date·location·organiser / description / "More info →" button
- **Hardcoded:** YANA support strip (mental health — always present, never remove) + "get featured" email CTA
- **Font:** Source Sans 3

### 9. Land & Property
- **Data:** `land_listings.json` — Brown & Co
- **AI output:** EA only (Norfolk/Suffolk/Cambridgeshire). Open with "This week's listings from [Brown & Co](URL):". Total acreage, standouts, price-per-acre. Skip non-EA. 90 words max.
- **Font:** Source Serif 4

### 10. Jobs — East of England
- **Data:** `jobs.json` — Farmers Weekly
- **AI output:** Open with "Jobs from [Farmers Weekly](URL):". 3–5 roles (prefer management/technical). Title, employer, location, salary, one sentence why interesting. `[Apply →](URL)` inline per job. 120 words max.
- **Font:** Source Sans 3

### 11. Machinery & Auctions
- **Data:** `machinery_auctions.json` — Cheffins
- **AI output:** Sale names, dates, type. One sentence context per sale. `[Cheffins](catalogue_URL)` inline. FETF note if open. 60 words max.
- **Font:** Source Serif 4

### 12. Tech Watch
- **Data:** `data/tech_watch.json` — Neil updates manually every week
- **AI call:** None — loaded directly from JSON
- **Format:** `{headline, body, url, source}` → headline (bold green) + body + source link
- **Font:** Source Sans 3

### 13. Regulatory & Health
- **Data:** `defra_blog.json` + `local_news.json`
- **AI output:** Disease alerts, NVZ changes, pesticide news, HSE alerts, Red Tractor, compliance deadlines. Flag urgent. No grant info. Cite `[DEFRA](exact_article_URL)`. 100 words max.
- **Font:** Source Serif 4

### 14. One Good Read
- **Data:** `local_news.json` + extra context (At a Glance bullets, to avoid repetition)
- **AI output:** Single best article for an EA farmer. Format: `[Article Title](URL)`, publication name, one-sentence reason. 50 words max. Title must be an inline link. Never the same story as At a Glance.
- **Rendered:** In `background:#fdf8ee` warm box, Source Serif 4

### 15. From the Soil
- **Data:** `data/from_the_soil.json` — 52 pre-written narrative stories
- **AI call:** None — `items[issue_number % 52]`
- **Content:** ~100-word narratives: scene → surprising fact → significance today. Categories: history, soil science, heritage breeds, seasonal fieldwork, notable figures, farming firsts. All East Anglia specific.
- **Rendered:** Gold top border, "FROM THE SOIL" label (gold tracked caps), italic Source Serif 4 `color:#666`

---

## EMAIL STRUCTURE (top to bottom)

| Element | Background | Notes |
|---|---|---|
| Preview text | hidden | From At a Glance bullet 1, ≤80 chars + zero-width joiners |
| Hero banner | `#1b3a2d` | Map SVG + Playfair masthead + date/issue chip |
| Legend strip | `#263f32` | Italic blurb, gold bottom border — hardcoded, never changes |
| Table of contents | `#ffffff` | 15 linked sections, emoji icons |
| Share strip | `#f0f7f2` | Two-column: text left, "Forward this →" right — prevents wrapping |
| 15 content sections | `#ffffff` | 44px h-padding, separated by ◆ ◆ ◆ dividers |
| Data Sources | `#f7f5f0` | Two-column, all 13 sources listed |
| Forward banner | `#263f32` | Playfair gold "Forward this email — it's free." |
| Footer | `#ffffff` | Legal, contact, `{{unsubscribe_url}}` (Resend fills at send time) |

---

## DESIGN SYSTEM

### Colours

| Token | Hex | Role |
|---|---|---|
| Dark green | `#1b3a2d` | Section badge backgrounds, table headers, links, CTA buttons |
| Gold | `#d4a853` | Margin Watch + One Good Read badges, hero subtitle, From the Soil divider |
| Lighter green | `#263f32` | Legend strip, forward banner |
| Page bg | `#f2f0eb` | Outer email background |
| Warm white | `#ffffff` | Content area |
| Divider bg | `#f7f5f0` | Section dividers, data sources strip |
| Divider rule | `#e0dbd0` | 1px lines flanking ◆ ◆ ◆ |
| Body text | `#333333` | Standard paragraphs |
| Muted text | `#9a8e7d` | Source captions |
| Green signal | `#2e7d32` | Price increase arrows, weather table low-rain rows |
| Red signal | `#c62828` | Price decrease arrows, weather table high-rain rows |
| Grey signal | `#666666` | No change |
| Share bg | `#f0f7f2` | Share strip |
| Share border | `#d4e8d9` | Share strip border |
| Margin box bg | `#fdf8ee` | Margin Watch + One Good Read inner box |
| Margin border | `#e8dcc4` | Margin Watch box border |

### Typography

| Font | Weight | Use |
|---|---|---|
| Playfair Display | 700, 900 | Masthead "Field Notes" (900), "East Anglia" (700), "Margin Indicator" label (700), forward banner (700) |
| Source Sans 3 | 400, 600, 700 | All body text, labels, badges, section badges, At a Glance, Events, Jobs, Tech Watch |
| Source Serif 4 | 400 regular + italic, 600 | Markets, Costs, Margin Watch, Livestock, Schemes, Weather, Land, Machinery, Regulatory, One Good Read, From the Soil |

### Section badge pattern
```html
<td style="background-color:#1b3a2d;border-radius:4px;padding:14px 20px 14px 12px;" valign="middle">
  <!-- 36×36px SVG icon + 12px white 700-weight uppercase letter-spacing:1.5px label -->
```
Margin Watch and One Good Read use `#d4a853` gold instead of dark green.

### Price table pattern
```html
<!-- Header: background-color:#1b3a2d, white text, 11px uppercase, letter-spacing:0.5px -->
<!-- Alternating rows: #ffffff / #faf8f4 -->
<!-- Change column: colour from _change_colour(change) — green/red/grey -->
<!-- Border: 1px solid #e8e2d6, border-radius:6px -->
```

---

## DATA MODEL

### ahdb_grain.json
```json
{
  "prices": [
    {
      "commodity": "Feed Wheat",
      "spot_price": 168.50,
      "prev_week_price": 167.00,
      "change": 1.50,
      "change_pct": 0.9,
      "uk_average_price": 165.75,
      "region": "Eastern"
    }
  ],
  "last_updated": "2026-03-23T19:00:00Z"
}
```

### ahdb_livestock.json
```json
{
  "pig_prices": {"price": 185.3, "prev_week_price": 184.1, "change": 1.2},
  "milk_prices": {"price": 34.5, "prev_period_price": 34.1, "change": 0.4},
  "beef_prices": {"price": 420.0, "prev_week_price": 418.0, "change": 2.0},
  "egg_prices": {"price": 125.0, "prev_week_price": 123.0, "change": 2.0},
  "poultry_prices": {"note": "Market commentary text"},
  "last_updated": "..."
}
```

### norwich_livestock.json
```json
{
  "url": "https://www.norwichlivestockmarket.com/component/content/article/...",
  "sale_date_text": "Wednesday 19th February 2025",
  "cattle_total_head": 153,
  "store_cattle_avg_gbp": null,
  "sheep_total_head": 456,
  "lambs": {
    "standard": {"head": 70, "avg_ppkg": 353.1, "avg_gbp": 130.00},
    "medium": {"head": 201, "avg_ppkg": 380.0, "avg_gbp": 145.00},
    "heavy": {"head": 137, "avg_ppkg": 395.0, "avg_gbp": 155.00},
    "heavy_plus": {"head": 48, "avg_ppkg": 410.0},
    "prime_hoggs": {"head": 30, "avg_ppkg": 420.0}
  },
  "source": "Norwich Livestock Market",
  "source_url": "https://www.norwichlivestockmarket.com/reports",
  "last_updated": "..."
}
```

### events.json
```json
{
  "events": [
    {
      "title": "Agriculture for Innovators",
      "date_start": "2026-04-15",
      "location": "Norwich",
      "organiser": "Agri-TechE",
      "url": "https://...",
      "description": "A conference connecting agri-tech innovators with farmers."
    }
  ],
  "last_updated": "..."
}
```

### community_events.json
```json
[]
// or:
[{"title": "...", "organiser": "...", "date_start": "YYYY-MM-DD", "location": "...", "url": "...", "description": "..."}]
```

### tech_watch.json
```json
{"headline": "...", "body": "...", "url": "https://...", "source": "Source Name"}
```

### from_the_soil.json
```json
[{"id": 1, "category": "history", "text": "~100-word narrative..."}]
// 52 items total, indexed by issue_number % 52
```

### issue_number.json
```json
{"current": 18}
// Currently at 18 due to test runs — reset before live send
```

---

## BUSINESS LOGIC

### Shared AI context (injected into every call)
> "You are writing a section of 'Field Notes: East Anglia', a free weekly farming intelligence newsletter for professional arable and mixed farmers in Norfolk, Suffolk, and Cambridgeshire. Readers are experienced farming professionals who want facts, numbers, and practical implications — not general explanations or hedging. Use farming-specific language where appropriate (ex-farm, delivered, p/kg dwt, £/t, week-on-week). Be concise and direct. Today's date: {date}."

### Tone rules (apply everywhere)
- Facts and numbers first — never hedge, never speculate
- No advice — never "consider selling", "you should", "we recommend"
- Farming units always — `p/kg dwt`, `ppl`, `p/doz`, `£/t ex-farm`
- East Anglia specificity — Norfolk poultry/eggs, north Norfolk dairy, significant pig sector, sugar beet, malting barley
- Inline citations only — `[Label](URL)` markdown, 1–2 words, one per source per section
- Word limits are real — each section has a hard maximum, enforced in prompts

### Markdown rendering pipeline
AI outputs plain text with markdown inline syntax. Two functions convert:

`text_to_html(text)`:
- `## heading` → `<p style="font-weight:700;color:#1b3a2d;">heading</p>`
- Bullets (•, –, -, *) → `<ul><li>` (blank lines between bullets do NOT close the list)
- Paragraphs → `<p style="margin:0 0 10px;">`
- Calls `_apply_inline_md()` on each line

`_apply_inline_md(text)`:
- `[text](url)` → `<a href="url" style="color:#1b3a2d;text-decoration:underline;">text</a>`
- `**bold**` → `<strong>`
- `*italic*` → `<em>`

### Illustration loading
`_load_illustrations()`:
- If `ASSETS_BASE_URL` set → returns HTTPS URLs (`{ASSETS_BASE_URL}/{filename}`)
- If not set → reads SVG from `newsletter/assets/`, base64-encodes, returns `data:image/svg+xml;base64,...`
- Gmail STRIPS base64 data URIs in `<img>` — always use ASSETS_BASE_URL for email sends

### Week-on-week price comparisons
Each scraper calls `archive_current()` before scraping, copying `data/X.json` → `data/previous/X_prev.json`. Scrapers load `load_previous()` to compute `change` and `prev_week_price` fields.

---

## CURRENT STATUS (23 March 2026)

| Area | Status |
|---|---|
| All 13 scrapers | Working and tested (added norwich_livestock.py) |
| Newsletter generation | Fully working — 13 AI sections + Python-built tables/cards |
| Email sending | Working — drafts to neil@neilpeacock.co.uk |
| Icons in email | Working — served from GitHub raw CDN |
| Domain | `fieldnoteseastanglia.co.uk` registered, DNS verification pending |
| FROM_EMAIL | Temporarily `onboarding@resend.dev` |
| Live subscribers | Not yet — no audience in Resend |
| NEWSLETTER_ENV | `draft` — broadcast not tested |
| Issue counter | At 18 due to test runs — **reset before live send** |
| Cron automation | Not yet set up |

---

## PENDING TASKS

1. **Reset issue counter** — set `data/issue_number.json` `{"current": 1}` before first real issue
2. **Confirm domain verified** — check Resend dashboard, then update `FROM_EMAIL` to `Field Notes <hello@fieldnoteseastanglia.co.uk>`
3. **Switch icon CDN** — once domain live, set `ASSETS_BASE_URL=https://fieldnoteseastanglia.co.uk/assets` in `.env`
4. **Set up subscriber list** — create audience in Resend, add `RESEND_AUDIENCE_ID` to `.env`
5. **Go live** — change `NEWSLETTER_ENV=live` in `.env`
6. **Set up cron** — schedule `run_scrapers.sh` Sunday 8pm and `run_newsletter.sh` Monday 5am
7. **Weather API** — optionally add `MET_OFFICE_API_KEY` for Met Office DataPoint

---

## NEIL UPDATES WEEKLY (manual)

Two files only:

**`data/tech_watch.json`**
```json
{"headline": "Short title", "body": "2–3 sentence description.", "url": "https://...", "source": "Source Name"}
```

**`data/community_events.json`**
```json
[
  {
    "title": "Event name",
    "organiser": "RNAA / NFU / etc",
    "date_start": "2026-04-15",
    "location": "Town, County",
    "url": "https://...",
    "description": "One sentence about the event."
  }
]
```
Can be `[]` when no community events to add.

---

## KEY TECHNICAL GOTCHAS

1. **Gmail strips base64 `<img>` tags** — always use HTTPS via `ASSETS_BASE_URL`; never send with blank `ASSETS_BASE_URL`
2. **Python 3.9 syntax** — `Optional[str]` not `str | None`; `from typing import Optional`
3. **`string.Template.safe_substitute()`** — intentional; `substitute()` would KeyError on `{{unsubscribe_url}}`
4. **Issue number increments every generate run** — not idempotent; reset manually after testing
5. **`FROM_EMAIL` in shell** — `<>` breaks zsh; always set in `.env` directly
6. **`base.get()` sets its own timeout** — never pass `timeout=` kwarg; causes `TypeError: multiple values for keyword argument`
7. **AHDB feed API date format** — must be `M/d/yyyy h:mm:ss AM` (not `dd/mm/yyyy`)
8. **AHDB pig SPP** — `.xls` not `.xlsx`; use xlrd; wide sparse layout; price at non_empty[1]
9. **AHDB beef/eggs/poultry URLs rotate** — use `_find_excel_url()` page-scraping helper; don't hardcode Azure blob URLs
10. **EDP/EADT block direct scraping** — `local_news.py` must use RSS only
11. **Norwich Market reports lag** — most recent may be weeks old; scraper picks up latest automatically
12. **`community_events.json` can be `[]`** — `isinstance(result, list)` check before merging
13. **Event description deduplication** — `build_event_cards_html()` strips leading title from og:description (common og:description pattern)
14. **Blank lines in AI output** — `text_to_html()` does NOT close `<ul>` on blank lines (AI often puts blank lines between bullets)
15. **`string.Template` dollar signs** — any `$` in AI output that matches a variable name will be substituted; `safe_substitute()` means unmatched ones are left, but real collisions are possible — rare in practice

---

## RUNNING COSTS

| Cost | Amount |
|---|---|
| Anthropic API | ~$0.18 per newsletter (13 Sonnet calls, ~1k in / 600 out) |
| Resend | Free up to 3,000 subscribers/month |
| Domain (Namecheap) | ~£8/yr |

---

## HOW TO RUN

```bash
cd /Users/neilpeacock/farm/field-notes
source .venv/bin/activate

# Generate newsletter (reads data/*.json, calls Claude, builds HTML)
python newsletter/generate.py

# Send draft to neil@neilpeacock.co.uk
python newsletter/send.py

# Run a single scraper
python scrapers/norwich_livestock.py

# Run all scrapers (as cron would)
bash run_scrapers.sh
```

Never use bare `python` without the venv — macOS system Python may differ.

---

## ABOUT NEIL

- Neil Peacock — building and running this himself
- Technical but not a professional developer — prefers clear explanations over jargon
- Based in East Anglia, farmer's son
- Draft email: neil@neilpeacock.co.uk
- Domain registrar: Namecheap

---

_Auto-generated by /claudeupdate in Claude Code. Last updated: 23 March 2026._
