# Entregabilidad de email — LeadHunter Pro

Guía práctica para que los emails de prospección **lleguen a la bandeja de
entrada** y no a spam. Una mala reputación de envío arruina cualquier campaña:
configura bien el dominio **antes** de enviar el primer email.

---

## 1. Conceptos clave

- **Reputación de envío**: los proveedores de correo (Gmail, Outlook, etc.)
  puntúan tu dominio e IP. Mala reputación = spam o rechazo.
- **Autenticación**: SPF, DKIM y DMARC demuestran que tú estás autorizado a
  enviar en nombre de tu dominio. Sin ellas, casi todo va a spam.
- **Warm-up**: aumentar el volumen de envío de forma gradual para construir
  reputación sin disparar las alarmas antispam.

---

## 2. SPF — Sender Policy Framework

SPF declara qué servidores pueden enviar correo en nombre de tu dominio.
Se publica como un registro **TXT** en el DNS del dominio.

Ejemplo (envío a través de Google Workspace):

```
Tipo:   TXT
Host:   @            (el dominio raíz, p. ej. tuempresa.es)
Valor:  v=spf1 include:_spf.google.com ~all
```

Si usas otro proveedor SMTP, sustituye `include:_spf.google.com` por el que
indique tu proveedor. Ejemplos habituales:

- Microsoft 365: `include:spf.protection.outlook.com`
- Amazon SES:    `include:amazonses.com`
- SMTP propio:   `ip4:TU.IP.DEL.SERVIDOR`

Reglas:
- Un dominio solo puede tener **un** registro SPF (combina los `include:`).
- Usa `~all` (softfail) al empezar; `-all` (hardfail) cuando tengas confianza.
- Evita superar **10 búsquedas DNS** dentro del registro SPF.

---

## 3. DKIM — DomainKeys Identified Mail

DKIM firma criptográficamente cada email. El receptor verifica la firma con una
clave pública publicada en tu DNS.

Pasos:

1. Genera el par de claves en tu proveedor de email (Google Workspace, M365,
   SES generan la clave por ti en su panel de administración).
2. El proveedor te da un registro **TXT** (o CNAME) con un selector. Ejemplo:

```
Tipo:   TXT
Host:   google._domainkey        (el "selector" lo da tu proveedor)
Valor:  v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ...   (clave pública)
```

3. Publica el registro en el DNS y **activa la firma DKIM** en el panel del
   proveedor.
4. Espera a la propagación DNS (puede tardar hasta 48 h) antes de activarlo.

---

## 4. DMARC — Domain-based Message Authentication

DMARC le dice a los receptores qué hacer con el correo que **no pasa** SPF ni
DKIM, y te envía informes. Se publica como TXT en `_dmarc.tudominio`.

Política recomendada para empezar (modo monitorización):

```
Tipo:   TXT
Host:   _dmarc
Valor:  v=DMARC1; p=none; rua=mailto:dmarc@tuempresa.es; fo=1; adkim=s; aspf=s
```

Evolución de la política `p=` a medida que ganas confianza:

1. `p=none`        — solo observar (semanas 1-4). Revisa los informes `rua`.
2. `p=quarantine`  — el correo no autenticado va a spam (cuando los informes
                     muestren que tu correo legítimo pasa SPF+DKIM).
3. `p=reject`      — el correo no autenticado se rechaza (objetivo final).

No pases a `quarantine`/`reject` hasta que los informes DMARC confirmen que
**todo tu correo legítimo** pasa la autenticación.

---

## 5. Calendario de warm-up de IP / dominio

Si el dominio o la IP son nuevos, **no envíes 200 emails el primer día**.
Calendario orientativo (ajústalo a tu volumen objetivo):

| Día / semana   | Envíos por día | Notas                                     |
|----------------|----------------|-------------------------------------------|
| Días 1-2       | 5-10           | Solo a contactos que respondan / fiables  |
| Días 3-5       | 10-20          | Vigila aperturas y respuestas             |
| Semana 2       | 20-40          | Incrementa solo si no hay quejas de spam  |
| Semana 3       | 40-60          | Mantén una tasa de rebote < 3%            |
| Semana 4       | 60-100         | Estabiliza el volumen                     |
| Semana 5+      | 100-150 máx.   | Tope prudente para prospección en frío    |

Buenas prácticas durante el warm-up:

- Empieza enviando a contactos de **alta calidad** (verificados, que respondan).
- Mantén la **tasa de rebote por debajo del 3-5%**; si sube, para y limpia la lista.
- Mantén las **quejas de spam por debajo del 0,1%**.
- Aumenta el volumen **solo** cuando las métricas sean sanas.
- Envía en **horario laboral** y de forma escalonada (no todo de golpe).

---

## 6. Límites de envío recomendados

LeadHunter Pro aplica límites por defecto en `send_outreach_batch()`:

- `min_seconds_between_sends = 45` — al menos 45 s entre envíos reales.
- `daily_cap = 40` — máximo de envíos reales por día.

Recomendaciones según el estado del dominio:

| Estado del dominio          | `daily_cap` sugerido | `min_seconds_between_sends` |
|-----------------------------|----------------------|-----------------------------|
| Nuevo (warm-up semana 1-2)  | 10-20                | 60-90 s                     |
| En warm-up (semana 3-4)     | 30-50                | 45-60 s                     |
| Establecido y con buena rep | 80-150               | 30-45 s                     |

Límites de los proveedores (referencia, pueden cambiar):

- **Gmail / Google Workspace**: ~500 destinatarios/día (cuenta gratuita ~100).
- **Microsoft 365**: ~10.000 destinatarios/día, máx. 30 mensajes/minuto.

Para prospección en frío conviene quedarse **muy por debajo** de estos topes.

---

## 7. Higiene de la lista y contenido

- **Verifica los emails** antes de enviar (evita rebotes que dañan la reputación).
- LeadHunter Pro añade automáticamente los **hard bounces** a la lista de
  supresión (`mark_bounced()`), no vuelvas a enviarles.
- Respeta siempre las **bajas** (lista de supresión, comprobada antes de enviar).
- Incluye la cabecera `List-Unsubscribe` (LeadHunter Pro la añade en cada email).
- Evita en el asunto y el cuerpo: MAYÚSCULAS excesivas, "GRATIS", "!!!",
  exceso de enlaces, imágenes pesadas sin texto.
- Mantén una **relación texto/HTML** equilibrada; el texto plano ayuda.
- Personaliza el mensaje (nombre, empresa, sector): mejora aperturas y reduce
  marcas de spam.

---

## 8. Comprobación final antes de la primera campaña

- [ ] Registro **SPF** publicado y válido.
- [ ] **DKIM** activado y firmando (clave pública en DNS).
- [ ] Registro **DMARC** publicado (al menos `p=none` con `rua`).
- [ ] DNS propagado (verifica con herramientas tipo `dig` o validadores online).
- [ ] Dominio en **warm-up** si es nuevo.
- [ ] `daily_cap` y `min_seconds_between_sends` ajustados al estado del dominio.
- [ ] Lista limpia de rebotes y supresiones.
- [ ] Email de prueba a una cuenta propia (Gmail/Outlook) revisando que NO
      cae en spam y que pasa SPF/DKIM/DMARC (mira las cabeceras del mensaje).
