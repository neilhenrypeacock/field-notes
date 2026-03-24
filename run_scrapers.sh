#!/bin/bash
# Runs all scrapers. Called by cron on Sunday evening.
# Cron: 0 20 * * 0 (BST: 0 19 * * 0)

set -e
cd "$(dirname "$0")"
source .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scrapers_$(date +%Y%m%d).log"

echo "====== Field Notes scraper run: $(date) ======" >> "$LOG_FILE"

run_scraper() {
    local name="$1"
    local script="$2"
    echo "--- Starting $name ---" >> "$LOG_FILE"
    if python "$script" >> "$LOG_FILE" 2>&1; then
        echo "--- $name: OK ---" >> "$LOG_FILE"
    else
        echo "--- $name: FAILED (exit code $?) ---" >> "$LOG_FILE"
    fi
}

# Priority order: most critical data first
run_scraper "AHDB Grain"         "scrapers/ahdb_grain.py"
run_scraper "Met Office"         "scrapers/met_office.py"
run_scraper "Defra Blog"         "scrapers/defra_blog.py"
run_scraper "GOV.UK Schemes"     "scrapers/govuk_schemes.py"
run_scraper "AHDB Fertiliser"    "scrapers/ahdb_fertiliser.py"
run_scraper "AHDB Livestock"     "scrapers/ahdb_livestock.py"
run_scraper "Norwich Livestock"  "scrapers/norwich_livestock.py"
run_scraper "AHDB Feed"          "scrapers/ahdb_feed.py"
run_scraper "Land Listings"      "scrapers/land_listings.py"
run_scraper "Jobs"               "scrapers/jobs.py"
run_scraper "Local News"         "scrapers/local_news.py"
run_scraper "Events"             "scrapers/events.py"
run_scraper "Machinery Auctions" "scrapers/machinery_auctions.py"
run_scraper "EA Flood Alerts"   "scrapers/ea_alerts.py"

echo "====== Scraper run complete: $(date) ======" >> "$LOG_FILE"
echo "Scrapers complete. Log: $LOG_FILE"
