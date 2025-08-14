##### CLASSSYYYY V1: PARELLELLL
### EMB_NV2_v4 (EMBEDDING NIVEL 2 V4) ###
# Este script é responsável por gerar embeddings para itens de compras e
# classificá-los em categorias unificadas. Foi modificado para que:
# 1. O processamento de embeddings seja realizado em paralelo, utilizando um único
#    Progress compartilhado com uma task para cada worker.
# 2. O cálculo de similaridade seja feito em paralelo, também com um único Progress
#    compartilhado exibindo a progressão de cada worker.
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

console = Console()
# Verificar se o Faiss está disponível
try:
    import faiss
    FAISS_AVAILABLE = True
    console.print("[green]Faiss instalado e disponível para busca de similaridade acelerada.[/green]")
except ImportError:
    FAISS_AVAILABLE = False
    console.print("[yellow]Faiss não encontrado. Será usada implementação padrão de NumPy.[/yellow]")
    console.print("[yellow]Para instalar: pip install faiss-cpu ou pip install faiss-gpu[/yellow]")

# Baixar recursos NLTK necessários
nltk.download('stopwords')
nltk.download('wordnet')

# Instância do console para exibição formatada
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

INPUT_FILE = INPUT_PATH + "\\INPUT_003.xlsx"
SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = OUTPUT_PATH + f"OUTPUT_003_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CHECKPOINT_PATH + f"CHECKPOINT_003_{TIMESTAMP}.pkl"

# Constantes para controle de execução
MAX_WORKERS = 8  # Número de threads para processamento paralelo
console.print("CPU: " + str(os.cpu_count()))
console.print("WORKERS = " + str(MAX_WORKERS))
TOP_N = 10  # Número de categorias mais relevantes a serem retornadas
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
            skiprows = list(range(1, last_processed + 1))  # Pular cabeçalho + linhas já processadas
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
    # Usando um único Progress para todo o catálogo
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

# Função auxiliar para particionar uma lista em n partes aproximadamente iguais
def partition_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

# ---------------------------------------------------------------------
# Processamento paralelo de embeddings com um único Progress compartilhado para cada worker
def process_embedding_partition_shared(batch_indices, texts, model, worker_id, progress, task_id):
    worker_results = []
    for i in batch_indices:
        batch = texts[i:i+BATCH_SIZE]
        batch_embeddings = process_batch(batch, model)
        worker_results.extend(batch_embeddings)
        progress.update(task_id, advance=1)
    return worker_results

