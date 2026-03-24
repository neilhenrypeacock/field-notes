"""
Scraper: Local farming news via RSS feeds.
Sources: Agriland UK, Defra Blog, NFU East Anglia, Farmers Guardian.
Keyword-filters for East Anglia farming relevance.
Outputs: data/local_news.json
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import re

import feedparser
import requests as _req
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, save_data

logger = logging.getLogger("field_notes.local_news")

FEEDS = [
    # EDP24 and EADT RSS endpoints return HTML — not available as RSS currently
    {"source": "Agriland UK", "url": "https://www.agriland.co.uk/feed/"},
    {"source": "Defra Blog", "url": "https://defrafarming.blog.gov.uk/feed/"},
]

# NFU and Farmers Guardian have no working RSS — scraped via HTML instead
NFU_NEWS_URL = "https://www.nfuonline.com/updates-and-information/"
FG_NEWS_URL = "https://www.farmersguardian.com/news/"

KEYWORDS = [
    "farm", "farming", "arable", "wheat", "barley", "osr", "oilseed", "beet",
    "sugar beet", "potato", "livestock", "pig", "poultry", "egg", "dairy",
    "nfu", "ahdb", "defra", "sfi", "countryside stewardship", "fetf",
    "norfolk", "suffolk", "cambridgeshire", "east anglia", "east anglian",
    "fakenham", "norwich", "bury st edmunds", "ely", "peterborough",
    "harvest", "drilling", "spraying", "agronomist", "agronomy",
    "avian flu", "bird flu", "tb", "bovine", "apha",
]

DAYS_BACK = 8


def _is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


def _parse_date(entry) -> "str | None":
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
    return None


def _text_summary(entry) -> str:
    for attr in ("summary", "description"):
        val = getattr(entry, attr, "")
        if val:
            return BeautifulSoup(val, "html.parser").get_text(strip=True)[:300]
    return ""


def _fix_xml(content: bytes) -> bytes:
    """Fix common RSS XML issues: unescaped & in attributes/text."""
    text = content.decode("utf-8", errors="replace")
    # Replace & not followed by a valid entity reference with &amp;
    text = re.sub(r"&(?!(?:[a-zA-Z]\w{0,10}|#\d{1,6}|#x[\da-fA-F]{1,5});)", "&amp;", text)
    return text.encode("utf-8")


def _scrape_feed(source_name: str, feed_url: str, cutoff: datetime) -> list[dict]:
    logger.info("Fetching %s RSS: %s", source_name, feed_url)
    try:
        resp = _req.get(feed_url, timeout=15, headers={"User-Agent": "FieldNotes/1.0"})
        content = _fix_xml(resp.content)
        feed = feedparser.parse(content)
    except Exception as exc:
        logger.warning("%s fetch failed: %s", source_name, exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("%s feed failed: %s", source_name, feed.bozo_exception)
        return []

    articles = []
    for entry in feed.entries:
        pub_str = _parse_date(entry)
        if pub_str:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            if pub_dt < cutoff:
                continue

        title = entry.get("title", "")
        summary = _text_summary(entry)
        full_text = f"{title} {summary}"

        if not _is_relevant(full_text):
            continue

        articles.append({
            "source": source_name,
            "title": title,
            "url": entry.get("link", ""),
            "published": pub_str,
            "summary": summary,
            "relevance_keywords": [kw for kw in KEYWORDS if kw in full_text.lower()][:5],
        })

    logger.info("%s: %d relevant articles", source_name, len(articles))
    return articles


def _scrape_html_nfu(cutoff: datetime) -> list:
    """Scrape NFU news from HTML page — NFU has no working RSS feed."""
    source = "NFU"
    logger.info("Fetching %s news (HTML): %s", source, NFU_NEWS_URL)
    try:
        resp = _req.get(NFU_NEWS_URL, timeout=15, headers={"User-Agent": "FieldNotes/1.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:
        logger.warning("%s HTML fetch failed: %s", source, exc)
        return []

    articles = []
    # Cards: <div class="card isLink">
    for card in soup.find_all("div", class_="card isLink"):
        link_el = card.find("a", class_="stretched-link")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        href = link_el.get("href", "")
        if not href.startswith("http"):
            href = "https://www.nfuonline.com" + href

        # Date: <time class="nfu-timeago" datetime="2026-03-23T16:00:00Z">
        time_el = card.find("time", class_="nfu-timeago")
        pub_str = None
        if time_el and time_el.get("datetime"):
            try:
                pub_dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
                pub_str = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        if not _is_relevant(title):
            continue

        articles.append({
            "source": source,
            "title": title,
            "url": href,
            "published": pub_str,
            "summary": "",
            "relevance_keywords": [kw for kw in KEYWORDS if kw in title.lower()][:5],
        })

    logger.info("%s: %d relevant articles (HTML)", source, len(articles))
    return articles


def _scrape_html_fg(cutoff: datetime) -> list:
    """Scrape Farmers Guardian news from HTML page — FG RSS feed is broken."""
    source = "Farmers Guardian"
    logger.info("Fetching %s news (HTML): %s", source, FG_NEWS_URL)
    try:
        resp = _req.get(
            FG_NEWS_URL, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FieldNotes/1.0)"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:
        logger.warning("%s HTML fetch failed: %s", source, exc)
        return []

    articles = []
    # Cards: <div class="row no-gutters listing-article-block">
    for card in soup.find_all("div", class_=lambda c: c and "listing-article-block" in c):
        # Title + link: div.platformheading h4 a
        heading_div = card.find("div", class_="platformheading")
        if not heading_div:
            continue
        link_el = heading_div.find("a", href=True)
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        href = link_el["href"]
        if not href.startswith("http"):
            href = "https://www.farmersguardian.com" + href

        # Date: div.published text like "24 March 2026 • 1 min read"
        pub_str = None
        pub_div = card.find("div", class_="published")
        if pub_div:
            import re as _re
            m = _re.search(r"(\d{1,2}\s+\w+\s+202\d)", pub_div.get_text())
            if m:
                try:
                    pub_dt = datetime.strptime(m.group(1), "%d %B %Y").replace(tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    pass

        # Summary: div.searchpara p
        summary_el = card.find("div", class_="searchpara")
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

        full_text = f"{title} {summary}"
        if not _is_relevant(full_text):
            continue

        articles.append({
            "source": source,
            "title": title,
            "url": href,
            "published": pub_str,
            "summary": summary,
            "relevance_keywords": [kw for kw in KEYWORDS if kw in full_text.lower()][:5],
        })

    logger.info("%s: %d relevant articles (HTML)", source, len(articles))
    return articles


def _scrape_feed_with_fallback(feed: dict, cutoff: datetime) -> list:
    """Try primary URL, then fallback_urls in order; return first non-empty result."""
    source = feed["source"]
    urls = [feed["url"]] + feed.get("fallback_urls", [])
    for url in urls:
        articles = _scrape_feed(source, url, cutoff)
        if articles:
            return articles
        logger.info("%s: no articles from %s, trying next URL", source, url)
    logger.warning("%s: all feed URLs exhausted — no articles found", source)
    return []


def scrape() -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    all_articles = []

    for feed in FEEDS:
        articles = _scrape_feed_with_fallback(feed, cutoff)
        all_articles.extend(articles)

    # NFU and Farmers Guardian: HTML scraping (no working RSS)
    all_articles.extend(_scrape_html_nfu(cutoff))
    all_articles.extend(_scrape_html_fg(cutoff))

    # Sort by published date, newest first
    all_articles.sort(key=lambda a: a.get("published") or "", reverse=True)
    # Deduplicate by title
    seen_titles = set()
    deduped = []
    for a in all_articles:
        if a["title"] not in seen_titles:
            seen_titles.add(a["title"])
            deduped.append(a)

    active_sources = list(dict.fromkeys(a["source"] for a in deduped))
    logger.info("Total relevant articles: %d (sources: %s)", len(deduped), ", ".join(active_sources))
    return {
        "sources": [f["source"] for f in FEEDS] + ["NFU", "Farmers Guardian"],
        "active_sources": active_sources,
        "articles": deduped[:20],
        "count": len(deduped),
    }


if __name__ == "__main__":
    archive_current("local_news.json")
    data = scrape()
    save_data("local_news.json", data)
    print(f"Found {data['count']} relevant articles")
    for a in data["articles"][:5]:
        print(f"  [{a['source']}] {a['title']}")
