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
from dash import html, dcc, dash_table, Input, Output, State, callback_context, ALL
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
)
from gvg_exporters import (
    export_results_json,
    export_results_excel,
    export_results_csv,
    export_results_pdf,
    export_results_html,
)
from gvg_database import fetch_documentos
from gvg_user import (
    get_current_user,
    get_user_initials,
    fetch_prompt_texts,
    add_prompt,
    save_user_results,
    delete_prompt,
)

try:
    from gvg_documents import process_pncp_document
    DOCUMENTS_AVAILABLE = True
except Exception:
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
    2: {"name": "Data (Assinatura)"},
    3: {"name": "Valor (Final)"},
}
RELEVANCE_LEVELS = {
    1: {"name": "Sem filtro"},
    2: {"name": "Flexível"},
    3: {"name": "Restritivo"},
}


# =====================================================================================
# Estilos reutilizados do GvG_SU_Report_v1 (mesmas cores, bordas, tipografia, layout)
# =====================================================================================
styles = {
    'container': {
        'display': 'flex',
        'height': 'calc(100vh - 60px)',
        'width': '100%',
        'marginTop': '60px',
        'padding': '5px',
    },
    'left_panel': {
    'width': '35%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'height': 'calc(100vh - 100px)'
    },
    'right_panel': {
    'width': '65%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
        'height': 'calc(100vh - 100px)'
    },
    # Caixa branca para os controles (acima)
    'controls_group': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'display': 'flex',
        'flexDirection': 'column',
        'gap': '8px',
        'marginTop': '8px',
    },
    # Botões retangulares (exportações)
    'submit_button': {
        'backgroundColor': '#FF5722',
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'height': '36px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer'
    },
    # Container da consulta NL no rodapé esquerdo (igual Reports)
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'alignItems': 'center',
    'marginTop': '10px'
    },
    'input_field': {
        'flex': '1',
        'border': 'none',
        'outline': 'none',
        'padding': '8px',
        'backgroundColor': 'transparent'
    },
    # Botão circular com seta (igual Reports)
    'arrow_button': {
        'backgroundColor': '#FF5722',
        'color': 'white',
        'border': 'none',
        'borderRadius': '50%',
        'width': '32px',
        'height': '32px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer'
    },
    'result_card': {
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'padding': '15px',
        'marginBottom': '12px',
    'outline': '#E0EAF9 solid 1px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
        'position': 'relative'
    },
    'logo': {
        'marginBottom': '20px',
        'maxWidth': '100px'
    },
}

styles['result_number'] = {
    'position': 'absolute',
    'top': '10px',
    'left': '10px',
    'backgroundColor': '#FF5722',
    'color': 'white',
    'borderRadius': '50%',
    'width': '24px',
    'height': '24px',
    'display': 'flex',
    'padding': '5px',
    'alignItems': 'center',
    'justifyContent': 'center',
    'fontSize': '12px',
    'fontWeight': 'bold',
}

# Título padrão para cards (igual ao de "Configurações de Busca")
styles['card_title'] = {'fontWeight': 'bold', 'color': '#003A70'}


# =====================================================================================
# App Dash (com Bootstrap para fontes e ícones FontAwesome)
# =====================================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'GovGo Search'

# Parse argumento --debug (ex: python GvG_Search_Browser.py --debug)
try:
    import argparse
    _parser = argparse.ArgumentParser(add_help=False)
    _parser.add_argument('--debug', action='store_true')
    _known, _ = _parser.parse_known_args()
    if _known and getattr(_known, 'debug', False):
        set_sql_debug(True)
except Exception:
    pass

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
        html.Img(src=LOGO_PATH, style={'height': '40px'}),
        html.H4("GvG Search", style={'marginLeft': '15px', 'color': '#003A70'})
    ], style={'display': 'flex', 'alignItems': 'center'}),
    html.Div([
        html.Div(
            _USER_INITIALS,
            title=f"{_USER.get('name','Usuário')} ({_USER.get('email','')})",
            style={
                'width': '32px', 'height': '32px', 'minWidth': '32px',
                'borderRadius': '50%', 'backgroundColor': '#FF5722',
                'color': 'white', 'fontWeight': 'bold', 'fontSize': '14px',
                'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                'cursor': 'default'
            }
        )
    ], style={'display': 'flex', 'alignItems': 'center'})
], style={
    'display': 'flex',
    'justifyContent': 'space-between',
    'alignItems': 'center',
    'backgroundColor': 'white',
    'padding': '10px 20px',
    'borderBottom': '1px solid #ddd',
    'width': '100%',
    'position': 'fixed',
    'top': 0,
    'zIndex': 1000
})


