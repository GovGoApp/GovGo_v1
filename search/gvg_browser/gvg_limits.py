"""Regras de limites por plano (Step2 Billing).

Funções principais:
- get_user_plan_limits(user_id)
- count_usage_today(user_id, event_type)
- ensure_capacity(user_id, tipo)

Tipos suportados para ensure_capacity:
- 'consultas'   -> event_type='query'
- 'resumos'     -> event_type='summary_success'
- 'boletim_run' -> event_type='boletim_run'
- 'favoritos'   -> usa COUNT em user_bookmarks active=true

Obs: apenas bloqueio; geração de toasts será implementada depois.
"""
from __future__ import annotations
from typing import Dict, Any
from datetime import date

from gvg_database import db_fetch_all
from gvg_debug import debug_log as dbg

class LimitExceeded(Exception):
    def __init__(self, tipo: str, limit: int):
        super().__init__(f"Limite diário de {tipo.upper()} atingido")
        self.tipo = tipo
        self.limit = limit

PLAN_LIMIT_COLUMNS = {
    'consultas': 'limit_consultas_per_day',
    'resumos': 'limit_resumos_per_day',
    'boletim_run': 'limit_boletim_per_day',
    'favoritos': 'limit_favoritos_capacity',
}

EVENT_TYPE_MAP = {
    'consultas': 'query',
    'resumos': 'summary_success',
    'boletim_run': 'boletim_run',
}

def get_user_plan_limits(user_id: str) -> Dict[str, int]:
    sql = """
    SELECT p.limit_consultas_per_day,
           p.limit_resumos_per_day,
           p.limit_boletim_per_day,
           p.limit_favoritos_capacity
    FROM public.system_plans p
    JOIN public.user_settings us ON us.plan_id = p.id
    WHERE us.user_id = %s
    """
    rows = db_fetch_all(sql, (user_id,), ctx="LIMITS.get_user_plan_limits")
    if not rows:
        # fallback: FREE defaults (hardcode simples, pode sincronizar com tabela futuramente)
        return {
            'limit_consultas_per_day': 30,
            'limit_resumos_per_day': 10,
            'limit_boletim_per_day': 5,
            'limit_favoritos_capacity': 50,
        }
    r = rows[0]
    # Suporta cursor que retorna tuplas ou dicionários
    if isinstance(r, dict):
        c, s, b, f = (
            r.get('limit_consultas_per_day'),
            r.get('limit_resumos_per_day'),
            r.get('limit_boletim_per_day'),
            r.get('limit_favoritos_capacity'),
        )
    else:
        # Ordem dos SELECTs acima
        try:
            c, s, b, f = r[0], r[1], r[2], r[3]
        except Exception:
            c = s = b = f = None
    return {
        'limit_consultas_per_day': int(c) if c is not None else 30,
        'limit_resumos_per_day': int(s) if s is not None else 10,
        'limit_boletim_per_day': int(b) if b is not None else 5,
        'limit_favoritos_capacity': int(f) if f is not None else 50,
    }

def count_usage_today(user_id: str, event_type: str) -> int:
    sql = """
    SELECT COUNT(*) AS c
    FROM public.user_usage_events
    WHERE user_id = %s
      AND event_type = %s
      AND created_at_date = current_date
    """
    rows = db_fetch_all(sql, (user_id, event_type), ctx="LIMITS.count_usage_today")
    if not rows:
        return 0
    r = rows[0]
    try:
        return int(r['c']) if isinstance(r, dict) else int(r[0])
    except Exception:
        return 0

def count_favoritos(user_id: str) -> int:
    sql = """
    SELECT COUNT(*) AS c
    FROM public.user_bookmarks
    WHERE user_id = %s AND active = true
    """
    rows = db_fetch_all(sql, (user_id,), ctx="LIMITS.count_favoritos")
    if not rows:
        return 0
    r = rows[0]
    try:
        return int(r['c']) if isinstance(r, dict) else int(r[0])
    except Exception:
        return 0

def ensure_capacity(user_id: str, tipo: str):
    if tipo not in PLAN_LIMIT_COLUMNS:
        return
    limits = get_user_plan_limits(user_id)
    limit_col = PLAN_LIMIT_COLUMNS[tipo]
    plan_limit = limits.get(limit_col)
    if plan_limit is None or plan_limit < 0:
        return
    if tipo == 'favoritos':
        used = count_favoritos(user_id)
    else:
        event_type = EVENT_TYPE_MAP.get(tipo)
        if not event_type:
            return
        used = count_usage_today(user_id, event_type)
    if used >= plan_limit:
        dbg('LIMIT', f"Excedido tipo={tipo} used={used} limit={plan_limit}")
        raise LimitExceeded(tipo, plan_limit)
    dbg('LIMIT', f"OK tipo={tipo} used={used} limit={plan_limit}")
    return

__all__ = [
    'LimitExceeded', 'ensure_capacity', 'get_user_plan_limits', 'count_usage_today', 'get_usage_status'
]

def get_usage_status(user_id: str) -> Dict[str, Any]:
    """Retorna dict com usados, limites e percentuais para UI.

    Estrutura:
    {
      'consultas': {'used': X, 'limit': Y, 'pct': P},
      'resumos': {...},
      'boletim_run': {...},
      'favoritos': {...}
    }
    """
    limits = get_user_plan_limits(user_id)
    out: Dict[str, Any] = {}
    # Consultas / Resumos / Boletim via eventos
    for tipo, ev in EVENT_TYPE_MAP.items():
        used = count_usage_today(user_id, ev)
        limit_val = limits.get(PLAN_LIMIT_COLUMNS[tipo])
        pct = (used / limit_val * 100.0) if limit_val else 0.0
        out[tipo] = {'used': used, 'limit': limit_val, 'pct': round(pct, 1)}
    # Favoritos
    fav_used = count_favoritos(user_id)
    fav_limit = limits.get('limit_favoritos_capacity')
    fav_pct = (fav_used / fav_limit * 100.0) if fav_limit else 0.0
    out['favoritos'] = {'used': fav_used, 'limit': fav_limit, 'pct': round(fav_pct, 1)}
    return out
