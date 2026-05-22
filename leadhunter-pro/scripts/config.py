"""
config.py — Carga de configuración desde variables de entorno y archivo .env.

Orden de búsqueda del archivo .env:
    1. Ruta indicada en la variable de entorno LEADHUNTER_ENV
    2. ./.env (directorio de trabajo actual)
    3. HOME/.leadhunter.env

La contraseña SMTP NUNCA se imprime ni se registra en logs. No se persiste en
ningún archivo JSON: vive solo en el .env (que debe estar en .gitignore).

Parser .env mínimo (sin dependencias externas):
    - Líneas KEY=VALUE
    - Ignora líneas en blanco y comentarios (#)
    - Elimina comillas simples/dobles alrededor del valor
    - Soporta el prefijo opcional "export "
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import HOME, SKILL_DIR, get_logger

_log = get_logger("config")

# Claves que se consideran sensibles y nunca deben mostrarse en claro
_SECRET_KEYS = {"SMTP_PASSWORD", "SMTP_PASS", "API_KEY", "SECRET"}

# Valores por defecto razonables
_DEFAULTS = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USE_TLS": "true",
    "SMTP_USE_SSL": "false",
    "SMTP_FROM_NAME": "LeadHunter Pro",
    "LEADHUNTER_MIN_SECONDS_BETWEEN_SENDS": "45",
    "LEADHUNTER_DAILY_CAP": "40",
}


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parser .env mínimo. Devuelve un dict KEY->VALUE."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        _log.warning("No se pudo leer %s: %s", path, e)
        return result

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Eliminar comillas envolventes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def _find_env_file() -> Optional[Path]:
    """Localiza el archivo .env según el orden de búsqueda definido."""
    candidates: list[Path] = []
    env_override = os.environ.get("LEADHUNTER_ENV")
    if env_override:
        candidates.append(Path(env_override).expanduser())
    candidates.append(Path.cwd() / ".env")
    candidates.append(SKILL_DIR / ".env")
    candidates.append(HOME / ".leadhunter.env")
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def get_env_path() -> Optional[Path]:
    """Devuelve la ruta del .env activo, o None si no se encuentra ninguno."""
    return _find_env_file()


def load_config() -> dict:
    """
    Carga toda la configuración combinando: valores por defecto < archivo .env
    < variables de entorno del sistema (estas tienen máxima prioridad).

    Returns:
        dict con todas las claves de configuración.
    """
    config: dict[str, str] = dict(_DEFAULTS)

    env_file = _find_env_file()
    if env_file:
        config.update(_parse_env_file(env_file))
        _log.info("Configuración cargada desde %s", env_file)
    else:
        _log.info("No se encontró archivo .env — usando entorno y valores por defecto")

    # Las variables de entorno del sistema tienen prioridad
    for key in list(config.keys()) + [
        "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_EMAIL",
        "LEADHUNTER_OUTPUT_DIR",
    ]:
        if key in os.environ:
            config[key] = os.environ[key]

    config["_env_file"] = str(env_file) if env_file else ""
    return config


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "si", "sí", "on")


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def get_smtp_config() -> dict:
    """
    Devuelve la configuración SMTP en el formato que espera outreach.send_email().

    Claves leídas: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM_EMAIL, SMTP_FROM_NAME, SMTP_USE_TLS, SMTP_USE_SSL.

    La contraseña se incluye en el dict pero NUNCA se registra en logs.
    """
    cfg = load_config()
    smtp_user = cfg.get("SMTP_USER", "")
    return {
        "smtp_host": cfg.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": _as_int(cfg.get("SMTP_PORT"), 587),
        "smtp_user": smtp_user,
        "smtp_password": cfg.get("SMTP_PASSWORD", ""),
        "from_email": cfg.get("SMTP_FROM_EMAIL") or smtp_user,
        "from_name": cfg.get("SMTP_FROM_NAME", "LeadHunter Pro"),
        "use_tls": _as_bool(cfg.get("SMTP_USE_TLS"), True),
        "use_ssl": _as_bool(cfg.get("SMTP_USE_SSL"), False),
    }


def smtp_config_status() -> dict:
    """
    Devuelve el estado de configuración de cada clave SMTP, SIN exponer la
    contraseña. Pensado para mostrar en la GUI ("configurado"/"no configurado").
    """
    cfg = load_config()
    keys = [
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL", "SMTP_FROM_NAME", "SMTP_USE_TLS", "SMTP_USE_SSL",
    ]
    status: dict[str, dict] = {}
    for k in keys:
        value = cfg.get(k, "")
        configured = bool(value)
        if k in _SECRET_KEYS:
            # Nunca mostrar el valor de un secreto
            display = "configurado" if configured else "no configurado"
        elif configured:
            display = str(value)
        else:
            display = "no configurado"
        status[k] = {"configured": configured, "display": display}
    return {
        "env_file": cfg.get("_env_file", ""),
        "env_found": bool(cfg.get("_env_file")),
        "keys": status,
    }


# ---------------------------------------------------------------------------
# CLI

def main() -> None:
    p = argparse.ArgumentParser(description="Configuración — LeadHunter Pro")
    p.add_argument("--status", action="store_true",
                   help="Mostrar estado de configuración (sin secretos)")
    args = p.parse_args()

    status = smtp_config_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
