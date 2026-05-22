"""
leadhunter-pro: utilities compartidas (cache, normalización, HTTP helper, observations).

Basado en norteia-lead-recon/_common.py — mejorado con helpers adicionales
para scoring de leads, manejo de nombres españoles y exportación de datos.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import logging.handlers
import os
import re
import sys
import threading
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import time


# ---------------------------------------------------------------------------
# Paths

HOME = Path.home()
SKILL_DIR = Path(__file__).resolve().parent.parent
CACHE_ROOT = HOME / ".cache" / "leadhunter-pro"
OBSERVATIONS_PATH = HOME / ".cache" / "leadhunter-pro" / "observations.jsonl"
DATA_DIR = HOME / ".cache" / "leadhunter-pro" / "data"
OPERATOR_STATE_PATH = HOME / ".cache" / "leadhunter-pro" / "state.json"


def today_dir() -> Path:
    """Returns the cache dir for today, creating it if needed."""
    d = CACHE_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%H%M%S")


# ---------------------------------------------------------------------------
# Cache

@dataclass
class CacheConfig:
    namespace: str
    ttl_seconds: Optional[int] = 60 * 60 * 24  # 24h default; None = forever


def _cache_key(namespace: str, key: str) -> Path:
    """Returns the cache file path for a given namespace+key."""
    safe = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    d = CACHE_ROOT / "_kv" / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def cache_get(cfg: CacheConfig, key: str) -> Optional[Any]:
    p = _cache_key(cfg.namespace, key)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if cfg.ttl_seconds is not None:
        age = time.time() - payload.get("_ts", 0)
        if age > cfg.ttl_seconds:
            return None
    return payload.get("value")


def cache_set(cfg: CacheConfig, key: str, value: Any) -> None:
    p = _cache_key(cfg.namespace, key)
    p.write_text(
        json.dumps({"_ts": time.time(), "_key": key, "value": value}, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# NIF / razón social normalization

_NIF_RE = re.compile(r"^[A-HJNPQRSUVW]\d{7}[0-9A-J]$|^\d{8}[A-Z]$|^[XYZ]\d{7}[A-Z]$", re.IGNORECASE)


def is_valid_nif(s: str) -> bool:
    """Loose validation for Spanish NIF/CIF/NIE formats. Doesn't validate check digit."""
    if not s:
        return False
    return bool(_NIF_RE.match(s.strip().upper()))


def normalize_nif(s: str) -> str:
    return (s or "").strip().upper().replace("-", "").replace(" ", "")


def normalize_razon_social(s: str) -> str:
    """Lowercase, remove diacritics, collapse whitespace, drop legal-form noise."""
    if not s:
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # Drop common legal forms for fuzzy matching
    for noise in [", s.l.", " s.l.", " sl", ", s.a.", " s.a.", " sa", " s.l.u.", " slu",
                  " s.coop.", " sccl", " scoop", ", c.b.", " cb", ", s.c.", " sc"]:
        if s.endswith(noise):
            s = s[: -len(noise)]
    s = re.sub(r"\s+", " ", s).strip()
    return s


