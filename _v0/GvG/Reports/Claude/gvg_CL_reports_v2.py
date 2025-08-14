## GvG Reports v2 using Claude
# Minimamente funcional. erros de layout e funcionalidade a serem corrigidos.
#  
import os
import sqlite3
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
import io
from openai import OpenAI

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
LOGO_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#LOGO\\LOGO_TEXTO_GOvGO_TRIM_v3.png"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
# Caminho para a logo local


if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

# OpenAI configuration
client = OpenAI(api_key="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")
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"
model_id = "gpt-4o"

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'GOvGO'

# Define custom styles
styles = {
    'container': {
        'display': 'flex',
        'height': '100vh',
        'width': '100%',
    },
    'left_panel': {
        'width': '40%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'height': '100%'
    },
    'right_panel': {
        'width': '60%',
        'backgroundColor': '#F5F5F5',
        'padding': '10px',
        'overflowY': 'auto',
        'height': '100%'
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
        'backgroundColor': '#E6F2FF',
        'borderRadius': '15px',
        'padding': '10px',
        'maxWidth': '80%',
        'marginBottom': '10px',
        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)',
        'position': 'relative'
    },
    'sql_message': {
        'alignSelf': 'flex-start',
        'backgroundColor': '#fff',
        'borderRadius': '15px',
        'padding': '10px',
        'maxWidth': '80%',
        'marginBottom': '10px',
        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)',
        'fontFamily': 'Consolas, monospace',
        'position': 'relative'
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
    }
}

# Store for conversation history, query results and counter
conversation_store = []
results_store = []
next_message_counter = 1

# Assistant functions
# OPENAI SEND USER MESSAGE
def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=formatted_content
    )
    
# OPENAI POLL RUN
def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    return client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

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
    try:
        send_user_message(user_query)
        run = poll_run()
        if run.status == 'completed':
            last_message = get_latest_assistant_message()
            if not last_message:
                print("Nenhuma mensagem de assistente recebida.")
                return None
            return last_message
        else:
            print(f"Run status: {run.status}")
            return None
    except Exception as e:
        print(f"Erro ao obter resposta do assistente: {str(e)}")
        return None

# EXTRAI SQL DO ASSISTENTE
def extract_sql_from_message(message) -> str:
    """
    Extrai e limpa o SQL do conteúdo da mensagem do assistente.
    Retorna apenas o texto (sem quebras de linha extras).
    """
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
    return " ".join(sql_query.replace("\n", " ").split())

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
    """Executa a consulta SQL no banco de dados"""
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Erro ao executar consulta: {e}")
        return pd.DataFrame()

# Substituir os dados de exemplo por estruturas vazias
initial_conversation = []  # Lista vazia em vez de exemplo predefinido
initial_results = []       # Lista vazia em vez de exemplo predefinido

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
    logo,
    chat_container,
    input_container
], style=styles['left_panel'])

results_container = html.Div(id='results-container', style=styles['right_panel'])

# Main layout
app.layout = html.Div([
    dcc.Store(id='conversation-store', data=initial_conversation),
    dcc.Store(id='results-store', data=initial_results),
    dcc.Store(id='counter-store', data=1),  # Começar do 1, não do 2
    dcc.Store(id='temp-df-store', data={}),
    html.Div([
        left_panel,
        results_container,
        # Hidden download component
        html.Div([
            dcc.Download(id="download-dataframe-xlsx"),
        ], style={"display": "none"}),
    ], style=styles['container']),
    dcc.Loading(id="loading-indicator", type="circle")
])

# Callback to render chat messages
@app.callback(
    Output('chat-container', 'children'),
    Input('conversation-store', 'data')
)
def render_chat(conversation):
    if not conversation:  # Se não houver mensagens, retorna uma lista vazia
        return []
    
    chat_elements = []
    
    for message in conversation:
        if message['type'] == 'user':
            chat_elements.append(html.Div([
                html.Div(
                    message['text'],
                    style={'fontWeight': 'bold', 'marginBottom': '5px'}
                ),
            ], style=styles['user_message']))
            
            # Add SQL response if available
            if 'sql' in message and message['sql']:
                chat_elements.append(html.Div([
                    html.Div(
                        message['id'],
                        style=styles['message_number']
                    ),
                    html.Div(message['sql'])
                ], style=styles['sql_message']))
    
    return chat_elements

# Callback to render results
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
            # Tentar carregar os dados, independente do formato
            if isinstance(result['data'], list):
                df_data = result['data']
            else:  # Tentar converter de outros formatos
                df_data = pd.DataFrame(result['data']).to_dict('records')
                
            if df_data:  # Se temos dados válidos
                result_elements.append(html.Div([
                    html.Div(
                        result['id'], 
                        style=styles['message_number']
                    ),
                    dash_table.DataTable(
                        data=df_data,
                        columns=[{'name': k, 'id': k} for k in df_data[0].keys()] if df_data else [],
                        page_size=10,
                        # Resto do código permanece o mesmo
                    ),
                    # Botões de ação permanecem iguais
                ], style=styles['result_card']))
        except Exception as e:
            print(f"Erro ao renderizar resultado {result['id']}: {e}")
    
    return result_elements

# Callback for query submission
@app.callback(
    Output('conversation-store', 'data'),
    Output('temp-df-store', 'data'),
    Output('counter-store', 'data'),
    Output('loading-indicator', 'children'),
    Input('submit-button', 'n_clicks'),
    Input('query-input', 'n_submit'),
    State('query-input', 'value'),
    State('conversation-store', 'data'),
    State('counter-store', 'data'),
)
def process_query(n_clicks, n_submit, query, conversation, counter):
    if not callback_context.triggered or (not n_clicks and not n_submit) or not query:
        raise PreventUpdate
        
    # Get current counter value
    message_counter = counter
    
    # Process natural language query
    try:
        # Função reescrita com base no reports_v8
        sql_query = generate_sql_from_nl(query)
        
        if not sql_query:
            sql_query = "Error: Could not generate SQL query"
        
        # Execute the query and store result
        df = execute_sql_query(sql_query)
        df_dict = df.to_dict('list')
        
        # Add new message to conversation
        new_message = {
            'id': str(message_counter),
            'type': 'user',
            'text': query,
            'sql': sql_query,
            'timestamp': datetime.now().isoformat()
        }
        
        updated_conversation = conversation + [new_message]
        
        # Increment counter
        next_counter = message_counter + 1
        
        # Return updated data
        return updated_conversation, df_dict, next_counter, ""
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        # Return unchanged data on error
        return conversation, {}, counter, f"Error: {str(e)}"

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
)
def download_xlsx(n_clicks, results):
    if not callback_context.triggered:
        raise PreventUpdate
        
    try:
        # Check which button was clicked
        button_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        if not button_id:
            raise PreventUpdate
            
        # Extract the result ID
        clicked_id = json.loads(button_id)['index']
        
        # Find the corresponding result
        result_data = next((r for r in results if r['id'] == clicked_id), None)
        
        if result_data and 'data' in result_data:
            # Convert to DataFrame
            df = pd.DataFrame(result_data['data'])
            
            # Generate Excel in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Results', index=False)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"GOvGO_Report_{clicked_id}_{timestamp}.xlsx"
            
            return dcc.send_bytes(output.getvalue(), filename)
    except Exception as e:
        print(f"Error downloading: {e}")
        
    raise PreventUpdate

# Add FontAwesome CSS for icons
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
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

# Run the server
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)