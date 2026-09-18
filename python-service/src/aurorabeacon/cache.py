"""
cache.py

The ONLY module in this project allowed to touch the filesystem. Every other
module (scoring.py, window_generator.py, moon.py) stays pure - this is where
that boundary is enforced.

Reads aurora_cache.json (currently written by the n8n crons) and hands back
ready-to-use Python objects instead of raw JSON strings - the four *_json
fields in the cache file are JSON-encoded STRINGS (since each n8n cron wrote
its own slice independently), so this module's job includes un-wrapping
those strings back into real lists/dicts.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================


# Anchored to this file's own location, not the process's working directory -
# always resolves to the same file no matter where `uv run` is launched from.
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "aurora_cache.json"
CACHE_PATH = os.environ.get("AURORA_CACHE_PATH", str(DEFAULT_CACHE_PATH))


# ============================================================
# DATA SHAPE
# ============================================================

@dataclass
class AuroraCache:
    astro_days: list[dict]
    kp_forecast: list[dict]
    weather_hourly: list[dict]
    ovation_probability: float
    ovation_observation_time: str | None
    ovation_forecast_time: str | None


# ============================================================
# LOADING
# ============================================================

def load_cache(path: str = CACHE_PATH) -> AuroraCache:
    """
    Reads the cache file and parses it into an AuroraCache.
    Raises FileNotFoundError if the file doesn't exist yet, and
    json.JSONDecodeError if it's corrupt - deliberately NOT swallowed here,
    since a missing/broken cache is something callers (e.g. a FastAPI
    endpoint) need to know about and handle explicitly, not something this
    module should silently paper over.
    """
    with open(path, "r") as f:
        raw = json.load(f)

    return AuroraCache(
        astro_days=json.loads(raw["astro_json"]) if raw.get("astro_json") else [],
        kp_forecast=json.loads(raw["kpforecast_json"]) if raw.get("kpforecast_json") else [],
        weather_hourly=json.loads(raw["weather_json"]) if raw.get("weather_json") else [],
        ovation_probability=raw.get("ovation_probability", 0.0),
        ovation_observation_time=raw.get("ovation_observation_time"),
        ovation_forecast_time=raw.get("ovation_forecast_time"),
    )


# ============================================================
# QUICK MANUAL TEST
# ============================================================

if __name__ == "__main__":
    try:
        cache = load_cache()
        print(f"Astro days loaded: {len(cache.astro_days)}")
        print(f"Kp forecast entries: {len(cache.kp_forecast)}")
        print(f"Weather entries: {len(cache.weather_hourly)}")
        print(f"OVATION probability: {cache.ovation_probability}")
    except FileNotFoundError:
        print(f"No cache file found at {CACHE_PATH}")
        print("Set AURORA_CACHE_PATH env var to point at the real file, e.g.:")
        print("  AURORA_CACHE_PATH=/path/to/aurora_cache.json uv run cache.py")


# ============================================================
# cache file update helper
# ============================================================

def update_cache(updates: dict, path: str = CACHE_PATH) -> None:
    """
    Merges `updates` into the existing cache file, touching only the keys
    provided - existing keys from other fetchers are left untouched.
    Creates the file if it doesn't exist yet.
    """
    try:
        with open(path, "r") as f:
            current = json.load(f)
    except FileNotFoundError:
        current = {}

    current.update(updates)

    with open(path, "w") as f:
        json.dump(current, f, indent=2)