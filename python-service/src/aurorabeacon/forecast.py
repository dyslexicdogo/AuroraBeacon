"""
forecast.py

The "glue" layer: for every dark-sky window in the forecast period, find the
matching weather and Kp data, work out the moon's contribution, and produce
a final score. This is the direct Python equivalent of the JS version's
renderForecastTable() loop.

NOTE ON TIME: this file assumes all input timestamps (astro, weather, Kp)
are already in the SAME timezone convention as each other. Getting that
alignment right for real fetched data is a decision for when fetchers.py
is written - see the conversation notes. Here, all sample data below is
deliberately kept in one consistent timeline so we can test the MATCHING
logic itself without also fighting timezone conversion at the same time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .window_generator import build_period_spans, generate_30_min_windows, get_dark_windows
from .moon import get_moon_state_for_time
from .scoring import calculate_score, ScoreBreakdown


# ============================================================
# CONSTANTS
# ============================================================

# Kp forecast entries are 3 hours apart. A window matches a Kp entry if it
# falls within this many hours of it - wide enough to always find a match,
# narrow enough to not accidentally grab the wrong 3-hour bucket.
KP_MATCH_WINDOW_HOURS = 2


# ============================================================
# DATA SHAPE
# ============================================================

@dataclass
class ForecastPoint:
    time: datetime
    sky_period: str
    score: ScoreBreakdown


# ============================================================
# NEAREST-MATCH LOOKUPS
# ============================================================

def find_nearest_weather(weather_hourly: list[dict], moment: datetime) -> dict | None:
    """
    Returns the weather entry whose "time" is closest to moment.
    Mirrors the JS getWeatherForTime()'s closest-match approach.
    """
    if not weather_hourly:
        return None

    def parse_weather_time(entry: dict) -> datetime:
        # Open-Meteo's hourly "time" looks like "2026-09-11T07:00" - no seconds.
        return datetime.strptime(entry["time"], "%Y-%m-%dT%H:%M")

    return min(weather_hourly, key=lambda entry: abs(parse_weather_time(entry) - moment))


def find_kp_for_time(kp_forecast: list[dict], moment: datetime) -> float:
    """
    Returns the highest Kp value among forecast entries within
    KP_MATCH_WINDOW_HOURS of moment. Mirrors the JS getKpForTime()'s
    "take the max within a tolerance window" approach, since a single
    3-hour Kp bucket should apply to every 30-minute window inside it.
    """
    def parse_kp_time(entry: dict) -> datetime:
        # NOAA's time_tag looks like "2026-09-11T07:00:00".
        return datetime.strptime(entry["time_tag"], "%Y-%m-%dT%H:%M:%S")

    window = timedelta(hours=KP_MATCH_WINDOW_HOURS)
    nearby = [entry for entry in kp_forecast if abs(parse_kp_time(entry) - moment) < window]

    if not nearby:
        return 0.0
    return max(entry["kp"] for entry in nearby)


# ============================================================
# BUILDING THE FULL FORECAST
# ============================================================

def build_forecast(
    astro_days: list[dict],
    weather_hourly: list[dict],
    kp_forecast: list[dict],
    start_time: datetime,
    hours: int = 72,
) -> list[ForecastPoint]:
    spans = build_period_spans(astro_days)
    all_windows = generate_30_min_windows(start_time, hours=hours)
    dark_windows = get_dark_windows(all_windows, spans)

    results = []
    for window_time, sky_period in dark_windows:
        weather = find_nearest_weather(weather_hourly, window_time)
        max_kp = find_kp_for_time(kp_forecast, window_time)
        moon_state = get_moon_state_for_time(astro_days, window_time)

        # If weather data doesn't cover this window at all, fall back to
        # "assume the worst" values rather than crashing - a missing
        # weather entry shouldn't produce a falsely high score.
        cloud_cover = weather["cloud_cover"] if weather else 100.0
        visibility = weather["visibility"] if weather else 0.0
        temperature = weather["temperature_2m"] if weather else 0.0
        dew_point = weather["dew_point_2m"] if weather else 0.0

        score = calculate_score(
            max_kp=max_kp,
            cloud_cover_percent=cloud_cover,
            visibility_m=visibility,
            temperature_c=temperature,
            dew_point_c=dew_point,
            sky_period=sky_period,
            practical_moon_illumination_percent=moon_state.practical_moon_illumination,
        )

        results.append(ForecastPoint(time=window_time, sky_period=sky_period, score=score))

    return results


# ============================================================
# QUICK MANUAL TEST
# ============================================================

if __name__ == "__main__":
    sample_astro_days = [
        {
            "date": "2026-09-11", "first_light": "04:14:00", "last_light": "22:10:29",
            "nautical_twilight_begin": "05:09:05", "nautical_twilight_end": "21:16:03",
            "moonrise": "07:02:11", "moonset": "19:31:35", "moon_illumination": 0.15,
        },
        {
            "date": "2026-09-12", "first_light": "04:17:20", "last_light": "22:06:00",
            "nautical_twilight_begin": "05:11:30", "nautical_twilight_end": "21:12:00",
            "moonrise": "08:15:00", "moonset": "20:05:00", "moon_illumination": 1.5,
        },
    ]

    sample_weather = [
        {"time": "2026-09-11T21:00", "cloud_cover": 20, "visibility": 40000, "temperature_2m": 8.0, "dew_point_2m": 2.0},
        {"time": "2026-09-11T22:00", "cloud_cover": 15, "visibility": 42000, "temperature_2m": 7.5, "dew_point_2m": 1.5},
        {"time": "2026-09-11T23:00", "cloud_cover": 90, "visibility": 8000, "temperature_2m": 7.0, "dew_point_2m": 6.5},
    ]

    sample_kp = [
        {"time_tag": "2026-09-11T21:00:00", "kp": 5.33, "observed": "predicted"},
        {"time_tag": "2026-09-12T00:00:00", "kp": 6.0, "observed": "predicted"},
    ]

    forecast = build_forecast(
        sample_astro_days, sample_weather, sample_kp,
        start_time=datetime(2026, 9, 11, 20, 30),
        hours=4,
    )

    for point in forecast:
        print(f"{point.time} [{point.sky_period}] -> score={point.score.final_score}%")