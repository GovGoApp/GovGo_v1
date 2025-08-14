##### CLASSY ITENS - Classificação de Itens com Embeddings e Similaridade Hierárquica #####
###### FAISSSSS RULESSSS!!!!!
#### CLASSIFICAÇÂO DIRETA E CLASSFICAÇÃO HIERÁRQUICA - APENAS NV0+NV1+NV2 ######


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
import math

console = Console()

# Baixar recursos NLTK necessários
nltk.download('stopwords')
nltk.download('wordnet')

# Instância do console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos - atualizar estas definições
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
NOVA_CAT_PATH = BASE_PATH + "CAT\\NOVA\\"
CLASSY_PATH = BASE_PATH + "CLASSY\\"
ITENS_PATH = CLASSY_PATH + "CLASSY_ITENS\\"


# Novos caminhos para INPUT_ITENS
MS_FLAG = 1 # MS é Material ou Serviço
OC_FLAG = 1
IT_FLAG = 1
TYPE_INPUT = "_MS" if MS_FLAG else ""
TYPE_INPUT += "_OC" if OC_FLAG else ""
TYPE_INPUT += "_IT" if IT_FLAG else ""

INPUT_ITENS_PATH = ITENS_PATH + f"INPUT_ITENS{TYPE_INPUT}\\"
OUTPUT_ITENS_PATH = ITENS_PATH + "OUTPUT_ITENS\\"

# Manter os caminhos existentes para embeddings
EMBEDDINGS_PATH = CLASSY_PATH + "EMBEDDING\\"

# Novo caminho para embeddings dos itens
INPUT_ITENS_EMBEDDINGS_PATH = ITENS_PATH + "INPUT_ITENS_EMBEDDINGS\\"
SAVE_INPUT_EMBED = True

SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV2" # NV0 e NV1

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

MAX_WORKERS = 8  # Número de threads para processamento paralelo
BATCH_SIZE = 100  # Tamanho do lote para processamento de embeddings

PAGE_BEGIN = 176  # Página inicial para leitura do Excel
PAGE_END = 176 # Página final para leitura do Excel 

EMBEDDING_MODEL = "text-embedding-3-large"

OUTPUT_DEBUG = True  # Controla o modo de depuração da saída
SAMPLE_SIZE = 200 # Número de amostras a serem extraídas para depuração

TOP_N = 5  # Número de categorias mais relevantes a serem retornadas
TOP_NV1 = 5  # Número de candidatos NV1 a manter

# Pesos para combinação das abordagens
WEIGHT_HIERARCHICAL = 0.1  # Peso para abordagem hierárquica
WEIGHT_DIRECT = 0.9   # Peso para abordagem direta

# Pesos para níveis hierárquicos - modificado para apenas NV1 (soma = 1.0)
WEIGHT_NV1 = 1.0

# Caminhos para armazenamento de embeddings hierárquicos
CAT_EMBED_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"
CAT_EMBED_NV1_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV1_{EMBEDDING_MODEL.replace('-', '_')}.pkl"

# Criar locks para acessos concorrentes
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

def extract_item_type(description):
    """Extract whether an item is a MATERIAL or SERVIÇO from its description."""
    if not description or not isinstance(description, str):
        return None
        
    description = description.upper()
    if description.startswith("MATERIAL"):
        return "M"
    elif description.startswith("SERVIÇO"):
        return "S"
    else:
        return None
    
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

def load_data():  #modificado de cf_v2_1
    """Carregar dados do Excel e catálogo unificado para a versão ITENS."""
    console.print("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]")
    
    try:
        # Carregar arquivo INPUT_ITENS ao invés do INPUT normal
        df_items = pd.read_excel(INPUT_FILE, sheet_name=SHEET)
        
        # Renomear a coluna 'descrição' para 'objetoCompra' para manter compatibilidade
        # com o código existente que processa o campo 'objetoCompra'
        if 'descrição' in df_items.columns and 'objetoCompra' not in df_items.columns:
            df_items['objetoCompra'] = df_items['descrição']
            
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
        
    return df_items, cat, pd.DataFrame(), None

def print_catalog_debug_info(cat_texts_by_level, cat_meta_by_level):
    """Imprime informações de debug sobre o catálogo preparado."""
    console.print("[bold magenta]===== INFORMAÇÕES DE DEBUG DO CATÁLOGO =====[/bold magenta]")
    
    # Informações sobre cat_texts_by_level
    for level in ['NV1']:
        console.print(f"[bold cyan]Estrutura de cat_texts_by_level['{level}']:[/bold cyan]")
        if cat_texts_by_level[level]:
            console.print(f"  Tipo: {type(cat_texts_by_level[level])}")
            console.print(f"  Tamanho: {len(cat_texts_by_level[level])} itens")
            console.print(f"  Primeiro item: {cat_texts_by_level[level][0][:100]}...")
        else:
            console.print("  [red]Vazio![/red]")
    
    # Informações sobre cat_meta_by_level
    for level in ['NV1']:
        console.print(f"[bold cyan]Estrutura de cat_meta_by_level['{level}']:[/bold cyan]")
        if cat_meta_by_level[level]:
            console.print(f"  Tipo: {type(cat_meta_by_level[level])}")
            console.print(f"  Tamanho: {len(cat_meta_by_level[level])} itens")
            console.print(f"  Chaves do primeiro item: {list(cat_meta_by_level[level][0].keys())}")
            console.print(f"  Valores do primeiro item:")
            for key, value in cat_meta_by_level[level][0].items():
                console.print(f"    {key}: {value}")
        else:
            console.print("  [red]Vazio![/red]")


