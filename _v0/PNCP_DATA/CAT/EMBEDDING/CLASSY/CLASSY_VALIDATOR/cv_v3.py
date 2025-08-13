import os
import pandas as pd
import sqlite3
import dash
from dash import html, dcc, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from datetime import datetime
import json
import random
import threading

# Definindo os caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"
VALIDATION_PATH = BASE_PATH + "CLASSY\\CLASSY_ITENS\\VALIDATION\\"
os.makedirs(VALIDATION_PATH, exist_ok=True)

# Criar arquivo de resultados de validação com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
VALIDATION_FILE = VALIDATION_PATH + f"validation_results_{TIMESTAMP}.xlsx"

# Cores para seleção
BORDER_COLORS = ['#28a745', '#ffc107', '#fd7e14', '#dc3545', '#8b0000']
COLOR_NAMES = ['Verde', 'Amarelo', 'Laranja', 'Vermelho', 'Bordô']

# Estilos para os componentes
DESCRIPTION_STYLE = {
    'height': '300px',
    'overflow-y': 'auto',
    'padding': '15px',
    'margin-bottom': '10px',
    'border': '1px solid #ddd',
    'border-radius': '5px',
    'background-color': '#f9f9f9',
}

# Aumentado largura dos quadros TOP para ocupar melhor o espaço
TOP_BOX_STYLE = {
    'height': '300px', # Mesma altura da descrição
    'overflow-y': 'auto',
    'padding': '15px',
    'margin': '5px',
    'border': '1px solid #ddd',
    'border-radius': '5px',
    'cursor': 'pointer',
    'background-color': '#f9f9f9',
    'position': 'relative',
    'font-size': '12px',
}

CONFIDENCE_STYLE = {
    'margin-top': '10px',
    'font-weight': 'bold',
    'font-size': '18px',
    'margin-bottom': '10px'
}

SCORE_STYLE = {
    'margin-top': '10px',
    'font-weight': 'normal',
    'font-size': '14px'
}

ID_STYLE = {
    'margin-top': '5px',
    'font-size': '12px',
    'color': '#666',
    'font-style': 'italic'
}

ORDER_LABEL_STYLE = {
    'position': 'absolute',
    'top': '5px',
    'right': '5px',
    'font-weight': 'bold',
    'font-size': '18px',
    'width': '30px',
    'height': '30px',
    'text-align': 'center',
    'line-height': '30px',
    'border-radius': '50%',
    'color': 'white'
}

# Inicializar app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "CLASSY VALIDATOR - Validação de Classificações"

# Estado global para controle de navegação
app.validation_results = []
app.current_item_index = 0
app.total_items = 0
app.items_df = None
app.current_selections = []
app.preloaded = False

def load_sample_data():
    """Carrega uma pequena amostra de dados para inicialização rápida"""
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT ID, numeroControlePNCP, numeroItem, ID_ITEM_CONTRATACAO, descrição, item_type, 
    TOP_1, TOP_2, TOP_3, TOP_4, TOP_5, 
    SCORE_1, SCORE_2, SCORE_3, SCORE_4, SCORE_5, CONFIDENCE 
    FROM item_classificacao ORDER BY RANDOM() LIMIT 20;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Verificar se há dados
    if len(df) == 0:
        return pd.DataFrame()
    
    # Randomizar a ordem dos itens - REMOVIDO random_state
    df = df.sample(frac=1).reset_index(drop=True)
    
    return df

def load_full_data():
    """Carrega todos os dados em segundo plano"""
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT ID, numeroControlePNCP, numeroItem, ID_ITEM_CONTRATACAO, descrição, 
    item_type, TOP_1, TOP_2, TOP_3, TOP_4, TOP_5, 
    SCORE_1, SCORE_2, SCORE_3, SCORE_4, SCORE_5, CONFIDENCE
    FROM item_classificacao
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Randomizar a ordem dos itens - REMOVIDO random_state
    df = df.sample(frac=1).reset_index(drop=True)
    
    app.items_df = df
    app.total_items = len(df)

def save_validation_results():
    """Salva os resultados da validação em um arquivo Excel"""
    if not app.validation_results:
        return False
    
    # Salvar em Excel
    results_df = pd.DataFrame(app.validation_results)
    results_df.to_excel(VALIDATION_FILE, index=False)
    
    # Também salvar JSON para backup
    #json_file = VALIDATION_FILE.replace('.xlsx', '.json')
    #with open(json_file, 'w') as f:
    #    json.dump(app.validation_results, f, indent=2)
    
    return True

