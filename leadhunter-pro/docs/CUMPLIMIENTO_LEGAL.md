# Cumplimiento legal — LeadHunter Pro

> **AVISO**: Este documento es una guía práctica de cumplimiento, no constituye
> asesoramiento jurídico. Antes de lanzar campañas de prospección comercial,
> revisa esta documentación con un profesional legal especializado en
> protección de datos.

LeadHunter Pro trata datos personales (emails, nombres de decisores, teléfonos)
de empresas y profesionales. En España esto está regulado, principalmente, por:

- **RGPD** — Reglamento (UE) 2016/679 General de Protección de Datos.
- **LOPDGDD** — Ley Orgánica 3/2018 de Protección de Datos Personales.
- **LSSI-CE** — Ley 34/2002 de Servicios de la Sociedad de la Información y
  de Comercio Electrónico (en particular su **artículo 21**, comunicaciones
  comerciales por vía electrónica).

---

## 1. Consentimiento para email comercial B2B en España (LSSI-CE)

**Punto clave**: en España, el **artículo 21 de la LSSI-CE** prohíbe el envío de
comunicaciones comerciales por correo electrónico (o equivalente) que **no hayan
sido solicitadas o expresamente autorizadas** por el destinatario.

Esto significa que, como regla general, **se requiere consentimiento previo**
también para el email comercial B2B. La LSSI-CE no distingue entre destinatario
particular y profesional cuando la comunicación va dirigida a una **persona
física identificada o identificable** (p. ej. `nombre.apellido@empresa.es`).

### Excepción del artículo 21.2 (relación contractual previa)

Sí se permite enviar comunicaciones comerciales **sin consentimiento previo**
cuando concurren **todas** estas condiciones:

1. Existe una **relación contractual previa** con el destinatario.
2. Los datos se obtuvieron **lícitamente** en el marco de esa relación.
3. La comunicación se refiere a **productos o servicios similares** a los que
   inicialmente fueron objeto de contratación.
4. En **cada** comunicación se ofrece al destinatario la posibilidad de
   **oponerse / darse de baja** de forma sencilla y gratuita.

### Direcciones genéricas de empresa

El envío a buzones **genéricos no nominativos** (`info@`, `contacto@`,
`administracion@`) que **no identifican a una persona física** se considera, en
la práctica, fuera del ámbito subjetivo del RGPD (no hay dato personal). Aun
así, sigue aplicando la LSSI-CE respecto a la comunicación comercial. Mantén un
criterio prudente: prioriza estos buzones genéricos frente a emails nominativos
cuando no dispongas de base de legitimación clara.

### Conclusión operativa

- Email **nominativo** de un profesional → necesitas consentimiento **o** una
  base de interés legítimo sólida y documentada (ver sección 3 — LIA), y
  siempre con derecho de oposición claro.
- Email **genérico** de empresa → menor riesgo RGPD, pero sigue aplicando la
  LSSI-CE. Incluye siempre el mecanismo de baja.
- En **todos** los casos: identifícate, indica que es publicidad, ofrece baja.

---

## 2. ROPA — Registro de Actividades de Tratamiento (plantilla)

El RGPD (art. 30) obliga a mantener un Registro de Actividades de Tratamiento.
Rellena esta ficha para la actividad "Prospección comercial B2B".

