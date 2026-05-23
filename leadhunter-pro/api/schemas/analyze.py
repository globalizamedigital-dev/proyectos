"""Request / response del endpoint POST /analyze."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.common import SCHEMA_VERSION, DecisionMaker


class AnalyzeRequest(BaseModel):
    input: str = Field(..., min_length=3, description="NIF o razón social")
    premium: bool = Field(False, description="Activar fuentes de pago (sin uso en MVP)")
    user_claims: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Afirmaciones del operador sobre la empresa "
            "(p.ej. {'is_customer': True}). Si no se respaldan por las "
            "fuentes públicas, la respuesta incluye `assertion_mismatch`."
        ),
    )


class AssertionMismatch(BaseModel):
    claim: str
    expected: Any
    found: Any
    source: str
    note: str | None = None


class AnalyzeResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    input: dict[str, Any]
    summary: dict[str, Any]
    registral_timeline: list[dict[str, Any]] = Field(default_factory=list, alias="registralTimeline")
    decision_makers: list[DecisionMaker] = Field(default_factory=list, alias="decisionMakers")
    emails: list[dict[str, Any]] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    web: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    public_sector: dict[str, Any] = Field(default_factory=dict, alias="publicSector")
    warnings: list[str] = Field(default_factory=list)
    assertion_mismatches: list[AssertionMismatch] = Field(default_factory=list)
