# app.py
import dash
from dash import html, dcc, callback, Input, Output, State, ctx, ALL, MATCH, no_update
import dash_bootstrap_components as dbc
from datetime import datetime, date
import pandas as pd
import json
from utils import (
    fetch_processos, fetch_documentos, generate_keywords, summarize_document,
    process_data, format_keywords, to_excel, get_excel_filename,
    get_modalidades, get_ufs_brasil
)

# Inicializa o app Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# ============================================
# Layout do aplicativo
# ============================================

app.layout = dbc.Container([
    # Título
    html.H1("Visualização de Processos - PNCP", className="my-3"),
    
    # Layout principal: filtros e resultados
    dbc.Row([
        # Coluna de filtros 
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filtros", className="filter-header"),
                dbc.CardBody([
                    # Input para palavras-chave
                    html.Div([
                        dbc.Label("Palavras-chave:"),
                        dbc.InputGroup([
                            dbc.Input(
                                id="keyword-input",
                                placeholder="Digite e pressione Enter",
                                type="text",
                                debounce=True
                            ),
                            dbc.Button("Adicionar", id="add-keyword", n_clicks=0)
                        ]),
                        html.Div(id="keyword-chips", className="mt-2")
                    ]),
                    html.Hr(),
                    
                    # Seletores de data
                    html.Div([
                        dbc.Label("Data Inicial:"),
                        dcc.DatePickerSingle(
                            id="data-inicial",
                            date=date(datetime.now().year, datetime.now().month, 1),
                            display_format="DD/MM/YYYY"
                        ),
                        html.Br(),
                        dbc.Label("Data Final:"),
                        dcc.DatePickerSingle(
                            id="data-final",
                            date=date.today(),
                            display_format="DD/MM/YYYY"
                        )
                    ]),
                    html.Hr(),
                    
                    # Seletor de modalidade
                    html.Div([
                        dbc.Label("Modalidade:"),
                        dcc.Dropdown(
                            id="modalidade",
                            options=[{"label": k, "value": v} for k, v in get_modalidades().items()],
                            value=6,
                            clearable=False
                        )
                    ]),
                    html.Hr(),
                    
                    # Seletor de UFs
                    html.Div([
                        dbc.Label("UFs:"),
                        dcc.Dropdown(
                            id="ufs",
                            options=[{"label": f"{k} - {v}", "value": k} for k, v in get_ufs_brasil().items()],
                            value=["ES", "SP"],
                            multi=True
                        )
                    ]),
                    html.Hr(),
                    
                    # Tamanho da página
                    html.Div([
                        dbc.Label("Itens por página:"),
                        dbc.Input(
                            id="tamanho-pagina",
                            type="number",
                            min=10,
                            max=100,
                            step=10,
                            value=50
                        )
                    ]),
                    html.Hr(),
                    
                    # Botão de busca
                    dbc.Button(
                        "Buscar Processos",
                        id="buscar-processos",
                        color="primary",
                        className="w-100 mt-2"
                    )
                ])
            ])
        ], md=3, className="mb-3"),
        
        # Coluna de resultados
        dbc.Col([
            # Área de filtros ativos
            html.Div([
                html.H4("Filtros Ativos:", className="mb-2"),
                html.Div(id="filtros-ativos", className="mb-3")
            ]),
            
            # Botão para exportação
            html.Div([
                dbc.Button(
                    "Exportar Excel", 
                    id="btn-excel",
                    color="success",
                    className="mb-3"
                ),
                dcc.Download(id="download-excel")
            ]),
            
            # Contador de resultados
            html.Div(id="resultados-info", className="mb-2"),
            
            # Contêiner de resultados com rolagem infinita
            html.Div(
                id="processos-container",
                children=[],
                style={"minHeight": "200px"}
            ),
            
            # Botão "Carregar mais" para rolagem infinita
            html.Div(
                id="carregar-mais-container",
                className="text-center my-3",
                children=[
                    dbc.Button(
                        "Carregar Mais Resultados", 
                        id="carregar-mais",
                        color="secondary",
                        className="d-none"
                    )
                ]
            )
        ], md=9)
    ]),
    
    # Armazenamento de dados
    dcc.Store(id="store-processos", data=[]),
    dcc.Store(id="store-filtrados", data=[]),
    dcc.Store(id="store-keywords", data=[]),
    dcc.Store(id="store-page", data=1),
    
    # Modal para sumários
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Sumário do Documento")),
        dbc.ModalBody([
            html.H5(id="sumario-titulo", className="mb-3"),
            dbc.Spinner(html.Div(id="sumario-conteudo", className="sumario-texto"))
        ]),
        dbc.ModalFooter(
            dbc.Button("Fechar", id="fechar-sumario", className="ms-auto")
        )
    ], id="sumario-modal", size="lg", is_open=False),
    
    # Indicador global de carregamento
    dbc.Spinner(
        html.Div(id="loading-output"),
        spinner_style={"width": "3rem", "height": "3rem"},
        fullscreen=True,
        fullscreen_style={"backgroundColor": "rgba(255, 255, 255, 0.7)"},
        show_initially=False
    )
], fluid=True)

