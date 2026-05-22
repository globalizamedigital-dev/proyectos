"""
leads_db.py — Base de datos de leads persistente (datastore de producción).

Hasta ahora los leads vivían solo en snapshots JSON dispersos. Este módulo
proporciona un almacén SQLite único con deduplicación entre ejecuciones.

Base de datos: HOME/.cache/leadhunter-pro/leads.db

Tabla leads(id, nif, razon_social, domain, score, email_principal, decisor,
telefono, provincia, sector, outreach_status, first_seen, last_seen, data TEXT).
El dict completo del lead se guarda como JSON en `data`; las columnas extraídas
sirven para consultas rápidas. Índices en nif, score, provincia, outreach_status.

Clave de deduplicación: NIF si existe, si no razón social normalizada + dominio.
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
from _common import HOME, get_logger, normalize_nif, normalize_razon_social, now_iso

DB_PATH = HOME / ".cache" / "leadhunter-pro" / "leads.db"
_log = get_logger("leads_db")


# ---------------------------------------------------------------------------
# Base de datos

def _init_db() -> sqlite3.Connection:
    """Inicializa (idempotente) la base de datos de leads."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            nif TEXT,
            razon_social TEXT,
            domain TEXT,
            score INTEGER DEFAULT 0,
            email_principal TEXT,
            decisor TEXT,
            telefono TEXT,
            provincia TEXT,
            sector TEXT,
            outreach_status TEXT DEFAULT 'new',
            first_seen TEXT,
            last_seen TEXT,
            data TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_nif ON leads(nif)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_provincia ON leads(provincia)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(outreach_status)")
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Extracción de campos del dict de lead

def _extract_domain(lead: dict) -> str:
    d = lead.get("domain")
    if isinstance(d, dict):
        return (d.get("resolved") or "").strip().lower()
    if isinstance(d, str):
        return d.strip().lower()
    # analyze.py guarda el dominio en web.domain
    web = lead.get("web")
    if isinstance(web, dict) and web.get("domain"):
        return str(web["domain"]).strip().lower()
    return ""


def _extract_score(lead: dict) -> int:
    s = lead.get("score")
    if isinstance(s, dict):
        try:
            return int(s.get("score", 0))
        except (ValueError, TypeError):
            return 0
    try:
        return int(s) if s is not None else 0
    except (ValueError, TypeError):
        return 0


def _extract_email(lead: dict) -> str:
    emails = lead.get("emails", [])
    for e in emails:
        if isinstance(e, dict) and e.get("email"):
            return str(e["email"]).strip().lower()
        if isinstance(e, str) and e:
            return e.strip().lower()
    return ""


def _extract_decisor(lead: dict) -> str:
    dms = lead.get("decisionMakers", [])
    for dm in dms:
        if isinstance(dm, dict) and dm.get("name"):
            return str(dm["name"])
        if isinstance(dm, str) and dm:
            return dm
    return ""


def _extract_phone(lead: dict) -> str:
    phones = lead.get("phones", [])
    if phones:
        return str(phones[0])
    wc = lead.get("webContact")
    if isinstance(wc, dict) and wc.get("phones"):
        return str(wc["phones"][0])
    return ""


def _extract_provincia(lead: dict) -> str:
    geo = lead.get("geocoded")
    if isinstance(geo, dict):
        prov = geo.get("provincia") or geo.get("province")
        if prov:
            return str(prov)
    return str(lead.get("provincia") or lead.get("city") or "")


def _extract_razon_social(lead: dict) -> str:
    rs = lead.get("razonSocial") or lead.get("razon_social")
    if not rs:
        inp = lead.get("input")
        if isinstance(inp, dict):
            rs = inp.get("razon_social")
    return str(rs or "")


def _dedup_key(nif: str, razon_social: str, domain: str) -> str:
    """Clave de deduplicación: NIF normalizado si existe, si no rs+dominio."""
    nif_n = normalize_nif(nif) if nif else ""
    if nif_n:
        return f"nif:{nif_n}"
    rs_n = normalize_razon_social(razon_social)
    return f"rs:{rs_n}|dom:{domain.lower()}"


# ---------------------------------------------------------------------------
# API pública

