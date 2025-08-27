-- Migration: add config columns to user_prompts and insert defaults into system_config
-- Date: 2025-08-26

BEGIN;

-- 1) Add columns to store search configuration per prompt
ALTER TABLE public.user_prompts
    ADD COLUMN IF NOT EXISTS search_type SMALLINT,
    ADD COLUMN IF NOT EXISTS search_approach SMALLINT,
    ADD COLUMN IF NOT EXISTS relevance_level SMALLINT,
    ADD COLUMN IF NOT EXISTS sort_mode SMALLINT,
    ADD COLUMN IF NOT EXISTS max_results INTEGER,
    ADD COLUMN IF NOT EXISTS top_categories_count INTEGER,
    ADD COLUMN IF NOT EXISTS filter_expired BOOLEAN;

-- Optional: sensible defaults for future inserts (UI may override)
ALTER TABLE public.user_prompts
    ALTER COLUMN search_type SET DEFAULT 1,
    ALTER COLUMN search_approach SET DEFAULT 3,
    ALTER COLUMN relevance_level SET DEFAULT 2,
    ALTER COLUMN sort_mode SET DEFAULT 1,
    ALTER COLUMN max_results SET DEFAULT 30,
    ALTER COLUMN top_categories_count SET DEFAULT 10,
    ALTER COLUMN filter_expired SET DEFAULT TRUE;

-- Optional checks to keep values in range (comment out if undesired)
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_search_type_chk CHECK (search_type IN (1,2,3));
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_search_approach_chk CHECK (search_approach IN (1,2,3));
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_relevance_level_chk CHECK (relevance_level IN (1,2,3));
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_sort_mode_chk CHECK (sort_mode IN (1,2,3));
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_max_results_chk CHECK (max_results BETWEEN 1 AND 100);
-- ALTER TABLE public.user_prompts ADD CONSTRAINT user_prompts_top_categories_count_chk CHECK (top_categories_count BETWEEN 1 AND 50);

-- 2) Upsert default configuration values into system_config (key -> value)
-- Keys are snake_case as requested
INSERT INTO public.system_config (key, value, description, updated_at)
VALUES
    ('default_search_type', '1', 'Tipo de busca padrão: 1 Semântica, 2 Palavras‑chave, 3 Híbrida', CURRENT_TIMESTAMP),
    ('default_search_approach', '3', 'Abordagem padrão: 1 Direta, 2 Correspondência de Categoria, 3 Filtro de Categoria', CURRENT_TIMESTAMP),
    ('default_relevance_level', '2', 'Nível de relevância: 1 Sem filtro, 2 Flexível, 3 Restritivo', CURRENT_TIMESTAMP),
    ('default_sort_mode', '1', 'Ordenação: 1 Similaridade, 2 Data (Assinatura), 3 Valor (Final)', CURRENT_TIMESTAMP),
    ('default_max_results', '30', 'Máximo de resultados padrão', CURRENT_TIMESTAMP),
    ('default_top_categories', '10', 'Quantidade de TOP categorias padrão', CURRENT_TIMESTAMP),
    ('default_filter_expired', 'true', 'Filtrar processos com datas encerradas por padrão', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;
