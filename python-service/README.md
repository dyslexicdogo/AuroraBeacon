# aurorabeacon (service)

The FastAPI service behind AuroraBeacon: scheduled data fetchers, the aurora scoring logic, and
the ntfy alert jobs.

See the [project README](../Readme.md) for what it does, how to run and deploy it, and the
configuration options, and [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md) for why it is
built this way.

```bash
uv sync
uv run uvicorn aurorabeacon.main:app --reload   # run the API and scheduler
uv run pytest                                   # run the tests
```