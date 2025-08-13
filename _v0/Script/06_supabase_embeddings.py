# =======================================================================
# [6/7] PROCESSAMENTO DE EMBEDDINGS E INTEGRAÇÃO COM SUPABASE - VERSÃO V2
# =======================================================================
# Este script processa os dados de contratações, gera embeddings usando
# a API da OpenAI e os insere no banco Supabase para busca semântica.
# 
# VERSÃO V2 - CAMPOS EXTRAS + FASE 3 CATEGORIZAÇÃO AUTOMÁTICA:
# - Inclui todos os campos extras baixados pelo 01_pncp_download_v2.py
# - Sincroniza com a estrutura completa da base local
# - Atualiza tanto dados principais quanto campos extras no Supabase
# - FASE 3: Categorização automática dos embeddings inseridos/atualizados
# 
# Funcionalidades:
# - FASE 1: Pré-processamento de texto e geração de embeddings via API OpenAI
# - FASE 2: Inserção de dados e vetores no Supabase com todos os campos extras
# - FASE 3: Categorização automática usando busca pgvector e paralelismo
# - Processamento paralelo com múltiplas barras de progresso
# - Armazenamento local de cache de embeddings
# - Monitoramento detalhado do processamento
# 
# Resultado: Base de dados vetorial completa com categorização automática.
# =======================================================================

import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import threading
import random
import shutil
import math
import datetime
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from openai import OpenAI

import re
import unidecode
import nltk
import os
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Imports específicos para FASE 3 - Categorização automática
# Note: Usando create_connection local e calculate_confidence implementada abaixo


# Configure Rich console
console = Console()

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))
load_dotenv(os.path.join(script_dir, "openai.env"))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))


# Fetch connection variables
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Base paths from files.env
DATA_PATH = os.getenv("DATA_PATH")
NEW_PATH = os.getenv("NEW_PATH")
OLD_PATH = os.getenv("OLD_PATH")
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH")


# Configurações para processamento paralelo
MAX_WORKERS = 10
BATCH_SIZE = 100

# Lock para controle de concorrência
stats_lock = threading.Lock()
embedding_lock = threading.Lock()

# Configuração OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Estatísticas globais
global_stats = {
    'contratacoes_inseridas': 0,
    'embeddings_inseridos': 0,
    'contratacoes_duplicadas': 0,
    'embeddings_duplicados': 0,
    'embeddings_gerados': 0,
    'embeddings_pulados': 0,
    'erros': 0
}

# Configuração de embeddings
EMBEDDING_DIM = 3072
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_MODEL_INDEX = 1

# Modelos disponíveis
EMBEDDING_MODELS = {
    0: "text-embedding-3-small",
    1: "text-embedding-3-large",
    2: "text-embedding-ada-002"
}

# ===== CONFIGURAÇÕES PARA FASE 3 - CATEGORIZAÇÃO AUTOMÁTICA =====
# TOP K categorias para busca pgvector
TOP_K = 5
# Estatísticas da FASE 3
fase3_stats = {
    'worker_stats': {},
    'total_processed': 0,
    'total_updated': 0,
    'total_errors': 0
}
fase3_stats_lock = threading.Lock()

