# Cazador Globalizame · Constitución del proyecto

> Producto de **Globalizame** (Mario Ruiz Gallego, Sevilla).
> Documento vivo. Cualquier decisión que choque con este texto necesita
> justificación explícita en el PR. *No se viola lo escrito porque sí.*

---

## 1 · Identidad

- **Nombre**: Cazador Globalizame
- **Misión**: convertir las fuentes públicas oficiales españolas en un
  flujo continuo de leads B2B cualificados — con decisor, contacto y
  contexto — para que una PYME pueda hacer ventas sin depender del
  fundador 24/7.
- **Tagline**: *"Tu negocio liberado. Tu tiempo recuperado."*
- **Antimisión**: NO somos otra herramienta SaaS genérica. No somos un
  proxy de Apollo, no inflamos métricas, no vendemos humo.

## 2 · Voz y marca

- Tono: directo, Isra Bravo, sin rodeos, sin corporate. El cliente es el
  héroe; LeadHunter es el arma.
- Sin emojis en producto, marketing ni código.
- Colores: verde `#86CA28` (acción), púrpura `#700962` (acento), negro
  `#0A0A0A` (fondo), naranja `#FFA500` (alerta), blanco `#FFFFFF`.
- Tipografía: **Josefin Sans** títulos · **Inter** cuerpo.
- Numerales tabulares siempre que se muestren datos.

---

## 3 · Principios rectores

1. **Hecho > perfecto**. Lo que está en producción mueve la aguja; lo
   que está perfecto en un branch no.
2. **Auditar antes de tocar**. Antes de proponer un cambio, leemos el
   estado actual. Si no se ha leído, no se opina.
3. **Clean slate cuando hay deuda técnica**. Mejor reescribir un módulo
   roto que parchearlo tres veces.
4. **Sin bloqueos externos**. Si una fuente cae, degradamos limpio y
   seguimos. Ninguna integración tumba el pipeline entero.
5. **Verificar antes de afirmar**. Nunca se referencia una versión, un
   precio o un endpoint sin haberlo verificado vivo.
6. **Stack flexible**. Las herramientas se eligen por necesidad real, no
   por moda ni por costumbre. Cualquier dependencia debe justificar su
   peso.
7. **Sin humo, con datos**. Cada lead reportado debe tener trazabilidad
   a una fuente pública verificable. Si un dato no se puede citar, no
   se publica.

---

## 4 · Reglas no negociables

### 4.1 · Fuentes de datos

- **Solo fuentes públicas oficiales españolas o sus equivalentes
  legales**: BORME, BOE, OSM, Cartociudad, PLACSP, AEPD, INE,
  Infosubvenciones, eInforma (Iberinform), Brave Search.
- **NUNCA** Apollo, Apify, Google Maps Places, Google Search scraping,
  scraping directo de LinkedIn, ni cualquier fuente que rompa los ToS o
  el RGPD.
- Cuando una fuente devuelva HTML de error envuelto en HTTP 200, se
  detecta y se marca `requires-cert`/`blocked`/`captcha`/`js-spa`. Nunca
  se trata como `ok` falso.

### 4.2 · Compliance

- **GDPR y LSSI-CE por construcción**, no como añadido.
- Cada email saliente lleva header `List-Unsubscribe` + `List-Unsubscribe-Post`
  (one-click).
- Suppression list persistente: una baja se respeta para siempre,
  cross-canal (email, WhatsApp, llamada).
- Bounces 5xx → marcar como `hard-bounce` y no reintentar.
- Datos personales (nombres + emails de decisores) se separan
  estructuralmente de datos públicos (razón social, NIF, dirección) en
  los outputs.

### 4.3 · Calidad de código

- **TypeScript strict**, sin `any`. Sin `@ts-ignore`.
- Python con type hints donde añada valor, especialmente en límites de
  módulo.
- Antes de marcar una tarea completada los **55 tests existentes** (o
  los que haya en su momento) deben pasar. Cero excepciones.
- Cualquier filtro de calidad de datos debe ser **estricto por
  defecto**. Es preferible un campo vacío que basura ("Pisos en venta"
  como nombre de decisor es un bug crítico, no un edge case).
- Endpoints externos hardcodeados: solo con fallback documentado o con
  detección de degradación.

### 4.4 · Operación

