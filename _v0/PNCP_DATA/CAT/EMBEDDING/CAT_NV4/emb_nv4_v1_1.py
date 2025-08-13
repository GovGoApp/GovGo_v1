#!/usr/bin/env python
# -*- coding: utf-8 -*-
### EMB_NV4_v1 - Versão com processamento de lotes em paralelo confiável
### VERSÃO v1.1: Claude 3.7 Sonnet Thinking (VS CODE COpilot)

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

# Estado global compartilhado
g_processed_batches = {}
g_batch_status = {}
g_start_time = time.time()
g_total_items_processed = 0
g_avg_batch_time = 0.0

# Configurar logging para o console e arquivo
def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    with log_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    if level == "ERROR":
        console.print(f"[bold red]{log_entry}[/bold red]")
    elif level == "WARNING":
        console.print(f"[bold yellow]{log_entry}[/bold yellow]")
    elif level == "SUCCESS":
        console.print(f"[bold green]{log_entry}[/bold green]")
    else:
        console.print(log_entry)

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

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=25):
    """Gera embeddings sem criar barras de progresso que causariam conflito."""
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Log estático para acompanhamento
    log_message(f"Gerando embeddings para {len(texts)} textos em {total_batches} batches...", "INFO")
    
    # Processar em lotes sem barras de progresso
    start_time = time.time()
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
        
        # Log periódico para batches maiores
        if (i // batch_size) % 10 == 0 or (i + batch_size >= len(texts)):
            progress_pct = min(100, int(100 * (i + len(batch)) / len(texts)))
            elapsed = time.time() - start_time
            rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
            log_message(f"Progresso de embeddings: {progress_pct}% ({i + len(batch)}/{len(texts)}) - {rate:.1f} textos/s", "INFO")
    
    log_message(f"Embeddings gerados em {time.time() - start_time:.1f}s", "SUCCESS")
    return embeddings

def cosine_similarity(a, b):
    """Calcula similaridade de cosseno entre dois vetores."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

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
        # Inicializar relatório
        update_batch_status(batch_id, "▶ Iniciando processamento", progress=0)
        
        # Criar DataFrame de resultados
        result_df = batch_df.copy()
        
        # Adicionar TOP_N colunas
        for i in range(1, TOP_N + 1):
            result_df[f"TOP_{i}"] = ""
            result_df[f"SCORE_{i}"] = 0.0
        
        # 1. EXTRAIR TEXTOS
        update_batch_status(batch_id, "📄 Extraindo textos...", progress=5)
        raw_texts = []
        for idx, row in enumerate(batch_df.iterrows()):
            _, row_data = row
            obj_compra = str(row_data.get("objetoCompra", ""))
            itens = str(row_data.get("itens", ""))
            combined_text = f"{obj_compra} {itens}".strip()
            raw_texts.append(combined_text)
            
            # Atualizar progresso periodicamente
            if idx % (batch_size // 10 or 1) == 0:
                progress = 5 + int(10 * idx / batch_size)
                update_batch_status(batch_id, f"📄 Extraindo textos: {idx}/{batch_size}", progress=progress)
        
        # 2. PRÉ-PROCESSAR TEXTOS
        update_batch_status(batch_id, "🔄 Iniciando pré-processamento", progress=15)
        
        with ThreadPoolExecutor(max_workers=max(2, MAX_WORKERS // 4)) as executor:
            # Dividir em chunks para processamento paralelo
            chunk_size = max(1, len(raw_texts) // (MAX_WORKERS // 4))
            chunks = [raw_texts[i:i+chunk_size] for i in range(0, len(raw_texts), chunk_size)]
            chunks_total = len(chunks)
            
            # Contador compartilhado de progresso
            completed_chunks = [0]
            chunk_lock = threading.Lock()
            
            def process_and_report(chunk):
                result = [preprocess_text(text) for text in chunk]
                with chunk_lock:
                    completed_chunks[0] += 1
                    percent = int(100 * completed_chunks[0] / chunks_total)
                    progress = 15 + int(15 * completed_chunks[0] / chunks_total)
                    update_batch_status(
                        batch_id, 
                        f"🔄 Pré-processamento: {completed_chunks[0]}/{chunks_total} chunks ({percent}%)", 
                        progress=progress
                    )
                return result
            
            # Processar chunks em paralelo com relatórios de progresso
            futures = [executor.submit(process_and_report, chunk) for chunk in chunks]
            processed_chunks = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Combinar resultados
        processed_texts = []
        for chunk in processed_chunks:
            processed_texts.extend(chunk)
        
        # 3. GERAR EMBEDDINGS
        update_batch_status(batch_id, "🧠 Gerando embeddings...", progress=30)
        
        # Medir progresso durante a geração de embeddings
        embeddings = []
        emb_batch_size = 25  # Tamanho do batch para OpenAI
        total_emb_batches = int(np.ceil(len(processed_texts) / emb_batch_size))
        
        for i in range(0, len(processed_texts), emb_batch_size):
            current_batch = i // emb_batch_size + 1
            percent = int(100 * current_batch / total_emb_batches)
            progress = 30 + int(30 * current_batch / total_emb_batches)
            
            update_batch_status(
                batch_id, 
                f"🧠 Embeddings: {current_batch}/{total_emb_batches} batches ({percent}%)", 
                progress=progress
            )
            
            batch = processed_texts[i:i+emb_batch_size]
            batch_embeddings = process_batch(batch, EMBEDDING_MODEL)
            embeddings.extend(batch_embeddings)
        
        # 4. CALCULAR SIMILARIDADES
        update_batch_status(batch_id, "🔍 Calculando similaridades...", progress=60)
        
        items_total = len(embeddings)
        for idx, item_embed in enumerate(embeddings):
            # Calcular similaridade com todas as categorias
            sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
            
            # Obter TOP_N categorias com maior similaridade
            top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
            
            # Armazenar TOP_N categorias e scores
            for i, cat_idx in enumerate(top_indices):
                if i < TOP_N:
                    _, nom = cat_meta[cat_idx]
                    result_df.iloc[idx, result_df.columns.get_loc(f"TOP_{i+1}")] = nom
                    result_df.iloc[idx, result_df.columns.get_loc(f"SCORE_{i+1}")] = float(sims[cat_idx])
            
            # Atualizar progresso periodicamente
            if idx % (items_total // 10 or 1) == 0 or idx == items_total - 1:
                percent = int(100 * (idx + 1) / items_total)
                progress = 60 + int(30 * (idx + 1) / items_total)
                rate = (idx + 1) / (time.time() - batch_start_time) if time.time() - batch_start_time > 0 else 0
                
                update_batch_status(
                    batch_id, 
                    f"🔍 Similaridades: {idx+1}/{items_total} ({percent}%) • {rate:.1f} itens/s", 
                    progress=progress
                )
        
        # 5. FINALIZAR E SALVAR
        update_batch_status(batch_id, "💾 Salvando resultados...", progress=90)
        
        # Processar colunas finais
        if "id" in result_df.columns and "id_pncp" not in result_df.columns:
            result_df = result_df.rename(columns={"id": "id_pncp"})
        
        # Garantir presença das colunas necessárias
        desired_columns = ['id_pncp', 'objetoCompra', 'itens']
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"TOP_{i}")
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"SCORE_{i}")
        
        final_columns = [col for col in desired_columns if col in result_df.columns]
        result_df = result_df[final_columns]
        
        # Salvar resultados
        last_processed = start_idx + len(batch_df) - 1
        batch_filename = os.path.join(
            BATCH_OUTPUT_DIR, 
            f"batch_{batch_id:04d}_{start_idx}_{last_processed}.xlsx"
        )
        
        result_df.to_excel(batch_filename, index=False)
        
        # Calcular estatísticas e tempo
        batch_time = time.time() - batch_start_time
        items_per_second = len(batch_df) / batch_time
        
        # Mensagem de conclusão com estatísticas
        completion_message = (
            f"✅ CONCLUÍDO - {len(batch_df)} itens em {batch_time:.1f}s ({items_per_second:.1f} itens/s)"
        )
        update_batch_status(batch_id, completion_message, progress=100)
        
        # Atualizar contadores globais
        with status_lock:
            global g_total_items_processed, g_avg_batch_time
            g_processed_batches[batch_id] = {
                'time': batch_time,
                'items': batch_size,
                'speed': items_per_second
            }
            
            g_total_items_processed += batch_size
            
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
        update_batch_status(batch_id, f"❌ ERRO: {str(e)}", progress=-1)  # -1 indica erro
        log_queue.put((batch_id, f"[ERRO] {error_msg}"))
        log_message(error_msg, "ERROR")
        log_message(traceback.format_exc(), "ERROR")
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
                    # Obter mensagem da fila com timeout para permitir verificações periódicas
                    try:
                        batch_id, message = log_queue.get(timeout=0.5)
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
                        
                        # Submeter lote para processamento
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
                        
                        # Atualizar status
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