# ── Base Python image ────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5

WORKDIR /app

# System dependencies (for asyncpg and other compiled packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies layer ───────────────────────────────────────
# src/ must be copied before the editable install, or it breaks silently
FROM base AS deps

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install -e ".[google-calendar]"

# ── API runtime image ────────────────────────────────────────
FROM deps AS api

COPY apps/api/ ./apps/api/
COPY demo/ ./demo/

# Alembic config is at the root
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash synapse && \
    chown -R synapse:synapse /app
USER synapse

EXPOSE 8000

# Default command — overridden by docker-compose.yml
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