# Função auxiliar para calcular confidence (implementação local)
def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações"""
    import math
    
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    
    # Verificar se top_score é zero para evitar divisão por zero
    if top_score == 0.0:
        return 0.0
    
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = (1 - math.exp(-10 * weighted_gap))
    
    return confidence

# Variável global para as opções de pré-processamento
preprocessing_options = {}

# Garantir que os recursos NLTK necessários estão disponíveis
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
except:
    console.print("[yellow]Aviso: Alguns recursos NLTK não puderam ser baixados[/yellow]")

#############################################
# FUNÇÕES DE EMBEDDINGS E PRÉ-PROCESSAMENTO
#############################################

def gvg_create_embedding_filename(base_path, model_index, preproc_options):
    """Cria nome de arquivo de embeddings baseado no modelo e nas opções de pré-processamento"""
    preproc_code = (
        f"{'A' if preproc_options['remove_accents'] else 'a'}"
        f"{'X' if preproc_options['remove_special_chars'] else 'x'}"
        f"{'S' if preproc_options['keep_separators'] else 's'}"
        f"{'C' if preproc_options['case'] == 'upper' else 'c' if preproc_options['case'] == 'lower' else 'o'}"
        f"{'W' if preproc_options['remove_stopwords'] else 'w'}"
        f"{'L' if preproc_options['lemmatize'] else 'l'}"
    )
    
    return os.path.join(base_path, f"GvG_embeddings_{model_index}_{preproc_code}.pkl")

def gvg_parse_embedding_filename(filename):
    """Analisa um nome de arquivo de embeddings para extrair o modelo e as opções de pré-processamento"""
    basename = os.path.basename(filename)
    
    # Verificar se o formato do nome é válido
    parts = basename.split('_')
    if len(parts) < 3 or not basename.endswith('.pkl'):
        raise ValueError(f"Formato de nome de arquivo inválido: {basename}")
    
    # Extrair o índice do modelo e o código de pré-processamento
    try:
        model_index = int(parts[-2])
        if model_index not in EMBEDDING_MODELS:
            raise ValueError(f"Índice de modelo inválido: {model_index}")
    except ValueError:
        raise ValueError(f"Índice de modelo não é um número válido: {parts[-2]}")
    
    preproc_code = parts[-1].replace('.pkl', '')
    
    # Obter o nome do modelo a partir do índice
    model_name = EMBEDDING_MODELS[model_index]
    
    # Verificar se o código de pré-processamento tem o formato correto
    if len(preproc_code) != 6:
        raise ValueError(f"Código de pré-processamento inválido: {preproc_code}")
    
    # Extrair as opções de pré-processamento
    preproc_options = {
        "remove_accents": preproc_code[0] == 'A',
        "remove_special_chars": preproc_code[1] == 'X',
        "keep_separators": preproc_code[2] == 'S',
        "case": "upper" if preproc_code[3] == 'C' else "lower" if preproc_code[3] == 'c' else "original",
        "remove_stopwords": preproc_code[4] == 'W',
        "lemmatize": preproc_code[5] == 'L'
    }
    
    return model_name, model_index, preproc_options

def gvg_pre_processing(text, 
                      remove_accents=True, 
                      remove_special_chars=True, 
                      keep_separators=False, 
                      case='lower', 
                      remove_stopwords=True, 
                      lemmatize=True):
    """Aplica pré-processamento ao texto conforme as opções especificadas"""
    
    # Conversão para string se necessário
    if pd.isna(text) or text is None:
        return ""
    
    text = str(text)
    
    # Remover acentos se configurado
    if remove_accents:
        text = unidecode.unidecode(text)
    
    # Conversão de caso
    if case == 'lower':
        text = text.lower()
    elif case == 'upper':
        text = text.upper()
    # Se case == 'original', não fazer nada
    
    # Remover caracteres especiais
    if remove_special_chars:
        if keep_separators:
            # Manter alguns separadores gráficos
            if remove_accents:
                # Se acentos forem removidos, usar apenas letras ASCII
                if case == 'lower':
                    pattern = r'[^a-z0-9\s:;,.!?_\-]'
                elif case == 'upper':
                    pattern = r'[^A-Z0-9\s:;,.!?_\-]'
                else:  # original
                    pattern = r'[^a-zA-Z0-9\s:;,.!?_\-]'
            else:
                # Se acentos forem mantidos, incluir caracteres acentuados
                if case == 'lower':
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s:;,.!?_\-]'
                elif case == 'upper':
                    pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
                else:  # original
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
            
            # Manter letras, números, espaços e separadores gráficos comuns
            text = re.sub(pattern, '', text)
        else:
            # Padrão para remover tudo exceto letras, números e espaços
            if remove_accents:
                # Se acentos forem removidos, usar apenas letras ASCII
                if case == 'lower':
                    pattern = r'[^a-z0-9\s]'
                elif case == 'upper':
                    pattern = r'[^A-Z0-9\s]'
                else:  # original
                    pattern = r'[^a-zA-Z0-9\s]'
            else:
                # Se acentos forem mantidos, incluir caracteres acentuados
                if case == 'lower':
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s]'
                elif case == 'upper':
                    pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
                else:  # original
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
            
            # Remover tudo exceto letras, números e espaços
            text = re.sub(pattern, '', text)
    
    # Dividir o texto em palavras
    words = text.split()
    
    # Remover stopwords se configurado
    if remove_stopwords:
        sw = set(stopwords.words('portuguese'))
        # Considerar a caixa das stopwords
        if case == 'lower':
            words = [word for word in words if word.lower() not in sw]
        elif case == 'upper':
            words = [word for word in words if word.lower() not in sw]
        else:  # original
            words = [word for word in words if word.lower() not in sw]
    
    # Aplicar lematização se configurado
    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        words = [lemmatizer.lemmatize(word) for word in words]
    
    return ' '.join(words)

def generate_embeddings_batch(texts, model=EMBEDDING_MODEL, max_retries=3, retry_delay=2):
    """Gera embeddings para um lote de textos usando a API OpenAI"""
    if not texts:
        return []
    
    # Validar e limpar textos
    validated_batch = []
    for text in texts:
        # Converter para string se não for
        if not isinstance(text, str):
            text = str(text)
            
        # Verificar se a string não está vazia após processamento
        if not text.strip():
            text = " "  # Espaço em branco para evitar erro de string vazia
            
        # Limitar tamanho se necessário (OpenAI tem limite de tokens)
        if len(text) > 8000:
            text = text[:8000]
            
        validated_batch.append(text)
    
    # Verificação final: batch não pode estar vazio
    if not validated_batch:
        validated_batch = [" "]
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=validated_batch
            )
            
            # Garantir que cada embedding tenha a dimensão correta
            results = []
            for item in response.data:
                emb = np.array(item.embedding, dtype=np.float32)
                # Verificar dimensão do embedding recebido
                if emb.shape != (EMBEDDING_DIM,):
                    console.print(f"[yellow]Aviso: Embedding recebido com formato {emb.shape} em vez de ({EMBEDDING_DIM},). Ajustando...[/yellow]")
                    if len(emb) > EMBEDDING_DIM:
                        # Truncar se maior
                        emb = emb[:EMBEDDING_DIM]
                    else:
                        # Preencher com zeros se menor
                        padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                        padded[:len(emb)] = emb
                        emb = padded
                results.append(emb)
            return results
            
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                console.print(f"[bold yellow]Detalhes do batch: {len(validated_batch)} itens[/bold yellow]")
                raise
    
    return []

#############################################
# FUNÇÕES DE BANCO DE DADOS
#############################################

def create_connection():
    """Cria conexão com o banco PostgreSQL"""
    try:
        connection = psycopg2.connect(
            host=HOST,
            database=DBNAME,
            user=USER,
            password=PASSWORD,
            port=PORT
        )
        return connection
    except Exception as e:
        console.print(f"[bold red]Erro ao conectar ao banco: {e}[/bold red]")
        return None

def execute_with_retry(cursor, sql, data, worker_id=None, max_retries=3):
    """Executa query com retry automático"""
    for attempt in range(max_retries):
        try:
            cursor.execute(sql, data)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    if worker_id:
                        console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            if worker_id:
                console.print(f"[red]Worker {worker_id} - Erro definitivo: {e}[/red]")
            raise
    return False

def execute_batch_with_retry(cursor, sql, data_list, worker_id, max_retries=3):
    """Executa inserção em lote com retry"""
    for attempt in range(max_retries):
        try:
            # Usar batch_size igual ao tamanho da lista para inserção única
            execute_values(cursor, sql, data_list, template=None, page_size=len(data_list))
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            console.print(f"[red]Worker {worker_id} - Erro definitivo em lote: {e}[/red]")
            raise
    return False

def load_existing_records(connection):
    """Carrega registros existentes para verificação de duplicatas"""
    cursor = connection.cursor()
    try:
        # Carregar IDs com commit read
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        
        # Carregar IDs de contratações existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes")
        existing_contracts = set(row[0] for row in cursor.fetchall())
        
        # Carregar IDs de embeddings existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes_embeddings")
        existing_embeddings = set(row[0] for row in cursor.fetchall())
        
        # Finalizar a transação de leitura
        connection.commit()
        
        console.print(f"[cyan]Contratações existentes: {len(existing_contracts)}[/cyan]")
        console.print(f"[cyan]Embeddings existentes: {len(existing_embeddings)}[/cyan]")
        
        return existing_contracts, existing_embeddings
    except Exception as e:
        console.print(f"[red]Erro ao carregar registros existentes: {e}[/red]")
        return set(), set()
    finally:
        cursor.close()

def clean_value_for_db(value):
    """Limpa valores para inserção no banco, convertendo NaT/NaN para None"""
    if pd.isna(value):
        return None
    return value

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

def partition_dataframe(df, num_partitions):
    """Divide DataFrame em partições para processamento paralelo"""
    partition_size = len(df) // num_partitions
    remainder = len(df) % num_partitions
    
    partitions = []
    start = 0
    
    for i in range(num_partitions):
        # Distribuir o remainder entre as primeiras partições
        end = start + partition_size + (1 if i < remainder else 0)
        if start < len(df):
            partitions.append(df.iloc[start:end])
        start = end
    
    return partitions

def load_or_create_embeddings_cache():
    """Carrega ou cria cache de embeddings"""
    global preprocessing_options
    
    # Verificar se o diretório existe
    if not os.path.exists(EMBEDDINGS_PATH):
        os.makedirs(EMBEDDINGS_PATH)
    
    # Buscar arquivos de embeddings existentes
    embedding_files = [f for f in os.listdir(EMBEDDINGS_PATH) if f.startswith('GvG_embeddings_') and f.endswith('.pkl')]
    
    if embedding_files:
        # Ordenar por data de modificação (mais recente primeiro)
        embedding_files.sort(key=lambda x: os.path.getmtime(os.path.join(EMBEDDINGS_PATH, x)), reverse=True)
        
        # Tentar usar o arquivo mais recente
        try:
            latest_file = embedding_files[0]
            latest_path = os.path.join(EMBEDDINGS_PATH, latest_file)
            
            # Analisar o arquivo mais recente para extrair configurações
            model_name, model_idx, detected_options = gvg_parse_embedding_filename(latest_path)
            
            # Verificar se o modelo é compatível
            if model_idx == EMBEDDING_MODEL_INDEX:
                # Modelo compatível - usar este arquivo
                preprocessing_options = detected_options
                console.print(f"[green]Encontrado arquivo de embeddings: {latest_file}[/green]")
                console.print(f"[green]Usando configurações detectadas: {preprocessing_options}[/green]")
                return latest_path
            else:
                # Modelo incompatível - procurar outro arquivo com o modelo correto
                console.print(f"[yellow]Arquivo mais recente usa modelo incompatível: {model_name} (índice {model_idx})[/yellow]")
                console.print(f"[yellow]Procurando outro arquivo com o modelo {EMBEDDING_MODEL} (índice {EMBEDDING_MODEL_INDEX})...[/yellow]")
                
                # Procurar nos outros arquivos
                for file in embedding_files[1:]:
                    file_path = os.path.join(EMBEDDINGS_PATH, file)
                    try:
                        file_model_name, file_model_idx, file_options = gvg_parse_embedding_filename(file_path)
                        if file_model_idx == EMBEDDING_MODEL_INDEX:
                            # Encontramos um arquivo com o modelo correto
                            preprocessing_options = file_options
                            console.print(f"[green]Encontrado arquivo compatível: {file}[/green]")
                            console.print(f"[green]Usando configurações detectadas: {preprocessing_options}[/green]")
                            return file_path
                    except Exception as e:
                        console.print(f"[yellow]Erro ao analisar arquivo {file}: {e}[/yellow]")
                        continue
        
        except Exception as e:
            console.print(f"[yellow]Erro ao analisar o arquivo mais recente: {e}[/yellow]")
            # Tentativa de fallback: usar qualquer arquivo válido
            for file in embedding_files[1:]:
                try:
                    file_path = os.path.join(EMBEDDINGS_PATH, file)
                    model_name, model_idx, detected_options = gvg_parse_embedding_filename(file_path)
                    preprocessing_options = detected_options
                    console.print(f"[yellow]Usando arquivo alternativo: {file}[/yellow]")
                    console.print(f"[yellow]Configurações detectadas: {preprocessing_options}[/yellow]")
                    return file_path
                except Exception:
                    continue
        
        # Se chegou aqui, não encontrou nenhum arquivo válido ou compatível
        # Definir opções padrão
        preprocessing_options = {
            "remove_special_chars": True,     # a: True
            "keep_separators": False,         # X: False
            "remove_accents": True,           # S: True
            "case": "lower",                  # o: lower
            "remove_stopwords": True,         # w: True
            "lemmatize": True                 # l: True
        }
        console.print("[yellow]Não foi possível encontrar um arquivo compatível. Usando configurações padrão (aXSowl).[/yellow]")
        
        # Criar novo arquivo com o modelo desejado e opções padrão
        new_filename = gvg_create_embedding_filename(EMBEDDINGS_PATH, EMBEDDING_MODEL_INDEX, preprocessing_options)
        return new_filename
    
    else:
        # Não há arquivos de embeddings - criar com configurações padrão
        preprocessing_options = {
            "remove_special_chars": True,     # a: True
            "keep_separators": False,         # X: False
            "remove_accents": True,           # S: True
            "case": "lower",                  # o: lower
            "remove_stopwords": True,         # w: True
            "lemmatize": True                 # l: True
        }
        console.print("[yellow]Nenhum arquivo de embeddings encontrado. Criando novo com configurações padrão.[/yellow]")
        
        # Criar novo arquivo
        new_filename = gvg_create_embedding_filename(EMBEDDINGS_PATH, EMBEDDING_MODEL_INDEX, preprocessing_options)
        return new_filename

#############################################
# FUNÇÕES DE PROCESSAMENTO
#############################################

def process_embedding_batch(worker_id, batch_df, embeddings_dict, progress, task_id):
    """Processa um lote de descrições para geração de embeddings"""
    local_embeddings = {}
    local_stats = {'embeddings_gerados': 0, 'embeddings_pulados': 0, 'erros': 0}
    
    try:
        # Preparar textos para processamento em sublotes de BATCH_SIZE
        texts_to_process = []
        ids_to_process = []
        
        # Pré-processar as descrições e preparar para embeddings
        for idx, row in batch_df.iterrows():
            try:
                numero_controle = str(row['numeroControlePNCP'])
                
                # VERIFICAR SE JÁ EXISTE NO DICIONÁRIO DE EMBEDDINGS
                if numero_controle in embeddings_dict:
                    # Já temos o embedding para este ID, pular
                    local_stats['embeddings_pulados'] += 1
                    # Atualizar progresso mesmo para itens pulados
                    progress.update(task_id, advance=1)
                    continue
                
                # Pré-processar o texto usando as opções configuradas
                processed_text = gvg_pre_processing(
                    row['descricaoCompleta'],
                    remove_special_chars=preprocessing_options['remove_special_chars'],
                    keep_separators=preprocessing_options['keep_separators'],
                    remove_accents=preprocessing_options['remove_accents'],
                    case=preprocessing_options['case'],
                    remove_stopwords=preprocessing_options['remove_stopwords'],
                    lemmatize=preprocessing_options['lemmatize']
                )
                
                texts_to_process.append(processed_text)
                ids_to_process.append(numero_controle)
                
            except Exception as e:
                console.print(f"[red]Worker {worker_id} - Erro ao pré-processar texto {idx}: {e}[/red]")
                local_stats['erros'] += 1
                progress.update(task_id, advance=1)  # Atualizar progresso mesmo para erros
        
        # Se não há textos para processar, retornar
        if not texts_to_process:
            console.print(f"[yellow]Worker {worker_id} - Nenhum texto novo para processar (todos já existem)[/yellow]")
            return local_embeddings, local_stats
        
        # Processar em sublotes
        for i in range(0, len(texts_to_process), BATCH_SIZE):
            sublote_texts = texts_to_process[i:i + BATCH_SIZE]
            sublote_ids = ids_to_process[i:i + BATCH_SIZE]
            
            try:
                # Gerar embeddings para o sublote
                embeddings = generate_embeddings_batch(sublote_texts, EMBEDDING_MODEL)
                
                # Associar embeddings aos IDs
                for embedding, numero_controle in zip(embeddings, sublote_ids):
                    local_embeddings[numero_controle] = embedding
                    local_stats['embeddings_gerados'] += 1
                
                # Atualizar progresso
                progress.update(task_id, advance=len(sublote_texts))
                
            except Exception as e:
                console.print(f"[red]Worker {worker_id} - Erro ao gerar embeddings para sublote: {e}[/red]")
                local_stats['erros'] += len(sublote_texts)
                progress.update(task_id, advance=len(sublote_texts))
        
        # Adicionar embeddings locais ao dicionário global (thread-safe)
        with embedding_lock:
            embeddings_dict.update(local_embeddings)
        
        return local_embeddings, local_stats
    
    except Exception as e:
        console.print(f"[red]Worker {worker_id} - Erro geral no batch de embeddings: {e}[/red]")
        local_stats['erros'] += len(batch_df)
        return {}, local_stats

def process_db_batch(worker_id, batch_df, embeddings_dict, existing_contracts, existing_embeddings, progress, task_id):
    """Processa um lote para inserção no banco de dados com TODOS OS CAMPOS EXTRAS"""
    # Criar conexão dedicada para este worker
    connection = create_connection()
    if not connection:
        console.print(f"[bold red]Worker {worker_id} não conseguiu criar conexão![/bold red]")
        return {
            'contratacoes_inseridas': 0,
            'embeddings_inseridos': 0,
            'contratacoes_duplicadas': 0,
            'embeddings_duplicados': 0,
            'erros': len(batch_df)
        }
    
    cursor = connection.cursor()
    
    # Estatísticas locais para este worker
    local_stats = {
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'erros': 0
    }
    
    try:
        # Processar registros em lotes menores para atualizar o progresso frequentemente
        for i in range(0, len(batch_df), BATCH_SIZE):
            sublote = batch_df.iloc[i:i+BATCH_SIZE]
            
            contract_data = []
            embedding_data = []
            
            # Preparar dados para inserção
            for _, row in sublote.iterrows():
                try:
                    numero_controle = str(row['numeroControlePNCP'])
                    
                    # Preparar contratação se não existir
                    if numero_controle not in existing_contracts:
                        try:
                            # TODOS OS CAMPOS EXTRAS INCLUÍDOS AQUI
                            contract_data.append((
                                numero_controle,
                                int(row['anoCompra']),
                                row['descricaoCompleta'],
                                clean_value_for_db(row['valorTotalEstimado']) or 0.0,
                                clean_value_for_db(row.get('valorTotalHomologado')) or 0.0,
                                clean_value_for_db(row['dataAberturaProposta']),
                                clean_value_for_db(row['dataEncerramentoProposta']),
                                row['unidadeOrgao_ufSigla'],
                                row['unidadeOrgao_municipioNome'],
                                row['unidadeOrgao_nomeUnidade'],
                                row['orgaoEntidade_razaosocial'],
                                # CAMPOS EXTRAS ADICIONADOS
                                clean_value_for_db(row.get('datainclusao')),
                                clean_value_for_db(row.get('linksistemaorigem')),
                                clean_value_for_db(row.get('modalidadeid')),
                                clean_value_for_db(row.get('modalidadenome')),
                                clean_value_for_db(row.get('modadisputaid')),
                                clean_value_for_db(row.get('modadisputanome')),
                                clean_value_for_db(row.get('usuarionome')),
                                clean_value_for_db(row.get('orgaoentidade_poderid')),
                                clean_value_for_db(row.get('orgaoentidade_esferaid'))
                            ))
                            local_stats['contratacoes_inseridas'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar contratação {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    else:
                        local_stats['contratacoes_duplicadas'] += 1
                    
                    # Preparar embedding se não existir
                    if numero_controle not in existing_embeddings and numero_controle in embeddings_dict:
                        try:
                            embedding = embeddings_dict[numero_controle]
                            embedding_data.append((
                                numero_controle,
                                embedding.tolist(),  # Converter para lista para JSON
                                EMBEDDING_MODEL,
                                json.dumps({
                                    "preprocessing": preprocessing_options,
                                    "model_index": EMBEDDING_MODEL_INDEX,
                                    "timestamp": datetime.now().isoformat()
                                })
                            ))
                            local_stats['embeddings_inseridos'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar embedding {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    elif numero_controle in existing_embeddings:
                        local_stats['embeddings_duplicados'] += 1
                
                except Exception as e:
                    console.print(f"[red]Worker {worker_id} - Erro ao processar registro: {e}[/red]")
                    local_stats['erros'] += 1
            
            # INSERÇÕES EM TRANSAÇÃO ÚNICA
            try:
                # Inserir contratações em lote
                if contract_data:
                    # SQL COM TODOS OS CAMPOS EXTRAS
                    contract_sql = """
                        INSERT INTO contratacoes (
                            numeroControlePNCP, anoCompra, descricaoCompleta,
                            valorTotalEstimado, valorTotalHomologado, dataAberturaProposta, dataEncerramentoProposta,
                            unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                            unidadeOrgao_nomeUnidade, orgaoEntidade_razaosocial,
                            datainclusao, linksistemaorigem, modalidadeid,
                            modalidadenome, modadisputaid, modadisputanome,
                            usuarionome, orgaoentidade_poderid, orgaoentidade_esferaid
                        ) VALUES %s
                    """
                    
                    execute_batch_with_retry(cursor, contract_sql, contract_data, worker_id)
                
                # Inserir embeddings individualmente (devido ao pgvector)
                if embedding_data:
                    for emb_data in embedding_data:
                        single_emb_sql = """
                            INSERT INTO contratacoes_embeddings (
                                numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                            ) VALUES (%s, %s::vector, %s, %s)
                        """
                        execute_with_retry(cursor, single_emb_sql, emb_data, worker_id=worker_id)
                
                # Commit da transação
                connection.commit()
                
                # Atualizar progresso
                progress.update(task_id, advance=len(sublote))
                
                # Breve pausa para reduzir contenção
                time.sleep(0.05)
                
            except Exception as e:
                connection.rollback()
                console.print(f"[bold red]Worker {worker_id} - Erro na transação: {e}[/bold red]")
                local_stats['erros'] += len(sublote)
                progress.update(task_id, advance=len(sublote))
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Worker {worker_id} - Erro geral: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
    
    finally:
        cursor.close()
        connection.close()
    
    # Atualizar estatísticas globais
    update_global_stats(
        contratacoes_inseridas=local_stats['contratacoes_inseridas'],
        embeddings_inseridos=local_stats['embeddings_inseridos'],
        contratacoes_duplicadas=local_stats['contratacoes_duplicadas'],
        embeddings_duplicados=local_stats['embeddings_duplicados'],
        erros=local_stats['erros']
    )
    
    return local_stats


# ===== FASE 3 - FUNÇÕES DE CATEGORIZAÇÃO AUTOMÁTICA =====

def get_inserted_embeddings_ids(numero_controle_list):
    """Obtém os IDs dos embeddings inseridos baseado na lista de números de controle"""
    if not numero_controle_list:
        return []
    
    try:
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, numerocontrolepncp, embedding_vector
            FROM contratacoes_embeddings 
            WHERE numerocontrolepncp = ANY(%s)
            AND embedding_vector IS NOT NULL
            AND (top_categories IS NULL OR confidence IS NULL)
            ORDER BY id
        """, (numero_controle_list,))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        console.print(f"[red]Erro ao obter embeddings inseridos: {e}[/red]")
        return []

