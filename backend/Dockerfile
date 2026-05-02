# Multi-stage: wheel build terpisah agar image runtime lebih ramping.
# Build: docker compose build backend  (context ./backend)

FROM python:3.11-slim-bullseye AS builder

WORKDIR /build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install build dependencies hanya untuk compile wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.11-slim-bullseye AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOGGING_CONF_PATH=/app/docker/logging.conf \
    PIP_NO_CACHE_DIR=1

# postgresql-client untuk pg_isready di entrypoint; curl untuk healthcheck Compose.
# Install runtime dependencies saja, bukan build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python packages dari wheels, lalu bersihkan agresif
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels /root/.cache /tmp/* \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type f -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11 -type f -name "*.pyo" -delete \
    && find /usr/local/lib/python3.11 -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type d -name "test" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -name "*.dist-info" -type d -exec sh -c 'rm -f "$1"/RECORD "$1"/INSTALLER' _ {} \; 2>/dev/null || true \
    && rm -rf /usr/local/lib/python3.11/site-packages/pip* \
    && rm -rf /usr/local/lib/python3.11/site-packages/setuptools* \
    && rm -rf /usr/local/lib/python3.11/site-packages/wheel*

# Copy hanya file yang diperlukan untuk runtime
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY docker/logging.conf /app/docker/logging.conf
COPY scripts /app/scripts
COPY entrypoint.sh /app/entrypoint.sh

# Bersihkan __pycache__ dari aplikasi yang di-copy
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /app -type f -name "*.pyc" -delete \
    && find /app -type f -name "*.pyo" -delete

# User non-root: log sengketa ke /tmp agar writable.
RUN groupadd --gid 1000 agentpay \
    && useradd --uid 1000 --gid agentpay --shell /bin/bash --create-home agentpay \
    && chown -R agentpay:agentpay /app \
    && chmod +x /app/entrypoint.sh

USER agentpay

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health >/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
