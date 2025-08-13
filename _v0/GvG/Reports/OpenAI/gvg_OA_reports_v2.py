import os
import io
import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table, no_update, ALL
from dash.dcc import send_data_frame
import dash_bootstrap_components as dbc

# Configurações de caminhos (ajuste conforme seu ambiente)
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

# =============================================================================
# Funções de Lógica (adaptadas do reports_v8.py)
# =============================================================================

def generate_sql_from_nl(nl_query: str) -> str:
    """
    Simula a geração de um comando SQL a partir da consulta em linguagem natural.
    Em uma implementação real, esta função integraria a chamada à API OpenAI.
    """
    # Exemplo: sempre retorna uma query para a tabela 'contrato'.
    return "SELECT * FROM contrato LIMIT 100;"

def execute_report(sql: str) -> pd.DataFrame:
    """
    Executa a query SQL no banco de dados SQLite.
    Se o arquivo DB não existir, gera dados fictícios para demonstração.
    """
    try:
        if os.path.exists(DB_FILE):
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return df
        else:
            # Dados simulados para demonstração
            data = {
                "ID": [1, 2, 3],
                "Valor": [100, 200, 300],
                "Data": ["2024-01-01", "2024-01-02", "2024-01-03"]
            }
            return pd.DataFrame(data)
    except Exception as e:
        print("Erro ao executar a query:", e)
        return pd.DataFrame()

def generate_report_filename(sql: str) -> str:
    """
    Gera um nome para o relatório em Excel com base no conteúdo do SQL.
    Se 'contrato' estiver presente, retorna "CONTRATO_REPORT.xlsx".
    """
    base = "REPORT"
    if "contrato" in sql.lower():
        base = "CONTRATO_REPORT"
    return base.upper() + ".xlsx"

# =============================================================================
# Layout e Funcionalidades com Dash
# =============================================================================

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "GovGo - Chat de Consultas PNCP"

app.layout = dbc.Container([
    html.H1("GovGo - Chat de Consultas PNCP", className="text-center my-4"),
    # Armazena o histórico da conversa (lista de interações)
    dcc.Store(id="conversation-store", data=[]),
    # Componente para download do arquivo Excel
    dcc.Download(id="download-excel"),
    dbc.Row([
        dbc.Col([
            html.H4("Chat - Consultas"),
            html.Div(id="left-chat", style={
                "height": "500px",
                "overflowY": "auto",
                "border": "1px solid #ccc",
                "padding": "10px",
                "backgroundColor": "#fdfdfd"
            }),
            dbc.InputGroup([
                dbc.Input(id="user-input", placeholder="Faça uma pergunta...", type="text"),
                dbc.Button("Enviar", id="send-btn", color="primary")
            ], className="mt-2")
        ], width=6),
        dbc.Col([
            html.H4("Resultados"),
            html.Div(id="right-results", style={
                "height": "500px",
                "overflowY": "auto",
                "border": "1px solid #ccc",
                "padding": "10px",
                "backgroundColor": "#fdfdfd"
            })
        ], width=6)
    ], className="mb-4")
], fluid=True)

# -----------------------------------------------------------------------------
# Callback: Atualiza o histórico de conversas quando o usuário envia uma mensagem
# -----------------------------------------------------------------------------
@app.callback(
    Output("conversation-store", "data"),
    Output("user-input", "value"),
    Input("send-btn", "n_clicks"),
    State("user-input", "value"),
    State("conversation-store", "data"),
    prevent_initial_call=True
)
def update_conversation(n_clicks, user_message, conversation):
    if not user_message or user_message.strip() == "":
        return conversation, ""
    new_id = len(conversation) + 1  # Numeração sequencial
    sql = generate_sql_from_nl(user_message)
    df = execute_report(sql)
    # Prepara os dados para a DataTable
    table_data = df.to_dict("records")
    table_columns = [{"name": col, "id": col} for col in df.columns]
    conversation.append({
        "id": new_id,
        "query": user_message,
        "sql": sql,
        "result": {"data": table_data, "columns": table_columns}
    })
    return conversation, ""

# -----------------------------------------------------------------------------
# Callback: Renderiza o painel esquerdo (chat de consultas)
# -----------------------------------------------------------------------------
@app.callback(
    Output("left-chat", "children"),
    Input("conversation-store", "data")
)
def render_left_chat(conversation):
    elements = []
    for conv in conversation:
        num = conv["id"]
        # Mensagem do usuário: alinhada à direita, fundo azul claro
        user_div = html.Div([
            html.Strong(f"#{num} "),
            html.Span(conv["query"])
        ], style={
            "textAlign": "right",
            "backgroundColor": "#cce5ff",
            "padding": "5px",
            "borderRadius": "10px",
            "margin": "5px"
        })
        # Resposta do assistente (SQL): alinhada à esquerda, fundo cinza claro
        sql_div = html.Div([
            html.Strong(f"#{num} "),
            html.Span(conv["sql"])
        ], style={
            "textAlign": "left",
            "backgroundColor": "#e2e3e5",
            "padding": "5px",
            "borderRadius": "10px",
            "margin": "5px"
        })
        elements.extend([user_div, sql_div])
    return elements

# -----------------------------------------------------------------------------
# Callback: Renderiza o painel direito (resultados)
# -----------------------------------------------------------------------------
@app.callback(
    Output("right-results", "children"),
    Input("conversation-store", "data")
)
def render_right_results(conversation):
    cards = []
    for conv in conversation:
        num = conv["id"]
        card = dbc.Card([
            dbc.CardHeader(html.H5(f"Resultado #{num}")),
            dbc.CardBody([
                dash_table.DataTable(
                    data=conv["result"]["data"],
                    columns=conv["result"]["columns"],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', "padding": "5px"},
                    style_header={'backgroundColor': "#f8f9fa", 'fontWeight': 'bold'},
                    page_action="none"
                ),
                dbc.ButtonGroup([
                    dbc.Button("Download", id={"type": "download-btn", "index": num}, color="primary", size="sm"),
                    dbc.Button("Nuvem", color="secondary", size="sm"),
                    dbc.Button("Compartilhar", color="secondary", size="sm")
                ], className="mt-2")
            ])
        ], className="mb-3")
        cards.append(card)
    return cards

# -----------------------------------------------------------------------------
# Callback: Exporta os dados para Excel via botão de Download
# -----------------------------------------------------------------------------
@app.callback(
    Output("download-excel", "data"),
    Input({"type": "download-btn", "index": ALL}, "n_clicks"),
    State("conversation-store", "data"),
    prevent_initial_call=True
)
def download_excel(n_clicks_list, conversation):
    if not n_clicks_list or not any(n_clicks_list):
        return no_update
    triggered = ctx.triggered_id
    if not triggered:
        return no_update
    conv_id = triggered["index"]
    conv = next((item for item in conversation if item["id"] == conv_id), None)
    if not conv:
        return no_update
    df = pd.DataFrame(conv["result"]["data"])
    filename = generate_report_filename(conv["sql"])
    return send_data_frame(df.to_excel, filename, index=False)

# =============================================================================
# Execução do Servidor (localhost) na porta 8051
# =============================================================================
if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
