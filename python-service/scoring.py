"""
scoring.py

Pure scoring logic for AuroraBeacon.

IMPORTANT DESIGN RULE: nothing in this file touches the network, the filesystem,
or a clock. Every function takes plain values in and returns a plain value out.
This is deliberate - it means these functions can be tested by just calling them
with made-up numbers, and can be reused unchanged no matter what infrastructure
(FastAPI, a cron script, anything else) ends up calling them.
"""

from dataclasses import dataclass


# ============================================================
# CONSTANTS - the "tuning knobs" for the formula.
# These are the numbers we reasoned through earlier in the project.
# ============================================================

# --- Kp gate ---
# Below KP_MIN, the score is crushed toward 0 - not worth going outside.
# At/above KP_FULL, the Kp gate no longer reduces the score at all.
# 3 and 6 were chosen based on Inverness's specific geomagnetic latitude.
KP_MIN = 3.0
KP_FULL = 6.0

# --- Cloud gate ---
# Below CLOUD_OK, cloud cover doesn't penalise the score at all (50-60% is "fine").
# At/above CLOUD_MAX, cloud cover crushes the score to 0 regardless of anything else.
CLOUD_OK = 65.0
CLOUD_MAX = 95.0

# --- Darkness base scores, by sky period ---
# "Astronomical Twilight" is treated as acceptable-but-not-best, per our earlier decision.
BASE_DARK_BRIGHT_SKY = 0.0
BASE_DARK_TWILIGHT = 60.0
BASE_DARK_NIGHT = 100.0

# How much a fully-illuminated moon can reduce the darkness score (30% max reduction).
MOON_PENALTY_WEIGHT = 0.3

# --- Sky clarity sub-weights (cloud / visibility / fog-proxy) ---
CLOUD_WEIGHT = 0.7
VISIBILITY_WEIGHT = 0.15
FOG_WEIGHT = 0.15

# Visibility distance (metres) that counts as "perfectly clear" for scoring purposes.
VISIBILITY_FULL_MARKS_M = 10_000.0

# Dew-point spread (°C) that counts as "no fog risk" for scoring purposes.
FOG_SAFE_SPREAD_C = 5.0

# --- Top-level formula weights ---
AURORA_WEIGHT = 0.5
SKY_CLARITY_WEIGHT = 0.35
DARKNESS_WEIGHT = 0.15

# Kp value that represents "maximum realistic aurora activity" for scaling to 0-100.
KP_SCALE_MAX = 9.0


# ============================================================
# SMALL HELPERS
# ============================================================

def clamp(value: float, low: float, high: float) -> float:
    """Restrict value to the [low, high] range."""
    return max(low, min(high, value))


# ============================================================
# GATE FUNCTIONS
# A "gate" is a 0.0-1.0 multiplier that can crush the final score toward zero
# when a hard condition isn't met - as opposed to a normal weighted factor,
# which only ever partially influences the result.
# ============================================================

def kp_gate(max_kp: float) -> float:
    """
    Returns 0.0 if max_kp is at/below KP_MIN (too weak to matter),
    1.0 if at/above KP_FULL (strong enough to not hold the score back),
    and a linear ramp in between.
    """
    return clamp((max_kp - KP_MIN) / (KP_FULL - KP_MIN), 0.0, 1.0)


def cloud_gate(cloud_cover_percent: float) -> float:
    """
    Returns 1.0 (no penalty) at/below CLOUD_OK,
    0.0 (fully crushed) at/above CLOUD_MAX,
    and a linear ramp in between.
    """
    if cloud_cover_percent <= CLOUD_OK:
        return 1.0
    return clamp(
        (CLOUD_MAX - cloud_cover_percent) / (CLOUD_MAX - CLOUD_OK),
        0.0,
        1.0,
    )


# ============================================================
# SUB-SCORES
# Each of these returns a plain 0-100 number for one aspect of viewing conditions.
# ============================================================

def aurora_activity_score(max_kp: float) -> float:
    """Space-weather activity, scaled 0-100 against KP_SCALE_MAX."""
    return min(100.0, (max_kp / KP_SCALE_MAX) * 100.0)