- **Logs WARN** cuando una tabla/endpoint hardcodeado deja de
  responder, no silencio. El operador debe enterarse.
- **Retries** acotados: como regla general `retries=1` cuando hay
  fallback alternativo; nunca 3+ por endpoint a no ser que el adapter
  no tenga otra ruta.
- **Timeouts** explícitos en toda llamada de red. Cero socket sin
  cerrar; cero conexión SMTP sin `try/finally`.
- **Sin secretos en código**. `.env` siempre, `.env` siempre en
  `.gitignore`, Secret Manager en producción.
- **`--no-verify` está prohibido** salvo petición explícita del
  operador con justificación.

### 4.5 · UX / Producto

- Por defecto, la app va en **modo oscuro**. Light mode existe pero es
  secundario.
- La pantalla de un operador NUNCA se queda colgada. Si un worker
  tarda, hay feedback visual; si falla, hay error claro; si la ventana
  se cierra, los workers se cancelan.
- Cada microcopy se gana su sitio. Sin "Lorem ipsum corporate".
- Los datos vacíos se muestran como `—`, no como "N/A" o "null".

### 4.6 · Uso interno

- **Cazador es herramienta interna de Globalizame**, no SaaS público.
  Solo lo usan Mario y el equipo de Globalizame para generar leads
  propios y para enriquecer el trabajo "white-glove" con clientes del
  servicio integral.
- **Cero coste de variables externas**. eInforma / Findymail /
  NeverBounce y demás servicios de pago se mantienen fuera del MVP. Si
  algún día un cliente paga específicamente por ellos, se activan
  detrás de feature flag.
- **Nada de cobros dentro de la app**: sin Stripe, sin pricing pages,
  sin checkout. La facturación a clientes del servicio integral de
  Globalizame sigue su flujo habitual (factura clásica, fuera de
  Cazador).
- El embudo comercial de Globalizame sigue su lógica:
  Publicidad (gancho) → Auditoría GRATIS (urgencia) → Servicio Integral.
  Cazador es **el arma que usamos** para generar leads en ese embudo,
  no el embudo en sí.
- **MVP recortado 2026-05-24: Cazador solo descubre y cualifica leads,
  no los contacta.** El outreach (email/SMTP, WhatsApp) queda fuera del
  MVP. El operador exporta los leads y los mete en sus canales actuales
  (CRM Globalizame, n8n existente, herramienta externa). Si en el
  futuro se reactiva el outreach interno, se reabre el bloque G del
  spec entonces; las tablas Supabase `outreach_*` siguen en el schema
  por higiene, sin uso.

---

## 5 · Decisiones de stack ya tomadas

| Capa | Elección | Por qué |
|---|---|---|
| Backend lógica | Python 3.12 (módulos en `scripts/`) | Reaprovecha los 12 parsers existentes |
| Desktop / interno | Tkinter + PyInstaller | Solo herramienta interna offline |
| Frontend producto | Next.js 16 App Router + TS strict + Tailwind v4 + shadcn (Base UI) | Vercel-native, deploy gratis |
| BD operativa | Supabase Postgres + pgvector | Ya en stack Globalizame |
| Orquestación | n8n self-hosted (VPS) | Ya en stack |
| Workers serverless | Cloud Run Jobs + Cloud Tasks (cuando se necesite escalar) | Pago por uso |
| IA | Vertex AI Gemini 3.1 Pro (razonamiento) + 2.5 Flash (volumen) | Ya en stack |
| Email transaccional | SendGrid o Postmark | Reputación; SMTP propio se quema |
| WhatsApp | YCloud + Meta WhatsApp Cloud API | Ya en stack |
| Cobros | ~~Stripe~~ | Descartado · uso interno de Globalizame, sin facturación dentro de la app |

**Lo descartado en el camino**: Mission Control (es CRM de NorteIA, no
aplica), Hysteria / proxies de evasión (ningún problema es de IP),
Apollo/Clearbit (filosofía y coste), LinkedIn scraping (ToS).

---

## 6 · Cómo se modifica esta constitución

1. PR explícito que toque solo este archivo.
2. Justificación: qué dejó de aplicar y por qué.
3. Aprobación del operador (Mario).
4. La versión queda en el historial git; no se reescribe en silencio.

---

*Vigente desde 2026-05-23. Última auditoría integral: commit `9cb32cb`
(saneamiento de ~30 bugs, 55/55 tests).*
