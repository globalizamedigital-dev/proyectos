# Changelog — Cazador Globalizame

Versionado simple: `MAYOR.MENOR.PATCH`. Cada release tag se hace en git
con la misma cadena (`v0.2.0-mvp`, `v0.3.0`, …).

---

## [0.2.0-mvp] — 2026-05-23

Primer MVP web SaaS interno end-to-end. App entera navegable en local
con `uvicorn` + `next dev`.

### Cambios estructurales

- **Renombrado** producto a *Cazador Globalizame* (antes "LeadHunter Pro").
- Web Next.js 16 en `web/`, branded con paleta Globalizame
  (verde `#86CA28` · púrpura `#700962` · negro `#0A0A0A`) + Josefin Sans
  / Inter.
- FastAPI thin layer en `api/` que envuelve `scripts/`.
- Supabase proyecto nuevo `globalizame-cazador` (`tfdjnnkgoynrkmyekusv`,
  Frankfurt, free tier) aislado del CRM existente.
- GCP project reutilizado: `globalizame-apis-493012` (para Cloud Run y
  Vertex AI cuando se activen).

### Funcional añadido (sprints)

#### Sprint 0 · Cimientos (commit `91bff96`)
- 7 migraciones SQL aplicadas a Supabase vía Management API.
- 9 tablas: tenants, tenant_members, leads, outreach_templates,
  outreach_sequences, outreach_events, suppression, usage_events,
  leads_embeddings (pgvector).
- RLS multi-tenant activo en todas las tablas; un único tenant activo
  (`globalizame`).
- Seed con 2 plantillas Isra Bravo y 1 secuencia base.
- Clientes Supabase para web (browser + server con cookies).
- GitHub Actions CI con path filters (web, python, sql-lint).

#### Sprint 1 · Scrapling Fase A (commit `9a8eee8`)
- `scripts/fetch_client.py` con 3 modos: plain (urllib), stealthy (TLS
  fingerprint Chrome via curl_cffi), dynamic (Playwright headless).
- Feature flag `LEADHUNTER_USE_SCRAPLING` para rollback inmediato.
- Adapters migrados a `fetch_stealthy`: `ddg`, `infoempresa`, `osm`.
- `aepd` usa `fetch_dynamic` para renderizar la SPA Angular del
  sedeAEPD.
- DDG ya no devuelve CAPTCHA. Overpass-api.de responde 200.

#### Sprint 2 · FastAPI thin layer (commit `bfde698`)
- `api/` con FastAPI 0.115 + uvicorn.
- Auth JWT contra JWKS de Supabase Auth (ES256, sin shared secret).
- Endpoints: `POST /discover`, `POST /analyze`, `GET /health`,
  `GET /health/sources`.
- Logging JSON estructurado apto para Cloud Logging.
- Middleware con trace_id + duration_ms + fallback estable a JSON en
  cualquier 500.
- Dockerfile multi-stage Cloud Run-ready (incluye chromium para
  fetch_dynamic).
- 7 tests pasando.

#### Sprint 3 · Web ↔ API integración real (commit `6261124`)
- Login con magic link Supabase + página branded.
- `web/src/middleware.ts` protege `/(app)/*` con redirect a `/login`.
- `api-client.ts` que añade Authorization Bearer automáticamente.
- Discover real (sustituyendo el mock setTimeout) con AbortController
  por componente y banner naranja "modo demo · API offline" cuando
  status=0; rojo para 4xx/5xx.
- Status bar polling `/health/sources` cada 30 s.

#### Sprint 4 · 4 pantallas operativas (commit `726a223`)
- `/analizar`: input NIF/razón social con detección de formato,
  switches para "claims" del operador, ficha completa con secciones y
  banner de `assertion_mismatch`.
- `/leads`: tabla persistida desde Supabase con `@tanstack/react-table`,
  filtros (provincia, score mínimo, buscador), multi-select, bulk
  actions, paginación.
- `/outreach`: cola con leads `queued`/`new`, selector de plantilla y
  preview en vivo con merge tags renderizados sobre el primer lead
  seleccionado.
- `/config`: 4 tabs (SMTP, WhatsApp, Suppression, Equipo) con CRUD
  contra Supabase para suppression list.

#### Sprint 6 · Privacy & GDPR (commit `0efddc7`)
- `POST /privacy/export`: descarga JSON con leads, outreach_events y
  suppression del sujeto. Sirve para derecho de acceso (RGPD art. 15).
- `DELETE /privacy/erase`: borra con `ON DELETE CASCADE` + suppression.
  Audit log en `usage_events`. Irreversible.
- `GET /unsubscribe?token=...` público; HMAC-SHA256 sobre el email con
  el service_role_key como secret. Página HTML branded de confirmación.
- 5ª tab "Privacidad" en `/config` con UI para ambos (erase exige
  escribir `ERASE` para confirmar).
- 7 tests nuevos (auth, tampering, roundtrip).

### Calidad

- Tests Python: 62/62 OK (55 base + 7 fetch_client).
- Tests API: 14/14 OK.
- Web typecheck strict + build: verde (9 rutas).
- Error boundaries: `(app)/error.tsx`, `global-error.tsx`, `not-found.tsx`
  branded.

### Pendiente para `0.3.0`

- Sprint 5 · Outreach send real + n8n (necesita SMTP + Meta WA token).
- Sprint 7 · Gemini scoring + entity resolution + copy (necesita SA
  rotada en GCP IAM).
- Sprint 8 · BORME daily Cloud Run Job (necesita gcloud CLI + deploy).
- Sprint 9 · Cloud Monitoring + alerts.
- Tests E2E con Playwright.

---

## [0.1.0] — 2026-05-22

Saneamiento previo a la SaaS web. Trabajo en el MVP Python+Tkinter.

- `9cb32cb` · Auditoría integral, ~30 bugs corregidos:
  Mirrors Overpass, encoding UTF-8 en stdout, IconButton font duplicado,
  scraper de webs muertas, detección de SPA en AEPD, captcha DDG,
  recursos SMTP sin cerrar, etc.
- 55 tests verde.
- App Tkinter operativa con tema oscuro Globalizame.

---

## [0.0.x] — pre-cazador

Etapa "leadhunter-pro" Python pura. Sin web. Solo `main.py {discover,
analyze, score, outreach --preview}` + Tkinter GUI offline. Base sólida
sobre la que se construyó el resto.
