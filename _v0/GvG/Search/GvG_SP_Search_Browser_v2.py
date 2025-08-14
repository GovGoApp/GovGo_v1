"""
GvG_SP_Search_Browser_v2.py
Versão 2.0 - Interface web com funcionalidades estendidas
- Todas as funcionalidades do v1 preservadas
- Modals para visualização de documentos PNCP
- Geração de palavras-chave com chips visuais
- Sumarização de documentos em interface gráfica
- Cache inteligente para performance
- Botões de ação integrados em cada card de resultado
"""

import dash
from dash import html, dcc, callback, Input, Output, State, ctx, ALL, MATCH, no_update
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd
import json
import os
import sys
import numpy as np
import psycopg2
import time
from rich.console import Console
from openai import OpenAI
from dotenv import load_dotenv


# Importar funções do módulo de pré-processamento
try:
    from gvg_pre_processing import (
        gvg_pre_processing,
        EMBEDDING_MODELS,
        EMBEDDING_MODELS_REVERSE
    )
except ImportError:
    print("ERRO: Não foi possível importar o módulo de pré-processamento.")
    sys.exit(1)

# Importar funções de busca (NOVAS FUNÇÕES ADICIONADAS)
from gvg_search_utils import (
    create_connection, semantic_search, keyword_search, hybrid_search,
    calculate_confidence, format_currency, export_results_to_excel,
    test_connection, get_embedding, parse_numero_controle_pncp,
    fetch_documentos, generate_keywords, summarize_document
)

# Configure Rich console
console = Console()


# Configurações
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

DEFAULT_PREPROC_PARAMS = {
    "remove_special_chars": True,
    "keep_separators": True,
    "remove_accents": False,
    "case": "lower",
    "remove_stopwords": True,
    "lemmatize": True
}

# Inicializa o app Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'],
    suppress_callback_exceptions=True
)
server = app.server

