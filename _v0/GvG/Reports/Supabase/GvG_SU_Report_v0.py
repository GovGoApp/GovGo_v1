import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import openai
from datetime import datetime, timedelta
import time
import os
import base64
import traceback
import sqlite3
import dash_bootstrap_components as dbc
import dash.dependencies
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from supabase config
env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
config = {}
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()

# OpenAI configuration
from openai import OpenAI
client = OpenAI(api_key="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")
thread = client.beta.threads.create()

assistant_id = "asst_MoxO9SNrQt4313fJ8Lzqt7iA"  # SUPABASE_SQL_v0 Assistant
model_id = "gpt-4o"

# Supabase Database Configuration
DB_CONFIG = {
    'host': config.get('host'),
    'port': config.get('port'),
    'dbname': config.get('dbname'),
    'user': config.get('user'),
    'password': config.get('password')
}

class SupabaseConnection:
    def __init__(self):
        self.connection = None
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def execute_query(self, query, params=None):
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def close(self):
        if self.connection:
            self.connection.close()

db = SupabaseConnection()

# Variável de controle para debug
DEBUG = True

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Assistant functions - IDENTICO AO gvg_CL_reports_v3.py
# OPENAI SEND USER MESSAGE
def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    debug_print(f"Enviando mensagem para thread {thread.id[:8]}...: '{content[:50]}...'")
    formatted_content = [{"type": "text", "text": content}]
    try:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=formatted_content
        )
        debug_print("Mensagem enviada com sucesso")
    except Exception as e:
        debug_print(f"Erro ao enviar mensagem: {str(e)}")
        raise
    
# OPENAI POLL RUN
def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    debug_print(f"Iniciando run para thread {thread.id[:8]}...")
    try:
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )
        debug_print(f"Run finalizado com status: {run.status}")
        return run
    except Exception as e:
        debug_print(f"Erro no poll_run: {str(e)}")
        raise

