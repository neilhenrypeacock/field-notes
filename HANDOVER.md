# Field Notes: East Anglia — Full Handover

**What it is:** A free weekly email newsletter for professional arable and mixed farmers in Norfolk, Suffolk, and Cambridgeshire. Sent every Monday morning. ~5-minute read. Covers everything a farmer needs to know without spending two hours scrolling.

**Who reads it:** Experienced farming professionals. They want facts, numbers, and practical implications. Not general explanations, not hedging, not advice.

---

## How it works (pipeline overview)

```
Sunday 8pm  →  run_scrapers.sh  →  13 scrapers pull data  →  data/*.json
Monday 5am  →  run_newsletter.sh  →  generate.py  →  Claude AI (13 calls)  →  HTML + plain text  →  send.py  →  Resend API  →  subscribers
```

1. **Scrapers** run Sunday evening and pull data from 13 sources into `data/*.json`
2. **generate.py** runs Monday morning:
   - Loads all JSON data files
   - Makes 13 Claude Sonnet API calls (one per section)
   - Builds HTML price tables and event cards in Python (not AI)
   - Assembles the full HTML email from `template.html` using `string.Template.safe_substitute()`
   - Saves `newsletter/output/field_notes_YYYY_MM_DD.html` and `.txt`
3. **send.py** sends via Resend API
   - `NEWSLETTER_ENV=draft` → sends to `DRAFT_EMAIL` only
   - `NEWSLETTER_ENV=live` → broadcasts to full audience

**Cost per issue:** ~$0.18 Anthropic API + free Resend (up to 3,000 subscribers)

---

## Design system

### Palette

| Colour | Hex | Used for |
|--------|-----|----------|
| Dark green | `#1b3a2d` | Section badge backgrounds, table headers, link colour, CTA buttons |
| Gold | `#d4a853` | Margin Watch + One Good Read badges, hero subtitle, From the Soil divider |
| Warm off-white | `#f2f0eb` | Page background |
| Light green | `#263f32` | Legend strip (below hero), forward banner |
| Section bg | `#f7f5f0` | Dividers |
| Warm white | `#ffffff` | Content area |
| Body text | `#333333` | Standard paragraph text |
| Muted | `#9a8e7d` | Source lines, captions |

### Typography

Three Google Fonts loaded via `@import` at top of `<style>`:

- **Playfair Display** (700, 900 weight) — headlines only: `Field Notes` masthead, `East Anglia` subtitle, `Margin Indicator` label
- **Source Sans 3** (400, 600, 700) — body text throughout, section badges, labels
- **Source Serif 4** (regular + italic, 400 + 600) — editorial prose sections (Markets, Costs, Livestock, Weather, Machinery, Regulatory, One Good Read, From the Soil)

The distinction matters: data-heavy sections use Sans (scannable), editorial sections use Serif (readable, warm).

### Container

640px max-width, centred, `background-color:#f2f0eb` outer wrapper, inner content on white `#ffffff`. The entire email is table-based (no `<div>`) for email client compatibility.

### Section badges

Every section starts with a full-width dark green badge:
```html
<td style="background-color:#1b3a2d;border-radius:4px;padding:14px 20px 14px 12px;" valign="middle">
  <!-- 36×36px watercolour SVG icon + uppercase white label -->
```

Two exceptions use gold (`#d4a853`) instead of dark green: **Margin Watch** and **One Good Read**.

### Section dividers

Between every section:
```
◆ ◆ ◆  (three diamonds, letter-spaced, on #f7f5f0 background)
```
Flanked by 1px `#e0dbd0` rules above and below.

### Price tables

Consistent style across all price tables:
- Header row: `background-color:#1b3a2d`, white text, 11px uppercase, letter-spacing 0.5px
- Alternating rows: `#ffffff` / `#faf8f4`
- Change column: `▲ #2e7d32 green` / `▼ #c62828 red` / `#666666 grey` for zero
- Border: `1px solid #e8e2d6`, `border-radius:6px`

---

## Email structure (top to bottom)

### 1. Preview text (hidden)
Invisible to eye but shown in inbox preview. Pulled from the first bullet of At a Glance, truncated to ~80 chars. Zero-width non-joiner characters pad it to suppress Gmail showing body text.

