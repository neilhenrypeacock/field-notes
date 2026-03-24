# Field Notes: East Anglia — Full Design Brief

> This document covers the complete design, architecture, and editorial reasoning behind the newsletter. Written for use in Claude Chat to continue developing the project.

---

## What It Is

**Field Notes: East Anglia** is a free weekly farming intelligence newsletter sent every Monday morning to farmers in Norfolk, Suffolk, and Cambridgeshire. It aggregates data from ~12 sources, runs each section through Claude AI, and assembles it into a single HTML email.

The goal is simple: save a working farmer two hours of scrolling. Everything they'd otherwise piece together across AHDB, GOV.UK, Farmers Weekly, Met Office, and Cheffins in one place, written in plain farming language.

**Tone rules** (applied across every AI section):
- Experienced professional audience — no explaining what a combine harvester is
- Actual numbers always (£/t, p/kg, %, dates) — never vague generalisations
- Farming-specific language throughout: ex-farm, delivered, p/kg dwt, NVZ, SFI, FETF
- Lead with what matters most right now (deadlines, price moves, weather risks)
- No hedging, no caveats, no "it's worth noting that"

---

## Technical Architecture

```
Sunday 8pm UTC:   run_scrapers.sh   → 12 scrapers → data/*.json
Monday 5am UTC:   run_newsletter.sh → generate.py → template.html → output/field_notes_YYYY_MM_DD.html
                                                  → send.py → Resend API → subscribers
Daily 6am UTC:    run_daily_check.sh → monitor/daily_check.py → RSS monitor (Defra/GOV.UK)
```

**Stack:**
- Python 3.9 (no `str | None` syntax — use `Optional[str]`)
- `anthropic` SDK — Claude claude-sonnet-4-5 (claude-sonnet-4-5), 12 calls per issue
- `resend` SDK — email sending (free up to 3,000 subscribers/month)
- `string.Template.safe_substitute()` — unknown `$vars` left as-is (safe for `{{unsubscribe_url}}`)
- `xlrd`, `openpyxl` — Excel parsing for AHDB data
- `feedparser` — RSS/Atom feeds
- `requests` with retry logic in `scrapers/base.py`

**Cost per issue:** ~$0.15 Anthropic API + £0 Resend (within free tier)

---

## File Structure

```
field-notes/
├── .env                         # Keys: ANTHROPIC_API_KEY, RESEND_API_KEY, etc.
├── scrapers/
│   ├── base.py                  # Shared HTTP session, retry, save_data(), archive_current()
│   ├── ahdb_grain.py            # Feed wheat, milling wheat, feed barley prices
│   ├── ahdb_livestock.py        # Pig SPP, milk farmgate price
│   ├── ahdb_feed.py             # Feed commodity prices (soya, wheat feed, etc.)
│   ├── ahdb_fertiliser.py       # Fertiliser prices (urea, DAP, AN, UAN)
│   ├── met_office.py            # 5-day weather (Met Office DataPoint → Open-Meteo fallback)
│   ├── defra_blog.py            # DEFRA farming blog posts (Atom feed)
│   ├── govuk_schemes.py         # GOV.UK farming scheme updates (Atom feed)
│   ├── local_news.py            # RSS: Agriland UK + Defra Blog (EDP/EADT block scraping)
│   ├── machinery_auctions.py    # Cheffins auction calendar + news
│   ├── events.py                # Local farming events
│   ├── jobs.py                  # Farmers Weekly East of England jobs
│   └── land_listings.py         # Brown & Co land/property listings
├── data/
│   ├── *.json                   # Current week's scraped data
│   ├── issue_number.json        # {"current": N} — auto-incremented on each generate run
│   └── previous/                # Last week's data (for week-on-week price comparisons)
├── newsletter/
│   ├── generate.py              # Main orchestrator
│   ├── send.py                  # Resend API sender
│   ├── template.html            # Full HTML email template (640px)
│   ├── template_plain.txt       # Plain-text fallback
│   ├── assets/                  # 12 watercolour SVG illustrations + map SVG
│   └── output/                  # Generated HTML + TXT files
├── prompts/                     # 12 AI prompt files (one per section)
└── monitor/
    └── daily_check.py           # RSS monitor for urgent Defra/GOV.UK alerts
```

