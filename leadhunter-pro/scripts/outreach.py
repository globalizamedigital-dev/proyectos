"""
outreach.py — Automatización de outreach: email, LinkedIn, WhatsApp.

Funciones:
    - Cargar y rellenar plantillas de email personalizadas
    - Enviar via SMTP (Gmail o SMTP personalizado)
    - Rastrear emails enviados en SQLite
    - Generar mensajes para LinkedIn
    - Generar mensajes para WhatsApp

Sin APIs externas para el envío — solo smtplib de stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import smtplib
import sqlite3
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    HOME, SKILL_DIR, emit_observation, get_logger, now_iso,
)
import suppression

_log = get_logger("outreach")

# Base de datos SQLite para tracking
DB_PATH = HOME / ".cache" / "leadhunter-pro" / "outreach.db"

# Directorio de plantillas
TEMPLATES_DIR = SKILL_DIR / "templates"

# Límites de entregabilidad por defecto
DEFAULT_MIN_SECONDS_BETWEEN_SENDS = 45
DEFAULT_DAILY_CAP = 40


# ---------------------------------------------------------------------------
# Base de datos de tracking

def _init_db() -> sqlite3.Connection:
    """Inicializa la base de datos SQLite para tracking de outreach."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            lead_nif TEXT,
            lead_razon_social TEXT,
            to_email TEXT NOT NULL,
            subject TEXT,
            channel TEXT DEFAULT 'email',
            template_name TEXT,
            status TEXT DEFAULT 'sent',
            error TEXT,
            message_preview TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_outreach_email ON outreach_log(to_email)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_outreach_nif ON outreach_log(lead_nif)
    """)
    conn.commit()
    return conn


def log_outreach(
    to_email: str,
    channel: str,
    status: str,
    lead: Optional[dict] = None,
    subject: Optional[str] = None,
    template_name: Optional[str] = None,
    error: Optional[str] = None,
    message_preview: Optional[str] = None,
) -> int:
    """Registra un intento de outreach en la base de datos."""
    conn = _init_db()
    try:
        cur = conn.execute("""
            INSERT INTO outreach_log
                (ts, lead_nif, lead_razon_social, to_email, subject, channel, template_name, status, error, message_preview)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now_iso(),
            (lead or {}).get("nif"),
            (lead or {}).get("razonSocial"),
            to_email,
            subject,
            channel,
            template_name,
            status,
            error,
            (message_preview or "")[:500],
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_outreach_history(to_email: Optional[str] = None, lead_nif: Optional[str] = None) -> list[dict]:
    """Obtiene el historial de outreach para un email o NIF."""
    conn = _init_db()
    try:
        if to_email:
            rows = conn.execute(
                "SELECT * FROM outreach_log WHERE to_email = ? ORDER BY ts DESC LIMIT 50",
                (to_email,)
            ).fetchall()
        elif lead_nif:
            rows = conn.execute(
                "SELECT * FROM outreach_log WHERE lead_nif = ? ORDER BY ts DESC LIMIT 50",
                (lead_nif,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM outreach_log ORDER BY ts DESC LIMIT 100"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def has_been_contacted(to_email: str, days: int = 30) -> bool:
    """Comprueba si este email ha sido contactado en los últimos N días."""
    history = get_outreach_history(to_email=to_email)
    if not history:
        return False
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = [h for h in history if h.get("ts", "") >= cutoff and h.get("status") == "sent"]
    return bool(recent)


def get_sent_today_count() -> int:
    """Cuenta los emails realmente enviados hoy (status='sent') — cap diario."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _init_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM outreach_log "
            "WHERE status = 'sent' AND substr(ts, 1, 10) = ?",
            (today,),
        ).fetchone()
        return int(row["n"]) if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cumplimiento legal: supresión, bajas y rebotes

def process_unsubscribe_request(email: str) -> int:
    """
    Procesa una solicitud de baja (respuesta 'BAJA' a un email).
    Añade el email a la lista de supresión.

    Returns:
        id de la entrada de supresión.
    """
    sid = suppression.add_suppression(
        email=email, reason="email-reply-baja", source="outreach",
    )
    _log.info("Baja procesada para %s (supresión id=%s)", email, sid)
    emit_observation("outreach", {"action": "unsubscribe", "email": email})
    return sid


def mark_bounced(email: str) -> int:
    """
    Marca un email como rebotado (hard bounce) y lo añade a la lista de
    supresión para no volver a enviarle.

    Returns:
        id de la entrada de supresión.
    """
    sid = suppression.add_suppression(
        email=email, reason="hard-bounce", source="outreach",
    )
    log_outreach(to_email=email, channel="email", status="bounced",
                 error="hard-bounce")
    _log.warning("Email rebotado %s añadido a supresión (id=%s)", email, sid)
    emit_observation("outreach", {"action": "bounce", "email": email})
    return sid


# ---------------------------------------------------------------------------
# Template engine (sin Jinja2 — solo stdlib)

def load_template(template_name: str) -> Optional[str]:
    """Carga una plantilla de email del directorio templates/."""
    # Intentar varias extensiones
    for ext in [".txt", ".html", ".md"]:
        path = TEMPLATES_DIR / template_name
        if not path.suffix:
            path = TEMPLATES_DIR / (template_name + ext)
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def fill_template(template: str, variables: dict) -> str:
    """
    Rellena una plantilla con variables.
    Soporta {variable} y {{variable}} como placeholders.
    También soporta condicionales simples: {if variable}...{endif}
    """
    result = template

    # Primero procesar condicionales simples
    cond_pattern = re.compile(r'\{if\s+(\w+)\}(.*?)\{endif\}', re.DOTALL)
    def replace_conditional(m):
        var_name = m.group(1)
        content = m.group(2)
        if variables.get(var_name):
            return content
        return ""

    result = cond_pattern.sub(replace_conditional, result)

    # Luego reemplazar variables {{var}} y {var}
    for key, value in variables.items():
        if value is None:
            value = ""
        result = result.replace(f"{{{{{key}}}}}", str(value))
        result = result.replace(f"{{{key}}}", str(value))

    return result


def _unsubscribe_mailto(from_email: str) -> str:
    """Devuelve la URL mailto: de baja para un remitente dado (RFC 8058)."""
    addr = from_email or ""
    return f"mailto:{addr}?subject=BAJA" if addr else "mailto:?subject=BAJA"


def prepare_email(
    lead: dict,
    template_name: str = "email_cold_es.txt",
    from_email: Optional[str] = None,
) -> Optional[dict]:
    """
    Prepara un email personalizado para un lead.

    Args:
        lead: diccionario del lead.
        template_name: nombre de la plantilla.
        from_email: remitente, usado para construir el enlace de baja
                    ({enlace_baja} en las plantillas).

    Returns:
        dict con keys: to, subject, body, template_name
        None si no hay email disponible
    """
    # Obtener email del lead
    to_email = None
    emails = lead.get("emails", [])
    for email_info in emails:
        if isinstance(email_info, dict):
            to_email = email_info.get("email")
        elif isinstance(email_info, str):
            to_email = email_info
        if to_email:
            break

    if not to_email:
        return None

    # Cargar template
    template = load_template(template_name)
    if not template:
        template = _default_cold_email_template()

    # Preparar variables para el template
    decision_makers = lead.get("decisionMakers", [])
    nombre_decisor = ""
    if decision_makers:
        first_dm = decision_makers[0]
        if isinstance(first_dm, dict):
            nombre_decisor = first_dm.get("name", "")
        else:
            nombre_decisor = str(first_dm)
    # Solo primer nombre para saludo
    nombre_corto = nombre_decisor.split()[0] if nombre_decisor else "estimado/a"

    domain = lead.get("domain", {})
    if isinstance(domain, dict):
        domain_str = domain.get("resolved", "")
    else:
        domain_str = str(domain or "")

    sector = lead.get("cnae") or lead.get("sector") or "tu sector"
    ciudad = (lead.get("geocoded") or {}).get("muni") or lead.get("city") or ""

    variables = {
        "nombre_decisor": nombre_decisor,
        "nombre_corto": nombre_corto,
        "empresa": lead.get("razonSocial", ""),
        "sector": sector,
        "ciudad": ciudad,
        "dominio": domain_str,
        "nif": lead.get("nif", ""),
        "score": str(lead.get("score", {}).get("score", "")) if isinstance(lead.get("score"), dict) else "",
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        # Enlace de baja (opt-out) — RFC: mailto con asunto BAJA
        "enlace_baja": _unsubscribe_mailto(from_email or ""),
    }

    body = fill_template(template, variables)

    # Extraer asunto si está en el template (primera línea con "Asunto:")
    subject = ""
    lines = body.split("\n")
    if lines and lines[0].startswith("Asunto:"):
        subject = lines[0].replace("Asunto:", "").strip()
        body = "\n".join(lines[1:]).strip()
    else:
        subject = f"Propuesta para {lead.get('razonSocial', 'vuestra empresa')}"

    return {
        "to": to_email,
        "subject": subject,
        "body": body,
        "template_name": template_name,
        "variables": variables,
    }


def _default_cold_email_template() -> str:
    """Template por defecto si no se encuentra el archivo."""
    return """Asunto: Propuesta de colaboración para {empresa}

Hola {nombre_corto},

Me pongo en contacto contigo como {empresa}, empresa del sector {sector}{if ciudad} en {ciudad}{endif}.

Me gustaría presentarles una solución que podría ser de gran valor para su negocio.

¿Tendría 15 minutos esta semana para una llamada rápida?

Un cordial saludo,
[Tu nombre]
[Tu empresa]
[Tu teléfono]
"""


def send_email(to: str, subject: str, body: str, config: dict) -> bool:
    """
    Envía un email via SMTP.

    Cumplimiento legal: ANTES de enviar comprueba la lista de supresión. Si el
    destinatario (o su dominio) está suprimido, NO se envía (se registra como
    status="suppressed" y se devuelve False).

    Cada email lleva cabeceras List-Unsubscribe / List-Unsubscribe-Post
    (RFC 2369 / RFC 8058) con un mailto: de baja.

    Manejo de rebotes: ante SMTPRecipientsRefused o un código 5xx el email se
    registra como status="bounced" y se añade automáticamente a la lista de
    supresión (reason="hard-bounce").

    Args:
        to: Email destinatario
        subject: Asunto
        body: Cuerpo del mensaje
        config: {
            "smtp_host": str,
            "smtp_port": int,
            "smtp_user": str,
            "smtp_password": str,
            "from_email": str,
            "from_name": str,
            "use_tls": bool,
            "use_ssl": bool,
        }

    Returns:
        bool: True si se envió correctamente. False si estaba suprimido.
    """
    smtp_host = config.get("smtp_host", "smtp.gmail.com")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user", "")
    smtp_password = config.get("smtp_password", "")
    from_email = config.get("from_email") or smtp_user
    from_name = config.get("from_name", "LeadHunter Pro")
    use_tls = config.get("use_tls", True)
    use_ssl = config.get("use_ssl", False)

    if not smtp_user or not smtp_password:
        raise ValueError("Se requiere smtp_user y smtp_password en la configuración")

    # --- Cumplimiento legal: comprobar lista de supresión ANTES de enviar ---
    if suppression.is_suppressed(email=to):
        _log.warning("Envío bloqueado: %s está en la lista de supresión", to)
        log_outreach(to_email=to, channel="email", status="suppressed",
                     subject=subject, error="destinatario en lista de supresión")
        emit_observation("outreach", {"action": "email_suppressed", "to": to})
        return False

    # Crear mensaje MIME
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = from_email

    # Cabeceras de baja (RFC 2369 / RFC 8058) — obligatorias para entregabilidad
    unsub = _unsubscribe_mailto(from_email)
    msg["List-Unsubscribe"] = f"<{unsub}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    # Añadir texto plano y HTML si aplica
    if "<html>" in body.lower():
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

    server = None
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            if use_tls:
                server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to, msg.as_string())
        server.quit()

        emit_observation("outreach", {"action": "email_sent", "to": to, "subject": subject})
        return True

    except smtplib.SMTPAuthenticationError as e:
        _safe_quit(server)
        raise ValueError(f"Error de autenticación SMTP: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        # Destinatario rechazado — hard bounce
        _safe_quit(server)
        mark_bounced(to)
        raise RuntimeError(f"Destinatario rechazado (hard bounce): {e}")
    except smtplib.SMTPSenderRefused as e:
        _safe_quit(server)
        raise RuntimeError(f"Remitente rechazado por el servidor SMTP: {e}")
    except smtplib.SMTPDataError as e:
        # Errores 5xx en la fase DATA suelen indicar rechazo permanente
        _safe_quit(server)
        code = getattr(e, "smtp_code", 0)
        if isinstance(code, int) and 500 <= code < 600:
            mark_bounced(to)
            raise RuntimeError(f"Rechazo permanente 5xx (hard bounce): {e}")
        raise RuntimeError(f"Error SMTP en DATA: {e}")
    except smtplib.SMTPException as e:
        _safe_quit(server)
        raise RuntimeError(f"Error SMTP al enviar: {e}")


def _safe_quit(server) -> None:
    """Cierra una conexión SMTP ignorando cualquier error."""
    if server is not None:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            pass


def generate_linkedin_message(lead: dict) -> str:
    """
    Genera un mensaje de conexión LinkedIn personalizado.

    Returns:
        str: Mensaje para LinkedIn (máx 300 caracteres para invitación)
    """
    razon_social = lead.get("razonSocial", "vuestra empresa")
    sector = lead.get("sector") or lead.get("cnae") or ""
    ciudad = (lead.get("geocoded") or {}).get("muni") or lead.get("city") or ""

    decision_makers = lead.get("decisionMakers", [])
    nombre = ""
    if decision_makers:
        first_dm = decision_makers[0]
        if isinstance(first_dm, dict):
            nombre = first_dm.get("name", "").split()[0]
        else:
            nombre = str(first_dm).split()[0]

    saludo = f"Hola {nombre}," if nombre else "Hola,"

    partes = [saludo]
    partes.append(f"Vi {razon_social}")
    if ciudad:
        partes.append(f"en {ciudad}")
    if sector:
        partes.append(f"(sector {sector})")
    partes.append("y creo que podemos aportaros valor. ¿Conectamos?")

    mensaje = " ".join(partes)

    # Truncar a 300 caracteres (límite LinkedIn)
    if len(mensaje) > 295:
        mensaje = mensaje[:292] + "..."

    return mensaje


def generate_whatsapp_message(lead: dict) -> str:
    """
    Genera un mensaje de WhatsApp personalizado para el lead.
    Incluye link de WhatsApp si hay teléfono disponible.

    Returns:
        str: Mensaje de WhatsApp + URL opcional
    """
    razon_social = lead.get("razonSocial", "vuestra empresa")
    decision_makers = lead.get("decisionMakers", [])
    nombre = ""
    if decision_makers:
        first_dm = decision_makers[0]
        if isinstance(first_dm, dict):
            nombre = first_dm.get("name", "").split()[0]
        else:
            nombre = str(first_dm).split()[0]

    saludo = f"Hola {nombre}!" if nombre else "Hola!"

    mensaje = (
        f"{saludo} Me pongo en contacto desde [Tu empresa]. "
        f"He visto {razon_social} y creo que tenemos algo interesante que proponeros. "
        f"¿Podrías darme 5 minutos para contártelo? 🙏"
    )

    # Obtener teléfono
    phones = lead.get("phones", [])
    if not phones:
        web_contact = lead.get("webContact") or {}
        phones = web_contact.get("phones", []) if isinstance(web_contact, dict) else []

    phone = phones[0] if phones else None

    result = {"mensaje": mensaje}

    if phone:
        # Normalizar teléfono para WhatsApp (quitar +, espacios)
        phone_clean = re.sub(r"[^0-9]", "", phone)
        if not phone_clean.startswith("34") and phone_clean.startswith("6"):
            phone_clean = "34" + phone_clean
        wa_url = f"https://wa.me/{phone_clean}?text={urllib.parse.quote(mensaje)}"
        result["whatsapp_url"] = wa_url

    return json.dumps(result, ensure_ascii=False)


def send_outreach_batch(
    leads: list[dict],
    template_name: str,
    smtp_config: dict,
    dry_run: bool = True,
    skip_already_contacted: bool = True,
    days_since_last_contact: int = 30,
    min_seconds_between_sends: int = DEFAULT_MIN_SECONDS_BETWEEN_SENDS,
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> dict:
    """
    Envía outreach a un lote de leads, respetando:
      - Lista de supresión (cumplimiento legal): los destinatarios suprimidos
        se cuentan aparte como `suppressed` y NUNCA reciben email.
      - Throttle de envío: espera `min_seconds_between_sends` entre envíos reales.
      - Cap diario: si se alcanza `daily_cap` envíos hoy, se detiene y devuelve
        `daily_cap_reached: True`.

    Args:
        leads: Lista de leads con emails
        template_name: Nombre de la plantilla a usar
        smtp_config: Configuración SMTP
        dry_run: Si True, solo simula sin enviar
        skip_already_contacted: Omitir leads ya contactados
        days_since_last_contact: Días mínimos entre contactos
        min_seconds_between_sends: segundos de espera entre envíos reales
        daily_cap: número máximo de envíos reales en el día

    Returns:
        dict con stats: {sent, skipped, suppressed, errors, previews,
                         daily_cap_reached, bounced}
    """
    sent = 0
    skipped = 0
    suppressed = 0
    bounced = 0
    errors: list[dict] = []
    previews: list[dict] = []
    daily_cap_reached = False

    from_email = smtp_config.get("from_email") or smtp_config.get("smtp_user", "")

    # Envíos ya realizados hoy — punto de partida para el cap diario
    already_sent_today = get_sent_today_count() if not dry_run else 0
    remaining_today = max(0, daily_cap - already_sent_today)
    if not dry_run and remaining_today <= 0:
        return {
            "dry_run": dry_run,
            "sent": 0,
            "skipped": 0,
            "suppressed": 0,
            "bounced": 0,
            "errors": [],
            "previews": [],
            "total": len(leads),
            "daily_cap_reached": True,
            "sent_today_before": already_sent_today,
        }

    last_real_send: Optional[float] = None

    for lead in leads:
        prepared = prepare_email(lead, template_name, from_email=from_email)
        if not prepared:
            skipped += 1
            continue

        to_email = prepared["to"]

        # --- Cumplimiento legal: comprobar lista de supresión ---
        if suppression.is_suppressed(email=to_email, nif=lead.get("nif")):
            suppressed += 1
            log_outreach(
                to_email=to_email, channel="email", status="suppressed",
                lead=lead, subject=prepared["subject"],
                template_name=template_name,
                error="destinatario en lista de supresión",
            )
            continue

        # Comprobar si ya fue contactado recientemente
        if skip_already_contacted and has_been_contacted(to_email, days=days_since_last_contact):
            skipped += 1
            continue

        previews.append({
            "to": to_email,
            "subject": prepared["subject"],
            "preview": prepared["body"][:200],
        })

        if dry_run:
            sent += 1
            continue

        # --- Cap diario ---
        if (already_sent_today + sent) >= daily_cap:
            daily_cap_reached = True
            break

        # --- Throttle entre envíos reales ---
        if last_real_send is not None and min_seconds_between_sends > 0:
            elapsed = time.monotonic() - last_real_send
            wait_for = min_seconds_between_sends - elapsed
            if wait_for > 0:
                time.sleep(wait_for)

        try:
            success = send_email(
                to=to_email,
                subject=prepared["subject"],
                body=prepared["body"],
                config=smtp_config,
            )
            last_real_send = time.monotonic()
            if success:
                log_outreach(
                    to_email=to_email,
                    channel="email",
                    status="sent",
                    lead=lead,
                    subject=prepared["subject"],
                    template_name=template_name,
                    message_preview=prepared["body"][:500],
                )
                sent += 1
            else:
                # send_email devolvió False -> estaba suprimido
                suppressed += 1
        except Exception as e:
            error_msg = str(e)
            errors.append({"to": to_email, "error": error_msg})
            if "bounce" in error_msg.lower():
                bounced += 1
            else:
                log_outreach(
                    to_email=to_email,
                    channel="email",
                    status="error",
                    lead=lead,
                    subject=prepared["subject"],
                    template_name=template_name,
                    error=error_msg,
                )

    return {
        "dry_run": dry_run,
        "sent": sent,
        "skipped": skipped,
        "suppressed": suppressed,
        "bounced": bounced,
        "errors": errors,
        "previews": previews[:5],
        "total": len(leads),
        "daily_cap_reached": daily_cap_reached,
        "sent_today_before": already_sent_today,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Outreach — LeadHunter Pro")
    p.add_argument("--preview", action="store_true", help="Previsualizar email para lead")
    p.add_argument("--lead-json", dest="lead_json", help="JSON del lead")
    p.add_argument("--template", default="email_cold_es.txt", help="Nombre de plantilla")
    p.add_argument("--linkedin", action="store_true", help="Generar mensaje LinkedIn")
    p.add_argument("--whatsapp", action="store_true", help="Generar mensaje WhatsApp")
    p.add_argument("--history", help="Ver historial de outreach para un email")
    args = p.parse_args()

    if args.history:
        history = get_outreach_history(to_email=args.history)
        print(json.dumps(history, ensure_ascii=False, indent=2))
        return

    lead = {}
    if args.lead_json:
        lead = json.loads(args.lead_json)
    else:
        # Lead de ejemplo
        lead = {
            "razonSocial": "Asesores García S.L.",
            "emails": [{"email": "info@asesoresgarcia.es", "confidence": "high"}],
            "decisionMakers": [{"name": "María García López", "role": "Gerente"}],
            "phones": ["+34 912 345 678"],
            "city": "Madrid",
        }

    if args.preview or not any([args.linkedin, args.whatsapp]):
        prepared = prepare_email(lead, args.template)
        print(json.dumps(prepared, ensure_ascii=False, indent=2))

    if args.linkedin:
        msg = generate_linkedin_message(lead)
        print(f"\nLinkedIn message:\n{msg}")

    if args.whatsapp:
        msg = generate_whatsapp_message(lead)
        print(f"\nWhatsApp message:\n{msg}")


if __name__ == "__main__":
    main()
