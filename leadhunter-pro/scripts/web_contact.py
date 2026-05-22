"""
web_contact.py — Scraping de datos de contacto de sitios web de empresa.

Estrategia:
    - Prueba paths: /, /contacto, /contactanos, /contact, /about, /nosotros, /equipo, etc.
    - Extrae: emails (regex), teléfonos (regex español), nombres+roles de páginas de equipo
    - Respeta robots.txt (comprobación básica)
    - Sin dependencias externas (solo urllib + re)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CacheConfig, SourceStatus, cache_get, cache_set, http_get

CACHE = CacheConfig(namespace="web-contact", ttl_seconds=60 * 60 * 24 * 3)

# Paths a intentar
CONTACT_PATHS = [
    "/",
    "/contacto",
    "/contactanos",
    "/contactar",
    "/contact",
    "/contact-us",
    "/nosotros",
    "/sobre-nosotros",
    "/quienes-somos",
    "/about",
    "/about-us",
    "/equipo",
    "/team",
    "/empresa",
    "/nuestra-empresa",
    "/quien-somos",
]

# Regex para emails (más estricto que el genérico)
EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,10}\b"
)

# Regex para teléfonos españoles
# Móviles: 6xx xxx xxx, 7xx xxx xxx
# Fijos: 9xx xxx xxx, 8xx xxx xxx
# Con prefijo internacional: +34 / 0034
PHONE_RE = re.compile(
    r"(?:\+34\s?|0034\s?)?(?:6[0-9]{2}|7[0-9]{2}|8[0-9]{2}|9[0-9]{2})"
    r"[\s.\-]?[0-9]{3}[\s.\-]?[0-9]{3}"
)

# Dominios a filtrar de emails (genéricos, no de empresa)
EMAIL_BLACKLIST_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.es",
    "live.com", "live.es", "icloud.com", "me.com", "msn.com",
    "example.com", "test.com", "email.com",
}

# Indicadores de emails de empresa (señales positivas)
COMPANY_EMAIL_INDICATORS = [
    "info@", "contacto@", "admin@", "hola@", "hello@",
    "ventas@", "comercial@", "direccion@", "gerencia@",
]


def _check_robots(base_url: str, path: str) -> bool:
    """Comprueba robots.txt básicamente. Retorna True si está permitido."""
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base_url.rstrip("/") + "/robots.txt")
        rp.read()
        return rp.can_fetch("*", base_url.rstrip("/") + path)
    except Exception:
        return True  # Si falla la comprobación, asumir permitido


def _extract_emails(html: str, domain: str) -> list[dict]:
    """Extrae emails del HTML, clasificados por confianza."""
    emails_found: dict[str, dict] = {}

    # Eliminar scripts y CSS para evitar falsos positivos
    clean = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", " ", clean, flags=re.DOTALL | re.IGNORECASE)
    # Decodificar entidades HTML básicas
    clean = clean.replace("&#64;", "@").replace("&#46;", ".").replace("(at)", "@").replace("[at]", "@")
    clean = clean.replace(" at ", "@").replace("[dot]", ".").replace("(dot)", ".")

    for m in EMAIL_RE.finditer(clean):
        email = m.group(0).lower().strip(".,;:")
        if "@" not in email:
            continue
        parts = email.split("@")
        if len(parts) != 2:
            continue
        local, email_domain = parts

        # Filtrar obviamente inválidos
        if len(local) < 2 or len(email_domain) < 4:
            continue
        if email_domain in EMAIL_BLACKLIST_DOMAINS:
            continue

        # Clasificar confianza
        confidence = "low"
        if email_domain.rstrip("/").replace("www.", "") == domain.replace("www.", ""):
            confidence = "high"  # Email del mismo dominio
        elif any(email.startswith(ind) for ind in COMPANY_EMAIL_INDICATORS):
            confidence = "medium"

        if email not in emails_found:
            emails_found[email] = {
                "email": email,
                "domain": email_domain,
                "confidence": confidence,
                "via": "web_scrape",
            }

    # Ordenar: high primero
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(emails_found.values(), key=lambda x: order.get(x["confidence"], 9))


def _extract_phones(html: str) -> list[str]:
    """Extrae números de teléfono españoles del HTML."""
    clean = re.sub(r"<[^>]+>", " ", html)
    phones_found: set[str] = set()

    for m in PHONE_RE.finditer(clean):
        phone_raw = m.group(0)
        # Normalizar: quitar espacios, puntos, guiones internos
        phone = re.sub(r"[\s.\-]", "", phone_raw)
        # Asegurar formato válido (9 dígitos sin prefijo o 11/12 con +34)
        if phone.startswith("+34"):
            digits = phone[3:]
        elif phone.startswith("0034"):
            digits = phone[4:]
        else:
            digits = phone

        if len(digits) == 9 and digits[0] in "6789":
            phones_found.add(f"+34{digits}")

    # Filtrar teléfonos que parezcan fechas o códigos
    valid_phones = []
    for p in phones_found:
        digits = p.replace("+34", "")
        # Evitar secuencias muy repetitivas (111111111, etc.)
        if len(set(digits)) < 3:
            continue
        valid_phones.append(p)

    return sorted(valid_phones)


def _extract_address(html: str) -> Optional[str]:
    """Intenta extraer dirección postal del HTML."""
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = re.sub(r"\s+", " ", clean)

    # Patrón de dirección española: Calle X nº X, CP XXXXX Ciudad
    addr_patterns = [
        re.compile(r"(?:C/|Calle|Avda?\.?|Avenida|Plaza|Paseo|Pol\.?\s+Ind\.?)\s+[^,\n]{5,60},?\s*\d{5}\s+[A-Za-záéíóúñü]+", re.IGNORECASE),
        re.compile(r"\d{5}\s+[A-Za-záéíóúñü]{3,30}(?:\s*,\s*[A-Za-záéíóúñü]{3,30})?"),
    ]

    for pattern in addr_patterns:
        m = pattern.search(clean)
        if m:
            return m.group(0).strip()

    return None


def _extract_persons_from_team_page(html: str) -> list[dict]:
    """Extrae personas con roles de una página de equipo."""
    try:
        from person_finder import _extract_names_from_html
        return _extract_names_from_html(html, "")
    except ImportError:
        return []


def scrape_contact(domain: str) -> dict:
    """
    Scrapea la web de una empresa para extraer información de contacto.

    Args:
        domain: Dominio de la empresa (sin https://)

    Returns:
        dict con keys: emails, phones, persons, raw_address, pages_scraped
    """
    if not domain:
        return {"emails": [], "phones": [], "persons": [], "raw_address": None, "error": "no-domain"}

    cache_key = f"contact:{domain}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    # Normalizar dominio
    domain = domain.replace("http://", "").replace("https://", "").strip("/")
    base_url = f"https://{domain}"

    all_emails: dict[str, dict] = {}
    all_phones: set[str] = set()
    all_persons: list[dict] = []
    raw_address = None
    pages_scraped: list[str] = []
    errors: list[str] = []

    # Comprobar robots.txt una vez
    robots_checked = False

    for path in CONTACT_PATHS:
        url = base_url + path

        # Comprobar robots.txt (solo para paths no raíz)
        if not robots_checked and path != "/":
            robots_ok = _check_robots(base_url, path)
            robots_checked = True
            if not robots_ok:
                continue

        try:
            status, html = http_get(url, timeout=12)
        except Exception as e:
            errors.append(f"{url}: {e}")
            continue

        if status not in (200, 301, 302):
            continue

        if not html or len(html) < 100:
            continue

        pages_scraped.append(url)

        # Extraer emails
        for email_info in _extract_emails(html, domain):
            email = email_info["email"]
            # Si ya lo tenemos con mayor confianza, no sobreescribir
            if email not in all_emails or email_info.get("confidence") == "high":
                all_emails[email] = email_info

        # Extraer teléfonos
        phones = _extract_phones(html)
        all_phones.update(phones)

        # Extraer dirección (solo si no tenemos)
        if not raw_address:
            raw_address = _extract_address(html)

        # Extraer personas (solo en páginas de equipo/nosotros)
        if any(kw in path for kw in ["/equipo", "/team", "/nosotros", "/about", "/empresa"]):
            persons = _extract_persons_from_team_page(html)
            # Evitar duplicados
            existing_names = {p.get("name", "") for p in all_persons}
            for person in persons:
                if person.get("name") not in existing_names:
                    all_persons.append(person)
                    existing_names.add(person.get("name", ""))

    SourceStatus.mark("WebContact", "ok" if pages_scraped else "no-pages")

    # Ordenar emails por confianza
    order = {"high": 0, "medium": 1, "low": 2}
    sorted_emails = sorted(all_emails.values(), key=lambda x: order.get(x.get("confidence", "low"), 9))

    result = {
        "domain": domain,
        "emails": sorted_emails,
        "phones": sorted(all_phones),
        "persons": all_persons,
        "raw_address": raw_address,
        "pages_scraped": pages_scraped,
        "errors": errors[:5],
    }

    cache_set(CACHE, cache_key, result)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Web Contact Scraper — LeadHunter Pro")
    p.add_argument("--domain", required=True, help="Dominio de la empresa (sin https://)")
    args = p.parse_args()
    result = scrape_contact(args.domain)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