---

## HTML Email Design System

### Container & Layout
- **Width:** 640px max, responsive to 100%
- **Outer background:** `#f2f0eb` (warm cream)
- **Outer padding:** 20px top/bottom, 12px left/right
- **Inner container:** white `#ffffff` with rounded top (`border-radius: 12px 12px 0 0` on hero)
- **Content padding:** `0 44px` throughout the white content area

### Colour Palette
| Name | Hex | Used for |
|---|---|---|
| Dark green | `#1b3a2d` | Hero banner bg, section badge bg, table headers |
| Mid green | `#263f32` | About strip bg, forward banner bg |
| Gold | `#d4a853` | Subheadings, Margin Watch badge, One Good Read badge, gold bar accent |
| Light gold | `#E8CC7A` | Background wash elements |
| Cream | `#f2f0eb` | Page background |
| Off-white | `#f7f5f0` | Section divider background |
| Body text | `#333333` | Main content |
| Muted text | `#9a8e7d` | Source lines, captions |
| Source links | `#8a7e6d` | Source link text |
| Sage text | `#c8d6c0` | Banner meta text |
| Green price | `#2e7d32` | Price up arrow |
| Red price | `#c62828` | Price down arrow |

### Typography
All fonts loaded via Google Fonts `@import`:
- **Playfair Display** (700, 900) — hero heading "Field Notes", "East Anglia", Margin Watch subhead
- **Source Sans 3** (400, 600, 700) — body text, labels, navigation, At a Glance, Jobs, Events
- **Source Serif 4** (italic 400, regular 400/600) — Markets, Costs, Machinery, Regulatory, Land, Weather, One Good Read body text; About strip quote

Fallback stack: `Arial, Helvetica, sans-serif` or `Georgia, 'Times New Roman', serif`

### Section Badges
All section headings use the same badge pattern:
- `background-color: #1b3a2d` (dark green) — all sections except Margin Watch and One Good Read
- `background-color: #d4a853` (gold) — Margin Watch and One Good Read
- `border-radius: 4px`
- `padding: 14px 20px 14px 12px`
- 36×36px watercolour SVG illustration left of text
- Text: 12px, `font-weight: 700`, `letter-spacing: 1.5px`, `text-transform: uppercase`
- Dark green badge: white text. Gold badge: `#1b3a2d` dark green text

### Section Dividers
Between every section:
```
1px line (#e0dbd0)
◆  ◆  ◆  (10px, gold, letter-spacing 4px, on #f7f5f0 background)
1px line (#e0dbd0)
```

### Price Tables
Built in Python (`build_price_table_html()` in `generate.py`):
- Header row: `background-color: #1b3a2d`, white text, 11px uppercase
- Alternating rows: `#ffffff` / `#faf8f4`
- Change column: ▲ green `#2e7d32` / ▼ red `#c62828` / grey `#666666` for no change
- Border: `1px solid #e8e2d6`, border-radius 6px

### Weather Table
Built in Python (`build_weather_table_html()`):
- Row background colour-coded by rain probability:
  - `< 30%` rain: green bg `#f0f7f2`, green text
  - `30–60%` rain: gold bg `#fdf8ee`, gold text
  - `≥ 60%` rain: red bg `#fdf2f2`, red text
- Symbol: ☑ (green), ✖ (red), ❓ (gold)

### Special Sections

**Margin Watch** — gold-accented card:
- Container: `background-color: #fdf8ee`, `border: 1px solid #e8dcc4`, `border-left: 4px solid #d4a853`
- Title "Margin Indicator" in Playfair Display 16px dark green

