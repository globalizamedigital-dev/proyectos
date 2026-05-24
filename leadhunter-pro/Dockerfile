# Cazador API · imagen para Cloud Run europe-west1.
# Multi-stage: builder con Playwright + dependencias, runtime sin caché pip.

# ── Stage 1: builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Dependencias del sistema (incluidas las que pide Playwright/Patchright).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gcc libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Lista de deps; las clavamos en el pyproject para reproducibilidad.
COPY api/pyproject.toml ./pyproject.toml
RUN pip install \
        "fastapi>=0.115" "uvicorn[standard]>=0.32" \
        "pydantic>=2.9" "pydantic-settings>=2.6" \
        "pyjwt[crypto]>=2.10" "cryptography>=43" "httpx>=0.27" \
        "supabase>=2.10" "python-json-logger>=2.0" \
        "scrapling[fetchers]>=0.4"

# Playwright/chromium: hace falta para fetch_dynamic (AEPD SPA).
# Si no quieres pagarte el ~250 MB de chromium en la imagen, comenta
# esta línea y AEPD caerá al fallback stealthy automáticamente.
RUN playwright install --with-deps chromium || true

# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Copia paquetes y binarios desde el builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Dependencias runtime para chromium headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Importante: api/ y scripts/ van como hermanos para que main.py los
# añada al sys.path (igual que en local).
COPY scripts/ /app/scripts/
COPY api/     /app/api/

WORKDIR /app/api

# Cloud Run inyecta $PORT en runtime; uvicorn lo respeta.
EXPOSE 8080
CMD exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" --workers 1