# Painel de controles (esquerda)
controls_panel = html.Div([
    html.Div([
        html.Div("Configurações de Busca", style={'fontWeight': 'bold', 'color': '#003A70'}),
        html.Button(
            html.I(className="fas fa-chevron-down"),
            id='config-toggle-btn',
            title='Mostrar/ocultar configurações',
            style={**styles['arrow_button'], 'width': '28px', 'height': '28px'}
        ),
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'}),
    dbc.Collapse(
        html.Div([
            html.Div([
                html.Label('Tipo', className='gvg-form-label'),
                dcc.Dropdown(id='search-type', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SEARCH_TYPES.items()], value=1, clearable=False, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Abordagem', className='gvg-form-label'),
                dcc.Dropdown(id='search-approach', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SEARCH_APPROACHES.items()], value=3, clearable=False, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Relevância', className='gvg-form-label'),
                dcc.Dropdown(id='relevance-level', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in RELEVANCE_LEVELS.items()], value=2, clearable=False, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Ordenação', className='gvg-form-label'),
                dcc.Dropdown(id='sort-mode', options=[{'label': f"{k} - {v['name']}", 'value': k} for k, v in SORT_MODES.items()], value=1, clearable=False, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Máx. resultados', className='gvg-form-label'),
                dcc.Input(id='max-results', type='number', min=5, max=1000, value=DEFAULT_MAX_RESULTS, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                html.Label('TOP categorias', className='gvg-form-label'),
                dcc.Input(id='top-categories', type='number', min=5, max=50, value=DEFAULT_TOP_CATEGORIES, style={'width': '100%', 'flex': '1'})
            ], className='gvg-form-row'),
            html.Div([
                dcc.Checklist(id='toggles', options=[
                    {'label': ' Filtrar encerrados', 'value': 'filter_expired'},
                ], value=['filter_expired'])
            ], style={'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap'})
        ], style={**styles['controls_group'], 'position': 'relative'}, className='gvg-controls'),
        id='config-collapse', is_open=True
    ),
    html.Div('Consulta', style={**styles['card_title'], 'marginTop': '8px'}),
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
        html.Div('Histórico', style={'fontWeight': 'bold', 'color': '#003A70'}),
        html.Button(
            html.I(className="fas fa-chevron-down"),
            id='history-toggle-btn',
            title='Mostrar/ocultar histórico',
            style={**styles['arrow_button'], 'width': '28px', 'height': '28px'}
        ),
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '8px'}),
    dbc.Collapse(
        html.Div([
            html.Div(id='history-list')
        ], id='history-card', style=styles['controls_group']),
        id='history-collapse', is_open=True
    )
], style=styles['left_panel'])


# Painel de resultados (direita)
results_panel = html.Div([
    html.Div(id='status-bar', style={**styles['result_card'], 'display': 'none'}),
    html.Div([
        html.Div('Exportar', style=styles['card_title']),
        html.Div([
            html.Button('JSON', id='export-json', style={**styles['submit_button'], 'width': '120px'}),
            html.Button('XLSX', id='export-xlsx', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
            html.Button('CSV', id='export-csv', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
            html.Button('PDF', id='export-pdf', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
            html.Button('HTML', id='export-html', style={**styles['submit_button'], 'width': '120px', 'marginLeft': '6px'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginTop': '8px'})
    ], id='export-panel', style={**styles['result_card'], 'display': 'none'}),
    html.Div(id='categories-table', style={**styles['result_card'], 'display': 'none'}),
    html.Div([
        html.Div('Resultados', style=styles['card_title']),
        html.Div(id='results-table-inner')
    ], id='results-table', style={**styles['result_card'], 'display': 'none'}),
    html.Div(id='results-details')
], style=styles['right_panel'])


# Layout principal
app.layout = html.Div([
    dcc.Store(id='store-results', data=[]),
    dcc.Store(id='store-categories', data=[]),
    dcc.Store(id='store-meta', data={}),
    dcc.Store(id='store-last-query', data=""),
    dcc.Store(id='store-history', data=[]),
    dcc.Store(id='store-history-open', data=True),
    dcc.Store(id='processing-state', data=False),
    dcc.Store(id='store-config-open', data=True),
    dcc.Download(id='download-out'),

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
        return sorted(results, key=lambda x: (x.get('details', {}).get('dataassinatura') or x.get('details', {}).get('dataAssinatura') or ''), reverse=True)
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


def _highlight_terms(text: str, query: str) -> str:
    if not text:
        return ''
    safe = str(text)
    for term in (query or '').split():
        if len(term) <= 2:
            continue
        try:
            safe = re.sub(rf"({re.escape(term)})", r"<mark style='background:#FFE08A'>\1</mark>", safe, flags=re.IGNORECASE)
        except re.error:
            pass
    return safe


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
            if s_type == 1:
                results, confidence = semantic_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
            elif s_type == 2:
                results, confidence = keyword_search(query, limit=safe_limit, filter_expired=filter_expired)
            else:
                results, confidence = hybrid_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
        elif approach == 2:
            if categories:
                results, confidence, _ = categories_correspondence_search(
                    query_text=query,
                    top_categories=categories,
                    limit=safe_limit,
                    filter_expired=filter_expired,
                    console=None,
                )
        elif approach == 3:
            if categories:
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


# Callback: define estado de processamento quando clicar seta
@app.callback(
    Output('processing-state', 'data', allow_duplicate=True),
    Input('submit-button', 'n_clicks'),
    State('query-input', 'value'),
    State('processing-state', 'data'),
    prevent_initial_call=True,
)
def set_processing_state(n_clicks, query, is_processing):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    if is_processing or not query or not query.strip():
        raise PreventUpdate
    return True


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

@app.callback(
    Output('history-list', 'children'),
    Input('store-history', 'data')
)
def render_history_list(history):
    items = history or []
    if not items:
        return html.Div('Sem consultas ainda.', style={'color': '#555'})
    # Render as buttons
    buttons = []
    for i, q in enumerate(items):
        buttons.append(
            html.Div([
                html.Button(
                    q,
                    id={'type': 'history-item', 'index': i},
                    title=q,
                    style={
                        'backgroundColor': 'white',
                        'color': '#003A70',
                        'border': '1px solid #D0D7E2',
                        'borderRadius': '16px',
                        'display': 'block',
                        'width': '100%',
                        'textAlign': 'left',
                        'padding': '8px 12px',
                        'whiteSpace': 'normal',
                        'wordBreak': 'break-word',
                        'lineHeight': '1.25',
                        'cursor': 'pointer'
                    }
                ),
                html.Button(
                    html.I(className='fas fa-trash'),
                    id={'type': 'history-delete', 'index': i},
                    title='Apagar esta consulta',
                    style={
                        'width': '28px', 'height': '28px', 'minWidth': '28px',
                        'borderRadius': '50%', 'border': '1px solid #FF5722',
                        'backgroundColor': 'white', 'color': '#FF5722',
                        'cursor': 'pointer'
                    },
                    className='delete-btn'
                )
            ], className='history-item-row', style={'display': 'flex', 'gap': '8px', 'alignItems': 'flex-start', 'marginBottom': '6px'})
        )
    return html.Div(buttons, style={'display': 'flex', 'flexDirection': 'column'})
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
        html.Div('Resumo da Busca', style=styles['card_title']),
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
    Input('store-results', 'data'),
    prevent_initial_call=True,
)
def render_results_table(results):
    if not results:
        return html.Div("Nenhum resultado encontrado", style={'color': '#555'})
    data = []
    for r in results:
        d = r.get('details', {})
        unidade = d.get('unidadeorgao_nomeunidade') or d.get('unidadeOrgao_nomeUnidade') or d.get('orgaoentidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/A'
        municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or d.get('municipioentidade') or 'N/A'
        uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or d.get('uf') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or d.get('valorfinal') or d.get('valorFinal') or 0)
        data_enc = format_date(d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento') or d.get('dataassinatura') or d.get('dataAssinatura') or 'N/A')
        data.append({
            'Rank': r.get('rank'),
            'Órgão': unidade,
            'Local': local,
            'Similaridade': round(r.get('similarity', 0), 4),
            'Valor (R$)': valor,
            'Data Encerramento': str(data_enc),
        })
    cols = [{'name': k, 'id': k} for k in ['Rank', 'Órgão', 'Local', 'Similaridade', 'Valor (R$)', 'Data Encerramento']]
    return dash_table.DataTable(
        data=data,
        columns=cols,
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'fontSize': '12px', 'padding': '6px', 'maxWidth': '140px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'fontSize': '13px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}],
        css=[{'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 'rule': 'font-size: 11px !important;'}]
    )


## Detalhes por resultado (cards)
@app.callback(
    Output('results-details', 'children'),
    Input('store-results', 'data'),
    Input('store-last-query', 'data'),
    prevent_initial_call=True,
)
def render_details(results, last_query):
    if not results:
        return []
    cards = []
    for r in results:
        d = r.get('details', {}) or {}
        descricao_full = d.get('descricaocompleta') or d.get('descricaoCompleta') or d.get('objeto') or ''
        destaque = _highlight_terms(descricao_full, last_query or '')

        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or d.get('valorfinal') or d.get('valorFinal') or 0)
        data_inc = _format_br_date(d.get('datainclusao') or d.get('dataInclusao') or d.get('dataassinatura') or d.get('dataAssinatura'))
        data_ab = _format_br_date(d.get('dataaberturaproposta') or d.get('dataAberturaProposta'))
        data_en = _format_br_date(d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or d.get('dataEncerramento'))

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
                html.Span('Datas: ', style={'fontWeight': 'bold'}), html.Span(f"Inclusão: {data_inc} | Abertura: {data_ab} | Encerramento: {data_en}")
            ]),
            html.Div([
                html.Span('Link: ', style={'fontWeight': 'bold'}), html.A(link_text, href=link, target='_blank', style={'wordBreak': 'break-all'}) if link else html.Span('N/A')
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span('Descrição: ', style={'fontWeight': 'bold'}),
                html.Div(dcc.Markdown(dangerously_allow_html=True, children=destaque))
            ])
        ], style={'marginTop': '20px', 'paddingTop': '16px', 'paddingLeft': '40px', 'paddingRight': '160px'})

        # Botões (dummy) no canto superior direito
        action_btns = html.Div([
            html.Button('Resumo do Edital', title='Resumo do Edital (dummy)', style={'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'borderRadius': '16px', 'height': '28px', 'padding': '0 10px', 'cursor': 'pointer'}),
            html.Button('Itens do Edital', title='Itens do Edital (dummy)', style={'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'borderRadius': '16px', 'height': '28px', 'padding': '0 10px', 'cursor': 'pointer', 'marginLeft': '6px'}),
        ], style={'position': 'absolute', 'top': '10px', 'right': '10px', 'display': 'flex'})

        cards.append(html.Div([
            body,
            action_btns,
            html.Div(str(r.get('rank')), style=styles['result_number'])
        ], style=styles['result_card']))
    return cards

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
            /* Compact controls inside left panel config card */
            .gvg-controls .Select-control { min-height: 32px; height: 32px; border-radius: 16px; font-size: 12px; border: 1px solid #D0D7E2; box-shadow: none; }
            .gvg-controls .is-focused .Select-control, .gvg-controls .Select.is-focused > .Select-control { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); }
            .gvg-controls .is-open .Select-control { border-color: #52ACFF; }
            .gvg-controls .Select-value-label,
            .gvg-controls .Select-option,
            .gvg-controls .VirtualizedSelectOption,
            .gvg-controls .Select-placeholder { font-size: 12px; }
            .gvg-controls .Select-menu-outer { font-size: 12px; border-radius: 12px; }
            .gvg-controls input[type="number"] { height: 32px; border-radius: 16px; font-size: 12px; padding: 6px 10px; border: 1px solid #D0D7E2; outline: none; }
            .gvg-controls input[type="number"]:focus { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); outline: none; }
            /* Reduce label spacing slightly */
            .gvg-controls label { font-size: 12px; margin-bottom: 4px; }
            /* Remove default input spinners for consistent look (optional) */
            .gvg-controls input[type=number]::-webkit-outer-spin-button,
            .gvg-controls input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
            .gvg-controls input[type=number] { -moz-appearance: textfield; }
            /* Horizontal form rows */
            .gvg-controls .gvg-form-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
            .gvg-controls .gvg-form-label { width: 130px; min-width: 130px; font-size: 12px; color: #003A70; margin: 0; font-weight: 600; }
            .gvg-controls .gvg-form-row > *:last-child { flex: 1; }

            /* History row hover: show delete button */
            .history-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
            .history-item-row:hover .delete-btn { opacity: 1; }
            .history-item-row .delete-btn:hover { background-color: #FDEDEC; }
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
'''


if __name__ == '__main__':
    # Porta padrão diferente do Reports para evitar conflito
    app.run_server(debug=True, port=8060, dev_tools_hot_reload=True, dev_tools_props_check=False, dev_tools_ui=False)

