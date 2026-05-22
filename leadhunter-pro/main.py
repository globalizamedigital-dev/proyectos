#!/usr/bin/env python3
"""
LeadHunter Pro — Entry point.

Uso:
    python main.py gui                            # Lanzar interfaz gráfica Tkinter
    python main.py discover --geo Sevilla --sector "asesoría fiscal"
    python main.py analyze --input B12345678
    python main.py analyze --input "Asesores García S.L."
    python main.py person --razon-social "Empresa X" --domain empresa.es
    python main.py email --razon-social "Empresa X" --domain empresa.es
    python main.py score --lead-file /path/to/lead.json
    python main.py outreach --preview --lead-json '{...}'
    python main.py version
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Forzar UTF-8 en stdout/stderr: la consola de Windows usa cp1252 por defecto
# y crashea al imprimir caracteres como ⚠ o acentos. errors="replace" evita
# que un carácter no representable aborte el comando.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# Añadir scripts/ al path
_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))


def cmd_gui(args):
    """Lanza la interfaz gráfica Tkinter."""
    try:
        import tkinter as tk
    except ImportError:
        print("ERROR: Tkinter no está disponible en este entorno Python.")
        print("En Ubuntu/Debian: sudo apt-get install python3-tk")
        sys.exit(1)

    _GUI_DIR = Path(__file__).resolve().parent / "gui"
    sys.path.insert(0, str(_GUI_DIR.parent))

    try:
        from gui.app import run
        run()
    except Exception as e:
        print(f"ERROR al lanzar GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_discover(args):
    """Descubrimiento de leads por geo + sector."""
    from discover import discover
    payload = discover(
        geo=args.geo,
        sector=args.sector,
        max_results=args.max,
        enrich=not args.no_enrich,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    else:
        # Resumen legible
        print(f"\nLeadHunter Pro — Discover")
        print(f"  Geo:     {args.geo}")
        print(f"  Sector:  {args.sector}")
        print(f"  Leads:   {payload['totalCandidates']}")
        print(f"  Sin dom: {payload['totalUnresolvedDomain']}")
        print(f"\nFuentes:")
        for src, status in payload["sourcesAvailability"].items():
            icon = "[OK]" if "ok" in status else "[--]"
            print(f"  {icon} {src}: {status}")
        print(f"\nTop leads:")
        for c in payload["candidates"][:10]:
            score_data = c.get("score") or {}
            score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
            grade = score_data.get("grade", "?") if isinstance(score_data, dict) else "?"
            domain = (c.get("domain") or {}).get("resolved", "—")
            dms = c.get("decisionMakers", [])
            dm = dms[0].get("name", "") if dms and isinstance(dms[0], dict) else ""
            emails = c.get("emails", [])
            email = emails[0].get("email", "") if emails and isinstance(emails[0], dict) else ""
            print(f"  [{score:3d}/{grade}] {c.get('razonSocial', '?')[:40]}")
            if domain != "—":
                print(f"         Web: {domain}")
            if dm:
                print(f"         Decisor: {dm}")
            if email:
                print(f"         Email: {email}")
        print(f"\nSnapshot: {payload['writes'].get('snapshot', '?')}")


def cmd_analyze(args):
    """Análisis completo de empresa por NIF o razón social."""
    from analyze import analyze
    payload = analyze(
        input_str=args.input,
        premium=args.premium,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    else:
        inp = payload["input"]
        rs = inp.get("razon_social") or inp.get("nif") or "?"
        score_data = payload.get("score") or {}
        score = score_data.get("score", "?") if isinstance(score_data, dict) else "?"
        grade = score_data.get("grade", "?") if isinstance(score_data, dict) else "?"

        print(f"\nLeadHunter Pro — Analyze: {rs}")
        print(f"  NIF: {inp.get('nif', '—')}")
        print(f"  Score: {score}/100 [{grade}]")
        print(f"\nWeb:")
        web = payload.get("web") or {}
        print(f"  Dominio: {web.get('domain', '—')} (via {web.get('resolved_via', '?')})")
        print(f"\nDecisores ({len(payload.get('decisionMakers', []))}):")
        for dm in payload.get("decisionMakers", [])[:5]:
            if isinstance(dm, dict):
                print(f"  • {dm.get('name', '?')} — {dm.get('role', '?')}")
        print(f"\nEmails ({len(payload.get('emails', []))}):")
        for em in payload.get("emails", [])[:5]:
            if isinstance(em, dict):
                print(f"  • {em.get('email', '?')} [{em.get('confidence', '?')}]")
        print(f"\nTeléfonos: {', '.join(payload.get('phones', [])[:3]) or '—'}")
        print(f"\nDPO AEPD: {payload.get('compliance', {}).get('dpoRegistered', '—')}")
        print(f"Contratos: {len(payload.get('publicSector', {}).get('contracts', []))}")
        print(f"Subvenciones: {len(payload.get('publicSector', {}).get('subsidies', []))}")
        print(f"\nRecomendación: {payload.get('recommendation', {}).get('nextStep', '—')}")

        if payload.get("warnings"):
            print("\nAvisos:")
            for w in payload["warnings"]:
                print(f"  ⚠ {w}")

        print(f"\nSnapshot: {payload['writes'].get('snapshot', '?')}")


def cmd_person(args):
    """Busca decisores de una empresa."""
    from person_finder import find_decision_makers
    results = find_decision_makers(
        razon_social=args.razon_social,
        domain=args.domain,
        city=args.city,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_email(args):
    """Busca emails de una empresa."""
    from email_finder import find_emails
    results = find_emails(
        razon_social=args.razon_social,
        domain=args.domain,
        admin_names=args.names or None,
        city=args.city,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_score(args):
    """Puntúa un lead."""
    from lead_scorer import score
    if args.lead_json:
        lead = json.loads(args.lead_json)
    elif args.lead_file:
        lead = json.loads(Path(args.lead_file).read_text(encoding="utf-8"))
    else:
        # Demo
        lead = {
            "razonSocial": "Demo S.L.",
            "domain": {"resolved": "demo.es"},
            "emails": [{"email": "info@demo.es", "confidence": "high"}],
        }
    result = score(lead)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_outreach(args):
    """Outreach para un lead."""
    from outreach import prepare_email, generate_linkedin_message, generate_whatsapp_message
    if args.lead_json:
        lead = json.loads(args.lead_json)
    else:
        lead = {}

    if args.preview:
        result = prepare_email(lead, args.template or "email_cold_es.txt")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.linkedin:
        print(generate_linkedin_message(lead))
    if args.whatsapp:
        print(generate_whatsapp_message(lead))


def cmd_version(args):
    print("LeadHunter Pro v1.0.0")
    print("Python:", sys.version)
    print("Scripts dir:", _SCRIPTS_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="LeadHunter Pro — Motor de generación de leads B2B",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py gui
  python main.py discover --geo Sevilla --sector "asesoría fiscal"
  python main.py discover --geo Madrid --sector "desarrollo software" --max 100
  python main.py analyze --input B12345678
  python main.py analyze --input "Asesores García S.L."
  python main.py person --razon-social "Empresa X" --domain empresa.es
  python main.py email --razon-social "Empresa X" --domain empresa.es
  python main.py score --lead-json '{"razonSocial": "Demo S.L.", "domain": {"resolved": "demo.es"}}'
        """
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # gui
    subparsers.add_parser("gui", help="Lanzar interfaz gráfica Tkinter")

    # discover
    p_disc = subparsers.add_parser("discover", help="Descubrir leads por geo + sector")
    p_disc.add_argument("--geo", required=True, help="Provincia o ciudad")
    p_disc.add_argument("--sector", required=True, help="Sector o CNAE")
    p_disc.add_argument("--max", type=int, default=50, help="Máximo de resultados")
    p_disc.add_argument("--no-enrich", dest="no_enrich", action="store_true",
                         help="Sin enriquecimiento avanzado")
    p_disc.add_argument("--json", action="store_true", help="Salida JSON completa")
    p_disc.add_argument("--pretty", action="store_true", help="JSON con indentación")

    # analyze
    p_anal = subparsers.add_parser("analyze", help="Analizar empresa por NIF o razón social")
    p_anal.add_argument("--input", required=True, help="NIF/CIF o razón social")
    p_anal.add_argument("--premium", action="store_true", help="Incluir fuentes premium")
    p_anal.add_argument("--json", action="store_true", help="Salida JSON completa")
    p_anal.add_argument("--pretty", action="store_true", help="JSON con indentación")

    # person
    p_person = subparsers.add_parser("person", help="Buscar decisores de una empresa")
    p_person.add_argument("--razon-social", dest="razon_social", required=True)
    p_person.add_argument("--domain", help="Dominio web de la empresa")
    p_person.add_argument("--city", help="Ciudad para contexto")

    # email
    p_email = subparsers.add_parser("email", help="Buscar emails de una empresa")
    p_email.add_argument("--razon-social", dest="razon_social", required=True)
    p_email.add_argument("--domain", help="Dominio web")
    p_email.add_argument("--names", nargs="*", help="Nombres de administradores")
    p_email.add_argument("--city")

    # score
    p_score = subparsers.add_parser("score", help="Puntuar un lead")
    p_score.add_argument("--lead-json", dest="lead_json", help="Lead como JSON string")
    p_score.add_argument("--lead-file", dest="lead_file", help="Archivo JSON del lead")

    # outreach
    p_out = subparsers.add_parser("outreach", help="Outreach para un lead")
    p_out.add_argument("--lead-json", dest="lead_json", help="Lead como JSON string")
    p_out.add_argument("--template", help="Nombre de plantilla")
    p_out.add_argument("--preview", action="store_true")
    p_out.add_argument("--linkedin", action="store_true")
    p_out.add_argument("--whatsapp", action="store_true")

    # version
    subparsers.add_parser("version", help="Mostrar versión")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "gui": cmd_gui,
        "discover": cmd_discover,
        "analyze": cmd_analyze,
        "person": cmd_person,
        "email": cmd_email,
        "score": cmd_score,
        "outreach": cmd_outreach,
        "version": cmd_version,
    }

    cmd_fn = dispatch.get(args.command)
    if cmd_fn:
        cmd_fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
