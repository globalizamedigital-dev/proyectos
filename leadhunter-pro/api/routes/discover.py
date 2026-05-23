"""POST /discover · thin layer sobre scripts/discover.py."""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, status

from deps import AuthUser
from schemas.discover import DiscoverRequest, DiscoverResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discover", tags=["discover"])

# Pool dedicado para no bloquear el event loop con el scraping sync de scripts/.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="discover-")


@router.post("", response_model=DiscoverResponse, status_code=status.HTTP_200_OK)
async def post_discover(req: DiscoverRequest, user: AuthUser) -> DiscoverResponse:
    """
    Lanza un descubrimiento contra las fuentes públicas y devuelve los leads
    ya puntuados. El usuario debe estar autenticado (cualquier rol).
    """
    logger.info("discover: user=%s geo=%s sector=%s max=%d",
                user.id, req.geo, req.sector, req.max)

    try:
        from discover import discover as run_discover  # type: ignore[import-not-found]
    except ImportError as exc:
        logger.exception("scripts/discover.py no importable")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"discover engine missing: {exc}",
        ) from exc

    loop = asyncio.get_running_loop()
    try:
        payload = await loop.run_in_executor(
            _pool,
            lambda: run_discover(req.geo, req.sector, req.max, enrich=req.enrich),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("discover failed for geo=%s sector=%s", req.geo, req.sector)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"discover engine error: {type(exc).__name__}: {exc}",
        ) from exc

    return _coerce_response(payload)


def _coerce_response(payload: dict) -> DiscoverResponse:
    """Adapta el dict heredado de scripts/discover.py a la respuesta Pydantic."""
    sources_av = payload.get("sourcesAvailability", {}) or {}
    sources = [{"source": k, "state": v} for k, v in sources_av.items()]
    return DiscoverResponse.model_validate({
        "schema_version": payload.get("schemaVersion", "2.0.0"),
        "query": payload.get("query", {}),
        "candidates": payload.get("candidates", []) or [],
        "totalCandidates": payload.get("totalCandidates", 0),
        "totalUnresolvedDomain": payload.get("totalUnresolvedDomain", 0),
        "sourcesAvailability": sources,
        "leadsPersisted": payload.get("leadsPersisted", 0),
    })
