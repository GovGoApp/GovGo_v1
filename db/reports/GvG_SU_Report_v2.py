## GvG Reports v3 using Supabase - v2 with SQL History
# Adaptado do sistema Claude para usar PostgreSQL/Supabase
# v2: Adicionado histórico de SQLs
#  
import os
import pandas as pd
import uuid
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from datetime import datetime
import json
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
import traceback
import io
import dash.dependencies
import io
from openai import OpenAI

# Variável de controle para debug
DEBUG = False

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Carregar configurações do DB diretamente do arquivo .env
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
debug_print(f"Caminho do .env: {env_path}")
debug_print(f"Arquivo .env existe: {os.path.exists(env_path)}")

config = {}
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value


# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
LOGO_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#LOGO\\LOGO_TEXTO_GOvGO_TRIM_v3.png"
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")

if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

# OpenAI configuration
api_key = config.get('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)
thread = client.beta.threads.create()

# Assistant ID - PNCP_SQL_SUPABASE_v1_2 do .env
assistant_id = config.get('OPENAI_ASSISTANT_SQL_SUPABASE_v1')
model_id = "gpt-4o"

# Supabase Database Configuration
DB_CONFIG = {
    'host': config.get('SUPABASE_HOST'),
    'port': config.get('SUPABASE_PORT'),
    'dbname': config.get('SUPABASE_DBNAME'),
    'user': config.get('SUPABASE_USER'),
    'password': config.get('SUPABASE_PASSWORD')
}

# Debug das configurações carregadas
debug_print(f"Configurações carregadas: {len(config)} itens")
debug_print(f"DB Host: {DB_CONFIG['host']}")
debug_print(f"DB User: {DB_CONFIG['user']}")
debug_print(f"Assistant ID: {assistant_id}")

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'GOvGO'
app.title = 'SQL Reports v2'

# Define custom styles
styles = {
    'container': {
        'display': 'flex',
        'height': 'calc(100vh - 60px)',  # Altura total da janela menos o cabeçalho
        'width': '100%',
        'marginTop': '60px',  # Mover a margem para o estilo base
         #'backgroundColor': '#FFFFFF',  # Adicionado: fundo branco para o container principal
        'padding': '5px'  # Adicionado: padding para o container
    },
    'left_panel': {
        'width': '40%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',  # Adicionado: margem externa
        'borderRadius': '15px',  # Adicionado: bordas arredondadas
        'overflowY': 'auto',  # Mantém o scroll apenas quando necessário
        'display': 'flex',
        'flexDirection': 'column',
        'height': 'calc(100vh - 100px)'  # Ajustado para considerar margens e paddings extras
    },
    'right_panel': {
        'width': '60%',
        'backgroundColor': '#E0EAF9',  # Alterado: agora igual ao left_panel
        'padding': '10px',
        'margin': '5px',  # Adicionado: margem externa
        'borderRadius': '15px',  # Adicionado: bordas arredondadas
        'overflowY': 'auto',
        'height': 'calc(100vh - 100px)'  # Ajustado para considerar margens e paddings extras
    },
    'chat_container': {
        'flex': '1',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'marginBottom': '10px'
    },
    'user_message': {
        'alignSelf': 'flex-end',
        'backgroundColor': '#B9D1FF',  # Novo: azul claro
        'color': '#003A70',            # Novo: azul escuro
        'borderRadius': '15px',
        'padding': '12px',
        'maxWidth': '80%',
        'marginBottom': '10px',
        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)',
        'position': 'relative',
        'wordWrap': 'break-word',      # Quebrar palavras longas
        'overflowWrap': 'break-word',  # Quebra para navegadores modernos
        'wordBreak': 'break-word',     # Força quebra em caracteres se necessário
        'fontWeight': 'normal'         # Novo: remover negrito
    },
    'sql_message': {
        'alignSelf': 'flex-start',
        'backgroundColor': '#52ACFF',  # Alterado: azul médio
        'color': '#FFFFFF',            # Novo: texto branco
        'borderRadius': '15px',
        'padding': '10px',
        'maxWidth': '80%',
        'marginBottom': '10px',
        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)',
        'fontFamily': 'Consolas, monospace',
        'fontSize': '12px',
        'position': 'relative',
        'wordWrap': 'break-word',      # Quebrar palavras longas
        'overflowWrap': 'break-word',  # Quebra para navegadores modernos
        'wordBreak': 'break-word',     # Força quebra em caracteres se necessário
        'fontWeight': 'normal'         # Novo: remover negrito
    },
    'message_number': {
        'position': 'absolute',
        'top': '-10px',
        'left': '-10px',
        'backgroundColor': '#FF5722',
        'color': 'white',
        'borderRadius': '50%',
        'width': '24px',
        'height': '24px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'fontSize': '12px',
        'fontWeight': 'bold'
    },
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'alignItems': 'center',
        'marginTop': 'auto'
    },
    'input_field': {
        'flex': '1',
        'border': 'none',
        'outline': 'none',
        'padding': '8px',
        'backgroundColor': 'transparent'
    },
    'submit_button': {
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
        'marginBottom': '20px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
        'position': 'relative'
    },
    'action_buttons': {
        'display': 'flex',
        'justifyContent': 'flex-end',
        'marginTop': '10px'
    },
    'action_button': {
        'marginLeft': '5px',
        'width': '32px',
        'height': '32px',
        'borderRadius': '50%',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer',
        'border': 'none'
    },
    'download_button': {
        'backgroundColor': '#4CAF50',
        'color': 'white'
    },
    'cloud_button': {
        'backgroundColor': '#2196F3',
        'color': 'white'
    },
    'share_button': {
        'backgroundColor': '#9C27B0',
        'color': 'white'
    },
    'logo': {
        'marginBottom': '20px',
        'maxWidth': '150px'
    },
    'loading_container': {
        'display': 'flex',
        'justifyContent': 'center',
        'padding': '20px'
    },
    'status_message': {
        'margin': '10px',
        'color': '#555',
        'fontSize': '14px'
    },
    # Novos estilos para o histórico
    'history_modal': {
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'width': '100%',
        'height': '100%',
        'backgroundColor': 'rgba(0, 0, 0, 0.6)',
        'justifyContent': 'center',
        'alignItems': 'center',
        'zIndex': 2000,
        'backdropFilter': 'blur(2px)'
    },
    'history_content': {
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'padding': '25px',
        'width': '85%',
        'maxWidth': '900px',
        'maxHeight': '85%',
        'overflowY': 'auto',
        'boxShadow': '0 10px 30px rgba(0,0,0,0.3)',
        'animation': 'fadeIn 0.3s ease'
    },
    'history_header': {
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'marginBottom': '25px',
        'borderBottom': '2px solid #e0e0e0',
        'paddingBottom': '15px'
    },
    'history_item': {
        'backgroundColor': '#f8f9fa',
        'border': '1px solid #dee2e6',
        'borderRadius': '10px',
        'padding': '18px',
        'marginBottom': '12px',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    },
    'history_item_hover': {
        'backgroundColor': '#e3f2fd',
        'borderColor': '#2196F3',
        'transform': 'translateY(-2px)',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.15)'
    },
    'history_sql': {
        'fontFamily': 'Consolas, "Courier New", monospace',
        'fontSize': '11px',
        'backgroundColor': '#f1f3f4',
        'padding': '10px',
        'borderRadius': '6px',
        'marginTop': '10px',
        'wordBreak': 'break-all',
        'border': '1px solid #e0e0e0',
        'color': '#555'
    },
    'close_button': {
        'backgroundColor': '#dc3545',
        'color': 'white',
        'border': 'none',
        'borderRadius': '50%',
        'width': '36px',
        'height': '36px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer',
        'transition': 'all 0.2s ease',
        'fontSize': '16px'
    }
}

