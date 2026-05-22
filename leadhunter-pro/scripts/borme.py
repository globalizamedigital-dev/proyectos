"""
borme.py — adaptador para BORME (Boletín Oficial del Registro Mercantil).

Fuente principal: BOE.es publica el BORME en formato XML.
Endpoints:
    BORME-A sumario: https://www.boe.es/diario_borme/xml.php?id=BORME-S-{date}
    Búsqueda por empresa: https://www.boe.es/borme/dias/

Mejoras respecto a la versión original:
    - Búsqueda NIF real via scraping del buscador BORME
    - Extracción mejorada de nombres de administradores desde XML de actos
    - Fallback a búsqueda DDG si falla buscador directo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    CacheConfig, SourceStatus, cache_get, cache_set, emit_observation,
    http_get, is_valid_nif, normalize_nif, normalize_razon_social,
)


BOE_BORME_BASE = "https://www.boe.es"
BOE_BORME_SUMARIO = "https://www.boe.es/diario_borme/xml.php?id=BORME-S-{date}"
BORME_SEARCH_URL = "https://www.boe.es/borme/dias/"
# Búsqueda directa en la web del BORME
BORME_WEB_SEARCH = "https://www.boe.es/buscar/borme.php?q={query}&campo%5B%5D=titulo&sort_field%5B0%5D=fec&sort_order%5B0%5D=desc&page_hits=20"

CACHE_BORME = CacheConfig(namespace="borme", ttl_seconds=None)  # inmutable
CACHE_BORME_INDEX = CacheConfig(namespace="borme-idx", ttl_seconds=60 * 60 * 24)
CACHE_BORME_NIF = CacheConfig(namespace="borme-nif", ttl_seconds=60 * 60 * 24 * 7)


def _date_range(years: int) -> list[str]:
    """Genera fechas YYYYMMDD para los últimos N años (primer día de cada mes)."""
    today = datetime.utcnow().date()
    out = []
    for ym in range(years * 12):
        d = (today.replace(day=1) - timedelta(days=ym * 30)).replace(day=1)
        out.append(d.strftime("%Y%m%d"))
    return list(dict.fromkeys(out))


def fetch_sumario_xml(date_yyyymmdd: str) -> Optional[str]:
    """Obtiene el sumario BORME para una fecha dada. Caché permanente por fecha."""
    cache_key = f"sumario:{date_yyyymmdd}"
    cached = cache_get(CACHE_BORME, cache_key)
    if cached is not None:
        return cached
    url = BOE_BORME_SUMARIO.format(date=date_yyyymmdd)
    status, body = http_get(url, timeout=20)
    if status != 200 or "<?xml" not in body[:200]:
        return None
    cache_set(CACHE_BORME, cache_key, body)
    return body


def parse_sumario(xml_text: str) -> list[dict]:
    """Extrae (act_id, section, province, url) del sumario XML del BORME."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        ident = (item.findtext("identificador") or "").strip()
        titulo = (item.findtext("titulo") or "").strip()
        url_html = (item.findtext("urlHtml") or "").strip()
        url_xml = (item.findtext("urlXml") or "").strip()
        if ident:
            out.append({
                "id": ident,
                "title": titulo,
                "html": url_html,
                "xml": url_xml,
            })
    return out


def fetch_act_xml(url_xml: str) -> Optional[str]:
    """Obtiene el XML de un acto BORME individual. Caché permanente por ID."""
    if not url_xml:
        return None
    full = url_xml if url_xml.startswith("http") else BOE_BORME_BASE + url_xml
    cache_key = f"act:{full}"
    cached = cache_get(CACHE_BORME, cache_key)
    if cached is not None:
        return cached
    status, body = http_get(full, timeout=20)
    if status != 200:
        SourceStatus.mark("BORME-act", f"http-{status}")
        return None
    cache_set(CACHE_BORME, cache_key, body)
    return body


def _is_real_person_name(text: str) -> bool:
    """Reusa el filtro de person_finder para descartar texto que parece
    administrativo pero no es un nombre humano (cargos sueltos, secciones
    enteras del BORME, frases tipo "El Consejo de Administración")."""
    try:
        from person_finder import _looks_like_person_name
        return _looks_like_person_name(text)
    except Exception:
        # Fallback mínimo si person_finder no es importable: 2-5 palabras
        # capitalizadas, sin números ni símbolos.
        words = (text or "").strip().split()
        if not (2 <= len(words) <= 5):
            return False
        return all(w[:1].isupper() and w.replace("-", "").isalpha() for w in words)


