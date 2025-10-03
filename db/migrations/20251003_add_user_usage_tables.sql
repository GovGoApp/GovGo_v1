-- Migration: usage tracking tables
CREATE TABLE IF NOT EXISTS public.user_usage_events (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'query','favorite_add','favorite_remove',
    'summary_request','summary_success',
    'boletim_create','boletim_run'
  )),
  ref_type TEXT,
  ref_id TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_user_usage_events_user_event_time ON public.user_usage_events (user_id, event_type, created_at);

CREATE TABLE IF NOT EXISTS public.user_usage_counters (
  user_id UUID NOT NULL REFERENCES auth.users(id),
  metric_key TEXT NOT NULL,
  metric_value BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, metric_key)
);
