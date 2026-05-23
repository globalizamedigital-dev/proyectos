"""Request / response del endpoint POST /discover."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.common import SCHEMA_VERSION, Lead, SourceStatusEntry


class DiscoverRequest(BaseModel):
    geo: str = Field(..., min_length=2, description="Provincia española")
    sector: str = Field(..., min_length=2, description="Texto libre o CNAE 4 dígitos")
    max: int = Field(25, ge=5, le=100, description="Máx. de candidatos a devolver")
    enrich: bool = Field(True, description="Resolver dominio + scrapear web + permutar emails")


class DiscoverResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    query: dict[str, Any]
    candidates: list[Lead]
    total_candidates: int = Field(0, alias="totalCandidates")
    total_unresolved_domain: int = Field(0, alias="totalUnresolvedDomain")
    sources_availability: list[SourceStatusEntry] = Field(
        default_factory=list, alias="sourcesAvailability"
    )
    leads_persisted: int = Field(0, alias="leadsPersisted")
