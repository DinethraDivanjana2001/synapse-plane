# ── Base Python image ────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies (for asyncpg and other compiled packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies layer ───────────────────────────────────────
# `pip install -e .` is an EDITABLE install: it needs src/ present at
# install time to build a working path mapping into site-packages. Copying
# only pyproject.toml here (to cache this layer separately from source
# changes) silently produces a broken link — `import synapse_plane` then
# fails at runtime even though pip reports success. So src/ must be copied
# before this RUN, not after.
FROM base AS deps

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install -e "."

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
