### EMB_NV4_v2 - Versão com processamento de lotes em paralelo confiável
# ### VERSÃO v1.2: o3-mini-high (ChatGPT)

import os
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn, MofNCompleteColumn
from rich.live import Live
from rich.table import Table
from rich import box
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle
import time
import re
import unidecode
import nltk
import queue

# Criação da instância do console
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")


# Função para criar a tabela de status atualizada dos batches com informações da fase atual
def create_batch_status_table(batch_statuses, completed, total):
    table = Table(
        title=f"Processamento de Lotes ({completed}/{total} concluídos)",
        box=box.SIMPLE,
        expand=False,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Última Atualização", style="yellow", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Fase Atual", style="bold blue")
    batch_ids = sorted(batch_statuses.keys())[-12:]
    for batch_id in batch_ids:
        status = batch_statuses.get(batch_id, {})
        msg = status.get("message", "Desconhecido")
        phase = status.get("phase", "")
        # Define cor conforme a mensagem
        if "CONCLUÍDO" in msg:
            style = "green"
        elif "ERRO" in msg:
            style = "red"
        elif "Calculando" in msg:
            style = "blue"
        elif "Gerando" in msg:
            style = "yellow"
        else:
            style = "white"
        table.add_row(
            f"{batch_id}",
            status.get("time", ""),
            f"[{style}]{msg}[/{style}]",
            phase
        )
    return table

# Configurações e caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
EXCEL_FILE = CLASS_PATH + "#CONTRATAÇÃO_ID_COMPRAS_ITENS.xlsx"  # Arquivo com 1M de linhas
SHEET = "ITENS"
NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = CLASS_PATH + f"GRANDES_VOLUMES_CATNV4_OPENAI_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_GRANDES_VOLUMES_{TIMESTAMP}.pkl"
BATCH_OUTPUT_DIR = os.path.join(CLASS_PATH, "BATCH_OUTPUT")
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)

MAX_CONCURRENT_BATCHES = 12
BATCH_SIZE = 5000
MAX_WORKERS = os.cpu_count() * 2
TOP_N = 10
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDINGS_DIR = BASE_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = os.path.join(EMBEDDINGS_DIR, f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl")
for directory in [EMBEDDINGS_DIR, BATCH_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Locks para acesso concorrente
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()

# Inicialização do NLTK
try:
    nltk_data_path = os.path.join(os.path.expanduser('~'), 'nltk_data')
    os.makedirs(nltk_data_path, exist_ok=True)
    nltk.data.path.append(nltk_data_path)
    for resource in ['stopwords', 'wordnet']:
        try:
            nltk.download(resource, quiet=True)
        except Exception as e:
            console.print(f"[yellow]Aviso: Não foi possível baixar {resource}: {str(e)}[/yellow]")
    from nltk.corpus import stopwords
    portuguese_stopwords = set(stopwords.words('portuguese'))
    from nltk.stem import WordNetLemmatizer
    lemmatizer = WordNetLemmatizer()
except Exception as e:
    console.print(f"[bold red]Erro na configuração do NLTK: {str(e)}[/bold red]")
    portuguese_stopwords = set()
    class SimpleLemmatizer:
        def lemmatize(self, word):
            return word
    lemmatizer = SimpleLemmatizer()

def preprocess_text(text):
    try:
        text = unidecode.unidecode(str(text))
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        words = text.split()
        words = [word for word in words if word not in portuguese_stopwords]
        words = [lemmatizer.lemmatize(word) for word in words]
    except Exception as e:
        console.print(f"[yellow]Aviso: Usando processamento simplificado para texto: {str(e)}[/yellow]")
        text = unidecode.unidecode(str(text)).lower()
        text = re.sub(r'[^a-z\s]', '', text)
        words = [word for word in text.split() if len(word) > 2]
    return ' '.join(words)

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

def save_checkpoint(last_processed, output_file, batch_files=None):
    with checkpoint_lock:
        processed_ids = list(get_processed_batch_ids(batch_files or []))
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file,
            'batch_files': batch_files or [],
            'processed_batch_ids': processed_ids
        }
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo: {last_processed} itens processados, {len(processed_ids)} lotes concluídos[/green]")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
            console.print(f"[yellow]Checkpoint encontrado - Último processado: {checkpoint['last_processed']}[/yellow]")
            return checkpoint
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar checkpoint: {str(e)}[/bold red]")
    return None

def load_data():
    console.print("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]")
    checkpoint = load_checkpoint()
    last_processed = 0
    batch_files = []
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint.get('last_processed', 0)
        batch_files = checkpoint.get('batch_files', [])
        skiprows = list(range(1, last_processed + 1)) if last_processed > 0 else None
    else:
        skiprows = None
    try:
        if skiprows:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel (a partir da linha {last_processed+1}).[/green]")
        else:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
        raise
    try:
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Carregadas {len(cat)} categorias do catálogo unificado.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise
    return df_items, cat, last_processed, batch_files, checkpoint

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

def process_batch(batch, model=EMBEDDING_MODEL):
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model=model, input=batch)
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI (lote de {len(batch)} textos): {str(e)}[/bold red]")
                raise

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=25):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
    return embeddings

