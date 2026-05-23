-- 0003_outreach.sql
-- Plantillas, secuencias y eventos de outreach (email + WhatsApp).

create table if not exists public.outreach_templates (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references public.tenants(id) on delete cascade,
    slug        text not null,
    name        text not null,
    channel     text not null check (channel in ('email','whatsapp')),
    subject     text,                       -- solo email
    body        text not null,              -- texto plano o HTML; con merge tags {{lead.xxx}}
    variables   text[] not null default '{}',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    unique (tenant_id, slug)
);

comment on table public.outreach_templates is 'Plantillas con merge tags. Versionado por updated_at.';

create table if not exists public.outreach_sequences (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references public.tenants(id) on delete cascade,
    slug        text not null,
    name        text not null,
    -- steps: [{ "template_slug": "...", "wait_days": 3, "channel": "email" }, ...]
    steps       jsonb not null default '[]'::jsonb,
    enabled     boolean not null default true,
    created_at  timestamptz not null default now(),
    unique (tenant_id, slug)
);

comment on table public.outreach_sequences is
    'Secuencias multi-paso. Las dispara n8n leyendo de aquí.';

create table if not exists public.outreach_events (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references public.tenants(id) on delete cascade,
    lead_id         uuid not null references public.leads(id) on delete cascade,
    template_id     uuid references public.outreach_templates(id) on delete set null,
    sequence_id     uuid references public.outreach_sequences(id) on delete set null,
    channel         text not null check (channel in ('email','whatsapp')),
    event_type      text not null check (event_type in (
        'queued','sent','opened','clicked','replied',
        'bounced','unsubscribed','skipped','failed'
    )),
    skip_reason     text,
    error_message   text,
    -- meta: payload tal cual del webhook (SendGrid/Meta/etc.) cuando aplique
    meta            jsonb not null default '{}'::jsonb,
    created_at      timestamptz not null default now()
);

comment on table public.outreach_events is
    'Cada interacción con un lead. Append-only; no se borra ni edita.';

create index if not exists outreach_events_lead_idx
    on public.outreach_events(lead_id, created_at desc);

create index if not exists outreach_events_tenant_created_idx
    on public.outreach_events(tenant_id, created_at desc);

create index if not exists outreach_events_type_idx
    on public.outreach_events(tenant_id, event_type, created_at desc);
