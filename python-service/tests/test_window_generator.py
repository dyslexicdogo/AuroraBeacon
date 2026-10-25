from datetime import datetime

from aurorabeacon.window_generator import (
    build_period_spans,
    generate_30_min_windows,
    get_dark_windows,
    get_sky_period,
)

DAYS = [
    {
        "date": "2026-09-11", "first_light": "04:14:00", "last_light": "22:10:29",
        "nautical_twilight_begin": "05:09:05", "nautical_twilight_end": "21:16:03",
    },
    {
        "date": "2026-09-12", "first_light": "04:17:20", "last_light": "22:06:00",
        "nautical_twilight_begin": "05:11:30", "nautical_twilight_end": "21:12:00",
    },
]


def test_two_days_make_one_night_span_that_crosses_midnight():
    spans = build_period_spans(DAYS)
    assert len(spans.night_spans) == 1
    night = spans.night_spans[0]
    assert night.start == datetime(2026, 9, 11, 22, 10, 29)
    assert night.end == datetime(2026, 9, 12, 4, 17, 20)


def test_one_day_alone_cannot_close_a_night():
    spans = build_period_spans(DAYS[:1])
    assert spans.night_spans == []


def test_sky_period_through_the_evening_and_night():
    spans = build_period_spans(DAYS)
    expectations = [
        (datetime(2026, 9, 11, 12, 0), "Bright Sky"),
        (datetime(2026, 9, 11, 21, 30), "Astronomical Twilight"),
        (datetime(2026, 9, 11, 23, 0), "Astronomical Night"),
        (datetime(2026, 9, 12, 3, 0), "Astronomical Night"),   # after midnight
        (datetime(2026, 9, 12, 4, 30), "Astronomical Twilight"),
    ]
    for moment, expected in expectations:
        assert get_sky_period(spans, moment) == expected, moment


def test_span_boundaries_start_inclusive_end_exclusive():
    spans = build_period_spans(DAYS)
    assert get_sky_period(spans, datetime(2026, 9, 11, 22, 10, 29)) == "Astronomical Night"
    assert get_sky_period(spans, datetime(2026, 9, 12, 4, 17, 20)) == "Astronomical Twilight"


def test_windows_round_down_to_the_half_hour_and_step_by_30_minutes():
    windows = generate_30_min_windows(datetime(2026, 9, 11, 18, 10), hours=2)
    assert windows[0] == datetime(2026, 9, 11, 18, 0)
    assert windows[1] == datetime(2026, 9, 11, 18, 30)
    assert windows[-1] == datetime(2026, 9, 11, 20, 0)
    assert len(windows) == 5


def test_dark_windows_drop_bright_sky_and_carry_the_period():
    spans = build_period_spans(DAYS)
    windows = generate_30_min_windows(datetime(2026, 9, 11, 20, 0), hours=3)
    dark = get_dark_windows(windows, spans)
    assert all(period != "Bright Sky" for _, period in dark)
    assert dark[0] == (datetime(2026, 9, 11, 21, 30), "Astronomical Twilight")
    assert len(dark) < len(windows)