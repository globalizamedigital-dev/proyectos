"""
person_finder.py — Encuentra decisores (CEOs, fundadores, directores, gerentes) de una empresa.

Estrategia:
    1. Parsear nombres de administradores del BORME raw (si disponible)
    2. DuckDuckGo: '"empresa X" "director" OR "CEO" OR "fundador" OR "gerente"'
    3. Scraping de páginas web de la empresa: /equipo, /nosotros, /empresa
    4. Retorna: [{name, role, linkedin_hint, source}]

Sin APIs externas — solo urllib + regex.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    CacheConfig, SourceStatus, cache_get, cache_set, emit_observation,
    http_get, normalize_razon_social,
)

CACHE = CacheConfig(namespace="person-finder", ttl_seconds=60 * 60 * 24 * 7)

# Roles de interés para B2B outreach
ROLES_INTERES = [
    "CEO", "Director General", "Director", "Directora", "Gerente",
    "Fundador", "Fundadora", "Co-fundador", "Co-fundadora",
    "Administrador", "Administradora", "Socio", "Socia",
    "Presidente", "Presidenta", "Responsable", "Jefe", "Jefa",
    "Manager", "Managing Director", "Owner", "Propietario", "Propietaria",
]

# Palabras clave para búsqueda DDG
DDG_KEYWORDS_ES = ["director", "CEO", "fundador", "gerente", "administrador", "responsable", "propietario"]
DDG_KEYWORDS_EN = ["CEO", "founder", "director", "manager", "owner"]

# Paths web donde suelen aparecer nombres de personas del equipo
TEAM_PATHS = [
    "/equipo", "/nosotros", "/empresa", "/sobre-nosotros", "/quienes-somos",
    "/about", "/team", "/about-us", "/quien-somos", "/nuestra-empresa",
    "/direccion", "/directivos", "/management",
]


def _extract_names_from_html(html: str, razon_social: str) -> list[dict]:
    """
    Extrae nombres y roles de una página HTML de empresa.
    Busca patrones de nombres seguidos de roles en tarjetas de equipo.
    """
    found = []
    if not html:
        return found

    # Limpiar HTML para análisis
    # Eliminar scripts y estilos
    clean = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", " ", clean, flags=re.DOTALL | re.IGNORECASE)

    # Buscar bloques de tarjetas de equipo (estructura típica)
    # Patrón 1: h3/h4 con nombre seguido de p/span con rol
    card_patterns = [
        re.compile(r'<(?:h[2-5]|strong)[^>]*>([A-ZÁÉÍÓÚÑÜ][a-záéíóúñüa-zA-Z\s]{4,35})</(?:h[2-5]|strong)>\s*(?:<[^>]+>)*\s*([^<]{5,60})', re.IGNORECASE),
        re.compile(r'class="[^"]*(?:name|nombre)[^"]*"[^>]*>([A-ZÁÉÍÓÚÑÜ][a-záéíóúñüa-zA-Z\s]{4,35})</[^>]+>', re.IGNORECASE),
        re.compile(r'<dt[^>]*>([A-ZÁÉÍÓÚÑÜ][a-záéíóúñüa-zA-Z\s]{4,35})</dt>\s*<dd[^>]*>([^<]{5,60})</dd>', re.IGNORECASE),
    ]

    for pattern in card_patterns:
        for m in pattern.finditer(clean):
            nombre = m.group(1).strip()
            rol = m.group(2).strip() if m.lastindex >= 2 else ""
            rol = re.sub(r"<[^>]+>", "", rol).strip()

            if not _looks_like_person_name(nombre):
                continue

            found.append({
                "name": nombre,
                "role": _classify_role(rol),
                "raw_role": rol[:100],
                "source": "web-team-page",
                "linkedin_hint": _guess_linkedin(nombre, razon_social),
            })

    # Patrón 2: buscar nombres + rol en texto libre
    # "Juan García López, Director General de..."
    free_text_pattern = re.compile(
        r'([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})'
        r'\s*,?\s*'
        r'(' + "|".join(re.escape(r) for r in ROLES_INTERES) + r')'
        r'(?:\s+(?:de|del|de la|en)\s+[^,.\n]{0,50})?',
        re.IGNORECASE
    )
    plain_text = re.sub(r"<[^>]+>", " ", clean)
    plain_text = re.sub(r"\s+", " ", plain_text)

    for m in free_text_pattern.finditer(plain_text):
        nombre = m.group(1).strip()
        rol = m.group(2).strip()
        if not _looks_like_person_name(nombre):
            continue
        found.append({
            "name": nombre,
            "role": _classify_role(rol),
            "raw_role": rol,
            "source": "web-free-text",
            "linkedin_hint": _guess_linkedin(nombre, razon_social),
        })

    # Deduplicar por nombre normalizado
    seen_names = set()
    deduped = []
    for p in found:
        norm = normalize_razon_social(p["name"])
        if norm not in seen_names:
            seen_names.add(norm)
            deduped.append(p)

    return deduped


def _looks_like_person_name(text: str) -> bool:
    """Verifica que el texto parezca un nombre de persona (no empresa, no frase)."""
    if not text or len(text) < 5 or len(text) > 60:
        return False
    # Debe tener al menos 2 palabras
    words = text.strip().split()
    if len(words) < 2:
        return False
    # No debe contener signos de puntuación extraños
    if re.search(r'[0-9@<>&\[\]{}|\\]', text):
        return False
    # Primera letra de cada palabra debe ser mayúscula o minúscula (no todo mayúsculas = empresa)
    if text == text.upper() and len(text) > 10:
        return False
    # No debe ser claramente un nombre de empresa
    company_indicators = ["s.l.", "s.a.", "ltda", "inc.", "corp.", "grupo", "servicios", "soluciones"]
    text_lower = text.lower()
    if any(ind in text_lower for ind in company_indicators):
        return False
    return True


def _classify_role(raw_role: str) -> str:
    """Clasifica un rol raw en categorías estándar."""
    if not raw_role:
        return "Desconocido"
    r = raw_role.lower()
    if any(k in r for k in ["ceo", "director general", "dirección general"]):
        return "CEO / Director General"
    if any(k in r for k in ["fundador", "founder", "co-fundador"]):
        return "Fundador"
    if any(k in r for k in ["director", "directora"]):
        return "Director/a"
    if any(k in r for k in ["gerente"]):
        return "Gerente"
    if any(k in r for k in ["administrador", "administradora"]):
        return "Administrador/a"
    if any(k in r for k in ["socio", "socia", "propietario", "propietaria", "owner"]):
        return "Socio/Propietario"
    if any(k in r for k in ["presidente", "presidenta"]):
        return "Presidente/a"
    return raw_role[:50]


def _guess_linkedin(nombre: str, empresa: str) -> Optional[str]:
    """Genera sugerencia de perfil LinkedIn."""
    import unicodedata
    slug = nombre.strip().lower()
    slug = "".join(c for c in unicodedata.normalize("NFKD", slug) if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    if slug:
        return f"https://www.linkedin.com/in/{slug}"
    return None


def find_from_borme_raw(borme_raw: list[str]) -> list[dict]:
    """Extrae decisores del raw BORME (lista de strings de actos)."""
    found = []
    for raw_text in (borme_raw or []):
        admins = _parse_admins_borme(raw_text)
        for admin in admins:
            found.append({
                "name": admin["name"],
                "role": admin["role"],
                "raw_role": admin.get("raw_role", ""),
                "source": "BORME",
                "linkedin_hint": _guess_linkedin(admin["name"], ""),
            })
    return found


def _parse_admins_borme(text: str) -> list[dict]:
    """Parsea administradores de texto BORME."""
    found = []
    # Patrones BORME típicos
    patterns = [
        (r"Administrador\s+[úu]nic[oa]:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Administrador único"),
        (r"Administrador[a]?:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Administrador"),
        (r"Gerente:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Gerente"),
        (r"Consejero\s+[Dd]elegado:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Consejero Delegado"),
        (r"Presidente[a]?:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Presidente"),
        (r"Director[a]?\s+[Gg]eneral:\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})", "Director General"),
    ]
    for pattern, role in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            nombre = m.group(1).strip()
            if _looks_like_person_name(nombre):
                found.append({"name": nombre, "role": role, "raw_role": role})
    return found


def find_from_ddg(razon_social: str, city: Optional[str] = None) -> list[dict]:
    """Busca decisores mediante DuckDuckGo."""
    try:
        from ddg import search as ddg_search
    except ImportError:
        return []

    found = []
    # Construcción de query orientada a encontrar personas
    keywords = " OR ".join(f'"{k}"' for k in DDG_KEYWORDS_ES[:4])
    query = f'"{razon_social}" ({keywords})'
    if city:
        query += f" {city}"

    try:
        results = ddg_search(query, max_results=5)
    except Exception:
        return []

    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("snippet", "") or ""

        # Extraer nombres del título y snippet
        combined = f"{title} {snippet}"
        names = _extract_person_names_from_text(combined)

        for name_info in names:
            # Intentar determinar si hay LinkedIn
            linkedin = None
            if "linkedin.com/in/" in url:
                linkedin = url

            found.append({
                "name": name_info["name"],
                "role": name_info.get("role", "Desconocido"),
                "source": "DDG",
                "url": url,
                "linkedin_hint": linkedin or _guess_linkedin(name_info["name"], razon_social),
            })

    return found


def _extract_person_names_from_text(text: str) -> list[dict]:
    """Extrae posibles nombres de personas y sus roles de un texto libre."""
    found = []
    # Patrón: Nombre seguido de rol
    for rol in ROLES_INTERES:
        pattern = re.compile(
            rf'([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+(?:de\s+la?|del?\s+)?[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){{1,3}})'
            rf'\s*[,–-]?\s*{re.escape(rol)}',
            re.IGNORECASE
        )
        for m in pattern.finditer(text):
            nombre = m.group(1).strip()
            if _looks_like_person_name(nombre):
                found.append({"name": nombre, "role": _classify_role(rol)})

    # Patrón inverso: Rol seguido de Nombre
    for rol in ROLES_INTERES:
        pattern = re.compile(
            rf'{re.escape(rol)}\s*[,:]?\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){{1,3}})',
            re.IGNORECASE
        )
        for m in pattern.finditer(text):
            nombre = m.group(1).strip()
            if _looks_like_person_name(nombre):
                found.append({"name": nombre, "role": _classify_role(rol)})

    return found


def find_from_website(domain: str, razon_social: str) -> list[dict]:
    """Scrapea la web de la empresa buscando nombres del equipo."""
    if not domain:
        return []

    # Normalizar dominio
    if not domain.startswith("http"):
        base = f"https://{domain}"
    else:
        base = domain.rstrip("/")

    found = []
    for path in TEAM_PATHS:
        url = base + path
        try:
            status, body = http_get(url, timeout=10)
            if status != 200:
                continue
            persons = _extract_names_from_html(body, razon_social)
            for p in persons:
                p["url"] = url
            found.extend(persons)
            if found:
                break  # Con una página con resultados es suficiente
        except Exception:
            continue

    return found


def find_decision_makers(
    razon_social: str,
    domain: Optional[str] = None,
    borme_raw: Optional[list[str]] = None,
    city: Optional[str] = None,
) -> list[dict]:
    """
    Encuentra decisores de una empresa combinando múltiples fuentes.

    Returns:
        list[dict]: [{name, role, source, linkedin_hint}]
    """
    cache_key = f"dm:{normalize_razon_social(razon_social)}:{domain or ''}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    all_found: list[dict] = []

    # 1. BORME raw (fuente más fiable)
    if borme_raw:
        borme_results = find_from_borme_raw(borme_raw)
        all_found.extend(borme_results)

    # 2. Web de la empresa
    if domain:
        web_results = find_from_website(domain, razon_social)
        all_found.extend(web_results)

    # 3. DuckDuckGo (si no tenemos suficientes resultados)
    if len(all_found) < 2:
        ddg_results = find_from_ddg(razon_social, city)
        all_found.extend(ddg_results)

    # Deduplicar por nombre normalizado
    seen_names: set[str] = set()
    deduped: list[dict] = []
    for dm in all_found:
        norm_name = normalize_razon_social(dm.get("name", ""))
        if norm_name and norm_name not in seen_names:
            seen_names.add(norm_name)
            deduped.append(dm)

    # Ordenar: BORME primero, luego web, luego DDG
    source_order = {"BORME": 0, "web-team-page": 1, "web-free-text": 2, "DDG": 3}
    deduped.sort(key=lambda x: source_order.get(x.get("source", ""), 99))

    emit_observation("tool_lead_recon", {
        "phase": "person_finder",
        "razon_social": razon_social,
        "count": len(deduped),
    })

    cache_set(CACHE, cache_key, deduped)
    return deduped


def main() -> None:
    p = argparse.ArgumentParser(description="Person Finder — LeadHunter Pro")
    p.add_argument("--razon-social", dest="razon_social", required=True)
    p.add_argument("--domain")
    p.add_argument("--city")
    args = p.parse_args()
    result = find_decision_makers(args.razon_social, args.domain, city=args.city)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
