#!/usr/bin/env python
# -*- coding: utf-8 -*-
### EMB_NV4_v1 - Versão com processamento de lotes em paralelo confiável
### VERSÃO v1.2: Claude 3.7 Sonnet Thinking (VS CODE COpilot)
### MATRIZ DE SIMILARIDADE E OUTRAS MODIFICAÇÕES

import os
import sys
import io
import numpy as np
import pandas as pd
import re
import unidecode
import nltk
import time
import pickle
import threading
import traceback
import queue
import concurrent.futures
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.progress import TaskProgressColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box
from rich.layout import Layout
from rich.align import Align
from concurrent.futures import ThreadPoolExecutor, as_completed

# Criar instância do console para exibição formatada
console = Console(record=True)

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
EXCEL_FILE = CLASS_PATH + "#CONTRATAÇÃO_ID_COMPRAS_ITENS.xlsx"
SHEET = "ITENS"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Adicionar este diretório nas configurações iniciais, logo após a definição de BATCH_OUTPUT_DIR
SIMILARITY_PATH = os.path.join(CLASS_PATH, "similarity_matrices")
os.makedirs(SIMILARITY_PATH, exist_ok=True)

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = CLASS_PATH + f"GRANDES_VOLUMES_CATNV4_OPENAI_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_GRANDES_VOLUMES_{TIMESTAMP}.pkl"
BATCH_OUTPUT_DIR = os.path.join(CLASS_PATH, "BATCH_OUTPUT")
LOG_FILE = CLASS_PATH + f"LOG_GRANDES_VOLUMES_{TIMESTAMP}.txt"

# Criar diretório para outputs em batch se não existir
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)

# Configurações de performance
MAX_CONCURRENT_BATCHES = min(12, os.cpu_count())  # Máximo de lotes ativos simultaneamente
BATCH_SIZE = 5000  # Tamanho do batch para processamento e salvamento
SAVE_EVERY_N_BATCHES = 1  # Frequência de salvamento (a cada N batches)
REPORT_INTERVAL = 60  # Intervalo em segundos para relatórios de progresso

# Constantes para controle de execução
MAX_WORKERS = os.cpu_count() * 2  # Número de threads para processamento paralelo
TOP_N = 10  # Número de categorias mais relevantes a serem retornadas
EMBEDDING_MODEL = "text-embedding-3-large"  # Modelo de embedding

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = BASE_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"