def sky_clarity_score(cloud_cover_percent: float, visibility_m: float,
                       temperature_c: float, dew_point_c: float) -> float:
    """
    Combines cloud cover, visibility, and a dew-point-spread fog proxy
    into one 0-100 "how clear is the sky" number.
    """
    cloud_component = 100.0 - cloud_cover_percent
    visibility_component = min(100.0, (visibility_m / VISIBILITY_FULL_MARKS_M) * 100.0)

    dew_point_spread = temperature_c - dew_point_c
    fog_component = clamp((dew_point_spread / FOG_SAFE_SPREAD_C) * 100.0, 0.0, 100.0)

    return (
        cloud_component * CLOUD_WEIGHT
        + visibility_component * VISIBILITY_WEIGHT
        + fog_component * FOG_WEIGHT
    )


def darkness_score(sky_period: str, practical_moon_illumination_percent: float) -> float:
    """
    Base darkness depends on sky_period ("Bright Sky" / "Astronomical Twilight" /
    "Astronomical Night"), then gets reduced by how much the moon is washing out
    the sky right now (already adjusted for horizon-ramp elsewhere - this function
    just applies the illumination number it's given).
    """
    if sky_period == "Astronomical Night":
        base = BASE_DARK_NIGHT
    elif sky_period == "Astronomical Twilight":
        base = BASE_DARK_TWILIGHT
    else:
        base = BASE_DARK_BRIGHT_SKY

    moon_reduction = 1.0 - (practical_moon_illumination_percent / 100.0) * MOON_PENALTY_WEIGHT
    return base * moon_reduction


# ============================================================
# FINAL SCORE
# ============================================================

@dataclass
class ScoreBreakdown:
    """Everything needed to both show the final score AND explain how it was reached."""
    final_score: int
    aurora_score: float
    sky_clarity_score: float
    darkness_score: float
    kp_gate_value: float
    cloud_gate_value: float


def calculate_score(
    max_kp: float,
    cloud_cover_percent: float,
    visibility_m: float,
    temperature_c: float,
    dew_point_c: float,
    sky_period: str,
    practical_moon_illumination_percent: float,
) -> ScoreBreakdown:
    """
    The single entry point other code should call. Takes one moment's worth of
    already-gathered data, returns a full breakdown of the 0-100 final score.
    """
    aurora = aurora_activity_score(max_kp)
    clarity = sky_clarity_score(cloud_cover_percent, visibility_m, temperature_c, dew_point_c)
    darkness = darkness_score(sky_period, practical_moon_illumination_percent)

    weighted = (
        aurora * AURORA_WEIGHT
        + clarity * SKY_CLARITY_WEIGHT
        + darkness * DARKNESS_WEIGHT
    )

    kp_g = kp_gate(max_kp)
    cloud_g = cloud_gate(cloud_cover_percent)

    final = round(weighted * kp_g * cloud_g)

    return ScoreBreakdown(
        final_score=final,
        aurora_score=aurora,
        sky_clarity_score=clarity,
        darkness_score=darkness,
        kp_gate_value=kp_g,
        cloud_gate_value=cloud_g,
    )


# ============================================================
# QUICK MANUAL TEST
# Run this file directly (`python scoring.py` or `uv run scoring.py`) to sanity-check
# the formula against a couple of known scenarios, without needing FastAPI or any
# other infrastructure at all.
# ============================================================

if __name__ == "__main__":
    # Scenario from earlier in the project: low Kp, clear-ish sky, night - should score LOW.
    weak_kp_clear_night = calculate_score(
        max_kp=2.0,
        cloud_cover_percent=0,
        visibility_m=45000,
        temperature_c=4.9,
        dew_point_c=-2,
        sky_period="Astronomical Night",
        practical_moon_illumination_percent=80,
    )
    print("Weak Kp, clear night:", weak_kp_clear_night)

    # Strong Kp, fully clouded - should be crushed toward 0 by the cloud gate.
    strong_kp_full_cloud = calculate_score(
        max_kp=7.0,
        cloud_cover_percent=100,
        visibility_m=2000,
        temperature_c=8.0,
        dew_point_c=7.5,
        sky_period="Astronomical Night",
        practical_moon_illumination_percent=10,
    )
    print("Strong Kp, 100% cloud:", strong_kp_full_cloud)

    # Strong Kp, clear night - should score HIGH.
    strong_kp_clear_night = calculate_score(
        max_kp=7.0,
        cloud_cover_percent=10,
        visibility_m=40000,
        temperature_c=5.0,
        dew_point_c=-1.0,
        sky_period="Astronomical Night",
        practical_moon_illumination_percent=5,
    )
    print("Strong Kp, clear night:", strong_kp_clear_night)