def upsert_lead(lead: dict) -> int:
    """
    Inserta o actualiza un lead. Deduplica por NIF (si existe) o por
    razón social normalizada + dominio.

    Returns:
        id del lead en la base de datos. 0 si el lead no tiene datos mínimos.
    """
    nif = str(lead.get("nif") or "")
    razon_social = _extract_razon_social(lead)
    domain = _extract_domain(lead)

    if not nif and not razon_social:
        _log.warning("upsert_lead omitido: lead sin NIF ni razón social")
        return 0

    dedup_key = _dedup_key(nif, razon_social, domain)
    score = _extract_score(lead)
    email = _extract_email(lead)
    decisor = _extract_decisor(lead)
    telefono = _extract_phone(lead)
    provincia = _extract_provincia(lead)
    sector = str(lead.get("sector") or lead.get("cnae") or "")
    now = now_iso()
    data_json = json.dumps(lead, ensure_ascii=False)

    conn = _init_db()
    try:
        try:
            existing = conn.execute(
                "SELECT id, first_seen, outreach_status FROM leads WHERE dedup_key = ?",
                (dedup_key,),
            ).fetchone()

            if existing:
                lead_id = existing["id"]
                first_seen = existing["first_seen"] or now
                # Conserva el estado de outreach existente
                outreach_status = existing["outreach_status"] or "new"
                conn.execute(
                    """UPDATE leads SET
                           nif=?, razon_social=?, domain=?, score=?, email_principal=?,
                           decisor=?, telefono=?, provincia=?, sector=?,
                           last_seen=?, data=?
                       WHERE id=?""",
                    (normalize_nif(nif) if nif else None, razon_social, domain, score,
                     email, decisor, telefono, provincia, sector, now, data_json, lead_id),
                )
                conn.commit()
                _log.info("Lead actualizado id=%d key=%s", lead_id, dedup_key)
                return lead_id
            else:
                cur = conn.execute(
                    """INSERT INTO leads
                           (dedup_key, nif, razon_social, domain, score, email_principal,
                            decisor, telefono, provincia, sector, outreach_status,
                            first_seen, last_seen, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (dedup_key, normalize_nif(nif) if nif else None, razon_social, domain,
                     score, email, decisor, telefono, provincia, sector, "new",
                     now, now, data_json),
                )
                conn.commit()
                _log.info("Lead insertado id=%d key=%s", cur.lastrowid, dedup_key)
                return cur.lastrowid
        except Exception:
            # Si algo revienta entre execute() y commit() dejamos la BD en
            # estado consistente. SQLite descartaría la transacción al cerrar
            # la conexión, pero rollback explícito es más predecible.
            try:
                conn.rollback()
            except Exception:
                pass
            raise
    finally:
        conn.close()


def upsert_leads(leads: list[dict]) -> int:
    """Upsert de una lista de leads. Devuelve cuántos se procesaron."""
    n = 0
    for lead in leads:
        if upsert_lead(lead):
            n += 1
    return n


def get_lead(nif: Optional[str] = None, razon_social: Optional[str] = None) -> Optional[dict]:
    """
    Obtiene un lead por NIF o por razón social. Devuelve el dict completo
    (deserializado desde la columna `data`) con `_db_id` y `_outreach_status`.
    """
    conn = _init_db()
    try:
        row = None
        if nif:
            row = conn.execute(
                "SELECT * FROM leads WHERE nif = ?", (normalize_nif(nif),)
            ).fetchone()
        if not row and razon_social:
            rs_n = normalize_razon_social(razon_social)
            rows = conn.execute("SELECT * FROM leads").fetchall()
            for r in rows:
                if normalize_razon_social(r["razon_social"] or "") == rs_n:
                    row = r
                    break
        if not row:
            return None
        return _row_to_lead(row)
    finally:
        conn.close()


def _row_to_lead(row: sqlite3.Row) -> dict:
    """Convierte una fila de la BD en un dict de lead enriquecido."""
    try:
        lead = json.loads(row["data"]) if row["data"] else {}
    except (json.JSONDecodeError, TypeError):
        lead = {}
    lead["_db_id"] = row["id"]
    lead["_outreach_status"] = row["outreach_status"]
    lead["_first_seen"] = row["first_seen"]
    lead["_last_seen"] = row["last_seen"]
    return lead


def query_leads(
    min_score: int = 0,
    provincia: Optional[str] = None,
    sector: Optional[str] = None,
    has_email: Optional[bool] = None,
    outreach_status: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """
    Consulta leads con filtros. Devuelve una lista de dicts de lead ordenada
    por score descendente.
    """
    conn = _init_db()
    try:
        clauses = ["score >= ?"]
        params: list = [min_score]
        if provincia:
            clauses.append("LOWER(provincia) LIKE ?")
            params.append(f"%{provincia.lower()}%")
        if sector:
            clauses.append("LOWER(sector) LIKE ?")
            params.append(f"%{sector.lower()}%")
        if outreach_status:
            clauses.append("outreach_status = ?")
            params.append(outreach_status)
        if has_email is True:
            clauses.append("email_principal IS NOT NULL AND email_principal != ''")
        elif has_email is False:
            clauses.append("(email_principal IS NULL OR email_principal = '')")

        sql = (
            "SELECT * FROM leads WHERE " + " AND ".join(clauses)
            + " ORDER BY score DESC LIMIT ?"
        )
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_lead(r) for r in rows]
    finally:
        conn.close()


def update_outreach_status(lead_id: int, status: str) -> bool:
    """Actualiza el estado de outreach de un lead. Devuelve True si se actualizó."""
    conn = _init_db()
    try:
        cur = conn.execute(
            "UPDATE leads SET outreach_status = ? WHERE id = ?",
            (status, lead_id),
        )
        conn.commit()
        if cur.rowcount:
            _log.info("Lead id=%d -> outreach_status=%s", lead_id, status)
        return cur.rowcount > 0
    finally:
        conn.close()


def count_leads() -> dict:
    """Devuelve totales: {total: int, by_status: {status: count}}."""
    conn = _init_db()
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        rows = conn.execute(
            "SELECT outreach_status, COUNT(*) AS n FROM leads GROUP BY outreach_status"
        ).fetchall()
        by_status = {(r["outreach_status"] or "new"): r["n"] for r in rows}
        return {"total": int(total), "by_status": by_status}
    finally:
        conn.close()


def export_leads_csv(path: str | Path, filters: Optional[dict] = None) -> Path:
    """
    Exporta leads (con filtros opcionales) a un CSV. `filters` acepta las mismas
    claves que query_leads(). Devuelve la ruta del archivo.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    filters = filters or {}
    leads = query_leads(
        min_score=filters.get("min_score", 0),
        provincia=filters.get("provincia"),
        sector=filters.get("sector"),
        has_email=filters.get("has_email"),
        outreach_status=filters.get("outreach_status"),
        limit=filters.get("limit", 100000),
    )
    fields = ["nif", "razon_social", "domain", "score", "email_principal",
              "decisor", "telefono", "provincia", "sector", "outreach_status",
              "first_seen", "last_seen"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "nif": lead.get("nif", ""),
                "razon_social": _extract_razon_social(lead),
                "domain": _extract_domain(lead),
                "score": _extract_score(lead),
                "email_principal": _extract_email(lead),
                "decisor": _extract_decisor(lead),
                "telefono": _extract_phone(lead),
                "provincia": _extract_provincia(lead),
                "sector": lead.get("sector") or lead.get("cnae") or "",
                "outreach_status": lead.get("_outreach_status", ""),
                "first_seen": lead.get("_first_seen", ""),
                "last_seen": lead.get("_last_seen", ""),
            })
    _log.info("Exportados %d leads a %s", len(leads), path)
    return path


