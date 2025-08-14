##### CLASSY FAISS - Classificação de Itens com Embeddings e Similaridade Hierárquica #####
###### FAISSSSS RULESSSS!!!!!

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
import faiss

console = Console()

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
CLASSY_PATH = BASE_PATH + "CLASSY\\"
INPUT_PATH = CLASSY_PATH + "INPUT\\"

OUTPUT_PATH = CLASSY_PATH + "CF_v3\\OUTPUT\\"
CHECKPOINT_PATH = CLASSY_PATH + "CF_v3\\CHECKPOINT\\"

SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

# Constantes para controle de execução
MAX_WORKERS = 12  # Número de threads para processamento paralelo
console.print("WORKERS = " + str(MAX_WORKERS))


BATCH_SIZE = 100  # Tamanho do lote para processamento de embeddings
INPUT_INITIAL_NUMBER = 1

PAGE_BEGIN = 1  # Página inicial para leitura do Excel
PAGE_END = 1 # Página final para leitura do Excel 
# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"

OUTPUT_DEBUG = True  # Controla o modo de depuração da saída

# Parâmetros para beam search hierárquica
TOP_N = 10  # Número de categorias mais relevantes a serem retornadas
TOP_NV1 = 5  # Número de candidatos NV1 a manter
TOP_NV2 = 5   # Número de candidatos NV2 a manter por NV1
TOP_NV3 = 5   # Número de candidatos NV3 a manter por NV2

# Pesos para cada nível na pontuação final
WEIGHT_NV0 = 0.1
WEIGHT_NV1 = 0.2
WEIGHT_NV2 = 0.3
WEIGHT_NV3 = 0.5

# Caminhos para armazenamento de embeddings hierárquicos
EMBEDDINGS_DIR = CLASSY_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"
CAT_EMBED_NV4_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_NV4_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV3_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_NV3_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV2_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_NV2_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV1_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_NV1_{EMBEDDING_MODEL.replace('-', '_')}.pkl"

# Input embeddings
# Adicionar próximo às outras definições de diretório
INPUT_EMBEDDINGS_DIR = CLASSY_PATH + "INPUT_EMBEDDINGS\\"

# Verificar se o diretório existe e criar se necessário
if not os.path.exists(INPUT_EMBEDDINGS_DIR):
    os.makedirs(INPUT_EMBEDDINGS_DIR)

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

def normalize_code(code_value):
    """Converte qualquer valor para string, preservando zeros à esquerda."""
    if code_value is None:
        return ''
    return str(code_value)

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

