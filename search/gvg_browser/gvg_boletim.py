"""
gvg_boletim.py
Funções de persistência para Boletins de busca agendada.

Observações:
- Uso de wrappers centralizados (gvg_database) com métricas [DB].
- Mantidos fallbacks para schemas antigos (user_boletins) e ausência de colunas (filters).
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timezone
import time

try:
    from search.gvg_browser.gvg_user import get_current_user  # type: ignore
    from search.gvg_browser.gvg_database import (
        db_fetch_all, db_fetch_one, db_execute, db_execute_many
    )  # type: ignore
    from search.gvg_browser.gvg_debug import debug_log as dbg  # type: ignore
except Exception:
    try:
        from .gvg_user import get_current_user  # type: ignore
        from .gvg_database import db_fetch_all, db_fetch_one, db_execute, db_execute_many  # type: ignore
        from .gvg_debug import debug_log as dbg  # type: ignore
    except Exception:
        from gvg_user import get_current_user  # type: ignore
        from gvg_database import db_fetch_all, db_fetch_one, db_execute, db_execute_many  # type: ignore
        from gvg_debug import debug_log as dbg  # type: ignore


# Cache leve em memória para listas de boletins por usuário
_BOLETIM_CACHE: Dict[str, Dict[str, Any]] = {}
_TTL_BOLETIM_SECONDS = 300  # 5 minutos

def _cache_get(key: str):
    ent = _BOLETIM_CACHE.get(key)
    if not ent:
        return None
    if ent.get('expires', 0) > time.time():
        return ent.get('value')
    _BOLETIM_CACHE.pop(key, None)
    return None

def _cache_set(key: str, value: Any, ttl: int = _TTL_BOLETIM_SECONDS):
    _BOLETIM_CACHE[key] = {'value': value, 'expires': time.time() + ttl}

def _cache_invalidate_prefix(prefix: str):
    for k in list(_BOLETIM_CACHE.keys()):
        if str(k).startswith(prefix):
            _BOLETIM_CACHE.pop(k, None)

def fetch_user_boletins() -> List[Dict[str, Any]]:
    """Retorna boletins ATIVOS do usuário atual com campos para UI (inclui filters quando existir)."""
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return []
    # Cache por usuário
    ck = f"BOLETIM.fetch_user_boletins:{uid}"
    cached = _cache_get(ck)
    if cached is not None:
        return list(cached)
    items: List[Dict[str, Any]] = []
    # 1) user_schedule com filters
    rows = db_fetch_all(
        (
            """
            SELECT id, query_text, schedule_type, schedule_detail, channels,
                   config_snapshot, created_at, last_run_at, filters
              FROM public.user_schedule
             WHERE user_id = %s AND active = true
          ORDER BY created_at DESC
            """
        ),
        (uid,),
        ctx="BOLETIM.fetch_user_boletins:with_filters",
    )
    has_filters = True
    # 2) Se vazio, tentar user_schedule sem filters
    if not rows:
        rows = db_fetch_all(
            (
                """
                SELECT id, query_text, schedule_type, schedule_detail, channels,
                       config_snapshot, created_at, last_run_at
                  FROM public.user_schedule
                 WHERE user_id = %s AND active = true
              ORDER BY created_at DESC
                """
            ),
            (uid,),
            ctx="BOLETIM.fetch_user_boletins:without_filters",
        )
        has_filters = False
    # 3) Se ainda vazio, fallback para tabela legada user_boletins
    if not rows:
        legacy = db_fetch_all(
            (
                """
                SELECT id, query_text, schedule_type, schedule_detail, channels, created_at
                  FROM public.user_boletins
                 WHERE user_id = %s AND active = true
              ORDER BY created_at DESC
                """
            ),
            (uid,),
            ctx="BOLETIM.fetch_user_boletins:legacy",
        )
        for r in (legacy or []):
            items.append({
                'id': r[0],
                'query_text': r[1],
                'schedule_type': r[2],
                'schedule_detail': r[3] or {},
                'channels': r[4] or [],
                'created_at': r[5] if len(r) > 5 else None,
            })
    _cache_set(ck, items)
    return list(items)
    # Mapear linhas de user_schedule
    for r in rows:
        # rows é tuplas (as_dict=False)
        item = {
            'id': r[0],
            'query_text': r[1],
            'schedule_type': r[2],
            'schedule_detail': r[3] or {},
            'channels': r[4] or [],
            'config_snapshot': r[5] or {},
            'created_at': r[6],
            'last_run_at': r[7] if len(r) > 7 else None,
        }
        if has_filters and len(r) > 8:
            item['filters'] = r[8]
        items.append(item)
    _cache_set(ck, items)
    return list(items)


def create_user_boletim(
    query_text: str,
    schedule_type: str,
    schedule_detail: Dict[str, Any],
    channels: List[str],
    config_snapshot: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    if not query_text or not schedule_type:
        return None
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return None
    # Tenta inserir em user_schedule (com filters)
    row = db_fetch_one(
        (
            """
            INSERT INTO public.user_schedule
                (user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, filters)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
            RETURNING id
            """
        ),
        (uid, query_text, schedule_type, json.dumps(schedule_detail), json.dumps(channels), json.dumps(config_snapshot), json.dumps(filters or {})),
        ctx="BOLETIM.create_user_boletim:insert_with_filters",
    )
    if row and (isinstance(row, (list, tuple)) and row[0] is not None):
        # Invalida cache do usuário
        _cache_invalidate_prefix(f"BOLETIM.fetch_user_boletins:{uid}")
        return int(row[0])
    # Sem filters
    row2 = db_fetch_one(
        (
            """
            INSERT INTO public.user_schedule
                (user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            RETURNING id
            """
        ),
        (uid, query_text, schedule_type, json.dumps(schedule_detail), json.dumps(channels), json.dumps(config_snapshot)),
        ctx="BOLETIM.create_user_boletim:insert_without_filters",
    )
    if row2 and (isinstance(row2, (list, tuple)) and row2[0] is not None):
        _cache_invalidate_prefix(f"BOLETIM.fetch_user_boletins:{uid}")
        return int(row2[0])
    # Fallback para tabela legada
    row3 = db_fetch_one(
        (
            """
            INSERT INTO public.user_boletins
                (user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            RETURNING id
            """
        ),
        (uid, query_text, schedule_type, json.dumps(schedule_detail), json.dumps(channels), json.dumps(config_snapshot)),
        ctx="BOLETIM.create_user_boletim:legacy_insert",
    )
    pid = int(row3[0]) if row3 and isinstance(row3, (list, tuple)) and row3[0] is not None else None
    if pid:
        _cache_invalidate_prefix(f"BOLETIM.fetch_user_boletins:{uid}")
    return pid


def deactivate_user_boletim(boletim_id: int) -> bool:
    if not boletim_id:
        return False
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return False
    # Tenta em user_schedule
    aff = db_execute(
        "UPDATE public.user_schedule SET active = false, updated_at = now() WHERE id = %s AND user_id = %s",
        (boletim_id, uid),
        ctx="BOLETIM.deactivate_user_boletim:user_schedule",
    )
    if aff and aff > 0:
        _cache_invalidate_prefix(f"BOLETIM.fetch_user_boletins:{uid}")
        return True
    # Fallback para tabela legada
    aff2 = db_execute(
        "UPDATE public.user_boletins SET active = false, updated_at = now() WHERE id = %s AND user_id = %s",
        (boletim_id, uid),
        ctx="BOLETIM.deactivate_user_boletim:legacy",
    )
    ok = bool(aff2 and aff2 > 0)
    if ok:
        _cache_invalidate_prefix(f"BOLETIM.fetch_user_boletins:{uid}")
    return ok


def list_active_schedules_all(now_dt: datetime) -> List[Dict[str, Any]]:
    """Lista boletins (user_schedule) ativos elegíveis para execução em now_dt (semana/dia)."""
    items: List[Dict[str, Any]] = []
    # user_schedule com/sem filters
    rows = db_fetch_all(
        (
            """
            SELECT id, user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, filters, last_run_at
              FROM public.user_schedule
             WHERE active = true
            """
        ),
        ctx="BOLETIM.list_active_schedules_all:with_filters",
    )
    have_filters = True
    if not rows:
        rows = db_fetch_all(
            (
                """
                SELECT id, user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, last_run_at
                  FROM public.user_schedule
                 WHERE active = true
                """
            ),
            ctx="BOLETIM.list_active_schedules_all:without_filters",
        )
        have_filters = False
    # Fallback user_boletins
    if not rows:
        rows = db_fetch_all(
            (
                """
                SELECT id, user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, last_run_at
                  FROM public.user_boletins
                 WHERE active = true
                """
            ),
            ctx="BOLETIM.list_active_schedules_all:legacy",
        )
        have_filters = False
    import json as _json
    dow_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
    dow = dow_map[now_dt.weekday()]
    for r in (rows or []):
        if have_filters:
            (sid, uid, q, stype, sdetail, channels, snapshot, filters, last_run_at) = r
        else:
            (sid, uid, q, stype, sdetail, channels, snapshot, last_run_at) = r
            filters = None
        stype = (stype or '').upper()
        try:
            detail = sdetail if isinstance(sdetail, dict) else _json.loads(sdetail or '{}')
        except Exception:
            detail = {}
        try:
            if filters and isinstance(filters, str):
                filters = _json.loads(filters)
        except Exception:
            filters = filters if isinstance(filters, dict) else {}
        cfg_days = detail.get('days') if isinstance(detail, dict) else None
        due = False
        if stype in ('DIARIO', 'MULTIDIARIO'):
            days = list(cfg_days) if cfg_days else ['seg', 'ter', 'qua', 'qui', 'sex']
            due = dow in days
        elif stype == 'SEMANAL':
            days = list(cfg_days) if cfg_days else []
            due = (dow in days)
        if not due:
            continue
        items.append({
            'id': sid,
            'user_id': uid,
            'query_text': q,
            'schedule_type': stype,
            'schedule_detail': sdetail or {},
            'channels': channels or [],
            'config_snapshot': snapshot or {},
            'filters': filters or {},
            'last_run_at': last_run_at,
        })
    return items


def record_boletim_results(boletim_id: int, user_id: str, run_token: str, run_at: datetime, rows: List[Dict[str, Any]]) -> int:
    """Insere resultados em public.user_boletim via executemany; retorna total inserido."""
    if not rows:
        return 0
    import json as _json
    sql = (
        "INSERT INTO public.user_boletim (boletim_id, user_id, run_token, run_at, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload)\n"
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    data = [
        (
            boletim_id,
            user_id,
            run_token,
            run_at,
            r.get('numero_controle_pncp'),
            r.get('similarity'),
            r.get('data_publicacao_pncp'),
            r.get('data_encerramento_proposta'),
            _json.dumps(r.get('payload') or {}),
        )
        for r in rows
    ]
    aff = db_execute_many(sql, data, ctx="BOLETIM.record_boletim_results")
    return int(aff or 0)


def fetch_unsent_results_for_boletim(boletim_id: int, baseline_iso: Optional[str]) -> List[Dict[str, Any]]:
    """Retorna resultados não enviados (sent=false) aplicando baseline de publicação quando possível."""
    base = [
        "SELECT id, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload, run_at",
        "FROM public.user_boletim",
        "WHERE boletim_id = %s AND sent = false",
    ]
    params: List[Any] = [boletim_id]
    if baseline_iso:
        base.append("AND (data_publicacao_pncp >= %s OR run_at >= to_timestamp(%s,'YYYY-MM-DD'))")
        params.extend([baseline_iso, baseline_iso])
    sql = "\n".join(base)
    rows = db_fetch_all(sql, tuple(params), as_dict=True, ctx="BOLETIM.fetch_unsent_results_for_boletim") or []
    return rows


def mark_results_sent(result_ids: List[int], sent_at: Optional[datetime] = None) -> int:
    if not result_ids:
        return 0
    sent_at = sent_at or datetime.now(timezone.utc)
    sql = "UPDATE public.user_boletim SET sent = true, sent_at = %s WHERE id = ANY(%s)"
    aff = db_execute(sql, (sent_at, result_ids), ctx="BOLETIM.mark_results_sent")
    return int(aff or 0)


def touch_last_run(boletim_id: int, dt: datetime) -> bool:
    # Atualiza em user_schedule; se não afetar, tenta tabela legada
    aff = db_execute("UPDATE public.user_schedule SET last_run_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id), ctx="BOLETIM.touch_last_run:user_schedule")
    if aff and aff > 0:
        return True
    aff2 = db_execute("UPDATE public.user_boletins SET last_run_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id), ctx="BOLETIM.touch_last_run:legacy")
    return bool(aff2 and aff2 > 0)


__all__ = [
    'fetch_user_boletins', 'create_user_boletim', 'deactivate_user_boletim',
    'list_active_schedules_all', 'record_boletim_results', 'fetch_unsent_results_for_boletim', 'mark_results_sent', 'touch_last_run'
]

# --- Helpers adicionais para envio ---

def get_user_email(user_id: str) -> Optional[str]:
    row = db_fetch_one("SELECT email FROM auth.users WHERE id = %s", (user_id,), ctx="BOLETIM.get_user_email")
    if isinstance(row, (list, tuple)):
        return row[0] if row else None
    if isinstance(row, dict):
        return row.get('email')  # type: ignore
    return None


def set_last_sent(boletim_id: int, dt: datetime) -> bool:
    # Coluna pode não existir: se falhar, apenas loga e retorna True (não crítico)
    try:
        db_execute("UPDATE public.user_schedule SET last_sent_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id), ctx="BOLETIM.set_last_sent")
        return True
    except Exception as e:  # db_execute já trata, mas mantemos defensive
        try:
            dbg('BOLETIM', f"WARN set_last_sent: {e}")
        except Exception:
            pass
        return True