def get_embeddings(texts, model=EMBEDDING_MODEL):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI com progress bars por worker."""
    embeddings = []
    all_indices = list(range(0, len(texts), BATCH_SIZE))
    partitions = partition_list(all_indices, MAX_WORKERS)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    progress.start()
    futures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for worker_id, partition in enumerate(partitions, start=1):
            task_id = progress.add_task(f"Worker {worker_id} embeddings", total=len(partition))
            futures.append(executor.submit(process_embedding_partition_shared, partition, texts, model, worker_id, progress, task_id))
        for future in futures:
            embeddings.extend(future.result())
    progress.stop()
    return embeddings

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
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

# ---------------------------------------------------------------------
# Cálculo paralelo da similaridade com um único Progress compartilhado para cada worker
# MODIFICADO: Versão otimizada usando vetorização NumPy
def process_similarity_partition_shared(args_sublist, cat_embeds_matrix, cat_meta, worker_id, progress, task_id):
    worker_results = []
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            continue
            
        # Normalize o embedding do item
        item_norm = np.linalg.norm(item_embed)
        if item_norm == 0:
            norm_item_embed = item_embed
        else:
            norm_item_embed = item_embed / item_norm
            
        # Calcular similaridade usando produto escalar (os embeddings do catálogo já estão normalizados)
        sims = np.dot(cat_embeds_matrix, norm_item_embed)
        
        # Obter os TOP_N índices com maior similaridade
        top_indices = np.argsort(sims)[-TOP_N:][::-1]
        
        # Formatar os resultados
        result = {}
        for i, cat_idx in enumerate(top_indices):
            _, nom = cat_meta[cat_idx]
            result[f"TOP_{i+1}"] = nom
            result[f"SCORE_{i+1}"] = float(sims[cat_idx])
            
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
        
    return worker_results

# Versão usando Faiss para busca de similaridade acelerada
def process_similarity_partition_faiss(args_sublist, faiss_index, cat_meta, worker_id, progress, task_id):
    worker_results = []
    embeddings = []
    indices = []
    
    # Coletar embeddings válidos
    for idx, item_embed in args_sublist:
        if item_embed is not None:
            embeddings.append(item_embed)
            indices.append(idx)
    
    # Se não há embeddings válidos, retorna resultados vazios
    if not embeddings:
        return [(idx, {}) for idx, _ in args_sublist]
    
    # Transformar em array numpy e normalizar
    embeddings_array = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings_array)
    
    # Realizar busca em lote
    D, I = faiss_index.search(embeddings_array, TOP_N)
    
    # Processar resultados
    for i, (distances, neighbors) in enumerate(zip(D, I)):
        idx = indices[i]
        result = {}
        for j, (neighbor_idx, distance) in enumerate(zip(neighbors, distances)):
            _, nom = cat_meta[neighbor_idx]
            # Faiss usa distância euclidiana, converter para similaridade cosseno (1 - dist²/2)
            similarity = 1 - (distance ** 2) / 2
            result[f"TOP_{j+1}"] = nom
            result[f"SCORE_{j+1}"] = float(similarity)
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
    
    # Adicionar resultados vazios para embeddings nulos
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            
    return worker_results

def classify_items(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens
    e compara com os embeddings do catálogo unificado para classificação.
    Tanto a geração dos embeddings quanto o cálculo de similaridade são realizados
    em paralelo com um único Progress compartilhado exibindo a progressão de cada worker.
    
    MODIFICADO: Usa cálculo vetorizado de similaridade e opcionalmente Faiss
    """
    result_df = df_items.copy()
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0

    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Geração dos embeddings dos itens
    item_embeds = embedding_function(item_texts)
    
    # Preparar embeddings do catálogo para cálculo vetorizado
    cat_embeds_array = np.array(cat_embeds)
    
    # Normalizar os embeddings do catálogo (uma única vez)
    cat_norms = np.linalg.norm(cat_embeds_array, axis=1, keepdims=True)
    cat_norms = np.where(cat_norms == 0, 1, cat_norms)  # Evitar divisão por zero
    norm_cat_embeds = cat_embeds_array / cat_norms
    
    # Criar índice Faiss se disponível
    faiss_index = None
    if FAISS_AVAILABLE:
        console.print("[cyan]Usando Faiss para busca de similaridade acelerada...[/cyan]")
        d = cat_embeds_array.shape[1]  # Dimensão dos embeddings
        faiss_index = faiss.IndexFlatIP(d)  # Índice para produto interno (similaridade de cosseno)
        # Normalizar antes de adicionar ao índice
        normalized_vectors = cat_embeds_array.astype(np.float32).copy()
        faiss.normalize_L2(normalized_vectors)
        faiss_index.add(normalized_vectors)
    
    # Preparar argumentos para cálculo de similaridade
    args_list = [(idx, item_embed) for idx, item_embed in enumerate(item_embeds)]
    partitions = partition_list(args_list, MAX_WORKERS)
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
        for worker_id, part in enumerate(partitions, start=1):
            task_id = progress.add_task(f"Worker {worker_id} similarity", total=len(part))
            if FAISS_AVAILABLE and faiss_index is not None:
                futures.append(executor.submit(
                    process_similarity_partition_faiss, 
                    part, 
                    faiss_index,
                    cat_meta,
                    worker_id, 
                    progress, 
                    task_id
                ))
            else:
                futures.append(executor.submit(
                    process_similarity_partition_shared, 
                    part, 
                    norm_cat_embeds,
                    cat_meta,
                    worker_id, 
                    progress, 
                    task_id
                ))
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
        
        # Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        console.print("[bold magenta]Iniciando classificação com processamento paralelo...[/bold magenta]")
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
