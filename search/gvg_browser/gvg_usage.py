"""User usage tracking utilities.

Extensão: agregador de métricas por evento (tokens, DB, arquivos, tempo total).
Uso típico:

    from gvg_usage import usage_event_start, usage_event_finish
    usage_event_start(user_id, 'query', ref_type='query', ref_id='123')
    ... chamadas IA/DB ...
    usage_event_finish()

As funções instrumentadas (gvg_ai_utils / gvg_database / fetch_documentos) somam métricas automaticamente
quando um evento está ativo.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import threading, time, json
import os
from gvg_database import db_execute, db_execute_many
from gvg_debug import debug_log as dbg

# Métrica agora usa o próprio nome do event_type (dicionário antigo removido)

# =============================
# Aggregator (thread-local)
# =============================

class UsageAggregator:
    __slots__ = (
        'user_id','event_type','ref_type','ref_id','start_ts',
        'tokens_in','tokens_out','tokens_total',
        'db_rows_read','db_rows_written','file_bytes_in','file_bytes_out'
    )
    def __init__(self, user_id: str, event_type: str, ref_type: Optional[str], ref_id: Optional[str]):
        self.user_id = user_id
        self.event_type = event_type
        self.ref_type = ref_type
        self.ref_id = ref_id
        self.start_ts = time.perf_counter()
        self.tokens_in = 0
        self.tokens_out = 0
        self.tokens_total = 0
        self.db_rows_read = 0
        self.db_rows_written = 0
        self.file_bytes_in = 0
        self.file_bytes_out = 0
    # ---- adders ----
    def add_tokens(self, tin: Optional[int], tout: Optional[int], ttotal: Optional[int] = None):
        prev_in = self.tokens_in
        prev_out = self.tokens_out
        prev_total = self.tokens_total
        if tin: self.tokens_in += int(tin)
        if tout: self.tokens_out += int(tout)
        if ttotal is not None:
            self.tokens_total += int(ttotal)
        else:
            est = 0
            if tin: est += int(tin)
            if tout: est += int(tout)
            self.tokens_total += est
        dbg('EVENT', f"tokens add tin={tin or 0} tout={tout or 0} total_delta={self.tokens_total - prev_total} agg_in={self.tokens_in} agg_out={self.tokens_out} agg_total={self.tokens_total} event={self.event_type}")

    def add_db_read(self, n: int):
        prev = self.db_rows_read
        if n: self.db_rows_read += int(n)
        dbg('EVENT', f"db_read add={n} agg_read={self.db_rows_read} delta={self.db_rows_read - prev} event={self.event_type}")

    def add_db_written(self, n: int):
        prev = self.db_rows_written
        if n: self.db_rows_written += int(n)
        dbg('EVENT', f"db_write add={n} agg_written={self.db_rows_written} delta={self.db_rows_written - prev} event={self.event_type}")
    def add_file_in(self, b: int):
        try:
            if b: self.file_bytes_in += int(b)
        except Exception: pass
    def add_file_out(self, b: int):
        try:
            if b: self.file_bytes_out += int(b)
        except Exception: pass
    # ---- finalize ----
    def as_meta(self) -> Dict[str, Any]:
        elapsed_ms = int((time.perf_counter() - self.start_ts) * 1000)
        mb_in = round(self.file_bytes_in / (1024*1024), 3) if self.file_bytes_in else 0
        mb_out = round(self.file_bytes_out / (1024*1024), 3) if self.file_bytes_out else 0
        meta = {
            'tokens_in': self.tokens_in,
            'tokens_out': self.tokens_out,
            'tokens_total': self.tokens_total,
            'db_rows_read': self.db_rows_read,
            'db_rows_written': self.db_rows_written,
            'file_mb_in': mb_in,
            'file_mb_out': mb_out,
            'elapsed_ms': elapsed_ms,
        }
        # Remove zeros para compactar
        return {k:v for k,v in meta.items() if v}

_TL = threading.local()

def _get_current_aggregator() -> Optional[UsageAggregator]:  # usado por outros módulos
    return getattr(_TL, 'usage_aggr', None)

def usage_event_start(user_id: str, event_type: str, ref_type: Optional[str] = None, ref_id: Optional[str] = None):
    if not user_id or not event_type or not _usage_enabled():
        return
    # Se já existe, fecha antes sem gravar (prevenção de vazamento)
    if getattr(_TL, 'usage_aggr', None) is not None:
        try:
            dbg('USAGE', 'warn previous aggregator not finished; discarding')
        except Exception: pass
        setattr(_TL, 'usage_aggr', None)
    aggr = UsageAggregator(user_id, event_type, ref_type, ref_id)
    setattr(_TL, 'usage_aggr', aggr)
    try:
        dbg('USAGE', f"start event='{event_type}' user={user_id} ref={ref_type}:{ref_id}")
    except Exception: pass

def usage_event_finish(extra_meta: Optional[Dict[str, Any]] = None):
    aggr = getattr(_TL, 'usage_aggr', None)
    if aggr is None:
        return
    setattr(_TL, 'usage_aggr', None)  # limpar antes de gravar
    meta = aggr.as_meta()
    if extra_meta:
        try: meta.update({k:v for k,v in (extra_meta or {}).items() if v is not None})
        except Exception: pass
    # Chamamos record_usage direto (evita loops)
    try:
        dbg('USAGE', f"finish event='{aggr.event_type}' tokens_total={meta.get('tokens_total')} db_r={meta.get('db_rows_read')} db_w={meta.get('db_rows_written')} elapsed_ms={meta.get('elapsed_ms')}")
    except Exception: pass
    # Log EVENT para tempo total
    dbg('EVENT', f"finish elapsed_ms={meta.get('elapsed_ms')} tokens_total={meta.get('tokens_total')} db_read={meta.get('db_rows_read')} db_written={meta.get('db_rows_written')} event={aggr.event_type}")
    try:
        record_usage(aggr.user_id, aggr.event_type, aggr.ref_type, aggr.ref_id, meta)
    except Exception:
        pass

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
    dbg('USAGE', f"→ event '{event_type}' user={user_id} ref={ref_type}:{ref_id} meta_keys={list((meta or {}).keys())}")
    try:
        db_execute(
            "INSERT INTO public.user_usage_events (user_id,event_type,ref_type,ref_id,meta) VALUES (%s,%s,%s,%s,%s::jsonb)",
            (user_id, event_type, ref_type, ref_id, None if meta is None else json.dumps(meta)),
            ctx="USAGE.record_usage:event"
        )
    except Exception as e:
        try: dbg('USAGE', f"warn insert event {event_type}: {e}")
        except Exception: pass
    metric = event_type  # usar o próprio nome
    try:
        db_execute(
            "INSERT INTO public.user_usage_counters (user_id,metric_key,metric_value) VALUES (%s,%s,1) ON CONFLICT (user_id,metric_key) DO UPDATE SET metric_value = public.user_usage_counters.metric_value + 1, updated_at = now()",
            (user_id, metric),
            ctx="USAGE.record_usage:counter"
        )
        dbg('USAGE', f"✓ counter '{metric}' incremented for user={user_id}")
    except Exception as e:
        dbg('USAGE', f"warn upsert counter {metric}: {e}")
        

def record_usage_bulk(user_id: str, events: List[Tuple[str,str,str,Dict[str,Any]]]) -> None:
    if not _usage_enabled():
        return
    rows_evt=[]; rows_cnt=[]
    import json
    dbg('USAGE', f"→ bulk events count={len(events)} user={user_id}")
    for ev_type, ref_type, ref_id, meta in events:
        rows_evt.append((user_id, ev_type, ref_type, ref_id, json.dumps(meta or {}) ))
        rows_cnt.append((user_id, ev_type))
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
            dbg('USAGE', f"✓ bulk counter '{metric}' incremented user={uid}")
        except Exception as e:
            dbg('USAGE', f"warn bulk counter {metric}: {e}")

def usage_event_set_ref(ref_type: Optional[str], ref_id: Optional[str]):
    """Atualiza ref_type/ref_id do evento ativo (usar após obter ID persistido)."""
    aggr = getattr(_TL, 'usage_aggr', None)
    if not aggr:
        return
    try:
        if ref_type:
            aggr.ref_type = ref_type
        if ref_id:
            aggr.ref_id = ref_id
    except Exception:
        pass

def record_success_event(user_id: str, base_meta: Optional[Dict[str, Any]], success_type: str, ref_type: Optional[str]=None, ref_id: Optional[str]=None):
    """Registra um evento de sucesso (ex: query_success) reutilizando parte da meta original.
    success_type deve estar permitido no CHECK da tabela.
    """
    try:
        meta = dict(base_meta or {})
    except Exception:
        meta = {}
    record_usage(user_id, success_type, ref_type, ref_id, meta)

__all__ = ['record_usage','record_usage_bulk','usage_event_start','usage_event_finish','usage_event_set_ref','_get_current_aggregator','record_success_event']
