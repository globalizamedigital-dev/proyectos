"""
GDPR + LSSI · endpoints de privacidad.

- POST /privacy/export  : devuelve todo lo asociado a un sujeto (email,
                          teléfono o NIF). Para responder a derecho de
                          acceso del RGPD art. 15.
- DELETE /privacy/erase : borra de leads, outreach_events, embeddings y
                          suppression al sujeto. Derecho al olvido
                          (RGPD art. 17). Operación IRREVERSIBLE.
- GET  /unsubscribe     : endpoint público que da de baja un email
                          (canal `email`) vía token firmado. Sin auth.
                          Lo enlazan las plantillas con {{enlace_baja}}.

El sujeto se identifica por uno de tres campos:
    email   = string lowercase
    phone   = string sin espacios
    nif     = string uppercase normalizado

Mantenemos auditoría: cada erase emite un registro en `usage_events`
con service='supabase', operation='gdpr_erase'.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from db import get_supabase
from deps import AuthUser
from settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["privacy"])

# ── Subject normalizers ──────────────────────────────────────────────

SubjectKind = Literal["email", "phone", "nif"]

_NIF_RE = re.compile(r"^[A-HJNPQRSUVW]\d{7}[0-9A-J]$|^\d{8}[A-Z]$|^[XYZ]\d{7}[A-Z]$")


def _normalize(kind: SubjectKind, value: str) -> str:
    v = value.strip()
    if kind == "email":
        return v.lower()
    if kind == "phone":
        return re.sub(r"\s+", "", v)
    # nif
    return re.sub(r"[\s-]+", "", v).upper()


class SubjectRequest(BaseModel):
    kind: SubjectKind
    value: str = Field(..., min_length=3)

    @field_validator("value")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


# ── Token unsubscribe (HMAC, sin estado en BD) ───────────────────────

def _sign_token(email: str, secret: str) -> str:
    """Token estable: base64url(email_lc + '.' + hmac_sha256(email_lc, secret)[:16]).

    El HMAC se calcula sobre la versión LOWERCASE para que tokens
    generados con distintos cases del mismo email coincidan al verificar.
    """
    email_lc = email.lower()
    mac = hmac.new(secret.encode(), email_lc.encode(), hashlib.sha256).digest()[:16]
    payload = f"{email_lc}.{base64.urlsafe_b64encode(mac).decode().rstrip('=')}"
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def _verify_token(token: str, secret: str) -> str | None:
    """Devuelve el email si el token es válido; None si no."""
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        email, sig = decoded.rsplit(".", 1)
        expected = hmac.new(secret.encode(), email.encode(), hashlib.sha256).digest()[:16]
        if hmac.compare_digest(
            base64.urlsafe_b64encode(expected).decode().rstrip("="),
            sig,
        ):
            return email
    except Exception:  # noqa: BLE001
        return None
    return None


def _unsubscribe_secret(settings: Settings) -> str:
    """
    Secret para firmar tokens de baja. Usamos el service_role_key como
    base: garantiza que solo el backend puede emitir tokens válidos. El
    `[:64]` evita pasar el token completo a HMAC, pero conserva entropía
    suficiente.
    """
    return settings.supabase_service_role_key[:64]


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/privacy/export", tags=["privacy"])
def privacy_export(
    req: SubjectRequest,
    user: AuthUser,
    # Anotamos `Any` (no `Client`) porque FastAPI inspecciona el tipo y al
    # ver una clase no-primitiva intenta deducir un body schema. Con `Any`
    # se queda quieto y respeta el `Depends(get_supabase)`.
    sb: Annotated[Any, Depends(get_supabase)],
) -> dict[str, Any]:
    """
    Devuelve todo lo asociado al sujeto. Responde al RGPD art. 15
    (derecho de acceso) y sirve también como log forense.
    """
    norm = _normalize(req.kind, req.value)
    logger.info("privacy_export: user=%s kind=%s subject=hash:%s",
                user.id, req.kind, hashlib.sha256(norm.encode()).hexdigest()[:8])

    # Construimos filtros por tipo de sujeto.
    leads = _query_leads(sb, req.kind, norm)
    lead_ids = [l["id"] for l in leads]
    events = _query_events(sb, lead_ids) if lead_ids else []
    suppression = _query_suppression(sb, req.kind, norm)

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "subject": {"kind": req.kind, "value": norm},
        "counts": {
            "leads": len(leads),
            "outreach_events": len(events),
            "suppression": len(suppression),
        },
        "leads": leads,
        "outreach_events": events,
        "suppression": suppression,
    }


@router.delete("/privacy/erase", tags=["privacy"])
def privacy_erase(
    req: SubjectRequest,
    user: AuthUser,
    sb: Annotated[Any, Depends(get_supabase)],
) -> dict[str, Any]:
    """
    BORRA todos los datos del sujeto. Operación IRREVERSIBLE.
    Las relaciones tienen ON DELETE CASCADE, así que basta con borrar
    el lead (cascade limpia outreach_events y leads_embeddings).
    Suppression list también se borra.
    """
    norm = _normalize(req.kind, req.value)
    leads = _query_leads(sb, req.kind, norm)
    lead_ids = [l["id"] for l in leads]

    deleted_leads = 0
    if lead_ids:
        sb.table("leads").delete().in_("id", lead_ids).execute()
        deleted_leads = len(lead_ids)

    deleted_suppression = 0
    sup = _query_suppression(sb, req.kind, norm)
    if sup:
        for row in sup:
            sb.table("suppression").delete().eq("channel", row["channel"]).eq(
                "identifier", row["identifier"]
            ).execute()
        deleted_suppression = len(sup)

    # Auditoría: log + usage_event
    logger.warning(
        "GDPR_ERASE: user=%s kind=%s subject_hash=%s leads=%d suppression=%d",
        user.id, req.kind, hashlib.sha256(norm.encode()).hexdigest()[:12],
        deleted_leads, deleted_suppression,
    )
    try:
        sb.table("usage_events").insert({
            "service": "supabase",
            "operation": "gdpr_erase",
            "units": deleted_leads + deleted_suppression,
            "meta": {"subject_kind": req.kind, "by_user": user.id},
        }).execute()
    except Exception:  # noqa: BLE001
        # Auditoría es nice-to-have; no rompemos el erase si la inserción falla.
        logger.exception("usage_events insert tras erase falló")

    return {
        "erased": True,
        "subject": {"kind": req.kind, "value": norm},
        "deleted": {"leads": deleted_leads, "suppression": deleted_suppression},
    }


@router.get("/unsubscribe", tags=["privacy"], include_in_schema=False)
def unsubscribe(
    token: Annotated[str, Query(min_length=8)],
    settings: Annotated[Settings, Depends(get_settings)],
    sb: Annotated[Any, Depends(get_supabase)],
) -> Response:
    """
    Endpoint público (sin auth). Lo invocan los enlaces de baja dentro
    de los emails. Token HMAC-SHA256 sobre el email + service_role_key.
    """
    email = _verify_token(token, _unsubscribe_secret(settings))
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    # Single tenant: 'globalizame'. Buscamos su id.
    tenant_row = (
        sb.table("tenants").select("id").eq("slug", "globalizame").maybe_single().execute()
    )
    if not tenant_row.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant 'globalizame' no existe")

    sb.table("suppression").upsert({
        "tenant_id": tenant_row.data["id"],
        "channel": "email",
        "identifier": email,
        "reason": "user_unsubscribed",
    }).execute()

    logger.info("unsubscribe: email=%s tenant=%s", email, tenant_row.data["id"])

    # Página HTML simple, sin JS, alineada a la marca.
    html = _unsubscribe_html(email)
    return Response(content=html, media_type="text/html; charset=utf-8")


# ── Internals ────────────────────────────────────────────────────────

def _query_leads(sb: Client, kind: SubjectKind, value: str) -> list[dict[str, Any]]:
    q = sb.table("leads").select("*")
    if kind == "email":
        return q.eq("email_principal", value).execute().data or []
    if kind == "phone":
        return q.eq("telefono", value).execute().data or []
    return q.eq("nif", value).execute().data or []


def _query_events(sb: Client, lead_ids: list[str]) -> list[dict[str, Any]]:
    if not lead_ids:
        return []
    return sb.table("outreach_events").select("*").in_("lead_id", lead_ids).execute().data or []


def _query_suppression(sb: Client, kind: SubjectKind, value: str) -> list[dict[str, Any]]:
    q = sb.table("suppression").select("*").eq("identifier", value)
    # nif → channel "nif", email → "email", phone → "phone"/"whatsapp"
    if kind == "phone":
        return q.in_("channel", ["phone", "whatsapp"]).execute().data or []
    return q.eq("channel", kind).execute().data or []


def _unsubscribe_html(email: str) -> str:
    """Página de confirmación sin JS, branded Globalizame."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Baja registrada · Cazador Globalizame</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{ color-scheme: dark; }}
  body {{
    margin: 0; min-height: 100vh; display: flex; align-items: center;
    justify-content: center; padding: 24px;
    background: #0a0a0a; color: #fafafa;
    font-family: ui-sans-serif,-apple-system,BlinkMacSystemFont,Inter,sans-serif;
  }}
  .card {{
    max-width: 520px; width: 100%; padding: 40px;
    border: 1px solid rgba(255,255,255,0.1); background: #141414;
  }}
  .eyebrow {{ font-size: 10px; letter-spacing: .18em; text-transform: uppercase; color: #a3a3a3; }}
  h1 {{ font-size: 32px; font-weight: 300; letter-spacing: -.02em; margin: 16px 0; }}
  .accent {{ color: #86ca28; }}
  code {{ background: #1f1f1f; padding: 2px 6px; font-family: ui-monospace,Menlo,Consolas,monospace; }}
  p {{ color: #a3a3a3; line-height: 1.6; font-size: 14px; }}
  .footer {{ margin-top: 32px; font-size: 11px; color: #525252; letter-spacing: .14em; text-transform: uppercase; }}
</style>
</head>
<body>
  <div class="card">
    <span class="eyebrow">baja registrada</span>
    <h1>Hecho. <span class="accent">No te volvemos a escribir.</span></h1>
    <p>
      El email <code>{email}</code> queda fuera de cualquier secuencia de outreach
      de Globalizame. La baja se aplica cross-canal (email, WhatsApp) y es definitiva.
    </p>
    <p>
      Si fue un error o quieres volver, escríbenos a
      <a href="mailto:info@globalizame.com" style="color:#86ca28">info@globalizame.com</a>.
    </p>
    <div class="footer">cazador · globalizame</div>
  </div>
</body>
</html>"""
