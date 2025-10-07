-- Step1c Billing Migration (simplificado)
-- Objetivo: recriar user_settings (caso não esteja consistente) e adicionar plan_id_at_event + coluna de data simples para facilitar índices diários.
-- Removemos coluna gerada (que falhou) e usamos coluna simples + trigger para manter created_at_date.

BEGIN;

-- 1. Recriar user_settings (idempotente via DROP/CREATE)
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

-- 2. Garantir coluna plan_id_at_event em user_usage_events
ALTER TABLE public.user_usage_events
    ADD COLUMN IF NOT EXISTS plan_id_at_event smallint REFERENCES public.system_plans(id);

-- 3. Adicionar coluna simples created_at_date (sem generated)
ALTER TABLE public.user_usage_events
    ADD COLUMN IF NOT EXISTS created_at_date date;

-- 3a. Backfill created_at_date
UPDATE public.user_usage_events SET created_at_date = created_at::date WHERE created_at_date IS NULL;

-- 3b. Trigger para manter created_at_date em futuros inserts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'user_usage_events_set_date'
    ) THEN
        CREATE FUNCTION user_usage_events_set_date() RETURNS trigger AS $$
        BEGIN
            IF NEW.created_at_date IS NULL THEN
                NEW.created_at_date = NEW.created_at::date;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'tg_user_usage_events_set_date'
    ) THEN
        CREATE TRIGGER tg_user_usage_events_set_date
        BEFORE INSERT ON public.user_usage_events
        FOR EACH ROW
        EXECUTE FUNCTION user_usage_events_set_date();
    END IF;
END$$;

-- 4. Índices (usar created_at_date)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relname='user_usage_events_user_day_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_user_day_idx ON public.user_usage_events (user_id, event_type, created_at_date);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relname='user_usage_events_plan_idx' AND n.nspname='public'
    ) THEN
        CREATE INDEX user_usage_events_plan_idx ON public.user_usage_events (plan_id_at_event);
    END IF;
END$$;

-- 5. Backfill user_settings
INSERT INTO public.user_settings (user_id, name, plan_id, plan_started_at, plan_status)
SELECT u.id, COALESCE(u.raw_user_meta_data->>'name', u.email), 1, now(), 'active'
FROM auth.users u
LEFT JOIN public.user_settings s ON s.user_id = u.id
WHERE s.user_id IS NULL;

-- 6. Backfill plan_id_at_event
UPDATE public.user_usage_events e
SET plan_id_at_event = COALESCE(s.plan_id,1)
FROM public.user_settings s
WHERE s.user_id = e.user_id AND e.plan_id_at_event IS NULL;

COMMIT;