def categorize_embedding_batch_fase3(worker_id, embedding_data_batch, progress_task):
    """Categoriza um batch de embeddings (FASE 3)"""
    results = []
    
    # Atualizar estatísticas do worker
    with fase3_stats_lock:
        fase3_stats['worker_stats'][worker_id] = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'start_time': time.time()
        }
    
    try:
        # Criar conexão para este worker
        connection = create_connection()
        cursor = connection.cursor()
        
        for i, (record_id, numero_controle, embedding_vector) in enumerate(embedding_data_batch):
            try:
                # Query para buscar TOP K categorias usando pgvector
                search_query = """
                SELECT 
                    codcat,
                    nomcat,
                    1 - (cat_embeddings <=> %s::vector) AS similarity
                FROM 
                    categorias
                WHERE 
                    cat_embeddings IS NOT NULL
                ORDER BY 
                    similarity DESC
                LIMIT %s
                """
                
                cursor.execute(search_query, (embedding_vector, TOP_K))
                category_results = cursor.fetchall()
                
                if category_results:
                    # Extrair códigos e similaridades com precisão otimizada
                    top_categories = [row[0] for row in category_results]
                    top_similarities = [round(float(row[2]), 4) for row in category_results]
                    
                    # Calcular confiabilidade com 4 casas decimais
                    raw_confidence = calculate_confidence(top_similarities)
                    confidence = round(raw_confidence, 4)
                    
                    results.append({
                        'id': record_id,
                        'numero_controle': numero_controle,
                        'top_categories': top_categories,
                        'top_similarities': top_similarities,
                        'confidence': confidence,
                        'success': True
                    })
                    
                    # Atualizar estatísticas
                    with fase3_stats_lock:
                        fase3_stats['worker_stats'][worker_id]['updated'] += 1
                        
                else:
                    # Não encontrou categorias
                    results.append({
                        'id': record_id,
                        'numero_controle': numero_controle,
                        'top_categories': None,
                        'top_similarities': None,
                        'confidence': 0.0,
                        'success': False,
                        'error': 'Nenhuma categoria encontrada'
                    })
                    
                    with fase3_stats_lock:
                        fase3_stats['worker_stats'][worker_id]['errors'] += 1
                
                # Atualizar progresso
                with fase3_stats_lock:
                    fase3_stats['worker_stats'][worker_id]['processed'] += 1
                
                # Atualizar barra de progresso visual
                if progress_task:
                    progress_task[0].update(progress_task[1], advance=1)
                    
            except Exception as e:
                results.append({
                    'id': record_id,
                    'numero_controle': numero_controle,
                    'top_categories': None,
                    'top_similarities': None,
                    'confidence': 0.0,
                    'success': False,
                    'error': str(e)
                })
                
                with fase3_stats_lock:
                    fase3_stats['worker_stats'][worker_id]['errors'] += 1
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        # Erro na conexão do worker
        for record_id, numero_controle, _ in embedding_data_batch:
            results.append({
                'id': record_id,
                'numero_controle': numero_controle,
                'top_categories': None,
                'top_similarities': None,
                'confidence': 0.0,
                'success': False,
                'error': f'Erro de conexão: {str(e)}'
            })
            
            with fase3_stats_lock:
                fase3_stats['worker_stats'][worker_id]['errors'] += 1
    
    return results

