import pytest

from aurorabeacon.scoring import calculate_score, cloud_gate, darkness_score, kp_gate


# ---------- Kp gate: 0 at Kp <= 3, ramps to 1 at Kp >= 6 ----------

@pytest.mark.parametrize("kp, expected", [
    (0.0, 0.0),
    (2.0, 0.0),
    (3.0, 0.0),
    (4.5, 0.5),
    (6.0, 1.0),
    (9.0, 1.0),
])
def test_kp_gate(kp, expected):
    assert kp_gate(kp) == pytest.approx(expected)


# ---------- Cloud gate: 1 up to 65% cover, ramps to 0 at 95% ----------

@pytest.mark.parametrize("cloud, expected", [
    (0, 1.0),
    (50, 1.0),
    (65, 1.0),
    (80, 0.5),
    (95, 0.0),
    (100, 0.0),
])
def test_cloud_gate(cloud, expected):
    assert cloud_gate(cloud) == pytest.approx(expected)


# ---------- Darkness: base by sky period, reduced by moon up to 30% ----------

def test_darkness_bases_with_no_moon():
    assert darkness_score("Astronomical Night", 0) == pytest.approx(100)
    assert darkness_score("Astronomical Twilight", 0) == pytest.approx(60)
    assert darkness_score("Bright Sky", 0) == pytest.approx(0)


def test_full_moon_cuts_night_darkness_by_30_percent():
    assert darkness_score("Astronomical Night", 100) == pytest.approx(70)


def test_bright_sky_stays_zero_whatever_the_moon():
    assert darkness_score("Bright Sky", 100) == pytest.approx(0)


# ---------- Whole score: the three cases the gates exist for ----------

def _score(**overrides):
    inputs = dict(
        max_kp=7.0,
        cloud_cover_percent=10,
        visibility_m=40000,
        temperature_c=5.0,
        dew_point_c=-1.0,
        sky_period="Astronomical Night",
        practical_moon_illumination_percent=5,
    )
    inputs.update(overrides)
    return calculate_score(**inputs)


def test_good_night_scores_high():
    assert _score().final_score == 86


def test_low_kp_crushes_score_even_under_a_clear_dark_sky():
    assert _score(max_kp=2.0).final_score == 0


def test_total_cloud_crushes_score_even_with_strong_kp():
    assert _score(cloud_cover_percent=100).final_score == 0


def test_daylight_scores_lower_than_night_all_else_equal():
    assert _score(sky_period="Bright Sky").final_score < _score().final_score   