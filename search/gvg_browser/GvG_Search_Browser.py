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
from dotenv import load_dotenv
import re
import io
import json
from datetime import datetime
import hashlib
from typing import List, Dict, Any, Tuple

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context, ALL
from dash.exceptions import PreventUpdate

from datetime import datetime as _dt
from datetime import date as _date

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
)
from gvg_exporters import (
    export_results_json,
    export_results_excel,
    export_results_csv,
    export_results_pdf,
    export_results_html,
)
from gvg_user import (
    get_user_initials,
    set_current_user,
    set_access_token,
    fetch_prompt_texts,
    add_prompt,
    save_user_results,
    delete_prompt,
    fetch_bookmarks,
    add_bookmark,
    remove_bookmark,
    get_current_user,
    fetch_user_results_for_prompt_text,
    get_prompt_preproc_output,
)
from gvg_database import get_user_resumo, upsert_user_resumo, fetch_documentos, db_fetch_all, insert_user_message

from gvg_boletim import (
    create_user_boletim,
    deactivate_user_boletim,
    fetch_user_boletins,
)
from gvg_styles import styles, CSS_ALL, _COLOR_PRIMARY, _COLOR_SECONDARY, _COLOR_BACKGROUND, _COLOR_BACKGROUND_ALT, _COLOR_GRAY

from gvg_debug import debug_log as dbg

from gvg_search_core import (
    SQL_DEBUG,
    set_sql_debug,
    get_relevance_filter_status,
    set_relevance_filter_level,
    toggle_intelligent_processing,
    get_top_categories_for_query,
    semantic_search,
    keyword_search,
    hybrid_search,
    correspondence_search,
    category_filtered_search,
    get_negation_embedding,
    _augment_aliases,
    _sanitize_sql_conditions,
    
)
from gvg_schema import (
    get_contratacao_core_columns,
    normalize_contratacao_row,
    project_result_for_output,
    PRIMARY_KEY,
)

from gvg_ai_utils import generate_contratacao_label
from gvg_email import send_html_email, render_boletim_email_html, render_favorito_email_html, render_history_email_html
from gvg_search_core import fetch_itens_contratacao
from gvg_billing import (
    get_system_plans, 
    get_user_settings, 
    upgrade_plan, 
    schedule_downgrade, 
    cancel_scheduled_downgrade, 
    apply_scheduled_plan_changes,
    create_checkout_session,  # Stripe integration (legacy)
    create_checkout_embedded_session
)
from gvg_notifications import add_note, NOTIF_SUCCESS, NOTIF_ERROR, NOTIF_WARNING, NOTIF_INFO

# Autenticação (Supabase)
try:
    from gvg_auth import (
        sign_in,
        sign_up_with_metadata,
        verify_otp,
        reset_password,
        sign_out,
        resend_otp,
    set_session,
    recover_session_from_code,
    update_user_password,
    )
except Exception:
    # Permite rodar sem pacote instalado (até instalar requirements)
    def sign_in(*args, **kwargs):
        return False, None, "Auth indisponível"
    def verify_otp(*args, **kwargs):
        return False, None, "Auth indisponível"
    def reset_password(*args, **kwargs):
        return False, "Auth indisponível"
    def recover_session_from_code(*args, **kwargs):
        return False, None, "Auth indisponível"
    def update_user_password(*args, **kwargs):
        return False, None, "Auth indisponível"
    def set_session(*args, **kwargs):
        return False, None, "Auth indisponível"
    def sign_out(*args, **kwargs):
        return False
    def resend_otp(*args, **kwargs):
        return False, "Auth indisponível"


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


# Feature flags globais, disponíveis antes da construção da UI
try:
    ENABLE_SEARCH_V2 = (os.getenv('GVG_ENABLE_SEARCH_V2', 'false').strip().lower() in ('1','true','yes','on'))
except Exception:
    ENABLE_SEARCH_V2 = False

# Pré-filtro V2: usa a mesma flag do V2. Se UI está ativa, o core também aplica filtros.
ENABLE_PREFILTER_V2 = ENABLE_SEARCH_V2

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

# Opções estáticas (Modalidade e Modo de Disputa)
# Observação: value usa o código cru (sem zero à esquerda); label exibe zero à esquerda para clareza visual
MODALIDADE_OPTIONS = [
    {"label": "01 - Pregão", "value": "1"},
    {"label": "02 - Concorrência", "value": "2"},
    {"label": "03 - Concurso", "value": "3"},
    {"label": "04 - Leilão", "value": "4"},
    {"label": "05 - Diálogo Competitivo", "value": "5"},
    {"label": "06 - Dispensa de Licitação", "value": "6"},
    {"label": "07 - Inexigibilidade de Licitação", "value": "7"},
    {"label": "08 - Credenciamento", "value": "8"},
]

MODO_OPTIONS = [
    {"label": "01 - Aberto", "value": "1"},
    {"label": "02 - Fechado", "value": "2"},
    {"label": "03 - Aberto/Fechado", "value": "3"},
    {"label": "04 - Fechado/Aberto", "value": "4"},
]


# =====================================================================================
# Cores padronizadas para datas de encerramento (tabela e detalhes)
# =====================================================================================
COLOR_ENC_NA = "#838383"       # cinza (sem data)
COLOR_ENC_EXPIRED = "#800080"    # roxo
COLOR_ENC_LT3 = "#FF0000EE"      # vermelho escuro (<= 3 dias)
COLOR_ENC_LT7 = "#FF6200"        # laranja (<= 7 dias)
COLOR_ENC_LT15 = "#FFB200"       # amarelo (<= 15 dias)
COLOR_ENC_LT30 = "#01B33A"     # verde (<= 30 dias)
COLOR_ENC_GT30 = "#0099FF"     # azul  ( > 30 dias)


# styles agora vem de gvg_styles


# =====================================================================================
# App Dash (com Bootstrap para fontes e ícones FontAwesome)
# =====================================================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=[
        "https://js.stripe.com/v3",
        "https://js.stripe.com/v3/embedded"
    ]
)
app.title = 'GovGo Search'

# =====================================================================================
# STRIPE WEBHOOK (Flask Route - embutido no Dash)
# =====================================================================================
# Carregar .env cedo para garantir STRIPE_PUBLISHABLE_KEY disponível
try:
    load_dotenv()
except Exception:
    pass
@app.server.route('/billing/webhook', methods=['POST'])
def stripe_webhook():
    """
    Endpoint POST para receber webhooks do Stripe.
    O Dash usa Flask internamente (app.server é o Flask app).
    """
    from flask import request, jsonify
    from gvg_billing import verify_webhook, handle_webhook_event
    
    payload = request.data
    signature = request.headers.get('Stripe-Signature')
    
    if not signature:
        dbg('WEBHOOK', 'Requisição sem Stripe-Signature header')
        return jsonify({'error': 'Missing signature'}), 400
    
    # Validar webhook
    event = verify_webhook(payload, signature)
    
    if 'error' in event:
        dbg('WEBHOOK', f"Erro ao verificar webhook: {event['error']}")
        return jsonify({'error': event['error']}), 400
    
    # Processar evento
    result = handle_webhook_event(event)
    
    if result.get('status') == 'error':
        dbg('WEBHOOK', f"Erro ao processar evento: {result.get('message')}")
        return jsonify({'error': result.get('message')}), 500
    
    dbg('WEBHOOK', f"Evento processado: {event.get('event_type')} [{event.get('event_id')}]")
    try:
        dbg('BILL', f"[webhook.route] processed type={event.get('event_type')} id={event.get('event_id')}")
    except Exception:
        pass
    return jsonify({'status': 'success'}), 200


@app.server.route('/billing/health', methods=['GET'])
def webhook_health():
    """Health check para verificar se webhook está online."""
    from flask import jsonify
    return jsonify({'status': 'healthy', 'service': 'gvg_billing_webhook'}), 200

# Rota simples para validar logs após o start
@app.server.route('/debug/ping', methods=['GET'])
def debug_ping():
    from flask import jsonify
    try:
        dbg('UI', 'PING')
    except Exception:
        pass
    return jsonify({'status': 'ok', 'ts': _dt.utcnow().isoformat()}), 200

# Rota que emite logs em todas as áreas ativas e retorna estado do DEBUG
@app.server.route('/debug/info', methods=['GET'])
def debug_info():
    from flask import jsonify
    try:
        areas = ['SQL','DB','AUTH','SEARCH','DOCS','ASSISTANT','IA','UI','BROWSER','BOLETIM','BMK','FAV','PRE','RESUMO','EVENT','USAGE','LIMIT','ERROR','BILL','WEBHOOK']
        for a in areas:
            try:
                dbg(a, f"TEST {a}")
            except Exception:
                pass
        return jsonify({'DEBUG': os.getenv('DEBUG'), 'DEV': os.getenv('GVG_BROWSER_DEV'), 'areas': areas, 'ts': _dt.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Log básico de cada request quando DEBUG estiver ligado
try:
    from flask import request
    if (os.getenv('DEBUG') or '').strip().lower() in ('1','true','yes','on'):
        @app.server.before_request
        def _log_request_path():
            try:
                dbg('UI', f"REQ {request.method} {request.path}")
            except Exception:
                pass
except Exception:
    pass

# =============================
# API auxiliar: status rápido de plano (usado pós-pagamento)
# =============================
@app.server.route('/api/plan_status', methods=['GET'])
def api_plan_status():
    from flask import request, jsonify
    uid = (request.args.get('uid') or '').strip()
    if not uid:
        return jsonify({'error': 'uid requerido'}), 400
    try:
        from gvg_billing import get_user_settings, get_usage_snapshot  # type: ignore
        settings = get_user_settings(uid)
        usage = get_usage_snapshot(uid)
        try:
            dbg('BILL', f"[/api/plan_status] uid={uid} plan={settings.get('plan_code')} usage_ok={bool(usage)}")
        except Exception:
            pass
        return jsonify({
            'plan_code': settings.get('plan_code'),
            'limits': settings.get('limits', {}),
            'usage': usage.get('usage', {}),
            'generated_at': usage.get('generated_at')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================
# Stripe Elements: criar assinatura e aplicar resultado
# =============================
@app.server.route('/billing/create_subscription', methods=['POST'])
def api_create_subscription():
    from flask import request, jsonify
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get('user_id') or '').strip()
        plan_code = (data.get('plan_code') or '').strip().upper()
        email = (data.get('email') or '').strip()
        name = data.get('name')
        if not all([user_id, plan_code, email]):
            return jsonify({'error': 'Parâmetros obrigatórios faltando'}), 400
        from gvg_billing import create_subscription_elements  # type: ignore
        result = create_subscription_elements(user_id, plan_code, email, name)
        if result.get('error'):
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.server.route('/billing/apply_subscription', methods=['POST'])
def api_apply_subscription():
    from flask import request, jsonify
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get('user_id') or '').strip()
        plan_code = (data.get('plan_code') or '').strip().upper()
        customer_id = (data.get('customer_id') or '').strip()
        subscription_id = (data.get('subscription_id') or '').strip()
        payment_intent_id = (data.get('payment_intent_id') or '').strip() or None
        amount_paid = data.get('amount_paid')
        currency = (data.get('currency') or 'BRL').upper()
        if not all([user_id, plan_code, customer_id, subscription_id]):
            return jsonify({'error': 'Dados insuficientes'}), 400
        from gvg_billing import apply_subscription_result  # type: ignore
        result = apply_subscription_result(user_id, plan_code, customer_id, subscription_id, payment_intent_id, amount_paid, currency)
        if result.get('error'):
            return jsonify(result), 400
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Embedded Checkout: endpoint para criar sessão embutida
@app.server.route('/billing/create_checkout_embedded', methods=['POST'])
def api_create_checkout_embedded():
    from flask import request, jsonify
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get('user_id') or '').strip()
        plan_code = (data.get('plan_code') or '').strip().upper()
        email = (data.get('email') or '').strip()
        name = data.get('name')
        try:
            dbg('BILL', f"[/billing/create_checkout_embedded] in uid={user_id} plan={plan_code}")
        except Exception:
            pass
        if not all([user_id, plan_code, email]):
            return jsonify({'error': 'Parâmetros obrigatórios faltando'}), 400
        from gvg_billing import create_checkout_embedded_session  # type: ignore
        result = create_checkout_embedded_session(user_id, plan_code, email, name)
        if result.get('error'):
            try:
                dbg('BILL', f"[/billing/create_checkout_embedded] error: {result.get('error')}")
            except Exception:
                pass
            return jsonify(result), 400
        try:
            dbg('BILL', f"[/billing/create_checkout_embedded] ok session_id={result.get('checkout_session_id')} has_secret={bool(result.get('client_secret'))}")
        except Exception:
            pass
        return jsonify(result), 200
    except Exception as e:
        try:
            dbg('BILL', f"[/billing/create_checkout_embedded] exception: {e}")
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500

# Parse argumentos --debug e --markdown (ex: python GvG_Search_Browser.py --debug --markdown)
AUTH_INIT = {'status': 'unauth', 'user': None}
try:
    import argparse
    _parser = argparse.ArgumentParser(add_help=False)
    _parser.add_argument('--debug', action='store_true')
    _parser.add_argument('--markdown', action='store_true')
    _parser.add_argument('--pass', dest='auto_pass', action='store_true')
    _known, _ = _parser.parse_known_args()
    if _known and getattr(_known, 'debug', False):
        set_sql_debug(True)
        try:
            os.environ['DEBUG'] = '1'
            # Forçar modo dev para evitar conflito com GVG_BROWSER_DEV
            os.environ['GVG_BROWSER_DEV'] = '1'
        except Exception:
            pass
        try:
            dbg('UI', f"DEBUG={os.getenv('DEBUG')} DEV={os.getenv('GVG_BROWSER_DEV')}")
        except Exception:
            pass
    if _known and getattr(_known, 'markdown', False):
        try:
            set_markdown_enabled(True)
        except Exception:
            pass
    # Bypass de autenticação via variáveis de ambiente quando --pass for usado
    if _known and getattr(_known, 'auto_pass', False):
        try:
            load_dotenv()
            _uid = os.getenv('PASS_USER_UID')
            _name = os.getenv('PASS_USER_NAME')
            _email = os.getenv('PASS_USER_EMAIL')
            if _uid and _name and _email:
                _bypass_user = {'uid': _uid, 'name': _name, 'email': _email}
                AUTH_INIT = {'status': 'auth', 'user': _bypass_user}
                try:
                    set_current_user(_bypass_user)
                except Exception:
                    pass
                dbg('AUTH', 'Bypass (--pass) com usuário de ambiente aplicado.')
            else:
                dbg('AUTH', 'Variáveis PASS_USER_UID/NAME/EMAIL ausentes; bypass ignorado.')
        except Exception:
            AUTH_INIT = {'status': 'unauth', 'user': None}
except Exception:
    pass

# ==============================================================
# Suporte a variáveis de ambiente: DEBUG/PASS (equivalentes a --debug/--pass)
# ==============================================================
try:
    def _truthy(val) -> bool:
        try:
            return str(val).strip().lower() in ("1", "true", "yes", "on")
        except Exception:
            return False

    # DEBUG via ambiente => mesmo efeito de --debug (liga verbose SQL/assistants)
    if _truthy(os.getenv("DEBUG")):
        try:
            set_sql_debug(True)
        except Exception:
            pass
        # Se DEBUG estiver ativo por env, default também ativar dev quando não especificado
        if not _truthy(os.getenv('GVG_BROWSER_DEV')):
            try:
                os.environ['GVG_BROWSER_DEV'] = '1'
            except Exception:
                pass

    # PASS via ambiente => mesmo efeito de --pass (bypass de autenticação)
    if _truthy(os.getenv("PASS")):
        try:
            load_dotenv()
            _uid = os.getenv('PASS_USER_UID')
            _name = os.getenv('PASS_USER_NAME')
            _email = os.getenv('PASS_USER_EMAIL')
            if _uid and _name and _email:
                _bypass_user = {'uid': _uid, 'name': _name, 'email': _email}
                AUTH_INIT = {'status': 'auth', 'user': _bypass_user}
                try:
                    set_current_user(_bypass_user)
                except Exception:
                    pass
                dbg('AUTH', 'Bypass (PASS=on) com usuário de ambiente aplicado.')
            else:
                dbg('AUTH', 'Variáveis PASS_USER_UID/NAME/EMAIL ausentes; bypass ignorado.')
        except Exception:
            AUTH_INIT = {'status': 'unauth', 'user': None}
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

# Plano do usuário - busca do banco na inicialização
def _get_user_plan_code(user: dict) -> str:
    try:
        uid = user.get('uid')
        if not uid:
            return 'FREE'
        from gvg_billing import get_user_settings
        settings = get_user_settings(uid)
        return (settings.get('plan_code') or 'FREE').upper()
    except Exception:
        return 'FREE'

_USER_PLAN_CODE = _get_user_plan_code(_USER)
_PLAN_BADGE_STYLE = styles.get(f"plan_badge_{_USER_PLAN_CODE.lower()}", styles.get('plan_badge_free'))
LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"
header = html.Div([
    html.Div([
        html.Img(src=LOGO_PATH, style=styles['header_logo']),
        html.Div("Search", className='gvg-header-title', style=styles['header_title']),
        html.Div(_USER_PLAN_CODE, id='header-plan-badge', style={**_PLAN_BADGE_STYLE, 'marginLeft': '6px'})
    ], style=styles['header_left']),
    html.Div([
        html.Button([
            html.I(className='fas fa-comments')
        ], id='header-message-btn', title='Enviar mensagem', style=styles['header_message_btn']),
        html.Div(
            id='header-user-badge',
            children='U',  # inicial do usuário; atualizado por callback
            style=styles['header_user_badge']
        )
    ], style=styles['header_right'])
], style=styles['header'])

# ------------------ Overlay de Autenticação (bloqueia UI até autenticar) ------------------
catchy_lines = [
    "Busque licitações públicas com inteligência artificial.",
    "Encontre oportunidades de contratos governamentais rapidamente.",
    "Consultas avançadas para licitações e contratos públicos.",
    "Sua porta de entrada para o mercado público.",
    "Descubra licitações relevantes com facilidade.",
]
auth_overlay = html.Div([
    html.Div([
        html.Img(src=LOGO_PATH, style=styles['auth_logo']),
        #html.H3("GovGo Search", style=styles['auth_title']),
        #html.Div([html.Div(line, style=styles['auth_subtitle']) for line in catchy_lines]),
        html.Div(id='auth-error', style={'display': 'none', **styles['auth_error']}),
        html.Div([
            html.Label('E-mail', className='gvg-form-label'),
            dcc.Input(id='auth-email', type='email', placeholder='seu@email.com', autoComplete='username', style=styles['auth_input']),
            html.Label('Senha', className='gvg-form-label', style={'marginTop': '8px'}),
            html.Div([
                dcc.Input(id='auth-password', type='password', placeholder='••••••••', autoComplete='current-password', style=styles['auth_input_eye']),
                html.Button(html.I(className='fas fa-eye'), id='auth-pass-toggle', title='Mostrar/ocultar senha', n_clicks=0, style=styles['auth_eye_button'])
            ], style=styles['auth_input_group']),
            html.Div([
                html.Div(dcc.Checklist(id='auth-remember', options=[{'label': ' Lembrar e-mail e senha neste navegador', 'value': 'yes'}], value=[], style={'fontSize': '11px'}), style={'marginTop': '6px'}),
                html.A('Esqueci minha senha', id='auth-forgot', n_clicks=0, style=styles['auth_link'])
            ], style=styles['auth_row_between']),
            html.Div([
                html.Button('Entrar', id='auth-login', style=styles['auth_btn_primary']),
                html.Button('Cadastrar', id='auth-switch-signup', style=styles['auth_btn_secondary'])
            ], style=styles['auth_actions_center'])
        ], id='auth-view-login', style={'display': 'block'}),
        html.Div([
            html.Label('Nome completo', className='gvg-form-label'),
            dcc.Input(id='auth-fullname', type='text', placeholder='Seu nome', style=styles['auth_input']),
            html.Label('Telefone', className='gvg-form-label', style={'marginTop': '8px'}),
            dcc.Input(id='auth-phone', type='text', placeholder='(DDD) 90000-0000', style=styles['auth_input']),
            html.Label('E-mail', className='gvg-form-label', style={'marginTop': '8px'}),
            dcc.Input(id='auth-email-sign', type='email', placeholder='seu@email.com', autoComplete='username', style=styles['auth_input']),
            html.Label('Senha', className='gvg-form-label', style={'marginTop': '8px'}),
            html.Div([
                dcc.Input(id='auth-password-sign', type='password', placeholder='••••••••', autoComplete='new-password', style=styles['auth_input_eye']),
                html.Button(html.I(className='fas fa-eye'), id='auth-pass-toggle-sign', title='Mostrar/ocultar senha', n_clicks=0, style=styles['auth_eye_button'])
            ], style=styles['auth_input_group']),
            dcc.Checklist(id='auth-terms', options=[{'label': ' Aceito os Termos de Contratação', 'value': 'ok'}], value=[], style={'marginTop': '8px', 'fontSize': '11px'}),
            html.Div([
                html.Button('Cadastrar', id='auth-signup', style=styles['auth_btn_primary']),
                html.Button('Voltar', id='auth-switch-login', style=styles['auth_btn_secondary'])
            ], style=styles['auth_actions_center'])
        ], id='auth-view-signup', style={'display': 'none'}),
        html.Div([
            html.Div('Confirme o seu e-mail', style=styles['card_title']),
            html.Div(id='auth-confirm-text', style=styles['auth_subtitle']),
            html.Label('Código de confirmação', className='gvg-form-label', style={'marginTop': '8px'}),
            dcc.Input(id='auth-otp', type='text', placeholder='Código recebido por e-mail', style=styles['auth_input']),
            html.Div([
                html.Button('Confirmar', id='auth-confirm', style=styles['auth_btn_primary']),
                html.Button('Voltar', id='auth-switch-login-2', style=styles['auth_btn_secondary']),
                html.Button('Reenviar código', id='auth-resend-link', style=styles['auth_btn_secondary'])
            ], style=styles['auth_actions'])
        ], id='auth-view-confirm', style={'display': 'none'}),
        html.Div([
            html.Div('Redefinir senha', style=styles['card_title']),
            html.Div('Defina sua nova senha para continuar.', style=styles['auth_subtitle']),
            html.Label('Nova senha', className='gvg-form-label', style={'marginTop': '8px'}),
            html.Div([
                dcc.Input(id='auth-new-pass', type='password', placeholder='Nova senha', autoComplete='new-password', style=styles['auth_input_eye']),
                html.Button(html.I(className='fas fa-eye'), id='auth-pass-toggle-reset-1', title='Mostrar/ocultar senha', n_clicks=0, style=styles['auth_eye_button'])
            ], style=styles['auth_input_group']),
            html.Label('Confirmar nova senha', className='gvg-form-label', style={'marginTop': '8px'}),
            html.Div([
                dcc.Input(id='auth-new-pass2', type='password', placeholder='Repita a nova senha', autoComplete='new-password', style=styles['auth_input_eye']),
                html.Button(html.I(className='fas fa-eye'), id='auth-pass-toggle-reset-2', title='Mostrar/ocultar senha', n_clicks=0, style=styles['auth_eye_button'])
            ], style=styles['auth_input_group']),
            html.Div([
                html.Button('Confirmar', id='auth-reset-confirm', style=styles['auth_btn_primary']),
                html.Button('Cancelar', id='auth-reset-cancel', style=styles['auth_btn_secondary'])
            ], style=styles['auth_actions'])
        ], id='auth-view-reset', style={'display': 'none'}),
    ], style=styles['auth_card'])
], id='auth-overlay', style=styles['auth_overlay'])


# Painel de controles (esquerda)
controls_panel = html.Div([
    html.Div([
        html.Div([
            html.I(className='fas fa-search', style=styles['section_icon']),
            html.Div('Consulta', style=styles['card_title'])
        ], style=styles['section_header_left'])
    ], style=styles['row_header']),
    # Entrada de consulta com painel de Boletim embutido logo abaixo (layout em tabela)
    html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Td(
                        html.Div([
                            dcc.Textarea(
                                id='query-input',
                                placeholder='Digite sua consulta...',
                                rows=2,
                                style={**styles['input_field'], 'overflowY': 'auto', 'resize': 'none', 'height': '80px', 'width': '100%'}
                            )
                        ], id='query-textarea-wrap', style=styles.get('query_textbox', {})),
                        style=styles.get('query_text_cell', {'width': '100%'})
                    ),
                    html.Td(
                        html.Div([
                            html.Button(
                                html.I(className="fas fa-arrow-right"),
                                id='submit-button',
                                title='Executar busca',
                                style=styles['arrow_button']
                            ),
                            html.Button(
                                html.I(className="fas fa-calendar-plus"),
                                id='boletim-toggle-btn',
                                title='Agendar boletim desta consulta',
                                style={**styles['arrow_button'], 'marginTop': '6px', 'opacity': 0.4},
                                disabled=True
                            ),
                        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
                    , style=styles.get('query_buttons_cell', {'width': '36px'}) )
                ]),
                html.Tr([
                    html.Td(
                        dbc.Collapse(
                            html.Div([
                                html.Table([
                                    html.Tbody([
                                        html.Tr([
                                            html.Td([
                                                html.Div([
                                                    html.Label('Frequência', className='gvg-form-label'),
                                                    dcc.Dropdown(
                                                        id='boletim-freq',
                                                        options=[
                                                            {'label': 'Diário (Seg-Sex)', 'value': 'DIARIO'},
                                                            {'label': 'Semanal', 'value': 'SEMANAL'},
                                                        ],
                                                        value='DIARIO',
                                                        clearable=False,
                                                        style=styles['input_fullflex']
                                                    )
                                                ], className='gvg-form-row'),
                                                html.Div([
                                                    html.Label('Horários', className='gvg-form-label'),
                                                    dcc.Checklist(
                                                        id='boletim-multidiario-slots',
                                                        options=[
                                                            {'label': ' Manhã', 'value': 'manha'},
                                                            {'label': ' Tarde', 'value': 'tarde'},
                                                            {'label': ' Noite', 'value': 'noite'},
                                                        ],
                                                        value=['manha'],
                                                        labelStyle={'display': 'inline-block', 'marginRight': '12px', 'fontSize': '12px'}
                                                    )
                                                ], className='gvg-form-row', style=styles['hidden']),
                                                html.Div([
                                                    html.Label('Dias', className='gvg-form-label'),
                                                    dcc.Checklist(
                                                        id='boletim-semanal-dias',
                                                        options=[
                                                            {'label': ' Seg', 'value': 'seg'},
                                                            {'label': ' Ter', 'value': 'ter'},
                                                            {'label': ' Qua', 'value': 'qua'},
                                                            {'label': ' Qui', 'value': 'qui'},
                                                            {'label': ' Sex', 'value': 'sex'},
                                                        ],
                                                        value=['seg'],
                                                        labelStyle={'display': 'inline-block', 'marginRight': '10px', 'fontSize': '12px'}
                                                    )
                                                ], className='gvg-form-row'),
                                                html.Div([
                                                    html.Label('Canais', className='gvg-form-label'),
                                                    dcc.Checklist(
                                                        id='boletim-channels',
                                                        options=[
                                                            {'label': ' E-mail', 'value': 'email'},
                                                            {'label': ' WhatsApp', 'value': 'whatsapp'},
                                                        ],
                                                        value=['email'],
                                                        labelStyle={'display': 'inline-block', 'marginRight': '12px', 'fontSize': '12px'}
                                                    )
                                                ], className='gvg-form-row', style=styles['hidden'])
                                            ], style=styles.get('query_text_cell', {'width': '100%'}) ),
                                            html.Td(
                                                html.Div([
                                                    html.Button(
                                                        html.I(className='fas fa-plus'),
                                                        id='boletim-save-btn',
                                                        title='Salvar boletim',
                                                        style=styles['arrow_button'],
                                                        disabled=True
                                                    )
                                                ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}),
                                                style=styles.get('query_buttons_cell', {'width': '36px'})
                                            )
                                        ])
                                    ])
                                ], style=styles.get('query_table', {'width': '100%'}) )
                            ], style=styles['boletim_config_panel'], className='gvg-controls'),
                            id='boletim-collapse', is_open=False
                        ),
                        colSpan=2,
                        style={'paddingTop': '2px'}
                    )
                ])
            ])
        ], style=styles.get('query_table', {'width': '100%'}) ),
    ], id='query-container', style=styles['input_container']),

    ######## FILTROS AVANÇADOS ########
    html.Div([
        html.Button([
            html.Div([
                html.I(className='fas fa-filter', style=styles['section_icon']),
                html.Div("Filtros Avançados", style=styles['card_title'])
            ], style=styles['section_header_left']),
            html.I(className="fas fa-chevron-down")
        ], id='filters-toggle-btn', title='Mostrar/ocultar filtros', style=styles['section_header_button'])
    ], style=(styles['row_header'] if ENABLE_SEARCH_V2 else {**styles['row_header'], 'display': 'none'})),
    dbc.Collapse(
        html.Div([
            html.Div([
                html.Label('Nº PNCP', className='gvg-form-label'),
                dcc.Input(id='flt-pncp', type='text', placeholder='ex.: 2024.12345.1.1.1', style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Órgão (contém)', className='gvg-form-label'),
                dcc.Input(id='flt-orgao', type='text', placeholder='Nome do órgão', style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('CNPJ do Órgão', className='gvg-form-label'),
                dcc.Input(id='flt-cnpj', type='text', placeholder='Somente números', style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Estado (UF)', className='gvg-form-label'),
                dcc.Dropdown(
                    id='flt-uf',
                    options=[{'label': uf, 'value': uf} for uf in [
                        'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
                    ]],
                    placeholder='Selecione 1 ou vários estados',
                    value=[],
                    multi=True,
                    clearable=True,
                    style=styles['input_fullflex']
                )
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Municípios', className='gvg-form-label'),
                dcc.Input(id='flt-municipio', type='text', placeholder='Municípios separados por vírgula', style=styles['input_fullflex'])
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Modalidade', className='gvg-form-label'),
                dcc.Dropdown(
                    id='flt-modalidade-id',
                    options=[],  # carregado via callback
                    placeholder='Selecione 1 ou várias modalidades',
                    multi=True,
                    clearable=True,
                    searchable=True,
                    style=styles['input_fullflex']
                )
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Modo de Disputa', className='gvg-form-label'),
                dcc.Dropdown(
                    id='flt-modo-id',
                    options=[],  # carregado via callback
                    placeholder='Selecione 1 ou vários modos',
                    multi=True,
                    clearable=True,
                    searchable=True,
                    style=styles['input_fullflex']
                )
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Tipo de Período', className='gvg-form-label'),
                dcc.Dropdown(
                    id='flt-date-field',
                    options=[
                        {'label': 'Encerramento', 'value': 'encerramento'},
                        {'label': 'Abertura', 'value': 'abertura'},
                        {'label': 'Publicação', 'value': 'publicacao'},
                    ],
                    value='encerramento', clearable=False, style=styles['input_fullflex']
                )
            ], className='gvg-form-row'),
            html.Div([
                html.Label('Período', className='gvg-form-label'),
                html.Div([
                    dcc.Input(id='flt-date-start', type='text', placeholder='De: (dd/mm/aaaa)', maxLength=10, style=styles['input_fullflex']),
                    #html.Span(' — ', style={'padding': '0 4px'}),
                    html.Span('', style={'padding': '0 2px'}),
                    dcc.Input(id='flt-date-end', type='text', placeholder='Até: (dd/mm/aaaa)', maxLength=10, style=styles['input_fullflex'])
                ], style={'display': 'flex', 'gap': '4px', 'alignItems': 'center'})
            ], className='gvg-form-row'),
        ], style=styles['controls_group'], className='gvg-controls'),
    id='filters-collapse', is_open=False, style=({} if ENABLE_SEARCH_V2 else {'display': 'none'})
    ),

    ######## CONFIGURAÇÔES DE BUSCA ########
    html.Div([
        html.Button([
            html.Div([
                html.I(className='fas fa-sliders-h', style=styles['section_icon']),
                html.Div("Configurações de Busca", style=styles['card_title'])
            ], style=styles['section_header_left']),
            html.I(className="fas fa-chevron-down")
        ], id='config-toggle-btn', title='Mostrar/ocultar configurações', style=styles['section_header_button'])
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
    id='config-collapse', is_open=False
    ),

    ######## HISTÓRICO ########
    html.Div([
        html.Button([
            html.Div([
                html.I(className='fas fa-history', style=styles['section_icon']),
                html.Div('Histórico', style=styles['card_title'])
            ], style=styles['section_header_left']),
            html.I(className="fas fa-chevron-down")
        ], id='history-toggle-btn', title='Mostrar/ocultar histórico', style=styles['section_header_button'])
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div(id='history-list')
        ], id='history-card', style=styles['controls_group']),
        id='history-collapse', is_open=True
    ),
    
    ######## FAVORITOS ########
    html.Div([
        html.Button([
            html.Div([
                html.I(className='fas fa-bookmark', style=styles['section_icon']),
                html.Div('Favoritos', style=styles['card_title'])
            ], style=styles['section_header_left']),
            html.I(className="fas fa-chevron-down")
        ], id='favorites-toggle-btn', title='Mostrar/ocultar favoritos', style=styles['section_header_button'])
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div(id='favorites-list')
        ], id='favorites-card', style=styles['controls_group']),
        id='favorites-collapse', is_open=True
    ),

    ######## BOLETINS ########
    html.Div([
        html.Button([
            html.Div([
                html.I(className='fas fa-calendar', style=styles['section_icon']),
                html.Div('Boletins', style=styles['card_title'])
            ], style=styles['section_header_left']),
            html.I(className="fas fa-chevron-down")
        ], id='boletins-toggle-btn', title='Mostrar/ocultar boletins', style=styles['section_header_button'])
    ], style=styles['row_header']),
    dbc.Collapse(
        html.Div([
            html.Div(id='boletins-list')
        ], id='boletins-card', style=styles['controls_group']),
        id='boletins-collapse', is_open=True
    )
], style=styles['left_panel'])