# Estilos customizados (EXPANDIDOS COM NOVOS ESTILOS)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>GovGo Search v2.0</title>
        {%favicon%}
        {%css%}
        <style>
            .search-card { border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 15px; }
            .search-result { padding: 15px; border-left: 4px solid #007bff; margin-bottom: 10px; }
            .similarity-badge { font-size: 0.9em; }
            .description-text { font-size: 0.9em; color: #666; }
            .meta-info { font-size: 0.8em; color: #888; }
            .confidence-indicator { padding: 5px 10px; border-radius: 15px; color: white; }
            .confidence-high { background-color: #28a745; }
            .confidence-medium { background-color: #ffc107; color: #212529; }
            .confidence-low { background-color: #dc3545; }
            
            /* NOVOS ESTILOS PARA AS FUNCIONALIDADES ADICIONADAS */
            .document-card { 
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 8px; 
                padding: 10px; 
                margin-bottom: 10px; 
            }
            .keywords-card { 
                background-color: #e3f2fd; 
                border: 1px solid #bbdefb; 
                border-radius: 8px; 
                padding: 10px; 
                margin-bottom: 10px; 
            }
            .summary-card { 
                background-color: #f1f8e9; 
                border: 1px solid #c8e6c9; 
                border-radius: 8px; 
                padding: 10px; 
                margin-bottom: 10px; 
                max-height: 300px;
                overflow-y: auto;
            }
            .document-link { 
                color: #007bff; 
                text-decoration: none; 
                font-weight: 500;
            }
            .document-link:hover { 
                color: #0056b3; 
                text-decoration: underline; 
            }
            .keyword-chip {
                display: inline-block;
                background: #e0e0e0;
                border-radius: 16px;
                padding: 2px 8px;
                margin: 2px;
                font-size: 0.8rem;
                line-height: 20px;
                white-space: nowrap;
            }
            .action-buttons {
                margin-top: 10px;
                gap: 5px;
            }
            .process-actions {
                border-top: 1px solid #dee2e6;
                padding-top: 10px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout do aplicativo (ESTRUTURA ORIGINAL MANTIDA)
app.layout = dbc.Container([
    # Cabeçalho
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="fas fa-search me-3"),
                    "GovGo Search v2.0"  # Versão atualizada
                ], className="text-primary mb-2"),
            ])
        ])
    ], className="mb-4"),
    
    # Status de Conexão
    dbc.Row([
        dbc.Col([
            html.Div(id="connection-status", className="mb-3")
        ])
    ]),
    
    # Layout: BUSCA ESQUERDA, RESULTADOS DIREITA
    dbc.Row([
        # COLUNA ESQUERDA: Painel de Busca
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Configurações de Busca"),
                dbc.CardBody([
                    # Tipo de Busca
                    dbc.Label("Tipo de Busca:", className="fw-bold"),
                    dcc.Dropdown(
                        id="search-type",
                        options=[
                            {"label": f"{info['name']} - {info['description']}", "value": id}
                            for id, info in SEARCH_TYPES.items()
                        ],
                        value=1,
                        clearable=False,
                        className="mb-3"
                    ),
                    
                    # Campo de Busca
                    dbc.Label("Consulta:", className="fw-bold"),
                    dbc.InputGroup([
                        dbc.Input(
                            id="search-query",
                            placeholder="Digite sua consulta aqui...",
                            type="text"
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-search")],
                            id="search-button",
                            color="primary",
                            n_clicks=0
                        )
                    ], className="mb-3"),
                    
                    # Configurações Avançadas
                    dbc.Button("Configurações Avançadas", id="toggle-advanced", color="outline-secondary", size="sm"),
                    dbc.Collapse([
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checklist(
                                    id="preprocessing-options",
                                    options=[
                                        {"label": "Remover caracteres especiais", "value": "remove_special_chars"},
                                        {"label": "Manter separadores", "value": "keep_separators"},
                                        {"label": "Remover acentos", "value": "remove_accents"},
                                    ],
                                    value=["remove_special_chars", "keep_separators"]
                                )
                            ]),
                            dbc.Col([
                                dbc.Checklist(
                                    id="preprocessing-options-2",
                                    options=[
                                        {"label": "Converter para minúsculo", "value": "lowercase"},
                                        {"label": "Remover stopwords", "value": "remove_stopwords"},
                                        {"label": "Lemmatização", "value": "lemmatize"},
                                    ],
                                    value=["lowercase", "remove_stopwords", "lemmatize"]
                                )
                            ])
                        ])
                    ], id="advanced-settings", is_open=False)
                ])
            ])
        ], md=4),
        
        # COLUNA DIREITA: Resultados
        dbc.Col([
            # Informações da busca
            html.Div(id="search-info", className="mb-3"),
            
            # Resultados
            html.Div(id="search-results"),
            
            # Botões de ação
            html.Div([
                dbc.Button([html.I(className="fas fa-download me-2"), "Exportar Excel"], id="export-button", color="success", disabled=True, className="me-2"),
                dbc.Button([html.I(className="fas fa-redo me-2"), "Nova Busca"], id="clear-button", color="outline-primary")
            ], id="action-buttons", style={"display": "none"}, className="mt-3")
        ], md=7)
    ]),
    
    # NOVOS MODALS PARA AS FUNCIONALIDADES ADICIONADAS
    dbc.Modal([
        dbc.ModalHeader("Documentos do Processo"),
        dbc.ModalBody(id="documents-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="close-documents-modal", color="secondary")
        ])
    ], id="documents-modal", size="lg"),
    
    dbc.Modal([
        dbc.ModalHeader("Palavras-chave Geradas"),
        dbc.ModalBody(id="keywords-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="close-keywords-modal", color="secondary")
        ])
    ], id="keywords-modal", size="md"),
    
    dbc.Modal([
        dbc.ModalHeader("Resumo do Documento"),
        dbc.ModalBody(id="summary-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="close-summary-modal", color="secondary")
        ])
    ], id="summary-modal", size="lg"),
    
    # Stores para dados (EXPANDIDOS)
    dcc.Store(id="search-results-store", data=[]),
    dcc.Store(id="last-query-store", data=""),
    dcc.Store(id="search-type-store", data=1),
    dcc.Store(id="documents-store", data={}),  # NOVO
    dcc.Store(id="keywords-store", data={}),   # NOVO
    dcc.Store(id="summaries-store", data={}),  # NOVO
    
    # Download component
    dcc.Download(id="download-excel"),
    
    # Loading overlay
    dbc.Spinner(
        html.Div(id="loading-output"),
        spinner_style={"width": "3rem", "height": "3rem"},
        fullscreen=True,
        fullscreen_style={"backgroundColor": "rgba(255, 255, 255, 0.8)"},
        show_initially=False
    )
], fluid=True, className="py-4")

