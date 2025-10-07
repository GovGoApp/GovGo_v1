-- Step 2 Billing Data Model Migration
-- Idempotent adjustments for billing: users plan columns, plan snapshot in usage events, usage daily view.

-- 1) Ensure system_plans table exists (reference only, skip if already created externally)
-- (Commented out to avoid accidental overwrite)
-- CREATE TABLE IF NOT EXISTS public.system_plans (
--   id SMALLINT PRIMARY KEY,
--   code TEXT UNIQUE NOT NULL,
--   name TEXT NOT NULL,
--   price_month_brl NUMERIC(10,2) NOT NULL,
--   limit_consultas_per_day INTEGER NOT NULL,
--   limit_favoritos_capacity INTEGER NOT NULL,
--   limit_boletim_per_day INTEGER NOT NULL,
--   limit_resumos_per_day INTEGER NOT NULL,
--   active BOOLEAN NOT NULL DEFAULT TRUE,
--   created_at TIMESTAMPTZ NOT NULL DEFAULT now()
-- );

-- 2) Users table plan columns (assume users table exists; adjust name if different)
ALTER TABLE public.user_settings
  ADD COLUMN IF NOT EXISTS plan_id SMALLINT DEFAULT 1,
  ADD COLUMN IF NOT EXISTS plan_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS plan_renews_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS plan_status TEXT DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ;

-- 3) Foreign key (deferred if system_plans already loaded)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'user_settings_plan_id_fkey'
  ) THEN
    ALTER TABLE public.user_settings
      ADD CONSTRAINT user_settings_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.system_plans(id);
  END IF;
END$$;

-- 4) Add plan snapshot to usage events table if exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='user_usage_events') THEN
    ALTER TABLE public.user_usage_events
      ADD COLUMN IF NOT EXISTS plan_id_at_event SMALLINT;
  END IF;
END$$;

-- 5) Backfill plan snapshot
DO $$
DECLARE
  v_sql text;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='user_usage_events' AND column_name='plan_id_at_event') THEN
    UPDATE public.user_usage_events uue
      SET plan_id_at_event = us.plan_id
    FROM public.user_settings us
    WHERE uue.user_id::text = us.id::text AND uue.plan_id_at_event IS NULL;
  END IF;
END$$;

-- 6) Indexes for usage queries
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user_usage_events') THEN
    CREATE INDEX IF NOT EXISTS idx_uue_user_event_date ON public.user_usage_events (user_id, event_type, (created_at::date));
    CREATE INDEX IF NOT EXISTS idx_uue_plan ON public.user_usage_events (plan_id_at_event);
  END IF;
END$$;

-- 7) Optional materialized view for daily aggregates (create if not exists pattern)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_matviews WHERE schemaname='public' AND matviewname='user_usage_daily'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user_usage_events'
  ) THEN
    EXECUTE 'CREATE MATERIALIZED VIEW public.user_usage_daily AS
      SELECT user_id, created_at::date AS dia, event_type, COUNT(*) AS qtd
      FROM public.user_usage_events
      GROUP BY 1,2,3';
    CREATE INDEX idx_user_usage_daily_key ON public.user_usage_daily (user_id, dia, event_type);
  END IF;
END$$;

-- 8) Comment docs
COMMENT ON COLUMN public.user_settings.plan_id IS 'FK system_plans.id';
COMMENT ON COLUMN public.user_settings.plan_status IS 'active|past_due|canceled|trial';
COMMENT ON COLUMN public.user_usage_events.plan_id_at_event IS 'Snapshot do plano vigente no momento do evento';

-- End Step 2
