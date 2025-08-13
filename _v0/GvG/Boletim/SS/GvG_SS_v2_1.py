#### GvG Similarity Search Web UI (GvG_SS) v2
import os
import pandas as pd
import numpy as np
import pickle
import faiss
import sqlite3
from openai import OpenAI
import math
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import base64
import time
import locale
import traceback
import json
import io
from datetime import datetime

# Dash imports
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

# Configurar locale para formatação de valores em reais
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Usar locale padrão se não conseguir configurar

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
EMBEDDINGS_PATH = BASE_PATH + "GvG\\EG\\EMBEDDINGS\\"
LOGO_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#LOGO\\LOGO_TEXTO_GOvGO_TRIM_v3.png"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"

# Constantes para busca
TOP_N = 10  # Número de resultados a serem retornados por padrão
DEBUG = True  # Controle de debug

# Cliente OpenAI
client = OpenAI(api_key="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")

# Modelos de embedding disponíveis e suas dimensões
embedding_models = [
    {"modelo": "text-embedding-3-large", "dimensoes": 3072},
    {"modelo": "text-embedding-3-small", "dimensoes": 1536},
    {"modelo": "text-embedding-ada-002", "dimensoes": 1536}
]

# Inicializar NLTK
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Variáveis globais para cache
EMBEDDINGS_DICT = None
FAISS_INDEX = None
INDEX_KEYS = None
SELECTED_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # Dimensão padrão inicial

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Define custom styles (reaproveitando de gvg_sql_v1)
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
    'query_container': {
        'flex': '1',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'marginBottom': '10px'
    },
    'query_message': {
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
    'query_number': {
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
    },
    'model_dropdown': {
        'width': '100%',
        'marginBottom': '10px',
        'borderRadius': '5px',
        'border': '1px solid #ddd'
    }
}

# Funções de embeddings
def get_embedding_dimension(model_name):
    """Retorna a dimensão do modelo de embedding selecionado."""
    for model in embedding_models:
        if model["modelo"] == model_name:
            return model["dimensoes"]
    return 1536  # Dimensão padrão se o modelo não for encontrado

def preprocess_text(text):
    """Normaliza e limpa o texto para processamento."""
    text = unidecode.unidecode(str(text))
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

def get_embedding(text, model):
    """Gera embedding para um único texto."""
    max_retries = 3
    retry_delay = 2
    
    # Garantir que o texto não está vazio
    if not text or not text.strip():
        text = " "
    
    # Limitar tamanho se necessário
    if len(text) > 8000:
        text = text[:8000]
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model,
                input=[text]
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            if attempt < max_retries - 1:
                debug_print(f"Erro ao gerar embedding: {str(e)}. Tentativa {attempt+1}/{max_retries}.")
                time.sleep(retry_delay)
            else:
                debug_print(f"Erro ao gerar embedding: {str(e)}")
                raise

def load_embeddings(modelo):
    """Carrega os embeddings do modelo especificado."""
    filepath = EMBEDDINGS_PATH + f"GvG_embeddings_{modelo}.pkl"
    debug_print(f"Carregando embeddings do modelo {modelo}...")
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings_dict = pickle.load(f)
            debug_print(f"Carregados {len(embeddings_dict)} embeddings.")
            return embeddings_dict
        except Exception as e:
            debug_print(f"Erro ao carregar embeddings: {str(e)}")
            return None
    else:
        debug_print(f"Arquivo de embeddings não encontrado: {filepath}")
        return None

def create_faiss_index(embeddings_dict, dimension):
    """Cria um índice FAISS para busca por similaridade."""
    debug_print("Criando índice FAISS para busca rápida...")
    
    # Extrair chaves e vetores
    keys = list(embeddings_dict.keys())
    vectors = list(embeddings_dict.values())
    
    # Converter para array NumPy
    vectors_array = np.array(vectors, dtype=np.float32)
    
    # Criar índice
    index = faiss.IndexFlatIP(dimension)  # Produto interno (similaridade de cosseno)
    
    # Normalizar vetores para garantir similaridade de cosseno
    faiss.normalize_L2(vectors_array)
    
    # Adicionar vetores ao índice
    index.add(vectors_array)
    
    debug_print(f"Índice FAISS criado com {index.ntotal} vetores.")
    return index, keys

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações."""
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

def get_contratacao_details(numero_controle_pncp):
    """Busca os detalhes completos de uma contratação pelo seu número de controle."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = f"SELECT * FROM vw_contratacoes WHERE numeroControlePNCP = ?"
        df = pd.read_sql_query(query, conn, params=(numero_controle_pncp,))
        conn.close()
        
        if not df.empty:
            return df.iloc[0].to_dict()
        else:
            debug_print(f"Contratação não encontrada: {numero_controle_pncp}")
            return None
    except Exception as e:
        debug_print(f"Erro ao buscar detalhes da contratação: {str(e)}")
        return None

