"""
Scraper: Agricultural jobs in East Anglia.
Primary source: FW Jobs East of England.
Outputs: data/jobs.json
"""

import logging
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.jobs")

JOBS_URL = "https://jobs.fwi.co.uk/jobs/east-of-england/"
EA_COUNTIES = {"norfolk", "suffolk", "cambridge", "cambridgeshire", "essex", "east anglia", "east of england"}


def _is_ea_relevant(text: str) -> bool:
    return any(county in text.lower() for county in EA_COUNTIES)


def _parse_fwi_jobs(soup: BeautifulSoup) -> list[dict]:
    """
    FW Jobs page structure:
    <li class="lister__item cf" id="item-XXXXXXX">
      <div class="lister__details cf js-clickable">
        <h3 class="lister__header"><a href="/job/...">Title</a></h3>
        <ul class="lister__meta">
          <li class="lister__meta-item lister__meta-item--location">Location</li>
          <li class="lister__meta-item lister__meta-item--salary">Salary</li>
        </ul>
      </div>
    </li>
    """
    jobs = []
    cards = soup.select("li.lister__item")
    for card in cards:
        title_el = card.find("h3", class_="lister__header")
        if not title_el:
            continue
        link_el = title_el.find("a", href=True)
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        url = link_el["href"].strip()
        if url and not url.startswith("http"):
            url = "https://jobs.fwi.co.uk" + url

        location_el = card.find("li", class_="lister__meta-item--location")
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.find("li", class_="lister__meta-item--salary")
        salary = salary_el.get_text(strip=True) if salary_el else ""

        employer_el = card.find("li", class_="lister__meta-item--recruiter")
        employer = employer_el.get_text(strip=True) if employer_el else ""

        jobs.append({
            "title": title,
            "employer": employer,
            "location": location,
            "salary": salary,
            "description_snippet": "",
            "url": url,
        })

    return jobs


def scrape() -> dict:
    logger.info("Fetching FW Jobs East of England: %s", JOBS_URL)
    try:
        resp = get(JOBS_URL)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.error("Failed to fetch FW Jobs: %s", exc)
        return {"error": True, "message": str(exc)}

    jobs = _parse_fwi_jobs(soup)

    # Attempt to get total count from page
    total_text = soup.find(string=lambda t: t and "job" in t.lower() and any(c.isdigit() for c in t))
    total_available = 0
    if total_text:
        import re
        m = re.search(r"(\d+)", total_text)
        if m:
            total_available = int(m.group(1))

    logger.info("Found %d East Anglia jobs", len(jobs))
    return {
        "source": "FW Jobs East of England",
        "source_url": JOBS_URL,
        "jobs": jobs[:15],
        "total_shown": len(jobs),
        "total_available": total_available,
    }


if __name__ == "__main__":
    archive_current("jobs.json")
    data = scrape()
    save_data("jobs.json", data)
    print(f"Found {data.get('total_shown', 0)} jobs")
    for j in data.get("jobs", [])[:5]:
        print(f"  {j['title']} — {j['location']} — {j['salary']}")
