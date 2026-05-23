"""
Dependencias FastAPI compartidas: auth (JWT contra JWKS Supabase) y
cliente Supabase con service_role.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from settings import Settings, get_settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Auth: valida el JWT de acceso emitido por Supabase Auth.
# Supabase 2.x firma con ES256 y publica la clave pública en JWKS.
# ─────────────────────────────────────────────────────────────────────

@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    """Cliente JWKS cacheado (claves rotan poco, lo refrescamos cada hora)."""
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


class CurrentUser:
    """Usuario autenticado extraído del JWT. Pasable como `user: CurrentUser`."""

    __slots__ = ("id", "email", "role", "claims")

    def __init__(self, claims: dict[str, Any]):
        self.id: str = claims["sub"]
        self.email: str | None = claims.get("email")
        self.role: str = claims.get("role", "authenticated")
        self.claims = claims

    def __repr__(self) -> str:  # pragma: no cover
        return f"CurrentUser(id={self.id}, email={self.email})"


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> CurrentUser:
    """
    Extrae y valida el Bearer token. Lanza 401 si no es válido.

    Para tests locales: si `ALLOW_DEV_AUTH_BYPASS=true` y el header
    `Authorization` empieza por `Dev `, el resto del header se trata
    como un user-id mock. NUNCA activar en producción.
    """
    if settings.allow_dev_auth_bypass and authorization and authorization.startswith("Dev "):
        user_id = authorization.removeprefix("Dev ").strip() or "dev-user"
        return CurrentUser(claims={"sub": user_id, "email": "dev@local", "role": "authenticated"})

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token requerido",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        signing_key = _jwks_client(settings.jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256"],
            audience="authenticated",
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado") from None
    except jwt.InvalidAudienceError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token con audience inválido") from None
    except (jwt.InvalidTokenError, httpx.HTTPError, Exception) as exc:  # noqa: BLE001
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from None

    return CurrentUser(claims)


# Alias cómodo: `user: AuthUser` en lugar de `user: CurrentUser = Depends(get_current_user)`.
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
