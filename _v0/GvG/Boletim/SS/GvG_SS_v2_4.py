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

# Modelo único fixo
SELECTED_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # Dimensão do modelo text-embedding-3-large

# Inicializar NLTK com tratamento de erro
try:
    import nltk
    nltk.download('stopwords', quiet=True)
    
    # Download explícito do wordnet e recursos relacionados
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)  # Open Multilingual WordNet
    
    # Verificar se o wordnet está disponível
    from nltk.corpus import wordnet
    if not wordnet._wordnet_cache:
        debug_print("WordNet inicializado com sucesso")
except Exception as e:
    debug_print(f"Erro ao inicializar NLTK: {str(e)}")

# Variáveis globais para cache
EMBEDDINGS_DICT = None
FAISS_INDEX = None
INDEX_KEYS = None

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {datetime.now()}: {message}")

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
        'whiteSpace': 'pre-wrap'
    },
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'flexDirection': 'column',
        'alignItems': 'stretch',
        'marginTop': 'auto'
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
        'whiteSpace': 'pre-wrap'
    },
    'result_card': {
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'padding': '15px',
        'marginBottom': '20px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
        'position': 'relative'
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
        'fontFamily': 'Arial, sans-serif'
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
        'right': '10px',
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
        'fontFamily': 'Arial, sans-serif'
    }
}

# Funções de embeddings
def preprocess_text(text):
    """Normaliza e limpa o texto para processamento."""
    try:
        text = unidecode.unidecode(str(text))
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        
        # Remover stopwords
        try:
            sw = set(stopwords.words('portuguese'))
            words = text.split()
            words = [word for word in words if word not in sw]
        except Exception as e:
            debug_print(f"Erro ao processar stopwords: {str(e)}")
            words = text.split()
        
        # Lematização com tratamento de erro
        try:
            lemmatizer = WordNetLemmatizer()
            words = [lemmatizer.lemmatize(word) for word in words]
        except Exception as e:
            debug_print(f"Erro na lematização: {str(e)}. Continuando sem lematizar.")
            # Continua sem lematização
            
        return ' '.join(words)
    except Exception as e:
        debug_print(f"Erro no pré-processamento: {str(e)}")
        # Em caso de erro, retorna o texto original mas limpo
        return text.lower()

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
# Container para histórico de consultas
query_history_container = html.Div(id='query-history-container', style=styles['query_container'])

# Container para entrada de texto
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
        n_clicks=0,
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
    ),
    html.Div(id='hidden-div-for-js', style={'display': 'none'})
], style=styles['input_container'])

# Painel esquerdo completo (sem o dropdown de modelo)
left_panel = html.Div([
    query_history_container,
    input_container
], style=styles['left_panel'])

# Painel direito para resultados
results_container = html.Div(id='results-container', style=styles['right_panel'])