# ============================================
# Callbacks ORIGINAIS (mantidos)
# ============================================

# Verificar conexão na inicialização
@callback(
    Output("connection-status", "children"),
    Input("search-type", "value"),  # Trigger inicial
    prevent_initial_call=False
)
def check_connection(search_type):
    """Verifica status da conexão com o banco"""
    try:
        if test_connection():
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                "Conectado ao banco de dados Supabase com sucesso!"
            ], color="success", className="mb-0")
        else:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "Erro: Não foi possível conectar ao banco de dados."
            ], color="danger", className="mb-0")
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-times-circle me-2"),
            f"Erro de conexão: {str(e)}"
        ], color="danger", className="mb-0")

# Toggle configurações avançadas
@callback(
    Output("advanced-settings", "is_open"),
    Input("toggle-advanced", "n_clicks"),
    State("advanced-settings", "is_open"),
    prevent_initial_call=True
)
def toggle_advanced_settings(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# Busca principal (ATUALIZADA COM AS NOVAS FUNCIONALIDADES)
@callback(
    [Output("search-results", "children"),
     Output("search-info", "children"),
     Output("search-results-store", "data"),
     Output("last-query-store", "data"),
     Output("search-type-store", "data"),
     Output("action-buttons", "style"),
     Output("export-button", "disabled"),
     Output("loading-output", "children")],
    [Input("search-button", "n_clicks"),
     Input("search-query", "n_submit")],
    [State("search-query", "value"),
     State("search-type", "value"),
     State("preprocessing-options", "value"),
     State("preprocessing-options-2", "value")],
    prevent_initial_call=True
)
def perform_search(n_clicks, n_submit, query, search_type, prep_opts1, prep_opts2):
    """Executa a busca"""
    if not (n_clicks or n_submit) or not query:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    try:
        # Configurar pré-processamento
        prep_options = {
            "remove_special_chars": "remove_special_chars" in (prep_opts1 or []),
            "keep_separators": "keep_separators" in (prep_opts1 or []),
            "remove_accents": "remove_accents" in (prep_opts1 or []),
            "case": "lower" if "lowercase" in (prep_opts2 or []) else "original",
            "remove_stopwords": "remove_stopwords" in (prep_opts2 or []),
            "lemmatize": "lemmatize" in (prep_opts2 or [])
        }
        
        # Pré-processar consulta
        processed_query = gvg_pre_processing(
            query,
            remove_special_chars=prep_options["remove_special_chars"],
            keep_separators=prep_options["keep_separators"],
            remove_accents=prep_options["remove_accents"],
            case=prep_options["case"],
            remove_stopwords=prep_options["remove_stopwords"],
            lemmatize=prep_options["lemmatize"]
        )
        
        # Executar busca
        start_time = time.time()
        
        if search_type == 1:
            results, confidence = semantic_search(processed_query, limit=10)
        elif search_type == 2:
            results, confidence = keyword_search(processed_query, limit=10)
        elif search_type == 3:
            results, confidence = hybrid_search(processed_query, limit=10)
        else:
            results, confidence = semantic_search(processed_query, limit=10)
        
        search_time = time.time() - start_time
        
        # Gerar componentes de resultado
        if not results:
            search_results = dbc.Alert([
                html.I(className="fas fa-search me-2"),
                "Nenhum resultado encontrado para esta consulta."
            ], color="warning")
            
            search_info = dbc.Alert([
                html.H6(f"Consulta: \"{query}\"", className="mb-1"),
                html.Small(f"Consulta processada: \"{processed_query}\"", className="text-muted d-block"),
                html.Small(f"Tipo de busca: {SEARCH_TYPES[search_type]['name']}", className="text-muted d-block"),
                html.Small(f"Tempo: {search_time:.3f}s", className="text-muted")
            ], color="info", className="mb-0")
            
            return search_results, search_info, [], query, search_type, {"display": "none"}, True, ""
        
        # Criar cards de resultados (ATUALIZADO COM NOVOS BOTÕES)
        result_cards = create_result_cards_v2(results, query, search_type)
        
        # Informações da busca
        confidence_class = "confidence-high" if confidence > 70 else "confidence-medium" if confidence > 40 else "confidence-low"
        
        search_info = dbc.Alert([
            dbc.Row([
                dbc.Col([
                    html.H6(f"Consulta: \"{query}\"", className="mb-1"),
                    html.Small(f"Consulta processada: \"{processed_query}\"", className="text-muted d-block"),
                    html.Small(f"Tipo de busca: {SEARCH_TYPES[search_type]['name']}", className="text-muted d-block"),
                ], md=8),
                dbc.Col([
                    html.Div([
                        html.Span(f"Confiança: {confidence:.1f}%", 
                                className=f"confidence-indicator {confidence_class}"),
                        html.Small(f"Tempo: {search_time:.3f}s", className="text-muted d-block mt-1")
                    ], className="text-end")
                ], md=4)
            ])
        ], color="info", className="mb-0")
        
        return result_cards, search_info, results, query, search_type, {"display": "block"}, False, ""
        
    except Exception as e:
        error_msg = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Erro na busca: {str(e)}"
        ], color="danger")
        
        return error_msg, "", [], "", search_type, {"display": "none"}, True, ""

