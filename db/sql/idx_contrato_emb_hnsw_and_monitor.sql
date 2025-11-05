-- idx_contrato_emb_hnsw_and_monitor.sql
-- Cria índice HNSW em contrato_emb (halfvec) com parâmetros moderados e agenda coleta de estatísticas a cada 5 minutos.
-- Execute este script no Supabase SQL Editor (ou psql). Alguns passos exigem permissões de extensão.

-- =====================================================================
-- 1) Índice HNSW (CONCURRENTLY + parâmetros moderados)
-- =====================================================================
-- Observações:
-- - CONCURRENTLY evita bloquear leituras/escritas em produção.
-- - Parâmetros iniciais sugeridos: m=16, ef_construction=32 (mais leves que 32/64).
-- - WHERE embeddings_hv IS NOT NULL reduz linhas indexadas se houver NULLs.
-- - Ajuste a window com SET statement_timeout conforme o volume.

SET statement_timeout = '8h';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contrato_emb_hnsw
ON public.contrato_emb
USING hnsw (embeddings_hv halfvec_cosine_ops)
WITH (m = 16, ef_construction = 32)
WHERE embeddings_hv IS NOT NULL;

-- Ajuda o otimizador após a criação do índice
ANALYZE public.contrato_emb;

-- =====================================================================
-- 2) Monitoramento periódico (snapshot a cada 5 minutos)
-- =====================================================================
-- Requisitos: extensão pg_cron habilitada no projeto.
-- Supabase geralmente usa schema "extensions" para extensões.
-- Caso o comando com schema falhe, tente sem "WITH SCHEMA".

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA extensions;

-- Tabela de snapshots do progresso de criação de índices
CREATE TABLE IF NOT EXISTS public.index_build_stats (
  id               bigserial PRIMARY KEY,
  captured_at      timestamptz NOT NULL DEFAULT now(),
  pid              int,
  table_name       text,
  index_name       text,
  phase            text,
  tuples_done      bigint,
  tuples_total     bigint,
  pct_tuples       numeric(7,2),
  blocks_done      bigint,
  blocks_total     bigint,
  pct_blocks       numeric(7,2),
  lockers_total    int,
  lockers_done     int,
  state            text,
  wait_event_type  text,
  wait_event       text,
  query_start      timestamptz
);

-- Função de captura (insere um snapshot atual do pg_stat_progress_create_index)
-- Foca na tabela public.contrato_emb; se quiser capturar tudo, remova o WHERE relid ...
CREATE OR REPLACE FUNCTION public.capture_index_build_stats()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.index_build_stats (
    pid, table_name, index_name, phase,
    tuples_done, tuples_total, pct_tuples,
    blocks_done, blocks_total, pct_blocks,
    lockers_total, lockers_done, state,
    wait_event_type, wait_event, query_start
  )
  SELECT
    s.pid,
    (SELECT relname FROM pg_class WHERE oid = s.relid) AS table_name,
    CASE WHEN s.index_relid = 0 THEN '-' ELSE (SELECT relname FROM pg_class WHERE oid = s.index_relid) END AS index_name,
    s.phase,
    s.tuples_done,
    s.tuples_total,
    CASE WHEN s.tuples_total > 0 THEN ROUND(100.0 * s.tuples_done / s.tuples_total, 2) ELSE NULL END::numeric(7,2) AS pct_tuples,
    s.blocks_done,
    s.blocks_total,
    CASE WHEN s.blocks_total > 0 THEN ROUND(100.0 * s.blocks_done / s.blocks_total, 2) ELSE NULL END::numeric(7,2) AS pct_blocks,
    s.lockers_total,
    s.lockers_done,
    sa.state,
    sa.wait_event_type,
    sa.wait_event,
    sa.query_start
  FROM pg_stat_progress_create_index s
  LEFT JOIN pg_stat_activity sa ON sa.pid = s.pid
  WHERE s.relid = 'public.contrato_emb'::regclass;
END;
$$;

-- Agenda a execução a cada 5 minutos (idempotente)
-- OBS: Se seu pg_cron estiver no schema 'extensions', troque cron.schedule por extensions.schedule
-- e cron.job por extensions.job nos comandos abaixo.
-- Job pg_cron a cada 1 minuto (idempotente, com detecção de schema cron/extensions)
DO $job$
DECLARE has_cron boolean; has_ext boolean;
BEGIN
  SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name='cron') INTO has_cron;
  IF has_cron THEN
    -- reprograma para 1 minuto (remove se existir)
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname='monitor_idx_contrato_emb_hnsw') THEN
      PERFORM cron.unschedule((SELECT jobid FROM cron.job WHERE jobname='monitor_idx_contrato_emb_hnsw'));
    END IF;
    PERFORM cron.schedule(
      'monitor_idx_contrato_emb_hnsw',
      '* * * * *',
      'SELECT public.capture_index_build_stats();'
    );
  ELSE
    SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name='extensions') INTO has_ext;
    IF has_ext THEN
      IF EXISTS (SELECT 1 FROM extensions.job WHERE jobname='monitor_idx_contrato_emb_hnsw') THEN
        PERFORM extensions.unschedule((SELECT jobid FROM extensions.job WHERE jobname='monitor_idx_contrato_emb_hnsw'));
      END IF;
      PERFORM extensions.schedule(
        'monitor_idx_contrato_emb_hnsw',
        '* * * * *',
        'SELECT public.capture_index_build_stats();'
      );
    END IF;
  END IF;
END;
$job$;

-- Consultas úteis (opcionais) -------------------------------------------
-- Ver job agendado:
-- SELECT * FROM cron.job WHERE jobname = 'monitor_idx_contrato_emb_hnsw';
-- Cancelar job:
-- SELECT cron.unschedule((SELECT jobid FROM cron.job WHERE jobname = 'monitor_idx_contrato_emb_hnsw'));
-- Últimos snapshots:
-- SELECT * FROM public.index_build_stats ORDER BY captured_at DESC LIMIT 50;
-- Estatísticas rápidas:
-- SELECT date_trunc('hour', captured_at) h, avg(pct_blocks) avg_pct_blocks, max(pct_blocks) max_pct_blocks, count(*) samples
-- FROM public.index_build_stats GROUP BY 1 ORDER BY 1 DESC;
