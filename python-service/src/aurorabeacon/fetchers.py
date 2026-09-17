"""
fetchers.py

Four functions, one per data source, each doing the same three things:
  1. Fetch raw data from the API
  2. Trim/reshape it to only what the app actually uses
  3. Merge just its own slice into the cache file (via cache.update_cache)

This is the direct Python replacement for the four n8n crons - same logic,
just no n8n involved. Each function is independent and knows nothing about
the others, matching the original n8n design (separate crons, separate
cadences, separate cache keys).
"""

import json
import math
from datetime import datetime, timedelta, timezone as dt_timezone

import httpx

from .cache import update_cache


# ============================================================
# LOCATION
# Hardcoded for now - a single-location personal project. Would become a
# parameter if this ever needed to support more than one place.
# ============================================================

LATITUDE = 57.4778
LONGITUDE = -4.2247


# ============================================================
# KP FORECAST
# Global (no location needed) - NOAA's 3-day Kp forecast, UTC timestamps.
# ============================================================

def fetch_kp() -> None:
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
    response = httpx.get(url)
    response.raise_for_status()

    rows = response.json()
    now = datetime.now(dt_timezone.utc)

    future_rows = [
        {"time_tag": row["time_tag"], "kp": row["kp"], "observed": row["observed"]}
        for row in rows
        if datetime.fromisoformat(row["time_tag"]).replace(tzinfo=dt_timezone.utc) >= now
    ]

    update_cache({
        "kpforecast_json": json.dumps(future_rows),
        "kpforecast_updated_at": datetime.now(dt_timezone.utc).isoformat(),
    })


# ============================================================
# WEATHER
# Open-Meteo, location-specific, UTC (kept consistent with the original
# design decision - see forecast.py for how UTC gets reconciled with the
# local-time astro/moon data when they're actually compared).
# ============================================================

def fetch_weather() -> None:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,"
                  "visibility,temperature_2m,dew_point_2m",
        "forecast_days": 3,
        "timezone": "UTC",
    }
    response = httpx.get(url, params=params)
    response.raise_for_status()

    hourly = response.json()["hourly"]
    now = datetime.now(dt_timezone.utc)

    weather_data = []
    for i, time_str in enumerate(hourly["time"]):
        # Open-Meteo's "time" has no timezone suffix - it's UTC because we
        # asked for UTC, so attach that explicitly before comparing to `now`.
        entry_time = datetime.fromisoformat(time_str).replace(tzinfo=dt_timezone.utc)
        if entry_time < now:
            continue
        weather_data.append({
            "time": time_str,
            "cloud_cover": hourly["cloud_cover"][i],
            "cloud_cover_low": hourly["cloud_cover_low"][i],
            "cloud_cover_mid": hourly["cloud_cover_mid"][i],
            "cloud_cover_high": hourly["cloud_cover_high"][i],
            "visibility": hourly["visibility"][i],
            "temperature_2m": hourly["temperature_2m"][i],
            "dew_point_2m": hourly["dew_point_2m"][i],
        })

    update_cache({
        "weather_json": json.dumps(weather_data),
        "weather_updated_at": datetime.now(dt_timezone.utc).isoformat(),
    })


# ============================================================
# ASTRO
# sunrisesunset.io, location-specific, local time. Fetches a rolling 4-day
# window (today + 3 buffer days) - see window_generator.py's comments on
# why one extra day is needed to close out the last night's span.
# ============================================================

def fetch_astro() -> None:
    today = datetime.now().date()
    date_end = today + timedelta(days=4)

    url = "https://api.sunrisesunset.io/json"
    params = {
        "lat": LATITUDE,
        "lng": LONGITUDE,
        "date_start": today.isoformat(),
        "date_end": date_end.isoformat(),
        "time_format": "24",
    }
    response = httpx.get(url, params=params)
    response.raise_for_status()

    days = response.json()["results"]

    trimmed = [
        {
            "date": d["date"],
            "first_light": d["first_light"],
            "last_light": d["last_light"],
            "nautical_twilight_begin": d["nautical_twilight_begin"],
            "nautical_twilight_end": d["nautical_twilight_end"],
            "moonrise": d["moonrise"],
            "moonset": d["moonset"],
            "moon_illumination": d["moon_illumination"],
            "moon_phase": d["moon_phase"],
        }
        for d in days
    ]

    update_cache({
        "astro_json": json.dumps(trimmed),
        "astro_updated_at": datetime.now(dt_timezone.utc).isoformat(),
    })


# ============================================================
# OVATION
# NOAA's global aurora probability grid - no location parameter exists on
# this endpoint, so we fetch the whole globe and find the nearest grid
# point to our own coordinates locally (same approach as the n8n version,
# including the cos(latitude) correction for longitude degree-shrinkage).
# ============================================================

def fetch_ovation() -> None:
    url = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
    response = httpx.get(url)
    response.raise_for_status()

    data = response.json()

    lon_scale = math.cos(math.radians(LATITUDE))
    best_value = 0
    best_dist = float("inf")

    for grid_lon, grid_lat, value in data["coordinates"]:
        dist = math.sqrt((grid_lat - LATITUDE) ** 2 + ((grid_lon - LONGITUDE) * lon_scale) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_value = value

    update_cache({
        "ovation_probability": best_value,
        "ovation_observation_time": data["Observation Time"],
        "ovation_forecast_time": data["Forecast Time"],
        "ovation_updated_at": datetime.now(dt_timezone.utc).isoformat(),
    })


# ============================================================
# QUICK MANUAL TEST
# Run this file directly to fetch all four sources once, in sequence.
# ============================================================

if __name__ == "__main__":
    print("Fetching Kp...")
    fetch_kp()
    print("Fetching weather...")
    fetch_weather()
    print("Fetching astro...")
    fetch_astro()
    print("Fetching OVATION...")
    fetch_ovation()
    print("Done - check aurora_cache.json")