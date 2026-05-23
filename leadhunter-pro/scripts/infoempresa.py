"""
infoempresa.py — Scraping de InfoEmpresa.es para datos de empresa.

InfoEmpresa.es es gratuita y pública. Proporciona:
    - Sector, rango de empleados, rango de ingresos
    - Dirección, CIF, web
    - Administradores registrados

Patrón URL: https://www.infoempresa.com/empresa/es/{slug}
Búsqueda: https://www.infoempresa.com/buscar/es/empresa?filtros={nombre}

Sin API — scraping HTML best-effort.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CacheConfig, SourceStatus, cache_get, cache_set, emit_observation, http_get, normalize_razon_social
from fetch_client import fetch_stealthy

CACHE = CacheConfig(namespace="infoempresa", ttl_seconds=60 * 60 * 24 * 7)

INFOEMPRESA_BASE = "https://www.infoempresa.com"
# InfoEmpresa migró en 2025-2026 a la estructura /es-es/es/. Las URLs antiguas
# devolvían 301 a la home (sin conservar el NIF/slug) y luego una página
# prácticamente vacía. Las nuevas URLs sí responden con contenido, aunque la
# web sigue siendo agresiva con scrapers: si el body es minúsculo o no tiene
# señales de página de empresa, marcamos la fuente como `blocked` y seguimos.
INFOEMPRESA_SEARCH = INFOEMPRESA_BASE + "/es-es/es/buscar?filtros={query}"
INFOEMPRESA_COMPANY = INFOEMPRESA_BASE + "/es-es/es/empresa/{slug}"
INFOEMPRESA_NIF = INFOEMPRESA_BASE + "/es-es/es/empresa/cif/{nif}"

# Tamaño mínimo de body para considerar que la página tiene contenido real.
# Una página vacía o de login-wall típica pesa <2KB; las fichas reales >20KB.
_INFOEMPRESA_MIN_BODY = 2000


def _slugify(razon_social: str) -> str:
    """Convierte razón social a slug para InfoEmpresa."""
    s = normalize_razon_social(razon_social)
    # Eliminar formas jurídicas comunes
    for form in ["sl", "sa", "slu", "slp", "cb", "sccl"]:
        s = re.sub(rf"\b{form}\b", "", s)
    # Convertir espacios a guiones
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _clean_text(html_fragment: str) -> str:
    """Elimina tags HTML y normaliza espacios."""
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_field(html: str, label_pattern: str) -> Optional[str]:
    """Extrae el valor de un campo específico buscando por etiqueta."""
    pattern = re.compile(
        rf'{label_pattern}\s*:?\s*</?\w+[^>]*>?\s*([^<\n]{{2,100}})',
        re.IGNORECASE
    )
    m = pattern.search(html)
    if m:
        return _clean_text(m.group(1)).strip()

    # Fallback: buscar patrón más genérico
    pattern2 = re.compile(
        rf'{label_pattern}[^>]*>[^<]*</[^>]+>\s*<[^>]+>\s*([^<]{{2,100}})',
        re.IGNORECASE
    )
    m2 = pattern2.search(html)
    if m2:
        return _clean_text(m2.group(1)).strip()

    return None


def _parse_company_page(html: str, url: str) -> dict:
    """Parsea la página de empresa de InfoEmpresa."""
    result: dict = {
        "source": "InfoEmpresa",
        "url": url,
        "razonSocial": None,
        "nif": None,
        "sector": None,
        "employees_range": None,
        "revenue_range": None,
        "address": None,
        "website": None,
        "admins": [],
        "cnae": None,
        "founded": None,
        "raw": {},
    }

    if not html:
        return result

    # Razón social (en el h1 o título de la página)
    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
    if h1_match:
        result["razonSocial"] = _clean_text(h1_match.group(1))

    # NIF/CIF
    nif_patterns = [
        re.compile(r'\b([A-HJNPQRSUVW]\d{7}[0-9A-J])\b', re.IGNORECASE),
        re.compile(r'CIF[:\s]+([A-HJNPQRSUVW]\d{7}[0-9A-J])', re.IGNORECASE),
    ]
    for pat in nif_patterns:
        m = pat.search(html)
        if m:
            result["nif"] = m.group(1).upper()
            break

    # Dirección (buscar en bloques de dirección)
    addr_patterns = [
        re.compile(r'(?:Calle|C/|Avda?\.?|Avenida|Plaza|Paseo)\s+[^<\n]{5,100}', re.IGNORECASE),
        re.compile(r'\b\d{5}\s+[A-Za-záéíóúñü]{3,30}\b'),
    ]
    for pat in addr_patterns:
        m = pat.search(html)
        if m:
            result["address"] = _clean_text(m.group(0))
            break

    # Sector/actividad
    sector_match = re.search(r'(?:Actividad|Sector|CNAE)[:\s]+</?\w+[^>]*>?\s*([^<\n]{5,100})', html, re.IGNORECASE)
    if sector_match:
        result["sector"] = _clean_text(sector_match.group(1))

    # Código CNAE
    cnae_match = re.search(r'CNAE[:\s-]+(\d{4})', html, re.IGNORECASE)
    if cnae_match:
        result["cnae"] = cnae_match.group(1)

    # Empleados
    emp_patterns = [
        re.compile(r'(?:Empleados?|Trabajadores?)[:\s]+</?\w+[^>]*>?\s*([^<\n]{2,50})', re.IGNORECASE),
        re.compile(r'(\d+\s*[-–]\s*\d+)\s*empleados?', re.IGNORECASE),
        re.compile(r'(\d+)\s*empleados?', re.IGNORECASE),
    ]
    for pat in emp_patterns:
        m = pat.search(html)
        if m:
            result["employees_range"] = _clean_text(m.group(1))
            break

    # Facturación/ingresos
    rev_patterns = [
        re.compile(r'(?:Facturaci[oó]n|Ingresos?|Revenue)[:\s]+</?\w+[^>]*>?\s*([^<\n]{2,80})', re.IGNORECASE),
        re.compile(r'([€$]?\s*\d[\d.,]+\s*(?:M|K|mill[oó]nes?|miles)?)\s*(?:de\s+)?(?:euros?|€)', re.IGNORECASE),
    ]
    for pat in rev_patterns:
        m = pat.search(html)
        if m:
            result["revenue_range"] = _clean_text(m.group(1))
            break

    # Web de la empresa
    web_match = re.search(
        r'(?:Web|Website|P[aá]gina\s+web)[:\s]+.*?href="(https?://[^"]+)"',
        html, re.IGNORECASE
    )
    if not web_match:
        # Buscar links externos que no sean de InfoEmpresa
        external_links = re.findall(r'href="(https?://(?!www\.infoempresa)[^"]{10,100})"', html)
        for link in external_links:
            if not any(skip in link for skip in ["google.", "facebook.", "twitter.", "linkedin."]):
                result["website"] = link
                break
    else:
        result["website"] = web_match.group(1)

    # Administradores (buscar en tablas o listas de cargos)
    admin_section = re.search(
        r'(?:Administrador|Directivo|Cargo|Cargo\s+social)[^<]*</[^>]+>(.*?)(?=<h[23]|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    if admin_section:
        admin_text = admin_section.group(1)
        # Extraer nombres de administradores
        name_pattern = re.compile(
            r'([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})',
        )
        roles_seen = set()
        for m in name_pattern.finditer(_clean_text(admin_text)):
            name = m.group(1).strip()
            if len(name) > 5 and name not in roles_seen:
                roles_seen.add(name)
                result["admins"].append({"name": name, "role": "Desconocido"})

    # Año de constitución
    year_match = re.search(r'(?:Constituci[oó]n|Fundaci[oó]n|A[ñn]o)[:\s]+(\d{4})', html, re.IGNORECASE)
    if year_match:
        result["founded"] = year_match.group(1)

    return result


def search(query: str, max_results: int = 5) -> list[dict]:
    """Busca empresas en InfoEmpresa por nombre."""
    cache_key = f"search:{normalize_razon_social(query)}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    url = INFOEMPRESA_SEARCH.format(query=urllib.parse.quote(query))
    status, body = fetch_stealthy(url, timeout=20)

    if status != 200:
        SourceStatus.mark("InfoEmpresa", f"http-{status}")
        return []
    # Login-wall / página vacía: la web responde 200 pero sin contenido útil.
    if len(body) < _INFOEMPRESA_MIN_BODY:
        SourceStatus.mark("InfoEmpresa", "blocked")
        return []

    SourceStatus.mark("InfoEmpresa", "ok")

    # Extraer resultados de búsqueda (links a ficha de empresa).
    # Aceptamos tanto la ruta antigua /empresa/es/ como la nueva /es-es/es/empresa/
    # para no romper si la web vuelve a cambiar la estructura.
    link_pattern = re.compile(
        r'href="(/(?:es-es/es/)?empresa/[^"]+)"[^>]*>\s*<[^>]+>\s*([^<]+)</[^>]+>',
        re.IGNORECASE
    )
    seen_urls: set[str] = set()

    for m in link_pattern.finditer(body):
        path = m.group(1)
        nombre = _clean_text(m.group(2))

        if path in seen_urls:
            continue
        seen_urls.add(path)

        if not nombre or len(nombre) < 3:
            continue

        results.append({
            "razonSocial": nombre,
            "url": INFOEMPRESA_BASE + path,
            "slug": path.split("/")[-1],
        })

        if len(results) >= max_results:
            break

    cache_set(CACHE, cache_key, results)
    return results


def lookup(razon_social: Optional[str] = None, nif: Optional[str] = None) -> dict:
    """
    Busca datos de empresa en InfoEmpresa.es.

    Args:
        razon_social: Nombre de la empresa
        nif: NIF/CIF de la empresa

    Returns:
        dict con datos de empresa o {"error": "..."} si no se encuentra
    """
    if not razon_social and not nif:
        return {"error": "Se requiere razon_social o nif"}

    cache_key = f"lookup:{normalize_razon_social(razon_social or '')}:{nif or ''}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    # Intentar búsqueda por NIF primero (más preciso)
    if nif:
        nif_upper = nif.strip().upper()
        url = INFOEMPRESA_NIF.format(nif=nif_upper)
        status, body = fetch_stealthy(url, timeout=20)
        if status == 200 and len(body) > _INFOEMPRESA_MIN_BODY:
            result = _parse_company_page(body, url)
            if result.get("razonSocial") or result.get("nif"):
                SourceStatus.mark("InfoEmpresa", "ok")
                cache_set(CACHE, cache_key, result)
                emit_observation("tool_lead_recon", {"phase": "infoempresa.lookup", "nif": nif, "found": True})
                return result
        elif status == 200:
            # 200 con body minúsculo => login-wall o bloqueo.
            SourceStatus.mark("InfoEmpresa", "blocked")

    # Búsqueda por razón social
    if razon_social:
        search_results = search(razon_social)
        if not search_results:
            # Intentar con slug directo
            slug = _slugify(razon_social)
            if slug:
                url = INFOEMPRESA_COMPANY.format(slug=slug)
                status, body = fetch_stealthy(url, timeout=20)
                if status == 200 and len(body) > 500:
                    result = _parse_company_page(body, url)
                    if result.get("razonSocial"):
                        cache_set(CACHE, cache_key, result)
                        return result

            result = {"error": "not-found", "razonSocial": razon_social}
            cache_set(CACHE, cache_key, result)
            return result

        # Tomar el primer resultado y hacer lookup completo
        first = search_results[0]
        url = first["url"]
        status, body = fetch_stealthy(url, timeout=20)
        if status == 200:
            result = _parse_company_page(body, url)
            SourceStatus.mark("InfoEmpresa", "ok")
            emit_observation("tool_lead_recon", {
                "phase": "infoempresa.lookup",
                "razon_social": razon_social,
                "found": bool(result.get("razonSocial")),
            })
            cache_set(CACHE, cache_key, result)
            return result

    result = {"error": "not-found"}
    cache_set(CACHE, cache_key, result)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="InfoEmpresa scraper — LeadHunter Pro")
    p.add_argument("--razon-social", dest="razon_social")
    p.add_argument("--nif")
    p.add_argument("--search", help="Buscar por nombre (retorna lista)")
    args = p.parse_args()

    if args.search:
        results = search(args.search)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.razon_social or args.nif:
        result = lookup(razon_social=args.razon_social, nif=args.nif)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
