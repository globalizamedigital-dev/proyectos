# Cazador Globalizame — Arquitectura objetivo

> Documento de referencia consolidado. La app actual (Python + Tkinter)
> se considera **herramienta interna**; el producto comercial se construye
> como SaaS web sobre Vercel + GCP + Supabase, reaprovechando los parsers
> Python como microservicios.

---

## Stack target

```
┌─────────────── FUENTES PÚBLICAS ESPAÑOLAS ───────────────┐
│  BORME · BOE · OSM · Cartociudad · PLACSP · AEPD · INE   │
└────────────────────────┬─────────────────────────────────┘
                         │  (workers de scraping)
                         ▼
              ┌──────────────────────┐
              │  Cloud Run Jobs      │  ←── Cloud Scheduler (cron)
              │  (BORME daily, etc.) │
              └──────┬──────┬────────┘
                     │      │
                     ▼      ▼
           Cloud Storage    Cloud Tasks
           (snapshots)      (queue retry)
                     │
                     ▼
              ┌──────────────────────────────────┐
              │  Vertex AI Gemini                │
              │  - Resolución de entidad         │
              │  - CNAE auto + scoring           │
              │  - Generación copy outreach      │
              └──────┬───────────────────────────┘
                     │
                     ▼
              ┌──────────────────────────────────┐
              │  Supabase Postgres + pgvector    │  ←── eInforma, Findymail,
              │  (corpus de leads, embeddings)   │      NeverBounce, Brave
              └──────┬───────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  n8n (orquestación)      │
        │  Discover → Enrich →     │
        │  Score → Outreach        │
        └──────┬──────┬────────────┘
               │      │
               ▼      ▼
          SendGrid   YCloud (WhatsApp)
               │      │
               ▼      ▼
        ┌──────────────────────────┐
        │  Webhooks de respuesta   │
        └──────────────────────────┘
                     ▲
                     │
              ┌──────┴───────────────────────────┐
              │  Next.js 16 (App Router)         │
              │  Vercel · Globalizame branding   │
              │  Tabs: Discover · Analizar ·     │
              │        Leads · Outreach · Config │
              └──────────────────────────────────┘
```

---

## Servicios externos · justificación 1-a-1

### Datos y enriquecimiento

| Servicio | Para qué | Coste aprox |
|---|---|---|
| **eInforma API** (Iberinform) | Balances reales, empleados, deuda de empresas españolas. Sin esto, "lead cualificado" es marketing | 0,15–0,80 €/consulta |
| **Findymail** | Emails B2B verificados con confianza, respeta ToS LinkedIn | 49–99 €/mes |
| **NeverBounce** | Verificación SMTP-API (el probe local no funciona contra Microsoft/Google) | ~5 €/1.000 emails |
| **Brave Search API** | Reemplaza DDG (que da CAPTCHA), JSON limpio | 5 €/1.000 q |
| **Browserless** o **Browserbase** | Playwright gestionado para SPAs (AEPD, InfoEmpresa) | 30–100 €/mes |

### Google Cloud

| Servicio | Rol |
|---|---|
| **Cloud Run Jobs** | Contenedores serverless para los scrapers actuales |
| **Cloud Scheduler** | Cron daily BORME + weekly PLACSP + monthly INE |
| **Cloud Tasks** | Cola con reintentos exponenciales (reemplaza el `ThreadPoolExecutor`) |
| **Cloud Storage** | Snapshots crudos (XML/HTML) para reextracción sin pegar a fuentes |
| **Document AI** | Parseo de PDFs BORME con tablas |
| **Vertex AI Gemini** | Entidad-resolution + CNAE + scoring + copy outreach |
| **Secret Manager** | Credenciales fuentes/APIs |
| **Cloud Logging** | Observabilidad scrapers |

### Stack actual de Globalizame que mantenemos

| Componente | Uso |
|---|---|
| Supabase Postgres + pgvector | Corpus de leads + dedup semántico |
| n8n self-hosted (VPS) | Orquestación post-scraping |
| Gemini 3.1 Pro + 2.5 Flash | Razonamiento (3.1) + volumen (2.5) |
| YCloud + Meta WhatsApp Cloud | Canal post-email |
| ~~Stripe~~ | Descartado · uso interno, sin cobros en la app |
| Easypanel + VPS | Hosting de n8n |

---

## Migración por fases (orientativo)

### Fase 0 — Hoy
- [x] Auditoría y saneamiento del MVP Python+Tkinter (commit `9cb32cb`)
- [→] Frontend web Next.js con marca Globalizame, pantalla Discover funcional contra mock

### Fase 1 — Backend mínimo viable
- [ ] FastAPI thin layer que expone los módulos Python actuales como endpoints (`/discover`, `/analyze`)
- [ ] Despliegue del FastAPI en Cloud Run (1 servicio)
- [ ] Frontend Next.js conectado a la API real

### Fase 2 — Persistencia y queue
- [ ] Schema Supabase para leads + outreach + suppression
- [ ] Migración del SQLite local
- [ ] Cloud Tasks para discover de gran volumen

### Fase 3 — Enriquecimiento de pago
- [ ] Integración eInforma (1 endpoint nuevo)
- [ ] Integración Findymail + NeverBounce
- [ ] Reemplazo del SMTP-probe por NeverBounce API

### Fase 4 — Inteligencia
- [ ] Entity resolution con Gemini 2.5 Flash
- [ ] Scoring LLM con Gemini 3.1 Pro
- [ ] Generación de copy outreach personalizado

### Fase 5 — Outreach a escala
- [ ] SendGrid + warmup
- [ ] Secuencias n8n
- [ ] WhatsApp via YCloud
- [ ] Webhook de respuestas → Supabase

---

## Lo que sale del scope del producto

- **Mission Control** (CRM interno de NorteIA): no aplica, stack Globalizame es Supabase
- **LinkedIn scraping directo**: prohibido por ToS, riesgo legal alto
- **Apollo / Clearbit / Lusha**: caros y duplican lo que eInforma + Findymail ya dan
- **Hysteria / proxies de evasión**: ningún problema de la app es de IP

---

## Marca aplicada al producto

| Token | Valor |
|---|---|
| `--brand-green` | `#86CA28` (acción, CTAs) |
| `--brand-purple` | `#700962` (acento secundario, navegación) |
| `--brand-black` | `#0A0A0A` (fondo principal modo oscuro) |
| `--brand-white` | `#FFFFFF` |
| `--brand-orange` | `#FFA500` (alertas) |
| Tipografía títulos | `Josefin Sans` |
| Tipografía cuerpo | `Inter` |
| Tono copy | Directo, Isra Bravo, sin humo. "Tu negocio liberado. Tu tiempo recuperado." |

El producto NO es "una app más". Es la herramienta que vende la propuesta de
Globalizame: sistemas que funcionan sin ti.