**One Good Read** — gold card:
- Container: `background-color: #fdf8ee`, `border: 1px solid #e8dcc4`, border-radius 6px
- Body in Source Serif 4

### Source Lines
All source references: 11px, `color: #9a8e7d`, linked to specific article URL where possible.
Label is `Source:` for 1 link, `Sources:` for multiple.

### Illustrations
12 watercolour-style SVGs in `newsletter/assets/fn_illustration_01–12.svg`
- Each: `viewBox="0 0 140 80"`, `width="140" height="80"`
- Embedded as base64 data URIs (no external requests — email client compatibility)
- Style: semi-transparent overlapping circles and shapes (opacity 0.12–0.5)
- Palette matches design system: gold `#D4A843`, sage `#8FBF96`, sky `#9BBFDF`, earth tones

**Banner map:** `newsletter/assets/fn_map_east_anglia_banner.svg`
- East Anglia county outlines (Norfolk, Suffolk, Cambridgeshire) from ONS boundary data
- `viewBox="70 10 310 250"`, `width="200" height="161"`
- Transparent background (no fill) — floats on dark green banner
- Colours: Norfolk `#D4A843` gold, Suffolk `#8FBF96` sage, Cambridgeshire `#B8956A` brown
- Embedded as base64 data URI like the illustrations

---

## Full Email Structure (top to bottom)

```
[Outer cream wrapper]
  [640px container]
    1. Hero banner (dark green #1b3a2d)
       Left: tagline / Field Notes / East Anglia / date·readtime·issue#
       Right: East Anglia county map (floating, 200×161px, opacity 0.75)

    2. About strip (mid green #263f32, italic Source Serif 4)
       "A free weekly briefing that saves you two hours..."

    3. Table of contents (white, 13px links, anchor links to each section)

    4. Share strip (light sage green #f0f7f2)
       "Know a farmer... Forward this to them →"

    5. White content area (padding: 0 44px)
       ├── At a Glance
       ├── ◆ ◆ ◆ divider
       ├── Markets — What You're Selling
       ├── ◆ ◆ ◆ divider
       ├── Costs — What You're Paying
       ├── ◆ ◆ ◆ divider
       ├── Margin Watch  [gold badge]
       ├── ◆ ◆ ◆ divider
       ├── Schemes & Grants
       ├── ◆ ◆ ◆ divider
       ├── Weather — Your Week Ahead
       ├── ◆ ◆ ◆ divider
       ├── Land & Property
       ├── ◆ ◆ ◆ divider
       ├── Jobs — East of England
       ├── ◆ ◆ ◆ divider
       ├── Machinery & Auctions
       ├── ◆ ◆ ◆ divider
       ├── Regulatory & Health
       ├── ◆ ◆ ◆ divider
       ├── Events
       ├── ◆ ◆ ◆ divider
       └── One Good Read  [gold badge]

    6. Data Sources strip (two-column, dark green header)

    7. Forward banner (#263f32, above footer)
       "Forwarded this? Subscribe free →"

    8. Footer (dark green, legal/unsubscribe)
```

---

## Section-by-Section Reference

---

### 1. At a Glance
**Why it exists:** Email scanners — readers who open on a phone between jobs. Three bullets is the minimum viable dose of information. If they read nothing else, they've still got the three most important things this week.

**Data source:** Aggregated from five scrapers: `defra_blog.json`, `local_news.json`, `govuk_schemes.json`, `ahdb_livestock.json`, `machinery_auctions.json`

**AI prompt rules:**
- Exactly 3 bullet points, max 25 words each
- Start each with a strong verb or specific number
- Focus on deadlines, price moves, weather risks, alerts
- No other text — no intro, no outro

**Template variable:** `$at_a_glance`
**Font:** Source Sans 3, 14px, line-height 1.7

---

### 2. Markets — What You're Selling
**Why it exists:** The price a farmer gets for their grain determines whether the year is profitable. East Anglian farmers are overwhelmingly arable — wheat, barley, oilseed rape. This section answers: what's the market doing and what should I be watching?