# Painel de resultados (direita)
results_panel = html.Div([
    html.Div(id='tabs-bar', style=styles['tabs_bar']),
    html.Div(id='status-bar', style={**styles['result_card'], 'display': 'none'}),
    # Spinner central durante processamento (idêntico ao botão de busca em modo cálculo)
    html.Div(
        [
            # Barra de progresso fina sob o spinner
            html.Div(
                [
                    html.Div(
                        id='progress-fill',
            style={**styles['progress_fill'], 'width': '0%'}
                    )
                ],
                id='progress-bar',
        style={**styles['progress_bar_container'], 'display': 'none'}
            ),
            # Rótulo/percentual abaixo da barra
            html.Div(
                id='progress-label',
                children='',
        style={**styles['progress_label'], 'display': 'none'}
            )
        ],
        id='gvg-center-spinner',
    style=styles['center_spinner']
    ),
    html.Div([
        html.Div([
            html.Div('Exportar', style=styles['card_title']),
            html.Button('JSON', id='export-json', style={**styles['export_button'], 'width': '60px'}),
            html.Button('XLSX', id='export-xlsx', style={**styles['export_button'], 'width': '60px', 'marginLeft': '6px'}),
            html.Button('CSV', id='export-csv', style={**styles['export_button'], 'width': '60px', 'marginLeft': '6px'}),
            html.Button('PDF', id='export-pdf', style={**styles['export_button'], 'width': '60px', 'marginLeft': '6px'}),
            html.Button('HTML', id='export-html', style={**styles['export_button'], 'width': '60px', 'marginLeft': '6px'}),
    ], style=styles['export_row'])
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
    # Precisa estar no topo para capturar hash/query do Supabase na navegação inicial
    dcc.Location(id='url'),
    dcc.Store(id='store-auth', data=AUTH_INIT),
    dcc.Store(id='store-auth-view', data='login'),
    dcc.Store(id='store-auth-error', data=''),
    dcc.Store(id='store-auth-pending-email', data=''),
    dcc.Store(id='store-auth-remember', data={'email': '', 'password': '', 'remember': False}, storage_type='local'),
    dcc.Store(id='store-plan-action', data=None),
    dcc.Store(id='store-stripe-checkout-url', data=None),
    dcc.Store(id='store-app-init', data={'initializing': False}),
    dcc.Store(id='store-results', data=[]),
    dcc.Store(id='store-results-sorted', data=[]),
    dcc.Store(id='store-result-sessions', data={}),
    dcc.Store(id='store-active-session', data=None),
    dcc.Store(id='store-session-event', data=None),
    dcc.Store(id='store-categories', data=[]),
    dcc.Store(id='store-meta', data={}),
    dcc.Store(id='store-last-query', data=""),
    dcc.Store(id='store-boletim-open', data=False),
    dcc.Store(id='store-boletins', data=[]),
    dcc.Store(id='store-boletins-open', data=True),
    dcc.Store(id='store-history', data=[]),
    dcc.Store(id='store-history-open', data=True),
    dcc.Store(id='store-favorites', data=[]),
    dcc.Store(id='store-favorites-open', data=True),
    dcc.Store(id='store-planos-data', data=None),
    # Stripe Elements: publishable key e sessão do Elements
    dcc.Store(id='store-stripe-pk', data=os.getenv('STRIPE_PUBLISHABLE_KEY')),
    dcc.Store(id='store-elements-session', data=None),
    # Evento de pagamento Stripe (session_id e timestamp)
    dcc.Store(id='store-payment-event', data=None),
    # Timers de pagamento: auto-fechamento e polling de status
    dcc.Interval(id='payment-autoclose-interval', interval=1000, n_intervals=0, disabled=True),
    dcc.Interval(id='payment-check-interval', interval=1000, n_intervals=0, disabled=True),
    # Campo oculto para capturar session_id vindo do postMessage sem reload
    dcc.Input(id='stripe-success-input', type='text', value='', style={'display': 'none'}),
    # Campo oculto para resultado do Stripe Elements (JSON)
    dcc.Input(id='stripe-elements-result', type='text', value='', style={'display': 'none'}),
    dcc.Store(id='processing-state', data=False),
    dcc.Store(id='store-config-open', data=False),
    dcc.Store(id='store-items', data={}),
    dcc.Store(id='store-sort', data=None),
    dcc.Store(id='store-panel-active', data={}),
    dcc.Store(id='store-cache-itens', data={}),
    dcc.Store(id='store-cache-docs', data={}),
    dcc.Store(id='store-cache-resumo', data={}),
    dcc.Store(id='progress-store', data={'percent': 0, 'label': ''}),
    # Filtros avançados da busca (payload canônico)
    dcc.Store(id='store-search-filters', data={}),
    # Contexto do modal de e-mail (tipo: 'boletim'|'favorito', id ou índice)
    dcc.Store(id='store-email-modal-context', data=None),
    # Fila de envio de e-mail (para fechar modal imediatamente e enviar em segundo plano)
    dcc.Store(id='store-email-send-request', data=None),
    # Token da consulta corrente (para vincular aba pendente ao resultado final)
    dcc.Store(id='store-current-query-token', data=None),
    # Notificações Toast (lista de notificações ativas)
    dcc.Store(id='store-notifications', data=[]),
    dcc.Interval(id='notifications-interval', interval=500, n_intervals=0, disabled=False),
    dcc.Interval(id='progress-interval', interval=400, n_intervals=0, disabled=True),
    dcc.Download(id='download-out'),
    # Options dinâmicas de Modalidade
    dcc.Store(id='store-modalidade-options', data=[]),

    # Container de notificações Toast (fixo no canto/centro da tela)
    html.Div(id='toast-container', style=styles['toast_container']),
    
    # Listener para mensagens do popup Stripe (atualização dinâmica sem reload)
    html.Script("""
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'stripe_success') {
                try {
                    const sid = event.data.session_id || '';
                    console.log('[Stripe] Sucesso recebendo session_id:', sid);
                    const hidden = document.getElementById('stripe-success-input');
                    if (hidden) {
                        hidden.value = sid;
                        // Disparar evento input para Dash reagir
                        const ev = new Event('input', { bubbles: true });
                        hidden.dispatchEvent(ev);
                    }
                } catch(e) {
                    console.error('Erro ao processar stripe_success:', e);
                }
            }
        });
    """),
    # Scripts de assets são carregados automaticamente (assets/stripe-elements.js)

    header,
    # Popover de Mensagem (botão ao lado do avatar)
    dbc.Popover(
        html.Div([
            html.Div(
                dcc.Textarea(id='message-textarea', placeholder='Escreva sua mensagem...', rows=6, style=styles['message_textarea']),
                style=styles.get('message_wrap', {'padding': '0 12px'})
            ),
            html.Div([
                html.Button([
                    html.I(className='fas fa-paper-plane', style={'marginRight': '6px'}),
                    html.Span('Enviar')
                ], id='message-send-btn', n_clicks=0, style=styles.get('message_send_btn', styles['auth_btn_primary']))
            ], style=styles.get('message_actions', {'display': 'flex', 'justifyContent': 'flex-end', 'padding': '0 12px'}))
        ], style=styles['message_menu']),
        id='message-popover',
        target='header-message-btn',
        is_open=False,
        placement='bottom',
        trigger='manual',  # controle via callback
        body=True
    ),
    # Popover do usuário (menu do avatar)
    dbc.Popover(
        html.Div([
            html.Div([
                html.Div(id='user-menu-name', style=styles['user_menu_name']),
                html.Div(id='user-menu-email', style=styles['user_menu_email'])
            ], style=styles['user_menu_user']),
            html.Hr(style=styles['user_menu_sep']),
            html.Div([
                html.I(className='fas fa-tags', style=styles['user_menu_icon']),
                html.Span('Planos')
            ], id='user-menu-item-planos', n_clicks=0, role='button', style=styles['user_menu_item']),
            html.Div([
                html.I(className='fas fa-cog', style=styles['user_menu_icon']),
                html.Span('Configurações')
            ], id='user-menu-item-config', n_clicks=0, role='button', style=styles['user_menu_item']),
            html.Div([
                html.I(className='fas fa-sign-out-alt', style=styles['user_menu_icon']),
                html.Span('Sair')
            ], id='user-menu-item-logout', n_clicks=0, role='button', style=styles['user_menu_item'])
        ], style=styles['user_menu']),
        id='user-menu-popover',
        target='header-user-badge',
        is_open=False,
        placement='bottom',
        trigger='manual',  # controle via callback
        body=True
    ),
    # Modal Planos e Limites
    dbc.Modal([
        dbc.ModalHeader(
            html.Div([
                html.Span('Planos e Limites', style={'fontWeight': '600', 'fontSize': '18px'}),
                html.Button('×', id='planos-modal-close', title='Fechar',
                            style={'background': 'transparent', 'border': 'none', 'fontSize': '22px', 'lineHeight': '1', 'cursor': 'pointer', 'color': '#555', 'padding': '0 8px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%'}),
            close_button=False,
            style={'borderBottom': '1px solid #E0EAF9'}
        ),
        dbc.ModalBody(id='planos-modal-body', children=html.Div('Carregando...', style={'fontSize': '12px'}), style={'paddingTop': '18px', 'paddingBottom': '24px'})
    ], id='planos-modal', is_open=False, size='xl', backdrop=True, centered=True),
    # Modal do Stripe Embedded Checkout (padrão Stripe, embutido)
    dbc.Modal([
        dbc.ModalHeader(
            html.Div([
                html.Span('Pagamento', style={'fontWeight': '600', 'fontSize': '16px'}),
                html.Button('×', id='stripe-payment-close', title='Fechar',
                            style={'background': 'transparent', 'border': 'none', 'fontSize': '20px', 'lineHeight': '1', 'cursor': 'pointer', 'color': '#555', 'padding': '0 8px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%'})
        , close_button=False),
        dbc.ModalBody([
            html.Div(id='stripe-embedded-checkout', style={'minHeight': '480px'}),
            html.Div(id='stripe-payment-error', style={'color': '#b00020', 'fontSize': '12px', 'marginTop': '8px'}),
            # html.Div([
            #     html.Button('Cancelar', id='stripe-payment-cancel', style=styles['auth_btn_secondary'])
            # ], style={'display': 'flex', 'justifyContent': 'flex-end', 'marginTop': '8px'})
        ], style={'paddingTop': '12px', 'paddingBottom': '16px'})
    ], id='stripe-payment-modal', is_open=False, size='md', backdrop=True, centered=True),
    auth_overlay,
    # Modal de envio de e-mail (boletim/favoritos) – compacto, sem título/X
    dbc.Modal([
        html.Div(id='email-modal-title', children='Enviar por e-mail', style={'display': 'none'}),
        dbc.ModalBody([
            html.Div([
                dcc.Input(
                    id='email-modal-input', type='text', placeholder='ex.: a@ex.com, b@ex.com',
                    debounce=True, autoFocus=True,
                    style={'flex': '1', 'minWidth': 0, 'padding': '8px'}
                ),
                html.Button('Enviar', id='email-modal-send', style={**styles['auth_btn_primary'], 'margin': '0'})
            ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center'}),
            html.Div(style={'height': '8px'}),
            dcc.Checklist(id='email-modal-self', options=[{'label': ' Enviar para meu e-mail', 'value': 'self'}], value=[], style={'fontSize': '12px'}),
            html.Div(id='email-modal-error', style={'display': 'none', 'color': '#b00020', 'fontSize': '12px', 'marginTop': '6px'})
        ]),
    ], id='email-modal', is_open=False, size='sm', centered=True, backdrop=True, style={'maxWidth': '480px', 'width': '95vw', 'borderRadius': '16px'}),
    html.Div([
        html.Div([
            controls_panel
        ], className='gvg-slide'),
        html.Div([
            results_panel
        ], className='gvg-slide')
    ], id='gvg-main-panels', style=styles['container'])
])


# =====================================================================================
# Helper: renderizar barras de uso (consumo vs limites)
# =====================================================================================
def _render_usage_bars(usage: Dict[str, Any]) -> html.Div:
    """Renderiza barras de progresso para o consumo atual do usuário.
    
    Args:
        usage: dict retornado por get_usage_status(user_id) com formato:
               {'consultas': {'used': X, 'limit': Y, 'pct': P}, ...}
    
    Returns:
        html.Div com barras de progresso coloridas por tipo de uso
    """
    bars = []
    labels = {
        'consultas': ('Consultas', 'fa-search'),
        'resumos': ('Resumos', 'fa-file-alt'),
        'boletim_run': ('Boletins', 'fa-calendar'),
        'favoritos': ('Favoritos', 'fa-bookmark'),
    }
    
    for key, (label, icon) in labels.items():
        data = usage.get(key, {})
        used = data.get('used', 0)
        limit = data.get('limit', 1)
        pct = data.get('pct', 0.0)
        
        # Cor da barra baseada no percentual de uso
        if pct >= 100:
            color = '#D32F2F'  # vermelho (limite atingido)
        elif pct >= 80:
            color = '#FF9800'  # laranja (aviso)
        else:
            color = '#4CAF50'  # verde (ok)
        
        bars.append(html.Div([
            html.Div([
                html.I(className=f'fas {icon}', style={'marginRight': '6px', 'fontSize': '11px', 'width': '14px', 'flexShrink': '0'}),
                html.Span(f'{label}: {used}/{limit} ({pct:.0f}%)', style={'fontSize': '12px', 'color': '#424242', 'whiteSpace': 'nowrap', 'marginRight': '5px', 'flexShrink': '0'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '5px', 'minWidth': 'fit-content'}),
            html.Div([
                html.Div(style={
                    'width': f'{min(pct, 100)}%',
                    'height': '6px',
                    'backgroundColor': color,
                    'borderRadius': '3px',
                    'transition': 'width 0.3s ease'
                })
            ], style={
                'flex': '1',
                'height': '6px',
                'backgroundColor': '#e0e0e0',
                'borderRadius': '3px',
                'overflow': 'hidden'
            })
        ], style={'marginBottom': '10px', 'display': 'flex', 'alignItems': 'center'}))
    
    return html.Div(bars, style={'padding': '0 4px'})


# =====================================================================================
# Stripe: Clientside callback para abrir popup do checkout
# =====================================================================================
app.clientside_callback(
    """
    function(action_data) {
    if (!action_data || !action_data.action) {
            return window.dash_clientside.no_update;
        }
    // Legado (popup Checkout)
    if (action_data.action === 'open_popup' && action_data.url) {
            // Abrir popup centralizado
            const width = 600;
            const height = 800;
            const left = (window.screen.width - width) / 2;
            const top = (window.screen.height - height) / 2;
            
            const popup = window.open(
                action_data.url,
                'stripe-checkout',
                `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
            );
            
            // Opcional: detectar quando popup fecha e recarregar planos
            if (popup) {
                const checkClosed = setInterval(function() {
                    if (popup.closed) {
                        clearInterval(checkClosed);
                        console.log('Popup fechado, recarregando dados...');
                        // Você pode adicionar lógica aqui para atualizar planos
                    }
                }, 1000);
            }
        }
        // Novo fluxo: abrir modal Elements
    if (action_data.action === 'open_embedded' && action_data.session) {
            try {
                // Apenas sinaliza abertura; a montagem ocorrerá no callback que observa o modal aberto
                const hidden = document.getElementById('stripe-payment-error');
                if (hidden) hidden.textContent = '';
            } catch(e) { console.error(e); }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('store-stripe-checkout-url', 'data'),
    Input('store-plan-action', 'data'),
)

# Abre/fecha o modal de pagamento quando a store receber sessão (Embedded)
@app.callback(
    Output('stripe-payment-modal', 'is_open'),
    Output('store-elements-session', 'data'),
    Input('store-plan-action', 'data'),
    Input('stripe-payment-close', 'n_clicks'),
    State('stripe-payment-modal', 'is_open'),
    prevent_initial_call=True
)
def open_close_elements_modal(action_data, close_clicks, is_open):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig in ('stripe-payment-close',):
        try:
            dbg('BILL', f"[modal] close clicked by={trig}")
        except Exception:
            pass
        return False, None
    # Ação de abrir
    if action_data and action_data.get('action') == 'open_embedded':
        session = action_data.get('session')
        try:
            has_secret = bool((session or {}).get('client_secret'))
            dbg('BILL', f"[modal] open request has_client_secret={has_secret}")
        except Exception:
            pass
        return True, session
    raise PreventUpdate

# Clientside para montar o Payment Element quando o modal abre
app.clientside_callback(
    """
    async function(is_open, session, publishableKey) {
        // Cleanup ao fechar: destrói instância existente e limpa container
        if (!is_open) {
            if (window.__gvg_embedded_checkout && typeof window.__gvg_embedded_checkout.destroy === 'function') {
                try { window.__gvg_embedded_checkout.destroy(); } catch(_) {}
            }
            window.__gvg_embedded_checkout = null;
            const node = document.getElementById('stripe-embedded-checkout');
            if (node) { node.innerHTML = ''; }
            return window.dash_clientside.no_update;
        }
        if (!session) {
            return window.dash_clientside.no_update;
        }
        if (!publishableKey) {
            return 'Chave pública do Stripe ausente';
        }
        // Pequeno atraso para garantir carregamento dos scripts da CDN do Stripe
        await new Promise((resolve) => setTimeout(resolve, 400));
        if (!window.Stripe) {
            return 'Stripe.js indisponível';
        }
        try {
            const stripe = window.Stripe(publishableKey);
            if (!stripe || !stripe.initEmbeddedCheckout) {
                return 'Embedded Checkout indisponível';
            }
            // Se já há uma instância prévia, destrói antes de criar outra
            if (window.__gvg_embedded_checkout && typeof window.__gvg_embedded_checkout.destroy === 'function') {
                try { window.__gvg_embedded_checkout.destroy(); } catch(_) {}
            }
            const checkout = await stripe.initEmbeddedCheckout({ clientSecret: session.client_secret });
            window.__gvg_embedded_checkout = checkout;
            const mountNode = document.getElementById('stripe-embedded-checkout');
            if (mountNode) {
                mountNode.innerHTML = '';
                checkout.mount('#stripe-embedded-checkout');
            }
            return '';
        } catch(e) {
            return (e && e.message) || 'Erro ao montar Embedded Checkout';
        }
    }
    """,
    Output('stripe-payment-error', 'children'),
    Input('stripe-payment-modal', 'is_open'),
    State('store-elements-session', 'data'),
    State('store-stripe-pk', 'data')
)

# Removido callback legado de confirmação Elements (stripe-payment-confirm),
# pois o fluxo atual usa apenas o Embedded Checkout. Isso evita Input inexistente no layout.

@app.callback(
    Output('stripe-payment-modal', 'is_open', allow_duplicate=True),
    Output('store-payment-event', 'data', allow_duplicate=True),
    Input('store-plan-action', 'data'),
    State('store-auth', 'data'),
    prevent_initial_call=True
)
def handle_embedded_result(action_data, auth_data):
    if not action_data or action_data.get('action') != 'open_embedded':
        raise PreventUpdate
    user = (auth_data or {}).get('user') or {}
    uid = user.get('uid') or ''
    if not uid:
        raise PreventUpdate
    # Embedded Checkout usa webhooks para aplicar o plano; aqui apenas fechamos quando a ação for processada por outro callback.
    raise PreventUpdate

# =====================================================================================
# Autenticação: callbacks de overlay, views e ações
# =====================================================================================
@app.callback(
    Output('header-user-badge', 'children'),
    Output('header-user-badge', 'title'),
    Input('store-auth', 'data')
)
def reflect_header_badge(auth_data):
    data = auth_data or {}
    user = data.get('user') or {}
    name = (user.get('name') or '').strip() or 'Usuário'
    email = (user.get('email') or '').strip()
    # Construir iniciais: primeira letra do primeiro nome + primeira letra do último sobrenome
    initials = ''
    try:
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            initials = parts[0][:2].upper()
        else:
            initials = 'US'
    except Exception:
        initials = 'US'
    title = f"{name} ({email})" if email else name
    return initials, title

# =============================
# Modal Planos e Limites
# =============================
@app.callback(
    Output('planos-modal', 'is_open'),
    Input('user-menu-item-planos', 'n_clicks'),
    Input('planos-modal-close', 'n_clicks'),
    State('planos-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_planos_modal(open_from_menu, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trig = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig == 'user-menu-item-planos' and open_from_menu:
        return True
    if trig == 'planos-modal-close' and close_clicks:
        return False
    return is_open

@app.callback(
    Output('planos-modal-body', 'children'),
    Output('header-plan-badge', 'children', allow_duplicate=True),
    Output('header-plan-badge', 'style', allow_duplicate=True),
    Input('planos-modal', 'is_open'),
    State('store-planos-data', 'data'),
    prevent_initial_call=True
)
def load_planos_content(is_open, planos_data):
    """Renderiza modal de planos usando dados pré-carregados da store."""
    if not is_open:
        raise PreventUpdate
    
    # Ler dados da store (já carregados na inicialização)
    if not planos_data:
        raise PreventUpdate
    
    plans = planos_data.get('plans', [])
    current_code = planos_data.get('current_code', 'FREE')
    uid = planos_data.get('uid', '')
    
    # Mapa de descrições (fallback interno)
    desc_map = {
        'FREE': 'Uso básico para avaliação',
        'PLUS': 'Uso individual intensivo',
        'PRO': 'Equipes menores',
        'CORP': 'Uso corporativo/alto volume'
    }
    def fmt_num(v):
        try:
            iv = int(v)
            return f"{iv:,}".replace(',', '.')
        except Exception:
            try:
                fv = float(v)
                return ("{:.0f}".format(fv)).replace(',', '.')
            except Exception:
                return str(v)
    cards = []
    icon_map = [
        ('fa-search', 'Consultas', 'limit_consultas_per_day', True),
        ('fa-file-alt', 'Resumos', 'limit_resumos_per_day', True),
        ('fa-calendar', 'Boletins', 'limit_boletim_per_day', True),
        ('fa-bookmark', 'Favoritos', 'limit_favoritos_capacity', False),
    ]
    for p in plans:
        code = (p.get('code') or '').upper()
        price = (p.get('price_cents') or 0)/100
        is_current = code == current_code
        card_style = styles['planos_card_current'] if is_current else styles['planos_card']
        desc = p.get('desc') or desc_map.get(code) or ''
        limit_rows = []
        for icon, label, field, per_day in icon_map:
            raw = p.get(field, '-')
            display = '-' if raw in (None, '', '-') else fmt_num(raw)
            txt = f"{label}: {display}{' por dia' if per_day else ''}"
            limit_rows.append(html.Div([
                html.I(className=f"fas {icon}"),
                html.Span(txt, style=styles['planos_limit_item'])
            ], style=styles['planos_limit_row']))
        limits_nodes = html.Div(limit_rows, style=styles['planos_limits_list'])
        price_label = html.Div(
            f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
            style=styles['planos_price']
        )
        if is_current:
            btn = html.Button('Seu plano', disabled=True, title='Plano atual', style=styles['planos_btn_current'])
        else:
            # Só permite upgrade para planos com price maior; downgrade para menores
            try:
                current_plan = [cp for cp in plans if (cp.get('code') or '').upper()==current_code][0]
                current_price = (current_plan.get('price_cents') or 0)
            except Exception:
                current_price = 0
            action_type = 'upgrade' if ((p.get('price_cents') or 0) > current_price) else 'downgrade'
            btn = html.Button('Upgrade' if action_type=='upgrade' else 'Downgrade',
                              id={'type': 'plan-action-btn', 'code': code, 'action': action_type},
                              disabled=False,
                              title=('Mudar plano'),
                              style=styles['planos_btn_upgrade'])
        cards.append(html.Div([
            html.Div(code, style=styles.get(f'plan_badge_{code.lower()}', styles['plan_badge_free'])),
            html.Div(p.get('name') or code, style={'fontWeight': '600', 'fontSize': '14px'}),
            html.Div(desc, style=styles['planos_desc']),
            limits_nodes,
            price_label,
            btn
        ], style=card_style))
    
    # Obter consumo da store (já carregado na inicialização)
    usage = planos_data.get('usage')
    usage_section = None
    if usage:
        usage_section = html.Div([
            html.H6('Seu Uso Hoje:', style={'margin': '0 0 12px 0', 'fontSize': '13px', 'fontWeight': '600', 'color': '#424242'}),
            _render_usage_bars(usage)
        ], style={'marginBottom': '24px', 'padding': '16px', 'backgroundColor': '#f5f5f5', 'borderRadius': '8px'})
    
    # Preparar atualização do badge com plano real
    badge_style = styles.get(f'plan_badge_{current_code.lower()}', styles.get('plan_badge_free'))
    badge_style_with_margin = {**badge_style, 'marginRight': '10px'}
    
    # Montar retorno: seção de consumo + cards de planos + badge atualizado
    modal_content = html.Div([
        usage_section,
        html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    ]) if usage_section else html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    
    return modal_content, current_code, badge_style_with_margin


@app.callback(
    Output('url', 'href', allow_duplicate=True),
    Output('header-plan-badge', 'children', allow_duplicate=True),
    Output('header-plan-badge', 'style', allow_duplicate=True),
    Output('planos-modal-body', 'children', allow_duplicate=True),
    Output('store-plan-action', 'data'),
    Output('store-planos-data', 'data', allow_duplicate=True),
    Input({'type': 'plan-action-btn', 'code': ALL, 'action': ALL}, 'n_clicks'),
    State('store-auth', 'data'),
    State('planos-modal-body', 'children'),
    State('store-planos-data', 'data'),
    prevent_initial_call=True
)
def handle_plan_action(n_clicks_list, auth_data, current_children, planos_data):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    # Verificar se algum botão foi realmente clicado (n_clicks > 0)
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    
    trig = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        comp = json.loads(trig)
    except Exception:
        raise PreventUpdate
    
    code = comp.get('code')
    action = comp.get('action')
    user = (auth_data or {}).get('user') or {}
    uid = user.get('uid') or ''
    email = user.get('email') or ''
    name = user.get('name') or user.get('email', '').split('@')[0]
    
    if not uid or not code or not action:
        raise PreventUpdate
    try:
        dbg('BILL', f"[handle_plan_action] click uid={uid} code={code} action={action}")
    except Exception:
        pass
    
    # Se for UPGRADE para plano pago (PLUS, PRO, CORP) → abrir Stripe Embedded Checkout no modal
    if action == 'upgrade' and code in ('PLUS', 'PRO', 'CORP'):
        try:
            from gvg_billing import create_checkout_embedded_session  # type: ignore
            try:
                dbg('BILL', f"[handle_plan_action] creating embedded session uid={uid} plan={code}")
            except Exception:
                pass
            res = create_checkout_embedded_session(uid, code, email, name)
            if res.get('error') or not res.get('client_secret'):
                try:
                    dbg('BILL', f"[handle_plan_action] embedded error: {res.get('error')}")
                except Exception:
                    pass
                raise PreventUpdate
            emb = {
                'client_secret': res.get('client_secret'),
                'checkout_session_id': res.get('checkout_session_id'),
                'plan_code': code
            }
            try:
                dbg('BILL', f"[handle_plan_action] store-plan-action <- open_embedded sid={emb['checkout_session_id']} has_secret={bool(emb['client_secret'])}")
            except Exception:
                pass
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {'action': 'open_embedded', 'session': emb}, {**(planos_data or {}), 'pending_embedded': emb}
        except Exception as e:
            try:
                dbg('BILL', f"[handle_plan_action] exception creating embedded: {e}")
            except Exception:
                pass
            raise PreventUpdate
    
    # Se for downgrade ou upgrade para FREE → aplicar direto
    result = None
    if action == 'downgrade':
        result = upgrade_plan(uid, code)
    elif action == 'upgrade' and code == 'FREE':
        result = upgrade_plan(uid, code)
    else:
        raise PreventUpdate
    
    # Obter novo código do plano e atualizar badge
    new_code = (result.get('plan_code') if isinstance(result, dict) else None) or code
    new_code = new_code.upper()
    new_badge_style = styles.get(f'plan_badge_{new_code.lower()}', styles.get('plan_badge_free'))
    new_badge_style_with_margin = {**new_badge_style, 'marginRight': '10px'}
    
    # Reconstruir conteúdo do modal para atualizar o card ativo instantaneamente
    # Reutilizar a lógica de load_planos_content
    try:
        plans = get_system_plans()
    except Exception:
        plans = []
    fallback = [
        {'code': 'FREE', 'name': 'Free', 'desc': 'Uso básico para avaliação', 'price_cents': 0, 'limit_consultas_per_day': 5, 'limit_resumos_per_day': 1, 'limit_boletim_per_day': 1, 'limit_favoritos_capacity': 10},
        {'code': 'PLUS', 'name': 'Plus', 'desc': 'Uso individual intensivo', 'price_cents': 4900, 'limit_consultas_per_day': 30, 'limit_resumos_per_day': 40, 'limit_boletim_per_day': 4, 'limit_favoritos_capacity': 200},
        {'code': 'PRO', 'name': 'Professional', 'desc': 'Equipes menores', 'price_cents': 19900, 'limit_consultas_per_day': 100, 'limit_resumos_per_day': 400, 'limit_boletim_per_day': 10, 'limit_favoritos_capacity': 2000},
        {'code': 'CORP', 'name': 'Corporation', 'desc': 'Uso corporativo/alto volume', 'price_cents': 99900, 'limit_consultas_per_day': 1000, 'limit_resumos_per_day': 4000, 'limit_boletim_per_day': 100, 'limit_favoritos_capacity': 20000},
    ]
    if not plans:
        plans = fallback
    desc_map = {p['code']: p.get('desc') for p in fallback}
    def fmt_num(v):
        try:
            iv = int(v)
            return f"{iv:,}".replace(',', '.')
        except Exception:
            try:
                fv = float(v)
                return ("{:.0f}".format(fv)).replace(',', '.')
            except Exception:
                return str(v)
    cards = []
    icon_map = [
        ('fa-search', 'Consultas', 'limit_consultas_per_day', True),
        ('fa-file-alt', 'Resumos', 'limit_resumos_per_day', True),
        ('fa-calendar', 'Boletins', 'limit_boletim_per_day', True),
        ('fa-bookmark', 'Favoritos', 'limit_favoritos_capacity', False),
    ]
    for p in plans:
        p_code = (p.get('code') or '').upper()
        price = (p.get('price_cents') or 0)/100
        is_current = p_code == new_code
        card_style = styles['planos_card_current'] if is_current else styles['planos_card']
        desc = p.get('desc') or desc_map.get(p_code) or ''
        limit_rows = []
        for icon, label, field, per_day in icon_map:
            raw = p.get(field, '-')
            display = '-' if raw in (None, '', '-') else fmt_num(raw)
            txt = f"{label}: {display}{' por dia' if per_day else ''}"
            limit_rows.append(html.Div([
                html.I(className=f"fas {icon}"),
                html.Span(txt, style=styles['planos_limit_item'])
            ], style=styles['planos_limit_row']))
        limits_nodes = html.Div(limit_rows, style=styles['planos_limits_list'])
        price_label = html.Div(
            f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
            style=styles['planos_price']
        )
        if is_current:
            btn = html.Button('Seu plano', disabled=True, title='Plano atual', style=styles['planos_btn_current'])
        else:
            try:
                current_plan = [cp for cp in plans if (cp.get('code') or '').upper()==new_code][0]
                current_price = (current_plan.get('price_cents') or 0)
            except Exception:
                current_price = 0
            action_type = 'upgrade' if ((p.get('price_cents') or 0) > current_price) else 'downgrade'
            btn = html.Button('Upgrade' if action_type=='upgrade' else 'Downgrade',
                              id={'type': 'plan-action-btn', 'code': p_code, 'action': action_type},
                              disabled=False,
                              title=('Mudar plano'),
                              style=styles['planos_btn_upgrade'])
        cards.append(html.Div([
            html.Div(p_code, style=styles.get(f'plan_badge_{p_code.lower()}', styles['plan_badge_free'])),
            html.Div(p.get('name') or p_code, style={'fontWeight': '600', 'fontSize': '14px'}),
            html.Div(desc, style=styles['planos_desc']),
            limits_nodes,
            price_label,
            btn
        ], style=card_style))
    
    # Obter consumo atualizado
    usage_section = None
    if uid:
        try:
            from gvg_limits import get_usage_status
            usage = get_usage_status(uid)
            if usage:
                usage_section = html.Div([
                    html.H6('Seu Uso Hoje:', style={'margin': '0 0 12px 0', 'fontSize': '13px', 'fontWeight': '600', 'color': '#424242'}),
                    _render_usage_bars(usage)
                ], style={'marginBottom': '24px', 'padding': '16px', 'backgroundColor': '#f5f5f5', 'borderRadius': '8px'})
        except Exception:
            pass
    
    new_modal_content = html.Div([
        usage_section,
        html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    ]) if usage_section else html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    
    # Atualizar a store com o novo código do plano
    updated_planos_data = {**planos_data, 'current_code': new_code}
    if uid and usage:
        updated_planos_data['usage'] = usage
    
    # Retornar com dash.no_update para url.href (não redirecionar)
    return dash.no_update, new_code, new_badge_style_with_margin, new_modal_content, {'action': action, 'code': code, 'status': 'ok', 'plan': new_code}, updated_planos_data

# =============================
# Pós-pagamento Stripe: hidratar stores sem reload
# =============================
@app.callback(
    Output('store-payment-event', 'data'),
    Input('stripe-success-input', 'value'),
    State('store-auth', 'data'),
    prevent_initial_call=True
)
def capture_payment_success(session_id, auth_data):
    if not session_id:
        raise PreventUpdate
    user = (auth_data or {}).get('user') or {}
    uid = user.get('uid') or ''
    if not uid:
        raise PreventUpdate
    try:
        dbg('BILL', f"[postpay] capture success sid={session_id} uid={uid}")
    except Exception:
        pass
    # Hidratar settings direto (evita request externo por enquanto)
    try:
        from gvg_billing import get_user_settings, get_usage_snapshot  # type: ignore
        settings = get_user_settings(uid)
        usage = get_usage_snapshot(uid)
        return {
            'session_id': session_id,
            'uid': uid,
            'plan_code': settings.get('plan_code'),
            'limits': settings.get('limits'),
            'usage': usage.get('usage'),
            'ts': _dt.datetime.utcnow().isoformat()
        }
    except Exception as e:
        try:
            dbg('BILL', f"[postpay] erro hidratar plano: {e}")
        except Exception:
            pass
        raise PreventUpdate


@app.callback(
    Output('header-plan-badge', 'children', allow_duplicate=True),
    Output('header-plan-badge', 'style', allow_duplicate=True),
    Output('store-planos-data', 'data', allow_duplicate=True),
    Output('planos-modal-body', 'children', allow_duplicate=True),
    Input('store-payment-event', 'data'),
    State('store-planos-data', 'data'),
    State('planos-modal', 'is_open'),
    prevent_initial_call=True
)
def refresh_plan_after_payment(event_data, planos_data, modal_open):
    if not event_data:
        raise PreventUpdate
    try:
        dbg('BILL', f"[postpay] refresh badge plan={event_data.get('plan_code')} modal_open={modal_open}")
    except Exception:
        pass
    plan_code = (event_data.get('plan_code') or 'FREE').upper()
    # Atualizar badge
    badge_style = styles.get(f'plan_badge_{plan_code.lower()}', styles.get('plan_badge_free'))
    badge_style_with_margin = {**badge_style, 'marginRight': '10px'}
    # Atualizar store-planos-data
    updated = dict(planos_data or {})
    updated['current_code'] = plan_code
    if event_data.get('usage'):
        updated['usage'] = event_data.get('usage')
    # Se modal não está aberto, não re-renderizar body
    if not modal_open:
        return plan_code, badge_style_with_margin, updated, dash.no_update

    # Habilitar/Desabilitar timers com base no modal e sessão
    app.clientside_callback(
        """
        function(is_open, session) {
            // habilita polling quando modal abre com sessão válida; desabilita ao fechar
            const enable = !!(is_open && session && session.client_secret);
            return [enable ? false : true, enable ? 0 : 0, true, 0];
        }
        """,
        Output('payment-check-interval', 'disabled'),
        Output('payment-check-interval', 'n_intervals'),
        Output('payment-autoclose-interval', 'disabled'),
        Output('payment-autoclose-interval', 'n_intervals'),
        Input('stripe-payment-modal', 'is_open'),
        State('store-elements-session', 'data'),
    )

    # Poll leve do plan_status e emitir evento de pagamento quando houver mudança de plano
    app.clientside_callback(
        """
        async function(n, auth, planos) {
            if (typeof n !== 'number' || n < 0) return window.dash_clientside.no_update;
            const user = (auth && auth.user) || {};
            const uid = user.uid || '';
            if (!uid) return window.dash_clientside.no_update;
            const current = (planos && planos.current_code) ? String(planos.current_code).toUpperCase() : 'FREE';
            try {
                const resp = await fetch(`/api/plan_status?uid=${encodeURIComponent(uid)}`);
                if (!resp.ok) return window.dash_clientside.no_update;
                const data = await resp.json();
                const plan_code = (data && data.plan_code) ? String(data.plan_code).toUpperCase() : null;
                if (!plan_code || plan_code === current) {
                    return window.dash_clientside.no_update;
                }
                // Detected change: disparar store-payment-event e iniciar autoclose; parar polling
                const payload = {
                    uid: uid,
                    plan_code: plan_code,
                    limits: data.limits || {},
                    usage: (data.usage || {}),
                    ts: new Date().toISOString()
                };
                return [payload, true, 0, false, 0];
            } catch(_) { return window.dash_clientside.no_update; }
        }
        """,
        Output('store-payment-event', 'data'),
        Output('payment-check-interval', 'disabled'),
        Output('payment-check-interval', 'n_intervals'),
        Output('payment-autoclose-interval', 'disabled'),
        Output('payment-autoclose-interval', 'n_intervals'),
        Input('payment-check-interval', 'n_intervals'),
        State('store-auth', 'data'),
        State('store-planos-data', 'data'),
    )

    # Fechamento automático do modal após 5s (5 ticks)
    app.clientside_callback(
        """
        function(n, is_open) {
            if (is_open !== true) return window.dash_clientside.no_update;
            if (typeof n !== 'number') return window.dash_clientside.no_update;
            if (n >= 5) {
                return [false, true, 0];
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('stripe-payment-modal', 'is_open'),
        Output('payment-autoclose-interval', 'disabled'),
        Output('payment-autoclose-interval', 'n_intervals'),
        Input('payment-autoclose-interval', 'n_intervals'),
        State('stripe-payment-modal', 'is_open'),
    )
    # Re-renderizar cards (reutilizar lógica simplificada)
    try:
        from gvg_billing import get_system_plans  # type: ignore
        plans = get_system_plans()
    except Exception:
        plans = []
    fallback = [
        {'code': 'FREE', 'name': 'Free', 'price_cents': 0, 'limit_consultas_per_day': 5, 'limit_resumos_per_day': 1, 'limit_boletim_per_day': 1, 'limit_favoritos_capacity': 10},
        {'code': 'PLUS', 'name': 'Plus', 'price_cents': 4900, 'limit_consultas_per_day': 30, 'limit_resumos_per_day': 40, 'limit_boletim_per_day': 4, 'limit_favoritos_capacity': 200},
        {'code': 'PRO', 'name': 'Professional', 'price_cents': 19900, 'limit_consultas_per_day': 100, 'limit_resumos_per_day': 400, 'limit_boletim_per_day': 10, 'limit_favoritos_capacity': 2000},
        {'code': 'CORP', 'name': 'Corporation', 'price_cents': 99900, 'limit_consultas_per_day': 1000, 'limit_resumos_per_day': 4000, 'limit_boletim_per_day': 100, 'limit_favoritos_capacity': 20000},
    ]
    if not plans:
        plans = fallback
    def fmt_num(v):
        try:
            iv = int(v); return f"{iv:,}".replace(',', '.')
        except Exception:
            try:
                fv = float(v); return ("{:.0f}".format(fv)).replace(',', '.')
            except Exception:
                return str(v)
    icon_map = [
        ('fa-search', 'Consultas', 'limit_consultas_per_day', True),
        ('fa-file-alt', 'Resumos', 'limit_resumos_per_day', True),
        ('fa-calendar', 'Boletins', 'limit_boletim_per_day', True),
        ('fa-bookmark', 'Favoritos', 'limit_favoritos_capacity', False),
    ]
    cards = []
    for p in plans:
        code = (p.get('code') or '').upper()
        price = (p.get('price_cents') or 0)/100
        is_current = code == plan_code
        card_style = styles['planos_card_current'] if is_current else styles['planos_card']
        limit_rows = []
        for icon, label, field, per_day in icon_map:
            raw = p.get(field, '-')
            display = '-' if raw in (None, '', '-') else fmt_num(raw)
            txt = f"{label}: {display}{' por dia' if per_day else ''}"
            limit_rows.append(html.Div([
                html.I(className=f"fas {icon}"),
                html.Span(txt, style=styles['planos_limit_item'])
            ], style=styles['planos_limit_row']))
        limits_nodes = html.Div(limit_rows, style=styles['planos_limits_list'])
        price_label = html.Div(
            f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
            style=styles['planos_price']
        )
        if is_current:
            btn = html.Button('Seu plano', disabled=True, title='Plano atual', style=styles['planos_btn_current'])
        else:
            try:
                current_plan = [cp for cp in plans if (cp.get('code') or '').upper()==plan_code][0]
                current_price = (current_plan.get('price_cents') or 0)
            except Exception:
                current_price = 0
            action_type = 'upgrade' if ((p.get('price_cents') or 0) > current_price) else 'downgrade'
            btn = html.Button('Upgrade' if action_type=='upgrade' else 'Downgrade',
                              id={'type': 'plan-action-btn', 'code': code, 'action': action_type},
                              disabled=False,
                              title=('Mudar plano'),
                              style=styles['planos_btn_upgrade'])
        cards.append(html.Div([
            html.Div(code, style=styles.get(f'plan_badge_{code.lower()}', styles['plan_badge_free'])),
            html.Div(p.get('name') or code, style={'fontWeight': '600', 'fontSize': '14px'}),
            limits_nodes,
            price_label,
            btn
        ], style=card_style))
    usage_section = None
    if event_data.get('usage'):
        usage_section = html.Div([
            html.H6('Seu Uso Hoje:', style={'margin': '0 0 12px 0', 'fontSize': '13px', 'fontWeight': '600', 'color': '#424242'}),
            _render_usage_bars(event_data.get('usage'))
        ], style={'marginBottom': '24px', 'padding': '16px', 'backgroundColor': '#f5f5f5', 'borderRadius': '8px'})
    modal_content = html.Div([
        usage_section,
        html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    ]) if usage_section else html.Div(cards, className='planos-cards-wrapper', style={'display': 'flex', 'flexWrap': 'nowrap', 'gap': '16px'})
    return plan_code, badge_style_with_margin, updated, modal_content


# =========================
# Feature flag: ativar/desativar Filtros Avançados e V2
# =========================
import os as _os


def _build_sql_conditions_from_ui_filters(f: dict | None) -> list[str]:
    """Converte a store de filtros avançados em lista de strings SQL (V2 filter[]).
    Campos suportados: pncp (exact), orgao (ILIKE), cnpj (exact), uf (exact), municipio (ILIKE),
    modalidade_id (exact), período por campo (encerramento/abertura/publicacao) com DatePickerRange.
    """
    if not f or not isinstance(f, dict):
        return []
    out: list[str] = []
    pncp = (f.get('pncp') or '').strip() if f.get('pncp') else ''
    orgao = (f.get('orgao') or '').strip() if f.get('orgao') else ''
    cnpj = (f.get('cnpj') or '').strip() if f.get('cnpj') else ''
    uf_val = f.get('uf') if isinstance(f, dict) else None
    municipio = (f.get('municipio') or '').strip() if f.get('municipio') else ''
    modalidade_id = f.get('modalidade_id') if f.get('modalidade_id') is not None else None
    modo_id = f.get('modo_id') if f.get('modo_id') is not None else None
    date_field = (f.get('date_field') or 'encerramento').strip()
    ds = (f.get('date_start') or '').strip() if f.get('date_start') else ''
    de = (f.get('date_end') or '').strip() if f.get('date_end') else ''

    if pncp:
        out.append(f"c.numero_controle_pncp = '{pncp}'")
    if orgao:
        # Procurar tanto na razão social do órgão quanto no nome da unidade do órgão
        _org = orgao.replace("'", "''").replace('%', '%%')
        out.append(
            f"( c.orgao_entidade_razao_social ILIKE '%{_org}%' OR c.unidade_orgao_nome_unidade ILIKE '%{_org}%' )"
        )
    if cnpj:
        out.append(f"c.orgao_entidade_cnpj = '{cnpj}'")
    # UF pode ser string única ou lista
    if isinstance(uf_val, list):
        ufs = [str(u).strip() for u in uf_val if str(u).strip()]
        if ufs:
            in_list = ", ".join([f"'{u.replace("'","''")}'" for u in ufs])
            out.append(f"c.unidade_orgao_uf_sigla IN ({in_list})")
    else:
        uf = (str(uf_val).strip() if uf_val is not None else '')
        if uf:
            out.append(f"c.unidade_orgao_uf_sigla = '{uf.replace("'","''")}'")
    if municipio:
        # Suporta múltiplos municípios separados por vírgula (OR)
        parts = [p.strip() for p in municipio.split(',') if p and p.strip()]
        if parts:
            ors = [f"c.unidade_orgao_municipio_nome ILIKE '%{p.replace("'","''").replace('%','%%')}%'" for p in parts]
            out.append("( " + " OR ".join(ors) + " )")
    # Modalidade pode ser string única ou lista
    if isinstance(modalidade_id, list):
        mods = [str(x).strip() for x in modalidade_id if str(x).strip()]
        if mods:
            in_list = ", ".join([f"'{m.replace("'", "''")}'" for m in mods])
            out.append(f"c.modalidade_id IN ({in_list})")
    else:
        mod = (str(modalidade_id).strip() if modalidade_id is not None else '')
        if mod:
            out.append(f"c.modalidade_id = '{mod.replace("'","''")}'")
    # Modo de disputa: string ou lista
    if isinstance(modo_id, list):
        modos = [str(x).strip() for x in modo_id if str(x).strip()]
        if modos:
            in_list2 = ", ".join([f"'{m.replace("'", "''")}'" for m in modos])
            out.append(f"c.modo_disputa_id IN ({in_list2})")
    else:
        md = (str(modo_id).strip() if modo_id is not None else '')
        if md:
            out.append(f"c.modo_disputa_id = '{md.replace("'","''")}'")
    # Date range
    col = 'data_encerramento_proposta'
    if date_field == 'abertura':
        col = 'data_abertura_proposta'
    elif date_field == 'publicacao':
        col = 'data_inclusao'
    if ds and de:
        out.append(
            f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') BETWEEN to_date('{ds}','YYYY-MM-DD') AND to_date('{de}','YYYY-MM-DD')"
        )
    elif ds:
        out.append(
            f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') >= to_date('{ds}','YYYY-MM-DD')"
        )
    elif de:
        out.append(
            f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') <= to_date('{de}','YYYY-MM-DD')"
        )
    return out

def _has_any_filter(f: dict | None) -> bool:
    """Retorna True se algum filtro foi preenchido (ignorando apenas date_field)."""
    if not f or not isinstance(f, dict):
        return False
    for k, v in f.items():
        if k == 'date_field':
            continue
        if isinstance(v, str) and v.strip():
            return True
        if v not in (None, '', []):
            return True
    return False

def _sql_only_search(sql_conditions: list[str], limit: int, filter_expired: bool) -> list[dict]:
    """Executa busca direta na tabela contratacao aplicando apenas condições SQL.

    Retorna lista de resultados no formato esperado pela UI (details em snake_case + aliases).
    """
    # Centraliza acesso ao BD via wrappers com métricas [DB]
    try:
        from gvg_database import db_fetch_all  # type: ignore
    except Exception:
        db_fetch_all = None  # type: ignore
    from gvg_schema import get_contratacao_core_columns, normalize_contratacao_row, project_result_for_output
    results: list[dict] = []
    cols = get_contratacao_core_columns('c')
    # Sanitizar condições para escapar '%' e padronizar parênteses
    sanitized = _sanitize_sql_conditions(sql_conditions or [], context='generic')
    where_parts = []
    for cond in sanitized:
        if isinstance(cond, str) and cond.strip():
            where_parts.append(f"( {cond.strip()} )")
    if filter_expired:
        where_parts.append("(to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= current_date OR c.data_encerramento_proposta IS NULL OR c.data_encerramento_proposta='')")
    where_sql = ("\nWHERE " + "\n  AND ".join(where_parts)) if where_parts else ""
    sql = (
        "SELECT\n  " + ",\n  ".join(cols) + "\n" +
        "FROM contratacao c" + where_sql + "\n" +
        "LIMIT %s"
    )
    if SQL_DEBUG:
        dbg('SQL', 'SQL-only query montada (sem embeddings).')
        dbg('SQL', sql)
    try:
        rows = db_fetch_all(sql, (int(limit or 30),), as_dict=True, ctx="GSB._sql_only_search") if db_fetch_all else []
    except Exception as e:
        try:
            dbg('SQL', f"Erro na busca SQL-only: {e}")
        except Exception:
            pass
        rows = []
    for rec in (rows or []):
        try:
            norm = normalize_contratacao_row(rec)
            details = project_result_for_output(norm)
            try:
                _augment_aliases(details)
            except Exception:
                pass
            pid = details.get('numero_controle_pncp')
            results.append({
                'id': pid,
                'numero_controle': pid,
                'similarity': 0.0,
                'rank': 0,
                'details': details,
            })
        except Exception:
            continue
    return results


def _restrict_results_by_sql(sql_conditions: list[str], current_results: list[dict], limit: int, filter_expired: bool) -> list[dict]:
    """Intersecta resultados atuais com um WHERE SQL, preservando ordem/rank.

    - Executa uma query apenas para obter o conjunto de PNCP válidos segundo as condições.
    - Intersecta mantendo a ordem dos resultados atuais.
    """
    if not current_results:
        return []
    try:
        from gvg_database import db_fetch_all  # type: ignore
    except Exception:
        db_fetch_all = None  # type: ignore
    from gvg_schema import PRIMARY_KEY
    # Sanitizar condições também aqui
    sanitized = _sanitize_sql_conditions(sql_conditions or [], context='generic')
    where_parts = []
    for cond in sanitized:
        if isinstance(cond, str) and cond.strip():
            where_parts.append(f"( {cond.strip()} )")
    if filter_expired:
        where_parts.append("(to_date(NULLIF(c.data_encerramento_proposta,'') ,'YYYY-MM-DD') >= current_date OR c.data_encerramento_proposta IS NULL OR c.data_encerramento_proposta='')")
    where_sql = ("\nWHERE " + "\n  AND ".join(where_parts)) if where_parts else ""
    sql = f"SELECT c.{PRIMARY_KEY} FROM contratacao c{where_sql} LIMIT %s"
    valid: set[str] = set()
    try:
        rows = db_fetch_all(sql, (int(limit or 30),), as_dict=True, ctx="GSB._restrict_results_by_sql") if db_fetch_all else []
        for rec in (rows or []):
            v = rec.get(PRIMARY_KEY)
            if v is not None:
                valid.add(str(v))
    except Exception as e:
        try:
            dbg('SQL', f"Pós-filtro falhou: {e}")
        except Exception:
            pass
        return current_results[:limit]
    # Interseção preservando ordem
    out = []
    for r in current_results:
        rid = str(r.get('id') or r.get('numero_controle'))
        if rid in valid:
            out.append(r)
        if len(out) >= limit:
            break
    return out


# =====================================================================================
# Boletins: callbacks (habilitar botão, toggle, salvar, listar, remover)
# =====================================================================================
@app.callback(
    Output('boletim-toggle-btn', 'disabled'),
    Output('boletim-toggle-btn', 'style'),
    Input('query-input', 'value'),
    Input('boletim-collapse', 'is_open'),
    prevent_initial_call=False
)
def enable_boletim_button(q, is_open):
    enabled = bool(q and isinstance(q, str) and q.strip())
    base_style = styles['arrow_button_inverted'] if is_open else styles['arrow_button']
    style = {**base_style, 'marginTop': '6px', 'opacity': 1.0 if enabled else 0.4}
    return (not enabled), style

@app.callback(
    Output('boletim-multidiario-slots', 'value'),
    Output('boletim-multidiario-slots', 'disabled'),
    Output('boletim-semanal-dias', 'value'),
    Output('boletim-semanal-dias', 'disabled'),
    Input('boletim-freq', 'value'),
    prevent_initial_call=False
)
def sync_boletim_controls(freq):
    # UI simplificada: horários e canais escondidos; aqui apenas garantimos defaults coerentes.
    all_days = ['seg','ter','qua','qui','sex']
    if freq == 'DIARIO':
        return ['manha'], True, all_days, True
    # SEMANAL
    return ['manha'], True, ['seg'], False

@app.callback(
    Output('boletim-collapse', 'is_open'),
    Output('store-boletim-open', 'data'),
    Input('boletim-toggle-btn', 'n_clicks'),
    State('store-boletim-open', 'data'),
    prevent_initial_call=True
)
def toggle_boletim_panel(n, is_open):
    if not n:
        raise PreventUpdate
    new_state = not bool(is_open)
    return new_state, new_state

@app.callback(
    Output('boletim-save-btn', 'disabled'),
    Input('boletim-freq', 'value'),
    Input('boletim-semanal-dias', 'value'),
    Input('query-input', 'value'),
    Input('store-boletins', 'data'),
    prevent_initial_call=False
)
def validate_boletim(freq, dias, query_text, boletins):
    # Regras de desabilitação (True = desabilita)
    q = (query_text or '').strip()
    if len(q) < 3:
        return True
    if freq == 'SEMANAL' and not (dias and len(dias) > 0):
        return True
    # Demais campos estão fixos por default nesta fase simplificada
    # Duplicidade por texto (case-insensitive, trim)
    try:
        qn = q.lower()
        for b in (boletins or []):
            bt = ((b.get('query_text') or '').strip()).lower()
            if bt == qn:
                return True
    except Exception:
        pass
    # Caso válido => habilita (False)
    return False

@app.callback(
    Output('boletim-save-btn', 'title'),
    Output('boletim-save-btn', 'style'),
    Input('boletim-freq', 'value'),
    Input('boletim-semanal-dias', 'value'),
    Input('query-input', 'value'),
    Input('store-boletins', 'data'),
    prevent_initial_call=False
)
def refresh_boletim_save_visuals(freq, dias, query_text, boletins):
    """Atualiza hint (title) e opacidade do botão '+' para indicar estado.

    Mantém o estilo base e o ícone '+', apenas ajustando a opacidade.
    """
    base = dict(styles['arrow_button'])
    q = (query_text or '').strip()
    # Mensagens de orientação
    if len(q) < 3:
        base.update({'opacity': 0.4})
        title = 'Digite uma consulta (mín. 3 caracteres)'
        return title, base
    if freq == 'SEMANAL' and not (dias and len(dias) > 0):
        base.update({'opacity': 0.4})
        title = 'Selecione ao menos um dia'
        return title, base
    # Campos avançados estão com defaults
    # Duplicado?
    try:
        qn = q.lower()
        for b in (boletins or []):
            bt = ((b.get('query_text') or '').strip()).lower()
            if bt == qn:
                base.update({'opacity': 0.4})
                title = 'Já salvo para esta consulta'
                return title, base
    except Exception:
        pass
    # Válido e não duplicado
    base.update({'opacity': 1.0})

    return 'Salvar boletim', base

@app.callback(
    Output('store-boletins', 'data', allow_duplicate=True),
    Output('boletim-save-btn', 'children', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('boletim-save-btn', 'n_clicks'),
    State('query-input', 'value'),
    State('boletim-freq', 'value'),
    State('boletim-multidiario-slots', 'value'),
    State('boletim-semanal-dias', 'value'),
    State('boletim-channels', 'value'),
    State('search-type', 'value'),
    State('search-approach', 'value'),
    State('relevance-level', 'value'),
    State('sort-mode', 'value'),
    State('max-results', 'value'),
    State('top-categories', 'value'),
    State('toggles', 'value'),
    State('store-search-filters', 'data'),
    State('store-boletins', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True
)
def save_boletim(n, query, freq, slots, dias, channels, s_type, approach, rel, sort_mode, max_res, top_cat, toggles, ui_filters, current, notifications):
    if not n:
        raise PreventUpdate
    if not query or len(query.strip()) < 3:
        raise PreventUpdate
    # Campos ocultos: manter defaults
    channels = channels or ['email']
    # Evita duplicados por texto de consulta (case-insensitive, trim)
    updated_notifs = list(notifications or [])
    try:
        qn = (query or '').strip().lower()
        for b in (current or []):
            bt = ((b.get('query_text') or '').strip()).lower()
            if bt == qn:
                # Notificação de boletim duplicado
                notif = add_note(NOTIF_WARNING, "Boletim já existe para esta consulta.")
                updated_notifs.append(notif)
                return dash.no_update, html.I(className='fas fa-plus'), updated_notifs
    except Exception:
        pass
    schedule_detail = {}
    if freq == 'SEMANAL':
        schedule_detail = {'days': dias or []}
    else:
        # DIARIO
        schedule_detail = {'days': ['seg','ter','qua','qui','sex']}
    # Log essencial: tentativa de salvar
    try:
        dbg('BOLETIM', f"save: freq={freq} days={schedule_detail.get('days')} q='{(query or '').strip()[:80]}'")
    except Exception:
        pass
    config_snapshot = {
        'search_type': s_type,
        'search_approach': approach,
        'relevance_level': rel,
        'sort_mode': sort_mode,
        'max_results': max_res,
        'top_categories_count': top_cat,
    'filter_expired': 'filter_expired' in (toggles or []),
    }
    boletim_id = create_user_boletim(
        query_text=query.strip(),
        schedule_type=freq,
        schedule_detail=schedule_detail,
        channels=channels or ['email'],
        config_snapshot=config_snapshot,
        filters=ui_filters or {},
    )
    if not boletim_id:
        try:
            dbg('BOLETIM', "save: falha (id vazio)")
        except Exception:
            pass
        # Notificação de erro ao salvar
        notif = add_note(NOTIF_ERROR, "Erro ao salvar boletim. Tente novamente.")
        updated_notifs.append(notif)
        # Mantém ícone '+'
        return dash.no_update, html.I(className='fas fa-plus'), updated_notifs
    item = {
        'id': boletim_id,
        'query_text': query.strip(),
        'schedule_type': freq,
        'schedule_detail': schedule_detail,
    'channels': channels or ['email'],
    # Preenche imediatamente para a UI renderizar completo sem reload
    'config_snapshot': config_snapshot,
    'filters': ui_filters or {},
    }
    data = (current or [])
    data.insert(0, item)
    # Deduplicação defensiva
    data = _dedupe_boletins(data) if '_dedupe_boletins' in globals() else data
    # Mantém o ícone '+'; desabilitará via validate_boletim (lista agora contém a query)
    try:
        dbg('BOLETIM', f"save: ok id={boletim_id} total={len(data)}")
    except Exception:
        pass
    # Notificação de sucesso
    notif = add_note(NOTIF_SUCCESS, "Boletim criado com sucesso!")
    updated_notifs.append(notif)
    return data[:200], html.I(className='fas fa-plus'), updated_notifs

def _dedupe_boletins(items):
    """Remove duplicados por id; loga quantos removeu."""
    seen = set()
    out = []
    dupes = 0
    for b in (items or []):
        bid = b.get('id')
        if bid in seen:
            dupes += 1
            continue
        seen.add(bid)
        out.append(b)
    if dupes:
        dbg('BOLETIM', f"Boletins duplicados removidos: {dupes}")
    return out

@app.callback(
    Output('store-boletins', 'data'),
    Input('store-auth', 'data'),
)
def load_boletins_on_auth(auth_data):
    if not auth_data or auth_data.get('status') != 'auth':
        return []
    fetched = fetch_user_boletins() or []
    try:
        dbg('BOLETIM', f"load: fetched={len(fetched)}")
    except Exception:
        pass
    ui_items = []
    for b in fetched:
        ui_items.append({
            'id': b.get('id'),
            'query_text': b.get('query_text'),
            'schedule_type': b.get('schedule_type'),
            'schedule_detail': b.get('schedule_detail'),
            'channels': b.get('channels'),
            'config_snapshot': b.get('config_snapshot'),
            'created_at': b.get('created_at'),
            'last_run_at': b.get('last_run_at'),
            'filters': b.get('filters'),
        })
    return _dedupe_boletins(ui_items)

@app.callback(
    Output('store-boletins', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'boletim-delete', 'id': ALL}, 'n_clicks'),
    State('store-boletins', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True
)
def delete_boletim(n_list, boletins, notifications):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_value = ctx.triggered[0].get('value', None)
    try:
        comp = json.loads(trig_id)
    except Exception:
        raise PreventUpdate
    if comp.get('type') != 'boletim-delete':
        raise PreventUpdate
    bid = comp.get('id')
    if not bid:
        raise PreventUpdate
    # Proteção: só processa se houve clique (>0)
    if not clicked_value or clicked_value <= 0:
        #print(f"Ignorando trigger sem clique efetivo id={bid} valor={clicked_value}")
        raise PreventUpdate
    try:
        dbg('BOLETIM', f"delete: id={bid} before={len(boletins or [])}")
    except Exception:
        pass
    
    updated_notifs = list(notifications or [])
    try:
        deactivate_user_boletim(int(bid))
        #print(f"Boletim deletado id={bid} n_clicks={clicked_value}")
        new_list = [b for b in (boletins or []) if b.get('id') != bid]
        new_list = _dedupe_boletins(new_list) if '_dedupe_boletins' in globals() else new_list
        try:
            dbg('BOLETIM', f"delete: ok id={bid} after={len(new_list)}")
        except Exception:
            pass
        # Notificação de sucesso
        notif = add_note(NOTIF_INFO, "Boletim removido com sucesso.")
        updated_notifs.append(notif)
        return new_list, updated_notifs
    except Exception:
        # Notificação de erro
        notif = add_note(NOTIF_ERROR, "Erro ao remover boletim. Tente novamente.")
        updated_notifs.append(notif)
        return dash.no_update, updated_notifs

@app.callback(
    Output('boletins-list', 'children'),
    Input('store-boletins', 'data'),
    prevent_initial_call=False
)
def render_boletins_list(data):
    if not data:
        return [html.Div('Sem boletins.', style={'color': '#555', 'fontSize': '12px'})]
    # Sem logs verbosos aqui
    items = []
    for b in data:
        # 1) Configurações (mesmo padrão do histórico)
        cfg_spans = []
        try:
            snap = b.get('config_snapshot') or {}
            st = snap.get('search_type'); sa = snap.get('search_approach'); rl = snap.get('relevance_level'); sm = snap.get('sort_mode')
            mr = snap.get('max_results'); tc = snap.get('top_categories_count'); fe = snap.get('filter_expired')
            if st in SEARCH_TYPES:
                cfg_spans.append(html.Span([html.Span('Tipo: ', style={'fontWeight': 'bold'}), html.Span(SEARCH_TYPES[st]['name'], style={'fontStyle': 'italic'})]))
            if sa in SEARCH_APPROACHES:
                cfg_spans.append(html.Span([html.Span('Abordagem: ', style={'fontWeight': 'bold'}), html.Span(SEARCH_APPROACHES[sa]['name'], style={'fontStyle': 'italic'})]))
            if rl in RELEVANCE_LEVELS:
                cfg_spans.append(html.Span([html.Span('Relevância: ', style={'fontWeight': 'bold'}), html.Span(RELEVANCE_LEVELS[rl]['name'], style={'fontStyle': 'italic'})]))
            if sm in SORT_MODES:
                cfg_spans.append(html.Span([html.Span('Ordenação: ', style={'fontWeight': 'bold'}), html.Span(SORT_MODES[sm]['name'], style={'fontStyle': 'italic'})]))
            if mr is not None:
                cfg_spans.append(html.Span([html.Span('Máx: ', style={'fontWeight': 'bold'}), html.Span(str(mr), style={'fontStyle': 'italic'})]))
            if tc is not None:
                cfg_spans.append(html.Span([html.Span('Categorias: ', style={'fontWeight': 'bold'}), html.Span(str(tc), style={'fontStyle': 'italic'})]))
            if fe is not None:
                cfg_spans.append(html.Span([html.Span('Encerradas: ', style={'fontWeight': 'bold'}), html.Span('ON' if fe else 'OFF', style={'fontStyle': 'italic'})]))
        except Exception:
            pass
        inter_cfg = []
        for j, p in enumerate(cfg_spans):
            if j > 0:
                inter_cfg.append(html.Span(' | '))
            inter_cfg.append(p)
        line_config = html.Div(inter_cfg, style=styles['history_config']) if inter_cfg else html.Div('', style=styles['history_config'])

        # 2) Filtros (somente em 'filters'; não usar mais config_snapshot.filters)
        f = b.get('filters') or {}
        def _has(v):
            if v is None:
                return False
            if isinstance(v, str):
                return bool(v.strip())
            if isinstance(v, list):
                return len([x for x in v if str(x).strip()]) > 0
            return True
        filt_spans = []
        if _has(f.get('pncp')):
            filt_spans.append(html.Span([
                html.Span('PNCP nº: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('pncp') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('orgao')):
            filt_spans.append(html.Span([
                html.Span('Órgão: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('orgao') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('cnpj')):
            filt_spans.append(html.Span([
                html.Span('CNPJ: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('cnpj') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('uf')):
            uf_val = f.get('uf')
            if isinstance(uf_val, list):
                uf_txt = ', '.join([str(x).strip() for x in uf_val if str(x).strip()])
            else:
                uf_txt = str(uf_val or '').strip()
            if uf_txt:
                filt_spans.append(html.Span([
                    html.Span('UF: ', style={'fontWeight': 'bold'}),
                    html.Span(uf_txt, style={'fontStyle': 'italic'})
                ]))
        if _has(f.get('municipio')):
            filt_spans.append(html.Span([
                html.Span('Municípios: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('municipio') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('modalidade_id')):
            mid = f.get('modalidade_id')
            if isinstance(mid, list):
                mid_txt = ', '.join([str(x).strip() for x in mid if str(x).strip()])
            else:
                mid_txt = str(mid or '').strip()
            filt_spans.append(html.Span([
                html.Span('Modalidade: ', style={'fontWeight': 'bold'}),
                html.Span(mid_txt, style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('modo_id')):
            mo = f.get('modo_id')
            if isinstance(mo, list):
                mo_txt = ', '.join([str(x).strip() for x in mo if str(x).strip()])
            else:
                mo_txt = str(mo or '').strip()
            filt_spans.append(html.Span([
                html.Span('Modo: ', style={'fontWeight': 'bold'}),
                html.Span(mo_txt, style={'fontStyle': 'italic'})
            ]))
        df_label = {'encerramento': 'Encerramento', 'abertura': 'Abertura', 'publicacao': 'Publicação'}.get(str(f.get('date_field') or 'encerramento'), 'Encerramento')
        ds = f.get('date_start'); de = f.get('date_end')
        def _fmt(dv):
            return _format_br_date(dv) if dv else ''
        if ds or de:
            date_text = None
            if ds and de:
                date_text = f"desde {_fmt(ds)} até {_fmt(de)}"
            elif ds:
                date_text = f"desde {_fmt(ds)}"
            elif de:
                date_text = f"até {_fmt(de)}"
            if date_text:
                filt_spans.append(html.Span([
                    html.Span(f"Período ({df_label}): ", style={'fontWeight': 'bold'}),
                    html.Span(date_text, style={'fontStyle': 'italic'})
                ]))
        inter_filters = []
        for j, p in enumerate(filt_spans):
            if j > 0:
                inter_filters.append(html.Span(' | '))
            inter_filters.append(p)
        line_filters = html.Div([html.Span('Filtros: ', style={'fontWeight': 'bold'}), html.Span(inter_filters)], style=styles['history_config']) if inter_filters else html.Div('', style=styles['history_config'])

        # 3) Frequência (periodicidade), separar da linha de configs
        freq = b.get('schedule_type')
        detail = b.get('schedule_detail') or {}
        freq_spans = []
        freq_spans.append(html.Span([html.Span('Frequência: ', style={'fontWeight': 'bold'}), html.Span(str(freq or ''), style={'fontStyle': 'italic'})]))
        if freq == 'MULTIDIARIO':
            slots = ' / '.join(detail.get('slots') or []) or '-'
            freq_spans.append(html.Span([html.Span('Horários: ', style={'fontWeight': 'bold'}), html.Span(slots, style={'fontStyle': 'italic'})]))
        elif freq == 'SEMANAL':
            dias = ', '.join(detail.get('days') or []) or '-'
            freq_spans.append(html.Span([html.Span('Dias: ', style={'fontWeight': 'bold'}), html.Span(dias, style={'fontStyle': 'italic'})]))
        else:
            freq_spans.append(html.Span([html.Span('Dias: ', style={'fontWeight': 'bold'}), html.Span('Seg–Sex', style={'fontStyle': 'italic'})]))
        # Removido: exibição de "Última execução" no card de boletins
        inter_freq = []
        for j, p in enumerate(freq_spans):
            if j > 0:
                inter_freq.append(html.Span(' | '))
            inter_freq.append(p)
        line_freq = html.Div(inter_freq, style=styles['history_config'])

        items.append(
            html.Div([
                html.Button([
                    html.Div(b.get('query_text','')[:160] + ('...' if len(b.get('query_text',''))>160 else ''), style=styles['boletim_query']),
                    line_config,
                    line_filters,
                    line_freq
                ],
                    id={'type': 'boletim-item', 'id': b.get('id')},
                    style=styles['boletim_item_button']
                ),
                html.Div([
                    html.Button(
                        html.I(className='fas fa-trash'),
                        id={'type': 'boletim-delete', 'id': b.get('id')},
                        className='delete-btn action-btn',
                        style=styles['boletim_delete_btn']
                    ),
                    html.Button(
                        html.I(className='fas fa-undo'),
                        id={'type': 'boletim-replay', 'id': b.get('id')},
                        title='Reabrir resultados deste boletim',
                        style=styles['history_replay_btn'],
                        className='delete-btn action-btn'
                    ),
                    html.Button(
                        html.I(className='fas fa-envelope'),
                        id={'type': 'boletim-email', 'id': b.get('id')},
                        title='Enviar por e-mail (em breve)',
                        style=styles['history_replay_btn'],
                        className='delete-btn action-btn'
                    ),
                    # [FUTURO] Botão "Editar" do item de boletim
                    # Mantido comentado até implementação do fluxo de edição.
                    # A ideia: ao clicar, preencher os controles do painel de boletim
                    # (frequência, dias) com os valores do item selecionado e abrir o collapse.
                    # Depois, o usuário pode salvar novamente (atualização) ou cancelar.
                    # html.Button(
                    #     html.I(className='fas fa-pencil-alt'),
                    #     id={'type': 'boletim-edit', 'id': b.get('id')},
                    #     className='edit-btn action-btn',
                    #     style=styles['boletim_delete_btn']
                    # )
                ], style=styles['fav_actions_col'])
            ], style=styles['boletim_item_row'], className='boletim-item-row')
        )
    return items


# Toggle do painel de lista de Boletins (colapsar/expandir)
@app.callback(
    Output('boletins-collapse', 'is_open'),
    Output('store-boletins-open', 'data'),
    Input('boletins-toggle-btn', 'n_clicks'),
    State('store-boletins-open', 'data'),
    prevent_initial_call=True,
)
def toggle_boletins_collapse(n, is_open):
    if not n:
        raise PreventUpdate
    new_state = not bool(is_open)
    return new_state, new_state

@app.callback(
    Output('boletins-toggle-btn', 'children'),
    Input('store-boletins-open', 'data')
)
def update_boletins_icon(is_open):
    icon = 'fa-chevron-up' if is_open else 'fa-chevron-down'
    return [
        html.Div([
            html.I(className='fas fa-calendar', style=styles['section_icon']),
            html.Div('Boletins', style=styles['card_title'])
        ], style=styles['section_header_left']),
        html.I(className=f"fas {icon}")
    ]


# Inicialização pós-login e limpeza no logout
@app.callback(
    Output('store-app-init', 'data', allow_duplicate=True),
    Output('processing-state', 'data', allow_duplicate=True),
    Output('store-history', 'data', allow_duplicate=True),
    Output('store-favorites', 'data', allow_duplicate=True),
    Output('store-history-open', 'data', allow_duplicate=True),
    Output('store-favorites-open', 'data', allow_duplicate=True),
    Output('progress-store', 'data', allow_duplicate=True),
    Output('store-sort', 'data', allow_duplicate=True),
    Output('query-input', 'value', allow_duplicate=True),
    Output('store-results', 'data', allow_duplicate=True),
    Output('store-results-sorted', 'data', allow_duplicate=True),
    Output('store-categories', 'data', allow_duplicate=True),
    Output('store-meta', 'data', allow_duplicate=True),
    Output('store-last-query', 'data', allow_duplicate=True),
    Output('store-result-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('store-panel-active', 'data', allow_duplicate=True),
    Output('store-cache-itens', 'data', allow_duplicate=True),
    Output('store-cache-docs', 'data', allow_duplicate=True),
    Output('store-cache-resumo', 'data', allow_duplicate=True),
    Input('store-auth', 'data'),
    prevent_initial_call=True,
)
def on_auth_changed(auth_data):
    data = auth_data or {}
    status = data.get('status')
    # Valores padrão para limpeza
    empty_results = []
    empty_categories = []
    empty_meta = {}
    empty_sessions = {}
    empty_panel = {}
    empty_cache = {}
    if status == 'auth':
        # Entrando: ligar spinner e iniciar fase de inicialização
        return (
            {'initializing': True},  # store-app-init
            True,                    # processing-state
            [],                      # store-history (limpa rápido)
            [],                      # store-favorites (limpa rápido)
            True,                    # store-history-open
            True,                    # store-favorites-open
            {'percent': 0, 'label': ''},  # progress-store
            None,                    # store-sort
            '',                      # query-input vazio
            empty_results,
            [],                      # store-results-sorted
            empty_categories,
            empty_meta,
            '',                      # store-last-query
            empty_sessions,
            None,                    # store-active-session
            empty_panel,
            empty_cache,
            empty_cache,
            empty_cache,
        )
    # Saindo: desligar spinner e limpar tudo da UI
    return (
        {'initializing': False},
        False,
        [],
        [],
    True,
    True,
    {'percent': 0, 'label': ''},
    None,
    '',
        empty_results,
        [],
        empty_categories,
        empty_meta,
        '',
        empty_sessions,
        None,
        empty_panel,
        empty_cache,
        empty_cache,
        empty_cache,
    )


@app.callback(
    Output('store-app-init', 'data', allow_duplicate=True),
    Output('processing-state', 'data', allow_duplicate=True),
    Output('store-history', 'data', allow_duplicate=True),
    Output('store-favorites', 'data', allow_duplicate=True),
    Input('store-app-init', 'data'),
    prevent_initial_call=True,
)
def perform_initial_load(init_state):
    state = init_state or {}
    if not state.get('initializing'):
        raise PreventUpdate
    # Carregar dados do usuário atual
    try:
        # Evita consultas com user_id vazio
        u = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
        uid = (u or {}).get('uid') or ''
        hist = load_history(max_items=50) or [] if uid else []
    except Exception:
        hist = []
    try:
        favs = fetch_bookmarks(limit=100) if uid and 'fetch_bookmarks' in globals() else []  # type: ignore
    except Exception:
        favs = []
    # Concluir inicialização
    return {'initializing': False}, False, hist, favs
@app.callback(
    Output('auth-overlay', 'style'),
    Input('store-auth', 'data')
)
def toggle_auth_overlay(auth_data):
    try:
        is_auth = (auth_data or {}).get('status') == 'auth'
        if is_auth:
            st = dict(styles['auth_overlay'])
            st.update({'display': 'none'})
            return st
        return styles['auth_overlay']
    except Exception:
        return styles['auth_overlay']


@app.callback(
    Output('auth-view-login', 'style'),
    Output('auth-view-signup', 'style'),
    Output('auth-view-confirm', 'style'),
    Output('auth-view-reset', 'style'),
    Output('auth-confirm-text', 'children'),
    Output('auth-error', 'children'),
    Output('auth-error', 'style'),
    Input('store-auth-view', 'data'),
    Input('store-auth-error', 'data'),
    Input('store-auth-pending-email', 'data'),
)
def reflect_auth_view(view, err_text, pending_email):
    v = (view or 'login')
    show = {'display': 'block'}
    hide = {'display': 'none'}
    login_st = show if v == 'login' else hide
    signup_st = show if v == 'signup' else hide
    confirm_st = show if v == 'confirm' else hide
    reset_st = show if v == 'reset' else hide
    try:
        confirm_txt = f"Enviamos um código para {pending_email}. Confira sua caixa de entrada." if (pending_email or '').strip() else "Digite o código enviado para o seu e-mail."
    except Exception:
        confirm_txt = "Digite o código enviado para o seu e-mail."
    # Aceita string ou componente no erro
    err_children = None
    show_err = False
    try:
        if isinstance(err_text, str):
            err_children = err_text.strip()
            show_err = bool(err_children)
        else:
            err_children = err_text
            show_err = err_text is not None
    except Exception:
        err_children = ''
        show_err = False
    err_style = {**styles['auth_error'], 'display': ('block' if show_err else 'none')}
    return login_st, signup_st, confirm_st, reset_st, confirm_txt, err_children, err_style


## removido callback duplicado de logout (substituído pelo existente mais abaixo)


@app.callback(
    Output('store-auth', 'data', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Output('store-auth-view', 'data', allow_duplicate=True),
    Output('store-auth-remember', 'data', allow_duplicate=True),
    Output('store-auth-pending-email', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('auth-login', 'n_clicks'),
    State('auth-email', 'value'),
    State('auth-password', 'value'),
    State('auth-remember', 'value'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def do_login(n_clicks, email, password, remember_values, notifications):
    if not n_clicks:
        raise PreventUpdate
    email = (email or '').strip()
    password = password or ''
    updated_notifs = list(notifications or [])
    if not email or not password:
        return dash.no_update, 'Informe e-mail e senha.', dash.no_update, dash.no_update, dash.no_update, dash.no_update
    ok, session, err = False, None, None
    try:
        ok, session, err = sign_in(email, password)
        try:
            dbg('AUTH', f"[GvG_Browser.do_login] sign_in ok={ok} err={err} session_keys={list((session or {}).keys())}")
        except Exception:
            pass
    except Exception as e:
        ok, session, err = False, None, f"Erro ao autenticar: {e}"
    if not ok or not session or not session.get('user'):
        # Se e-mail não confirmado, direcionar para view de confirmação e preparar reenvio
        raw = (err or '')
        if isinstance(raw, str) and ('Email not confirmed' in raw or 'email not confirmed' in raw.lower()):
            pending = (email or '').strip()
            msg = f"Seu e-mail não foi confirmado. Informe o código enviado ou clique em 'Reenviar código'."
            # Notificação de aviso
            notif = add_note(NOTIF_WARNING, "E-mail não confirmado. Verifique o código enviado.")
            updated_notifs.append(notif)
            return dash.no_update, msg, 'confirm', dash.no_update, pending, updated_notifs
        # Caso geral: mensagem amigável
        msg = err or 'Falha no login.'
        # Notificação de erro
        notif = add_note(NOTIF_ERROR, "Falha no login. Verifique suas credenciais.")
        updated_notifs.append(notif)
        return dash.no_update, msg, dash.no_update, dash.no_update, dash.no_update, updated_notifs
    # Usuário autenticado
    try:
        set_current_user(session.get('user'))
    except Exception:
        pass
    auth_state = {
        'status': 'auth',
        'user': session.get('user'),
        'access_token': session.get('access_token'),
        'refresh_token': session.get('refresh_token'),
    }
    remember_on = isinstance(remember_values, (list, tuple)) and ('yes' in (remember_values or []))
    remember_payload = {'email': email if remember_on else '', 'password': password if remember_on else '', 'remember': bool(remember_on)}
    
    # Notificação de sucesso no login
    u = session.get('user', {})
    username = u.get('username', 'Usuário')
    notif = add_note(NOTIF_SUCCESS, f"Bem-vindo, {username}!")
    updated_notifs.append(notif)
    
    return auth_state, '', 'login', remember_payload, dash.no_update, updated_notifs


@app.callback(
    Output('store-auth-view', 'data', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Output('store-auth-pending-email', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('auth-signup', 'n_clicks'),
    State('auth-fullname', 'value'),
    State('auth-phone', 'value'),
    State('auth-email-sign', 'value'),
    State('auth-password-sign', 'value'),
    State('auth-terms', 'value'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def do_signup(n_clicks, fullname, phone, email, password, terms, notifications):
    if not n_clicks:
        raise PreventUpdate
    
    updated_notifs = list(notifications or [])
    email = (email or '').strip()
    password = password or ''
    if 'ok' not in (terms or []):
        try:
            dbg('AUTH', f"[GvG_Browser.do_signup] terms not accepted | email={email}")
        except Exception:
            pass
        # Notificação de aviso: termos não aceitos
        notif = add_note(NOTIF_WARNING, "Aceite os Termos de Contratação para continuar.")
        updated_notifs.append(notif)
        return dash.no_update, 'Você precisa aceitar os Termos de Contratação.', dash.no_update, updated_notifs
    if not email or not password or not (fullname or '').strip():
        try:
            dbg('AUTH', f"[GvG_Browser.do_signup] missing fields | email_set={bool(email)} name_set={bool((fullname or '').strip())} phone_set={bool((phone or '').strip())}")
        except Exception:
            pass
        # Notificação de erro: campos obrigatórios
        notif = add_note(NOTIF_ERROR, "Preencha nome, e-mail e senha.")
        updated_notifs.append(notif)
        return dash.no_update, 'Preencha nome, e-mail e senha.', dash.no_update, updated_notifs
    ok, msg = False, 'Erro ao cadastrar.'
    try:
        try:
            dbg('AUTH', f"[GvG_Browser.do_signup] calling sign_up_with_metadata | email={email} has_phone={bool((phone or '').strip())}")
        except Exception:
            pass
        ok, msg = sign_up_with_metadata(email=email, password=password, full_name=(fullname or '').strip(), phone=(phone or '').strip())
    except Exception as e:
        ok, msg = False, f"Erro ao cadastrar: {e}"
    try:
        dbg('AUTH', f"[GvG_Browser.do_signup] result ok={ok} msg={msg}")
    except Exception:
        pass
    if not ok:
        # Notificação de erro no cadastro
        notif = add_note(NOTIF_ERROR, "Erro ao cadastrar. Verifique os dados.")
        updated_notifs.append(notif)
        return dash.no_update, (msg or 'Falha ao cadastrar.'), dash.no_update, updated_notifs
    try:
        dbg('AUTH', f"[GvG_Browser.do_signup] moving to confirm | pending_email={email}")
    except Exception:
        pass
    # Notificação de sucesso no cadastro
    notif = add_note(NOTIF_SUCCESS, "Cadastro realizado! Verifique seu e-mail.")
    updated_notifs.append(notif)
    return 'confirm', '', email, updated_notifs


@app.callback(
    Output('store-auth', 'data', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Output('store-auth-view', 'data', allow_duplicate=True),
    Input('auth-confirm', 'n_clicks'),
    State('store-auth-pending-email', 'data'),
    State('auth-otp', 'value'),
    prevent_initial_call=True,
)
def do_confirm(n_clicks, email, otp):
    if not n_clicks:
        raise PreventUpdate
    email = (email or '').strip()
    otp = (otp or '').strip()
    if not email or not otp:
        return dash.no_update, 'Informe o código recebido por e-mail.', dash.no_update
    ok, session, err = False, None, None
    try:
        try:
            masked = (('*' * max(0, len(otp) - 2)) + otp[-2:]) if otp else ''
            dbg('AUTH', f"[GvG_Browser.do_confirm] calling verify_otp | email={email} otp_masked={masked}")
        except Exception:
            pass
        ok, session, err = verify_otp(email=email, token=otp, type_='signup')
    except Exception as e:
        ok, session, err = False, None, f"Erro na confirmação: {e}"
    try:
        dbg('AUTH', f"[GvG_Browser.do_confirm] result ok={ok} err={err} session_keys={list((session or {}).keys())}")
    except Exception:
        pass
    if not ok or not session or not session.get('user'):
        # Mensagem amigável; detalhes ficam no console quando debug ativo
        # Instruir usuário a usar o botão fixo "Reenviar código"
        email_safe = email
        msg = f"Código inválido ou expirado. Clique em 'Reenviar código' para {email_safe}."
        return dash.no_update, msg, dash.no_update
    try:
        set_current_user(session.get('user'))
    except Exception:
        pass
    auth_state = {
        'status': 'auth',
        'user': session.get('user'),
        'access_token': session.get('access_token'),
        'refresh_token': session.get('refresh_token'),
    }
    return auth_state, '', 'login'


@app.callback(
    Output('store-auth-error', 'data', allow_duplicate=True),
    Input('auth-forgot', 'n_clicks'),
    State('auth-email', 'value'),
    prevent_initial_call=True,
)
def do_forgot(n_clicks, email):
    if not n_clicks:
        raise PreventUpdate
    email = (email or '').strip()
    if not email:
        return 'Informe seu e-mail para recuperar a senha.'
    ok, msg = False, 'Não foi possível iniciar a recuperação.'
    try:
        ok, msg = reset_password(email)
    except Exception as e:
        ok, msg = False, f"Erro ao solicitar recuperação: {e}"
    return (msg or 'Verifique seu e-mail.')


# Reenvio de OTP (link na tela de confirmação)
@app.callback(
    Output('store-auth-error', 'data', allow_duplicate=True),
    Input('auth-resend-link', 'n_clicks'),
    State('store-auth-pending-email', 'data'),
    prevent_initial_call=True,
)
def do_resend_otp(n_clicks, email):
    if not n_clicks:
        raise PreventUpdate
    email = (email or '').strip()
    if not email:
        return 'Informe o e-mail novamente e solicite cadastro.'
    ok, msg = resend_otp(email, type_='signup')
    if ok:
        return f'Enviamos um novo código para {email}.'
    # Mensagem amigável sempre; detalhes no console via debug
    return 'Não foi possível reenviar o código. Tente novamente em instantes.'


# =============================
# Stripe Checkout - Páginas de Retorno
# =============================
@app.callback(
    Output('planos-modal', 'is_open', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Input('url', 'pathname'),
    Input('url', 'search'),
    State('store-auth', 'data'),
    prevent_initial_call=True
)
def handle_stripe_return(pathname, search, auth_data):
    """
    Detecta retorno do Stripe (/checkout/success ou /checkout/cancel)
    e exibe mensagem apropriada.
    """
    if not pathname:
        raise PreventUpdate
    
    # Sucesso: pagamento confirmado
    if pathname == '/checkout/success':
        session_id = None
        try:
            params = dict([part.split('=', 1) for part in (search or '').lstrip('?').split('&') if '=' in part])
            session_id = params.get('session_id')
        except Exception:
            pass
        
        dbg('BILLING', f"Retorno Stripe SUCCESS: session_id={session_id}")
        
        # Se está em popup (window.opener existe), fechar e recarregar página pai
        # Se não está em popup, mostrar mensagem
        return False, html.Div([
            html.H3("✅ Pagamento Confirmado!", style={'color': '#28a745', 'textAlign': 'center'}),
            html.P("Seu plano está sendo ativado...", style={'textAlign': 'center'}),
            html.Script("""
                // Se está em popup, fechar e recarregar pai
                if (window.opener) {
                    window.opener.postMessage({type: 'stripe_success', session_id: '%s'}, '*');
                    window.close();
                } else {
                    // Se não está em popup, redirecionar para home após 2s
                    setTimeout(function() {
                        window.location.href = '/';
                    }, 2000);
                }
            """ % (session_id or ''))
        ])
    
    # Cancelamento: usuário desistiu
    elif pathname == '/checkout/cancel':
        dbg('BILLING', "Retorno Stripe CANCEL: usuário cancelou pagamento")
        
        # Reabrir modal de planos com mensagem
        return True, "⚠️ Pagamento cancelado. Você pode tentar novamente quando quiser."
    
    # Não é página de retorno do Stripe
    raise PreventUpdate


# Detecta link de recuperação na URL e aciona a view de reset
@app.callback(
    Output('store-auth-view', 'data', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Output('store-auth', 'data', allow_duplicate=True),
    Output('url', 'search', allow_duplicate=True),
    Output('url', 'hash', allow_duplicate=True),
    Input('url', 'search'),
    Input('url', 'hash'),
    prevent_initial_call='initial_duplicate',
)
def detect_recovery_in_url(search_query, url_hash):
    # 1) Tentar tokens no fragmento (#...) vindo do Supabase (access_token, refresh_token, type=recovery)
    try:
        h = (url_hash or '').lstrip('#')
        if h:
            hparams = dict([part.split('=', 1) for part in h.split('&') if '=' in part])
            typ = (hparams.get('type') or '').lower()
            acc = hparams.get('access_token')
            ref = hparams.get('refresh_token')
            if typ == 'recovery' and acc:
                # Criar sessão com tokens do fragmento
                ok, session, err = set_session(acc, ref)
                if ok and session and session.get('user'):
                    try:
                        set_current_user(session.get('user'))
                        set_access_token(session.get('access_token'))
                    except Exception:
                        pass
                    auth_state = {
                        'status': 'recovery',
                        'user': session.get('user'),
                        'access_token': session.get('access_token'),
                        'refresh_token': session.get('refresh_token'),
                    }
                    # Limpa hash e search (se houver)
                    return 'reset', '', auth_state, '', ''
                else:
                    # Tokens inválidos
                    return 'login', (err or 'Link de recuperação inválido.'), dash.no_update, dash.no_update, ''
    except Exception:
        # Ignora erros de parsing
        pass

    # 2) Fallback: querystring ?type=recovery&code=...
    try:
        s = (search_query or '').lstrip('?')
        if not s:
            raise PreventUpdate
        params = dict([part.split('=', 1) for part in s.split('&') if '=' in part])
        typ = (params.get('type') or '').lower()
        code = params.get('code') or params.get('token') or ''
        if typ != 'recovery' or not code:
            raise PreventUpdate
    except Exception:
        raise PreventUpdate
    ok, session, err = False, None, None
    try:
        ok, session, err = recover_session_from_code(code)
    except Exception as e:
        ok, session, err = False, None, f"Erro ao validar link: {e}"
    if not ok or not session or not session.get('user'):
        return 'login', (err or 'Link de recuperação inválido ou expirado.'), dash.no_update, '', dash.no_update
    try:
        set_current_user(session.get('user'))
        set_access_token(session.get('access_token'))
    except Exception:
        pass
    auth_state = {
        'status': 'recovery',
        'user': session.get('user'),
        'access_token': session.get('access_token'),
        'refresh_token': session.get('refresh_token'),
    }
    # Limpa a querystring
    return 'reset', '', auth_state, '', dash.no_update


# Confirmar redefinição de senha
@app.callback(
    Output('store-auth', 'data', allow_duplicate=True),
    Output('store-auth-error', 'data', allow_duplicate=True),
    Output('store-auth-view', 'data', allow_duplicate=True),
    Output('url', 'search', allow_duplicate=True),
    Input('auth-reset-confirm', 'n_clicks'),
    State('auth-new-pass', 'value'),
    State('auth-new-pass2', 'value'),
    prevent_initial_call=True,
)
def confirm_password_reset(n_clicks, p1, p2):
    if not n_clicks:
        raise PreventUpdate
    p1 = (p1 or '').strip(); p2 = (p2 or '').strip()
    if not p1 or not p2:
        return dash.no_update, 'Informe e confirme a nova senha.', dash.no_update, dash.no_update
    if p1 != p2:
        return dash.no_update, 'As senhas não conferem.', dash.no_update, dash.no_update
    ok, session, err = False, None, None
    try:
        ok, session, err = update_user_password(p1)
    except Exception as e:
        ok, session, err = False, None, f"Erro ao atualizar senha: {e}"
    if not ok:
        return dash.no_update, (err or 'Não foi possível atualizar a senha.'), dash.no_update, dash.no_update
    # Se a API não retornar sessão, mantém usuário atual e fecha overlay assim mesmo
    user_info = None
    try:
        user_info = (session or {}).get('user')
        if user_info:
            set_current_user(user_info)
    except Exception:
        pass
    auth_state = {
        'status': 'auth',
        'user': user_info or (get_current_user() if 'get_current_user' in globals() else None),
        'access_token': (session or {}).get('access_token'),
        'refresh_token': (session or {}).get('refresh_token'),
    }
    try:
        set_access_token(auth_state.get('access_token'))
    except Exception:
        pass
    # Fecha overlay (view login por segurança) e limpa querystring
    return auth_state, '', 'login', ''


# Cancelar redefinição: volta para login
@app.callback(
    Output('store-auth-view', 'data', allow_duplicate=True),
    Input('auth-reset-cancel', 'n_clicks'),
    prevent_initial_call=True,
)
def cancel_password_reset(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return 'login'


# Abrir/fechar Popover do usuário (avatar)
@app.callback(
    Output('user-menu-popover', 'is_open'),
    Input('header-user-badge', 'n_clicks'),
    Input('user-menu-item-planos', 'n_clicks'),
    Input('user-menu-item-config', 'n_clicks'),
    Input('user-menu-item-logout', 'n_clicks'),
    State('user-menu-popover', 'is_open'),
    prevent_initial_call=True,
)
def toggle_user_menu(click_avatar, click_plan, click_cfg, click_logout, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig == 'header-user-badge':
        return not is_open
    # Qualquer item do menu fecha o popover
    return False


# Abrir/fechar Popover de Mensagem e limpar textarea ao enviar
@app.callback(
    Output('message-popover', 'is_open'),
    Output('message-textarea', 'value'),
    Input('header-message-btn', 'n_clicks'),
    State('message-popover', 'is_open'),
    prevent_initial_call=True,
)
def toggle_message_popover(click_open, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig == 'header-message-btn' and (click_open or 0) >= 0:
        return (not is_open), dash.no_update
    raise PreventUpdate


# Enviar mensagem: persiste no BD, loga e notifica
@app.callback(
    Output('message-popover', 'is_open', allow_duplicate=True),
    Output('message-textarea', 'value', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('message-send-btn', 'n_clicks'),
    State('message-textarea', 'value'),
    State('store-auth', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def handle_send_message(n_clicks, text_value, auth_data, notifications):
    if not n_clicks:
        raise PreventUpdate
    notifs = list(notifications or [])
    msg = (text_value or '').strip()
    if not msg:
        notif = add_note(NOTIF_WARNING, 'Escreva uma mensagem antes de enviar.')
        notifs.append(notif)
        return dash.no_update, dash.no_update, notifs
    user = (auth_data or {}).get('user') or {}
    uid = (user.get('uid') or '').strip()
    if not uid:
        notif = add_note(NOTIF_ERROR, 'Faça login para enviar mensagens.')
        notifs.append(notif)
        return dash.no_update, dash.no_update, notifs
    user_name = (user.get('name') or user.get('email') or 'Usuário').strip()
    try:
        res = insert_user_message(uid, user_name, msg, 0)
        if res and res.get('id') is not None:
            try:
                dbg('MESSAGE', f"insert uid={uid} id={res.get('id')} len={len(msg)} status=0")
            except Exception:
                pass
            notif = add_note(NOTIF_SUCCESS, 'Mensagem enviada com sucesso! Obrigado.')
            notifs.append(notif)
            # Fecha popover e limpa textarea
            return False, '', notifs
        else:
            try:
                dbg('MESSAGE', f"insert FAIL uid={uid} len={len(msg)}")
            except Exception:
                pass
            notif = add_note(NOTIF_ERROR, 'Não foi possível enviar sua mensagem. Tente novamente.')
            notifs.append(notif)
            return dash.no_update, dash.no_update, notifs
    except Exception as e:
        try:
            dbg('MESSAGE', f"exception: {e}")
        except Exception:
            pass
        notif = add_note(NOTIF_ERROR, 'Erro ao enviar sua mensagem.')
        notifs.append(notif)
        return dash.no_update, dash.no_update, notifs


# Renderizar nome e e-mail no menu do usuário
@app.callback(
    Output('user-menu-name', 'children'),
    Output('user-menu-email', 'children'),
    Input('store-auth', 'data'),
)
def render_user_menu_userinfo(auth_data):
    user = (auth_data or {}).get('user') or {}
    name = (user.get('name') or 'Usuário')
    email = (user.get('email') or '')
    return name, email


@app.callback(
    Output('store-auth', 'data'),
    Input('user-menu-item-logout', 'n_clicks'),
    State('store-auth', 'data'),
    prevent_initial_call=True,
)
def do_logout(n_clicks, auth_data):
    if not n_clicks:
        raise PreventUpdate
    try:
        rt = (auth_data or {}).get('refresh_token')
        try:
            sign_out(rt)
        except Exception:
            pass
    except Exception:
        pass
    # Limpa token/acesso e reseta usuário local (não apaga dados persistidos)
    try:
        set_access_token(None)
    except Exception:
        pass
    try:
        set_current_user({'uid': '', 'email': '', 'name': 'Usuário'})
    except Exception:
        pass
    return {'status': 'unauth', 'user': None}


# Mostrar/ocultar senha (login) via botão de olho
@app.callback(
    Output('auth-password', 'type'),
    Output('auth-pass-toggle', 'children'),
    Input('auth-pass-toggle', 'n_clicks'),
    State('auth-password', 'type'),
    prevent_initial_call=False,
)
def toggle_login_password_eye(n_clicks, current_type):
    try:
        show = (current_type == 'password')
        new_type = 'text' if show else 'password'
        icon = html.I(className=('far fa-eye-slash' if show else 'far fa-eye'))
        return new_type, icon
    except Exception:
        return 'password', html.I(className='far fa-eye')


# Mostrar/ocultar senha (signup) via botão de olho
@app.callback(
    Output('auth-password-sign', 'type'),
    Output('auth-pass-toggle-sign', 'children'),
    Input('auth-pass-toggle-sign', 'n_clicks'),
    State('auth-password-sign', 'type'),
    prevent_initial_call=False,
)
def toggle_signup_password_eye(n_clicks, current_type):
    try:
        show = (current_type == 'password')
        new_type = 'text' if show else 'password'
        icon = html.I(className=('far fa-eye-slash' if show else 'far fa-eye'))
        return new_type, icon
    except Exception:
        return 'password', html.I(className='far fa-eye')


# Mostrar/ocultar senha (reset) via botões de olho
@app.callback(
    Output('auth-new-pass', 'type'),
    Output('auth-pass-toggle-reset-1', 'children'),
    Input('auth-pass-toggle-reset-1', 'n_clicks'),
    State('auth-new-pass', 'type'),
    prevent_initial_call=False,
)
def toggle_reset_password_eye1(n_clicks, current_type):
    try:
        show = (current_type == 'password')
        new_type = 'text' if show else 'password'
        icon = html.I(className=('far fa-eye-slash' if show else 'far fa-eye'))
        return new_type, icon
    except Exception:
        return 'password', html.I(className='far fa-eye')


@app.callback(
    Output('auth-new-pass2', 'type'),
    Output('auth-pass-toggle-reset-2', 'children'),
    Input('auth-pass-toggle-reset-2', 'n_clicks'),
    State('auth-new-pass2', 'type'),
    prevent_initial_call=False,
)
def toggle_reset_password_eye2(n_clicks, current_type):
    try:
        show = (current_type == 'password')
        new_type = 'text' if show else 'password'
        icon = html.I(className=('far fa-eye-slash' if show else 'far fa-eye'))
        return new_type, icon
    except Exception:
        return 'password', html.I(className='far fa-eye')
# Prefill de e-mail/senha com base no store local (quando voltar para a view login)
@app.callback(
    Output('auth-email', 'value'),
    Output('auth-password', 'value'),
    Output('auth-remember', 'value'),
    Input('store-auth-view', 'data'),
    State('store-auth-remember', 'data'),
    prevent_initial_call=True,
)
def prefill_login_fields(view, remember):
    if (view or 'login') != 'login':
        raise PreventUpdate
    try:
        rem = remember or {}
        if rem.get('remember'):
            return rem.get('email', ''), rem.get('password', ''), ['yes']
    except Exception:
        pass
    return '', '', []


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

def _enc_status_text(status: str, dt_value) -> str:
    """Mapeia status interno para texto da tag.
    Regras especiais: se status não for 'expired' e a data for hoje => 'encerra hoje!'.
    """
    from datetime import date as _date
    if status == 'na':
        return 'sem data'
    if status == 'expired':
        return 'expirada'
    # detectar hoje
    try:
        dt = _parse_date_generic(dt_value)
        if dt and dt == _date.today():
            return 'é hoje!'
    except Exception:
        pass
    if status == 'lt3':
        return 'em até 3 dias'
    if status == 'lt7':
        return 'em até 7 dias'
    if status == 'lt15':
        return 'em até 15 dias'
    if status == 'lt30':
        return 'em até 30 dias'
    if status == 'gt30':
        return 'mais de 30 dias'
    return ''


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


# =========================
# Assinaturas de sessões (deduplicação)
# =========================
def _extract_pncp_id_from_result(r: dict) -> str:
    try:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        return str(pid) if pid is not None else ''
    except Exception:
        return ''


def _make_query_signature(query: str, meta: dict, results: list, max_ids: int = 20) -> str:
    """Cria uma assinatura estável da sessão de busca para evitar duplicação de abas.

    Usa: query normalizada, parâmetros de meta principais e primeiros N ids PNCP.
    """
    q_norm = (query or '').strip().lower()
    try:
        ids = []
        for r in (results or [])[:max_ids]:
            rid = _extract_pncp_id_from_result(r)
            if rid:
                ids.append(rid)
    except Exception:
        ids = []
    payload = {
        'q': q_norm,
        'search': (meta or {}).get('search'),
        'approach': (meta or {}).get('approach'),
        'relevance': (meta or {}).get('relevance'),
        'order': (meta or {}).get('order'),
        'filter_expired': bool((meta or {}).get('filter_expired')),
        'max_results': (meta or {}).get('max_results'),
        'top_categories': (meta or {}).get('top_categories'),
        'ids': ids,
    }
    try:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hashlib.sha1(blob).hexdigest()
    except Exception:
        return f"fallback:{q_norm}:{len(ids)}:{(meta or {}).get('order')}"


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
def load_history(max_items: int = 20) -> list:
    try:
        u = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
        uid = (u or {}).get('uid') or ''
        if not uid:
            return []
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
    Output('store-session-event', 'data', allow_duplicate=True),
    Output('processing-state', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('processing-state', 'data'),
    State('query-input', 'value'),
    State('search-type', 'value'),
    State('search-approach', 'value'),
    State('relevance-level', 'value'),
    State('sort-mode', 'value'),
    State('max-results', 'value'),
    State('top-categories', 'value'),
    State('toggles', 'value'),
    State('store-current-query-token', 'data'),
    State('store-search-filters', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def run_search(is_processing, query, s_type, approach, relevance, order, max_results, top_cat, toggles, current_token, ui_filters, notifications):
    if not is_processing:
        raise PreventUpdate
    # Permitir também buscas somente por filtros (quando V2 ativo)
    try:
        if isinstance(ui_filters, str):
            import json as _json
            ui_filters = _json.loads(ui_filters)
    except Exception:
        pass
    if (not query or len((query or '').strip()) < 3) and not (ENABLE_SEARCH_V2 and _has_any_filter(ui_filters)):
        raise PreventUpdate
    # Resetar e iniciar progresso
    try:
        progress_reset()
        progress_set(10, 'Iniciando')
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

    # Pré-processar consulta (V1 ou V2 conforme flag) e capturar filtros UI
    base_terms = query
    filter_list = _build_sql_conditions_from_ui_filters(ui_filters) if ENABLE_SEARCH_V2 else []
    info = None
    try:
        # 1) Se V2 ativo, tente reutilizar preproc_output salvo (evita custo de IA)
        if ENABLE_SEARCH_V2:
            try:
                cached = get_prompt_preproc_output((query or '').strip(), (ui_filters or {}))
            except Exception:
                cached = None
            if isinstance(cached, dict) and (cached.get('search_terms') or cached.get('sql_conditions') is not None):
                info = cached
                try:
                    dbg('PRE', f"cache HIT user_prompts.preproc_output terms='{(info.get('search_terms') or '')[:60]}' sql_conds={len(info.get('sql_conditions') or [])}")
                except Exception:
                    pass
                if (info.get('search_terms') or '').strip():
                    base_terms = info['search_terms']
            else:
                try:
                    dbg('PRE', 'cache MISS user_prompts.preproc_output')
                except Exception:
                    pass
        # 2) Caso não haja cache, processe com o assistant normalmente
        if info is None:
            processor = SearchQueryProcessor()
            if ENABLE_SEARCH_V2:
                info = processor.process_query_v2(query or '', filter_list)
            else:
                info = processor.process_query(query or '')
            if (info.get('search_terms') or '').strip():
                base_terms = info['search_terms']
            try:
                dbg('PRE', f"assistant OUTPUT terms='{(info.get('search_terms') or '')[:60]}' sql_conds={len(info.get('sql_conditions') or [])}")
            except Exception:
                pass
        try:
            progress_set(10, 'Pré-processando consulta')
        except Exception:
            pass
    except Exception:
        info = {'search_terms': query or '', 'negative_terms': '', 'sql_conditions': [], 'embeddings': bool((query or '').strip())}

    import time
    t0 = time.time()
    # Início do evento de uso (query). Ref será ajustado após persistir prompt.
    from gvg_usage import usage_event_start  # type: ignore
    from gvg_limits import ensure_capacity, LimitExceeded  # type: ignore
    user = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
    uid = (user or {}).get('uid') or ''
    usage_started = False
    if uid:
        # Checar limites separadamente para capturar erros
        try:
            ensure_capacity(uid, 'consultas')
        except LimitExceeded:
            dbg('LIMIT', 'bloqueando busca: limite consultas atingido')
            # Notificação de limite atingido (CRÍTICO)
            updated_notifs = list(notifications or [])
            try:
                notif = add_note(NOTIF_ERROR, "Limite diário de consultas atingido. Faça upgrade do seu plano.")
                updated_notifs.append(notif)
            except Exception:
                pass
            # Reset do progresso para fechar spinner
            try:
                progress_reset()
            except Exception:
                pass
            # Retorna: results=no_update, categories=no_update, meta=no_update, query=no_update, 
            # session_event=no_update, processing=FALSE (para fechar spinner), notifications=updated
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False, updated_notifs
        except Exception as e:
            # Não aborta a busca; continua e ainda registra evento
            dbg('LIMIT', f"erro ensure_capacity: {e}")
        # Tentar iniciar evento
        try:
            usage_event_start(uid, 'query', ref_type='prompt', ref_id=None)
            usage_started = True
        except Exception as e:
            dbg('USAGE', f"erro start query: {e}")
    else:
        dbg('USAGE', 'uid vazio: busca seguirá sem tracking')

    # Sanitizar limites vindos da UI ANTES de usar
    safe_limit = _sanitize_limit(max_results, default=DEFAULT_MAX_RESULTS, min_v=5, max_v=1000)
    safe_top = _sanitize_limit(top_cat, default=DEFAULT_TOP_CATEGORIES, min_v=1, max_v=100)

    categories: List[dict] = []
    if approach in (2, 3) and (not ENABLE_SEARCH_V2 or info.get('embeddings', True)):
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
    filter_route = 'none'
    try:
        if approach == 1:
            try:
                progress_set(70, 'Executando busca direta')
            except Exception:
                pass
            # Roteamento por embeddings (V2): se embeddings=false, executar caminho SQL-only
            if ENABLE_SEARCH_V2 and not info.get('embeddings', True):
                results = _sql_only_search(info.get('sql_conditions') or filter_list, safe_limit, filter_expired)
                confidence = 1.0 if results else 0.0
                filter_route = 'sql-only'
            elif s_type == 1:
                if ENABLE_SEARCH_V2 and (info.get('sql_conditions') or filter_list):
                    where_sql = info.get('sql_conditions') or filter_list
                    results, confidence = semantic_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb, where_sql=where_sql)
                    filter_route = 'prefilter'
                else:
                    results, confidence = semantic_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
            elif s_type == 2:
                if ENABLE_SEARCH_V2 and (info.get('sql_conditions') or filter_list):
                    where_sql = info.get('sql_conditions') or filter_list
                    results, confidence = keyword_search(query, limit=safe_limit, filter_expired=filter_expired, where_sql=where_sql)
                    filter_route = 'prefilter'
                else:
                    results, confidence = keyword_search(query, limit=safe_limit, filter_expired=filter_expired)
            else:
                if ENABLE_SEARCH_V2 and (info.get('sql_conditions') or filter_list):
                    where_sql = info.get('sql_conditions') or filter_list
                    results, confidence = hybrid_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb, where_sql=where_sql)
                    filter_route = 'prefilter'
                else:
                    results, confidence = hybrid_search(query, limit=safe_limit, filter_expired=filter_expired, use_negation=negation_emb)
        elif approach == 2:
            if categories:
                try:
                    progress_set(70, 'Executando busca por correspondência')
                except Exception:
                    pass
                if ENABLE_SEARCH_V2 and (info.get('sql_conditions') or filter_list):
                    where_sql = info.get('sql_conditions') or filter_list
                    results, confidence, _ = correspondence_search(
                        query_text=query,
                        top_categories=categories,
                        limit=safe_limit,
                        filter_expired=filter_expired,
                        console=None,
                        where_sql=where_sql,
                    )
                    filter_route = 'prefilter'
                else:
                    results, confidence, _ = correspondence_search(
                    query_text=query,
                    top_categories=categories,
                    limit=safe_limit,
                    filter_expired=filter_expired,
                    console=None,
                )
            elif ENABLE_SEARCH_V2 and not info.get('embeddings', True):
                # Fallback SQL-only quando embeddings=false e sem categorias
                results = _sql_only_search(info.get('sql_conditions') or filter_list, safe_limit, filter_expired)
                confidence = 1.0 if results else 0.0
                filter_route = 'sql-only'
        elif approach == 3:
            if categories:
                try:
                    progress_set(70, 'Executando busca filtrada por categoria')
                except Exception:
                    pass
                if ENABLE_SEARCH_V2 and (info.get('sql_conditions') or filter_list):
                    where_sql = info.get('sql_conditions') or filter_list
                    results, confidence, _ = category_filtered_search(
                        query_text=query,
                        search_type=s_type,
                        top_categories=categories,
                        limit=safe_limit,
                        filter_expired=filter_expired,
                        use_negation=negation_emb,
                        console=None,
                        where_sql=where_sql,
                    )
                    filter_route = 'prefilter'
                else:
                    results, confidence, _ = category_filtered_search(
                    query_text=query,
                    search_type=s_type,
                    top_categories=categories,
                    limit=safe_limit,
                    filter_expired=filter_expired,
                    use_negation=negation_emb,
                    console=None,
                )
            elif ENABLE_SEARCH_V2 and not info.get('embeddings', True):
                # Fallback SQL-only quando embeddings=false e sem categorias
                results = _sql_only_search(info.get('sql_conditions') or filter_list, safe_limit, filter_expired)
                confidence = 1.0 if results else 0.0
                filter_route = 'sql-only'
    except Exception as search_error:
        results = []
        confidence = 0.0
        # Notificação de erro na busca
        updated_notifs = list(notifications or [])
        try:
            notif = add_note(NOTIF_ERROR, "Erro ao executar busca. Tente novamente.")
            updated_notifs.append(notif)
        except Exception:
            pass
        # Retornar imediatamente com erro
        try:
            progress_reset()
        except Exception:
            pass
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False, updated_notifs

    try:
        progress_set(78, 'Ordenando resultados')
    except Exception:
        pass
    # Com V2 ativo, aplicamos pré-filtro no core; pós-filtro não é necessário.
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
                filters=(ui_filters or {}) if ENABLE_SEARCH_V2 else None,
                preproc_output=(info if (ENABLE_SEARCH_V2 and isinstance(info, dict)) else None),
            )
            try:
                if ENABLE_SEARCH_V2 and isinstance(info, dict):
                    dbg('PRE', f"saved user_prompts.preproc_output ok terms='{(info.get('search_terms') or '')[:60]}' sql_conds={len(info.get('sql_conditions') or [])}")
            except Exception:
                pass
            if prompt_id:
                try:
                    save_user_results(prompt_id, results or [])
                except Exception:
                    pass
                # Atualiza ref do evento agora que temos prompt_id
                try:
                    from gvg_usage import usage_event_set_ref
                    usage_event_set_ref('prompt', str(prompt_id))
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
        'filter_route': filter_route,
    }
    try:
        progress_set(100, 'Concluído')
        progress_reset()
    except Exception:
        pass
    # Evento de sessão (gatilho único para criar/ativar aba)
    try:
        sign = _make_query_signature(query, meta, results)
        session_event = {
            'token': current_token or int(time.time()*1000),
            'type': 'query',
            'status': 'completed',
            'title': (query or '').strip(),
            'signature': sign,
            'payload': {
                'results': results or [],
                'categories': categories or [],
                'meta': meta or {},
            }
        }
    except Exception:
        session_event = None
    # Importante: evitar escrever diretamente nas stores globais (results/categories/meta/last_query)
    # para não competir com sync_active_session. Apenas emitir o evento de sessão e encerrar o processamento.
    # Finalizar evento de uso
    try:
        from gvg_usage import usage_event_finish, record_usage  # type: ignore
        meta_end = {'results': len(results or [])}
        if usage_started:
            ok = usage_event_finish(meta_end)
            if not ok and uid:
                # fallback
                record_usage(uid, 'query', ref_type='prompt', ref_id=None, meta={**meta_end, 'fallback': 'finish_failed'})
        else:
            if uid:
                record_usage(uid, 'query', ref_type='prompt', ref_id=None, meta={**meta_end, 'fallback': 'no_start'})
    except Exception as e:
        dbg('USAGE', f"erro finish/fallback query: {e}")
    
    # Notificações de resultado da busca
    updated_notifs = list(notifications or [])
    try:
        count = len(results or [])
        if count > 0:
            # Sucesso: resultados encontrados
            notif = add_note(NOTIF_SUCCESS, f"Busca concluída: {count} resultado{'s' if count != 1 else ''} encontrado{'s' if count != 1 else ''}")
            updated_notifs.append(notif)
        else:
            # Aviso: nenhum resultado
            notif = add_note(NOTIF_WARNING, "Nenhum resultado encontrado. Tente termos diferentes.")
            updated_notifs.append(notif)
        
        # Aviso adicional se usando rota SQL-only
        if filter_route == 'sql-only':
            notif = add_note(NOTIF_INFO, "Busca realizada apenas com filtros SQL")
            updated_notifs.append(notif)
    except Exception:
        pass
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, session_event, False, updated_notifs


# ========================= Abas de resultados (sessões) =========================

"""
Criação/ativação de sessões com deduplicação por assinatura.
Fluxo: run_search emite store-session-event; este callback consome e cria/ativa aba.
"""
@app.callback(
    Output('store-result-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Input('store-session-event', 'data'),
    State('store-result-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def create_or_update_session(session_event, sessions, active):
    if not session_event:
        raise PreventUpdate
    try:
        sessions = dict(sessions or {})
        sign = session_event.get('signature')
        title = (session_event.get('title') or '').strip() or 'Consulta'
        s_type = session_event.get('type') or 'query'
        payload = session_event.get('payload') or {}
        status = session_event.get('status') or 'completed'
        token = session_event.get('token')

        # 1) Se evento é de conclusão (completed) tentar localizar sessão pendente via token
        if status == 'completed' and token is not None:
            for sid, sess in sessions.items():
                if sess.get('pending_token') == token:
                    # Atualizar esta sessão com dados finais
                    sess['results'] = payload.get('results') or []
                    sess['categories'] = payload.get('categories') or []
                    sess['meta'] = payload.get('meta') or {}
                    sess['signature'] = sign
                    sess.pop('pending_token', None)
                    sess['title'] = title  # manter texto original (sem Processando)
                    return sessions, sid

        # 2) Caso assinatura já exista (duplicidade)
        #    - Para 'history': mover a aba existente para o fim (direita) e ativar
        #    - Demais tipos: apenas ativar
        if sign:
            for sid, sess in sessions.items():
                if sess.get('signature') and sess.get('signature') == sign:
                    try:
                        if (session_event.get('type') or '').lower() == 'history':
                            # Reordenar: remover e reinserir para ir ao final (dict preserva ordem de inserção)
                            data = sessions.pop(sid)
                            sessions[sid] = data
                    except Exception:
                        pass
                    return sessions, sid

        # 3) Evento pendente: criar nova sessão vazia
        if status == 'pending':
            import time as _t
            sid = (('p-' if s_type == 'pncp' else 'q-') + str(int(_t.time()*1000)))
            # Limite de 100 abas (remove a mais antiga não ativa)
            keys = list(sessions.keys())
            if len(keys) >= 100:
                for k in keys:
                    if k != active:
                        sessions.pop(k, None)
                        break
            sessions[sid] = {
                'type': s_type,
                'title': title,  # será exibido como Processando na renderização
                'results': [],
                'categories': [],
                'meta': payload.get('meta') or {'status': 'processing'},
                'sort': None,
                'signature': None,
                'pending_token': token,
            }
            return sessions, sid
        # Limite de 100 abas (remove a mais antiga não ativa)
        keys = list(sessions.keys())
        if len(keys) >= 100:
            for k in keys:
                if k != active:
                    sessions.pop(k, None)
                    break
        import time as _t
        sid = (('p-' if s_type == 'pncp' else 'q-') + str(int(_t.time()*1000)))
        sessions[sid] = {
            'type': s_type,
            'title': title,
            'results': payload.get('results') or [],
            'categories': payload.get('categories') or [],
            'meta': payload.get('meta') or {},
            'sort': None,
            'signature': sign,
        }
        return sessions, sid
    except Exception:
        raise PreventUpdate


# Renderiza barra de abas
@app.callback(
    Output('tabs-bar', 'children'),
    Input('store-result-sessions', 'data'),
    Input('store-active-session', 'data'),
)
def render_tabs_bar(sessions, active):
    sessions = sessions or {}
    out = []
    for sid, sess in sessions.items():
        is_active = (sid == active)
        # Estilo base da aba
        base_style = dict(styles['tab_button_base'])
        close_style = dict(styles['tab_close_btn'])
        if sess.get('type') == 'pncp':
            # Cor dinâmica com base na data de encerramento
            status_color = None
            try:
                first = (sess.get('results') or [None])[0] or {}
                details = (first.get('details') or {}) if isinstance(first, dict) else {}
                end_date = (
                    details.get('dataencerramentoproposta')
                    or details.get('dataEncerramentoProposta')
                    or details.get('dataEncerramento')
                )
                _status, _color = _enc_status_and_color(end_date)
                status_color = _color
            except Exception:
                status_color = None
            # Fallback de cor quando inexistente
            status_color = status_color or '#2E7D32'  # verde padrão
            if is_active:
                base_style.update({
                    'backgroundColor': status_color,
                    'border': f'2px solid {status_color}',
                    'color': 'white',
                })
                close_style.update({
                    'border': '2px solid white',
                    'color': 'white',
                    'backgroundColor': 'transparent'
                })
            else:
                base_style.update({
                    'backgroundColor': 'white',
                    'border': f'2px solid {status_color}',
                    'color': status_color,
                })
                close_style.update({
                    'border': f'1px solid {status_color}',
                    'color': status_color,
                    'backgroundColor': 'white'
                })
        elif sess.get('type') == 'history':
            base_style.update(styles['tab_button_query'])
            if is_active:
                base_style.update(styles['tab_button_active'])
        elif sess.get('type') == 'boletim':
            base_style.update(styles['tab_button_query'])
            if is_active:
                base_style.update(styles['tab_button_active'])
        else:
            # Abas de consulta (query) permanecem como estão
            base_style.update(styles['tab_button_query'])
            if is_active:
                base_style.update(styles['tab_button_active'])
        # Define o label conforme o tipo da sessão
        if sess.get('type') == 'pncp':
            # Título: Rotulo - Local
            municipio = ''
            uf = ''
            rotulo = ''
            try:
                first = (sess.get('results') or [None])[0] or {}
                details = (first.get('details') or {}) if isinstance(first, dict) else {}
                municipio = details.get('unidade_orgao_municipio_nome') or ''
                uf = details.get('unidade_orgao_uf_sigla') or ''
                # Preferir sempre rotulo vindo do favorito/BD; somente fallback leve se inexistente
                rotulo = details.get('rotulo') or ''
                if not rotulo:
                    # Fallback secundário: NÃO usar objeto_compra inteiro para evitar poluição; curta referência
                    obj = details.get('objeto_compra') or ''
                    if isinstance(obj, str) and obj:
                        rotulo = (obj.split(' ')[0][:30])  # primeira palavra curta
            except Exception:
                municipio, uf, rotulo = '', '', ''
            loc = f"{municipio}/{uf}".strip('/') if (municipio or uf) else ''
            if not rotulo:
                # fallback final
                try:
                    pid = (details.get('numerocontrolepncp') if details else None) or (details.get('numero_controle_pncp') if details else None) or (first.get('id') if isinstance(first, dict) else None) or ''
                except Exception:
                    pid = ''
                rotulo = f"PNCP {pid}".strip()
            label_full = f"{rotulo} - {loc}" if loc else rotulo
        elif sess.get('type') == 'history':
            if sess.get('pending_token') is not None:
                label_full = "HISTÓRICO: Processando"
            else:
                q = sess.get('title') or ''
                q_short = (q[:40] + '...') if isinstance(q, str) else '...'
                label_full = f"HISTÓRICO: {q_short}"
        elif sess.get('type') == 'boletim':
            if sess.get('pending_token') is not None:
                label_full = "BOLETIM: Processando"
            else:
                q = sess.get('title') or ''
                q_short = (q[:40] + '...') if isinstance(q, str) else '...'
                label_full = f"BOLETIM: {q_short}"
        else:
            # Query tab: se pendente mostrar Processando + spinner
            if sess.get('pending_token') is not None:
                label_full = "CONSULTA: Processando"
            else:
                q = sess.get('title') or ''
                q_short = (q[:40] + '...') if isinstance(q, str) else '...'
                label_full = f"CONSULTA: {q_short}"
        # Truncamento defensivo para caber na aba (além do ellipsis via CSS)
        label = label_full

        # Left icon based on tab type
        if sess.get('type') == 'pncp':
            icon = html.I(className="fas fa-bookmark")
        elif sess.get('type') == 'history':
            icon = html.I(className="fas fa-history")
        elif sess.get('type') == 'boletim':
            icon = html.I(className="fas fa-calendar")
        else:
            if sess.get('pending_token') is not None:
                icon = html.I(className="fas fa-spinner fa-spin")
            else:
                icon = html.I(className="fas fa-search")
        out.append(html.Div([
            icon,
            html.Span(label, title=label_full),
            html.Button(html.I(className='fas fa-times'), id={'type': 'tab-close', 'sid': sid}, style=close_style, title='Fechar')
        ], id={'type': 'tab-activate', 'sid': sid}, style=base_style))
    return out


# Oculta/mostra a barra de abas conforme existência de sessões
@app.callback(
    Output('tabs-bar', 'style'),
    Input('store-result-sessions', 'data'),
)
def toggle_tabs_bar_style(sessions):
    if not sessions:
        return {'display': 'none'}
    return styles['tabs_bar']


# Ativar/fechar abas
@app.callback(
    Output('store-active-session', 'data', allow_duplicate=True),
    Output('store-result-sessions', 'data', allow_duplicate=True),
    Input({'type': 'tab-activate', 'sid': ALL}, 'n_clicks'),
    Input({'type': 'tab-close', 'sid': ALL}, 'n_clicks'),
    State('store-active-session', 'data'),
    State('store-result-sessions', 'data'),
    prevent_initial_call=True,
)
def on_tab_click(_activates, _closes, active, sessions):
    sessions = sessions or {}
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig = ctx.triggered[0]['prop_id']
    # Ignore synthetic triggers when components are created (n_clicks is None/0)
    try:
        clicks = int(ctx.triggered[0].get('value') or 0)
    except Exception:
        clicks = 0
    if clicks <= 0:
        raise PreventUpdate
    # Estrutura de id é dict; usamos substring
    if 'tab-close' in trig:
        # fechar
        try:
            import json
            sid = json.loads(trig.split('.')[0]).get('sid')
        except Exception:
            sid = None
        if not sid:
            raise PreventUpdate
        sessions.pop(sid, None)
        # Se fechou ativo, escolher outro (último da lista) ou None
        if active == sid:
            active = next(iter(sessions.keys()), None)
        return active, sessions
    else:
        try:
            import json
            sid = json.loads(trig.split('.')[0]).get('sid')
        except Exception:
            sid = None
        if not sid or sid not in sessions:
            raise PreventUpdate
        return sid, sessions


# Sincroniza sessão ativa com stores legadas (results/categories/meta/last_query)
@app.callback(
    Output('store-results', 'data', allow_duplicate=True),
    Output('store-results-sorted', 'data', allow_duplicate=True),
    Output('store-categories', 'data', allow_duplicate=True),
    Output('store-meta', 'data', allow_duplicate=True),
    Output('store-last-query', 'data', allow_duplicate=True),
    Input('store-active-session', 'data'),
    State('store-result-sessions', 'data'),
    prevent_initial_call=True,
)
def sync_active_session(active, sessions):
    sessions = sessions or {}
    sess = sessions.get(active) if active else None
    if not sess:
        raise PreventUpdate
    # Evitar sincronizar sessão de consulta pendente (sem resultados ainda)
    if sess.get('type') == 'query' and sess.get('pending_token') is not None:
        raise PreventUpdate
    results = sess.get('results') or []
    meta = sess.get('meta') or {}
    categories = sess.get('categories') or []
    # last_query deve refletir a aba ativa (para o card de resumo) em 'query', 'history' e 'boletim'
    last_query = (sess.get('title') or '') if (sess.get('type') in ('query','history','boletim')) else ''
    # results-sorted será recalculado pelo callback existente compute_sorted_results
    return results, [], categories, meta, last_query


# Clique em favorito: além de preencher pncp:<id>, abre uma aba PNCP
@app.callback(
    Output('store-result-sessions', 'data', allow_duplicate=True),
    Output('store-active-session', 'data', allow_duplicate=True),
    Input({'type': 'favorite-item', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    State('store-result-sessions', 'data'),
    State('store-active-session', 'data'),
    prevent_initial_call=True,
)
def open_pncp_tab_from_favorite(n_clicks_list, favs, sessions, active):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i; break
    if idx is None:
        raise PreventUpdate
    try:
        item = (favs or [])[idx]
        pid = str(item.get('numero_controle_pncp')) if item else None
    except Exception:
        pid = None
    if not pid:
        raise PreventUpdate
    sessions = sessions or {}
    # Reutiliza sessão existente via assinatura
    pncp_sign = f"pncp:{pid}"
    for sid, sess in sessions.items():
        if sess.get('signature') == pncp_sign:
            return sessions, sid
    # Criar nova sessão PNCP buscando detalhes completos do BD
    # Preferir descrição como título da aba PNCP; fallback para "PNCP <id>"
    # Tenta usar a descrição já presente no item de favoritos
    try:
        title = (
            (item.get('descricaocompleta') if item else None)
            or (item.get('descricaoCompleta') if item else None)
            or (item.get('objeto') if item else None)
            or (item.get('descricao') if item else None)
        )
        title = title.strip() if isinstance(title, str) else None
    except Exception:
        title = None
    details = {'numerocontrolepncp': pid}
    try:
        # Preferir wrappers centralizados
        sql = "SELECT\n  " + ",\n  ".join(get_contratacao_core_columns('c')) + f"\nFROM contratacao c\nWHERE c.{PRIMARY_KEY} = %s LIMIT 1"
        rows = db_fetch_all(sql, (pid,), as_dict=True, ctx="GSB.open_pncp_tab_from_favorite")
        if rows:
            rec = rows[0]
            details = {k: rec.get(k) for k in rec.keys()}
            _augment_aliases(details)
            # Título preferencial com descrição
            desc = (
                details.get('descricaocompleta')
                or details.get('descricaoCompleta')
                or details.get('objeto')
                or details.get('descricao')
            )
            if isinstance(desc, str) and desc.strip():
                title = desc.strip()
    except Exception:
        # mantém details mínimo (com id) como fallback
        pass

    mock_result = {'id': pid, 'numero_controle': pid, 'similarity': 1.0, 'rank': 1, 'details': details}
    import time as _t
    sid = f"p-{int(_t.time()*1000)}"
    # Limite 100
    keys = list(sessions.keys())
    if len(keys) >= 100:
        for k in keys:
            if k != active:
                sessions.pop(k, None)
                break
    sessions[sid] = {
        'type': 'pncp',
        'title': (title or f"PNCP {pid}"),
        'results': [mock_result],
        'categories': [],
    'meta': {'order': 1, 'count': 1},
    'sort': None,
    'signature': pncp_sign,
    }
    # Ajuste: garantir que rotulo (e local se preciso) fiquem presentes em details para o render_tabs_bar usar "rotulo - local"
    try:
        fav_rotulo = (item or {}).get('rotulo') or ''
        if fav_rotulo and not details.get('rotulo'):
            details['rotulo'] = fav_rotulo
        # Fallback de local caso não venha do BD
        if not details.get('unidade_orgao_municipio_nome') and (item or {}).get('unidade_orgao_municipio_nome'):
            details['unidade_orgao_municipio_nome'] = item.get('unidade_orgao_municipio_nome')
        if not details.get('unidade_orgao_uf_sigla') and (item or {}).get('unidade_orgao_uf_sigla'):
            details['unidade_orgao_uf_sigla'] = item.get('unidade_orgao_uf_sigla')
    except Exception:
        pass
    return sessions, sid


# Callback: seta/spinner do botão de envio no estilo Reports
@app.callback(
    Output('submit-button', 'children'),
    Output('submit-button', 'disabled'),
    Output('submit-button', 'style'),
    Input('processing-state', 'data'),
    Input('query-input', 'value'),
    Input('store-search-filters', 'data'),
)
def update_submit_button(is_processing, query_text, filters):
    # Enquanto processa: mostra spinner e desabilita
    if is_processing:
        return html.I(className="fas fa-spinner fa-spin", style={'color': 'white'}), True, styles['arrow_button']
    # Habilita se houver texto na query OU qualquer filtro avançado preenchido
    has_query = bool((query_text or '').strip())
    try:
        has_filters = _has_any_filter(filters)
    except Exception:
        has_filters = False
    enabled = bool(has_query or has_filters)
    st = dict(styles['arrow_button'])
    st['opacity'] = 1.0 if enabled else 0.4
    return html.I(className="fas fa-arrow-right"), (not enabled), st


# Mostrar/ocultar spinner central no painel direito (comportamento global)
@app.callback(
    Output('gvg-center-spinner', 'style'),
    Input('processing-state', 'data')
)
def toggle_center_spinner(is_processing):
    # Exibe o spinner central sempre que houver processamento global ativo
    return {'display': 'block'} if is_processing else {'display': 'none'}


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


# Reflete a barra de progresso na UI (comportamento global)
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
    try:
        percent = int((data or {}).get('percent', 0))
    except Exception:
        percent = 0
    label = (data or {}).get('label') or ''

    show_progress = bool(is_processing and (percent > 0 and percent < 100))

    bar_style = dict(styles['progress_bar_container'])
    bar_style['display'] = 'block' if show_progress else 'none'

    fill_style = dict(styles['progress_fill'])
    fill_style['width'] = f'{percent}%'
    label_text = f"{percent}% — {label}" if label else (f"{percent}%" if percent else '')
    label_style = dict(styles['progress_label'])
    label_style['display'] = 'block' if show_progress else 'none'
    return fill_style, bar_style, label_text, label_style


# Limpar conteúdo do painel de resultados ao iniciar nova busca (global)
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
    prevent_initial_call=True,
)
def clear_results_content_on_start(is_processing):
    if not is_processing:
        raise PreventUpdate
    # Esvazia conteúdos imediatamente durante o início do processamento global
    return [], [], [], [], {}, {}, {}, {}


# Ocultar cartões/tabelas enquanto processa (global; evita flicker de conteúdo antigo)
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
    Output('store-session-event', 'data', allow_duplicate=True),
    Output('store-current-query-token', 'data', allow_duplicate=True),
    Input('submit-button', 'n_clicks'),
    State('query-input', 'value'),
    State('processing-state', 'data'),
    State('store-search-filters', 'data'),
    prevent_initial_call=True,
)
def set_processing_state(n_clicks, query, is_processing, ui_filters):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    # Permitir filtro-only quando V2: ui_filters já vem como State
    filters = ui_filters
    try:
        if isinstance(filters, str):
            import json as _json
            filters = _json.loads(filters)
    except Exception:
        pass
    if is_processing:
        raise PreventUpdate
    if (not query or not query.strip()) and not (ENABLE_SEARCH_V2 and _has_any_filter(filters)):
        raise PreventUpdate
    # Criar token único para esta rodada
    import time as _t
    token = int(_t.time()*1000)
    # Evento de sessão inicial "pendente" (aba vazia)
    pending_event = {
        'token': token,
        'type': 'query',
        'status': 'pending',
        'title': (query or '').strip(),
        'signature': None,  # ainda não conhecida
        'payload': {
            'results': [],
            'categories': [],
            'meta': {'status': 'processing'}
        }
    }
    return True, pending_event, token


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
    icon = 'fa-chevron-up' if is_open else 'fa-chevron-down'
    return [
        html.Div([
            html.I(className='fas fa-sliders-h', style=styles['section_icon']),
            html.Div("Configurações de Busca", style=styles['card_title'])
        ], style=styles['section_header_left']),
        html.I(className=f"fas {icon}")
    ]


# Toggle collapse de Filtros Avançados
@app.callback(
    Output('filters-collapse', 'is_open'),
    Input('filters-toggle-btn', 'n_clicks'),
    State('filters-collapse', 'is_open'),
    prevent_initial_call=True,
)
def toggle_filters(n, is_open):
    if not n:
        raise PreventUpdate
    return not bool(is_open)


@app.callback(
    Output('filters-toggle-btn', 'children'),
    Input('filters-collapse', 'is_open')
)
def update_filters_icon(is_open):
    icon = 'fa-chevron-up' if is_open else 'fa-chevron-down'
    return [
        html.Div([
            html.I(className='fas fa-filter', style=styles['section_icon']),
            html.Div("Filtros Avançados", style=styles['card_title'])
        ], style=styles['section_header_left']),
        html.I(className=f"fas {icon}")
    ]


# Sincroniza Store de Filtros com inputs da UI
@app.callback(
    Output('store-search-filters', 'data'),
    Input('flt-pncp', 'value'),
    Input('flt-orgao', 'value'),
    Input('flt-cnpj', 'value'),
    Input('flt-uf', 'value'),
    Input('flt-municipio', 'value'),
    Input('flt-modalidade-id', 'value'),
    Input('flt-modo-id', 'value'),
    Input('flt-date-field', 'value'),
    Input('flt-date-start', 'value'),
    Input('flt-date-end', 'value'),
    prevent_initial_call=False,
)
def sync_filters_store(pncp, orgao, cnpj, uf, municipio, modalidade_id, modo_id, date_field, start_date_txt, end_date_txt):
    def val(x):
        try:
            s = (x or '').strip()
            return s if s else None
        except Exception:
            return None
    # Parse dd/mm/aaaa -> YYYY-MM-DD (also accept ISO input)
    def to_iso(dtxt: str | None) -> str | None:
        if not dtxt:
            return None
        s = str(dtxt).strip()
        if not s:
            return None
        try:
            # Accept already-ISO
            if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                return s
            m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
            if m:
                dd, mm, yy = m.group(1), m.group(2), m.group(3)
                # basic sanity check
                int(dd); int(mm); int(yy)
                return f"{yy}-{mm}-{dd}"
        except Exception:
            return None
        return None
    # uf pode ser lista (multi=True)
    uf_payload = None
    try:
        if isinstance(uf, list):
            uf_payload = [str(x).strip() for x in uf if str(x or '').strip()]
            if not uf_payload:
                uf_payload = None
        else:
            s = (uf or '').strip()
            uf_payload = s if s else None
    except Exception:
        uf_payload = None
    # Dates parsing and coercion: ensure end >= start when both provided
    iso_start = to_iso(start_date_txt or '')
    iso_end = to_iso(end_date_txt or '')
    try:
        if iso_start and iso_end:
            from datetime import datetime as _d
            ds = _d.strptime(iso_start, '%Y-%m-%d').date()
            de = _d.strptime(iso_end, '%Y-%m-%d').date()
            if de < ds:
                iso_end = iso_start  # force end >= start
    except Exception:
        pass
    payload = {
        'pncp': val(pncp),
        'orgao': val(orgao),
        'cnpj': val(cnpj),
        'uf': uf_payload,
        'municipio': val(municipio),
    'modalidade_id': modalidade_id if modalidade_id not in ('', None, []) else None,
    'modo_id': modo_id if modo_id not in ('', None, []) else None,
        'date_field': (date_field or 'encerramento'),
        'date_start': iso_start,
        'date_end': iso_end,
    }
    return payload

# Garantir que a data final nunca seja menor que a inicial (ajuste visual)
@app.callback(
    Output('flt-date-end', 'value'),
    Input('flt-date-start', 'value'),
    State('flt-date-end', 'value'),
    prevent_initial_call=True,
)
def ensure_end_after_start(start_txt, end_txt):
    try:
        if not start_txt or not end_txt:
            raise PreventUpdate
        m1 = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(start_txt).strip())
        m2 = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(end_txt).strip())
        if not (m1 and m2):
            raise PreventUpdate
        from datetime import datetime as _d
        ds = _d.strptime(f"{m1.group(3)}-{m1.group(2)}-{m1.group(1)}", '%Y-%m-%d').date()
        de = _d.strptime(f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}", '%Y-%m-%d').date()
        if de < ds:
            return start_txt
    except Exception:
        pass
    raise PreventUpdate


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
    icon = 'fa-chevron-up' if is_open else 'fa-chevron-down'
    return [
        html.Div([
            html.I(className='fas fa-history', style=styles['section_icon']),
            html.Div('Histórico', style=styles['card_title'])
        ], style=styles['section_header_left']),
        html.I(className=f"fas {icon}")
    ]


@app.callback(
    Output('query-container', 'style'),
    Input('store-config-open', 'data')
)
def move_query_on_collapse(is_open):
    # Keep the query container directly below the config card with standard spacing
    base = styles['input_container'].copy()
    base['marginTop'] = '10px'
    return base
@app.callback(
    Output('flt-modalidade-id', 'options'),
    Input('store-auth', 'data'),
    prevent_initial_call=False,
)
def load_modalidade_options(_auth):
    """Retorna opções estáticas de modalidades (sem consultar o BD)."""
    try:
        return MODALIDADE_OPTIONS
    except Exception:
        return []

@app.callback(
    Output('flt-modo-id', 'options'),
    Input('store-auth', 'data'),
    prevent_initial_call=False,
)
def load_modo_options(_auth):
    """Retorna opções estáticas de modos de disputa (sem consultar o BD)."""
    try:
        return MODO_OPTIONS
    except Exception:
        return []



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
    # Busca dados enriquecidos (texto + configurações) e reconcilia com a ordem atual de history
    from gvg_user import fetch_prompts_with_config
    items_order = history or []
    if not items_order:
        return html.Div('Sem consultas ainda.', style=styles['muted_text'])
    try:
        rich = fetch_prompts_with_config(limit=max(50, len(items_order))) or []
        # Mapa por texto
        by_text = { (r.get('text') or '').strip(): r for r in rich }
    except Exception:
        by_text = {}
    buttons = []
    for i, q in enumerate(items_order):
        q_txt = (q or '').strip()
        rec = by_text.get(q_txt) or {}
        # Linha 1: prompt em negrito
        line1 = html.Div(q_txt, style=styles['history_prompt'])
        # Linha 2: configurações (10px)
        cfg_spans = []
        try:
            st = rec.get('search_type'); sa = rec.get('search_approach'); rl = rec.get('relevance_level'); sm = rec.get('sort_mode')
            mr = rec.get('max_results'); tc = rec.get('top_categories_count'); fe = rec.get('filter_expired')
            if st in SEARCH_TYPES:
                cfg_spans.append(html.Span([
                    html.Span('Tipo: ', style={'fontWeight': 'bold'}),
                    html.Span(SEARCH_TYPES[st]['name'], style={'fontStyle': 'italic'})
                ]))
            if sa in SEARCH_APPROACHES:
                cfg_spans.append(html.Span([
                    html.Span('Abordagem: ', style={'fontWeight': 'bold'}),
                    html.Span(SEARCH_APPROACHES[sa]['name'], style={'fontStyle': 'italic'})
                ]))
            if rl in RELEVANCE_LEVELS:
                cfg_spans.append(html.Span([
                    html.Span('Relevância: ', style={'fontWeight': 'bold'}),
                    html.Span(RELEVANCE_LEVELS[rl]['name'], style={'fontStyle': 'italic'})
                ]))
            if sm in SORT_MODES:
                cfg_spans.append(html.Span([
                    html.Span('Ordenação: ', style={'fontWeight': 'bold'}),
                    html.Span(SORT_MODES[sm]['name'], style={'fontStyle': 'italic'})
                ]))
            if mr is not None:
                cfg_spans.append(html.Span([
                    html.Span('Máx: ', style={'fontWeight': 'bold'}),
                    html.Span(str(mr), style={'fontStyle': 'italic'})
                ]))
            if tc is not None:
                cfg_spans.append(html.Span([
                    html.Span('Categorias: ', style={'fontWeight': 'bold'}),
                    html.Span(str(tc), style={'fontStyle': 'italic'})
                ]))
            if fe is not None:
                cfg_spans.append(html.Span([
                    html.Span('Encerradas: ', style={'fontWeight': 'bold'}),
                    html.Span('ON' if fe else 'OFF', style={'fontStyle': 'italic'})
                ]))
        except Exception:
            pass
        if cfg_spans:
            inter_cfg = []
            for j, p in enumerate(cfg_spans):
                if j > 0:
                    inter_cfg.append(html.Span(' | '))
                inter_cfg.append(p)
            line2 = html.Div(inter_cfg, style=styles['history_config'])
        else:
            line2 = html.Div('', style=styles['history_config'])
        # Linha 3: filtros (se houver)
        line3 = html.Div('', style=styles['history_config'])
        try:
            f = rec.get('filters') or {}
            if isinstance(f, str):
                import json as _json
                try:
                    f = _json.loads(f)
                except Exception:
                    f = {}
            def _has(v):
                if v is None:
                    return False
                if isinstance(v, str):
                    return bool(v.strip())
                if isinstance(v, list):
                    return len([x for x in v if str(x).strip()]) > 0
                return True
            parts = []
            if _has(f.get('pncp')):
                parts.append(html.Span([
                    html.Span('PNCP nº: ', style={'fontWeight': 'bold'}),
                    html.Span(str(f.get('pncp') or ''), style={'fontStyle': 'italic'})
                ]))
            if _has(f.get('orgao')):
                parts.append(html.Span([
                    html.Span('Órgão: ', style={'fontWeight': 'bold'}),
                    html.Span(str(f.get('orgao') or ''), style={'fontStyle': 'italic'})
                ]))
            if _has(f.get('cnpj')):
                parts.append(html.Span([
                    html.Span('CNPJ: ', style={'fontWeight': 'bold'}),
                    html.Span(str(f.get('cnpj') or ''), style={'fontStyle': 'italic'})
                ]))
            if _has(f.get('uf')):
                uf_val = f.get('uf')
                if isinstance(uf_val, list):
                    uf_txt = ', '.join([str(x).strip() for x in uf_val if str(x).strip()])
                else:
                    uf_txt = str(uf_val or '').strip()
                if uf_txt:
                    parts.append(html.Span([
                        html.Span('UF: ', style={'fontWeight': 'bold'}),
                        html.Span(uf_txt, style={'fontStyle': 'italic'})
                    ]))
            if _has(f.get('municipio')):
                parts.append(html.Span([
                    html.Span('Municípios: ', style={'fontWeight': 'bold'}),
                    html.Span(str(f.get('municipio') or ''), style={'fontStyle': 'italic'})
                ]))
            if _has(f.get('modalidade_id')):
                mid = f.get('modalidade_id')
                if isinstance(mid, list):
                    mid_txt = ', '.join([str(x).strip() for x in mid if str(x).strip()])
                else:
                    mid_txt = str(mid or '').strip()
                parts.append(html.Span([
                    html.Span('Modalidade: ', style={'fontWeight': 'bold'}),
                    html.Span(mid_txt, style={'fontStyle': 'italic'})
                ]))
            if _has(f.get('modo_id')):
                mo = f.get('modo_id')
                if isinstance(mo, list):
                    mo_txt = ', '.join([str(x).strip() for x in mo if str(x).strip()])
                else:
                    mo_txt = str(mo or '').strip()
                parts.append(html.Span([
                    html.Span('Modo: ', style={'fontWeight': 'bold'}),
                    html.Span(mo_txt, style={'fontStyle': 'italic'})
                ]))
            df_label = {'encerramento': 'Encerramento', 'abertura': 'Abertura', 'publicacao': 'Publicação'}.get(str(f.get('date_field') or 'encerramento'), 'Encerramento')
            ds = f.get('date_start'); de = f.get('date_end')
            def _fmt(dv):
                return _format_br_date(dv) if dv else ''
            if ds or de:
                date_text = None
                if ds and de:
                    date_text = f"desde {_fmt(ds)} até {_fmt(de)}"
                elif ds:
                    date_text = f"desde {_fmt(ds)}"
                elif de:
                    date_text = f"até {_fmt(de)}"
                if date_text:
                    parts.append(html.Span([
                        html.Span(f"Período ({df_label}): ", style={'fontWeight': 'bold'}),
                        html.Span(date_text, style={'fontStyle': 'italic'})
                    ]))
            if parts:
                inter = []
                for j, p in enumerate(parts):
                    if j > 0:
                        inter.append(html.Span(' | '))
                    inter.append(p)
                line3 = html.Div([html.Span('Filtros: ', style={'fontWeight': 'bold'}), html.Span(inter)], style=styles['history_config'])
        except Exception:
            pass
        body = html.Div([line1, line2, line3])
        buttons.append(
            html.Div([
                html.Button(
                    body,
                    id={'type': 'history-item', 'index': i},
                    title=q_txt,
                    style=styles['history_item_button']
                ),
                html.Div([
                    html.Button(
                        html.I(className='fas fa-trash'),
                        id={'type': 'history-delete', 'index': i},
                        title='Apagar esta consulta',
                        style=styles['history_delete_btn'],
                        className='delete-btn'
                    ),
                    html.Button(
                        html.I(className='fas fa-undo'),
                        id={'type': 'history-replay', 'index': i},
                        title='Reabrir resultados desta consulta',
                        style=styles['history_replay_btn'],
                        className='delete-btn'
                    ),
                    html.Button(
                        html.I(className='fas fa-envelope'),
                        id={'type': 'history-email', 'index': i},
                        title='Enviar resultados por e-mail',
                        style=styles.get('fav_email_btn', styles.get('history_replay_btn', {})),
                        className='delete-btn'
                    )
                ], style=styles['history_actions_col'])
            ], className='history-item-row', style=styles['history_item_row'])
        )
    return html.Div(buttons, style=styles['column'])
@app.callback(
    Output('status-bar', 'children'),
    Output('categories-table', 'children'),
    Input('store-meta', 'data'),
    Input('store-categories', 'data'),
    State('store-last-query', 'data'),
    State('store-search-filters', 'data'),
    prevent_initial_call=True,
)
def render_status_and_categories(meta, categories, last_query, filters):
    if not meta:
        # hide both when no meta
        return dash.no_update, dash.no_update
    status = [
        html.Div([
            html.Span('Busca: ', style={'fontWeight': 'bold'}),
            html.Span(last_query or '', style={'fontStyle': 'italic'})
        ], style={'marginTop': '6px'}),
        html.Div([
            html.Span('Tipo: ', style={'fontWeight': 'bold'}), html.Span(SEARCH_TYPES.get(meta.get('search'),{}).get('name',''), style={'fontStyle': 'italic'}),
            html.Span(" | "),
            html.Span('Abordagem: ', style={'fontWeight': 'bold'}), html.Span(SEARCH_APPROACHES.get(meta.get('approach'),{}).get('name',''), style={'fontStyle': 'italic'}),
            html.Span(" | "),
            html.Span('Relevância: ', style={'fontWeight': 'bold'}), html.Span(RELEVANCE_LEVELS.get(meta.get('relevance'),{}).get('name',''), style={'fontStyle': 'italic'}),
            html.Span(" | "),
            html.Span('Ordenação: ', style={'fontWeight': 'bold'}), html.Span(SORT_MODES.get(meta.get('order'),{}).get('name',''), style={'fontStyle': 'italic'})
        ], style={'color': '#555', 'marginTop': '6px'}),
        html.Div([
            html.Span('Máx Resultados: ', style={'fontWeight': 'bold'}), html.Span(str(meta.get('max_results', '')), style={'fontStyle': 'italic'}),
            html.Span(" | "),
            html.Span('Categorias: ', style={'fontWeight': 'bold'}), html.Span(str(meta.get('top_categories', '')), style={'fontStyle': 'italic'}),
            html.Span(" | "),
            html.Span('Filtrar Data Encerradas: ', style={'fontWeight': 'bold'}), html.Span('ON' if meta.get('filter_expired') else 'OFF', style={'fontStyle': 'italic'}),
        ], style={'color': '#555', 'marginTop': '6px'})
    ]

    # Filtros avançados (resumo) — mostrar quando houver algum ativo
    try:
        f = filters or {}
        def _has(v):
            if v is None:
                return False
            if isinstance(v, str):
                return bool(v.strip())
            if isinstance(v, list):
                return len([x for x in v if str(x).strip()]) > 0
            return True
        parts = []
        if _has(f.get('pncp')):
            parts.append(html.Span([
                html.Span('PNCP nº: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('pncp') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('orgao')):
            parts.append(html.Span([
                html.Span('Órgão: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('orgao') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('cnpj')):
            parts.append(html.Span([
                html.Span('CNPJ: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('cnpj') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('uf')):
            uf_val = f.get('uf')
            if isinstance(uf_val, list):
                uf_txt = ', '.join([str(x).strip() for x in uf_val if str(x).strip()])
            else:
                uf_txt = str(uf_val or '').strip()
            if uf_txt:
                parts.append(html.Span([
                    html.Span('UF: ', style={'fontWeight': 'bold'}),
                    html.Span(uf_txt, style={'fontStyle': 'italic'})
                ]))
        if _has(f.get('municipio')):
            parts.append(html.Span([
                html.Span('Municípios: ', style={'fontWeight': 'bold'}),
                html.Span(str(f.get('municipio') or ''), style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('modalidade_id')):
            mid = f.get('modalidade_id')
            if isinstance(mid, list):
                mid_txt = ', '.join([str(x).strip() for x in mid if str(x).strip()])
            else:
                mid_txt = str(mid or '').strip()
            parts.append(html.Span([
                html.Span('Modalidade: ', style={'fontWeight': 'bold'}),
                html.Span(mid_txt, style={'fontStyle': 'italic'})
            ]))
        if _has(f.get('modo_id')):
            mo = f.get('modo_id')
            if isinstance(mo, list):
                mo_txt = ', '.join([str(x).strip() for x in mo if str(x).strip()])
            else:
                mo_txt = str(mo or '').strip()
            parts.append(html.Span([
                html.Span('Modo: ', style={'fontWeight': 'bold'}),
                html.Span(mo_txt, style={'fontStyle': 'italic'})
            ]))
        # Date range with label
        df_label = {'encerramento': 'Encerramento', 'abertura': 'Abertura', 'publicacao': 'Publicação'}.get(str(f.get('date_field') or 'encerramento'), 'Encerramento')
        ds = f.get('date_start')
        de = f.get('date_end')
        def _fmt(dv):
            return _format_br_date(dv) if dv else ''
        if ds or de:
            date_text = None
            if ds and de:
                date_text = f"desde {_fmt(ds)} até {_fmt(de)}"
            elif ds:
                date_text = f"desde {_fmt(ds)}"
            elif de:
                date_text = f"até {_fmt(de)}"
            if date_text:
                parts.append(html.Span([
                    html.Span(f"Período ({df_label}): ", style={'fontWeight': 'bold'}),
                    html.Span(date_text, style={'fontStyle': 'italic'})
                ]))
        if parts:
            # separadores ' | '
            interleaved = []
            for i, p in enumerate(parts):
                if i > 0:
                    interleaved.append(html.Span(' | '))
                interleaved.append(p)
            status.insert(1, html.Div([
                html.Span('Filtros: ', style={'fontWeight': 'bold'}),
                html.Span(interleaved)
            ], style={'marginTop': '6px'}))
    except Exception:
        pass

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
            'color': _COLOR_PRIMARY,
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
        if SQL_DEBUG:
            dbg('UI', "render_details: Nenhum resultado para renderizar.")
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

        status_text = _enc_status_text(_enc_status, raw_en)
        tag = html.Span(status_text, style={**styles['date_status_tag'], 'backgroundColor': enc_color}) if status_text else None
        # Modalidade e Modo de Disputa
        modalidade_id = (
            d.get('modalidade_id') or d.get('modalidadeid') or d.get('modalidadeId')
        )
        modalidade_nome = (
            d.get('modalidade_nome') or d.get('modalidadenome') or d.get('modalidadeNome')
        )
        modo_id = (
            d.get('modo_disputa_id') or d.get('mododisputaid') or d.get('modaDisputaId') or d.get('modadisputaid')
        )
        modo_nome = (
            d.get('modo_disputa_nome') or d.get('mododisputanome') or d.get('modaDisputaNome')
        )

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
                html.Span('Modalidade: ', style={'fontWeight': 'bold'}),
                html.Span(f"{str(modalidade_id) if modalidade_id else 'N/A'}" + (f" - {modalidade_nome}" if modalidade_nome else '' ))
            ]),
            html.Div([
                html.Span('Modo de Disputa: ', style={'fontWeight': 'bold'}),
                html.Span(f"{str(modo_id) if modo_id else 'N/A'}" + (f" - {modo_nome}" if modo_nome else '' ))
            ]),
            # Datas em linhas separadas
            html.Div([
                html.Span('Abertura: ', style={'fontWeight': 'bold'}),
                html.Span(str(data_ab), )
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '4px'}),
            html.Div([
                html.Span('Encerramento: ', style={'fontWeight': 'bold'}),
                html.Span(str(data_en), style={'color': enc_color, 'fontWeight': 'bold'}),
                tag
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginTop': '2px'}),
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
            ], className='gvg-right-actions', style=styles['right_panel_actions']),
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
                className='gvg-panel-wrapper',
                style=styles['panel_wrapper']
            )
        ], style=styles['details_right_panel'])

        # Card final com duas colunas (detalhes 60% / itens 40%)
        _card_style = dict(styles['result_card'])
        _card_style['marginBottom'] = '6px'  # reduzir espaço vertical entre cards (apenas nos cards de detalhe)
        
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
            ], className='gvg-details-row', style={'display': 'flex', 'gap': '10px', 'alignItems': 'stretch'}),
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
    if not results:
        return children_out, style_out, btn_styles, updated_cache
    # Build pncp id list aligned with components order
    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    # Normaliza cliques para casar com número de componentes
    if not isinstance(n_clicks_list, list):
        n_clicks_list = [0] * len(pncp_ids)
    elif len(n_clicks_list) < len(pncp_ids):
        n_clicks_list = list(n_clicks_list) + [0] * (len(pncp_ids) - len(n_clicks_list))
    elif len(n_clicks_list) > len(pncp_ids):
        n_clicks_list = list(n_clicks_list[:len(pncp_ids)])

    for i in range(len(pncp_ids)):
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
    if not results:
        return children_out, style_out, btn_styles, updated_cache
    pncp_ids = []
    for r in results:
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        pncp_ids.append(str(pid) if pid is not None else 'N/A')
    # Normaliza cliques para casar com número de componentes
    if not isinstance(n_clicks_list, list):
        n_clicks_list = [0] * len(pncp_ids)
    elif len(n_clicks_list) < len(pncp_ids):
        n_clicks_list = list(n_clicks_list) + [0] * (len(pncp_ids) - len(n_clicks_list))
    elif len(n_clicks_list) > len(pncp_ids):
        n_clicks_list = list(n_clicks_list[:len(pncp_ids)])

    for i in range(len(pncp_ids)):
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
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'resumo-btn', 'pncp': ALL}, 'n_clicks'),
    Input('store-panel-active', 'data'),
    State('store-results-sorted', 'data'),
    State('store-cache-resumo', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def load_resumo_for_cards(n_clicks_list, active_map, results, cache_resumo, notifications):
    """Generate and display a summary for the main document of each process.

    Heuristic: prefer PDFs matching common names (edital, termo de referencia/TR, projeto basico,
    anexo i, pregão/pe/concorrência/dispensa); else first PDF; else first document.
    """
    # Usar funções do pipeline de documentos do módulo gvg_documents (já importadas no topo)
    # DOCUMENTS_AVAILABLE é definido no início deste arquivo, com base nas imports de summarize_document/process_pncp_document
    children_out, style_out, btn_styles = [], [], []
    # Inicializar lista de notificações atualizada
    updated_notifs = list(notifications or [])
    # Debug início do callback

    updated_cache = dict(cache_resumo or {})
    # Quando não há resultados, não há componentes correspondentes; retornar listas vazias é seguro
    if not results:
        # Retorno deve respeitar 5 outputs
        return children_out, style_out, btn_styles, updated_cache, updated_notifs

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

    # Normaliza a lista de cliques para ter o mesmo tamanho dos componentes
    if not isinstance(n_clicks_list, list):
        n_clicks_list = [0] * len(pncp_ids)
    elif len(n_clicks_list) < len(pncp_ids):
        n_clicks_list = list(n_clicks_list) + [0] * (len(pncp_ids) - len(n_clicks_list))
    elif len(n_clicks_list) > len(pncp_ids):
        n_clicks_list = list(n_clicks_list[:len(pncp_ids)])

    for i in range(len(pncp_ids)):
        pid = pncp_ids[i]
        clicks = (n_clicks_list[i] or 0)
        is_open = (str(pid) in (active_map or {}) and (active_map or {}).get(str(pid)) == 'resumo')
    # debug opcional
    # if SQL_DEBUG:
    #     dbg('RESUMO', f"index={i} pncp={pid} clicks={clicks} -> {'abrir' if is_open else 'fechar'}")

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
            # Helper para validar se um resumo é "bom" (nem erro, nem fallback)
            def _is_good_summary(text: str | None) -> bool:
                if not isinstance(text, str) or not text.strip():
                    return False
                t = text.strip()
                if t.startswith('Erro'):
                    return False
                if t == 'Não foi possível gerar o resumo.':
                    return False
                if 'Limite diário de resumos atingido' in t:
                    return False
                return True

            # 1) Sempre tentar BD primeiro (prioridade sobre cache)
            try:
                user = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
                uid = (user or {}).get('uid') or ''
            except Exception:
                uid = ''
            if uid:
                try:
                    db_summary = get_user_resumo(uid, pid)
                except Exception:
                    db_summary = None
                if _is_good_summary(db_summary):
                    if SQL_DEBUG:
                        sz = len(db_summary) if isinstance(db_summary, str) else 'N/A'
                        dbg('RESUMO', f"Resumo obtido do BD (chars={sz})")
                    try:
                        updated_cache[str(pid)] = {'docs': (docs or []), 'summary': db_summary}
                    except Exception:
                        pass
                    children_out.append([html.Div(dcc.Markdown(children=db_summary, className='markdown-summary'), style=styles['details_content_inner'])])
                    style_out[-1] = {**style_out[-1], 'display': 'block'}
                    btn_styles[-1] = inverted_btn_style
                    continue

            # 2) Se não houver BD válido, tentar cache somente se for bom
            try:
                if isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'summary' in cache_resumo[str(pid)]:
                    cached_summary = cache_resumo[str(pid)]['summary']
                    if _is_good_summary(cached_summary):
                        children_out.append([html.Div(dcc.Markdown(children=cached_summary, className='markdown-summary'), style=styles['details_content_inner'])])
                        style_out[-1] = {**style_out[-1], 'display': 'block'}
                        btn_styles[-1] = inverted_btn_style
                        continue
            except Exception:
                pass

            # Antes de gerar, tentar carregar do BD por usuário
            try:
                user = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
                uid = (user or {}).get('uid') or ''
            except Exception:
                uid = ''
            if uid:
                try:
                    db_summary = get_user_resumo(uid, pid)
                except Exception:
                    db_summary = None
                if db_summary:
                    # Debug: indicar caminho GET (BD)
                    if SQL_DEBUG:
                        sz = len(db_summary) if isinstance(db_summary, str) else 'N/A'
                        dbg('RESUMO', f"Resumo obtido do BD (chars={sz})")
                    try:
                        updated_cache[str(pid)] = {'docs': (docs or []), 'summary': db_summary}
                    except Exception:
                        pass
                    children_out.append([html.Div(dcc.Markdown(children=db_summary, className='markdown-summary'), style=styles['details_content_inner'])])
                    style_out[-1] = {**style_out[-1], 'display': 'block'}
                    btn_styles[-1] = inverted_btn_style
                    continue
            if SQL_DEBUG:
                dbg('DOCS', f"RESUMO pncp={pid} documentos_encontrados={len(docs)}")
            if not docs:
                children_out.append(html.Div('Nenhum documento encontrado para este processo.', style=styles['details_content_inner']))
                style_out[-1] = {**style_out[-1], 'display': 'block'}
                btn_styles[-1] = inverted_btn_style
                continue

            # Preparar dados PNCP
            pncp_data = {}
            # Build pncp_data from matching result
            try:
                d = (results[i] or {}).get('details', {}) or {}
                pncp_data = _build_pncp_data(d)
            except Exception:
                pncp_data = {}
            # Timestamp único por PNCP (lote)
            try:
                if isinstance(pncp_data, dict):
                    if not pncp_data.get('batch_ts'):
                        pncp_data['batch_ts'] = datetime.now().strftime('%Y%m%d_%H%M')
            except Exception:
                pass

            # Call summarizer para TODOS os documentos e concatenar resultados
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
                        html.I(className="fas fa-spinner fa-spin", style={'color': _COLOR_PRIMARY, 'fontSize': '24px'}),
                        style=styles['details_spinner_center']
                    ),
                    style={**styles['details_content_inner'], 'height': '100%'}
                )
            ])

            # Verificar limite de resumos ANTES de processar (se não estiver em cache)
            if uid and pid and not (isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'summary' in cache_resumo[str(pid)]):
                try:
                    from gvg_limits import ensure_capacity, LimitExceeded  # type: ignore
                    ensure_capacity(uid, 'resumos')
                except LimitExceeded:
                    # Limite atingido: retornar mensagem e não processar
                    summary_text = "⚠️ **Limite diário de resumos atingido.**\n\nFaça upgrade do seu plano para gerar mais resumos hoje."
                    try:
                        updated_cache[str(pid)] = {'docs': docs, 'summary': summary_text}
                    except Exception:
                        pass
                    children_out.append([
                        html.Div(
                            dcc.Markdown(summary_text, style={'fontSize': '12px', 'lineHeight': '1.6'}),
                            style=styles['details_content_inner']
                        )
                    ])
                    # Notificação de limite atingido (CRÍTICO)
                    try:
                        notif = add_note(NOTIF_ERROR, "Limite diário de resumos atingido. Faça upgrade do plano.")
                        updated_notifs.append(notif)
                    except Exception:
                        pass
                    continue
                except Exception as e:
                    dbg('LIMIT', f"erro ao verificar limite de resumos: {e}")

            # Iniciar tracking somente para geração real (sem cache) e só gravar se sucesso
            summary_event_started = False
            try:
                if uid and pid and not (isinstance(cache_resumo, dict) and str(pid) in cache_resumo and isinstance(cache_resumo[str(pid)], dict) and 'summary' in cache_resumo[str(pid)]):
                    from gvg_usage import usage_event_start  # type: ignore
                    usage_event_start(uid, 'summary_success', ref_type='sumário', ref_id=str(pid))
                    summary_event_started = True
            except Exception:
                summary_event_started = False

            if DOCUMENTS_AVAILABLE:
                combined = []
                try:
                    for idx_doc, doc in enumerate(docs or []):
                        nome = str(doc.get('nome') or doc.get('titulo') or f'Documento {idx_doc+1}')
                        url = str(doc.get('url') or doc.get('uri') or '')
                        if not url:
                            continue
                        # Numerador do documento no lote
                        try:
                            if isinstance(pncp_data, dict):
                                pncp_data['doc_seq'] = idx_doc + 1
                        except Exception:
                            pass
                        if summarize_document:
                            if SQL_DEBUG:
                                short = (url[:80] + '...') if len(url) > 80 else url
                                dbg('RESUMO', f"Gerando resumo do doc {idx_doc+1}/{len(docs)}: '{nome}' url='{short}'")
                            piece = summarize_document(url, max_tokens=500, document_name=nome, pncp_data=pncp_data)
                        elif process_pncp_document:
                            if SQL_DEBUG:
                                short = (url[:80] + '...') if len(url) > 80 else url
                                dbg('RESUMO', f"Gerando resumo (fallback) do doc {idx_doc+1}/{len(docs)}: '{nome}' url='{short}'")
                            piece = process_pncp_document(url, max_tokens=500, document_name=nome, pncp_data=pncp_data)
                        else:
                            piece = 'Pipeline de documentos não está disponível neste ambiente.'
                        if isinstance(piece, str) and piece.strip():
                            combined.append(f"## {nome}\n\n{piece}\n")
                    summary_text = "\n\n---\n\n".join(combined) if combined else None
                except Exception as e:
                    summary_text = f"Erro ao gerar resumo: {e}"
            else:
                summary_text = 'Pipeline de documentos não está disponível neste ambiente.'

            if SQL_DEBUG and summary_text is not None:
                sz = len(summary_text) if isinstance(summary_text, str) else 'N/A'
                dbg('RESUMO', f"Resumo GERADO (chars={sz})")

            # Guardar fallback só para exibição (não cachear/persistir)
            is_good = False
            if isinstance(summary_text, str) and summary_text.strip() and not summary_text.startswith('Erro') and summary_text != 'Pipeline de documentos não está disponível neste ambiente.':
                is_good = True
            display_text = summary_text if is_good else 'Não foi possível gerar o resumo.'

            try:
                if is_good:
                    updated_cache[str(pid)] = {'docs': docs, 'summary': summary_text}
            except Exception:
                pass

            # Persistir no BD por usuário (best-effort)
            if uid and is_good:
                try:
                    upsert_user_resumo(uid, pid, summary_text)
                except Exception:
                    pass
            # Finalizar ou descartar evento summary_success conforme resultado
            try:
                if summary_event_started and uid and pid:
                    extra = {}
                    ok = bool(isinstance(summary_text, str) and summary_text.strip())
                    if ok:
                        extra['chars'] = len(summary_text)
                        extra['status'] = 'success'
                        from gvg_usage import usage_event_finish  # type: ignore
                        usage_event_finish(extra)
                    else:
                        extra['status'] = 'empty'
                        from gvg_usage import usage_event_discard  # type: ignore
                        usage_event_discard()
            except Exception:
                pass
            
            # Notificações de resultado do resumo
            updated_notifs = list(notifications or [])
            try:
                if is_good:
                    # Sucesso
                    notif = add_note(NOTIF_SUCCESS, "Resumo gerado com sucesso!")
                    updated_notifs.append(notif)
                elif isinstance(summary_text, str) and summary_text.startswith('Erro'):
                    # Erro ao gerar
                    notif = add_note(NOTIF_ERROR, "Erro ao gerar resumo. Tente novamente.")
                    updated_notifs.append(notif)
            except Exception:
                pass
            
            # Substitui o spinner pelo conteúdo final (resumo)
            children_out[-1] = [html.Div(dcc.Markdown(children=display_text, className='markdown-summary'), style=styles['details_content_inner'])]
        else:
            children_out.append([])
    return children_out, style_out, btn_styles, updated_cache, updated_notifs

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
            # Permitir cache somente se for bom (nem erro, nem fallback)
            def _is_good_summary(text: str | None) -> bool:
                if not isinstance(text, str) or not text.strip():
                    return False
                t = text.strip()
                if t.startswith('Erro'):
                    return False
                if t == 'Não foi possível gerar o resumo.':
                    return False
                if 'Limite diário de resumos atingido' in t:
                    return False
                return True
            if _is_good_summary(cached):
                children_out.append([html.Div(dcc.Markdown(children=cached, className='markdown-summary'), style=styles['details_content_inner'])])
                btn_styles.append(styles['btn_pill_inverted'])
            else:
                spinner = html.Div(
                    html.Div(
                        html.I(className="fas fa-spinner fa-spin", style={'color': _COLOR_PRIMARY, 'fontSize': '24px'}),
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
    # Ignorar criação inicial dos componentes (n_clicks None/0)
    try:
        clicks = int(ctx.triggered[0].get('value') or 0)
    except Exception:
        clicks = 0
    if clicks <= 0:
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
        # Usar o estilo canônico centralizado (mantém borda/cor/radius padronizados)
        base = dict(styles['panel_wrapper'])
        if str(pid) in (active_map or {}):
            base['display'] = 'block'
            # Não alterar a borda; já é definida pelo styles['panel_wrapper']
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
    State('store-active-session', 'data'),
    State('store-result-sessions', 'data'),
    prevent_initial_call=True,
)
def toggle_results_visibility(meta, results, categories, active, sessions):
    base = styles['result_card'].copy()
    hidden = {**base, 'display': 'none'}
    show = base
    # Detecta tipo de sessão ativa
    sess_type = None
    try:
        sess_type = (sessions or {}).get(active, {}).get('type')
    except Exception:
        sess_type = None
    status_style = show if meta else hidden
    cats_style = show if categories else hidden
    show_results = bool(results)
    export_style = show if show_results else hidden
    table_style = show if show_results else hidden
    details_style = show if show_results else hidden
    # Em abas PNCP, exibir somente o card de detalhe
    if sess_type == 'pncp':
        status_style = hidden
        cats_style = hidden
        export_style = hidden
        table_style = hidden
        details_style = show if show_results else hidden
    # Em abas HISTÓRICO, esconder categorias; demais cards seguem como na consulta
    if sess_type == 'history':
        cats_style = hidden
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
    # Limitar a 20 entradas
    if len(items) > 20:
        items = items[:20]
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
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'history-delete', 'index': ALL}, 'n_clicks'),
    State('store-history', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def delete_history_item(n_clicks_list, history, notifications):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    
    updated_notifs = list(notifications or [])
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
    
    # Notificação de sucesso
    notif = add_note(NOTIF_INFO, "Item removido do histórico.")
    updated_notifs.append(notif)
    
    return items, updated_notifs


# Rever item do histórico: abre aba HISTÓRICO com resultados salvos
@app.callback(
    Output('store-session-event', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'history-replay', 'index': ALL}, 'n_clicks'),
    State('store-history', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def replay_from_history(n_clicks_list, history, notifications):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    
    updated_notifs = list(notifications or [])
    # Qual índice foi clicado
    idx = None
    for i, n in enumerate(n_clicks_list):
        if n:
            idx = i; break
    if idx is None:
        raise PreventUpdate
    items = list(history or [])
    if idx < 0 or idx >= len(items):
        raise PreventUpdate
    prompt_text = (items[idx] or '').strip()
    if not prompt_text:
        raise PreventUpdate
    # Buscar resultados persistidos e montar evento de sessão
    try:
        rows = fetch_user_results_for_prompt_text(prompt_text, limit=500)
    except Exception:
        rows = []
    
    # Notificação conforme resultado
    if rows:
        notif = add_note(NOTIF_INFO, f"Consulta reaberta: {len(rows)} resultado(s) carregado(s).")
        updated_notifs.append(notif)
    else:
        notif = add_note(NOTIF_WARNING, "Nenhum resultado encontrado para esta consulta.")
        updated_notifs.append(notif)
    
    # Meta mínima para cards
    meta = {'order': 1, 'count': len(rows), 'source': 'history'}
    session_event = {
        'type': 'history',
        'status': 'completed',
        'title': prompt_text,
        'signature': f"history:{prompt_text[:100]}",
        'payload': {
            'results': rows,
            'categories': [],
            'meta': meta
        }
    }
    return session_event, updated_notifs


# Rever item de boletim: abre aba BOLETIM com resultados do último run
@app.callback(
    Output('store-session-event', 'data', allow_duplicate=True),
    Output('store-search-filters', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'boletim-replay', 'id': ALL}, 'n_clicks'),
    State('store-boletins', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def replay_from_boletim(n_clicks_list, boletins, notifications):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    # Verifica qual botão foi clicado e obtém o boletim_id
    try:
        trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
        comp = json.loads(trig_id)
        if comp.get('type') != 'boletim-replay':
            raise PreventUpdate
        boletim_id = comp.get('id')
    except Exception:
        raise PreventUpdate
    # Guarda: ignorar disparos de montagem/atualização de layout (n_clicks == 0)
    try:
        trig_val = ctx.triggered[0].get('value', None)
        # Alguns ambientes retornam None na criação; tratar como 0
        clicks = int(trig_val) if trig_val is not None else 0
        if clicks <= 0:
            raise PreventUpdate
    except Exception:
        raise PreventUpdate
    if not boletim_id:
        raise PreventUpdate
    try:
        dbg('BOLETIM', f"[replay_from_boletim] trigger id={boletim_id}")
    except Exception:
        pass

    # Buscar query_text/config do boletim e último run_token
    title = ''
    run_token = None
    cfg = {}
    filters_cfg = None
    try:
        # Título/config da aba
        row = None
        try:
            row = db_fetch_all(
                "SELECT query_text, config_snapshot, filters FROM user_schedule WHERE id = %s",
                (int(boletim_id),), as_dict=False, ctx="GSB.replay_from_boletim:load_schedule_with_filters"
            )
        except Exception:
            row = db_fetch_all(
                "SELECT query_text, config_snapshot FROM user_schedule WHERE id = %s",
                (int(boletim_id),), as_dict=False, ctx="GSB.replay_from_boletim:load_schedule"
            )
        row = (row or [None])[0]
        if row:
            title = (row[0] or '').strip()
            try:
                cfg = row[1] or {}
                if isinstance(cfg, str):
                    cfg = json.loads(cfg)
            except Exception:
                cfg = {}
            try:
                if len(row) > 2:
                    filters_cfg = row[2] or {}
                    if isinstance(filters_cfg, str):
                        filters_cfg = json.loads(filters_cfg)
            except Exception:
                filters_cfg = None
        # Último run_token
        rt = db_fetch_all(
            """
            SELECT run_token
            FROM user_boletim
            WHERE boletim_id = %s
            GROUP BY run_token
            ORDER BY MAX(run_at) DESC
            LIMIT 1
            """,
            (int(boletim_id),), as_dict=False, ctx="GSB.replay_from_boletim:last_run_token"
        )
        if rt:
            run_token = rt[0][0]
        if not run_token:
            try:
                dbg('BOLETIM', f"[replay_from_boletim] boletim_id={boletim_id} sem run_token")
            except Exception:
                pass
            # Notificação de erro quando não há execuções (retornar dash.no_update em vez de PreventUpdate)
            updated_notifs = list(notifications or [])
            notif = add_note(NOTIF_WARNING, "Este boletim ainda não foi executado.")
            updated_notifs.append(notif)
            return dash.no_update, dash.no_update, updated_notifs
        # Carregar resultados deste run com join na contratacao
        cols = get_contratacao_core_columns('c')
        sql = (
            "SELECT ub.numero_controle_pncp, ub.similarity, ub.payload, "
            + ", ".join(cols) +
            " FROM user_boletim ub LEFT JOIN contratacao c ON c.numero_controle_pncp = ub.numero_controle_pncp"
            " WHERE ub.boletim_id = %s AND ub.run_token = %s"
            " ORDER BY COALESCE(ub.similarity,0) DESC, ub.numero_controle_pncp"
        )
        rows = db_fetch_all(sql, (int(boletim_id), run_token), as_dict=False, ctx="GSB.replay_from_boletim:load_results") or []
        c_start = 3  # após numero_controle_pncp, similarity, payload
        # Para nomes, reexecutamos a lista de cols importada
        desc = ['numero_controle_pncp', 'similarity', 'payload'] + cols
        # Mapeamento das colunas de contratacao
        results = []
        for idx, row in enumerate(rows):
            pncp = row[0]
            sim = float(row[1] or 0.0)
            payload_json = row[2]
            details = {}
            # Se há colunas da contratacao, projetar
            try:
                if len(row) > c_start:
                    colnames = desc[c_start:]
                    rec = dict(zip(colnames, row[c_start:]))
                    norm = normalize_contratacao_row(rec)
                    details = project_result_for_output(norm)
                else:
                    details = {}
            except Exception:
                details = {}
            # Fallback via payload quando dados do join faltarem
            try:
                if isinstance(payload_json, (str, bytes)):
                    import json as _json
                    try:
                        payload_json = _json.loads(payload_json)
                    except Exception:
                        payload_json = {}
                if isinstance(payload_json, dict):
                    # Preencher only-if-missing para não sobrescrever BD
                    details.setdefault('unidade_orgao_uf_sigla', payload_json.get('uf'))
                    details.setdefault('orgaoentidade_razaosocial', payload_json.get('orgao'))
                    details.setdefault('unidadeorgao_nomeunidade', payload_json.get('unidade'))
                    details.setdefault('unidadeorgao_municipionome', payload_json.get('municipio'))
                    details.setdefault('descricaocompleta', payload_json.get('objeto'))
                    details.setdefault('modalidade_nome', payload_json.get('modalidade'))
                    details.setdefault('modo_disputa_nome', payload_json.get('modo_disputa'))
                    # Datas
                    enc = payload_json.get('data_encerramento_proposta')
                    if enc and not details.get('dataencerramentoproposta') and not details.get('dataEncerramentoProposta'):
                        try:
                            # padronizar para YYYY-MM-DD
                            from datetime import datetime as _d
                            if 'T' in enc:
                                dt = _d.fromisoformat(enc)
                                details['dataencerramentoproposta'] = dt.strftime('%Y-%m-%d')
                            else:
                                details['dataencerramentoproposta'] = str(enc)[:10]
                        except Exception:
                            details['dataencerramentoproposta'] = str(enc)[:10]
                    # Valor estimado
                    val = payload_json.get('valor')
                    if val is not None and not details.get('valortotalestimado'):
                        try:
                            details['valortotalestimado'] = float(val)
                        except Exception:
                            details['valortotalestimado'] = val
            except Exception:
                pass
            # Garantir aliases mínimos e id
            try:
                _augment_aliases(details)
            except Exception:
                pass
            pid = details.get('numero_controle_pncp') or details.get('numerocontrolepncp') or pncp
            results.append({
                'id': pid,
                'numero_controle': pid,
                'similarity': sim,
                'rank': idx + 1,
                'details': details,
            })
    except Exception as e:
        # Falha geral ao carregar; não cria evento
        try:
            dbg('BOLETIM', f"[replay_from_boletim] erro: {e}")
        except Exception:
            pass
        raise PreventUpdate

    # Meta enriquecida a partir do config_snapshot para unificar com card de busca
    meta = {
        'order': (cfg.get('sort_mode') if isinstance(cfg, dict) else 1) or 1,
        'count': len(results),
        'source': 'boletim',
        'run_token': run_token,
        'search': (cfg.get('search_type') if isinstance(cfg, dict) else None),
        'approach': (cfg.get('search_approach') if isinstance(cfg, dict) else None),
        'relevance': (cfg.get('relevance_level') if isinstance(cfg, dict) else None),
        'max_results': (cfg.get('max_results') if isinstance(cfg, dict) else None),
        'top_categories': (cfg.get('top_categories_count') if isinstance(cfg, dict) else None),
        'filter_expired': bool((cfg.get('filter_expired') if isinstance(cfg, dict) else False)),
    }
    session_event = {
        'type': 'boletim',
        'status': 'completed',
        'title': title or 'Boletim',
        'signature': f"boletim:{boletim_id}:{str(run_token)[:32]}",
        'payload': {
            'results': results,
            'categories': [],
            'meta': meta,
        }
    }
    try:
        dbg('BOLETIM', f"[replay_from_boletim] emitindo sessão com {len(results)} resultados run_token={run_token}")
    except Exception:
        pass
    
    # Notificação de resultado
    updated_notifs = list(notifications or [])
    if results:
        notif = add_note(NOTIF_INFO, f"Boletim reaberto: {len(results)} resultado(s) carregado(s).")
        updated_notifs.append(notif)
    else:
        notif = add_note(NOTIF_WARNING, "Nenhum resultado encontrado para este boletim.")
        updated_notifs.append(notif)
    
    return session_event, (filters_cfg if filters_cfg else dash.no_update), updated_notifs


# Aplicar item do histórico na UI (configs + filtros), sem executar busca
@app.callback(
    Output('search-type', 'value'),
    Output('search-approach', 'value'),
    Output('relevance-level', 'value'),
    Output('sort-mode', 'value'),
    Output('max-results', 'value'),
    Output('top-categories', 'value'),
    Output('toggles', 'value'),
    Output('flt-pncp', 'value'),
    Output('flt-orgao', 'value'),
    Output('flt-cnpj', 'value'),
    Output('flt-uf', 'value'),
    Output('flt-municipio', 'value'),
    Output('flt-modalidade-id', 'value'),
    Output('flt-modo-id', 'value'),
    Output('flt-date-field', 'value'),
    Output('flt-date-start', 'value'),
    Output('flt-date-end', 'value', allow_duplicate=True),
    Input({'type': 'history-item', 'index': ALL}, 'n_clicks'),
    State('store-history', 'data'),
    prevent_initial_call=True,
)
def apply_history_to_ui(n_clicks_list, history):
    # Sem clique efetivo? Não atualiza nada.
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    # Índice clicado
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
    q_text = (items[idx] or '').strip()
    if not q_text:
        raise PreventUpdate

    # Buscar registro rico deste prompt
    rec = {}
    try:
        from gvg_user import fetch_prompts_with_config as _fetch_prompts_with_config
        rich = _fetch_prompts_with_config(limit=max(50, len(items))) or []
        by_text = { (r.get('text') or '').strip(): r for r in rich }
        rec = by_text.get(q_text) or {}
    except Exception:
        rec = {}

    # Extrair configurações
    st = rec.get('search_type')
    sa = rec.get('search_approach')
    rl = rec.get('relevance_level')
    sm = rec.get('sort_mode')
    mr = rec.get('max_results')
    tc = rec.get('top_categories_count')
    fe = rec.get('filter_expired')  # bool ou None

    # Extrair filtros (jsonb pode vir como str)
    f = rec.get('filters') or {}
    if isinstance(f, str):
        try:
            f = json.loads(f)
        except Exception:
            f = {}

    def _fmt_ddmmyyyy(val):
        if not val:
            return ''
        s = str(val).strip()
        # já em dd/mm/aaaa
        import re as _re
        if _re.match(r'^\d{2}/\d{2}/\d{4}$', s):
            return s
        # ISO yyyy-mm-dd
        if _re.match(r'^\d{4}-\d{2}-\d{2}$', s):
            try:
                from datetime import datetime as _d
                dt = _d.strptime(s, '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except Exception:
                return ''
        return ''

    # Campos de filtros com limpeza quando ausentes
    pncp = (f.get('pncp') or '').strip() if isinstance(f.get('pncp'), str) else (f.get('pncp') or '')
    orgao = (f.get('orgao') or '').strip() if isinstance(f.get('orgao'), str) else (f.get('orgao') or '')
    cnpj = (f.get('cnpj') or '').strip() if isinstance(f.get('cnpj'), str) else (f.get('cnpj') or '')
    uf_val = f.get('uf')
    if isinstance(uf_val, list):
        uf_out = [str(x).strip() for x in uf_val if str(x or '').strip()]
    elif uf_val is None or uf_val == '':
        uf_out = []
    else:
        # valor único -> lista com 1
        uf_out = [str(uf_val).strip()] if str(uf_val).strip() else []
    municipio = (f.get('municipio') or '').strip() if isinstance(f.get('municipio'), str) else (f.get('municipio') or '')
    mod_id = f.get('modalidade_id')
    if isinstance(mod_id, list):
        mod_out = [str(x).strip() for x in mod_id if str(x or '').strip()]
    elif mod_id is None or mod_id == '':
        mod_out = []
    else:
        mod_out = [str(mod_id).strip()] if str(mod_id).strip() else []
    modo_id = f.get('modo_id')
    if isinstance(modo_id, list):
        modo_out = [str(x).strip() for x in modo_id if str(x or '').strip()]
    elif modo_id is None or modo_id == '':
        modo_out = []
    else:
        modo_out = [str(modo_id).strip()] if str(modo_id).strip() else []
    date_field = (f.get('date_field') or 'encerramento')
    date_start = _fmt_ddmmyyyy(f.get('date_start'))
    date_end = _fmt_ddmmyyyy(f.get('date_end'))

    # Preparar saídas; quando config ausente, mantém valor atual (dash.no_update)
    toggles_val = (['filter_expired'] if (fe is True) else ([] if fe is False else dash.no_update))

    return (
        (st if st is not None else dash.no_update),
        (sa if sa is not None else dash.no_update),
        (rl if rl is not None else dash.no_update),
        (sm if sm is not None else dash.no_update),
        (mr if mr is not None else dash.no_update),
        (tc if tc is not None else dash.no_update),
        toggles_val,
        pncp,
        orgao,
        cnpj,
        uf_out,
        municipio,
        mod_out,
        modo_out,
        date_field,
        date_start,
        date_end,
    )


# ==========================
# Favoritos (UI e callbacks)
# ==========================
# Ordenação ascendente por data de encerramento (expirados primeiro; sem data por último)
def _sort_favorites_list(favs: list) -> list:
    try:
        from datetime import date as _date
        def _key(it: dict):
            dt = _parse_date_generic((it or {}).get('data_encerramento_proposta'))
            return (dt is None, dt or _date.max)
        return sorted(list(favs or []), key=_key)
    except Exception:
        return list(favs or [])
@app.callback(
    Output('store-favorites', 'data'),
    Input('store-favorites', 'data'),
    prevent_initial_call=False,
)
def init_favorites(favs):
    # Inicializa a Store de favoritos na primeira renderização (mesmo padrão do histórico)
    if favs:
        return _sort_favorites_list(favs)
    try:
        data = fetch_bookmarks(limit=200)
        return _sort_favorites_list(data)
    except Exception:
        return []

@app.callback(
    Output('store-planos-data', 'data'),
    Input('store-auth', 'data'),
    prevent_initial_call=False,
)
def load_planos_data_on_init(auth_data):
    """Carrega dados de planos/limites na inicialização (junto com usuário)."""
    user = (auth_data or {}).get('user') or {}
    uid = user.get('uid') or ''
    
    try:
        # Buscar planos do sistema
        plans = get_system_plans()
    except Exception:
        plans = []
    
    # Fallback se banco falhar
    fallback_plans = [
        {'code': 'FREE', 'name': 'Free', 'desc': 'Uso básico para avaliação', 'price_cents': 0, 'limit_consultas_per_day': 5, 'limit_resumos_per_day': 1, 'limit_boletim_per_day': 1, 'limit_favoritos_capacity': 10},
        {'code': 'PLUS', 'name': 'Plus', 'desc': 'Uso individual intensivo', 'price_cents': 4900, 'limit_consultas_per_day': 30, 'limit_resumos_per_day': 40, 'limit_boletim_per_day': 4, 'limit_favoritos_capacity': 200},
        {'code': 'PRO', 'name': 'Professional', 'desc': 'Equipes menores', 'price_cents': 19900, 'limit_consultas_per_day': 100, 'limit_resumos_per_day': 400, 'limit_boletim_per_day': 10, 'limit_favoritos_capacity': 2000},
        {'code': 'CORP', 'name': 'Corporation', 'desc': 'Uso corporativo/alto volume', 'price_cents': 99900, 'limit_consultas_per_day': 1000, 'limit_resumos_per_day': 4000, 'limit_boletim_per_day': 100, 'limit_favoritos_capacity': 20000},
    ]
    if not plans:
        plans = fallback_plans
    
    # Buscar plano e uso atual do usuário
    try:
        settings = get_user_settings(uid)
        current_code = (settings.get('plan_code') or 'FREE').upper()
    except Exception:
        current_code = 'FREE'
    
    # Buscar consumo atual
    usage = None
    if uid:
        try:
            from gvg_limits import get_usage_status
            usage = get_usage_status(uid)
        except Exception:
            pass
    
    return {
        'plans': plans,
        'current_code': current_code,
        'usage': usage,
        'uid': uid
    }


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
                dbg('FAV', f"load_favorites_on_results: carregados={len(favs)}")
        except Exception:
            pass
        return _sort_favorites_list(favs)
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
    return [
        html.Div([
            html.I(className='fas fa-bookmark', style=styles['section_icon']),
            html.Div('Favoritos', style=styles['card_title'])
        ], style=styles['section_header_left']),
        html.I(className=f"fas {icon}")
    ]


@app.callback(
    Output('favorites-list', 'children'),
    Input('store-favorites', 'data'),
    Input('toggles', 'value')
)
def render_favorites_list(favs, toggles):
    hide_expired = 'filter_expired' in (toggles or [])
    items = []
    visible_count = 0
    for i, f in enumerate(favs or []):
        pncp = f.get('numero_controle_pncp') or 'N/A'
        rotulo = (f.get('rotulo') or '') if isinstance(f, dict) else ''
        if not rotulo:
            # fallback: objeto_compra truncado
            raw_obj = f.get('objeto_compra') or ''
            if isinstance(raw_obj, str):
                rotulo = (raw_obj[:30] + ('…' if len(raw_obj) > 30 else '')) if raw_obj else ''
        if isinstance(rotulo, str) and len(rotulo) > 50:
            rotulo = rotulo[:50] + '…'
        orgao = f.get('orgao_entidade_razao_social') or ''
        mun = f.get('unidade_orgao_municipio_nome') or ''
        uf = f.get('unidade_orgao_uf_sigla') or ''
        local = f"{mun}/{uf}".strip('/') if (mun or uf) else ''
        raw_enc = f.get('data_encerramento_proposta')
        enc_txt = _format_br_date(raw_enc)
        _enc_status, enc_color = _enc_status_and_color(raw_enc)
        body_color = {'color': '#808080'} if _enc_status == 'expired' else {}
        status_text = _enc_status_text(_enc_status, raw_enc)
        tag = html.Span(status_text, style={**styles['date_status_tag'], 'backgroundColor': enc_color}) if status_text else None
        date_row = html.Div([
            html.Span(enc_txt, style={'color': enc_color, 'fontWeight': 'bold'}),
            tag
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '4px'})
        body = html.Div([
            html.Div(rotulo or (orgao[:40] if isinstance(orgao, str) else ''), style=styles.get('fav_label')),
            html.Div(local, style=styles.get('fav_local')),
            html.Div(orgao, style=styles.get('fav_orgao')),
            date_row
        ], style={'textAlign': 'left', 'display': 'flex', 'flexDirection': 'column', **body_color})
        btn_style = {**styles['fav_item_button'], 'whiteSpace': 'normal', 'textAlign': 'left', 'width': 'auto', 'flex': '1 1 auto'}
        if _enc_status == 'expired':
            btn_style.update({'border': '2px solid #CFCFCF', 'color': '#808080'})
        else:
            btn_style.update({'border': f'2px solid {enc_color}'})
        row_style = dict(styles['fav_item_row'])
        if hide_expired and _enc_status == 'expired':
            # Apenas oculta visualmente para manter índice consistente
            row_style['display'] = 'none'
        else:
            visible_count += 1
        actions_col = html.Div([
            html.Button(
                html.I(className='fas fa-trash'),
                id={'type': 'favorite-delete', 'index': i},
                className='delete-btn',
                style=styles['fav_delete_btn']
            ),
            # Botão de e-mail (placeholder, sem funcionalidade por enquanto)
            html.Button(
                html.I(className='fas fa-envelope'),
                id={'type': 'favorite-email', 'index': i},
                className='email-btn',
                style=styles['fav_email_btn'],
                n_clicks=0
            )
        ], style=styles['fav_actions_col'])

        row = html.Div([
            html.Button(
                body,
                id={'type': 'favorite-item', 'index': i},
                style=btn_style
            ),
            actions_col
        ], className='fav-item-row', style=row_style)
        items.append(row)
    if not items:
        items = [html.Div('Sem favoritos.', style={'color': '#555'})]
    elif hide_expired and visible_count == 0:
        # Todos ocultos pela filtragem
        items.append(html.Div('Todos os favoritos estão expirados (filtro ativo).', style={'color': '#555', 'fontSize': '12px'}))
    return items


# =============================
# Modal de E-mail: abrir/fechar
# =============================
@app.callback(
    Output('store-email-modal-context', 'data', allow_duplicate=True),
    Input({'type': 'boletim-email', 'id': ALL}, 'n_clicks'),
    Input({'type': 'favorite-email', 'index': ALL}, 'n_clicks'),
    Input({'type': 'history-email', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    State('store-history', 'data'),
    prevent_initial_call=True
)
def open_email_modal(n_clicks_boletim, n_clicks_fav, n_clicks_hist, favs, history_list):
    ctx = callback_context
    if not ctx or not ctx.triggered:
        raise PreventUpdate
    which = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        comp = json.loads(which)
    except Exception:
        raise PreventUpdate
    # Ignorar disparos de montagem (n_clicks None/0)
    trig_val = ctx.triggered[0].get('value', None)
    clicks = int(trig_val) if trig_val is not None else 0
    if clicks <= 0:
        raise PreventUpdate
    if comp.get('type') == 'boletim-email':
        return {'kind': 'boletim', 'id': comp.get('id')}
    if comp.get('type') == 'favorite-email':
        idx = comp.get('index')
        try:
            pncp = str((favs or [])[int(idx)].get('numero_controle_pncp'))
        except Exception:
            pncp = None
        return {'kind': 'favorito', 'pncp': pncp}
    if comp.get('type') == 'history-email':
        idx = comp.get('index')
        prompt = None
        try:
            prompt = (history_list or [])[int(idx)]
        except Exception:
            prompt = None
        if prompt:
            try:
                from gvg_usage import record_usage
                record_usage('history_email_open', meta={'len': len(prompt)})
            except Exception:
                pass
            try:
                dbg('EMAIL', f"open history email prompt='{(prompt or '')[:60]}'")
            except Exception:
                pass
        return {'kind': 'history', 'prompt': prompt}
    raise PreventUpdate


@app.callback(
    Output('email-modal', 'is_open'),
    Output('email-modal-title', 'children'),
    Input('store-email-modal-context', 'data')
)
def reflect_email_modal(ctx_data):
    if not ctx_data:
        return False, 'Enviar por e-mail'
    kind = ctx_data.get('kind')
    if kind == 'boletim':
        return True, 'Enviar boletim por e-mail'
    if kind == 'favorito':
        return True, 'Enviar favorito por e-mail'
    if kind == 'history':
        return True, 'Enviar histórico (consulta) por e-mail'
    return False, 'Enviar por e-mail'


def _parse_recipients(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[\s,;]+", str(raw).strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if '@' in p and '.' in p:
            out.append(p)
    # dedupe
    seen = set()
    uniq = []
    for e in out:
        if e.lower() not in seen:
            uniq.append(e)
            seen.add(e.lower())
    return uniq



@app.callback(
    Output('store-email-send-request', 'data'),
    Output('store-email-modal-context', 'data', allow_duplicate=True),
    Output('email-modal-error', 'children'),
    Output('email-modal-error', 'style'),
    Input('email-modal-send', 'n_clicks'),
    Input('email-modal-input', 'n_submit'),
    State('store-email-modal-context', 'data'),
    State('email-modal-input', 'value'),
    State('email-modal-self', 'value'),
    State('store-auth', 'data'),
    prevent_initial_call=True
)
def queue_email_send(n, n_submit, ctx_data, raw_recipients, self_opts, auth_state):
    if (n or 0) <= 0 and (n_submit or 0) <= 0:
        raise PreventUpdate
    user_email = ((auth_state or {}).get('user') or {}).get('email')
    recips = _parse_recipients(raw_recipients)
    if 'self' in (self_opts or []) and user_email:
        recips.append(user_email)
    # dedupe
    recips = list({e.lower(): e for e in recips}.values()) if recips else []
    if not recips:
        return dash.no_update, dash.no_update, 'Informe ao menos um e-mail válido ou selecione "Enviar para meu e-mail".', {'display': 'block', 'color': '#b00020', 'fontSize': '12px'}
    # Cria um pedido de envio e fecha o modal imediatamente (limpando o contexto)
    req = {'context': ctx_data, 'recipients': recips}
    return req, None, '', {'display': 'none'}


# Processamento em segundo plano: quando há um pedido na Store, envia e limpa
@app.callback(
    Output('store-email-send-request', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('store-email-send-request', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True
)
def process_email_send(req, notifications):
    if not req:
        raise PreventUpdate
    
    updated_notifs = list(notifications or [])
    ctxd = (req or {}).get('context') or {}
    recips = (req or {}).get('recipients') or []
    kind = ctxd.get('kind')
    try:
        if kind == 'boletim':
            bid = ctxd.get('id')
            row = db_fetch_all(
                "SELECT query_text, config_snapshot, schedule_type, schedule_detail FROM user_schedule WHERE id=%s",
                (int(bid),), as_dict=False, ctx="GSB.email:load_schedule")
            row = (row or [["", "", "", {}]])[0]
            qtxt = (row[0] or '').strip()
            cfg = row[1] or {}
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            stype = row[2] or None
            sdetail = row[3] or {}
            last_run_row = db_fetch_all("SELECT MAX(run_at) FROM public.user_boletim WHERE boletim_id=%s", (int(bid),), as_dict=False, ctx="GSB.email:last_run_at")
            last_run = (last_run_row or [[None]])[0][0]
            if not last_run:
                return None
            rows = db_fetch_all(
                """
                SELECT id, numero_controle_pncp, similarity, data_publicacao_pncp, data_encerramento_proposta, payload
                FROM public.user_boletim WHERE boletim_id=%s AND run_at=%s
                """,
                (int(bid), last_run), as_dict=True, ctx="GSB.email:load_results"
            ) or []
            # Montar mapas de itens e documentos
            pncp_ids = [str(r.get('numero_controle_pncp') or '') for r in rows if r.get('numero_controle_pncp')]
            items_map = {}
            docs_map = {}
            for pid in pncp_ids:
                try:
                    itens = fetch_itens_contratacao(pid, limit=200) or []  # limite de segurança
                except Exception:
                    itens = []
                try:
                    docs = fetch_documentos(pid) or []
                except Exception:
                    docs = []
                items_map[pid] = itens
                docs_map[pid] = docs
                try:
                    dbg('EMAIL', f"boletim pncp={pid} itens={len(itens)} docs={len(docs)}")
                except Exception:
                    pass
            try:
                html = render_boletim_email_html(qtxt, rows, cfg, stype, sdetail, items_map=items_map, docs_map=docs_map)
            except Exception:
                html = render_boletim_email_html(qtxt, rows, cfg, stype, sdetail)
            subject = f"Boletim GovGo — {qtxt}"
            try:
                dbg('EMAIL', f"boletim email total_results={len(rows)} pncp_ids={len(pncp_ids)}")
            except Exception:
                pass
        elif kind == 'favorito':
            pncp = (ctxd.get('pncp') or '').strip()
            if not pncp:
                return None
            cols = get_contratacao_core_columns('c')
            rows = db_fetch_all("SELECT " + ",".join(cols) + " FROM contratacao c WHERE c.numero_controle_pncp=%s LIMIT 1", (pncp,), as_dict=True, ctx="GSB.email:load_favorito")
            if not rows:
                return None
            rec = rows[0]
            details = project_result_for_output(normalize_contratacao_row(rec))
            # Buscar itens e documentos
            try:
                fav_itens = fetch_itens_contratacao(pncp, limit=200) or []
            except Exception:
                fav_itens = []
            try:
                fav_docs = fetch_documentos(pncp) or []
            except Exception:
                fav_docs = []
            try:
                dbg('EMAIL', f"favorito pncp={pncp} itens={len(fav_itens)} docs={len(fav_docs)}")
            except Exception:
                pass
            try:
                html = render_favorito_email_html(details, itens=fav_itens, docs=fav_docs)
            except Exception:
                html = render_favorito_email_html(details)
            subject = f"Favorito GovGo — PNCP {pncp}"
        elif kind == 'history':
            prompt_text = (ctxd.get('prompt') or '').strip()
            if not prompt_text:
                return None
            try:
                from gvg_user import fetch_user_results_for_prompt_text
                rows = fetch_user_results_for_prompt_text(prompt_text, limit=500) or []
            except Exception:
                rows = []
            # Montar mapas itens/docs
            pncp_ids = []
            for r in rows:
                try:
                    pid = (r.get('details') or {}).get('numero_controle_pncp')
                    if pid:
                        pncp_ids.append(str(pid))
                except Exception:
                    pass
            items_map = {}
            docs_map = {}
            for pid in pncp_ids:
                try:
                    itens = fetch_itens_contratacao(pid, limit=200) or []
                except Exception:
                    itens = []
                try:
                    docs = fetch_documentos(pid) or []
                except Exception:
                    docs = []
                items_map[pid] = itens
                docs_map[pid] = docs
                try:
                    dbg('EMAIL', f"history pncp={pid} itens={len(itens)} docs={len(docs)}")
                except Exception:
                    pass
            try:
                from gvg_email import render_history_email_html
                html = render_history_email_html(prompt_text, rows, items_map=items_map, docs_map=docs_map)
            except Exception:
                try:
                    html = render_history_email_html(prompt_text, rows)
                except Exception:
                    html = f"<div>Falha ao gerar e-mail de histórico para: {prompt_text}</div>"
            subject = f"Consulta GovGo — {prompt_text[:80]}" if prompt_text else "Consulta GovGo"
            try:
                from gvg_usage import record_usage
                record_usage('history_email', meta={'results': len(rows)})
            except Exception:
                pass
            try:
                dbg('EMAIL', f"history email prompt='{prompt_text[:50]}' results={len(rows)} pncp_ids={len(pncp_ids)}")
            except Exception:
                pass
        else:
            return None

        email_sent_count = 0
        email_failed_count = 0
        for to in recips:
            try:
                send_html_email(to, subject, html)
                email_sent_count += 1
            except Exception:
                email_failed_count += 1
        
        # Notificações de resultado
        if email_sent_count > 0:
            notif = add_note(NOTIF_SUCCESS, f"E-mail enviado com sucesso para {email_sent_count} destinatário(s)!")
            updated_notifs.append(notif)
        if email_failed_count > 0:
            notif = add_note(NOTIF_WARNING, f"Falha ao enviar para {email_failed_count} destinatário(s).")
            updated_notifs.append(notif)
    except Exception as e:
        # Notificação de erro geral
        notif = add_note(NOTIF_ERROR, "Erro ao processar envio de e-mail. Tente novamente.")
        updated_notifs.append(notif)
    # Limpa a fila ao final (fecha ciclo)
    return None, updated_notifs


# Clique em bookmark no card: alterna estado e persiste
@app.callback(
    Output({'type': 'bookmark-btn', 'pncp': ALL}, 'children', allow_duplicate=True),
    Output('store-favorites', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'bookmark-btn', 'pncp': ALL}, 'n_clicks'),
    State('store-results-sorted', 'data'),
    State('store-favorites', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def toggle_bookmark(n_clicks_list, results, favs, notifications):
    # Conjunto de favoritos atual
    fav_set = {str(x.get('numero_controle_pncp')) for x in (favs or [])}

    # Obter a lista de componentes atualmente correspondidos pelo padrão (na ordem do layout)
    ctx = callback_context
    layout_pncp_ids = []
    try:
        # ctx.inputs é um dict com chaves JSON do id -> propriedade
        keys = list((ctx.inputs or {}).keys()) if ctx else []
        import json as _json
        for k in keys:
            try:
                tid = _json.loads(k.split('.')[0])
                if isinstance(tid, dict) and tid.get('type') == 'bookmark-btn':
                    layout_pncp_ids.append(str(tid.get('pncp')))
            except Exception:
                continue
    except Exception:
        layout_pncp_ids = []

    # Mapear PNCPs dos resultados (para localizar índice clicado)
    results_pncp_ids = []
    for r in (results or []):
        d = (r or {}).get('details', {}) or {}
        pid = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or d.get('numero_controle_pncp') or r.get('id') or r.get('numero_controle')
        results_pncp_ids.append(str(pid) if pid is not None else 'N/A')

    # Determine if a click occurred and which index dentre os resultados
    clicked_pid = None
    clicked_idx = None
    if ctx and ctx.triggered:
        try:
            id_str = ctx.triggered[0]['prop_id'].split('.')[0]
            import json as _json
            t = _json.loads(id_str)
            clicked_pid = str(t.get('pncp'))
            # localizar índice correspondente ao pncp nos resultados
            for i, pid in enumerate(results_pncp_ids):
                if str(pid) == clicked_pid:
                    clicked_idx = i
                    break
        except Exception:
            clicked_pid = None
            clicked_idx = None

    # Persist toggle somente em clique real (n_clicks > 0)
    updated_favs = list(favs or [])
    updated_notifs = list(notifications or [])
    # Se foi disparado pela criação dos componentes (n_clicks None/0), não faz nada
    if clicked_pid and clicked_pid != 'N/A' and clicked_idx is not None and (n_clicks_list[clicked_idx] or 0) > 0:
        if clicked_pid in fav_set:
            try:
                remove_bookmark(clicked_pid)
            except Exception:
                pass
            # Otimista local
            updated_favs = [x for x in updated_favs if str(x.get('numero_controle_pncp')) != clicked_pid]
            # Adicionar notificação de remoção
            try:
                notif = add_note(NOTIF_INFO, f"Favorito removido: {clicked_pid}")
                updated_notifs.append(notif)
            except Exception:
                pass
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    dbg('FAV', f"toggle_bookmark: REMOVE {clicked_pid}")
            except Exception:
                pass
        else:
            # Adicionar favorito com geração de rótulo
            fav_item = {'numero_controle_pncp': clicked_pid}
            try:
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
                descricao_full = (
                    d.get('descricaocompleta')
                    or d.get('descricaoCompleta')
                    or d.get('objeto')
                    or ''
                )
                rotulo = None
                try:
                    rotulo = generate_contratacao_label(descricao_full) if descricao_full else None
                except Exception:
                    rotulo = None
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
                    'objeto_compra': (descricao_full[:100] if isinstance(descricao_full, str) else ''),
                    'data_encerramento_proposta': data_en,
                    'rotulo': rotulo,
                })
            except Exception:
                pass
            try:
                add_bookmark(clicked_pid, fav_item.get('rotulo'))
            except Exception:
                try:
                    add_bookmark(clicked_pid)
                except Exception:
                    pass
            # Registrar evento de uso para adição de favorito (compatibilidade histórica)
            try:
                from gvg_usage import record_usage
                user = get_current_user() if 'get_current_user' in globals() else {'uid': ''}
                uid = (user or {}).get('uid') or ''
                if uid:
                    record_usage(uid, 'favorite_add', ref_type='favorito', ref_id=clicked_pid, meta={'rotulo': fav_item.get('rotulo')})
            except Exception:
                pass
            updated_favs = ([fav_item] + [x for x in updated_favs if str(x.get('numero_controle_pncp')) != clicked_pid])
            # Adicionar notificação de sucesso
            try:
                rotulo_text = fav_item.get('rotulo') or clicked_pid
                notif = add_note(NOTIF_SUCCESS, f"Favorito adicionado: {rotulo_text}")
                updated_notifs.append(notif)
            except Exception:
                pass
            try:
                from gvg_search_core import SQL_DEBUG
                if SQL_DEBUG:
                    dbg('FAV', f"toggle_bookmark: ADD {clicked_pid} rotulo={fav_item.get('rotulo')}")
            except Exception:
                pass
        # Sem recarregar do BD aqui: mantemos atualização otimista no UI
    # Ordenar sempre a Store de favoritos após add/remove
    updated_favs = _sort_favorites_list(updated_favs)
    # Ícones imediatos (com base no updated_favs)
    fav_set_after = {str(x.get('numero_controle_pncp')) for x in (updated_favs or [])}
    # Se não há componentes correspondidos no layout no momento, retornar lista vazia
    if not layout_pncp_ids:
        return [], updated_favs, updated_notifs
    children_out = []
    for pid in layout_pncp_ids:
        icon_class = 'fas fa-bookmark' if pid in fav_set_after else 'far fa-bookmark'
        children_out.append(html.I(className=icon_class))

    return children_out, updated_favs, updated_notifs


@app.callback(
    Output({'type': 'bookmark-btn', 'pncp': ALL}, 'children', allow_duplicate=True),
    Input('store-favorites', 'data'),
    State('store-results-sorted', 'data'),
    State({'type': 'bookmark-btn', 'pncp': ALL}, 'n_clicks'),  # usado apenas para obter a contagem/ordem atual
    prevent_initial_call=True,
)
def sync_bookmark_icons(favs, results, current_n_clicks):
    # Conjunto de favoritos atualizado
    fav_set = {str(x.get('numero_controle_pncp')) for x in (favs or [])}

    # Extrair os ids dos componentes atualmente montados no layout (ordem do layout)
    ctx = callback_context
    layout_pncp_ids = []
    try:
        keys = list((ctx.states or {}).keys()) if ctx else []
        import json as _json
        for k in keys:
            if not k.endswith('.n_clicks'):
                continue
            try:
                tid = _json.loads(k.split('.')[0])
                if isinstance(tid, dict) and tid.get('type') == 'bookmark-btn':
                    layout_pncp_ids.append(str(tid.get('pncp')))
            except Exception:
                continue
    except Exception:
        layout_pncp_ids = []

    # Se não há componentes no layout, retornar lista vazia para casar com o spec de saída []
    if not layout_pncp_ids:
        return []

    # Montar ícones conforme favoritos
    children_out = []
    for pid in layout_pncp_ids:
        is_fav = pid in fav_set
        icon_class = 'fas fa-bookmark' if is_fav else 'far fa-bookmark'
        children_out.append(html.I(className=icon_class))

    return children_out


# Clique em um favorito: não altera o campo de consulta (apenas outras ações usam este clique)
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
    # Não preenche mais o campo de consulta
    return dash.no_update


# Remover um favorito via lista
@app.callback(
    Output('store-favorites', 'data', allow_duplicate=True),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input({'type': 'favorite-delete', 'index': ALL}, 'n_clicks'),
    State('store-favorites', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def delete_favorite(n_clicks_list, favs, notifications):
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate
    
    updated_notifs = list(notifications or [])
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
    dbg('FAV', f"delete_favorite fired idx={idx} pid={pid}")
    # Remove no BD (best-effort)
    success = False
    try:
        remove_bookmark(pid)
        success = True
    except Exception:
        pass
    # Remove da Store localmente
    updated = [x for x in (favs or []) if str(x.get('numero_controle_pncp')) != pid]
    updated = _sort_favorites_list(updated)

    # Notificação
    if success:
        notif = add_note(NOTIF_INFO, "Favorito removido com sucesso.")
        updated_notifs.append(notif)
    else:
        notif = add_note(NOTIF_ERROR, "Erro ao remover favorito. Tente novamente.")
        updated_notifs.append(notif)
    
    return updated, updated_notifs


# Exportações
from types import SimpleNamespace

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Resultados_Busca'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.callback(
    Output('download-out', 'data'),
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('export-json', 'n_clicks'),
    Input('export-xlsx', 'n_clicks'),
    Input('export-csv', 'n_clicks'),
    Input('export-pdf', 'n_clicks'),
    Input('export-html', 'n_clicks'),
    State('store-results', 'data'),
    State('store-last-query', 'data'),
    State('store-meta', 'data'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def export_files(n_json, n_xlsx, n_csv, n_pdf, n_html, results, query, meta, notifications):
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
    
    updated_notifs = list(notifications or [])
    export_type = {
        'export-json': 'JSON',
        'export-xlsx': 'Excel',
        'export-csv': 'CSV',
        'export-pdf': 'PDF',
        'export-html': 'HTML'
    }.get(btn_id, 'arquivo')
    
    try:
        path = None
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
                notif = add_note(NOTIF_ERROR, "Erro ao exportar PDF. Biblioteca ausente.")
                updated_notifs.append(notif)
                return dash.no_update, updated_notifs
        elif btn_id == 'export-html':
            path = export_results_html(results, query or '', params, OUTPUT_DIR)
        else:
            raise PreventUpdate
        
        if path and os.path.exists(path):
            # Sucesso na exportação
            notif = add_note(NOTIF_SUCCESS, f"Arquivo {export_type} exportado com sucesso!")
            updated_notifs.append(notif)
            return dcc.send_file(path), updated_notifs
        else:
            # Arquivo não foi criado
            notif = add_note(NOTIF_ERROR, f"Erro ao exportar {export_type}. Tente novamente.")
            updated_notifs.append(notif)
            return dash.no_update, updated_notifs
            
    except Exception as e:
        # Erro genérico na exportação
        notif = add_note(NOTIF_ERROR, f"Erro ao exportar {export_type}. Verifique os dados.")
        updated_notifs.append(notif)
        return dash.no_update, updated_notifs


# =====================================================================================
# CALLBACKS: Notificações Toast
# =====================================================================================

# Renderiza as notificações ativas
@app.callback(
    Output('toast-container', 'children'),
    Input('store-notifications', 'data'),
    prevent_initial_call=False,
)
def render_notifications(notifications):
    """Renderiza lista de notificações Toast ativas."""
    if not notifications:
        return []
    
    toasts = []
    for notif in notifications:
        notif_id = notif.get('id')
        tipo = notif.get('tipo', 'info')
        texto = notif.get('texto', '')
        icon = notif.get('icon', 'fas fa-info-circle')
        color = notif.get('color', '#17a2b8')
        
        toast = html.Div([
            html.Div(
                html.I(className=icon, style={'color': color}),
                style=styles['toast_icon']
            ),
            html.Div(texto, style=styles['toast_text']),
        ], id={'type': 'toast-item', 'id': notif_id}, style={**styles['toast_item'], 'borderColor': color})
        
        toasts.append(toast)
    
    return toasts


# Auto-remove notificações após 3 segundos (triggered por Interval)
@app.callback(
    Output('store-notifications', 'data', allow_duplicate=True),
    Input('notifications-interval', 'n_intervals'),
    State('store-notifications', 'data'),
    prevent_initial_call=True,
)
def auto_remove_notifications(n_intervals, notifications):
    """Remove notificações após 3 segundos (3000ms)."""
    import time
    
    if not notifications:
        raise PreventUpdate
    
    current_time = time.time()
    # Filtra notificações com mais de 3 segundos
    updated_notifs = [
        n for n in notifications
        if (current_time - n.get('timestamp', 0)) < 3.0
    ]
    
    # Se nada mudou, não atualizar
    if len(updated_notifs) == len(notifications):
        raise PreventUpdate
    
    return updated_notifs


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
                        <script>
                        // Auto-scroll tabs bar to the end when a new tab is added
                        (function() {
                            function setupObserverFor(el) {
                                if (!el || el.dataset.gvgTabsObserved) return;
                                el.dataset.gvgTabsObserved = '1';
                                var lastCount = el.children ? el.children.length : 0;
                                try {
                                    var obs = new MutationObserver(function(mutations) {
                                        var count = el.children ? el.children.length : 0;
                                        if (count > lastCount) {
                                            // new tab(s) added -> scroll to end
                                            el.scrollLeft = el.scrollWidth;
                                        }
                                        lastCount = count;
                                    });
                                    obs.observe(el, { childList: true });
                                } catch (e) {
                                    // MutationObserver not available or failed
                                }
                                // Initial scroll to end (useful on first render with many tabs)
                                setTimeout(function(){ try { el.scrollLeft = el.scrollWidth; } catch(_) {} }, 0);
                            }

                            function ensureObserver() {
                                var el = document.getElementById('tabs-bar');
                                if (el) setupObserverFor(el);
                            }

                            if (document.readyState === 'loading') {
                                document.addEventListener('DOMContentLoaded', ensureObserver);
                            } else {
                                ensureObserver();
                            }

                            // Also watch for DOM updates that might replace the tabs container
                            try {
                                var rootObs = new MutationObserver(function() { ensureObserver(); });
                                rootObs.observe(document.body, { childList: true, subtree: true });
                            } catch (e) {
                                // Ignore
                            }
                        })();
                        </script>
                        
        </footer>
    </body>
</html>
'''.replace('%CSS_ALL%', CSS_ALL)


"""WSGI server entrypoint for Gunicorn/Render."""
# Expor no nível de módulo para que `gunicorn GvG_Search_Browser:server` funcione
server = app.server  # WSGI entrypoint para Gunicorn/Render

if __name__ == '__main__':
    # Respeitar porta/host de ambiente (Render/Paas)
    _env = os.environ
    # DEBUG (apenas logs): variável DEBUG controla somente logs/verbosidade no console (já tratada acima)
    # DEV/PROD: variável GVG_BROWSER_DEV controla modo de execução do servidor (dev tools, host, reloader)
    _dev_mode = (_env.get('GVG_BROWSER_DEV', 'false') or 'false').strip().lower() in ('1', 'true', 'yes', 'on')
    if _dev_mode:
        # Desenvolvimento: http://127.0.0.1:8060
        _port_dev = int(_env.get('BROWSER_PORT', '8060'))
        app.run_server(
            debug=True,  # Dash dev tools
            host='127.0.0.1',
            port=_port_dev,
            dev_tools_hot_reload=True,
            dev_tools_props_check=False,
            dev_tools_ui=False,
            dev_tools_hot_reload_interval=0.5,
            use_reloader=False,
        )
    else:
        # Produção: sem dev tools, exposto em todas as interfaces
        _port_prod = int(_env.get('PORT', _env.get('RENDER_PORT', '8060')))
        app.run_server(
            debug=True,
            host='0.0.0.0',
            port=_port_prod,
            dev_tools_hot_reload=False,
            dev_tools_props_check=False,
            dev_tools_ui=False,
            use_reloader=False,
        )