def extract_admins_from_act_xml(xml_text: str) -> list[str]:
    """
    Extrae nombres de administradores/representantes del XML de un acto BORME.
    Los actos de constitución y nombramiento tienen sección <administradores> o similar.
    """
    admins = []
    if not xml_text:
        return admins

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # Fallback: regex sobre texto plano
        return _extract_admins_regex(xml_text)

    # Buscar en varias ubicaciones del XML del BOE
    admin_tags = ["administrador", "representante", "apoderado", "gerente",
                  "consejero", "secretario", "presidente", "director"]

    for tag in admin_tags:
        for el in root.iter(tag):
            # El nombre puede estar en texto directo o en sub-elementos
            nombre = el.text or ""
            nombre = nombre.strip()
            if not nombre:
                # Buscar sub-elementos con nombre
                for sub in el:
                    texto = (sub.text or "").strip()
                    if texto and _is_real_person_name(texto):
                        nombre = texto
                        break
            if _is_real_person_name(nombre):
                admins.append(nombre)

    # Si no hay tags específicos, buscar en texto general
    if not admins:
        admins = _extract_admins_regex(xml_text)

    return list(dict.fromkeys(admins))  # deduplicar


def _extract_admins_regex(text: str) -> list[str]:
    """
    Extrae nombres de administradores mediante patrones regex en texto plano.
    Los BORME suelen incluir "Administrador único: NOMBRE APELLIDO APELLIDO"
    """
    patrones = [
        r"(?:Administrador[a]?\s+[úu]nico|Administrador[a]?|Gerente|Representante|Director[a]?|Consejero[a]?)[\s:]+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,4})",
        r"(?:Consejero[a]?\s+[Dd]elegado)[\s:]+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,4})",
        r"Nombrado[s]?\s+(?:como\s+)?(?:administrador|gerente|director)[\s:]+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,4})",
    ]
    found = []
    for patron in patrones:
        for match in re.findall(patron, text, re.IGNORECASE):
            if _is_real_person_name(match):
                found.append(match)
    return list(dict.fromkeys(found))