# OPENAI GET LATEST ASSISTANT MESSAGE
def get_latest_assistant_message():
    """Retorna a mensagem do assistente na posição [0] da thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

def get_assistant_response(user_query: str):
    """
    Função genérica para enviar uma consulta ao assistente e obter sua resposta.
    Retorna o conteúdo da resposta ou None em caso de erro.
    """
    debug_print(f"Solicitando resposta para query: '{user_query[:50]}...'")
    try:
        send_user_message(user_query)
        run = poll_run()
        if run.status == 'completed':
            last_message = get_latest_assistant_message()
            if not last_message:
                debug_print("Nenhuma mensagem de assistente recebida.")
                return None
            debug_print("Resposta do assistente recebida com sucesso")
            return last_message
        else:
            debug_print(f"Run status não é 'completed': {run.status}")
            return None
    except Exception as e:
        debug_print(f"Erro ao obter resposta do assistente: {str(e)}")
        return None

# EXTRAI SQL DO ASSISTENTE
def extract_sql_from_message(message) -> str:
    """Extrai e limpa o SQL do conteúdo da mensagem do assistente."""
    debug_print("Extraindo SQL da mensagem do assistente")
    try:
        blocks = message.content if isinstance(message.content, list) else [message.content]
        sql_parts = []
        for block in blocks:
            if isinstance(block, dict) and "text" in block:
                sql_parts.append(block["text"])
            elif hasattr(block, "text") and hasattr(block.text, "value"):
                sql_parts.append(block.text.value)
            else:
                sql_parts.append(str(block))
        sql_query = " ".join(sql_parts)
        clean_sql = " ".join(sql_query.replace("\n", " ").split())
        debug_print(f"SQL extraído: '{clean_sql[:100]}...'")
        return clean_sql
    except Exception as e:
        debug_print(f"Erro ao extrair SQL: {str(e)}")
        return ""

## GERA SQL A PARTIR DE CONSULTA EM LINGUAGEM NATURAL
def generate_sql_from_nl(nl_query: str) -> str:
    """
    Converte uma consulta em linguagem natural em um comando SQL.
    Utiliza a função genérica get_assistant_response e extrai o SQL.
    """
    assistant_message = get_assistant_response(nl_query)
    if assistant_message:
        return extract_sql_from_message(assistant_message)
    return None

def execute_sql_query(sql_query):
    """Executa a consulta SQL no banco de dados Supabase PostgreSQL"""
    debug_print(f"Executando SQL: '{sql_query[:100]}...'")
    try:
        # Verificar se o SQL começa com "Error:"
        if sql_query.startswith("Error:"):
            debug_print(f"SQL inválido detectado: {sql_query}")
            return pd.DataFrame()  # Retornar DataFrame vazio
            
        results = db.execute_query(sql_query)
        if results is None:
            debug_print("Erro ao executar consulta no banco")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        debug_print(f"SQL executado com sucesso. Linhas retornadas: {len(df)}")
        return df
    except Exception as e:
        debug_print(f"Erro ao executar consulta: {e}")
        return pd.DataFrame()

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "GvG Supabase Reports v0"

# Define styles
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
    "overflow-y": "auto"
}

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

# Layout
app.layout = html.Div([
    # Sidebar
    html.Div([
        html.H2("GvG Reports", className="display-4"),
        html.Hr(),
        html.P("Sistema de Relatórios PNCP com Supabase PostgreSQL", className="lead"),
        
        html.H5("Consulta SQL"),
        dcc.Textarea(
            id='sql-input',
            placeholder='Digite sua consulta em linguagem natural...',
            style={'width': '100%', 'height': 150, 'margin-bottom': '10px'}
        ),
        
        html.Button(
            'Gerar SQL',
            id='generate-sql-btn',
            n_clicks=0,
            className='btn btn-primary',
            style={'width': '100%', 'margin-bottom': '10px'}
        ),
        
        html.Button(
            'Executar Query',
            id='execute-query-btn',
            n_clicks=0,
            className='btn btn-success',
            style={'width': '100%', 'margin-bottom': '10px'}
        ),
        
        html.Button(
            'Limpar',
            id='clear-btn',
            n_clicks=0,
            className='btn btn-secondary',
            style={'width': '100%', 'margin-bottom': '20px'}
        ),
        
        html.Hr(),
        
        html.H5("Configurações"),
        dcc.Checklist(
            id='options-checklist',
            options=[
                {'label': 'Mostrar SQL Gerado', 'value': 'show_sql'},
                {'label': 'Auto-executar', 'value': 'auto_execute'},
                {'label': 'Visualização Automática', 'value': 'auto_viz'}
            ],
            value=['show_sql']
        ),
        
        html.Hr(),
        
        html.H5("Estatísticas"),
        html.Div(id='stats-display')
        
    ], style=SIDEBAR_STYLE),
    
    # Main content
    html.Div([
        # Header
        html.Div([
            html.H1("Relatórios PNCP - Supabase PostgreSQL", className="h3 mb-3 text-gray-800"),
            html.P("Sistema integrado com OpenAI Assistant para consultas inteligentes", className="mb-4")
        ]),
        
        # Status alerts
        html.Div(id='status-alerts'),
        
        # SQL Generated Section
        html.Div([
            html.H4("SQL Gerado"),
            dcc.Textarea(
                id='generated-sql',
                style={'width': '100%', 'height': 150, 'font-family': 'monospace'},
                readOnly=True
            )
        ], id='sql-section', style={'display': 'none', 'margin-bottom': '20px'}),
        
        # Results Section
        html.Div([
            html.H4("Resultados da Consulta"),
            html.Div(id='query-results'),
            html.Div(id='results-stats', style={'margin-top': '10px'})
        ], id='results-section', style={'display': 'none', 'margin-bottom': '20px'}),
        
        # Visualization Section
        html.Div([
            html.H4("Visualizações"),
            html.Div([
                html.Label("Tipo de Gráfico:"),
                dcc.Dropdown(
                    id='chart-type',
                    options=[
                        {'label': 'Barra', 'value': 'bar'},
                        {'label': 'Linha', 'value': 'line'},
                        {'label': 'Pizza', 'value': 'pie'},
                        {'label': 'Scatter', 'value': 'scatter'},
                        {'label': 'Histograma', 'value': 'histogram'},
                        {'label': 'Box Plot', 'value': 'box'}
                    ],
                    value='bar',
                    style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}
                ),
                html.Label("Coluna X:"),
                dcc.Dropdown(
                    id='x-column',
                    style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}
                ),
                html.Label("Coluna Y:"),
                dcc.Dropdown(
                    id='y-column',
                    style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}
                ),
                html.Button(
                    'Gerar Gráfico',
                    id='create-chart-btn',
                    n_clicks=0,
                    className='btn btn-info',
                    style={'margin-left': '20px'}
                )
            ], style={'margin-bottom': '20px'}),
            
            dcc.Graph(id='data-visualization')
        ], id='viz-section', style={'display': 'none', 'margin-bottom': '20px'}),
        
        # Export Section
        html.Div([
            html.H4("Exportar Dados"),
            html.Button(
                'Download CSV',
                id='download-csv-btn',
                n_clicks=0,
                className='btn btn-outline-primary',
                style={'margin-right': '10px'}
            ),
            html.Button(
                'Download JSON',
                id='download-json-btn',
                n_clicks=0,
                className='btn btn-outline-primary'
            ),
            dcc.Download(id="download-data")
        ], id='export-section', style={'display': 'none'})
        
    ], style=CONTENT_STYLE),
    
    # Hidden divs to store data
    html.Div(id='current-data', style={'display': 'none'}),
    html.Div(id='thread-id', style={'display': 'none'})
])

# Substituir os dados de exemplo por estruturas vazias - IDENTICO AO ORIGINAL
initial_conversation = []  # Lista vazia em vez de exemplo predefinido
initial_results = []       # Lista vazia em vez de exemplo predefinido

# Store for conversation history, query results and counter - IDENTICO AO ORIGINAL
conversation_store = []
results_store = []
next_message_counter = 1

# Callbacks - IDENTICOS AO gvg_CL_reports_v3.py

@app.callback(
    [Output('query-results', 'children'),
     Output('current-data', 'children'),
     Output('results-section', 'style'),
     Output('results-stats', 'children'),
     Output('x-column', 'options'),
     Output('y-column', 'options')],
    [Input('execute-query-btn', 'n_clicks')],
    [State('generated-sql', 'value')]
)
def execute_query(n_clicks, sql_query):
    if n_clicks == 0 or not sql_query:
        raise PreventUpdate
    
    try:
        # Execute query
        results = db.execute_query(sql_query)
        
        if results is None:
            return (
                html.Div("Erro ao executar a consulta.", className="alert alert-danger"),
                None,
                {'display': 'block', 'margin-bottom': '20px'},
                "",
                [],
                []
            )
        
        if not results:
            return (
                html.Div("Consulta executada com sucesso, mas não retornou resultados.", className="alert alert-info"),
                None,
                {'display': 'block', 'margin-bottom': '20px'},
                "",
                [],
                []
            )
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Create data table
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{"name": i, "id": i} for i in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': '#f1f1f1', 'fontWeight': 'bold'},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
        
        # Stats
        stats = html.Div([
            html.P(f"Registros encontrados: {len(df)}"),
            html.P(f"Colunas: {len(df.columns)}")
        ])
        
        # Column options for charts
        column_options = [{'label': col, 'value': col} for col in df.columns]
        
        return (
            table,
            df.to_json(orient='records'),
            {'display': 'block', 'margin-bottom': '20px'},
            stats,
            column_options,
            column_options
        )
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return (
            html.Div(f"Erro ao executar consulta: {str(e)}", className="alert alert-danger"),
            None,
            {'display': 'block', 'margin-bottom': '20px'},
            "",
            [],
            []
        )

@app.callback(
    [Output('data-visualization', 'figure'),
     Output('viz-section', 'style')],
    [Input('create-chart-btn', 'n_clicks')],
    [State('current-data', 'children'),
     State('chart-type', 'value'),
     State('x-column', 'value'),
     State('y-column', 'value')]
)
def create_visualization(n_clicks, data_json, chart_type, x_col, y_col):
    if n_clicks == 0 or not data_json:
        raise PreventUpdate
    
    try:
        df = pd.read_json(data_json, orient='records')
        
        if chart_type == 'bar':
            fig = px.bar(df, x=x_col, y=y_col)
        elif chart_type == 'line':
            fig = px.line(df, x=x_col, y=y_col)
        elif chart_type == 'pie':
            fig = px.pie(df, names=x_col, values=y_col)
        elif chart_type == 'scatter':
            fig = px.scatter(df, x=x_col, y=y_col)
        elif chart_type == 'histogram':
            fig = px.histogram(df, x=x_col)
        elif chart_type == 'box':
            fig = px.box(df, y=y_col)
        else:
            fig = px.bar(df, x=x_col, y=y_col)
        
        fig.update_layout(
            title=f"{chart_type.title()} Chart",
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        
        return fig, {'display': 'block', 'margin-bottom': '20px'}
        
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        return {}, {'display': 'none'}

@app.callback(
    [Output('viz-section', 'style', allow_duplicate=True),
     Output('export-section', 'style')],
    [Input('current-data', 'children')],
    [State('options-checklist', 'value')],
    prevent_initial_call=True
)
def show_sections(data_json, options):
    if not data_json:
        return {'display': 'none'}, {'display': 'none'}
    
    viz_style = {'display': 'block', 'margin-bottom': '20px'} if 'auto_viz' in options else {'display': 'none'}
    export_style = {'display': 'block', 'margin-bottom': '20px'}
    
    return viz_style, export_style

@app.callback(
    Output("download-data", "data"),
    [Input("download-csv-btn", "n_clicks"),
     Input("download-json-btn", "n_clicks")],
    [State('current-data', 'children')],
    prevent_initial_call=True
)
def download_data(csv_clicks, json_clicks, data_json):
    if not data_json:
        raise PreventUpdate
    
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    df = pd.read_json(data_json, orient='records')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if button_id == "download-csv-btn":
        return dcc.send_data_frame(df.to_csv, f"pncp_data_{timestamp}.csv", index=False)
    elif button_id == "download-json-btn":
        return dcc.send_data_frame(df.to_json, f"pncp_data_{timestamp}.json", orient='records')

@app.callback(
    [Output('sql-input', 'value'),
     Output('generated-sql', 'value', allow_duplicate=True),
     Output('query-results', 'children', allow_duplicate=True),
     Output('current-data', 'children', allow_duplicate=True),
     Output('data-visualization', 'figure', allow_duplicate=True)],
    [Input('clear-btn', 'n_clicks')],
    prevent_initial_call=True
)
def clear_all(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate
    
    return "", "", "", "", {}

@app.callback(
    Output('stats-display', 'children'),
    [Input('current-data', 'children')]
)
def update_stats(data_json):
    if not data_json:
        return html.P("Nenhum dado carregado")
    
    df = pd.read_json(data_json, orient='records')
    
    return html.Div([
        html.P(f"Registros: {len(df)}"),
        html.P(f"Colunas: {len(df.columns)}"),
        html.P(f"Memória: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    ])

# Auto-execute functionality
@app.callback(
    Output('execute-query-btn', 'n_clicks'),
    [Input('generated-sql', 'value')],
    [State('options-checklist', 'value'),
     State('execute-query-btn', 'n_clicks')]
)
def auto_execute(sql_value, options, current_clicks):
    if 'auto_execute' in options and sql_value:
        return current_clicks + 1
    raise PreventUpdate

if __name__ == '__main__':
    # Test database connection on startup
    if db.connect():
        logger.info("Successfully connected to Supabase PostgreSQL")
        db.close()
    else:
        logger.error("Failed to connect to Supabase PostgreSQL")
    
    app.run_server(debug=True, host='127.0.0.1', port=8055)