# ============================================
# NOVOS CALLBACKS PARA AS FUNCIONALIDADES ADICIONADAS
# ============================================

# Callback para buscar documentos
@callback(
    [Output("documents-modal", "is_open"),
     Output("documents-modal-body", "children"),
     Output("documents-store", "data")],
    [Input({"type": "documents-button", "index": ALL}, "n_clicks")],
    [State("search-results-store", "data"),
     State("documents-store", "data")],
    prevent_initial_call=True
)
def show_documents(n_clicks_list, results, documents_store):
    """Mostra documentos de um processo específico"""
    if not any(n_clicks_list) or not results:
        return False, "", documents_store
    
    # Encontrar qual botão foi clicado
    button_id = ctx.triggered[0]["prop_id"]
    process_index = json.loads(button_id.split(".")[0])["index"]
    
    if process_index >= len(results):
        return False, "Processo não encontrado", documents_store
    
    result = results[process_index]
    process_id = result.get("id", "")
    
    # Verificar se já temos os documentos em cache
    if process_id in documents_store:
        documents = documents_store[process_id]
    else:
        try:
            documents = fetch_documentos(process_id)
            documents_store[process_id] = documents
        except Exception as e:
            return True, dbc.Alert(f"Erro ao buscar documentos: {str(e)}", color="danger"), documents_store
    
    if not documents:
        modal_body = dbc.Alert("Nenhum documento encontrado para este processo.", color="warning")
    else:
        # Criar lista de documentos
        doc_items = []
        for i, doc in enumerate(documents):
            titulo = doc.get('titulo', 'Documento sem título')
            url = doc.get('url', '#')
            
            doc_card = html.Div([
                html.H6(titulo, className="mb-2"),
                html.A("Abrir Documento", href=url, target="_blank", className="document-link me-3"),
                dbc.Button([
                    html.I(className="fas fa-file-alt me-1"),
                    "Sumarizar"
                ], 
                id={"type": "summarize-button", "process": process_id, "doc": i},
                color="outline-info", 
                size="sm"
                )
            ], className="document-card")
            
            doc_items.append(doc_card)
        
        modal_body = html.Div(doc_items)
    
    return True, modal_body, documents_store