# ============================================
# Callbacks para interatividade
# ============================================

# Callback para adicionar palavras-chave
@callback(
    [Output("store-keywords", "data"),
     Output("keyword-input", "value")],
    [Input("add-keyword", "n_clicks"),
     Input("keyword-input", "n_submit")],
    [State("store-keywords", "data"),
     State("keyword-input", "value")]
)
def add_keyword(n_clicks, n_submit, keywords, value):
    # Verifica se foi acionado
    if not (n_clicks or n_submit) or not value:
        return keywords, value
    
    # Separa múltiplas palavras-chave
    new_keywords = [k.strip().lower() for k in value.replace(";", ",").split(",") if k.strip()]
    
    # Adiciona às existentes sem duplicar
    current_keywords = keywords or []
    for kw in new_keywords:
        if kw and kw not in current_keywords:
            current_keywords.append(kw)
    
    return current_keywords, ""

# Callback para remover palavra-chave
@callback(
    Output("store-keywords", "data", allow_duplicate=True),
    Input({"type": "remove-keyword", "index": ALL}, "n_clicks"),
    State("store-keywords", "data"),
    prevent_initial_call=True
)
def remove_keyword(clicks, keywords):
    if not any(clicks) or not keywords:
        return no_update
    
    # Identifica qual botão foi clicado
    button_id = ctx.triggered_id
    if button_id:
        index = button_id["index"]
        keywords = [kw for i, kw in enumerate(keywords) if i != index]
    
    return keywords

# Callback para renderizar chips de palavras-chave
@callback(
    Output("keyword-chips", "children"),
    Input("store-keywords", "data")
)
def render_keyword_chips(keywords):
    if not keywords:
        return html.P("Nenhuma palavra-chave definida", className="text-muted small")
    
    chips = []
    for i, keyword in enumerate(keywords):
        chips.append(
            dbc.Badge(
                [
                    keyword,
                    html.I(className="fas fa-times ms-1", style={"cursor": "pointer"})
                ],
                id={"type": "remove-keyword", "index": i},
                color="light",
                text_color="dark",
                className="me-1 mb-1",
                style={"cursor": "pointer"}
            )
        )
    
    return html.Div(chips)

# Callback para renderizar filtros ativos
@callback(
    Output("filtros-ativos", "children"),
    [Input("store-keywords", "data"),
     Input("data-inicial", "date"),
     Input("data-final", "date"),
     Input("modalidade", "value"),
     Input("ufs", "value")]
)
def render_filtros_ativos(keywords, data_inicial, data_final, modalidade, ufs):
    filtros = []
    
    # Palavras-chave
    if keywords:
        filtros.append(html.Div([
            html.Strong("Palavras-chave: "),
            html.Span(", ".join(keywords))
        ]))
    
    # Datas
    if data_inicial or data_final:
        data_ini = datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%d/%m/%Y") if data_inicial else "N/D"
        data_fim = datetime.strptime(data_final, "%Y-%m-%d").strftime("%d/%m/%Y") if data_final else "N/D"
        filtros.append(html.Div([
            html.Strong("Período: "),
            html.Span(f"{data_ini} até {data_fim}")
        ]))
    
    # Modalidade
    if modalidade:
        nome_modalidade = next((k for k, v in get_modalidades().items() if v == modalidade), "Desconhecida")
        filtros.append(html.Div([
            html.Strong("Modalidade: "),
            html.Span(nome_modalidade)
        ]))
    
    # UFs
    if ufs:
        filtros.append(html.Div([
            html.Strong("UFs: "),
            html.Span(", ".join(ufs))
        ]))
    
    if not filtros:
        return html.P("Nenhum filtro aplicado", className="text-muted")
    
    return filtros

