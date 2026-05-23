-- 0005_usage_events.sql
-- Telemetría de consumo de servicios externos con cuota.
-- Hoy: Vertex AI Gemini + Meta WhatsApp Cloud. Free tier monitorizado.

create table if not exists public.usage_events (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid references public.tenants(id) on delete cascade,
    service         text not null check (service in (
        'gemini','meta_whatsapp','smtp','supabase'
    )),
    operation       text,                 -- 'entity_resolve','classify_cnae','score_lead', etc.
    units           int not null default 1,
    cost_eur        numeric(10,4),        -- opcional; 0 mientras todo sea free tier
    free_tier_remaining_pct numeric(5,2), -- 0..100, null si no aplica
    meta            jsonb not null default '{}'::jsonb,
    created_at      timestamptz not null default now()
);

comment on table public.usage_events is
    'Consumo de servicios externos. Vigilancia del free tier.';

create index if not exists usage_events_service_created_idx
    on public.usage_events(service, created_at desc);

create index if not exists usage_events_tenant_service_idx
    on public.usage_events(tenant_id, service, created_at desc);
