"""
analyze.py — orquestador del modo --analyze.

Recibe NIF o razón social. Cruza BORME (timeline) + Cartociudad + PLACSP +
Infosubvenciones + AEPD + InfoEmpresa + person_finder + email_finder +
web_contact + lead_scorer. Escribe JSON + HTML twin.

Mejoras sobre versión original:
    - InfoEmpresa para datos de empresa adicionales
    - person_finder para encontrar decisores
    - email_finder para emails directos
    - web_contact para scraping de contacto
    - lead_scorer para puntuación del lead
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    SourceStatus, emit_observation, is_valid_nif, normalize_nif,
    now_iso, today_dir, write_html_twin, write_snapshot,
)

import aepd
import borme
import cartociudad
import domain_resolver
import infosubvenciones
import placsp


def analyze(input_str: str, premium: bool = False) -> dict:
    """Pipeline principal de análisis."""
    nif: Optional[str] = None
    razon_social: Optional[str] = None
    if is_valid_nif(input_str):
        nif = normalize_nif(input_str)
    else:
        razon_social = input_str.strip()

    payload: dict[str, Any] = {
        "schemaVersion": "2.0.0",
        "app": "leadhunter-pro",
        "mode": "analyze",
        "premium": premium,
        "timestamp": now_iso(),
        "input": {"raw": input_str, "nif": nif, "razon_social": razon_social},
        "company": {},
        "registralTimeline": [],
        "admins_borme": [],
        "address": None,
        "publicSector": {"contracts": [], "subsidies": []},
        "compliance": {},
        "web": {},
        "infoempresa": {},
        "decisionMakers": [],
        "emails": [],
        "phones": [],
        "webContact": {},
        "score": {},
        "premiumData": None,
        "sourcesAvailability": {},
        "writes": {},
        "warnings": [],
    }

    if not nif:
        payload["warnings"].append(
            "Entrada es razón social (no NIF). El timeline BORME requiere NIF. "
            "Para completar, ejecuta --discover filtrando por la razón social y obtén el NIF correcto."
        )

    # --- Paralelo: BORME timeline + PLACSP + subvenciones + AEPD ---
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures: dict = {}
        if nif:
            futures[pool.submit(borme.analyze_by_nif, nif)] = "BORME"
            futures[pool.submit(placsp.by_nif, nif, 5)] = "PLACSP"
            futures[pool.submit(infosubvenciones.by_nif, nif)] = "Infosubvenciones"
            futures[pool.submit(aepd.lookup_dpo, nif, None)] = "AEPD"
        elif razon_social:
            futures[pool.submit(aepd.lookup_dpo, None, razon_social)] = "AEPD"

        # InfoEmpresa (por NIF o razón social)
        try:
            import infoempresa
            if nif:
                futures[pool.submit(infoempresa.lookup, None, nif)] = "InfoEmpresa"
            elif razon_social:
                futures[pool.submit(infoempresa.lookup, razon_social, None)] = "InfoEmpresa"
        except ImportError:
            pass

        for fut in as_completed(futures):
            src = futures[fut]
            try:
                result = fut.result()
            except Exception as e:  # noqa: BLE001
                emit_observation("source_unavailable", {"source": src, "error": str(e)})
                continue

            if src == "BORME":
                payload["registralTimeline"] = result.get("timeline", [])
                payload["admins_borme"] = result.get("admins", [])
                # Extraer razón social de BORME si no la teníamos
                if result.get("razonSocial") and not razon_social:
                    razon_social = result["razonSocial"]
                    payload["input"]["razon_social"] = razon_social
                if result.get("note"):
                    payload["warnings"].append(f"BORME: {result['note']}")
            elif src == "PLACSP":
                payload["publicSector"]["contracts"] = result or []
            elif src == "Infosubvenciones":
                payload["publicSector"]["subsidies"] = result or []
            elif src == "AEPD":
                payload["compliance"] = {
                    "dpoRegistered": result.get("registered", False),
                    "method": result.get("method"),
                    "signal": "alta-madurez-compliance" if result.get("registered") else "no-dpo-detected",
                }
            elif src == "InfoEmpresa":
                if not result.get("error"):
                    payload["infoempresa"] = result
                    # Complementar razón social si falta
                    if result.get("razonSocial") and not razon_social:
                        razon_social = result["razonSocial"]
                        payload["input"]["razon_social"] = razon_social
                    # Integrar admins de InfoEmpresa
                    for admin in result.get("admins", []):
                        if isinstance(admin, dict) and admin.get("name"):
                            payload["admins_borme"].append(admin.get("name"))

    # --- Resolución de dominio web ---
    rs_for_domain = razon_social or ""
    if rs_for_domain:
        domain_info = domain_resolver.resolve(rs_for_domain)
        payload["web"] = {
            "domain": domain_info.get("resolved"),
            "resolved_via": domain_info.get("via"),
            "confidence": domain_info.get("confidence"),
            "candidates": domain_info.get("candidates", [])[:5],
        }
        # También integrar web de InfoEmpresa si mejor
        if not domain_info.get("resolved") and payload["infoempresa"].get("website"):
            import urllib.parse
            ie_url = payload["infoempresa"]["website"]
            ie_domain = urllib.parse.urlparse(ie_url).netloc.replace("www.", "")
            if ie_domain:
                payload["web"]["domain"] = ie_domain
                payload["web"]["resolved_via"] = "infoempresa"
                payload["web"]["confidence"] = "high"

    # --- Enriquecimiento: personas + emails + web contact ---
    resolved_domain = payload["web"].get("domain")

    if rs_for_domain or resolved_domain:
        with ThreadPoolExecutor(max_workers=3) as pool:
            enrich_futures = {}

            try:
                from person_finder import find_decision_makers
                borme_raw_names = payload["admins_borme"]
                enrich_futures[pool.submit(
                    find_decision_makers, rs_for_domain, resolved_domain, borme_raw_names
                )] = "PersonFinder"
            except ImportError:
                pass

            if resolved_domain:
                try:
                    from web_contact import scrape_contact
                    enrich_futures[pool.submit(scrape_contact, resolved_domain)] = "WebContact"
                except ImportError:
                    pass

            for fut in as_completed(enrich_futures):
                src = enrich_futures[fut]
                try:
                    result = fut.result()
                except Exception:
                    continue

                if src == "PersonFinder":
                    payload["decisionMakers"] = result or []
                elif src == "WebContact":
                    payload["webContact"] = result or {}
                    # Integrar teléfonos
                    if isinstance(result, dict):
                        payload["phones"] = result.get("phones", [])
                        # Integrar emails de web
                        for email_info in result.get("emails", []):
                            payload["emails"].append(email_info)

        # Email finder (después de tener decisores)
        try:
            from email_finder import find_emails
            admin_names = [
                dm.get("name", "") for dm in payload["decisionMakers"]
                if isinstance(dm, dict) and dm.get("name")
            ]
            email_results = find_emails(rs_for_domain, resolved_domain, admin_names or None)
            existing = {e.get("email") for e in payload["emails"] if isinstance(e, dict)}
            for email in email_results:
                if email.get("email") not in existing:
                    payload["emails"].append(email)
                    existing.add(email.get("email"))
        except ImportError:
            pass

    # --- Geocodificación ---
    address = None
    if payload["infoempresa"].get("address"):
        address = payload["infoempresa"]["address"]
    if address:
        geo = cartociudad.geocode(address)
        if geo:
            payload["address"] = address
            payload["geocoded"] = geo

    # --- Scoring del lead ---
    try:
        from lead_scorer import score as score_lead
        lead_for_score = {
            "razonSocial": razon_social,
            "nif": nif,
            "domain": {"resolved": resolved_domain} if resolved_domain else None,
            "emails": payload["emails"],
            "phones": payload["phones"],
            "decisionMakers": payload["decisionMakers"],
            "compliance": payload["compliance"],
            "publicContracts": payload["publicSector"]["contracts"],
            "subsidies": payload["publicSector"]["subsidies"],
        }
        payload["score"] = score_lead(lead_for_score)
    except ImportError:
        pass

    # --- Premium slot ---
    if premium:
        payload["premiumData"] = {
            "source": "Registradores.org",
            "implemented": False,
            "note": (
                "Modo --premium reservado para integración con registradores.org. "
                "Coste estimado: nota simple ~€10, cuentas anuales ~€10."
            ),
            "estimatedCost": {"min": 10, "max": 30, "currency": "EUR"},
        }

    payload["sourcesAvailability"] = SourceStatus.snapshot()

    # --- Recomendación heurística ---
    qualified = []
    reason_parts = []
    if payload["compliance"].get("dpoRegistered"):
        qualified.append("formacion-eu-ai-act")
        reason_parts.append("DPO registrado")
    if payload["publicSector"]["subsidies"]:
        qualified.append("lidera-ia")
        reason_parts.append("ha recibido subvenciones")
    if payload["publicSector"]["contracts"]:
        qualified.append("auditoria-ia")
        reason_parts.append("contrata con sector público")
    if payload["emails"]:
        reason_parts.append(f"{len(payload['emails'])} email(s) encontrado(s)")
    if payload["decisionMakers"]:
        reason_parts.append(f"{len(payload['decisionMakers'])} decisor(es) identificado(s)")

    payload["recommendation"] = {
        "qualifiedFor": qualified,
        "reason": "; ".join(reason_parts) if reason_parts else "Datos insuficientes",
        "nextStep": _recommend_next_step(payload),
    }

    # --- Persistir ---
    snapshot_path = write_snapshot("analyze", payload)
    html_path = _render_html_twin(payload)
    payload["writes"] = {
        "snapshot": str(snapshot_path),
        "htmlTwin": str(html_path) if html_path else None,
    }

    emit_observation("tool_lead_recon", {
        "phase": "analyze.complete",
        "nif": nif,
        "premium": premium,
        "qualifiedFor": qualified,
        "score": payload.get("score", {}).get("score"),
        "emails_found": len(payload["emails"]),
        "decision_makers": len(payload["decisionMakers"]),
    })
    return payload


def _recommend_next_step(payload: dict) -> str:
    """Recomienda el siguiente paso según los datos disponibles."""
    if not payload["emails"] and not payload["web"].get("domain"):
        return "Resolver dominio web manualmente, luego re-analizar"
    if not payload["decisionMakers"]:
        return "Buscar decisor en LinkedIn antes de outreach"
    if payload["emails"]:
        email_verified = any(
            e.get("confidence") == "verified"
            for e in payload["emails"]
            if isinstance(e, dict)
        )
        if email_verified:
            return "Email verificado disponible — listo para outreach"
        return "Email encontrado (sin verificar SMTP) — intentar outreach"
    return "Completar datos antes de outreach"


def _render_html_twin(payload: dict) -> Optional[Path]:
    template_path = Path(__file__).resolve().parent.parent / "templates" / "analyze.html.jinja"
    if not template_path.exists():
        return None
    template = template_path.read_text(encoding="utf-8")
    rendered = template.replace("{{PAYLOAD_JSON}}", json.dumps(payload, ensure_ascii=False))
    title = payload["input"]["razon_social"] or payload["input"]["nif"] or "Análisis"
    rendered = rendered.replace("{{TITLE}}", f"Analyze: {title}")
    return write_html_twin("analyze", rendered)


def main() -> None:
    p = argparse.ArgumentParser(description="LeadHunter Pro — analyze orchestrator")
    p.add_argument("--input", required=True, help="NIF/CIF o razón social")
    p.add_argument("--premium", action="store_true")
    p.add_argument("--no-score", dest="no_score", action="store_true")
    args = p.parse_args()

    if args.premium:
        print("WARN: --premium activado. La integración con registradores.org NO está implementada aún.")

    payload = analyze(args.input, args.premium)
    print(json.dumps({
        "input": payload["input"],
        "score": payload.get("score"),
        "registralTimelineCount": len(payload["registralTimeline"]),
        "contractsCount": len(payload["publicSector"]["contracts"]),
        "subsidiesCount": len(payload["publicSector"]["subsidies"]),
        "compliance": payload["compliance"],
        "web": payload["web"],
        "decisionMakers": payload["decisionMakers"],
        "emailsFound": len(payload["emails"]),
        "emails": payload["emails"][:3],
        "phones": payload["phones"][:3],
        "recommendation": payload["recommendation"],
        "warnings": payload["warnings"],
        "writes": payload["writes"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
