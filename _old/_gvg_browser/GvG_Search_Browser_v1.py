"""
GvG_Search_Browser.py
Versão browser (Dash) do GvG_Search_Terminal, reutilizando o visual dos Reports.

Funcionalidades principais:
- Busca PNCP: Semântica, Palavras‑chave, Híbrida; Abordagens: Direta, Correspondência, Filtro
- Pré-processamento inteligente e filtro de relevância (via gvg_search_core)
- Tabelas de TOP categorias e Resultados (estilo Reports)
- Cards de detalhes por resultado (cores/bordas/fontes iguais aos Reports)
- Exportações: JSON/XLSX/CSV/PDF/HTML
- Documentos do processo: listar links e processar (quando disponível)
"""

from __future__ import annotations

import os
import re
import io
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate

# =====================================================================================
# Importações locais (usar os módulos já copiados para gvg_browser)
# =====================================================================================
from gvg_preprocessing import (
    format_currency,
    format_date,
    decode_poder,
    decode_esfera,
    SearchQueryProcessor,
)
from gvg_ai_utils import (
    generate_keywords,
    get_embedding,
    get_negation_embedding,
)
from gvg_search_core import (
    semantic_search,
    keyword_search,
    hybrid_search,
    toggle_intelligent_processing,
    set_sql_debug,
    get_intelligent_status,
    set_relevance_filter_level,
    get_relevance_filter_status,
    get_top_categories_for_query,
    correspondence_search as categories_correspondence_search,
    category_filtered_search as categories_category_filtered_search,
    fetch_contratacao_by_pncp,
)
from gvg_exporters import (
    export_results_json,
    export_results_excel,
    export_results_csv,
    export_results_pdf,
    export_results_html,
)
from gvg_documents import fetch_documentos

from gvg_styles import styles, CSS_ALL

from gvg_user import (
    get_current_user,
    get_user_initials,
    fetch_prompt_texts,
    add_prompt,
    save_user_results,
    delete_prompt,
    fetch_bookmarks,
    add_bookmark,
    remove_bookmark,
)


try:
    # Prefer summarize_document; fall back to process_pncp_document if needed
    try:
        from gvg_documents import summarize_document  # type: ignore
    except Exception:
        summarize_document = None  # type: ignore
    try:
        from gvg_documents import process_pncp_document  # type: ignore
    except Exception:
        process_pncp_document = None  # type: ignore
    try:
        from gvg_documents import set_markdown_enabled  # type: ignore
    except Exception:
        def set_markdown_enabled(_enabled: bool):
            return None
    DOCUMENTS_AVAILABLE = bool(summarize_document or process_pncp_document)
except Exception:
    summarize_document = None  # type: ignore
    process_pncp_document = None  # type: ignore
    def set_markdown_enabled(_enabled: bool):
        return None
    DOCUMENTS_AVAILABLE = False


# =====================================================================================
# Constantes / dicionários (idênticos à semântica do Terminal/Function)
# =====================================================================================
DEFAULT_MAX_RESULTS = 30
DEFAULT_TOP_CATEGORIES = 10

SEARCH_TYPES = {
    1: {"name": "Semântica"},
    2: {"name": "Palavras‑chave"},
    3: {"name": "Híbrida"},
}
SEARCH_APPROACHES = {
    1: {"name": "Direta"},
    2: {"name": "Correspondência de Categoria"},
    3: {"name": "Filtro de Categoria"},
}
SORT_MODES = {
    1: {"name": "Similaridade"},
    2: {"name": "Data (Encerramento)"},
    3: {"name": "Valor (Estimado)"},
}
RELEVANCE_LEVELS = {
    1: {"name": "Sem filtro"},
    2: {"name": "Flexível"},
    3: {"name": "Restritivo"},
}


# =====================================================================================
# Cores padronizadas para datas de encerramento (tabela e detalhes)
# =====================================================================================
COLOR_ENC_NA = "#000000"       # N/A
COLOR_ENC_EXPIRED = "#800080"  # roxo
COLOR_ENC_LT3 = "#FF0000EE"      # vermelho escuro (<= 3 dias)
COLOR_ENC_LT7 = "#FF6200"      # vermelho (<= 7 dias)
COLOR_ENC_LT15 = "#FFBD21"     # laranja (<= 15 dias)
COLOR_ENC_LT30 = "#BBFF00B4"     # amarelo (<= 30 dias)
COLOR_ENC_GT30 = "#2BFF00AF"     # verde  (> 30 dias)


# styles agora vem de gvg_styles


# =====================================================================================
# App Dash (com Bootstrap para fontes e ícones FontAwesome)
# =====================================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'GovGo Search'

# Parse argumentos --debug e --markdown (ex: python GvG_Search_Browser.py --debug --markdown)
try:
    import argparse
    _parser = argparse.ArgumentParser(add_help=False)
    _parser.add_argument('--debug', action='store_true')
    _parser.add_argument('--markdown', action='store_true')
    _known, _ = _parser.parse_known_args()
    if _known and getattr(_known, 'debug', False):
        set_sql_debug(True)
    if _known and getattr(_known, 'markdown', False):
        try:
            set_markdown_enabled(True)
        except Exception:
            pass
except Exception:
    pass

# ==========================
# Progresso global (polled por Interval)
# ==========================
PROGRESS = {"percent": 0, "label": ""}

def progress_set(percent: int, label: str | None = None):
    try:
        p = int(max(0, min(100, percent)))
    except Exception:
        p = 0
    PROGRESS["percent"] = p
    if label is not None:
        PROGRESS["label"] = str(label)

def progress_reset():
    PROGRESS["percent"] = 0
    PROGRESS["label"] = ""

def b64_image(image_path: str) -> str:
    try:
        with open(image_path, 'rb') as f:
            import base64
            image = f.read()
        return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')
    except Exception:
        return ''


# Cabeçalho fixo no topo
_USER = get_current_user()
_USER_INITIALS = get_user_initials(_USER.get('name'))
LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"
header = html.Div([
    html.Div([
    html.Img(src=LOGO_PATH, style=styles['header_logo']),
    html.H4("GvG Search", style=styles['header_title'])
    ], style=styles['header_left']),
    html.Div([
        html.Div(
            _USER_INITIALS,
            title=f"{_USER.get('name','Usuário')} ({_USER.get('email','')})",
        style=styles['header_user_badge']
        )
    ], style=styles['header_right'])
], style=styles['header'])


# Painel de controles (esquerda)
controls_panel = html.Div([
    html.Div('Consulta', style={**styles['card_title'], }),
    # Entrada de consulta estilo Reports no rodapé esquerdo
    html.Div([
        dcc.Textarea(
            id='query-input',
            placeholder='Digite sua consulta...',
            rows=2,
            style={**styles['input_field'], 'overflowY': 'auto', 'resize': 'none', 'height': '80px'}
        ),
        html.Button(
            html.I(className="fas fa-arrow-right"),
            id='submit-button',
            style=styles['arrow_button']
        )
    ], id='query-container', style=styles['input_container']),
    html.Div([
        html.Div("Configurações de Busca", style=styles['card_title']),
        html.Button(
            html.I(className="fas fa-chevron-down"),
            id='config-toggle-btn',
            title='Mostrar/ocultar configurações',
            style={**styles['arrow_button_small'], 'marginRight': '12px'}
        ),
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div([
                html.Label('Tipo', className='gvg-form-label'),
                dcc.Dropdown(id='search-type', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SEARCH_TYPES.items()], value=1, clearable=False, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Abordagem', className='gvg-form-label'),
                dcc.Dropdown(id='search-approach', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SEARCH_APPROACHES.items()], value=3, clearable=False, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Relevância', className='gvg-form-label'),
                dcc.Dropdown(id='relevance-level', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in RELEVANCE_LEVELS.items()], value=2, clearable=False, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Ordenação', className='gvg-form-label'),
                dcc.Dropdown(id='sort-mode', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SORT_MODES.items()], value=1, clearable=False, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Máx. resultados', className='gvg-form-label'),
                dcc.Input(id='max-results', type='number', min=5, max=1000, value=DEFAULT_MAX_RESULTS, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('TOP categorias', className='gvg-form-label'),
                dcc.Input(id='top-categories', type='number', min=5, max=50, value=DEFAULT_TOP_CATEGORIES, style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                dcc.Checklist(id='toggles', options=[
                    {'label': ' Filtrar encerrados', 'value': 'filter_expired'},
                ], value=['filter_expired'])
            ], style=styles['row_wrap_gap'])
        ], style={**styles['controls_group'], 'position': 'relative'}, className='gvg-controls'),
        id='config-collapse', is_open=True
    ),

    html.Div([
        html.Div('Histórico de Consultas', style=styles['card_title']),
        html.Button(
            html.I(className="fas fa-chevron-down"),
            id='history-toggle-btn',
            title='Mostrar/ocultar histórico',
            style={**styles['arrow_button_small'], 'marginRight': '12px'}
        ),
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div(id='history-list')
        ], id='history-card', style=styles['controls_group']),
        id='history-collapse', is_open=True
    ),
    html.Div([
        html.Div('Favoritos', style=styles['card_title']),
        html.Button(
            html.I(className="fas fa-chevron-down"),
            id='favorites-toggle-btn',
            title='Mostrar/ocultar favoritos',
            style={**styles['arrow_button_small'], 'marginRight': '12px'}
        ),
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div(id='favorites-list')
        ], id='favorites-card', style=styles['controls_group']),
        id='favorites-collapse', is_open=True
    )
], style=styles['left_panel'])