# Adicionar novos estilos para a numeração
styles['message_number_sql'] = {
    'position': 'absolute',
    'right': '-30px',  # À direita do balão
    'top': '50%',      # Na altura do meio
    'transform': 'translateY(-50%)',  # Centralizado verticalmente
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
    'fontfamily': 'Arial, sans-serif'  # Fonte padrão
}

styles['result_number'] = {
    'position': 'absolute',
    'bottom': '10px',  # Parte inferior
    'left': '10px',    # Lado esquerdo
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
    'fontfamily': 'Arial, sans-serif'  # Fonte padrão
}

# Store for conversation history, query results, counter and SQL history
conversation_store = []
results_store = []
next_message_counter = 1
sql_history_store = []  # Nova store para histórico de SQL

# Função para carregar histórico do arquivo JSON
def load_sql_history():
    history_file = os.path.join(os.path.dirname(__file__), 'sql_history.json')
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        debug_print(f"Erro ao carregar histórico: {e}")
    return []

# Função para salvar histórico no arquivo JSON
def save_sql_history(sql_history):
    history_file = os.path.join(os.path.dirname(__file__), 'sql_history.json')
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(sql_history, f, indent=2, ensure_ascii=False)
        debug_print(f"Histórico salvo em: {history_file}")
    except Exception as e:
        debug_print(f"Erro ao salvar histórico: {e}")

