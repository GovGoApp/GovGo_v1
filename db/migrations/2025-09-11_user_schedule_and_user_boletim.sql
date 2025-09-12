-- Migration: Rename user_boletins -> user_schedule and create user_boletim (results)
-- Note: Run on Postgres (Render). Safe-guarded renames; will no-op if already applied.

-- 1) Rename table user_boletins -> user_schedule (if exists)
DO $$
BEGIN
  IF to_regclass('public.user_boletins') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.user_boletins RENAME TO user_schedule';
  END IF;
END $$;

-- 1.1) Rename common constraints if they exist (optional, for consistency)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'user_boletins_pkey'
  ) THEN
    EXECUTE 'ALTER TABLE public.user_schedule RENAME CONSTRAINT user_boletins_pkey TO user_schedule_pkey';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'user_boletins_schedule_type_check'
  ) THEN
    EXECUTE 'ALTER TABLE public.user_schedule RENAME CONSTRAINT user_boletins_schedule_type_check TO user_schedule_schedule_type_check';
  END IF;
END $$;

-- 2) Create table user_boletim (results for scheduled bulletins)
CREATE TABLE IF NOT EXISTS public.user_boletim (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  boletim_id BIGINT NOT NULL REFERENCES public.user_schedule(id),
  user_id TEXT NOT NULL,
  run_token TEXT NOT NULL,
  run_at TIMESTAMPTZ NOT NULL,
  numero_controle_pncp TEXT NOT NULL REFERENCES public.contratacao(numero_controle_pncp),
  similarity NUMERIC NULL,
  data_publicacao_pncp TEXT NULL,
  data_encerramento_proposta TEXT NULL,
  payload JSONB NULL,
  sent BOOLEAN NOT NULL DEFAULT FALSE,
  sent_at TIMESTAMPTZ NULL
);

-- Indexes to speed up queries
CREATE INDEX IF NOT EXISTS idx_user_boletim_boletim_pncp ON public.user_boletim (boletim_id, numero_controle_pncp);
CREATE INDEX IF NOT EXISTS idx_user_boletim_user_sent ON public.user_boletim (user_id, sent);
CREATE INDEX IF NOT EXISTS idx_user_boletim_run_token ON public.user_boletim (run_token);
CREATE INDEX IF NOT EXISTS idx_user_boletim_run_at ON public.user_boletim (run_at);
