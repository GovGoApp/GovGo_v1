"""User usage tracking utilities."""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import os
from gvg_database import db_execute, db_execute_many
from gvg_debug import debug_log as dbg

_EVENT_TO_METRIC = {
  'query': 'queries_total',
  'favorite_add': 'favorites_added_total',
  'favorite_remove': 'favorites_removed_total',
  'summary_request': 'summaries_requested_total',
  'summary_success': 'summaries_generated_total',
  'boletim_create': 'boletins_created_total',
  'boletim_run': 'boletins_runs_total'
}

# Flag de ambiente: se definida e falsa, não grava eventos/contadores
def _usage_enabled() -> bool:
    try:
        val = os.getenv('GVG_USAGE_ENABLE', 'true').strip().lower()
        return val in ('1','true','yes','on')
    except Exception:
        return True

def record_usage(user_id: str, event_type: str, ref_type: Optional[str]=None, ref_id: Optional[str]=None, meta: Optional[Dict[str, Any]]=None) -> None:
    if not user_id or not event_type or not _usage_enabled():
        return
    try:
        db_execute(
            "INSERT INTO public.user_usage_events (user_id,event_type,ref_type,ref_id,meta) VALUES (%s,%s,%s,%s,%s::jsonb)",
            (user_id, event_type, ref_type, ref_id, None if meta is None else __import__('json').dumps(meta)),
            ctx="USAGE.record_usage:event"
        )
    except Exception as e:
        try: dbg('USAGE', f"warn insert event {event_type}: {e}")
        except Exception: pass
    metric = _EVENT_TO_METRIC.get(event_type)
    if not metric:
        return
    try:
        db_execute(
            "INSERT INTO public.user_usage_counters (user_id,metric_key,metric_value) VALUES (%s,%s,1) ON CONFLICT (user_id,metric_key) DO UPDATE SET metric_value = public.user_usage_counters.metric_value + 1, updated_at = now()",
            (user_id, metric),
            ctx="USAGE.record_usage:counter"
        )
    except Exception as e:
        try: dbg('USAGE', f"warn upsert counter {metric}: {e}")
        except Exception: pass

def record_usage_bulk(user_id: str, events: List[Tuple[str,str,str,Dict[str,Any]]]) -> None:
    if not _usage_enabled():
        return
    rows_evt=[]; rows_cnt=[]
    import json
    for ev_type, ref_type, ref_id, meta in events:
        rows_evt.append((user_id, ev_type, ref_type, ref_id, json.dumps(meta or {}) ))
        metric=_EVENT_TO_METRIC.get(ev_type)
        if metric:
            rows_cnt.append((user_id, metric))
    if rows_evt:
        try:
            db_execute_many("INSERT INTO public.user_usage_events (user_id,event_type,ref_type,ref_id,meta) VALUES (%s,%s,%s,%s,%s::jsonb)", rows_evt, ctx="USAGE.record_usage_bulk:events")
        except Exception as e:
            try: dbg('USAGE', f"warn bulk events: {e}")
            except Exception: pass
    for (uid, metric) in rows_cnt:
        try:
            db_execute(
                "INSERT INTO public.user_usage_counters (user_id,metric_key,metric_value) VALUES (%s,%s,1) ON CONFLICT (user_id,metric_key) DO UPDATE SET metric_value = public.user_usage_counters.metric_value + 1, updated_at = now()",
                (uid, metric),
                ctx="USAGE.record_usage_bulk:counter"
            )
        except Exception as e:
            try: dbg('USAGE', f"warn bulk counter {metric}: {e}")
            except Exception: pass

__all__ = ['record_usage','record_usage_bulk']