# Assistant functions
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
        
        # Remover marcações de código markdown
        sql_query = sql_query.replace("```sql", "").replace("```", "")
        
        # Limpar quebras de linha e espaços extras
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
    debug_print(f"Executando SQL: '{sql_query}...'")
    try:
        # Verificar se o SQL começa com "Error:"
        if sql_query.startswith("Error:"):
            debug_print(f"SQL inválido detectado: {sql_query}")
            return pd.DataFrame()  # Retornar DataFrame vazio
            
        # Conectar ao PostgreSQL/Supabase
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Executar query e obter resultados
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        debug_print(f"SQL executado com sucesso. Linhas retornadas: {len(df)}")
        return df
    except Exception as e:
        debug_print(f"Erro ao executar consulta: {e}")
        debug_print(traceback.format_exc())
        # Criar DataFrame especial para indicar erro
        error_df = pd.DataFrame({'__ERROR__': [str(e)]})
        return error_df

# Substituir os dados de exemplo por estruturas vazias
initial_conversation = []  # Lista vazia em vez de exemplo predefinido
initial_results = []       # Lista vazia em vez de exemplo predefinido
initial_sql_history = load_sql_history()   # Carregar histórico do arquivo JSON

# Substituir a definição de logo existente com:
import base64

def b64_image(image_path):
    """Converte uma imagem local para string base64 para uso no Dash"""
    try:
        with open(image_path, 'rb') as f:
            image = f.read()
        return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')
    except Exception as e:
        print(f"Erro ao carregar imagem: {e}")
        return ''


# Componente de logo usando a imagem local
logo = html.Div(
    html.Img(
        src=b64_image(LOGO_PATH),
        style=styles['logo']
    )
)

chat_container = html.Div(id='chat-container', style=styles['chat_container'])

input_container = html.Div([
    dcc.Input(
        id='query-input',
        type='text',
        placeholder='Faça uma pergunta...',
        style=styles['input_field']
    ),
    html.Button(
        html.I(className="fas fa-arrow-right"),
        id='submit-button',
        style=styles['submit_button']
    )
], style=styles['input_container'])

left_panel = html.Div([
    chat_container,
    input_container
], style=styles['left_panel'])

results_container = html.Div(id='results-container', style=styles['right_panel'])

