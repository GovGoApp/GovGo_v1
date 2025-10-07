-- Step2b: remover 'query_success' do CHECK (reverte mudança)
BEGIN;
ALTER TABLE public.user_usage_events DROP CONSTRAINT IF EXISTS user_usage_events_event_type_check;
ALTER TABLE public.user_usage_events
  ADD CONSTRAINT user_usage_events_event_type_check CHECK (event_type = ANY (ARRAY[
    'query', 'favorite_add', 'favorite_remove', 'summary_request', 'summary_success', 'boletim_create', 'boletim_run'
  ]));
COMMIT;
