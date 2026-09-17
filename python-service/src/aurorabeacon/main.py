"""
main.py

The FastAPI app itself. Deliberately thin - this file's only job is to sit
between HTTP and the real logic (cache.py, forecast.py), which were already
built and tested independently of any web framework at all.
"""

from datetime import datetime

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from .scheduler import create_scheduler

from .cache import load_cache
from .forecast import build_forecast

# ============================================================
# lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown()

app = FastAPI(title="AuroraBeacon", lifespan=lifespan)

# ============================================================
# debug
# ============================================================

@app.get("/debug/jobs")
def debug_jobs():
    scheduler = app.state.scheduler
    return [
        {"id": job.id, "next_run": str(job.next_run_time)}
        for job in scheduler.get_jobs()
    ]

# ============================================================
# HEALTH CHECK
# A trivial endpoint to confirm the server itself is up, separate from
# whether the cache/data behind it is working.
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# FORECAST
# ============================================================

@app.get("/forecast")
def forecast(hours: int = 72):
    """
    Returns the scored dark-window forecast, starting from right now.
    `hours` is optional (default 72, matching the 3-night goal) - lets the
    webpage ask for a shorter window later if it ever wants to.
    """
    try:
        cache = load_cache()
    except FileNotFoundError:
        # 503 = "server's fine, but the thing it depends on isn't ready yet" -
        # more accurate than a generic 500, and tells the webpage this is a
        # temporary/expected state (cache not fetched yet), not a real bug.
        raise HTTPException(status_code=503, detail="Cache not available yet")

    points = build_forecast(
        astro_days=cache.astro_days,
        weather_hourly=cache.weather_hourly,
        kp_forecast=cache.kp_forecast,
        start_time=datetime.now(),
        hours=hours,
    )

    return {
        "ovation_probability": cache.ovation_probability,
        "ovation_observation_time": cache.ovation_observation_time,
        "forecast": points,
    }