# Callback para gerar palavras-chave
@callback(
    [Output("keywords-modal", "is_open"),
     Output("keywords-modal-body", "children"),
     Output("keywords-store", "data")],
    [Input({"type": "keywords-button", "index": ALL}, "n_clicks")],
    [State("search-results-store", "data"),
     State("keywords-store", "data")],
    prevent_initial_call=True
)
def generate_process_keywords_callback(n_clicks_list, results, keywords_store):
    """Gera palavras-chave para um processo específico"""
    if not any(n_clicks_list) or not results:
        return False, "", keywords_store
    
    # Encontrar qual botão foi clicado
    button_id = ctx.triggered[0]["prop_id"]
    process_index = json.loads(button_id.split(".")[0])["index"]
    
    if process_index >= len(results):
        return False, "Processo não encontrado", keywords_store
    
    result = results[process_index]
    process_id = result.get("id", "")
    details = result.get("details", {})
    descricao = details.get('descricaocompleta', '')
    
    # Verificar se já temos as palavras-chave em cache
    if process_id in keywords_store:
        keywords = keywords_store[process_id]
    else:
        if not descricao or descricao.strip() == '':
            return True, dbc.Alert("Descrição não disponível para gerar palavras-chave.", color="warning"), keywords_store
        
        try:
            keywords = generate_keywords(descricao)
            keywords_store[process_id] = keywords
        except Exception as e:
            return True, dbc.Alert(f"Erro ao gerar palavras-chave: {str(e)}", color="danger"), keywords_store
    
    # Formatar palavras-chave como chips
    keywords_list = [kw.strip() for kw in keywords.split(";") if kw.strip()]
    chips = [html.Span(kw, className="keyword-chip") for kw in keywords_list]
    
    modal_body = html.Div([
        html.H6(f"Processo: {process_id}", className="mb-3"),
        html.P("Palavras-chave geradas:", className="fw-bold"),
        html.Div(chips, className="mb-3"),
        html.Hr(),
        html.P("Descrição original:", className="fw-bold"),
        html.P(descricao[:500] + ("..." if len(descricao) > 500 else ""), className="text-muted")
    ])
    
    return True, modal_body, keywords_store

# Callback para sumarizar documentos
@callback(
    [Output("summary-modal", "is_open"),
     Output("summary-modal-body", "children"),
     Output("summaries-store", "data")],
    [Input({"type": "summarize-button", "process": ALL, "doc": ALL}, "n_clicks")],
    [State("documents-store", "data"),
     State("summaries-store", "data")],
    prevent_initial_call=True
)
def summarize_document_callback(n_clicks_list, documents_store, summaries_store):
    """Sumariza um documento específico"""
    if not any(n_clicks_list):
        return False, "", summaries_store
    
    # Encontrar qual botão foi clicado
    button_id = ctx.triggered[0]["prop_id"]
    button_data = json.loads(button_id.split(".")[0])
    process_id = button_data["process"]
    doc_index = button_data["doc"]
    
    # Criar chave única para o cache
    summary_key = f"{process_id}_{doc_index}"
    
    # Verificar se já temos o resumo em cache
    if summary_key in summaries_store:
        summary = summaries_store[summary_key]
        doc_title = "Documento"
    else:
        # Buscar documento
        if process_id not in documents_store:
            return True, dbc.Alert("Documentos não encontrados", color="danger"), summaries_store
        
        documents = documents_store[process_id]
        if doc_index >= len(documents):
            return True, dbc.Alert("Documento não encontrado", color="danger"), summaries_store
        
        doc = documents[doc_index]
        doc_title = doc.get('titulo', 'Documento')
        doc_url = doc.get('url', '')
        
        if not doc_url:
            return True, dbc.Alert("URL do documento não disponível", color="warning"), summaries_store
        
        try:
            summary = summarize_document(doc_url)
            summaries_store[summary_key] = summary
        except Exception as e:
            return True, dbc.Alert(f"Erro ao sumarizar documento: {str(e)}", color="danger"), summaries_store
    
    modal_body = html.Div([
        html.H6(f"Resumo: {doc_title}", className="mb-3"),
        html.Div(summary, className="summary-card")
    ])
    
    return True, modal_body, summaries_store