**Data source:** `ahdb_grain.json`
- Scraper: `scrapers/ahdb_grain.py`
- Source: **AHDB UK Corn Returns** — Excel file published weekly on Azure Blob storage
- URL pattern: `ahdb.org.uk/cereals-oilseeds/uk-corn-returns`
- Sheet: "Spot", Eastern region row
- Data: Feed wheat, milling wheat, feed barley — current week + previous week for change calc

**AI prompt rules (120 words max):**
- Lead with the most significant movement
- Use ex-farm / delivered / £/t language
- Include actual price figures and week-on-week changes
- Note any forward market signals worth watching
- If no change data: state current prices without speculating

**HTML output:** AI narrative paragraph(s) + programmatically-built price table (▲▼ coloured)
**Template variables:** `$markets_summary`, `$price_table_grain`
**Static source line:** "AHDB UK Corn Returns" → `ahdb.org.uk/cereals-oilseeds/uk-corn-returns`
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 3. Costs — What You're Paying
**Why it exists:** Margin is revenue minus cost. If the farmer knows their grain price but not their input prices, they can't make decisions. Fertiliser (the biggest variable cost) and feed are the critical numbers. Fuel costs are tracked but not always available.

**Data sources:** `ahdb_fertiliser.json` + `ahdb_feed.json`
- Scraper: `scrapers/ahdb_fertiliser.py` — AHDB fertiliser price Excel
- Scraper: `scrapers/ahdb_feed.py` — AHDB feed commodity Excel export API
  - **Note:** Feed prices API requires date format `M/d/yyyy h:mm:ss AM` (not dd/mm/yyyy — will fail otherwise)
- Fertiliser products: Granular urea, DAP, AN (UK), Imported AN, UAN, Ammonium sulphate
- Feed products: Soyameal Hi-Pro, Brazilian soya 48%, Wheat feed

**AI prompt rules (100 words max):**
- Highlight significant month-on-month or week-on-week changes
- Include actual £/t prices
- Seasonal context: e.g. "spring N applications underway — buy now or wait?"
- If no change data: state current prices only

**HTML output:** AI narrative + fertiliser price table
**Template variables:** `$costs_summary`, `$price_table_fertiliser`
**Static source lines:** AHDB Fertiliser Prices + AHDB Feed Commodity Prices (both linked)
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 4. Margin Watch
**Why it exists:** The one number that tells a farmer if they're making money. Takes the current wheat price and subtracts a typical East Anglian cost of production to give a simple verdict: positive, negative, or tight. No frills — just the bottom line.

**Data sources:** Derived from `ahdb_grain.json` (wheat price) + `ahdb_fertiliser.json`
- Uses first price in grain `prices[]` list as the wheat price indicator

**AI prompt rules (60 words max — deliberately short):**
- Calculate margin against typical East Anglian CoP: ~£160–180/t (use this if no better data)
- State: positive / negative / tight
- Compare to previous week if data available
- Be blunt about what it means for profitability
- One brief caveat max ("costs vary by farm") — no hedging beyond that

