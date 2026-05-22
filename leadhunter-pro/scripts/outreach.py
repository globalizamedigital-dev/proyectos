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
import urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    HOME, SKILL_DIR, emit_observation, now_iso,
)

# Base de datos SQLite para tracking
DB_PATH = HOME / ".cache" / "leadhunter-pro" / "outreach.db"

# Directorio de plantillas
TEMPLATES_DIR = SKILL_DIR / "templates"


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


def prepare_email(lead: dict, template_name: str = "email_cold_es.txt") -> Optional[dict]:
    """
    Prepara un email personalizado para un lead.

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
        bool: True si se envió correctamente
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

    # Crear mensaje MIME
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = from_email

    # Añadir texto plano y HTML si aplica
    if "<html>" in body.lower():
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

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
        raise ValueError(f"Error de autenticación SMTP: {e}")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"Error SMTP al enviar: {e}")


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
) -> dict:
    """
    Envía outreach a un lote de leads.

    Args:
        leads: Lista de leads con emails
        template_name: Nombre de la plantilla a usar
        smtp_config: Configuración SMTP
        dry_run: Si True, solo simula sin enviar
        skip_already_contacted: Omitir leads ya contactados
        days_since_last_contact: Días mínimos entre contactos

    Returns:
        dict con stats: {sent, skipped, errors, previews}
    """
    sent = 0
    skipped = 0
    errors = []
    previews = []

    for lead in leads:
        prepared = prepare_email(lead, template_name)
        if not prepared:
            skipped += 1
            continue

        to_email = prepared["to"]

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

        try:
            success = send_email(
                to=to_email,
                subject=prepared["subject"],
                body=prepared["body"],
                config=smtp_config,
            )
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
        except Exception as e:
            error_msg = str(e)
            errors.append({"to": to_email, "error": error_msg})
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
        "errors": errors,
        "previews": previews[:5],
        "total": len(leads),
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
