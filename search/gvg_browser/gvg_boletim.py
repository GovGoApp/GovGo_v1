"""
gvg_boletim.py
Funções de persistência para Boletins de busca agendada.

Tabelas:
- public.user_schedule (antes public.user_boletins): agenda por usuário
    Campos: id, user_id, query_text, schedule_type, schedule_detail (jsonb),
                    channels (jsonb), config_snapshot (jsonb), next_run_at, last_run_at, active, created_at.
- public.user_boletim: resultados por execução de boletim (uma linha por PNCP)
    Campos: id, created_at, boletim_id, user_id, run_token, run_at,
                    numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta,
                    payload, sent, sent_at

Observações:
- next_run_at é deixado como NULL aqui; cálculo ficará em processo externo.
- Soft delete: active=false.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import json

try:
    # Execução como pacote (python -m search.gvg_browser...)
    from .gvg_user import get_current_user
    from .gvg_database import create_connection
    from .gvg_debug import debug_log as dbg
except Exception:  # fallback para execução direta dentro da pasta
    from gvg_user import get_current_user
    from gvg_database import create_connection
    from gvg_debug import debug_log as dbg
from datetime import datetime, timezone


def fetch_user_boletins() -> List[Dict[str, Any]]:
    """Retorna somente boletins ATIVOS do usuário atual, com campos mínimos para UI.

    Campos retornados: id, query_text, schedule_type, schedule_detail, channels.
    (Demais campos poderão ser adicionados futuramente se a interface precisar.)
    """
    user = get_current_user()
    uid = user.get('uid')
    if not uid:
        return []
    conn = None
    cur = None
    items: List[Dict[str, Any]] = []
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute(
                """
                    SELECT id, query_text, schedule_type, schedule_detail, channels
                      FROM public.user_schedule
                     WHERE user_id = %s
                       AND active = true
                  ORDER BY created_at DESC
                """,
                (uid,)
            )
            rows = cur.fetchall() or []
        except Exception as e1:
            # Fallback: tabela legada public.user_boletins
            try:
                dbg('BOLETIM', f"user_schedule indisponível; usando fallback user_boletins ({e1})")
            except Exception:
                pass
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
            rows = cur.fetchall() or []
        for r in rows:
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
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


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
        try:
            cur.execute(
                """
                INSERT INTO public.user_schedule
                    (user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (uid, query_text, schedule_type, json.dumps(schedule_detail), json.dumps(channels), json.dumps(config_snapshot))
            )
            row = cur.fetchone()
        except Exception as e1:
            # Fallback: tabela legada public.user_boletins
            try:
                dbg('BOLETIM', f"INSERT em user_schedule falhou; tentando user_boletins ({e1})")
            except Exception:
                pass
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
        try:
            cur.execute(
                "UPDATE public.user_schedule SET active = false, updated_at = now() WHERE id = %s AND user_id = %s",
                (boletim_id, uid)
            )
            if cur.rowcount == 0:
                # Se nenhuma linha afetada, tentar na tabela legada
                cur.execute(
                    "UPDATE public.user_boletins SET active = false, updated_at = now() WHERE id = %s AND user_id = %s",
                    (boletim_id, uid)
                )
        except Exception as e1:
            # Fallback direto para tabela legada se user_schedule não existir
            try:
                dbg('BOLETIM', f"UPDATE user_schedule falhou; fallback user_boletins ({e1})")
            except Exception:
                pass
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


