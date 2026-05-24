# Cazador Globalizame

> Herramienta interna de Globalizame para **descubrir y cualificar
> leads B2B** a partir de fuentes oficiales españolas (BORME, OSM,
> Cartociudad, PLACSP, AEPD, INE/DIRCE, Infosubvenciones).
>
> **No es SaaS público. No hay cobros dentro de la app.** Lo usa el
> equipo de Globalizame para sus propios leads y para los clientes del
> Servicio Integral.
>
> **MVP recortado (2026-05-24): Cazador NO hace outreach automatizado.**
> Solo descubre, cualifica, persiste y exporta. El contacto con los
> leads se hace en los canales existentes de Globalizame (CRM, n8n,
> herramientas externas). El schema Supabase mantiene las tablas
> `outreach_*` por si vuelve, pero hoy no se usan desde la web.

---

## ⚖️ Aviso legal — léelo antes de usar

Esta herramienta trata datos personales y permite enviar comunicaciones
comerciales. En España, el envío de email comercial está regulado por
la **LSSI-CE (art. 21)**, el **RGPD** y la **LOPDGDD**, y **como regla
general requiere consentimiento previo o una base de interés legítimo
documentada**.

Antes de lanzar cualquier campaña, lee
[`docs/CUMPLIMIENTO_LEGAL.md`](docs/CUMPLIMIENTO_LEGAL.md). Incluye
plantillas de ROPA y test de interés legítimo (LIA), y un checklist de
obligaciones legales. El uso indebido es responsabilidad del operador.

---

## 📐 Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│  Fuentes oficiales españolas: BORME, OSM, Cartociudad,       │
│                               PLACSP, AEPD, INE, Infosub.    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ scripts/ · Python 3.12 │   ←── scrapling, urllib,
            │ adapters + parsing     │       playwright (opcional)
            └─────────┬──────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────┐         ┌──────────────────────┐
│ main.py CLI    │         │ api/ · FastAPI       │
│ gui/  Tkinter  │         │ /discover /analyze   │
│ (offline)      │         │ /privacy /health     │
└────────────────┘         └──────────┬───────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │ web/ · Next.js 16    │
                          │ Login magic-link     │
                          │ 5 pantallas + status │
                          └──────────────────────┘

                                      ▲
                                      │ stateful storage
                          ┌───────────┴──────────┐
                          │ Supabase (Frankfurt) │
                          │ globalizame-cazador  │
                          │ 9 tablas + RLS       │
                          └──────────────────────┘
```

Stack 100 % free-tier hasta que un cliente pague algo concreto. Ver
[`ARCHITECTURE.md`](ARCHITECTURE.md) para la versión larga y
[`.specify/specs/production-grade-platform/`](.specify/specs/production-grade-platform/)
para spec + plan + tasks.

---

## 🚀 Arranque rápido (local)

### Requisitos
- **Python 3.12+**
- **Node.js 24+** y npm
- Cuenta Supabase (proyecto `globalizame-cazador`, ya creado)
- Browser (Chrome / Firefox) para la web

### 1. Clonar y dependencias

```bash
git clone <repo>
cd proyectos/leadhunter-pro

# Python (incluye scrapling, fastapi, supabase-py, etc.)
pip install -r requirements.txt
pip install fastapi "uvicorn[standard]" pydantic-settings "pyjwt[crypto]" \
            cryptography httpx supabase python-json-logger \
            pytest pytest-asyncio

# Web
cd web && npm install && cd ..
```

### 2. Configurar credenciales

Hay **dos** archivos de credenciales locales, ambos gitignored:

| Archivo | Para | Cómo crearlo |
|---|---|---|
| `proyectos/leadhunter-pro/info` | Bandeja del operador. Vas pegando claves según las consigues; sirve como fuente única de verdad. | A mano. Formato `clave: valor`. |
| `.env` (raíz del proyecto) | Variables que lee el código Python (CLI, API). | A partir de `.env.example`. Lo rellena el operador con los valores de `info`. |
| `web/.env.local` | Variables que lee el código Next.js (frontend). | Solo `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` + `NEXT_PUBLIC_API_BASE_URL`. |

Valores mínimos para que arranque la web:

```bash
# .env (raíz)
SUPABASE_URL=https://tfdjnnkgoynrkmyekusv.supabase.co
SUPABASE_PROJECT_REF=tfdjnnkgoynrkmyekusv
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service_role key>

