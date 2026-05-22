"""
osm.py — Overpass API (OpenStreetMap) para POI lookup por categoría + bounding box.

Endpoint público: https://overpass-api.de/api/interpreter
Rate-limit: ~1 req/sec, máx 25k entries por query.

Mejora: Todas las 50 provincias españolas incluidas.

Uso:
    python osm.py --tag "office=tax_advisor" --province Sevilla
    python osm.py --tag "office=consulting" --bbox 37.0,-6.0,37.5,-5.5
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CacheConfig, SourceStatus, cache_get, cache_set, emit_observation, http_get

CACHE = CacheConfig(namespace="osm", ttl_seconds=60 * 60 * 24 * 7)
OVERPASS_URL = "https://overpass-api.de/api/interpreter?data={query}"

# Bounding boxes aproximadas para las 50 provincias españolas.
# Formato: (sur, oeste, norte, este) WGS84
# Redondeadas para uso con Overpass. Para producción usar shapefile oficial del IGN.
PROVINCE_BBOX: dict[str, tuple[float, float, float, float]] = {
    # Andalucía
    "Almería": (36.7, -3.1, 37.7, -1.6),
    "Cádiz": (35.8, -6.5, 36.9, -5.1),
    "Córdoba": (37.2, -5.5, 38.7, -4.0),
    "Granada": (36.6, -4.2, 37.8, -2.8),
    "Huelva": (37.0, -7.6, 38.2, -6.2),
    "Jaén": (37.4, -4.2, 38.7, -2.5),
    "Málaga": (36.5, -5.5, 37.2, -3.9),
    "Sevilla": (36.9, -6.5, 38.0, -5.0),
    # Aragón
    "Huesca": (41.5, -1.0, 43.0, 0.7),
    "Teruel": (39.9, -1.9, 41.2, 0.5),
    "Zaragoza": (41.0, -2.0, 42.1, 0.1),
    # Asturias
    "Asturias": (42.9, -7.2, 43.7, -4.5),
    # Baleares
    "Baleares": (38.6, 1.1, 40.1, 4.4),
    # Canarias
    "Las Palmas": (27.6, -15.9, 29.5, -13.3),
    "Santa Cruz de Tenerife": (27.6, -18.2, 29.5, -13.4),
    # Cantabria
    "Cantabria": (42.8, -4.9, 43.5, -3.2),
    # Castilla-La Mancha
    "Albacete": (38.3, -2.7, 39.7, -0.8),
    "Ciudad Real": (38.3, -5.1, 39.5, -2.6),
    "Cuenca": (39.3, -2.8, 40.8, -1.0),
    "Guadalajara": (40.3, -3.2, 41.3, -1.2),
    "Toledo": (39.2, -5.6, 40.2, -2.8),
    # Castilla y León
    "Ávila": (40.1, -5.7, 41.0, -4.4),
    "Burgos": (41.5, -4.3, 43.1, -2.6),
    "León": (41.8, -7.0, 43.3, -4.7),
    "Palencia": (41.6, -4.9, 43.0, -3.6),
    "Salamanca": (40.1, -7.0, 41.2, -5.5),
    "Segovia": (40.6, -4.5, 41.4, -3.3),
    "Soria": (41.0, -3.2, 42.1, -1.7),
    "Valladolid": (41.1, -5.3, 41.8, -4.1),
    "Zamora": (40.9, -6.9, 42.2, -5.4),
    # Cataluña
    "Barcelona": (41.2, 1.3, 42.0, 2.5),
    "Gerona": (41.6, 2.2, 42.5, 3.4),
    "Lérida": (41.2, 0.3, 42.8, 1.8),
    "Tarragona": (40.6, 0.5, 41.4, 1.6),
    # Comunidad Valenciana
    "Alicante": (37.8, -1.1, 38.9, 0.5),
    "Castellón": (39.6, -0.7, 40.8, 0.6),
    "Valencia": (38.9, -1.5, 40.0, 0.5),
    # Extremadura
    "Badajoz": (38.1, -7.6, 39.6, -5.1),
    "Cáceres": (39.1, -7.2, 40.5, -5.0),
    # Galicia
    "La Coruña": (42.8, -9.3, 43.8, -7.4),
    "Lugo": (42.4, -7.8, 43.7, -6.6),
    "Orense": (41.8, -8.0, 42.7, -6.8),
    "Pontevedra": (41.8, -8.9, 42.6, -8.0),
    # La Rioja
    "La Rioja": (41.9, -3.2, 42.6, -1.7),
    # Madrid
    "Madrid": (39.9, -4.6, 41.2, -3.0),
    # Murcia
    "Murcia": (37.3, -2.4, 38.8, -0.6),
    # Navarra
    "Navarra": (41.9, -2.5, 43.3, -0.7),
    # País Vasco
    "Álava": (42.4, -3.1, 43.0, -2.2),
    "Guipúzcoa": (42.9, -2.5, 43.4, -1.7),
    "Bizkaia": (43.0, -3.4, 43.5, -2.4),
    # Aliases comunes
    "Bilbao": (43.1, -3.2, 43.5, -2.7),
    "San Sebastián": (42.9, -2.5, 43.4, -1.7),
    "Vitoria": (42.4, -3.1, 43.0, -2.2),
    # Ceuta y Melilla
    "Ceuta": (35.8, -5.4, 35.95, -5.2),
    "Melilla": (35.2, -3.0, 35.4, -2.8),
}

# Alias para nombres alternativos
PROVINCE_ALIASES = {
    "a coruna": "La Coruña",
    "la coruna": "La Coruña",
    "coruña": "La Coruña",
    "girona": "Gerona",
    "lleida": "Lérida",
    "tarragona": "Tarragona",
    "ourense": "Orense",
    "gipuzkoa": "Guipúzcoa",
    "bizkaia": "Bizkaia",
    "araba": "Álava",
    "illes balears": "Baleares",
    "islas baleares": "Baleares",
    "gran canaria": "Las Palmas",
    "tenerife": "Santa Cruz de Tenerife",
    "gijon": "Asturias",
    "oviedo": "Asturias",
    "santander": "Cantabria",
    "logrono": "La Rioja",
    "pamplona": "Navarra",
}


def resolve_province(name: str) -> Optional[str]:
    """Resuelve nombre de provincia incluyendo alias. Retorna clave exacta para PROVINCE_BBOX."""
    if not name:
        return None
    # Búsqueda exacta
    if name in PROVINCE_BBOX:
        return name
    # Normalizar y buscar
    norm = name.strip().lower()
    # Quitar diacríticos para búsqueda fuzzy
    import unicodedata
    norm_clean = "".join(c for c in unicodedata.normalize("NFKD", norm) if not unicodedata.combining(c))

    # Alias
    if norm_clean in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[norm_clean]

    # Comparación sin diacríticos
    for prov_key in PROVINCE_BBOX:
        prov_norm = "".join(c for c in unicodedata.normalize("NFKD", prov_key.lower()) if not unicodedata.combining(c))
        if prov_norm == norm_clean or norm_clean in prov_norm:
            return prov_key

    return None


def query_overpass(tag: str, bbox: tuple[float, float, float, float], timeout: int = 30) -> list[dict]:
    """
    tag: "office=tax_advisor" o "shop=*" — par de etiquetas Overpass.
    bbox: (sur, oeste, norte, este) WGS84.
    """
    cache_key = f"{tag}:{bbox}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    s, w, n, e = bbox
    if "=*" in tag:
        key = tag.split("=")[0]
        ql = f'[out:json][timeout:{timeout}];(node["{key}"]({s},{w},{n},{e});way["{key}"]({s},{w},{n},{e});relation["{key}"]({s},{w},{n},{e}););out center tags;'
    else:
        k, v = tag.split("=", 1)
        ql = f'[out:json][timeout:{timeout}];(node["{k}"="{v}"]({s},{w},{n},{e});way["{k}"="{v}"]({s},{w},{n},{e});relation["{k}"="{v}"]({s},{w},{n},{e}););out center tags;'

    url = OVERPASS_URL.format(query=urllib.parse.quote(ql))
    status, body = http_get(url, timeout=timeout + 5)
    if status != 200:
        SourceStatus.mark("OSM", f"http-{status}")
        emit_observation("source_unavailable", {"source": "OSM-Overpass", "status": status})
        return []

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        SourceStatus.mark("OSM", "parse-error")
        return []

    SourceStatus.mark("OSM", "ok")
    results: list[dict] = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        center = el.get("center") or {}
        lat = el.get("lat") or center.get("lat")
        lon = el.get("lon") or center.get("lon")
        if not (lat and lon):
            continue
        name = tags.get("name") or tags.get("brand")
        if not name:
            continue
        results.append({
            "razonSocial": name,
            "lat": lat,
            "lon": lon,
            "address": _build_address(tags),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website") or tags.get("contact:website"),
            "email": tags.get("email") or tags.get("contact:email"),
            "tags": tags,
            "source": "OSM",
        })
    cache_set(CACHE, cache_key, results)
    return results


def _build_address(tags: dict) -> Optional[str]:
    parts = []
    if tags.get("addr:street"):
        s = tags["addr:street"]
        if tags.get("addr:housenumber"):
            s += f" {tags['addr:housenumber']}"
        parts.append(s)
    if tags.get("addr:postcode"):
        parts.append(tags["addr:postcode"])
    if tags.get("addr:city"):
        parts.append(tags["addr:city"])
    return ", ".join(parts) if parts else None


def discover(tag: str, province: Optional[str] = None, bbox: Optional[str] = None) -> list[dict]:
    """Descubre POIs por etiqueta OSM en una provincia o bbox dada."""
    if bbox:
        s, w, n, e = [float(x) for x in bbox.split(",")]
        bb = (s, w, n, e)
    elif province:
        resolved = resolve_province(province)
        if resolved and resolved in PROVINCE_BBOX:
            bb = PROVINCE_BBOX[resolved]
        else:
            SourceStatus.mark("OSM", f"province-not-found:{province}")
            return []
    else:
        return []
    return query_overpass(tag, bb)


def main() -> None:
    p = argparse.ArgumentParser(description="OSM Overpass adapter — LeadHunter Pro")
    p.add_argument("--tag", required=True, help="Etiqueta Overpass, ej. office=tax_advisor")
    p.add_argument("--province", help="Nombre de provincia española")
    p.add_argument("--bbox", help="sur,oeste,norte,este")
    p.add_argument("--list-provinces", action="store_true", help="Listar todas las provincias disponibles")
    args = p.parse_args()

    if args.list_provinces:
        print(json.dumps(sorted(PROVINCE_BBOX.keys()), ensure_ascii=False, indent=2))
        return

    print(json.dumps(discover(args.tag, args.province, args.bbox), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
