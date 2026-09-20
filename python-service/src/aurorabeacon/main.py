"""
main.py

The FastAPI app itself. Deliberately thin - this file's only job is to sit
between HTTP and the real logic (cache.py, forecast.py), which were already
built and tested independently of any web framework at all.
"""

from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .scheduler import create_scheduler
from .cache import load_cache
from .forecast import build_forecast
from .fetchers import fetch_kp, fetch_weather, fetch_astro, fetch_ovation


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    try:
        load_cache()
    except FileNotFoundError:
        print("[startup] No cache found - fetching all sources once now")
        fetch_kp()
        fetch_weather()
        fetch_astro()
        fetch_ovation()

    yield
    scheduler.shutdown()


app = FastAPI(title="AuroraBeacon", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

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


# ============================================================
# scheduler lifespan
# ============================================================

def refresh_missing_sources() -> None:
    try:
        cache = load_cache()
    except FileNotFoundError:
        cache = None

    if cache is None or not cache.astro_days:
        print("[startup] astro_json missing - fetching")
        fetch_astro()
    if cache is None or not cache.kp_forecast:
        print("[startup] kpforecast_json missing - fetching")
        fetch_kp()
    if cache is None or not cache.weather_hourly:
        print("[startup] weather_json missing - fetching")
        fetch_weather()
    if cache is None or cache.ovation_updated_at is None:
        print("[startup] ovation data missing - fetching")
        fetch_ovation()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    refresh_missing_sources()

    yield
    scheduler.shutdown()


# ============================================================
# Remove this later
# ============================================================
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)