"""
Entry point del API cazador.

Sube los routers `discover`, `analyze`, `health`. CORS solo a los
orígenes configurados (Vercel preview + producción + localhost dev).
Logging JSON apto para Cloud Logging.

Ejecutar local:
    cd api && uvicorn main:app --reload --port 8000

Ejecutar en Cloud Run: el contenedor expone $PORT (8080 por defecto)
desde Dockerfile.
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Añadimos `scripts/` al import path para reutilizar los módulos de scraping.
_API_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _API_DIR.parent / "scripts"
sys.path.insert(0, str(_API_DIR))
sys.path.insert(0, str(_SCRIPTS_DIR))

from logging_config import configure_logging  # noqa: E402
from routes import analyze, discover, health, privacy  # noqa: E402
from settings import get_settings  # noqa: E402

_settings = get_settings()
configure_logging(_settings.log_level)
logger = logging.getLogger("cazador.api")

app = FastAPI(
    title="Cazador Globalizame · API",
    description=(
        "Thin layer FastAPI sobre los adapters Python que genera leads B2B "
        "cualificados desde fuentes oficiales españolas. Uso interno de Globalizame."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def trace_and_log(request: Request, call_next):
    """Asigna un trace_id por request y mide la latencia."""
    trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        # Cualquier excepción no capturada → JSON estable, no un 500 desnudo.
        logger.exception("unhandled exception trace_id=%s", trace_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": str(exc),
                "trace_id": trace_id,
            },
        )
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Trace-Id"] = trace_id
    logger.info(
        "request",
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 1),
        },
    )
    return response


app.include_router(health.router)
app.include_router(discover.router)
app.include_router(analyze.router)
app.include_router(privacy.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "cazador-api",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