def prepare_catalog_entries(cat_df):
    """Preparar entradas de catálogo unificado para embedding, apenas nível NV1."""
    console.print("[bold magenta]Preparando textos de catálogo para o nível NV1...[/bold magenta]")
    
    # Dicionários para armazenar textos e metadados por nível - apenas NV1
    cat_texts_by_level = {
        'NV1': []
    }
    
    cat_meta_by_level = {
        'NV1': []
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
        
        # Processamento nível NV1 apenas
        processed_nv1 = set()
        for _, row in cat_df.iterrows():
            # Formar corretamente os códigos para NV1
            codnv0 = str(row.get('CODNV0', ''))
            codnv1 = str(row.get('CODNV1', '')).zfill(4)
            codcat_nv1 = f"{codnv0}{codnv1}"  # CODCAT para NV1
            
            # Formar corretamente os nomes para NV1
            nomnv0 = row.get('NOMNV0', '')
            nomnv1 = row.get('NOMNV1', '')
            nomcat_nv1 = f"{nomnv0} :: {nomnv1}"  # NOMCAT para NV1
            
            if codcat_nv1 not in processed_nv1:
                processed_nv1.add(codcat_nv1)
                # Texto concatenado até NV1
                combined_text = preprocess_text(nomcat_nv1)
                cat_texts_by_level['NV1'].append(combined_text)
                cat_meta_by_level['NV1'].append({
                    'CODCAT': codcat_nv1, 
                    'NOMCAT': nomcat_nv1,
                    'CODNV0': codnv0,
                    'CODNV1': codnv1,
                    'NOMNV0': nomnv0,
                    'NOMNV1': nomnv1
                })
            
            progress.update(task, advance=1)
    
    # Reportar estatísticas
    console.print(f"[magenta]Nível NV1: {len(cat_texts_by_level['NV1'])} textos únicos preparados.[/magenta]")
    
    return cat_texts_by_level, cat_meta_by_level

def calculate_direct_similarity(item_embed, cat_embeddings_nv2, cat_meta_nv2):
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    item_embed = query_embed[0]
    
    # Calcular similaridades diretamente usando produto escalar
    cat_embeds_array = np.array(cat_embeddings_nv2)
    similarities = np.dot(cat_embeds_array, item_embed)
    
    # Ordenar e selecionar TOP_N
    indices_scores = [(i, sim) for i, sim in enumerate(similarities)]
    indices_scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = indices_scores[:TOP_N]
    
    # Formatar resultados
    results = []
    for idx, (cat_idx, similarity) in enumerate(top_indices):
        meta = cat_meta_nv2[cat_idx]
        
        # Gerar CODCAT se não existir
        if 'CODCAT' in meta:
            code = meta['CODCAT']
        else:
            codnv0 = meta.get('CODNV0', '')
            codnv1 = meta.get('CODNV1', '').zfill(4)
            code = f"{codnv0}{codnv1}"
        
        # Gerar NOMCAT se não existir
        if 'NOMCAT' in meta:
            name = meta['NOMCAT']
        else:
            nomnv0 = meta.get('NOMNV0', '')
            nomnv1 = meta.get('NOMNV1', '')
            name = f"{nomnv0} :: {nomnv1}"
        
        results.append({
            'code': code,
            'name': name,
            'score': float(similarity),
        })
    
    return results

def calculate_confidence(scores):
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

def combine_results(hierarchical_results, direct_results):
    """
    Combina os resultados do cálculo hierárquico e do cálculo direto.
    Quando um código está presente em apenas um método, usa o score desse método sem diluição.
    Quando está presente em ambos, aplica os pesos WEIGHT_HIERARCHICAL e WEIGHT_DIRECT.
    """
    all_candidates = {}
    
    # Adicionar resultados hierárquicos
    for result in hierarchical_results:
        code = result['code']
        hier_score = result['score'] 
        
        # Se só tivermos hierárquico, não diluir o score com peso
        all_candidates[code] = {
            'code': code,
            'name': result['name'],
            'hier_score': hier_score,
            'direct_score': 0.0,  # Valor padrão
            'combined_score': hier_score,  # Inicialmente, score puro sem ajuste de peso
            'level': result.get('level', ''),
            'level_scores': result.get('level_scores', {})
        }
        
        # Adicionar cálculo para visualização - inicialmente apenas score hierárquico
        all_candidates[code]['score_calculation'] = f"{hier_score:.4f} (hierárquico)"
    
    # Adicionar resultados diretos
    for result in direct_results:
        code = result['code']
        direct_score = result['score']
        
        if code in all_candidates:
            # O código já existe no hierárquico - ajustar para usar os pesos
            hier_score = all_candidates[code]['hier_score']
            weighted_hier = hier_score * WEIGHT_HIERARCHICAL
            weighted_direct = direct_score * WEIGHT_DIRECT
            combined_score = weighted_hier + weighted_direct
            
            # Atualizar candidato existente
            all_candidates[code]['direct_score'] = direct_score
            all_candidates[code]['combined_score'] = combined_score  # Score ponderado
            all_candidates[code]['score_calculation'] = f"{WEIGHT_HIERARCHICAL} × {hier_score:.4f} + {WEIGHT_DIRECT} × {direct_score:.4f} = {combined_score:.4f}"
            
        else:
            # Criar novo candidato com score direto puro
            all_candidates[code] = {
                'code': code,
                'name': result['name'],
                'hier_score': 0.0,
                'direct_score': direct_score,
                'combined_score': direct_score,  # Score direto sem diluição
            }
    
    # Converter para lista e ordenar
    combined_list = list(all_candidates.values())
    combined_list.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Pegar os TOP_N melhores
    return combined_list[:TOP_N]

def create_hierarchical_indices(cat_texts_by_level, model=EMBEDDING_MODEL):
    """
    Cria embeddings e índice FAISS apenas para o nível NV1 do catálogo.
    
    Args:
        cat_texts_by_level: Dicionário com textos para cada nível
        model: Modelo de embedding a ser usado
    
    Returns:
        Tupla contendo (indices, embeddings_by_level)
    """
    console.print("[bold magenta]Criando embeddings e índice hierárquico para NV1...[/bold magenta]")
    
    # Garantir que o diretório de embeddings existe
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    indices = {}
    embeddings_by_level = {}
    
    # --------------------------------------------------------------------
    # ETAPA 1: Processar explicitamente o nível NV1
    # --------------------------------------------------------------------
    level = 'NV1'
    
    texts = cat_texts_by_level[level]
    if not texts:
        console.print(f"[bold red]ERRO CRÍTICO: Nenhum texto encontrado para {level}[/bold red]")
        return {}, {}
    
    # Arquivos para NV1
    level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
    level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
    
    # Remover arquivos antigos se existirem
    if os.path.exists(level_embed_file):
        console.print(f"[yellow]Removendo arquivo de embeddings existente para {level}...[/yellow]")
        os.remove(level_embed_file)
    
    if os.path.exists(level_index_file):
        console.print(f"[yellow]Removendo índice FAISS existente para {level}...[/yellow]")
        os.remove(level_index_file)
    
    # Gerar embeddings para NV1
    console.print(f"[cyan]Gerando embeddings para {level}...[/cyan]")
    try:
        nv1_embeddings = get_embeddings(texts, max_workers=1)
        
        if not nv1_embeddings or len(nv1_embeddings) == 0:
            console.print(f"[bold red]ERRO CRÍTICO: Nenhum embedding gerado para {level}[/bold red]")
            return {}, {}
        
        console.print(f"[green]Gerados {len(nv1_embeddings)} embeddings para {level}[/green]")
        
        # Salvar embeddings NV1
        console.print(f"[cyan]Salvando embeddings para {level}...[/cyan]")
        if save_embeddings(nv1_embeddings, level_embed_file):
            console.print(f"[green]Embeddings para {level} salvos com sucesso em {level_embed_file}[/green]")
        else:
            console.print(f"[bold red]ERRO: Falha ao salvar embeddings para {level}[/bold red]")
            return {}, {}
        
        # Criar índice FAISS para NV1
        console.print(f"[cyan]Criando índice FAISS para {level}...[/cyan]")
        embeddings_array = np.array(nv1_embeddings, dtype=np.float32)
        index_nv1 = faiss.IndexFlatIP(embeddings_array.shape[1])
        faiss.normalize_L2(embeddings_array)
        index_nv1.add(embeddings_array)
        
        # Salvar índice NV1
        faiss.write_index(index_nv1, level_index_file)
        console.print(f"[green]Índice FAISS para {level} salvo com sucesso em {level_index_file}[/green]")
        
        # Armazenar em memória
        indices[level] = index_nv1
        embeddings_by_level[level] = nv1_embeddings
        
    except Exception as e:
        console.print(f"[bold red]ERRO processando {level}: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return {}, {}
    
    # Verificação final do embedding e índice NV1
    console.print("[bold cyan]Verificação final dos embeddings e índices...[/bold cyan]")
    
    if level not in embeddings_by_level or not embeddings_by_level[level]:
        console.print(f"[bold red]ERRO: {level} não tem embeddings em memória![/bold red]")
        return {}, {}
    
    if level not in indices:
        console.print(f"[bold red]ERRO: {level} não tem índice FAISS em memória![/bold red]")
        return {}, {}
        
    if not os.path.exists(level_embed_file):
        console.print(f"[bold red]ERRO: Arquivo de embeddings para {level} não encontrado![/bold red]")
        return {}, {}
        
    if not os.path.exists(level_index_file):
        console.print(f"[bold red]ERRO: Arquivo de índice FAISS para {level} não encontrado![/bold red]")
        return {}, {}
        
    file_size_embed = os.path.getsize(level_embed_file) / (1024 * 1024)
    file_size_index = os.path.getsize(level_index_file) / (1024 * 1024)
    
    console.print(f"[green]Verificação {level}: {len(embeddings_by_level[level])} embeddings em memória[/green]")
    console.print(f"[green]Verificação {level}: Arquivo de embeddings presente ({file_size_embed:.2f} MB)[/green]")
    console.print(f"[green]Verificação {level}: Índice FAISS em memória[/green]")
    console.print(f"[green]Verificação {level}: Arquivo de índice FAISS presente ({file_size_index:.2f} MB)[/green]")
    
    console.print("[bold green]Embeddings e índices para NV1 criados com sucesso![/bold green]")
    return indices, embeddings_by_level

def partition_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n)]

