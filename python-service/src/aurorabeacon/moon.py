"""
moon.py

Pure functions for figuring out (a) whether the moon is currently above the
horizon, and (b) a "practical" illumination percentage that tapers up/down
over a 30-minute window near moonrise/moonset, instead of jumping instantly
from 0% to full strength the second the moon crosses the horizon.

Same rules as scoring.py and window_generator.py: no network, no filesystem,
no implicit "now" - every function takes the values it needs as parameters.

Ported from the JS getMoonState()/getMoonStateForNow() functions, including
the two real edge cases discovered along the way:
  1. moonrise can come AFTER moonset on a given day (the moon was already up
     from the previous day and sets before it rises again) - handled by
     checking which order the two times fall in, not assuming one order.
  2. Either field can be `null` on a given calendar day - the moon doesn't
     rise or set exactly once every day, since its cycle (~24h50m) doesn't
     line up neatly with a 24-hour calendar day.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .window_generator import parse_time


# ============================================================
# CONSTANTS
# ============================================================

RAMP_MINUTES = 30  # how long the taper near moonrise/moonset lasts


# ============================================================
# DATA SHAPE
# ============================================================

@dataclass
class MoonState:
    is_moon_up: bool
    practical_moon_illumination: float
    moonrise: datetime | None
    moonset: datetime | None


# ============================================================
# SMALL HELPERS
# ============================================================

def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _minutes_between(a: datetime, b: datetime) -> float:
    """b - a, in minutes. Can be negative if b is before a."""
    return (b - a).total_seconds() / 60.0


# ============================================================
# CORE LOGIC
# ============================================================

def get_moon_state(day: dict, moment: datetime) -> MoonState:
    """
    day: one entry from astro_json (has "date", "moonrise", "moonset",
         "moon_illumination" - moonrise/moonset may be None).
    moment: the specific time to evaluate.
    """
    moonrise = parse_time(day["date"], day["moonrise"]) if day.get("moonrise") else None
    moonset = parse_time(day["date"], day["moonset"]) if day.get("moonset") else None

    is_moon_up, ramp_factor = _moon_up_and_ramp(moonrise, moonset, moment)

    practical_illumination = 0.0
    if is_moon_up:
        practical_illumination = round(day["moon_illumination"] * ramp_factor, 1)

    return MoonState(
        is_moon_up=is_moon_up,
        practical_moon_illumination=practical_illumination,
        moonrise=moonrise,
        moonset=moonset,
    )


def _moon_up_and_ramp(
    moonrise: datetime | None,
    moonset: datetime | None,
    moment: datetime,
) -> tuple[bool, float]:
    """
    Returns (is_moon_up, ramp_factor).
    ramp_factor is 1.0 when moment is more than RAMP_MINUTES away from
    whichever boundary is closest, and tapers toward 0.0 right at the
    boundary - handles the "just cleared the horizon" case from earlier
    in the project.
    """
    # --- Case: both times missing (rare, not expected in Scotland) ---
    if moonrise is None and moonset is None:
        return False, 0.0

    # --- Case: only moonrise known (moon rose today, doesn't set until tomorrow) ---
    if moonrise is not None and moonset is None:
        if moment < moonrise:
            return False, 0.0
        since_rise = _minutes_between(moonrise, moment)
        ramp = clamp01(since_rise / RAMP_MINUTES)
        return True, ramp

    # --- Case: only moonset known (moon was already up, sets today) ---
    if moonrise is None and moonset is not None:
        if moment >= moonset:
            return False, 0.0
        until_set = _minutes_between(moment, moonset)
        ramp = clamp01(until_set / RAMP_MINUTES)
        return True, ramp

    # --- Case: both known - the normal case, but order can flip ---
    if moonrise < moonset:
        is_up = moonrise <= moment < moonset
    else:
        is_up = moment < moonset or moment >= moonrise

    if not is_up:
        return False, 0.0

    # Ramp near whichever boundary we're closest to. Handle the day-wrap
    # the same way the JS version did: if we're measuring "since moonrise"
    # but moonrise is actually later in the clock than moonset (the flipped
    # case), the rise happened "yesterday" relative to moment - add 24h.
    if moment >= moonrise:
        since_rise = _minutes_between(moonrise, moment)
    else:
        since_rise = _minutes_between(moonrise - timedelta(days=1), moment)

    if moment < moonset:
        until_set = _minutes_between(moment, moonset)
    else:
        until_set = _minutes_between(moment, moonset + timedelta(days=1))

    if since_rise < RAMP_MINUTES:
        ramp = clamp01(since_rise / RAMP_MINUTES)
    elif until_set < RAMP_MINUTES:
        ramp = clamp01(until_set / RAMP_MINUTES)
    else:
        ramp = 1.0

    return True, ramp


# ============================================================
# DAY SELECTION
# Given several days of astro data, pick the one matching a specific moment's
# calendar date - matters for cross-midnight moments (e.g. 2am "belongs" to
# yesterday's moonrise/moonset context in some cases).
# ============================================================

def get_moon_state_for_time(days: list[dict], moment: datetime) -> MoonState:
    target_date_str = moment.strftime("%Y-%m-%d")
    day = next((d for d in days if d["date"] == target_date_str), days[0])
    return get_moon_state(day, moment)


# ============================================================
# QUICK MANUAL TEST
# ============================================================

if __name__ == "__main__":
    # Normal case: moonrise before moonset, same day.
    normal_day = {
        "date": "2026-09-08",
        "moonrise": "02:11:55",
        "moonset": "19:15:27",
        "moon_illumination": 9.11,
    }
    print("Just before moonrise:", get_moon_state(normal_day, datetime(2026, 9, 8, 2, 0)))
    print("Right at moonrise:   ", get_moon_state(normal_day, datetime(2026, 9, 8, 2, 12)))
    print("Well after moonrise: ", get_moon_state(normal_day, datetime(2026, 9, 8, 10, 0)))
    print("Near moonset:        ", get_moon_state(normal_day, datetime(2026, 9, 8, 19, 5)))

    # Null-moonrise case, straight from real API output seen earlier.
    null_moonrise_day = {
        "date": "2026-09-06",
        "moonrise": None,
        "moonset": "18:44:23",
        "moon_illumination": 26.42,
    }
    print("\nNull moonrise, before set:", get_moon_state(null_moonrise_day, datetime(2026, 9, 6, 10, 0)))
    print("Null moonrise, after set: ", get_moon_state(null_moonrise_day, datetime(2026, 9, 6, 20, 0)))