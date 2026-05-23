# Cazador Globalizame · Plan de implementación

> Plan derivado de `spec.md` y `.specify/memory/constitution.md`.
> Mapea cada **FR** del spec a archivos, servicios y dependencias
> concretas. Stack 100 % free-tier hasta primer cliente.

---

## 1 · Resumen ejecutivo

Monorepo con dos workspaces en `proyectos/leadhunter-pro/`:

- `scripts/` + `main.py` + `gui/` · Python 3.12 — núcleo de scraping y
  GUI Tkinter (herramienta interna offline, ya existente).
- `web/` · Next.js 16 — app interna del equipo Globalizame (ya existe Discover).
- `api/` · FastAPI thin layer — **nuevo**, expone los módulos Python
  como REST para que `web/` los consuma.

Persistencia en un **proyecto Supabase nuevo y dedicado**
(`globalizame-cazador`, free tier, región Frankfurt). Inteligencia
contra **Google AI Studio** con la API key personal del operador (free
tier de Gemini 2.5 Flash). Outreach vía SMTP propio + Meta WhatsApp
Cloud API directa. Despliegue del frontend en Vercel; backend en Cloud
Run región `europe-west1`. Workers de ingesta en Cloud Run Jobs +
Cloud Scheduler.

---

## 2 · Tech stack (concreto)

### Lenguajes y frameworks
| Capa | Tech | Versión | Notas |
|---|---|---|---|
| Núcleo scraping | Python | 3.12 | Ya en uso, tests 55/55 OK tras commit `9cb32cb` |
| Stealth HTTP | **Scrapling** | ≥ 0.2 | BSD-3, gratis; reemplaza `urllib` en fuentes con WAF |
| Headless browser | **Playwright** (Python) | ≥ 1.40 | Solo cuando StealthyFetcher no basta (AEPD SPA) |
| API REST | **FastAPI** | ≥ 0.110 | Async-first, autodoc OpenAPI |
| Frontend | Next.js | 16.2.6 | App Router + Cache Components + Turbopack |
| UI | Tailwind v4 + shadcn (Base UI) | ya instalado | Branding Globalizame ya aplicado |
| Tipos | TypeScript strict | 5.x | `no any`, `no @ts-ignore` |
| DB SDK | `supabase-js` v2 (web) + `supabase-py` (Python) | última | Auth + DB + Realtime |
| LLM | Google AI Studio (Gemini 2.5 Flash) | API v1beta | Free tier 1.5k req/día |
| Orquestación | n8n self-hosted | 2.11.3 | Ya en VPS Globalizame |
| Email | SMTP propio (tenant) | — | `smtplib` stdlib |
| WhatsApp | Meta WhatsApp Cloud API | v20.0 | Free 1.000 conv/mes |

### Servicios externos (todos free tier)
| Servicio | Free tier | Uso |
|---|---|---|
| **Supabase** | 500 MB BD, 1 GB Storage, 50k MAU | BD + Auth + Storage + Realtime |
| **Vercel** | Hobby plan | Frontend Next.js deploy + previews |
| **Google Cloud** | 2M req/mes Cloud Run, 10GB Storage, 1M ops Cloud Tasks | Backend FastAPI + workers de ingesta |
| **Google AI Studio** | 1.5k req/día Gemini 2.5 Flash | Scoring, CNAE, entity res |
| **Meta WhatsApp Cloud API** | 1.000 conv/mes service-initiated | Canal WhatsApp |
| **Cloudflare** | Free plan | DNS + proxy del dominio |
| **GitHub Actions** | 2.000 min/mes en repos privados | CI/CD |

### Servicios pendientes de configurar (env vars)
Variables que el operador rellena en el deploy; ninguna se hardcodea:

```
# Supabase (proyecto globalizame-cazador · tfdjnnkgoynrkmyekusv)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=    # solo backend

# GCP / Vertex AI (proyecto existente globalizame-apis-493012)
GCP_PROJECT_ID=globalizame-apis-493012
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-service-account.json
VERTEX_AI_LOCATION=europe-west1
VERTEX_AI_MODEL=gemini-2.5-flash

# Meta WhatsApp Cloud API (un único tenant: Globalizame)
META_WA_PHONE_NUMBER_ID=
META_WA_ACCESS_TOKEN=
META_WA_VERIFY_TOKEN=

# SMTP de Globalizame — guardado cifrado en BD (no env)
```