def prepare_catalog_entries(cat_df):
    """Preparar entradas de catálogo unificado para embedding, separadas por níveis hierárquicos."""
    console.print("[bold magenta]Preparando textos de catálogo por níveis hierárquicos...[/bold magenta]")
    
    # Dicionários para armazenar textos e metadados por nível
    cat_texts_by_level = {
        'NV0': [],
        'NV1': [],
        'NV2': [],
        'NV3': [],
        'NV4': []  # nível completo/original
    }
    
    cat_meta_by_level = {
        'NV0': [],
        'NV1': [],
        'NV2': [],
        'NV3': [],
        'NV4': []
    }
    
    # Usando um único Progress para todo o catálogo
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("Processando catálogo unificado...", total=len(cat_df))
        
        # Processamento para NV0 (Material/Serviço) - adicionado antes dos outros processamentos
        processed_nv0 = set()
        # Adicionar explicitamente Material e Serviço
        cat_texts_by_level['NV0'].append(preprocess_text("MATERIAL"))
        cat_meta_by_level['NV0'].append({
            'CODNV0': 'M',
            'NOMNV0': 'MATERIAL'
        })
        
        cat_texts_by_level['NV0'].append(preprocess_text("SERVIÇO"))
        cat_meta_by_level['NV0'].append({
            'CODNV0': 'S',
            'NOMNV0': 'SERVIÇO'
        })


        # Processamento nível NV4 (completo/original)
        processed_codcats = set()  # Para evitar duplicatas
        for _, row in cat_df.iterrows():
            codcat = row.get('CODCAT', '')
            nomcat = row.get('NOMCAT', '')
            
            if codcat not in processed_codcats:
                processed_codcats.add(codcat)
                combined_text = preprocess_text(nomcat)  # Apenas texto, sem códigos
                cat_texts_by_level['NV4'].append(combined_text)
                cat_meta_by_level['NV4'].append({
                    'CODCAT': codcat,
                    'NOMCAT': nomcat,
                    'CODNV0': row.get('CODNV0', ''),
                    'CODNV1': row.get('CODNV1', ''),
                    'CODNV2': row.get('CODNV2', ''),
                    'CODNV3': row.get('CODNV3', ''),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', ''),
                    'NOMNV3': row.get('NOMNV3', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV4
        
        # Processamento nível NV3
        processed_nv3 = set()
        for _, row in cat_df.iterrows():
            codnv3_key = f"{row.get('CODNV0', '')}{row.get('CODNV1', '')}{row.get('CODNV2', '')}{row.get('CODNV3', '')}"
            
            if codnv3_key not in processed_nv3:
                processed_nv3.add(codnv3_key)
                # Texto concatenado até NV3
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}; {row.get('NOMNV2', '')}; {row.get('NOMNV3', '')}")
                cat_texts_by_level['NV3'].append(combined_text)
                cat_meta_by_level['NV3'].append({
                    'CODNV0': row.get('CODNV0', ''),
                    'CODNV1': row.get('CODNV1', ''),
                    'CODNV2': row.get('CODNV2', ''),
                    'CODNV3': row.get('CODNV3', ''),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', ''),
                    'NOMNV3': row.get('NOMNV3', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV3
        
        # Processamento nível NV2
        processed_nv2 = set()
        for _, row in cat_df.iterrows():
            codnv2_key = f"{row.get('CODNV0', '')}{row.get('CODNV1', '')}{row.get('CODNV2', '')}"
            
            if codnv2_key not in processed_nv2:
                processed_nv2.add(codnv2_key)
                # Texto concatenado até NV2
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}; {row.get('NOMNV2', '')}")
                cat_texts_by_level['NV2'].append(combined_text)
                cat_meta_by_level['NV2'].append({
                    'CODNV0': row.get('CODNV0', ''),
                    'CODNV1': row.get('CODNV1', ''),
                    'CODNV2': row.get('CODNV2', ''),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV2
        
        # Processamento nível NV1
        processed_nv1 = set()
        for _, row in cat_df.iterrows():
            codnv1_key = f"{row.get('CODNV0', '')}{row.get('CODNV1', '')}"
            
            if codnv1_key not in processed_nv1:
                processed_nv1.add(codnv1_key)
                # Texto concatenado até NV1
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}")
                cat_texts_by_level['NV1'].append(combined_text)
                cat_meta_by_level['NV1'].append({
                    'CODNV0': row.get('CODNV0', ''),
                    'CODNV1': row.get('CODNV1', ''),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV1
    
    # Reportar estatísticas
    for level, texts in cat_texts_by_level.items():
        console.print(f"[magenta]Nível {level}: {len(texts)} textos únicos preparados.[/magenta]")
    
    return cat_texts_by_level, cat_meta_by_level

def create_hierarchical_indices(cat_texts_by_level, model=EMBEDDING_MODEL):
    """Criar embeddings e índices FAISS para cada nível hierárquico."""
    console.print("[bold magenta]Criando embeddings e índices FAISS hierárquicos...[/bold magenta]")
    
    indices = {}
    embeddings_by_level = {}
    
    for level, texts in cat_texts_by_level.items():
        console.print(f"[cyan]Gerando embeddings para o nível {level}...[/cyan]")
        embeddings = get_embeddings(texts)
        embeddings_by_level[level] = embeddings
        
        level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
        save_embeddings(embeddings, level_embed_file)
        
        console.print(f"[cyan]Criando índice FAISS para o nível {level}...[/cyan]")
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        index = faiss.IndexFlatIP(embeddings_array.shape[1])
        
        faiss.normalize_L2(embeddings_array)
        
        index.add(embeddings_array)
        
        indices[level] = index
        
        level_index_file = EMBEDDINGS_DIR + f"FAISS_INDEX_{level}.index"
        try:
            faiss.write_index(index, level_index_file)
            console.print(f"[green]Índice FAISS {level} salvo em {level_index_file}[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar índice FAISS {level}: {str(e)}[/bold red]")
    
    return indices, embeddings_by_level

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

def get_embeddings(texts, model=EMBEDDING_MODEL, existing_progress=None):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI com progress bars por worker."""
    embeddings = []
    all_indices = list(range(0, len(texts), BATCH_SIZE))
    partitions = partition_list(all_indices, MAX_WORKERS)
    
    use_external_progress = existing_progress is not None
    progress = existing_progress if use_external_progress else Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    
    if not use_external_progress:
        progress.start()
        
    futures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        task_ids = []
        for worker_id, partition in enumerate(partitions, start=1):
            task_id = progress.add_task(f"Worker {worker_id} embeddings", total=len(partition))
            task_ids.append(task_id)
            futures.append(executor.submit(process_embedding_partition_shared, partition, texts, model, worker_id, progress, task_id))
        for future in futures:
            embeddings.extend(future.result())
    
    if not use_external_progress:
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
            
        item_norm = np.linalg.norm(item_embed)
        if item_norm == 0:
            norm_item_embed = item_embed
        else:
            norm_item_embed = item_embed / item_norm
            
        sims = np.dot(cat_embeds_matrix, norm_item_embed)
        
        top_indices = np.argsort(sims)[-TOP_N:][::-1]
        
        result = {}
        for i, cat_idx in enumerate(top_indices):
            codcat, nomcat = cat_meta[cat_idx]
            result[f"TOP_{i+1}"] = f"{codcat} - {nomcat}"
            result[f"SCORE_{i+1}"] = float(sims[cat_idx])
            
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
        
    return worker_results

def process_similarity_partition_faiss(args_sublist, faiss_index, cat_meta, worker_id, progress, task_id):
    worker_results = []
    embeddings = []
    indices = []
    
    for idx, item_embed in args_sublist:
        if item_embed is not None:
            embeddings.append(item_embed)
            indices.append(idx)
    
    if not embeddings:
        return [(idx, {}) for idx, _ in args_sublist]
    
    embeddings_array = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings_array)
    
    D, I = faiss_index.search(embeddings_array, TOP_N)
    
    for i, (distances, neighbors) in enumerate(zip(D, I)):
        idx = indices[i]
        result = {}
        
        pairs = []
        for j, (neighbor_idx, distance) in enumerate(zip(neighbors, distances)):
            codcat, nomcat = cat_meta[neighbor_idx]
            similarity = 1 - (distance ** 2) / 2
            pairs.append((similarity, codcat, nomcat))
        
        pairs.sort(reverse=True)
        
        for j, (similarity, codcat, nomcat) in enumerate(pairs):
            result[f"TOP_{j+1}"] = f"{codcat} - {nomcat}"
            result[f"SCORE_{j+1}"] = float(similarity)
        
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
    
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            
    return worker_results

def hierarchical_beam_search(item_embed, indices, cat_meta_by_level, 
                             beam_width_nv1=10, beam_width_nv2=5, beam_width_nv3=5,
                             weights=(0.2, 0.3, 0.5)):
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    D_nv1, I_nv1 = indices['NV1'].search(query_embed, beam_width_nv1)
    similarities_nv1 = 1 - (D_nv1[0] ** 2) / 2
    
    final_results = []
    
    for i, (nv1_idx, nv1_similarity) in enumerate(zip(I_nv1[0], similarities_nv1)):
        nv1_meta = cat_meta_by_level['NV1'][nv1_idx]
        nv1_code = str(nv1_meta.get('CODNV0', '')) + str(nv1_meta.get('CODNV1', ''))
        
        nv2_candidates = []
        for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
            if (nv2_meta.get('CODNV0', '') == nv1_meta.get('CODNV0', '') and 
                nv2_meta.get('CODNV1', '') == nv1_meta.get('CODNV1', '')):
                nv2_candidates.append(j)
        
        if not nv2_candidates:
            continue
            
        nv2_embeddings = np.array([cat_embeddings_by_level['NV2'][j] for j in nv2_candidates], dtype=np.float32)
        temp_index_nv2 = faiss.IndexFlatIP(nv2_embeddings.shape[1])
        faiss.normalize_L2(nv2_embeddings)
        temp_index_nv2.add(nv2_embeddings)
        
        D_nv2, I_nv2 = temp_index_nv2.search(query_embed, min(beam_width_nv2, len(nv2_candidates)))
        similarities_nv2 = 1 - (D_nv2[0] ** 2) / 2
        
        I_nv2_global = [nv2_candidates[idx] for idx in I_nv2[0]]
        
        for j, (nv2_local_idx, nv2_similarity) in enumerate(zip(I_nv2[0], similarities_nv2)):
            nv2_global_idx = nv2_candidates[nv2_local_idx]
            nv2_meta = cat_meta_by_level['NV2'][nv2_global_idx]
            nv2_code = str(nv2_meta.get('CODNV0', '')) + str(nv2_meta.get('CODNV1', '')) + str(nv2_meta.get('CODNV2', ''))
            
            nv3_candidates = []
            for k, nv3_meta in enumerate(cat_meta_by_level['NV3']):
                if (nv3_meta.get('CODNV0', '') == nv2_meta.get('CODNV0', '') and 
                    nv3_meta.get('CODNV1', '') == nv2_meta.get('CODNV1', '') and
                    nv3_meta.get('CODNV2', '') == nv2_meta.get('CODNV2', '')):
                    nv3_candidates.append(k)
            
            if not nv3_candidates:
                composite_score = weights[0] * nv1_similarity + weights[1] * nv2_similarity
                
                code = str(nv2_meta.get('CODNV0', '')) + str(nv2_meta.get('CODNV1', '')) + str(nv2_meta.get('CODNV2', ''))
                name = f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}"
                
                final_results.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV2',
                    'metadata': nv2_meta,
                    'level_scores': {
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity)
                    }
                })
                continue
                
            nv3_embeddings = np.array([cat_embeddings_by_level['NV3'][k] for k in nv3_candidates], dtype=np.float32)
            temp_index_nv3 = faiss.IndexFlatIP(nv3_embeddings.shape[1])
            faiss.normalize_L2(nv3_embeddings)
            temp_index_nv3.add(nv3_embeddings)
            
            D_nv3, I_nv3 = temp_index_nv3.search(query_embed, min(beam_width_nv3, len(nv3_candidates)))
            similarities_nv3 = 1 - (D_nv3[0] ** 2) / 2
            
            I_nv3_global = [nv3_candidates[idx] for idx in I_nv3[0]]
            
            for k, (nv3_local_idx, nv3_similarity) in enumerate(zip(I_nv3[0], similarities_nv3)):
                nv3_global_idx = nv3_candidates[nv3_local_idx]
                nv3_meta = cat_meta_by_level['NV3'][nv3_global_idx]
                
                composite_score = (weights[0] * nv1_similarity + 
                                  weights[1] * nv2_similarity + 
                                  weights[2] * nv3_similarity)
                
                code = (str(nv3_meta.get('CODNV0', '')) + 
                        str(nv3_meta.get('CODNV1', '')) + 
                        str(nv3_meta.get('CODNV2', '')) + 
                        str(nv3_meta.get('CODNV3', '')))
                name = (f"{nv3_meta.get('NOMNV0', '')}; {nv3_meta.get('NOMNV1', '')}; " +
                       f"{nv3_meta.get('NOMNV2', '')}; {nv3_meta.get('NOMNV3', '')}")
                
                final_results.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV3',
                    'metadata': nv3_meta,
                    'level_scores': {
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity),
                        'NV3': float(nv3_similarity)
                    }
                })
    
    final_results.sort(key=lambda x: x['score'], reverse=True)
    
    return final_results[:TOP_N]


def optimized_hierarchical_beam_search(item_embed, indices, cat_meta_by_level, cat_embeddings_by_level,
                           beam_width_nv1=10, beam_width_nv2=5, beam_width_nv3=5,
                           weights=(0.2, 0.3, 0.5)):
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    D_nv1, I_nv1 = indices['NV1'].search(query_embed, beam_width_nv1)
    similarities_nv1 = 1 - (D_nv1[0] ** 2) / 2
    
    candidates = []
    
    for nv1_idx, nv1_similarity in zip(I_nv1[0][:beam_width_nv1], similarities_nv1[:beam_width_nv1]):
        nv1_meta = cat_meta_by_level['NV1'][nv1_idx]
        nv1_code = str(nv1_meta.get('CODNV0', '')) + str(nv1_meta.get('CODNV1', ''))
        
        all_nv2_results = []
        for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
            if (nv2_meta.get('CODNV0', '') == nv1_meta.get('CODNV0', '') and 
                nv2_meta.get('CODNV1', '') == nv1_meta.get('CODNV1', '')):
                
                nv2_similarity = np.dot(cat_embeddings_by_level['NV2'][j], item_embed)
                
                all_nv2_results.append((j, nv2_similarity, nv2_meta))
        
        all_nv2_results.sort(key=lambda x: x[1], reverse=True)
        top_nv2_results = all_nv2_results[:beam_width_nv2]
        
        for nv2_idx, nv2_similarity, nv2_meta in top_nv2_results:
            nv2_code = str(nv2_meta.get('CODNV0', '')) + str(nv2_meta.get('CODNV1', '')) + str(nv2_meta.get('CODNV2', ''))
            
            all_nv3_results = []
            for k, nv3_meta in enumerate(cat_meta_by_level['NV3']):
                if (nv3_meta.get('CODNV0', '') == nv2_meta.get('CODNV0', '') and 
                    nv3_meta.get('CODNV1', '') == nv2_meta.get('CODNV1', '') and
                    nv3_meta.get('CODNV2', '') == nv2_meta.get('CODNV2', '')):
                    
                    nv3_similarity = np.dot(cat_embeddings_by_level['NV3'][k], item_embed)
                    
                    composite_score = (weights[0] * nv1_similarity + 
                                      weights[1] * nv2_similarity + 
                                      weights[2] * nv3_similarity)
                    
                    code = (str(nv3_meta.get('CODNV0', '')) + 
                           str(nv3_meta.get('CODNV1', '')) + 
                           str(nv3_meta.get('CODNV2', '')) + 
                           str(nv3_meta.get('CODNV3', '')))
                    
                    name = (f"{nv3_meta.get('NOMNV0', '')}; {nv3_meta.get('NOMNV1', '')}; " +
                           f"{nv3_meta.get('NOMNV2', '')}; {nv3_meta.get('NOMNV3', '')}")
                    
                    all_nv3_results.append({
                        'code': code,
                        'name': name,
                        'score': float(composite_score),
                        'level': 'NV3',
                        'level_scores': {
                            'NV1': float(nv1_similarity),
                            'NV2': float(nv2_similarity),
                            'NV3': float(nv3_similarity)
                        }
                    })
            
            if not all_nv3_results:
                composite_score = weights[0] * nv1_similarity + weights[1] * nv2_similarity
                
                code = str(nv2_meta.get('CODNV0', '')) + str(nv2_meta.get('CODNV1', '')) + str(nv2_meta.get('CODNV2', ''))
                name = f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}"
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV2',
                    'level_scores': {
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity)
                    }
                })
            else:
                all_nv3_results.sort(key=lambda x: x['score'], reverse=True)
                candidates.extend(all_nv3_results[:beam_width_nv3])
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:TOP_N]

def process_similarity_partition_beam_search(args_sublist, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps, worker_id, progress, task_id):
    worker_results = []
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            continue
        
        results = fast_hierarchical_beam_search(
            item_embed, indices, cat_meta_by_level, cat_embeddings_by_level,
            hierarchical_maps
        )
        
        formatted_result = {}
        for i, result in enumerate(results):
            formatted_result[f"TOP_{i+1}"] = f"{result['code']} - {result['name']}"
            formatted_result[f"SCORE_{i+1}"] = result['score']
            
        if results:
            
            level_scores = results[0]['level_scores']
            for level, score in level_scores.items():
                formatted_result[f"SCORE_{level}"] = score
            
            if OUTPUT_DEBUG and 'score_calculation' in results[0]:
                formatted_result["SCORE_CALCULATION"] = results[0]['score_calculation']
                
            if OUTPUT_DEBUG and 'debug_info' in results[0]:
                debug = results[0]['debug_info']
                
                for i, nv1_info in enumerate(debug['nv1_results'][:TOP_NV1]):
                    formatted_result[f"TOP_NV1_{i+1}"] = f"{nv1_info['code']} - {nv1_info['name']}"
                    formatted_result[f"SCORE_NV1_{i+1}"] = nv1_info['similarity']
                
                for i, nv2_info in enumerate(debug['nv2_results'][:TOP_NV2]):
                    formatted_result[f"TOP_NV2_{i+1}"] = f"{nv2_info['code']} - {nv2_info['name']}"
                    formatted_result[f"SCORE_NV2_{i+1}"] = nv2_info['similarity']
                
                for i, nv3_info in enumerate(debug['nv3_results'][:TOP_NV3]):
                    formatted_result[f"TOP_NV3_{i+1}"] = f"{nv3_info['code']} - {nv3_info['name']}"
                    formatted_result[f"SCORE_NV3_{i+1}"] = nv3_info['similarity']
                
                # Adicionar TOP_NV0 e SCORE_NV0
                for i, nv0_info in enumerate(debug['nv0_results']):
                    formatted_result[f"TOP_NV0_{i+1}"] = f"{nv0_info['code']} - {nv0_info['name']}"
                    formatted_result[f"SCORE_NV0_{i+1}"] = nv0_info['similarity']
            
        worker_results.append((idx, formatted_result))
        progress.update(task_id, advance=1)
        
    return worker_results

def classify_items_beam_search(df_items, indices, cat_meta_by_level, cat_embeddings_by_level, embedding_function):
    """Versão modificada da função classify_items que usa beam search hierárquica."""
    result_df = df_items.copy()
    
    # Pré-calcular relações hierárquicas
    hierarchical_maps = precompute_hierarchical_relationships(cat_meta_by_level)
    
    # Adicionar colunas básicas para resultados
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    
    # Em modo debug, adicionar colunas extras
    if OUTPUT_DEBUG:
        result_df["SCORE_CALCULATION"] = ""
        
        # Adicionar colunas para NV0 (apenas 2 - Material e Serviço)
        for i in range(1, 3):  # Sempre serão apenas 2 opções: M e S
            result_df[f"TOP_NV0_{i}"] = ""
            result_df[f"SCORE_NV0_{i}"] = 0.0
            
        # Resto do código para outros níveis...
        for i in range(1, TOP_NV1 + 1):  # Modificado para usar TOP_NV1
            result_df[f"TOP_NV1_{i}"] = ""
            result_df[f"SCORE_NV1_{i}"] = 0.0
        
        for i in range(1, TOP_NV2 + 1):  # Modificado para usar TOP_NV2 
            result_df[f"TOP_NV2_{i}"] = ""
            result_df[f"SCORE_NV2_{i}"] = 0.0
            
        for i in range(1, TOP_NV3 + 1):  # Modificado para usar TOP_NV3
            result_df[f"TOP_NV3_{i}"] = ""
            result_df[f"SCORE_NV3_{i}"] = 0.0

    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    
    with progress:
        embed_task = progress.add_task("[cyan]Gerando embeddings...", total=1)
        item_embeds = embedding_function(item_texts, existing_progress=progress)
        progress.update(embed_task, completed=1)
        
        args_list = [(idx, item_embed) for idx, item_embed in enumerate(item_embeds)]
        partitions = partition_list(args_list, MAX_WORKERS)
        similarity_results = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for worker_id, part in enumerate(partitions, start=1):
                task_id = progress.add_task(f"Worker {worker_id} similaridade hierárquica otimizada", total=len(part))
                futures.append(executor.submit(
                    process_similarity_partition_beam_search, 
                    part, 
                    indices,
                    cat_meta_by_level,
                    cat_embeddings_by_level,
                    hierarchical_maps,  # Novo parâmetro: mapas hierárquicos pré-calculados
                    worker_id, 
                    progress, 
                    task_id
                ))
            for future in futures:
                similarity_results.extend(future.result())
    
    for idx, similarity_data in similarity_results:
        for key, value in similarity_data.items():
            result_df.at[idx, key] = value

    if "id" in result_df.columns and "id_pncp" not in result_df.columns:
        result_df = result_df.rename(columns={"id": "id_pncp"})
    
    desired_columns = ['id_pncp', 'objetoCompra']
    
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"TOP_{i}")
    
    desired_columns.extend(['SCORE_NV1', 'SCORE_NV2', 'SCORE_NV3'])
    
    if OUTPUT_DEBUG:
        desired_columns.append("SCORE_CALCULATION")
        for i in range(1, 6):
            desired_columns.extend([f"TOP_NV1_{i}", f"SCORE_NV1_{i}"])
            desired_columns.extend([f"TOP_NV2_{i}", f"SCORE_NV2_{i}"])
            desired_columns.extend([f"TOP_NV3_{i}", f"SCORE_NV3_{i}"])
    
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"SCORE_{i}")
    
    final_columns = [col for col in desired_columns if col in result_df.columns]
    
    # Em modo debug, ajustar a ordem das colunas conforme especificado
    if OUTPUT_DEBUG:
        # Definir ordem exata das colunas conforme solicitado
        ordered_columns = [
            'id_pncp', 'objetoCompra',
            # TOP_1 a TOP_10
            *[f"TOP_{i}" for i in range(1, TOP_N + 1)],
            # SCORE_1 a SCORE_10
            *[f"SCORE_{i}" for i in range(1, TOP_N + 1)],
            # Scores por nível
            'SCORE_NV0', 'SCORE_NV1', 'SCORE_NV2', 'SCORE_NV3', 
            'SCORE_CALCULATION',
            # TOP_NV0_1 e TOP_NV0_2
            *[f"TOP_NV0_{i}" for i in range(1, 3)],
            # SCORE_NV0_1 e SCORE_NV0_2
            *[f"SCORE_NV0_{i}" for i in range(1, 3)],
            # TOP_NV1_1 a TOP_NV1_n
            *[f"TOP_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            # SCORE_NV1_1 a SCORE_NV1_n
            *[f"SCORE_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            # TOP_NV2_1 a TOP_NV2_n
            *[f"TOP_NV2_{i}" for i in range(1, TOP_NV2 + 1)],
            # SCORE_NV2_1 a SCORE_NV2_n
            *[f"SCORE_NV2_{i}" for i in range(1, TOP_NV2 + 1)],
            # TOP_NV3_1 a TOP_NV3_n
            *[f"TOP_NV3_{i}" for i in range(1, TOP_NV3 + 1)],
            # SCORE_NV3_1 a SCORE_NV3_n
            *[f"SCORE_NV3_{i}" for i in range(1, TOP_NV3 + 1)]
        ]
        
        # Filtrar apenas colunas que existem no DataFrame
        final_columns = [col for col in ordered_columns if col in result_df.columns]
        return result_df[final_columns]
    
    return result_df[final_columns]

def process_input_file(input_number):
    global CHECKPOINT_FILE, INPUT_FILE, OUTPUT_FILE
    
    input_num_str = f"{input_number:03d}"
    INPUT_FILE = INPUT_PATH + f"\\INPUT_{input_num_str}.xlsx"
    OUTPUT_FILE = OUTPUT_PATH + f"OUTPUT_{input_num_str}.xlsx"
    CHECKPOINT_FILE = CHECKPOINT_PATH + f"CHECKPOINT_{input_num_str}_{TIMESTAMP}.pkl"
    
    input_embed_file = INPUT_EMBEDDINGS_DIR + f"INPUT_EMBED_{input_num_str}.pkl"
    
    console.print(f"\n[bold green]{'='*80}[/bold green]")
    console.print(f"[bold green]PROCESSANDO ARQUIVO: {os.path.basename(INPUT_FILE)}[/bold green]")
    console.print(f"[bold green]{'='*80}[/bold green]\n")
    
    start_time = time.time()
    
    try:
        df_items, _, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        def get_or_load_embeddings(texts, existing_progress=None):
            if os.path.exists(input_embed_file):
                console.print("[cyan]Embeddings existentes encontrados. Carregando...[/cyan]")
                try:
                    saved_embeddings = load_embeddings(input_embed_file)
                    if saved_embeddings and len(saved_embeddings) == len(texts):
                        console.print(f"[green]Embeddings carregados com sucesso para {len(saved_embeddings)} itens.[/green]")
                        return saved_embeddings
                    else:
                        console.print("[yellow]Embeddings existentes incompatíveis. Gerando novos...[/yellow]")
                except Exception as e:
                    console.print(f"[red]Erro ao carregar embeddings: {str(e)}. Gerando novos...[/red]")
            
            new_embeddings = get_embeddings(texts, existing_progress=existing_progress)
            
            console.print("[cyan]Salvando embeddings para uso futuro...[/cyan]")
            save_embeddings(new_embeddings, input_embed_file)
            
            return new_embeddings
        
        console.print("[bold magenta]Iniciando classificação hierárquica com processamento paralelo...[/bold magenta]")
        
        results = classify_items_beam_search(df_items, indices, cat_meta_by_level, cat_embeddings_by_level, get_or_load_embeddings)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação hierárquica de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        
        console.print(f"[bold magenta]Salvando resultados em {OUTPUT_FILE}...[/bold magenta]")
        results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[green]Resultados salvos com sucesso![/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Falha no processamento do arquivo {INPUT_FILE}: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return False
    

def fast_hierarchical_beam_search(item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps):
    """Versão ultra-otimizada da busca hierárquica que inclui NV0 (Material/Serviço)"""
    
    # Extrair mapeamentos pré-calculados
    nv1_to_nv2 = hierarchical_maps['nv1_to_nv2']
    nv2_to_nv3 = hierarchical_maps['nv2_to_nv3']
    
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # 1. Calcular similaridade para Material vs Serviço (NV0)
    material_embed = cat_embeddings_by_level['NV0'][0]  # M
    servico_embed = cat_embeddings_by_level['NV0'][1]   # S
    
    nv0_similarity_M = float(np.dot(material_embed, item_embed))
    nv0_similarity_S = float(np.dot(servico_embed, item_embed))
    
    # Determinar qual tem maior score
    if nv0_similarity_M > nv0_similarity_S:
        nv0_code = "M"
        nv0_similarity = nv0_similarity_M
    else:
        nv0_code = "S"
        nv0_similarity = nv0_similarity_S
    
    # Informações de debug para NV0
    debug_info = {
        'nv0_results': [
            {'code': 'M', 'name': 'MATERIAL', 'similarity': float(nv0_similarity_M), 'rank': 1 if nv0_code == 'M' else 2},
            {'code': 'S', 'name': 'SERVIÇO', 'similarity': float(nv0_similarity_S), 'rank': 1 if nv0_code == 'S' else 2}
        ],
        'nv1_results': [],
        'nv2_results': [],
        'nv3_results': []
    }
    
    # 2. Buscar candidatos NV1
    D_nv1, I_nv1 = indices['NV1'].search(query_embed, TOP_NV1)
    similarities_nv1 = 1 - (D_nv1[0] ** 2) / 2
    
    candidates = []
    
    # 3. Para cada NV1, buscar seus descendentes
    for idx, (nv1_idx, nv1_similarity) in enumerate(zip(I_nv1[0], similarities_nv1)):
        nv1_meta = cat_meta_by_level['NV1'][nv1_idx]
        nv1_meta_codnv0 = str(nv1_meta.get('CODNV0', ''))
        nv1_meta_codnv1 = str(nv1_meta.get('CODNV1', ''))
        nv1_code = f"{nv1_meta_codnv0}{nv1_meta_codnv1}"
        
        # Informações de debug para NV1
        if OUTPUT_DEBUG:
            nv1_info = {
                'code': nv1_code,
                'name': f"{nv1_meta.get('NOMNV0', '')}; {nv1_meta.get('NOMNV1', '')}",
                'similarity': float(nv1_similarity),
                'rank': idx + 1,
                'nv0': nv1_meta_codnv0
            }
            debug_info['nv1_results'].append(nv1_info)
        
        # Obter índices de NV2 que pertencem a este NV1
        nv2_indices = nv1_to_nv2.get(nv1_code, [])
        if not nv2_indices:
            continue
        
        # Calcular similaridades de todos os NV2 filhos
        nv2_embeddings = np.array([cat_embeddings_by_level['NV2'][j] for j in nv2_indices])
        nv2_similarities = np.dot(nv2_embeddings, item_embed)
        
        # Ordenar e selecionar os top NV2
        nv2_with_scores = [(nv2_indices[j], sim, j) for j, sim in enumerate(nv2_similarities)]
        nv2_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_nv2 = nv2_with_scores[:TOP_NV2]
        
        # 4. Para cada NV2 selecionado, buscar NV3
        for rank_nv2, (nv2_idx, nv2_similarity, local_idx) in enumerate(top_nv2):
            nv2_meta = cat_meta_by_level['NV2'][nv2_idx]
            nv2_meta_codnv0 = str(nv2_meta.get('CODNV0', ''))
            nv2_meta_codnv1 = str(nv2_meta.get('CODNV1', ''))
            nv2_meta_codnv2 = str(nv2_meta.get('CODNV2', ''))
            nv2_code = f"{nv2_meta_codnv0}{nv2_meta_codnv1}{nv2_meta_codnv2}"
            
            # Informações de debug para NV2
            if OUTPUT_DEBUG:
                nv2_info = {
                    'code': nv2_code,
                    'name': f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}",
                    'similarity': float(nv2_similarity),
                    'rank': rank_nv2 + 1,
                    'parent': nv1_code
                }
                debug_info['nv2_results'].append(nv2_info)
            
            # Obter índices de NV3 que pertencem a este NV2
            nv3_indices = nv2_to_nv3.get(nv2_code, [])
            
            # Se não há NV3, adicionar o NV2 como resultado
            if not nv3_indices:
                composite_score = (WEIGHT_NV0 * nv0_similarity + 
                                   WEIGHT_NV1 * nv1_similarity + 
                                   WEIGHT_NV2 * nv2_similarity)
                
                code = f"{nv2_meta_codnv0}{nv2_meta_codnv1}{nv2_meta_codnv2}"
                name = f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}"
                
                score_calc = (f"{WEIGHT_NV0} * {nv0_similarity:.4f} + "
                             f"{WEIGHT_NV1} * {nv1_similarity:.4f} + "
                             f"{WEIGHT_NV2} * {nv2_similarity:.4f} = {composite_score:.4f}")
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV2',
                    'level_scores': {
                        'NV0': float(nv0_similarity),
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity)
                    },
                    'score_calculation': score_calc if OUTPUT_DEBUG else ""
                })
                continue
            
            # 5. Calcular similaridades de NV3
            nv3_embeddings = np.array([cat_embeddings_by_level['NV3'][k] for k in nv3_indices])
            nv3_similarities = np.dot(nv3_embeddings, item_embed)
            
            # Ordenar e selecionar os top NV3
            nv3_with_scores = [(nv3_indices[k], sim, k) for k, sim in enumerate(nv3_similarities)]
            nv3_with_scores.sort(key=lambda x: x[1], reverse=True)
            top_nv3 = nv3_with_scores[:TOP_NV3]
            
            # 6. Adicionar candidatos NV3
            for rank_nv3, (nv3_idx, nv3_similarity, local_idx) in enumerate(top_nv3):
                nv3_meta = cat_meta_by_level['NV3'][nv3_idx]
                nv3_meta_codnv0 = str(nv3_meta.get('CODNV0', ''))
                nv3_meta_codnv1 = str(nv3_meta.get('CODNV1', ''))
                nv3_meta_codnv2 = str(nv3_meta.get('CODNV2', ''))
                nv3_meta_codnv3 = str(nv3_meta.get('CODNV3', ''))
                
                # Calcular score composto ponderado incluindo NV0
                composite_score = (WEIGHT_NV0 * nv0_similarity + 
                                   WEIGHT_NV1 * nv1_similarity + 
                                   WEIGHT_NV2 * nv2_similarity + 
                                   WEIGHT_NV3 * nv3_similarity)
                
                code = f"{nv3_meta_codnv0}{nv3_meta_codnv1}{nv3_meta_codnv2}{nv3_meta_codnv3}"
                name = (f"{nv3_meta.get('NOMNV0', '')}; {nv3_meta.get('NOMNV1', '')}; "
                       f"{nv3_meta.get('NOMNV2', '')}; {nv3_meta.get('NOMNV3', '')}")
                
                score_calc = (f"{WEIGHT_NV0} * {nv0_similarity:.4f} + "
                             f"{WEIGHT_NV1} * {nv1_similarity:.4f} + "
                             f"{WEIGHT_NV2} * {nv2_similarity:.4f} + "
                             f"{WEIGHT_NV3} * {nv3_similarity:.4f} = {composite_score:.4f}")
                
                # Informações de debug para NV3
                if OUTPUT_DEBUG:
                    nv3_info = {
                        'code': code,
                        'name': name,
                        'similarity': float(nv3_similarity),
                        'rank': rank_nv3 + 1,
                        'parent': nv2_code,
                        'composite_score': composite_score,
                        'score_calculation': score_calc
                    }
                    debug_info['nv3_results'].append(nv3_info)
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV3',
                    'level_scores': {
                        'NV0': float(nv0_similarity),
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity),
                        'NV3': float(nv3_similarity)
                    },
                    'score_calculation': score_calc if OUTPUT_DEBUG else ""
                })
    
    # Ordenar e selecionar os candidatos finais
    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = candidates[:TOP_N]
    
    # Adicionar informações de debug ao primeiro candidato
    if OUTPUT_DEBUG and top_candidates:
        top_candidates[0]['debug_info'] = debug_info
    
    return top_candidates

def precompute_hierarchical_relationships(cat_meta_by_level):
    console.print("[cyan]Pré-calculando relações hierárquicas para busca acelerada...[/cyan]")
    
    nv1_to_nv2 = {}
    nv2_to_nv3 = {}
    
    for i, nv1_meta in enumerate(cat_meta_by_level['NV1']):
        nv1_code = f"{nv1_meta.get('CODNV0', '')}{nv1_meta.get('CODNV1', '')}"
        nv1_to_nv2[nv1_code] = []
    
    for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
        nv1_code = f"{nv2_meta.get('CODNV0', '')}{nv2_meta.get('CODNV1', '')}"
        if nv1_code in nv1_to_nv2:
            nv1_to_nv2[nv1_code].append(j)
    
    for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
        nv2_code = f"{nv2_meta.get('CODNV0', '')}{nv2_meta.get('CODNV1', '')}{nv2_meta.get('CODNV2', '')}"
        nv2_to_nv3[nv2_code] = []
    
    for k, nv3_meta in enumerate(cat_meta_by_level['NV3']):
        nv2_code = f"{nv3_meta.get('CODNV0', '')}{nv3_meta.get('CODNV1', '')}{nv3_meta.get('CODNV2', '')}"
        if nv2_code in nv2_to_nv3:
            nv2_to_nv3[nv2_code].append(k)
    
    console.print(f"[green]Relações hierárquicas pré-calculadas: {len(nv1_to_nv2)} NV1 e {len(nv2_to_nv3)} NV2[/green]")
    
    return {
        'nv1_to_nv2': nv1_to_nv2,
        'nv2_to_nv3': nv2_to_nv3
    }



def main():
    global cat_embeddings_by_level, cat_meta_by_level, indices
    global PAGE_BEGIN, PAGE_END
    
    start_total = time.time()
    
    try:
        indices = {}
        cat_embeddings_by_level = {}
        all_files_exist = True
        
        console.print("[bold magenta]Verificando embeddings e índices hierárquicos existentes...[/bold magenta]")
        
        # Modificar esta linha para incluir 'NV0'
        for level in ['NV0', 'NV1', 'NV2', 'NV3', 'NV4']:  # Adicionado 'NV0'
            level_index_file = EMBEDDINGS_DIR + f"FAISS_INDEX_{level}.index"
            level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
            
            if not os.path.exists(level_index_file) or not os.path.exists(level_embed_file):
                all_files_exist = False
                console.print(f"[yellow]Arquivos para nível {level} não encontrados.[/yellow]")
                break
        
        if all_files_exist:
            console.print("[cyan]Todos os arquivos de embedding e índices encontrados. Tentando carregar...[/cyan]")
            
            loading_success = True
            # Modificar esta linha também para incluir 'NV0'
            for level in ['NV0', 'NV1', 'NV2', 'NV3', 'NV4']:  # Adicionado 'NV0'
                level_index_file = EMBEDDINGS_DIR + f"FAISS_INDEX_{level}.index"
                level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
                
                try:
                    embeddings = load_embeddings(level_embed_file)
                    if embeddings is None:
                        loading_success = False
                        console.print(f"[yellow]Falha ao carregar embeddings {level}.[/yellow]")
                        break
                    
                    try:
                        indices[level] = faiss.read_index(level_index_file)
                        cat_embeddings_by_level[level] = embeddings
                        console.print(f"[green]Índice FAISS e embeddings {level} carregados com sucesso.[/green]")
                    except Exception as e:
                        loading_success = False
                        console.print(f"[bold red]Erro ao carregar índice FAISS {level}: {str(e)}[/bold red]")
                        break
                except Exception as e:
                    loading_success = False
                    console.print(f"[bold red]Erro ao carregar embeddings {level}: {str(e)}[/bold red]")
                    break
            
            if loading_success:
                try:
                    metadata_file = EMBEDDINGS_DIR + "CAT_META_BY_LEVEL.pkl"
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'rb') as f:
                            cat_meta_by_level = pickle.load(f)
                        console.print("[green]Metadados do catálogo carregados com sucesso.[/green]")
                    else:
                        loading_success = False
                        console.print("[yellow]Arquivo de metadados não encontrado.[/yellow]")
                except Exception as e:
                    loading_success = False
                    console.print(f"[bold red]Erro ao carregar metadados: {str(e)}[/bold red]")
            
            if loading_success:
                console.print("[bold green]Todos os embeddings, índices e metadados carregados com sucesso![/bold green]")
            else:
                console.print("[yellow]Falha ao carregar arquivos existentes. Gerando novos...[/yellow]")
                catalog_file = NOVA_CAT_FILE
                cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
                console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
                
                cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
                
                with open(EMBEDDINGS_DIR + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                    pickle.dump(cat_meta_by_level, f)
                console.print("[green]Metadados do catálogo salvos.[/green]")
                
                indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        else:
            console.print("[yellow]Arquivos de embedding ou índices não encontrados. Gerando novos...[/yellow]")
            
            catalog_file = NOVA_CAT_FILE
            cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
            console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
            
            cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
            
            with open(EMBEDDINGS_DIR + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                pickle.dump(cat_meta_by_level, f)
            console.print("[green]Metadados do catálogo salvos.[/green]")
            
            indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        
        if PAGE_BEGIN < 1:
            console.print("[bold yellow]AVISO: PAGE_BEGIN menor que 1, ajustando para 1.[/bold yellow]")
            PAGE_BEGIN = 1
            
        if PAGE_END > 51:
            console.print("[bold yellow]AVISO: PAGE_END maior que 51, ajustando para 51.[/bold yellow]")
            PAGE_END = 51
            
        if PAGE_END < PAGE_BEGIN:
            console.print("[bold red]ERRO: PAGE_END não pode ser menor que PAGE_BEGIN. Ajustando para PAGE_BEGIN.[/bold red]")
            PAGE_END = PAGE_BEGIN
        
        console.print(f"[bold blue]Buscando arquivos para processamento no intervalo: {PAGE_BEGIN} a {PAGE_END}[/bold blue]")
        
        input_files = []
        for i in range(PAGE_BEGIN, PAGE_END + 1):
            input_num_str = f"{i:03d}"
            input_file = INPUT_PATH + f"\\INPUT_{input_num_str}.xlsx"
            if os.path.exists(input_file):
                input_files.append(i)
            else:
                console.print(f"[yellow]Arquivo INPUT_{input_num_str}.xlsx não encontrado e será ignorado.[/yellow]")
        
        if not input_files:
            console.print(f"[bold red]Nenhum arquivo encontrado no intervalo de {PAGE_BEGIN} a {PAGE_END}.[/bold red]")
            return
            
        console.print(f"[bold blue]Encontrados {len(input_files)} arquivos para processamento no intervalo.[/bold blue]")
        
        success_count = 0
        failure_count = 0
        
        for i, input_number in enumerate(input_files):
            console.print(f"[bold cyan]Processando arquivo {i+1}/{len(input_files)}: INPUT_{input_number:03d}.xlsx[/bold cyan]")
            result = process_input_file(input_number)
            if result:
                success_count += 1
                console.print(f"[green]✓ Arquivo {i+1}/{len(input_files)} processado com sucesso[/green]")
            else:
                failure_count += 1
                console.print(f"[red]✗ Falha no processamento do arquivo {i+1}/{len(input_files)}[/red]")
        
        end_total = time.time()
        total_time = end_total - start_total
        console.print(f"[bold green]{'='*80}[/bold green]")
        console.print(f"[bold green]PROCESSAMENTO COMPLETO![/bold green]")
        console.print(f"[bold green]Arquivos processados com sucesso: {success_count}[/bold green]")
        console.print(f"[bold red]Arquivos com falha: {failure_count}[/bold red]")
        console.print(f"[bold green]Tempo total: {total_time/60:.2f} minutos[/bold green]")
        console.print(f"[bold green]{'='*80}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline principal falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
