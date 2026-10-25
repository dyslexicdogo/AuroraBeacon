# AuroraBeacon: Architecture Decisions

A record of how the Python service is built and why. Add new entries at the bottom of the
relevant section instead of rewriting history. Last updated: 24 Oct 2026.

## 1. What this is

A self-hosted service that tells me when northern lights are worth looking for at Inverness.
It combines space weather, cloud cover, darkness and the moon into a score, publishes it as a
small JSON API and a static website, and pushes alerts to my phone through ntfy.

## 2. Shape of the system

```
NOAA Kp forecast ─┐
NOAA OVATION ─────┤                       ┌─> GET /forecast ──> static site (GitHub Pages, docs/)
Open-Meteo ───────┼─> fetchers.py ─> aurora_cache.json
sunrisesunset.io ─┘   (APScheduler)       └─> notification_job.py / go_now.py ──> ntfy ──> phone
```

Everything runs in one container (FastAPI + uvicorn, with the scheduler inside the same
process) on the Debian mini PC, behind Cloudflare.

### Module map

| Module | Role | Touches I/O? |
|---|---|---|
| `scoring.py` | Gates, sub-scores and the final score | No (pure) |
| `window_generator.py` | 30-minute windows, night/twilight spans, sky period | No (pure) |
| `moon.py` | Moon up/down and the horizon ramp | No (pure) |
| `forecast.py` | Glue: matches weather, Kp and moon to each window, scores it | No (pure) |
| `cache.py` | The only module that reads or writes the cache file | Disk |
| `fetchers.py` | Four fetchers, one per data source | Network, cache |
| `scheduler.py` | APScheduler job table | Calls the above |
| `notifier.py` | Sends one ntfy push | Network |
| `notification_job.py` | 7pm planning alert | Cache, ntfy |
| `go_now.py` | Live "go now" alert with dedupe | Cache, ntfy |
| `main.py` | FastAPI app, startup self-healing, CORS | HTTP |

## 3. Decisions

### 3.1 Pure logic, one I/O boundary
All scoring logic is plain functions: values in, values out, no clock, no network, no files.
Only `cache.py` touches the filesystem. This lets every formula be tested with made-up numbers
and kept unchanged whatever calls it (FastAPI, a script, a test).

### 3.2 Python service instead of Android/Kotlin, and no n8n
The first attempt was a native Android app with Clean Architecture, KMP and DI. The Gradle and
dependency friction outweighed the learning value, so the project moved to a web-first Python
service. n8n then prototyped the four fetch crons, but it was dropped: the same jobs run as
APScheduler jobs inside the service, so there is one thing to deploy and no external workflow
engine. The notification path is ntfy, so no custom Android app is needed.

### 3.3 JSON file cache, per-source keys
Each fetcher writes only its own keys into `aurora_cache.json` on a named Docker volume
(`/app/data`). Writes take a lock and are atomic (write to a temp file, then `os.replace`), so
jobs firing at the same moment can't overwrite each other and a reader never sees half a file.
MySQL was rejected because it needed a server and credentials. SQLite was rejected because n8n
has no built-in node for it. At this scale a single JSON file is enough.

