# Aurora Predictor — Architecture Decisions Log

A living record of design decisions made during development, and the reasoning behind them.
Append to this file as each phase progresses — don't rewrite history, add new entries.

---

## Phase 1: Architecture & Data Flow Design — ✅ Locked

### Layering (Clean Architecture)
Three layers, dependencies point inward only:

- **Presentation** — Compose UI + ViewModel(s). Depends on Domain.
- **Domain** — Models, Repository *interfaces*, Use Cases, ProbabilityEngine. Depends on nothing else.
- **Data** — Repository implementations, API clients (NOAA, Open-Meteo), DTOs/mappers. Depends on Domain (to implement its interfaces).

**Rule:** Data implements the contracts Domain defines. Domain never imports anything from Data.
This is Dependency Inversion — it's what makes Domain testable in a plain JVM test, no emulator required.

### Key decisions
- **Repository = contract, not storage.** An interface in `domain/repository/`; the *implementation*
  lives in `data/`. Domain calls the interface and never knows which real backend answers it.
- **Use Case = orchestrator, not scheduler.** `GetForecastUseCase` gathers data from repositories and
  runs `ProbabilityEngine`. It does **not** know about WorkManager or the 3-hour schedule — that's an
  infrastructure concern. WorkManager *calls* the Use Case; the Use Case doesn't schedule itself.
  This keeps the Use Case unit-testable without Android framework dependencies.
- **ProbabilityEngine = pure function.** Takes already-fetched values in, returns a score out. No I/O,
  no repository calls, no knowledge that a network exists. Testable with hardcoded inputs.
- **SunMoonPosition stays a repository**, even though it's deterministic/computable, to keep the
  Use Case's data-gathering pattern uniform. Its Data-layer implementation will do local calculation
  instead of an HTTP call — the interface contract doesn't care how the answer is produced.

### Open / deferred decisions
- Met Office DataHub API (higher-res UK data) considered as a v2 upgrade over Open-Meteo — deferred,
  not a blocker, avoids extra auth setup while learning architecture.
- AuroraWatch UK (magnetometer-based, ground-truth geomagnetic activity in nT) considered as a
  supplementary cross-check field later. Not used for core scoring — it doesn't expose Bz or solar
  wind speed/density separately, which the domain formula needs as independent weighted inputs.

---

## Phase 2: Domain Models & Contracts — 🚧 In Progress

### `WeatherSnapshot` — ✅ Locked

```kotlin
data class WeatherSnapshot(
    val forecastTime: Instant,       // the future moment this snapshot describes
    val forecastFetchTime: Instant,  // when this data was actually fetched from the API
    val cloudHigh: Int,              // % 0-100 — a count, not a continuous measurement, stays Int
    val cloudMid: Int,               // % 0-100
    val cloudLow: Int,               // % 0-100
    val visibility: Double,          // km
    val temperature: Double,         // °C
    val dewPoint: Double              // °C — ProbabilityEngine computes temperature - dewPoint (spread)
                                      // as a granular fog/optical-clarity proxy, rather than a
                                      // pre-baked or boolean fog flag. Keeps the model a pure data
                                      // holder; all scoring logic (incl. the fog threshold) stays in
                                      // ProbabilityEngine, so the formula can be tuned/tested in isolation.
)
```

**Numeric type convention (applies to all domain models):** `Double` for continuous/measured
values — matches what JSON parsing libraries (kotlinx.serialization, Moshi) default to, avoiding
type-mismatch friction in `ProbabilityEngine`'s math. `Int` stays for percentages, which represent
a count/whole-number concept rather than a continuous measurement.

**Design principle reinforced here:** models hold *raw fetched facts* only. Any derived/computed
value (dew point spread, fog judgment, etc.) is computed by `ProbabilityEngine`, not baked into the
model at parse time. This was explicitly chosen over a pre-computed `dewPointSpread` field and over
a boolean `fog` flag from Open-Meteo's WMO weather code.

**Open decision:** concrete type for `Instant` — `kotlinx.datetime.Instant` vs `java.time.LocalDateTime`.
Deferred to the Data layer phase, since it depends on how the chosen API's timestamps are parsed.

### `SolarActivity` + `KpForecastSlot` — ✅ Locked (supersedes earlier single-class `SolarActivity` and the deleted `SpaceWeatherAlert`)

**Why two classes, not one:** NOAA exposes two genuinely different products — a live L1 in-situ
reading (updates every 1-5 min, "go out now" data) and a 3-hour-bucketed Kp forecast spanning
1-3 days ahead. A single model can't represent both a point-in-time reading and a list of future
forecast buckets without conflating them. `SpaceWeatherAlert` (CME arrival-window fields) was
proposed as a third class, then dropped — `KpForecastSlot` was judged to already cover "what's
coming" for v1 purposes, without needing separate CME-specific arrival-window tracking.

```kotlin
enum class FlareClass { A, B, C, M, X }   // GOES flare classification. Split into class + magnitude
                                            // (not a raw "X1.5" string) because NOAA already reports
                                            // these as separate raw values — this isn't a derived
                                            // interpretation like fog or night phase, it's how the
                                            // data actually arrives.

data class SolarActivity(                  // LIVE reading, ~1-5 min cadence, L1 satellite
    val activityTime: Instant,             // sensor reading time
    val activityFetchTime: Instant,        // local fetch time
    val kp: Double,                        // 0.0-9.0
    val bz: Double,                        // nT — negative = favorable for aurora
    val solarWindSpeed: Double,            // km/s
    val solarWindDensity: Double,          // particles/cm³
    val flareClass: FlareClass? = null,    // most recent flare, if any
    val flareMagnitude: Double? = null     // e.g. 1.5 for "X1.5"
)

data class KpForecastSlot(                 // ONE 3-hour bucket; app holds List<KpForecastSlot>
    val timeSlot: Instant,                 // start of this 3-hour window
    val predictedKp: Double,               // 0.0-9.0
    val noaaScale: String? = null,         // "G1"-"G5" geomagnetic storm scale, null if below G1
    val isPredicted: Boolean               // true = forecast, false = already-observed history
)
```

