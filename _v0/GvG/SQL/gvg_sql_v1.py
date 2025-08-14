import os
import sqlite3
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
from datetime import datetime
import json
import base64
import io
import traceback
import time  # Adicione esta importação no início do arquivo

# Variável de controle para debug
DEBUG = False

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
LOGO_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#LOGO\\LOGO_TEXTO_GOvGO_TRIM_v3.png"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"


# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'SQL Direct Executor'

# Define custom styles
styles = {
    'container': {
        'display': 'flex',
        'height': 'calc(100vh - 60px)',
        'width': '100%',
        'marginTop': '60px',
        'padding': '5px'
    },
    'left_panel': {
        'width': '40%',
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
        'width': '60%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
        'height': 'calc(100vh - 100px)'
    },
    'chat_container': {
        'flex': '1',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'marginBottom': '10px'
    },
    'sql_message': {
        'backgroundColor': '#52ACFF',
        'color': '#FFFFFF',
        'borderRadius': '15px',
        'padding': '10px',
        'marginBottom': '10px',
        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)',
        'fontFamily': 'Consolas, monospace',
        'fontSize': '12px',
        'position': 'relative',
        'wordWrap': 'break-word',
        'overflowWrap': 'break-word',
        'wordBreak': 'break-word',
        'fontWeight': 'normal',
        'whiteSpace': 'pre-wrap'  # Preserva quebras de linha
    },
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'flexDirection': 'column',  # Alterado para empilhar conteúdos
        'alignItems': 'stretch',
        'marginTop': 'auto'
    },
    'input_field': {
        'border': 'none',
        'outline': 'none',
        'padding': '8px',
        'backgroundColor': 'transparent',
        'width': '100%',
        'minHeight': '120px',  # Aumentar altura mínima para múltiplas linhas
        'resize': 'vertical'   # Permitir redimensionamento vertical
    },
    'error_message': {
        'backgroundColor': '#FFEBEE',
        'color': '#D32F2F',
        'borderRadius': '15px',
        'padding': '15px',
        'marginBottom': '20px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
        'fontFamily': 'Consolas, monospace',
        'fontSize': '12px',
        'position': 'relative',
        'wordWrap': 'break-word',
        'overflowWrap': 'break-word',
        'wordBreak': 'break-word',
        'whiteSpace': 'pre-wrap'  # Preserva quebras de linha
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
    'result_number': {
        'position': 'absolute',
        'bottom': '10px',
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
        'fontfamily': 'Arial, sans-serif'
    },
    'debug_info': {
        'marginTop': '5px',
        'fontSize': '11px',
        'color': '#666',
        'fontStyle': 'italic',
        'borderTop': '1px dashed #999',
        'paddingTop': '5px'
    },
    # Estilo específico para numeração da instrução SQL (no canto inferior direito)
    'sql_number': {
        'position': 'absolute',
        'bottom': '10px',
        'right': '10px',  # Mudado para direita
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
        'fontfamily': 'Arial, sans-serif'
    }
}

def b64_image(image_path):
    """Converte uma imagem local para string base64 para uso no Dash"""
    try:
        with open(image_path, 'rb') as f:
            image = f.read()
        return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')
    except Exception as e:
        print(f"Erro ao carregar imagem: {e}")
        return ''

# Componente de SQL history
sql_history_container = html.Div(id='sql-history-container', style=styles['chat_container'])

