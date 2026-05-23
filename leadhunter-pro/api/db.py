"""
Cliente Supabase compartido. Inicializado con `service_role` para que el
backend pueda escribir leads sin tropezarse con RLS (RLS sigue siendo la
defensa cuando el frontend usa la anon key).

Uso:
    from db import get_supabase

    @router.post("/discover")
    def post_discover(sb = Depends(get_supabase)): ...
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from settings import Settings, get_settings


@lru_cache
def _build_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    """
    Devuelve un cliente Supabase service_role. Singleton.

    Sin parámetros a propósito: si la firma incluyese `settings: Settings`,
    FastAPI inspeccionaría ese sub-parámetro al usar la función como
    dependency y trataría Settings (que extiende BaseModel) como un
    embed body, lo que rompe el parseo del body real de la ruta.
    """
    s = get_settings()
    return _build_client(s.supabase_url, s.supabase_service_role_key)