```
REGISTRO DE ACTIVIDADES DE TRATAMIENTO
Actividad: Prospección comercial / generación de leads B2B

1. RESPONSABLE DEL TRATAMIENTO
   - Nombre / razón social: ____________________________________
   - NIF/CIF:               ____________________________________
   - Dirección postal:      ____________________________________
   - Email de contacto:     ____________________________________
   - Delegado de Protección de Datos (DPO), si aplica: __________

2. FINES DEL TRATAMIENTO
   - Identificación de empresas y profesionales potencialmente
     interesados en los productos/servicios de la empresa.
   - Envío de comunicaciones comerciales de prospección.
   - Gestión de la relación comercial previa al contrato.

3. BASE JURÍDICA (art. 6 RGPD)
   [ ] Consentimiento del interesado (art. 6.1.a)
   [ ] Interés legítimo del responsable (art. 6.1.f)
       -> Requiere test de ponderación documentado (ver sección 3)
   [ ] Ejecución de un contrato o medidas precontractuales (art. 6.1.b)

4. CATEGORÍAS DE INTERESADOS
   - Personas de contacto / decisores de empresas (B2B).
   - Profesionales autónomos.

5. CATEGORÍAS DE DATOS PERSONALES
   - Datos identificativos: nombre y apellidos, cargo.
   - Datos de contacto profesional: email, teléfono.
   - Datos de la empresa asociada: razón social, NIF, sector, web.
   - NO se tratan categorías especiales de datos (art. 9 RGPD).

6. ORIGEN DE LOS DATOS
   - Fuentes de acceso público: BORME, PLACSP, Infosubvenciones,
     registro de DPOs de la AEPD, OpenStreetMap, webs corporativas.
   - Datos inferidos: permutaciones de email a partir de nombre + dominio.
   - Indica aquí cualquier fuente adicional: ____________________

7. CATEGORÍAS DE DESTINATARIOS
   - Personal interno de la empresa (departamento comercial).
   - Encargados de tratamiento (p. ej. proveedor de email/SMTP): ____

8. TRANSFERENCIAS INTERNACIONALES
   [ ] No se realizan.
   [ ] Sí, a: __________ con garantías: __________________________

9. PLAZOS DE SUPRESIÓN
   - Leads sin respuesta: ______ meses desde el último contacto.
   - Bajas / oposiciones: se conservan en lista de supresión de forma
     indefinida con la única finalidad de NO volver a contactar.
   - Leads convertidos en clientes: pasan al tratamiento "Clientes".

10. MEDIDAS DE SEGURIDAD (art. 32 RGPD)
   - Credenciales SMTP fuera del código (archivo .env, no versionado).
   - Acceso restringido a las bases de datos locales (.db).
   - Registro de actividad (log) de envíos y bajas.
   - Lista de supresión persistente comprobada antes de cada envío.

   Fecha de última actualización del registro: ____ / ____ / ______
```

---

## 3. LIA — Test de interés legítimo (balancing test)

Si la base jurídica elegida es el **interés legítimo** (art. 6.1.f RGPD), debes
documentar un test de ponderación ANTES de iniciar la prospección. Plantilla:

```
TEST DE INTERÉS LEGÍTIMO (LIA) — Prospección comercial B2B

PASO 1. IDENTIFICACIÓN DEL INTERÉS LEGÍTIMO
   - ¿Cuál es el interés legítimo perseguido?
     El desarrollo de la actividad comercial de la empresa mediante la
     captación de nuevos clientes en el ámbito B2B.
   - ¿Es un interés real, actual y lícito? [ ] Sí  [ ] No
   - Considerando 47 RGPD: el marketing directo PUEDE constituir un
     interés legítimo. ¿Aplica a este caso?  ________________________

PASO 2. TEST DE NECESIDAD
   - ¿El tratamiento es necesario para lograr el interés? [ ] Sí [ ] No
   - ¿Existe una forma menos intrusiva de lograrlo?
     ________________________________________________________________
   - ¿Se tratan solo los datos mínimos imprescindibles (minimización)?
     [ ] Sí — solo contacto profesional, nada de categorías especiales.

PASO 3. TEST DE PONDERACIÓN (equilibrio de intereses)
   a) Naturaleza de los datos:
      - Datos de contacto PROFESIONAL, no de la esfera privada.  [Bajo riesgo]
      - ¿Se usan emails nominativos de personas físicas?  ______________
   b) Expectativas razonables del interesado:
      - ¿Un profesional cuyo email aparece en fuentes públicas
        esperaría recibir una propuesta comercial B2B relevante
        para su sector?  [ ] Sí  [ ] No  [ ] Parcialmente
   c) Impacto sobre el interesado:
      - Impacto previsible: bajo (un email comercial puntual y relevante).
      - Posible molestia mitigada por: segmentación por sector,
        frecuencia limitada y baja inmediata en cada envío.
   d) Garantías adicionales aplicadas:
      [ ] Mecanismo de baja claro en cada comunicación (responde BAJA).
      [ ] Lista de supresión que impide volver a contactar.
      [ ] Cap diario de envíos y throttle entre envíos.
      [ ] No se contacta a buzones que ya hayan rechazado.
      [ ] Información de transparencia disponible (política de privacidad).

PASO 4. CONCLUSIÓN
   - ¿Prevalece el interés legítimo sobre los derechos y libertades
     del interesado?  [ ] Sí  [ ] No
   - Si la conclusión es afirmativa, el interés legítimo es base válida.
   - Si es negativa o dudosa, NO uses interés legítimo: obtén
     consentimiento previo.

   Responsable de la valoración: __________________________________
   Fecha: ____ / ____ / ______     Revisión prevista: ____________
```

