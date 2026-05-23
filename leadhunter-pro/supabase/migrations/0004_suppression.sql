-- 0004_suppression.sql
-- Lista de supresión cross-canal: emails/teléfonos/NIFs que NO se contactan.
-- Una baja es definitiva (GDPR + LSSI). Se respeta para siempre.

create table if not exists public.suppression (
    tenant_id    uuid not null references public.tenants(id) on delete cascade,
    channel      text not null check (channel in ('email','whatsapp','phone','nif')),
    identifier   text not null,
    reason       text not null check (reason in (
        'user_unsubscribed','hard_bounce','spam_complaint',
        'gdpr_erase','manual','imported'
    )),
    notes        text,
    created_at   timestamptz not null default now(),
    primary key (tenant_id, channel, identifier)
);

comment on table public.suppression is
    'Lista de supresión definitiva por canal. Driver de "skipped:suppressed".';

create index if not exists suppression_identifier_idx
    on public.suppression(identifier);

-- Normalización: NIF en mayúsculas, email/teléfono en minúsculas y sin espacios
create or replace function public.normalize_suppression_identifier()
returns trigger
language plpgsql
as $$
begin
    if new.channel = 'nif' then
        new.identifier := upper(regexp_replace(new.identifier, '\s+', '', 'g'));
    elsif new.channel = 'email' then
        new.identifier := lower(trim(new.identifier));
    elsif new.channel in ('whatsapp','phone') then
        new.identifier := regexp_replace(new.identifier, '\s+', '', 'g');
    end if;
    return new;
end;
$$;

drop trigger if exists suppression_normalize on public.suppression;
create trigger suppression_normalize
    before insert or update on public.suppression
    for each row execute function public.normalize_suppression_identifier();
