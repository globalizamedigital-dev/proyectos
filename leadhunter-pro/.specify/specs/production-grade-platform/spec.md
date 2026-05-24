# Cazador Globalizame · Spec — Plataforma interna

> Master spec del producto interno.
> Cubre todo lo necesario para pasar de "MVP Python+Tkinter funcional"
> a "herramienta operativa de Globalizame que genera leads B2B
> cualificados desde fuentes oficiales españolas".
>
> **No es SaaS público.** Lo usan Mario y el equipo de Globalizame. Si
> en el futuro se abre como SaaS, se reabre esta spec.
>
> Cualquier requisito de este documento debe ser **testable**. Donde
> faltan datos del operador, se toman defaults informados y se marcan
> con [DEFAULT].

---

## 1 · Overview

Cazador Globalizame es la herramienta de generación de leads B2B de
Globalizame. Cruza fuentes oficiales españolas (BORME, OSM, Cartociudad,
PLACSP, AEPD, INE, Infosubvenciones), las puntúa con Gemini (free tier
de Google AI Studio), las persiste en Supabase (proyecto nuevo dedicado)
y dispara secuencias de outreach por SMTP propio del cliente + Meta
WhatsApp Cloud API (free tier), orquestadas en n8n.

**Stack 100% free-tier hasta tener cliente que pague.** Ningún servicio
externo de pago (eInforma, Findymail, NeverBounce, SendGrid, Brave
Search, Document AI, Browserless) entra en el MVP. Se contemplan como
upgrades opcionales en el roadmap, pero ningún FR del MVP los exige.

El producto se entrega como SaaS web (Next.js en Vercel) más una CLI/GUI
Python para uso interno y demos offline. La constitución del proyecto
(`.specify/memory/constitution.md`) gobierna las decisiones que esta
spec no cubre.

### Objetivos medibles

| KPI | Objetivo MVP | Verificación |
|---|---|---|
| Tiempo búsqueda Discover 25 leads (con enrich) | ≤ 45 s p95 | Tests de carga + métricas Cloud Run |
| Leads con email permutado de confianza alta | ≥ 40 % | Query a Supabase sobre dataset reciente |
| Cobertura fuentes "ok" en producción | ≥ 4 / 6 | Endpoint `/health/sources` |
| Tests automatizados pasando | 100 % (≥ 55) | CI verde en cada commit |
| MTTR ante caída de fuente externa | ≤ 1 h | Postmortem post-incidente |
| Coste total de servicios externos | 0 €/mes | Billing GCP + APIs en free tier |
| Primer informe semanal de leads entregado | Junio 2026 [DEFAULT] | Export CSV/JSON en `_clientes/<cliente>/leads/` |
| Reducción de tiempo de prospección manual | ≥ 80 % vs proceso actual | Cronometrar antes/después en Globalizame |

> KPI de email **bajado de 60 → 40 %**: sin NeverBounce ni servicio
> equivalente, solo podemos garantizar permutación heurística + SMTP-
> probe propio (que falla contra Google/Microsoft). 40 % es realista
> con el permutador actual.

### No-objetivos

- LinkedIn scraping directo.
- Resolver Cloudflare con servicios de terceros (Anti-CAPTCHA, etc.).
- Soporte para entidades fuera de España.
- App móvil nativa.

---

## 2 · Personas y escenarios

### Persona A · Operador interno (Mario)
Usa la app para investigar leads para Globalizame y para clientes en
modo "white-glove". Conoce los detalles, le importa la calidad por
encima del volumen.

**Escenario A1 · Discover para presentación comercial**
1. Abre `/discover`, elige *Sevilla* + *asesoría fiscal*, slider en 25.
2. Lanza la búsqueda. En ≤ 30 s ve la tabla con score, decisor, email.
3. Click en un lead → side sheet con fuentes que han contribuido,
   PLACSP, AEPD, etc.
4. Exporta CSV para reunión.

**Escenario A2 · Análisis profundo de un NIF**
1. Va a `/analizar`, pega `B41234567`.
2. Recibe ficha completa: registralTimeline, decisores, web,
   compliance, contratos, subvenciones.
