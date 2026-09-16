"""
window_generator.py

Pure functions for turning the astro data (sunrise/sunset-style day objects)
into: (1) a list of 30-minute timestamps to score, and (2) a way to look up
what "sky period" (Bright Sky / Astronomical Twilight / Astronomical Night)
any given moment falls into.

Same rule as scoring.py: no network, no filesystem, no dependency on "real now"
except where explicitly passed in as a parameter. Everything here is testable
with made-up data.

NOTE ON TIMEZONES: this project deals with one fixed UK location, and the
sunrisesunset.io API already returns times local to that location (its
"tzid" field confirmed this - see ARCHITECTURE_DECISIONS.md). To keep things
simple, every datetime in this module is "naive" (no attached timezone info)
and is implicitly assumed to already be in that local time. This only works
because the whole project - the API responses, this code, and eventually the
server it runs on - agrees to treat every timestamp as the same local time.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta


# ============================================================
# CONSTANTS
# ============================================================

WINDOW_STEP_MINUTES = 30
DEFAULT_FORECAST_HOURS = 72  # matches the "3 nights ahead" goal


# ============================================================
# DATA SHAPES
# ============================================================

@dataclass
class Span:
    """A period of time with a start and an end - e.g. one night's dark window."""
    start: datetime
    end: datetime

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end


@dataclass
class PeriodSpans:
    """All the night spans and twilight spans built from several days of astro data."""
    night_spans: list[Span] = field(default_factory=list)
    twilight_spans: list[Span] = field(default_factory=list)


# ============================================================
# PARSING
# ============================================================

def parse_time(date_str: str, time_str: str) -> datetime:
    """
    Combines a date string ("2026-09-11") and a time string ("22:26:04")
    into one naive datetime. Mirrors the JS parseTime() helper exactly.
    """
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")


# ============================================================
# BUILDING NIGHT / TWILIGHT SPANS
# ============================================================

def build_period_spans(days: list[dict]) -> PeriodSpans:
    """
    Takes the astro_json list (one dict per day, each with first_light,
    last_light, nautical_twilight_begin, nautical_twilight_end) and builds
    the actual overnight spans.

    IMPORTANT: a single day's "last_light" and next day's "first_light"
    together define ONE continuous night span, since darkness crosses
    midnight. This is why the loop looks at days[i] and days[i + 1] together,
    and why the LAST day in the list can't produce a complete span of its own
    (there's no days[i + 1] to close it out) - this mirrors the JS version's
    same limitation, which is why the astro cron fetches extra buffer days.
    """
    spans = PeriodSpans()

    for i in range(len(days) - 1):
        today = days[i]
        tomorrow = days[i + 1]

        dusk = parse_time(today["date"], today["last_light"])
        nautical_end = parse_time(today["date"], today["nautical_twilight_end"])
        nautical_begin = parse_time(tomorrow["date"], tomorrow["nautical_twilight_begin"])
        dawn = parse_time(tomorrow["date"], tomorrow["first_light"])

        spans.night_spans.append(Span(start=dusk, end=dawn))
        spans.twilight_spans.append(Span(start=nautical_end, end=dusk))
        spans.twilight_spans.append(Span(start=dawn, end=nautical_begin))

    return spans


# ============================================================
# SKY PERIOD LOOKUP
# ============================================================

def get_sky_period(spans: PeriodSpans, moment: datetime) -> str:
    """
    Returns "Astronomical Night", "Astronomical Twilight", or "Bright Sky"
    for the given moment, checking the night spans first since night takes
    priority over twilight if they ever overlapped (they shouldn't, but
    checking night first is the safe order).
    """
    if any(span.contains(moment) for span in spans.night_spans):
        return "Astronomical Night"
    if any(span.contains(moment) for span in spans.twilight_spans):
        return "Astronomical Twilight"
    return "Bright Sky"


# ============================================================
# WINDOW GENERATION
# ============================================================

def generate_30_min_windows(
    start_time: datetime,
    hours: int = DEFAULT_FORECAST_HOURS,
) -> list[datetime]:
    """
    Builds a list of datetimes, one every 30 minutes, starting from the
    30-minute mark at or before start_time, up to `hours` hours later.
    """
    # Round down to the nearest 30-minute mark, matching the JS version's
    # setMinutes(floor(minutes / 30) * 30) behaviour.
    rounded_minute = (start_time.minute // WINDOW_STEP_MINUTES) * WINDOW_STEP_MINUTES
    current = start_time.replace(minute=rounded_minute, second=0, microsecond=0)

    end_time = start_time + timedelta(hours=hours)
    step = timedelta(minutes=WINDOW_STEP_MINUTES)

    windows = []
    while current < end_time:
        windows.append(current)
        current += step

    return windows


def get_dark_windows(
    windows: list[datetime],
    spans: PeriodSpans,
) -> list[tuple[datetime, str]]:
    """
    Filters a list of windows down to only the ones that aren't "Bright Sky",
    pairing each surviving window with its sky period so callers don't have
    to look it up twice.
    """
    result = []
    for window in windows:
        period = get_sky_period(spans, window)
        if period != "Bright Sky":
            result.append((window, period))
    return result


# ============================================================
# QUICK MANUAL TEST
# ============================================================

if __name__ == "__main__":
    sample_days = [
        {
            "date": "2026-09-11",
            "first_light": "04:14:00",
            "last_light": "22:10:29",
            "nautical_twilight_begin": "05:09:05",
            "nautical_twilight_end": "21:16:03",
        },
        {
            "date": "2026-09-12",
            "first_light": "04:17:20",
            "last_light": "22:06:00",
            "nautical_twilight_begin": "05:11:30",
            "nautical_twilight_end": "21:12:00",
        },
    ]

    spans = build_period_spans(sample_days)
    print(f"Night spans: {spans.night_spans}")
    print(f"Twilight spans: {spans.twilight_spans}")

    # A few sample moments to check sky period lookup
    test_moments = [
        datetime(2026, 9, 11, 12, 0),   # noon - should be Bright Sky
        datetime(2026, 9, 11, 21, 30),  # early evening twilight
        datetime(2026, 9, 11, 23, 0),   # should be Astronomical Night
        datetime(2026, 9, 12, 3, 0),    # still night, past midnight
        datetime(2026, 9, 12, 4, 30),   # morning twilight
    ]
    for moment in test_moments:
        print(f"{moment} -> {get_sky_period(spans, moment)}")

    # Generate windows and show only the dark ones
    windows = generate_30_min_windows(datetime(2026, 9, 11, 18, 0), hours=24)
    dark_windows = get_dark_windows(windows, spans)
    print(f"\n{len(windows)} total windows generated, {len(dark_windows)} are dark:")
    for window, period in dark_windows[:5]:
        print(f"  {window} -> {period}")