> Stripe **no aplica**: Cazador es uso interno. Si en el futuro se
> abre como SaaS, se añade entonces.

---

## 3 · Estructura del repo (tras este plan)

```
proyectos/leadhunter-pro/
├── ARCHITECTURE.md
├── CHANGELOG.md                         # añadir
├── .specify/
│   ├── memory/constitution.md
│   ├── feature.json
│   └── specs/production-grade-platform/
│       ├── spec.md
│       └── plan.md                       # este archivo
│
├── scripts/                              # Python núcleo (existente)
│   ├── _common.py
│   ├── aepd.py · borme.py · cartociudad.py · ddg.py · dirce.py
│   ├── discover.py · analyze.py · cross.py
│   ├── domain_resolver.py · email_finder.py · web_contact.py
│   ├── infoempresa.py · infosubvenciones.py · placsp.py · osm.py
│   ├── lead_scorer.py · leads_db.py · outreach.py · person_finder.py
│   ├── suppression.py
│   ├── fetch_client.py                  # NUEVO · wrapper Scrapling
│   ├── llm_client.py                    # NUEVO · cliente Gemini con fallback
│   └── supabase_repo.py                 # NUEVO · reemplaza/complementa leads_db.py
│
├── api/                                  # NUEVO · FastAPI thin layer
│   ├── main.py                          # app FastAPI + routers
│   ├── deps.py                          # auth, db, settings
│   ├── routes/
│   │   ├── discover.py · analyze.py · enrich.py · health.py
│   │   ├── outreach.py · privacy.py · webhooks.py
│   ├── schemas/                         # Pydantic models
│   ├── workers/                         # Cloud Run Jobs entrypoints
│   │   ├── borme_daily.py · cleanup.py
│   ├── Dockerfile
│   └── pyproject.toml                   # deps separadas del core
│
├── web/                                  # Next.js 16 (existente)
│   ├── src/app/
│   │   ├── page.tsx                     # redirect → /discover
│   │   ├── layout.tsx                   # fuentes + dark mode
│   │   ├── (app)/                       # route group con shell
│   │   │   ├── layout.tsx               # sidebar + topbar + statusbar
│   │   │   ├── discover/                # ✅ existente
│   │   │   ├── analizar/                # NUEVO
│   │   │   ├── leads/                   # NUEVO
│   │   │   ├── outreach/                # NUEVO
│   │   │   ├── config/                  # NUEVO
│   │   ├── (auth)/                      # NUEVO · login / signup magic link
│   │   ├── api/                         # route handlers que proxyean a FastAPI
│   ├── src/lib/
│   │   ├── api-client.ts                # fetch wrapper con auth
│   │   ├── supabase-browser.ts          # cliente Supabase
│   │   └── supabase-server.ts
│   ├── src/components/                  # shell, score-chip, etc.
│   └── package.json
│
├── supabase/                             # NUEVO · schema + RLS + seeds
│   ├── migrations/
│   │   ├── 0001_init_tenants.sql
│   │   ├── 0002_leads.sql
│   │   ├── 0003_outreach.sql
│   │   ├── 0004_suppression.sql
│   │   ├── 0005_usage_events.sql
│   │   └── 0006_pgvector.sql
│   └── seed.sql                         # tenant demo "Globalizame"
│
├── tests/                                # ya existe; 55 OK
└── n8n/                                  # NUEVO · workflows exportados
    ├── discover-daily.json
    └── outreach-sequence.json
```

---

## 4 · Arquitectura por request

### 4.1 · Discover (FR-A, FR-B, FR-D, FR-E)

```
[web/discover] ──fetch──> [api/routes/discover]
                              │
                              ├─ scripts/discover.py (existente)
                              │     ├─ borme.py        (fetch_plain)
                              │     ├─ osm.py          (fetch_stealthy)
                              │     ├─ cartociudad.py  (fetch_plain)
                              │     ├─ placsp.py       (fetch_plain)
                              │     └─ ddg.py          (fetch_stealthy)
                              │
                              ├─ llm_client.score()    Gemini 2.5 Flash
                              ├─ supabase_repo.upsert_leads()
                              └─ devuelve JSON (schema 2.0.0) ──> tabla web
```

