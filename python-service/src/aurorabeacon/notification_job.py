"""
notification_job.py

Runs once daily at 7pm: builds tonight's forecast, checks whether anything
crosses the alert threshold, and sends one notification if so. Deliberately
separate from notifier.py (which just sends) and forecast.py (which just
scores) - this file's only job is the threshold decision itself.
"""

from datetime import datetime

from .cache import load_cache
from .forecast import build_forecast
from .notifier import send_notification


ALERT_THRESHOLD = 50  # tune this once you've seen real scores over a few nights


def run_evening_check() -> None:
    try:
        cache = load_cache()
    except FileNotFoundError:
        print("[notification_job] No cache file yet - skipping tonight's check")
        return

    points = build_forecast(
        astro_days=cache.astro_days,
        weather_hourly=cache.weather_hourly,
        kp_forecast=cache.kp_forecast,
        start_time=datetime.now(),
        hours=12,  # just tonight, not the full 3-day window
    )

    best = max(points, key=lambda p: p.score.final_score, default=None)

    if best and best.score.final_score >= ALERT_THRESHOLD:
        send_notification(
            title="Aurora Alert 🌌",
            message=f"Best chance tonight: {best.score.final_score}% around "
                    f"{best.time.strftime('%H:%M')} ({best.sky_period})",
            priority="high",
        )
    else:
        print(f"[notification_job] Best score tonight: "
              f"{best.score.final_score if best else 'n/a'}% - below threshold, no alert sent")


if __name__ == "__main__":
    run_evening_check()