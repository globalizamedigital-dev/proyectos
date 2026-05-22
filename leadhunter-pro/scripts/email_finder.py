"""
email_finder.py — Encuentra emails directos personales de propietarios/directores.

Estrategia (sin APIs externas):
    1. Obtener nombres admin/director (de person_finder o datos BORME)
    2. Obtener dominio de la empresa (de domain_resolver)
    3. Generar permutaciones: firstname.lastname@domain, f.lastname@domain, etc.
       Manejo especial para nombres españoles con 2 apellidos.
    4. Verificar via SMTP MX check (EHLO + MAIL FROM + RCPT TO sin enviar)
    5. Scraping de páginas web de contacto para emails (regex)
    6. Retornar ordenados por confianza

NOTA: La verificación SMTP es pasiva (no envía correo). Algunos servidores
de correo bloquean verificaciones RCPT TO (técnica anti-harvesting).
En ese caso se retorna confianza "high" sin verificación smtp.
"""
from __future__ import annotations

import argparse
import json
import re
import smtplib
import socket
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    CacheConfig, SourceStatus, cache_get, cache_set, emit_observation,
    http_get, normalize_razon_social, generar_permutaciones_email, parse_nombre_partes,
)

CACHE = CacheConfig(namespace="email-finder", ttl_seconds=60 * 60 * 24 * 3)
CACHE_SMTP = CacheConfig(namespace="smtp-verify", ttl_seconds=60 * 60 * 24 * 7)

# Timeout para conexiones SMTP
# Timeout SMTP por intento (segundos). Bajado de 8→5: con 8 cada email no
# verificable bloquea ~10s (handshake + EHLO + MAIL FROM + RCPT TO), lo que
# convierte el enriquecimiento de 20 leads en >3 min de espera.
SMTP_TIMEOUT = 5


def get_mx_record(domain: str) -> Optional[str]:
    """
    Obtiene el registro MX de un dominio.
    Usa el módulo dns.resolver si está disponible, sino intenta con nslookup/dig.
    Fallback: usa el propio dominio como servidor de mail.
    """
    # Intentar con dnspython si está disponible
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        # El de menor preferencia (número más bajo) tiene mayor prioridad
        records = sorted(answers, key=lambda r: r.preference)
        return str(records[0].exchange).rstrip(".")
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: socket DNS lookup básico
    try:
        # Intentar resolver directamente como servidor de mail
        host_info = socket.getaddrinfo(f"mail.{domain}", 25, socket.AF_INET, socket.SOCK_STREAM)
        if host_info:
            return f"mail.{domain}"
    except Exception:
        pass

    try:
        host_info = socket.getaddrinfo(domain, 25, socket.AF_INET, socket.SOCK_STREAM)
        if host_info:
            return domain
    except Exception:
        pass

    return None


