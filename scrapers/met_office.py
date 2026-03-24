"""
Scraper: Met Office DataPoint API — 5-day daily forecast for Norwich.
Falls back to Open-Meteo if DataPoint key not configured or request fails.
Outputs: data/met_office.json
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.base import archive_current, get, save_data

logger = logging.getLogger("field_notes.met_office")

# Norwich coordinates
LAT = 52.63
LON = 1.30

# Met Office DataPoint — Norwich location ID (query site list to verify)
NORWICH_LOCATION_ID = "310136"

WEATHER_CODES = {
    0: "Clear", 1: "Sunny", 2: "Partly cloudy", 3: "Partly cloudy",
    5: "Mist", 6: "Fog", 7: "Cloudy", 8: "Overcast",
    9: "Light rain shower", 10: "Light rain shower", 11: "Drizzle",
    12: "Light rain", 13: "Heavy rain shower", 14: "Heavy rain shower",
    15: "Heavy rain", 16: "Sleet shower", 17: "Sleet shower", 18: "Sleet",
    19: "Hail shower", 20: "Hail shower", 21: "Hail",
    22: "Light snow shower", 23: "Light snow shower", 24: "Light snow",
    25: "Heavy snow shower", 26: "Heavy snow shower", 27: "Heavy snow",
    28: "Thunder shower", 29: "Thunder shower", 30: "Thunder",
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _datapoint(api_key: str) -> list[dict]:
    """Fetch 5-day daily forecast from Met Office DataPoint."""
    url = (
        f"http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/"
        f"{NORWICH_LOCATION_ID}?res=daily&key={api_key}"
    )
    resp = get(url)
    data = resp.json()

    periods = data["SiteRep"]["DV"]["Location"]["Period"]
    days = []
    for period in periods:
        date_str = period["value"].split("Z")[0]  # "2026-03-23Z" → "2026-03-23"
        reps = period["Rep"]
        if isinstance(reps, dict):
            reps = [reps]

        day_rep = next((r for r in reps if r.get("$") == "Day"), reps[0] if reps else {})
        night_rep = next((r for r in reps if r.get("$") == "Night"), {})

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days.append({
            "date": date_str,
            "day_of_week": DAY_NAMES[dt.weekday()],
            "weather_type_code": int(day_rep.get("W", -1)),
            "weather_description": WEATHER_CODES.get(int(day_rep.get("W", -1)), "Unknown"),
            "max_temp_c": int(day_rep.get("Dm", day_rep.get("T", 0))),
            "min_temp_c": int(night_rep.get("Nm", night_rep.get("T", 0))),
            "wind_speed_mph": int(day_rep.get("S", 0)),
            "wind_direction": day_rep.get("D", ""),
            "wind_gust_mph": int(day_rep.get("G", 0)),
            "precip_probability_pct": int(day_rep.get("PPd", day_rep.get("PP", 0))),
            "uv_index": int(day_rep.get("U", 0)),
            "humidity_pct": int(day_rep.get("H", 0)),
            "farming_summary": None,
        })
    return days


def _open_meteo() -> list[dict]:
    """Fallback: Open-Meteo free API, no key required."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        f"precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max"
        f"&wind_speed_unit=mph&timezone=Europe/London&forecast_days=7"
    )
    resp = get(url)
    data = resp.json()
    daily = data["daily"]

    # WMO weather codes → simple description
    wmo_desc = {
        0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow",
        80: "Light rain shower", 81: "Rain shower", 82: "Heavy rain shower",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
    }

    days = []
    for i, date_str in enumerate(daily["time"]):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        code = daily["weather_code"][i]
        days.append({
            "date": date_str,
            "day_of_week": DAY_NAMES[dt.weekday()],
            "weather_type_code": code,
            "weather_description": wmo_desc.get(code, "Unknown"),
            "max_temp_c": round(daily["temperature_2m_max"][i]),
            "min_temp_c": round(daily["temperature_2m_min"][i]),
            "wind_speed_mph": round(daily["wind_speed_10m_max"][i]),
            "wind_direction": "",
            "wind_gust_mph": round(daily["wind_gusts_10m_max"][i]),
            "precip_probability_pct": daily["precipitation_probability_max"][i],
            "uv_index": 0,
            "humidity_pct": 0,
            "farming_summary": None,
        })
    return days


def scrape() -> dict:
    api_key = os.getenv("MET_OFFICE_API_KEY", "")
    source = "unknown"

    days = []
    if api_key:
        try:
            logger.info("Fetching Met Office DataPoint forecast for Norwich")
            days = _datapoint(api_key)
            source = "Met Office DataPoint"
        except Exception as exc:
            logger.warning("DataPoint failed (%s), falling back to Open-Meteo", exc)

    if not days:
        logger.info("Fetching Open-Meteo forecast for Norwich (lat=%s, lon=%s)", LAT, LON)
        try:
            days = _open_meteo()
            source = "Open-Meteo (fallback)"
        except Exception as exc:
            logger.error("Open-Meteo also failed: %s", exc)
            return {"error": True, "message": str(exc)}

    logger.info("Got %d-day forecast from %s", len(days), source)
    return {
        "source": source,
        "location": "Norwich, East Anglia",
        "latitude": LAT,
        "longitude": LON,
        "forecast_from": days[0]["date"] if days else None,
        "days": days,
        "wind_unit": "mph",
        "temp_unit": "celsius",
    }


if __name__ == "__main__":
    archive_current("met_office.json")
    data = scrape()
    save_data("met_office.json", data)
    if not data.get("error"):
        print(f"Got {len(data['days'])}-day forecast from {data['source']}")
        for d in data["days"]:
            print(f"  {d['day_of_week']} {d['date']}: {d['weather_description']}, {d['max_temp_c']}°C max, {d['wind_speed_mph']}mph wind")