def cosine_similarity(a, b):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

def process_text_batch(texts):
    return [preprocess_text(text) for text in texts]

def process_complete_batch(batch_df, cat_embeds, cat_meta, batch_id, start_idx, log_queue, batch_status):
    batch_start_time = time.time()
    try:
        log_queue.put((batch_id, f"Lote {batch_id} iniciado - {len(batch_df)} itens", "Início"))
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "Iniciado", "phase": "Extração"}
        result_df = batch_df.copy()
        for i in range(1, TOP_N + 1):
            result_df[f"TOP_{i}"] = ""
            result_df[f"SCORE_{i}"] = 0.0
        raw_texts = []
        for _, row in batch_df.iterrows():
            objeto = str(row.get("objetoCompra", ""))
            itens = str(row.get("itens", ""))
            combined_text = f"{objeto} {itens}".strip()
            raw_texts.append(combined_text)
        log_queue.put((batch_id, "Extração de textos concluída.", "Extração"))
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "Extração concluída", "phase": "Pré-processamento"}
        with ThreadPoolExecutor(max_workers=max(2, MAX_WORKERS // 4)) as executor:
            chunk_size = max(1, len(raw_texts) // (MAX_WORKERS // 4))
            chunks = [raw_texts[i:i+chunk_size] for i in range(0, len(raw_texts), chunk_size)]
            processed_chunks = list(executor.map(process_text_batch, chunks))
        processed_texts = [pt for chunk in processed_chunks for pt in chunk]
        log_queue.put((batch_id, "Pré-processamento concluído.", "Pré-processamento"))
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "Pré-processamento concluído", "phase": "Geração de Embeddings"}
        item_embeds = get_embeddings(processed_texts)
        log_queue.put((batch_id, "Geração de embeddings concluída.", "Geração de Embeddings"))
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "Embeddings gerados", "phase": "Cálculo de Similaridades"}
        total_items = len(item_embeds)
        for idx, item_embed in enumerate(item_embeds):
            sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
            top_indices = np.argsort(sims)[-TOP_N:][::-1] if sims.size > 0 else []
            for i, cat_idx in enumerate(top_indices):
                if i < TOP_N:
                    _, nome = cat_meta[cat_idx]
                    result_df.iloc[idx, result_df.columns.get_loc(f"TOP_{i+1}")] = nome
                    result_df.iloc[idx, result_df.columns.get_loc(f"SCORE_{i+1}")] = float(sims[cat_idx])
            if idx % 1000 == 0 or idx == total_items - 1:
                perc = int(100 * (idx + 1) / total_items)
                log_queue.put((batch_id, f"Calculando similaridades: {perc}% concluído.", "Cálculo"))
        log_queue.put((batch_id, "Cálculo de similaridades concluído.", "Finalização"))
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "Lote CONCLUÍDO", "phase": "Concluído"}
        if "id" in result_df.columns and "id_pncp" not in result_df.columns:
            result_df = result_df.rename(columns={"id": "id_pncp"})
        desired_columns = ['id_pncp', 'objetoCompra', 'itens']
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"TOP_{i}")
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"SCORE_{i}")
        final_columns = [col for col in desired_columns if col in result_df.columns]
        result_df = result_df[final_columns]
        last_processed = start_idx + len(batch_df) - 1
        batch_filename = os.path.join(BATCH_OUTPUT_DIR, f"batch_{batch_id:04d}_{start_idx}_{last_processed}.xlsx")
        result_df.to_excel(batch_filename, index=False)
        batch_time = time.time() - batch_start_time
        items_per_second = len(batch_df) / batch_time
        log_queue.put((batch_id, f"Lote {batch_id} CONCLUÍDO - {len(batch_df)} itens em {batch_time:.1f}s ({items_per_second:.1f} itens/s).", "Concluído"))
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
        console.print(f"[bold red]{error_msg}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        batch_status[batch_id] = {"time": datetime.now().strftime("%H:%M:%S"), "message": "[ERRO] " + error_msg, "phase": "Erro"}
        return None

def get_processed_batch_ids(batch_files):
    processed_ids = set()
    if not batch_files:
        return processed_ids
    for file_path in batch_files:
        try:
            filename = os.path.basename(file_path)
            batch_id = int(filename.split('_')[1])
            processed_ids.add(batch_id)
        except (IndexError, ValueError):
            console.print(f"[yellow]Warning: Could not extract batch ID from {file_path}[/yellow]")
    return processed_ids

def main():
    console.print("[bold yellow]EMB_NV4_v2 - Sistema de classificação com embeddings para grandes volumes - Versão Melhorada[/bold yellow]")
    start_time = time.time()
    batch_status = {}
    log_queue = queue.Queue()
    df_items, cat, last_processed, batch_files, checkpoint = load_data()
    cat_texts, cat_meta = prepare_catalog_entries(cat)
    console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
    cat_embeddings = load_embeddings(CAT_EMBED_FILE)
    if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
        console.print("[yellow]Embeddings de catálogo não encontrados. Gerando novos...[/yellow]")
        cat_embeddings = get_embeddings(cat_texts)
        save_embeddings(cat_embeddings, CAT_EMBED_FILE)
    else:
        console.print("[green]Embeddings de catálogo carregados com sucesso.[/green]")
    batches = []
    total_items = len(df_items)
    for i in range(0, total_items, BATCH_SIZE):
        batch_df = df_items.iloc[i:i+BATCH_SIZE].copy().reset_index(drop=True)
        batches.append((i, batch_df))
    processed_batch_ids = get_processed_batch_ids(batch_files)
    console.print(f"[yellow]Encontrados {len(processed_batch_ids)} lotes já processados[/yellow]")
    results = []
    total_batches = len(batches)
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor, Live(create_batch_status_table(batch_status, 0, total_batches), refresh_per_second=1) as live:
        future_to_batch = {}
        for idx, (start_idx, batch_df) in enumerate(batches):
            batch_id = idx + 1
            if batch_id in processed_batch_ids:
                continue
            future = executor.submit(process_complete_batch, batch_df, cat_embeddings, cat_meta, batch_id, start_idx, log_queue, batch_status)
            future_to_batch[future] = batch_id
        completed_batches = 0
        while future_to_batch:
            for future in as_completed(list(future_to_batch.keys())):
                res = future.result()
                batch_id = future_to_batch.pop(future)
                if res is not None:
                    results.append(res)
                    completed_batches += 1
                    save_checkpoint(res['last_processed'], OUTPUT_FILE, batch_files)
                live.update(create_batch_status_table(batch_status, completed_batches, total_batches))
            while not log_queue.empty():
                bid, msg, phase = log_queue.get()
                console.log(f"[Batch {bid}] [{phase}] {msg}")
    end_time = time.time()
    console.print(f"[bold green]Processamento concluído em {end_time - start_time:.1f} segundos.[/bold green]")

if __name__ == "__main__":
    main()
