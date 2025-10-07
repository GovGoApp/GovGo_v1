"""Regras de limites por plano (Step2 Billing).

Funções principais:
- get_user_plan_limits(user_id)
- count_usage_today(user_id, event_type)
- ensure_capacity(user_id, tipo)

Tipos suportados para ensure_capacity:
- 'consultas'   -> event_type='query_success'
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
    rows = db_fetch_all(sql, (user_id,))
    if not rows:
        # fallback: FREE defaults (hardcode simples, pode sincronizar com tabela futuramente)
        return {
            'limit_consultas_per_day': 30,
            'limit_resumos_per_day': 10,
            'limit_boletim_per_day': 5,
            'limit_favoritos_capacity': 50,
        }
    r = rows[0]
    return {
        'limit_consultas_per_day': r['limit_consultas_per_day'],
        'limit_resumos_per_day': r['limit_resumos_per_day'],
        'limit_boletim_per_day': r['limit_boletim_per_day'],
        'limit_favoritos_capacity': r['limit_favoritos_capacity'],
    }

def count_usage_today(user_id: str, event_type: str) -> int:
    sql = """
    SELECT COUNT(*) AS c
    FROM public.user_usage_events
    WHERE user_id = %s
      AND event_type = %s
      AND created_at_date = current_date
    """
    rows = db_fetch_all(sql, (user_id, event_type))
    return int(rows[0]['c']) if rows else 0

def count_favoritos(user_id: str) -> int:
    sql = """
    SELECT COUNT(*) AS c
    FROM public.user_bookmarks
    WHERE user_id = %s AND active = true
    """
    rows = db_fetch_all(sql, (user_id,))
    return int(rows[0]['c']) if rows else 0

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
    'LimitExceeded', 'ensure_capacity', 'get_user_plan_limits', 'count_usage_today'
]
