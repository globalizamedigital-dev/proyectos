"""
suppression.py — Lista de supresión persistente (registro de opt-out).

Registro RGPD/LSSI-CE de bajas. Cualquier email, dominio o NIF presente en
esta lista NO debe recibir comunicaciones comerciales. La integración con
outreach.py garantiza que se comprueba SIEMPRE antes de enviar.

Base de datos SQLite en: HOME/.cache/leadhunter-pro/suppression.db

Tabla suppression(id, ts, email, domain, nif, reason, source) con índices
en email, domain y nif.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import HOME, get_logger, now_iso

DB_PATH = HOME / ".cache" / "leadhunter-pro" / "suppression.db"
_log = get_logger("suppression")


# ---------------------------------------------------------------------------
# Helpers de normalización

def _norm_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    e = email.strip().lower()
    return e or None


def _norm_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    d = domain.strip().lower()
    if d.startswith("http://") or d.startswith("https://"):
        d = d.split("//", 1)[1]
    if d.startswith("www."):
        d = d[4:]
    d = d.split("/", 1)[0]
    return d or None


def _norm_nif(nif: Optional[str]) -> Optional[str]:
    if not nif:
        return None
    n = nif.strip().upper().replace("-", "").replace(" ", "")
    return n or None


def _domain_of_email(email: Optional[str]) -> Optional[str]:
    e = _norm_email(email)
    if e and "@" in e:
        return _norm_domain(e.split("@", 1)[1])
    return None


# ---------------------------------------------------------------------------
# Base de datos

def _init_db() -> sqlite3.Connection:
    """Inicializa (idempotente) la base de datos de supresión."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suppression (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            email TEXT,
            domain TEXT,
            nif TEXT,
            reason TEXT DEFAULT 'opt-out',
            source TEXT DEFAULT 'manual'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_email ON suppression(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_domain ON suppression(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_nif ON suppression(nif)")
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# API pública

def add_suppression(
    email: Optional[str] = None,
    domain: Optional[str] = None,
    nif: Optional[str] = None,
    reason: str = "opt-out",
    source: str = "manual",
) -> int:
    """
    Añade una entrada a la lista de supresión. Idempotente: si ya existe una
    entrada con exactamente los mismos email/domain/nif, no la duplica.

    Returns:
        id de la entrada (nueva o existente). 0 si no se aportó ningún dato.
    """
    email = _norm_email(email)
    domain = _norm_domain(domain)
    nif = _norm_nif(nif)

    if not any([email, domain, nif]):
        _log.warning("add_suppression llamado sin email/domain/nif")
        return 0

    conn = _init_db()
    try:
        existing = conn.execute(
            """SELECT id FROM suppression
               WHERE IFNULL(email,'') = IFNULL(?,'')
                 AND IFNULL(domain,'') = IFNULL(?,'')
                 AND IFNULL(nif,'') = IFNULL(?,'')""",
            (email, domain, nif),
        ).fetchone()
        if existing:
            return existing["id"]

        cur = conn.execute(
            """INSERT INTO suppression (ts, email, domain, nif, reason, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now_iso(), email, domain, nif, reason, source),
        )
        conn.commit()
        _log.info("Supresión añadida: email=%s domain=%s nif=%s reason=%s",
                  email, domain, nif, reason)
        return cur.lastrowid
    finally:
        conn.close()


def is_suppressed(
    email: Optional[str] = None,
    domain: Optional[str] = None,
    nif: Optional[str] = None,
) -> bool:
    """
    Devuelve True si el email, el dominio del email, el dominio aportado o el
    NIF aparecen en la lista de supresión.
    """
    email = _norm_email(email)
    nif = _norm_nif(nif)
    # Comprueba el dominio aportado y, además, el dominio extraído del email
    domains: set[str] = set()
    d = _norm_domain(domain)
    if d:
        domains.add(d)
    de = _domain_of_email(email)
    if de:
        domains.add(de)

    if not email and not domains and not nif:
        return False

    conn = _init_db()
    try:
        if email:
            row = conn.execute(
                "SELECT 1 FROM suppression WHERE email = ? LIMIT 1", (email,)
            ).fetchone()
            if row:
                return True
        for dom in domains:
            row = conn.execute(
                "SELECT 1 FROM suppression WHERE domain = ? LIMIT 1", (dom,)
            ).fetchone()
            if row:
                return True
        if nif:
            row = conn.execute(
                "SELECT 1 FROM suppression WHERE nif = ? LIMIT 1", (nif,)
            ).fetchone()
            if row:
                return True
        return False
    finally:
        conn.close()


def remove_suppression(email: str) -> int:
    """
    Elimina todas las entradas de supresión asociadas a un email concreto.

    Returns:
        número de filas eliminadas.
    """
    email = _norm_email(email)
    if not email:
        return 0
    conn = _init_db()
    try:
        cur = conn.execute("DELETE FROM suppression WHERE email = ?", (email,))
        conn.commit()
        _log.info("Supresión eliminada para email=%s (%d filas)", email, cur.rowcount)
        return cur.rowcount
    finally:
        conn.close()


def list_suppressions() -> list[dict]:
    """Devuelve todas las entradas de la lista de supresión."""
    conn = _init_db()
    try:
        rows = conn.execute(
            "SELECT * FROM suppression ORDER BY ts DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_suppressions() -> int:
    """Número total de entradas en la lista de supresión."""
    conn = _init_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM suppression").fetchone()
        return int(row["n"]) if row else 0
    finally:
        conn.close()


def import_suppressions_csv(path: str | Path) -> int:
    """
    Importa entradas de supresión desde un CSV.
    Columnas reconocidas: email, domain, nif, reason, source (cabecera flexible).

    Returns:
        número de entradas importadas.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {path}")

    imported = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normaliza las claves de la cabecera a minúsculas
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            email = r.get("email") or None
            domain = r.get("domain") or None
            nif = r.get("nif") or r.get("cif") or None
            reason = r.get("reason") or "csv-import"
            source = r.get("source") or "csv-import"
            if any([email, domain, nif]):
                add_suppression(email=email, domain=domain, nif=nif,
                                reason=reason, source=source)
                imported += 1
    _log.info("Importadas %d entradas de supresión desde %s", imported, path)
    return imported


def export_suppressions_csv(path: str | Path) -> Path:
    """Exporta toda la lista de supresión a un CSV. Devuelve la ruta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list_suppressions()
    fields = ["id", "ts", "email", "domain", "nif", "reason", "source"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    _log.info("Exportadas %d entradas de supresión a %s", len(rows), path)
    return path


# ---------------------------------------------------------------------------
# CLI

def main() -> None:
    p = argparse.ArgumentParser(description="Lista de supresión — LeadHunter Pro")
    sub = p.add_subparsers(dest="action")

    p_add = sub.add_parser("add", help="Añadir entrada de supresión")
    p_add.add_argument("--email")
    p_add.add_argument("--domain")
    p_add.add_argument("--nif")
    p_add.add_argument("--reason", default="opt-out")
    p_add.add_argument("--source", default="manual")

    p_chk = sub.add_parser("check", help="Comprobar si está suprimido")
    p_chk.add_argument("--email")
    p_chk.add_argument("--domain")
    p_chk.add_argument("--nif")

    p_rm = sub.add_parser("remove", help="Eliminar email de la lista")
    p_rm.add_argument("--email", required=True)

    sub.add_parser("list", help="Listar todas las supresiones")

    p_imp = sub.add_parser("import", help="Importar CSV")
    p_imp.add_argument("--path", required=True)

    p_exp = sub.add_parser("export", help="Exportar CSV")
    p_exp.add_argument("--path", required=True)

    args = p.parse_args()

    if args.action == "add":
        new_id = add_suppression(email=args.email, domain=args.domain,
                                 nif=args.nif, reason=args.reason, source=args.source)
        print(json.dumps({"added_id": new_id}, ensure_ascii=False))
    elif args.action == "check":
        result = is_suppressed(email=args.email, domain=args.domain, nif=args.nif)
        print(json.dumps({"suppressed": result}, ensure_ascii=False))
    elif args.action == "remove":
        n = remove_suppression(args.email)
        print(json.dumps({"removed": n}, ensure_ascii=False))
    elif args.action == "list":
        print(json.dumps(list_suppressions(), ensure_ascii=False, indent=2))
    elif args.action == "import":
        n = import_suppressions_csv(args.path)
        print(json.dumps({"imported": n}, ensure_ascii=False))
    elif args.action == "export":
        out = export_suppressions_csv(args.path)
        print(json.dumps({"exported_to": str(out), "count": count_suppressions()},
                         ensure_ascii=False))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
