"""
Configura pytest para que `api/` sea importable como módulo root
(usamos imports absolutos: `from settings import ...`).
"""
import os
import sys
from pathlib import Path

# Inyecta `api/` y `scripts/` en sys.path para que los imports absolutos
# funcionen igual que en runtime.
_API = Path(__file__).resolve().parent.parent
_SCRIPTS = _API.parent / "scripts"
sys.path.insert(0, str(_API))
sys.path.insert(0, str(_SCRIPTS))

# Defaults para tests: env vars mínimas, dev auth bypass activo.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-srv")
os.environ.setdefault("SUPABASE_PROJECT_REF", "test")
os.environ.setdefault("ALLOW_DEV_AUTH_BYPASS", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")