# Callback para buscar processos
@callback(
    [Output("store-processos", "data"),
     Output("store-filtrados", "data"),
     Output("store-page", "data"),
     Output("loading-output", "children"),
     Output("processos-container", "children")],
    Input("buscar-processos", "n_clicks"),
    [State("data-inicial", "date"),
     State("data-final", "date"),
     State("modalidade", "value"),
     State("ufs", "value"),
     State("tamanho-pagina", "value"),
     State("store-keywords", "data")],
    prevent_initial_call=True
)
def buscar_processos(n_clicks, data_inicial, data_final, modalidade, ufs, tamanho_pagina, keywords):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    
    # Formata datas para API
    data_inicial_str = datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%Y%m%d") if data_inicial else ""
    data_final_str = datetime.strptime(data_final, "%Y-%m-%d").strftime("%Y%m%d") if data_final else ""
    
    # Busca na API
    processos, error_msg = fetch_processos(data_inicial_str, data_final_str, modalidade, tamanho_pagina, ufs)
    
    if error_msg:
        return [], [], 1, error_msg, html.Div(error_msg, className="alert alert-danger")
    
    if not processos:
        return [], [], 1, "", html.Div("Nenhum processo encontrado", className="alert alert-info")
    
    # Processa dados
    df = process_data(processos)
    
    # Filtra por palavras-chave, se houver
    if keywords and "objeto" in df.columns:
        mask = pd.Series(False, index=df.index)
        for kw in keywords:
            mask |= df["objeto"].str.lower().str.contains(kw.lower(), na=False)
        df_filtered = df[mask]
    else:
        df_filtered = df
    
    # Converte para dicionário para armazenamento
    processos_list = df.to_dict("records")
    filtrados_list = df_filtered.to_dict("records")
    
    # Gera cartões para os primeiros 10 resultados
    cards = criar_cards_processos(filtrados_list[:10])
    
    return processos_list, filtrados_list, 1, "", cards

# Callback para carregar mais resultados (rolagem infinita)
@callback(
    [Output("processos-container", "children", allow_duplicate=True),
     Output("store-page", "data", allow_duplicate=True),
     Output("carregar-mais", "className")],
    Input("carregar-mais", "n_clicks"),
    [State("store-filtrados", "data"),
     State("store-page", "data"),
     State("processos-container", "children")],
    prevent_initial_call=True
)
def carregar_mais_resultados(n_clicks, filtrados, page, current_cards):
    if not n_clicks or not filtrados:
        return no_update, no_update, no_update
    
    # Calcula índices para a próxima página
    itens_por_pagina = 10
    start = page * itens_por_pagina
    end = start + itens_por_pagina
    
    # Verifica se há mais itens
    if start >= len(filtrados):
        return no_update, no_update, "d-none"
    
    # Obtém próximo conjunto de resultados
    next_items = filtrados[start:end]
    next_cards = criar_cards_processos(next_items)
    
    # Combina com cards existentes
    all_cards = current_cards + next_cards
    
    # Esconde botão se for o último lote
    btn_class = "d-none" if end >= len(filtrados) else "mt-3"
    
    return all_cards, page + 1, btn_class

# Callback para mostrar/esconder botão "Carregar mais"
@callback(
    Output("carregar-mais", "className", allow_duplicate=True),
    [Input("store-filtrados", "data"),
     Input("store-page", "data")],
    prevent_initial_call=True
)
def update_carregar_mais(filtrados, page):
    if not filtrados:
        return "d-none"
    
    itens_por_pagina = 10
    total_loaded = page * itens_por_pagina
    
    if total_loaded >= len(filtrados):
        return "d-none"
    else:
        return "mt-3"

# Callback para mostrar informações de resultados
@callback(
    Output("resultados-info", "children"),
    [Input("store-processos", "data"),
     Input("store-filtrados", "data")]
)
def update_resultado_info(processos, filtrados):
    if not processos:
        return ""
    
    total_processos = len(processos)
    total_filtrados = len(filtrados)
    
    if total_processos == total_filtrados:
        return html.P(f"Exibindo todos os {total_processos} processos encontrados.")
    else:
        return html.P(f"Exibindo {total_filtrados} de {total_processos} processos (filtrados).")

# Callback para exportar para Excel
@callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    [State("store-processos", "data"),
     State("store-filtrados", "data")],
    prevent_initial_call=True
)
def export_excel(n_clicks, processos, filtrados):
    if not n_clicks or not processos:
        return no_update
    
    df_all = pd.DataFrame(processos)
    df_filtered = pd.DataFrame(filtrados)
    
    excel_data = to_excel(df_all, df_filtered)
    
    return dcc.send_bytes(excel_data, get_excel_filename())

