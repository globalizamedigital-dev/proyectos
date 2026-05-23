-- seed.sql
-- Datos iniciales para Cazador Globalizame.
-- Único tenant del MVP: globalizame.
-- Idempotente: se puede correr varias veces sin romper.

insert into public.tenants (id, slug, name)
values ('00000000-0000-0000-0000-000000000001', 'globalizame', 'Globalizame')
on conflict (slug) do nothing;

-- Plantillas de outreach base (Isra Bravo style, sin emojis, directo)
insert into public.outreach_templates (tenant_id, slug, name, channel, subject, body, variables)
values (
    '00000000-0000-0000-0000-000000000001',
    'email_cold_es',
    'Cold email B2B en español (Isra Bravo)',
    'email',
    '{{empresa}} — ¿integramos IA en vuestro equipo?',
    'Hola {{nombre_corto}},

He visto que {{empresa}} es referencia en {{sector}}. Te escribo directo: en los últimos meses hemos ayudado a empresas como la vuestra a automatizar tareas repetitivas y liberar hasta un 30% del tiempo del equipo.

Te propongo una llamada de 15 minutos para ver si encaja. Si no, te lo digo a la cara.

¿Tienes hueco esta semana o la siguiente?

Mario Ruiz
Globalizame · globalizame.com

---
Para no recibir más correos: {{enlace_baja}}',
    array['nombre_corto','empresa','sector','enlace_baja']
)
on conflict (tenant_id, slug) do nothing;

insert into public.outreach_templates (tenant_id, slug, name, channel, subject, body, variables)
values (
    '00000000-0000-0000-0000-000000000001',
    'email_followup_es',
    'Follow-up corto a los 3 días',
    'email',
    'Re: {{empresa}}',
    'Hola {{nombre_corto}},

Te escribí hace unos días. No quiero darte la lata: si no encaja, dímelo y te elimino de mi lista. Sin rencor.

Si sí encaja, me dices y agendamos los 15 min.

Mario

---
Para no recibir más correos: {{enlace_baja}}',
    array['nombre_corto','empresa','enlace_baja']
)
on conflict (tenant_id, slug) do nothing;

-- Secuencia base: touch1 → 3 días → touch2 (follow-up). Sin touch3 en MVP.
insert into public.outreach_sequences (tenant_id, slug, name, steps, enabled)
values (
    '00000000-0000-0000-0000-000000000001',
    'cold_b2b_v1',
    'Cold B2B v1 (2 toques)',
    '[
        {"template_slug": "email_cold_es", "wait_days": 0, "channel": "email"},
        {"template_slug": "email_followup_es", "wait_days": 3, "channel": "email"}
    ]'::jsonb,
    true
)
on conflict (tenant_id, slug) do nothing;
