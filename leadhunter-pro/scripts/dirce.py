"""
dirce.py — DIRCE (Directorio Central de Empresas, INE) — SOLO segment sizing.

DIRCE NO es un directorio nominal. Es estadístico agregado por CNAE × provincia × estrato.
Esta skill lo usa SOLO para dimensionar el segmento, NUNCA para listar empresas.

Endpoint INE Tempus3:
    https://servicios.ine.es/wstempus/jsCache/ES/DATOS_TABLA/{tabla}
La tabla más usable para DIRCE empresas activas por CNAE+provincia es la 4719.

Output:
    {"totalCompanies": int|null, "source": "DIRCE", "year": int, "note": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CacheConfig, SourceStatus, cache_get, cache_set, get_logger, http_get

CACHE = CacheConfig(namespace="dirce", ttl_seconds=60 * 60 * 24 * 30)
INE_TABLE_URL = "https://servicios.ine.es/wstempus/jsCache/ES/DATOS_TABLA/{tabla}?nult=1"

# IDs de tabla DIRCE conocidos. INE renumera las tablas cada cierto tiempo; al
# probar varios en orden cubrimos los cambios sin requerir un refactor anual.
_DIRCE_TABLE_IDS = ("4720", "4719")


def segment_size(cnae: str, province: Optional[str] = None) -> dict:
    """
    Returns the approximate number of companies in DIRCE for the given CNAE
    (and optionally province). Heuristic: queries a known INE table and
    extracts the relevant cell. NEVER returns a list of companies.

    Hoy en día la integración real está pendiente: el id de tabla cambia entre
    refrescos de INE y mapear CNAE+provincia→celda exige conocer la estructura
    de cada versión. En vez de pretender que funciona, probamos las tablas
    conocidas, logueamos WARN si todas fallan, y devolvemos `null` total con
    nota explícita para que el orquestador lo trate como dato no disponible.
    """
    cache_key = f"{cnae}:{province or '*'}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    logger = get_logger("dirce")
    last_status = 0
    used_table = None
    for table_id in _DIRCE_TABLE_IDS:
        status, _body = http_get(INE_TABLE_URL.format(tabla=table_id), timeout=10, retries=1)
        last_status = status
        if status == 200:
            used_table = table_id
            break
        logger.warning("DIRCE tabla %s -> http %s (probable cambio de id en INE)", table_id, status)

    if used_table is None:
        SourceStatus.mark("DIRCE", f"tables-missing-{last_status}")
        logger.warning(
            "DIRCE: ninguna de las tablas %s respondió 200; el id de tabla cambió. "
            "Actualizar _DIRCE_TABLE_IDS en scripts/dirce.py.",
            _DIRCE_TABLE_IDS,
        )
        note = (
            "Ninguna tabla DIRCE conocida responde. INE ha renumerado las tablas; "
            "actualizar _DIRCE_TABLE_IDS en scripts/dirce.py."
        )
    else:
        # Tabla viva pero el parsing CNAE×provincia sigue sin estar implementado.
        SourceStatus.mark("DIRCE", "stub")
        note = (
            f"Tabla INE {used_table} accesible, pero el mapeo CNAE×provincia→celda "
            "no está implementado. Integración completa requiere parser específico."
        )

    result = {
        "totalCompanies": None,
        "source": "DIRCE",
        "note": note,
        "cnae": cnae,
        "province": province,
        "ine_table_probed": used_table,
    }
    cache_set(CACHE, cache_key, result)
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cnae", required=True)
    p.add_argument("--province")
    args = p.parse_args()
    print(json.dumps(segment_size(args.cnae, args.province), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