def update_categorization_batch_fase3(results):
    """Atualiza os dados de categorização no banco (FASE 3)"""
    try:
        connection = create_connection()
        cursor = connection.cursor()
        
        updated_count = 0
        
        for result in results:
            if result['success'] and result['top_categories']:
                cursor.execute("""
                    UPDATE contratacoes_embeddings 
                    SET 
                        top_categories = %s,
                        top_similarities = %s,
                        confidence = %s
                    WHERE id = %s
                """, (
                    result['top_categories'],
                    result['top_similarities'],
                    result['confidence'],
                    result['id']
                ))
                
                if cursor.rowcount > 0:
                    updated_count += 1
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return updated_count
        
    except Exception as e:
        console.print(f"[red]Erro ao atualizar batch de categorização: {e}[/red]")
        return 0

def execute_fase3_categorization(processed_numero_controles):
    """Executa a FASE 3 - Categorização automática dos embeddings inseridos/atualizados"""
    if not processed_numero_controles:
        log_message("Nenhum embedding novo para categorizar", "warning")
        return
    
    log_message("Fase 3: Categorização automática")
    log_message(f"Categorizando {len(processed_numero_controles)} embeddings")
    
    # Obter os IDs dos embeddings a serem categorizados
    embeddings_to_categorize = get_inserted_embeddings_ids(processed_numero_controles)
    
    if not embeddings_to_categorize:
        log_message("Nenhum embedding encontrado para categorização", "warning")
        return
    
    log_message(f"Encontrados {len(embeddings_to_categorize)} embeddings para categorizar")
    
    # Resetar estatísticas da FASE 3
    with fase3_stats_lock:
        fase3_stats.update({
            'worker_stats': {},
            'total_processed': 0,
            'total_updated': 0,
            'total_errors': 0
        })
    
    # Dividir em batches (padrão populate_categorization_data_v2.py: 1 batch por worker + worker extra para resto)
    total_embeddings = len(embeddings_to_categorize)
    batch_size = total_embeddings // MAX_WORKERS
    remainder = total_embeddings % MAX_WORKERS
    
    batches = []
    start_idx = 0
    
    for i in range(MAX_WORKERS):
        # Batches normais + 1 extra para os primeiros workers se houver resto
        current_batch_size = batch_size + (1 if i < remainder else 0)
        end_idx = start_idx + current_batch_size
        
        if start_idx < total_embeddings:
            batch_embeddings = embeddings_to_categorize[start_idx:end_idx]
            if batch_embeddings:  # Só adicionar se não for vazio
                batches.append(batch_embeddings)
            start_idx = end_idx
    
    # Filtrar batches vazios
    batches = [batch for batch in batches if batch]
    
    console.print(f"[cyan]Processamento em {len(batches)} workers com batches de tamanhos: {[len(b) for b in batches]}[/cyan]")
    
    # Processar com múltiplas barras de progresso
    inicio_fase3 = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        tasks = []
        for worker_id in range(len(batches)):
            task = progress.add_task(
                f"Worker {worker_id+1}/{len(batches)} - Categorizando", 
                total=len(batches[worker_id])
            )
            tasks.append(task)
        
        with ThreadPoolExecutor(max_workers=len(batches)) as executor:
            futures = []
            
            for worker_id, batch in enumerate(batches):
                future = executor.submit(
                    categorize_embedding_batch_fase3,
                    worker_id + 1,
                    batch,
                    (progress, tasks[worker_id])
                )
                futures.append(future)
            
            # Aguardar conclusão e coletar resultados
            all_results = []
            for future in futures:
                try:
                    result = future.result()
                    all_results.extend(result)
                except Exception as e:
                    console.print(f"[bold red]Erro em worker de categorização: {e}[/bold red]")
    
    # Atualizar banco com os resultados
    console.print("[cyan]Atualizando banco de dados com categorias...[/cyan]")
    updated_count = update_categorization_batch_fase3(all_results)
    
    # Tempo total da FASE 3
    tempo_fase3 = time.time() - inicio_fase3
    
    # Calcular estatísticas finais
    with fase3_stats_lock:
        total_processed = sum(stats.get('processed', 0) for stats in fase3_stats['worker_stats'].values())
        total_updated = sum(stats.get('updated', 0) for stats in fase3_stats['worker_stats'].values())
        total_errors = sum(stats.get('errors', 0) for stats in fase3_stats['worker_stats'].values())
        
        # Atualizar estatísticas globais da FASE 3
        fase3_stats['total_processed'] = total_processed
        fase3_stats['total_updated'] = total_updated
        fase3_stats['total_errors'] = total_errors
    
    # Relatório da FASE 3
    log_message(f"Fase 3 concluída: {total_processed} processados, {total_updated} categorizados, {total_errors} erros em {tempo_fase3:.1f}s", "success")


