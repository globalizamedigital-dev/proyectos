# Runbook · Cazador Globalizame

Flujos de respuesta a incidentes comunes. Léelos en orden de impacto
descendente. Cada sección sigue el patrón **síntoma → causa probable →
qué hacer**.

---

## 0 · Qué tienes a mano siempre

- **Credenciales** en `proyectos/leadhunter-pro/info` (gitignored).
  Bandeja única del operador.
- **Supabase Studio**: https://supabase.com/dashboard/project/tfdjnnkgoynrkmyekusv
- **GCP Console**: https://console.cloud.google.com/?project=globalizame-apis-493012
- **Logs locales API**: stdout del `uvicorn` (JSON, busca por
  `trace_id`).
- **Logs locales web**: consola del navegador + stdout del `next dev`.

---

## 1 · "No me llega el magic link al hacer login"

**Síntomas**: pulsas el botón "Enviar enlace" en `/login`, el botón
cambia a "revisa tu email", pero el email nunca llega.

**Causas más probables**:
1. **El email no está dado de alta en Supabase Auth**. Por seguridad,
   Supabase Auth con magic link **no envía emails a direcciones no
   registradas** si tienes activado "Email Confirm" en restrictivo.
2. SMTP por defecto de Supabase tiene cap muy bajo (~3/hora).

**Qué hacer**:
1. Abre Supabase Studio → Authentication → Users. Verifica que el email
   está en la lista. Si no, **Add user** → email + tilda "auto confirm".
2. Comprueba carpeta spam.
3. Verifica que el usuario está asignado a `tenant_members` con el
   tenant `globalizame` (si no, login funciona pero no ve nada por RLS):
   ```sql
   select tm.role, u.email from public.tenant_members tm
   join auth.users u on u.id = tm.user_id
   join public.tenants t on t.id = tm.tenant_id
   where t.slug = 'globalizame';
   ```
4. Si vas a hacer pruebas intensivas, configura un SMTP propio en
   Supabase Studio → Authentication → Email Templates → SMTP Settings.

---

## 2 · "La web carga pero `/discover` está vacío y no devuelve nada"

**Síntomas**: La página carga, login OK, pero al pulsar "Buscar Leads"
o no pasa nada o aparece banner naranja "modo demo · API offline".

**Causas**:
1. **El API FastAPI no está corriendo**. La web hace fetch a
   `NEXT_PUBLIC_API_BASE_URL` (por defecto `http://localhost:8000`).
2. Token JWT inválido o expirado.

**Qué hacer**:
1. Verifica que el API está vivo:
   ```bash
   curl http://localhost:8000/health
   ```
   Si no responde, arráncalo:
   ```bash
   cd api && uvicorn main:app --reload --port 8000
   ```
2. Si el API está vivo pero el banner sigue → abre DevTools → Network.
   La request a `/discover` te dirá si es 401 (auth) o 502 (engine
   error).
3. Para 401: refresca la página (renueva el token) o logout/login.
4. Para 502: el `scripts/discover.py` ha fallado. Mira el log del
   uvicorn — verás un stacktrace con el adapter problemático
   (probablemente una fuente externa caída; no es bloqueante porque
   discover degrada).

---

## 3 · "Las migraciones de Supabase fallan al aplicarse"

**Síntomas**: error 400/401 al ejecutar el script de migraciones via
Management API.

**Causas**:
1. El token PAT (`access_token_supabase` en `info`) ha caducado o se
   ha revocado.
2. La migración tiene SQL incompatible (ej. `CREATE EXTENSION` sin
   permisos).

**Qué hacer**:
1. Regenera el PAT en https://supabase.com/dashboard/account/tokens →
   actualiza `info` (clave `access_token_supabase`).
2. Verifica que el `project_ref` en `info` coincide con el del proyecto
   que quieres tocar:
   ```bash
   curl -H "Authorization: Bearer $PAT" \
        https://api.supabase.com/v1/projects | jq '.[].ref'
   ```
3. Si una migración falla por idempotencia (ej. constraint ya existe),
   añade `IF NOT EXISTS` o `DROP ... IF EXISTS` al script y reaplica.

---

## 4 · "El API devuelve 500 con `[Errno 11001] getaddrinfo failed`"

**Síntomas**: `/discover`, `/analyze` o `/privacy/*` devuelven 500 con
error de DNS.

**Causa**: el código intenta conectarse a un Supabase URL no
resoluble. Suele pasar porque `.env` no se cargó o tiene un valor
placeholder.

**Qué hacer**:
1. Verifica `.env` en la raíz del proyecto:
   ```bash
   grep SUPABASE_URL .env
   ```
   Debe ser `https://tfdjnnkgoynrkmyekusv.supabase.co`, no
   `https://x.supabase.co` o similar.
2. Reinicia uvicorn (los cambios en `.env` no se hot-reload).
3. Para tests, verifica que `api/tests/conftest.py` está fijando las
   env vars antes de importar `main`.

---

## 5 · "Una fuente externa empieza a fallar (BORME, AEPD, OSM…)"

