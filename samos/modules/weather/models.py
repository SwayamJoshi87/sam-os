"""Weather module using OpenWeatherMap (or compatible one-call/current API)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from samos.db import ExternalError, get_conn


def _api_key() -> str:
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        raise ExternalError("OPENWEATHER_API_KEY not configured")
    return key


def _get(url: str, timeout: int = 10) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise ExternalError(f"weather API error: {e.code} {body}")
    except Exception as e:
        raise ExternalError(f"weather request failed: {e}")


def _cache(location: str, type_: str, payload: dict):
    with get_conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO weather_cache (location, type, payload, fetched_at)
            VALUES (?, ?, ?, ?)
            """,
            (location, type_, json.dumps(payload), datetime.now().isoformat()),
        )


def current_weather(location: str) -> dict:
    """Fetch current weather for a location."""
    key = _api_key()
    units = os.environ.get("OPENWEATHER_UNITS", "metric")
    q = urllib.parse.quote(location)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={q}&appid={key}&units={units}"
    data = _get(url)
    result = {
        "location": data.get("name", location),
        "description": data["weather"][0]["description"] if data.get("weather") else "unknown",
        "temp": data.get("main", {}).get("temp"),
        "feels_like": data.get("main", {}).get("feels_like"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind_speed": data.get("wind", {}).get("speed"),
        "timestamp": datetime.now().isoformat(),
    }
    _cache(location, "current", result)
    return result


def weather_forecast(location: str, days: int = 3) -> list[dict]:
    """Fetch multi-day forecast for a location.

    Uses the free 5-day/3-hour forecast endpoint and rolls into days.
    """
    key = _api_key()
    units = os.environ.get("OPENWEATHER_UNITS", "metric")
    q = urllib.parse.quote(location)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={q}&appid={key}&units={units}"
    data = _get(url)
    items = data.get("list", [])

    by_day: dict[str, list[dict]] = {}
    for item in items:
        dt = item.get("dt_txt", "")[:10]
        if dt not in by_day:
            by_day[dt] = []
        by_day[dt].append(item)

    out = []
    for dt in sorted(by_day.keys())[:days]:
        slots = by_day[dt]
        temps = [s["main"]["temp"] for s in slots]
        descriptions = [s["weather"][0]["description"] for s in slots if s.get("weather")]
        most_common = max(set(descriptions), key=descriptions.count) if descriptions else "unknown"
        out.append({
            "date": dt,
            "temp_min": min(temps) if temps else None,
            "temp_max": max(temps) if temps else None,
            "description": most_common,
        })

    _cache(location, "forecast", {"days": out})
    return out
