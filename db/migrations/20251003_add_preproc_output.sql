-- Adiciona coluna de cache do pré-processamento nas tabelas de prompts e agendamentos
-- Seguro para executar múltiplas vezes (IF NOT EXISTS)

ALTER TABLE IF EXISTS public.user_schedule
    ADD COLUMN IF NOT EXISTS preproc_output jsonb;

ALTER TABLE IF EXISTS public.user_prompts
    ADD COLUMN IF NOT EXISTS preproc_output jsonb;

-- Opcional: índices GIN se necessário para consultas futuras
-- CREATE INDEX IF NOT EXISTS idx_user_schedule_preproc_output ON public.user_schedule USING GIN (preproc_output);
-- CREATE INDEX IF NOT EXISTS idx_user_prompts_preproc_output ON public.user_prompts USING GIN (preproc_output);
