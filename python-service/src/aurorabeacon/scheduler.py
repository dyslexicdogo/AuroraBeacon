"""
scheduler.py

Schedules the four fetchers on their own cadences, all restricted to the
6pm-6am window - the direct Python replacement for the four n8n Schedule
Trigger nodes. Uses APScheduler's CronTrigger, which supports the same
hour-range syntax you used directly in n8n's cron expressions.

Cadence choices:
  - weather:  every 30 min - matches how fast cloud cover genuinely changes
  - ovation:  every 30 min - matches its own ~30-90 min real-world lead time
  - kp:       every 3 hours - NOAA only updates this forecast twice a day
              anyway, and Kp's own buckets are 3 hours wide, so checking
              more often than that buys nothing
  - astro:    once a day, at 17:00 - just before the 6pm window opens, so
              the night's boundary/moon data is as fresh as possible before
              anything actually gets scored tonight
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .fetchers import fetch_kp, fetch_weather, fetch_astro, fetch_ovation
from .notification_job import run_evening_check



def _safe(fn):
    """
    Wraps a fetcher so one failed run (network hiccup, API down) logs and
    moves on, rather than silently killing the entire scheduler thread.
    APScheduler does log exceptions on its own, but printing here makes
    failures obvious immediately during development.
    """
    def wrapped():
        try:
            fn()
        except Exception as e:
            print(f"[scheduler] {fn.__name__} failed: {e}")
    wrapped.__name__ = fn.__name__
    return wrapped


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/London")

    # 6pm-6am, every 30 minutes
    scheduler.add_job(
        _safe(fetch_weather),
        CronTrigger(hour="18-23,0-6", minute="0,30"),
        id="fetch_weather",
    )
    scheduler.add_job(
        _safe(fetch_ovation),
        CronTrigger(hour="18-23,0-6", minute="0,30"),
        id="fetch_ovation",
    )

    # 6pm-6am, every 3 hours (on the hour, within the window)
    scheduler.add_job(
        _safe(fetch_kp),
        CronTrigger(hour="18,21,0,3,6", minute="0"),
        id="fetch_kp",
    )

    # once daily, just before the window opens
    scheduler.add_job(
        _safe(fetch_astro),
        CronTrigger(hour="17", minute="0"),
        id="fetch_astro",
    )

    # once daily, at 7pm, to send notifications for the evening
    scheduler.add_job(_safe(run_evening_check),
                      CronTrigger(hour="19", minute="0"),
                      id="notification_job")

    return scheduler

