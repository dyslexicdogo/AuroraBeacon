from datetime import datetime

from aurorabeacon.forecast import find_nearest_weather, find_kp_for_time

# Weather and Kp timestamps are UTC. Windows are naive Europe/London local time.
# In summer (BST) local = UTC + 1h; in winter (GMT) they're identical.

WEATHER_SUMMER = [
    {"time": "2026-07-15T20:00", "cloud_cover": 10},
    {"time": "2026-07-15T21:00", "cloud_cover": 50},
    {"time": "2026-07-15T22:00", "cloud_cover": 90},
]


def test_weather_summer_matches_utc_hour_behind_local():
    # 22:00 BST == 21:00 UTC, so we want the cloud_cover=50 entry
    result = find_nearest_weather(WEATHER_SUMMER, datetime(2026, 7, 15, 22, 0))
    assert result["cloud_cover"] == 50


def test_weather_winter_local_equals_utc():
    weather = [
        {"time": "2026-12-15T21:00", "cloud_cover": 50},
        {"time": "2026-12-15T22:00", "cloud_cover": 90},
    ]
    result = find_nearest_weather(weather, datetime(2026, 12, 15, 22, 0))
    assert result["cloud_cover"] == 90


def test_kp_summer_uses_converted_time():
    kp = [
        {"time_tag": "2026-07-15T18:00:00", "kp": 1.0},
        {"time_tag": "2026-07-15T21:00:00", "kp": 6.0},
    ]
    # 23:30 BST == 22:30 UTC, which is 1.5h from the 21:00 UTC entry
    assert find_kp_for_time(kp, datetime(2026, 7, 15, 23, 30)) == 6.0