### 4.2 · Analyze (FR-A, FR-B, FR-D, FR-E)

```
[web/analizar] ──fetch──> [api/routes/analyze]
                              │
                              ├─ scripts/analyze.py (existente)
                              │     ├─ borme.analyze_by_nif
                              │     ├─ placsp.by_nif
                              │     ├─ infosubvenciones.by_nif
                              │     ├─ aepd.lookup_dpo    (fetch_dynamic, Playwright)
                              │     └─ infoempresa.lookup (fetch_stealthy)
                              │
                              ├─ llm_client.entity_resolve()
                              ├─ assertion_check(user_claims, evidence)
                              └─ devuelve ficha + assertion_mismatch?
```

### 4.3 · Outreach send (FR-G, FR-H)

```
[web/outreach] ──fetch──> [api/routes/outreach.send]
                              │
                              ├─ suppression.check(emails)
                              ├─ template_engine.render(lead, template)
                              │     └─ llm_client.personalize() opcional
                              │
                              ├─ encolar en n8n queue (webhook)
                              │     │
                              │     ├─ smtp_send_node → SMTP propio del tenant
                              │     └─ whatsapp_send_node → Meta WA Cloud API
                              │
                              └─ outreach_events INSERT (sent)

[webhook bounce] ─> /webhooks/bounce → mark_bounced + suppression INSERT
[unsubscribe link] ─> /unsubscribe?token → suppression INSERT
```

### 4.4 · Ingesta continua (FR-A2)

```
Cloud Scheduler (cron diario 06:00) ─> Cloud Run Job (borme_daily.py)
                                              │
                                              ├─ borme.fetch_summary(date)
                                              ├─ Cloud Storage: snapshot raw XML
                                              ├─ borme.parse → leads candidatos
                                              └─ supabase_repo.upsert_batch
```

---

## 5 · Fases de implementación

> Cada fase termina con commit, push, tests verdes y demo navegable.
> Numeración no es estricta; algunas pueden paralelizarse.

### Sprint 0 · Cimientos (1-2 días)
- [ ] Crear proyecto Supabase `globalizame-cazador` (consola).
- [ ] Migraciones SQL iniciales (`0001..0006`) con RLS activado.
- [ ] Aplicar migraciones vía Supabase MCP (`apply_migration`).
- [ ] Generar tipos TS con `mcp__supabase__generate_typescript_types`.
- [ ] Crear `.env.example` consolidado para web/, api/, scripts/.
- [ ] CI GitHub Actions: type-check + pytest + lint (path filters).

**FRs cubiertos**: E0, E1, E2, E3, E4, E5, I1, I5.

### Sprint 1 · Scrapling Fase A (1 día)
- [ ] `pip install scrapling playwright; playwright install chromium`.
- [ ] `scripts/fetch_client.py` con tres APIs (`plain`, `stealthy`, `dynamic`) y misma firma `(int, str)` que el actual.
- [ ] Migrar `ddg.py`, `infoempresa.py`, `aepd.py`, `osm.py` (overpass).
- [ ] Tests: verificar `aepd` ya no devuelve `js-spa`.

**FRs cubiertos**: A3, A4, A5.

### Sprint 2 · FastAPI thin layer (2 días)
- [ ] `api/` workspace con FastAPI + Uvicorn.
- [ ] Endpoints `POST /discover`, `POST /analyze`, `GET /health/sources`.
- [ ] Auth middleware Supabase JWT (verifica firma con jwks).
- [ ] Pydantic schemas que reflejen el shape de los snapshots existentes (`schemaVersion: "2.0.0"`).
- [ ] Dockerfile multi-stage; deploy a Cloud Run con `gcloud run deploy`.

**FRs cubiertos**: B1, B2, B3, B5.

### Sprint 3 · Integración web ↔ API (1 día)
- [ ] `web/src/lib/api-client.ts` con `fetch` autenticado.
- [ ] `discover-client.tsx` cambia el `setTimeout` mock por `await api.discover(...)`.
- [ ] Auth Supabase magic link en `(auth)/` con redirect a `/discover`.
- [ ] Tests E2E mínimos con Playwright en CI: login → discover → ver leads.

**FRs cubiertos**: F1, F2, F3, F4.

