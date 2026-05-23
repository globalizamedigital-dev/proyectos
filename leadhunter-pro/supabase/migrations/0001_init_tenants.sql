-- 0001_init_tenants.sql
-- Tenants y miembros del equipo Globalizame.
-- Cazador es herramienta interna: solo habrá un tenant activo ("globalizame"),
-- pero el schema mantiene multi-tenant por higiene y para no atarse las manos.

create extension if not exists "pgcrypto";

create table if not exists public.tenants (
    id          uuid primary key default gen_random_uuid(),
    slug        text not null unique,
    name        text not null,
    created_at  timestamptz not null default now()
);

comment on table public.tenants is 'Cuentas dueñas de leads. MVP: solo "globalizame".';

create table if not exists public.tenant_members (
    tenant_id   uuid not null references public.tenants(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        text not null default 'member' check (role in ('admin','member','viewer')),
    created_at  timestamptz not null default now(),
    primary key (tenant_id, user_id)
);

comment on table public.tenant_members is 'Usuarios Supabase Auth asignados a cada tenant. Driver del RLS.';

create index if not exists tenant_members_user_idx on public.tenant_members(user_id);

-- Helper: devuelve el conjunto de tenants a los que pertenece el usuario actual.
-- Se usa en políticas RLS de todas las tablas con tenant_id.
create or replace function public.current_user_tenants()
returns setof uuid
language sql
stable
security definer
set search_path = public
as $$
    select tm.tenant_id
    from public.tenant_members tm
    where tm.user_id = auth.uid()
$$;

comment on function public.current_user_tenants() is
    'Tenants a los que pertenece auth.uid(). Driver del RLS.';

-- RLS en tenants/tenant_members
alter table public.tenants enable row level security;
alter table public.tenant_members enable row level security;

drop policy if exists tenants_select_own on public.tenants;
create policy tenants_select_own on public.tenants
    for select using (id in (select public.current_user_tenants()));

drop policy if exists tenant_members_select_own on public.tenant_members;
create policy tenant_members_select_own on public.tenant_members
    for select using (
        tenant_id in (select public.current_user_tenants())
        or user_id = auth.uid()
    );

-- Trigger: cuando un usuario nuevo se registra, NO se auto-asigna a ningún
-- tenant. Mario lo añade a mano vía /config o vía SQL. Esto evita que
-- alguien que entre por magic link a otra app vea Cazador por accidente.
