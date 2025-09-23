"""
Envia boletins por email para usuários, usando o último run de cada boletim
(caso last_run_at > last_sent_at). HTML reaproveita estilos do site (inline).

Uso:
  python -m search.gvg_browser.scripts.send_boletins_email

Requisitos: SMTP_* no .env; DB configurado.
"""
from __future__ import annotations

import os
import json
import sys
from pathlib import Path

# Garante que o pacote 'search' (raiz do repo) esteja no sys.path quando rodado via cron
try:
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
except Exception:
    pass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from search.gvg_browser.gvg_boletim import set_last_sent, get_user_email
    from search.gvg_browser.gvg_database import create_connection
    from search.gvg_browser.gvg_email import send_html_email
    from search.gvg_browser.gvg_styles import styles
except Exception:
    # Execução direta
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from gvg_boletim import set_last_sent, get_user_email
    from gvg_database import create_connection
    from gvg_email import send_html_email
    from gvg_styles import styles
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

PIPELINE_TIMESTAMP = os.getenv("PIPELINE_TIMESTAMP") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"log_{PIPELINE_TIMESTAMP}.log")

def log_line(msg: str) -> None:
    try:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _style_inline(d: Dict[str, Any]) -> str:
    return "; ".join(f"{k}:{v}" for k, v in (d or {}).items())


def _fetch_boletins_to_send() -> List[Dict[str, Any]]:
    """Retorna boletins candidatos (last_run_at > last_sent_at) com metadados."""
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
                SELECT id, user_id, query_text, schedule_type, schedule_detail,
                       last_run_at, last_sent_at
                  FROM public.user_schedule
                 WHERE active = true
                   AND last_run_at IS NOT NULL
                   AND (last_sent_at IS NULL OR last_sent_at < last_run_at)
                """
            )
            cols = [d[0] for d in cur.description]
            out = [dict(zip(cols, r)) for r in cur.fetchall() or []]
        except Exception as e1:
        # fallback silencioso: sem logs verbosos
            cur.execute(
                """
                SELECT id, user_id, query_text, schedule_type, schedule_detail, last_run_at
                  FROM public.user_boletins
                 WHERE active = true AND last_run_at IS NOT NULL
                """
            )
            cols = [d[0] for d in cur.description]
            out = [dict(zip(cols, r)) for r in cur.fetchall() or []]
        return out
    except Exception as e:
        # erro silencioso: retorna lista vazia
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
        # erro silencioso: retorna vazio
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
    # Cabeçalho
    log_line("================================================================================")
    log_line(f"[2/2] ENVIO DE BOLETINS — Sessão: {PIPELINE_TIMESTAMP}")
    log_line(f"Data: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log_line("================================================================================")

    boletins = _fetch_boletins_to_send()
    log_line(f"Boletins candidatos a envio: {len(boletins)}")
    total = len(boletins)
    done = 0
    last_pct = -1

    sent = 0
    skipped = 0

    for b in boletins:
        sid = b['id']
        uid = b['user_id']
        query = b.get('query_text') or ''
        stype = (b.get('schedule_type') or '').upper()
        sdetail = b.get('schedule_detail') or {}
        if isinstance(sdetail, str):
            try:
                sdetail = json.loads(sdetail)
            except Exception:
                sdetail = {}
        last_sent = b.get('last_sent_at')

        def _to_dt(x: Any) -> Optional[datetime]:
            if not x:
                return None
            if isinstance(x, datetime):
                return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
            if isinstance(x, str):
                try:
                    return datetime.fromisoformat(x.replace('Z', '+00:00'))
                except Exception:
                    try:
                        return datetime.strptime(x[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    except Exception:
                        return None
            return None

        ls_dt = _to_dt(last_sent)
        now_date = now.astimezone(timezone.utc).date()
        sent_today = (ls_dt.astimezone(timezone.utc).date() == now_date) if ls_dt else False

        # Dias configurados
        dow_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
        cur_dow = dow_map.get(now.weekday())
        cfg_days = (sdetail or {}).get('days') if isinstance(sdetail, dict) else None
        days = []
        if stype in ('DIARIO', 'MULTIDIARIO'):
            days = list(cfg_days) if cfg_days else ['seg', 'ter', 'qua', 'qui', 'sex']
        elif stype == 'SEMANAL':
            days = list(cfg_days) if cfg_days else []
        if cur_dow not in days:
            done += 1
            skipped += 1
            # progresso ao pular
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Envio: {pct}% [{bar}] ({done}/{total})")
                last_pct = pct
            continue

        # Frequência
        if stype in ('DIARIO', 'SEMANAL'):
            if sent_today:
                done += 1
                skipped += 1
                # progresso ao pular
                pct = int((done * 100) / max(1, total))
                if pct == 100 or pct - last_pct >= 5:
                    fill = int(round(pct * 20 / 100))
                    bar = "█" * fill + "░" * (20 - fill)
                    log_line(f"Envio: {pct}% [{bar}] ({done}/{total})")
                    last_pct = pct
                continue
        elif stype == 'MULTIDIARIO':
            min_int = None
            try:
                v = (sdetail or {}).get('min_interval_minutes')
                if isinstance(v, (int, float)):
                    min_int = int(v)
            except Exception:
                min_int = None
            if min_int and ls_dt and (now - ls_dt).total_seconds() < min_int * 60:
                done += 1
                skipped += 1
                # progresso ao pular
                pct = int((done * 100) / max(1, total))
                if pct == 100 or pct - last_pct >= 5:
                    fill = int(round(pct * 20 / 100))
                    bar = "█" * fill + "░" * (20 - fill)
                    log_line(f"Envio: {pct}% [{bar}] ({done}/{total})")
                    last_pct = pct
                continue

        email = get_user_email(uid)
        if not email:
            skipped += 1
            done += 1
            # atualiza progresso mesmo ao pular
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Envio: {pct}% [{bar}] ({done}/{total})")
                last_pct = pct
            continue
        rows, last_run = _fetch_latest_run_rows(sid)
        html = _render_html_boletim(query, rows)
        subject = f"Boletim GovGo — {query}"
        ok = send_html_email(email, subject, html)
        if ok:
            set_last_sent(sid, now)
            log_line(f"Enviado: boletim id={sid} para {email} (itens={len(rows)})")
            sent += 1
        else:
            log_line(f"Falha envio: boletim id={sid} para {email}")

        # Progresso
        done += 1
        pct = int((done * 100) / max(1, total))
        if pct == 100 or pct - last_pct >= 5:
            fill = int(round(pct * 20 / 100))
            bar = "█" * fill + "░" * (20 - fill)
            log_line(f"Envio: {pct}% [{bar}] ({done}/{total})")
            last_pct = pct

    log_line(f"Resumo envio: enviados={sent}, pulados={skipped}, candidatos={total}")


if __name__ == '__main__':
    run_once()
