-- Tabelas de Embeddings para contrato, ata e pca
-- Requer extensão pgvector

CREATE EXTENSION IF NOT EXISTS vector;

-- CONTRATO EMB (referencia por id_contrato, PK da tabela public.contrato)
CREATE TABLE IF NOT EXISTS public.contrato_emb (
  id_contrato_emb        bigserial PRIMARY KEY,
  id_contrato            bigint UNIQUE NOT NULL REFERENCES public.contrato(id_contrato) ON DELETE CASCADE,
  modelo_embedding       text,
  confidence             numeric,
  metadata               jsonb,
  created_at             timestamptz DEFAULT now(),
  top_categories         text[],
  top_similarities       double precision[],
  embeddings             vector
);

-- ATA EMB
CREATE TABLE IF NOT EXISTS public.ata_emb (
  id_ata_emb                   bigserial PRIMARY KEY,
  numero_controle_pncp_ata     text UNIQUE NOT NULL REFERENCES public.ata(numero_controle_pncp_ata) ON DELETE CASCADE,
  modelo_embedding             text,
  confidence                   numeric,
  metadata                     jsonb,
  created_at                   timestamptz DEFAULT now(),
  top_categories               text[],
  top_similarities             double precision[],
  embeddings                   vector
);

-- PCA EMB (embedding agregado do cabeçalho + descrições dos itens)
CREATE TABLE IF NOT EXISTS public.pca_emb (
  id_pca_emb              bigserial PRIMARY KEY,
  id_pca_pncp             text UNIQUE NOT NULL REFERENCES public.pca(id_pca_pncp) ON DELETE CASCADE,
  modelo_embedding        text,
  confidence              numeric,
  metadata                jsonb,
  created_at              timestamptz DEFAULT now(),
  top_categories          text[],
  top_similarities        double precision[],
  embeddings              vector
);
