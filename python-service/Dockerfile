FROM python:3.12-slim

# Give the container real timezone data and set it to match every
# assumption baked into window_generator.py/moon.py/forecast.py - those
# treat "now" as already being local UK time, not UTC.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Europe/London

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src

ENV PYTHONPATH=/app/src
ENV AURORA_CACHE_PATH=/app/data/aurora_cache.json

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "aurorabeacon.main:app", "--host", "0.0.0.0", "--port", "8000"]