**Síntomas**: la barra de estado inferior muestra dots naranja o
muted. Discover devuelve menos leads.

**Causas**:
- WAF de la fuente nos bloqueó (Cloudflare, mod_security, captcha).
- Endpoint cambió (BORME, AEPD lo hacen 1-2 veces al año).
- Rate limit alcanzado.

**Qué hacer**:
1. Reproduce manualmente:
   ```bash
   python -c "from scripts.borme import fetch_borme_sumario; print(fetch_borme_sumario('2026-05-22')[:200])"
   ```
2. Si es WAF → migra ese adapter a `fetch_stealthy` (Scrapling). Mira
   `scripts/aepd.py` como ejemplo: `from fetch_client import fetch_stealthy`.
3. Si la fuente es SPA (JS) → migra a `fetch_dynamic`. Caso AEPD.
4. Si el endpoint cambió → busca el nuevo, actualiza la constante de
   URL, y añade detección de "endpoint-changed" en el adapter.
5. Nunca dejes el adapter en silencio; siempre `SourceStatus.mark(…)`
   con un estado claro (`ok | stub | blocked | captcha | js-spa |
   requires-cert | http-XXX`).

---

## 6 · "Gemini devuelve `Invalid JWT Signature`"

**Síntoma**: cualquier llamada a Vertex AI / Gemini falla con
`invalid_grant: Invalid JWT Signature`.

**Causa**: la service account key ha sido rotada o revocada en GCP IAM.

**Qué hacer**:
1. Abre https://console.cloud.google.com/iam-admin/serviceaccounts?project=globalizame-apis-493012
2. Click sobre `globalizame@globalizame-apis-493012.iam.gserviceaccount.com`
3. Pestaña **Keys** → **Add Key** → **JSON** → Create.
4. Reemplaza el archivo `D:\Globalizame\proyectos\generador-contenido\gcp-service-account.json`
   con el nuevo.
5. (Higiene) Borra o desactiva la key vieja en la misma pestaña.

---

## 7 · "Build de Vercel falla con `useSearchParams should be wrapped in a Suspense boundary`"

**Síntoma**: `npm run build` en local pasa pero el deploy a Vercel
falla.

**Causa**: nueva ruta usa `useSearchParams()` o `useRouter()` en un
client component sin `<Suspense>`.

**Qué hacer**: envuelve el componente que usa el hook en `<Suspense
fallback={null}>` como en `web/src/app/(auth)/login/page.tsx`. Ejemplo:
```tsx
export default function MyPage() {
  return (
    <Suspense fallback={null}>
      <MyContent />
    </Suspense>
  );
}
```

---

## 8 · "RLS no me deja escribir en una tabla"

**Síntomas**: insert/update vía `supabase-js` (anon key) devuelve error
"new row violates row-level security policy".

**Causa**: el usuario no está en `tenant_members` o intenta tocar una
fila de un tenant ajeno.

**Qué hacer**:
1. Verifica membership:
   ```sql
   select * from public.tenant_members where user_id = auth.uid();
   ```
2. Si la operación es legítima desde el servidor (un job, un webhook),
   usa **service_role_key** (saltar RLS). Solo en `api/` /
   `scripts/`, NUNCA en frontend.
3. Si la operación es del usuario y debería poder, revisa la política
   en `supabase/migrations/0007_rls.sql` y aplica un patch.

---

## 9 · "El cache de scrapling devuelve datos viejos"

**Síntoma**: cambias algo en una fuente pero `discover` sigue
devolviendo lo mismo.

**Causa**: caché agresivo en `~/.cache/leadhunter-pro/_kv/`.

**Qué hacer**:
```bash
# Borrar todo el caché local
rm -rf ~/.cache/leadhunter-pro/_kv/
# O solo una fuente concreta:
rm -rf ~/.cache/leadhunter-pro/_kv/borme/
```

---

## 10 · Operaciones de emergencia (en Globalizame)

### Borrar todos los datos de un sujeto (RGPD art. 17)

Via web (recomendado): `/config` → tab **Privacidad** → tipo → escribe
identificador → ESCRIBE `ERASE` en el confirm → botón borrar.

Via SQL directo (emergencia, salta el audit log):
```sql
delete from public.leads where email_principal = 'a@b.com';
-- cascade limpia outreach_events y leads_embeddings
delete from public.suppression where identifier = 'a@b.com';
```

### Apagar Cazador en frío

```bash
# Local
pkill -f "uvicorn main:app"
pkill -f "next dev"

# Producción (cuando esté desplegado)
gcloud run services update cazador-api --region europe-west1 --max-instances 0
```

### Rotar todos los secretos

1. Supabase: Studio → Settings → API → **Reset all keys**. Actualiza
   `info` + `.env` + `web/.env.local` + secrets en Vercel.
2. Gemini SA: ver sección 6.
3. Meta WhatsApp: regenerar System User token en Business Manager.

---

*Última actualización: 2026-05-23. Cuando añadas un nuevo flujo, sigue
el patrón síntoma → causa → qué hacer y manténlo corto.*