# web/.env.local
NEXT_PUBLIC_SUPABASE_URL=https://tfdjnnkgoynrkmyekusv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Levantar la app

Dos terminales:

```bash
# Terminal 1 — API FastAPI (puerto 8000)
cd api
uvicorn main:app --reload --port 8000

# Terminal 2 — Web Next.js (puerto 3000)
cd web
npm run dev
```

Abre **http://localhost:3000** → redirige a `/login`. Pega el email que
diste de alta en Supabase Auth → recibes magic link → click → entras a
`/discover`. La búsqueda llama al API real.

### 4. Dar de alta tu email para login

En Supabase Studio → Authentication → Users → **Add user**.
Email `mario@globalizame.com` (o el que sea). Después, en SQL editor:

```sql
insert into public.tenant_members (tenant_id, user_id, role)
select t.id, u.id, 'admin'
from public.tenants t, auth.users u
where t.slug = 'globalizame' and u.email = 'mario@globalizame.com'
on conflict do nothing;
```

---

## 🧪 Tests

```bash
# Python (scripts + GUI)
python -m unittest discover -s tests

# API (FastAPI)
cd api && python -m pytest tests/

# Web (typecheck + build)
cd web && npx tsc --noEmit && npm run build
```

Estado actual:
- Python: **62/62 OK**
- API: **14/14 OK**
- Web build: **verde** (9 rutas)

---

## 📦 GUI Tkinter offline (legacy)

La GUI Python sigue funcional como herramienta offline / standalone:

```bash
python main.py gui                                # ventana Tkinter
python main.py discover --geo Sevilla --sector "asesoría fiscal"
python main.py analyze --input B41234567
python main.py version
```

Para empaquetar `.exe` Windows:
```bash
pip install pyinstaller
pyinstaller leadhunter.spec
# Resultado: dist/LeadHunterPro/LeadHunterPro.exe
```

---

## 🗂️ Estructura

```
proyectos/leadhunter-pro/
├── scripts/        Adapters Python (BORME, OSM, AEPD…), scoring, dedup
├── api/            FastAPI thin layer · /discover /analyze /privacy /health
├── web/            Next.js 16 (App Router, TS strict, Tailwind v4, shadcn)
│   ├── src/app/
│   │   ├── (auth)/login        Magic link Supabase
│   │   ├── (app)/discover      Búsqueda de leads
│   │   ├── (app)/analizar      Análisis profundo + assertion-mismatch
│   │   ├── (app)/leads         Tabla persistida con filtros
│   │   ├── (app)/outreach      Cola + plantillas + preview
│   │   ├── (app)/config        SMTP · WA · Suppression · Equipo · Privacidad
│   │   └── auth/callback       Callback magic link
├── supabase/       Migraciones SQL aplicadas al proyecto globalizame-cazador
├── gui/            Tkinter (legacy / herramienta interna offline)
├── tests/          unittest suite Python
├── mappings/       CNAE + provincias
├── docs/           CUMPLIMIENTO_LEGAL · ENTREGABILIDAD_EMAIL · runbook
├── .specify/       Spec Kit · constitution + spec + plan + tasks
└── ARCHITECTURE.md Arquitectura objetivo (long form)
```

---

## 🆘 Algo ha petado

Mira [`docs/runbook.md`](docs/runbook.md) primero. Cubre los flujos
más comunes (build falla, API no responde, login no llega, mismatch
de schema Supabase, fuentes caídas).

---

## 📚 Más

- [`CHANGELOG.md`](CHANGELOG.md) — qué se hizo en cada release.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — visión técnica completa.
- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) —
  principios y reglas no negociables del proyecto.
- [`docs/CUMPLIMIENTO_LEGAL.md`](docs/CUMPLIMIENTO_LEGAL.md) — checklist
  legal antes de cualquier campaña.
- [`docs/ENTREGABILIDAD_EMAIL.md`](docs/ENTREGABILIDAD_EMAIL.md) — SPF /
  DKIM / DMARC + calendario de warm-up.