### Sprint 4 · Pantallas restantes (3 días)
- [ ] `/analizar` con input NIF/RS, llamada `/analyze`, render ficha + banner assertion_mismatch.
- [ ] `/leads` tabla persistida con filtros, multi-select, paginación virtualizada.
- [ ] `/outreach` cola, preview con merge tags, confirmación, dispatch.
- [ ] `/config` SMTP + WhatsApp + suppression manual + miembros.

**FRs cubiertos**: F5, F6, F7, F8, F9, G1, G2, G4.

### Sprint 5 · Outreach + n8n (2 días)
- [ ] Workflow n8n `outreach-sequence.json` exportado y versionado.
- [ ] Webhook receivers en API: bounce, unsubscribe, reply.
- [ ] `/unsubscribe` endpoint público.
- [ ] Suppression cross-canal verificada por test.

**FRs cubiertos**: G3, G5, H1, H4.

### Sprint 6 · Privacy + compliance (1 día)
- [ ] `POST /privacy/export` → JSON con leads + outreach + suppression del sujeto.
- [ ] `DELETE /privacy/erase` → borrado real.
- [ ] Pantalla `/config → privacidad` con los dos botones.

**FRs cubiertos**: H2, H3.

### Sprint 7 · Inteligencia (Gemini, 2 días)
- [ ] `scripts/llm_client.py` con cliente AI Studio + caché Supabase + circuit-breaker (degrada a heurístico si 429/timeout).
- [ ] `resolve_entity()`, `classify_cnae()`, `score_lead()`, `personalize_copy()`.
- [ ] Regression suite con ≥ 20 pares de entity resolution.

**FRs cubiertos**: D1, D2, D3, D4, D5.

### Sprint 8 · Ingesta diaria BORME (1-2 días)
- [ ] `api/workers/borme_daily.py` worker idempotente.
- [ ] Cloud Run Job + Cloud Scheduler cron `0 6 * * *`.
- [ ] Cloud Storage bucket `leadhunter-raw-{env}`.

**FRs cubiertos**: A1, A2, A6, I2.

### Sprint 9 · Observabilidad (1 día)
- [ ] Logs estructurados JSON desde FastAPI a Cloud Logging.
- [ ] Métricas a Cloud Monitoring: `discover_latency_p95`, `leads_per_search`, `bounce_rate`.
- [ ] Dashboard básico en Cloud Monitoring.
- [ ] `/health` agregado con db, sources, queue depth.

**FRs cubiertos**: I3, I4.

---

## 6 · Mapping FR → archivo / servicio

| FR | Archivo / servicio | Estado |
|---|---|---|
| A1, A6 | `scripts/discover.py` | Existente, mantener |
| A2 | `api/workers/borme_daily.py` + Cloud Scheduler | Sprint 8 |
| A3 | Adapters `scripts/*.py` | Endurecido en commit `9cb32cb` |
| A4 | `scripts/fetch_client.py` | Sprint 1 |
| A5 | timeouts ya aplicados | Mantener |
| B1-B5 | `api/` workspace | Sprint 2 |
| C1-C3 | `scripts/domain_resolver.py`, `email_finder.py`, `web_contact.py` | Existente |
| C4 | tabla `usage_events` en Supabase | Sprint 0 |
| D1-D5 | `scripts/llm_client.py` | Sprint 7 |
| E0-E5 | Supabase + migraciones | Sprint 0 |
| F1-F9 | `web/src/app/(app)/*` | Sprint 3 + 4 |
| G1-G5 | n8n workflows + `api/routes/outreach.py` | Sprint 5 |
| H1-H4 | `api/routes/privacy.py` + `/unsubscribe` | Sprint 6 |
| I1-I5 | GitHub Actions + Cloud Logging | Sprint 0 + 9 |

---

## 7 · Decisiones de diseño explícitas

1. **Monorepo, no microrepos.** El núcleo Python sigue siendo la fuente
   de verdad; FastAPI lo envuelve. Mover web a otro repo añade fricción
   sin beneficio en esta fase.

2. **API thin, no fat.** FastAPI NO duplica lógica de scripts. Solo
   serializa, autentica y devuelve. Cualquier cambio funcional toca
   `scripts/`, no `api/`.

3. **Schema 2.0.0 estable.** Los snapshots JSON actuales mantienen
   `schemaVersion: "2.0.0"`. La API devuelve el mismo shape para no
   romper la GUI Tkinter existente, que sigue funcionando offline.

