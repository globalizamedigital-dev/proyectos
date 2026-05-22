"""
lead_scorer.py — Puntúa leads de 0 a 100 en base a completitud e indicadores de cualificación.

Sistema de puntuación:
    +20 si tiene web
    +25 si tiene email directo verificado
    +15 si tiene nombre de decisor
    +15 si tiene teléfono
    +10 si tiene DPO registrado (señal de madurez tech)
    +10 si tiene contratos públicos
    +5  si tiene subvenciones recibidas

Calcula también "iceberg_completeness" % y lista lo que falta.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_observation


# ---------------------------------------------------------------------------
# Definición de señales de scoring

SCORING_RULES = [
    {
        "id": "has_website",
        "label": "Tiene web",
        "points": 20,
        "description": "La empresa tiene dominio web resuelto",
    },
    {
        "id": "has_verified_email",
        "label": "Email verificado",
        "points": 25,
        "description": "Email directo del decisor, verificado via SMTP",
    },
    {
        "id": "has_email",
        "label": "Email encontrado",
        "points": 15,
        "description": "Email encontrado (sin verificación SMTP)",
    },
    {
        "id": "has_decision_maker",
        "label": "Tiene decisor",
        "points": 15,
        "description": "Nombre del CEO/director/gerente identificado",
    },
    {
        "id": "has_phone",
        "label": "Tiene teléfono",
        "points": 15,
        "description": "Número de teléfono disponible",
    },
    {
        "id": "dpo_registered",
        "label": "DPO registrado en AEPD",
        "points": 10,
        "description": "Señal de madurez en compliance — empresa tech-aware",
    },
    {
        "id": "has_public_contracts",
        "label": "Contrata con sector público",
        "points": 10,
        "description": "Ha adjudicado contratos públicos (PLACSP)",
    },
    {
        "id": "has_subsidies",
        "label": "Ha recibido subvenciones",
        "points": 5,
        "description": "Tiene subvenciones registradas (Infosubvenciones)",
    },
]

# Campos del "iceberg" de información del lead
ICEBERG_FIELDS = [
    ("razonSocial", "Razón social", True),          # (campo, label, requerido)
    ("nif", "NIF/CIF", False),
    ("domain", "Dominio web", True),
    ("emails", "Email contacto", True),
    ("phones", "Teléfono", False),
    ("decisionMakers", "Decisor / CEO", True),
    ("registralAddress", "Dirección", False),
    ("geocoded", "Geolocalización", False),
    ("cnae", "CNAE / Sector", False),
    ("lastBormeEvent", "Evento BORME", False),
    ("publicContracts", "Contratos públicos", False),
    ("subsidies", "Subvenciones", False),
    ("dpoRegistered", "DPO AEPD", False),
]


def _has_value(lead: dict, field: str) -> bool:
    """Comprueba si un campo del lead tiene valor no vacío."""
    val = lead.get(field)
    if val is None:
        return False
    if isinstance(val, (list, dict)) and not val:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, bool):
        return val
    # Campo anidado domain.resolved
    if field == "domain":
        if isinstance(val, dict):
            return bool(val.get("resolved"))
        return bool(val)
    return True


def _has_verified_email(lead: dict) -> bool:
    """Comprueba si hay al menos un email verificado por SMTP."""
    emails = lead.get("emails", [])
    for email_info in emails:
        if isinstance(email_info, dict):
            if email_info.get("confidence") == "verified" or email_info.get("smtp_verified"):
                return True
        elif isinstance(email_info, str):
            # Si es string, no podemos saber si está verificado
            pass
    return False


def _has_any_email(lead: dict) -> bool:
    """Comprueba si hay al menos un email."""
    emails = lead.get("emails", [])
    return bool(emails)


def _has_decision_maker(lead: dict) -> bool:
    """Comprueba si hay al menos un decisor identificado."""
    dms = lead.get("decisionMakers", [])
    return bool(dms)


def _has_phone(lead: dict) -> bool:
    """Comprueba si hay teléfono en cualquier campo."""
    if lead.get("phones"):
        return True
    web_contact = lead.get("webContact") or {}
    if isinstance(web_contact, dict) and web_contact.get("phones"):
        return True
    # Buscar en campos de OSM
    if lead.get("phone"):
        return True
    return False


def _is_dpo_registered(lead: dict) -> bool:
    """Comprueba si tiene DPO registrado en AEPD."""
    compliance = lead.get("compliance") or {}
    if isinstance(compliance, dict):
        return bool(compliance.get("dpoRegistered"))
    return bool(lead.get("dpoRegistered"))


def _has_public_contracts(lead: dict) -> bool:
    """Comprueba si tiene contratos públicos."""
    # Señal PLACSP
    signals = lead.get("signals") or {}
    if isinstance(signals, dict):
        if signals.get("publicContractsCount", 0) > 0:
            return True
    # Campo directo
    contracts = lead.get("publicContracts") or lead.get("contracts") or []
    return bool(contracts)


def _has_subsidies(lead: dict) -> bool:
    """Comprueba si ha recibido subvenciones."""
    signals = lead.get("signals") or {}
    if isinstance(signals, dict):
        subs = signals.get("subsidiesReceived")
        if subs:
            return True
    subsidies = lead.get("subsidies") or []
    return bool(subsidies)


def score(lead: dict) -> dict:
    """
    Puntúa un lead de 0 a 100.

    Args:
        lead: Diccionario con datos del lead

    Returns:
        dict: {
            "score": int (0-100),
            "iceberg_completeness": float (0.0-1.0),
            "missing": list[str],
            "signals": dict,
            "grade": "A|B|C|D",
            "breakdown": list[dict],
        }
    """
    total_score = 0
    signals: dict[str, Any] = {}
    breakdown: list[dict] = []

    # Evaluar cada regla de scoring
    for rule in SCORING_RULES:
        rule_id = rule["id"]
        points = rule["points"]
        earned = False

        if rule_id == "has_website":
            earned = _has_value(lead, "domain")
        elif rule_id == "has_verified_email":
            earned = _has_verified_email(lead)
            # Si hay email verificado, no aplicar también "has_email"
        elif rule_id == "has_email":
            # Solo si NO hay email verificado
            if not _has_verified_email(lead):
                earned = _has_any_email(lead)
            else:
                earned = False  # Ya puntuado por verified
                points = 0  # No sumar puntos dobles
        elif rule_id == "has_decision_maker":
            earned = _has_decision_maker(lead)
        elif rule_id == "has_phone":
            earned = _has_phone(lead)
        elif rule_id == "dpo_registered":
            earned = _is_dpo_registered(lead)
        elif rule_id == "has_public_contracts":
            earned = _has_public_contracts(lead)
        elif rule_id == "has_subsidies":
            earned = _has_subsidies(lead)

        if earned:
            total_score += points

        signals[rule_id] = earned
        breakdown.append({
            "id": rule_id,
            "label": rule["label"],
            "points": points if earned else 0,
            "max_points": rule["points"],
            "earned": earned,
        })

    # Calcular iceberg_completeness
    filled_required = 0
    total_required = 0
    filled_optional = 0
    total_optional = 0
    missing: list[str] = []

    for field, label, required in ICEBERG_FIELDS:
        has_it = _has_value(lead, field)

        if field == "emails":
            has_it = _has_any_email(lead)
        elif field == "decisionMakers":
            has_it = _has_decision_maker(lead)
        elif field == "phones":
            has_it = _has_phone(lead)
        elif field == "dpoRegistered":
            has_it = _is_dpo_registered(lead)
        elif field == "publicContracts":
            has_it = _has_public_contracts(lead)
        elif field == "subsidies":
            has_it = _has_subsidies(lead)

        if required:
            total_required += 1
            if has_it:
                filled_required += 1
            else:
                missing.append(label)
        else:
            total_optional += 1
            if has_it:
                filled_optional += 1
            else:
                missing.append(label)

    # Completitud: combina required (peso 70%) + optional (peso 30%)
    required_pct = filled_required / total_required if total_required > 0 else 0.0
    optional_pct = filled_optional / total_optional if total_optional > 0 else 0.0
    iceberg_completeness = (required_pct * 0.7) + (optional_pct * 0.3)

    # Cap en 100
    total_score = min(100, total_score)

    # Grado A-D
    if total_score >= 75:
        grade = "A"
    elif total_score >= 50:
        grade = "B"
    elif total_score >= 25:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": total_score,
        "grade": grade,
        "iceberg_completeness": round(iceberg_completeness, 3),
        "missing": missing,
        "signals": signals,
        "breakdown": breakdown,
    }


def score_batch(leads: list[dict]) -> list[dict]:
    """Puntúa una lista de leads y añade el score a cada uno."""
    result = []
    for lead in leads:
        lead_score = score(lead)
        enriched = {**lead, "score": lead_score}
        result.append(enriched)
    # Ordenar por score descendente
    result.sort(key=lambda x: x.get("score", {}).get("score", 0) if isinstance(x.get("score"), dict) else 0, reverse=True)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Lead Scorer — LeadHunter Pro")
    p.add_argument("--lead-json", dest="lead_json", help="JSON del lead como string")
    p.add_argument("--lead-file", dest="lead_file", help="Archivo JSON con datos del lead")
    args = p.parse_args()

    if args.lead_json:
        lead = json.loads(args.lead_json)
    elif args.lead_file:
        lead = json.loads(Path(args.lead_file).read_text(encoding="utf-8"))
    else:
        # Demo con lead de ejemplo
        lead = {
            "razonSocial": "Asesores Pérez S.L.",
            "domain": {"resolved": "asesoresperez.es"},
            "emails": [{"email": "info@asesoresperez.es", "confidence": "high"}],
            "decisionMakers": [{"name": "Juan Pérez García", "role": "Gerente"}],
            "phones": ["+34 912 345 678"],
            "compliance": {"dpoRegistered": True},
        }
        print("Demo con lead de ejemplo:")

    result = score(lead)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
