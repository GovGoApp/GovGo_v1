#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EMB_NV4_v3_1 (EMBEDDING NIVEL 4 V3.1) – Versão com visualização de progresso fixada

Responsável por gerar embeddings para itens de compras e categorizá-los,
com um painel fixo de status para NUM_WORKERS (MAX_WORKERS) linhas, exibindo as fases
de trabalho (Pré-processamento, Embeddings, Similaridade, Concluído).
"""

import os
import re
import sys
import json
import threading
import pickle
import time
import numpy as np
import pandas as pd
import nltk
import unidecode
import traceback
import glob
import math
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.table import Table
from rich.live import Live
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Baixar recursos NLTK necessários
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="sk-proj-3OWO-4DE53j-....")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT")
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA")  # Novo caminho para o catálogo unificado
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO")
INPUT_DIR = os.path.join(CLASS_PATH, "INPUT")  # Diretório com os arquivos divididos
NOVA_CAT_FILE = os.path.join(NOVA_CAT_PATH, "NOVA CAT.xlsx")
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_PATH = os.path.join(CLASS_PATH, f"RESULTS_{TIMESTAMP}")
CHECKPOINT_FILE = os.path.join(CLASS_PATH, f"CHECKPOINT_ARQUIVOS_{TIMESTAMP}.pkl")

# Criar diretório de saída se não existir
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Parâmetros gerais
BATCH_SIZE = 20      # Tamanho do batch para processamento dentro de cada arquivo
MAX_WORKERS = 20      # Número de threads para processamento paralelo (NUM_WORKERS fixo)
TOP_N = 5            # Número de categorias mais relevantes a serem retornadas
EMBEDDING_MODEL = "text-embedding-3-large"  # Modelo de embedding

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = os.path.join(BASE_PATH, "EMBEDDING")
CAT_EMBED_FILE = os.path.join(EMBEDDINGS_DIR, f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl")

# Locks para acesso concorrente
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
status_lock = threading.Lock()

# Global: Dicionário para armazenar o status fixo dos NUM_WORKERS
WORKER_STATUS = {
    i: {"phase": "Aguardando", "current": 0, "total": 1, "start_time": None}
    for i in range(1, MAX_WORKERS + 1)
}

import time

def update_worker_status(worker_id, phase, current, total):
    with status_lock:
        # Se a fase não é "Aguardando" nem "Concluído" e ainda não há tempo de início, registra-o.
        if phase not in ["Aguardando", "Concluído"] and not WORKER_STATUS[worker_id].get("start_time"):
            WORKER_STATUS[worker_id]["start_time"] = time.time()
        # Se a fase for "Concluído", limpa o tempo de início.
        if phase == "Concluído":
            WORKER_STATUS[worker_id]["start_time"] = None
        WORKER_STATUS[worker_id].update({
            "phase": phase,
            "current": current,
            "total": total
        })

def format_timer(start_time):
    if start_time is None:
        return "-"
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    return f"{minutes:02d}:{seconds:02d}"

# Mapeamento de fase para texto numerado e cor desejada
PHASE_INFO = {
    "Aguardando": {"label": "Fase 0: Aguardando", "color": "grey37"},
    "Pré-processamento": {"label": "Fase 1: Pré-processamento", "color": "red"},
    "Embeddings": {"label": "Fase 2: Embeddings", "color": "yellow"},
    "Similaridade": {"label": "Fase 3: Similaridade", "color": "blue"},
    "Concluído": {"label": "Fase 4: Concluído", "color": "green"}
}

def rich_progress_bar_str(current, total, phase, width=20):
    """
    Gera uma barra de progresso Rich com largura fixa, alterando a cor de acordo com a fase.
    Retorna uma string com markup Rich com a barra e o percentual concluído.
    """
    info = PHASE_INFO.get(phase, {"color": "grey37"})
    color = info["color"]
    ratio = current / total if total else 0
    filled = int(ratio * width)
    empty = width - filled
    # Barra: blocos preenchidos na cor da fase; o restante em cinza
    bar = f"[{color}]{'='*filled}[/{color}][grey37]{'-'*empty}[/grey37]"
    pct = f"{int(ratio * 100)}%"
    return f"{bar} {pct}"

def render_worker_table():
    """
    Cria uma tabela Rich mostrando o status de cada worker com:
      - Worker: número do worker
      - Fase: fase atual de processamento (com número e na cor definida)
      - Progresso: barra de progresso visual (largura fixa de 20 caracteres) com cor definida pela fase
      - Timer: tempo decorrido no formato mm:ss
    """
    table = Table(title="Status dos Workers", expand=True)
    table.add_column("Worker", justify="center")
    table.add_column("Fase", justify="left")
    table.add_column("Progresso", justify="center")
    table.add_column("Timer", justify="center")
    
    with status_lock:
        for worker_id in range(1, MAX_WORKERS + 1):
            status = WORKER_STATUS.get(
                worker_id,
                {"phase": "Aguardando", "current": 0, "total": 1, "start_time": None}
            )
            current = status["current"]
            total = status["total"]
            phase = status["phase"]
            # Obtém as informações da fase (rótulo e cor)
            info = PHASE_INFO.get(phase, {"label": phase, "color": "grey37"})
            phase_label = f"[{info['color']}]{info['label']}[/{info['color']}]"
            progress_bar = rich_progress_bar_str(current, total, phase, width=20)
            timer = format_timer(status.get("start_time"))
            table.add_row(str(worker_id), phase_label, progress_bar, timer)
    return table

# ============================================================
# Função de cálculo da similaridade cosseno
def cosine_similarity(a, b):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

# ============================================================
# Pré-processamento de texto
def preprocess_text(text):
    text = unidecode.unidecode(str(text))
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

# ============================================================
# Funções de salvamento/carregamento de embeddings e checkpoints
def save_embeddings(embeddings, filepath):
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings salvos em {filepath}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
            return False

def load_embeddings(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar checkpoint: {str(e)}[/bold red]")
    return None

def save_checkpoint(processed_files):
    with checkpoint_lock:
        checkpoint = {'timestamp': datetime.now().isoformat(), 'processed_files': processed_files}
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[yellow]Checkpoint salvo: processados {len(processed_files)} arquivos[/yellow]")

# ============================================================
# Carregamento de arquivos de entrada e catálogo
def load_input_file(filepath):
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo {filepath}: {str(e)}[/bold red]")
        raise

def load_catalog():
    console.print("[bold magenta]Carregando catálogo unificado...[/bold magenta]")
    try:
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Carregadas {len(cat)} categorias do catálogo unificado.[/green]")
        return cat
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise

def prepare_catalog_entries(cat):
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    cat_texts = []
    cat_meta = []
    for entry in cat:
        codcat = entry.get('CODCAT', '')
        nomcat = entry.get('NOMCAT', '')
        combined_text = preprocess_text(f"{codcat} {nomcat}")
        cat_texts.append(combined_text)
        cat_meta.append((codcat, nomcat))
    console.print(f"[magenta]Preparados {len(cat_texts)} textos de catálogo unificado.[/magenta]")
    return cat_texts, cat_meta

# ============================================================
# Geração de embeddings para batches de textos (usado para o catálogo)
def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=100, show_progress=True):
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
    return embeddings

def process_batch(batch, model):
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model=model, input=batch)
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                if attempt == max_retries - 1:
                    console.print(f"[bold red]Erro após {max_retries} tentativas: {str(e)}[/bold red]")
                else:
                    console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

# ============================================================
# Função modificada: Processamento de um chunk (atribuído a um worker) com atualização do status
def process_chunk(chunk_df, cat_embeds, cat_meta, worker_id):
    # Fase 1: Pré-processamento
    raw_texts = chunk_df["objetoCompra"].fillna("").astype(str).tolist()
    total_preproc = len(raw_texts)
    item_texts = []
    for idx, text in enumerate(raw_texts, 1):
        processed = preprocess_text(text)
        item_texts.append(processed)
        update_worker_status(worker_id, "Pré-processamento", idx, total_preproc)
    # Fase 2: Embeddings
    total_embeddings = len(item_texts)
    item_embeds = []
    for i in range(0, total_embeddings, BATCH_SIZE):
        batch = item_texts[i:i+BATCH_SIZE]
        batch_embeddings = process_batch(batch, EMBEDDING_MODEL)
        item_embeds.extend(batch_embeddings)
        update_worker_status(worker_id, "Embeddings", min(i+BATCH_SIZE, total_embeddings), total_embeddings)
    # Fase 3: Similaridade
    total_sim = len(item_embeds)
    for i, item_embed in enumerate(item_embeds, 1):
        if item_embed is None:
            update_worker_status(worker_id, "Similaridade", i, total_sim)
            continue
        sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
        top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
        for j, cat_idx in enumerate(top_indices):
            if j < TOP_N:
                cod, nom = cat_meta[cat_idx]
                chunk_df.loc[i-1, f"TOP_{j+1}"] = nom
                chunk_df.loc[i-1, f"SCORE_{j+1}"] = float(sims[cat_idx])
        update_worker_status(worker_id, "Similaridade", i, total_sim)
    # Finaliza
    update_worker_status(worker_id, "Concluído", 1, 1)
    return chunk_df

# ============================================================
# Função modificada: Processamento paralelo de um arquivo inteiro com painel fixo
def process_file_parallel(input_file, cat_embeddings, cat_meta, file_idx):
    try:
        filename = os.path.basename(input_file)
        console.print(f"[bold blue]Processando arquivo {file_idx}: {filename}[/bold blue]")
        df_input = load_input_file(input_file)
        total_rows = len(df_input)
        chunk_size = max(1, min(1000, math.ceil(total_rows / MAX_WORKERS)))
        total_chunks = math.ceil(total_rows / chunk_size)
        console.print(f"[cyan]Arquivo tem {total_rows} linhas. Dividindo em {total_chunks} chunks (~{chunk_size} linhas cada)[/cyan]")
        chunks_results = []
        futures = {}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Cria um painel fixo com MAX_WORKERS linhas
            with Live(render_worker_table(), refresh_per_second=4, console=console) as live:
                for chunk_idx in range(total_chunks):
                    start_idx = chunk_idx * chunk_size
                    end_idx = min(start_idx + chunk_size, total_rows)
                    chunk_df = df_input.iloc[start_idx:end_idx].copy().reset_index(drop=True)
                    worker_id = (chunk_idx % MAX_WORKERS) + 1  # Reaproveita a linha de worker se necessário
                    future = executor.submit(process_chunk, chunk_df, cat_embeddings, cat_meta, worker_id)
                    futures[future] = chunk_idx
                # Enquanto houver tarefas pendentes, atualize o painel
                while any(not f.done() for f in futures):
                    live.update(render_worker_table())
                    time.sleep(0.5)
                # Atualiza o painel ao final da execução
                live.update(render_worker_table())

        # Combinar resultados dos chunks
        console.print("[cyan]Combinando resultados dos chunks...[/cyan]")
        if chunks_results or futures:
            # Coleta os resultados dos futures
            for future in as_completed(futures):
                try:
                    result = future.result()
                    chunks_results.append(result)
                except Exception as e:
                    console.print(f"[bold red]Erro no chunk {futures[future]}: {str(e)}[/bold red]")
                    console.print(traceback.format_exc())
            combined_results = pd.concat(chunks_results, ignore_index=True)
            desired_columns = ['id_pncp', 'objetoCompra']
            for i in range(1, TOP_N + 1):
                desired_columns.append(f"TOP_{i}")
            for i in range(1, TOP_N + 1):
                desired_columns.append(f"SCORE_{i}")
            final_columns = [col for col in desired_columns if col in combined_results.columns]
            combined_results = combined_results[final_columns]
            output_file = os.path.join(OUTPUT_PATH, f"RESULT_{os.path.basename(input_file)}")
            combined_results.to_excel(output_file, index=False)
            console.print(f"[green]Resultado do arquivo {file_idx} salvo em {output_file}[/green]")
            return input_file, True
        else:
            console.print(f"[bold red]Nenhum resultado gerado para o arquivo {filename}[/bold red]")
            return input_file, False

    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo {file_idx}: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return input_file, False

# ============================================================
# Função principal (main)
def main():
    start_time = time.time()
    try:
        checkpoint = load_checkpoint()
        processed_files = checkpoint['processed_files'] if checkpoint else []

        input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "INPUT_*.xlsx")))
        console.print(f"[bold blue]Encontrados {len(input_files)} arquivos de entrada[/bold blue]")
        remaining_files = [f for f in input_files if f not in processed_files]
        console.print(f"[bold blue]Processando {len(remaining_files)} arquivos restantes[/bold blue]")

        if not remaining_files:
            console.print("[yellow]Todos os arquivos já foram processados.[/yellow]")
            return

        # Processamento do catálogo unificado
        cat = load_catalog()
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if (cat_embeddings is None or len(cat_embeddings) != len(cat_texts)):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        console.print("[green]Embeddings de categorias preparados.[/green]")

        # Processamento sequencial dos arquivos restantes
        file_counter = 1
        for idx, input_file in enumerate(remaining_files, 1):
            file_path, success = process_file_parallel(input_file, cat_embeddings, cat_meta, file_counter)
            if success:
                processed_files.append(file_path)
                save_checkpoint(processed_files)
            file_counter += 1
            time.sleep(1)
        
        end_time = time.time()
        total_time = end_time - start_time
        console.print(f"[green]Processamento concluído em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total)[/green]")
        console.print(f"[cyan]Os resultados foram salvos em: {OUTPUT_PATH}[/cyan]")

    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        console.print(traceback.format_exc())

# ============================================================
# Ponto de entrada
if __name__ == "__main__":
    main()