input_container = html.Div([
    dcc.Textarea(
        id='sql-input',
        placeholder='Digite sua instrução SQL aqui...',
        style={
            'width': '100%', 
            'height': '200px',
            'marginBottom': '10px', 
            'fontFamily': 'Consolas, monospace', 
            'fontSize': '12px',
            'resize': 'vertical',
            'whiteSpace': 'pre-wrap',
            'border': 'none',
            'outline': 'none',
            'padding': '8px',
            'backgroundColor': '#FFFFFF'
        },
        rows=10
    ),
    html.Button(
        # Substitui texto por ícone
        html.I(className="fas fa-play", style={'marginRight': '5px'}), 
        # Adiciona id de conteúdo separado para facilitar atualização
        id='submit-button-content',
        style={
            'backgroundColor': '#FF5722', 
            'color': 'white', 
            'border': 'none', 
            'padding': '10px 15px', 
            'borderRadius': '5px',
            'width': '100%',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )
], style=styles['input_container'])

left_panel = html.Div([
    sql_history_container,
    input_container
], style=styles['left_panel'])

results_container = html.Div(id='results-container', style=styles['right_panel'])

# Cabeçalho
header = html.Div([
    # Logo à esquerda
    html.Div([
        html.Img(src=b64_image(LOGO_PATH), style={'height': '40px'}),
        html.H4("SQL Direct Executor", style={'marginLeft': '15px', 'color': '#003A70'})
    ], style={'display': 'flex', 'AlignItems': 'center'}),
    
    # Status à direita
    html.Div([
        html.Span(id='connection-status', children="Conectado", style={
            'color': '#4CAF50', 
            'fontWeight': 'bold'
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

# Layout principal
app.layout = html.Div([
    dcc.Store(id='sql-history-store', data=[]),
    dcc.Store(id='results-store', data=[]),
    dcc.Store(id='counter-store', data=1),
    dcc.Store(id='errors-store', data=[]),  # Adicionado para armazenar erros
    dcc.Store(id='processing-state', data=False),
    
    # Adicionar o loading indicator aqui
    html.Div(id='loading-indicator', style={'display': 'none'}),
    
    header,
    
    html.Div([
        left_panel,
        results_container,
        html.Div([
            dcc.Download(id="download-dataframe-xlsx"),
        ], style={"display": "none"}),
    ], style=styles['container']),
])

# Função para executar SQL
def execute_sql_query(sql_query):
    """Executa a consulta SQL no banco de dados"""
    debug_print(f"Executando SQL: '{sql_query}'")  # Mostra consulta completa
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        debug_print(f"SQL executado com sucesso. Linhas retornadas: {len(df)}")
        debug_print(f"Primeiras 5 linhas do resultado: {df.head().to_string()}")
        return df
    except Exception as e:
        debug_print(f"Erro ao executar consulta: {e}")
        debug_print(traceback.format_exc())
        raise e

# Callback para renderizar histórico de SQL
@app.callback(
    Output('sql-history-container', 'children'),
    Input('sql-history-store', 'data')
)
def render_sql_history(history):
    if not history:
        return []
    
    history_elements = []
    
    for item in history:
        # Incluindo informações de debug
        debug_info = html.Div([
            html.Div(f"Timestamp: {item.get('timestamp', 'N/A')}"),
            html.Div(f"Registros: {item.get('row_count', 'erro')} | ID: {item.get('id', 'N/A')}"),
        ], style=styles['debug_info'])
        
        history_elements.append(html.Div([
            html.Div(item['sql']),
            debug_info,
            # Adicionando a numeração no canto inferior direito
            html.Div(
                item['id'],
                style=styles['sql_number']  # Usando o novo estilo com posição à direita
            )
        ], style=styles['sql_message']))
    
    return history_elements

# Callback para renderizar resultados
@app.callback(
    Output('results-container', 'children'),
    [Input('results-store', 'data'), 
     Input('errors-store', 'data')]  # Adicionado para mostrar erros
)
def render_results(results, errors):
    result_elements = []
    
    # Renderizar erros primeiro
    if errors:
        for error in errors:
            result_elements.append(html.Div([
                html.H5("Erro SQL", style={'color': '#D32F2F', 'marginBottom': '10px'}),
                html.Div(error.get('query', 'Consulta desconhecida'), 
                         style={'marginBottom': '15px', 'fontFamily': 'Consolas, monospace', 'whiteSpace': 'pre-wrap'}),
                html.Div([
                    html.Strong("Mensagem: "), 
                    error.get('message', 'Erro desconhecido')
                ]),
                html.Div([
                    html.Strong("Detalhes: "), 
                    error.get('details', '')
                ]),
                html.Div(
                    error.get('id', '?'),
                    style=styles['result_number']
                )
            ], style=styles['error_message']))
    
    # Renderizar resultados
    if results:
        for result in results:
            try:
                if isinstance(result['data'], list):
                    df_data = result['data']
                else:
                    df_data = pd.DataFrame(result['data']).to_dict('records')
                    
                if df_data:
                    # Adicionar informações de debug
                    debug_info = html.Div([
                        html.Div(f"Timestamp: {result.get('timestamp', 'N/A')}"),
                        html.Div(f"Total registros: {len(df_data)}"),
                    ], style=styles['debug_info'])
                    
                    result_elements.append(html.Div([
                        debug_info,
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
                                'padding': '6px',
                                'fontSize': '12px'
                            },
                            style_header={
                                'backgroundColor': '#f8f9fa',
                                'fontWeight': 'bold',
                                'border': '1px solid #ddd',
                                'textAlign': 'left',
                                'fontSize': '13px'
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
                        ], style=styles['action_buttons']),
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

# Callback para processar consulta SQL
@app.callback(
    Output('sql-history-store', 'data'),
    Output('results-store', 'data'),
    Output('errors-store', 'data'),
    Output('counter-store', 'data'),
    Output('processing-state', 'data'),  # Adicionada saída para controlar o estado
    Output('connection-status', 'children'),
    Output('connection-status', 'style'),
    Input('submit-button-content', 'n_clicks'),
    State('sql-input', 'value'),
    State('sql-history-store', 'data'),
    State('results-store', 'data'),
    State('errors-store', 'data'),
    State('counter-store', 'data'),
    State('processing-state', 'data'),
    prevent_initial_call=True
)
def process_sql_query(n_clicks, sql_query, history, results, errors, counter, is_processing):
    if not sql_query:
        return history, results, errors, counter, False, "Conectado", {'color': '#4CAF50', 'fontWeight': 'bold'}
    
    # Debug: mostrar consulta completa
    debug_print(f"Requisição SQL #{counter}:\n{sql_query}")
    
    # Pequena pausa para garantir que o spinner seja visível
    time.sleep(0.5)  # Pausa de 0.5 segundos
    
    try:
        # Executar SQL
        df = execute_sql_query(sql_query)
        df_dict = df.to_dict('list')
        row_count = len(df)
        
        # Adicionar ao histórico
        new_history_item = {
            'id': str(counter),
            'sql': sql_query,
            'timestamp': datetime.now().isoformat(),
            'row_count': row_count
        }
        updated_history = history + [new_history_item]
        
        # Adicionar aos resultados
        new_result = {
            'id': str(counter),
            'data': df_dict,
            'timestamp': datetime.now().isoformat()
        }
        updated_results = results + [new_result]
        
        next_counter = counter + 1
        
        # Debug: mostrar resumo do resultado
        debug_print(f"Resultado SQL #{counter}: {row_count} registros")
        
        # Retorna False para processing-state para indicar conclusão
        return updated_history, updated_results, errors, next_counter, False, f"Conectado - {row_count} registros", {'color': '#4CAF50', 'fontWeight': 'bold'}
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        # Debug: mostrar erro completo
        debug_print(f"Erro SQL #{counter}:\n{error_msg}\n{stack_trace}")
        
        # Adicionar ao histórico como erro
        new_history_item = {
            'id': str(counter),
            'sql': sql_query,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'row_count': 'erro'
        }
        updated_history = history + [new_history_item]
        
        # Adicionar aos erros para exibir no painel de resultados
        new_error = {
            'id': str(counter),
            'query': sql_query,
            'message': error_msg,
            'details': stack_trace,
            'timestamp': datetime.now().isoformat()
        }
        updated_errors = errors + [new_error]
        
        next_counter = counter + 1
        
        # Retorna False para processing-state para indicar conclusão mesmo com erro
        return updated_history, results, updated_errors, next_counter, False, f"Erro: {error_msg[:30]}...", {'color': '#FF5722', 'fontWeight': 'bold'}

# Callback for downloading Excel
@app.callback(
    Output('download-dataframe-xlsx', 'data'),
    Input({'type': 'download-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('results-store', 'data'),
    prevent_initial_call=True
)
def download_xlsx(n_clicks, results):
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
                df.to_excel(writer, sheet_name='Results', index=False)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SQL_Results_{clicked_id}_{timestamp}.xlsx"
            
            debug_print(f"Preparando download do arquivo: {filename}")
            return dcc.send_bytes(output.getvalue(), filename)
    except Exception as e:
        debug_print(f"Erro ao fazer download: {e}")
        debug_print(traceback.format_exc())
        
    raise PreventUpdate

# Callback para atualizar o estilo e conteúdo do botão durante o processamento
@app.callback(
    Output('submit-button-content', 'children'),
    Output('submit-button-content', 'disabled'),
    Output('submit-button-content', 'style'),
    [Input('processing-state', 'data')],
    [State('submit-button-content', 'style')]
)
def update_button_state(is_processing, current_style):
    if is_processing:
        # Quando estiver processando, mostra o spinner
        return [
            html.I(className="fas fa-spinner fa-spin", style={'color': 'white'})
        ], True, {
            **current_style,
            'opacity': '0.8',
            'backgroundColor': '#FF5722',
            'color': 'white'
        }
    else:
        # Estado normal - mostra o ícone de execução
        return [
            html.I(className="fas fa-play", style={'marginRight': '5px'}),
            "Executar SQL"
        ], False, {
            **current_style,
            'opacity': '1',
            'backgroundColor': '#FF5722',
            'color': 'white',
            'borderRadius': '15px'
        }

# Callback para definir o estado de processamento quando o botão é clicado
@app.callback(
    Output('processing-state', 'data', allow_duplicate=True),
    Input('submit-button-content', 'n_clicks'),
    State('sql-input', 'value'),
    prevent_initial_call=True
)
def set_processing_state(n_clicks, sql_query):
    if not sql_query:
        raise PreventUpdate
        
    debug_print("Iniciando processamento...")
    return True  # Ativa o estado de processamento

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
    app.run_server(debug=True, port=8056, 
                   dev_tools_hot_reload=True, 
                   dev_tools_props_check=False, 
                   dev_tools_ui=False)