**HTML output:** Gold-accented card (`border-left: 4px solid #d4a853`) with AI text inside
**Badge colour:** Gold `#d4a853` (not dark green — signals it's a summary/verdict section)
**Template variable:** `$margin_watch`
**Static source line:** AHDB Corn Returns + AHDB Fertiliser (within the card)

---

### 5. Schemes & Grants
**Why it exists:** Government farming scheme money is significant — many East Anglian farmers now get 30–50% of farm income from SFI/CS payments. Deadlines slip past easily. This section ensures farmers don't miss open windows.

**Data sources:** `govuk_schemes.json` + `defra_blog.json`
- Scraper: `scrapers/govuk_schemes.py` — GOV.UK Atom feed (`gov.uk/government/organisations/rural-payments-agency`)
- Scraper: `scrapers/defra_blog.py` — Defra Farming Blog Atom feed (`defrafarming.blog.gov.uk/feed/`)
- Filters for: new schemes, updated schemes, closing deadlines, capital grants (FETF etc.)

**AI prompt rules (130 words max):**
- Cover SFI actions, Countryside Stewardship, capital grants (FETF, etc.)
- Plain English — not "actions", say "payments"
- Include specific payment rates if available
- **Flag deadlines explicitly with the exact date in bold**
- Prioritise urgency
- Bullet points for multiple schemes; single paragraph if one item
- If nothing significant: say so clearly

**Dynamic source links:** Up to 4 links — GOV.UK article URLs + Defra Blog post URLs (per-article)
**Template variables:** `$schemes_grants`, `$sources_schemes`
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 6. Weather — Your Week Ahead
**Why it exists:** Weather is the most operationally critical section for a working farmer. They can't spray in wind or rain. They can't drill in waterlogged ground. Frost kills crops. This section answers farmer-specific questions, not meteorological ones.

**Data sources:** `met_office.json`
- Primary scraper: `scrapers/met_office.py` — Met Office DataPoint API (requires `MET_OFFICE_API_KEY`)
- Fallback: Open-Meteo API (free, no key needed) — used when Met Office unavailable
- Location: East Anglia region (approx. 52.5°N, 1.5°E)
- Data: 5-day forecast — max temp, wind speed, precip probability, weather description

**AI prompt rules (100 words max):**
The prompt tells AI to answer the farmer's actual questions:
- Is there a spraying window? (dry + calm, wind <10mph, no rain)
- Is it fit for drilling or fieldwork?
- Is there frost risk?
- How much rain and when?

Language rules:
- "spray window" not "precipitation-free period"
- "rain" not "precipitation"
- "gusts up to X mph" not "moderate breeze"
- Specific days, not vague "mid-week"

**HTML output:** AI narrative + colour-coded 5-day weather table (green/gold/red by rain probability)
**Template variables:** `$weather_summary`, `$weather_table`
**Static source line:** "Open-Meteo API, East Anglia region"

---

### 7. Land & Property
**Why it exists:** East Anglian farmland is some of the most valuable in the UK (£10,000–15,000+/acre). Land rarely comes up and when it does, farmers need to know immediately. Also useful as a general market barometer.

**Data sources:** `land_listings.json`
- Scraper: `scrapers/land_listings.py`
- Source: **Brown & Co** — major East Anglian rural agent
- URL: `/services/rural/property-search`, card class `card--property-listing`
- Scrapes: property name, acreage, location, price, agent, URL

**AI prompt rules (90 words max):**
- Total acreage available across all listings
- Any standout properties (large acreage, notable location, unusual price)
- Price-per-acre ranges
- Which agents are active
- Flag any listings marked as new this week
- If few/no listings: say so

**Dynamic source links:** Up to 3 Brown & Co listing URLs (per-listing)
**Template variables:** `$land_property`, `$sources_land`
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 8. Jobs — East of England
**Why it exists:** Farming has a serious skills gap. Farm managers, agronomists, and specialist operators are genuinely hard to find and are paid well. This gives readers both a career resource and a sense of what roles farms are hiring for.

**Data sources:** `jobs.json`
- Scraper: `scrapers/jobs.py`
- Source: **Farmers Weekly Jobs** — `fwi.co.uk/jobs`
- Filters to: `li.lister__item` cards, East of England location only
- Extracts: title, employer, location, salary, URL

**AI prompt rules (120 words max, 3–5 jobs):**
- Prefer: farm management, agronomist, specialist technical, senior roles
- Deprioritise: general labouring
- For each job: title, employer/farm if notable, location, salary if stated, one-sentence hook
- Format as bullet list
- If fewer than 3 relevant: include what's there + note it was a quiet week

**Dynamic source links:** Up to 5 individual FWI job listing URLs
**Template variables:** `$jobs`, `$sources_jobs`
**Font:** Source Sans 3, 14px, line-height 1.7

---

### 9. Machinery & Auctions
**Why it exists:** Cheffins in Cambridge runs the largest machinery auctions in the UK. Buying secondhand machinery at auction is how most East Anglian farmers equip themselves. Knowing what's coming up (or what sold and for how much) is genuinely valuable market intelligence.

**Data sources:** `machinery_auctions.json`
- Scraper: `scrapers/machinery_auctions.py`
- Source: **Cheffins** — `cheffins.co.uk/machinery-vintage-auctions/`
- Auction calendar URL: `/auction-calendar.htm`
- News URL: `/news.htm`
- Extracts: sale dates, type, catalogue URL, lot categories, recent results

**AI prompt rules (90 words max):**
- Note: sale dates and types (combinables, sprayers, tractors, vintage, etc.)
- Broad categories of machinery featured
- Any significant lots or results if available
- If FETF 2026 is open: include one-sentence reminder that grant funding is available for new equipment

**Dynamic source links:** 1 Cheffins catalogue URL (reduced from 3 — one is sufficient)
**Template variables:** `$machinery`, `$sources_machinery`
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 10. Regulatory & Health
**Why it exists:** Regulatory non-compliance can cost a farm its Basic Payment, Red Tractor status, or worse. Disease outbreaks (avian flu, ASF, TB) require immediate action. This section is the early warning system.

**Data sources:** `defra_blog.json` + `local_news.json`
- Both scrapers pull Defra and news RSS feeds (see data sources in Schemes & Grants and Local News)

**AI prompt rules (100 words max):**
Topics to cover:
- APHA disease alerts (avian flu, TB, plant health)
- NVZ rule changes
- Pesticide/herbicide approval or withdrawal news
- HSE safety alerts
- Red Tractor standard changes
- Any other compliance matters

**Flag urgent actions explicitly** — especially if farmers need to act now (house birds, complete forms, meet deadline)

If nothing this week: "No major regulatory changes this week" + one standing reminder if relevant

**Dynamic source links:** Up to 3 Defra Blog post URLs
**Template variables:** `$regulatory`, `$sources_regulatory`
**Font:** Source Serif 4, 14px, line-height 1.75

---

### 11. Events
**Why it exists:** Farming is an isolated profession. Events — open days, farm walks, NFU meetings, demonstrations — matter for both knowledge-sharing and community. Given low scraper coverage, this section often uses fallback copy.

**Data sources:** `events.json`
- Scraper: `scrapers/events.py` (limited data availability)

**AI prompt rules (80 words max):**
- Event name, organiser, date, location per item
- Note if booking/registration required
- If no events in data: suggest farmers check `norfolkfwag.co.uk`, `rnaa.org.uk`, `nfuonline.com`

**Dynamic source links:** Up to 5 event organiser URLs
**Template variables:** `$events`, `$sources_events`
**Font:** Source Sans 3, 14px, line-height 1.7

---

### 12. One Good Read
**Why it exists:** The newsletter covers numbers and updates. This section offers one deeper article worth thinking about — something that might change how a farmer approaches their business, not just what they know today.

**Data sources:** `local_news.json`
- Scraper: `scrapers/local_news.py`
- Sources scraped (RSS only — EDP/EADT block direct scraping):
  - **Agriland UK** — `agriland.co.uk/feed/`
  - **Defra Blog** — `defrafarming.blog.gov.uk/feed/`
- Note: East Anglian Daily Times (EADT) and Eastern Daily Press (EDP) block scraping. RSS not currently available from them. This is a known limitation.

**AI prompt rules (50 words max — very tight):**
- Pick the single most interesting/useful/thought-provoking article
- Give: article title, publication name, one sentence why it matters to an East Anglian farmer
- Then: URL on the next line
- No padding, no over-explanation
- If no articles: say so

**Dynamic source link:** 1 article URL with publication name as link label
**Template variables:** `$one_good_read`, `$sources_read`
**HTML:** Rendered inside gold-background card (same as Margin Watch card style)
**Font:** Source Serif 4, 14px, line-height 1.7

---

## Data Sources Summary

| Scraper | Source | Method | Data |
|---|---|---|---|
| `ahdb_grain.py` | AHDB UK Corn Returns | Excel (Azure Blob) | Feed wheat, milling wheat, barley |
| `ahdb_fertiliser.py` | AHDB Fertiliser Prices | Excel export | Urea, DAP, AN, UAN prices |
| `ahdb_feed.py` | AHDB Feed Commodity Prices | Excel export API | Soya, wheat feed, rape meal |
| `ahdb_livestock.py` | AHDB | Excel (.xls via xlrd) | Pig SPP, milk farmgate price |
| `met_office.py` | Met Office DataPoint / Open-Meteo | REST API | 5-day forecast |
| `defra_blog.py` | Defra Farming Blog | Atom feed | Blog posts, announcements |
| `govuk_schemes.py` | GOV.UK / RPA | Atom feed | Scheme updates, deadlines |
| `local_news.py` | Agriland UK + Defra Blog | RSS | News articles |
| `machinery_auctions.py` | Cheffins | HTML scrape | Auction calendar, news |
| `jobs.py` | Farmers Weekly | HTML scrape | East of England ag jobs |
| `land_listings.py` | Brown & Co | HTML scrape | Farm/land listings |
| `events.py` | Various | HTML scrape | Local farming events |

---

## Generate Pipeline (generate.py)

### 1. Load all JSON data
All 12 `data/*.json` files loaded via `load_json()`. If a file is missing, returns `{"error": True}` and AI outputs `<em>Data unavailable this week.</em>`

### 2. Build combined data objects
Some sections combine multiple scrapers:
- `all_news` = defra + local_news + govuk_schemes + livestock + machinery (→ At a Glance)
- `costs_data` = fertiliser + feed (→ Input Costs)
- `margin_data` = first wheat price + fertiliser (→ Margin Watch)
- `regulatory_data` = defra + local_news (→ Regulatory)

### 3. AI section generation
12 Claude API calls — `claude-sonnet-4-5`, `max_tokens=600` each.
Shared system context prepended to every call:
> "You are writing a section of Field Notes: East Anglia... Readers are experienced farming professionals who want facts, numbers, and practical implications — not general explanations or hedging."

### 4. Price and weather table building
Python functions (not AI):
- `build_price_table_html()` — grain and fertiliser tables with ▲▼ colour coding
- `build_weather_table_html()` — 5-day table with rain probability colour coding

### 5. Source link building
`_build_section_sources()` extracts per-item URLs from scraped JSON and calls `_source_links_html()` to build the `<tr>` HTML blocks for 7 of 12 sections. Markets, Costs, Margin Watch, and Weather have static hardcoded source lines.

### 6. AI output to HTML
`text_to_html()` converts Claude's plain-text output:
- `## Heading` → bold dark green `<p>`
- `**bold**` → `<strong>`
- `*italic*` → `<em>`
- `• - – *` bullet lines → `<ul><li>` list
- Everything else → `<p>`

### 7. Template substitution
`string.Template.safe_substitute(html_vars)` — unknown `$vars` left as literal `$var` (safe for Resend's `{{unsubscribe_url}}` which uses `$` escaping via safe_substitute)

### 8. Plain text version
Parallel substitution into `template_plain.txt` using pre-built plain-text table variants.

### 9. Save outputs
`newsletter/output/field_notes_YYYY_MM_DD.html` and `.txt`

### Issue numbering
Auto-increments in `data/issue_number.json` on every `generate.py` run. Reset manually if running tests.

---

## Illustrations

12 watercolour SVGs, one per section:
| Variable | File | Section |
|---|---|---|
| `$illus_glance` | `fn_illustration_01_at_a_glance.svg` | At a Glance (also used in banner tagline at 22×22px) |
| `$illus_markets` | `fn_illustration_02_markets.svg` | Markets |
| `$illus_costs` | `fn_illustration_03_input_costs.svg` | Input Costs |
| `$illus_margins` | `fn_illustration_04_margin_watch.svg` | Margin Watch |
| `$illus_schemes` | `fn_illustration_05_schemes.svg` | Schemes & Grants |
| `$illus_weather` | `fn_illustration_06_weather.svg` | Weather |
| `$illus_land` | `fn_illustration_07_land.svg` | Land & Property |
| `$illus_jobs` | `fn_illustration_08_jobs.svg` | Jobs |
| `$illus_machinery` | `fn_illustration_09_machinery.svg` | Machinery |
| `$illus_regulatory` | `fn_illustration_10_regulatory.svg` | Regulatory |
| `$illus_events` | `fn_illustration_11_events.svg` | Events |
| `$illus_read` | `fn_illustration_12_one_good_read.svg` | One Good Read |
| `$banner_map` | `fn_map_east_anglia_banner.svg` | Hero banner (right side) |

All embedded as `data:image/svg+xml;base64,...` data URIs for email client compatibility — no external image requests.

---

## Known Issues & Limitations

- **EDP/EADT:** East Anglian Daily Times and Eastern Daily Press block scraping. Local news RSS feeds not currently available from them. `local_news.py` uses Agriland UK + Defra Blog as fallback.
- **Met Office fallback:** If `MET_OFFICE_API_KEY` not set or API fails, silently falls back to Open-Meteo.
- **AHDB feed prices date format:** The Excel export API requires `M/d/yyyy h:mm:ss AM` date format. Using `dd/mm/yyyy` silently fails.
- **AHDB pig SPP:** `.xls` format (requires `xlrd`). Wide layout — price at `non_empty[1]`, change at `non_empty[2]`.
- **Issue counter:** Increments on every `generate.py` run. Reset `data/issue_number.json` if test runs inflate it.
- **Domain:** `fieldnoteseastanglia.co.uk` (Namecheap). Resend domain verification pending DNS propagation. While unverified: use `FROM_EMAIL=Field Notes <onboarding@resend.dev>`.
- **Brown & Co only:** Land & Property currently only scrapes Brown & Co. Other East Anglian agents (Savills, Strutt & Parker, Carter Jonas) not yet covered.
- **Events data:** Sparse. Events section often falls back to AI suggesting readers check norfolkfwag.co.uk etc.

---

## Environment Variables

```
ANTHROPIC_API_KEY=       # console.anthropic.com
RESEND_API_KEY=          # resend.com/api-keys
MET_OFFICE_API_KEY=      # optional — falls back to Open-Meteo
RESEND_AUDIENCE_ID=      # set when sending to live list
FROM_EMAIL=              # Field Notes <hello@fieldnoteseastanglia.co.uk> once domain verified
NEWSLETTER_ENV=draft     # change to 'live' for broadcast
DRAFT_EMAIL=             # neil@neilpeacock.co.uk
LOG_LEVEL=INFO
```

---

## Sending

`newsletter/send.py` via Resend API:
- `NEWSLETTER_ENV=draft` → sends to `DRAFT_EMAIL` only (test mode)
- `NEWSLETTER_ENV=live` → broadcasts to full `RESEND_AUDIENCE_ID` list
- Both HTML and plain-text parts sent
- Resend replaces `{{unsubscribe_url}}` at send time (in footer)
- Send log written to `logs/send_log.json`

---

## Current Status (23 March 2026)

- v2 design: complete and live
- Issue #7 at last test run
- Domain DNS pending — using `onboarding@resend.dev` for now
- `NEWSLETTER_ENV=draft` (broadcast not yet tested)
- Dynamic per-article source links: implemented for 7 of 12 sections
- Data Sources strip: implemented at bottom of email
- East Anglia map in banner: implemented (as of this session)
