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
    from search.gvg_browser.gvg_database import create_connection, fetch_documentos
    from search.gvg_browser.gvg_email import send_html_email
    from search.gvg_browser.gvg_styles import styles
except Exception:
    # Execução direta
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from gvg_boletim import set_last_sent, get_user_email
    from gvg_database import create_connection, fetch_documentos
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
                       channels, config_snapshot, last_run_at, last_sent_at
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
        # Buscar linhas do último run
        cur.execute(
            """
            SELECT id, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload
              FROM public.user_boletim
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


def _render_html_boletim(query_text: str, items: List[Dict[str, Any]],
                         cfg_snapshot: Optional[Dict[str, Any]] = None,
                         schedule_type: Optional[str] = None,
                         schedule_detail: Optional[Dict[str, Any]] = None) -> str:
    """Render de e-mail com cabeçalho (logo + título), cabeçalho de busca e cards no estilo do GSB."""
    # --- Styles inline a partir de gvg_styles ---
    card_style = _style_inline(styles.get('result_card', {}))
    title_style = _style_inline(styles.get('card_title', {}))
    muted_style = _style_inline(styles.get('muted_text', {}))
    header_logo_style = _style_inline(styles.get('header_logo', {}))
    header_title_style = _style_inline(styles.get('header_title', {}))
    details_body_style = _style_inline(styles.get('details_body', {}))
    # Preferir estilo compatível com e-mail; fallback para o badge padrão
    number_badge_style = dict(styles.get('result_number_email', {}) or styles.get('result_number', {}))
    # Remover propriedades problemáticas em e-mail caso herdadas
    for k in ['position', 'top', 'left', 'right', 'bottom', 'display', 'alignItems', 'justifyContent', 'padding']:
        number_badge_style.pop(k, None)
    number_badge_style_str = _style_inline(number_badge_style)

    # --- Helpers de formatação (equivalentes ao GSB, mas locais) ---
    from datetime import datetime as _dt

    def _format_br_date(date_value) -> str:
        if not date_value:
            return 'N/A'
        s = str(date_value)
        try:
            s_clean = s.replace('Z', '')
            dt = _dt.fromisoformat(s_clean[:19]) if 'T' in s_clean else _dt.strptime(s_clean[:10], '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except Exception:
            # tenta DD/MM/YYYY já formatado
            try:
                _dt.strptime(s[:10], '%d/%m/%Y')
                return s[:10]
            except Exception:
                return s

    def _to_float(value):
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            import re as _re
            s = str(value).strip()
            if not s:
                return None
            s = _re.sub(r"[^0-9,\.-]", "", s)
            if s.count(',') == 1 and s.count('.') >= 1:
                s = s.replace('.', '').replace(',', '.')
            elif s.count(',') == 1 and s.count('.') == 0:
                s = s.replace(',', '.')
            elif s.count(',') > 1 and s.count('.') == 0:
                s = s.replace(',', '')
            return float(s)
        except Exception:
            return None

    def _format_money(value) -> str:
        f = _to_float(value)
        if f is None:
            return str(value or '')
        return f"{f:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _parse_date_generic(date_value):
        if not date_value:
            return None
        s = str(date_value).strip()
        if not s or s.upper() == 'N/A':
            return None
        try:
            if 'T' in s:
                s0 = s[:19]
                try:
                    return _dt.fromisoformat(s0).date()
                except Exception:
                    pass
            try:
                return _dt.strptime(s[:10], '%Y-%m-%d').date()
            except Exception:
                pass
            try:
                return _dt.strptime(s[:10], '%d/%m/%Y').date()
            except Exception:
                pass
        except Exception:
            return None
        return None

    # Cores de status de encerramento (iguais ao GSB)
    COLOR_ENC_NA = "#838383"
    COLOR_ENC_EXPIRED = "#800080"
    COLOR_ENC_LT3 = "#FF0000EE"
    COLOR_ENC_LT7 = "#FF6200"
    COLOR_ENC_LT15 = "#FFB200"
    COLOR_ENC_LT30 = "#01B33A"
    COLOR_ENC_GT30 = "#0099FF"

    def _enc_status_and_color(date_value):
        from datetime import date as _date
        dt = _parse_date_generic(date_value)
        if not dt:
            return 'na', COLOR_ENC_NA
        today = _date.today()
        diff = (dt - today).days
        if diff < 0:
            return 'expired', COLOR_ENC_EXPIRED
        if diff <= 3:
            return 'lt3', COLOR_ENC_LT3
        if diff <= 7:
            return 'lt7', COLOR_ENC_LT7
        if diff <= 15:
            return 'lt15', COLOR_ENC_LT15
        if diff <= 30:
            return 'lt30', COLOR_ENC_LT30
        return 'gt30', COLOR_ENC_GT30

    def _enc_status_text(status: str, dt_value) -> str:
        from datetime import date as _date
        if status == 'na':
            return 'sem data'
        if status == 'expired':
            return 'expirada'
        try:
            dt = _parse_date_generic(dt_value)
            if dt and dt == _date.today():
                return 'encerra hoje!'
        except Exception:
            pass
        if status == 'lt3':
            return 'encerra em até 3 dias'
        if status == 'lt7':
            return 'encerra em até 7 dias'
        if status == 'lt15':
            return 'encerra em até 15 dias'
        if status == 'lt30':
            return 'encerra em até 30 dias'
        if status == 'gt30':
            return 'encerra > 30 dias'
        return ''

    # --- Cabeçalho do e-mail ---
    LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"
    # Cabeçalho com título
    header_html = (
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
        f"<img src='{LOGO_PATH}' alt='GovGo' style='{header_logo_style}'/>"
        f"<h4 style='{header_title_style}'>GvG Search</h4>"
        f"</div>"
    )

    # Cabeçalho da busca (consulta + configurações) inspirado no GSB
    # Mapas de nomes iguais ao GSB
    SEARCH_TYPES = {1: "Semântica", 2: "Palavras‑chave", 3: "Híbrida"}
    SEARCH_APPROACHES = {1: "Direta", 2: "Correspondência de Categoria", 3: "Filtro de Categoria"}
    SORT_MODES = {1: "Similaridade", 2: "Data (Encerramento)", 3: "Valor (Estimado)"}
    RELEVANCE_LEVELS = {1: "Sem filtro", 2: "Flexível", 3: "Restritivo"}

    cfg = dict(cfg_snapshot or {})
    st = int(cfg.get('search_type', 3)) if isinstance(cfg.get('search_type'), (int, float, str)) else 3
    sa = int(cfg.get('search_approach', 3)) if isinstance(cfg.get('search_approach'), (int, float, str)) else 3
    rl = int(cfg.get('relevance_level', 2)) if isinstance(cfg.get('relevance_level'), (int, float, str)) else 2
    sm = int(cfg.get('sort_mode', 1)) if isinstance(cfg.get('sort_mode'), (int, float, str)) else 1
    mr = int(cfg.get('max_results', 50)) if isinstance(cfg.get('max_results'), (int, float, str)) else 50
    tc = int(cfg.get('top_categories_count', 10)) if isinstance(cfg.get('top_categories_count'), (int, float, str)) else 10
    cfg_parts = []
    try:
        if st in SEARCH_TYPES: cfg_parts.append(f"Tipo: {SEARCH_TYPES[st]}")
        if sa in SEARCH_APPROACHES: cfg_parts.append(f"Abordagem: {SEARCH_APPROACHES[sa]}")
        if rl in RELEVANCE_LEVELS: cfg_parts.append(f"Relevância: {RELEVANCE_LEVELS[rl]}")
        if sm in SORT_MODES: cfg_parts.append(f"Ordenação: {SORT_MODES[sm]}")
        cfg_parts.append(f"Máx.: {mr}")
        cfg_parts.append(f"Categorias: {tc}")
    except Exception:
        pass
    cfg_txt = " | ".join(cfg_parts)
    # Frequência (opcional)
    sched_line = ""
    try:
        stype = (schedule_type or '').upper()
        sdet = schedule_detail if isinstance(schedule_detail, dict) else {}
        days = sdet.get('days') if isinstance(sdet, dict) else None
        if stype:
            if isinstance(days, list) and days:
                sched_line = f"Frequência: {stype.title()} ({', '.join(days)})"
            else:
                sched_line = f"Frequência: {stype.title()}"
    except Exception:
        sched_line = ""

    header_html += (
        f"<div style='{title_style}'>Consulta</div>"
        f"<div style='font-size:12px;color:#003A70;'><span style='font-weight:bold;'>Texto: </span>{(query_text or '').strip()}</div>"
        f"<div style='font-size:11px;color:#003A70;margin-top:2px;'>{cfg_txt}</div>"
        + (f"<div style='font-size:11px;color:#003A70;margin-top:2px;'>{sched_line}</div>" if sched_line else "")
    )

    # --- Cards ---
    parts: List[str] = [header_html]
    if not items:
        parts.append(f"<div style='{card_style}'>Sem resultados nesta execução.</div>")
        return "\n".join(parts)

    # Ordenação: Data de Encerramento ascendente; N/A por último; empate por similaridade desc
    def _sort_key(it: Dict[str, Any]):
        payload = it.get('payload') or {}
        raw_enc = it.get('data_encerramento_proposta') or payload.get('data_encerramento_proposta')
        dt = _parse_date_generic(raw_enc)
        sim = it.get('similarity')
        try:
            simf = float(sim) if sim is not None else -1.0
        except Exception:
            simf = -1.0
        if dt is None:
            return (1, _dt.max.date(), -simf)
        return (0, dt, -simf)

    sorted_items = sorted(items, key=_sort_key)

    # --- Tabela de resultados (resumo) estilo GSB ---
    try:
        table_rows = []
        for idx, it in enumerate(sorted_items, start=1):
            payload = it.get('payload') or {}
            unidade = payload.get('orgao') or 'N/A'
            municipio = payload.get('municipio') or 'N/A'
            uf = payload.get('uf') or ''
            sim = it.get('similarity')
            try:
                sim_val = (round(float(sim), 4) if sim is not None else '')
            except Exception:
                sim_val = sim or ''
            valor = _format_money(payload.get('valor'))
            raw_enc = it.get('data_encerramento_proposta') or payload.get('data_encerramento_proposta')
            enc_txt = _format_br_date(raw_enc)
            status_key, enc_color = _enc_status_and_color(raw_enc)
            table_rows.append(
                f"<tr style='font-size:12px;'>"
                f"<td style='padding:6px;border:1px solid #ddd;'>{idx}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;'>{unidade}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;'>{municipio}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;'>{uf}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;'>{sim_val}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;'>R$ {valor}</td>"
                f"<td style='padding:6px;border:1px solid #ddd;color:{enc_color};font-weight:bold;'>{enc_txt}</td>"
                f"</tr>"
            )
        table_html = (
            f"<div style='{card_style}'>"
            f"<div style='{title_style}'>Resultados</div>"
            f"<table style='border-collapse:collapse;width:100%;'>"
            f"<thead style='background-color:#f8f9fa;'>"
            f"<tr style='font-size:13px;font-weight:bold;'>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>#</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Órgão</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Município</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>UF</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Similaridade</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Valor (R$)</th>"
            f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Data de Encerramento</th>"
            f"</tr>"
            f"</thead>"
            f"<tbody>" + "".join(table_rows) + f"</tbody>"
            f"</table>"
            f"</div>"
        )
        parts.append(table_html)
    except Exception:
        pass

    for i, it in enumerate(sorted_items, start=1):
        payload = it.get('payload') or {}
        orgao = payload.get('orgao') or ''
        unidade = payload.get('unidade') or ''
        municipio = payload.get('municipio') or ''
        uf = payload.get('uf') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        objeto = payload.get('objeto') or ''
        valor = _format_money(payload.get('valor'))
        data_abertura = _format_br_date(it.get('data_abertura_proposta') or payload.get('data_abertura_proposta'))
        raw_enc = it.get('data_encerramento_proposta') or payload.get('data_encerramento_proposta')
        data_enc = _format_br_date(raw_enc)
        status_key, enc_color = _enc_status_and_color(raw_enc)
        status_text = _enc_status_text(status_key, raw_enc)
        link = (payload.get('links') or {}).get('origem') or ''
        pncp_id = it.get('numero_controle_pncp') or ''

        # Truncar rótulo do link
        link_text = link or 'N/A'
        if link and len(link_text) > 100:
            link_text = link_text[:97] + '...'

        # Tag de status de data (aplica backgroundColor dinâmico)
        link_html = f"<a href='{link}' target='_blank'>{link_text}</a>" if link else 'N/A'

        # Documentos do processo (lista curta de links)
        docs_html = ""
        try:
            docs = fetch_documentos(str(pncp_id)) if pncp_id else []
        except Exception:
            docs = []
        if docs:
            max_docs = 5
            doc_items = []
            for d in docs[:max_docs]:
                try:
                    d_url = d.get('url')
                    if not d_url:
                        continue
                    d_nome = (d.get('nome') or 'Documento').strip()
                    if len(d_nome) > 80:
                        d_nome = d_nome[:77] + '...'
                    doc_items.append(f"<li style='margin:0 0 2px 0;'><a href='{d_url}' target='_blank'>{d_nome}</a></li>")
                except Exception:
                    continue
            if doc_items:
                more = len(docs) - len(doc_items)
                more_txt = f"<li style='color:#555;font-size:11px;list-style:none;margin-top:2px;'>+{more} mais…</li>" if more > 0 else ""
                docs_html = (
                    "<div style='margin-top:6px;'><span style='font-weight:bold;'>Documentos: </span>"
                    "<ul style='margin:4px 0 0 18px;padding:0;'>" + "".join(doc_items) + more_txt + "</ul></div>"
                )

        body_html = (
            f"<div style='{details_body_style}'>"
            f"<div style='font-weight:bold;color:#003A70;margin-bottom:6px;'>{i}</div>"
            f"<div><span style='font-weight:bold;'>Órgão: </span><span>{orgao}</span></div>"
            f"<div><span style='font-weight:bold;'>Unidade: </span><span>{unidade or 'N/A'}</span></div>"
            f"<div><span style='font-weight:bold;'>Local: </span><span>{local}</span></div>"
            f"<div><span style='font-weight:bold;'>ID PNCP: </span><span>{pncp_id or 'N/A'}</span></div>"
            f"<div><span style='font-weight:bold;'>Valor: </span><span>{valor}</span></div>"
            #f"<div style='display:flex;align-items:center;gap:4px;'><span style='font-weight:bold;'>Data de Abertura: </span><span> {data_abertura}</span></div>"
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
            f"<span style='font-weight:bold;'>Data de Encerramento: </span>"
            f"<span style='color:{enc_color};font-weight:bold;'> {data_enc} - {status_text}</span></div>"
            f"<div style='margin-bottom:8px;'><span style='font-weight:bold;'>Link: </span>{link_html}</div>"
            f"{docs_html}"
            f"<div><span style='font-weight:bold;'>Descrição: </span><span>{objeto}</span></div>"
            f"</div>"
        )

        parts.append(
            f"<div style='{card_style}'>"
            f"{body_html}"
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
        channels = b.get('channels') or []
        cfg_snapshot = b.get('config_snapshot') or {}
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
        html = _render_html_boletim(query, rows, cfg_snapshot, stype, sdetail)
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