3. Si afirma "es cliente nuestro" y la app no ve ninguna factura ni
   contrato cruzado, marca `assertion_mismatch` con la fuente que
   contradice.

### Persona B · Comercial de Globalizame (equipo Mario)
Trabaja a tiempo completo o parcial en Globalizame haciendo outreach
con los leads que Cazador genera para clientes del Servicio Integral.
Necesita una vista operativa: leads filtrables, plantillas y cola de
envío clara.

**Escenario B1 · Outreach semanal**
1. Lunes 9:00, abre `/leads`, filtra por `score ≥ B` y `outreach_status =
   new`.
2. Multi-selecciona 20 leads, click *Añadir a Outreach*.
3. Va a `/outreach`, elige plantilla *email_cold_es*, preview con
   merge tags personalizados.
4. Confirma envío. La cola n8n lo distribuye con throttling.
5. Las respuestas entran en el buzón de Globalizame y se loguean en
   Supabase vía webhook.

### Persona C · Admin / compliance (también Mario o quien designe)
Asegura que Globalizame no entra en lista negra de spam y respeta
GDPR/LSSI.

**Escenario C1 · Bounce review**
1. Abre `/config → bounces`, ve la lista de hard-bounces de la semana.
2. Confirma que las direcciones están en suppression.
3. Exporta un GDPR export para un sujeto que pidió derecho al olvido.

---

## 3 · Functional Requirements

> Cada requisito tiene ID. Cada ID es **testable**: se puede escribir
> un test unitario, de integración o un check manual reproducible.

### A · Ingesta de datos (scraping y fuentes)

- **FR-A1**: El sistema expone un comando `discover(provincia, sector,
  max)` que devuelve una lista ordenada por score, con al menos los
  campos `razonSocial, nif?, score, grade, decisor?, email?, phone?,
  domain?, sources[]`. *Test*: smoke con `Sevilla / asesoría fiscal /
  10` devuelve ≥ 5 leads.
- **FR-A2**: BORME se ingesta a diario (cron 06:00 Europe/Madrid)
  mediante worker en Cloud Run Job, guardando XML crudo en Cloud
  Storage. *Test*: tras 24 h hay ≥ 1 snapshot nuevo en `gs://leadhunter-raw/borme/{yyyy-mm-dd}/`.
- **FR-A3**: Cada adapter (`borme`, `osm`, `cartociudad`, `placsp`,
  `aepd`, `ddg`, `infoempresa`, `infosubvenciones`, `dirce`) implementa
  detección de degradación y marca `SourceStatus` con uno de:
  `ok | stub | blocked | captcha | js-spa | requires-cert | http-{n}`.
  Nunca `http-200` falso. *Test*: ya implementado para PLACSP/DDG/AEPD/
  InfoEmpresa en commit `9cb32cb`; mantener.
- **FR-A4**: Las fuentes con WAF/anti-bot (`ddg`, `infoempresa`,
  `aepd`, `overpass`) usan **Scrapling StealthyFetcher** (open-source,
  BSD-3, gratis); AEPD y cualquier futura SPA usan **DynamicFetcher**
  (Playwright local, gratis). El resto sigue con `httpx` plano. *Test*:
  lookup de `aepd.lookup_dpo` sobre un NIF conocido devuelve
  `registered=True` cuando lo es, sin `js-spa` en SourceStatus.
- **FR-A5**: Ninguna llamada de red puede colgar el proceso > 35 s.
  Todo `http_get` lleva `timeout` y `retries` explícitos. *Test*: smoke
  con un endpoint que se conoce muerto debe terminar el comando en ≤
  35 s.
- **FR-A6**: El pipeline degrada limpio: si N de 6 fuentes caen, las
  N-restantes producen leads igualmente. *Test*: mockear caída de
  BORME y PLACSP simultáneamente; `discover` sigue devolviendo
  candidatos a partir de OSM.

### B · Backend API (FastAPI thin layer)