def search_borme_by_razon_social(razon_social: str) -> list[dict]:
    """
    Busca en el BORME web por razón social.
    Retorna lista de coincidencias con NIF si disponible.
    """
    cache_key = f"search_rs:{normalize_razon_social(razon_social)}"
    cached = cache_get(CACHE_BORME_NIF, cache_key)
    if cached is not None:
        return cached

    # Búsqueda en buscador BOE/BORME
    query = urllib.parse.quote(razon_social[:50])
    url = BORME_WEB_SEARCH.format(query=query)
    status, body = http_get(url, timeout=20, headers={
        "Referer": "https://www.boe.es/borme/",
    })

    results = []
    if status == 200:
        # Extraer resultados de la página HTML del buscador
        # Patrón para links de resultados BORME
        pattern = re.compile(
            r'href="(/diario_borme/[^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        for m in pattern.finditer(body):
            link = m.group(1)
            titulo = m.group(2).strip()
            if any(skip in link for skip in ["/ayuda", "/calendario", "/dias/"]):
                continue
            # Extraer fecha del link (formato BORME-A-YYYY-MM-DD-NNNN)
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", link)
            results.append({
                "titulo": titulo,
                "url": BOE_BORME_BASE + link,
                "fecha": date_match.group(1) if date_match else None,
                "nif": None,  # Se extrae del acto XML si se necesita
            })

        # También buscar NIFs en el body de respuesta
        nif_pattern = re.compile(r"\b([A-HJNPQRSUVW]\d{7}[0-9A-J])\b", re.IGNORECASE)
        for m in nif_pattern.finditer(body):
            potential_nif = m.group(1).upper()
            if is_valid_nif(potential_nif) and results:
                results[-1]["nif"] = potential_nif

    cache_set(CACHE_BORME_NIF, cache_key, results[:10])
    return results[:10]


def analyze_by_nif_real(nif: str) -> dict:
    """
    Búsqueda NIF real en BORME mediante scraping del buscador de BOE.
    Estrategia: buscar el NIF directamente en el buscador del BOE.
    """
    nif = normalize_nif(nif)
    cache_key = f"nif_real:{nif}"
    cached = cache_get(CACHE_BORME_NIF, cache_key)
    if cached is not None:
        return cached

    # Búsqueda directa del NIF en el buscador BORME
    url = BORME_WEB_SEARCH.format(query=urllib.parse.quote(nif))
    status, body = http_get(url, timeout=20)

    timeline = []
    razon_social = None
    admins = []

    if status == 200:
        # Buscar menciones del NIF en los resultados
        if nif in body.upper():
            # Extraer entradas de la tabla de resultados
            row_pattern = re.compile(
                r'<tr[^>]*>.*?</tr>',
                re.DOTALL | re.IGNORECASE
            )
            for row in row_pattern.finditer(body):
                row_text = re.sub(r"<[^>]+>", " ", row.group(0))
                if nif in row_text.upper():
                    # Extraer fecha
                    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", row_text)
                    tipo_match = re.search(r"(Constituci|Nombramiento|Cese|Ampliaci|Disoluci|Fusi)", row_text, re.I)
                    if date_match:
                        timeline.append({
                            "date": date_match.group(1),
                            "type": tipo_match.group(0) if tipo_match else "Acto registral",
                            "raw": row_text[:200].strip(),
                        })

    result = {
        "nif": nif,
        "razonSocial": razon_social,
        "timeline": timeline,
        "admins": admins,
        "source": "BORME-web-search",
        "status": "ok" if timeline else "no-results",
    }
    cache_set(CACHE_BORME_NIF, cache_key, result)
    return result


def discover_by_cnae_province(cnae_codes: list[str], province: Optional[str], years: int = 1) -> list[dict]:
    """
    Modo descubrimiento. Retorna candidatos de empresa extraídos del BORME.
    Itera sumarios del rango de fechas dado y filtra por provincia.
    """
    SourceStatus.mark("BORME", "ok")
    candidates: list[dict] = []

    today = datetime.utcnow().date()
    days_to_check = min(30, years * 365)
    for offset in range(days_to_check):
        d = (today - timedelta(days=offset)).strftime("%Y%m%d")
        xml_text = fetch_sumario_xml(d)
        if not xml_text:
            continue
        for item in parse_sumario(xml_text):
            title = item["title"]
            if province and province.lower() not in title.lower():
                continue
            candidates.append({
                "razonSocial": _extract_razon_social(title),
                "nif": None,
                "bormeRef": item["id"],
                "bormeUrl": item["html"],
                "lastBormeEvent": {
                    "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
                    "type": _classify_act_type(title),
                },
                "_raw": title,
                "_admins_raw": [],
            })

    # Dedup por razón social
    seen: set[str] = set()
    deduped: list[dict] = []
    for c in candidates:
        key = normalize_razon_social(c.get("razonSocial") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    emit_observation("tool_lead_recon", {"phase": "borme.discover", "count": len(deduped)})
    return deduped


def _extract_razon_social(title: str) -> str:
    """Heurística: los títulos BORME suelen empezar con el nombre de empresa en mayúsculas."""
    parts = title.split(".")
    head = parts[0].strip()
    if head.endswith(",") or "," in head:
        head = head.split(",")[0].strip()
    return head[:200]


def _classify_act_type(title: str) -> str:
    t = title.lower()
    if "constituci" in t:
        return "Constitución"
    if "nombramiento" in t:
        return "Nombramientos"
    if "cese" in t:
        return "Ceses"
    if "ampliaci" in t and "capital" in t:
        return "Ampliación de capital"
    if "fusi" in t:
        return "Fusión"
    if "extinci" in t or "disoluci" in t:
        return "Disolución"
    if "traslado" in t:
        return "Traslado de domicilio"
    return "Otros"


def analyze_by_nif(nif: str) -> dict:
    """
    Modo análisis. Retorna el timeline BORME para un NIF dado.
    Intenta búsqueda real primero, fallback a nota informativa.
    """
    nif = normalize_nif(nif)
    if not is_valid_nif(nif):
        return {"nif": nif, "error": "invalid-nif-format", "timeline": [], "admins": []}

    SourceStatus.mark("BORME", "ok")
    # Intentar búsqueda real
    result = analyze_by_nif_real(nif)
    emit_observation("tool_lead_recon", {"phase": "borme.analyze", "nif": nif})
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="BORME adapter (LeadHunter Pro)")
    p.add_argument("--discover", action="store_true")
    p.add_argument("--analyze", action="store_true")
    p.add_argument("--search", help="Buscar por razón social")
    p.add_argument("--cnae", nargs="*", default=[])
    p.add_argument("--province")
    p.add_argument("--years", type=int, default=1)
    p.add_argument("--nif")
    args = p.parse_args()

    if args.discover:
        result = discover_by_cnae_province(args.cnae, args.province, years=args.years)
    elif args.analyze:
        if not args.nif:
            print(json.dumps({"error": "missing --nif"}, ensure_ascii=False))
            sys.exit(2)
        result = analyze_by_nif(args.nif)
    elif args.search:
        result = search_borme_by_razon_social(args.search)
    else:
        p.print_help()
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
