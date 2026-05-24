# Cazador Globalizame · Tareas ejecutables

> Desglose dependiente del [plan](./plan.md). Cada task es pequeña,
> accionable y vinculada a un archivo concreto.
>
> Convenciones:
> - `[OP]` = tarea del operador (Mario), bloquea las siguientes.
> - `[CL]` = ejecutable por Claude en sesión.
> - Marca con `[x]` cuando esté hecha en commit. Reusa estos IDs en
>   los mensajes de commit (`T042: api/deps.py JWT middleware`).
> - El orden dentro de cada fase implica dependencia (no
>   paralelizar salvo nota explícita).

---

## Fase 0 · Prerequisitos del operador (bloqueante)

Sin estos 5, Sprint 0 no arranca. Son todos one-off, externos al repo.

- [x] **[T001][OP]** Crear proyecto Supabase `globalizame-cazador` en https://supabase.com — región **eu-central-1 Frankfurt**, plan **Free**, password de DB guardado en 1Password.
- [ ] **[T002][OP]** En el proyecto recién creado, copiar `Project URL`, `anon key`, `service_role key` y `project ref`. Anotar para Sprint 0.
- [ ] **[T003][OP]** Generar API key Gemini en https://aistudio.google.com → guardar como `GEMINI_API_KEY` en 1Password.
- [ ] **[T004][OP]** Confirmar SMTP demo de Globalizame: o bien Hostinger del dominio `globalizame.com`, o bien Gmail con App Password. Anotar host, port, user, pass.
- [ ] **[T005][OP]** Dar de alta la app Meta WhatsApp Business en https://developers.facebook.com — obtener `phone_number_id`, `access_token` (System User), `verify_token` y registrar webhook URL placeholder.

---

## Fase 1 · Sprint 0 · Cimientos

### 1.A · Infraestructura local