# Callback para buscar e mostrar documentos
@callback(
    Output({"type": "documentos-container", "index": MATCH}, "children"),
    Input({"type": "processo-store", "index": MATCH}, "data"),
    prevent_initial_call=True
)
def carregar_documentos(processo):
    if not processo:
        return html.P("Nenhum documento disponível.")
    
    cnpj = processo.get("cnpj", "")
    ano = processo.get("ano", "")
    sequencial = processo.get("sequencial", "")
    
    if not (cnpj and ano and sequencial):
        return html.P("Dados insuficientes para buscar documentos.")
    
    # Busca documentos
    documentos = fetch_documentos(cnpj, ano, sequencial)
    
    if not documentos:
        return html.P("Nenhum documento encontrado.")
    
    # Cria lista de documentos
    doc_items = []
    for i, doc in enumerate(documentos):
        titulo = doc.get("titulo", "Documento")
        doc_url = doc.get("url", "#")
        
        doc_items.append(html.Div(
            [
                # Link para o documento
                html.A(titulo, href=doc_url, target="_blank", className="me-2"),
                
                # Botão sumarizar
                dbc.Button(
                    "Sumarizar",
                    id={"type": "btn-sumarizar", "proc_idx": processo.get("index", 0), "doc_idx": i},
                    color="secondary",
                    size="sm",
                    className="ms-2"
                )
            ],
            className="documento-item mb-1 d-flex justify-content-between align-items-center",
            **{"data-url": doc_url, "data-titulo": titulo}  # Armazena metadados como atributos
        ))
    
    return doc_items

# Callback para gerar tópicos
@callback(
    Output({"type": "topicos-card", "index": MATCH}, "children"),
    Output({"type": "topicos-card", "index": MATCH}, "className"),
    Output({"type": "loading-topicos", "index": MATCH}, "children"),
    Input({"type": "btn-topicos", "index": MATCH}, "n_clicks"),
    State({"type": "processo-store", "index": MATCH}, "data"),
    prevent_initial_call=True
)
def gerar_topicos(n_clicks, processo):
    if not n_clicks or not processo:
        return no_update, no_update, no_update
    
    objeto = processo.get("objeto", "")
    
    if not objeto:
        return "Objeto não disponível", "alert alert-warning", ""
    
    # Gera tópicos via OpenAI
    try:
        keywords = generate_keywords(objeto)
        
        # Formata tópicos como chips
        topicos_list = format_keywords(keywords)
        topicos_chips = [
            dbc.Badge(topico, color="light", text_color="dark", className="me-1 mb-1") 
            for topico in topicos_list
        ]
        
        return topicos_chips, "mt-3 topicos-card", ""
    except Exception as e:
        return f"Erro: {str(e)}", "alert alert-danger", ""

# Callback para sumarizar documento e mostrar modal
@callback(
    [Output("sumario-modal", "is_open"),
     Output("sumario-titulo", "children"),
     Output("sumario-conteudo", "children")],
    [Input({"type": "btn-sumarizar", "proc_idx": ALL, "doc_idx": ALL}, "n_clicks"),
     Input("fechar-sumario", "n_clicks")],
    [State("sumario-modal", "is_open")],
    prevent_initial_call=True
)
def mostrar_sumario(sumarizar_clicks, fechar_clicks, is_open):
    ctx_triggered = ctx.triggered_id
    
    # Fechar modal
    if ctx_triggered == "fechar-sumario":
        return False, "", ""
    
    # Abrir modal e mostrar sumário
    if isinstance(ctx_triggered, dict) and ctx_triggered.get("type") == "btn-sumarizar":
        # Identifica o documento clicado
        proc_idx = ctx_triggered.get("proc_idx")
        doc_idx = ctx_triggered.get("doc_idx")
        
        # Busca o elemento de documento (para obter URL e título)
        doc_elem = html.Div()  # Elemento padrão caso não encontre
        
        # Alternativa: buscar informações do documento diretamente (seria melhor usar outro método)
        # Por ora, usamos uma abordagem simplificada
        documento_url = f"https://exemplo.com/documento-{proc_idx}-{doc_idx}"
        documento_titulo = f"Documento {doc_idx + 1}"
        
        # Gera sumário
        with dbc.Spinner():
            sumario = summarize_document(documento_url)
        
        return True, documento_titulo, dbc.Card(dbc.CardBody(sumario))
    
    # Estado padrão
    return is_open, no_update, no_update

# ============================================
# Funções auxiliares para UI
# ============================================

# Modificar a função criar_cards_processos

