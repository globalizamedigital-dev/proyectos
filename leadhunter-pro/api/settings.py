"""
Configuración leída de variables de entorno con pydantic-settings.
Si una variable obligatoria falta, la app no arranca (fail-fast).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings globales del API. Cargadas desde env / .env del repo raíz."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ─────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_project_ref: str

    # ── Gemini / Vertex AI (opcional hasta Sprint 7) ─────────────────
    gcp_project_id: str = ""
    vertex_ai_location: str = "europe-west1"
    vertex_ai_model: str = "gemini-2.5-flash"
    google_application_credentials: str = ""

    # ── Operación ────────────────────────────────────────────────────
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    allow_dev_auth_bypass: bool = False  # Solo para tests locales.

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwks_url(self) -> str:
        """JWKS de Supabase Auth (ES256). Sirve para validar JWTs de usuarios."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    """Instancia única de Settings cacheada. Inyectable como dependencia FastAPI."""
    return Settings()
