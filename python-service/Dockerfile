FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "aurorabeacon.main:app", "--host", "0.0.0.0", "--port", "8000"]