# ===== FIM DAS FUNÇÕES DA FASE 3 =====

def process_excel_file(file_path):
    """Processa um arquivo Excel completo"""
    try:
        # Carregar dados do Excel
        console.print(f"[cyan]Carregando dados de {os.path.basename(file_path)}...[/cyan]")
        df = pd.read_excel(file_path)
        
        if df.empty:
            console.print(f"[yellow]Arquivo vazio: {os.path.basename(file_path)}[/yellow]")
            return False
        
        console.print(f"[cyan]Carregados {len(df)} registros[/cyan]")
        
        # Carregar ou criar cache de embeddings
        embeddings_cache_path = load_or_create_embeddings_cache()
        
        # Carregar embeddings existentes
        embeddings_dict = {}
        if os.path.exists(embeddings_cache_path):
            try:
                with open(embeddings_cache_path, 'rb') as f:
                    embeddings_dict = pickle.load(f)
                console.print(f"[cyan]Carregados {len(embeddings_dict)} embeddings do cache[/cyan]")
            except Exception as e:
                console.print(f"[yellow]Erro ao carregar embeddings do cache: {e}[/yellow]")
                embeddings_dict = {}
        
        # Criar conexão para verificar registros existentes
        connection = create_connection()
        if not connection:
            console.print("[bold red]Não foi possível conectar ao banco![/bold red]")
            return False
        
        # Carregar registros existentes para verificação de duplicatas
        existing_contracts, existing_embeddings = load_existing_records(connection)
        connection.close()
        
        # Lista para rastrear números de controle processados (para FASE 3)
        processed_numero_controles = list(df['numeroControlePNCP'].astype(str).unique())
        
        # Dividir em partições para processamento paralelo
        partitions = partition_dataframe(df, MAX_WORKERS)
        partitions = [p for p in partitions if len(p) > 0]  # Remover partições vazias
        
        log_message(f"Processando {len(df)} registros com {len(partitions)} workers")
        
        # FASE 1: Gerar embeddings
        log_message("Fase 1: Gerando embeddings")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            tasks = []
            for worker_id in range(len(partitions)):
                task = progress.add_task(
                    f"Embeddings worker {worker_id+1}", 
                    total=len(partitions[worker_id])
                )
                tasks.append(task)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for worker_id, partition in enumerate(partitions):
                    future = executor.submit(
                        process_embedding_batch,
                        worker_id + 1,
                        partition,
                        embeddings_dict,
                        progress,
                        tasks[worker_id]
                    )
                    futures.append(future)
                
                # Aguardar conclusão
                for future in futures:
                    try:
                        local_embeddings, local_stats = future.result()
                        update_global_stats(
                            embeddings_gerados=local_stats['embeddings_gerados'],
                            embeddings_pulados=local_stats['embeddings_pulados'],
                            erros=local_stats['erros']
                        )
                    except Exception as e:
                        log_message(f"Erro em worker: {e}", "error")
        
        # Salvar embeddings no cache
        try:
            with open(embeddings_cache_path, 'wb') as f:
                pickle.dump(embeddings_dict, f)
            log_message("Cache de embeddings salvo", "success")
        except Exception as e:
            log_message(f"Erro no cache: {e}", "error")
        
        # FASE 2: Inserir dados no banco
        log_message("Fase 2: Inserindo no Supabase")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            tasks = []
            for worker_id in range(len(partitions)):
                task = progress.add_task(
                    f"Worker {worker_id+1}/{len(partitions)} - Inserindo no banco", 
                    total=len(partitions[worker_id])
                )
                tasks.append(task)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for worker_id, partition in enumerate(partitions):
                    future = executor.submit(
                        process_db_batch,
                        worker_id + 1,               # ID do worker
                        partition,                   # Dados a processar
                        embeddings_dict,             # Embeddings
                        existing_contracts,          # Contratos existentes
                        existing_embeddings,         # Embeddings existentes
                        progress,                    # Objeto de progresso
                        tasks[worker_id]             # ID da tarefa visual
                    )
                    futures.append(future)
                
                # Aguardar conclusão de todos os workers
                for future in futures:
                    try:
                        result = future.result()
                        # Resultado processado com sucesso
                    except Exception as e:
                        console.print(f"[bold red]Erro em worker de banco: {e}[/bold red]")
        
        # FASE 3: Categorização automática dos embeddings inseridos/atualizados
        execute_fase3_categorization(processed_numero_controles)
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file_path)}: {e}[/bold red]")
        return False