def search_similar_items(query_text, embedding_model, embeddings_dict, faiss_index, keys, top_n=TOP_N):
    """Busca itens similares à consulta usando FAISS e recupera detalhes do banco de dados."""
    # Processar texto da consulta
    processed_query = preprocess_text(query_text)
    debug_print(f"Texto processado: {processed_query}")
    
    # Gerar embedding da consulta
    try:
        query_embedding = get_embedding(processed_query, embedding_model)
    except Exception as e:
        debug_print(f"Falha ao gerar embedding da consulta: {str(e)}")
        raise Exception(f"Falha ao gerar embedding da consulta: {str(e)}")
    
    # Converter para float32 e normalizar
    query_embedding = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_embedding)
    
    # Realizar busca
    distances, indices = faiss_index.search(query_embedding, top_n)
    
    # Processar resultados
    results = []
    scores = distances[0].tolist()  # Extrair scores para cálculo de confiança
    
    for i, (score, idx) in enumerate(zip(distances[0], indices[0])):
        # Obter a chave correspondente
        key = keys[idx]
        
        # Calcular similaridade a partir da distância
        similarity = float(score)  # A distância já é o produto interno normalizado (similaridade de cosseno)
        
        # Buscar detalhes completos no banco de dados
        details = get_contratacao_details(key)
        
        results.append({
            "rank": i+1,
            "id": key,
            "similarity": similarity,
            "details": details
        })
    
    # Calcular confiança geral na classificação
    confidence = calculate_confidence(scores)
    
    return results, confidence, processed_query

def format_currency(value):
    """Formata um valor como moeda brasileira."""
    try:
        if pd.isna(value):
            return "N/A"
        return locale.currency(float(value), grouping=True, symbol=True)
    except:
        return str(value)

def highlight_key_terms(text, query_terms, max_length=500):
    """Destaca termos da consulta no texto e limita o comprimento."""
    if not text:
        return "N/A"
        
    # Limitar comprimento se for muito longo
    if len(text) > max_length:
        text = text[:max_length] + "..."
        
    # Substituir :: por quebras de linha para melhorar legibilidade
    text = text.replace(" :: ", "\n• ")
    if not text.startswith("•"):
        text = "• " + text
        
    return text

def b64_image(image_path):
    """Converte uma imagem local para string base64 para uso no Dash"""
    try:
        with open(image_path, 'rb') as f:
            image = f.read()
        return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')
    except Exception as e:
        debug_print(f"Erro ao carregar imagem: {e}")
        return ''

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Busca por Similaridade - GOvGO'

# Componentes do layout
# 1. Dropdown para seleção de modelo
model_dropdown = dcc.Dropdown(
    id='model-dropdown',
    options=[{"label": model["modelo"], "value": model["modelo"]} for model in embedding_models],
    value=SELECTED_MODEL,
    clearable=False,
    style=styles['model_dropdown']
)

# 2. Container para histórico de consultas
query_history_container = html.Div(id='query-history-container', style=styles['query_container'])

