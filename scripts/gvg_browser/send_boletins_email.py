"""
Envia boletins por email para usuários, usando o último run de cada boletim
(caso last_run_at > last_sent_at). HTML reaproveita estilos do site (inline).

Uso:
  python -m search.gvg_browser.scripts.send_boletins_email

Requisitos: SMTP_* no .env; DB configurado.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from search.gvg_browser.gvg_boletim import set_last_sent, get_user_email
    from search.gvg_browser.gvg_debug import debug_log as dbg
    from search.gvg_browser.gvg_database import create_connection
    from search.gvg_browser.gvg_email import send_html_email
    from search.gvg_browser.gvg_styles import styles
except Exception:
    # Execução direta
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from gvg_boletim import set_last_sent, get_user_email
    from gvg_debug import debug_log as dbg
    from gvg_database import create_connection
    from gvg_email import send_html_email
    from gvg_styles import styles


def _style_inline(d: Dict[str, Any]) -> str:
    return "; ".join(f"{k}:{v}" for k, v in (d or {}).items())


def _fetch_boletins_to_send() -> List[Dict[str, Any]]:
    """Retorna boletins que têm run novo a enviar: last_run_at > last_sent_at."""
    conn=None; cur=None
    out: List[Dict[str, Any]] = []
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        # user_schedule prioritário; se falhar, tenta user_boletins (sem last_sent_at)
        try:
            cur.execute(
                """
                SELECT id, user_id, query_text, last_run_at, COALESCE(last_sent_at, to_timestamp(0)) AS last_sent_at
                  FROM public.user_schedule
                 WHERE active = true
                   AND last_run_at IS NOT NULL
                   AND (last_sent_at IS NULL OR last_sent_at < last_run_at)
                """
            )
            cols = [d[0] for d in cur.description]
            out = [dict(zip(cols, r)) for r in cur.fetchall() or []]
        except Exception as e1:
            try:
                dbg('BOLETIM', f"_fetch_boletins_to_send fallback sem last_sent_at ({e1})")
            except Exception:
                pass
            cur.execute(
                """
                SELECT id, user_id, query_text, last_run_at
                  FROM public.user_boletins
                 WHERE active = true AND last_run_at IS NOT NULL
                """
            )
            cols = [d[0] for d in cur.description]
            out = [dict(zip(cols, r)) for r in cur.fetchall() or []]
        return out
    except Exception as e:
        try:
            dbg('BOLETIM', f"Erro _fetch_boletins_to_send: {e}")
        except Exception:
            pass
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def _fetch_latest_run_rows(boletim_id: int) -> Tuple[List[Dict[str, Any]], Optional[datetime]]:
    """Retorna as linhas do último run (por maior run_at) e o run_at."""
    conn=None; cur=None
    try:
        conn = create_connection()
        if not conn:
            return [], None
        cur = conn.cursor()
        cur.execute(
            """
            SELECT MAX(run_at) FROM public.user_boletim WHERE boletim_id = %s
            """,
            (boletim_id,)
        )
        row = cur.fetchone()
        last_run = row[0] if row else None
        if not last_run:
            return [], None
        cur.execute(
            """
            SELECT id, payload FROM public.user_boletim
             WHERE boletim_id = %s AND run_at = %s
             ORDER BY similarity DESC NULLS LAST, id ASC
            """,
            (boletim_id, last_run)
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall() or []]
        return rows, last_run
    except Exception as e:
        try:
            dbg('BOLETIM', f"Erro _fetch_latest_run_rows: {e}")
        except Exception:
            pass
        return [], None
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def _render_html_boletim(query_text: str, items: List[Dict[str, Any]]) -> str:
    """Render simples dos cards com estilos inline baseados em styles['result_card']."""
    card_style = _style_inline(styles.get('result_card', {}))
    title_style = _style_inline(styles.get('card_title', {}))
    muted_style = _style_inline(styles.get('muted_text', {}))

    parts = [f"<h2 style='{title_style}'>Boletim: {query_text}</h2>"]
    if not items:
        parts.append(f"<div style='{card_style}'>Sem resultados nesta execução.</div>")
    for i, it in enumerate(items, start=1):
        payload = it.get('payload') or {}
        orgao = payload.get('orgao') or ''
        municipio = payload.get('municipio') or ''
        uf = payload.get('uf') or ''
        objeto = payload.get('objeto') or ''
        data_enc = payload.get('data_encerramento_proposta') or ''
        link = (payload.get('links') or {}).get('origem') or ''
        parts.append(
            f"<div style='{card_style}'>"
            f"<div style='{muted_style}'>{i:02d}</div>"
            f"<div><strong>{objeto}</strong></div>"
            f"<div style='{muted_style}'>{orgao} — {municipio}/{uf}</div>"
            f"<div style='{muted_style}'>Encerramento: {data_enc}</div>"
            f"<div><a href='{link}' target='_blank'>Abrir no sistema de origem</a></div>"
            f"</div>"
        )
    return "\n".join(parts)


def run_once(now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    boletins = _fetch_boletins_to_send()
    dbg('BOLETIM', f"Envio: {len(boletins)} boletim(ns) prontos para enviar")
    for b in boletins:
        sid = b['id']
        uid = b['user_id']
        query = b.get('query_text') or ''
        email = get_user_email(uid)
        if not email:
            dbg('BOLETIM', f"Sem email para user={uid}; pulando boletim id={sid}")
            continue
        rows, last_run = _fetch_latest_run_rows(sid)
        html = _render_html_boletim(query, rows)
        subject = f"Boletim GovGo — {query}"
        ok = send_html_email(email, subject, html)
        if ok:
            set_last_sent(sid, now)
            dbg('BOLETIM', f"Email enviado para {email} (boletim id={sid}, itens={len(rows)})")
        else:
            dbg('BOLETIM', f"Falha ao enviar email para {email} (boletim id={sid})")


if __name__ == '__main__':
    run_once()