# Callbacks para fechar modals
@callback(
    Output("documents-modal", "is_open", allow_duplicate=True),
    Input("close-documents-modal", "n_clicks"),
    prevent_initial_call=True
)
def close_documents_modal(n_clicks):
    return False

@callback(
    Output("keywords-modal", "is_open", allow_duplicate=True),
    Input("close-keywords-modal", "n_clicks"),
    prevent_initial_call=True
)
def close_keywords_modal(n_clicks):
    return False

@callback(
    Output("summary-modal", "is_open", allow_duplicate=True),
    Input("close-summary-modal", "n_clicks"),
    prevent_initial_call=True
)
def close_summary_modal(n_clicks):
    return False

# Exportar para Excel (MANTIDO)
@callback(
    Output("download-excel", "data"),
    Input("export-button", "n_clicks"),
    [State("search-results-store", "data"),
     State("last-query-store", "data"),
     State("search-type-store", "data")],
    prevent_initial_call=True
)
def export_to_excel(n_clicks, results, query, search_type):
    """Exporta resultados para Excel"""
    if not n_clicks or not results:
        return no_update
    
    try:
        # Criar DataFrame
        data = []
        for result in results:
            details = result.get("details", {})
            if details:
                data.append({
                    "Rank": result["rank"],
                    "ID": result["id"],
                    "Similaridade": result["similarity"],
                    "Órgão": details.get("orgaoentidade_razaosocial", "N/A"),
                    "Unidade": details.get("unidadeorgao_nomeunidade", "N/A"),
                    "Município": details.get("unidadeorgao_municipionome", "N/A"),
                    "UF": details.get("unidadeorgao_ufsigla", "N/A"),
                    "Valor": details.get("valortotalhomologado", 0),
                    "Data Abertura": details.get("dataaberturaproposta", "N/A"),
                    "Data Encerramento": details.get("dataencerramentoproposta", "N/A"),
                    "Descrição": details.get("descricaocompleta", "N/A")
                })
        
        df = pd.DataFrame(data)
        
        # Gerar arquivo Excel em memória
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Resultados', index=False)
        
        # Nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type]["name"].lower()
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()[:30].replace(" ", "_")
        filename = f"govgo_busca_{search_type_name}_{query_clean}_{timestamp}.xlsx"
        
        return dcc.send_bytes(output.getvalue(), filename)
        
    except Exception as e:
        return no_update

# Limpar resultados (MANTIDO)
@callback(
    [Output("search-query", "value"),
     Output("search-results", "children", allow_duplicate=True),
     Output("search-info", "children", allow_duplicate=True),
     Output("action-buttons", "style", allow_duplicate=True)],
    Input("clear-button", "n_clicks"),
    prevent_initial_call=True
)
def clear_search(n_clicks):
    """Limpa os resultados da busca"""
    if n_clicks:
        return "", "", "", {"display": "none"}
    return no_update, no_update, no_update, no_update

# ============================================
# Funções auxiliares (ATUALIZADA)
# ============================================

