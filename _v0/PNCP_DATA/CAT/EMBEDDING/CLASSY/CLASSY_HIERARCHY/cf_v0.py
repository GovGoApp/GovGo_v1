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
OUTPUT_PATH = CLASSY_PATH + "OUTPUT_CF\\"
CHECKPOINT_PATH = CLASSY_PATH + "CHECKPOINTS_CF\\"

SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

# Constantes para controle de execução
MAX_WORKERS = 8  # Número de threads para processamento paralelo
console.print("WORKERS = " + str(MAX_WORKERS))

TOP_N = 10  # Número de categorias mais relevantes a serem retornadas
BATCH_SIZE = 100  # Tamanho do lote para processamento de embeddings
INPUT_INITIAL_NUMBER = 1

PAGE_BEGIN = 1  # Página inicial para leitura do Excel
PAGE_END = 1 # Página final para leitura do Excel 
# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"


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
        'NV1': [],
        'NV2': [],
        'NV3': [],
        'NV4': []  # nível completo/original
    }
    
    cat_meta_by_level = {
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
        # Gerar embeddings para este nível
        console.print(f"[cyan]Gerando embeddings para o nível {level}...[/cyan]")
        embeddings = get_embeddings(texts)
        embeddings_by_level[level] = embeddings
        
        # Salvar embeddings para uso futuro
        level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
        save_embeddings(embeddings, level_embed_file)
        
        # Criar índice FAISS para este nível
        console.print(f"[cyan]Criando índice FAISS para o nível {level}...[/cyan]")
        
        # Converter para array numpy e normalizar
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Criar índice de produto interno (similaridade de cosseno)
        index = faiss.IndexFlatIP(embeddings_array.shape[1])
        
        # Normalizar vetores
        faiss.normalize_L2(embeddings_array)
        
        # Adicionar ao índice
        index.add(embeddings_array)
        
        # Armazenar índice
        indices[level] = index
        
        # Salvar índice em arquivo
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
    
    # Usar uma progress bar existente ou criar uma nova
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
    
    # Só parar a progress se nós a criamos
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
            codcat, nomcat = cat_meta[cat_idx]
            result[f"TOP_{i+1}"] = f"{codcat} - {nomcat}"
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
        
        # Converter distâncias para similaridades e criar pares ordenados
        pairs = []
        for j, (neighbor_idx, distance) in enumerate(zip(neighbors, distances)):
            codcat, nomcat = cat_meta[neighbor_idx]  # Corrigir para nomcat (antes estava nom)
            similarity = 1 - (distance ** 2) / 2
            pairs.append((similarity, codcat, nomcat))
        
        # Reordenar explicitamente por similaridade decrescente
        pairs.sort(reverse=True)
        
        # Agora popule o resultado com valores ordenados
        for j, (similarity, codcat, nomcat) in enumerate(pairs):
            result[f"TOP_{j+1}"] = f"{codcat} - {nomcat}"
            result[f"SCORE_{j+1}"] = float(similarity)
        
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
    
    # Adicionar resultados vazios para embeddings nulos
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            
    return worker_results

def hierarchical_search_with_fallback(item_embed, indices, cat_meta_by_level, z_gap_threshold=1.5):
    """
    Realiza busca hierárquica com fallback nos índices FAISS.
    
    Começa pelo nível mais específico (NV4) e vai descendo para níveis mais genéricos
    até encontrar uma correspondência confiável.
    
    Args:
        item_embed: Embedding do item a ser classificado
        indices: Dicionário de índices FAISS por nível
        cat_meta_by_level: Metadados do catálogo por nível
        z_gap_threshold: Valor inicial do threshold de z_gap (ajustado dinamicamente)
    
    Returns:
        tuple: (nível usado, metadados do match, scores, resultado formatado)
    """
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Níveis em ordem de especificidade (do mais específico para o mais genérico)
    levels = ['NV4', 'NV3', 'NV2', 'NV1']
    
    for level in levels:
        # Buscar 2 vizinhos mais próximos para calcular z-gap
        k = 10  # Buscar mais vizinhos para calcular estatísticas
        D, I = indices[level].search(query_embed, k)
        
        # Extrair distâncias/scores
        distances = D[0]
        
        # Converter distâncias para similaridades (1 - (d²/2))
        similarities = 1 - (distances ** 2) / 2
        
        # Calcular z-gap adaptativo
        if len(similarities) >= 2:
            # Calcular estatísticas
            score1 = similarities[0]
            score2 = similarities[1]
            mean_score = np.mean(similarities)
            std_score = np.std(similarities)
            
            # Evitar divisão por zero
            if std_score < 0.001:
                std_score = 0.001
                
            # Calcular z-gap normalizado
            z_gap = (score1 - score2) / std_score
            
            # Threshold adaptativo (mais rigoroso em níveis específicos)
            adjusted_threshold = z_gap_threshold
            if level == 'NV4':
                adjusted_threshold *= 1.2  # 20% mais rigoroso para NV4
            elif level == 'NV1':
                adjusted_threshold *= 0.8  # 20% menos rigoroso para NV1
            
            # Verificar se o match é confiável
            if z_gap >= adjusted_threshold:
                # Match confiável encontrado
                idx = I[0][0]  # Índice do melhor match
                metadata = cat_meta_by_level[level][idx]
                
                # Formatar resultado para retorno
                result = {}
                for i in range(min(TOP_N, len(similarities))):
                    idx_i = I[0][i]
                    meta_i = cat_meta_by_level[level][idx_i]
                    
                    # Determinar o código e nome a serem exibidos baseado no nível
                    if level == 'NV4':
                        code = meta_i.get('CODCAT', '')
                        name = meta_i.get('NOMCAT', '')
                    else:
                        # Construir código composto para níveis inferiores
                        nv_parts = [str(meta_i.get('CODNV0', ''))]
                        nom_parts = [meta_i.get('NOMNV0', '')]
                        
                        if level in ['NV1', 'NV2', 'NV3']:
                            nv_parts.append(meta_i.get('CODNV1', ''))
                            nom_parts.append(meta_i.get('NOMNV1', ''))
                        
                        if level in ['NV2', 'NV3']:
                            nv_parts.append(meta_i.get('CODNV2', ''))
                            nom_parts.append(meta_i.get('NOMNV2', ''))
                        
                        if level == 'NV3':
                            nv_parts.append(meta_i.get('CODNV3', ''))
                            nom_parts.append(meta_i.get('NOMNV3', ''))
                        
                        code = "".join(nv_parts)
                        name = "; ".join(nom_parts)
                    
                    result[f"TOP_{i+1}"] = f"{code} - {name}"
                    result[f"SCORE_{i+1}"] = float(similarities[i])
                
                # Adicionar informações sobre o nível de classificação
                result["NIVEL_CLASSIFICACAO"] = level
                result["Z_GAP"] = float(z_gap)
                
                return level, metadata, similarities, result
    
    # Se chegamos aqui, nenhum nível teve match confiável
    # Usamos o nível NV1 (mais genérico) como fallback final
    level = 'NV1'
    D, I = indices[level].search(query_embed, TOP_N)
    distances = D[0]
    similarities = 1 - (distances ** 2) / 2
    idx = I[0][0]
    metadata = cat_meta_by_level[level][idx]
    
    # Formatar resultado para retorno forçado no nível NV1
    result = {}
    for i in range(min(TOP_N, len(similarities))):
        idx_i = I[0][i]
        meta_i = cat_meta_by_level[level][idx_i]
        code = str(meta_i.get('CODNV0', '')) + str(meta_i.get('CODNV1', ''))
        name = f"{meta_i.get('NOMNV0', '')}; {meta_i.get('NOMNV1', '')}"
        result[f"TOP_{i+1}"] = f"{code} - {name}"
        result[f"SCORE_{i+1}"] = float(similarities[i])
    
    # Indicar que foi um fallback forçado
    result["NIVEL_CLASSIFICACAO"] = "NV1_FORCED"
    result["Z_GAP"] = 0.0
    
    return level, metadata, similarities, result


def process_similarity_partition_hierarchical(args_sublist, indices, cat_meta_by_level, worker_id, progress, task_id):
    """Processa similaridade usando busca hierárquica com fallback."""
    worker_results = []
    for idx, item_embed in args_sublist:
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            continue
        
        # Realizar busca hierárquica
        level, metadata, similarities, result = hierarchical_search_with_fallback(
            item_embed, indices, cat_meta_by_level
        )
        
        worker_results.append((idx, result))
        progress.update(task_id, advance=1)
        
    return worker_results

def classify_items(df_items, indices, cat_meta_by_level, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens
    e compara com os embeddings do catálogo unificado usando busca hierárquica.
    """
    result_df = df_items.copy()
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    # Adicionar colunas para informações sobre o nível hierárquico usado
    result_df["NIVEL_CLASSIFICACAO"] = ""
    result_df["Z_GAP"] = 0.0

    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Criar uma única progress bar para todo o processo
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    
    with progress:
        # Geração dos embeddings dos itens
        embed_task = progress.add_task("[cyan]Gerando embeddings...", total=1)
        item_embeds = embedding_function(item_texts, existing_progress=progress)
        progress.update(embed_task, completed=1)
        
        # Preparar argumentos para cálculo de similaridade
        args_list = [(idx, item_embed) for idx, item_embed in enumerate(item_embeds)]
        partitions = partition_list(args_list, MAX_WORKERS)
        similarity_results = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for worker_id, part in enumerate(partitions, start=1):
                task_id = progress.add_task(f"Worker {worker_id} similaridade hierárquica", total=len(part))
                futures.append(executor.submit(
                    process_similarity_partition_hierarchical, 
                    part, 
                    indices,
                    cat_meta_by_level,
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
    
    # Atualizar colunas desejadas para incluir informações de nível
    desired_columns = ['id_pncp', 'objetoCompra', 'NIVEL_CLASSIFICACAO', 'Z_GAP']
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"TOP_{i}")
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"SCORE_{i}")
    
    final_columns = [col for col in desired_columns if col in result_df.columns]
    return result_df[final_columns]

# Adicionar função para processar um arquivo específico:
def process_input_file(input_number):
    """Processa um arquivo de entrada específico e gera seu respectivo arquivo de saída."""
    global CHECKPOINT_FILE, INPUT_FILE, OUTPUT_FILE
    
    # Definir arquivos para esse processamento específico
    input_num_str = f"{input_number:03d}"
    INPUT_FILE = INPUT_PATH + f"\\INPUT_{input_num_str}.xlsx"
    OUTPUT_FILE = OUTPUT_PATH + f"OUTPUT_{input_num_str}.xlsx"
    CHECKPOINT_FILE = CHECKPOINT_PATH + f"CHECKPOINT_{input_num_str}_{TIMESTAMP}.pkl"
    
    # Arquivo para salvar embeddings do input
    input_embed_file = INPUT_EMBEDDINGS_DIR + f"INPUT_EMBED_{input_num_str}.pkl"
    
    console.print(f"\n[bold green]{'='*80}[/bold green]")
    console.print(f"[bold green]PROCESSANDO ARQUIVO: {os.path.basename(INPUT_FILE)}[/bold green]")
    console.print(f"[bold green]{'='*80}[/bold green]\n")
    
    start_time = time.time()
    
    try:
        # Carregar dados e verificar se existe checkpoint
        df_items, _, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Função personalizada para gerar ou carregar embeddings
        def get_or_load_embeddings(texts):
            # Verificar se já existem embeddings salvos para este input
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
            
            # Gerar novos embeddings
            new_embeddings = get_embeddings(texts)
            
            # Salvar os embeddings gerados
            console.print("[cyan]Salvando embeddings para uso futuro...[/cyan]")
            save_embeddings(new_embeddings, input_embed_file)
            
            return new_embeddings
        
        # Classificar items em batches com processamento paralelo e busca hierárquica
        console.print("[bold magenta]Iniciando classificação hierárquica com processamento paralelo...[/bold magenta]")
        
        # Usar nossa função personalizada em vez do get_embeddings padrão
        results = classify_items(df_items, indices, cat_meta_by_level, get_or_load_embeddings)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação hierárquica de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        
        # Estatísticas sobre níveis de classificação usados
        nivel_stats = results['NIVEL_CLASSIFICACAO'].value_counts()
        console.print("[cyan]Estatísticas de níveis utilizados:[/cyan]")
        for nivel, count in nivel_stats.items():
            console.print(f"  [cyan]{nivel}: {count} itens ({count/len(results)*100:.1f}%)[/cyan]")
        
        # Salvar resultados no arquivo Excel
        console.print(f"[bold magenta]Salvando resultados em {OUTPUT_FILE}...[/bold magenta]")
        results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[green]Resultados salvos com sucesso![/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Falha no processamento do arquivo {INPUT_FILE}: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return False

def main():
    global cat_embeddings_by_level, cat_meta_by_level, indices
    
    start_total = time.time()
    
    try:
        # Primeiro, verificar se todos os índices FAISS e embeddings existem
        indices = {}
        cat_embeddings_by_level = {}
        all_files_exist = True
        
        console.print("[bold magenta]Verificando embeddings e índices hierárquicos existentes...[/bold magenta]")
        
        for level in ['NV1', 'NV2', 'NV3', 'NV4']:
            level_index_file = EMBEDDINGS_DIR + f"FAISS_INDEX_{level}.index"
            level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
            
            # Verificar se os arquivos existem fisicamente
            if not os.path.exists(level_index_file) or not os.path.exists(level_embed_file):
                all_files_exist = False
                console.print(f"[yellow]Arquivos para nível {level} não encontrados.[/yellow]")
                break
        
        # Se todos os arquivos existem, tentar carregá-los diretamente
        if all_files_exist:
            console.print("[cyan]Todos os arquivos de embedding e índices encontrados. Tentando carregar...[/cyan]")
            
            loading_success = True
            for level in ['NV1', 'NV2', 'NV3', 'NV4']:
                level_index_file = EMBEDDINGS_DIR + f"FAISS_INDEX_{level}.index"
                level_embed_file = EMBEDDINGS_DIR + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
                
                try:
                    # Carregar embeddings
                    embeddings = load_embeddings(level_embed_file)
                    if embeddings is None:
                        loading_success = False
                        console.print(f"[yellow]Falha ao carregar embeddings {level}.[/yellow]")
                        break
                    
                    # Carregar índice FAISS
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
            
            # Carregar metadados do catálogo
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
            
            # Se tudo foi carregado com sucesso, podemos pular o processamento do catálogo
            if loading_success:
                console.print("[bold green]Todos os embeddings, índices e metadados carregados com sucesso![/bold green]")
                # Continuar para o processamento de arquivos
            else:
                console.print("[yellow]Falha ao carregar arquivos existentes. Gerando novos...[/yellow]")
                # Proceder com geração de embeddings
                # Carregar e processar catálogo
                catalog_file = NOVA_CAT_FILE
                cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
                console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
                
                # Preparar textos e metadados
                cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
                
                # Salvar metadados para uso futuro
                with open(EMBEDDINGS_DIR + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                    pickle.dump(cat_meta_by_level, f)
                console.print("[green]Metadados do catálogo salvos.[/green]")
                
                # Criar embeddings e índices
                indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        else:
            # Arquivos não existem, gerar tudo
            console.print("[yellow]Arquivos de embedding ou índices não encontrados. Gerando novos...[/yellow]")
            
            # Carregar e processar catálogo
            catalog_file = NOVA_CAT_FILE
            cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
            console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
            
            # Preparar textos e metadados
            cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
            
            # Salvar metadados para uso futuro
            with open(EMBEDDINGS_DIR + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                pickle.dump(cat_meta_by_level, f)
            console.print("[green]Metadados do catálogo salvos.[/green]")
            
            # Criar embeddings e índices
            indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        
        # Resto do código main() continua normalmente...
        # Validar as variáveis de intervalo
        if PAGE_BEGIN < 1:
            console.print("[bold yellow]AVISO: PAGE_BEGIN menor que 1, ajustando para 1.[/bold yellow]")
            PAGE_BEGIN = 1
            
        if PAGE_END > 51:
            console.print("[bold yellow]AVISO: PAGE_END maior que 51, ajustando para 51.[/bold yellow]")
            PAGE_END = 51
            
        if PAGE_END < PAGE_BEGIN:
            console.print("[bold red]ERRO: PAGE_END não pode ser menor que PAGE_BEGIN. Ajustando para PAGE_BEGIN.[/bold red]")
            PAGE_END = PAGE_BEGIN
        
        # Procurar arquivos INPUT_0XX.xlsx dentro do intervalo especificado
        console.print(f"[bold blue]Buscando arquivos para processamento no intervalo: {PAGE_BEGIN} a {PAGE_END}[/bold blue]")
        
        input_files = []
        for i in range(PAGE_BEGIN, PAGE_END + 1):  # +1 porque o range é exclusivo no final
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
        
        # Processar cada arquivo encontrado
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
        
        # Mostrar resumo do processamento completo
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