# 3. Container para entrada de texto
input_container = html.Div([
    dcc.Textarea(
        id='query-input',
        placeholder='Digite sua consulta aqui e pressione Enter ou clique em "Buscar"...',
        style={
            'width': '100%', 
            'height': '50px',  # ~ 2 linhas
            'marginBottom': '10px', 
            'fontFamily': 'Consolas, monospace', 
            'fontSize': '12px',
            'resize': 'none',  # Fixo em 2 linhas
            'whiteSpace': 'pre-wrap',
            'border': 'none',
            'outline': 'none',
            'padding': '8px',
            'backgroundColor': '#FFFFFF'
        }
    ),
    html.Button(
        html.Div([
            html.I(className="fas fa-search", style={'marginRight': '5px'}),
            "Buscar Similares"
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
        id='submit-button-content',
        style={
            'backgroundColor': '#FF5722',
            'color': 'white',
            'border': 'none',
            'padding': '10px 15px',
            'borderRadius': '25px',  # Botão mais arredondado
            'width': '100%',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )
], style=styles['input_container'])

# 4. Painel esquerdo completo
left_panel = html.Div([
    html.Div([
        html.H5("Modelo de Embedding", style={'marginBottom': '5px', 'color': '#003A70'}),
        model_dropdown
    ], style={'marginBottom': '15px'}),
    query_history_container,
    input_container
], style=styles['left_panel'])

# 5. Painel direito para resultados
results_container = html.Div(id='results-container', style=styles['right_panel'])

# 6. Cabeçalho
header = html.Div([
    # Logo à esquerda
    html.Div([
        html.Img(src=b64_image(LOGO_PATH), style={'height': '40px'}),
        html.H4("Busca por Similaridade", style={'marginLeft': '15px', 'color': '#003A70'})
    ], style={'display': 'flex', 'AlignItems': 'center'}),
    
    # Status à direita
    html.Div([
        html.Span(id='search-status', children="Pronto", style={
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
    dcc.Store(id='query-history-store', data=[]),
    dcc.Store(id='results-store', data=[]),
    dcc.Store(id='counter-store', data=1),
    dcc.Store(id='errors-store', data=[]),
    dcc.Store(id='processing-state', data=False),
    dcc.Store(id='embedding-cache', data={'model': SELECTED_MODEL, 'loaded': False}),
    
    # Loading indicator
    html.Div(id='loading-indicator', style={'display': 'none'}),
    
    # Trigger automático na inicialização
    dcc.Input(id='initialize-trigger', type='hidden', value='init'),
    
    header,
    
    html.Div([
        left_panel,
        results_container,
        html.Div([
            dcc.Download(id="download-dataframe-xlsx"),
        ], style={"display": "none"}),
    ], style=styles['container']),
])

# 2. Callback para carregar modelo automaticamente na inicialização
@app.callback(
    Output('embedding-cache', 'data'),
    Output('search-status', 'children'),
    Output('search-status', 'style'),
    Input('initialize-trigger', 'value'),
    prevent_initial_call=False  # Executar ao iniciar
)
def initialize_app(trigger):
    """Carrega o modelo padrão automaticamente na inicialização."""
    global EMBEDDINGS_DICT, FAISS_INDEX, INDEX_KEYS, SELECTED_MODEL, EMBEDDING_DIM
    
    model = SELECTED_MODEL  # Usar o modelo padrão (text-embedding-3-large)
    
    try:
        # Carregar embeddings
        embeddings_dict = load_embeddings(model)
        if not embeddings_dict:
            return {'model': model, 'loaded': False}, f"Erro ao carregar modelo {model}", {'color': '#D32F2F', 'fontWeight': 'bold'}
        
        # Criar índice FAISS
        faiss_index, keys = create_faiss_index(embeddings_dict, EMBEDDING_DIM)
        
        # Atualizar variáveis globais
        EMBEDDINGS_DICT = embeddings_dict
        FAISS_INDEX = faiss_index
        INDEX_KEYS = keys
        
        return {'model': model, 'loaded': True}, f"Modelo {model} carregado ({len(embeddings_dict)} itens)", {'color': '#4CAF50', 'fontWeight': 'bold'}
    except Exception as e:
        debug_print(f"Erro ao carregar embeddings: {e}")
        return {'model': model, 'loaded': False}, f"Erro ao carregar: {str(e)[:30]}...", {'color': '#D32F2F', 'fontWeight': 'bold'}

# 3. Modificar o callback de carregamento do modelo para evitar conflitos
@app.callback(
    Output('embedding-cache', 'data', allow_duplicate=True),
    Output('search-status', 'children', allow_duplicate=True),
    Output('search-status', 'style', allow_duplicate=True),
    Input('model-dropdown', 'value'),
    State('embedding-cache', 'data'),
    prevent_initial_call=True
)
def load_embeddings_for_model(model, cache):
    global EMBEDDINGS_DICT, FAISS_INDEX, INDEX_KEYS, SELECTED_MODEL, EMBEDDING_DIM
    
    if model == cache.get('model') and cache.get('loaded', False):
        # Já carregado, nada a fazer
        raise dash.exceptions.PreventUpdate
    
    try:
        # Atualizar variáveis globais
        SELECTED_MODEL = model
        EMBEDDING_DIM = get_embedding_dimension(model)
        
        # Carregar embeddings
        embeddings_dict = load_embeddings(model)
        if not embeddings_dict:
            return {'model': model, 'loaded': False}, f"Erro ao carregar modelo {model}", {'color': '#D32F2F', 'fontWeight': 'bold'}
        
        # Criar índice FAISS
        faiss_index, keys = create_faiss_index(embeddings_dict, EMBEDDING_DIM)
        
        # Atualizar variáveis globais
        EMBEDDINGS_DICT = embeddings_dict
        FAISS_INDEX = faiss_index
        INDEX_KEYS = keys
        
        return {'model': model, 'loaded': True}, f"Modelo {model} carregado ({len(embeddings_dict)} itens)", {'color': '#4CAF50', 'fontWeight': 'bold'}
    except Exception as e:
        debug_print(f"Erro ao carregar embeddings: {e}")
        return {'model': model, 'loaded': False}, f"Erro: {str(e)[:30]}...", {'color': '#D32F2F', 'fontWeight': 'bold'}

# 4. Adicionar suporte para tecla Enter no campo de texto
@app.callback(
    Output('submit-button-content', 'n_clicks', allow_duplicate=True),
    Input('query-input', 'n_submit'),
    State('query-input', 'value'),
    State('submit-button-content', 'n_clicks'),
    prevent_initial_call=True
)
def submit_on_enter(n_submit, query_text, current_clicks):
    """Aciona o botão de busca quando o usuário pressiona Enter."""
    if not query_text or not query_text.strip():
        raise dash.exceptions.PreventUpdate
    
    # Incrementar o número de cliques para simular um clique no botão
    return (current_clicks or 0) + 1

# 5. Modificar o input_container para melhorar a usabilidade
input_container = html.Div([
    dcc.Textarea(
        id='query-input',
        placeholder='Digite sua consulta aqui e pressione Enter ou clique em "Buscar"...',
        style={
            'width': '100%', 
            'height': '50px',  # ~ 2 linhas
            'marginBottom': '10px', 
            'fontFamily': 'Consolas, monospace', 
            'fontSize': '12px',
            'resize': 'none',  # Fixo em 2 linhas
            'whiteSpace': 'pre-wrap',
            'border': 'none',
            'outline': 'none',
            'padding': '8px',
            'backgroundColor': '#FFFFFF'
        }
    ),
    html.Button(
        html.Div([
            html.I(className="fas fa-search", style={'marginRight': '5px'}),
            "Buscar Similares"
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
        id='submit-button-content',
        style={
            'backgroundColor': '#FF5722',
            'color': 'white',
            'border': 'none',
            'padding': '10px 15px',
            'borderRadius': '25px',  # Botão mais arredondado
            'width': '100%',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )
], style=styles['input_container'])

# 6. Modificar o callback de processamento para evitar conflitos
@app.callback(
    Output('query-history-store', 'data'),
    Output('results-store', 'data'),
    Output('errors-store', 'data'),
    Output('counter-store', 'data'),
    Output('processing-state', 'data'),
    Input('submit-button-content', 'n_clicks'),
    State('query-input', 'value'),
    State('query-history-store', 'data'),
    State('results-store', 'data'),
    State('errors-store', 'data'),
    State('counter-store', 'data'),
    State('embedding-cache', 'data'),
    prevent_initial_call=True
)
def process_search_query(n_clicks, query_text, history, results, errors, counter, cache):
    if not query_text or not query_text.strip():
        raise dash.exceptions.PreventUpdate
    
    # Verificar se embeddings foram carregados
    if not cache.get('loaded', False):
        new_error = {
            'id': str(counter),
            'query': query_text,
            'message': "Modelo de embeddings não carregado",
            'details': "Selecione um modelo de embeddings válido e aguarde o carregamento.",
            'timestamp': datetime.now().isoformat()
        }
        updated_errors = errors + [new_error]
        
        new_history_item = {
            'id': str(counter),
            'query': query_text,
            'timestamp': datetime.now().isoformat(),
            'error': "Modelo não carregado",
            'count': 0
        }
        updated_history = history + [new_history_item]
        
        return updated_history, results, updated_errors, counter + 1, False
    
    try:
        # Buscar itens similares
        search_results, confidence, processed_query = search_similar_items(
            query_text, 
            SELECTED_MODEL, 
            EMBEDDINGS_DICT, 
            FAISS_INDEX, 
            INDEX_KEYS
        )
        
        # Adicionar ao histórico
        new_history_item = {
            'id': str(counter),
            'query': query_text,
            'processed_query': processed_query,
            'timestamp': datetime.now().isoformat(),
            'confidence': confidence,
            'count': len(search_results)
        }
        updated_history = history + [new_history_item]
        
        # Adicionar aos resultados
        new_result = {
            'id': str(counter),
            'query': query_text,
            'processed_query': processed_query,
            'data': search_results,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
        updated_results = results + [new_result]
        
        return updated_history, updated_results, errors, counter + 1, False
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        # Adicionar ao histórico como erro
        new_history_item = {
            'id': str(counter),
            'query': query_text,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'count': 0
        }
        updated_history = history + [new_history_item]
        
        # Adicionar aos erros
        new_error = {
            'id': str(counter),
            'query': query_text,
            'message': error_msg,
            'details': stack_trace,
            'timestamp': datetime.now().isoformat()
        }
        updated_errors = errors + [new_error]
        
        return updated_history, results, updated_errors, counter + 1, False

# Callback para download de Excel
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
            items = result_data['data']
            
            # Preparar dados para o Excel
            excel_data = []
            for item in items:
                details = item.get('details', {})
                row = {
                    'Rank': item.get('rank', 0),
                    'ID': item.get('id', ''),
                    'Similaridade': item.get('similarity', 0),
                    'Órgão': details.get('orgaoEntidade_razaosocial', '') if details else '',
                    'Unidade': details.get('unidadeOrgao_nomeUnidade', '') if details else '',
                    'Município': details.get('unidadeOrgao_municipioNome', '') if details else '',
                    'UF': details.get('unidadeOrgao_ufSigla', '') if details else '',
                    'Valor': details.get('valorTotalHomologado', 0) if details else 0,
                    'Data Abertura': details.get('dataAberturaProposta', '') if details else '',
                    'Data Encerramento': details.get('dataEncerramentoProposta', '') if details else '',
                    'Descrição': details.get('descricaoCompleta', '') if details else ''
                }
                excel_data.append(row)
            
            df = pd.DataFrame(excel_data)
            
            # Generate Excel in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Resultados', index=False)
                
                # Ajustar largura das colunas
                worksheet = writer.sheets['Resultados']
                for i, col in enumerate(df.columns):
                    column_len = max(df[col].astype(str).map(len).max(), len(col)) + 3
                    worksheet.set_column(i, i, column_len)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Busca_Similaridade_{clicked_id}_{timestamp}.xlsx"
            
            debug_print(f"Preparando download do arquivo: {filename}")
            return dcc.send_bytes(output.getvalue(), filename)
    except Exception as e:
        debug_print(f"Erro ao fazer download: {e}")
        debug_print(traceback.format_exc())
        
    raise PreventUpdate

# Callback para atualizar o botão durante processamento
@app.callback(
    Output('submit-button-content', 'children'),
    Output('submit-button-content', 'disabled'),
    Output('submit-button-content', 'style'),
    [Input('processing-state', 'data')],
    [State('submit-button-content', 'style')]
)
def update_button_state(is_processing, current_style):
    if is_processing:
        # Quando estiver processando, mostra apenas "Buscar" com spinner circular
        return [
            html.Div([
                html.I(className="fas fa-circle-notch fa-spin", 
                       style={'marginRight': '8px', 'fontSize': '16px'}),
                "Buscar"
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
        ], True, {
            **current_style,
            'opacity': '0.9',
            'backgroundColor': '#FF8A65',  # Cor mais clara para indicar estado de processamento
            'color': 'white',
            'borderRadius': '25px'  # Manter o border-radius consistente
        }
    else:
        # Estado normal - mostra o ícone de busca
        return [
            html.Div([
                html.I(className="fas fa-search", style={'marginRight': '5px'}),
                "Buscar Similares"
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
        ], False, {
            **current_style,
            'opacity': '1',
            'backgroundColor': '#FF5722',
            'color': 'white',
            'borderRadius': '25px'  # Manter o border-radius consistente
        }

# Callback para definir o estado de processamento quando o botão é clicado
@app.callback(
    Output('processing-state', 'data', allow_duplicate=True),
    Input('submit-button-content', 'n_clicks'),
    State('query-input', 'value'),
    prevent_initial_call=True
)
def set_processing_state(n_clicks, query_text):
    if not query_text:
        raise PreventUpdate
        
    debug_print("Iniciando processamento...")
    return True  # Ativa o estado de processamento

# Callback para limpar o campo de entrada após submissão
@app.callback(
    Output('query-input', 'value'),
    Input('counter-store', 'data'),
    prevent_initial_call=True
)
def clear_input_after_submit(counter):
    return ""

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
    app.run_server(debug=True, port=8057, 
                   dev_tools_hot_reload=True, 
                   dev_tools_props_check=False, 
                   dev_tools_ui=False)