def criar_cards_processos(processos):
    """Cria os cartões de processo para exibição"""
    if not processos:
        return [html.Div("Nenhum processo encontrado.", className="alert alert-warning")]
    
    cards = []
    for idx, processo in enumerate(processos):
        # Extrai informações
        orgao = processo.get("orgaoEntidade.razaoSocial", "N/D")
        uf = processo.get("unidadeOrgao.ufSigla", "N/D")
        data_inclusao = processo.get("dataInclusao", "N/D")
        if isinstance(data_inclusao, str) and "T" in data_inclusao:
            data_inclusao = data_inclusao.split("T")[0]
        num_processo = processo.get("processo", "N/D")
        objeto = processo.get("objeto", "N/D")
        valor_estimado = processo.get("valorTotalEstimado", "N/D")
        
        # Formata valor estimado
        if isinstance(valor_estimado, (int, float)):
            try:
                import locale
                valor_estimado = locale.currency(valor_estimado, grouping=True)
            except:
                valor_estimado = f"R$ {valor_estimado:,.2f}"
        
        # Identificadores para busca de documentos
        cnpj = processo.get("orgaoEntidade.cnpj", "")
        ano = processo.get("anoCompra", "")
        sequencial = processo.get("sequencialCompra", "")
        
        # Dados específicos do processo para armazenar
        processo_data = {
            "index": idx,
            "cnpj": cnpj,
            "ano": ano,
            "sequencial": sequencial,
            "objeto": objeto
        }
        
        # Carregar documentos no momento da criação do card
        documentos = []
        if cnpj and ano and sequencial:
            documentos = fetch_documentos(cnpj, ano, sequencial)
        
        # Layout de duas colunas: card principal e card de tópicos
        card = dbc.Row([
            # Coluna 1: Card do Processo
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5(orgao, className="mb-0"),
                        html.Span(f"UF: {uf}", className="badge bg-light text-dark ms-2")
                    ], className="d-flex justify-content-between align-items-center"),
                    
                    dbc.CardBody([
                        # Store para dados do processo
                        dcc.Store(
                            id={"type": "processo-store", "index": idx},
                            data=processo_data
                        ),
                        
                        # Informações principais
                        html.Div([
                            html.P([html.Strong("Data: "), html.Span(data_inclusao)], className="mb-1"),
                            html.P([html.Strong("Processo: "), html.Span(num_processo)], className="mb-1"),
                            html.P([html.Strong("Valor Estimado: "), html.Span(valor_estimado)], className="mb-1"),
                            html.Div([
                                html.Strong("Objeto: "), 
                                html.Span(objeto, className="objeto-texto"),
                                dbc.Button(
                                    "Gerar Tópicos", 
                                    id={"type": "btn-topicos", "index": idx},
                                    color="link",
                                    size="sm", 
                                    className="ms-2"
                                )
                            ], className="mb-2"),
                            
                            # Spinner para carregamento de tópicos
                            html.Div(
                                id={"type": "loading-topicos", "index": idx},
                                children=[],
                                style={"height": "20px"}
                            )
                        ]),
                        
                        # Divisor
                        html.Hr(className="my-2"),
                        
                        # Documentos - Exibidos diretamente
                        html.Div([
                            html.H6("Documentos:", className="mb-2"),
                            # Renderização direta dos documentos
                            html.Div(
                                [
                                    # Se não houver documentos
                                    html.P("Nenhum documento encontrado.") if not documentos else
                                    # Lista de documentos
                                    html.Div([
                                        html.Div(
                                            [
                                                # Link para o documento
                                                html.A(doc.get("titulo", "Documento"), 
                                                      href=doc.get("url", "#"), 
                                                      target="_blank", 
                                                      className="me-2"),
                                                
                                                # Botão sumarizar
                                                dbc.Button(
                                                    "Sumarizar",
                                                    id={"type": "btn-sumarizar", "proc_idx": idx, "doc_idx": i},
                                                    color="secondary",
                                                    size="sm",
                                                    className="ms-2"
                                                )
                                            ],
                                            className="documento-item mb-1 d-flex justify-content-between align-items-center",
                                        ) for i, doc in enumerate(documentos)
                                    ])
                                ],
                                id={"type": "documentos-container", "index": idx},
                                className="documentos-lista"
                            )
                        ])
                    ])
                ], className="mb-3 processo-card")
            ], md=8),
            
            # Coluna 2: Card de Tópicos
            dbc.Col([
                html.Div(
                    id={"type": "topicos-card", "index": idx},
                    children=[],
                    className="d-none"  # Inicialmente escondido
                )
            ], md=4)
        ], className="mb-3")
        
        cards.append(card)
    
    return cards

# Executa o aplicativo
if __name__ == "__main__":
    app.run_server(debug=True)