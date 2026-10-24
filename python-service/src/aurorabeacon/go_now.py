"""
go_now.py

The "go now" alert. Runs every 30 minutes through the night, a few minutes after
fresh weather and OVATION data land. If it's dark, the sky is workable and NOAA's
OVATION probability for your location is up, it sends ONE push notification, then
stays quiet unless things get clearly better or a cooldown has passed.

How it differs from the 7pm alert (notification_job.py):
  - 7pm alert  = planning: "tonight looks promising" (forecast Kp based)
  - go-now     = nowcast:  "it's happening, look north" (OVATION has 30-90 min lead)

Every threshold below is a starting guess. Each check prints one line to
`docker logs`, so after a week of real nights you can tune them from real values.
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from .cache import load_cache, read_value, update_cache
from .forecast import find_nearest_weather
from .notifier import send_notification
from .scoring import cloud_gate
from .window_generator import build_period_spans, get_sky_period


# ============================================================
# TUNING KNOBS
# ============================================================

# (minimum OVATION %, alert level). Checked top to bottom, first match wins.
OVATION_LEVELS = [(50, 3), (25, 2), (10, 1)]
LEVEL_LABELS = {1: "Possible", 2: "Likely", 3: "Strong"}

# scoring.cloud_gate is 1.0 up to 65% cloud and falls to 0.0 at 95%.
# 0.5 means "skip the alert if cloud cover is above roughly 80%".
MIN_CLOUD_GATE = 0.5

# After an alert, stay quiet this long unless the level goes UP.
COOLDOWN = timedelta(hours=3)

# Ignore OVATION data older than this (e.g. if the fetch job has been failing).
MAX_OVATION_AGE = timedelta(hours=2)

# Between these local hours, alerts below level 3 go out at "low" priority
# (no sound, still visible in the morning). Set to None to disable.
QUIET_HOURS = (0, 6)

STATE_KEY = "go_now_state"


# ============================================================
# HELPERS
# ============================================================

def ovation_level(probability: float) -> int:
    for minimum, level in OVATION_LEVELS:
        if probability >= minimum:
            return level
    return 0


def _ovation_is_fresh(updated_at: str | None) -> bool:
    if not updated_at:
        return False
    age = datetime.now(dt_timezone.utc) - datetime.fromisoformat(updated_at)
    return age <= MAX_OVATION_AGE


def _in_quiet_hours(now: datetime) -> bool:
    return QUIET_HOURS is not None and QUIET_HOURS[0] <= now.hour < QUIET_HOURS[1]


# ============================================================
# THE CHECK
# ============================================================

def run_go_now_check(now: datetime | None = None) -> str:
    """Runs one check, prints a one-line status, and returns it."""
    now = now or datetime.now()
    status = _check(now)
    print(f"[go_now] {now:%Y-%m-%d %H:%M} {status}")
    return status


def _check(now: datetime) -> str:
    try:
        cache = load_cache()
    except FileNotFoundError:
        return "skip: no cache yet"

    if not cache.astro_days:
        return "skip: no astro data"

    # 1. Is it dark at all?
    sky = get_sky_period(build_period_spans(cache.astro_days), now)
    if sky == "Bright Sky":
        return "skip: daylight"

    # 2. Is the live OVATION value fresh and high enough?
    if not _ovation_is_fresh(cache.ovation_updated_at):
        return "skip: OVATION data missing or stale"
    probability = cache.ovation_probability
    level = ovation_level(probability)
    if level == 0:
        return f"skip: OVATION {probability}% below minimum"

    # 3. Is the sky workable right now?
    weather = find_nearest_weather(cache.weather_hourly, now)
    cloud = weather["cloud_cover"] if weather else 100.0
    if cloud_gate(cloud) < MIN_CLOUD_GATE:
        return f"skip: too cloudy ({cloud}%), OVATION {probability}%"

    # 4. Dedupe: send if the cooldown has passed OR the level has gone up.
    state = read_value(STATE_KEY, {}) or {}
    last_at = datetime.fromisoformat(state["last_alert_at"]) if state.get("last_alert_at") else None
    last_level = state.get("last_level", 0)
    cooled_down = last_at is None or now - last_at >= COOLDOWN
    if not cooled_down and level <= last_level:
        return f"skip: cooldown (last alert {last_at:%H:%M}, level {last_level})"

    # 5. Send it.
    quiet = _in_quiet_hours(now) and level < 3
    priority = "low" if quiet else ("high" if level >= 2 else "default")
    send_notification(
        title=f"Aurora: {LEVEL_LABELS[level]} now",
        message=f"OVATION {probability:.0f}% | cloud {cloud:.0f}% | {sky}. Head out and look north.",
        priority=priority,
        tags="milky_way",
    )
    update_cache({STATE_KEY: {"last_alert_at": now.isoformat(), "last_level": level}})
    return f"SENT level {level} (OVATION {probability}%, cloud {cloud}%, priority {priority})"


if __name__ == "__main__":
    run_go_now_check()