# Criar os diretórios se não existirem
for directory in [EMBEDDINGS_DIR, BATCH_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Criar lock para acessos concorrentes
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
output_files_lock = threading.Lock()
log_lock = threading.Lock()
status_lock = threading.Lock()
global_similarity_lock = threading.Lock()

# Estado global compartilhado
g_processed_batches = {}
g_batch_status = {}
g_start_time = time.time()
g_total_items_processed = 0
g_avg_batch_time = 0.0

# Configurar logging para o console e arquivo
def log_message(message, level="INFO", batch_id=None, console_output=False):
    """Registra mensagem no arquivo de log e opcionalmente no console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Adicionar ID do lote à mensagem se fornecido
    if batch_id is not None and "[Lote" not in message:
        formatted_message = f"[Lote {batch_id}] {message}"
    else:
        formatted_message = message
    
    log_entry = f"[{timestamp}] [{level}] {formatted_message}"
    
    # Sempre escrever no arquivo de log
    with log_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    # Saída para console apenas se explicitamente solicitado
    if console_output:
        if level == "ERROR":
            console.print(f"[bold red]{formatted_message}[/bold red]")
        elif level == "WARNING":
            console.print(f"[bold yellow]{formatted_message}[/bold yellow]")
        elif level == "SUCCESS":
            console.print(f"[bold green]{formatted_message}[/bold green]")
        else:
            console.print(formatted_message)

# Inicializar NLTK
try:
    # Configurar caminho para dados NLTK
    nltk_data_path = os.path.join(os.path.expanduser('~'), 'nltk_data')
    os.makedirs(nltk_data_path, exist_ok=True)
    nltk.data.path.append(nltk_data_path)
    
    # Baixar recursos necessários
    for resource in ['stopwords', 'wordnet']:
        try:
            nltk.download(resource, quiet=True)
        except Exception as e:
            log_message(f"Aviso: Não foi possível baixar {resource}: {str(e)}", "WARNING")
    
    # Carregar stopwords antecipadamente
    from nltk.corpus import stopwords
    portuguese_stopwords = set(stopwords.words('portuguese'))
    
    # Inicializar lematizador
    from nltk.stem import WordNetLemmatizer
    lemmatizer = WordNetLemmatizer()
    
except Exception as e:
    log_message(f"Erro na configuração do NLTK: {str(e)}", "ERROR")
    # Fallback - define stopwords e lemmatizer vazios
    portuguese_stopwords = set()
    
    class SimpleLemmatizer:
        def lemmatize(self, word):
            return word
    
    lemmatizer = SimpleLemmatizer()

def preprocess_text(text):
    """Aplica pré-processamento no texto."""
    try:
        # Remover acentuação e converter para string
        text = unidecode.unidecode(str(text))
        # Converter para minúsculas
        text = text.lower()
        # Remover caracteres não alfabéticos
        text = re.sub(r'[^a-z\s]', '', text)
        
        # Remover stopwords
        words = text.split()
        words = [word for word in words if word not in portuguese_stopwords]
        
        # Lematizar
        words = [lemmatizer.lemmatize(word) for word in words]
        
    except Exception as e:
        # Em caso de erro, aplicar um processamento mais simples
        log_message(f"Aviso: Usando processamento simplificado para texto: {str(e)}", "WARNING")
        text = unidecode.unidecode(str(text)).lower()
        text = re.sub(r'[^a-z\s]', '', text)
        words = [word for word in text.split() if len(word) > 2]
    
    return ' '.join(words)

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            log_message(f"Embeddings salvos em {filepath}", "SUCCESS")
            return True
        except Exception as e:
            log_message(f"Erro ao salvar embeddings: {str(e)}", "ERROR")
            return False

def load_embeddings(filepath):
    """Carrega embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            log_message(f"Embeddings carregados de {filepath}", "SUCCESS")
            return embeddings
        except Exception as e:
            log_message(f"Erro ao carregar embeddings: {str(e)}", "ERROR")
    return None

def get_processed_batch_ids(batch_files):
    """Extract batch IDs from batch filenames to recognize already processed batches."""
    processed_ids = set()
    if not batch_files:
        return processed_ids
        
    for file_path in batch_files:
        try:
            # Extract batch ID from filename (format: batch_0001_start_end.xlsx)
            filename = os.path.basename(file_path)
            batch_id = int(filename.split('_')[1])
            processed_ids.add(batch_id)
        except (IndexError, ValueError):
            log_message(f"Aviso: Não foi possível extrair ID do lote de {file_path}", "WARNING")
    
    return processed_ids

def save_checkpoint(last_processed, output_file, batch_files=None):
    """Salva checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        # Extract batch IDs from filenames
        batch_ids = list(get_processed_batch_ids(batch_files or []))
        
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file,
            'batch_files': batch_files or [],
            'processed_batch_ids': batch_ids  # Add this to track batch IDs
        }
        
        try:
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump(checkpoint, f)
            log_message(f"Checkpoint salvo: {last_processed} itens processados, {len(batch_ids)} lotes concluídos", "SUCCESS")
            return True
        except Exception as e:
            log_message(f"Erro ao salvar checkpoint: {str(e)}", "ERROR")
            return False

def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
            log_message(f"Checkpoint encontrado - Último processado: {checkpoint['last_processed']}", "INFO")
            return checkpoint
        except Exception as e:
            log_message(f"Erro ao carregar checkpoint: {str(e)}", "ERROR")
    return None

def load_data():
    """Carrega dados do Excel e catálogo unificado."""
    console.print(Panel.fit("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]"))
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint = load_checkpoint()
    last_processed = 0
    batch_files = []
    
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint.get('last_processed', 0)
        batch_files = checkpoint.get('batch_files', [])
        
        # Verificar se os arquivos de batch ainda existem
        valid_batch_files = []
        for bf in batch_files:
            if os.path.exists(bf):
                valid_batch_files.append(bf)
            else:
                log_message(f"Arquivo de batch não encontrado: {bf}", "WARNING")
        
        if len(valid_batch_files) != len(batch_files):
            log_message(f"Alguns arquivos de batch não foram encontrados: {len(batch_files) - len(valid_batch_files)} perdidos", "WARNING")
            batch_files = valid_batch_files
        
        # Preparar para pular as linhas já processadas
        skiprows = list(range(1, last_processed + 1)) if last_processed > 0 else None
    else:
        skiprows = None
    
    # Carregar os dados do Excel
    try:
        if skiprows:
            log_message(f"Carregando Excel a partir da linha {last_processed+1}...", "INFO")
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
            log_message(f"Carregados {len(df_items)} itens do Excel (a partir da linha {last_processed+1}).", "SUCCESS")
        else:
            log_message("Carregando Excel do início...", "INFO")
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
            log_message(f"Carregados {len(df_items)} itens do Excel.", "SUCCESS")
    except Exception as e:
        log_message(f"Erro ao carregar arquivo Excel: {str(e)}", "ERROR")
        raise
    
    # Carregar catálogo unificado
    try:
        log_message(f"Carregando catálogo unificado de {NOVA_CAT_FILE}...", "INFO")
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        cat = cat_df.to_dict(orient="records")
        log_message(f"Carregadas {len(cat)} categorias do catálogo unificado.", "SUCCESS")
    except Exception as e:
        log_message(f"Erro ao carregar catálogo unificado: {str(e)}", "ERROR")
        raise
    
    return df_items, cat, last_processed, batch_files, checkpoint

def prepare_catalog_entries(cat):
    """Preparar entradas de catálogo unificado para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    
    cat_texts = []
    cat_meta = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando catálogo unificado..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(cat))
        
        for entry in cat:
            # Utiliza as colunas CODCAT e NOMCAT do arquivo Excel
            codcat = entry.get('CODCAT', '')
            nomcat = entry.get('NOMCAT', '')
            # Forma o texto de embedding concatenando os dois campos com um espaço
            combined_text = preprocess_text(f"{codcat} {nomcat}")
            cat_texts.append(combined_text)
            cat_meta.append((codcat, nomcat))
            progress.update(task, advance=1)
    
    log_message(f"Preparados {len(cat_texts)} textos de catálogo unificado.", "SUCCESS")
    return cat_texts, cat_meta

