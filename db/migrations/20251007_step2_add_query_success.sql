-- Step2: adicionar event_type 'query_success'
BEGIN;
ALTER TABLE public.user_usage_events DROP CONSTRAINT IF EXISTS user_usage_events_event_type_check;
ALTER TABLE public.user_usage_events
  ADD CONSTRAINT user_usage_events_event_type_check CHECK (event_type = ANY (ARRAY[
    'query', 'query_success', 'favorite_add', 'favorite_remove', 'summary_request', 'summary_success', 'boletim_create', 'boletim_run'
  ]));
COMMIT;