---

## 4. Checklist previo al outreach (LSSI-CE art. 21 + RGPD)

Antes de lanzar **cualquier** campaña, verifica:

- [ ] **Base jurídica definida** y documentada (consentimiento, interés
      legítimo con LIA, o relación contractual previa).
- [ ] **ROPA actualizado** con la actividad de prospección comercial.
- [ ] **Política de privacidad** publicada y accesible (web corporativa).
- [ ] La comunicación se **identifica como publicidad** de forma clara.
- [ ] El **remitente está identificado** (nombre/razón social real).
- [ ] Cada email incluye un **mecanismo de baja sencillo y gratuito**
      (LeadHunter Pro: respuesta "BAJA" + cabecera `List-Unsubscribe`).
- [ ] Existe un **proceso para atender las bajas** sin demora
      (`outreach.process_unsubscribe_request()` -> lista de supresión).
- [ ] La **lista de supresión** se comprueba **antes de cada envío**
      (integrado en `send_email()` y `send_outreach_batch()`).
- [ ] Se respeta un **plazo de conservación** definido para los leads.
- [ ] Las **credenciales SMTP** están en `.env` (no en el código ni en JSON).
- [ ] Se aplica **minimización**: solo datos de contacto profesional.
- [ ] Se segmenta por **sector relevante** (la oferta debe ser pertinente).
- [ ] Se respetan los **derechos del interesado**: acceso, rectificación,
      supresión, oposición. Hay un email de contacto para ejercerlos.
- [ ] Frecuencia de contacto **limitada** (cap diario + throttle activos).
- [ ] Si hay encargados de tratamiento (proveedor SMTP, etc.), existe el
      correspondiente **contrato de encargo** (art. 28 RGPD).

---

## 5. Cómo LeadHunter Pro ayuda al cumplimiento

| Obligación legal                         | Funcionalidad de la app                          |
|------------------------------------------|--------------------------------------------------|
| Atender bajas / oposiciones              | `scripts/suppression.py` (lista de supresión)    |
| No contactar a quien se dio de baja      | Comprobación en `send_email` y `send_outreach_batch` |
| Mecanismo de baja en cada email          | Cabecera `List-Unsubscribe` + placeholder `{enlace_baja}` |
| Procesar respuestas "BAJA"               | `outreach.process_unsubscribe_request()`         |
| Gestionar rebotes (hard bounce)          | `outreach.mark_bounced()` -> supresión           |
| Frecuencia razonable de envío            | `min_seconds_between_sends` + `daily_cap`        |
| Trazabilidad de envíos                   | `outreach.db` (tabla `outreach_log`)             |
| Seguridad de credenciales                | `scripts/config.py` + archivo `.env` no versionado |
| Plazo de conservación                    | `leads_db` con `first_seen` / `last_seen`        |

> Recuerda: estas funcionalidades son **herramientas de apoyo**. La
> responsabilidad del cumplimiento recae en el responsable del tratamiento.