# Painel de resultados (direita)
results_panel = html.Div([
        # Barra de abas (abas)
        html.Div(id='tabs-bar', style={**styles['result_card'], **styles['tabs_bar'], 'display': 'none'}),
        # Conteúdo das abas: query vs pncp
        html.Div([
            # Painel de consulta (query)
            html.Div([
                html.Div(id='status-bar', style={**styles['result_card'], 'display': 'none'}),
                # Spinner central durante processamento (mostrado apenas quando a aba ativa está processando)
                html.Div(
                    [
                        html.Div([
                            html.Div(id='progress-fill', style={**styles['progress_fill'], 'width': '0%'})
                        ], id='progress-bar', style={**styles['progress_bar_container'], 'display': 'none'}),
                        html.Div(id='progress-label', children='', style={**styles['progress_label'], 'display': 'none'})
                    ], id='gvg-center-spinner', style=styles['center_spinner']
                ),
                html.Div([
                    html.Div([
                        html.Div('Exportar', style=styles['card_title']),
                        html.Button('JSON', id='export-json', style={**styles['submit_button'], 'width': '120px'}),
                        html.Button('XLSX', id='export-xlsx', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
                        html.Button('CSV', id='export-csv', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
                        html.Button('PDF', id='export-pdf', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
                        html.Button('HTML', id='export-html', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
                    ], style=styles['export_row'])
                ], id='export-panel', style={**styles['result_card'], 'display': 'none'}),
                html.Div(id='categories-table', style={**styles['result_card'], 'display': 'none'}),
                html.Div([
                    html.Div('Resultados', style=styles['card_title']),
                    html.Div(id='results-table-inner')
                ], id='results-table', style={**styles['result_card'], 'display': 'none'}),
                html.Div(id='results-details')
            ], id='query-panel', style={'display': 'none'}),
            # Painel PNCP
            html.Div(id='pncp-panel', style={'display': 'none'})
        ], id='tab-content', style={'display': 'none', 'backgroundColor': 'transparent'})
], style=styles['right_panel'])


# Layout principal
app.layout = html.Div([
    dcc.Store(id='store-results', data=[]),
    dcc.Store(id='store-results-sorted', data=[]),
    dcc.Store(id='store-categories', data=[]),
    dcc.Store(id='store-meta', data={}),
    dcc.Store(id='store-last-query', data=""),
    dcc.Store(id='store-history', data=[]),
    dcc.Store(id='store-history-open', data=True),
    dcc.Store(id='store-favorites', data=[]),
    dcc.Store(id='store-favorites-open', data=True),
    dcc.Store(id='processing-state', data=False),
    dcc.Store(id='store-config-open', data=True),
    dcc.Store(id='store-items', data={}),
    dcc.Store(id='store-sort', data=None),
    dcc.Store(id='store-panel-active', data={}),
    dcc.Store(id='store-cache-itens', data={}),
    dcc.Store(id='store-cache-docs', data={}),
    dcc.Store(id='store-cache-resumo', data={}),
    dcc.Store(id='progress-store', data={'percent': 0, 'label': ''}),
    dcc.Interval(id='progress-interval', interval=400, n_intervals=0, disabled=True),
    dcc.Download(id='download-out'),
    # Stores de sessões (abas/tabs)
    dcc.Store(id='store-sessions', data={}),  # {session_id: {type: 'query'|'pncp', title: str, created: ts}}
    dcc.Store(id='store-active-session', data=None),
    dcc.Store(id='store-processing-session', data=None),
    dcc.Store(id='store-session-data', data={}),  # {sid: {results:[], categories:[], meta:{}, query:str}}

    header,
    html.Div([
        controls_panel,
        results_panel,
    ], style=styles['container'])
])


# =====================================================================================
# Helpers
# =====================================================================================
def _to_float(value):
    """Coerce numeric-like values (including BR-formatted strings) to float.

    Returns None when parsing is not possible.
    """
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if not s:
            return None
        # Remove currency symbols/spaces
        s = re.sub(r"[^0-9,\.-]", "", s)
        # Heuristics: if both '.' and ',' exist and exactly one comma, treat comma as decimal (pt-BR)
        if s.count(',') == 1 and s.count('.') >= 1:
            s = s.replace('.', '').replace(',', '.')
        elif s.count(',') == 1 and s.count('.') == 0:
            # Single comma, assume decimal comma
            s = s.replace(',', '.')
        elif s.count(',') > 1 and s.count('.') == 0:
            # Multiple commas as thousands
            s = s.replace(',', '')
        # else: assume dot-decimal or plain integer
        return float(s)
    except Exception:
        return None

def _sort_results(results: List[dict], order_mode: int) -> List[dict]:
    if not results:
        return results
    if order_mode == 1:
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
    if order_mode == 2:
        # Sort by closing date (data de encerramento)
        def _to_date(date_value):
            """Parse date string to sortable date object (YYYY-MM-DD preferred). Returns datetime.date or None if invalid."""
            if not date_value:
                return None
            s = str(date_value).strip()
            if not s:
                return None
            from datetime import datetime
            # Try ISO first
            for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y'):
                try:
                    return datetime.strptime(s[:10], fmt).date()
                except Exception:
                    continue
            # Fallback: try to extract YYYY-MM-DD
            import re
            m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
            if m:
                try:
                    return datetime.strptime(m.group(0), '%Y-%m-%d').date()
                except Exception:
                    pass
            return None
        def _date_key(item: dict):
            d = item.get('details', {}) or {}
            # Try canonical then aliases
            v = (
                d.get('data_encerramento_proposta')
                or d.get('dataencerramentoproposta')
                or d.get('dataEncerramentoProposta')
                or d.get('dataEncerramento')
            )
            dt = _to_date(v)
            # For descending order, None dates go last
            return dt if dt is not None else ''
    return sorted(results, key=_date_key, reverse=False)
    if order_mode == 3:
        # Prefer estimated value; fallback to homologated/final
        def _value_key(item: dict) -> float:
            d = item.get('details', {}) or {}
            # estimated first
            v_est = d.get('valor_total_estimado') or d.get('valortotalestimado') or d.get('valorTotalEstimado')
            v = _to_float(v_est)
            if v is None:
                # fallback to homologated/final
                v_hom = (
                    d.get('valor_total_homologado')
                    or d.get('valortotalhomologado')
                    or d.get('valorTotalHomologado')
                    or d.get('valorfinal')
                    or d.get('valorFinal')
                )
                v = _to_float(v_hom)
            return v if v is not None else 0.0
        return sorted(results, key=_value_key, reverse=True)
    return results


def _extract_text(d: dict, keys: List[str]) -> str:
    for k in keys:
        v = d.get(k)
        if v:
            return str(v)
    return ''


def _sorted_for_ui(results: List[dict], sort_state: dict) -> List[dict]:
    """Return a new list sorted according to sort_state = {field, direction}.

    Fields: orgao, municipio, uf, similaridade, valor, data
    Direction: 'asc' | 'desc'
    Always keeps None/missing at the end.
    """
    if not results:
        return []
    state = sort_state or {}
    field = (state.get('field') or 'similaridade').lower()
    direction = (state.get('direction') or 'desc').lower()
    is_desc = direction == 'desc'

    def key_fn(item: dict):
        d = item.get('details', {}) or {}
        if field == 'similaridade':
            v = item.get('similarity', None)
            if v is None:
                return float('inf')
            return -float(v) if is_desc else float(v)
        if field == 'valor':
            v_est = d.get('valor_total_estimado') or d.get('valortotalestimado') or d.get('valorTotalEstimado')
            v = _to_float(v_est)
            if v is None:
                # fallback homologado/final
                v_h = d.get('valor_total_homologado') or d.get('valortotalhomologado') or d.get('valorTotalHomologado') or d.get('valorfinal') or d.get('valorFinal')
                v = _to_float(v_h)
            if v is None:
                return float('inf')
            return -v if is_desc else v
        if field == 'data':
            dt = _parse_date_generic(
                d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento')
            )
            if dt is None:
                return float('inf')
            ordv = dt.toordinal()
            return -ordv if is_desc else ordv
        # For text fields we won't use key_fn; handled below
        if field in ('orgao', 'municipio', 'uf'):
            return 0
        # default: keep input order
        return float('inf')

    # Text fields: sort present values, then append missing to keep them last
    if field in ('orgao', 'municipio', 'uf'):
        def get_text(item: dict) -> str:
            d = item.get('details', {}) or {}
            if field == 'orgao':
                unidade = _extract_text(d, ['unidadeorgao_nomeunidade', 'unidadeOrgao_nomeUnidade'])
                orgao = _extract_text(d, ['orgaoentidade_razaosocial', 'orgaoEntidade_razaosocial', 'nomeorgaoentidade'])
                return (unidade or orgao or '').strip().lower()
            if field == 'municipio':
                return _extract_text(d, ['unidadeorgao_municipionome', 'unidadeOrgao_municipioNome', 'municipioentidade']).strip().lower()
            if field == 'uf':
                return _extract_text(d, ['unidadeorgao_ufsigla', 'unidadeOrgao_ufSigla', 'uf']).strip().lower()
            return ''
        present = [it for it in results if get_text(it)]
        missing = [it for it in results if not get_text(it)]
        present_sorted = sorted(present, key=lambda it: get_text(it), reverse=is_desc)
        out = present_sorted + missing
    else:
        # Stable sort based on key function; since key encodes direction, use reverse=False
        out = sorted(list(results), key=key_fn)
    # Recompute rank according to new order
    for i, r in enumerate(out, 1):
        r['rank'] = i
    return out


def _highlight_terms(text: str, query: str) -> str:
    """Destaca apenas os termos da consulta pós pré-processamento.

    - Usa SearchQueryProcessor() para obter os termos finais (mais limpos).
    - Não usa regex; cria spans de índice e envolve com <mark> sem sobreposição.
    - Case-insensitive, preservando o texto original.
    """
    if not text:
        return ''

    source = str(text)
    q = (query or '').strip()
    if not q:
        return source

    # 1) Pré-processar consulta para extrair termos finais
    try:
        processor = SearchQueryProcessor()
        info = processor.process_query(q) or {}
        processed = (info.get('search_terms') or '').strip()
    except Exception:
        processed = q

    # Lista de termos: filtrar curtos e duplicados
    terms_raw = [t for t in (processed.split() if processed else []) if len(t) > 2]
    if not terms_raw:
        return source
    # Normalizar para comparação (lower) e manter original para tamanho
    seen = set()
    terms = []
    for t in terms_raw:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            terms.append(t)
    # Ordenar por tamanho decrescente apenas por estética (não estritamente necessário)
    terms.sort(key=lambda x: len(x), reverse=True)

    # 2) Encontrar todas as ocorrências (sem regex)
    s_lower = source.lower()
    spans = []  # lista de (start, end)
    for t in terms:
        tl = t.lower()
        start = 0
        L = len(tl)
        while True:
            pos = s_lower.find(tl, start)
            if pos == -1:
                break
            spans.append((pos, pos + L))
            start = pos + L  # avança para evitar sobreposição infinita

    if not spans:
        return source

    # 3) Mesclar spans sobrepostos/contíguos (garante uma marcação por trecho)
    spans.sort(key=lambda x: x[0])
    merged = []
    for st, en in spans:
        if not merged or st > merged[-1][1]:
            merged.append([st, en])
        else:
            merged[-1][1] = max(merged[-1][1], en)

    # 4) Construir saída com <mark>
    out = []
    last = 0
    for st, en in merged:
        if st > last:
            out.append(source[last:st])
        out.append("<mark style='background:#FFE08A'>")
        out.append(source[st:en])
        out.append("</mark>")
        last = en
    if last < len(source):
        out.append(source[last:])
    return ''.join(out)


def _parse_date_generic(date_value):
    """Parse supported date formats to datetime.date or return None."""
    if not date_value:
        return None
    s = str(date_value).strip()
    if not s or s.upper() == 'N/A':
        return None
    try:
        # Normalize ISO with time
        from datetime import datetime
        if 'T' in s:
            s0 = s[:19]
            try:
                return datetime.fromisoformat(s0).date()
            except Exception:
                pass
        # YYYY-MM-DD
        try:
            return datetime.strptime(s[:10], '%Y-%m-%d').date()
        except Exception:
            pass
        # DD/MM/YYYY
        try:
            return datetime.strptime(s[:10], '%d/%m/%Y').date()
        except Exception:
            pass
    except Exception:
        return None
    return None


def _enc_status_and_color(date_value):
    """Return a tuple (status, color) for the closing date proximity.

    Status values: 'na', 'expired', 'lt3', 'lt7', 'lt15', 'lt30', 'gt30'
    Colors: black, purple, darkred, red, orange, yellow, green
    """
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


def _build_pncp_data(details: dict) -> dict:
    return {
        'id': details.get('numerocontrolepncp') or details.get('numeroControlePNCP'),
        'municipio': (details.get('unidadeorgao_municipionome') or details.get('municipioentidade') or ''),
        'uf': (details.get('unidadeorgao_ufsigla') or details.get('uf') or ''),
        'orgao': (details.get('orgaoentidade_razaosocial') or details.get('orgaoEntidade_razaosocial') or details.get('nomeorgaoentidade') or ''),
        'data_inclusao': details.get('datainclusao') or details.get('dataInclusao'),
        'data_abertura': details.get('dataaberturaproposta') or details.get('dataAberturaProposta'),
        'data_encerramento': details.get('dataencerramentoproposta') or details.get('dataEncerramentoProposta') or details.get('dataEncerramento'),
        'modalidade_id': details.get('modalidadeid') or details.get('modalidadeId'),
        'modalidade_nome': details.get('modalidadenome') or details.get('modalidadeNome'),
        'disputa_id': details.get('modadisputaid') or details.get('modaDisputaId'),
        'disputa_nome': details.get('modadisputanome') or details.get('modaDisputaNome'),
        'descricao': details.get('descricaocompleta') or details.get('descricaoCompleta') or details.get('objeto'),
        'link': details.get('linksistemaorigem') or details.get('linkSistemaOrigem')
    }


def _format_br_date(date_value) -> str:
    """Return date as DD/MM/YYYY; accepts ISO strings (with or without time)."""
    if not date_value:
        return 'N/A'
    s = str(date_value)
    try:
        # Handles 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' (with optional timezone 'Z')
        s_clean = s.replace('Z', '')
        dt = datetime.fromisoformat(s_clean[:19]) if 'T' in s_clean else datetime.strptime(s_clean[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return s


def _format_qty(value) -> str:
    """Format quantities using BR style: thousands '.', decimal ',' with up to 2 decimals when needed."""
    f = _to_float(value)
    if f is None:
        return str(value or '')
    if abs(f - int(f)) < 1e-9:
        return f"{int(f):,}".replace(',', '.')
    return f"{f:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _format_money(value) -> str:
    """Format monetary values without currency symbol, BR style (1.234,56)."""
    f = _to_float(value)
    if f is None:
        return str(value or '')
    return f"{f:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# Sanitização de limites vindos da UI
def _sanitize_limit(value, default=DEFAULT_MAX_RESULTS, min_v=5, max_v=1000) -> int:
    try:
        if value is None:
            return int(default)
        n = int(value)
        if n < min_v:
            return int(min_v)
        if n > max_v:
            return int(max_v)
        return n
    except Exception:
        return int(default)


# ==========================
# Histórico de consultas (por usuário)
# ==========================
def load_history(max_items: int = 50) -> list:
    try:
        return fetch_prompt_texts(limit=max_items)
    except Exception:
        return []

def save_history(history: list, max_items: int = 50):
    # Atualiza apenas a Store (memória). Persistência no banco ocorre em run_search
    # para garantir que as configurações do prompt sejam salvas junto.
    return None


# =====================================================================================
# Callbacks: buscar → executar pipeline → renderizar
# =====================================================================================
@app.callback(
    Output('store-results', 'data'),
    Output('store-categories', 'data'),
    Output('store-meta', 'data'),
    Output('store-last-query', 'data'),
    Output('processing-state', 'data', allow_duplicate=True),
    Input('processing-state', 'data'),
    State('query-input', 'value'),
    State('search-type', 'value'),
    State('search-approach', 'value'),
    State('relevance-level', 'value'),
    State('sort-mode', 'value'),
    State('max-results', 'value'),
    State('top-categories', 'value'),
    State('toggles', 'value'),
    prevent_initial_call=True,
)
def run_search(is_processing, query, s_type, approach, relevance, order, max_results, top_cat, toggles):
    if not is_processing:
        raise PreventUpdate
    if not query or len(query.strip()) < 3:
        raise PreventUpdate
    # Resetar e iniciar progresso
    try:
        progress_reset()
        progress_set(2, 'Iniciando')
    except Exception:
        pass

    # Alinhar nível de relevância
    try:
        curr_rel = get_relevance_filter_status().get('level')
        if curr_rel != relevance:
            set_relevance_filter_level(relevance)
    except Exception:
        pass

    # Forçar IA/Debug/Negation sempre ATIVOS; manter apenas toggle de encerrados
    try:
        toggle_intelligent_processing(True)
    except Exception:
        pass

    filter_expired = 'filter_expired' in (toggles or [])
    negation_emb = True

    # Pré-processar termos para categorias
    base_terms = query
    try:
        processor = SearchQueryProcessor()
        info = processor.process_query(query)
        try:
            progress_set(10, 'Pré-processando consulta')
        except Exception:
            pass
        # Debug opcional: exibir saída do Assistant quando SQL debug estiver ativo
        try:
            from gvg_search_core import SQL_DEBUG
            if SQL_DEBUG:
                print("[ASSISTANT][process_query] =>", info)
        except Exception:
            pass
        if (info.get('search_terms') or '').strip():
            base_terms = info['search_terms']
    except Exception:
        pass

    import time
    t0 = time.time()

    # Sanitizar limites vindos da UI ANTES de usar
    safe_limit = _sanitize_limit(max_results, default=DEFAULT_MAX_RESULTS, min_v=5, max_v=1000)
    safe_top = _sanitize_limit(top_cat, default=DEFAULT_TOP_CATEGORIES, min_v=1, max_v=100)

    categories: List[dict] = []
    if approach in (2, 3):
        try:
            try:
                progress_set(20, 'Buscando categorias')
            except Exception:
                pass
            categories = get_top_categories_for_query(
                query_text=base_terms or query,
                top_n=safe_top,
                use_negation=False,
                search_type=s_type,
                console=None,
            )
        except Exception:
            categories = []

    results: List[dict] = []
    confidence: float = 0.0
    try:
        if approach == 1:
            try:
                progress_set(70, 'Executando busca direta')
            except Exception:
                pass
            if s_type == 1:
                results, confidence = semantic_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
            elif s_type == 2:
                results, confidence = keyword_search(query, limit=safe_limit, filter_expired=filter_expired)
            else:
                results, confidence = hybrid_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
        elif approach == 2:
            if categories:
                try:
                    progress_set(70, 'Executando busca por correspondência')
                except Exception:
                    pass
                results, confidence, _ = categories_correspondence_search(
                    query_text=query,
                    top_categories=categories,
                    limit=safe_limit,
                    filter_expired=filter_expired,
                    console=None,
                )
        elif approach == 3:
            if categories:
                try:
                    progress_set(70, 'Executando busca filtrada por categoria')
                except Exception:
                    pass
                results, confidence, _ = categories_category_filtered_search(
                    query_text=query,
                    search_type=s_type,
                    top_categories=categories,
                    limit=safe_limit,
                    filter_expired=filter_expired,
                    use_negation=negation_emb,
                    console=None,
                )
    except Exception:
        results = []
        confidence = 0.0

    try:
        progress_set(78, 'Ordenando resultados')
    except Exception:
        pass
    results = _sort_results(results or [], order or 1)
    for i, r in enumerate(results, 1):
        r['rank'] = i

    elapsed = time.time() - t0
    # Persistir prompt do usuário e resultados (após processamento)
    try:
        if query and isinstance(query, str) and query.strip():
            # Preparar embedding do prompt (com negação, se aplicável)
            try:
                search_terms = (info.get('search_terms') if isinstance(info, dict) else None) or query
                negative_terms = (info.get('negative_terms') if isinstance(info, dict) else None) or ''
                embedding_input = f"{search_terms} -- {negative_terms}".strip() if negative_terms else search_terms
                emb = get_negation_embedding(embedding_input) if negation_emb else get_embedding(embedding_input)
                prompt_emb = emb.tolist() if emb is not None and hasattr(emb, 'tolist') else (emb if emb is not None else None)
            except Exception:
                prompt_emb = None
            try:
                progress_set(90, 'Salvando histórico')
            except Exception:
                pass
            prompt_id = add_prompt(
                query.strip(),
                search_type=s_type,
                search_approach=approach,
                relevance_level=relevance,
                sort_mode=order,
                max_results=safe_limit,
                top_categories_count=safe_top,
                filter_expired=filter_expired,
                embedding=prompt_emb,
            )
            if prompt_id:
                try:
                    save_user_results(prompt_id, results or [])
                except Exception:
                    pass
    except Exception:
        pass
    meta = {
        'elapsed': elapsed,
        'confidence': confidence,
        'count': len(results),
        'search': s_type,
        'approach': approach,
        'relevance': relevance,
        'order': order,
        'filter_expired': filter_expired,
        'negation': negation_emb,
    'max_results': safe_limit,
    'top_categories': safe_top,
    }
    try:
        progress_set(100, 'Concluído')
        progress_reset()
    except Exception:
        pass
    return results, categories, meta, query, False


# Callback: seta/spinner do botão de envio no estilo Reports
@app.callback(
    Output('submit-button', 'children'),
    Output('submit-button', 'disabled'),
    Output('submit-button', 'style'),
    Input('processing-state', 'data')
)
def update_submit_button(is_processing):
    if is_processing:
        return html.I(className="fas fa-spinner fa-spin", style={'color': 'white'}), True, styles['arrow_button']
    return html.I(className="fas fa-arrow-right"), False, styles['arrow_button']


# Mostrar/ocultar spinner central no painel direito
@app.callback(
    Output('gvg-center-spinner', 'style'),
    Input('processing-state', 'data')
)
def toggle_center_spinner(is_processing):
    # Controlado por callback abaixo com base na sessão ativa
    return dash.no_update


# Habilita/desabilita o Interval do progresso conforme o processamento
@app.callback(
    Output('progress-interval', 'disabled'),
    Input('processing-state', 'data')
)
def toggle_progress_interval(is_processing):
    return not bool(is_processing)


# Atualiza a Store de progresso periodicamente a partir do estado global
@app.callback(
    Output('progress-store', 'data'),
    Input('progress-interval', 'n_intervals'),
    State('processing-state', 'data'),
    prevent_initial_call=False,
)
def update_progress_store(_n, is_processing):
    if not is_processing:
        return {'percent': 0, 'label': ''}
    try:
        p = int(PROGRESS.get('percent', 0))
        lbl = PROGRESS.get('label', '')
    except Exception:
        p, lbl = 0, ''
    return {'percent': p, 'label': lbl}


# Reflete a barra de progresso na UI
@app.callback(
    Output('progress-fill', 'style'),
    Output('progress-bar', 'style'),
    Output('progress-label', 'children'),
    Output('progress-label', 'style'),
    Input('progress-store', 'data'),
    Input('processing-state', 'data'),
    prevent_initial_call=False,
)
def reflect_progress_bar(data, is_processing):
    percent = 0
    try:
        percent = int((data or {}).get('percent', 0))
    except Exception:
        percent = 0
    label = (data or {}).get('label') or ''
    bar_style = dict(styles['progress_bar_container'])
    bar_style['display'] = 'block' if (is_processing and percent > 0 and percent < 100) else 'none'

    fill_style = dict(styles['progress_fill'])
    fill_style['width'] = f'{percent}%'
    label_text = f"{percent}% — {label}" if label else (f"{percent}%" if percent else '')
    label_style = dict(styles['progress_label'])
    label_style['display'] = 'block' if (is_processing and percent > 0 and percent < 100) else 'none'
    return fill_style, bar_style, label_text, label_style


# Limpar conteúdo do painel de resultados ao iniciar nova busca
@app.callback(
    Output('results-table-inner', 'children', allow_duplicate=True),
    Output('results-details', 'children', allow_duplicate=True),
    Output('status-bar', 'children', allow_duplicate=True),
    Output('categories-table', 'children', allow_duplicate=True),
    Output('store-panel-active', 'data', allow_duplicate=True),
    Output('store-cache-itens', 'data', allow_duplicate=True),
    Output('store-cache-docs', 'data', allow_duplicate=True),
    Output('store-cache-resumo', 'data', allow_duplicate=True),
    Input('processing-state', 'data'),
    State('store-active-session', 'data'),
    State('store-processing-session', 'data'),
    prevent_initial_call=True,
)
def clear_results_content_on_start(is_processing, active_sid, processing_sid):
    if not is_processing:
        raise PreventUpdate
    # Only clear if the active tab is the one processing
    if not active_sid or not processing_sid or active_sid != processing_sid:
        raise PreventUpdate
    # Esvazia conteúdos imediatamente
    return [], [], [], [], {}, {}, {}, {}


# Ocultar cartões/tabelas enquanto processa (evita flicker de conteúdo antigo)
@app.callback(
    Output('status-bar', 'style', allow_duplicate=True),
    Output('categories-table', 'style', allow_duplicate=True),
    Output('export-panel', 'style', allow_duplicate=True),
    Output('results-table', 'style', allow_duplicate=True),
    Output('results-details', 'style', allow_duplicate=True),
    Input('processing-state', 'data'),
    prevent_initial_call=True,
)
def hide_result_panels_during_processing(is_processing):
    if not is_processing:
        raise PreventUpdate
    base = styles['result_card'].copy()
    hidden = {**base, 'display': 'none'}
    return hidden, hidden, hidden, hidden, hidden


# Callback: define estado de processamento quando clicar seta
@app.callback(
    Output('processing-state', 'data', allow_duplicate=True),
    Output('store-processing-session', 'data', allow_duplicate=True),
    Input('submit-button', 'n_clicks'),
    State('query-input', 'value'),
    State('processing-state', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def set_processing_state(n_clicks, query, is_processing, active_sid):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    if is_processing or not query or not query.strip():
        raise PreventUpdate
    return True, active_sid


# ==========================
# Abas/Tabs: helpers
# ==========================
def _session_title_for_query(query: str) -> str:
    q = (query or '').strip().replace('\n', ' ')
    return (q[:60] + '...') if len(q) > 60 else q or 'Consulta'

def _session_title_for_pncp(pncp_id: str) -> str:
    return f"PNCP {pncp_id}"

def _build_tab_progress():
    return html.Div([
        html.Div([html.Div(id='progress-fill', style={**styles['progress_fill'], 'width': '0%'})], id='progress-bar', style={**styles['progress_bar_container'], 'display': 'none'}),
        html.Div(id='progress-label', children='', style={**styles['progress_label'], 'display': 'none'})
    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'justifyContent': 'center', 'height': '120px'})

def _render_query_tab_skeleton(session_id: str, title: str):
    # Conteúdo inicial: apenas o progress bar central durante processamento
    return html.Div([
        html.Div(id={'type': 'status-bar', 'sid': session_id}, style={**styles['result_card'], 'display': 'none'}),
        html.Div(id={'type': 'export-panel', 'sid': session_id}, style={**styles['result_card'], 'display': 'none'}),
        html.Div(id={'type': 'categories-table', 'sid': session_id}, style={**styles['result_card'], 'display': 'none'}),
        html.Div([
            html.Div('Resultados', style=styles['card_title']),
            html.Div(id={'type': 'results-table-inner', 'sid': session_id})
        ], id={'type': 'results-table', 'sid': session_id}, style={**styles['result_card'], 'display': 'none'}),
        html.Div(id={'type': 'results-details', 'sid': session_id}),
        _build_tab_progress()
    ], id={'type': 'tab-content', 'sid': session_id})

def _render_pncp_tab_content(session_id: str, pncp_id: str, details: dict):
    # Renderiza único card de detalhe, idêntico ao card dos resultados
    r = {'rank': 1, 'details': details}
    # Reutiliza render de um único card criando a estrutura do card
    d = details or {}
    descricao_full = d.get('descricaocompleta') or d.get('descricaoCompleta') or d.get('objeto') or ''
    destaque = descricao_full
    valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or d.get('valorfinal') or d.get('valorFinal') or 0)
    data_inc = _format_br_date(d.get('datainclusao') or d.get('dataInclusao') or d.get('dataassinatura') or d.get('dataAssinatura'))
    data_ab = _format_br_date(d.get('dataaberturaproposta') or d.get('dataAberturaProposta'))
    raw_en = d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento')
    data_en = _format_br_date(raw_en)
    _enc_status, enc_color = _enc_status_and_color(raw_en)
    orgao = d.get('orgaoentidade_razaosocial') or d.get('orgaoEntidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/A'
    unidade = d.get('unidadeorgao_nomeunidade') or d.get('unidadeOrgao_nomeUnidade') or 'N/A'
    municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or d.get('municipioentidade') or 'N/A'
    uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or d.get('uf') or ''
    local = f"{municipio}/{uf}" if uf else municipio
    link = d.get('linksistemaorigem') or d.get('linkSistemaOrigem')
    pncp_id_txt = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or pncp_id
    link_text = link or 'N/A'
    if link and len(link_text) > 100:
        link_text = link_text[:97] + '...'
    body = html.Div([
        html.Div([html.Span('Órgão: ', style={'fontWeight': 'bold'}), html.Span(orgao)]),
        html.Div([html.Span('Unidade: ', style={'fontWeight': 'bold'}), html.Span(unidade)]),
        html.Div([html.Span('ID PNCP: ', style={'fontWeight': 'bold'}), html.Span(str(pncp_id_txt))]),
        html.Div([html.Span('Local: ', style={'fontWeight': 'bold'}), html.Span(local)]),
        html.Div([html.Span('Valor: ', style={'fontWeight': 'bold'}), html.Span(valor)]),
        html.Div([html.Span('Datas: ', style={'fontWeight': 'bold'}), html.Span(f"Abertura: {data_ab} | Encerramento: "), html.Span(str(data_en), style={'color': enc_color, 'fontWeight': 'bold'})]),
        html.Div([html.Span('Link: ', style={'fontWeight': 'bold'}), html.A(link_text, href=link, target='_blank', style=styles['link_break_all']) if link else html.Span('N/A')], style={'marginBottom': '8px'}),
        html.Div([html.Span('Descrição: ', style={'fontWeight': 'bold'}), html.Div(dcc.Markdown(children=destaque))])
    ], style=styles['details_body'])
    left_panel = html.Div(body, style=styles['details_left_panel'])
    right_panel = html.Div([], style=styles['details_right_panel'])
    _card_style = dict(styles['result_card']); _card_style['marginBottom'] = '6px'
    card = html.Div([
        html.Div([left_panel, right_panel], style={'display': 'flex', 'gap': '10px', 'alignItems': 'stretch'}),
        html.Div('1', style=styles['result_number'])
    ], style=_card_style)
    return html.Div([
        html.Div('Detalhes', style=styles['card_title']),
        card
    ], id={'type': 'tab-content', 'sid': session_id})


# Toggle config collapse open/close and icon
@app.callback(
    Output('store-config-open', 'data'),
    Input('config-toggle-btn', 'n_clicks'),
    State('store-config-open', 'data'),
    prevent_initial_call=True,
)
def toggle_config(n_clicks, is_open):
    if not n_clicks:
        raise PreventUpdate
    return not bool(is_open)


@app.callback(
    Output('config-collapse', 'is_open'),
    Input('store-config-open', 'data')
)
def reflect_collapse(is_open):
    return bool(is_open)


@app.callback(
    Output('config-toggle-btn', 'children'),
    Input('store-config-open', 'data')
)
def update_config_icon(is_open):
    return html.I(className="fas fa-chevron-down") if is_open else html.I(className="fas fa-chevron-right")


# Toggle collapse do Histórico
@app.callback(
    Output('store-history-open', 'data'),
    Input('history-toggle-btn', 'n_clicks'),
    State('store-history-open', 'data'),
    prevent_initial_call=True,
)
def toggle_history(n_clicks, is_open):
    if not n_clicks:
        raise PreventUpdate
    return not bool(is_open)


@app.callback(
    Output('history-collapse', 'is_open'),
    Input('store-history-open', 'data')
)
def reflect_history_collapse(is_open):
    return bool(is_open)


@app.callback(
    Output('history-toggle-btn', 'children'),
    Input('store-history-open', 'data')
)
def update_history_icon(is_open):
    return html.I(className="fas fa-chevron-down") if is_open else html.I(className="fas fa-chevron-right")


@app.callback(
    Output('query-container', 'style'),
    Input('store-config-open', 'data')
)
def move_query_on_collapse(is_open):
    # Keep the query container directly below the config card with standard spacing
    base = styles['input_container'].copy()
    base['marginTop'] = '10px'
    return base


# Status e categorias
@app.callback(
    Output('store-history', 'data'),
    Input('store-history', 'data'),
    prevent_initial_call=False,
)
def init_history(history):
    # Initialize from disk if empty
    if history:
        return history
    return load_history()


# ==========================
# Abas/Tabs: criação/ativação/fechamento
# ==========================
@app.callback(
    Output('store-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('store-processing-session', 'data', allow_duplicate=True),
    Output('tabs-bar', 'style', allow_duplicate=True),
    Output('tabs-bar', 'children', allow_duplicate=True),
    Input('processing-state', 'data'),  # quando inicia processamento de consulta
    State('query-input', 'value'),
    State('store-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def create_query_tab_on_processing(is_processing, query_value, sessions, active_sid):
    if not is_processing or not query_value or not query_value.strip():
        raise PreventUpdate
    # Cria sessão para consulta imediatamente
    sessions = dict(sessions or {})
    import time, uuid
    sid = str(uuid.uuid4())
    title = _session_title_for_query(query_value)
    sessions[sid] = {'type': 'query', 'title': title, 'created': time.time(), 'query': query_value}
    # limite 100 abas: remove a mais antiga não ativa
    if len(sessions) > 100:
        # remove a mais antiga por created (exceto ativa)
        oldest = sorted([(k, v.get('created', 0.0)) for k, v in sessions.items()], key=lambda x: x[1])
        for k, _ in oldest:
            if k != active_sid:
                sessions.pop(k, None)
                break
    # Render tabs bar e conteúdo
    tabs = _render_tabs_bar(sessions, sid)
    bar_style = {**styles['result_card'], **styles['tabs_bar'], 'display': 'flex'}
    return sessions, sid, sid, bar_style, tabs


def _render_tabs_bar(sessions: dict, active_sid: str):
    buttons = []
    for sid, meta in sessions.items():
        t = meta.get('type')
        title = meta.get('title') or ''
        base = dict(styles['tab_button_base'])
        if t == 'query':
            base.update(styles['tab_button_query'])
        else:
            base.update(styles['tab_button_pncp'])
        if sid == active_sid:
            base.update(styles['tab_button_active'])
        btn = html.Div([
            html.Span(title, title=title, style={'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
            html.Button('x', id={'type': 'tab-close', 'sid': sid}, style=styles['tab_close_btn'])
        ], id={'type': 'tab-btn', 'sid': sid}, n_clicks=0, style=base)
        buttons.append(btn)
    return buttons

def _render_tabs_contents(sessions: dict, active_sid: str):
    # Nesta versão, usamos um conteúdo compartilhado; retornamos vazio e controlamos visibilidade com 'tab-content'
    return []


@app.callback(
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('tabs-bar', 'children', allow_duplicate=True),
    Input({'type': 'tab-btn', 'sid': ALL}, 'n_clicks'),
    State('store-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def activate_tab(n_clicks_list, sessions, active_sid):
    if not n_clicks_list:
        raise PreventUpdate
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    try:
        id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        import json as _json
        btn_id = _json.loads(id_str)
    except Exception:
        raise PreventUpdate
    sid = btn_id.get('sid')
    if not sid or sid not in (sessions or {}):
        raise PreventUpdate
    return sid, _render_tabs_bar(sessions, sid)


@app.callback(
    Output('store-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('tabs-bar', 'children', allow_duplicate=True),
    Input({'type': 'tab-close', 'sid': ALL}, 'n_clicks'),
    State('store-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def close_tab(n_clicks_list, sessions, active_sid):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    ctx = callback_context
    try:
        id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        import json as _json
        t = _json.loads(id_str)
        sid_to_close = t.get('sid')
    except Exception:
        raise PreventUpdate
    sessions = dict(sessions or {})
    if sid_to_close not in sessions:
        raise PreventUpdate
    sessions.pop(sid_to_close, None)
    new_active = active_sid
    if not sessions:
        # Sem abas
        return {}, None, []
    if sid_to_close == active_sid:
        # escolhe a mais recente
        new_active = sorted([(k, v.get('created', 0.0)) for k, v in sessions.items()], key=lambda x: x[1])[-1][0]
    return sessions, new_active, _render_tabs_bar(sessions, new_active)

@app.callback(
    Output('history-list', 'children'),
    Input('store-history', 'data')
)
def render_history_list(history):
    items = history or []
    if not items:
        return html.Div('Sem consultas ainda.', style=styles['muted_text'])
    # Render as buttons
    buttons = []
    for i, q in enumerate(items):
        buttons.append(
            html.Div([
                html.Button(
                    q,
                    id={'type': 'history-item', 'index': i},
                    title=q,
                    style=styles['history_item_button']
                ),
                html.Button(
                    html.I(className='fas fa-trash'),
                    id={'type': 'history-delete', 'index': i},
                    title='Apagar esta consulta',
                    style=styles['history_delete_btn'],
                    className='delete-btn'
                )
            ], className='history-item-row', style=styles['history_item_row'])
        )
    return html.Div(buttons, style=styles['column'])
@app.callback(
    Output('status-bar', 'children'),
    Output('categories-table', 'children'),
    Input('store-meta', 'data'),
    Input('store-categories', 'data'),
    State('store-last-query', 'data'),
    prevent_initial_call=True,
)
def render_status_and_categories(meta, categories, last_query):
    if not meta:
        # hide both when no meta
        return dash.no_update, dash.no_update
    status = [
        html.Div([
            html.Span('Busca: ', style={'fontWeight': 'bold'}),
            html.Span(last_query or '')
        ], style={'marginTop': '6px'}),
        html.Div([
            html.Span(f"Tipo: {SEARCH_TYPES.get(meta.get('search'),{}).get('name','')}") ,
            html.Span(" | "),
            html.Span(f"Abordagem: {SEARCH_APPROACHES.get(meta.get('approach'),{}).get('name','')}") ,
            html.Span(" | "),
            html.Span(f"Relevância: {RELEVANCE_LEVELS.get(meta.get('relevance'),{}).get('name','')}") ,
            html.Span(" | "),
            html.Span(f"Ordenação: {SORT_MODES.get(meta.get('order'),{}).get('name','')}")
        ], style={'color': '#555', 'marginTop': '6px'}),
        html.Div([
            html.Span(f"Máx Resultados: {meta.get('max_results', '')}"),
            html.Span(" | "),
            html.Span(f"Categorias: {meta.get('top_categories', '')}"),
            html.Span(" | "),
            html.Span(f"Filtrar Data Encerradas: {'ON' if meta.get('filter_expired') else 'OFF'}"),
        ], style={'color': '#555', 'marginTop': '6px'})
    ]

    cats_elem = []
    if categories:
        data = [
            {
                'Rank': c.get('rank'),
                'Código': c.get('codigo'),
                'Similaridade': round(c.get('similarity_score', 0), 4),
                'Descrição': c.get('descricao', ''),
            }
            for c in categories
        ]
        cols = [{'name': k, 'id': k} for k in ['Rank', 'Código', 'Similaridade', 'Descrição']]
        cats_elem = [
            html.Div('Categorias', style=styles['card_title']),
            dash_table.DataTable(
                data=data,
                columns=cols,
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'fontSize': '12px', 'padding': '6px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'fontSize': '13px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}],
                css=[{'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 'rule': 'font-size: 11px !important;'}]
            )
        ]
    return status, cats_elem


# Tabela de resultados (resumo)
@app.callback(
    Output('results-table-inner', 'children'),
    Input('store-results-sorted', 'data'),
    Input('store-sort', 'data'),
    prevent_initial_call=True,
)
def render_results_table(results, sort_state):
    if not results:
        return html.Div("Nenhum resultado encontrado", style={'color': '#555'})
    data = []
    for r in results:
        d = r.get('details', {}) or {}
        unidade = d.get('orgaoentidade_razaosocial') or d.get('orgaoEntidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/A'
        municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or d.get('municipioentidade') or 'N/A'
        uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or d.get('uf') or ''
        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or d.get('valorfinal') or d.get('valorFinal') or 0)
        raw_enc = d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento') or d.get('dataassinatura') or d.get('dataAssinatura') or 'N/A'
        data_enc = _format_br_date(raw_enc)
        enc_status, _enc_color = _enc_status_and_color(raw_enc)
        data.append({
            'Rank': r.get('rank'),
            'Órgão': unidade,
            'Município': municipio,
            'UF': uf,
            'Similaridade': round(r.get('similarity', 0), 4),
            'Valor (R$)': valor,
            'Data Encerramento': str(data_enc),
            'EncStatus': enc_status,
        })
    cols = [{'name': k, 'id': k} for k in ['Rank', 'Órgão', 'Município', 'UF', 'Similaridade', 'Valor (R$)', 'Data Encerramento']]
    # Map current sort state to DataTable sort_by
    st = sort_state or {'field': 'similaridade', 'direction': 'desc'}
    field_to_col = {
        'orgao': 'Órgão',
        'municipio': 'Município',
        'uf': 'UF',
        'similaridade': 'Similaridade',
        'valor': 'Valor (R$)',
        'data': 'Data Encerramento',
    }
    sort_by = []
    if st.get('field') in field_to_col:
        sort_by = [{'column_id': field_to_col[st['field']], 'direction': st.get('direction', 'asc')}]
    # Active header highlight (laranja) for current sorted column
    active_col = field_to_col.get(st.get('field')) if st else None
    header_cond = []
    if active_col:
        header_cond.append({
            'if': {'column_id': active_col},
            'backgroundColor': '#FFE6DB',  # light orange highlight
            'color': '#FF5722',
            'fontWeight': 'bold'
        })
    return dash_table.DataTable(
        id='results-dt',
        data=data,
        columns=cols,
        sort_action='custom',
        sort_by=sort_by,
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'fontSize': '12px', 'padding': '6px', 'maxWidth': '140px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'fontSize': '13px'},
        style_header_conditional=header_cond,
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'},
            {'if': {'filter_query': '{EncStatus} = "na"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_NA},
            {'if': {'filter_query': '{EncStatus} = "expired"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_EXPIRED},
            {'if': {'filter_query': '{EncStatus} = "lt3"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_LT3},
            {'if': {'filter_query': '{EncStatus} = "lt7"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_LT7},
            {'if': {'filter_query': '{EncStatus} = "lt15"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_LT15},
            {'if': {'filter_query': '{EncStatus} = "lt30"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_LT30},
            {'if': {'filter_query': '{EncStatus} = "gt30"', 'column_id': 'Data Encerramento'}, 'color': COLOR_ENC_GT30},
        ],
        css=[{'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 'rule': 'font-size: 11px !important;'}]
    )


## Detalhes por resultado (cards)
@app.callback(
    Output('results-details', 'children'),
    Input('store-results-sorted', 'data'),
    Input('store-last-query', 'data'),
    prevent_initial_call=True,
)
def render_details(results, last_query):
    if not results:
        # Debug: sem resultados
        try:
            from gvg_search_core import SQL_DEBUG
            if SQL_DEBUG:
                print("[GSB][render_details] Nenhum resultado para renderizar.")
        except Exception:
            pass
        return []

    cards = []
    # Título do painel de detalhes (aparece junto com os cartões)
    cards.append(html.Div('Detalhes', style=styles['card_title']))
    for r in results:
        d = r.get('details', {}) or {}
        descricao_full = d.get('descricaocompleta') or d.get('descricaoCompleta') or d.get('objeto') or ''
         # Desativado o highlight por performance; usar texto puro
        destaque = descricao_full

        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or d.get('valorfinal') or d.get('valorFinal') or 0)
        data_inc = _format_br_date(d.get('datainclusao') or d.get('dataInclusao') or d.get('dataassinatura') or d.get('dataAssinatura'))
        data_ab = _format_br_date(d.get('dataaberturaproposta') or d.get('dataAberturaProposta'))
        raw_en = d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento')
        data_en = _format_br_date(raw_en)
        _enc_status, enc_color = _enc_status_and_color(raw_en)

        orgao = d.get('orgaoentidade_razaosocial') or d.get('orgaoEntidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/A'
        unidade = d.get('unidadeorgao_nomeunidade') or d.get('unidadeOrgao_nomeUnidade') or 'N/A'
        municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or d.get('municipioentidade') or 'N/A'
        uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or d.get('uf') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        link = d.get('linksistemaorigem') or d.get('linkSistemaOrigem')
        pncp_id = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or 'N/A'

        # Truncar texto do link visível, mantendo href original
        link_text = link or 'N/A'
        if link and len(link_text) > 100:
            link_text = link_text[:97] + '...'

        body = html.Div([
            html.Div([
                html.Span('Órgão: ', style={'fontWeight': 'bold'}), html.Span(orgao)
            ]),
            html.Div([
                html.Span('Unidade: ', style={'fontWeight': 'bold'}), html.Span(unidade)
            ]),
            html.Div([
                html.Span('ID PNCP: ', style={'fontWeight': 'bold'}), html.Span(str(pncp_id))
            ]),
            html.Div([
                html.Span('Local: ', style={'fontWeight': 'bold'}), html.Span(local)
            ]),
            html.Div([
                html.Span('Valor: ', style={'fontWeight': 'bold'}), html.Span(valor)
            ]),
            html.Div([
                html.Span('Datas: ', style={'fontWeight': 'bold'}),
                html.Span(f"Abertura: {data_ab} | Encerramento: "),
                html.Span(str(data_en), style={'color': enc_color, 'fontWeight': 'bold'})
            ]),
            html.Div([
                html.Span('Link: ', style={'fontWeight': 'bold'}), html.A(link_text, href=link, target='_blank', style=styles['link_break_all']) if link else html.Span('N/A')
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span('Descrição: ', style={'fontWeight': 'bold'}),
                html.Div(dcc.Markdown(children=destaque))
            ])
        ], style=styles['details_body'])

        # Painel esquerdo (detalhes)
        left_panel = html.Div(body, style=styles['details_left_panel'])

        # Painel direito (Itens/Documento/Resumo)
        right_panel = html.Div([
            # Botões dentro do painel direito (canto superior direito do painel)
            html.Div([
                html.Button('Itens', id={'type': 'itens-btn', 'pncp': str(pncp_id)}, title='Itens', style=styles['btn_pill']),
                html.Button('Documentos', id={'type': 'docs-btn', 'pncp': str(pncp_id)}, title='Documentos', style=styles['btn_pill']),
                html.Button('Resumo', id={'type': 'resumo-btn', 'pncp': str(pncp_id)}, title='Resumo', style=styles['btn_pill']),
            ], style=styles['right_panel_actions']),
            # Wrapper fixo com 3 painéis sobrepostos (somente um visível)
            html.Div(
                id={'type': 'panel-wrapper', 'pncp': str(pncp_id)},
                children=[
                    html.Div(
                        id={'type': 'itens-card', 'pncp': str(pncp_id)},
                        children=[],
                        style=styles['details_content_base']
                    ),
                    html.Div(
                        id={'type': 'docs-card', 'pncp': str(pncp_id)},
                        children=[],
                        style=styles['details_content_base']
                    ),
                    html.Div(
                        id={'type': 'resumo-card', 'pncp': str(pncp_id)},
                        children=[],
                        style=styles['details_content_base']
                    ),
                ],
                style=styles['panel_wrapper']
            )
        ], style=styles['details_right_panel'])

        # Card final com duas colunas (detalhes 60% / itens 40%)
        _card_style = dict(styles['result_card'])
        _card_style['marginBottom'] = '6px'  # reduzir espaço vertical entre cards (apenas nos cards de detalhe)
        # Debug por card
        try:
            from gvg_search_core import SQL_DEBUG
            #if SQL_DEBUG:
            #    print(f"[GSB][render_details] Card rank={r.get('rank')} pncp={pncp_id} pronto.")
        except Exception:
            pass
        # Botão bookmark ao lado do número do card
        bookmark_btn = html.Button(
            html.I(className="far fa-bookmark"),
            id={'type': 'bookmark-btn', 'pncp': str(pncp_id)},
            title='Salvar/Remover favorito',
            style=styles['bookmark_btn']
        )
        cards.append(html.Div([
            html.Div([
                left_panel,
                right_panel
            ], style={'display': 'flex', 'gap': '10px', 'alignItems': 'stretch'}),
            html.Div(str(r.get('rank')), style=styles['result_number']),
            bookmark_btn
        ], style=_card_style))
    return cards


# Sync sorted results with sort state and base results
@app.callback(
    Output('store-results-sorted', 'data'),
    Input('store-results', 'data'),
    Input('store-sort', 'data'),
    prevent_initial_call=True,
)
def compute_sorted_results(results, sort_state):
    try:
        return _sorted_for_ui(results or [], sort_state or {'field': 'similaridade', 'direction': 'desc'})
    except Exception:
        return results or []


# Initialize default sort based on meta order when a search completes
@app.callback(
    Output('store-sort', 'data'),
    Input('store-meta', 'data'),
    prevent_initial_call=True,
)
def init_sort_from_meta(meta):
    if not meta:
        raise PreventUpdate
    order = meta.get('order', 1)
    if order == 1:
        return {'field': 'similaridade', 'direction': 'desc'}
    if order == 2:
        # keep ascending to show mais próximo ao início (compatível com _sort_results)
        return {'field': 'data', 'direction': 'asc'}
    if order == 3:
        return {'field': 'valor', 'direction': 'desc'}
    return {'field': 'similaridade', 'direction': 'desc'}


@app.callback(
    Output('store-sort', 'data', allow_duplicate=True),
    Input('results-dt', 'sort_by'),
    State('store-sort', 'data'),
    prevent_initial_call=True,
)
def on_header_sort(sort_by, curr):
    # sort_by is a list like [{'column_id': 'Órgão', 'direction': 'asc'}]
    if not sort_by:
        raise PreventUpdate
    sb = sort_by[0]
    col = sb.get('column_id')
    dir_ = sb.get('direction') or 'asc'
    col_to_field = {
        'Órgão': 'orgao',
        'Município': 'municipio',
        'UF': 'uf',
        'Similaridade': 'similaridade',
        'Valor (R$)': 'valor',
        'Data Encerramento': 'data',
    }
    fld = col_to_field.get(col)
    if not fld:
        raise PreventUpdate
    new_state = {'field': fld, 'direction': dir_}
    curr = curr or {}
    if curr.get('field') == new_state['field'] and curr.get('direction') == new_state['direction']:
        raise PreventUpdate
    return new_state


@app.callback(
    Output({'type': 'itens-card', 'pncp': ALL}, 'children'),
    Output({'type': 'itens-card', 'pncp': ALL}, 'style'),
    Output({'type': 'itens-btn', 'pncp': ALL}, 'style'),
    Output('store-cache-itens', 'data', allow_duplicate=True),
    Input({'type': 'itens-btn', 'pncp': ALL}, 'n_clicks'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    State('store-cache-itens', 'data'),
    prevent_initial_call=True,
)
def load_itens_for_cards(n_clicks_list, active_map, results, cache_itens):
    from gvg_search_core import fetch_itens_contratacao
    children_out, style_out, btn_styles = [], [], []
    updated_cache = dict(cache_itens or {})
    if not results or not isinstance(n_clicks_list, list):
        return children_out, style_out, btn_styles, updated_cache
    # Build pncp id list aligned with components order
    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    count = min(len(pncp_ids), len(n_clicks_list))
    for i in range(count):
        pid = pncp_ids[i]
        clicks = n_clicks_list[i] or 0
        # Ativo se mapa marcar 'itens' para esse pncp
        is_open = (str(pid) in (active_map or {}) and (active_map or {}).get(str(pid)) == 'itens')

        # Button style toggle
        normal_btn_style = styles['btn_pill']
        inverted_btn_style = styles['btn_pill_inverted']
        btn_styles.append(inverted_btn_style if is_open else normal_btn_style)

        st = {
            'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
            'display': 'block' if is_open else 'none', 'overflowY': 'auto',
            'boxSizing': 'border-box'
        }
        style_out.append(st)

        if is_open and pid and pid != 'N/A':
            # Cache: use if available
            itens = None
            try:
                if isinstance(cache_itens, dict) and str(pid) in cache_itens:
                    itens = cache_itens.get(str(pid)) or []
            except Exception:
                itens = None
            if itens is None:
                try:
                    itens = fetch_itens_contratacao(pid, limit=500) or []
                except Exception:
                    itens = []
            rows = []
            total_sum = 0.0
            for idx_it, it in enumerate(itens, start=1):
                desc = (it.get('descricao_item') or it.get('descricao') or it.get('objeto') or '')
                desc = str(desc)
                if len(desc) > 50:
                    desc = desc[:47] + '...'
                qty = it.get('quantidade_item') or it.get('quantidade') or it.get('qtd')
                unit = it.get('valor_unitario_estimado') or it.get('valor_unitario') or it.get('valorUnitario')
                tot = it.get('valor_total_estimado') or it.get('valor_total') or it.get('valorTotal')
                f_qty = _to_float(qty) or 0.0
                f_unit = _to_float(unit) or 0.0
                f_total = _to_float(tot) if _to_float(tot) is not None else (f_qty * f_unit)
                total_sum += (f_total or 0.0)
                rows.append({
                    'Nº': idx_it,
                    'Descrição': desc,
                    'Qtde': _format_qty(f_qty),
                    'Unit (R$)': _format_money(f_unit),
                    'Total (R$)': _format_money(f_total),
                })
            cols = [{'name': k, 'id': k} for k in ['Nº', 'Descrição', 'Qtde', 'Unit (R$)', 'Total (R$)']]
            table = dash_table.DataTable(
                data=rows,
                columns=cols,
                page_action='none',
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'fontSize': '12px', 'padding': '6px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'fontSize': '13px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}],
                css=[{'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 'rule': 'font-size: 11px !important;'}]
            )
            summary = html.Div([
                html.Span('Itens: ', style={'fontWeight': 'bold'}), html.Span(str(len(rows))),
                html.Span('  |  '),
                html.Span('Total: ', style={'fontWeight': 'bold'}), html.Span(_format_money(total_sum)),
            ], style=styles['summary_right'])
            # persist cache
            try:
                updated_cache[str(pid)] = itens
            except Exception:
                pass
            children_out.append([html.Div([table, summary], style=styles['details_content_inner'])])
        else:
            children_out.append([])
    return children_out, style_out, btn_styles, updated_cache

@app.callback(
    Output({'type': 'docs-card', 'pncp': ALL}, 'children'),
    Output({'type': 'docs-card', 'pncp': ALL}, 'style'),
    Output({'type': 'docs-btn', 'pncp': ALL}, 'style'),
    Output('store-cache-docs', 'data', allow_duplicate=True),
    Input({'type': 'docs-btn', 'pncp': ALL}, 'n_clicks'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    State('store-cache-docs', 'data'),
    prevent_initial_call=True,
)
def load_docs_for_cards(n_clicks_list, active_map, results, cache_docs):
    children_out, style_out, btn_styles = [], [], []
    updated_cache = dict(cache_docs or {})
    if not results or not isinstance(n_clicks_list, list):
        return children_out, style_out, btn_styles, updated_cache
    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    count = min(len(pncp_ids), len(n_clicks_list))
    for i in range(count):
        pid = pncp_ids[i]
        clicks = n_clicks_list[i] or 0
        is_open = (str(pid) in (active_map or {}) and (active_map or {}).get(str(pid)) == 'docs')

        normal_btn_style = styles['btn_pill']
        inverted_btn_style = styles['btn_pill_inverted']
        btn_styles.append(inverted_btn_style if is_open else normal_btn_style)

        st = {
            'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
            'display': 'block' if is_open else 'none', 'overflowY': 'auto',
            'boxSizing': 'border-box'
        }
        style_out.append(st)

        if is_open and pid and pid != 'N/A':
            # Cache: use if available
            docs = None
            try:
                if isinstance(cache_docs, dict) and str(pid) in cache_docs:
                    docs = cache_docs.get(str(pid)) or []
            except Exception:
                docs = None
            if docs is None:
                try:
                    docs = fetch_documentos(pid) or []
                except Exception:
                    docs = []
            rows = []
            for idx_doc, doc in enumerate(docs, start=1):
                nome = doc.get('nome') or doc.get('titulo') or 'Documento'
                url = doc.get('url') or doc.get('uri') or ''
                # Render as markdown link [nome](url)
                safe_nome = str(nome).replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                doc_markdown = f"[{safe_nome}]({url})" if url else safe_nome
                rows.append({
                    'Nº': idx_doc,
                    'Documento': doc_markdown,
                })
            cols = [
                {'name': 'Nº', 'id': 'Nº'},
                {'name': 'Documento', 'id': 'Documento', 'presentation': 'markdown'},
            ]
            table = dash_table.DataTable(
                data=rows,
                columns=cols,
                page_action='none',
                markdown_options={'link_target': '_blank'},
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'fontSize': '12px', 'padding': '6px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'fontSize': '13px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}],
                css=[{'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 'rule': 'font-size: 11px !important;'}]
            )
            try:
                updated_cache[str(pid)] = docs
            except Exception:
                pass
            children_out.append([html.Div([table], style=styles['details_content_inner'])])
        else:
            children_out.append([])
    return children_out, style_out, btn_styles, updated_cache

@app.callback(
    Output({'type': 'resumo-card', 'pncp': ALL}, 'children', allow_duplicate=True),
    Output({'type': 'resumo-card', 'pncp': ALL}, 'style', allow_duplicate=True),
    Output({'type': 'resumo-btn', 'pncp': ALL}, 'style', allow_duplicate=True),
    Output('store-cache-resumo', 'data', allow_duplicate=True),
    Input({'type': 'resumo-btn', 'pncp': ALL}, 'n_clicks'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    State('store-cache-resumo', 'data'),
    prevent_initial_call=True,
)
def load_resumo_for_cards(n_clicks_list, active_map, results, cache_resumo):
    """Generate and display a summary for the main document of each process.

    Heuristic: prefer PDFs matching common names (edital, termo de referencia/TR, projeto basico,
    anexo i, pregão/pe/concorrência/dispensa); else first PDF; else first document.
    """
    # Usar funções do pipeline de documentos do módulo gvg_documents (já importadas no topo)
    # DOCUMENTS_AVAILABLE é definido no início deste arquivo, com base nas imports de summarize_document/process_pncp_document
    children_out, style_out, btn_styles = [], [], []
    # Debug início do callback

    updated_cache = dict(cache_resumo or {})
    if not results or not isinstance(n_clicks_list, list):
        return children_out, style_out, btn_styles, updated_cache

    # Helper to pick main doc
    def pick_main_doc(docs: list) -> dict | None:
        if not docs:
            return None
        # Normalize and score by keywords
        keywords = [
            r"edital",
            r"termo\s+de\s+refer(ê|e)ncia|termo\s+de\s+referencia|\bTR\b",
            r"projeto\s+b(á|a)sico|projeto\s+basico",
            r"anexo\s*i\b",
            r"preg(ã|a)o|\bpe\b|concorr(ê|e)ncia|dispensa",
        ]
        def is_pdf(name: str) -> bool:
            return name.lower().endswith('.pdf') if name else False
        # First pass: keyword + pdf
        for kw in keywords:
            rx = re.compile(kw, flags=re.IGNORECASE)
            for d in docs:
                nome = str(d.get('nome') or d.get('titulo') or '')
                url = str(d.get('url') or d.get('uri') or '')
                if (nome and rx.search(nome)) or (url and rx.search(url)):
                    # Prefer pdf
                    if is_pdf(nome) or is_pdf(url):
                        return d
        # Second pass: first pdf
        for d in docs:
            nome = str(d.get('nome') or d.get('titulo') or '')
            url = str(d.get('url') or d.get('uri') or '')
            if is_pdf(nome) or is_pdf(url):
                return d
        # Fallback: first
        return docs[0]

    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')

    count = min(len(pncp_ids), len(n_clicks_list))
    for i in range(count):
        pid = pncp_ids[i]
        clicks = n_clicks_list[i] or 0
        is_open = (str(pid) in (active_map or {}) and (active_map or {}).get(str(pid)) == 'resumo')
        try:
            from gvg_search_core import SQL_DEBUG
            #if SQL_DEBUG:
            #    print(f"[GSB][RESUMO] index={i} pncp={pid} clicks={clicks} -> {'abrir' if is_open else 'fechar'}")
        except Exception:
            pass

        normal_btn_style = styles['btn_pill']
        inverted_btn_style = styles['btn_pill_inverted']
        btn_styles.append(inverted_btn_style if is_open else normal_btn_style)

        st = {
            'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
            'display': 'block' if is_open else 'none', 'overflowY': 'auto',
            'boxSizing': 'border-box'
        }
        style_out.append(st)

        if is_open and pid and pid != 'N/A':
            try:
                # Cache documentos para escolher principal rapidamente
                docs = None
                if isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'docs' in cache_resumo[str(pid)]:
                    docs = cache_resumo[str(pid)]['docs'] or []
                if docs is None:
                    docs = fetch_documentos(pid) or []
            except Exception:
                docs = []
            # Se já existe summary no cache, evita recomputar e mostra direto
            try:
                if isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'summary' in cache_resumo[str(pid)]:
                    cached_summary = cache_resumo[str(pid)]['summary']
                    children_out.append([html.Div(dcc.Markdown(children=cached_summary, className='markdown-summary'), style=styles['details_content_inner'])])
                    style_out[-1] = {**style_out[-1], 'display': 'block'}
                    btn_styles[-1] = inverted_btn_style
                    continue
            except Exception:
                pass
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    print(f"[GSB][RESUMO] pncp={pid} documentos_encontrados={len(docs)}")
            except Exception:
                pass
            if not docs:
                children_out.append(html.Div('Nenhum documento encontrado para este processo.', style=styles['details_content_inner']))
                style_out[-1] = {**style_out[-1], 'display': 'block'}
                btn_styles[-1] = inverted_btn_style
                continue

            main_doc = pick_main_doc(docs)
            if not main_doc:
                children_out.append(html.Div('Nenhum documento disponível para resumo.', style=styles['details_content_inner']))
                style_out[-1] = {**style_out[-1], 'display': 'block'}
                btn_styles[-1] = inverted_btn_style
                continue

            nome = main_doc.get('nome') or main_doc.get('titulo') or 'Documento'
            url = main_doc.get('url') or main_doc.get('uri') or ''
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    short = (url[:80] + '...') if len(url) > 80 else url
                    print(f"[GSB][RESUMO] Documento escolhido: nome='{nome}' url='{short}'")
            except Exception:
                pass
            pncp_data = {}
            # Build pncp_data from matching result
            try:
                d = (results[i] or {}).get('details', {}) or {}
                pncp_data = _build_pncp_data(d)
            except Exception:
                pncp_data = {}

            # Call summarizer (prefer summarize_document) with cache
            summary_text = None
            try:
                if isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'summary' in cache_resumo[str(pid)]:
                    summary_text = cache_resumo[str(pid)]['summary']
            except Exception:
                summary_text = None
            # Enquanto processa, mostre spinner centralizado
            children_out.append([
                html.Div(
                    html.Div(
                        html.I(className="fas fa-spinner fa-spin", style={'color': '#FF5722', 'fontSize': '24px'}),
                        style=styles['details_spinner_center']
                    ),
                    style={**styles['details_content_inner'], 'height': '100%'}
                )
            ])

            if DOCUMENTS_AVAILABLE:
                try:
                    if summarize_document:
                        try:
                            from gvg_search_core import SQL_DEBUG
                            if SQL_DEBUG:
                                print("[GSB][RESUMO] Gerando resumo via summarize_document...")
                        except Exception:
                            pass
                        summary_text = summarize_document(url, max_tokens=500, document_name=nome, pncp_data=pncp_data)
                    elif process_pncp_document:
                        try:
                            from gvg_search_core import SQL_DEBUG
                            if SQL_DEBUG:
                                print("[GSB][RESUMO] Gerando resumo via process_pncp_document (fallback)...")
                        except Exception:
                            pass
                        summary_text = process_pncp_document(url, max_tokens=500, document_name=nome, pncp_data=pncp_data)
                except Exception as e:
                    summary_text = f"Erro ao gerar resumo: {e}"
            else:
                summary_text = 'Pipeline de documentos não está disponível neste ambiente.'

            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG and summary_text is not None:
                    sz = len(summary_text) if isinstance(summary_text, str) else 'N/A'
                    print(f"[GSB][RESUMO] Resumo gerado (chars={sz})")
            except Exception:
                pass

            if not summary_text:
                summary_text = 'Não foi possível gerar o resumo.'

            try:
                updated_cache[str(pid)] = {'docs': docs, 'summary': summary_text}
            except Exception:
                pass
            # Substitui o spinner pelo conteúdo final (resumo)
            children_out[-1] = [html.Div(dcc.Markdown(children=summary_text, className='markdown-summary'), style=styles['details_content_inner'])]
        else:
            children_out.append([])
    return children_out, style_out, btn_styles, updated_cache

# Callback rápido para exibir spinner imediatamente ao ativar o painel de Resumo
@app.callback(
    Output({'type': 'resumo-card', 'pncp': ALL}, 'children', allow_duplicate=True),
    Output({'type': 'resumo-card', 'pncp': ALL}, 'style', allow_duplicate=True),
    Output({'type': 'resumo-btn', 'pncp': ALL}, 'style', allow_duplicate=True),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    State('store-cache-resumo', 'data'),
    prevent_initial_call=True,
)
def show_resumo_spinner_when_active(active_map, results, cache_resumo):
    children_out, style_out, btn_styles = [], [], []
    if not results:
        return children_out, style_out, btn_styles
    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    for pid in pncp_ids:
        is_open = (str(pid) in (active_map or {}) and (active_map or {}).get(str(pid)) == 'resumo')
        st = {
            'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
            'display': 'block' if is_open else 'none', 'overflowY': 'auto',
            'boxSizing': 'border-box'
        }
        style_out.append(st)
        if is_open:
            # Se houver resumo em cache, mostra direto o conteúdo
            cached = None
            try:
                if isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict):
                    cached = cache_resumo[str(pid)].get('summary')
            except Exception:
                cached = None
            if cached:
                children_out.append([html.Div(dcc.Markdown(children=cached, className='markdown-summary'), style=styles['details_content_inner'])])
                btn_styles.append(styles['btn_pill_inverted'])
            else:
                spinner = html.Div(
                    html.Div(
                        html.I(className="fas fa-spinner fa-spin", style={'color': '#FF5722', 'fontSize': '24px'}),
                        style=styles['details_spinner_center']
                    ),
                    style={**styles['details_content_inner'], 'height': '100%'}
                )
                children_out.append([spinner])
                btn_styles.append(styles['btn_pill_inverted'])
        else:
            children_out.append([])
            btn_styles.append(styles['btn_pill'])
    return children_out, style_out, btn_styles

# Define painel ativo por PNCP ao clicar em qualquer botão (sem toggle de fechamento)
@app.callback(
    Output('store-panel-active', 'data', allow_duplicate=True),
    Input({'type': 'itens-btn', 'pncp': ALL}, 'n_clicks'),
    Input({'type': 'docs-btn', 'pncp': ALL}, 'n_clicks'),
    Input({'type': 'resumo-btn', 'pncp': ALL}, 'n_clicks'),
    State('store-results-sorted', 'data'),
    State('store-panel-active', 'data'),
    prevent_initial_call=True,
)
def set_active_panel(it_clicks, dc_clicks, rs_clicks, results, active_map):
    active_map = dict(active_map or {})
    if not results:
        raise PreventUpdate
    # Determine which pncp/index fired
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig = ctx.triggered[0]['prop_id']
    # id is like {"type":"itens-btn","pncp":"..."}.n_clicks
    try:
        import json as _json
        id_str = trig.split('.')[0]
        trg_id = _json.loads(id_str)
    except Exception:
        raise PreventUpdate
    pncp = str(trg_id.get('pncp'))
    t = trg_id.get('type')
    # Toggle: if clicking the same active tab, remove selection
    current = active_map.get(pncp)
    if t == 'itens-btn':
        active_map[pncp] = None if current == 'itens' else 'itens'
    elif t == 'docs-btn':
        active_map[pncp] = None if current == 'docs' else 'docs'
    elif t == 'resumo-btn':
        active_map[pncp] = None if current == 'resumo' else 'resumo'
    # Clean None to avoid truthy checks
    if active_map.get(pncp) is None:
        active_map.pop(pncp, None)
    return active_map

# Atualiza ícones (seta para cima/baixo) após o texto dos botões conforme toggle
@app.callback(
    Output({'type': 'itens-btn', 'pncp': ALL}, 'children'),
    Output({'type': 'docs-btn', 'pncp': ALL}, 'children'),
    Output({'type': 'resumo-btn', 'pncp': ALL}, 'children'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    prevent_initial_call=True,
)
def update_button_icons(active_map, results):
    itens_children, docs_children, resumo_children = [], [], []
    pncp_ids = []
    for r in (results or []):
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    for pid in pncp_ids:
        active = (active_map or {}).get(str(pid))
        def btn(label, is_active):
            icon = html.I(className=("fas fa-chevron-up" if is_active else "fas fa-chevron-down"), style={'marginLeft': '6px'})
            return [label, icon]
        itens_children.append(btn('Itens', active == 'itens'))
        docs_children.append(btn('Documentos', active == 'docs'))
        resumo_children.append(btn('Resumo', active == 'resumo'))
    return itens_children, docs_children, resumo_children

# Mostrar wrapper apenas se alguma aba ativa existir para o PNCP correspondente
@app.callback(
    Output({'type': 'panel-wrapper', 'pncp': ALL}, 'style'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    prevent_initial_call=True,
)
def toggle_panel_wrapper(active_map, results):
    styles_out = []
    pncp_ids = []
    for r in (results or []):
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    for pid in pncp_ids:
        base = {
            'marginTop': '50px', 'backgroundColor': '#FFFFFF', 'border': '1px solid transparent',
            'borderRadius': '12px', 'padding': '10px',
            'flex': '1 1 auto', 'minHeight': '0', 'position': 'relative', 'display': 'none'
        }
        if str(pid) in (active_map or {}):
            base['display'] = 'block'
            base['border'] = '1px solid #FF5722'
        styles_out.append(base)
    return styles_out

## Visibilidade dos painéis de resultado
@app.callback(
    Output('status-bar', 'style'),
    Output('categories-table', 'style'),
    Output('export-panel', 'style'),
    Output('results-table', 'style'),
    Output('results-details', 'style'),
    Input('store-meta', 'data'),
    Input('store-results', 'data'),
    Input('store-categories', 'data'),
    prevent_initial_call=True,
)
def toggle_results_visibility(meta, results, categories):
    base = styles['result_card'].copy()
    hidden = {**base, 'display': 'none'}
    show = base
    status_style = show if meta else hidden
    cats_style = show if categories else hidden
    show_results = bool(results)
    export_style = show if show_results else hidden
    table_style = show if show_results else hidden
    details_style = show if show_results else hidden
    return status_style, cats_style, export_style, table_style, details_style


# ==========================
# Render dentro da aba ativa (consulta)
# ==========================
@app.callback(
    Output({'type': 'status-bar', 'sid': MATCH}, 'children'),
    Output({'type': 'categories-table', 'sid': MATCH}, 'children'),
    Output({'type': 'export-panel', 'sid': MATCH}, 'style'),
    Output({'type': 'results-table', 'sid': MATCH}, 'style'),
    Output({'type': 'results-details', 'sid': MATCH}, 'style'),
    Input('store-meta', 'data'),
    Input('store-categories', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def reflect_active_tab_visibility(meta, categories, active_sid):
    # Mostra controles apenas dentro da aba ativa
    base = styles['result_card'].copy(); hidden = {**base, 'display': 'none'}; show = base
    if not meta:
        return dash.no_update, dash.no_update, hidden, hidden, hidden
    cats_children = dash.no_update
    if categories:
        cats_children = dash.no_update  # já renderizado no callback de status acima
    show_results = meta.get('count', 0) > 0
    return dash.no_update, cats_children, (show if show_results else hidden), (show if show_results else hidden), (show if show_results else hidden)


"""
Tabs/Session wiring:
- Show tabs bar when sessions exist
- Switch query-panel vs pncp-panel based on active session type
- Render PNCP card inside pncp-panel using session details
- Show center spinner only when processing and the active session is the one processing
- Persist search outputs per session and restore when switching tabs
"""
@app.callback(
    Output('tabs-bar', 'style'),
    Output('tab-content', 'style'),
    Input('store-sessions', 'data')
)
def toggle_tabs_bar(sessions):
    if sessions:
        return {**styles['result_card'], **styles['tabs_bar'], 'display': 'flex'}, {'display': 'block', 'backgroundColor': 'transparent'}
    return {**styles['result_card'], **styles['tabs_bar'], 'display': 'none'}, {'display': 'none'}


# Conteúdo de tabs: seleção da aba ativa (mostra apenas a ativa)
@app.callback(
    Output('gvg-center-spinner', 'style', allow_duplicate=True),
    Input('processing-state', 'data'),
    State('store-active-session', 'data'),
    State('store-processing-session', 'data'),
    prevent_initial_call=True,
)
def show_spinner_in_active_tab(is_processing, active_sid, processing_sid):
    # Show only if processing and the active tab is the one processing
    if is_processing and active_sid and processing_sid and active_sid == processing_sid:
        return {'display': 'block'}
    return {'display': 'none'}


# Switch content panels based on active session
@app.callback(
    Output('query-panel', 'style'),
    Output('pncp-panel', 'style'),
    Output('pncp-panel', 'children', allow_duplicate=True),
    Input('store-active-session', 'data'),
    State('store-sessions', 'data'),
    prevent_initial_call=True,
)
def switch_active_tab_content(active_sid, sessions):
    sessions = sessions or {}
    if not active_sid or active_sid not in sessions:
        return {'display': 'none'}, {'display': 'none'}, dash.no_update
    meta = sessions.get(active_sid) or {}
    if meta.get('type') == 'pncp':
        # Render PNCP card
        details = meta.get('details') or {}
        pncp_id = meta.get('pncp_id') or ''
        return {'display': 'none'}, {'display': 'block'}, _render_pncp_tab_content(active_sid, pncp_id, details)
    # query tab
    return {'display': 'block'}, {'display': 'none'}, dash.no_update


# Persist results data per session on search completion and restore when switching tabs
@app.callback(
    Output('store-session-data', 'data', allow_duplicate=True),
    Output('store-processing-session', 'data', allow_duplicate=True),
    Input('store-results', 'data'),
    Input('store-categories', 'data'),
    Input('store-meta', 'data'),
    State('store-active-session', 'data'),
    State('store-session-data', 'data'),
    prevent_initial_call=True,
)
def persist_data_to_session(results, categories, meta, active_sid, session_data):
    session_data = dict(session_data or {})
    if not active_sid:
        raise PreventUpdate
    # On first results/meta after starting a search, persist into the active session
    data = session_data.get(active_sid, {})
    changed = False
    if results is not None:
        data['results'] = results
        changed = True
    if categories is not None:
        data['categories'] = categories
        changed = True
    if meta is not None:
        data['meta'] = meta
        changed = True
    session_data[active_sid] = data
    if changed:
        return session_data, None
    raise PreventUpdate


@app.callback(
    Output('store-results', 'data', allow_duplicate=True),
    Output('store-categories', 'data', allow_duplicate=True),
    Output('store-meta', 'data', allow_duplicate=True),
    Input('store-active-session', 'data'),
    State('store-session-data', 'data'),
    prevent_initial_call=True,
)
def restore_data_when_switching_tabs(active_sid, session_data):
    # When switching to a query tab, restore its data into the shared stores
    data = (session_data or {}).get(active_sid) or {}
    if not data:
        raise PreventUpdate
    return data.get('results', []), data.get('categories', []), data.get('meta', {})


# Atualiza histórico quando uma busca termina com sucesso
@app.callback(
    Output('store-history', 'data', allow_duplicate=True),
    Input('store-meta', 'data'),
    State('store-last-query', 'data'),
    State('store-history', 'data'),
    prevent_initial_call=True,
)
def update_history_on_search(meta, last_query, history):
    if not meta:
        raise PreventUpdate
    q = (last_query or '').strip()
    if not q:
        raise PreventUpdate
    items = list(history or [])
    # Dedup and move to top
    items = [x for x in items if x != q]
    items.insert(0, q)
    save_history(items)
    return items


# Clique no histórico reenvia a consulta
@app.callback(
    Output('query-input', 'value'),
    Output('processing-state', 'data', allow_duplicate=True),
    Output('store-history', 'data', allow_duplicate=True),
    Input({'type': 'history-item', 'index': ALL}, 'n_clicks'),
    State('store-history', 'data'),
    prevent_initial_call=True,
)
def run_from_history(n_clicks_list, history):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    # Find which index clicked
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i
            break
    if idx is None:
        raise PreventUpdate
    items = list(history or [])
    if idx < 0 or idx >= len(items):
        raise PreventUpdate
    q = items[idx]
    # Move clicked to top
    items = [x for x in items if x != q]
    items.insert(0, q)
    save_history(items)
    # Retorno: apenas preencher o campo de consulta; não iniciar busca automaticamente
    return q, dash.no_update, items


# Excluir item do histórico
@app.callback(
    Output('store-history', 'data', allow_duplicate=True),
    Input({'type': 'history-delete', 'index': ALL}, 'n_clicks'),
    State('store-history', 'data'),
    prevent_initial_call=True,
)
def delete_history_item(n_clicks_list, history):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i
            break
    if idx is None:
        raise PreventUpdate
    items = list(history or [])
    if idx < 0 or idx >= len(items):
        raise PreventUpdate
    # Remove selected index (memória + banco)
    to_delete = None
    try:
        to_delete = items[idx]
    except Exception:
        to_delete = None
    if to_delete:
        try:
            delete_prompt(to_delete)
        except Exception:
            pass
    if 0 <= idx < len(items):
        del items[idx]
    save_history(items)
    return items


# ==========================
# Favoritos (UI e callbacks)
# ==========================
@app.callback(
    Output('store-favorites', 'data'),
    Input('store-favorites', 'data'),
    prevent_initial_call=False,
)
def init_favorites(favs):
    # Inicializa a Store de favoritos na primeira renderização (mesmo padrão do histórico)
    if favs:
        return favs
    try:
        return fetch_bookmarks(limit=200)
    except Exception:
        return []

@app.callback(
    Output('store-favorites', 'data', allow_duplicate=True),
    Input('store-meta', 'data'),
    prevent_initial_call=True,
)
def load_favorites_on_results(meta):
    try:
        favs = fetch_bookmarks(limit=200)
        try:
            from gvg_search_core import SQL_DEBUG
            if SQL_DEBUG:
                print(f"[GSB][FAV] load_favorites_on_results: carregados={len(favs)}")
        except Exception:
            pass
        return favs
    except Exception:
        return []



@app.callback(
    Output('store-favorites-open', 'data'),
    Input('favorites-toggle-btn', 'n_clicks'),
    State('store-favorites-open', 'data'),
    prevent_initial_call=True,
)
def toggle_favorites(n_clicks, is_open):
    if not n_clicks:
        raise PreventUpdate
    return not bool(is_open)


@app.callback(
    Output('favorites-collapse', 'is_open'),
    Input('store-favorites-open', 'data')
)
def reflect_favorites_collapse(is_open):
    return bool(is_open)


@app.callback(
    Output('favorites-toggle-btn', 'children'),
    Input('store-favorites-open', 'data')
)
def update_favorites_icon(is_open):
    icon = 'fa-chevron-up' if is_open else 'fa-chevron-down'
    return html.I(className=f"fas {icon}")


@app.callback(
    Output('favorites-list', 'children'),
    Input('store-favorites', 'data')
)
def render_favorites_list(favs):

    items = []
    for i, f in enumerate(favs or []):
        pncp = f.get('numero_controle_pncp') or 'N/A'
        orgao = f.get('orgao_entidade_razao_social') or ''
        mun = f.get('unidade_orgao_municipio_nome') or ''
        uf = f.get('unidade_orgao_uf_sigla') or ''
        local = f"{mun}/{uf}".strip('/') if (mun or uf) else ''
        desc = f.get('objeto_compra') or ''
        if isinstance(desc, str) and len(desc) > 100:
            desc = desc[:100]
        raw_enc = f.get('data_encerramento_proposta')
        enc_txt = _format_br_date(raw_enc)
        _enc_status, enc_color = _enc_status_and_color(raw_enc)
        body = html.Div([
            html.Div(orgao),
            html.Div(local),
            html.Div(desc),
            html.Div(enc_txt, style={'color': enc_color})
        ], style={'textAlign': 'left', 'display': 'flex', 'flexDirection': 'column'})
        row = html.Div([
            # Evitar ocupar 100% da largura para não cobrir a lixeira; usar flex elástico
            html.Button(
                body,
                id={'type': 'favorite-item', 'index': i},
                style={**styles['history_item_button'], 'whiteSpace': 'normal', 'textAlign': 'left', 'width': 'auto', 'flex': '1 1 auto'}
            ),
            html.Button(
                html.I(className='fas fa-trash'),
                id={'type': 'favorite-delete', 'index': i},
                className='delete-btn',
                style=styles['history_delete_btn']
            )
        ], className='history-item-row', style=styles['history_item_row'])
        items.append(row)
    if not items:
        items = [html.Div('Sem favoritos.', style={'color': '#555'})]
    return items


# Clique em bookmark no card: alterna estado e persiste
@app.callback(
    Output({'type': 'bookmark-btn', 'pncp': ALL}, 'children', allow_duplicate=True),
    Output('store-favorites', 'data', allow_duplicate=True),
    Input({'type': 'bookmark-btn', 'pncp': ALL}, 'n_clicks'),
    State('store-results-sorted', 'data'),
    State('store-favorites', 'data'),
    prevent_initial_call=True,
)
def toggle_bookmark(n_clicks_list, results, favs):

    fav_set = {str(x.get('numero_controle_pncp')) for x in (favs or [])}
    pncp_ids = []
    for r in (results or []):
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')

    # Determine if a click occurred and which index
    ctx = callback_context
    clicked_pid = None
    clicked_idx = None
    if ctx and ctx.triggered:
        try:
            id_str = ctx.triggered[0]['prop_id'].split('.')[0]
            import json as _json
            t = _json.loads(id_str)
            clicked_pid = str(t.get('pncp'))
            # localizar índice correspondente ao pncp para checar n_clicks
            for i, pid in enumerate(pncp_ids):
                if str(pid) == clicked_pid:
                    clicked_idx = i
                    break
        except Exception:
            clicked_pid = None
            clicked_idx = None

    # Persist toggle somente em clique real (n_clicks > 0)
    updated_favs = list(favs or [])
    # Se foi disparado pela criação dos componentes (n_clicks None/0), não faz nada
    if clicked_pid and clicked_pid != 'N/A' and clicked_idx is not None and (n_clicks_list[clicked_idx] or 0) > 0:
        if clicked_pid in fav_set:
            try:
                remove_bookmark(clicked_pid)
            except Exception:
                pass
            # Otimista local
            updated_favs = [x for x in updated_favs if str(x.get('numero_controle_pncp')) != clicked_pid]
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    print(f"[GSB][BMK] toggle_bookmark: REMOVE {clicked_pid}")
            except Exception:
                pass
        else:
            try:
                add_bookmark(clicked_pid)
            except Exception:
                pass
            # Otimista local (adiciona no topo) com os mesmos campos exibidos no card de detalhes
            fav_item = {'numero_controle_pncp': clicked_pid}
            try:
                # Obter o resultado correspondente e extrair campos como no card de detalhes
                r = (results or [])[clicked_idx] if clicked_idx is not None else None
                d = (r or {}).get('details', {}) or {}
                orgao = (
                    d.get('orgaoentidade_razaosocial')
                    or d.get('orgaoEntidade_razaosocial')
                    or d.get('nomeorgaoentidade')
                    or ''
                )
                municipio = (
                    d.get('unidadeorgao_municipionome')
                    or d.get('unidadeOrgao_municipioNome')
                    or d.get('municipioentidade')
                    or ''
                )
                uf = (
                    d.get('unidadeorgao_ufsigla')
                    or d.get('unidadeOrgao_ufSigla')
                    or d.get('uf')
                    or ''
                )
                descricao = (
                    d.get('descricaocompleta')
                    or d.get('descricaoCompleta')
                    or d.get('objeto')
                    or ''
                )
                if isinstance(descricao, str) and len(descricao) > 100:
                    descricao = descricao[:100]
                raw_en = (
                    d.get('dataencerramentoproposta')
                    or d.get('dataEncerramentoProposta')
                    or d.get('dataEncerramento')
                )
                data_en = _format_br_date(raw_en)
                fav_item.update({
                    'orgao_entidade_razao_social': orgao,
                    'unidade_orgao_municipio_nome': municipio,
                    'unidade_orgao_uf_sigla': uf,
                    'objeto_compra': descricao,
                    'data_encerramento_proposta': data_en,
                })
            except Exception:
                pass
            updated_favs = ([fav_item] + [x for x in updated_favs if str(x.get('numero_controle_pncp')) != clicked_pid])
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    print(f"[GSB][BMK] toggle_bookmark: ADD {clicked_pid}")
            except Exception:
                pass
        # Sem recarregar do BD aqui: mantemos atualização otimista no UI
    # Ícones imediatos (com base no updated_favs)
    fav_set_after = {str(x.get('numero_controle_pncp')) for x in (updated_favs or [])}
    children_out = []
    for pid in pncp_ids:
        icon_class = 'fas fa-bookmark' if pid in fav_set_after else 'far fa-bookmark'
        children_out.append(html.I(className=icon_class))

    return children_out, updated_favs


@app.callback(
    Output({'type': 'bookmark-btn', 'pncp': ALL}, 'children', allow_duplicate=True),
    Input('store-favorites', 'data'),
    State('store-results-sorted', 'data'),
    prevent_initial_call=True,
)
def sync_bookmark_icons(favs, results):
    fav_set = {str(x.get('numero_controle_pncp')) for x in (favs or [])}
    pncp_ids = []
    for r in (results or []):
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    children_out = []
    for pid in pncp_ids:
        is_fav = pid in fav_set
        icon_class = 'fas fa-bookmark' if is_fav else 'far fa-bookmark'
        children_out.append(html.I(className=icon_class))

    return children_out


# Clique em um favorito: filtra a lista para destacá-lo (por ora, só preenche consulta)
@app.callback(
    Output('query-input', 'value', allow_duplicate=True),
    Input({'type': 'favorite-item', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    prevent_initial_call=True,
)
def select_favorite(n_clicks_list, favs):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i
            break
    if idx is None:
        raise PreventUpdate
    try:
        item = (favs or [])[idx]
    except Exception:
        item = None
    if not item:
        raise PreventUpdate
    pncp = item.get('numero_controle_pncp')
    # Criar uma aba PNCP imediatamente
    raise PreventUpdate


@app.callback(
    Output('store-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('tabs-bar', 'children', allow_duplicate=True),
    Input({'type': 'favorite-item', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    State('store-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def open_pncp_tab_from_favorite(n_clicks_list, favs, sessions, active_sid):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    # discover which index
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i; break
    if idx is None:
        raise PreventUpdate
    item = (favs or [])[idx]
    pncp = item.get('numero_controle_pncp')
    if not pncp:
        raise PreventUpdate
    # Fetch detalhes completos para evitar N/A
    details = fetch_contratacao_by_pncp(pncp) or {}
    sessions = dict(sessions or {})
    import time, uuid
    sid = str(uuid.uuid4())
    title = _session_title_for_pncp(pncp)
    sessions[sid] = {'type': 'pncp', 'title': title, 'created': time.time(), 'pncp_id': pncp, 'details': details}
    # limite 100
    if len(sessions) > 100:
        oldest = sorted([(k, v.get('created', 0.0)) for k, v in sessions.items()], key=lambda x: x[1])
        sessions.pop(oldest[0][0], None)
    tabs = _render_tabs_bar(sessions, sid)
    return sessions, sid, tabs


# Remover um favorito via lista
@app.callback(
    Output('store-favorites', 'data', allow_duplicate=True),
    Input({'type': 'favorite-delete', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    prevent_initial_call=True,
)
def delete_favorite(n_clicks_list, favs):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    # Localiza o primeiro índice clicado (mesma lógica do histórico)
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i
            break
    if idx is None:
        raise PreventUpdate
    # Resolve o PNCP a partir do array atual de favoritos
    try:
        item = (favs or [])[idx]
        pid = str(item.get('numero_controle_pncp')) if item else None
    except Exception:
        pid = None
    if not pid:
        raise PreventUpdate
    # Diagnóstico mínimo sempre visível
    print(f"[GSB][FAV] delete_favorite fired idx={idx} pid={pid}")
    # Remove no BD (best-effort)
    try:
        remove_bookmark(pid)
    except Exception:
        pass
    # Remove da Store localmente
    updated = [x for x in (favs or []) if str(x.get('numero_controle_pncp')) != pid]

    return updated


# Exportações
from types import SimpleNamespace

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Resultados_Busca'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.callback(
    Output('download-out', 'data'),
    Input('export-json', 'n_clicks'),
    Input('export-xlsx', 'n_clicks'),
    Input('export-csv', 'n_clicks'),
    Input('export-pdf', 'n_clicks'),
    Input('export-html', 'n_clicks'),
    State('store-results', 'data'),
    State('store-last-query', 'data'),
    State('store-meta', 'data'),
    prevent_initial_call=True,
)
def export_files(n_json, n_xlsx, n_csv, n_pdf, n_html, results, query, meta):
    if not results:
        raise PreventUpdate
    # Qual botão foi clicado
    if not callback_context.triggered:
        raise PreventUpdate
    btn_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    params = SimpleNamespace(
        search=meta.get('search', 1),
        approach=meta.get('approach', 3),
        relevance=meta.get('relevance', 2),
        order=meta.get('order', 1),
    )
    try:
        if btn_id == 'export-json':
            path = export_results_json(results, query or '', params, OUTPUT_DIR)
        elif btn_id == 'export-xlsx':
            path = export_results_excel(results, query or '', params, OUTPUT_DIR)
        elif btn_id == 'export-csv':
            path = export_results_csv(results, query or '', params, OUTPUT_DIR)
        elif btn_id == 'export-pdf':
            path = export_results_pdf(results, query or '', params, OUTPUT_DIR)
            if not path:
                # ReportLab ausente
                raise PreventUpdate
        elif btn_id == 'export-html':
            path = export_results_html(results, query or '', params, OUTPUT_DIR)
        else:
            raise PreventUpdate
        if path and os.path.exists(path):
            return dcc.send_file(path)
    except Exception:
        pass
    raise PreventUpdate


# Adicionar FontAwesome para ícones (igual Reports)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <style>
            /* CSS importado do módulo gvg_css.py */
            %CSS_ALL%
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
                        <script>
                        // Submit search on Enter when focus is in the textarea; Shift+Enter adds a newline
                        (function() {
                            document.addEventListener('keydown', function(e) {
                                var el = document.activeElement;
                                if (el && el.id === 'query-input' && e.key === 'Enter') {
                                    if (!e.shiftKey) {
                                        e.preventDefault();
                                        var btn = document.getElementById('submit-button');
                                        if (btn && !btn.disabled) {
                                            btn.click();
                                        }
                                    }
                                }
                            }, true);
                        })();
                        </script>
        </footer>
    </body>
</html>
'''.replace('%CSS_ALL%', CSS_ALL)


if __name__ == '__main__':
    # Porta padrão diferente do Reports para evitar conflito
    # Desativar hot-reload para evitar resets durante processamento pesado de documentos
    app.run_server(debug=True, port=8060, dev_tools_hot_reload=False, dev_tools_props_check=False, dev_tools_ui=False)
