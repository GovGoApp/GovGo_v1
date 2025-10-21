-- Migration: create table public.user_documents (no UNIQUE)
-- WARNING: Review before running in production

CREATE SEQUENCE IF NOT EXISTS public.user_documents_id_seq;

CREATE TABLE IF NOT EXISTS public.user_documents (
  id bigint NOT NULL DEFAULT nextval('user_documents_id_seq'::regclass),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  user_id uuid NOT NULL,
  numero_controle_pncp text NOT NULL,
  doc_name text NOT NULL,
  doc_type text,
  storage_url text NOT NULL,
  size_bytes bigint NOT NULL DEFAULT 0,
  CONSTRAINT user_documents_pkey PRIMARY KEY (id),
  CONSTRAINT user_documents_numero_controle_fkey FOREIGN KEY (numero_controle_pncp) REFERENCES public.contratacao(numero_controle_pncp)
);