def verify_email_smtp(email: str, from_addr: str = "verify@leadhunter.pro") -> dict:
    """
    Verifica un email via SMTP sin enviar mensaje.
    Protocolo: connect → EHLO → MAIL FROM → RCPT TO → QUIT

    Retorna:
        {"valid": bool, "method": "smtp", "code": int, "message": str, "mx_host": str}
    """
    cache_key = f"smtp:{email}"
    cached = cache_get(CACHE_SMTP, cache_key)
    if cached is not None:
        return cached

    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return {"valid": False, "method": "smtp", "error": "invalid-email"}

    mx_host = get_mx_record(domain)
    if not mx_host:
        result = {
            "valid": False,
            "method": "smtp",
            "error": "no-mx-record",
            "mx_host": None,
        }
        cache_set(CACHE_SMTP, cache_key, result)
        return result

    smtp: Optional[smtplib.SMTP] = None
    try:
        # Conectar al servidor MX en puerto 25
        smtp = smtplib.SMTP(timeout=SMTP_TIMEOUT)
        smtp.connect(mx_host, 25)

        # EHLO
        code, msg = smtp.ehlo("leadhunter-verify.local")
        if code not in (200, 220, 250):
            result = {"valid": False, "method": "smtp", "code": code, "mx_host": mx_host,
                      "error": f"ehlo-failed-{code}"}
            cache_set(CACHE_SMTP, cache_key, result)
            return result

        # MAIL FROM (simulado)
        code, msg = smtp.mail(from_addr)
        if code not in (200, 250):
            result = {"valid": False, "method": "smtp", "code": code, "mx_host": mx_host,
                      "error": f"mail-from-failed-{code}"}
            cache_set(CACHE_SMTP, cache_key, result)
            return result

        # RCPT TO — la clave de la verificación
        code, msg = smtp.rcpt(email)
        valid = code in (200, 250, 251)
        result = {
            "valid": valid,
            "method": "smtp",
            "code": code,
            "message": msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg),
            "mx_host": mx_host,
        }
        cache_set(CACHE_SMTP, cache_key, result)
        return result

    except smtplib.SMTPConnectError:
        result = {"valid": False, "method": "smtp", "error": "connection-refused", "mx_host": mx_host}
    except smtplib.SMTPServerDisconnected:
        result = {"valid": False, "method": "smtp", "error": "server-disconnected", "mx_host": mx_host}
    except socket.timeout:
        result = {"valid": False, "method": "smtp", "error": "timeout", "mx_host": mx_host}
    except ConnectionRefusedError:
        result = {"valid": False, "method": "smtp", "error": "port-25-blocked", "mx_host": mx_host}
    except OSError as e:
        result = {"valid": False, "method": "smtp", "error": f"os-error:{e}", "mx_host": mx_host}
    except Exception as e:
        result = {"valid": False, "method": "smtp", "error": f"smtp-error:{type(e).__name__}", "mx_host": mx_host}
    finally:
        # Cierre garantizado de la conexión: smtp.quit() puede a su vez fallar
        # si el servidor ya cortó, así que cubrimos con close() de respaldo.
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                try:
                    smtp.close()
                except Exception:
                    pass

    cache_set(CACHE_SMTP, cache_key, result)
    return result


def verify_email_http(email: str, domain: str) -> dict:
    """
    Verificación alternativa via HTTP: busca el email en páginas de la empresa.
    Más lento pero funciona cuando SMTP port 25 está bloqueado.
    """
    try:
        from web_contact import scrape_contact
        contact_data = scrape_contact(domain)
        found_emails = [e["email"] for e in contact_data.get("emails", [])]
        if email.lower() in [e.lower() for e in found_emails]:
            return {"valid": True, "method": "web_scrape", "source": "company_website"}
        return {"valid": False, "method": "web_scrape"}
    except Exception:
        return {"valid": False, "method": "web_scrape", "error": "scrape-failed"}


def find_emails_from_web(domain: str) -> list[dict]:
    """Extrae emails directamente de la web de la empresa."""
    try:
        from web_contact import scrape_contact
        contact_data = scrape_contact(domain)
        results = []
        for email_info in contact_data.get("emails", []):
            results.append({
                "email": email_info["email"],
                "confidence": email_info.get("confidence", "medium"),
                "via": "web_scrape",
                "name": None,
                "smtp_verified": False,
            })
        return results
    except Exception:
        return []


