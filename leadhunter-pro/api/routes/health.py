"""
GET /health           → liveness y readiness rápidos (sin auth).
GET /health/sources   → estado de cada fuente externa según último uso.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from supabase import Client

from db import get_supabase
from schemas.common import HealthResponse, SourceStatusEntry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health(sb: Annotated[Client, Depends(get_supabase)]) -> HealthResponse:
    """Liveness + readiness. Comprueba que la BD responde."""
    db_ok = True
    try:
        sb.table("tenants").select("id").limit(1).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("health: db ping failed: %s", exc)
        db_ok = False

    sources = _read_source_status()
    overall = "ok" if db_ok and all(s.state == "ok" for s in sources) else "degraded"
    return HealthResponse(status=overall, db="ok" if db_ok else "down", sources=sources)


@router.get("/sources", response_model=list[SourceStatusEntry])
def health_sources() -> list[SourceStatusEntry]:
    """Snapshot del estado de cada fuente. Cero side-effects."""
    return _read_source_status()


def _read_source_status() -> list[SourceStatusEntry]:
    """Lee scripts._common.SourceStatus si está importado; si no, vacío."""
    try:
        from _common import SourceStatus  # type: ignore[import-not-found]
        snapshot = SourceStatus.snapshot()
        return [SourceStatusEntry(source=src, state=state) for src, state in snapshot.items()]
    except Exception:  # noqa: BLE001
        return []
