-- 0007_rls.sql
-- RLS para todas las tablas con tenant_id.
-- Política: el usuario solo ve/edita filas cuyo tenant_id está en
-- public.current_user_tenants() (definido en 0001_init_tenants).

-- ── leads ──────────────────────────────────────────────────────────
alter table public.leads enable row level security;

drop policy if exists leads_rw_own on public.leads;
create policy leads_rw_own on public.leads
    for all
    using (tenant_id in (select public.current_user_tenants()))
    with check (tenant_id in (select public.current_user_tenants()));

-- ── outreach_templates ─────────────────────────────────────────────
alter table public.outreach_templates enable row level security;

drop policy if exists outreach_templates_rw_own on public.outreach_templates;
create policy outreach_templates_rw_own on public.outreach_templates
    for all
    using (tenant_id in (select public.current_user_tenants()))
    with check (tenant_id in (select public.current_user_tenants()));

-- ── outreach_sequences ─────────────────────────────────────────────
alter table public.outreach_sequences enable row level security;

drop policy if exists outreach_sequences_rw_own on public.outreach_sequences;
create policy outreach_sequences_rw_own on public.outreach_sequences
    for all
    using (tenant_id in (select public.current_user_tenants()))
    with check (tenant_id in (select public.current_user_tenants()));

-- ── outreach_events ────────────────────────────────────────────────
alter table public.outreach_events enable row level security;

drop policy if exists outreach_events_rw_own on public.outreach_events;
create policy outreach_events_rw_own on public.outreach_events
    for all
    using (tenant_id in (select public.current_user_tenants()))
    with check (tenant_id in (select public.current_user_tenants()));

-- ── suppression ────────────────────────────────────────────────────
alter table public.suppression enable row level security;

drop policy if exists suppression_rw_own on public.suppression;
create policy suppression_rw_own on public.suppression
    for all
    using (tenant_id in (select public.current_user_tenants()))
    with check (tenant_id in (select public.current_user_tenants()));

-- ── usage_events ───────────────────────────────────────────────────
alter table public.usage_events enable row level security;

drop policy if exists usage_events_rw_own on public.usage_events;
create policy usage_events_rw_own on public.usage_events
    for all
    using (
        tenant_id is null  -- métricas globales legibles por cualquier miembro
        or tenant_id in (select public.current_user_tenants())
    )
    with check (
        tenant_id is null
        or tenant_id in (select public.current_user_tenants())
    );

-- ── leads_embeddings ───────────────────────────────────────────────
-- Hereda permisos del lead: si puedes ver el lead, puedes ver su embedding.
alter table public.leads_embeddings enable row level security;

drop policy if exists leads_embeddings_rw_own on public.leads_embeddings;
create policy leads_embeddings_rw_own on public.leads_embeddings
    for all
    using (
        lead_id in (
            select id from public.leads
            where tenant_id in (select public.current_user_tenants())
        )
    )
    with check (
        lead_id in (
            select id from public.leads
            where tenant_id in (select public.current_user_tenants())
        )
    );