def find_emails(
    razon_social: str,
    domain: Optional[str] = None,
    admin_names: Optional[list[str]] = None,
    city: Optional[str] = None,
) -> list[dict]:
    """
    Encuentra emails directos de propietarios/directores de una empresa.

    Args:
        razon_social: Nombre de la empresa
        domain: Dominio web de la empresa (si se conoce)
        admin_names: Lista de nombres de administradores/directores
        city: Ciudad (para contexto)

    Returns:
        list[dict]: [{"email": "...", "confidence": "verified|high|medium|low",
                      "via": "smtp_verified|web_scrape|permutation", "name": "..."}]
    """
    cache_key = f"emails:{normalize_razon_social(razon_social)}:{domain or ''}"
    cached = cache_get(CACHE, cache_key)
    if cached is not None:
        return cached

    results: list[dict] = []

    # 1. Si tenemos dominio, scraping web primero (más directo)
    if domain:
        web_emails = find_emails_from_web(domain)
        results.extend(web_emails)

    # 2. Si tenemos nombres de administradores, generar permutaciones
    if domain and admin_names:
        for full_name in admin_names[:5]:  # Limitar a 5 nombres
            partes = parse_nombre_partes(full_name)
            nombre = partes.get("nombre", "")
            apellido1 = partes.get("apellido1", "")
            apellido2 = partes.get("apellido2")

            if not nombre:
                continue

            permutaciones = generar_permutaciones_email(nombre, apellido1, apellido2, domain)

            for email_candidate in permutaciones[:8]:  # Top 8 permutaciones
                # Verificar si ya lo tenemos
                existing = {r["email"] for r in results}
                if email_candidate in existing:
                    continue

                # Intentar verificación SMTP
                smtp_result = verify_email_smtp(email_candidate)

                if smtp_result.get("valid"):
                    results.append({
                        "email": email_candidate,
                        "confidence": "verified",
                        "via": "smtp_verified",
                        "name": full_name,
                        "smtp_code": smtp_result.get("code"),
                        "mx_host": smtp_result.get("mx_host"),
                    })
                elif smtp_result.get("error") in ("port-25-blocked", "connection-refused", "timeout", "server-disconnected"):
                    # No podemos verificar SMTP, pero la permutación es válida
                    # Añadir con confianza "high" solo las más probables (primeras 3)
                    if permutaciones.index(email_candidate) < 3:
                        results.append({
                            "email": email_candidate,
                            "confidence": "high",
                            "via": "permutation",
                            "name": full_name,
                            "smtp_note": smtp_result.get("error"),
                        })
                else:
                    # SMTP respondió pero rechazó (usuario no existe)
                    if smtp_result.get("error") and "mx-record" not in smtp_result.get("error", ""):
                        continue  # Skip inválidos confirmados
                    # Sin MX record: añadir con confianza baja
                    if permutaciones.index(email_candidate) == 0:
                        results.append({
                            "email": email_candidate,
                            "confidence": "low",
                            "via": "permutation",
                            "name": full_name,
                        })

                # Pequeña pausa para no sobrecargar el servidor MX
                time.sleep(0.5)

    # 3. Si no tenemos dominio ni nombres, intentar encontrar via DDG
    if not domain and razon_social:
        try:
            from ddg import search as ddg_search
            query = f'"{razon_social}" email contacto'
            ddg_results = ddg_search(query, max_results=3)
            for r in ddg_results:
                snippet = r.get("snippet", "") or r.get("title", "")
                # Buscar emails en snippets
                email_re = re.compile(r'\b[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,10}\b')
                for m in email_re.finditer(snippet):
                    email = m.group(0).lower()
                    if "@gmail." not in email and "@hotmail." not in email:
                        existing = {r["email"] for r in results}
                        if email not in existing:
                            results.append({
                                "email": email,
                                "confidence": "medium",
                                "via": "ddg_snippet",
                                "name": None,
                            })
        except Exception:
            pass

    # Ordenar por confianza
    order = {"verified": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda x: order.get(x.get("confidence", "low"), 9))

    # Deduplicar
    seen: set[str] = set()
    deduped = []
    for r in results:
        email = r.get("email", "").lower()
        if email and email not in seen:
            seen.add(email)
            deduped.append(r)

    emit_observation("tool_lead_recon", {
        "phase": "email_finder",
        "razon_social": razon_social,
        "domain": domain,
        "found": len(deduped),
    })

    cache_set(CACHE, cache_key, deduped)
    return deduped


def main() -> None:
    p = argparse.ArgumentParser(description="Email Finder — LeadHunter Pro")
    p.add_argument("--razon-social", dest="razon_social", required=True)
    p.add_argument("--domain")
    p.add_argument("--names", nargs="*", default=[], help="Nombres de administradores")
    p.add_argument("--city")
    p.add_argument("--verify-only", help="Solo verificar un email concreto")
    args = p.parse_args()

    if args.verify_only:
        domain = args.verify_only.split("@")[1] if "@" in args.verify_only else ""
        result = verify_email_smtp(args.verify_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        result = find_emails(
            args.razon_social,
            domain=args.domain,
            admin_names=args.names or None,
            city=args.city,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
