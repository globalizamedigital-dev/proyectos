"""
aepd.py — lookup en el registro de Delegados de Protección de Datos (DPO) de la AEPD.

Endpoint: https://www.aepd.es/dpd/buscar.html (formulario web)
La AEPD no expone API JSON pública, pero el formulario acepta GET con query params.
Esta implementación es best-effort: hace una consulta y parsea la respuesta HTML
para detectar si hay coincidencia. Si la página cambia, marca SourceStatus="down".

Uso:
    python aepd.py --nif B12345678
    python aepd.py --razon-social "Asesores Pérez S.L."
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CacheConfig, SourceStatus, cache_get, cache_set, emit_observation, http_get, normalize_nif
from fetch_client import fetch_dynamic, fetch_stealthy

CACHE = CacheConfig(namespace="aepd", ttl_seconds=60 * 60 * 24 * 30)
# La AEPD migró el buscador de DPO entre 2024-2026. Probamos en orden:
#   1) URL clásica (www.aepd.es/dpd/buscar.html) — devuelve 404 hoy pero la
#      mantenemos por si la AEPD la restaura.
#   2) Nueva sede electrónica (sedeaepd.gob.es) — actualmente es una SPA
#      Angular renderizada en cliente; sin Playwright el HTML no contiene
#      datos. Si detectamos esto, marcamos `js-spa` y degradamos limpio.
AEPD_ENDPOINTS_NIF = [
    "https://www.aepd.es/dpd/buscar.html?nif={nif}",
    "https://sedeaepd.gob.es/sede-electronica/dpd/buscar?nif={nif}",
]
AEPD_ENDPOINTS_NAME = [
    "https://www.aepd.es/dpd/buscar.html?razon_social={name}",
    "https://sedeaepd.gob.es/sede-electronica/dpd/buscar?razon_social={name}",
]
# Marcadores de "shell SPA": página vacía o que solo carga JS bundles.
_SPA_MARKERS = ("chunk-", "<app-root", "ng-version", "id=\"app\"")
_AEPD_MIN_BODY = 1500


def lookup_dpo(nif: Optional[str] = None, razon_social: Optional[str] = None) -> dict:
    """
    Returns:
        {
            "registered": bool,
            "source": "AEPD" | None,
            "raw_match": str | None,
            "method": "nif" | "razon-social",
        }

    NOTE: La AEPD ha cambiado la URL del buscador en 2024-2025. Este módulo
    intenta el endpoint conocido pero NO falla si responde 404 o HTML vacío:
    devuelve {"registered": False, "source": None} y emite source_unavailable.
    """
    import urllib.parse

    if nif:
        nif = normalize_nif(nif)
        cache_key = f"nif:{nif}"
        method = "nif"
        endpoints = [u.format(nif=urllib.parse.quote(nif)) for u in AEPD_ENDPOINTS_NIF]
        needle = nif
    elif razon_social:
        cache_key = f"name:{razon_social}"
        method = "razon-social"
        endpoints = [u.format(name=urllib.parse.quote(razon_social)) for u in AEPD_ENDPOINTS_NAME]
        needle = razon_social
    else:
        return {"registered": False, "source": None, "method": None, "error": "missing-input"}

    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    # Probar endpoints en orden:
    #   1º · URL clásica con fetch_stealthy (Chrome TLS) — barato y rápido.
    #   2º · Sede electrónica nueva con fetch_dynamic (Playwright) — más caro
    #        pero renderiza la SPA Angular para que aparezcan los datos.
    last_status: int = 0
    last_url = endpoints[0]
    for idx, url in enumerate(endpoints):
        if idx == 0:
            status, body = fetch_stealthy(url, timeout=15)
        else:
            # SPA: esperamos al selector típico de Angular o, en su defecto,
            # red en idle. 8 s de espera basta para que pinte el resultado.
            status, body = fetch_dynamic(
                url,
                wait_for="app-root, [data-testid=dpo-results], main",
                wait_ms=2000,
                timeout=25,
            )
        last_status, last_url = status, url
        if status not in (200, 302):
            continue
        # Detectar shell SPA sin renderizar: 200 con contenido inútil.
        if len(body) < _AEPD_MIN_BODY or all(m in body for m in ("chunk-",)) and "<app-root></app-root>" in body:
            SourceStatus.mark("AEPD", "js-spa")
            emit_observation("source_unavailable", {"source": "AEPD", "status": "js-spa", "url": url})
            continue
        SourceStatus.mark("AEPD", "ok")
        found = needle.upper() in body.upper()
        result = {
            "registered": found,
            "source": "AEPD" if found else None,
            "method": method,
            "url": url,
        }
        cache_set(CACHE, cache_key, result)
        return result

    # Ningún endpoint dio respuesta scrapeable.
    SourceStatus.mark("AEPD", f"endpoint-changed-http-{last_status}")
    emit_observation("source_unavailable", {"source": "AEPD", "status": last_status})
    result = {
        "registered": False,
        "source": None,
        "method": method,
        "error": "endpoint-changed",
        "note": "AEPD migró a SPA en sedeaepd.gob.es; lookup plano no soportado.",
        "url": last_url,
    }
    cache_set(CACHE, cache_key, result)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="AEPD DPO registry lookup")
    p.add_argument("--nif")
    p.add_argument("--razon-social", dest="razon_social")
    args = p.parse_args()
    print(json.dumps(lookup_dpo(nif=args.nif, razon_social=args.razon_social), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
