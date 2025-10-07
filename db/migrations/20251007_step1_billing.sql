-- Step 1 Billing Migration
-- Adiciona colunas de plano em user_settings e snapshot de plano em user_usage_events
-- Idempotência simples: checa existência via DO blocks

-- 1. user_settings: adicionar colunas se não existirem
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='user_id'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN user_id uuid UNIQUE;
        ALTER TABLE public.user_settings ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='plan_id'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN plan_id smallint DEFAULT 1;
        ALTER TABLE public.user_settings ADD CONSTRAINT user_settings_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.system_plans(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='plan_started_at'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN plan_started_at timestamptz;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='plan_renews_at'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN plan_renews_at timestamptz;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='plan_status'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN plan_status text DEFAULT 'active';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='trial_ends_at'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN trial_ends_at timestamptz;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_settings' AND column_name='next_plan_id'
    ) THEN
        ALTER TABLE public.user_settings ADD COLUMN next_plan_id smallint;
        ALTER TABLE public.user_settings ADD CONSTRAINT user_settings_next_plan_id_fkey FOREIGN KEY (next_plan_id) REFERENCES public.system_plans(id);
    END IF;
END$$;

-- 2. user_usage_events: adicionar plan_id_at_event
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='public' AND table_name='user_usage_events' AND column_name='plan_id_at_event'
    ) THEN
        ALTER TABLE public.user_usage_events ADD COLUMN plan_id_at_event smallint;
        ALTER TABLE public.user_usage_events ADD CONSTRAINT user_usage_events_plan_id_fkey FOREIGN KEY (plan_id_at_event) REFERENCES public.system_plans(id);
    END IF;
END$$;

-- 3. Índices para contagem rápida
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace 
        WHERE c.relname='user_usage_events_user_day_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_user_day_idx ON public.user_usage_events (user_id, event_type, (created_at::date));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace 
        WHERE c.relname='user_usage_events_plan_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_plan_idx ON public.user_usage_events (plan_id_at_event);
    END IF;
END$$;

-- 4. Backfill user_settings: inserir linhas para cada usuário em auth.users que não tenha registro
INSERT INTO public.user_settings (user_id, name, plan_id, plan_started_at, plan_status)
SELECT u.id, COALESCE(u.raw_user_meta_data->>'name', u.email), 1, now(), 'active'
FROM auth.users u
LEFT JOIN public.user_settings s ON s.user_id = u.id
WHERE s.user_id IS NULL;

-- 5. Backfill plan_id_at_event com plano atual do usuário (ou 1 se nulo)
UPDATE public.user_usage_events e
SET plan_id_at_event = COALESCE(s.plan_id,1)
FROM public.user_settings s
WHERE s.user_id = e.user_id AND e.plan_id_at_event IS NULL;

-- 6. (Opcional) Ajuste constraint event_type para incluir futuros 'query_success'
-- Será aplicado em step separado quando eventos forem criados.