def levenshtein(a: str, b: str) -> int:
    """Iterative Levenshtein. Used for fuzzy razón social dedup."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


# ---------------------------------------------------------------------------
# Nombre español utilities

def normalize_name(nombre: str) -> str:
    """Elimina diacríticos, pasa a minúsculas y elimina partículas."""
    if not nombre:
        return ""
    s = nombre.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # Eliminar partículas comunes
    for particula in [" de ", " del ", " de la ", " de los ", " de las "]:
        s = s.replace(particula, " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_nombre_partes(nombre_completo: str) -> dict:
    """
    Parsea un nombre completo español en partes.
    Asume formato: Nombre [Nombre2] Apellido1 [Apellido2]
    Retorna: {"nombre": str, "apellido1": str, "apellido2": str|None}
    """
    if not nombre_completo:
        return {"nombre": "", "apellido1": "", "apellido2": None}

    partes = normalize_name(nombre_completo).split()
    if len(partes) == 1:
        return {"nombre": partes[0], "apellido1": "", "apellido2": None}
    elif len(partes) == 2:
        return {"nombre": partes[0], "apellido1": partes[1], "apellido2": None}
    elif len(partes) == 3:
        return {"nombre": partes[0], "apellido1": partes[1], "apellido2": partes[2]}
    else:
        # 4+ partes: asumir 2 nombres + 2 apellidos
        return {"nombre": partes[0], "apellido1": partes[-2], "apellido2": partes[-1]}


def generar_permutaciones_email(nombre: str, apellido1: str, apellido2: Optional[str], dominio: str) -> list[str]:
    """
    Genera permutaciones de email para nombres españoles con 2 apellidos.
    Retorna lista de candidatos email ordenados por probabilidad.
    """
    if not dominio or not nombre:
        return []

    n = normalize_name(nombre).replace(" ", "")
    a1 = normalize_name(apellido1).replace(" ", "") if apellido1 else ""
    a2 = normalize_name(apellido2).replace(" ", "") if apellido2 else ""

    if not n:
        return []

    permutaciones = []

    # Con 2 apellidos (caso español más común)
    if a1 and a2:
        permutaciones.extend([
            f"{n}.{a1}.{a2}@{dominio}",   # jose.garcia.lopez
            f"{n}.{a1}@{dominio}",         # jose.garcia
            f"{n[0]}.{a1}.{a2}@{dominio}", # j.garcia.lopez
            f"{n[0]}.{a1}@{dominio}",      # j.garcia
            f"{n}{a1}@{dominio}",           # josegarcia
            f"{n}{a1}{a2}@{dominio}",       # josegarcialopez
            f"{n[0]}{a1}@{dominio}",        # jgarcia
            f"{n[0]}{a1}{a2}@{dominio}",    # jgarcialopez
            f"{a1}.{n}@{dominio}",          # garcia.jose
            f"{a1}{a2}@{dominio}",          # garcialopez
            f"{n}@{dominio}",               # jose
            f"{a1}@{dominio}",              # garcia
            f"info@{dominio}",              # generico
            f"contacto@{dominio}",          # generico
            f"admin@{dominio}",             # generico
        ])
    elif a1:
        permutaciones.extend([
            f"{n}.{a1}@{dominio}",
            f"{n[0]}.{a1}@{dominio}",
            f"{n}{a1}@{dominio}",
            f"{n[0]}{a1}@{dominio}",
            f"{a1}.{n}@{dominio}",
            f"{n}@{dominio}",
            f"{a1}@{dominio}",
            f"info@{dominio}",
            f"contacto@{dominio}",
            f"admin@{dominio}",
        ])
    else:
        permutaciones.extend([
            f"{n}@{dominio}",
            f"info@{dominio}",
            f"contacto@{dominio}",
            f"admin@{dominio}",
        ])

    # Deduplicar manteniendo orden
    seen: set[str] = set()
    result = []
    for p in permutaciones:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Structured logging

_LOG_PATH = HOME / ".cache" / "leadhunter-pro" / "leadhunter.log"
_loggers: dict[str, logging.Logger] = {}
_logger_lock = threading.Lock()


def get_logger(name: str = "leadhunter") -> logging.Logger:
    """
    Returns a configured logger that writes to both console and a rotating
    log file at HOME/.cache/leadhunter-pro/leadhunter.log (max 5MB, 3 backups).
    Idempotent: repeated calls with the same name reuse the same logger.
    """
    with _logger_lock:
        if name in _loggers:
            return _loggers[name]

        logger = logging.getLogger(f"leadhunter.{name}")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )

            # Console handler
            console = logging.StreamHandler()
            console.setFormatter(fmt)
            console.setLevel(logging.WARNING)
            logger.addHandler(console)

            # Rotating file handler
            try:
                _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.handlers.RotatingFileHandler(
                    str(_LOG_PATH), maxBytes=5 * 1024 * 1024, backupCount=3,
                    encoding="utf-8",
                )
                file_handler.setFormatter(fmt)
                file_handler.setLevel(logging.INFO)
                logger.addHandler(file_handler)
            except OSError:
                pass  # Log file unavailable — console only

        _loggers[name] = logger
        return logger


# ---------------------------------------------------------------------------
# Rate limiting (per-host throttle)

class RateLimiter:
    """
    Thread-safe per-host request throttle. Tracks the last request time per
    host and sleeps to enforce a minimum interval between requests.
    """
    _last_request: dict[str, float] = {}
    _lock = threading.Lock()

    @classmethod
    def wait(cls, host: str, min_interval_seconds: float = 1.0) -> None:
        """Blocks until at least `min_interval_seconds` have passed since the
        last request to `host`. Records the new request time."""
        if not host or min_interval_seconds <= 0:
            return
        with cls._lock:
            now = time.monotonic()
            last = cls._last_request.get(host, 0.0)
            elapsed = now - last
            sleep_for = min_interval_seconds - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
                cls._last_request[host] = time.monotonic()
            else:
                cls._last_request[host] = now

    @classmethod
    def reset(cls) -> None:
        """Clears all recorded request times. Mainly for tests."""
        with cls._lock:
            cls._last_request.clear()


# ---------------------------------------------------------------------------
# HTTP helper (no external deps, urllib only)

# Status codes that warrant a retry: connection failures + transient server errors
_RETRYABLE_STATUS = {0, -1, 429, 500, 502, 503, 504}


def http_get(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 15,
    retries: int = 3,
    rate_limit: float = 1.0,
) -> tuple[int, str]:
    """
    Returns (status_code, body_text). Never raises on HTTP errors.

    Args:
        url: URL to fetch.
        headers: optional extra headers.
        timeout: per-request timeout in seconds.
        retries: number of attempts on transient failures (0/-1/429/5xx).
                 Total attempts = retries (so retries=3 => up to 3 tries).
        rate_limit: minimum seconds between requests to the same host.
    """
    import urllib.request
    import urllib.error

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LeadHunterPro/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    if headers:
        default_headers.update(headers)

    try:
        host = urllib.parse.urlparse(url).netloc or url
    except Exception:  # noqa: BLE001
        host = url

    logger = get_logger("http")
    attempts = max(1, retries)
    status, body = -1, ""

    for attempt in range(attempts):
        # Per-host throttle before every request
        RateLimiter.wait(host, rate_limit)

        req = urllib.request.Request(url, headers=default_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, body = r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                body = ""
            status = e.code
        except urllib.error.URLError as e:
            status, body = 0, str(e)
        except Exception as e:  # noqa: BLE001
            status, body = -1, str(e)

        if status not in _RETRYABLE_STATUS:
            return status, body

        # Transient failure — back off exponentially (1s, 2s, 4s)
        if attempt < attempts - 1:
            backoff = 2 ** attempt
            logger.warning(
                "http_get %s -> status %s, retry %d/%d in %ds",
                url, status, attempt + 1, attempts - 1, backoff,
            )
            time.sleep(backoff)

    logger.error("http_get %s failed after %d attempts (last status %s)",
                 url, attempts, status)
    return status, body


def http_post(url: str, data: dict, headers: Optional[dict] = None, timeout: int = 15) -> tuple[int, str]:
    """POST JSON data, returns (status_code, body_text)."""
    import urllib.request
    import urllib.error
    import json as _json

    default_headers = {
        "User-Agent": "LeadHunterPro/1.0",
        "Content-Type": "application/json",
    }
    if headers:
        default_headers.update(headers)

    body_bytes = _json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers=default_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body
    except Exception as e:
        return -1, str(e)


# ---------------------------------------------------------------------------
# Observations

def emit_observation(obs_type: str, payload: dict) -> None:
    """Appends a JSONL line to observations file."""
    obs = {
        "ts": now_iso(),
        "type": obs_type,
        "app": "leadhunter-pro",
        "session": os.environ.get("LEADHUNTER_SESSION_ID", "local"),
        "payload": payload,
    }
    OBSERVATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OBSERVATIONS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obs, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CNAE mapping helpers

def load_cnae_mapping() -> dict:
    p = SKILL_DIR / "mappings" / "cnae.json"
    if not p.exists():
        return {"sectors": {}, "_provinceCodes": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_sector(input_str: str) -> dict:
    """
    Dado un sector libre ("asesoría fiscal" o "6920"), retorna:
        {"input": ..., "cnae": [...], "matched_via": "exact|alias|cnae|fuzzy|none", "label": "..."}
    """
    mapping = load_cnae_mapping()
    sectors = mapping.get("sectors", {})
    norm = (input_str or "").strip().lower()

    # 1) CNAE directo
    if re.fullmatch(r"\d{4}", norm):
        for label, data in sectors.items():
            if norm in data.get("cnae", []) or norm in data.get("alsoCheck", []):
                return {"input": input_str, "cnae": [norm], "matched_via": "cnae", "label": label}
        return {"input": input_str, "cnae": [norm], "matched_via": "cnae", "label": None}

    # 2) Match exacto
    if norm in sectors:
        data = sectors[norm]
        return {
            "input": input_str,
            "cnae": data["cnae"] + data.get("alsoCheck", []),
            "matched_via": "exact",
            "label": norm,
        }

    # 3) Alias
    for label, data in sectors.items():
        if norm in [a.lower() for a in data.get("aliases", [])]:
            return {
                "input": input_str,
                "cnae": data["cnae"] + data.get("alsoCheck", []),
                "matched_via": "alias",
                "label": label,
            }

    # 4) Fuzzy: substring o Levenshtein ≤ 3
    norm_clean = normalize_razon_social(norm)
    best = None
    best_dist = 4
    for label, data in sectors.items():
        candidates = [label] + data.get("aliases", [])
        for c in candidates:
            cn = normalize_razon_social(c)
            if not cn:
                continue
            d = levenshtein(norm_clean, cn)
            if d < best_dist:
                best_dist = d
                best = (label, data)
    if best:
        label, data = best
        return {
            "input": input_str,
            "cnae": data["cnae"] + data.get("alsoCheck", []),
            "matched_via": "fuzzy",
            "label": label,
        }

    return {"input": input_str, "cnae": [], "matched_via": "none", "label": None}


def province_code(name: str) -> Optional[str]:
    """Normaliza nombre de provincia española a código INE de 2 dígitos."""
    mapping = load_cnae_mapping().get("_provinceCodes", {})
    norm = normalize_razon_social(name or "")
    for k, v in mapping.items():
        if k.startswith("_"):
            continue
        if normalize_razon_social(k) == norm:
            return v
    return None


# ---------------------------------------------------------------------------
# Operator state read/write

def read_operator_state() -> dict:
    if not OPERATOR_STATE_PATH.exists():
        return {}
    try:
        return json.loads(OPERATOR_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def update_operator_state_section(section: str, value: Any) -> bool:
    """Fusiona `value` en la sección `section` del estado. Idempotente."""
    OPERATOR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = read_operator_state()
    state[section] = value
    state["lastUpdated"] = now_iso()
    OPERATOR_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


# ---------------------------------------------------------------------------
# Output helpers

def write_snapshot(mode: str, payload: dict) -> Path:
    """Escribe snapshot JSON en ~/.cache/leadhunter-pro/<today>/<mode>-<HHMMSS>.json"""
    out = today_dir() / f"{mode}-{now_compact()}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def write_html_twin(mode: str, html: str) -> Path:
    out = today_dir() / f"{mode}-{now_compact()}.html"
    out.write_text(html, encoding="utf-8")
    return out


def export_leads_csv(leads: list[dict], output_path: Optional[Path] = None) -> Path:
    """Exporta lista de leads a CSV."""
    if output_path is None:
        output_path = today_dir() / f"leads-{now_compact()}.csv"

    fields = ["razonSocial", "nif", "score", "domain", "email", "phone",
              "decisionMaker", "city", "cnae", "sources"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = {
                "razonSocial": lead.get("razonSocial", ""),
                "nif": lead.get("nif", ""),
                "score": lead.get("score", {}).get("score", "") if isinstance(lead.get("score"), dict) else lead.get("score", ""),
                "domain": lead.get("domain", {}).get("resolved", "") if isinstance(lead.get("domain"), dict) else lead.get("domain", ""),
                "email": _first_email(lead),
                "phone": _first_phone(lead),
                "decisionMaker": _first_decision_maker(lead),
                "city": lead.get("city", "") or (lead.get("geocoded") or {}).get("muni", ""),
                "cnae": lead.get("cnae", ""),
                "sources": ", ".join(lead.get("sourcesHit", []) or []),
            }
            writer.writerow(row)

    return output_path


def _first_email(lead: dict) -> str:
    emails = lead.get("emails", [])
    if emails and isinstance(emails[0], dict):
        return emails[0].get("email", "")
    elif emails:
        return str(emails[0])
    return ""


def _first_phone(lead: dict) -> str:
    phones = lead.get("phones", [])
    if phones:
        return str(phones[0])
    wc = lead.get("webContact", {})
    if wc and wc.get("phones"):
        return str(wc["phones"][0])
    return ""


def _first_decision_maker(lead: dict) -> str:
    dms = lead.get("decisionMakers", [])
    if dms and isinstance(dms[0], dict):
        return dms[0].get("name", "")
    elif dms:
        return str(dms[0])
    return ""


# ---------------------------------------------------------------------------
# Source availability registry

class SourceStatus:
    """Singleton-ish status tracker. Sources push their up/down status here."""
    _status: dict[str, str] = {}

    @classmethod
    def mark(cls, source: str, status: str) -> None:
        cls._status[source] = status

    @classmethod
    def snapshot(cls) -> dict[str, str]:
        return dict(cls._status)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None
    print("Skill dir:", SKILL_DIR)
    print("Cache root:", CACHE_ROOT)
    print("Today dir:", today_dir())
    print("NIF B12345678 valid?", is_valid_nif("B12345678"))
    print("Normalized 'Asesores Perez, S.L.':", normalize_razon_social("Asesores Perez, S.L."))
    print("Sector 'asesoria fiscal' ->", json.dumps(resolve_sector("asesoria fiscal"), ensure_ascii=True))
    print("Province 'Sevilla' ->", province_code("Sevilla"))
    partes = parse_nombre_partes("José García López")
    print("Nombre partes:", partes)
    emails = generar_permutaciones_email(partes["nombre"], partes["apellido1"], partes["apellido2"], "empresa.es")
    print("Permutaciones email:", emails[:5])