- **FR-B1**: Servicio FastAPI desplegado en Cloud Run región
  `europe-west1` [DEFAULT] con endpoints:
  - `POST /discover` body `{ geo, sector, max, enrich }`
  - `POST /analyze` body `{ input: nif | razon_social, premium? }`
  - `POST /enrich` body `{ lead_id }`
  - `GET /health/sources` → snapshot de `SourceStatus`
- **FR-B2**: Todos los endpoints devuelven JSON con shape estable y
  `schemaVersion: "2.0.0"` heredado de los snapshots actuales.
- **FR-B3**: Autenticación por JWT emitido por Supabase Auth.
  Endpoints rechazan llamadas sin token con 401. *Test*: curl sin
  Authorization → 401.
- **FR-B4**: Rate-limit por tenant: 60 reqs/min, 1.000 leads/día por
  defecto [DEFAULT, configurable]. *Test*: 61ª request en 60 s → 429.
- **FR-B5**: Cualquier excepción no capturada se serializa como
  `{ "error": "...", "traceback_id": "..." }` y se loguea en Cloud
  Logging. Nunca un 500 desnudo.

### C · Enrichment (heurístico, 100% gratis)

> Toda mejora de calidad de lead se hace con código propio sobre datos
> públicos. Cero servicios de pago en el MVP. Cuando llegue cliente
> que lo pague, se activarán los adapters comerciales como upgrade
> opcional (ver sección 5 · Out of scope).

- **FR-C1**: Resolución de dominio web por heurística (`scripts/
  domain_resolver.py`) + scraping de la home si responde
  (`scripts/web_contact.py`). *Test*: para una razón social con web
  conocida, el resolver devuelve el dominio correcto con
  `confidence: heuristic`.
- **FR-C2**: Permutación local de emails B2B según patrones españoles
  (`scripts/email_finder.generar_permutaciones_email`) sobre `(nombre,
  apellido1, apellido2, dominio)`. *Test*: para `("José", "García",
  "López", "demo.es")` devuelve al menos `jose.garcia@demo.es` y
  `j.garcia.lopez@demo.es` en el top 5.
- **FR-C3**: Verificación SMTP best-effort propia
  (`scripts/email_finder.verify_email_smtp`) — sin servicio externo.
  Marcado como `low/medium` cuando el MX responde 250 al RCPT TO; la
  app reconoce que Microsoft/Google no responden y muestra `smtp_note:
  timeout` sin marcarlo como inválido. *Test*: contra un email
  conocido válido en un dominio que acepta probes (e.g. catch-all
  configurado en test), devuelve `valid: true`.
- **FR-C4**: Tabla `usage_events` registra consumo de **fuentes con
  cuota** (Gemini, WhatsApp Cloud) para vigilar el free tier. Schema:
  `(tenant, service, units, timestamp, free_tier_remaining?)`. *Test*:
  10 llamadas a Gemini → 10 filas; cuando `free_tier_remaining < 10 %`
  se emite WARN.

### D · Inteligencia (Gemini · free tier Google AI Studio)

> Toda llamada LLM va contra el endpoint público de **Google AI
> Studio** (`generativelanguage.googleapis.com`) con la API key
> personal de Mario. El free tier de Gemini 2.5 Flash hoy cubre 1.500
> req/día y 1M tokens/día — más que de sobra para el MVP. Vertex AI
> queda como upgrade futuro si se supera el cupo.

- **FR-D1**: Entity resolution: `resolve_entity(input)` usa Gemini 2.5
  Flash para decidir si dos razones sociales son la misma entidad,
  reemplazando el `levenshtein` actual cuando la confianza léxica
  baja. Caché Supabase 30 días por `hash(pair)` para no quemar cuota.
  *Test*: pareja `"Asesoría García S.L." ↔ "Asesores Garcia, S.L."`
  devuelve `match: true, confidence: high`.
- **FR-D2**: CNAE auto-clasificación desde texto libre o desde
  contenido de la web del lead. Llamada cacheada 30 días por
  `hash(input)`. *Test*: "consultora de IA" → `6202`.