def check_new_records():
    """Verifica se houve inserção de novos registros nos scripts anteriores"""
    try:
        # Caminho do arquivo de log
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGS")
        log_file = os.path.join(log_dir, "processamento.log")
        
        # Se o arquivo não existir, não continuar
        if not os.path.exists(log_file):
            return False
            
        # Obter a data atual para filtrar apenas registros de hoje
        data_atual = datetime.now().strftime("%Y-%m-%d")
        
        # Ler o arquivo de log
        with open(log_file, "r") as f:
            lines = f.readlines()
            
        # Filtrar apenas as linhas de hoje
        todays_lines = [line for line in lines if line.startswith(data_atual)]
        
        if not todays_lines:
            return False
            
        # Verificar se algum script adicionou registros
        for line in todays_lines:
            if "SCRIPT03:" in line or "SCRIPT04:" in line:
                # Extrair o número de registros adicionados
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        count = int(parts[1].split()[0])
                        if count > 0:
                            # Se encontrou pelo menos um registro adicionado, continuar
                            return True
                    except ValueError:
                        # Se não conseguir converter para int, ignorar esta linha
                        pass
                        
        # Se chegou aqui, nenhum script adicionou registros
        return False
        
    except Exception as e:
        print(f"Erro ao verificar registros no log: {e}")
        return False  # Em caso de erro, não continuar