def create_result_cards_v2(results, query, search_type):
    """Cria os cards de resultado com as NOVAS FUNCIONALIDADES"""
    if not results:
        return []
    
    cards = []
    for i, result in enumerate(results):
        details = result.get("details", {})
        
        # Informações principais
        rank = result["rank"]
        similarity = result["similarity"]
        contract_id = result["id"]
        
        # Detalhes da contratação
        orgao = details.get("orgaoentidade_razaosocial", "N/A")
        unidade = details.get("unidadeorgao_nomeunidade", "N/A")
        municipio = details.get("unidadeorgao_municipionome", "N/A")
        uf = details.get("unidadeorgao_ufsigla", "N/A")
        valor = details.get("valortotalhomologado", 0)
        data_abertura = details.get("dataaberturaproposta", "N/A")
        data_encerramento = details.get("dataencerramentoproposta", "N/A")
        descricao = details.get("descricaocompleta", "N/A")
        
        # Formatar valor
        try:
            valor_formatado = f"R$ {float(valor):,.2f}" if valor and valor != "N/A" else "N/A"
        except:
            valor_formatado = "N/A"
        
        # Truncar descrição
        descricao_truncada = (descricao[:200] + "...") if len(str(descricao)) > 200 else descricao
        
        # Cor da borda baseada na similaridade
        if similarity > 0.8:
            border_color = "success"
        elif similarity > 0.6:
            border_color = "warning"
        else:
            border_color = "secondary"
        
        # Card principal (ESTRUTURA ORIGINAL + NOVOS BOTÕES)
        card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6(f"#{rank} - {contract_id}", className="mb-0 text-primary")
                    ], md=8),
                    dbc.Col([
                        dbc.Badge(
                            f"Similaridade: {similarity:.4f}",
                            color=border_color,
                            className="similarity-badge"
                        )
                    ], md=4, className="text-end")
                ])
            ]),
            dbc.CardBody([
                # Informações do órgão (MANTIDAS)
                html.Div([
                    html.Strong("Órgão: "), html.Span(orgao, className="text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Unidade: "), html.Span(unidade, className="text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Local: "), html.Span(f"{municipio}/{uf}", className="text-muted")
                ], className="mb-2"),
                
                # Informações contratuais (MANTIDAS)
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Strong("Valor: "), html.Span(valor_formatado, className="text-success fw-bold")
                        ])
                    ], md=6),
                    dbc.Col([
                        html.Div([
                            html.Strong("Encerramento: "), html.Span(str(data_encerramento), className="text-muted")
                        ])
                    ], md=6)
                ], className="mb-3"),
                
                # Descrição (MANTIDA)
                html.Div([
                    html.Strong("Descrição:"),
                    html.P(descricao_truncada, className="description-text mt-1")
                ]),
                
                # Scores específicos para busca híbrida (MANTIDOS)
                *([
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            dbc.Badge(f"Semântico: {result.get('semantic_score', 0):.4f}", color="info", className="me-2")
                        ], md=6),
                        dbc.Col([
                            dbc.Badge(f"Palavra-chave: {result.get('keyword_score', 0):.4f}", color="secondary")
                        ], md=6)
                    ])
                ] if search_type == 3 and 'semantic_score' in result else []),
                
                # NOVOS BOTÕES DE AÇÃO
                html.Hr(),
                html.Div([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.I(className="fas fa-file-pdf me-1"),
                            "Ver Documentos"
                        ], 
                        id={"type": "documents-button", "index": i},
                        color="outline-primary", 
                        size="sm"
                        ),
                        dbc.Button([
                            html.I(className="fas fa-tags me-1"),
                            "Gerar Palavras-chave"
                        ], 
                        id={"type": "keywords-button", "index": i},
                        color="outline-info", 
                        size="sm"
                        )
                    ])
                ], className="process-actions")
            ])
        ], className="search-card mb-3", color=border_color, outline=True)
        
        cards.append(card)
    
    return cards

if __name__ == "__main__":
    app.run(
        debug=True, 
        host='127.0.0.1',  # Forçar localhost
        port=8062,  # Nova porta para v2
        dev_tools_hot_reload=True, 
        dev_tools_props_check=False, 
        dev_tools_ui=False
    )