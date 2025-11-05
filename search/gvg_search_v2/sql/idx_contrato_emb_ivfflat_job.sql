-- GovGo v1 – Índice IVFFLAT para contrato_emb (halfvec)
-- Objetivo: criar o índice no servidor sem depender da sessão do editor (pg_cron) e evitar timeouts.
-- Tabela/coluna: public.contrato_emb(embeddings_hv) com halfvec_cosine_ops.
-- Estratégia: agendar CREATE INDEX CONCURRENTLY como um único comando via pg_cron. Idempotente.

-- IMPORTANTE:
-- 1) Em Supabase, pg_cron já costuma estar disponível. Se não estiver, ative:
--    CREATE EXTENSION IF NOT EXISTS pg_cron;
-- 2) Para evitar timeout do job, ajuste temporariamente o statement_timeout no NÍVEL DO BANCO (mais seguro):
--    ALTER DATABASE postgres SET statement_timeout = '12h';
--    -- Depois de concluir o índice, reverta:
--    -- ALTER DATABASE postgres RESET statement_timeout;
-- 3) Não coloque DO/FUNCTION envolvendo CREATE INDEX CONCURRENTLY. O cron deve executar SÓ o CREATE.

-- (Opcional) Limpa job anterior com o mesmo nome
SELECT cron.unschedule('contrato_emb_ivfflat_build')
WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'contrato_emb_ivfflat_build');

-- Agenda o CREATE INDEX CONCURRENTLY como ÚNICO comando
-- Ajuste lists conforme necessário (recomendado 800–1600 para 1,6M linhas). Comece com 1200.
SELECT cron.schedule(
  'contrato_emb_ivfflat_build',
  '*/1 * * * *',
  $$CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contrato_emb_ivfflat
    ON public.contrato_emb
    USING ivfflat (embeddings_hv halfvec_cosine_ops)
    WITH (lists = 1200)
    WHERE embeddings_hv IS NOT NULL$$
);

-- (Opcional) ANALYZE em job separado – também único comando, remova após concluir
SELECT cron.unschedule('contrato_emb_analyze_once')
WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'contrato_emb_analyze_once');

SELECT cron.schedule(
  'contrato_emb_analyze_once',
  '0 * * * *',
  $$ANALYZE public.contrato_emb$$
);

-- =====================
-- Verificações de progresso
-- =====================
-- Em andamento? (vazio = nada criando)
-- SELECT
--   s.pid,
--   a.relname AS table_name,
--   COALESCE(ai.relname, '-') AS index_name,
--   s.phase, s.tuples_done, s.tuples_total,
--   s.blocks_done, s.blocks_total,
--   sa.state, sa.wait_event_type, sa.wait_event,
--   sa.query_start, now() - sa.query_start AS running_for,
--   LEFT(sa.query, 200) AS query_sample
-- FROM pg_stat_progress_create_index s
-- JOIN pg_stat_activity sa ON sa.pid = s.pid
-- LEFT JOIN pg_class a  ON a.oid  = s.relid
-- LEFT JOIN pg_class ai ON ai.oid = s.index_relid
-- ORDER BY sa.query_start DESC;

-- Índice criado e válido?
-- SELECT c.relname AS index_name, am.amname AS method, ix.indisvalid, ix.indisready,
--        pg_get_expr(ix.indpred, ix.indrelid) AS predicate
-- FROM pg_class c
-- JOIN pg_index ix ON ix.indexrelid = c.oid
-- JOIN pg_am am ON am.oid = c.relam
-- WHERE c.relname IN ('idx_contrato_emb_ivfflat');

-- Tamanho do índice
-- SELECT relname, pg_size_pretty(pg_relation_size(relid)) AS index_size
-- FROM pg_stat_all_indexes
-- WHERE schemaname='public' AND relname IN ('idx_contrato_emb_ivfflat');

-- Uso efetivo (antes/depois de uma consulta de similaridade)
-- SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname='public' AND indexrelname='idx_contrato_emb_ivfflat';

-- =====================
-- Cancelar jobs após concluir
-- =====================
-- SELECT cron.unschedule('contrato_emb_ivfflat_build');
-- SELECT cron.unschedule('contrato_emb_analyze_once');

-- =====================
-- Dica de consulta (probes):
-- =====================
-- SET LOCAL ivfflat.probes = 32;  -- teste 16/32/64
-- SET LOCAL enable_seqscan = off;
-- EXPLAIN ANALYZE
-- WITH q AS (
--   SELECT embeddings_hv AS v FROM public.contrato_emb WHERE embeddings_hv IS NOT NULL LIMIT 1
-- )
-- SELECT numero_controle_pncp
-- FROM public.contrato_emb t
-- CROSS JOIN q
-- ORDER BY t.embeddings_hv <=> q.v
-- LIMIT 10;
