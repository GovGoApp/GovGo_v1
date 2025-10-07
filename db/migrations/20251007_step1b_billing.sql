-- Step1b Billing Migration (rebuild user_settings and fix index strategy)
-- Recria user_settings com PK=user_id e adiciona snapshot de plano em user_usage_events.
-- Substitui migration anterior 20251007_step1_billing.sql.

BEGIN;

-- 1. Recriar user_settings
DROP TABLE IF EXISTS public.user_settings CASCADE;
CREATE TABLE public.user_settings (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    name text,
    plan_id smallint NOT NULL DEFAULT 1 REFERENCES public.system_plans(id),
    plan_started_at timestamptz,
    plan_renews_at timestamptz,
    plan_status text NOT NULL DEFAULT 'active',
    trial_ends_at timestamptz,
    next_plan_id smallint REFERENCES public.system_plans(id)
);

-- 2. Ajustes user_usage_events: adicionar plan_id_at_event (se faltar) e coluna gerada created_date
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='user_usage_events' AND column_name='plan_id_at_event'
    ) THEN
        ALTER TABLE public.user_usage_events ADD COLUMN plan_id_at_event smallint REFERENCES public.system_plans(id);
    END IF;
END$$;

-- 2b. Coluna gerada (se possível) para data (IMMUTABLE) usada em índices/queries diárias
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='user_usage_events' AND column_name='created_date'
    ) THEN
        ALTER TABLE public.user_usage_events ADD COLUMN created_date date GENERATED ALWAYS AS (created_at::date) STORED;
    END IF;
END$$;

-- 3. Índices (evitar função não IMMUTABLE usando coluna gerada)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relname='user_usage_events_user_day_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_user_day_idx ON public.user_usage_events (user_id, event_type, created_date);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relname='user_usage_events_plan_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_plan_idx ON public.user_usage_events (plan_id_at_event);
    END IF;
END$$;

-- 4. Backfill user_settings para usuários existentes
INSERT INTO public.user_settings (user_id, name, plan_id, plan_started_at, plan_status)
SELECT u.id, COALESCE(u.raw_user_meta_data->>'name', u.email), 1, now(), 'active'
FROM auth.users u
LEFT JOIN public.user_settings s ON s.user_id = u.id
WHERE s.user_id IS NULL;

-- 5. Backfill plan_id_at_event
UPDATE public.user_usage_events e
SET plan_id_at_event = COALESCE(s.plan_id,1)
FROM public.user_settings s
WHERE s.user_id = e.user_id AND e.plan_id_at_event IS NULL;

COMMIT;
