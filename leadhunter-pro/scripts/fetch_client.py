"""
fetch_client.py — abstracción de transporte HTTP para adapters.

Tres modos seleccionables por adapter, todos con la **misma firma**
que el `http_get` original (`(int, str)`) para que migrar un adapter
sea cambiar un import:

    fetch_plain     → urllib (estado original; default, sin coste extra).
    fetch_stealthy  → Scrapling Fetcher con TLS fingerprint Chrome; sin
                      browser ni Playwright. Útil contra WAF que detectan
                      Python (DDG, InfoEmpresa, OSM Overpass).
    fetch_dynamic   → Scrapling DynamicFetcher con Playwright; renderiza
                      JS. Reservado para SPAs (AEPD sedeAEPD).

Diseño:
- Si Scrapling no está instalado o falla al importar, fetch_stealthy/
  dynamic caen a fetch_plain con un WARNING (no rompen el pipeline).
- Feature flag `LEADHUNTER_USE_SCRAPLING=false` desactiva Scrapling
  globalmente y fuerza fetch_plain en todos los modos. Útil para
  rollback rápido sin tocar código.
- Errores de Scrapling se capturan y devuelven `(status, body)` con
  `status` en {-2, -3} para distinguirlos del 0 de urllib.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import get_logger, http_get  # noqa: E402

_logger = get_logger("fetch")

# Feature flag global. "false" → todo cae a urllib (rollback).
_USE_SCRAPLING = os.environ.get("LEADHUNTER_USE_SCRAPLING", "true").lower() != "false"

# Cache de disponibilidad: probamos a importar una vez y recordamos.
_scrapling_available: Optional[bool] = None
_dynamic_available: Optional[bool] = None


def _has_scrapling() -> bool:
    """¿Está Scrapling instalado y operativo? Cacheado tras el primer try."""
    global _scrapling_available
    if _scrapling_available is not None:
        return _scrapling_available
    if not _USE_SCRAPLING:
        _scrapling_available = False
        return False
    try:
        from scrapling.fetchers import Fetcher  # noqa: F401
        _scrapling_available = True
    except Exception as exc:  # noqa: BLE001
        _logger.warning("Scrapling no disponible (%s) — fallback a urllib", exc)
        _scrapling_available = False
    return _scrapling_available


def _has_dynamic() -> bool:
    """¿Tenemos Playwright instalado para DynamicFetcher?"""
    global _dynamic_available
    if _dynamic_available is not None:
        return _dynamic_available
    if not _has_scrapling():
        _dynamic_available = False
        return False
    try:
        from scrapling.fetchers import DynamicFetcher  # noqa: F401
        _dynamic_available = True
    except Exception as exc:  # noqa: BLE001
        _logger.warning("DynamicFetcher no disponible (%s)", exc)
        _dynamic_available = False
    return _dynamic_available


def _response_to_tuple(r) -> tuple[int, str]:
    """Convierte un scrapling.Response a la tupla (status, body) clásica."""
    try:
        body = r.body
        if isinstance(body, bytes):
            body = body.decode(r.encoding or "utf-8", errors="replace")
        return int(r.status or 0), body or ""
    except Exception as exc:  # noqa: BLE001
        return -2, f"scrapling-response-error:{type(exc).__name__}:{exc}"


# ─────────────────────────────────────────────────────────────────────
# Modo 1 · fetch_plain — urllib tal cual, fallback universal.
# ─────────────────────────────────────────────────────────────────────
def fetch_plain(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 15,
    retries: int = 3,
    rate_limit: float = 1.0,
) -> tuple[int, str]:
    """HTTP simple con urllib. Reemplazo directo del antiguo `http_get`."""
    return http_get(url, headers=headers, timeout=timeout, retries=retries,
                    rate_limit=rate_limit)


# ─────────────────────────────────────────────────────────────────────
# Modo 2 · fetch_stealthy — TLS fingerprint Chrome, sin browser.
# ─────────────────────────────────────────────────────────────────────
def fetch_stealthy(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 15,
    retries: int = 3,
    rate_limit: float = 1.0,
    impersonate: str = "chrome131",
) -> tuple[int, str]:
    """
    Fetch con TLS fingerprint de Chrome real (vía curl_cffi).
    Bypassa WAFs sencillos sin necesidad de Playwright.

    Si Scrapling no está disponible, cae a fetch_plain con WARNING.
    """
    if not _has_scrapling():
        return fetch_plain(url, headers=headers, timeout=timeout,
                           retries=retries, rate_limit=rate_limit)

    try:
        from scrapling.fetchers import Fetcher
    except Exception as exc:  # noqa: BLE001
        _logger.warning("Fetcher import falló (%s) — fallback urllib", exc)
        return fetch_plain(url, headers=headers, timeout=timeout)

    last_status, last_body = 0, ""
    attempts = max(1, retries)
    for attempt in range(attempts):
        try:
            r = Fetcher.get(
                url,
                timeout=timeout,
                impersonate=impersonate,
                headers=headers or {},
                # Scrapling toma rate_limit internamente; no necesitamos throttle
                # adicional aquí porque cada adapter ya pasa por su propio caché.
            )
            last_status, last_body = _response_to_tuple(r)
            if 200 <= last_status < 400:
                return last_status, last_body
            if last_status in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                _logger.warning(
                    "fetch_stealthy %s -> %d (intento %d/%d)",
                    url, last_status, attempt + 1, attempts,
                )
                continue
            return last_status, last_body
        except Exception as exc:  # noqa: BLE001
            last_status, last_body = -3, f"stealthy-error:{type(exc).__name__}:{exc}"
            if attempt < attempts - 1:
                _logger.warning(
                    "fetch_stealthy %s lanzó %s (intento %d/%d)",
                    url, type(exc).__name__, attempt + 1, attempts,
                )
                continue
    return last_status, last_body


# ─────────────────────────────────────────────────────────────────────
# Modo 3 · fetch_dynamic — Playwright real (SPAs).
# ─────────────────────────────────────────────────────────────────────
def fetch_dynamic(
    url: str,
    wait_for: Optional[str] = None,
    wait_ms: int = 0,
    timeout: int = 25,
    headers: Optional[dict] = None,
    network_idle: bool = True,
) -> tuple[int, str]:
    """
    Renderiza JS con Playwright headless. `wait_for` es un selector CSS
    al que esperamos antes de devolver el HTML; `wait_ms` es un sleep
    adicional opcional (en milisegundos).

    Si DynamicFetcher no está disponible (no se instaló Playwright o
    chromium), cae a fetch_stealthy → fetch_plain.
    """
    if not _has_dynamic():
        return fetch_stealthy(url, headers=headers, timeout=timeout)

    try:
        from scrapling.fetchers import DynamicFetcher
        r = DynamicFetcher.fetch(
            url,
            headless=True,
            timeout=timeout * 1000,             # Scrapling usa ms
            wait=wait_ms,
            wait_selector=wait_for,
            network_idle=network_idle,
            extra_headers=headers or {},
        )
        return _response_to_tuple(r)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("fetch_dynamic %s lanzó %s — fallback stealthy",
                        url, type(exc).__name__)
        return fetch_stealthy(url, headers=headers, timeout=timeout)


__all__ = ["fetch_plain", "fetch_stealthy", "fetch_dynamic"]