### 2. Hero banner
Dark green `#1b3a2d` full-width block. Left: watermark icon + "WEEKLY FARMING INTELLIGENCE" super-label (gold, 11px tracked caps) + "Field Notes" (Playfair 38px white) + "East Anglia" (Playfair 22px gold) + date/issue chip. Right: East Anglia map SVG, 200px, `opacity:0.75`.

### 3. Legend strip
`#263f32` background, `border-bottom:3px solid #d4a853`. Italic Source Serif 4, 14px, muted green text:
> *"A free weekly briefing that saves you two hours of scrolling. Markets, weather, grants, land, jobs — everything an East Anglian farmer needs to know, in one place. Built by a farmer's son trying to give something back to the industry that raised him."*

This never changes — it's hardcoded.

### 4. Table of contents
White background. "IN THIS ISSUE" label (10px tracked caps). 15 section links with emoji icons, separated by `·` dots, 2.1 line-height (wraps naturally). Each links to its section anchor.

### 5. Share strip
Light green `#f0f7f2` background. Two-column table: left = "Know a farmer or agronomist who'd benefit?", right = "Forward this →" (dark green, bold, right-aligned). The two-column layout prevents wrapping on mobile.

### 6–20. Content sections (white background, 44px horizontal padding)

Each section follows the same pattern:
1. Spacer row (28–32px top padding)
2. Section badge (full-width green or gold bar with 36px icon + label)
3. Spacer (18px)
4. AI-generated text
5. Optional: price table, event cards, or Norwich Market table
6. Optional: source attribution or CTA
7. Section divider (◆ ◆ ◆)

### 21. Data Sources strip
`#f7f5f0` background. Two-column layout: Markets/Livestock/Weather left, Policy/Land/Jobs/Tech right. All sources listed with links.

### 22. Forward banner
`#263f32` background. "Forward this email — it's free." (Playfair gold, 18px bold). Static — never changes.

### 23. Footer
White. Legal disclaimer, contact email, unsubscribe link (`{{unsubscribe_url}}` — filled by Resend at send time).

---

## All 15 sections: data → AI → output

### At a Glance
**Data:** All scraped data (grain, livestock, weather, defra, schemes, news, machinery)
**AI prompt:** Exactly 3 bullets, max 25 words each. Must cover a mix of sectors — never all arable. 1 bullet on markets/prices, 1 on weather/fieldwork, 1 on policy/grants/community. Each starts with a strong verb or number. No intro/outro.
**Output:** 3 bullet points → `text_to_html()` renders as `<ul>`

### Markets — What You're Selling
**Data:** `ahdb_grain.json` — feed wheat, milling wheat, feed barley (Eastern region + UK average from AHDB Corn Returns Excel)
**AI prompt:** Lead with biggest movement. Eastern region price first; only compare to UK average if difference >£2/t. Cite `[AHDB]` inline on first mention. 120 words max. Price table appended separately.
**Output:** AI prose (Source Serif 4) + Python-built price table (commodity / this week / last week / change / UK avg)

### Costs — What You're Paying
**Data:** `ahdb_fertiliser.json` + `ahdb_feed.json`
**AI prompt:** Fertiliser + feed commodity movements. UK figures — note regional variation once. Cite `[AHDB]` inline for each. Seasonal context if relevant. 100 words max.
**Output:** AI prose + fertiliser price table + source line

### Margin Watch
**Data:** Wheat price + fertiliser data (combined)
**AI prompt:** Factual only — state wheat price, key input costs, indicative margin vs typical EA cost of production (£160–180/t). State if margin positive/negative/tight. Week-on-week wheat change if available. 3–4 sentences. NO advice, no "consider selling".
**Output:** Gold badge, gold-bordered box (`background:#fdf8ee; border-left:4px solid #d4a853`). AI prose inside.

### Livestock & Dairy
**Data:** `ahdb_livestock.json` (pig SPP, milk farmgate, beef deadweight, eggs, poultry) + `norwich_livestock.json` (Norwich market sale report)
**AI prompt:** Lead with biggest price movement. Cover each sector where data available: pigs (p/kg dwt), dairy (ppl), eggs (p/doz), beef (p/kg dwt). Cite `[AHDB]` and `[Norwich Market]` inline. 120 words max. Facts only.
**Output:** AI prose (Source Serif 4) + AHDB price table (5 rows) + Norwich Market table + reader price CTA

