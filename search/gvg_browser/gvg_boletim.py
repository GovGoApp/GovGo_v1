"""
gvg_boletim.py
Funções de persistência para Boletins de busca agendada.

Tabela alvo: public.user_boletins (ver DDL fornecida anteriormente).
Campos principais utilizados aqui: id, user_id, query_text, schedule_type, schedule_detail (jsonb),
channels (jsonb), config_snapshot (jsonb), next_run_at, last_run_at, active, created_at.

Observações:
- next_run_at é deixado como NULL aqui; cálculo ficará em processo externo.
- Soft delete: active=false.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import json

from gvg_user import get_current_user
from gvg_database import create_connection


def fetch_user_boletins() -> List[Dict[str, Any]]:
    """Retorna somente boletins ATIVOS do usuário atual, com campos mínimos para UI.

    Campos retornados: id, query_text, schedule_type, schedule_detail, channels.
    (Demais campos poderão ser adicionados futuramente se a interface precisar.)
    """
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return []
    conn = None; cur = None
    items: List[Dict[str, Any]] = []
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute(
            """
                SELECT id, query_text, schedule_type, schedule_detail, channels
                  FROM public.user_boletins
                 WHERE user_id = %s
                   AND active = true
              ORDER BY created_at DESC
            """,
            (uid,)
        )
        for r in cur.fetchall() or []:
            items.append({
                'id': r[0],
                'query_text': r[1],
                'schedule_type': r[2],
                'schedule_detail': r[3] or {},
                'channels': r[4] or [],
            })
        return items
    except Exception:
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def create_user_boletim(
    query_text: str,
    schedule_type: str,
    schedule_detail: Dict[str, Any],
    channels: List[str],
    config_snapshot: Dict[str, Any],
) -> Optional[int]:
    if not query_text or not schedule_type:
        return None
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return None
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.user_boletins
                (user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            RETURNING id
            """,
            (uid, query_text, schedule_type, json.dumps(schedule_detail), json.dumps(channels), json.dumps(config_snapshot))
        )
        row = cur.fetchone()
        conn.commit()
        return int(row[0]) if row and row[0] is not None else None
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return None
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def deactivate_user_boletim(boletim_id: int) -> bool:
    if not boletim_id:
        return False
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return False
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute(
            "UPDATE public.user_boletins SET active = false, updated_at = now() WHERE id = %s AND user_id = %s",
            (boletim_id, uid)
        )
        conn.commit()
        return True
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


__all__ = [
    'fetch_user_boletins', 'create_user_boletim', 'deactivate_user_boletim'
]
