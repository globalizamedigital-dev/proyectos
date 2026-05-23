"""
Shapes compartidos entre endpoints. SCHEMA_VERSION fija el contrato con
el frontend y con la GUI Tkinter que aún consume los snapshots locales.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Mantenemos la versión heredada de los snapshots existentes para no
# romper consumidores (GUI Tkinter, exports JSON antiguos).
SCHEMA_VERSION = "2.0.0"


Grade = Literal["A", "B", "C", "D"]
EmailConfidence = Literal["high", "medium", "low"]
SourceName = Literal[
    "BORME", "OSM", "Cartociudad", "PLACSP", "AEPD",
    "DDG", "InfoEmpresa", "WebContact", "DIRCE",
]
SourceState = Literal[
    "ok", "stub", "blocked", "captcha", "js-spa",
    "requires-cert", "endpoint-changed", "html-error-200", "not-atom",
]


class DecisionMaker(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None


class Lead(BaseModel):
    """Forma canónica de un lead. Espejo del row de Supabase + extras runtime."""

    model_config = ConfigDict(extra="allow")  # Tolerante con campos extra del scraper.

    razon_social: str = Field(..., alias="razonSocial")
    nif: str | None = None
    score: int = 0
    grade: Grade = "D"
    decisor: str | None = None
    decisor_role: str | None = None
    email: str | None = None
    email_confidence: EmailConfidence | None = None
    phone: str | None = None
    domain: str | None = None
    cnae: str | None = None
    sector: str | None = None
    provincia: str | None = None
    city: str | None = None
    sources: list[SourceName] = Field(default_factory=list, alias="sourcesHit")
    decision_makers: list[DecisionMaker] = Field(default_factory=list, alias="decisionMakers")


class SourceStatusEntry(BaseModel):
    source: SourceName | str
    state: SourceState | str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "down"]
    sources: list[SourceStatusEntry]
    schema_version: str = SCHEMA_VERSION
    api_version: str = "0.1.0"


class ErrorResponse(BaseModel):
    """Shape estable para errores; nunca devolvemos un 500 desnudo."""

    error: str
    detail: str | None = None
    trace_id: str | None = None
