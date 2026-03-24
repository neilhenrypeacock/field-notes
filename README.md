# Field Notes: East Anglia

Weekly AI-powered farming intelligence newsletter for Norfolk, Suffolk, and Cambridgeshire.

## Setup

```bash
cd field-notes
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

### API Keys Required

| Key | Source |
|-----|--------|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `RESEND_API_KEY` | resend.com |
| `RESEND_AUDIENCE_ID` | Resend dashboard → Audiences |
| `MET_OFFICE_API_KEY` | metoffice.gov.uk/services/data/datapoint (free) |
| `DRAFT_EMAIL` | Your email address for draft review |

## Usage

### Run individual scrapers
```bash
python scrapers/defra_blog.py
python scrapers/met_office.py
python scrapers/ahdb_grain.py
# etc.
```

### Generate newsletter (requires ANTHROPIC_API_KEY)
```bash
python newsletter/generate.py
# Output: newsletter/output/field_notes_YYYY_MM_DD.html
```

### Send (draft mode by default)
```bash
python newsletter/send.py
# Sends to DRAFT_EMAIL. Set NEWSLETTER_ENV=live for broadcast.
```

### Daily monitor
```bash
python monitor/daily_check.py
```

## Cron Schedule (Hetzner, UTC)

```cron
# Sunday 8pm — run all scrapers
0 20 * * 0 /home/fieldnotes/field-notes/run_scrapers.sh

# Monday 5am — generate and send newsletter
0 5 * * 1 /home/fieldnotes/field-notes/run_newsletter.sh

# Daily 6am — RSS monitor
0 6 * * * /home/fieldnotes/field-notes/run_daily_check.sh
```

**BST (April–October):** shift all times 1 hour earlier.

## Project Structure

```
scrapers/       — 12 data scrapers (run independently)
data/           — JSON output from scrapers
data/previous/  — Last week's data for comparison
newsletter/     — Generator, HTML template, send script
monitor/        — Daily RSS change detector
prompts/        — 12 AI prompt files (one per section)
web/            — Landing page (index.html)
logs/           — Scraper and send logs
```

## Notes

- Scrapers are polite: 1-2s random delay, 3-attempt retry, descriptive User-Agent
- AHDB AJAX scrapers (grain, feed) require session cookies — if they fail, grain scraper falls back to market report HTML
- Met Office DataPoint falls back to Open-Meteo (no key needed)
- EDP/EADT block direct scraping — local_news.py uses RSS feeds only
- Set `NEWSLETTER_ENV=draft` (default) to review before switching to `live`
