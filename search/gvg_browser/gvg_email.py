"""
gvg_email.py
Utilitário de envio de email via SMTP.

Lê variáveis de ambiente:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
  SMTP_TLS (true/false), SMTP_USE_SSL (true/false), SMTP_TIMEOUT, SMTP_REPLY_TO, SMTP_SUBJECT_PREFIX

Exposta a função send_html_email(to, subject, html, text_alt=None).
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional, Any, Dict, List

# Opcional: estilos do site para reaproveitar no HTML de e-mail

try:
    from gvg_styles import styles  # type: ignore
except Exception:
    styles = {}

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")

def _get_smtp_config():
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM")
    use_tls = _env_bool("SMTP_TLS", True)
    use_ssl = _env_bool("SMTP_USE_SSL", False)
    timeout = int(os.getenv("SMTP_TIMEOUT", "15"))
    reply_to = os.getenv("SMTP_REPLY_TO")
    subject_prefix = os.getenv("SMTP_SUBJECT_PREFIX", "")
    return {
        "host": host,
        "port": port,
        "user": user,
        "pwd": pwd,
        "from": from_addr,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": timeout,
        "reply_to": reply_to,
        "subject_prefix": subject_prefix,
    }

def send_html_email(to: str, subject: str, html: str, text_alt: Optional[str] = None) -> bool:
    cfg = _get_smtp_config()
    # Dry-run se faltar configuração crítica
    if not cfg["host"] or not cfg["from"] or (not cfg["use_ssl"] and not cfg["use_tls"] and not cfg["port"]):
        # Log simplificado; o caller deve ter um logger
        print(f"[EMAIL] Dry-run: to={to} subject={subject} (config SMTP ausente)")
        return False

    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to
    if cfg["subject_prefix"]:
        subject = f"{cfg['subject_prefix']} {subject}"
    msg["Subject"] = subject
    if cfg["reply_to"]:
        msg["Reply-To"] = cfg["reply_to"]

    if not text_alt:
        text_alt = "Veja este boletim em um cliente compatível com HTML."
    msg.set_content(text_alt)
    msg.add_alternative(html, subtype="html")

    try:
        if cfg["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=cfg["timeout"]) as server:
                if cfg["user"] and cfg["pwd"]:
                    server.login(cfg["user"], cfg["pwd"])
                server.send_message(msg)
                return True
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"]) as server:
                if cfg["use_tls"]:
                    server.starttls(context=ssl.create_default_context())
                if cfg["user"] and cfg["pwd"]:
                    server.login(cfg["user"], cfg["pwd"])
                server.send_message(msg)
                return True
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar para {to}: {e}")
        return False

__all__ = ["send_html_email"]

# Limites para anexar detalhes adicionais
EMAIL_MAX_ITENS_PER_PNCP = 10
EMAIL_MAX_DOCS_PER_PNCP = 10


# ========================
# Renderers de e-mail HTML
# ========================

def _style_inline(d: Dict[str, Any]) -> str:
    return "; ".join(f"{k}:{v}" for k, v in (d or {}).items())


def _format_br_date(date_value) -> str:
    if not date_value:
        return 'N/A'
    from datetime import datetime as _dt
    s = str(date_value)
    try:
        s_clean = s.replace('Z', '')
        dt = _dt.fromisoformat(s_clean[:19]) if 'T' in s_clean else _dt.strptime(s_clean[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
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

def _format_qty(v: float | None) -> str:
    if v is None:
        return ''
    try:
        if abs(v - int(v)) < 1e-9:
            return str(int(v))
        return f"{v:.2f}".rstrip('0').rstrip('.')
    except Exception:
        return str(v)


def _format_money(value) -> str:
    f = _to_float(value)
    if f is None:
        return str(value or '')
    return f"{f:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _parse_date_generic(date_value):
    if not date_value:
        return None
    from datetime import datetime as _dt
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


def _render_itens_inline(itens: List[Dict[str, Any]], limit: int = EMAIL_MAX_ITENS_PER_PNCP) -> str:
    if itens is None:
        return ""
    if not itens:
        return "<div style='font-size:12px;color:#003A70;'>Sem itens.</div>"
    rows_html = []
    total_geral = 0.0
    for i, it in enumerate(itens[:limit], start=1):
        desc = (it.get('descricao_item') or it.get('descricao') or it.get('objeto') or '')
        desc = str(desc)
        if len(desc) > 120:
            desc = desc[:117] + '...'
        qty = it.get('quantidade_item') or it.get('quantidade') or it.get('qtd')
        unit = it.get('valor_unitario_estimado') or it.get('valor_unitario') or it.get('valorUnitario')
        tot = it.get('valor_total_estimado') or it.get('valor_total') or it.get('valorTotal')
        f_qty = _to_float(qty) or 0.0
        f_unit = _to_float(unit) or 0.0
        f_total = _to_float(tot) if _to_float(tot) is not None else (f_qty * f_unit)
        total_geral += (f_total or 0.0)
        rows_html.append(
            f"<tr style='font-size:11px;'>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{i}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{desc}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:right;'>{_format_qty(f_qty)}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:right;'>{_format_money(f_unit)}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:right;'>{_format_money(f_total)}</td>"
            f"</tr>"
        )
    extra = max(0, len(itens) - limit)
    header = (
        "<thead><tr style='font-size:11px;font-weight:bold;background:#f8f9fa;'>"
        "<th style='border:1px solid #ddd;padding:4px;width:28px;'>#</th>"
        "<th style='border:1px solid #ddd;padding:4px;'>Descrição</th>"
        "<th style='border:1px solid #ddd;padding:4px;width:55px;text-align:right;'>Qtd</th>"
        "<th style='border:1px solid #ddd;padding:4px;width:80px;text-align:right;'>V.Unit</th>"
        "<th style='border:1px solid #ddd;padding:4px;width:95px;text-align:right;'>V.Total</th>"
        "</tr></thead>"
    )
    footer = (
        f"<tr style='font-size:11px;font-weight:bold;background:#fafafa;'>"
        f"<td colspan='4' style='border:1px solid #ddd;padding:4px;text-align:right;'>Soma</td>"
        f"<td style='border:1px solid #ddd;padding:4px;text-align:right;'>{_format_money(total_geral)}</td>"
        f"</tr>"
    )
    table = (
        "<table style='border-collapse:collapse;width:100%;margin-top:4px;'>"
        + header + "<tbody>" + ''.join(rows_html) + footer + "</tbody></table>"
    )
    if extra:
        table += f"<div style='font-size:10px;color:#003A70;margin-top:2px;'>+{extra} itens não exibidos...</div>"
    return table


def _render_docs_inline(docs: List[Dict[str, Any]], limit: int = EMAIL_MAX_DOCS_PER_PNCP) -> str:
    if docs is None:
        return ""
    if not docs:
        return "<div style='font-size:12px;color:#003A70;'>Sem documentos.</div>"
    lines = []
    for d in docs[:limit]:
        url = d.get('url') or d.get('link') or ''
        nome = d.get('nome') or d.get('nome_arquivo') or ''
        if not nome and url:
            try:
                nome = url.split('/')[-1][:80]
            except Exception:
                nome = 'documento'
        if len(nome) > 80:
            nome = nome[:77] + '...'
        link_html = f"<a href='{url}' target='_blank'>{nome or 'documento'}</a>" if url else (nome or 'documento')
        lines.append(f"<li style='margin-bottom:2px;'>{link_html}</li>")
    extra = max(0, len(docs) - limit)
    html_list = "<ul style='padding-left:16px;margin:4px 0;'>" + ''.join(lines) + "</ul>"
    if extra:
        html_list += f"<div style='font-size:10px;color:#003A70;margin-top:2px;'>+{extra} documentos não exibidos...</div>"
    return html_list


def render_boletim_email_html(query_text: str, items: List[Dict[str, Any]],
                              cfg_snapshot: Optional[Dict[str, Any]] = None,
                              schedule_type: Optional[str] = None,
                              schedule_detail: Optional[Dict[str, Any]] = None,
                              items_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                              docs_map: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> str:
    """Render completo de boletim (título + resumo + tabela + cards)."""
    card_style = _style_inline(styles.get('result_card', {}))
    title_style = _style_inline(styles.get('card_title', {}))
    details_body_style = _style_inline(styles.get('details_body', {}))
    header_logo_style = _style_inline(styles.get('header_logo', {}))
    header_title_style = _style_inline(styles.get('header_title', {}))

    LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"
    header_html = (
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
        f"<img src='{LOGO_PATH}' alt='GovGo' style='{header_logo_style}'/>"
        f"<h4 style='{header_title_style}'>GvG Search</h4>"
        f"</div>"
    )

    parts: List[str] = [header_html]
    # Cabeçalho da consulta
    cfg = dict(cfg_snapshot or {})
    SEARCH_TYPES = {1: "Semântica", 2: "Palavras‑chave", 3: "Híbrida"}
    SEARCH_APPROACHES = {1: "Direta", 2: "Correspondência de Categoria", 3: "Filtro de Categoria"}
    SORT_MODES = {1: "Similaridade", 2: "Data (Encerramento)", 3: "Valor (Estimado)"}
    RELEVANCE_LEVELS = {1: "Sem filtro", 2: "Flexível", 3: "Restritivo"}
    try:
        st = int(cfg.get('search_type', 3)); sa = int(cfg.get('search_approach', 3)); rl = int(cfg.get('relevance_level', 2)); sm = int(cfg.get('sort_mode', 1))
        mr = int(cfg.get('max_results', 50)); tc = int(cfg.get('top_categories_count', 10))
    except Exception:
        st, sa, rl, sm, mr, tc = 3, 3, 2, 1, 50, 10
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
        pass
    parts.append(
        f"<div style='{title_style}'>Consulta</div>"
        f"<div style='font-size:12px;color:#003A70;'><span style='font-weight:bold;'>Texto: </span>{(query_text or '').strip()}</div>"
        f"<div style='font-size:11px;color:#003A70;margin-top:2px;'>{' | '.join(cfg_parts)}</div>"
        + (f"<div style='font-size:11px;color:#003A70;margin-top:2px;'>{sched_line}</div>" if sched_line else "")
    )

    if not items:
        parts.append(f"<div style='{card_style}'>Sem resultados nesta execução.</div>")
        return "\n".join(parts)

    # Ordenação: data enc. asc, N/A no fim; desempate por similaridade desc
    from datetime import datetime as _dt
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

    # Tabela resumo
    try:
        table_rows = []
        for idx, it in enumerate(sorted_items, start=1):
            pl = it.get('payload') or {}
            unidade = pl.get('orgao') or 'N/A'
            municipio = pl.get('municipio') or 'N/A'
            uf = pl.get('uf') or ''
            sim = it.get('similarity')
            try:
                sim_val = (round(float(sim), 4) if sim is not None else '')
            except Exception:
                sim_val = sim or ''
            valor = _format_money(pl.get('valor'))
            raw_enc = it.get('data_encerramento_proposta') or pl.get('data_encerramento_proposta')
            enc_txt = _format_br_date(raw_enc)
            _status, enc_color = _enc_status_and_color(raw_enc)
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
        parts.append(
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
    except Exception:
        pass

    # Cards
    for i, it in enumerate(sorted_items, start=1):
        pl = it.get('payload') or {}
        orgao = pl.get('orgao') or ''
        unidade = pl.get('unidade') or ''
        municipio = pl.get('municipio') or ''
        uf = pl.get('uf') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        objeto = pl.get('objeto') or ''
        valor = _format_money(pl.get('valor'))
        data_abertura = _format_br_date(it.get('data_abertura_proposta') or pl.get('data_abertura_proposta'))
        raw_enc = it.get('data_encerramento_proposta') or pl.get('data_encerramento_proposta')
        data_enc = _format_br_date(raw_enc)
        status_key, enc_color = _enc_status_and_color(raw_enc)
        status_text = _enc_status_text(status_key, raw_enc)
        link = (pl.get('links') or {}).get('origem') or ''
        pncp_id = it.get('numero_controle_pncp') or ''
        link_text = link or 'N/A'
        if link and len(link_text) > 100:
            link_text = link_text[:97] + '...'
        link_html = f"<a href='{link}' target='_blank'>{link_text}</a>" if link else 'N/A'
        body_parts = [
            f"<div style='{details_body_style}'>",
            f"<div style='font-weight:bold;color:#003A70;margin-bottom:6px;'>{i}</div>",
            f"<div><span style='font-weight:bold;'>Órgão: </span><span>{orgao}</span></div>",
            f"<div><span style='font-weight:bold;'>Unidade: </span><span>{unidade or 'N/A'}</span></div>",
            f"<div><span style='font-weight:bold;'>Local: </span><span>{local}</span></div>",
            f"<div><span style='font-weight:bold;'>ID PNCP: </span><span>{pncp_id or 'N/A'}</span></div>",
            f"<div><span style='font-weight:bold;'>Valor: </span><span>{valor}</span></div>",
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'><span style='font-weight:bold;'>Data de Encerramento: </span><span style='color:{enc_color};font-weight:bold;'> {data_enc} - {status_text}</span></div>",
            f"<div style='margin-bottom:8px;'><span style='font-weight:bold;'>Link: </span>{link_html}</div>",
            f"<div><span style='font-weight:bold;'>Descrição: </span><span>{objeto}</span></div>",
        ]
        if items_map is not None:
            body_parts.append(
                "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
                + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Itens</div>"
                + _render_itens_inline((items_map or {}).get(pncp_id, []))
            )
        if docs_map is not None:
            body_parts.append(
                "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
                + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Documentos</div>"
                + _render_docs_inline((docs_map or {}).get(pncp_id, []))
            )
        body_parts.append("</div>")
        body_html = ''.join(body_parts)
        parts.append(f"<div style='{card_style}'>{body_html}</div>")

    return "\n".join(parts)


def render_favorito_email_html(details: Dict[str, Any], itens: Optional[List[Dict[str, Any]]] = None, docs: Optional[List[Dict[str, Any]]] = None) -> str:
    """Render do card de detalhes de uma contratação única (favorito)."""
    card_style = _style_inline(styles.get('result_card', {}))
    details_body_style = _style_inline(styles.get('details_body', {}))
    # Extrair campos em snake_case (gvg_schema)
    orgao = details.get('orgao_entidade_razao_social') or ''
    unidade = details.get('unidade_orgao_nome_unidade') or ''
    municipio = details.get('unidade_orgao_municipio_nome') or ''
    uf = details.get('unidade_orgao_uf_sigla') or ''
    local = f"{municipio}/{uf}" if uf else municipio
    pncp_id = details.get('numero_controle_pncp') or ''
    valor = _format_money(details.get('valor_total_estimado') or details.get('valor_total_homologado'))
    raw_enc = details.get('data_encerramento_proposta')
    data_enc = _format_br_date(raw_enc)
    status_key, enc_color = _enc_status_and_color(raw_enc)
    status_text = _enc_status_text(status_key, raw_enc)
    link = details.get('link_sistema_origem') or ''
    link_text = link or 'N/A'
    if link and len(link_text) > 100:
        link_text = link_text[:97] + '...'
    link_html = f"<a href='{link}' target='_blank'>{link_text}</a>" if link else 'N/A'
    objeto = details.get('objeto_compra') or ''

    body_parts = [
        f"<div style='{details_body_style}'>",
        f"<div><span style='font-weight:bold;'>Órgão: </span><span>{orgao}</span></div>",
        f"<div><span style='font-weight:bold;'>Unidade: </span><span>{unidade or 'N/A'}</span></div>",
        f"<div><span style='font-weight:bold;'>Local: </span><span>{local}</span></div>",
        f"<div><span style='font-weight:bold;'>ID PNCP: </span><span>{pncp_id or 'N/A'}</span></div>",
        f"<div><span style='font-weight:bold;'>Valor: </span><span>{valor}</span></div>",
        f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'><span style='font-weight:bold;'>Data de Encerramento: </span><span style='color:{enc_color};font-weight:bold;'> {data_enc} - {status_text}</span></div>",
        f"<div style='margin-bottom:8px;'><span style='font-weight:bold;'>Link: </span>{link_html}</div>",
        f"<div><span style='font-weight:bold;'>Descrição: </span><span>{objeto}</span></div>",
    ]
    if itens is not None:
        body_parts.append(
            "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
            + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Itens</div>"
            + _render_itens_inline(itens or [])
        )
    if docs is not None:
        body_parts.append(
            "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
            + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Documentos</div>"
            + _render_docs_inline(docs or [])
        )
    body_parts.append("</div>")
    body_html = ''.join(body_parts)
    return f"<div style='{card_style}'>{body_html}</div>"


def render_history_email_html(prompt_text: str, results: List[Dict[str, Any]], items_map: Optional[Dict[str, List[Dict[str, Any]]]] = None, docs_map: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> str:
    """Render e-mail para histórico de consulta reutilizando formato de boletim (sem config de agenda).

    results: saída de fetch_user_results_for_prompt_text (lista com 'details').
    """
    LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"
    card_style = _style_inline(styles.get('result_card', {}))
    title_style = _style_inline(styles.get('card_title', {}))
    details_body_style = _style_inline(styles.get('details_body', {}))
    header_logo_style = _style_inline(styles.get('header_logo', {}))
    header_title_style = _style_inline(styles.get('header_title', {}))
    header_html = (
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
        f"<img src='{LOGO_PATH}' alt='GovGo' style='{header_logo_style}'/>"
        f"<h4 style='{header_title_style}'>GvG Search</h4>"
        f"</div>"
    )
    parts: List[str] = [header_html]
    parts.append(
        f"<div style='{title_style}'>Histórico de Consulta</div>"
        f"<div style='font-size:12px;color:#003A70;'><span style='font-weight:bold;'>Texto: </span>{(prompt_text or '').strip()}</div>"
    )
    if not results:
        parts.append(f"<div style='{card_style}'>Sem resultados salvos para esta consulta.</div>")
        return "\n".join(parts)
    # Sort por rank asc
    try:
        results_sorted = sorted(results, key=lambda r: r.get('rank') or 10**9)
    except Exception:
        results_sorted = results
    # Tabela
    table_rows = []
    for r in results_sorted[:200]:  # limite de segurança
        d = r.get('details') or {}
        orgao = d.get('orgao_entidade_razao_social') or ''
        municipio = d.get('unidade_orgao_municipio_nome') or ''
        uf = d.get('unidade_orgao_uf_sigla') or ''
        valor = _format_money(d.get('valor_total_estimado') or d.get('valor_total_homologado'))
        enc = d.get('data_encerramento_proposta')
        enc_txt = _format_br_date(enc)
        _, enc_color = _enc_status_and_color(enc)
        rank = r.get('rank') or ''
        sim = r.get('similarity')
        try:
            sim_val = (round(float(sim),4) if sim is not None else '')
        except Exception:
            sim_val = sim or ''
        table_rows.append(
            f"<tr style='font-size:12px;'>"
            f"<td style='padding:6px;border:1px solid #ddd;'>{rank}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;'>{orgao}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;'>{municipio}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;'>{uf}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;'>{sim_val}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;'>R$ {valor}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;color:{enc_color};font-weight:bold;'>{enc_txt}</td>"
            f"</tr>"
        )
    parts.append(
        f"<div style='{card_style}'>"
        f"<div style='{title_style}'>Resultados Salvos</div>"
        f"<table style='border-collapse:collapse;width:100%;'>"
        f"<thead style='background-color:#f8f9fa;'>"
        f"<tr style='font-size:13px;font-weight:bold;'>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>#</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Órgão</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Município</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>UF</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Similaridade</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Valor (R$)</th>"
        f"<th style='padding:6px;border:1px solid #ddd;text-align:left;'>Data Enc.</th>"
        f"</tr>"
        f"</thead><tbody>{''.join(table_rows)}</tbody></table></div>"
    )
    # Cards
    for r in results_sorted[:200]:
        d = r.get('details') or {}
        orgao = d.get('orgao_entidade_razao_social') or ''
        unidade = d.get('unidade_orgao_nome_unidade') or ''
        municipio = d.get('unidade_orgao_municipio_nome') or ''
        uf = d.get('unidade_orgao_uf_sigla') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        objeto = d.get('objeto_compra') or ''
        valor = _format_money(d.get('valor_total_estimado') or d.get('valor_total_homologado'))
        enc = d.get('data_encerramento_proposta')
        enc_txt = _format_br_date(enc)
        status_key, enc_color = _enc_status_and_color(enc)
        status_text = _enc_status_text(status_key, enc)
        link = d.get('link_sistema_origem') or ''
        pid = d.get('numero_controle_pncp') or ''
        link_text = link or 'N/A'
        if link and len(link_text) > 100:
            link_text = link_text[:97] + '...'
        link_html = f"<a href='{link}' target='_blank'>{link_text}</a>" if link else 'N/A'
        body_html = (
            f"<div style='{details_body_style}'>"
            f"<div style='font-weight:bold;color:#003A70;margin-bottom:6px;'>{r.get('rank') or ''}</div>"
            f"<div><span style='font-weight:bold;'>Órgão: </span><span>{orgao}</span></div>"
            f"<div><span style='font-weight:bold;'>Unidade: </span><span>{unidade or 'N/A'}</span></div>"
            f"<div><span style='font-weight:bold;'>Local: </span><span>{local}</span></div>"
            f"<div><span style='font-weight:bold;'>ID PNCP: </span><span>{pid or 'N/A'}</span></div>"
            f"<div><span style='font-weight:bold;'>Valor: </span><span>{valor}</span></div>"
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
            f"<span style='font-weight:bold;'>Data de Encerramento: </span>"
            f"<span style='color:{enc_color};font-weight:bold;'> {enc_txt} - {status_text}</span></div>"
            f"<div style='margin-bottom:8px;'><span style='font-weight:bold;'>Link: </span>{link_html}</div>"
            f"<div><span style='font-weight:bold;'>Descrição: </span><span>{objeto}</span></div>"
        )
        if items_map is not None:
            body_html += (
                "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
                + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Itens</div>"
                + _render_itens_inline((items_map or {}).get(pid, []))
            )
        if docs_map is not None:
            body_html += (
                "<hr style='margin:10px 0;border:none;border-top:1px solid #ddd;'>"
                + "<div style='font-weight:bold;color:#003A70;font-size:13px;'>Documentos</div>"
                + _render_docs_inline((docs_map or {}).get(pid, []))
            )
        body_html += "</div>"
        parts.append(f"<div style='{card_style}'>{body_html}</div>")
    return "\n".join(parts)


__all__ += [
    'render_boletim_email_html',
    'render_favorito_email_html',
    'render_history_email_html',
    '_render_itens_inline','_render_docs_inline'
]