# Cabeçalho
header = html.Div([
    # Logo à esquerda
    html.Div([
        html.Img(src=b64_image(LOGO_PATH), style={'height': '40px'}),
        html.H4("Busca por Similaridade", style={'marginLeft': '15px', 'color': '#003A70'})
    ], style={'display': 'flex', 'alignItems': 'center'}),
    
    # Status à direita
    html.Div([
        html.Span(id='search-status', children="Inicializando...", style={
            'color': '#FF5722', 
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
    dcc.Store(id='model-loaded', data=False),
    
    # Trigger automático na inicialização
    dcc.Location(id='url', refresh=False),
    
    header,
    
    html.Div([
        left_panel,
        results_container,
        html.Div([
            dcc.Download(id="download-dataframe-xlsx"),
        ], style={"display": "none"}),
    ], style=styles['container']),
])

# Clientside callback para capturar Enter no textarea
app.clientside_callback(
    """
    function(id) {
        // Adiciona o event listener uma vez
        const textarea = document.getElementById('query-input');
        if (textarea && !textarea.hasAttribute('data-enter-listener')) {
            textarea.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault(); // Previne nova linha
                    document.getElementById('submit-button-content').click();
                }
            });
            textarea.setAttribute('data-enter-listener', 'true');
        }
        return ''; // Não precisa atualizar nada
    }
    """,
    Output('hidden-div-for-js', 'children'),
    Input('url', 'pathname') # Aciona quando a página carrega
)

# Callback para carregar modelo automaticamente na inicialização
@app.callback(
    Output('search-status', 'children'),
    Output('search-status', 'style'),
    Output('model-loaded', 'data'),
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def initialize_app(pathname):
    """Carrega o modelo automaticamente na inicialização."""
    global EMBEDDINGS_DICT, FAISS_INDEX, INDEX_KEYS
    
    try:
        # Carregar embeddings
        embeddings_dict = load_embeddings(SELECTED_MODEL)
        if not embeddings_dict:
            return f"Erro ao carregar modelo {SELECTED_MODEL}", {'color': '#D32F2F', 'fontWeight': 'bold'}, False
        
        # Criar índice FAISS
        faiss_index, keys = create_faiss_index(embeddings_dict, EMBEDDING_DIM)
        
        # Atualizar variáveis globais
        EMBEDDINGS_DICT = embeddings_dict
        FAISS_INDEX = faiss_index
        INDEX_KEYS = keys
        
        return f"Modelo {SELECTED_MODEL} carregado ({len(embeddings_dict)} itens)", {'color': '#4CAF50', 'fontWeight': 'bold'}, True
    except Exception as e:
        debug_print(f"Erro ao carregar embeddings: {e}")
        return f"Erro ao carregar: {str(e)[:30]}...", {'color': '#D32F2F', 'fontWeight': 'bold'}, False

# Callback para atualizar o botão durante processamento
@app.callback(
    Output('submit-button-content', 'children'),
    Output('submit-button-content', 'disabled'),
    Output('submit-button-content', 'style'),
    [Input('processing-state', 'data'),
     Input('model-loaded', 'data')],
    [State('submit-button-content', 'style')]
)
def update_button_state(is_processing, is_model_loaded, current_style):
    if not is_model_loaded:
        # Quando o modelo está carregando, desabilitar o botão
        return [
            html.Div([
                html.I(className="fas fa-cog fa-spin", 
                       style={'marginRight': '8px', 'fontSize': '16px'}),
                "Carregando Modelo..."
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
        ], True, {
            **current_style,
            'opacity': '0.7',
            'backgroundColor': '#FFA726',  # Laranja mais claro
            'color': 'white',
            'borderRadius': '25px'
        }
    elif is_processing:
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
    [State('query-input', 'value'),
     State('model-loaded', 'data')],
    prevent_initial_call=True
)
def set_processing_state(n_clicks, query_text, is_model_loaded):
    if not query_text or not query_text.strip() or not is_model_loaded:
        raise PreventUpdate
        
    debug_print("Iniciando processamento...")
    return True  # Ativa o estado de processamento

# Callback para processar consulta e buscar resultados
@app.callback(
    Output('query-history-store', 'data'),
    Output('results-store', 'data'),
    Output('errors-store', 'data'),
    Output('counter-store', 'data'),
    Output('processing-state', 'data'),
    Input('submit-button-content', 'n_clicks'),
    [State('query-input', 'value'),
     State('query-history-store', 'data'),
     State('results-store', 'data'),
     State('errors-store', 'data'),
     State('counter-store', 'data'),
     State('model-loaded', 'data')],
    prevent_initial_call=True
)
def process_search_query(n_clicks, query_text, history, results, errors, counter, is_model_loaded):
    if not query_text or not query_text.strip():
        raise PreventUpdate
    
    # Verificar se embeddings foram carregados
    if not is_model_loaded:
        new_error = {
            'id': str(counter),
            'query': query_text,
            'message': "Modelo de embeddings não carregado",
            'details': "Aguarde o carregamento do modelo.",
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

# Renderizar histórico de consultas
@app.callback(
    Output('query-history-container', 'children'),
    Input('query-history-store', 'data')
)
def render_query_history(history):
    if not history:
        return []
    
    history_elements = []
    
    for item in reversed(history):  # Mostrar mais recentes primeiro
        # Incluindo informações de debug
        debug_info = html.Div([
            html.Div(f"Timestamp: {item.get('timestamp', 'N/A')}"),
            html.Div(f"Processado: {item.get('processed_query', 'N/A')}"),
            html.Div(f"Confiança: {item.get('confidence', 0):.2f}% | Resultados: {item.get('count', 0)}")
        ], style=styles['debug_info'])
        
        history_elements.append(html.Div([
            html.Div(item['query']),
            debug_info,
            # Adicionando a numeração no canto inferior direito
            html.Div(
                item['id'],
                style=styles['query_number']
            )
        ], style=styles['query_message']))
    
    return history_elements

# Renderizar resultados
@app.callback(
    Output('results-container', 'children'),
    [Input('results-store', 'data'), 
     Input('errors-store', 'data')]
)
def render_results(results, errors):
    result_elements = []
    
    # Renderizar erros primeiro
    if errors:
        for error in reversed(errors):  # Mostrar mais recentes primeiro
            result_elements.append(html.Div([
                html.H5("Erro na Busca", style={'color': '#D32F2F', 'marginBottom': '10px'}),
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
        for result in reversed(results):  # Mostrar mais recentes primeiro
            try:
                # Adicionar informações de cabeçalho
                header_info = html.Div([
                    html.H5(f"Resultados para: \"{result.get('query', 'Consulta desconhecida')}\"", 
                           style={'color': '#003A70', 'marginBottom': '5px'}),
                    html.Div([
                        html.Span(f"Confiança: ", style={'fontWeight': 'bold'}),
                        html.Span(f"{result.get('confidence', 0):.2f}%")
                    ], style={'marginBottom': '10px', 'color': '#1976D2'}),
                    html.Div([
                        html.Span(f"Timestamp: {result.get('timestamp', 'N/A')} | "),
                        html.Span(f"Total de resultados: {len(result.get('data', []))}"),
                    ], style={'fontSize': '12px', 'color': '#666', 'marginBottom': '10px'})
                ])
                
                # Tabela resumida
                items_data = result.get('data', [])
                if items_data:
                    table_data = []
                    for item in items_data:
                        details = item.get('details', {})
                        table_data.append({
                            'Rank': item.get('rank', 0),
                            'ID': item.get('id', 'N/A'),
                            'Similaridade': f"{item.get('similarity', 0):.4f}",
                            'Valor': format_currency(details.get('valorTotalHomologado', 0)) if details else "N/A",
                            'Data Encerramento': details.get('dataEncerramentoProposta', 'N/A') if details else "N/A"
                        })
                    
                    table = dash_table.DataTable(
                        data=table_data,
                        columns=[
                            {'name': 'Rank', 'id': 'Rank', 'width': '10%'},
                            {'name': 'ID', 'id': 'ID', 'width': '40%'},
                            {'name': 'Similaridade', 'id': 'Similaridade', 'width': '15%'},
                            {'name': 'Valor', 'id': 'Valor', 'width': '20%'},
                            {'name': 'Data Encerramento', 'id': 'Data Encerramento', 'width': '15%'}
                        ],
                        style_table={
                            'overflowX': 'auto',
                            'width': '100%'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'maxWidth': '0',
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
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}
                        ],
                        tooltip_duration=None,
                        page_size=10
                    )

                    # Detalhes de cada resultado
                    details_panels = []
                    for item in items_data:
                        details = item.get('details', {})
                        if details:
                            # Preparar o texto da descrição
                            descricao = highlight_key_terms(
                                details.get('descricaoCompleta', 'N/A'),
                                set(result.get('processed_query', '').split())
                            )
                            
                            # Criar card para cada resultado
                            details_panels.append(html.Div([
                                html.H6(f"#{item['rank']} - {item['id']} (Similaridade: {item['similarity']:.4f})",
                                       style={'borderBottom': '1px solid #eee', 'paddingBottom': '8px', 'marginBottom': '10px'}),
                                html.Div([
                                    html.Div([
                                        html.Span("Órgão: ", style={'fontWeight': 'bold'}),
                                        html.Span(details.get('orgaoEntidade_razaosocial', 'N/A'))
                                    ], style={'marginBottom': '5px'}),
                                    html.Div([
                                        html.Span("Unidade: ", style={'fontWeight': 'bold'}),
                                        html.Span(details.get('unidadeOrgao_nomeUnidade', 'N/A'))
                                    ], style={'marginBottom': '5px'}),
                                    html.Div([
                                        html.Span("Local: ", style={'fontWeight': 'bold'}),
                                        html.Span(f"{details.get('unidadeOrgao_municipioNome', 'N/A')}/{details.get('unidadeOrgao_ufSigla', 'N/A')}")
                                    ], style={'marginBottom': '5px'}),
                                    html.Div([
                                        html.Span("Valor: ", style={'fontWeight': 'bold'}),
                                        html.Span(format_currency(details.get('valorTotalHomologado', 0)))
                                    ], style={'marginBottom': '5px'}),
                                    html.Div([
                                        html.Span("Datas: ", style={'fontWeight': 'bold'}),
                                        html.Span(f"Abertura: {details.get('dataAberturaProposta', 'N/A')} | Encerramento: {details.get('dataEncerramentoProposta', 'N/A')}")
                                    ], style={'marginBottom': '10px'}),
                                    html.Div([
                                        html.Span("Descrição:", style={'fontWeight': 'bold'}),
                                        html.Div(descricao, style={
                                            'whiteSpace': 'pre-line',
                                            'marginTop': '5px',
                                            'padding': '8px',
                                            'backgroundColor': '#f9f9f9',
                                            'borderRadius': '5px',
                                            'fontSize': '12px'
                                        })
                                    ])
                                ])
                            ], style={
                                'border': '1px solid #ddd',
                                'borderRadius': '5px',
                                'padding': '10px',
                                'marginBottom': '10px',
                                'backgroundColor': 'white'
                            }))
                    
                    # Botões de ação
                    action_buttons = html.Div([
                        html.Button(
                            html.I(className="fas fa-download"),
                            id={'type': 'download-btn', 'index': result['id']},
                            style={
                                'backgroundColor': '#4CAF50',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'padding': '5px 10px',
                                'marginTop': '10px'
                            },
                            title="Baixar como Excel"
                        ),
                    ], style={'display': 'flex', 'justifyContent': 'flex-end'})
                    
                    # Montar o container de resultados completo
                    result_elements.append(html.Div([
                        header_info,
                        table,
                        html.H6("Detalhes dos resultados:", 
                              style={'marginTop': '20px', 'marginBottom': '10px', 'color': '#003A70'}),
                        html.Div(details_panels),
                        action_buttons,
                        html.Div(
                            result['id'],
                            style=styles['result_number']
                        )
                    ], style={
                        **styles['result_card'],
                        'overflow': 'hidden'
                    }))
            except Exception as e:
                debug_print(f"Erro ao renderizar resultado {result.get('id', '?')}: {e}")
                debug_print(traceback.format_exc())
    
    return result_elements

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
    app.run_server(debug=True, port=8057)