def list_active_schedules_all(now_dt: datetime) -> List[Dict[str, Any]]:
    """Lista boletins (user_schedule) ativos que 'batem' com o momento now_dt (semana/dia).

    Regras atuais:
    - DIARIO: seg-sex
    - SEMANAL: dia presente em schedule_detail.days
    - MULTIDIARIO: tratado como DIARIO por enquanto
    """
    conn = None; cur = None
    items: List[Dict[str, Any]] = []
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, last_run_at
                  FROM public.user_schedule
                 WHERE active = true
                """
            )
            rows = cur.fetchall() or []
        except Exception as e1:
            # Fallback: tabela legada public.user_boletins
            try:
                dbg('BOLETIM', f"user_schedule indisponível; usando fallback user_boletins ({e1})")
            except Exception:
                pass
            cur.execute(
                """
                SELECT id, user_id, query_text, schedule_type, schedule_detail, channels, config_snapshot, last_run_at
                  FROM public.user_boletins
                 WHERE active = true
                """
            )
            rows = cur.fetchall() or []
        import json as _json
        dow_map = {0:'seg',1:'ter',2:'qua',3:'qui',4:'sex',5:'sab',6:'dom'}
        dow = dow_map[now_dt.weekday()]
        for r in rows:
            (sid, uid, q, stype, sdetail, channels, snapshot, last_run_at) = r
            stype = (stype or '').upper()
            # Determinar dias configurados
            try:
                detail = sdetail if isinstance(sdetail, dict) else _json.loads(sdetail or '{}')
            except Exception:
                detail = {}
            cfg_days = detail.get('days') if isinstance(detail, dict) else None
            due = False
            if stype in ('DIARIO','MULTIDIARIO'):
                # Para DIARIO/MULTIDIARIO: se não houver days, default seg-sex
                days = list(cfg_days) if cfg_days else ['seg','ter','qua','qui','sex']
                due = dow in days
            elif stype == 'SEMANAL':
                # Para SEMANAL: roda somente se days existir e contiver o dia atual
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
                'last_run_at': last_run_at,
            })
        return items
    except Exception as e:
        try:
            dbg('BOLETIM', f"Erro list_active_schedules_all: {e}")
        except Exception:
            pass
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def record_boletim_results(boletim_id: int, user_id: str, run_token: str, run_at: datetime, rows: List[Dict[str, Any]]) -> int:
    """Insere resultados em public.user_boletim.

    rows: cada item deve conter numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload (opc.)
    """
    if not rows:
        return 0
    conn=None; cur=None
    try:
        conn = create_connection()
        if not conn:
            return 0
        cur = conn.cursor()
        sql = (
            "INSERT INTO public.user_boletim (boletim_id, user_id, run_token, run_at, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload)\n"
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        data = []
        import json as _json
        for r in rows:
            data.append((
                boletim_id,
                user_id,
                run_token,
                run_at,
                r.get('numero_controle_pncp'),
                r.get('similarity'),
                r.get('data_publicacao_pncp'),
                r.get('data_encerramento_proposta'),
                _json.dumps(r.get('payload') or {})
            ))
        cur.executemany(sql, data)
        conn.commit()
        return len(rows)
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        try:
            dbg('BOLETIM', f"Erro record_boletim_results: {e}")
        except Exception:
            pass
        return 0
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def fetch_unsent_results_for_boletim(boletim_id: int, baseline_iso: Optional[str]) -> List[Dict[str, Any]]:
    """Retorna resultados não enviados (sent=false) aplicando baseline de publicação quando possível.

    baseline_iso: 'YYYY-MM-DD' (usado para comparar data_publicacao_pncp como TEXT)
    """
    conn=None; cur=None
    out: List[Dict[str, Any]] = []
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        base = [
            "SELECT id, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload, run_at",
            "FROM public.user_boletim",
            "WHERE boletim_id = %s AND sent = false"
        ]
        params: List[Any] = [boletim_id]
        if baseline_iso:
            base.append("AND (data_publicacao_pncp >= %s OR run_at >= to_timestamp(%s,'YYYY-MM-DD'))")
            params.extend([baseline_iso, baseline_iso])
        sql = "\n".join(base)
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall() or []:
            out.append(dict(zip(cols, row)))
        return out
    except Exception as e:
        try:
            dbg('BOLETIM', f"Erro fetch_unsent_results_for_boletim: {e}")
        except Exception:
            pass
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def mark_results_sent(result_ids: List[int], sent_at: Optional[datetime] = None) -> int:
    if not result_ids:
        return 0
    conn = None
    cur = None
    try:
        conn = create_connection()
        if not conn:
            return 0
        cur = conn.cursor()
        sent_at = sent_at or datetime.now(timezone.utc)
        sql = "UPDATE public.user_boletim SET sent = true, sent_at = %s WHERE id = ANY(%s)"
        cur.execute(sql, (sent_at, result_ids))
        conn.commit()
        return cur.rowcount or 0
    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        try:
            dbg('BOLETIM', f"Erro mark_results_sent: {e}")
        except Exception:
            pass
        return 0
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


def touch_last_run(boletim_id: int, dt: datetime) -> bool:
    conn=None; cur=None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        try:
            cur.execute("UPDATE public.user_schedule SET last_run_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id))
            if cur.rowcount == 0:
                cur.execute("UPDATE public.user_boletins SET last_run_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id))
        except Exception as e1:
            try:
                dbg('BOLETIM', f"UPDATE last_run em user_schedule falhou; fallback user_boletins ({e1})")
            except Exception:
                pass
            cur.execute("UPDATE public.user_boletins SET last_run_at = %s, updated_at = now() WHERE id = %s", (dt, boletim_id))
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
    'fetch_user_boletins', 'create_user_boletim', 'deactivate_user_boletim',
    'list_active_schedules_all', 'record_boletim_results', 'fetch_unsent_results_for_boletim', 'mark_results_sent', 'touch_last_run'
]
