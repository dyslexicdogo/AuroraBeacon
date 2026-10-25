# 🌌 AuroraBeacon

*Know when the lights are coming.*

AuroraBeacon is a small self-hosted service that tells me when northern lights are worth looking
for from Inverness, Scotland. It combines space weather, cloud cover, darkness and the moon into a
single score, shows it on a website, and sends a push alert to my phone when it matters.

**Live:** [forecast site](https://dyslexicdogo.github.io/AuroraBeacon/) ·
[forecast API](https://ab.145252.xyz/forecast)

> Scores are a model estimate, not a calibrated probability. The thresholds are still being tuned
> against real aurora nights.

## What it does

- **Forecast site:** the best window in the next three nights, a bar chart of every dark-sky
  half-hour, and the conditions behind each score (Kp, cloud, visibility, moon).
- **7pm planning alert:** one push each evening if tonight's best window scores well.
- **"Go now" alert:** a push when it is dark, the sky is workable and NOAA's live OVATION value
  for the location is up. It stays quiet for 3 hours after an alert unless things get clearly
  better, and sends silently between midnight and 6am unless the level is strong.

## How it works

```
NOAA Kp forecast ─┐
NOAA OVATION ─────┤                          ┌─> GET /forecast ──> static site (docs/)
Open-Meteo ───────┼─> fetchers ─> JSON cache ┤
sunrisesunset.io ─┘   (scheduled)            └─> alert jobs ──> ntfy ──> phone
```

Everything runs in one container: a FastAPI app with an APScheduler job table inside the same
process.

**The score** is a weighted blend of space weather (50%), sky clarity (35%) and darkness (15%),
multiplied by two gates that can crush it to zero:

- **Kp gate:** no chance below Kp 3, full strength from Kp 6 (tuned for Inverness's latitude).
- **Cloud gate:** no penalty up to 65% cloud, zero at 95%.

Darkness uses three sky periods (bright, astronomical twilight, astronomical night) and is reduced
by the moon when it is up. The reasoning behind every choice is in
[`python-service/ARCHITECTURE_DECISIONS.md`](python-service/ARCHITECTURE_DECISIONS.md).

## Repository layout

```
docs/                       Static website (served by GitHub Pages)
python-service/
  src/aurorabeacon/         The service
    scoring.py                Gates, sub-scores, final score (pure)
    window_generator.py       30-minute windows, night/twilight spans (pure)
    moon.py                   Moon up/down and horizon ramp (pure)
    forecast.py               Matches weather, Kp and moon to each window
    cache.py                  The only module that touches the cache file
    fetchers.py               One fetcher per data source
    scheduler.py              APScheduler job table
    notifier.py               Sends a push through ntfy
    notification_job.py       7pm planning alert
    go_now.py                 Live "go now" alert
    main.py                   FastAPI app
  tests/                    pytest tests
  Dockerfile
  docker-compose.yml
```

An earlier native Android attempt exists in the git history, before the "starting fresh with
FastAPI" commit.

## Run it locally

You need [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
cd python-service
uv sync
uv run uvicorn aurorabeacon.main:app --reload
```

On first start the cache is empty, so the service fetches all four data sources straight away
(this takes a few seconds). Then try:

```bash
curl localhost:8000/health
curl localhost:8000/forecast
```

To use the website against a local API, set `ALLOWED_ORIGINS` to the origin the page is served
from, for example `ALLOWED_ORIGINS=http://localhost:8080`.

## Tests

```bash
cd python-service
uv run pytest
```

The scoring, window, moon and timezone-lookup logic are pure functions, so the tests need no
network and no setup.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `NTFY_TOPIC` | ntfy topic for alerts. Treat it as a secret. Without it, alerts are skipped. | unset |
| `ALLOWED_ORIGINS` | Comma-separated origins allowed by CORS | the GitHub Pages site |
| `AURORA_CACHE_PATH` | Where the JSON cache lives | `aurora_cache.json` in the project root (`/app/data/` in Docker) |
| `TZ` | Container timezone. Astro times and windows use UK local time. | `Europe/London` in Docker |

The location is set by `LATITUDE` and `LONGITUDE` at the top of `fetchers.py`.

## Deploy with Docker

```bash
cd python-service
echo 'NTFY_TOPIC=your-private-topic-name' > .env     # .env is gitignored
docker compose up -d --build
```

- The cache and its data live on a named volume (`aurorabeacon_data`), so they survive rebuilds.
  Avoid `docker compose down -v`, which deletes it.
- The container is published on `127.0.0.1:47291` only. In my setup a Cloudflare Tunnel on the
  same host exposes it, and a Cloudflare rate-limit rule protects it.
- A missing or partial cache refills itself on startup.

### Schedule

| Job | When |
|---|---|
| Weather, OVATION | every 30 min, 18:00–06:00 |
| Kp forecast | every 3 hours, 18:00–06:00 |
| Sun and moon times | daily at 17:00 |
| Planning alert | daily at 19:00 |
| "Go now" check | every 30 min at :05 and :35, 18:00–06:00 |

Outside those hours nothing is refreshed, so by day the site shows the last overnight data.

## API

| Endpoint | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /forecast?hours=72` | Current OVATION value and a scored list of dark-sky windows. `hours` accepts 1–96. |

## Data sources

- [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov/): Kp forecast and the OVATION aurora model
- [Open-Meteo](https://open-meteo.com/): cloud cover, visibility, temperature and dew point
- [sunrisesunset.io](https://sunrisesunset.io/): twilight boundaries, moonrise/moonset and moon illumination
- [ntfy](https://ntfy.sh/): push notifications