# Modal para histórico de SQL
history_modal = html.Div([
    html.Div([
        html.Div([
            html.H4("📊 Histórico de Consultas SQL", style={
                'margin': 0, 
                'color': '#003A70',
                'fontSize': '20px',
                'fontWeight': 'bold'
            }),
            html.Div([
                html.Button(
                    html.I(className="fas fa-trash"),
                    id='clear-history-button',
                    style={
                        'backgroundColor': '#ffc107',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '50%',
                        'width': '32px',
                        'height': '32px',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'cursor': 'pointer',
                        'marginRight': '10px'
                    },
                    title="Limpar histórico"
                ),
                html.Button(
                    html.I(className="fas fa-times"),
                    id='close-history-modal',
                    style=styles['close_button'],
                    title="Fechar"
                )
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style=styles['history_header']),
        html.P("Clique em qualquer consulta para reutilizá-la:", style={
            'color': '#666', 
            'marginBottom': '20px',
            'fontSize': '14px',
            'textAlign': 'center'
        }),
        html.Div(id='history-list', children=[], style={'minHeight': '100px'})
    ], style=styles['history_content'])
], id='history-modal', style={'display': 'none', **styles['history_modal']})

# Novo componente de cabeçalho com cores atualizadas
header = html.Div([
    # Logo à esquerda com título
    html.Div([
        html.Img(src=b64_image(LOGO_PATH), style={'height': '40px'}),
        html.H4("Supabase Reports v2", style={'marginLeft': '15px', 'color': '#003A70'})
    ], style={'display': 'flex', 'alignItems': 'center'}),
    
    # Ícones à direita - com funcionalidade no histórico
    html.Div([
        html.I(
            className="fas fa-list", 
            id='history-button',
            style={
                'fontSize': '20px', 
                'marginRight': '15px', 
                'cursor': 'pointer',
                'color': '#FF5722'
            },
            title="Histórico de SQLs"
        ),
        html.I(className="fas fa-user-circle", style={
            'fontSize': '24px', 
            'cursor': 'pointer',
            'color': '#FF5722'
        })
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

# Ajustar o layout principal para incluir o cabeçalho e modal
app.layout = html.Div([
    dcc.Store(id='conversation-store', data=initial_conversation),
    dcc.Store(id='results-store', data=initial_results),
    dcc.Store(id='counter-store', data=1),
    dcc.Store(id='temp-df-store', data={}),
    dcc.Store(id='processing-state', data=False),  # Valor booleano literal
    dcc.Store(id='sql-history-store', data=initial_sql_history),  # Nova store
    
    # Adicionar o loading indicator aqui
    html.Div(id='loading-indicator', style={'display': 'none'}),
    
    # Modal do histórico
    history_modal,
    
    # Novo cabeçalho
    header,
    
    # Container principal ajustado para ficar abaixo do cabeçalho
    html.Div([
        left_panel,
        results_container,
        html.Div([
            dcc.Download(id="download-dataframe-xlsx"),
        ], style={"display": "none"}),
    ], style=styles['container']),
])

# Callback para controlar exibição do modal de histórico
@app.callback(
    Output('history-modal', 'style'),
    Input('history-button', 'n_clicks'),
    Input('close-history-modal', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_history_modal(history_clicks, close_clicks):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'history-button':
        # Mostrar modal
        return {'display': 'flex', **styles['history_modal']}
    elif trigger_id == 'close-history-modal':
        # Esconder modal
        return {'display': 'none'}
    
    # Por padrão, manter escondido
    return {'display': 'none'}

# Callback para renderizar lista do histórico
@app.callback(
    Output('history-list', 'children'),
    Input('history-modal', 'style'),
    State('sql-history-store', 'data'),
    prevent_initial_call=True
)
def render_history_list(modal_style, sql_history):
    # Só renderizar quando modal estiver visível
    if not modal_style or modal_style.get('display') != 'flex':
        raise PreventUpdate
    
    if not sql_history:
        return [html.Div("📝 Nenhum histórico encontrado.", style={'textAlign': 'center', 'color': '#666', 'padding': '20px', 'fontSize': '16px'})]
    
    history_items = []
    for i, item in enumerate(reversed(sql_history)):  # Mais recentes primeiro
        history_items.append(
            html.Div([
                html.Div([
                    html.Strong(f"#{len(sql_history) - i}: ", style={'color': '#FF5722'}),
                    html.Span(item['question'][:100] + ('...' if len(item['question']) > 100 else ''), style={'fontSize': '14px'})
                ], style={'marginBottom': '8px'}),
                html.Div(
                    item['sql'][:200] + ('...' if len(item['sql']) > 200 else ''),
                    style={**styles['history_sql'], 'fontSize': '11px', 'color': '#555'}
                ),
                html.Small(f"📅 {item['timestamp']}", style={'color': '#888', 'fontSize': '12px'})
            ],
            id={'type': 'history-item', 'index': i},
            style={
                **styles['history_item'],
                'transition': 'all 0.2s ease',
                'border': '1px solid #e0e0e0'
            },
            n_clicks=0
        ))
    
    return history_items

# Callback para quando clicar em item do histórico
@app.callback(
    Output('query-input', 'value', allow_duplicate=True),
    Output('history-modal', 'style', allow_duplicate=True),
    Input({'type': 'history-item', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('sql-history-store', 'data'),
    prevent_initial_call=True
)
def select_from_history(n_clicks_list, sql_history):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate
    
    # Encontrar qual item foi clicado
    triggered_id = ctx.triggered[0]['prop_id']
    if '.n_clicks' in triggered_id:
        # Extrair o índice do item clicado
        import json
        button_info = json.loads(triggered_id.split('.')[0])
        index = button_info['index']
        
        # Obter a pergunta original do histórico (lembrando que está reversed)
        if sql_history and index < len(sql_history):
            original_question = sql_history[-(index + 1)]['question']  # Ajuste para reversed
            # Retornar a pergunta para o input e fechar o modal
            return original_question, {'display': 'none'}
    
    raise PreventUpdate

# Callback para limpar histórico
@app.callback(
    Output('sql-history-store', 'data', allow_duplicate=True),
    Input('clear-history-button', 'n_clicks'),
    prevent_initial_call=True
)
def clear_history(n_clicks):
    if n_clicks:
        # Limpar arquivo JSON
        save_sql_history([])
        return []
    raise PreventUpdate

# Callback adicional para fechar modal clicando no fundo
@app.callback(
    Output('history-modal', 'style', allow_duplicate=True),
    Input('history-modal', 'n_clicks'),
    prevent_initial_call=True
)
def close_modal_on_background_click(n_clicks):
    if n_clicks:
        return {'display': 'none'}
    raise PreventUpdate

# Modificar o callback render_chat
@app.callback(
    Output('chat-container', 'children'),
    Input('conversation-store', 'data')
)
def render_chat(conversation):
    if not conversation:
        return []
    
    chat_elements = []
    
    for message in conversation:
        if message['type'] == 'user':
            chat_elements.append(html.Div([
                html.Div(
                    message['text'],
                    style={'fontWeight': 'normal', 'marginBottom': '5px'}  # Removido negrito
                ),
            ], style=styles['user_message']))
            
            # Add SQL response if available
            if 'sql' in message and message['sql']:
                chat_elements.append(html.Div([
                    html.Div(message['sql']),
                    html.Div(
                        message['id'],
                        style=styles['message_number_sql']
                    )
                ], style=styles['sql_message']))
    
    return chat_elements


@app.callback(
    Output('results-container', 'children'),
    Input('results-store', 'data')
)
def render_results(results):
    if not results:
        return []
    
    result_elements = []
    
    for result in results:
        try:
            debug_print(f"Processando resultado {result['id']}: data = {result['data']}")
            
            if isinstance(result['data'], list):
                df_data = result['data']
                debug_print(f"Resultado {result['id']}: dados já em lista, len = {len(df_data)}")
            else:
                debug_print(f"Resultado {result['id']}: convertendo dict para records")
                df_data = pd.DataFrame(result['data']).to_dict('records')
                debug_print(f"Resultado {result['id']}: após conversão, len = {len(df_data)}")
            
            # Debug: verificar dados recebidos
            debug_print(f"Resultado {result['id']}: df_data = {df_data}, len = {len(df_data) if df_data else 'None'}")
                
            # Verificar se é um erro SQL
            if df_data and len(df_data) > 0 and '__ERROR__' in df_data[0]:
                error_message = df_data[0]['__ERROR__']
                debug_print(f"Resultado {result['id']}: Erro detectado - {error_message[:100]}...")
                result_elements.append(html.Div([
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle", style={
                            'fontSize': '28px',
                            'color': '#dc3545',
                            'marginRight': '15px'
                        }),
                        html.Div([
                            html.H5("❌ Erro na Execução SQL", style={
                                'color': '#dc3545',
                                'marginBottom': '10px',
                                'fontWeight': 'bold'
                            }),
                            html.Pre(error_message, style={
                                'backgroundColor': '#f8f9fa',
                                'border': '1px solid #dee2e6',
                                'borderRadius': '5px',
                                'padding': '15px',
                                'fontSize': '12px',
                                'color': '#495057',
                                'whiteSpace': 'pre-wrap',
                                'wordBreak': 'break-word',
                                'maxHeight': '200px',
                                'overflowY': 'auto'
                            })
                        ], style={'flex': '1'})
                    ], style={
                        'display': 'flex',
                        'alignItems': 'flex-start',
                        'padding': '20px',
                        'backgroundColor': '#f8d7da',
                        'border': '1px solid #f5c6cb',
                        'borderRadius': '8px',
                        'margin': '10px 0'
                    }),
                    html.Div(
                        result['id'],
                        style=styles['result_number']
                    )
                ], style={
                    **styles['result_card'],
                    'overflow': 'hidden'
                }))
            # Verificar se há dados ou se retornou 0 linhas - melhorada a verificação
            elif df_data and len(df_data) > 0:
                debug_print(f"Resultado {result['id']}: Mostrando tabela com {len(df_data)} linhas")
                result_elements.append(html.Div([
                    dash_table.DataTable(
                        data=df_data,
                        columns=[{'name': k, 'id': k} for k in df_data[0].keys()] if df_data else [],
                        page_size=10,
                        style_table={
                            'overflowX': 'auto',
                            'width': '100%'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'maxWidth': '100px',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'padding': '6px',  # Reduzido para texto menor
                            'fontSize': '12px'  # Texto menor para itens
                        },
                        style_header={
                            'backgroundColor': '#f8f9fa',
                            'fontWeight': 'bold',  # Manter negrito no cabeçalho
                            'border': '1px solid #ddd',
                            'textAlign': 'left',
                            'fontSize': '13px'  # Texto levemente menor que o default
                        },
                        
                        tooltip_duration=None,
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}
                        ],
                        style_data={  
                            'fontWeight': 'normal'
                        },
                        css=[{
                            'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table', 
                            'rule': 'font-size: 11px !important;'
                        }]
                    ),
                    html.Div([
                        html.Button(
                            html.I(className="fas fa-download"),
                            id={'type': 'download-btn', 'index': result['id']},
                            style={**styles['action_button'], **styles['download_button']},
                            title="Baixar como Excel"
                        ),
                        #html.Button(
                        #    html.I(className="fas fa-cloud-upload-alt"),
                        #    style={**styles['action_button'], **styles['cloud_button']},
                        #   title="Salvar na nuvem"
                        #),
                        #html.Button(
                        #    html.I(className="fas fa-share-alt"),
                        #    style={**styles['action_button'], **styles['share_button']},
                        #    title="Compartilhar"
                        #),
                    ], style=styles['action_buttons']),
                    html.Div(
                        result['id'],
                        style=styles['result_number']
                    )
                ], style={
                    **styles['result_card'],
                    'overflow': 'hidden'
                }))
            else:
                # Mostrar card quando não há dados retornados
                debug_print(f"Resultado {result['id']}: Mostrando card para 0 linhas")
                result_elements.append(html.Div([
                    html.Div([
                        html.I(className="fas fa-info-circle", style={
                            'fontSize': '24px',
                            'color': '#17a2b8',
                            'marginRight': '10px'
                        }),
                        html.Span("SQL executado com sucesso. Linhas retornadas: 0", style={
                            'fontSize': '16px',
                            'color': '#495057'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'padding': '40px 20px',
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6',
                        'borderRadius': '8px',
                        'margin': '20px 0'
                    }),
                    html.Div(
                        result['id'],
                        style=styles['result_number']
                    )
                ], style={
                    **styles['result_card'],
                    'overflow': 'hidden'
                }))
        except Exception as e:
            print(f"Erro ao renderizar resultado {result['id']}: {e}")
    
    return result_elements

# Corrigir o callback set_processing_state
@app.callback(
    Output('processing-state', 'data'),
    Input('submit-button', 'n_clicks'),
    Input('query-input', 'n_submit'),
    State('query-input', 'value'),
    State('processing-state', 'data'),
    prevent_initial_call=True,  # Evitar chamada inicial
)
def set_processing_state(n_clicks, n_submit, query, is_processing):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    debug_print(f"set_processing_state acionado por: {trigger_id}")
    debug_print(f"Estado atual de processamento: {is_processing}")
    debug_print(f"Query: '{query}'")
    
    # Se já estiver processando ou query vazia
    if is_processing or not query:
        debug_print("Ignorando - já está processando ou query vazia")
        raise PreventUpdate
        
    debug_print("Iniciando processamento...")
    return True

# Segundo callback reage à mudança do estado de processamento e executa a consulta
@app.callback(
    Output('conversation-store', 'data'),
    Output('temp-df-store', 'data'),
    Output('counter-store', 'data'),
    Output('processing-state', 'data', allow_duplicate=True),
    Output('sql-history-store', 'data'),  # Novo output para histórico
    Input('processing-state', 'data'),
    State('query-input', 'value'),
    State('conversation-store', 'data'),
    State('counter-store', 'data'),
    State('sql-history-store', 'data'),  # Novo state para histórico
    prevent_initial_call=True,
)
def process_query(is_processing, query, conversation, counter, sql_history):
    debug_print(f"process_query chamado. Processando: {is_processing}")
    
    if not is_processing:
        debug_print("Ignorando - não está no estado de processamento")
        raise PreventUpdate
        
    debug_print(f"Processando query #{counter}: '{query}'")
    message_counter = counter
    
    try:
        # Gerar SQL
        debug_print("Gerando SQL a partir da query...")
        sql_query = generate_sql_from_nl(query)
        
        if not sql_query:
            debug_print("SQL não gerado")
            sql_query = "Error: Could not generate SQL query"
            
            # Log da criação da mensagem
            debug_print("Criando mensagem de erro para SQL não gerado")
            new_message = {
                'id': str(message_counter),
                'type': 'user',
                'text': query,
                'sql': sql_query,
                'timestamp': datetime.now().isoformat()
            }
            
            updated_conversation = conversation + [new_message]
            next_counter = message_counter + 1
            debug_print("Finalizando processamento sem dados")
            return updated_conversation, {}, next_counter, False, sql_history
        
        # Executar SQL
        debug_print("Executando consulta SQL...")
        df = execute_sql_query(sql_query)
        df_dict = df.to_dict('list')
        debug_print(f"Colunas obtidas: {list(df_dict.keys() if df_dict else [])}")
        
        # Log da criação da mensagem
        debug_print("Criando nova mensagem com SQL gerado")
        new_message = {
            'id': str(message_counter),
            'type': 'user',
            'text': query,
            'sql': sql_query,
            'timestamp': datetime.now().isoformat()
        }
        
        updated_conversation = conversation + [new_message]
        next_counter = message_counter + 1
        
        # Adicionar ao histórico de SQL - NOVO
        if sql_history is None:
            sql_history = []
        
        new_history_item = {
            'id': str(message_counter),
            'question': query,
            'sql': sql_query,
            'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        updated_sql_history = sql_history + [new_history_item]
        debug_print(f"Adicionado ao histórico de SQL. Total: {len(updated_sql_history)}")
        
        # Salvar histórico no arquivo JSON
        save_sql_history(updated_sql_history)
        
        debug_print("Processamento concluído com sucesso")
        return updated_conversation, df_dict, next_counter, False, updated_sql_history
        
    except Exception as e:
        debug_print(f"ERRO no processamento: {str(e)}")
        import traceback
        debug_print(traceback.format_exc())
        
        # Log da criação da mensagem de erro
        debug_print("Criando mensagem com erro")
        error_message = {
            'id': str(message_counter),
            'type': 'user',
            'text': query,
            'sql': f"Erro: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }
        
        updated_conversation = conversation + [error_message]
        debug_print("Finalizando processamento com erro")
        return updated_conversation, {}, counter, False, sql_history or []

# Callback para atualização de resultados
def update_results(df_dict, results, counter):
    if not df_dict:
        debug_print("update_results: Sem dados para atualizar")
        raise PreventUpdate
        
    try:
        debug_print(f"Atualizando resultados para consulta #{counter-1}")
        
        # Verificar dados de entrada
        if results is None:
            debug_print("Inicializando lista de resultados vazia")
            results = []
            
        if not isinstance(results, list):
            debug_print("Erro: results não é uma lista válida")
            raise PreventUpdate
            
        # Criar novo resultado
        debug_print(f"Criando novo resultado com {len(df_dict.keys() if df_dict else [])} colunas")
        new_result = {
            'id': str(counter - 1),
            'data': df_dict,
            'timestamp': datetime.now().isoformat()
        }
        
        # Adicionar à lista
        updated_results = results + [new_result]
        debug_print(f"Lista de resultados atualizada. Total: {len(updated_results)}")
        
        return updated_results, ""
        
    except Exception as e:
        debug_print(f"Erro ao atualizar resultados: {str(e)}")
        import traceback
        debug_print(traceback.format_exc())
        return results, ""

# Callback para renderização dos resultados
def render_results(results):
    if not results:
        debug_print("render_results: Sem resultados para renderizar")
        return []
    
    debug_print(f"Renderizando {len(results)} resultados")
    result_elements = []
    
    for i, result in enumerate(results):
        try:
            debug_print(f"Processando resultado #{result['id']} ({i+1}/{len(results)})")
            
            # Verificando formato dos dados
            if isinstance(result['data'], list):
                debug_print("Dados em formato de lista")
                df_data = result['data']
            else:
                debug_print("Convertendo formato de dados para registros")
                df_data = pd.DataFrame(result['data']).to_dict('records')
                
            if df_data:
                debug_print(f"Registros: {len(df_data)}, Colunas: {len(df_data[0].keys()) if df_data else 0}")
                # Criar elemento de tabela (código existente)
                result_elements.append(html.Div([
                    # ... resto do código existente
                ]))
        except Exception as e:
            debug_print(f"Erro ao renderizar resultado {result['id']}: {str(e)}")
            import traceback
            debug_print(traceback.format_exc())
    
    debug_print(f"Renderização concluída: {len(result_elements)} elementos criados")
    return result_elements

# Callback para atualizar resultados após uma consulta
@app.callback(
    Output('results-store', 'data'),
    Output('query-input', 'value'),
    Input('temp-df-store', 'data'),
    State('results-store', 'data'),
    State('counter-store', 'data')
)
def update_results(df_dict, results, counter):
    if not df_dict:
        raise PreventUpdate
        
    try:
        # Garantir que results é uma lista, mesmo que vazia
        if results is None:
            results = []
            
        if not isinstance(results, list):
            print("Erro: results não é uma lista válida")
            raise PreventUpdate
            
        # Criar novo resultado
        new_result = {
            'id': str(counter - 1),
            'data': df_dict,  # Usar diretamente o dicionário recebido
            'timestamp': datetime.now().isoformat()
        }
        
        # Adicionar à lista de resultados
        updated_results = results + [new_result]
        
        return updated_results, ""
        
    except Exception as e:
        import traceback
        print(f"Erro ao atualizar resultados: {e}")
        print(traceback.format_exc())
        return results, ""

# Callback for downloading Excel
@app.callback(
    Output('download-dataframe-xlsx', 'data'),
    Input({'type': 'download-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('results-store', 'data'),
    State('conversation-store', 'data'),
    prevent_initial_call=True  # Adicionar esta flag para prevenir chamadas iniciais
)
def download_xlsx(n_clicks, results, conversation):
    # Verifica se de fato houve um clique
    if not callback_context.triggered or not n_clicks or not any(n for n in n_clicks if n):
        raise PreventUpdate
        
    try:
        # Check which button was clicked
        button_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        if not button_id:
            raise PreventUpdate
            
        # Extract the result ID
        clicked_id = json.loads(button_id)['index']
        debug_print(f"Botão de download clicado para resultado #{clicked_id}")
        
        # Find the corresponding result
        result_data = next((r for r in results if r['id'] == clicked_id), None)
        
        if result_data and 'data' in result_data:
            # Convert to DataFrame
            df = pd.DataFrame(result_data['data'])
            
            # Generate Excel in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Primeira aba: dados dos resultados
                df.to_excel(writer, sheet_name='Results', index=False)
                
                # Segunda aba: histórico de perguntas e respostas
                if conversation:
                    conversation_data = []
                    for entry in conversation:
                        if entry.get('role') == 'user':
                            conversation_data.append({
                                'Tipo': 'Pergunta',
                                'Conteúdo': entry.get('content', '')
                            })
                        elif entry.get('role') == 'assistant':
                            conversation_data.append({
                                'Tipo': 'Resposta',
                                'Conteúdo': entry.get('content', '')
                            })
                    
                    if conversation_data:
                        conversation_df = pd.DataFrame(conversation_data)
                        conversation_df.to_excel(writer, sheet_name='Histórico', index=False)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"GOvGO_Report_{clicked_id}_{timestamp}.xlsx"
            
            debug_print(f"Preparando download do arquivo: {filename}")
            return dcc.send_bytes(output.getvalue(), filename)
    except Exception as e:
        debug_print(f"Erro ao fazer download: {e}")
        import traceback
        debug_print(traceback.format_exc())
        
    raise PreventUpdate

# Add FontAwesome CSS for icons and custom animations
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
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
        .history-item:hover {
            background-color: #e3f2fd !important;
            border-color: #2196F3 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        }
        .close-button:hover {
            background-color: #c82333 !important;
            transform: scale(1.1);
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

# 1. MOVER este callback para ANTES do bloco if __name__ == '__main__':
@app.callback(
    Output('submit-button', 'children'),
    Output('submit-button', 'disabled'),
    Output('submit-button', 'style'),
    Input('processing-state', 'data')
)
def update_submit_button(is_processing):
    debug_print(f"update_submit_button: Estado de processamento: {is_processing}")
    
    if is_processing:
        debug_print("Alterando botão para mostrar spinner")
        # Usar FontAwesome spinner em vez de dcc.Loading
        button_content = html.I(className="fas fa-spinner fa-spin", style={'color': 'white'})
        disabled = True
        style = {**styles['submit_button'], 'opacity': '1'}
    else:
        debug_print("Restaurando botão para estado normal")
        button_content = html.I(className="fas fa-arrow-right")
        disabled = False
        style = styles['submit_button']
    
    return button_content, disabled, style

# Teste para verificar se o card de 0 linhas está funcionando
def test_zero_rows():
    """Teste para verificar se o card de 0 linhas funciona corretamente"""
    debug_print("=== TESTE DE 0 LINHAS ===")
    
    # Simular um resultado vazio
    test_result = {
        'id': '999',
        'data': {},  # DataFrame vazio convertido para dict
        'timestamp': datetime.now().isoformat()
    }
    
    # Converter como seria feito na render_results
    if isinstance(test_result['data'], list):
        df_data = test_result['data']
    else:
        df_data = pd.DataFrame(test_result['data']).to_dict('records')
    
    debug_print(f"Teste - df_data: {df_data}")
    debug_print(f"Teste - len(df_data): {len(df_data)}")
    debug_print(f"Teste - bool(df_data): {bool(df_data)}")
    debug_print(f"Teste - condição if: {df_data and len(df_data) > 0}")
    
    if df_data and len(df_data) > 0:
        debug_print("Teste - ENTRARIA no IF (mostrar tabela)")
    else:
        debug_print("Teste - ENTRARIA no ELSE (mostrar card 0 linhas)")
    
    debug_print("=== FIM TESTE ===")

# Run the server
if __name__ == '__main__':
    # Teste de conexão com Supabase ao iniciar
    try:
        test_conn = psycopg2.connect(**DB_CONFIG)
        test_conn.close()
        debug_print("✅ Conexão com Supabase PostgreSQL estabelecida com sucesso!")
    except Exception as e:
        debug_print(f"❌ Erro ao conectar com Supabase: {e}")
    
    # Adicionar parâmetro para desabilitar cache
    app.run_server(debug=True, port=8056,  # Mudei a porta para 8056
                   dev_tools_hot_reload=True, 
                   dev_tools_props_check=False, 
                   dev_tools_ui=False)