# Inicialização rápida com amostra pequena
sample_df = load_sample_data()

# Iniciar carregamento completo em segundo plano
threading.Thread(target=load_full_data, daemon=True).start()

# Layout da aplicação
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("CLASSY VALIDATOR", className="text-center mb-4 mt-3"),
            
            # Armazenamento oculto de estado
            dcc.Store(id='item-data-store'),
            dcc.Store(id='selections-store', data=[]),
            dcc.Input(id='key-capture', type='text', style={'opacity': 0, 'position': 'fixed'}),
            
            # Modal de conclusão
            dbc.Modal([
                dbc.ModalHeader("Validação Concluída"),
                dbc.ModalBody([
                    html.P("Todos os itens foram validados!"),
                    html.P(id="modal-result-info")
                ]),
                dbc.ModalFooter(
                    dbc.Button("Fechar", id="close-modal", className="ms-auto")
                ),
            ], id="completion-modal", centered=True),
        ], width=12)
    ]),
    
    # Linha de cabeçalhos
    dbc.Row([
        dbc.Col([html.H4("Descrição do Item")], width=4),
        dbc.Col([html.H4("Categorias Sugeridas")], width=8)
    ]),
    
    # CORREÇÃO: COLOQUE DESCRIÇÃO E TOP_BOX NA MESMA LINHA
    dbc.Row([
        # Coluna da esquerda - Descrição (30%)
        dbc.Col([
            html.Div(id="item-description", style=DESCRIPTION_STYLE),
            html.Div([
                html.Span("Confiança: "),
                html.Span(id="item-confidence", style={"font-weight": "bold"})
            ], style=CONFIDENCE_STYLE),
            html.Div(id="item-id-display", style=ID_STYLE)
        ], width=4),
        
        # Coluna da direita - Todos os TOP_BOX (70%)
        dbc.Col([
            # Linha interna para os 5 TOP_BOX
            # MODIFICATION: Removed width=2 from inner dbc.Col and added className="g-0" to this dbc.Row
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div(id='order-label-1', className='order-label'),
                    html.Div(id='top-1-content', className='top-content'),
                    html.Div(id='score-1', style=SCORE_STYLE)
                ], id='top-box-1', className='top-box', n_clicks=0, style=TOP_BOX_STYLE)), # width=2 REMOVED
                
                dbc.Col(html.Div([
                    html.Div(id='order-label-2', className='order-label'),
                    html.Div(id='top-2-content', className='top-content'),
                    html.Div(id='score-2', style=SCORE_STYLE)
                ], id='top-box-2', className='top-box', n_clicks=0, style=TOP_BOX_STYLE)), # width=2 REMOVED
                
                dbc.Col(html.Div([
                    html.Div(id='order-label-3', className='order-label'),
                    html.Div(id='top-3-content', className='top-content'),
                    html.Div(id='score-3', style=SCORE_STYLE)
                ], id='top-box-3', className='top-box', n_clicks=0, style=TOP_BOX_STYLE)), # width=2 REMOVED
                
                dbc.Col(html.Div([
                    html.Div(id='order-label-4', className='order-label'),
                    html.Div(id='top-4-content', className='top-content'),
                    html.Div(id='score-4', style=SCORE_STYLE)
                ], id='top-box-4', className='top-box', n_clicks=0, style=TOP_BOX_STYLE)), # width=2 REMOVED
                
                dbc.Col(html.Div([
                    html.Div(id='order-label-5', className='order-label'),
                    html.Div(id='top-5-content', className='top-content'),
                    html.Div(id='score-5', style=SCORE_STYLE)
                ], id='top-box-5', className='top-box', n_clicks=0, style=TOP_BOX_STYLE)), # width=2 REMOVED
            ], className="g-0"), # Added g-0 to remove gutters between these expanding columns
        ], width=8),
    ], className="mb-3"),
    
    # Botões de navegação e instruções
    dbc.Row([
        dbc.Col([
            dbc.Button("< Anterior", id="prev-button", color="secondary", className="me-2"),
            dbc.Button("Próximo >", id="next-button", color="primary"),
        ], width=12, className="text-center mt-4")
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("Instruções:"),
                html.Ul([
                    html.Li("Clique para selecionar/desmarcar categoria"),
                    html.Li("Enter para confirmar e ir para o próximo item")
                ])
            ], className="mt-4 p-3 bg-light")
        ], width=12)
    ])
], fluid=True)