def process_batch(batch, model=EMBEDDING_MODEL):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=batch
            )
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                log_message(f"Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...", "WARNING")
                time.sleep(retry_delay)
            else:
                log_message(f"Erro na API OpenAI (lote de {len(batch)} textos): {str(e)}", "ERROR")
                raise

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=25, batch_id=None):
    """Gera embeddings sem criar barras de progresso que causariam conflito."""
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Log apenas para arquivo
    log_message(f"Gerando embeddings para {len(texts)} textos em {total_batches} batches...", 
                batch_id=batch_id)
    
    # Processar em lotes sem barras de progresso
    start_time = time.time()
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
        
        # Log periódico somente para arquivo
        if (i // batch_size) % 10 == 0 or (i + batch_size >= len(texts)):
            progress_pct = min(100, int(100 * (i + len(batch)) / len(texts)))
            elapsed = time.time() - start_time
            rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
            log_message(f"Progresso de embeddings: {progress_pct}% ({i + len(batch)}/{len(texts)}) - {rate:.1f} textos/s", 
                       batch_id=batch_id)
    
    log_message(f"Embeddings gerados em {time.time() - start_time:.1f}s", "SUCCESS", batch_id=batch_id)
    return embeddings

def cosine_similarity(a, b):
    """Calcula similaridade de cosseno entre dois vetores."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

def calculate_similarity_matrix(item_embeds, cat_embeds, batch_id=None, log_queue=None):
    """Calcula a matriz de similaridade completa entre todos os itens e categorias, com relatórios de progresso."""
    n_items = len(item_embeds)
    n_cats = len(cat_embeds)
    
    # Define filepath para esta matriz específica
    matrix_filename = f"similarity_matrix_batch_{batch_id}.pkl"
    matrix_filepath = os.path.join(SIMILARITY_PATH, matrix_filename)
    
    # Verifica se já existe uma matriz salva para este lote
    if os.path.exists(matrix_filepath):
        if log_queue and batch_id:
            log_queue.put((batch_id, f"Carregando matriz de similaridade existente: {matrix_filename}", "Cálculo"))
        
        try:
            with open(matrix_filepath, 'rb') as f:
                similarity_matrix = pickle.load(f)
                
            # Verifica as dimensões da matriz
            if similarity_matrix.shape == (n_items, n_cats):
                if log_queue and batch_id:
                    log_queue.put((batch_id, f"Matriz de similaridade carregada com sucesso: {n_items}×{n_cats}", "Cálculo"))
                return similarity_matrix
            else:
                if log_queue and batch_id:
                    log_queue.put((batch_id, f"Dimensões da matriz salva não correspondem, recalculando...", "Cálculo"))
        except Exception as e:
            if log_queue and batch_id:
                log_queue.put((batch_id, f"Erro ao carregar matriz: {str(e)}, recalculando...", "Cálculo"))
    
    # Reportar início do cálculo
    if log_queue and batch_id:
        log_queue.put((batch_id, f"Iniciando cálculo da matriz de similaridade: {n_items}×{n_cats}", "Cálculo"))
    
    # Converte para arrays numpy se ainda não forem
    start_time = time.time()
    item_embeds_array = np.vstack(item_embeds)
    cat_embeds_array = np.vstack(cat_embeds)
    
    # Reportar progresso após conversão
    if log_queue and batch_id:
        log_queue.put((batch_id, f"Arrays convertidos em {time.time()-start_time:.2f}s, normalizando vetores...", "Cálculo"))
    
    # Normaliza os embeddings para cálculo de similaridade de cosseno
    norm_start_time = time.time()
    items_norm = np.linalg.norm(item_embeds_array, axis=1, keepdims=True)
    cats_norm = np.linalg.norm(cat_embeds_array, axis=1, keepdims=True)
    
    # Evita divisão por zero
    items_norm = np.maximum(items_norm, 1e-10)
    cats_norm = np.maximum(cats_norm, 1e-10)
    
    normalized_items = item_embeds_array / items_norm
    normalized_cats = cat_embeds_array / cats_norm
    
    # Reportar progresso após normalização
    if log_queue and batch_id:
        log_queue.put((batch_id, f"Vetores normalizados em {time.time()-norm_start_time:.2f}s, calculando produto dot...", "Cálculo"))
    
    # Para matrizes muito grandes, podemos calcular em blocos para mostrar progresso
    dot_start_time = time.time()
    if n_items > 1000:
        # Código existente para cálculo em blocos...
        similarity_matrix = np.zeros((n_items, n_cats))
        # ... resto do código ...
    else:
        # Para matrizes menores, calcular de uma só vez
        similarity_matrix = np.dot(normalized_items, normalized_cats.T)
    
    # Salvar a matriz de similaridade
    try:
        with open(matrix_filepath, 'wb') as f:
            pickle.dump(similarity_matrix, f)
        if log_queue and batch_id:
            log_queue.put((batch_id, f"Matriz de similaridade salva em {matrix_filename}", "Cálculo"))
    except Exception as e:
        if log_queue and batch_id:
            log_queue.put((batch_id, f"Erro ao salvar matriz: {str(e)}", "Cálculo"))
    
    # Reportar conclusão
    if log_queue and batch_id:
        total_time = time.time() - start_time
        log_queue.put((
            batch_id, 
            f"✅ Matriz de similaridade {n_items}×{n_cats} calculada em {total_time:.2f}s ({n_items/total_time:.1f} itens/s)", 
            "Cálculo"
        ))
    
    return similarity_matrix

def clear_similarity_matrices(batch_id=None):
    """Limpa matrizes de similaridade salvas.
    
    Args:
        batch_id: Se fornecido, limpa apenas a matriz para este lote. Caso contrário, limpa todas.
    """
    if batch_id is not None:
        matrix_filename = f"similarity_matrix_batch_{batch_id}.pkl"
        matrix_filepath = os.path.join(SIMILARITY_PATH, matrix_filename)
        if os.path.exists(matrix_filepath):
            os.remove(matrix_filepath)
            log_message(f"Matriz de similaridade para lote {batch_id} removida", "INFO")
    else:
        import glob
        matrices = glob.glob(os.path.join(SIMILARITY_PATH, "similarity_matrix_batch_*.pkl"))
        for matrix_file in matrices:
            os.remove(matrix_file)
        log_message(f"Removidas {len(matrices)} matrizes de similaridade", "INFO")

def find_top_n_categories(similarity_matrix, top_n=10, batch_id=None, log_queue=None):
    """Encontra os índices e scores das TOP_N categorias mais similares para cada item, com relatórios de progresso."""
    num_items = similarity_matrix.shape[0]
    
    # Reportar início
    start_time = time.time()
    if log_queue and batch_id:
        log_queue.put((batch_id, f"Iniciando busca de TOP-{top_n} categorias para {num_items} itens", "Ranking"))
    
    # Usar np.argpartition é mais eficiente que np.argsort para encontrar apenas TOP_N
    top_indices = np.zeros((num_items, top_n), dtype=int)
    top_scores = np.zeros((num_items, top_n))
    
    # Definir intervalo de relatório
    report_interval = max(1, num_items // 10)  # Relatar a cada 10% ou a cada item
    
    for i in range(num_items):
        # Encontra os TOP_N maiores índices (mais rápido que argsort completo)
        indices = np.argpartition(similarity_matrix[i], -top_n)[-top_n:]
        # Ordenar apenas esses TOP_N índices
        sorted_local_indices = np.argsort(-similarity_matrix[i][indices])
        # Reordenar os índices originais
        sorted_indices = indices[sorted_local_indices]
        
        top_indices[i] = sorted_indices
        top_scores[i] = similarity_matrix[i][sorted_indices]
        
        # Reportar progresso periodicamente
        if log_queue and batch_id and (i % report_interval == 0 or i == num_items - 1):
            progress_pct = min(100, int(100 * (i + 1) / num_items))
            elapsed = time.time() - start_time
            rate = (i+1) / elapsed if elapsed > 0 else 0
            eta = (num_items - i - 1) / rate if rate > 0 else 0
            
            log_queue.put((
                batch_id, 
                f"Ranking TOP-{top_n}: {progress_pct}% ({i+1}/{num_items}) • {rate:.1f} itens/s • ETA: {eta:.1f}s", 
                "Ranking"
            ))
    
    # Reportar conclusão
    if log_queue and batch_id:
        total_time = time.time() - start_time
        log_queue.put((
            batch_id, 
            f"✅ TOP-{top_n} categorias encontradas em {total_time:.2f}s ({num_items/total_time:.1f} itens/s)", 
            "Ranking"
        ))
    
    return top_indices, top_scores

def process_text_batch(batch):
    """Processa um lote de textos aplicando pré-processamento paralelo."""
    return [preprocess_text(text) for text in batch]

def update_batch_status(batch_id, message, timestamp=None, progress=None):
    """Atualiza o status de um lote com thread safety e barra de progresso."""
    with status_lock:
        if timestamp is None:
            timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Se o status não existir para este lote, criar um novo
        if batch_id not in g_batch_status:
            g_batch_status[batch_id] = {
                'message': "",
                'time': timestamp,
                'last_update': time.time(),
                'progress': 0  # 0-100 ou -1 para erro
            }
        
        g_batch_status[batch_id]['message'] = message
        g_batch_status[batch_id]['time'] = timestamp
        g_batch_status[batch_id]['last_update'] = time.time()
        
        # Atualizar progresso se informado
        if progress is not None:
            g_batch_status[batch_id]['progress'] = progress

def create_status_table(batch_statuses, completed, total, start_time):
    """Cria uma tabela com barras de progresso para cada lote."""
    # Calcular métricas globais
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60
    
    if completed > 0 and g_total_items_processed > 0:
        rate = g_total_items_processed / elapsed
        estimated_remaining = ((total - completed) * g_avg_batch_time) / MAX_CONCURRENT_BATCHES if g_avg_batch_time > 0 else 0
    else:
        rate = 0
        estimated_remaining = 0
    
    # Criar tabela principal
    table = Table(
        title=f"Processamento de Lotes [{completed}/{total}] - {elapsed_min:.1f}min decorridos - ETA: {estimated_remaining/60:.1f}min",
        box=box.SIMPLE,
        expand=False,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Lote", justify="right", style="cyan", no_wrap=True, width=6)
    table.add_column("Status", style="white", no_wrap=False, width=45)
    table.add_column("Progresso", style="bright_blue", width=20)
    table.add_column("Atualizado", style="yellow", no_wrap=True, width=10)
    
    # Mostrar apenas os lotes ativos ou recentemente concluídos
    now = time.time()
    active_cutoff = now - 300  # Lotes ativos ou concluídos nos últimos 5 minutos
    
    # Filtrar e ordenar lotes por ID
    active_lotes = {}
    for batch_id, status in batch_statuses.items():
        last_update = status.get('last_update', 0)
        if last_update >= active_cutoff:
            active_lotes[batch_id] = status
    
    # Limitando aos 15 lotes mais recentes por ordem de ID
    batch_ids = sorted(active_lotes.keys())[-15:]
    
    for batch_id in batch_ids:
        status = active_lotes[batch_id]
        
        # Determinar a cor do status
        status_msg = status.get("message", "Desconhecido")
        progress_val = status.get("progress", 0)
        
        if progress_val == 100 or "CONCLUÍDO" in status_msg:
            style = "green"
        elif progress_val < 0 or "ERRO" in status_msg:
            style = "red"
        elif "Similaridades" in status_msg:
            style = "magenta"
        elif "Embeddings" in status_msg:
            style = "yellow"
        elif "Pré-processamento" in status_msg:
            style = "blue"
        elif "Extraindo" in status_msg:
            style = "cyan"
        else:
            style = "white"
        
        # Criar barra de progresso visual
        if progress_val >= 0:
            progress_bar = ""
            filled = int(progress_val / 5)  # 20 caracteres para 100%
            
            if progress_val == 100:
                # Barra completa com cor verde
                progress_bar = f"[green]{'█' * 20}[/green] {progress_val}%"
            else:
                # Barra parcial
                progress_bar = f"[{style}]{'█' * filled}{'░' * (20 - filled)}[/{style}] {progress_val}%"
        else:
            # Indicador de erro
            progress_bar = "[red]✖ ERRO[/red]"
        
        table.add_row(
            f"{batch_id}",
            f"[{style}]{status_msg}[/{style}]",
            progress_bar,
            status.get("time", "")
        )
    
    # Adicionar resumo de métricas
    if completed > 0:
        summary = Table(box=None, show_header=False, expand=False)
        summary.add_column("Métrica", style="bold cyan")
        summary.add_column("Valor", style="yellow")
        
        summary.add_row("Taxa de processamento", f"{rate:.2f} itens/s")
        summary.add_row("Tempo médio por lote", f"{g_avg_batch_time:.2f}s")
        summary.add_row("Progresso", f"{100 * completed / total:.1f}%")
        summary.add_row("Tempo restante estimado", f"{estimated_remaining/60:.1f} minutos")
        
        # Renderizar tabela combinada
        layout = Layout()
        layout.split_column(
            Layout(table, name="table"),
            Layout(summary, name="summary", size=5)
        )
        return layout
    
    return table

def process_complete_batch(batch_df, cat_embeds, cat_meta, batch_id, start_idx, log_queue):
    """Processa um lote completo com barras de progresso integradas ao status."""
    batch_start_time = time.time()
    batch_size = len(batch_df)
    
    try:
        # Inicializar relatório - apenas interface visual, sem log
        update_batch_status(batch_id, "▶ Iniciando processamento", progress=0)
        
        # Log para arquivo
        log_queue.put((batch_id, f"Lote {batch_id} iniciado - {len(batch_df)} itens"))
        
        # Inicialização
        log_queue.put((batch_id, f"Lote {batch_id} iniciado - {len(batch_df)} itens", "Início"))
        update_batch_status(batch_id, "Iniciado", progress=0)
        result_df = batch_df.copy()
        
        # Adicionar colunas TOP_N e SCORE_N
        for i in range(1, TOP_N + 1):
            result_df[f"TOP_{i}"] = ""
            result_df[f"SCORE_{i}"] = 0.0
        
        # Fase 1: Extração dos textos
        update_batch_status(batch_id, "Extraindo textos...", progress=5)
        raw_texts = []
        for _, row in batch_df.iterrows():
            objeto = str(row.get("objetoCompra", ""))
            itens = str(row.get("itens", ""))
            combined_text = f"{objeto} {itens}".strip()
            raw_texts.append(combined_text)
        
        log_queue.put((batch_id, "Extração de textos concluída.", "Extração"))
        update_batch_status(batch_id, "Extração concluída", progress=15)
        
        # Fase 2: Pré-processamento em paralelo
        update_batch_status(batch_id, "Pré-processando textos...", progress=20)
        with ThreadPoolExecutor(max_workers=max(2, MAX_WORKERS // 4)) as executor:
            chunk_size = max(1, len(raw_texts) // (MAX_WORKERS // 4))
            chunks = [raw_texts[i:i+chunk_size] for i in range(0, len(raw_texts), chunk_size)]
            processed_chunks = list(executor.map(process_text_batch, chunks))
        
        processed_texts = [pt for chunk in processed_chunks for pt in chunk]
        log_queue.put((batch_id, "Pré-processamento concluído.", "Pré-processamento"))
        update_batch_status(batch_id, "Pré-processamento concluído", progress=30)
        
        # Fase 3: Geração dos embeddings
        update_batch_status(batch_id, "Gerando embeddings...", progress=35)
        embeddings = get_embeddings(processed_texts, batch_id=batch_id)
        log_queue.put((batch_id, "Geração de embeddings concluída.", "Embeddings"))
        update_batch_status(batch_id, "Embeddings gerados", progress=50)
        
        # Fase 4: Cálculo de similaridades VETORIZADO com progresso
        log_queue.put((batch_id, "Calculando matriz de similaridade...", "Cálculo"))
        update_batch_status(batch_id, "Calculando matriz de similaridade", progress=60)
        
        # Calcular a matriz de similaridade completa de uma vez COM PROGRESSO
        similarity_matrix = calculate_similarity_matrix(embeddings, cat_embeds, batch_id, log_queue)
        
        # Encontrar TOP_N categorias mais similares para cada item COM PROGRESSO
        update_batch_status(batch_id, "Encontrando TOP categorias", progress=75)
        top_indices, top_scores = find_top_n_categories(similarity_matrix, TOP_N, batch_id, log_queue)
        
        # Atualizar o DataFrame com os resultados
        update_batch_status(batch_id, "Atualizando resultados...", progress=85)
        for idx in range(len(embeddings)):
            for i in range(TOP_N):
                if i < len(top_indices[idx]):
                    cat_idx = top_indices[idx][i]
                    if cat_idx < len(cat_meta):
                        _, nome = cat_meta[cat_idx]
                        result_df.iloc[idx, result_df.columns.get_loc(f"TOP_{i+1}")] = nome
                        result_df.iloc[idx, result_df.columns.get_loc(f"SCORE_{i+1}")] = float(top_scores[idx][i])
        
        log_queue.put((batch_id, "Cálculo de similaridades concluído.", "Finalização"))
        update_batch_status(batch_id, "Cálculos concluídos", progress=90)
        
        # Processamento das colunas finais
        if "id" in result_df.columns and "id_pncp" not in result_df.columns:
            result_df = result_df.rename(columns={"id": "id_pncp"})
        
        desired_columns = ['id_pncp', 'objetoCompra', 'itens']
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"TOP_{i}")
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"SCORE_{i}")
        
        final_columns = [col for col in desired_columns if col in result_df.columns]
        result_df = result_df[final_columns]
        
        # Salvar resultados
        update_batch_status(batch_id, "Salvando resultados...", progress=95)
        last_processed = start_idx + len(batch_df) - 1
        batch_filename = os.path.join(BATCH_OUTPUT_DIR, f"batch_{batch_id:04d}_{start_idx}_{last_processed}.xlsx")
        result_df.to_excel(batch_filename, index=False)
        
        batch_time = time.time() - batch_start_time
        items_per_second = len(batch_df) / batch_time
        
        completion_message = f"✅ CONCLUÍDO - {len(batch_df)} itens em {batch_time:.1f}s ({items_per_second:.1f} itens/s)"
        log_queue.put((batch_id, completion_message, "Concluído"))
        update_batch_status(batch_id, completion_message, progress=100)
        
        # Atualizar contadores globais
        with status_lock:
            global g_total_items_processed, g_avg_batch_time, g_processed_batches
            g_processed_batches[batch_id] = {
                'time': batch_time,
                'items': len(batch_df),
                'speed': items_per_second
            }
            
            g_total_items_processed += len(batch_df)
            
            # Atualizar tempo médio de processamento por lote
            if len(g_processed_batches) > 0:
                g_avg_batch_time = sum(batch['time'] for batch in g_processed_batches.values()) / len(g_processed_batches)
        
        return {
            'batch_id': batch_id,
            'start_idx': start_idx,
            'last_processed': last_processed,
            'batch_file': batch_filename,
            'items_processed': len(batch_df),
            'processing_time': batch_time
        }
    except Exception as e:
        error_msg = f"Erro ao processar lote {batch_id}: {str(e)}"
        log_queue.put((batch_id, f"[ERRO] {error_msg}", "Erro"))
        log_message(error_msg, "ERROR")
        log_message(traceback.format_exc(), "ERROR")
        update_batch_status(batch_id, f"❌ ERRO: {str(e)}", progress=-1)  # -1 indica erro
        return None

def main():
    """Função principal com processamento de lotes em paralelo e visualização avançada."""
    console.print(Panel.fit("[bold yellow]EMB_NV4_v2 - Sistema de classificação com embeddings para grandes volumes[/bold yellow]"))
    console.print("[bold green]Versão otimizada com processamento em lotes paralelos e monitoramento detalhado[/bold green]")
    
    # Inicializar arquivo de log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"=== Log iniciado em {datetime.now().isoformat()} ===\n")
    
    # Timestamp para início global
    global g_start_time
    g_start_time = time.time()
    
    try:
        # 1. Carregar dados e checkpoint
        df_items, cat, last_processed, batch_files, checkpoint = load_data()
        
        # 2. Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # 3. Verificar embeddings de catálogo
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        else:
            console.print("[green]Embeddings de catálogo carregados com sucesso.[/green]")
        
        # 4. Dividir em lotes
        batches = []
        for i in range(0, len(df_items), BATCH_SIZE):
            batch_df = df_items.iloc[i:i+BATCH_SIZE].copy()
            batch_df = batch_df.reset_index(drop=True)
            batches.append(batch_df)
        
        # 5. Verificar quais lotes já foram processados
        processed_batch_ids = get_processed_batch_ids(batch_files)
        log_message(f"Encontrados {len(processed_batch_ids)} lotes já processados", "INFO")
        
        # Preparar lotes a serem processados com informações adicionais
        batches_with_info = []
        next_start_idx = last_processed + 1
        
        for idx, batch_df in enumerate(batches):
            batch_id = idx + 1
            
            # Verificar se este lote já foi processado
            if batch_id in processed_batch_ids:
                log_message(f"Pulando lote {batch_id} (já processado)", "INFO")
                next_start_idx += len(batch_df)
                continue
                
            # Adicionar à lista para processamento
            batches_with_info.append({
                'batch_id': batch_id,
                'start_idx': next_start_idx,
                'batch_df': batch_df
            })
            next_start_idx += len(batch_df)
        
        # Verificar se há lotes para processar
        total_batches = len(batches_with_info)
        total_items = sum(len(info['batch_df']) for info in batches_with_info)
        
        if total_batches == 0:
            console.print("[bold green]Todos os lotes já foram processados.[/bold green]")
            log_message("Todos os lotes já foram processados. Não há trabalho a fazer.", "SUCCESS")
            return
        
        console.print(f"[bold cyan]Processando {total_batches} lotes com total de {total_items} itens[/bold cyan]")
        console.print(f"[bold cyan]Usando {MAX_CONCURRENT_BATCHES} workers para processamento paralelo[/bold cyan]")
        log_message(f"Iniciando processamento de {total_batches} lotes com {total_items} itens usando {MAX_CONCURRENT_BATCHES}", "INFO")
        
        # 6. Inicializar variáveis para acompanhamento
        current_batch_files = batch_files.copy() if batch_files else []
        completed_count = 0
        
        # Criamos uma fila thread-safe para logs de status dos lotes
        log_queue = queue.Queue()
        
        # Função para gerar a tabela de status atualizada
        def generate_status_display():
            return create_status_table(g_batch_status, completed_count, total_batches, g_start_time)
        
        # Thread para processar mensagens da fila de log
        def process_logs():
            last_report_time = time.time()
            
            while True:
                try:
                    # Obter mensagem da fila com timeout
                    try:
                        log_entry = log_queue.get(timeout=0.5)
                        
                        # Extrair batch_id e message independente do tamanho da tupla
                        batch_id = log_entry[0]
                        message = log_entry[1]
                        
                        # Terceiro elemento (categoria/fase) é opcional e pode ser ignorado no log
                        log_message(f"[Lote {batch_id}] {message}", "INFO")
                        log_queue.task_done()
                    except queue.Empty:
                        # Sem mensagens novas, verificar se ainda há trabalho a fazer
                        if not pending_batches and len(active_futures) == 0:
                            break
                    
                    # Gerar relatório periódico
                    current_time = time.time()
                    if current_time - last_report_time >= REPORT_INTERVAL:
                        # Relatório de progresso periódico
                        elapsed = current_time - g_start_time
                        if completed_count > 0:
                            rate = g_total_items_processed / elapsed if elapsed > 0 else 0
                            estimated_total = (total_items / g_total_items_processed) * elapsed if g_total_items_processed > 0 else 0
                            estimated_remaining = estimated_total - elapsed
                            
                            log_message(
                                f"RELATÓRIO DE PROGRESSO: {completed_count}/{total_batches} lotes, "
                                f"{g_total_items_processed}/{total_items} itens, "
                                f"{rate:.1f} itens/s, "
                                f"ETA: {estimated_remaining/60:.1f} minutos",
                                "INFO"
                            )
                        last_report_time = current_time
                        
                except Exception as e:
                    log_message(f"Erro no processador de logs: {str(e)}", "ERROR")
        
        # 7. Executar processamento com Live Table para status
        with Live(generate_status_display(), refresh_per_second=0.5) as live:
            # 8. Processar lotes em paralelo
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
                # Submeter lotes de forma controlada
                future_to_batch = {}
                
                # Iniciar lotes de forma progressiva
                active_futures = set()
                pending_batches = list(batches_with_info)
                
                # Iniciar thread de processamento de logs
                log_thread = threading.Thread(target=process_logs, daemon=True)
                log_thread.start()
                
                # Loop principal de processamento
                while pending_batches or active_futures:
                    # Atualizar a visualização
                    live.update(generate_status_display())
                    
                    # Submeter mais lotes se estiver abaixo do limite
                    while pending_batches and len(active_futures) < MAX_CONCURRENT_BATCHES:
                        batch_info = pending_batches.pop(0)
                        batch_id = batch_info['batch_id']
                        
                        # Inicializar status
                        update_batch_status(batch_id, "Aguardando início")
                        
                        # Submeter lote para processamento COM MENOS PARÂMETROS
                        future = executor.submit(
                            process_complete_batch,
                            batch_info['batch_df'],
                            cat_embeddings,
                            cat_meta,
                            batch_id,
                            batch_info['start_idx'],
                            log_queue
                        )
                        
                        future_to_batch[future] = batch_info
                        active_futures.add(future)
                        
                        # Atualizar status e visualização
                        update_batch_status(batch_id, "Submetido para processamento")
                        live.update(generate_status_display())
                    
                    # Esperar pelo menos um lote ser concluído
                    if active_futures:
                        # Aguardar a conclusão de pelo menos um future
                        done, active_futures = concurrent.futures.wait(
                            active_futures, 
                            return_when=concurrent.futures.FIRST_COMPLETED,
                            timeout=0.5  # Timeout para permitir atualização da interface
                        )
                        
                        # Processar os lotes concluídos
                        for future in done:
                            batch_info = future_to_batch[future]
                            batch_id = batch_info['batch_id']
                            
                            try:
                                # Processar resultado
                                result = future.result()
                                
                                if result:
                                    # Atualizar listas e contadores
                                    with output_files_lock:
                                        current_batch_files.append(result['batch_file'])
                                        completed_count += 1
                                    
                                    # Salvar checkpoint a cada N lotes
                                    if completed_count % SAVE_EVERY_N_BATCHES == 0:
                                        sorted_files = sorted(
                                            current_batch_files, 
                                            key=lambda x: int(os.path.basename(x).split('_')[1])
                                        )
                                        save_checkpoint(result['last_processed'], OUTPUT_FILE, sorted_files)
                                
                            except Exception as e:
                                log_message(f"Erro ao processar resultado do lote {batch_id}: {str(e)}", "ERROR")
                    else:
                        # Não há futures ativos, apenas aguardar um pouco para evitar CPU 100%
                        time.sleep(0.1)
            
            # Esperar a thread de logs terminar
            log_thread.join(timeout=1.0)
        
        # 9. Salvar checkpoint final
        if current_batch_files:
            # Ordenar arquivos por ID do lote
            sorted_batch_files = sorted(
                current_batch_files, 
                key=lambda x: int(os.path.basename(x).split('_')[1])
            )
            
            # Salvar checkpoint final
            save_checkpoint(next_start_idx - 1, OUTPUT_FILE, sorted_batch_files)
            
            # Para mesclagem, usamos o script separado
            log_message(
                f"Checkpoint final salvo. Para mesclar os lotes em um arquivo final, execute o script de mesclagem.", 
                "SUCCESS"
            )
        
        # 10. Exibir estatísticas totais
        end_time = time.time()
        total_time = end_time - g_start_time
        total_minutes = total_time / 60
        
        console.print(Panel.fit(f"[bold green]Processamento concluído![/bold green]"))
        console.print(f"[bold cyan]Tempo total: {total_minutes:.2f} minutos ({total_time:.2f} segundos)[/bold cyan]")
        
        if total_items > 0 and g_total_items_processed > 0:
            console.print(f"[bold cyan]Média por item: {total_time/g_total_items_processed:.4f} segundos[/bold cyan]")
            console.print(f"[bold cyan]Taxa de processamento: {g_total_items_processed/total_time:.2f} itens/segundo[/bold cyan]")
        
        console.print(f"[bold cyan]Total de itens processados: {g_total_items_processed}[/bold cyan]")
        
        # Criar relatório final no log
        log_message(f"RELATÓRIO FINAL - {completed_count}/{total_batches} lotes processados", "SUCCESS")
        log_message(f"Tempo total: {total_minutes:.2f} minutos", "SUCCESS")
        log_message(f"Itens processados: {g_total_items_processed}", "SUCCESS")
        if g_total_items_processed > 0:
            log_message(f"Taxa média: {g_total_items_processed/total_time:.2f} itens/segundo", "SUCCESS")
        log_message(f"Checkpoint final salvo com {len(current_batch_files)} arquivos de lote", "SUCCESS")
        log_message(f"Para mesclar os resultados, execute: python merge_batches.py {CHECKPOINT_FILE}", "INFO")
                
    except Exception as e:
        log_message(f"Erro durante processamento principal: {str(e)}", "ERROR")
        log_message(traceback.format_exc(), "ERROR")
        console.print(Panel.fit(f"[bold red]Erro durante processamento: {str(e)}[/bold red]"))
        console.print(traceback.format_exc())

# Executar o código principal se este arquivo for executado diretamente
if __name__ == "__main__":
    main()