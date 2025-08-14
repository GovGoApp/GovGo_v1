### EMB_NV2_v4 (EMBEDDING NIVEL 2 V4) ###
# Este script é responsável por gerar embeddings para itens de compras e
# classificá-los em categorias unificadas.
# As modificações a seguir implementam:
# 1. Geração de embeddings em lote (já existente).
# 2. Cálculo de similaridade de maneira vetorizada, com cada worker processando
#    uma partição dos itens e exibindo sua própria progress bar.
# Essa abordagem visa reduzir o tempo total de processamento.
#
# O restante do código permanece inalterado.

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Baixar recursos NLTK necessários
nltk.download('stopwords')
nltk.download('wordnet')

console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")  # Novo caminho para o catálogo unificado
CLASS_PATH = BASE_PATH + "CLASSY\\"
INPUT_PATH = CLASS_PATH + "INPUT\\"
OUTPUT_PATH = CLASS_PATH + "OUTPUT\\"
CHECKPOINT_PATH = CLASS_PATH + "CHECKPOINTS\\"

INPUT_FILE = INPUT_PATH + "\\INPUT_001.xlsx"
SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV3"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = OUTPUT_PATH + f"OUTPUT_001_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CHECKPOINT_PATH + f"CHECKPOINT_001_{TIMESTAMP}.pkl"

# Constantes para controle de execução
MAX_WORKERS = 8  # Número de threads para processamento paralelo (usado apenas para a similaridade)
console.print("CPU: " + str(os.cpu_count()))
console.print("WORKERS = " + str(MAX_WORKERS))
TOP_N = 5  # Número de categorias mais relevantes a serem retornadas
BATCH_SIZE = 100  # Tamanho do lote para processamento de embeddings

# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = BASE_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"

# Criar locks para acessos concorrentes
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()

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

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
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
    """Carrega embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def save_checkpoint(last_processed, output_file):
    """Salvar checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)

def load_data():
    """Carregar dados do Excel e catálogo unificado."""
    console.print("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]")
    checkpoint = load_checkpoint()
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        try:
            total_rows = pd.read_excel(INPUT_FILE, sheet_name=SHEET, nrows=0).shape[0]
            skiprows = list(range(1, last_processed + 1))
            df_items = pd.read_excel(INPUT_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel (a partir da linha {last_processed+1}).[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    else:
        try:
            df_items = pd.read_excel(INPUT_FILE, sheet_name=SHEET)
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
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Carregados {len(existing_results)} resultados anteriores.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
            existing_results = pd.DataFrame()
    else:
        existing_results = pd.DataFrame()
    return df_items, cat, existing_results, checkpoint

def prepare_catalog_entries(cat):
    """Preparar entradas de catálogo unificado para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    cat_texts = []
    cat_meta = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("Processando catálogo unificado...", total=len(cat))
        for entry in cat:
            codcat = entry.get('CODCAT', '')
            nomcat = entry.get('NOMCAT', '')
            combined_text = preprocess_text(f"{codcat} {nomcat}")
            cat_texts.append(combined_text)
            cat_meta.append((codcat, nomcat))
            progress.update(task, advance=1)
    console.print(f"[magenta]Preparados {len(cat_texts)} textos de catálogo unificado.[/magenta]")
    return cat_texts, cat_meta

# ---------------------------------------------------------------------
# Para embeddings, mantemos a geração por batch (vetorizado por API) – sem progress bars por worker
def process_batch(batch, model):
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
                retry_delay += attempt * 2
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

def get_embeddings(texts, model=EMBEDDING_MODEL):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI (por lote)."""
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
    return embeddings

# ---------------------------------------------------------------------
# Cálculo de similaridade vetorizado com progress por worker
def process_similarity_worker(worker_id, indices, item_embeds_arr, norm_cat, cat_meta, progress, task_id):
    worker_results = []
    for idx in indices:
        # Processamento vetorizado para cada item (linha)
        row = item_embeds_arr[idx]
        norm_item = row / np.maximum(np.linalg.norm(row), 1e-8)
        similarity_vector = np.dot(norm_item, norm_cat.T)  # Vetorizado para uma única linha
        top_indices = np.argsort(similarity_vector)[-TOP_N:][::-1]
        result = {}
        for j, cat_idx in enumerate(top_indices):
            result[f"TOP_{j+1}"] = cat_meta[cat_idx][1]
            result[f"SCORE_{j+1}"] = float(similarity_vector[cat_idx])
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
    console.print(f"[bold blue]Worker {worker_id} finalizou similaridade para {len(indices)} itens[/bold blue]")
    return worker_results

def partition_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]


def classify_items(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calculando os embeddings dos textos e 
    computando a similaridade com os embeddings do catálogo unificado de forma vetorizada.
    A computação é particionada entre workers, cada um exibindo seu próprio progress bar.
    """
    result_df = df_items.copy()
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0

    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Geração dos embeddings dos itens em lote
    item_embeds = embedding_function(item_texts)
    item_embeds_arr = np.vstack(item_embeds)  # (num_itens, D)
    
    # Converter embeddings do catálogo para matriz e normalizar uma vez
    cat_embeds_arr = np.vstack(cat_embeds)
    norm_cat = cat_embeds_arr / np.maximum(np.linalg.norm(cat_embeds_arr, axis=1, keepdims=True), 1e-8)
    
    # Particionar os índices dos itens entre os workers
    num_items = item_embeds_arr.shape[0]
    all_indices = list(range(num_items))
    partitions = partition_list(all_indices, MAX_WORKERS)
    
    similarity_results = []
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    progress.start()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for worker_id, indices in enumerate(partitions, start=1):
            task_id = progress.add_task(f"Worker {worker_id} similaridade", total=len(indices))
            futures.append(executor.submit(process_similarity_worker, worker_id, indices,
                                             item_embeds_arr, norm_cat, cat_meta, progress, task_id))
        for future in futures:
            similarity_results.extend(future.result())
    progress.stop()
    
    for idx, similarity_data in similarity_results:
        for key, value in similarity_data.items():
            result_df.at[idx, key] = value

    if "id" in result_df.columns and "id_pncp" not in result_df.columns:
        result_df = result_df.rename(columns={"id": "id_pncp"})
    desired_columns = ['id_pncp', 'objetoCompra']
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"TOP_{i}")
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"SCORE_{i}")
    final_columns = [col for col in desired_columns if col in result_df.columns]
    return result_df[final_columns]

def main():
    start_time = time.time()
    try:
        df_items, cat, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Preparar entradas do catálogo
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Carregar (ou gerar) embeddings do catálogo
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Classificar itens usando a similaridade vetorizada com progress bar por worker
        console.print("[bold magenta]Iniciando classificação (similaridade vetorizada por worker)...[/bold magenta]")
        results = classify_items(df_items, cat_embeddings, cat_meta, get_embeddings)
        
        end_time = time.time()
        total_time = end_time - start_time
        console.print(f"[green]Classificação de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        console.print(f"[cyan]Os embeddings foram salvos em:\n- Catálogo: {CAT_EMBED_FILE}")
        console.print(f"[bold magenta]Salvando resultados em {OUTPUT_FILE}...[/bold magenta]")
        results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[green]Resultados salvos com sucesso![/green]")
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
