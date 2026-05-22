"""
discover.py — orquestador del modo --discover.

Recibe geo + sector, lanza fuentes en paralelo, dedup + fuzzy match,
resuelve dominio, geocodifica, encuentra decisores, emails y web contact,
puntúa leads, escribe JSON + HTML twin.

Mejoras sobre la versión original:
    - person_finder.find_decision_makers()
    - email_finder.find_emails()
    - web_contact.scrape_contact()
    - lead_scorer.score()
    - Soporte para todas las 50 provincias españolas
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    SourceStatus, emit_observation, levenshtein, load_cnae_mapping, normalize_razon_social,
    now_iso, province_code, resolve_sector, today_dir, update_operator_state_section,
    write_html_twin, write_snapshot,
)

import borme
import dirce
import domain_resolver
import infosubvenciones
import osm
import placsp
import cartociudad


def _get_person_and_email(razon_social: str, domain_info: dict, borme_raw: list, city: str) -> dict:
    """Enriquecimiento de persona + email (ejecutado en thread separado)."""
    result = {"decisionMakers": [], "emails": [], "webContact": {}}

    resolved_domain = domain_info.get("resolved") if isinstance(domain_info, dict) else None

    try:
        from person_finder import find_decision_makers
        dms = find_decision_makers(razon_social, resolved_domain, borme_raw or None, city)
        result["decisionMakers"] = dms
    except Exception:
        pass

    try:
        from web_contact import scrape_contact
        if resolved_domain:
            wc = scrape_contact(resolved_domain)
            result["webContact"] = wc
            # Integrar emails de web contact
            for email_info in wc.get("emails", []):
                result["emails"].append(email_info)
    except Exception:
        pass

    try:
        from email_finder import find_emails
        admin_names = [dm.get("name", "") for dm in result["decisionMakers"] if isinstance(dm, dict)]
        emails = find_emails(razon_social, resolved_domain, admin_names or None, city)
        # Evitar duplicados
        existing = {e.get("email") for e in result["emails"]}
        for email in emails:
            if email.get("email") not in existing:
                result["emails"].append(email)
                existing.add(email.get("email"))
    except Exception:
        pass

    return result


def _provincial_bbox_for(province: str):
    return osm.PROVINCE_BBOX.get(province) or osm.PROVINCE_BBOX.get(
        osm.resolve_province(province) or ""
    )


def discover(geo: str, sector: str, max_results: int = 50, enrich: bool = True) -> dict:
    """Pipeline principal de descubrimiento. Retorna el payload completo (JSON-serializable)."""
    sector_resolution = resolve_sector(sector)
    cnae_codes = sector_resolution["cnae"]
    label = sector_resolution["label"] or sector
    province = geo

    payload: dict[str, Any] = {
        "schemaVersion": "2.0.0",
        "app": "leadhunter-pro",
        "mode": "discover",
        "timestamp": now_iso(),
        "query": {
            "geo": {"raw": geo, "province": province, "provinceCode": province_code(province)},
            "sector": {"input": sector, "cnae": cnae_codes, "matchedVia": sector_resolution["matched_via"], "label": label},
        },
        "segmentSize": dirce.segment_size(cnae_codes[0] if cnae_codes else "", province) if cnae_codes else None,
        "candidates": [],
        "totalCandidates": 0,
        "totalUnresolvedDomain": 0,
        "sourcesAvailability": {},
        "writes": {},
    }

    # --- Fase 1: descubrimiento paralelo ---
    raw_candidates: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(borme.discover_by_cnae_province, cnae_codes, province, 1): "BORME",
            pool.submit(placsp.discover, cnae_codes, province, 1): "PLACSP",
        }
        # OSM si tenemos bbox + tag conocido
        cnae_mapping = load_cnae_mapping()
        tag = cnae_mapping.get("verticalToOverpassTag", {}).get(label)
        if tag and _provincial_bbox_for(province):
            futures[pool.submit(osm.discover, tag, province, None)] = "OSM"

        for fut in as_completed(futures):
            src = futures[fut]
            try:
                items = fut.result() or []
            except Exception as e:  # noqa: BLE001
                emit_observation("source_unavailable", {"source": src, "error": str(e)})
                items = []
            for it in items:
                it["_source"] = src
                raw_candidates.append(it)

    # --- Fase 2: dedup + fuzzy ---
    deduped: list[dict] = []
    seen_keys: list[str] = []
    for c in raw_candidates:
        rs = c.get("razonSocial") or c.get("adjudicatario") or ""
        if not rs:
            continue
        key = normalize_razon_social(rs)
        is_dup = False
        for sk in seen_keys:
            if levenshtein(key, sk) <= 3:
                is_dup = True
                break
        if not is_dup:
            seen_keys.append(key)
            deduped.append(c)

    deduped = deduped[:max_results]

    # --- Fase 3: enriquecimiento por candidato ---
    enriched: list[dict] = []
    unresolved_domain = 0

    if enrich:
        # Enriquecimiento con domain + geo (en paralelo)
        def enrich_basic(cand):
            rs = cand.get("razonSocial") or cand.get("adjudicatario") or ""
            addr = cand.get("address") or cand.get("registralAddress")
            domain_info = domain_resolver.resolve(rs, city=province)
            geo_info = cartociudad.geocode(addr) if addr else None
            return cand, rs, addr, domain_info, geo_info

        with ThreadPoolExecutor(max_workers=6) as pool:
            basic_futures = [pool.submit(enrich_basic, c) for c in deduped]
            basic_results = [f.result() for f in basic_futures]

        for cand, rs, addr, domain_info, geo_info in basic_results:
            if not domain_info.get("resolved"):
                unresolved_domain += 1

            # Enriquecimiento avanzado (personas + emails + web)
            borme_raw = cand.get("_admins_raw", [])
            enrichment = _get_person_and_email(rs, domain_info, borme_raw, province)

            lead = {
                "razonSocial": rs,
                "nif": cand.get("nif"),
                "cnae": cnae_codes[0] if cnae_codes else None,
                "sector": label,
                "registralAddress": addr,
                "city": geo_info.get("muni") if geo_info else province,
                "geocoded": geo_info,
                "domain": domain_info,
                "decisionMakers": enrichment.get("decisionMakers", []),
                "emails": enrichment.get("emails", []),
                "phones": enrichment.get("webContact", {}).get("phones", []) if isinstance(enrichment.get("webContact"), dict) else [],
                "webContact": enrichment.get("webContact", {}),
                "lastBormeEvent": cand.get("lastBormeEvent"),
                "signals": {
                    "publicContractsCount": 1 if cand.get("_source") == "PLACSP" else 0,
                    "subsidiesReceived": None,
                    "dpoRegistered": None,
                },
                "sourcesHit": [cand.get("_source")],
                "_source_raw": cand.get("_source"),
            }

            # Scoring del lead
            try:
                from lead_scorer import score as score_lead
                lead["score"] = score_lead(lead)
            except Exception:
                lead["score"] = {"score": 0, "grade": "D", "iceberg_completeness": 0.0}

            enriched.append(lead)
    else:
        # Sin enriquecimiento avanzado
        for cand in deduped:
            rs = cand.get("razonSocial") or cand.get("adjudicatario") or ""
            addr = cand.get("address") or cand.get("registralAddress")
            domain_info = domain_resolver.resolve(rs, city=province)
            if not domain_info.get("resolved"):
                unresolved_domain += 1
            enriched.append({
                "razonSocial": rs,
                "nif": cand.get("nif"),
                "domain": domain_info,
                "registralAddress": addr,
                "sourcesHit": [cand.get("_source")],
                "score": {"score": 0, "grade": "D"},
            })

    # Ordenar por score si disponible
    enriched.sort(
        key=lambda x: (x.get("score") or {}).get("score", 0)
        if isinstance(x.get("score"), dict) else 0,
        reverse=True
    )

    payload["candidates"] = enriched
    payload["totalCandidates"] = len(enriched)
    payload["totalUnresolvedDomain"] = unresolved_domain
    payload["sourcesAvailability"] = SourceStatus.snapshot()

    # --- Fase 4: persistir ---
    snapshot_path = write_snapshot("discover", payload)
    html_path = _render_html_twin(payload)
    payload["writes"] = {
        "snapshot": str(snapshot_path),
        "htmlTwin": str(html_path) if html_path else None,
        "operatorState": "merged" if update_operator_state_section("leadHunterStats", {
            "lastRun": now_iso(),
            "lastMode": "discover",
            "lastQuery": payload["query"],
            "lastTotal": payload["totalCandidates"],
        }) else "skipped",
    }
    emit_observation("tool_lead_recon", {
        "phase": "discover.complete",
        "candidates": len(enriched),
        "unresolved_domains": unresolved_domain,
    })

    return payload


def _render_html_twin(payload: dict) -> Path | None:
    """Renderiza el HTML twin del discover con Leaflet."""
    template_path = Path(__file__).resolve().parent.parent / "templates" / "discover.html.jinja"
    if not template_path.exists():
        return None
    template = template_path.read_text(encoding="utf-8")
    rendered = template.replace("{{PAYLOAD_JSON}}", json.dumps(payload, ensure_ascii=False))
    rendered = rendered.replace("{{TITLE}}", f"Discover: {payload['query']['sector']['input']} en {payload['query']['geo']['raw']}")
    return write_html_twin("discover", rendered)


def main() -> None:
    p = argparse.ArgumentParser(description="LeadHunter Pro — discover orchestrator")
    p.add_argument("--geo", required=True, help="Provincia, municipio o CCAA")
    p.add_argument("--sector", required=True, help="CNAE o nombre de sector")
    p.add_argument("--max", type=int, default=50)
    p.add_argument("--no-enrich", dest="no_enrich", action="store_true",
                   help="Omitir enriquecimiento avanzado (más rápido)")
    args = p.parse_args()
    payload = discover(args.geo, args.sector, args.max, enrich=not args.no_enrich)
    print(json.dumps({
        "totalCandidates": payload["totalCandidates"],
        "totalUnresolvedDomain": payload["totalUnresolvedDomain"],
        "sourcesAvailability": payload["sourcesAvailability"],
        "writes": payload["writes"],
        "topPreview": [
            {
                "razonSocial": c.get("razonSocial"),
                "score": c.get("score", {}).get("score", 0) if isinstance(c.get("score"), dict) else 0,
                "domain": c.get("domain", {}).get("resolved") if isinstance(c.get("domain"), dict) else None,
                "emails": [e.get("email") for e in c.get("emails", [])[:2] if isinstance(e, dict)],
                "decisor": c.get("decisionMakers", [{}])[0].get("name") if c.get("decisionMakers") else None,
            }
            for c in payload["candidates"][:5]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
