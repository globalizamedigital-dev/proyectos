-- 0002_leads.sql
-- Tabla principal: leads B2B cualificados.
-- Reemplaza el SQLite local (scripts/leads_db.py). dedup_key viene del
-- mismo cálculo: hash(nif || razon_social_normalized || domain).

create table if not exists public.leads (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references public.tenants(id) on delete cascade,
    dedup_key       text not null,

    -- Identidad
    nif             text,
    razon_social    text,
    domain          text,
    cnae            text,
    sector          text,
    provincia       text,
    city            text,

    -- Scoring
    score           int not null default 0,
    grade           char(1) not null default 'D' check (grade in ('A','B','C','D')),
    score_rationale text,

    -- Contacto principal (resto en `data` jsonb)
    decisor         text,
    decisor_role    text,
    email_principal text,
    telefono        text,

    -- Estado operativo
    outreach_status text not null default 'new'
        check (outreach_status in ('new','queued','sent','replied','bounced','unsubscribed','do_not_contact')),

    -- Trazabilidad
    sources_hit     text[] not null default '{}',
    first_seen      timestamptz not null default now(),
    last_seen       timestamptz not null default now(),

    -- Snapshot completo: lo que el adapter devolvió (preserva schema 2.0.0)
    data            jsonb not null default '{}'::jsonb,

    unique (tenant_id, dedup_key)
);

comment on table public.leads is 'Corpus de leads cualificados. Dedup por (tenant_id, dedup_key).';

-- Índices para los filtros más comunes en /leads y /discover
create index if not exists leads_tenant_score_idx
    on public.leads(tenant_id, score desc);

create index if not exists leads_tenant_provincia_idx
    on public.leads(tenant_id, provincia);

create index if not exists leads_tenant_status_idx
    on public.leads(tenant_id, outreach_status);

create index if not exists leads_tenant_sector_idx
    on public.leads(tenant_id, sector);

create index if not exists leads_nif_idx on public.leads(nif) where nif is not null;

-- Trigger para mantener last_seen al hacer UPDATE
create or replace function public.touch_last_seen()
returns trigger
language plpgsql
as $$
begin
    new.last_seen := now();
    return new;
end;
$$;

drop trigger if exists leads_touch_last_seen on public.leads;
create trigger leads_touch_last_seen
    before update on public.leads
    for each row execute function public.touch_last_seen();