def main():
    """Função principal do processamento de embeddings"""
    console.print(Panel("[bold blue] [6/7] PROCESSAMENTO DE EMBEDDINGS SUPABASE[/bold blue]"))

    # Verificar se houve novos registros a serem processados
    if not check_new_records():
        log_message("Nenhum novo registro encontrado para processamento", "success")
        return

    # Verificar diretórios
    os.makedirs(NEW_PATH, exist_ok=True)
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    # Buscar arquivos Excel
    excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        log_message("Nenhum arquivo Excel encontrado", "success")
        return
    
    log_message(f"Processando {len(excel_files)} arquivo(s)")
    
    # Processar arquivos
    inicio = time.time()
    processed_files = 0
    
    for i, excel_file in enumerate(excel_files, 1):
        excel_path = os.path.join(NEW_PATH, excel_file)
        log_message(f"[{i}/{len(excel_files)}] Processando: {excel_file}")
        
        try:
            success = process_excel_file(excel_path)
            if success:
                processed_files += 1
                log_message(f"Arquivo processado: {excel_file}", "success")
            else:
                log_message(f"Falha no arquivo: {excel_file}", "error")
        except Exception as e:
            log_message(f"Erro no arquivo {excel_file}: {str(e)}", "error")
    
    # Verificar registros novos antes de encerrar
    if check_new_records():
        log_message("Novos registros detectados. Recomenda-se executar os scripts 03 e 04 novamente.", "warning")
    
    # Resultado final
    tempo_total = time.time() - inicio
    
    if processed_files == len(excel_files):
        log_message(f"Processamento concluído: {processed_files} arquivo(s) em {tempo_total:.1f}s", "success")
    else:
        log_message(f"Processamento com falhas: {processed_files}/{len(excel_files)} arquivo(s)", "warning")

if __name__ == "__main__":
    main()
