import pytest

from datetime import datetime

from aurorabeacon.moon import get_moon_state, get_moon_state_for_time

# Normal day: moonrise earlier in the clock than moonset.
NORMAL = {"date": "2026-09-08", "moonrise": "02:11:55", "moonset": "19:15:27", "moon_illumination": 9.11}

# Flipped day: the moon rises in the evening and sets the next morning,
# so moonset is EARLIER in the clock than moonrise.
FLIPPED = {"date": "2026-09-08", "moonrise": "22:00:00", "moonset": "05:00:00", "moon_illumination": 50.0}

ONLY_MOONSET = {"date": "2026-09-06", "moonrise": None, "moonset": "18:44:23", "moon_illumination": 26.42}
ONLY_MOONRISE = {"date": "2026-09-11", "moonrise": "07:02:11", "moonset": None, "moon_illumination": 0.15}
NEITHER = {"date": "2026-09-12", "moonrise": None, "moonset": None, "moon_illumination": 80.0}


def at(day, hour, minute=0):
    y, m, d = map(int, day["date"].split("-"))
    return datetime(y, m, d, hour, minute)


# ---------- Normal day ----------

def test_moon_is_down_before_moonrise():
    state = get_moon_state(NORMAL, at(NORMAL, 2, 0))
    assert state.is_moon_up is False
    assert state.practical_moon_illumination == 0.0


def test_moon_is_up_at_full_strength_mid_day():
    state = get_moon_state(NORMAL, at(NORMAL, 10, 0))
    assert state.is_moon_up is True
    assert state.practical_moon_illumination == pytest.approx(9.1, abs=0.05)


def test_ramp_is_half_strength_15_minutes_after_moonrise():
    state = get_moon_state(NORMAL, at(NORMAL, 2, 26))  # moonrise 02:11:55 + about 14 min
    assert state.is_moon_up is True
    assert 3.5 < state.practical_moon_illumination < 5.0


def test_ramp_tapers_down_before_moonset():
    state = get_moon_state(NORMAL, at(NORMAL, 19, 5))  # about 10 min before moonset
    assert 0 < state.practical_moon_illumination < 9.11 / 2


def test_moon_is_down_after_moonset():
    assert get_moon_state(NORMAL, at(NORMAL, 20, 0)).is_moon_up is False


# ---------- Flipped order (moonset earlier in the clock than moonrise) ----------

def test_flipped_day_moon_up_late_evening_and_after_midnight():
    assert get_moon_state(FLIPPED, at(FLIPPED, 23, 30)).practical_moon_illumination == pytest.approx(50.0)
    assert get_moon_state(FLIPPED, at(FLIPPED, 3, 0)).practical_moon_illumination == pytest.approx(50.0)


def test_flipped_day_moon_down_in_between():
    assert get_moon_state(FLIPPED, at(FLIPPED, 12, 0)).is_moon_up is False


# ---------- Missing moonrise or moonset ----------

def test_only_moonset_known_means_up_until_it_sets():
    assert get_moon_state(ONLY_MOONSET, at(ONLY_MOONSET, 10, 0)).is_moon_up is True
    assert get_moon_state(ONLY_MOONSET, at(ONLY_MOONSET, 20, 0)).is_moon_up is False


def test_only_moonrise_known_means_up_from_it_onward():
    assert get_moon_state(ONLY_MOONRISE, at(ONLY_MOONRISE, 5, 0)).is_moon_up is False
    assert get_moon_state(ONLY_MOONRISE, at(ONLY_MOONRISE, 12, 0)).is_moon_up is True


def test_neither_known_is_treated_as_down():
    assert get_moon_state(NEITHER, at(NEITHER, 12, 0)).is_moon_up is False


# ---------- Picking the right day ----------

def test_state_for_time_uses_the_day_matching_the_date():
    days = [NORMAL, {**NORMAL, "date": "2026-09-09", "moon_illumination": 40.0}]
    state = get_moon_state_for_time(days, datetime(2026, 9, 9, 10, 0))
    assert state.practical_moon_illumination == pytest.approx(40.0)