- **FR-D3**: Scoring del lead via Gemini 2.5 Flash (cambio de 3.1 Pro
  → 2.5 Flash para mantenerse en free tier) con prompt estructurado
  que recibe sector, geo, señales web y devuelve `score ∈ [0..100]` +
  `grade ∈ {A,B,C,D}` + `rationale` textual. *Test*: prompt regression
  suite con ≥ 20 casos estables. Si cuota se agota, fallback al
  scorer heurístico actual (`lead_scorer.py`).
- **FR-D4**: Generación de copy outreach: dada `(lead, template_id)`,
  genera asunto + cuerpo personalizado en estilo Isra Bravo. *Test*: el
  output no contiene placeholder `{{...}}` sin resolver ni emojis.
- **FR-D5**: Todo prompt incluye un timeout local de 15 s y degrada al
  fallback heurístico si la API falla. La UI nunca queda esperando a
  Gemini. *Test*: mockear timeout → respuesta del fallback en ≤ 16 s.

### E · Almacenamiento (Supabase · proyecto nuevo dedicado)

> **FR-E0**: Proyecto Supabase **`globalizame-cazador`** creado
> (`tfdjnnkgoynrkmyekusv`), aislado del CRM existente de Globalizame.
> Aislamiento por dos razones: 1) las migraciones del Cazador no
> contaminan el CRM; 2) un reset de migración no afecta a otras
> herramientas. Tier: **Free** (500 MB BD, 1 GB Storage,
> suficiente para ≥ 100k leads).

- **FR-E1**: Schema `public.leads` con dedup por `dedup_key = hash(nif
  || razon_social_normalized || domain)`. Migración desde el SQLite
  local existente (`scripts/leads_db.py`). *Test*: insertar el mismo
  lead dos veces produce 1 fila, no 2.
- **FR-E2**: Schema `public.outreach_events` registra cada interacción
  (sent, opened, clicked, replied, bounced, unsubscribed) con
  timestamp y `lead_id`. *Test*: un envío que rebota genera 2 eventos:
  `sent`, `bounced`.
- **FR-E3**: Tabla `suppression` con `(email|phone|nif), reason,
  timestamp`. Toda salida (email/SMS/WhatsApp) consulta esta tabla
  primero. *Test*: añadir email a suppression → siguiente envío al
  mismo email genera `skipped: suppressed` en lugar de envío.
- **FR-E4**: Embeddings de la razón social + sector almacenados en
  `pgvector` para dedup semántico cross-batch. *Test*: cosine sim ≥
  0.92 dispara `merge_candidate` en lugar de duplicar.
- **FR-E5**: RLS (Row-Level Security) activado en todas las tablas:
  cada tenant solo ve sus propios leads. *Test*: usuario del tenant A
  consulta lead del tenant B → 0 filas.

### F · Frontend SaaS (Next.js en Vercel)

- **FR-F1**: Cinco rutas en producción: `/discover`, `/analizar`,
  `/leads`, `/outreach`, `/config`. La shell `(app)/layout.tsx` ya
  existe y se reutiliza para todas. *Test*: navegar las 5 rutas no
  arroja 404.
- **FR-F2**: Marca Globalizame aplicada según constitución: verde
  primary, púrpura accent, dark por defecto, Josefin + Inter. *Test*:
  visual regression contra capturas de referencia.
- **FR-F3**: La pantalla nunca queda colgada. Un worker que tarda
  muestra feedback (shimmer + sondeando…); si falla, banner de error
  claro. *Test*: simular fetch que rechaza → UI vuelve a estado
  navegable en ≤ 1 s.
- **FR-F4**: Anti doble-submit en todos los CTAs principales
  (Discover, Analizar, Outreach send). *Test*: dos clicks rápidos →
  una sola request en network.
- **FR-F5**: Export CSV y JSON desde `/discover` y `/leads` con
  BOM UTF-8 y encoding correcto para Excel-ES. *Test*: abrir el CSV en
  Excel español muestra acentos correctos.
- **FR-F6**: Pantalla **Analizar** acepta NIF o razón social, llama a
  `/analyze`, renderiza la ficha y, si el operador metió una claim
  ("es cliente"), muestra banner naranja con `assertion_mismatch`
  cuando aplica.