**Norwich Market table** (Python-built from scraped data):
- Store cattle: head count, average price
- Lamb sections: prime hoggs, standard, medium, heavy, heavy+ — each with head count, p/kg average, £ average

**Reader CTA (hardcoded in template):**
> *Do you have local farm-gate prices to share? [Email us] — we feature reader data when available.*

### Schemes & Grants
**Data:** `govuk_schemes.json` + `defra_blog.json`
**AI prompt:** SFI actions, CS options, capital grants (FETF), anything with an imminent deadline. Plain English. Specific payment rates. Bold deadlines. Bullet format for multiple schemes. Max 130 words. Cite inline with `[DEFRA](URL)` using exact article URL.
**Output:** AI prose (Source Serif 4) + JustFarm CTA

**JustFarm CTA (hardcoded):**
> Not sure which schemes you qualify for? [Check your eligibility at JustFarm →](https://justfarm.app)

### Weather — Your Week Ahead
**Data:** `met_office.json` — 7-day Open-Meteo forecast (falls back gracefully if Met Office DataPoint unavailable)
**AI prompt:** Answer practical farmer questions: Is there a spraying window? Fit for drilling? Frost risk? How much rain and when? Farmer language ("spray window", "gusts up to X mph"). Specific days. 100 words max. Cite `[Met Office]` inline.
**Output:** AI prose + 7-day weather table (colour-coded rows: green <30% rain, gold 30–60%, red ≥60%)

### Community & Events
**Data:** `events.json` (scraped) + `community_events.json` (Neil's manually curated list)
**AI prompt:** 1–2 sentence scene-setting intro only — note time of year, what's on in the region. Do NOT list individual events (those appear as cards). If no events, direct to rnaa.org.uk / norfolkyfc.co.uk / NFU East Anglia. 40 words max.
**Output:** AI intro + Python-built event cards (one card per event: title, date/location/organiser, description, "More info →" button) + YANA support strip + "get featured" CTA

**Event card design:** bordered box (`1px solid #e8e2d6`, `border-radius:6px`), title in dark green bold 14px, meta in muted 12px, description 13px, dark green pill button.

**YANA strip (hardcoded, permanent):** Mental health support — You Are Not Alone, 0300 323 0400, yanahelp.org. Always present. Never remove.

### Land & Property
**Data:** `land_listings.json` — Brown & Co property search scraper
**AI prompt:** East Anglia only (Norfolk, Suffolk, Cambridgeshire). Open with "This week's listings from [Brown & Co](URL):" then describe properties. Total acreage, standout properties, price-per-acre, which agents active. Skip any non-EA counties. 90 words max.
**Output:** AI prose (Source Serif 4)

### Jobs — East of England
**Data:** `jobs.json` — Farmers Weekly East of England jobs
**AI prompt:** Open with "Jobs from [Farmers Weekly](URL):" then 3–5 most interesting roles. Prefer management/agronomist/technical over general labouring. Title, employer, location, salary if given, one sentence why it's interesting. Bullet list. Include `[Apply →](URL)` inline per job. 120 words max.
**Output:** AI prose with inline apply links (→ `_apply_inline_md()` converts to `<a>` tags)

### Machinery & Auctions
**Data:** `machinery_auctions.json` — Cheffins auction listings
**AI prompt:** Sale names, dates, type (modern/vintage/cessation). One sentence context max per sale. Link catalogue as `[Cheffins](URL)`. If FETF open, one sentence on grant funding. 60 words max.
**Output:** AI prose (Source Serif 4) with inline Cheffins links

### Tech Watch
**Data:** `data/tech_watch.json` — Neil updates this manually every week
**AI call:** None — loaded directly from JSON, no AI.
**Output:** Headline (bold dark green), body text, optional source link. Format: `{headline, body, url, source}` in JSON.

### Regulatory & Health
**Data:** `defra_blog.json` + `local_news.json`
**AI prompt:** APHA disease alerts (avian flu, TB, plant health), NVZ changes, pesticide approvals/withdrawals, HSE alerts, Red Tractor changes, compliance deadlines. Flag urgent actions. Do NOT repeat grants content. 100 words max. Cite `[DEFRA](URL)` inline.
**Output:** AI prose (Source Serif 4)

### One Good Read
**Data:** `local_news.json` + extra context (At a Glance content, to avoid repetition)
**AI prompt:** Pick the single most interesting article for an EA farmer this week. Output: `[Article Title](URL)`, publication name, one-sentence reason why it matters. 50 words max. Title must be an inline link — not a separate URL. Do NOT pick a story already covered in At a Glance.
**Output:** AI text in `background:#fdf8ee` warm box (Source Serif 4, 14px)

### From the Soil
**Data:** `data/from_the_soil.json` — 52 pre-written items, no scraping, no AI call
**Selection:** `items[issue_number % 52]` — rotates through the full library once per year
**Content:** ~100-word narrative stories about East Anglian farming history, soil science, heritage breeds, notable figures, seasonal fieldwork traditions. Structure: scene → surprising fact → significance today. Warm, authoritative, local.
**Output:** Gold top border, "FROM THE SOIL" label (gold tracked caps), italic Source Serif 4, `color:#666`

---

## Voice and tone

### The shared context (injected into every AI call)

> "You are writing a section of 'Field Notes: East Anglia', a free weekly farming intelligence newsletter for professional arable and mixed farmers in Norfolk, Suffolk, and Cambridgeshire. Readers are experienced farming professionals who want facts, numbers, and practical implications — not general explanations or hedging. Use farming-specific language where appropriate (ex-farm, delivered, p/kg dwt, £/t, week-on-week). Be concise and direct."

### Rules that apply everywhere

- **Facts and numbers first.** If there's a price, lead with it. If there's a change, say exactly how much.
- **No advice.** We never say "consider selling", "you should", "we recommend". We state facts. The farmer decides.
- **No hedging.** "Prices may move" adds nothing. State what happened.
- **Farming units always.** `p/kg dwt`, `ppl`, `p/doz`, `£/t ex-farm`, `delivered` — use whichever applies. Never just "£".
- **East Anglia specificity.** Norfolk is a major poultry and egg county. Significant pig sector. Dairy in north Norfolk and Cambridgeshire. Sugar beet. Malting barley. Reference this where relevant.
- **Inline citations only.** Sources are `[Label](URL)` inline — never footnotes, never separate source lines. 1–2 word labels. One citation per source per section.
- **Word limits are real.** Each prompt has a hard maximum. Concision is intentional — this is a briefing, not a report.

### Tone by section

| Section | Tone | Notes |
|---------|------|-------|
| At a Glance | Sharp, urgent | Verb-first bullets, no padding |
| Markets | Factual, technical | £/t, p/kg, week-on-week comparisons |
| Costs | Practical | "Should you be buying spring N now?" framing |
| Margin Watch | Clinical | No advice, just maths |
| Livestock | Factual | Numbers-heavy, multiple sectors |
| Schemes | Plain English | Bold deadlines, specific payment rates |
| Weather | Farmer-friendly | "spray window" not "precipitation-free period" |
| Events | Warm, brief | Scene-setting, not listing |
| Land | Descriptive | Acreage, price-per-acre, standout properties |
| Jobs | Informative | Why is this role interesting? |
| Machinery | Brief, functional | Awareness and links |
| Tech Watch | Curious, grounded | Neil's voice — manually written |
| Regulatory | Alert-led | Flag urgency, specific deadlines |
| One Good Read | Thoughtful | Deeper than news, worth 5 minutes |
| From the Soil | Warm, narrative | "An informed local speaking" |

---

## Data sources and scrapers

| Scraper | Source | Output | Notes |
|---------|--------|--------|-------|
| `ahdb_grain.py` | AHDB UK Corn Returns Excel (Azure Blob) | `ahdb_grain.json` | Eastern region + UK average |
| `ahdb_livestock.py` | AHDB (pig SPP .xls, milk, beef, eggs) | `ahdb_livestock.json` | Multiple Excel files per commodity |
| `ahdb_fertiliser.py` | AHDB Fertiliser Prices | `ahdb_fertiliser.json` | |
| `ahdb_feed.py` | AHDB Feed Ingredient Prices Excel | `ahdb_feed.json` | Date format quirk: `M/d/yyyy h:mm:ss AM` |
| `met_office.py` | Open-Meteo (Met Office DataPoint fallback) | `met_office.json` | 7-day forecast, East Anglia coords |
| `defra_blog.py` | Defra Farming Blog | `defra_blog.json` | |
| `govuk_schemes.py` | GOV.UK Atom feed | `govuk_schemes.json` | |
| `local_news.py` | EDP/EADT RSS (no direct scraping — site blocks it) | `local_news.json` | RSS only |
| `machinery_auctions.py` | Cheffins | `machinery_auctions.json` | |
| `events.py` | Various event sites | `events.json` | Fetches og:description per event URL |
| `jobs.py` | Farmers Weekly East of England | `jobs.json` | `li.lister__item` cards |
| `land_listings.py` | Brown & Co property search | `land_listings.json` | `card--property-listing` class |
| `norwich_livestock.py` | norwichlivestockmarket.com/reports | `norwich_livestock.json` | Regex-parses report narrative text |

**Manually updated weekly by Neil:**
- `data/tech_watch.json` — `{headline, body, url, source}`
- `data/community_events.json` — array of `{title, organiser, date_start, location, url, description}`

---

## Illustrations

14 watercolour SVG icons, one per section. Served from GitHub raw URLs in production (email-safe — Gmail strips base64 data URIs):

```
ASSETS_BASE_URL=https://raw.githubusercontent.com/neilhenrypeacock/field-notes-assets/main
```

When `ASSETS_BASE_URL` is set, generate.py uses HTTPS URLs. When not set (local preview), falls back to base64 data URIs. SVG files live in two places:
- `newsletter/assets/` — local source
- `web/assets/` — served from domain (when live)
- GitHub repo `neilhenrypeacock/field-notes-assets` — CDN for email

Once `fieldnoteseastanglia.co.uk` is live, switch `ASSETS_BASE_URL` to `https://fieldnoteseastanglia.co.uk/assets`.

---

## Key technical details

### Template substitution
`string.Template.safe_substitute()` — unknown `$vars` left as-is (safe for `{{unsubscribe_url}}` which Resend fills).

### Markdown to HTML conversion
Two functions in generate.py:

**`text_to_html(text)`** — converts full AI output:
- `## heading` → bold dark green `<p>`
- `**bold**` → `<strong>`
- `• - – *` bullets → `<ul><li>` (blank lines between bullets don't close the list)
- Paragraphs → `<p style="margin:0 0 10px;">`
- Calls `_apply_inline_md()` on each line

**`_apply_inline_md(text)`** — converts inline syntax:
- `[text](url)` → `<a href="url" style="color:#1b3a2d;text-decoration:underline;">text</a>`
- `**bold**` → `<strong>`
- `*italic*` → `<em>`

### Issue numbering
`data/issue_number.json` — auto-increments on every `generate.py` run. Reset before live launch if test runs have inflated it.

### AI model
`claude-sonnet-4-5` — 13 calls per issue, ~1,000 tokens in / 600 tokens out each. Usage logged to `logs/ai_usage.json` (last 200 calls).

### Plain text fallback
`template_plain.txt` — mirrors HTML structure. Same `$variables`. Weather table and price tables have separate plain-text renderers. Event cards omitted (AI intro text covers it).

---

## Infrastructure

- **Domain:** `fieldnoteseastanglia.co.uk` (Namecheap)
- **Email sending:** Resend (`resend.com`) — `FROM_EMAIL=Field Notes <hello@fieldnoteseastanglia.co.uk>`
- **DNS:** Pending verification — using `onboarding@resend.dev` until domain verified
- **Cron (on hosting server):**
  - `0 20 * * 0` — run_scrapers.sh (Sunday 8pm UTC)
  - `0 5 * * 1` — run_newsletter.sh (Monday 5am UTC)
  - `0 6 * * *` — run_daily_check.sh (daily RSS monitor)
- **Python:** 3.9 — use `Optional[str]` not `str | None`
- **Virtual env:** `.venv/` — activate with `source .venv/bin/activate`

---

## Files to edit week-to-week

| File | What to update |
|------|----------------|
| `data/tech_watch.json` | New tech/enterprise item |
| `data/community_events.json` | Upcoming local events |

Everything else is automated.

---

## What Neil does not touch

- All 13 scrapers run automatically
- All 13 AI calls happen automatically
- All HTML assembly is automatic
- Issue number increments automatically
- From the Soil rotates automatically (52-week cycle)
- Plain text generated automatically alongside HTML