# ---------------------------------------------------------------------------
# CLI

def main() -> None:
    p = argparse.ArgumentParser(description="Base de datos de leads — LeadHunter Pro")
    sub = p.add_subparsers(dest="action")

    sub.add_parser("count", help="Contar leads")

    p_q = sub.add_parser("query", help="Consultar leads")
    p_q.add_argument("--min-score", type=int, default=0)
    p_q.add_argument("--provincia")
    p_q.add_argument("--sector")
    p_q.add_argument("--status")
    p_q.add_argument("--limit", type=int, default=50)

    p_exp = sub.add_parser("export", help="Exportar leads a CSV")
    p_exp.add_argument("--path", required=True)
    p_exp.add_argument("--min-score", type=int, default=0)

    args = p.parse_args()

    if args.action == "count":
        print(json.dumps(count_leads(), ensure_ascii=False, indent=2))
    elif args.action == "query":
        results = query_leads(
            min_score=args.min_score, provincia=args.provincia,
            sector=args.sector, outreach_status=args.status, limit=args.limit,
        )
        summary = [{
            "nif": l.get("nif"),
            "razonSocial": _extract_razon_social(l),
            "score": _extract_score(l),
            "domain": _extract_domain(l),
            "status": l.get("_outreach_status"),
        } for l in results]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.action == "export":
        out = export_leads_csv(args.path, {"min_score": args.min_score})
        print(json.dumps({"exported_to": str(out)}, ensure_ascii=False))
    else:
        print(json.dumps(count_leads(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