# Callback para inicializar e navegar pelos itens
@app.callback(
    [Output('item-data-store', 'data'),
     Output('item-description', 'children'),
     Output('item-id-display', 'children'),
     Output('item-confidence', 'children'),
     Output('top-1-content', 'children'),
     Output('top-2-content', 'children'),
     Output('top-3-content', 'children'),
     Output('top-4-content', 'children'),
     Output('top-5-content', 'children'),
     Output('score-1', 'children'),
     Output('score-2', 'children'),
     Output('score-3', 'children'),
     Output('score-4', 'children'),
     Output('score-5', 'children'),
     Output('selections-store', 'data'),
     Output('completion-modal', 'is_open'),
     Output('modal-result-info', 'children'),
     # CORREÇÃO: Reset dos estilos dos boxes - Certifique-se de limpar as bordas
     Output('top-box-1', 'style'),
     Output('top-box-2', 'style'),
     Output('top-box-3', 'style'),
     Output('top-box-4', 'style'),
     Output('top-box-5', 'style'),
     # CORREÇÃO: Reset explícito dos labels de ordem - Certifique-se de ficar vazio
     Output('order-label-1', 'children'),
     Output('order-label-2', 'children'),
     Output('order-label-3', 'children'),
     Output('order-label-4', 'children'),
     Output('order-label-5', 'children'),
     # CORREÇÃO: Reset explícito dos estilos dos labels
     Output('order-label-1', 'style'),
     Output('order-label-2', 'style'),
     Output('order-label-3', 'style'),
     Output('order-label-4', 'style'),
     Output('order-label-5', 'style')],
    [Input('prev-button', 'n_clicks'),
     Input('next-button', 'n_clicks'),
     Input('key-capture', 'n_submit'),
     Input('close-modal', 'n_clicks')],
    [State('item-data-store', 'data'),
     State('selections-store', 'data'),
     State('completion-modal', 'is_open')]
)
def update_item_display(prev_clicks, next_clicks, key_submit, close_modal,
                        current_data, current_selections, modal_open):
    """Atualiza o display do item atual"""
    trigger = ctx.triggered_id if ctx.triggered_id else None
    
    # Reset dos estilos e seleções
    empty_label = ""
    box_style = dict(TOP_BOX_STYLE)  # Estilo base sem bordas
    empty_label_style = {}  # Estilo vazio para os labels
    
    # Inicialização - primeira vez que o callback é executado
    if not current_data:
        # Usar a amostra já carregada para início rápido
        if app.items_df is None:
            app.items_df = sample_df
            app.total_items = len(sample_df)
            app.current_item_index = 0
        
        if app.total_items == 0:
            return no_update, "Nenhum item encontrado na base de dados!", \
                   "Nenhum ID", "0%", \
                   no_update, no_update, no_update, no_update, no_update, \
                   no_update, True, "Nenhum item para validação. Verifique o banco de dados.", \
                   box_style, box_style, box_style, box_style, box_style, \
                   empty_label, empty_label, empty_label, empty_label, empty_label, \
                   empty_label_style, empty_label_style, empty_label_style, empty_label_style, empty_label_style
        
        # Reset das seleções
        app.current_selections = []
        
        # Obter o item atual
        current_item = app.items_df.iloc[app.current_item_index].to_dict()
        
        # Retornar os dados para exibição
        return current_item, \
               current_item['descrição'], \
               f"ID Contratação: {current_item['ID_ITEM_CONTRATACAO']}", \
               f"{current_item['CONFIDENCE']:.2f}%", \
               current_item['TOP_1'], \
               current_item['TOP_2'], \
               current_item['TOP_3'], \
               current_item['TOP_4'], \
               current_item['TOP_5'], \
               f"Score: {current_item['SCORE_1']:.4f}", \
               f"Score: {current_item['SCORE_2']:.4f}", \
               f"Score: {current_item['SCORE_3']:.4f}", \
               f"Score: {current_item['SCORE_4']:.4f}", \
               f"Score: {current_item['SCORE_5']:.4f}", \
               [], False, no_update, \
               box_style, box_style, box_style, box_style, box_style, \
               empty_label, empty_label, empty_label, empty_label, empty_label, \
               empty_label_style, empty_label_style, empty_label_style, empty_label_style, empty_label_style
    
    # Fechar modal
    if trigger == 'close-modal':
        return current_data, no_update, no_update, no_update, \
               no_update, no_update, no_update, no_update, no_update, \
               no_update, no_update, no_update, no_update, no_update, \
               current_selections, False, no_update, \
               no_update, no_update, no_update, no_update, no_update, \
               no_update, no_update, no_update, no_update, no_update, \
               no_update, no_update, no_update, no_update, no_update
    
    # Verificar se os dados completos foram carregados e substituir o DataFrame se necessário
    if app.preloaded and len(app.items_df) > len(sample_df):
        current_idx = app.current_item_index
        app.total_items = len(app.items_df)
        app.current_item_index = min(current_idx, app.total_items - 1)
    
    # Navegar para o próximo item ou anterior
    move_next = False
    if trigger in ['next-button', 'key-capture']:
        # Salvar a validação atual (ou a ausência dela) antes de avançar
        if current_data: # Se um item estiver carregado
            validated_categories = []
            # current_selections é o estado atual, pode estar vazio
            if current_selections: # Se houver seleções, popule validated_categories
                for idx in current_selections:
                    if idx == 0:
                        validated_categories.append(current_data['TOP_1'])
                    elif idx == 1:
                        validated_categories.append(current_data['TOP_2'])
                    elif idx == 2:
                        validated_categories.append(current_data['TOP_3'])
                    elif idx == 3:
                        validated_categories.append(current_data['TOP_4'])
                    elif idx == 4:
                        validated_categories.append(current_data['TOP_5'])
            
            # Adicionar o item ao registro de validação
            validation_item = {
                'ID': current_data['ID'],
                'numeroControlePNCP': current_data['numeroControlePNCP'],
                'numeroItem': current_data['numeroItem'],
                'ID_ITEM_CONTRATACAO': current_data['ID_ITEM_CONTRATACAO'],
                'descrição': current_data['descrição'],
                'item_type': current_data['item_type'],
                'original_top_1': current_data['TOP_1'],
                'original_top_2': current_data['TOP_2'],
                'original_top_3': current_data['TOP_3'],
                'original_top_4': current_data['TOP_4'],
                'original_top_5': current_data['TOP_5'],
                'original_score_1': current_data['SCORE_1'],
                'original_score_2': current_data['SCORE_2'],
                'original_score_3': current_data['SCORE_3'],
                'original_score_4': current_data['SCORE_4'],
                'original_score_5': current_data['SCORE_5'],
                'original_confidence': current_data['CONFIDENCE'],
                'validated_choices_indices': current_selections, # Será [] se nada for selecionado
                'validated_top_1': validated_categories[0] if len(validated_categories) > 0 else None,
                'validated_top_2': validated_categories[1] if len(validated_categories) > 1 else None,
                'validated_top_3': validated_categories[2] if len(validated_categories) > 2 else None,
                'validated_top_4': validated_categories[3] if len(validated_categories) > 3 else None,
                'validated_top_5': validated_categories[4] if len(validated_categories) > 4 else None,
                'validation_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            app.validation_results.append(validation_item)
            
            save_validation_results() # Salvar imediatamente
        
        move_next = True
    
    elif trigger == 'prev-button':
        app.current_item_index = max(0, app.current_item_index - 1)
    
    # Se precisamos avançar para o próximo item
    if move_next:
        app.current_item_index += 1
        
        # Se chegamos ao fim de todos os itens
        if app.current_item_index >= app.total_items:
            # Salvar resultados e mostrar mensagem de conclusão
            success = save_validation_results()
            modal_msg = f"Resultados salvos em:\n{VALIDATION_FILE}" if success else "Falha ao salvar resultados."
            return no_update, no_update, no_update, no_update, \
                   no_update, no_update, no_update, no_update, no_update, \
                   no_update, no_update, no_update, no_update, no_update, \
                   current_selections, True, modal_msg, \
                   no_update, no_update, no_update, no_update, no_update, \
                   no_update, no_update, no_update, no_update, no_update, \
                   no_update, no_update, no_update, no_update, no_update
    
    # Carregar o próximo/anterior item
    current_item = app.items_df.iloc[app.current_item_index].to_dict()
    
    # Reset das seleções ao mudar de item
    app.current_selections = []
    
    # Retornar os dados para exibição
    return current_item, \
           current_item['descrição'], \
           f"ID Contratação: {current_item['ID_ITEM_CONTRATACAO']}", \
           f"{current_item['CONFIDENCE']:.2f}%", \
           current_item['TOP_1'], \
           current_item['TOP_2'], \
           current_item['TOP_3'], \
           current_item['TOP_4'], \
           current_item['TOP_5'], \
           f"Score: {current_item['SCORE_1']:.4f}", \
           f"Score: {current_item['SCORE_2']:.4f}", \
           f"Score: {current_item['SCORE_3']:.4f}", \
           f"Score: {current_item['SCORE_4']:.4f}", \
           f"Score: {current_item['SCORE_5']:.4f}", \
           [], False, no_update, \
           box_style, box_style, box_style, box_style, box_style, \
           empty_label, empty_label, empty_label, empty_label, empty_label, \
           empty_label_style, empty_label_style, empty_label_style, empty_label_style, empty_label_style

# Callbacks para gerenciar seleção de boxes (um para cada box)
for i in range(5):
    @app.callback(
        [Output(f'top-box-{i+1}', 'style', allow_duplicate=True),
         Output(f'order-label-{i+1}', 'children', allow_duplicate=True),
         Output(f'order-label-{i+1}', 'style', allow_duplicate=True),
         Output('selections-store', 'data', allow_duplicate=True)],
        [Input(f'top-box-{i+1}', 'n_clicks'),
         Input('key-capture', 'value')],
        [State('selections-store', 'data'),
         State(f'top-box-{i+1}', 'style')],
        prevent_initial_call=True
    )
    def toggle_selection(n_clicks, key_value, current_selections, current_style):
        box_index = int(ctx.outputs_list[0]['id'].split('-')[2]) - 1
        
        # Verificar se foi uma interação por teclado para este box específico
        keyboard_selection = False
        if ctx.triggered_id == 'key-capture' and key_value:
            if key_value.isdigit() and 1 <= int(key_value) <= 5:
                if int(key_value) - 1 != box_index:
                    raise PreventUpdate
                keyboard_selection = True
            else:
                raise PreventUpdate
        
        if ctx.triggered_id != f'top-box-{box_index+1}' and not keyboard_selection:
            raise PreventUpdate
            
        new_style = dict(current_style)
        new_selections = list(current_selections)
        
        # Verificar se este box já está na lista de seleções
        if box_index in new_selections:
            # Se estiver, remover e resetar o estilo
            new_selections.remove(box_index)
            new_style.pop('border', None)
            return new_style, "", {}, new_selections
        else:
            # Se não estiver, adicionar à lista e definir o estilo
            new_selections.append(box_index)
            order = new_selections.index(box_index)
            
            if order < len(BORDER_COLORS):
                border_color = BORDER_COLORS[order]
                new_style['border'] = f'4px solid {border_color}'
                
                # Estilo para o label de ordem
                order_label_style = {
                    'position': 'absolute',
                    'top': '5px',
                    'right': '5px',
                    'font-weight': 'bold',
                    'font-size': '18px',
                    'width': '30px',
                    'height': '30px',
                    'text-align': 'center',
                    'line-height': '30px',
                    'border-radius': '50%',
                    'background-color': border_color,
                    'color': 'white'
                }
                
                return new_style, str(order + 1), order_label_style, new_selections
            
            return new_style, "", {}, new_selections

# Captura de teclas para navegação
@app.callback(
    Output('key-capture', 'value'),
    [Input('key-capture', 'value')],
    prevent_initial_call=True
)
def process_keyboard_input(value):
    if not value:
        return ""
    
    # Reset do valor para evitar processamentos duplicados
    return ""

# Captura de clique direito para avançar para o próximo item
app.clientside_callback(
    """
    function(n_clicks) {
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            // Simular clique no botão Next
            document.getElementById('next-button').click();
            return false;
        });
        return window.dash_clientside.no_update;
    }
    """,
    Output('item-description', 'n_clicks'),
    Input('item-description', 'n_clicks'),
    prevent_initial_call=True
)

if __name__ == '__main__':
    app.run_server(debug=True, port=8072, 
                  dev_tools_hot_reload=True, 
                  dev_tools_props_check=False, 
                  dev_tools_ui=False)