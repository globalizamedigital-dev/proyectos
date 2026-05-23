# Cazador Globalizame

Motor de generación de leads B2B para el mercado español. Descubre empresas por
sector y provincia, las enriquece con datos de fuentes públicas (BORME, PLACSP,
Infosubvenciones, AEPD, OpenStreetMap, webs corporativas), puntúa cada lead y
prepara campañas de outreach por email, LinkedIn y WhatsApp.

> **AVISO LEGAL IMPORTANTE — léelo antes de usar la app**
>
> Esta herramienta trata datos personales y permite enviar comunicaciones
> comerciales. En España, el envío de email comercial está regulado por la
> **LSSI-CE (art. 21)**, el **RGPD** y la **LOPDGDD**, y **como regla general
> requiere consentimiento previo o una base de interés legítimo documentada**.
>
> **Antes de lanzar cualquier campaña, lee
> [`docs/CUMPLIMIENTO_LEGAL.md`](docs/CUMPLIMIENTO_LEGAL.md)**, que incluye
> plantillas de ROPA y de test de interés legítimo (LIA) y un checklist de
> obligaciones legales. El uso indebido de esta herramienta es responsabilidad
> exclusiva del usuario.

---

## Qué hace

- **Descubrir**: busca empresas por provincia + sector/CNAE y las puntúa (0-100).
- **Analizar**: análisis completo de una empresa por NIF o razón social.
- **Enriquecer**: resuelve dominio web, decisores, emails y teléfonos.
- **Puntuar**: cada lead recibe un score y un grado A-D según su completitud.
- **Outreach**: prepara y envía emails personalizados con control de
  entregabilidad (throttle, cap diario) y de cumplimiento legal (lista de
  supresión, baja en cada email, gestión de rebotes).
- **Datastore**: todos los leads se guardan en una base SQLite con
  deduplicación entre ejecuciones.

---

## Requisitos

- **Python 3.11 o superior**.
- La funcionalidad principal usa **solo la biblioteca estándar** — no requiere
  instalar nada.
- Tkinter para la GUI (en Debian/Ubuntu: `sudo apt-get install python3-tk`).

## Instalación

```bash
git clone <repo>
cd leadhunter-pro

# (Opcional) dependencias que mejoran la funcionalidad y herramientas de build
pip install -r requirements.txt
```

## Configuración (.env)

Las credenciales SMTP **nunca** se guardan dentro de la aplicación: se leen de
un archivo `.env` que **no se versiona**.

```bash
cp .env.example .env
# Edita .env y rellena SMTP_USER, SMTP_PASSWORD, etc.
```

Para Gmail, usa una **Contraseña de aplicación**
(<https://myaccount.google.com/apppasswords>), no tu contraseña habitual.

Orden de búsqueda del `.env`:
1. La ruta de la variable de entorno `LEADHUNTER_ENV`.
2. `./.env` (directorio de trabajo).
3. `<raíz del proyecto>/.env`.
4. `~/.leadhunter.env`.

El archivo `.env` ya está en `.gitignore`. **No lo subas nunca al repositorio.**

## Uso

```bash
# Interfaz gráfica
python main.py gui

# Descubrir leads por provincia + sector
python main.py discover --geo Sevilla --sector "asesoría fiscal"
python main.py discover --geo Madrid --sector "desarrollo software" --max 100

# Analizar una empresa por NIF o razón social
python main.py analyze --input B12345678
python main.py analyze --input "Asesores García S.L."

# Otras utilidades
python main.py person  --razon-social "Empresa X" --domain empresa.es
python main.py email   --razon-social "Empresa X" --domain empresa.es
python main.py score   --lead-file lead.json
python main.py outreach --preview --lead-json '{...}'
python main.py version
```

Herramientas de cumplimiento y datos (CLI directa):

```bash
# Lista de supresión (bajas / opt-out)
python scripts/suppression.py add --email cliente@ejemplo.com
python scripts/suppression.py check --email cliente@ejemplo.com
python scripts/suppression.py list

# Base de datos de leads
python scripts/leads_db.py count
python scripts/leads_db.py query --min-score 50

# Estado de la configuración (sin exponer secretos)
python scripts/config.py --status
```

## Tests

```bash
python3 -m unittest tests.test_smoke -v
```

La suite usa solo `unittest` (stdlib) y funciona **sin conexión a red**.

## Construir el ejecutable Windows (.exe)

```bash
pip install pyinstaller

# Modo carpeta (arranque más rápido) — usa el spec incluido:
pyinstaller leadhunter.spec
# Resultado: dist/LeadHunterPro/LeadHunterPro.exe

# Modo onefile (un único .exe, arranque más lento):
pyinstaller --onefile --name LeadHunterPro --noconsole \
  --add-data "mappings;mappings" --add-data "templates;templates" \
  --add-data "docs;docs" --add-data "scripts;scripts" \
  --add-data "gui;gui" main.py
```

(En Linux/macOS, el separador de `--add-data` es `:` en lugar de `;`.)

## Estructura del proyecto

```
leadhunter-pro/
├── scripts/        Módulos del motor (fuentes, enriquecimiento, scoring,
│                   outreach, config, suppression, leads_db, _common)
├── mappings/       Mapeos de CNAE y provincias
├── templates/      Plantillas de email y HTML
├── docs/           Documentación de cumplimiento y entregabilidad
├── tests/          Suite de pruebas de humo (unittest)
├── gui/            Interfaz gráfica Tkinter
├── main.py         Punto de entrada CLI
├── leadhunter.spec Spec de PyInstaller
└── .env.example    Plantilla de configuración
```

## Documentación

- [`docs/CUMPLIMIENTO_LEGAL.md`](docs/CUMPLIMIENTO_LEGAL.md) — RGPD, LSSI-CE,
  plantillas de ROPA y LIA, checklist legal previo al outreach.
- [`docs/ENTREGABILIDAD_EMAIL.md`](docs/ENTREGABILIDAD_EMAIL.md) — configuración
  de SPF, DKIM, DMARC, calendario de warm-up y límites de envío.

## Privacidad y seguridad

- Las credenciales SMTP viven solo en `.env` (no versionado, no en JSON).
- Toda la información (leads, supresiones, envíos) se guarda **en local**, en
  bases SQLite bajo `~/.cache/leadhunter-pro/`.
- La lista de supresión se comprueba **antes de cada envío**.
- Cada email incluye un mecanismo de baja (`List-Unsubscribe` + "responde BAJA").
