"""POST /analyze · thin layer sobre scripts/analyze.py."""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException, status

from deps import AuthUser
from schemas.analyze import AnalyzeRequest, AnalyzeResponse, AssertionMismatch

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analyze-")


@router.post("", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def post_analyze(req: AnalyzeRequest, user: AuthUser) -> AnalyzeResponse:
    """
    Análisis completo por NIF o razón social. Si `user_claims` viene
    informado, comprueba contradicciones contra las fuentes y las añade
    a `assertion_mismatches`.
    """
    logger.info("analyze: user=%s input=%s premium=%s",
                user.id, req.input, req.premium)

    try:
        from analyze import analyze as run_analyze  # type: ignore[import-not-found]
    except ImportError as exc:
        logger.exception("scripts/analyze.py no importable")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"analyze engine missing: {exc}",
        ) from exc

    loop = asyncio.get_running_loop()
    try:
        payload = await loop.run_in_executor(
            _pool,
            lambda: run_analyze(req.input, req.premium),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze failed for input=%s", req.input)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"analyze engine error: {type(exc).__name__}: {exc}",
        ) from exc

    mismatches = _check_claims(req.user_claims or {}, payload)
    response = _coerce_response(payload)
    response.assertion_mismatches = mismatches
    return response


def _coerce_response(payload: dict) -> AnalyzeResponse:
    return AnalyzeResponse.model_validate({
        "schema_version": payload.get("schemaVersion", "2.0.0"),
        "input": payload.get("input", {}),
        "summary": payload.get("summary", {}),
        "registralTimeline": payload.get("registralTimeline", []) or [],
        "decisionMakers": payload.get("decisionMakers", []) or [],
        "emails": payload.get("emails", []) or [],
        "phones": payload.get("phones", []) or [],
        "web": payload.get("web", {}) or {},
        "compliance": payload.get("compliance", {}) or {},
        "publicSector": payload.get("publicSector", {}) or {},
        "warnings": payload.get("warnings", []) or [],
    })


def _check_claims(claims: dict[str, Any], payload: dict[str, Any]) -> list[AssertionMismatch]:
    """
    Detecta inconsistencias entre lo que el operador afirma y lo que las
    fuentes públicas devuelven. MVP: solo cubre las claims más comunes;
    se amplía cuando Gemini esté wireado en Sprint 7.
    """
    out: list[AssertionMismatch] = []

    if claims.get("is_customer") is True:
        contracts = payload.get("publicSector", {}).get("contracts", []) or []
        if not contracts:
            out.append(AssertionMismatch(
                claim="is_customer",
                expected="al menos un contrato adjudicado en PLACSP",
                found="0 contratos en PLACSP",
                source="PLACSP",
                note="No es prueba concluyente; solo señal de baja actividad pública.",
            ))

    if claims.get("has_dpo") is True:
        compliance = payload.get("compliance", {})
        if compliance.get("dpoRegistered") is False:
            out.append(AssertionMismatch(
                claim="has_dpo",
                expected="DPO registrado en AEPD",
                found="No registrado según AEPD",
                source="AEPD",
            ))

    return out