- [x] **[T010][CL]** Crear `.env.example` raíz con todas las claves consolidadas y placeholders comentados. Path: `proyectos/leadhunter-pro/.env.example`
- [x] **[T011][CL]** Crear `web/.env.local.example` con `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `API_BASE_URL`. Path: `web/.env.local.example`
- [x] **[T012][CL]** Añadir `.env*` real al `.gitignore` raíz si no está. Path: `proyectos/leadhunter-pro/.gitignore`

### 1.B · Migraciones Supabase

- [x] **[T013][CL]** `supabase/migrations/0001_init_tenants.sql` — tablas `tenants`, `tenant_members`, función `current_tenant_id()`.
- [x] **[T014][CL]** `supabase/migrations/0002_leads.sql` — tabla `leads` con `dedup_key`, `score`, `grade`, JSONB `data`, índices por `nif`, `score`, `provincia`, `outreach_status`.
- [x] **[T015][CL]** `supabase/migrations/0003_outreach.sql` — tablas `outreach_events`, `outreach_templates`, `outreach_sequences`.
- [x] **[T016][CL]** `supabase/migrations/0004_suppression.sql` — tabla `suppression` con clave compuesta `(tenant_id, channel, identifier)` y trigger de uppercase en NIF.
- [x] **[T017][CL]** `supabase/migrations/0005_usage_events.sql` — tabla `usage_events` para Gemini y Meta WA.
- [x] **[T018][CL]** `supabase/migrations/0006_pgvector.sql` — `CREATE EXTENSION vector` + tabla `leads_embeddings (lead_id, embedding vector(768))`.
- [x] **[T019][CL]** `supabase/migrations/0007_rls.sql` — políticas RLS para todas las tablas anteriores: `tenant_members.user_id = auth.uid()`.
- [x] **[T020][CL]** `supabase/seed.sql` — un tenant demo "Globalizame" con `slug=globalizame`.
- [x] **[T021][CL]** Aplicar migraciones al proyecto Supabase nuevo usando `mcp__supabase__apply_migration` una por una (ID = nombre del archivo sin extensión).
- [x] **[T022][CL]** Aplicar seed con `mcp__supabase__execute_sql`. Verificar con `list_tables`.
- [x] **[T023][CL]** Lanzar `mcp__supabase__get_advisors` (security + performance) y arreglar warnings antes de continuar.

### 1.C · Cliente Supabase en web

- [x] **[T024][CL]** Instalar deps en web: `npm i @supabase/supabase-js @supabase/ssr zod @tanstack/react-table`. Path: `web/package.json`
- [x] **[T025][CL]** Crear `web/src/lib/supabase-browser.ts` — `createBrowserClient` para uso en client components.
- [x] **[T026][CL]** Crear `web/src/lib/supabase-server.ts` — `createServerClient` con `cookies()` de Next.
- [x] **[T027][CL]** Generar `web/src/lib/database.types.ts` vía `mcp__supabase__generate_typescript_types` y commitear.

### 1.D · CI/CD

- [x] **[T028][CL]** Crear `.github/workflows/ci.yml` con jobs: `lint-web` (eslint), `typecheck-web` (tsc), `test-python` (pytest), `lint-python` (ruff). Path filters por workspace.
- [x] **[T029][CL]** Crear `.github/workflows/deploy.yml` con triggers `push: main` y jobs separados deploy-web (Vercel) + deploy-api (Cloud Run, placeholder hasta Sprint 2).
- [ ] **[T030][OP]** Conectar el repo a Vercel (importar `web/` como root), añadir env vars en dashboard.

---

## Fase 2 · Sprint 1 · Scrapling Fase A

### 2.A · Setup

- [x] **[T040][CL]** Añadir `scrapling>=0.2`, `playwright>=1.40` y `google-generativeai>=0.8` a `proyectos/leadhunter-pro/requirements.txt`.
- [x] **[T041][CL]** Crear `scripts/fetch_client.py` con tres funciones: `fetch_plain(url, **kw) -> (int, str)`, `fetch_stealthy(url, **kw) -> (int, str)`, `fetch_dynamic(url, wait_for=None, **kw) -> (int, str)`. Misma firma que `http_get` actual.
- [x] **[T042][CL]** Feature flag `LEADHUNTER_USE_SCRAPLING=true` en `_common.py` para permitir rollback rápido a urllib.
- [x] **[T043][CL]** Crear `tests/test_fetch_client.py` con tests mockeados para los 3 modos.

### 2.B · Migración de adapters

- [x] **[T044][CL]** Migrar `scripts/ddg.py` para usar `fetch_stealthy`; el UA de Chrome real ya no hace falta hardcodeado.
- [x] **[T045][CL]** Migrar `scripts/infoempresa.py` para usar `fetch_stealthy` en los 3 endpoints. Mantener `_INFOEMPRESA_MIN_BODY` como guard.
- [x] **[T046][CL]** Migrar `scripts/aepd.py` para usar `fetch_dynamic` en el endpoint `sedeaepd.gob.es` (espera al selector `[data-testid="dpo-results"]` con timeout 8s).
- [x] **[T047][CL]** Migrar `scripts/osm.py` `query_overpass()` para usar `fetch_stealthy`. Si funciona, simplificar de 3 mirrors a 1 (overpass-api.de).
- [x] **[T048][CL]** Correr `python -m unittest discover -s tests` y verificar 55+ verde.
- [x] **[T049][CL]** Smoke `python main.py discover --geo Sevilla --sector "asesoría fiscal" --max 5` y `analyze --input "Asesoria Camen S.L."` — output esperado en `SourceStatus`: `AEPD: ok` o `endpoint-changed` documentado (no `js-spa`).

---

## Fase 3 · Sprint 2 · FastAPI thin layer

### 3.A · Scaffold

- [x] **[T050][CL]** Crear `api/pyproject.toml` con FastAPI, uvicorn, pydantic-settings, python-jose, supabase-py.
- [x] **[T051][CL]** Crear `api/main.py` con `FastAPI()`, CORS, middleware de logging estructurado, OpenAPI tags.
- [x] **[T052][CL]** Crear `api/settings.py` con `pydantic_settings.BaseSettings` leyendo env vars.
- [x] **[T053][CL]** Crear `api/deps.py` con dependencia `get_current_user()` que valida JWT Supabase contra JWKS.
- [x] **[T054][CL]** Crear `api/db.py` con cliente Supabase compartido (`service_role` para escrituras backend).

### 3.B · Schemas y rutas

- [x] **[T055][CL]** `api/schemas/common.py` — `Lead`, `SourceStatus`, `SchemaVersion = "2.0.0"`.
- [x] **[T056][CL]** `api/schemas/discover.py` — request/response del endpoint.
- [x] **[T057][CL]** `api/schemas/analyze.py` — request/response.
- [x] **[T058][CL]** `api/routes/discover.py` — `POST /discover`, llama a `scripts.discover.discover()`.
- [x] **[T059][CL]** `api/routes/analyze.py` — `POST /analyze`, llama a `scripts.analyze.analyze()`.
- [x] **[T060][CL]** `api/routes/health.py` — `GET /health` y `GET /health/sources`.
- [x] **[T061][CL]** `api/tests/test_health.py` y `test_auth.py` (401 sin token, 200 con token válido mockeado).

### 3.C · Deploy

- [x] **[T062][CL]** Crear `api/Dockerfile` multi-stage: Python 3.12 slim + `playwright install chromium` + `scripts/` montado como módulo importable.
- [x] **[T063][CL]** Crear `api/.dockerignore` para excluir `__pycache__`, `tests/`, `.venv`.
- [x] **[T064][OP]** Crear proyecto GCP `globalizame-cazador`, habilitar Cloud Run y Cloud Build.
- [ ] **[T065][CL]** Deploy inicial con `gcloud run deploy api --source api/ --region europe-west1 --allow-unauthenticated=false`.
- [ ] **[T066][CL]** Configurar las env vars del runtime en Cloud Run (Supabase URL/key, Gemini key) vía `gcloud run services update`.
- [ ] **[T067][CL]** Actualizar `.github/workflows/deploy.yml` para automatizar el deploy api en push a `main`.

---

## Fase 4 · Sprint 3 · Web ↔ API real

- [x] **[T070][CL]** `web/src/lib/api-client.ts` — fetch wrapper con `Authorization: Bearer {sessionToken}` automático.
- [x] **[T071][CL]** `web/src/app/(auth)/login/page.tsx` — formulario magic link con marca Globalizame.
- [x] **[T072][CL]** `web/src/app/(auth)/callback/route.ts` — route handler para el callback Supabase.
- [x] **[T073][CL]** `web/src/middleware.ts` — proteger `(app)/*` con redirect a `/login` si no hay sesión.
- [x] **[T074][CL]** Reemplazar el `setTimeout` mock en `web/src/app/(app)/discover/_components/discover-client.tsx` por `api.discover({province, sector, max, enrich})`.
- [x] **[T075][CL]** Manejar errores de red en la UI: banner rojo si `api.discover` falla, mantener estado navegable.
- [ ] **[T076][CL]** Tests E2E con Playwright en `web/tests/e2e/`: login con magic link mockeado → discover → ver leads.
- [x] **[T077][CL]** Ajustar `web/src/components/app-shell/status-bar.tsx` para consumir `/health/sources` vivo en lugar de mocks.

---

## Fase 5 · Sprint 4 · Pantallas restantes

### 5.A · Analizar

- [x] **[T080][CL]** `web/src/app/(app)/analizar/page.tsx` — server component shell.
- [x] **[T081][CL]** `web/src/app/(app)/analizar/_components/analyze-form.tsx` — input NIF o razón social + opción premium (placeholder).
- [x] **[T082][CL]** `web/src/app/(app)/analizar/_components/ficha.tsx` — render con secciones (registralTimeline, decisores, web, compliance, sector público, subvenciones).
- [x] **[T083][CL]** `web/src/app/(app)/analizar/_components/assertion-banner.tsx` — banner naranja cuando hay `assertion_mismatch`.

### 5.B · Leads (tabla persistida)

- [x] **[T084][CL]** `web/src/app/(app)/leads/page.tsx` — server component que pre-carga la primera página desde Supabase.
- [x] **[T085][CL]** `web/src/app/(app)/leads/_components/leads-table.tsx` — `@tanstack/react-table` con virtualización, sort y paginación.
- [x] **[T086][CL]** `web/src/app/(app)/leads/_components/filters-bar.tsx` — provincia, sector, score≥X, status.
- [x] **[T087][CL]** `web/src/app/(app)/leads/_components/bulk-actions.tsx` — multi-select + "Añadir a Outreach".

### 5.C · Outreach

- [x] **[T088][CL]** `web/src/app/(app)/outreach/page.tsx` — server shell.
- [x] **[T089][CL]** `web/src/app/(app)/outreach/_components/queue.tsx` — leads en cola con avatar/empresa/email.
- [x] **[T090][CL]** `web/src/app/(app)/outreach/_components/template-picker.tsx` — selector + preview del template renderizado.
- [x] **[T091][CL]** `web/src/app/(app)/outreach/_components/send-modal.tsx` — confirmación con resumen "vas a enviar a N · {emails preview}".

### 5.D · Config

- [x] **[T092][CL]** `web/src/app/(app)/config/page.tsx` — layout con tabs SMTP · WhatsApp · Suppression · Equipo · Privacidad.
- [x] **[T093][CL]** `web/src/app/(app)/config/_components/smtp-form.tsx` — input host/port/user/pass + botón "Probar SMTP".
- [x] **[T094][CL]** `web/src/app/(app)/config/_components/whatsapp-form.tsx` — phone-number-id, access token, verify token, webhook URL (copiable).
- [x] **[T095][CL]** `web/src/app/(app)/config/_components/suppression-list.tsx` — tabla + botón "añadir manual" + import CSV.
- [x] **[T096][CL]** `web/src/app/(app)/config/_components/team-members.tsx` — invitar email / cambiar rol / eliminar.

---

## Fase 6 · Sprint 5 · Outreach + n8n

- [~] **~~[T100]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** `api/routes/outreach.py` — `POST /outreach/send` que valida suppression, renderiza template y dispara webhook n8n.
- [~] **~~[T101]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** `scripts/whatsapp_client.py` — wrapper de Meta WhatsApp Cloud API directa (send_text, send_template).
- [~] **~~[T102]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** Actualizar `scripts/outreach.py` para aceptar canal `email|whatsapp`.
- [~] **~~[T103]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[OP]** Crear workflow n8n `outreach-sequence` en `n8n.globalizame.cloud`: Webhook → switch canal → SMTP / WA → log a Supabase.
- [~] **~~[T104]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** Exportar el JSON del workflow a `n8n/outreach-sequence.json` para versionado.
- [~] **~~[T105]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** `api/routes/webhooks.py` — `POST /webhooks/bounce`, `POST /webhooks/reply`, `POST /webhooks/whatsapp-status`.
- [~] **~~[T106]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** `api/routes/privacy.py` — `GET /unsubscribe?token={signed}` que añade el email a suppression y renderiza una página HTML simple de confirmación.
- [~] **~~[T107]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** Validador SPF + DKIM en `scripts/smtp_config.py` que corre al guardar SMTP del tenant; warnings en UI si fallan.
- [~] **~~[T108]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** Test integración: añadir suppression → intentar enviar → debe registrar `skipped: suppressed` en `outreach_events`.

---

## Fase 7 · Sprint 6 · Privacy + compliance

- [x] **[T120][CL]** `api/routes/privacy.py` — `POST /privacy/export` devuelve JSON con todos los datos del sujeto.
- [x] **[T121][CL]** `api/routes/privacy.py` — `DELETE /privacy/erase` borra leads + outreach_events + embeddings.
- [x] **[T122][CL]** `web/src/app/(app)/config/_components/privacy-panel.tsx` — botones Export GDPR / Erase, input para email/NIF.
- [~] **~~[T123]~~** (descartada · scope-cut MVP 2026-05-24, sin outreach)[CL]** Plantillas email cold incluyen link a `/unsubscribe?token` por defecto; render falla si falta.
- [ ] **[T124][CL]** Test E2E: lead → outreach event → export → erase → consulta posterior devuelve 0 filas.

---

## Fase 8 · Sprint 7 · Inteligencia (Gemini free tier)

- [ ] **[T130][CL]** `scripts/llm_client.py` — clase `Gemini` con `generate_json(prompt, schema)`, caché Supabase por `hash(prompt)`, timeout 15s.
- [ ] **[T131][CL]** `scripts/llm_client.resolve_entity(a, b)` — devuelve `{match: bool, confidence: high|med|low, rationale}`.
- [ ] **[T132][CL]** `scripts/llm_client.classify_cnae(text)` — devuelve `{cnae: "6920", confidence}`.
- [ ] **[T133][CL]** `scripts/llm_client.score_lead(lead)` — devuelve `{score: 0..100, grade: A|B|C|D, rationale}`. Fallback a `lead_scorer.score_lead()` heurístico.
- [ ] **[T134][CL]** `scripts/llm_client.personalize_copy(lead, template_text)` — devuelve `{subject, body}` en estilo Isra Bravo.
- [ ] **[T135][CL]** Circuit breaker: tras 3 errores 429 consecutivos en 1 min, deshabilitar Gemini durante 5 min y usar fallbacks.
- [ ] **[T136][CL]** `tests/test_llm_regression.py` con 20 casos de entity resolution y CNAE classification.
- [ ] **[T137][CL]** Integrar `resolve_entity` en `scripts/discover.py` dedup y `analyze.py` cross-source.

---

## Fase 9 · Sprint 8 · Ingesta diaria BORME

- [ ] **[T150][CL]** `api/workers/borme_daily.py` — idempotente: lee fecha de ejecución, baja sumario BORME, parsea, upsert en Supabase, snapshot raw en Cloud Storage.
- [ ] **[T151][CL]** `api/workers/Dockerfile.worker` — imagen separada del API, solo con `scripts/` + worker.
- [ ] **[T152][OP]** Crear bucket `gs://leadhunter-raw-prod` en `europe-west1`, ACL privado.
- [ ] **[T153][CL]** Deploy Cloud Run Job: `gcloud run jobs create borme-daily --source api/workers/ --region europe-west1`.
- [ ] **[T154][CL]** Crear Cloud Scheduler job: `gcloud scheduler jobs create http borme-cron --schedule "0 6 * * *" --time-zone Europe/Madrid --uri ${JOB_URL}`.
- [ ] **[T155][CL]** Tras 24h, verificar manualmente: 1 snapshot en bucket + ≥10 filas nuevas en `leads`.

---

## Fase 10 · Sprint 9 · Observabilidad

- [ ] **[T160][CL]** `api/logging_config.py` con `python-json-logger`; cada log lleva `trace_id`, `tenant_id`, `user_id`.
- [ ] **[T161][CL]** Configurar Cloud Logging sink desde Cloud Run a un bucket de retención 30 días.
- [ ] **[T162][CL]** Definir 4 métricas custom Cloud Monitoring: `discover_latency_p95`, `leads_per_search`, `bounce_rate`, `gemini_cost_units_used`. Path: `infra/monitoring/metrics.yaml` (Terraform o gcloud commands documentados).
- [ ] **[T163][CL]** Crear dashboard "Cazador Globalizame" en Cloud Monitoring, exportar JSON a `infra/monitoring/dashboard.json`.
- [ ] **[T164][CL]** Ampliar `GET /health` con campos `db`, `sources` (snapshot), `queue_depth` (consulta a n8n) y `gemini_quota_remaining`.
- [ ] **[T165][CL]** Alert policy: `bounce_rate > 5%` o `gemini_quota_remaining < 10%` → email a Mario.

---

## Fase 11 · Polish y release

- [x] **[T180][CL]** `README.md` reescrito con setup completo (clonar → env vars → `npm i` web → `pip install` api → migraciones → run).
- [x] **[T181][CL]** `CHANGELOG.md` con versión `0.2.0 — production-grade platform MVP`, citando commits clave (`9cb32cb` auditoría, hashes de cada sprint).
- [x] **[T182][CL]** Error boundaries en cada pantalla `(app)/*/error.tsx` con copy en marca.
- [ ] **[T183][CL]** Auditoría rápida axe-core sobre las 5 pantallas; arreglar al menos los `serious`/`critical`.
- [ ] **[T184][CL]** Smoke test producción end-to-end: login real → discover real → analyze real → outreach send a buzón de Mario → ver evento `sent` → unsubscribe → ver evento `unsubscribed` → erase GDPR.
- [x] **[T185][CL]** `docs/runbook.md` con: cómo desplegar, cómo revertir, qué hacer si Gemini se agota, qué hacer si Supabase está caído, dónde están los logs.
- [x] **[T186][CL]** Tag de release `v0.2.0-mvp` en GitHub + nota de release.

---

## Resumen por contador

| Fase | Tasks | Operador | Claude |
|---|---|---|---|
| 0 Prerequisitos | 5 | 5 | 0 |
| 1 Cimientos | 21 | 1 | 20 |
| 2 Scrapling | 10 | 0 | 10 |
| 3 FastAPI | 18 | 1 | 17 |
| 4 Web ↔ API | 8 | 0 | 8 |
| 5 Pantallas | 17 | 0 | 17 |
| 6 Outreach n8n | 9 | 1 | 8 |
| 7 Privacy | 5 | 0 | 5 |
| 8 Gemini | 8 | 0 | 8 |
| 9 BORME diario | 6 | 1 | 5 |
| 10 Observabilidad | 6 | 0 | 6 |
| 11 Polish | 7 | 0 | 7 |
| **Total** | **120** | **9** | **111** |

---

*Tareas vigentes desde 2026-05-23. Si una task se sale del scope, se
crea sub-task `TXXX.1, TXXX.2, …`. No se borran tasks: se marcan como
`~~T###~~ (descartada · razón)` y se justifica en PR.*