### 3.4 Space-weather inputs
- **OVATION** (NOAA's location-specific aurora probability, 30–90 min lead) is the live signal. It
  already does the geomagnetic-latitude work, so the service doesn't reimplement that physics.
  The grid has no location filter, so the whole grid is fetched and the nearest point to
  Inverness is found locally, with a cos(latitude) correction for longitude.
- **3-day Kp forecast** drives the multi-day look-ahead, because OVATION only covers the next hour
  or so. OVATION is deliberately not folded into the 3-day score.
- Raw Kp/Bz/solar-wind values were rejected as the live input. Flare class and CME data were
  deferred as a possible later feature.

### 3.5 Scoring model
Final score = weighted score × cloud gate × Kp gate.

| Part | Rule |
|---|---|
| Weights | Space weather 50%, sky clarity 35%, darkness 15% |
| Kp gate | 0 at Kp ≤ 3, ramps to 1 at Kp ≥ 6 (tuned to Inverness's geomagnetic latitude) |
| Cloud gate | 1 up to 65% cover, ramps to 0 at 95%. 50–60% cloud is fine; near-total cloud kills the score |
| Sky clarity | 70% cloud, 15% visibility (10 km = full marks), 15% fog proxy (temperature minus dew point, 5 °C = safe) |
| Darkness | Base 0 / 60 / 100 for Bright Sky / Astronomical Twilight / Astronomical Night, reduced up to 30% by moon illumination |

The gates exist because a plain weighted average let a clear dark sky prop up a useless Kp, and
strong Kp prop up a fully clouded sky. Both situations should score close to zero.

### 3.6 Sky periods and the moon
- Three tiers instead of five. Twilight counts as "acceptable", brighter than that does not.
- A night crosses midnight, so one night span needs two consecutive days of astro data (dusk of
  day N to dawn of day N+1). The astro fetch asks for 5 days so the last night can close.
- Moon "up" uses moonrise and moonset times, not altitude. Either time can be missing on a given
  day, and moonrise can fall after moonset, so all combinations are handled.
- A 30-minute ramp after moonrise and before moonset avoids treating a moon on the horizon as
  fully bright.

### 3.7 Time handling
- Astro and moon times and the scoring windows are naive `Europe/London` local time. The container
  runs with `TZ=Europe/London` and the scheduler uses the same zone.
- Open-Meteo and NOAA timestamps are UTC. They are converted to local time at lookup, with
  `zoneinfo`, in `forecast.py`. Without this, lookups were an hour off during BST.
- A pytest file covers the summer (BST) and winter (GMT) cases, because the bug is invisible
  outside BST and can't otherwise be verified.

### 3.8 Scheduling
- Weather and OVATION every 30 min, Kp every 3 hours (NOAA only updates it about twice a day),
  astro daily at 17:00, the planning alert at 19:00, and the go-now check at :05 and :35.
- Fetch jobs only run 18:00–06:00. That window is an efficiency filter to avoid wasted calls, not
  the definition of darkness. Real darkness comes from the astro boundaries at scoring time.
- Each job is wrapped so one failure is logged and doesn't stop the scheduler.

### 3.9 Alerts (ntfy)
- ntfy was chosen over SMS (no genuinely free UK option), Telegram and email.
- The topic name is a secret: it lives in the `NTFY_TOPIC` environment variable via a gitignored
  `.env` file. It was once committed to a public repo and had to be rotated.
- HTTP headers must be ASCII, so titles are stripped of emoji. The emoji comes from an ntfy tag.
- **7pm planning alert:** best window in the next 12 hours, sent if its score reaches the threshold
  (50, provisional).
- **Go-now alert:** needs darkness, fresh OVATION data (under 2 h old) at or above 10%, and cloud
  gate at least 0.5. Levels are Possible (10%), Likely (25%) and Strong (50%). After an alert it
  stays quiet for 3 hours unless the level rises. From 00:00–06:00 alerts below Strong go out at
  low priority (silent).

### 3.10 Startup self-healing
On startup, each cache source is checked separately and any missing one is fetched immediately.
The earlier all-or-nothing check meant a partly filled cache never repaired itself, and the first
`/forecast` after a rebuild returned nothing until the 18:00 jobs ran.

### 3.11 API, website and security
- The site is one static file in `docs/`, served by GitHub Pages, reading `/forecast`. The Pages
  free plan serves only the repo root or `/docs`, which is why the folder is named `docs/`.
- CORS is limited to the site's origin through the `ALLOWED_ORIGINS` variable.
- There are no debug endpoints, the FastAPI docs pages are disabled, and the `hours` parameter is
  bounded to 1–96.
- A Cloudflare rate-limit rule on the hostname blocks bursts from one IP. The limit sits at
  Cloudflare rather than in the app because the app only sees the proxy's address.
- The forecast data isn't sensitive, so there is no login. A key in a static site's JavaScript
  would be visible to everyone anyway.
- Hosting on Railway, Render or Supabase was rejected: no permanent free tier, free instances that
  sleep (which would kill the scheduler), and a database product that can't run this service.

## 4. Deliberately not done
- Met Office DataHub for weather (needs registration and has stricter limits; Open-Meteo is enough).
- AuroraWatch UK as a cross-check (its activity value doesn't expose the independent inputs).
- A history log for tuning the thresholds (judged too much machinery; tuning will use my own
  sightings instead).
- Edge-caching `/forecast` at Cloudflare (it interacts badly with the CORS headers).

## 5. Open items
- **Thresholds are unvalidated guesses:** the 50% planning alert, the OVATION levels 10/25/50 and
  the cloud limit. Revisit after real aurora nights.
- Rebind the container port to `127.0.0.1` once I confirm `cloudflared` runs on the same host.
- When weather data is missing for a window, the score assumes worst case (100% cloud), which the
  site then displays as if it were real.
- Tests cover only the timezone lookups. The scoring, moon and window modules still need tests.
