-- 0006_pgvector.sql
-- Embeddings para dedup semántico de leads (razón social + sector).
-- Vertex AI text-embedding-004 devuelve vectores de 768 dim.

create extension if not exists vector;

create table if not exists public.leads_embeddings (
    lead_id     uuid primary key references public.leads(id) on delete cascade,
    embedding   vector(768) not null,
    model       text not null default 'text-embedding-004',
    updated_at  timestamptz not null default now()
);

comment on table public.leads_embeddings is
    'Embedding del par (razon_social, sector). Dedup semántico cross-batch.';

-- Índice ivfflat para búsqueda aproximada de vecinos. lists=100 es razonable
-- hasta ~10k leads; reconstruir con valores mayores si crecemos.
create index if not exists leads_embeddings_ivfflat_idx
    on public.leads_embeddings
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
