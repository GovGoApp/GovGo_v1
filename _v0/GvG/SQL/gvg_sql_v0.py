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

# Variável de controle para debug
DEBUG = True

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
LOGO_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#LOGO\\LOGO_TEXTO_GOvGO_TRIM_v3.png"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp_v2.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")

if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

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
        'fontWeight': 'normal'
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
        style={'width': '100%', 'height': '100px', 'marginBottom': '10px', 'fontFamily': 'Consolas, monospace'}
    ),
    html.Button(
        'Executar SQL',
        id='submit-button',
        style={'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'padding': '10px 15px', 'borderRadius': '5px'}
    )
], style={'padding': '10px'})

left_panel = html.Div([
    html.H4("Instruções SQL", style={'marginBottom': '15px'}),
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
    ], style={'display': 'flex', 'alignItems': 'center'}),
    
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
    debug_print(f"Executando SQL: '{sql_query[:100]}...'")
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        debug_print(f"SQL executado com sucesso. Linhas retornadas: {len(df)}")
        return df
    except Exception as e:
        debug_print(f"Erro ao executar consulta: {e}")
        import traceback
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
        history_elements.append(html.Div([
            html.Div(item['sql']),
            html.Div(f"Registros: {item.get('row_count', 'erro')}", 
                     style={'fontSize': '11px', 'color': '#666', 'marginTop': '5px'})
        ], style=styles['sql_message']))
    
    return history_elements

# Callback para renderizar resultados
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
            if isinstance(result['data'], list):
                df_data = result['data']
            else:
                df_data = pd.DataFrame(result['data']).to_dict('records')
                
            if df_data:
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
    Output('counter-store', 'data'),
    Output('submit-button', 'disabled'),
    Output('connection-status', 'children'),
    Output('connection-status', 'style'),
    Input('submit-button', 'n_clicks'),
    State('sql-input', 'value'),
    State('sql-history-store', 'data'),
    State('results-store', 'data'),
    State('counter-store', 'data'),
    prevent_initial_call=True
)
def process_sql_query(n_clicks, sql_query, history, results, counter):
    if not sql_query:
        return history, results, counter, False, "Conectado", {'color': '#4CAF50', 'fontWeight': 'bold'}
    
    try:
        # Executar SQL
        debug_print(f"Executando SQL #{counter}: {sql_query}")
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
        
        return updated_history, updated_results, next_counter, False, f"Conectado - {row_count} registros", {'color': '#4CAF50', 'fontWeight': 'bold'}
        
    except Exception as e:
        error_msg = str(e)
        # Adicionar ao histórico como erro
        new_history_item = {
            'id': str(counter),
            'sql': sql_query,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'row_count': 'erro'
        }
        updated_history = history + [new_history_item]
        
        next_counter = counter + 1
        
        return updated_history, results, next_counter, False, f"Erro: {error_msg[:30]}...", {'color': '#FF5722', 'fontWeight': 'bold'}

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
        import traceback
        debug_print(traceback.format_exc())
        
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
    app.run_server(debug=True, port=8054, 
                   dev_tools_hot_reload=True, 
                   dev_tools_props_check=False, 
                   dev_tools_ui=False)