4. **Supabase como single source of truth.** Adiós SQLite local en
   producción. La GUI Tkinter se conecta a Supabase con la anon key
   cuando hay red, o sigue con SQLite cuando trabaja offline. Sync
   opcional pendiente (no MVP).

5. **n8n para orquestación de outreach, no en API.** FastAPI dispara
   webhooks a n8n self-hosted (`n8n.globalizame.cloud`). Throttling,
   retries y secuencias multi-paso viven ahí; FastAPI permanece
   stateless.

6. **Cero servicios de pago en MVP.** Todos los upgrades de pago (ver
   `spec.md § 5`) están detrás de feature flags `feature_einforma:
   bool`, `feature_neverbounce: bool`, etc. Por defecto `false`.

7. **Web abre sesión, no la mantiene en server.** Cookies HTTPOnly de
   Supabase Auth, sin estado de servidor. La FastAPI valida JWT cada
   request, no guarda sesión.

8. **Dark-first.** Toda pantalla diseñada en dark; light es derivado.

---

## 8 · Dependencias nuevas a instalar

### Python (en `scripts/` y `api/`)
```
# scripts/requirements.txt — añadir:
scrapling>=0.2
playwright>=1.40
google-generativeai>=0.8
supabase>=2.0

# api/pyproject.toml — nuevo workspace:
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.6
pydantic-settings>=2.2
httpx>=0.27
python-jose[cryptography]>=3.3   # JWT
google-cloud-storage>=2.16
google-cloud-tasks>=2.16
```

### Web (en `web/package.json`)
```
@supabase/supabase-js
@supabase/ssr           # Auth con cookies en App Router
zod                     # validación cliente
@tanstack/react-table   # /leads tabla virtualizada
```

### Plataforma
- Playwright Chromium descargado en CI y en Cloud Run image.
- gcloud CLI en CI para deploy.
- Supabase CLI para migraciones locales (`supabase db push`).

---

## 9 · CI / CD

`.github/workflows/ci.yml`:
- **on push/pr**: type-check TS (`web`), pytest (`scripts` + `api`),
  ruff lint Python.
- **on push main**: deploy `web/` a Vercel (vía Vercel GH integration),
  deploy `api/` a Cloud Run con `gcloud run deploy --source api/`,
  push migraciones Supabase si `supabase/migrations/` cambió.
- Previews automáticas en Vercel por PR.

---

## 10 · Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Gemini free tier insuficiente | Media | Caché agresivo en Supabase + circuit-breaker a heurístico |
| Meta WhatsApp 1k conv/mes corto en demos | Baja | Métricas + activar YCloud cuando se acerque al límite |
| Scrapling rompe import de adapters viejos | Media | `fetch_client.py` con misma firma; rollback por env var `USE_SCRAPLING=false` |
| Supabase free tier insuficiente para corpus BORME | Baja-Media | Mover snapshots crudos a Cloud Storage; BD solo guarda lo estructurado |
| Cloud Run cold start lento | Media | Min instances = 1 cuando haya tráfico real; antes irrelevante |
| Tests Python rompen tras refactor a `fetch_client` | Alta | Tests primero (TDD) en Sprint 1; mock de Scrapling |
| Auth JWT mal validado en API | Media | Lib `python-jose` con jwks dinámico desde Supabase |
| SMTP del tenant bloqueado por spam | Alta | Validar SPF/DKIM al guardar config; warnings en `/config` |

---

## 11 · Pendiente del operador antes de empezar Sprint 0

1. **Crear proyecto Supabase** `globalizame-cazador` en consola
   (Frankfurt, free tier) y pasar el `project-ref` para completar
   `FR-E0`.
2. **Crear API key Gemini** en `aistudio.google.com` y guardarla en
   1Password (provisional) — luego se migra a Secret Manager.
3. **Confirmar SMTP de Globalizame para demos**: Hostinger del
   dominio `globalizame.com` (preferido) o Gmail con App Password.
4. **App Meta WhatsApp Business** dada de alta para tener phone-number-ID
   y access token.

Con estos 4 puntos el Sprint 0 arranca sin bloqueos.

---

*Plan vigente desde 2026-05-23. Cualquier desviación → PR que
modifique este archivo + justificación.*
