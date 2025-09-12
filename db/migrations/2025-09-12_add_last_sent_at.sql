-- Adiciona coluna de controle de envio de boletim por agenda (não destrutivo)
ALTER TABLE IF EXISTS public.user_schedule
ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ NULL;

-- Opcional: índice simples para consultas por envio
-- CREATE INDEX IF NOT EXISTS idx_user_schedule_last_sent_at ON public.user_schedule (last_sent_at);