- **FR-F7**: Pantalla **Leads** es una tabla persistida (no efímera
  como Discover). Permite filtros por sector, provincia, score,
  outreach_status. Multi-select + bulk actions. *Test*: 1.000 leads se
  paginan sin freeze (virtualizado).
- **FR-F8**: Pantalla **Outreach** muestra cola por tenant, plantilla
  seleccionada, preview de un lead concreto, botón "Enviar a todos".
  Confirmación modal antes de disparar.
- **FR-F9**: Pantalla **Config** edita: SMTP propio (opcional),
  webhooks, suppression manual, API keys, miembros del equipo.

### G · Outreach (SMTP propio · WhatsApp free tier)

> Cero servicio de email transaccional de pago. El tenant configura su
> propio SMTP (Hostinger, Gmail con App Password, Zoho free, etc.) en
> `/config`. WhatsApp va por **Meta WhatsApp Cloud API directa**, que
> tiene 1.000 conversaciones gratis/mes — sin pasar por YCloud
> (de pago) hasta que el volumen lo justifique.

- **FR-G1**: Envío email vía **SMTP propio del tenant** configurado en
  `/config`. La app valida la conexión al guardar (`/config → Probar
  SMTP`). Si el SMTP no está configurado, los CTAs de Outreach quedan
  deshabilitados con tooltip explicativo.
- **FR-G2**: Cada email lleva headers `List-Unsubscribe` y
  `List-Unsubscribe-Post: List-Unsubscribe=One-Click`. *Test*:
  inspeccionar headers del email enviado.
- **FR-G3**: Secuencias multi-paso (touch1 → wait 3d → touch2 → wait
  5d → touch3) orquestadas en n8n. Una respuesta detiene la
  secuencia. *Test*: simular reply → siguientes touches no se envían.
- **FR-G4**: Canal WhatsApp vía **Meta WhatsApp Cloud API directa**
  (free tier, 1.000 conversaciones/mes incluidas) cuando el lead tiene
  `phone` y el tenant tiene la app de WhatsApp Business configurada.
  YCloud queda como upgrade opcional. *Test*: envío a número de prueba
  registrado en la app Meta Business.
- **FR-G5**: Bounces 5xx → `mark_bounced(email)` automático y la
  dirección entra en suppression cross-canal. *Test*: simular SMTP
  5.7.1 → siguiente `send_email(same)` retorna `skipped: bounced`.

### H · Compliance / Suppression

- **FR-H1**: Endpoint público `/unsubscribe?token=...` que da de baja
  un email sin pedir login. *Test*: GET con token válido → 200 + email
  en suppression.
- **FR-H2**: Export GDPR `POST /privacy/export` devuelve todos los
  datos asociados a un email/teléfono/NIF. *Test*: snapshot JSON
  incluye `leads, outreach_events, suppression`.
- **FR-H3**: Derecho al olvido `DELETE /privacy/erase` borra (no
  oculta) los datos personales del sujeto. *Test*: tras llamada,
  `SELECT * FROM leads WHERE email = ?` devuelve 0 filas.
- **FR-H4**: Cada email saliente incluye link visible y funcional al
  `/unsubscribe`. *Test*: template Jinja contiene el link; render
  fallido sin link es error.

### I · Operación / Observabilidad

- **FR-I1**: Cada commit pasa CI con: type-check TS strict + pytest
  Python + lint. CI rojo bloquea merge. *Test*: el propio CI.
- **FR-I2**: Logs estructurados (JSON) a Cloud Logging desde Cloud
  Run; nivel WARN cuando una fuente cambia de estado a `down`. *Test*:
  forzar AEPD a `js-spa` → aparece línea WARN en Cloud Logging.
- **FR-I3**: Health endpoint `/health` agrega `db: ok`, `sources:
  4/6`, `queue_depth: 12`. *Test*: curl devuelve 200 con todos los
  campos.
- **FR-I4**: Métricas exportadas a Cloud Monitoring:
  `discover_latency_p95`, `leads_per_search`, `bounce_rate`,
  `external_api_cost_eur`. *Test*: dashboard de Monitoring muestra las
  4 métricas con datos recientes.