def process_embedding_partition_shared(batch_indices, texts, model, worker_id, progress, task_id):
    worker_results = []
    for i in batch_indices:
        batch = texts[i:i+BATCH_SIZE]
        batch_embeddings = process_batch(batch, model)
        worker_results.extend(batch_embeddings)
        progress.update(task_id, advance=1)
    return worker_results

def get_embeddings(texts, model=EMBEDDING_MODEL, existing_progress=None, max_workers=MAX_WORKERS):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI com progress bars por worker."""
    embeddings = []
    all_indices = list(range(0, len(texts), BATCH_SIZE))
    partitions = partition_list(all_indices, max_workers)
    
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
    """Processa um lote de textos para embeddings, com tentativas em caso de erro e validação de entrada."""
    max_retries = 5
    retry_delay = 5
    
    # Validar batch antes de enviar para API
    validated_batch = []
    for text in batch:
        # Garantir que é string e não está vazio
        if text is None:
            text = ""
        
        # Converter para string se não for
        if not isinstance(text, str):
            text = str(text)
            
        # Verificar se a string não está vazia após processamento
        if not text.strip():
            text = " "  # Espaço em branco para evitar erro de string vazia
            
        # Limitar tamanho se necessário (OpenAI tem limite de tokens)
        if len(text) > 8000:  # Valor arbitrário seguro
            text = text[:8000]
            
        validated_batch.append(text)
    
    # Verificação final: batch não pode estar vazio
    if not validated_batch:
        validated_batch = [" "]  # Adicionar pelo menos uma string não vazia
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=validated_batch
            )
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                # Logar detalhes adicionais para debug em caso de erro
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                console.print(f"[bold yellow]Detalhes do batch: {len(validated_batch)} itens[/bold yellow]")
                if validated_batch:
                    console.print(f"[bold yellow]Primeiro item: {validated_batch[0][:100]}...[/bold yellow]")
                raise

def fast_hierarchical_beam_search_combined(item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps, item_type=None):
    """
    Versão que combina cálculo hierárquico com cálculo direto, respeitando tipo (M/S).
    Modificada para usar apenas NV1.
    """
    
    # Inicializar resultados vazios
    hierarchical_results = []
    direct_results = []
    
    # 1. Realizar cálculo hierárquico apenas se o peso for diferente de zero
    if WEIGHT_HIERARCHICAL != 0:
        hierarchical_results = fast_hierarchical_beam_search(
            item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, 
            hierarchical_maps, item_type
        )
    
    # 2. Realizar cálculo direto apenas se o peso for diferente de zero
    # OU se ambos pesos forem zero (neste caso, usamos apenas a classificação direta)
    if WEIGHT_DIRECT != 0 or (WEIGHT_HIERARCHICAL == 0 and WEIGHT_DIRECT == 0):
        direct_results = calculate_direct_similarity_with_faiss(
            item_embed, indices, cat_meta_by_level['NV2'], item_type
        )
    
    # 3. Se ambos pesos forem zero, formatamos os resultados diretos para manter
    # a estrutura consistente com o formato esperado pela função de combinação
    if WEIGHT_HIERARCHICAL == 0 and WEIGHT_DIRECT == 0:
        combined_results = []
        for result in direct_results:
            combined_results.append({
                'code': result['code'],
                'name': result['name'],
                'hier_score': 0.0,
                'direct_score': result['score'],
                'combined_score': result['score'],
                'level': result['level'],
                'level_scores': result['level_scores']
            })
    else:
        # Caso contrário, combinar os resultados normalmente
        combined_results = combine_results(hierarchical_results, direct_results)
    
    # Adicionar informações de debug ao primeiro resultado
    if OUTPUT_DEBUG and combined_results:
        debug_info = {}
        if hierarchical_results and 'debug_info' in hierarchical_results[0]:
            debug_info = hierarchical_results[0]['debug_info']
        
        # Adicionar informações dos resultados diretos e hierárquicos
        debug_info['direct_results'] = direct_results
        debug_info['hierarchical_results'] = hierarchical_results
        debug_info['item_type'] = item_type  # Adicionar o tipo do item
        
        # Adicionar ao primeiro resultado combinado
        combined_results[0]['debug_info'] = debug_info
    
    return combined_results

def process_similarity_partition_combined(args_sublist, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps, worker_id, progress, task_id):
    """Processa similaridade usando ambos os métodos e os combina."""
    worker_results = []
    
    # Modifique esta linha para desempacotar os 4 valores corretamente
    for args in args_sublist:
        idx = args[0]
        item_embed = args[1]
        item_description = args[2] if len(args) > 2 else None
        item_type = args[3] if len(args) > 3 else None
        
        if item_embed is None:
            worker_results.append((idx, {}))
            progress.update(task_id, advance=1)
            continue
        
        # Usar o tipo de item extraído diretamente da tupla de argumentos
        results = fast_hierarchical_beam_search_combined(
            item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, 
            hierarchical_maps, item_type
        )
        
        # Resto da função permanece igual
        formatted_result = {}
        for i, result in enumerate(results):
            formatted_result[f"TOP_{i+1}"] = f"{result['code']} - {result['name']}"
            formatted_result[f"SCORE_{i+1}"] = round(result['combined_score'], 4)
            formatted_result[f"HIER_SCORE_{i+1}"] = round(result['hier_score'], 4)
            formatted_result[f"DIRECT_SCORE_{i+1}"] = round(result['direct_score'], 4)
            
        if results:
            level_scores = results[0]['level_scores']
            for level, score in level_scores.items():
                formatted_result[f"SCORE_{level}"] = score
            
            if 'score_calculation' in results[0]:
                formatted_result["SCORE_CALCULATION"] = results[0]['score_calculation']
                
            if OUTPUT_DEBUG and 'debug_info' in results[0]:
                debug = results[0]['debug_info']
                
                # Adicionar resultados hierárquicos
                hierarchical_results = results[0]['debug_info'].get('hierarchical_results', [])
                for i, hier_result in enumerate(hierarchical_results[:TOP_N]):
                    formatted_result[f"TOP_HIER_{i+1}"] = f"{hier_result['code']} - {hier_result['name']}"
                    formatted_result[f"SCORE_HIER_{i+1}"] = hier_result['score']
                
                # Adicionar resultados diretos
                direct_results = results[0]['debug_info'].get('direct_results', [])
                for i, direct_result in enumerate(direct_results[:TOP_N]):
                    formatted_result[f"TOP_DIRECT_{i+1}"] = f"{direct_result['code']} - {direct_result['name']}"
                    formatted_result[f"SCORE_DIRECT_{i+1}"] = direct_result['score']
                
                # As informações de nível continuam como antes
                if 'nv1_results' in debug:
                    for i, nv1_info in enumerate(debug['nv1_results'][:TOP_NV1]):
                        formatted_result[f"TOP_NV1_{i+1}"] = f"{nv1_info['code']} - {nv1_info['name']}"
                        formatted_result[f"SCORE_NV1_{i+1}"] = nv1_info['similarity']
                
        worker_results.append((idx, formatted_result))
        progress.update(task_id, advance=1)
        
    return worker_results

def calculate_direct_similarity_with_faiss(item_embed, indices, cat_meta_nv1, item_type=None):
    """
    Versão que usa o índice FAISS existente para busca direta e respeita o tipo (M/S).
    Modificada para usar apenas NV1 como nível direto.
    """
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Usar índice FAISS existente - buscar mais itens para depois filtrar
    search_k = TOP_N * 3 if item_type else TOP_N
    D, I = indices['NV1'].search(query_embed, search_k)
    
    results = []
    for i, (idx, distance) in enumerate(zip(I[0], D[0])):
        meta = cat_meta_nv1[idx]
        
        # Gerar CODCAT_NV1 se não existir
        if 'CODCAT' in meta:
            code = meta['CODCAT']
        else:
            # Construir o código a partir dos componentes individuais
            codnv0 = meta.get('CODNV0', '')
            codnv1 = meta.get('CODNV1', '').zfill(4)
            code = f"{codnv0}{codnv1}"
        
        # Gerar NOMCAT se não existir
        if 'NOMCAT' in meta:
            name = meta['NOMCAT']
        else:
            # Construir o nome a partir dos componentes individuais
            nomnv0 = meta.get('NOMNV0', '')
            nomnv1 = meta.get('NOMNV1', '')
            name = f"{nomnv0} :: {nomnv1}"
        
        cat_type = meta.get('CODNV0', '')  # Obtém o tipo da categoria (M/S)
        
        # Se um tipo de item foi especificado, filtre apenas categorias compatíveis
        if item_type and cat_type != item_type:
            continue
            
        # Converter distância para similaridade
        similarity = float(distance)
        
        results.append({
            'code': code,
            'name': name,
            'score': similarity,
            'level': 'NV1',
            'level_scores': {'NV1': similarity}
        })
        
        # Se já temos TOP_N resultados do tipo correto, podemos parar
        if len(results) >= TOP_N:
            break
    
    return results[:TOP_N]  # Garantir que retornamos no máximo TOP_N resultados

def precompute_hierarchical_relationships(cat_meta_by_level):
    """
    Versão simplificada que retorna um dicionário vazio.
    Como só temos NV1, não há relações hierárquicas para calcular.
    """
    console.print("[cyan]Sem relações hierárquicas para pré-calcular (usando apenas NV1).[/cyan]")
    return {}

def classify_items_combined(df_items, indices, cat_meta_by_level, cat_embeddings_by_level, embedding_function):
    """Versão modificada para processar arquivos INPUT_ITENS e respeitar tipo M/S."""
    # Criar um dicionário com todas as colunas e valores iniciais
    num_rows = len(df_items)
    result_columns = {}
    
    # Copiar as colunas originais - incluindo as novas colunas de INPUT_ITENS
    for col in df_items.columns:
        result_columns[col] = df_items[col].values
    
    # Adicionar coluna para o tipo de item (para debug)
    result_columns["item_type"] = [""] * num_rows
    
    # Pré-alocar todas as colunas com valores padrão
    # Colunas básicas para resultados
    for i in range(1, TOP_N + 1):
        result_columns[f"TOP_{i}"] = [""] * num_rows
        result_columns[f"SCORE_{i}"] = [0.0] * num_rows
        result_columns[f"HIER_SCORE_{i}"] = [0.0] * num_rows
        result_columns[f"DIRECT_SCORE_{i}"] = [0.0] * num_rows
        result_columns["CONFIDENCE"] = [0.0] * num_rows
    
    # Criar DataFrame de uma vez com todas as colunas pré-alocadas
    result_df = pd.DataFrame(result_columns)
    
    # Pré-calcular relações hierárquicas
    hierarchical_maps = precompute_hierarchical_relationships(cat_meta_by_level)

    # Processar textos e gerar embeddings
    # Usar 'objetoCompra' que foi mapeado da coluna 'descrição' na função load_data
    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Extrair e armazenar o tipo de item (M/S) das descrições
    item_types = [extract_item_type(text) for text in df_items["objetoCompra"]]
    for idx, item_type in enumerate(item_types):
        result_df.at[idx, "item_type"] = item_type if item_type else "Desconhecido"
    
    # O resto do processamento segue igual, mas modificado para passar o tipo do item
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    
    with progress:
        # Gerar embeddings
        embed_task = progress.add_task("[cyan]Gerando embeddings...", total=1)
        item_embeds = embedding_function(item_texts, existing_progress=progress)
        progress.update(embed_task, completed=1)
        
        # Processar similaridade em paralelo - incluindo o tipo do item e descrição nos argumentos
        args_list = [(idx, item_embed, df_items["objetoCompra"].iloc[idx], item_types[idx]) 
                     for idx, item_embed in enumerate(item_embeds)]
                     
        partitions = partition_list(args_list, MAX_WORKERS)
        similarity_results = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for worker_id, part in enumerate(partitions, start=1):
                task_id = progress.add_task(f"Worker {worker_id} similaridade", total=len(part))
                futures.append(executor.submit(
                    process_similarity_partition_combined, 
                    part, indices, cat_meta_by_level, cat_embeddings_by_level,
                    hierarchical_maps, worker_id, progress, task_id
                ))
            
            for future in futures:
                similarity_results.extend(future.result())
    
    # Atualizar DataFrame com os resultados
    for idx, similarity_data in similarity_results:
        for key, value in similarity_data.items():
            result_df.at[idx, key] = value

        if any(f"SCORE_{i+1}" in similarity_data for i in range(TOP_N)):
            scores = [similarity_data.get(f"SCORE_{i+1}", 0.0) for i in range(TOP_N)]
            scores = [s for s in scores if s > 0]  # remover zeros
            confidence = calculate_confidence(scores)
            result_df.at[idx, "CONFIDENCE"] = round(confidence, 2)

    # Garantir que sempre retornamos um DataFrame válido
    if OUTPUT_DEBUG:
        ordered_columns = [
            'numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 'item_type',
            # TOP_1 a TOP_5
            *[f"TOP_{i}" for i in range(1, TOP_N + 1)],
            # SCORE_1 a SCORE_5
            *[f"SCORE_{i}" for i in range(1, TOP_N + 1)],
            # Scores por nível
            'SCORE_NV1',
            'SCORE_CALCULATION',
            # TOP_NV1_1 a TOP_NV1_n
            *[f"TOP_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            # SCORE_NV1_1 a SCORE_NV1_n
            *[f"SCORE_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            # Hierárquicos vs Diretos
            *[f"TOP_HIER_{i}" for i in range(1, TOP_N + 1)],
            *[f"SCORE_HIER_{i}" for i in range(1, TOP_N + 1)],
            *[f"TOP_DIRECT_{i}" for i in range(1, TOP_N + 1)],
            *[f"SCORE_DIRECT_{i}" for i in range(1, TOP_N + 1)],
            # Confiança
            'CONFIDENCE'
        ]
        
        # Filtrar apenas colunas que existem no DataFrame
        final_columns = [col for col in ordered_columns if col in result_df.columns]
        return result_df[final_columns]
    else:
        # Modo não-debug - incluir apenas colunas essenciais
        desired_columns = ['numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 'item_type']
        
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"TOP_{i}")
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"SCORE_{i}")
        
        desired_columns.append("CONFIDENCE")

        final_columns = [col for col in desired_columns if col in result_df.columns]
        return result_df[final_columns]
    
def process_input_file(input_number):
    global INPUT_FILE, OUTPUT_FILE
    
    input_num_str = f"{input_number:03d}"
    
    # Extrair valores de parâmetros para nome de arquivo
    # WH = Weight Hierarchical, WD = Weight Direct
    wh_str = f"H{int(WEIGHT_HIERARCHICAL*10)}"
    wd_str = f"D{int(WEIGHT_DIRECT*10)}"
    
    # NNN = Número de candidatos considerados em cada nível - MODIFICADO para apenas NV1 e NV2
    nnn_str = f"{TOP_NV1}"
    
    # Flags para filtros
    ms_flag = "1" if MS_FLAG else "0"
    oc_flag = "1" if OC_FLAG else "0"
    it_flag = "1" if IT_FLAG else "0"
    
    # Construir nome de arquivo com padrão modificado: H{WH}_D{WD}_{NNN}_{MS}_{OC}_{IT}
    config_suffix = f"{wh_str}_{wd_str}_{nnn_str}_{ms_flag}_{oc_flag}_{it_flag}_NV1"
    
    # Ajustar nomes de arquivo para INPUT_ITEM com todos os parâmetros
    INPUT_FILE = INPUT_ITENS_PATH + f"INPUT_ITEM_{input_num_str}.xlsx"
    OUTPUT_FILE = OUTPUT_ITENS_PATH + f"OUTPUT_ITEM_{input_num_str}_{config_suffix}_{TIMESTAMP}.xlsx"
    INPUT_EMBED_FILE = INPUT_ITENS_EMBEDDINGS_PATH + f"INPUT_ITEM_EMBED_{input_num_str}.pkl"
    
    console.print(f"\n[bold green]{'='*80}[/bold green]")
    console.print(f"[bold green]PROCESSANDO ARQUIVO: {os.path.basename(INPUT_FILE)}[/bold green]")
    console.print(f"[bold green]SAÍDA: {os.path.basename(OUTPUT_FILE)}[/bold green]")
    console.print(f"[bold green]{'='*80}[/bold green]\n")
    
    start_time = time.time()
    
    try:
        df_items, _, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        def get_or_load_embeddings(texts, existing_progress=None):
            if os.path.exists(INPUT_EMBED_FILE):
                console.print("[cyan]Embeddings existentes encontrados. Carregando...[/cyan]")
                try:
                    saved_embeddings = load_embeddings(INPUT_EMBED_FILE)
                    if saved_embeddings and len(saved_embeddings) == len(texts):
                        console.print(f"[green]Embeddings carregados com sucesso para {len(saved_embeddings)} itens.[/green]")
                        return saved_embeddings
                    else:
                        console.print("[yellow]Embeddings existentes incompatíveis. Gerando novos...[/yellow]")
                except Exception as e:
                    console.print(f"[red]Erro ao carregar embeddings: {str(e)}. Gerando novos...[/red]")
            
            new_embeddings = get_embeddings(texts, existing_progress=existing_progress, max_workers=MAX_WORKERS)
            
            if SAVE_INPUT_EMBED:
                console.print("[cyan]Salvando embeddings para uso futuro...[/cyan]")
                save_embeddings(new_embeddings, INPUT_EMBED_FILE)
            else:
                console.print("[yellow]Salvar embeddings desativado.[/yellow]")
            
            return new_embeddings
        
        console.print("[bold magenta]Iniciando classificação híbrida (hierárquica + direta) com processamento paralelo...[/bold magenta]")
        console.print("[bold yellow]ATENÇÃO: Usando apenas níveis hierárquicos NV1 e NV2 (sem NV3)[/bold yellow]")
        
        # Usar a função de classificação combinada adaptada para itens
        results = classify_items_combined(df_items, indices, cat_meta_by_level, cat_embeddings_by_level, get_or_load_embeddings)
        
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

def fast_hierarchical_beam_search(item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps, item_type=None):
    """
    Versão simplificada que retorna diretamente os resultados de NV1.
    Como só temos NV1, não há hierarquia real para navegar.
    """
    
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Calcular similaridades NV1 usando produto escalar
    nv1_embeddings = np.array(cat_embeddings_by_level['NV1'])
    nv1_similarities_all = np.dot(nv1_embeddings, item_embed)
    
    # Ordenar e selecionar os TOP_N melhores, filtrando por tipo se especificado
    nv1_indices_scores = []
    for i, sim in enumerate(nv1_similarities_all):
        nv1_meta = cat_meta_by_level['NV1'][i]
        cat_type = nv1_meta.get('CODNV0', '')
        
        # Se item_type foi informado, só incluir categorias do mesmo tipo
        if item_type is None or cat_type == item_type:
            nv1_indices_scores.append((i, sim))
    
    # Ordenar e selecionar top candidatos do tipo correto
    nv1_indices_scores.sort(key=lambda x: x[1], reverse=True)
    top_nv1 = nv1_indices_scores[:TOP_N]
    
    candidates = []
    
    debug_info = {
        'nv1_results': [],
        'item_type': item_type
    }
    
    # Processar resultados NV1
    for idx, (nv1_idx, nv1_similarity) in enumerate(top_nv1):
        nv1_meta = cat_meta_by_level['NV1'][nv1_idx]
        nv1_code = f"{str(nv1_meta.get('CODNV0', ''))}{str(nv1_meta.get('CODNV1', '')).zfill(4)}"

        if OUTPUT_DEBUG:
            nv1_info = {
                'code': nv1_code,
                'name': f"{nv1_meta.get('NOMNV0', '')} :: {nv1_meta.get('NOMNV1', '')}",
                'similarity': float(nv1_similarity),
                'rank': idx + 1
            }
            debug_info['nv1_results'].append(nv1_info)
        
        # Cada resultado NV1 é um candidato direto
        code = nv1_code
        name = f"{nv1_meta.get('NOMNV0', '')} :: {nv1_meta.get('NOMNV1', '')}"
        
        candidates.append({
            'code': code,
            'name': name,
            'score': float(nv1_similarity),
            'level': 'NV1',
            'level_scores': {
                'NV1': float(nv1_similarity)
            },
            'score_calculation': f"{nv1_similarity:.4f}"
        })
    
    # Adicionar informações de debug ao primeiro resultado
    if OUTPUT_DEBUG and candidates:
        candidates[0]['debug_info'] = debug_info
    
    return candidates

def analyze_hierarchical_results(output_file):
    """
    Carrega um arquivo de resultados e exibe os candidatos dos níveis hierárquicos.
    Requer que OUTPUT_DEBUG esteja configurado como True quando o arquivo foi gerado.
    MODIFICADO para mostrar apenas NV1 e NV2.
    
    Args:
        output_file: Caminho para o arquivo de resultados.
    """
    try:
        console.print(f"\n[bold magenta]{'='*80}[/bold magenta]")
        console.print(f"[bold magenta]ANÁLISE HIERÁRQUICA DE: {os.path.basename(output_file)}[/bold magenta]")
        console.print(f"[bold magenta]{'='*80}[/bold magenta]\n")
        
        df = pd.read_excel(output_file)
        
        if 'TOP_NV1_1' not in df.columns:
            console.print("[bold red]Este arquivo não contém informações de debug hierárquico.[/bold red]")
            console.print("[bold red]Execute novamente com OUTPUT_DEBUG=True.[/bold red]")
            return
        
        # Selecionar um subconjunto de itens para análise (ou todos se for pequeno)
        sample_size = min(10, len(df))
        samples = df.sample(sample_size) if len(df) > 10 else df
        
        # Para cada item da amostra
        for i, row in samples.iterrows():
            console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
            console.print(f"[bold cyan]Item {i+1}/{sample_size}: {row.get('descrição', row.get('objetoCompra', ''))}[/bold cyan]")
            console.print(f"[bold cyan]{'='*60}[/bold cyan]")
            
            # Resultado final escolhido
            console.print(f"\n[bold green]RESULTADO FINAL:[/bold green]")
            for j in range(1, TOP_N + 1):
                if f"TOP_{j}" in row and pd.notna(row[f"TOP_{j}"]):
                    console.print(f"  TOP_{j}: {row[f'TOP_{j}']} - Score: {row.get(f'SCORE_{j}', 'N/A')}")
            
            # Resultados do Nível 1
            console.print(f"\n[bold yellow]CANDIDATOS NÍVEL 1:[/bold yellow]")
            for j in range(1, TOP_NV1 + 1):
                if f"TOP_NV1_{j}" in row and pd.notna(row[f"TOP_NV1_{j}"]):
                    console.print(f"  NV1_{j}: {row[f'TOP_NV1_{j}']} - Score: {row.get(f'SCORE_NV1_{j}', 'N/A')}")
                       
            # Score calculation
            if "SCORE_CALCULATION" in row and pd.notna(row["SCORE_CALCULATION"]):
                console.print(f"\n[bold blue]CÁLCULO DE SCORE:[/bold blue]")
                console.print(f"  {row['SCORE_CALCULATION']}")
            
            console.print("\n" + "-"*80)
            
            # Perguntar se deseja continuar após cada item
            if i < sample_size - 1:
                response = input("Pressione Enter para ver o próximo item (ou 'q' para sair): ")
                if response.lower() == 'q':
                    break
        
        # Estatísticas gerais
        console.print("\n[bold magenta]ESTATÍSTICAS GERAIS:[/bold magenta]")
                # Estatísticas gerais (completion of analyze_hierarchical_results function)
        console.print("\n[bold magenta]ESTATÍSTICAS GERAIS:[/bold magenta]")
        console.print(f"Total de itens analisados: {len(df)}")
        
    except Exception as e:
        console.print(f"[bold red]Erro na análise hierárquica: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

def analyze_direct_results(output_file):
    """
    Carrega um arquivo de resultados e exibe os candidatos da classificação direta.
    Requer que OUTPUT_DEBUG esteja configurado como True quando o arquivo foi gerado.
    
    Args:
        output_file: Caminho para o arquivo de resultados.
    """
    try:
        console.print(f"\n[bold magenta]{'='*80}[/bold magenta]")
        console.print(f"[bold magenta]ANÁLISE DE CLASSIFICAÇÃO DIRETA: {os.path.basename(output_file)}[/bold magenta]")
        console.print(f"[bold magenta]{'='*80}[/bold magenta]\n")
        
        df = pd.read_excel(output_file)
        
        if 'TOP_DIRECT_1' not in df.columns:
            console.print("[bold red]Este arquivo não contém informações de debug para classificação direta.[/bold red]")
            console.print("[bold red]Execute novamente com OUTPUT_DEBUG=True.[/bold red]")
            return
        
        # Selecionar um subconjunto de itens para análise (ou todos se for pequeno)
        sample_size = min(10, len(df))
        samples = df.sample(sample_size) if len(df) > 10 else df
        
        # Para cada item da amostra
        for i, row in samples.iterrows():
            console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
            console.print(f"[bold cyan]Item {i+1}/{sample_size}: {row.get('descrição', row.get('objetoCompra', ''))}[/bold cyan]")
            console.print(f"[bold cyan]{'='*60}[/bold cyan]")
            
            # Resultado final escolhido
            console.print(f"\n[bold green]RESULTADO FINAL COMBINADO:[/bold green]")
            for j in range(1, TOP_N + 1):
                if f"TOP_{j}" in row and pd.notna(row[f"TOP_{j}"]):
                    console.print(f"  TOP_{j}: {row[f'TOP_{j}']} - Score: {row.get(f'SCORE_{j}', 'N/A')}")
            
            # Resultados da classificação direta
            console.print(f"\n[bold yellow]RESULTADOS DIRETOS (SEM HIERARQUIA):[/bold yellow]")
            for j in range(1, TOP_N + 1):
                if f"TOP_DIRECT_{j}" in row and pd.notna(row[f"TOP_DIRECT_{j}"]):
                    console.print(f"  TOP_DIRECT_{j}: {row[f'TOP_DIRECT_{j}']} - Score: {row.get(f'SCORE_DIRECT_{j}', 'N/A')}")
            
            # Pontuações e confiança
            if "CONFIDENCE" in row and pd.notna(row["CONFIDENCE"]):
                console.print(f"\n[bold blue]CONFIANÇA: {row['CONFIDENCE']:.2f}%[/bold blue]")
            
            console.print("\n" + "-"*80)
            
            # Perguntar se deseja continuar após cada item
            if i < sample_size - 1:
                response = input("Pressione Enter para ver o próximo item (ou 'q' para sair): ")
                if response.lower() == 'q':
                    break
        
        # Estatísticas gerais
        console.print("\n[bold magenta]ESTATÍSTICAS GERAIS:[/bold magenta]")
        console.print(f"Total de itens analisados: {len(df)}")
        
    except Exception as e:
        console.print(f"[bold red]Erro na análise direta: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

def export_debug_to_markdown(output_file):
    """
    Exporta informações de debug dos resultados hierárquicos e diretos para um arquivo Markdown.
    Requer que OUTPUT_DEBUG esteja configurado como True quando o arquivo foi gerado.
    MODIFICADO: Adaptado para apenas mostrar informações de NV1 e NV2.
    
    Args:
        output_file: Caminho para o arquivo de resultados.
    """
    if not OUTPUT_DEBUG:
        console.print("[yellow]OUTPUT_DEBUG está desativado. Ativando-o para exportar informações de debug.[/yellow]")
        return
    
    try:
        console.print(f"[bold magenta]Exportando informações de debug para Markdown...[/bold magenta]")
        
        df = pd.read_excel(output_file)
        
        if 'TOP_NV1_1' not in df.columns:
            console.print("[bold red]Este arquivo não contém informações de debug hierárquico.[/bold red]")
            console.print("[bold red]Execute novamente com OUTPUT_DEBUG=True.[/bold red]")
            return
        
        # Criar nome do arquivo de saída
        base_filename = os.path.basename(output_file)
        md_filename = os.path.join(
            os.path.dirname(output_file),
            f"DEBUG_{os.path.splitext(base_filename)[0]}.md"
        )
        
        # Extrair parâmetros do nome do arquivo
        file_parts = os.path.splitext(base_filename)[0].split('_')
        if len(file_parts) >= 3:
            model_config = '_'.join(file_parts[2:])
        else:
            model_config = "Configuração desconhecida"
        
        # Selecionar uma amostra para análise
        sample_size = min(SAMPLE_SIZE, len(df))
        samples = df.sample(sample_size) if len(df) > SAMPLE_SIZE else df
        
        with open(md_filename, 'w', encoding='utf-8') as md_file:
            # Cabeçalho do documento
            md_file.write(f"# Análise de Debug - {base_filename}\n\n")
            md_file.write(f"**Configuração:** {model_config}\n")
            md_file.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            md_file.write(f"**Total de itens:** {len(df)}\n\n")
            
            md_file.write("## Parâmetros do Modelo\n\n")
            md_file.write(f"- **WEIGHT_HIERARCHICAL:** {WEIGHT_HIERARCHICAL}\n")
            md_file.write(f"- **WEIGHT_DIRECT:** {WEIGHT_DIRECT}\n")
            md_file.write(f"- **WEIGHT_NV1:** {WEIGHT_NV1}\n")
            md_file.write(f"- **TOP_NV1:** {TOP_NV1}\n")
            
            # Estatísticas gerais
            md_file.write("## Estatísticas Gerais\n\n")
            
            # Calcular estatísticas
            confidence_gt50 = len(df[df['CONFIDENCE'] > 50])/len(df)*100 if 'CONFIDENCE' in df.columns else 'N/A'
            confidence_lt50 = len(df[df['CONFIDENCE'] <= 50])/len(df)*100 if 'CONFIDENCE' in df.columns else 'N/A'
            
            md_file.write(f"- **Confiança > 50%:** {confidence_gt50:.2f}%\n")
            md_file.write(f"- **Confiança ≤ 50%:** {confidence_lt50:.2f}%\n\n")
            
            # Análise item por item
            md_file.write("## Análise de Itens\n\n")
            
            for i, row in samples.iterrows():
                item_desc = row.get('descrição', row.get('objetoCompra', 'Sem descrição'))
                md_file.write(f"### ITEM {i+1}: {item_desc}\n\n")
                
                # Resultados finais combinados
                md_file.write("#### Resultados Finais (Combinados)\n\n")
                for j in range(1, TOP_N + 1):
                    if f"TOP_{j}" in row and pd.notna(row[f"TOP_{j}"]):
                        md_file.write(f"- **TOP_{j}:** {row[f'TOP_{j}']} - Score: {row.get(f'SCORE_{j}', 'N/A')}\n")
                
                # Informação de confiança
                if "CONFIDENCE" in row and pd.notna(row["CONFIDENCE"]):
                    md_file.write(f"\n**Confiança:** {row['CONFIDENCE']:.2f}%\n")
                
                # Cálculo de score quando disponível
                if "SCORE_CALCULATION" in row and pd.notna(row["SCORE_CALCULATION"]):
                    md_file.write(f"\n**Cálculo de Score:** {row['SCORE_CALCULATION']}\n")
                
                # Resultados da classificação direta
                md_file.write("\n#### Resultados Diretos\n\n")
                direct_present = False
                for j in range(1, TOP_N + 1):
                    if f"TOP_DIRECT_{j}" in row and pd.notna(row[f"TOP_DIRECT_{j}"]):
                        direct_present = True
                        md_file.write(f"- **TOP_DIRECT_{j}:** {row[f'TOP_DIRECT_{j}']} - Score: {row.get(f'SCORE_DIRECT_{j}', 'N/A')}\n")
                
                if not direct_present:
                    md_file.write("*Informações de classificação direta não disponíveis*\n")
                
                # Candidatos do nível 1
                md_file.write("\n#### Candidatos Nível 1\n\n")
                nv1_present = False
                for j in range(1, TOP_NV1 + 1):
                    if f"TOP_NV1_{j}" in row and pd.notna(row[f"TOP_NV1_{j}"]):
                        nv1_present = True
                        md_file.write(f"- **NV1_{j}:** {row[f'TOP_NV1_{j}']} - Score: {row.get(f'SCORE_NV1_{j}', 'N/A')}\n")
                
                if not nv1_present:
                    md_file.write("*Informações de candidatos NV1 não disponíveis*\n")
                
                md_file.write("\n---\n\n")  # Separador entre itens
            
            md_file.write("## Conclusões\n\n")
            md_file.write("Esta análise de debug permite visualizar como os diferentes níveis hierárquicos (NV1 e NV2) contribuem para a classificação final, comparando com a abordagem direta.\n\n")
            md_file.write("Para mais detalhes, execute as funções `analyze_hierarchical_results()` e `analyze_direct_results()` diretamente no console.\n")
        
        console.print(f"[bold green]Informações de debug exportadas para: {md_filename}[/bold green]")
        return md_filename
        
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar debug para Markdown: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return None

def main():
    global cat_embeddings_by_level, cat_meta_by_level, indices
    global PAGE_BEGIN, PAGE_END
    
    start_total = time.time()
    
    try:
        indices = {}
        cat_embeddings_by_level = {}
        levels = ['NV1']
        
        console.print("[bold magenta]Verificando embeddings e índices hierárquicos...[/bold magenta]")
        
        # Verificar se todos os arquivos necessários existem
        missing_files = False
        for level in levels:
            level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
            level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
            metadata_file = EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl"
            
            if not os.path.exists(level_index_file) or not os.path.exists(level_embed_file) or not os.path.exists(metadata_file):
                missing_files = True
                console.print(f"[yellow]Arquivos para {level} incompletos ou ausentes.[/yellow]")
                break
        
        # Carregar ou gerar embeddings
        if not missing_files:
            # Tentar carregar arquivos existentes
            console.print("[cyan]Tentando carregar embeddings e índices existentes...[/cyan]")
            load_success = True
            
            try:
                # Carregar metadados primeiro
                with open(EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl", 'rb') as f:
                    cat_meta_by_level = pickle.load(f)
                console.print("[green]Metadados do catálogo carregados.[/green]")
                
                # Carregar embeddings e índices
                for level in levels:
                    level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
                    level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
                    
                    embeddings = load_embeddings(level_embed_file)
                    if embeddings is None:
                        raise Exception(f"Falha ao carregar embeddings para {level}")
                        
                    indices[level] = faiss.read_index(level_index_file)
                    cat_embeddings_by_level[level] = embeddings
                    console.print(f"[green]Embeddings e índice para {level} carregados com sucesso.[/green]")
            except Exception as e:
                load_success = False
                console.print(f"[yellow]Erro ao carregar arquivos: {str(e)}[/yellow]")
                
            if load_success:
                console.print("[bold green]Todos os embeddings e índices carregados com sucesso![/bold green]")
            else:
                missing_files = True  # Forçar geração se o carregamento falhar
        
        if missing_files:
            # Gerar novos embeddings
            console.print("[yellow]Gerando novos embeddings e índices...[/yellow]")
            
            # Carregar catálogo
            catalog_file = NOVA_CAT_FILE
            cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
            console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
            
            # Preparar entradas e salvar metadados
            cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
            print_catalog_debug_info(cat_texts_by_level, cat_meta_by_level)

            with open(EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                pickle.dump(cat_meta_by_level, f)
            console.print("[green]Metadados do catálogo salvos.[/green]")
            
            # Gerar embeddings e índices
            indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
            console.print("[green]Embeddings e índices criados com sucesso.[/green]")
                
            
        if PAGE_END < PAGE_BEGIN:
            console.print("[bold red]ERRO: PAGE_END não pode ser menor que PAGE_BEGIN. Ajustando para PAGE_BEGIN.[/bold red]")
            PAGE_END = PAGE_BEGIN
        
        # Modificar a busca de arquivos para encontrar arquivos INPUT_ITEM
        console.print(f"[bold blue]Buscando arquivos para processamento no intervalo: {PAGE_BEGIN} a {PAGE_END}[/bold blue]")
        
        input_files = []
        for i in range(PAGE_BEGIN, PAGE_END + 1):
            input_num_str = f"{i:03d}"
            input_file = INPUT_ITENS_PATH + f"\\INPUT_ITEM_{input_num_str}.xlsx"
            if os.path.exists(input_file):
                input_files.append(i)
            else:
                console.print(f"[yellow]Arquivo INPUT_ITEM_{input_num_str}.xlsx não encontrado e será ignorado.[/yellow]")
        
        if not input_files:
            console.print(f"[bold red]Nenhum arquivo encontrado no intervalo de {PAGE_BEGIN} a {PAGE_END}.[/bold red]")
            return
            
        console.print(f"[bold blue]Encontrados {len(input_files)} arquivos para processamento no intervalo.[/bold blue]")
        
        success_count = 0
        failure_count = 0
        
        for i, input_number in enumerate(input_files):
            console.print(f"[bold cyan]Processando arquivo {i+1}/{len(input_files)}: INPUT_ITEM_{input_number:03d}.xlsx[/bold cyan]")
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

        # Adicionar esta parte para analisar o último arquivo processado
        if OUTPUT_DEBUG and success_count > 0:
            console.print(f"\n[bold cyan]Analisando resultados do último arquivo processado...[/bold cyan]")
            
            # O OUTPUT_FILE contém o caminho do último arquivo processado
            console.print("\n[bold magenta]ANÁLISE HIERÁRQUICA[/bold magenta]")
            #analyze_hierarchical_results(OUTPUT_FILE)
            
            console.print("\n[bold magenta]ANÁLISE DIRETA[/bold magenta]")
            #analyze_direct_results(OUTPUT_FILE)
            
            # Exportar para Markdown
            md_file = export_debug_to_markdown(OUTPUT_FILE)
            if md_file:
                console.print(f"\n[bold green]Para referência futura, as análises foram exportadas para: {md_file}[/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Pipeline principal falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()