**Rejected: computed `isHeadOutNowAlertActive: Boolean` getter on the model.** Same pattern as the
dew-point-spread and `NightPhase` decisions — a threshold-based boolean derived from raw fields,
proposed to live on the data model. Rejected for the same reason: models hold raw facts only.
**Where it belongs instead:** the Presentation layer — a computed property on the ViewModel's UI
state, derived from whatever `ProbabilityEngine` already output. Not a Domain concern at all; it's
purely a UI-display decision, one layer further out than where dew point/night phase logic lives.

### `SunMoonPosition` — ⏳ Not yet started
Confirmed required fields: sun altitude angle (below horizon = astronomical night), moon altitude
angle relative to horizon, moon phase/illumination. Reasoning: illumination alone isn't enough —
a full moon *below* the horizon shouldn't reduce the visibility score, so altitude is needed
alongside phase. Types/units not yet finalized.

### `SunMoonPosition` — ✅ Locked

```kotlin
data class SunMoonPosition(
    val positionTime: Instant,   // deterministic/computed for this moment — no fetchTime needed,
                                  // since this isn't retrieved from a changing external source
    val sunAltitude: Double,     // degrees above(+)/below(-) horizon; astronomical night < -18°
    val moonAltitude: Double,    // degrees above(+)/below(-) horizon
    val moonIllumination: Double, // % 0.0-100.0, fraction of visible moon face lit
    val moonAzimuth: Double      // degrees 0-360, compass direction of the moon
)
```

**Decisions made:**
- No `fetchTime` — position is computed deterministically from location+time, not fetched from a
  live/changing source, so "when was this fetched" isn't a meaningful concept here.
- Considered a `NightPhase` enum (DAYLIGHT / CIVIL_TWILIGHT / .../ ASTRONOMICAL_NIGHT) derived from
  `sunAltitude`, but dropped it — same reasoning as the dew-point-spread decision in `WeatherSnapshot`:
  the model should hold raw facts only, and threshold interpretation belongs in `ProbabilityEngine`,
  where it can be tuned/tested without touching the model.
- `moonAzimuth` kept even though the current domain spec only states "moon illumination reduces
  visibility score" (no directional rule). Justification: aurora activity concentrates toward
  magnetic north, so direction is physically relevant to visibility, not speculative scope creep.
  **Caveat:** this field is captured but not yet consumed by any formula — Phase 4 (Probability
  Engine) must explicitly decide how/whether azimuth weights the score, or it does nothing.

### Repository interfaces — ✅ Locked — Phase 2 Complete

```kotlin
interface WeatherRepository {
    suspend fun getForecast(
        location: Location,
        startDate: Instant
    ): Result<List<WeatherSnapshot>>
}

interface KpForecastRepository {
    suspend fun getGlobalKpForecast(): Result<List<KpForecastSlot>>
    // no Location param — Kp/Bz are global scalar values, not location-dependent
}

interface LocalAuroraActivityRepository {
    suspend fun getLocalAuroraActivity(
        location: Location
    ): Result<LocalAuroraActivity>
}

interface SunMoonRepository {
    suspend fun getSunMoonPositions(
        location: Location,
        startDate: Instant
    ): Result<List<SunMoonPosition>>
}
```

**Design decisions:**
- All four interfaces are `suspend fun`, not `Flow<...>` — WorkManager calls each one, gets one
  answer, done. No open/ongoing stream needed for a periodically-triggered fetch.
- All four wrapped in `Result<...>`, applied **uniformly across all repositories, including
  `SunMoonRepository`** even though sun/moon position is computed locally rather than fetched over
  a network. Deliberate choice: keeps `GetForecastUseCase` able to treat all repositories
  identically, rather than special-casing the one that "can't fail" from a network perspective.
- `Location` is a shared `domain/model/` data class (`latitude`, `longitude`) used wherever a
  repository needs a coordinate — not redeclared per-interface.
- `KpForecastRepository` intentionally takes no `Location` — confirms the earlier reasoning that
  Kp/Bz/solar wind are planetary-scalar values, not location-specific. `LocalAuroraActivityRepository`
  is the one that's location-aware, since it resolves NOAA's OVATION grid to a specific coordinate.

---

## Phase 2 Summary — Complete Domain Layer

**Models:** `Location`, `WeatherSnapshot`, `LocalAuroraActivity`, `KpForecastSlot`, `SunMoonPosition`,
`FlareClass` (defined, currently unused — parked for a future flare-severity feature)

**Repositories:** `WeatherRepository`, `KpForecastRepository`, `LocalAuroraActivityRepository`,
`SunMoonRepository`

**Rejected/superseded along the way (kept here for the reasoning trail, not as active design):**
- Single combined `SolarActivity` (raw Kp/Bz/wind) → replaced by `LocalAuroraActivity` (consumes
  NOAA's already-localized OVATION probability instead of reimplementing geomagnetic-latitude physics)
- `SpaceWeatherAlert` (CME arrival window) → superseded by `KpForecastSlot` for v1
- Pre-computed `dewPointSpread`, `NightPhase` enum, `isHeadOutNowAlertActive` getter → all rejected
  as derived/interpreted values that don't belong on raw data models
- `moonAzimuth` → kept, but flagged as captured-and-unused until Phase 4 formula explicitly weights it

---

---

## Phase 3–6
Not yet started. See project roadmap for scope.