- **FR-I5**: Secrets gestionados en Secret Manager. Cero secretos en
  el repo. *Test*: `grep -r 'sk_live\|sbp_\|AIza\|SG\.'` en el repo no
  devuelve nada.

---

## 4 · Defaults asumidos [DEFAULT]

Cuando el operador no especificó, esta spec asume:

1. **Modelo de producto**: **uso 100 % interno de Globalizame.**
   Cazador no es SaaS público; lo usan únicamente Mario y su equipo. No
   hay registro abierto, no hay checkout, no hay pricing public.
2. **Región Cloud**: `europe-west1` (Bélgica) — más cerca de Sevilla,
   sigue dentro de GDPR. Free tier de Cloud Run aplica.
3. **Single-tenant operacional**: el schema Supabase mantiene la
   noción de `tenants` por higiene (RLS, separación lógica), pero solo
   hay **un tenant activo**: `globalizame`. Si en el futuro se abre
   como SaaS, el schema lo soporta sin reescritura.
4. **Auth**: Supabase Auth con email + magic link. Solo se dan de alta
   los emails del equipo de Globalizame; no hay signup público.
5. **Locale**: solo `es-ES`; i18n descartado.
6. **Theme**: dark por defecto, light secundario.
7. **APIs externas a configurar manualmente**: la app expone variables
   de entorno para Gemini (Vertex AI service account), Supabase URL+keys,
   SMTP propio y Meta WhatsApp Cloud. Ninguna se hardcodea, ninguna se
   asume preconfigurada en producción — se añaden en el deploy.

Cambiar cualquiera requiere modificar esta sección + justificar en PR.

---

## 5 · Out of scope (explícito)

**Servicios externos de pago — fuera del MVP, sí en el roadmap como
upgrade opcional cuando un cliente lo pague:**
- **eInforma** (Iberinform) → balances/empleados/deuda reales.
- **Findymail / Hunter / Snov** → emails B2B verificados con API.
- **NeverBounce / ZeroBounce / MillionVerifier** → verificación
  industrial de emails.
- **SendGrid / Postmark / Resend** → email transaccional con
  reputación.
- **Brave Search / Serper API** → reemplazo de DDG con resultados
  estructurados.
- **Browserless / Browserbase** → Playwright gestionado en cloud.
- **Document AI** (GCP) → parseo industrial de PDFs BORME.
- **Vertex AI con cuota dedicada** → cuando el free tier de Google AI
  Studio se quede corto.
- **YCloud** → cuando Meta WhatsApp Cloud free tier se quede corto.

**Fuera totalmente del producto:**
- LinkedIn scraping o cualquier integración que rompa ToS.
- Hysteria / proxies de evasión.
- Apollo, Clearbit, Lusha, Cognism.
- App móvil nativa.
- Soporte fuera de España.
- Multi-language en la UI.
- **SaaS público / self-service signup / Stripe checkout / pricing
  page** — Cazador es herramienta interna; si en el futuro se abre,
  se reabre la spec.
- **Outreach automatizado (email + WhatsApp) — recortado del MVP
  2026-05-24.** El MVP se queda en descubrir → cualificar → persistir
  → exportar. Los FR del bloque G (`outreach`) y la persona B
  (Comercial de Globalizame) quedan como referencia histórica pero
  no se implementan. Si vuelven, se actualiza la spec entera.
  El operador exporta el CSV de leads y hace el outreach por sus
  canales habituales (CRM, n8n existente, herramienta externa).

---

## 6 · Open questions (decisiones pendientes del operador)

1. ¿Service account de Vertex AI regenerada? La SA actual
   (`globalizame@globalizame-apis-493012.iam.gserviceaccount.com`)
   devuelve "Invalid JWT Signature"; pendiente rotar la key en consola
   GCP IAM. **Único bloqueante real** para Sprint 7 (Gemini scoring).

---

## 7 · Trazabilidad

- Constitución base: `.specify/memory/constitution.md`
- Arquitectura técnica detallada: `ARCHITECTURE.md`
- Auditoría inicial y fixes: commit `9cb32cb`
- Web scaffold + Discover MVP: `web/` (Next.js 16)

*Última actualización: 2026-05-23.*
