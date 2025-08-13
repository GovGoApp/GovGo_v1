##### CLASSY ITENS - Classificação de Itens com Embeddings e Similaridade Hierárquica #####
###### FAISSSSS RULESSSS!!!!!
#### CLASSIFICAÇÂO DIRETA E CLASSFICAÇÃO HIERÁRQUICA ######


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

ASSISTANT_ID = "asst_Rqb93ZDsLBPDTyYAc6JhHiYz"  # ID do assistente MSOCIT_to_TEXT

# Definir caminhos e arquivos - atualizar estas definições
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
NOVA_CAT_PATH = BASE_PATH + "CAT\\NOVA\\"
CLASSY_PATH = BASE_PATH + "CLASSY\\"
ITENS_PATH = CLASSY_PATH + "CLASSY_ITENS\\"


# Novos caminhos para INPUT_ITENS
MS_FLAG = 0 # MS é Material ou Serviço
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
SAVE_INPUT_EMBED = False

SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

MAX_WORKERS = 8  # Número de threads para processamento paralelo
BATCH_SIZE = 10  # Tamanho do lote para processamento de embeddings ##100

PAGE_BEGIN = 999  # Página inicial para leitura do Excel
PAGE_END = 999 # Página final para leitura do Excel 

EMBEDDING_MODEL = "text-embedding-3-large"

OUTPUT_DEBUG = True  # Controla o modo de depuração da saída
SAMPLE_SIZE = 100 # Número de amostras a serem extraídas para depuração

TOP_N = 5  # Número de categorias mais relevantes a serem retornadas
TOP_NV1 = 5  # Número de candidatos NV1 a manter
TOP_NV2 = 5  # Número de candidatos NV2 a manter por NV1
TOP_NV3 = 5   # Número de candidatos NV3 a manter por NV2


# Pesos para combinação das abordagens
WEIGHT_HIERARCHICAL = 0.5  # Peso para abordagem hierárquica
WEIGHT_DIRECT = 0.5   # Peso para abordagem direta

WEIGHT_NV1 = 0.33
WEIGHT_NV2 = 0.33
WEIGHT_NV3 = 0.34

# Caminhos para armazenamento de embeddings hierárquicos

CAT_EMBED_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"
CAT_EMBED_NV4_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV4_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV3_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV3_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV2_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV2_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV1_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV1_{EMBEDDING_MODEL.replace('-', '_')}.pkl"

# Criar locks para acessos concorrentes
embedding_lock = threading.Lock()

# Cache para evitar reformulações repetidas
reformulation_cache = {}
cache_lock = threading.Lock()
CACHE_PATH = ITENS_PATH + "CACHE\\"
CACHE_FILE = CACHE_PATH + "reformulation_cache.pkl"
CACHE_BATCH = 100  # Salvar cache a cada 100 itens

# Carregar cache existente se disponível
def load_cache():
    global reformulation_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'rb') as f:
                reformulation_cache = pickle.load(f)
            console.print(f"[green]Cache de reformulação carregado com {len(reformulation_cache)} entradas[/green]")
    except Exception as e:
        console.print(f"[yellow]Erro ao carregar cache: {str(e)}. Iniciando com cache vazio.[/yellow]")
        reformulation_cache = {}

# Salvar cache para uso futuro
def save_cache():
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(reformulation_cache, f)
        console.print(f"[green]Cache de reformulação salvo com {len(reformulation_cache)} entradas[/green]")
    except Exception as e:
        console.print(f"[yellow]Erro ao salvar cache: {str(e)}[/yellow]")

# Função para enviar mensagem para o assistente
def send_user_message(thread_id, content):
    """Envia uma mensagem do usuário para a thread."""
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=formatted_content
    )

# Função para aguardar completamento da execução
def poll_run(thread_id, assistant_id):
    """Tenta criar e aguardar uma run. Se já existir uma run ativa, aguarda e tenta novamente."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
        except Exception as e:
            error_msg = str(e)
            if "already has an active run" in error_msg and attempt < max_retries - 1:
                console.print(f"[yellow]Thread com run ativo. Tentativa {attempt+1}/{max_retries}. Aguardando 2 segundos...[/yellow]")
                time.sleep(2)
            else:
                raise e

# Função para obter a última mensagem do assistente
def get_latest_assistant_message(thread_id):
    """Retorna a última mensagem do assistente na thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread_id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

# Função para reformular o texto usando o assistente
# Modificação para salvar cache a cada 100 itens em vez de 10
def reformat_item_description(original_text):
    """
    Reformula a descrição de um item usando o assistente da OpenAI.
    Usa cache para evitar chamadas repetidas para o mesmo texto.
    
    Args:
        original_text: Texto original do item
        
    Returns:
        Texto reformulado pelo assistente
    """
    # Verificar se já temos esse texto no cache
    with cache_lock:
        if original_text in reformulation_cache:
            return reformulation_cache[original_text]
    
    # Se não está no cache, consultar o assistente
    try:
        # Criar uma nova thread para este item
        thread = client.beta.threads.create()
        
        # Enviar o texto original para o assistente
        send_user_message(thread.id, original_text)
        
        # Executar o assistente
        run = poll_run(thread.id, ASSISTANT_ID)
        
        # Obter a resposta
        if run.status == "completed":
            message = get_latest_assistant_message(thread.id)
            if message and message.content:
                content = message.content[0].text.value.strip()
                
                # Salvar no cache
                with cache_lock:
                    reformulation_cache[original_text] = content
                
                # Periodicamente salvar o cache (a cada 100 novos itens) - MODIFICADO DE 10 PARA 100
                if len(reformulation_cache) % CACHE_BATCH == 0:
                    save_cache()
                
                return content
        
        # Em caso de problemas, retornar o texto original
        return original_text
    
    except Exception as e:
        console.print(f"[red]Erro ao reformular texto: {str(e)}. Usando texto original.[/red]")
        return original_text

# Nova função para processar lotes de reformulação em paralelo
def process_reformulation_partition(batch_indices, texts, worker_id, progress, task_id):
    """
    Processa um lote de reformulações de texto em paralelo.
    
    Args:
        batch_indices: Lista de índices a serem processados
        texts: Lista de textos originais
        worker_id: ID do worker para logging
        progress: Objeto de progresso para atualização
        task_id: ID da tarefa de progresso
        
    Returns:
        Lista de tuplas (índice, texto reformulado)
    """
    worker_results = []
    for i in batch_indices:
        original_text = texts[i]
        reformulated_text = reformat_item_description(original_text)
        worker_results.append((i, reformulated_text))
        progress.update(task_id, advance=1)
    return worker_results

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
                    'CODCAT': str(codcat),
                    'NOMCAT': nomcat,
                    'CODNV0': str(row.get('CODNV0', '')),
                    'CODNV1': str(row.get('CODNV1', '')).zfill(4),
                    'CODNV2': str(row.get('CODNV2', '')).zfill(5),
                    'CODNV3': str(row.get('CODNV3', '')).zfill(5),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', ''),
                    'NOMNV3': row.get('NOMNV3', '')
                })

            
            progress.update(task, advance=0.25)  # 25% do progresso para NV4
        
        # Processamento nível NV3
        processed_nv3 = set()
        for _, row in cat_df.iterrows():
            codnv3_key = f"{str(row.get('CODNV0', ''))}{str(row.get('CODNV1', ''))}{str(row.get('CODNV2', ''))}{str(row.get('CODNV3', ''))}"


            
            if codnv3_key not in processed_nv3:
                processed_nv3.add(codnv3_key)
                # Texto concatenado até NV3
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}; {row.get('NOMNV2', '')}; {row.get('NOMNV3', '')}")
                cat_texts_by_level['NV3'].append(combined_text)
                cat_meta_by_level['NV3'].append({
                    'CODNV0': str(row.get('CODNV0', '')),
                    'CODNV1': str(row.get('CODNV1', '')).zfill(4),
                    'CODNV2': str(row.get('CODNV2', '')).zfill(5),
                    'CODNV3': str(row.get('CODNV3', '')).zfill(5),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', ''),
                    'NOMNV3': row.get('NOMNV3', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV3
        
        # Processamento nível NV2
        processed_nv2 = set()
        for _, row in cat_df.iterrows():
            codnv2_key = f"{str(row.get('CODNV0', ''))}{str(row.get('CODNV1', ''))}{str(row.get('CODNV2', ''))}"
            
            if codnv2_key not in processed_nv2:
                processed_nv2.add(codnv2_key)
                # Texto concatenado até NV2
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}; {row.get('NOMNV2', '')}")
                cat_texts_by_level['NV2'].append(combined_text)
                cat_meta_by_level['NV2'].append({
                    'CODNV0': str(row.get('CODNV0', '')),
                    'CODNV1': str(row.get('CODNV1', '')).zfill(4),
                    'CODNV2': str(row.get('CODNV2', '')).zfill(5),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', ''),
                    'NOMNV2': row.get('NOMNV2', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV2
        
        # Processamento nível NV1
        processed_nv1 = set()
        for _, row in cat_df.iterrows():
            codnv1_key = f"{str(row.get('CODNV0', ''))}{str(row.get('CODNV1', ''))}"
            
            if codnv1_key not in processed_nv1:
                processed_nv1.add(codnv1_key)
                # Texto concatenado até NV1
                combined_text = preprocess_text(f"{row.get('NOMNV0', '')}; {row.get('NOMNV1', '')}")
                cat_texts_by_level['NV1'].append(combined_text)
                cat_meta_by_level['NV1'].append({
                    'CODNV0': str(row.get('CODNV0', '')),
                    'CODNV1': str(row.get('CODNV1', '')).zfill(4),
                    'NOMNV0': row.get('NOMNV0', ''),
                    'NOMNV1': row.get('NOMNV1', '')
                })
            
            progress.update(task, advance=0.25)  # 25% do progresso para NV1
    
    # Reportar estatísticas
    for level, texts in cat_texts_by_level.items():
        console.print(f"[magenta]Nível {level}: {len(texts)} textos únicos preparados.[/magenta]")
    
    return cat_texts_by_level, cat_meta_by_level

def calculate_direct_similarity(item_embed, cat_embeddings_nv4, cat_meta_nv4):
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    item_embed = query_embed[0]
    
    # Calcular similaridades diretamente usando produto escalar
    cat_embeds_array = np.array(cat_embeddings_nv4)
    similarities = np.dot(cat_embeds_array, item_embed)
    
    # Ordenar e selecionar TOP_N
    indices_scores = [(i, sim) for i, sim in enumerate(similarities)]
    indices_scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = indices_scores[:TOP_N]
    
    # Formatar resultados
    results = []
    for idx, (cat_idx, similarity) in enumerate(top_indices):
        meta = cat_meta_nv4[cat_idx]
        code = meta['CODCAT']
        name = meta['NOMCAT']
        
        results.append({
            'code': code,
            'name': name,
            'score': float(similarity),
            'level': 'NV4',
            'level_scores': {'NV4': float(similarity)}
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

def combine_results_old(hierarchical_results, direct_results):
    """
    Combina os resultados do cálculo hierárquico e do cálculo direto,
    com os pesos WEIGHT_HIERARCHICAL e WEIGHT_DIRECT.
    """
    all_candidates = {}
    
    # Adicionar resultados hierárquicos
    for result in hierarchical_results:
        code = result['code']
        hier_score = result['score'] 
        weighted_hier = hier_score * WEIGHT_HIERARCHICAL
        
        all_candidates[code] = {
            'code': code,
            'name': result['name'],
            'hier_score': hier_score,
            'direct_score': 0.0,  # Valor padrão
            'combined_score': weighted_hier,
            'level': result.get('level', ''),
            'level_scores': result.get('level_scores', {})
        }
        
        # Adicionar cálculo para visualização
        all_candidates[code]['score_calculation'] = f"{WEIGHT_HIERARCHICAL} × {hier_score:.4f}"
    
    # Adicionar resultados diretos
    for result in direct_results:
        code = result['code']
        direct_score = result['score']
        weighted_direct = direct_score * WEIGHT_DIRECT
        
        if code in all_candidates:
            # Atualizar candidato existente
            all_candidates[code]['direct_score'] = direct_score
            all_candidates[code]['combined_score'] += weighted_direct
            all_candidates[code]['score_calculation'] += f" + {WEIGHT_DIRECT} × {direct_score:.4f}"
            
            # Atualizar o nível NV4 se não existir
            if 'NV4' not in all_candidates[code]['level_scores']:
                all_candidates[code]['level_scores']['NV4'] = direct_score
        else:
            # Criar novo candidato
            all_candidates[code] = {
                'code': code,
                'name': result['name'],
                'hier_score': 0.0,
                'direct_score': direct_score,
                'combined_score': weighted_direct,
                'level': 'NV4',
                'level_scores': {'NV4': direct_score},
                'score_calculation': f"{WEIGHT_DIRECT} × {direct_score:.4f}"
            }
    
    # Adicionar resultado final ao cálculo
    for code, candidate in all_candidates.items():
        candidate['score_calculation'] += f" = {candidate['combined_score']:.4f}"
    
    # Converter para lista e ordenar
    combined_list = list(all_candidates.values())
    combined_list.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Pegar os TOP_N melhores
    return combined_list[:TOP_N]

def combine_results_exclusive(hierarchical_results, direct_results):
    """
    Combina os resultados do cálculo hierárquico e do cálculo direto,
    considerando APENAS itens que aparecem em ambas as listas.
    Não inclui fallbacks quando não há suficientes para TOP_N.
    """
    # Obter códigos que existem em ambos os resultados
    hier_codes = {result['code'] for result in hierarchical_results}
    direct_codes = {result['code'] for result in direct_results}
    
    # Interseção - códigos que aparecem em ambos os conjuntos
    common_codes = hier_codes.intersection(direct_codes)
    
    # Se não houver códigos em comum, retornar lista vazia ou aviso
    if not common_codes:
        console.print("[yellow]Aviso: Nenhum código em comum entre os resultados hierárquicos e diretos.[/yellow]")
        return []  # Retornar lista vazia em vez de fallback
    
    # Criar dicionários para acesso rápido aos resultados por código
    hier_dict = {result['code']: result for result in hierarchical_results}
    direct_dict = {result['code']: result for result in direct_results}
    
    # Lista para armazenar resultados combinados
    combined_results = []
    
    # Processar apenas códigos comuns
    for code in common_codes:
        hier_result = hier_dict[code]
        direct_result = direct_dict[code]
        
        # Usar scores completos de ambos os métodos (sem diluir com zeros)
        hier_score = hier_result['score']
        direct_score = direct_result['score']
        
        # Aplicar pesos conforme definido nas constantes globais
        weighted_hier = hier_score * WEIGHT_HIERARCHICAL
        weighted_direct = direct_score * WEIGHT_DIRECT
        combined_score = weighted_hier + weighted_direct
        
        # Criar resultado combinado
        combined_result = {
            'code': code,
            'name': hier_result['name'],  # Usar o nome do hierárquico (geralmente mais completo)
            'hier_score': hier_score,
            'direct_score': direct_score,
            'combined_score': combined_score,
            'level': hier_result.get('level', 'NV4'),
            'level_scores': hier_result.get('level_scores', {}).copy(),  # Copiar para evitar referência
            'score_calculation': f"{WEIGHT_HIERARCHICAL} × {hier_score:.4f} + {WEIGHT_DIRECT} × {direct_score:.4f} = {combined_score:.4f}"
        }
        
        # Atualizar o nível NV4 se não existir
        if 'NV4' not in combined_result['level_scores']:
            combined_result['level_scores']['NV4'] = direct_score
            
        combined_results.append(combined_result)
    
    # Ordenar por pontuação combinada (maior para menor) e limitar aos TOP_N melhores
    combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Não incluir nenhum fallback, apenas retornar os itens da interseção (mesmo que sejam menos que TOP_N)
    return combined_results[:TOP_N]

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
            
            # Atualizar o nível NV4 se não existir
            if 'NV4' not in all_candidates[code]['level_scores']:
                all_candidates[code]['level_scores']['NV4'] = direct_score
        else:
            # Criar novo candidato com score direto puro
            all_candidates[code] = {
                'code': code,
                'name': result['name'],
                'hier_score': 0.0,
                'direct_score': direct_score,
                'combined_score': direct_score,  # Score direto sem diluição
                'level': 'NV4',
                'level_scores': {'NV4': direct_score},
                'score_calculation': f"{direct_score:.4f} (direto)"
            }
    
    # Converter para lista e ordenar
    combined_list = list(all_candidates.values())
    combined_list.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Pegar os TOP_N melhores
    return combined_list[:TOP_N]

def create_hierarchical_indices(cat_texts_by_level, model=EMBEDDING_MODEL):
    console.print("[bold magenta]Criando embeddings e índices FAISS hierárquicos...[/bold magenta]")
    
    indices = {}
    embeddings_by_level = {}
    
    for level, texts in cat_texts_by_level.items():
        if not texts:
            console.print(f"[bold red]Aviso: Nenhum texto encontrado para o nível {level}[/bold red]")
            # Criar array vazio em vez de pular
            embeddings_by_level[level] = []
            continue
            
        console.print(f"[cyan]Gerando embeddings para o nível {level}... ({len(texts)} textos)[/cyan]")
        embeddings = get_embeddings(texts)
        
        # Mesmo se estiver vazio, manter entrada no dicionário
        embeddings_by_level[level] = embeddings if embeddings else []

        # Salvar embeddings em arquivo
        level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
        save_embeddings(embeddings, level_embed_file)
        
        
        if not embeddings or len(embeddings) == 0:
            console.print(f"[bold red]Erro: Falha na geração de embeddings para {level}[/bold red]")
            continue
            
        # Resto do código de criação do índice...
        try:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Se for 1D, tentar corrigir, mas não abandonar se falhar
            if len(embeddings_array.shape) != 2:
                try:
                    embeddings_array = np.vstack(embeddings)
                except:
                    # Tentar converter cada embedding para array
                    fixed_embeddings = []
                    for e in embeddings:
                        if isinstance(e, (list, np.ndarray)):
                            fixed_embeddings.append(np.array(e))
                    embeddings_array = np.array(fixed_embeddings, dtype=np.float32)
            
            # Cria o índice e adiciona (sem abandonar)
            index = faiss.IndexFlatIP(embeddings_array.shape[1])
            faiss.normalize_L2(embeddings_array)
            index.add(embeddings_array)
            indices[level] = index
            
            # Salva o índice (continua mesmo se falhar)
            try:
                level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
                faiss.write_index(index, level_index_file)
            except Exception as e:
                console.print(f"[red]Erro ao salvar índice {level}: {str(e)}[/red]")
                
        except Exception as e:
            console.print(f"[bold red]Erro ao processar embeddings para {level}: {str(e)}[/bold red]")
    
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
        # Usar as constantes globais em vez de hardcoded 5
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
    
    desired_columns = ['id_pncp', 'objetoCompra', 'texto_reformulado']
    
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
            'id_pncp', 'objetoCompra', 'texto_reformulado',
            # TOP_1 a TOP_10
            *[f"TOP_{i}" for i in range(1, TOP_N + 10)],
            # SCORE_1 a SCORE_10
            *[f"SCORE_{i}" for i in range(1, TOP_N + 10)],
            # Scores por nível
            'SCORE_NV1', 'SCORE_NV2', 'SCORE_NV3', 
            'SCORE_CALCULATION',
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

def fast_hierarchical_beam_search_combined(item_embed, indices, cat_meta_by_level, cat_embeddings_by_level, hierarchical_maps, item_type=None):
    """Versão que combina cálculo hierárquico com cálculo direto, respeitando tipo (M/S)."""
    
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
            item_embed, indices, cat_meta_by_level['NV4'], item_type
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
                
                # CORREÇÃO: Adicionar diretamente os resultados hierárquicos
                # Independentemente da estrutura do debug
                hierarchical_results = results[0]['debug_info'].get('hierarchical_results', [])
                for i, hier_result in enumerate(hierarchical_results[:TOP_N]):
                    formatted_result[f"TOP_HIER_{i+1}"] = f"{hier_result['code']} - {hier_result['name']}"
                    formatted_result[f"SCORE_HIER_{i+1}"] = hier_result['score']
                
                # CORREÇÃO: Adicionar diretamente os resultados diretos
                # Independentemente da estrutura do debug
                direct_results = results[0]['debug_info'].get('direct_results', [])
                for i, direct_result in enumerate(direct_results[:TOP_N]):
                    formatted_result[f"TOP_DIRECT_{i+1}"] = f"{direct_result['code']} - {direct_result['name']}"
                    formatted_result[f"SCORE_DIRECT_{i+1}"] = direct_result['score']
                
                # As informações de nível continuam como antes
                if 'nv1_results' in debug:
                    for i, nv1_info in enumerate(debug['nv1_results'][:TOP_NV1]):
                        formatted_result[f"TOP_NV1_{i+1}"] = f"{nv1_info['code']} - {nv1_info['name']}"
                        formatted_result[f"SCORE_NV1_{i+1}"] = nv1_info['similarity']
                
                if 'nv2_results' in debug:
                    for i, nv2_info in enumerate(debug['nv2_results'][:TOP_NV2]):
                        formatted_result[f"TOP_NV2_{i+1}"] = f"{nv2_info['code']} - {nv2_info['name']}"
                        formatted_result[f"SCORE_NV2_{i+1}"] = nv2_info['similarity']
                
                if 'nv3_results' in debug:
                    for i, nv3_info in enumerate(debug['nv3_results'][:TOP_NV3]):
                        formatted_result[f"TOP_NV3_{i+1}"] = f"{nv3_info['code']} - {nv3_info['name']}"
                        formatted_result[f"SCORE_NV3_{i+1}"] = nv3_info['similarity']
        
        worker_results.append((idx, formatted_result))
        progress.update(task_id, advance=1)
        
    return worker_results

def calculate_direct_similarity_with_faiss(item_embed, indices, cat_meta_nv4, item_type=None):
    """Versão que usa o índice FAISS existente para busca direta e respeita o tipo (M/S)."""
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Usar índice FAISS existente - buscar mais itens para depois filtrar
    search_k = TOP_N * 3 if item_type else TOP_N
    D, I = indices['NV4'].search(query_embed, search_k)
    
    results = []
    for i, (idx, distance) in enumerate(zip(I[0], D[0])):
        meta = cat_meta_nv4[idx]
        code = meta['CODCAT']
        cat_type = meta.get('CODNV0', '')  # Obtém o tipo da categoria (M/S)
        
        # Se um tipo de item foi especificado, filtre apenas categorias compatíveis
        if item_type and cat_type != item_type:
            continue
            
        name = meta['NOMCAT']
        
        # Converter distância para similaridade
        similarity = float(distance)
        
        results.append({
            'code': code,
            'name': name,
            'score': similarity,
            'level': 'NV4',
            'level_scores': {'NV4': similarity}
        })
        
        # Se já temos TOP_N resultados do tipo correto, podemos parar
        if len(results) >= TOP_N:
            break
    
    return results[:TOP_N]  # Garantir que retornamos no máximo TOP_N resultados

def classify_items_combined(df_items, indices, cat_meta_by_level, cat_embeddings_by_level, embedding_function):
    """Versão modificada para processar arquivos INPUT_ITENS e respeitar tipo M/S com reformulação paralela."""
    # Início igual ao original...
    num_rows = len(df_items)
    result_columns = {}
    
    # Copiar as colunas originais
    for col in df_items.columns:
        result_columns[col] = df_items[col].values
    
    # Adicionar coluna para o tipo de item e texto reformulado
    result_columns["item_type"] = [""] * num_rows
    result_columns["texto_original"] = [""] * num_rows
    result_columns["texto_reformulado"] = [""] * num_rows
    
    # Criar DataFrame
    result_df = pd.DataFrame(result_columns)
    
    # Pré-calcular relações hierárquicas
    hierarchical_maps = precompute_hierarchical_relationships(cat_meta_by_level)

    # MODIFICAÇÃO: Reformulação paralela dos textos usando o assistente
    console.print("[bold magenta]Reformulando textos de itens para melhorar classificação...[/bold magenta]")
    
    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    
    # Guardar textos originais
    for i, text in enumerate(raw_texts):
        result_df.at[i, "texto_original"] = text
    
    # Processar reformulações em paralelo
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        main_task = progress.add_task("[bold blue]Reformulando textos...", total=len(raw_texts))
        
        # Dividir índices em partições para processamento paralelo
        all_indices = list(range(len(raw_texts)))
        partitions = partition_list(all_indices, MAX_WORKERS)
        
        # Processar reformulações em paralelo
        reformulation_results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            task_ids = []
            
            for worker_id, partition in enumerate(partitions, start=1):
                task_id = progress.add_task(f"Worker {worker_id} reformulando", total=len(partition))
                task_ids.append(task_id)
                futures.append(executor.submit(
                    process_reformulation_partition, 
                    partition, 
                    raw_texts, 
                    worker_id, 
                    progress, 
                    task_id
                ))
            
            # Coletar resultados de todos os workers
            for future in futures:
                reformulation_results.extend(future.result())
    
    console.print("\n")

    # Organizar resultados de reformulação
    reformulated_texts = [""] * len(raw_texts)
    for idx, reformulated_text in reformulation_results:
        reformulated_texts[idx] = reformulated_text
        result_df.at[idx, "texto_reformulado"] = reformulated_text
    
    # Processar textos reformulados em vez dos originais
    #item_texts = [preprocess_text(text) for text in reformulated_texts]

    # Substituir a coluna objetoCompra pelo texto reformulado para todo o processamento subsequente
    df_items["objetoCompra_original"] = df_items["objetoCompra"].copy()  # Backup da descrição original 
    df_items["objetoCompra"] = reformulated_texts  # Substituir pela reformulação
    item_texts = [preprocess_text(text) for text in reformulated_texts]
    
    # Extrair e armazenar o tipo de item (M/S) das descrições originais
    item_types = [extract_item_type(text) for text in df_items["objetoCompra"]]
    for idx, item_type in enumerate(item_types):
        result_df.at[idx, "item_type"] = item_type if item_type else "Desconhecido"
    
    # O restante do processamento segue igual...
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
        # Definir ordem exata das colunas como em cf_v2_1
        ordered_columns = [
            # Colunas iniciais específicas deste sistema
            'numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 
            'descrição', 'item_type', 'texto_reformulado', 
            # TOP_1 a TOP_N (resultados combinados)
            *[f"TOP_{i}" for i in range(1, TOP_N + 1)],
            # SCORE_1 a SCORE_N (scores combinados)
            *[f"SCORE_{i}" for i in range(1, TOP_N + 1)],
            # Scores por componente
            *[f"HIER_SCORE_{i}" for i in range(1, TOP_N + 1)],
            *[f"DIRECT_SCORE_{i}" for i in range(1, TOP_N + 1)],
            # Scores por nível
            'SCORE_NV1', 'SCORE_NV2', 'SCORE_NV3', 'SCORE_NV4',
            'SCORE_CALCULATION',
            # Resultados da abordagem hierárquica pura
            *[f"TOP_HIER_{i}" for i in range(1, TOP_N + 1)],
            *[f"SCORE_HIER_{i}" for i in range(1, TOP_N + 1)],
            # Resultados da abordagem direta pura
            *[f"TOP_DIRECT_{i}" for i in range(1, TOP_N + 1)],
            *[f"SCORE_DIRECT_{i}" for i in range(1, TOP_N + 1)],
            # Detalhes dos níveis hierárquicos
            *[f"TOP_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            *[f"SCORE_NV1_{i}" for i in range(1, TOP_NV1 + 1)],
            *[f"TOP_NV2_{i}" for i in range(1, TOP_NV2 + 1)],
            *[f"SCORE_NV2_{i}" for i in range(1, TOP_NV2 + 1)],
            *[f"TOP_NV3_{i}" for i in range(1, TOP_NV3 + 1)],
            *[f"SCORE_NV3_{i}" for i in range(1, TOP_NV3 + 1)],
            # Adicionar coluna CONFIDENCE ao final
            'CONFIDENCE'
        ]
        
        # Filtrar apenas colunas que existem no DataFrame
        final_columns = [col for col in ordered_columns if col in result_df.columns]
        return result_df[final_columns]

    else:
        # Modo não-debug - incluir todas as colunas originais + resultados
        desired_columns = ['numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 'texto_reformulado','item_type']
        
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
    
    # NNN = Número de candidatos considerados em cada nível
    nnn_str = f"{TOP_NV1},{TOP_NV2},{TOP_NV3}"
    if TOP_NV1 == TOP_NV2 == TOP_NV3 == 5:
        nnn_str = "5,5,5"  # Formato compacto para configuração padrão
    
    # Flags para filtros
    ms_flag = "1" if MS_FLAG else "0"
    oc_flag = "1" if OC_FLAG else "0"
    it_flag = "1" if IT_FLAG else "0"
    
    # Construir nome de arquivo com padrão: H{WH}_D{WD}_{NNN}_{MS}_{OC}_{IT}
    config_suffix = f"{wh_str}_{wd_str}_{nnn_str.replace(',','_')}_{ms_flag}_{oc_flag}_{it_flag}"
    
    # Ajustar nomes de arquivo para INPUT_ITEM com todos os parâmetros
    INPUT_FILE = INPUT_ITENS_PATH + f"INPUT_ITEM_{input_num_str}.xlsx"
    OUTPUT_FILE = OUTPUT_ITENS_PATH + f"OUTPUT_ITEM_{input_num_str}_{config_suffix}_{TIMESTAMP}_v03.xlsx"
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
            
            new_embeddings = get_embeddings(texts, existing_progress=existing_progress)
            
           

            if SAVE_INPUT_EMBED:
                console.print("[cyan]Salvando embeddings para uso futuro...[/cyan]")
                save_embeddings(new_embeddings, INPUT_EMBED_FILE)
            else :
                console.print("[yellow]Salvar embeddings desativado.[/yellow]")
            
            return new_embeddings
        
        console.print("[bold magenta]Iniciando classificação híbrida (hierárquica + direta) com processamento paralelo...[/bold magenta]")
        
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
    """Versão que respeita o tipo (M/S) no beam search hierárquico com ordenação global de resultados."""
    
    nv1_to_nv2 = hierarchical_maps['nv1_to_nv2']
    nv2_to_nv3 = hierarchical_maps['nv2_to_nv3']
    
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Calcular similaridades NV1 usando produto escalar
    nv1_embeddings = np.array(cat_embeddings_by_level['NV1'])
    nv1_similarities_all = np.dot(nv1_embeddings, item_embed)
    
    # Ordenar e selecionar os TOP_NV1 melhores, filtrando por tipo se especificado
    nv1_indices_scores = []
    for i, sim in enumerate(nv1_similarities_all):
        nv1_meta = cat_meta_by_level['NV1'][i]
        cat_type = nv1_meta.get('CODNV0', '')
        
        # Se item_type foi informado, só incluir categorias do mesmo tipo
        if item_type is None or cat_type == item_type:
            nv1_indices_scores.append((i, sim))
    
    # Ordenar e selecionar top candidatos do tipo correto
    nv1_indices_scores.sort(key=lambda x: x[1], reverse=True)
    top_nv1 = nv1_indices_scores[:TOP_NV1]
    
    candidates = []
    
    debug_info = {
        'nv1_results': [],
        'nv2_results': [],
        'nv3_results': [],
        'item_type': item_type
    }
    
    # Listas para coletar TODOS os resultados NV2 e NV3 antes de ordenação global
    all_nv2_results = []
    all_nv3_results = []
    
    # Continuar com o processamento como antes
    for idx, (nv1_idx, nv1_similarity) in enumerate(top_nv1):
        nv1_meta = cat_meta_by_level['NV1'][nv1_idx]
        nv1_code = f"{str(nv1_meta.get('CODNV0', ''))}{str(nv1_meta.get('CODNV1', '')).zfill(4)}"

        if OUTPUT_DEBUG:
            nv1_info = {
                'code': nv1_code,
                'name': f"{nv1_meta.get('NOMNV0', '')}; {nv1_meta.get('NOMNV1', '')}",
                'similarity': float(nv1_similarity),
                'rank': idx + 1
            }
            debug_info['nv1_results'].append(nv1_info)
        
        nv2_indices = nv1_to_nv2.get(nv1_code, [])
        
        if not nv2_indices:
            continue
            
        # Calcular similaridades NV2
        nv2_embeddings = np.array([cat_embeddings_by_level['NV2'][j] for j in nv2_indices])
        nv2_similarities = np.dot(nv2_embeddings, item_embed)
        
        nv2_with_scores = [(nv2_indices[j], sim, j) for j, sim in enumerate(nv2_similarities)]
        nv2_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_nv2 = nv2_with_scores[:TOP_NV2]
        
        for rank_nv2, (nv2_idx, nv2_similarity, local_idx) in enumerate(top_nv2):
            nv2_meta = cat_meta_by_level['NV2'][nv2_idx]
            nv2_code = f"{str(nv2_meta.get('CODNV0', ''))}{str(nv2_meta.get('CODNV1', '')).zfill(4)}{str(nv2_meta.get('CODNV2', '')).zfill(5)}"            
            
            if OUTPUT_DEBUG:
                nv2_info = {
                    'code': nv2_code,
                    'name': f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}",
                    'similarity': float(nv2_similarity),
                    'parent': nv1_code,
                    'parent_similarity': float(nv1_similarity),
                    'rank_local': rank_nv2 + 1
                }
                # Coletar todos os resultados NV2 para ordenação global posterior
                all_nv2_results.append(nv2_info)
            
            nv3_indices = nv2_to_nv3.get(nv2_code, [])
            
            if not nv3_indices:
                composite_score = WEIGHT_NV1 * nv1_similarity + WEIGHT_NV2 * nv2_similarity
                
                code = f"{str(nv2_meta.get('CODNV0', ''))}{str(nv2_meta.get('CODNV1', '')).zfill(4)}{str(nv2_meta.get('CODNV2', '')).zfill(5)}"
                name = f"{nv2_meta.get('NOMNV0', '')}; {nv2_meta.get('NOMNV1', '')}; {nv2_meta.get('NOMNV2', '')}"
                
                score_calc = f"{WEIGHT_NV1} * {nv1_similarity:.4f} + {WEIGHT_NV2} * {nv2_similarity:.4f} = {composite_score:.4f}"
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV2',
                    'level_scores': {
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity)
                    },
                    'score_calculation': score_calc if OUTPUT_DEBUG else ""
                })
                continue
                
            nv3_embeddings = np.array([cat_embeddings_by_level['NV3'][k] for k in nv3_indices])
            nv3_similarities = np.dot(nv3_embeddings, item_embed)
            
            nv3_with_scores = [(nv3_indices[k], sim, k) for k, sim in enumerate(nv3_similarities)]
            nv3_with_scores.sort(key=lambda x: x[1], reverse=True)
            top_nv3 = nv3_with_scores[:TOP_NV3]
            
            for rank_nv3, (nv3_idx, nv3_similarity, local_idx) in enumerate(top_nv3):
                nv3_meta = cat_meta_by_level['NV3'][nv3_idx]
                
                composite_score = (WEIGHT_NV1 * nv1_similarity + 
                                   WEIGHT_NV2 * nv2_similarity + 
                                   WEIGHT_NV3 * nv3_similarity)
                
                if 'CODCAT' in nv3_meta:
                    code = nv3_meta['CODCAT']
                else:
                    codnv0 = str(nv3_meta.get('CODNV0', ''))
                    codnv1 = str(nv3_meta.get('CODNV1', '')).zfill(4)
                    codnv2 = str(nv3_meta.get('CODNV2', '')).zfill(5)
                    codnv3 = str(nv3_meta.get('CODNV3', '')).zfill(5)
                    code = f"{codnv0}{codnv1}{codnv2}{codnv3}"
                
                name = (f"{nv3_meta.get('NOMNV0', '')}; {nv3_meta.get('NOMNV1', '')}; "
                       f"{nv3_meta.get('NOMNV2', '')}; {nv3_meta.get('NOMNV3', '')}")
                
                score_calc = (f"{WEIGHT_NV1} * {nv1_similarity:.4f} + "
                            f"{WEIGHT_NV2} * {nv2_similarity:.4f} + "
                            f"{WEIGHT_NV3} * {nv3_similarity:.4f} = {composite_score:.4f}")
                
                if OUTPUT_DEBUG:
                    nv3_info = {
                        'code': code,
                        'name': name,
                        'similarity': float(nv3_similarity),
                        'parent': nv2_code,
                        'parent_similarity': float(nv2_similarity),
                        'grandparent_similarity': float(nv1_similarity),
                        'rank_local': rank_nv3 + 1,
                        'composite_score': composite_score,
                        'score_calculation': score_calc
                    }
                    # Coletar todos os resultados NV3 para ordenação global posterior
                    all_nv3_results.append(nv3_info)
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'score': float(composite_score),
                    'level': 'NV3',
                    'level_scores': {
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity),
                        'NV3': float(nv3_similarity)
                    },
                    'score_calculation': score_calc if OUTPUT_DEBUG else ""
                })
    
    # Ordenar todos os candidatos pelo score composto
    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = candidates[:TOP_N]
    
    # CORREÇÃO: Ordenação global dos resultados NV2 e NV3 para visualização
    if OUTPUT_DEBUG:
        # Ordenar NV2 pela similaridade
        all_nv2_results.sort(key=lambda x: x['similarity'], reverse=True)
        # Atribuir rank global
        for i, result in enumerate(all_nv2_results):
            result['rank_global'] = i + 1
        # Limitar ao TOP_NV2 global
        debug_info['nv2_results'] = all_nv2_results[:TOP_NV2]
        
        # Ordenar NV3 pela similaridade
        all_nv3_results.sort(key=lambda x: x['similarity'], reverse=True)
        # Atribuir rank global
        for i, result in enumerate(all_nv3_results):
            result['rank_global'] = i + 1
        # Limitar ao TOP_NV3 global
        debug_info['nv3_results'] = all_nv3_results[:TOP_NV3]
        
        if top_candidates:
            top_candidates[0]['debug_info'] = debug_info
    
    return top_candidates

def precompute_hierarchical_relationships(cat_meta_by_level):
    console.print("[cyan]Pré-calculando relações hierárquicas para busca acelerada...[/cyan]")
    
    nv1_to_nv2 = {}
    nv2_to_nv3 = {}
    
    for i, nv1_meta in enumerate(cat_meta_by_level['NV1']):
        nv1_code = f"{str(nv1_meta.get('CODNV0', ''))}{str(nv1_meta.get('CODNV1', ''))}"
        nv1_to_nv2[nv1_code] = []
    
    for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
        nv1_code = f"{str(nv2_meta.get('CODNV0', ''))}{str(nv2_meta.get('CODNV1', ''))}"
        if nv1_code in nv1_to_nv2:
            nv1_to_nv2[nv1_code].append(j)
    
    for j, nv2_meta in enumerate(cat_meta_by_level['NV2']):
        nv2_code = f"{str(nv2_meta.get('CODNV0', ''))}{str(nv2_meta.get('CODNV1', ''))}{str(nv2_meta.get('CODNV2', ''))}"
        nv2_to_nv3[nv2_code] = []
    
    for k, nv3_meta in enumerate(cat_meta_by_level['NV3']):
        nv2_code = f"{str(nv3_meta.get('CODNV0', ''))}{str(nv3_meta.get('CODNV1', ''))}{str(nv3_meta.get('CODNV2', ''))}"
        if nv2_code in nv2_to_nv3:
            nv2_to_nv3[nv2_code].append(k)
    
    console.print(f"[green]Relações hierárquicas pré-calculadas: {len(nv1_to_nv2)} NV1 e {len(nv2_to_nv3)} NV2[/green]")
    
    return {
        'nv1_to_nv2': nv1_to_nv2,
        'nv2_to_nv3': nv2_to_nv3
    }

def analyze_hierarchical_results(output_file):
    """
    Carrega um arquivo de resultados e exibe os candidatos dos níveis hierárquicos.
    Requer que OUTPUT_DEBUG esteja configurado como True quando o arquivo foi gerado.
    
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
            # Por esta implementação:
            console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
            texto_reformulado = row.get('texto_reformulado', row.get('objetoCompra', ''))
            texto_original = row.get('texto_original', row.get('objetoCompra_original', row.get('descrição', '')))
            console.print(f"[bold cyan]Item {i+1}/{sample_size}:[/bold cyan]")
            console.print(f"[bold cyan]Reformulado: {texto_reformulado}[/bold cyan]")
            console.print(f"[bold cyan]Original: {texto_original}[/bold cyan]")
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
            
            # Resultados do Nível 2
            console.print(f"\n[bold yellow]CANDIDATOS NÍVEL 2:[/bold yellow]")
            for j in range(1, TOP_NV2 + 1):
                if f"TOP_NV2_{j}" in row and pd.notna(row[f"TOP_NV2_{j}"]):
                    console.print(f"  NV2_{j}: {row[f'TOP_NV2_{j}']} - Score: {row.get(f'SCORE_NV2_{j}', 'N/A')}")
            
            # Resultados do Nível 3
            console.print(f"\n[bold yellow]CANDIDATOS NÍVEL 3:[/bold yellow]")
            for j in range(1, TOP_NV3 + 1):
                if f"TOP_NV3_{j}" in row and pd.notna(row[f"TOP_NV3_{j}"]):
                    console.print(f"  NV3_{j}: {row[f'TOP_NV3_{j}']} - Score: {row.get(f'SCORE_NV3_{j}', 'N/A')}")
            
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
        console.print(f"Total de itens analisados: {len(df)}")
        
        # Adicionar ao final do main
        console.print("\n[bold cyan]Para analisar os resultados hierárquicos, execute:[/bold cyan]")
        console.print(f"analyze_hierarchical_results('{output_file}')")
        
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
            texto_reformulado = row.get('texto_reformulado', row.get('objetoCompra', ''))
            texto_original = row.get('texto_original', row.get('objetoCompra_original', row.get('descrição', '')))
            console.print(f"[bold cyan]Item {i+1}/{sample_size}:[/bold cyan]")
            console.print(f"[bold cyan]Reformulado: {texto_reformulado}[/bold cyan]")
            console.print(f"[bold cyan]Original: {texto_original}[/bold cyan]")
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
            md_file.write(f"- **WEIGHT_NV2:** {WEIGHT_NV2}\n")
            md_file.write(f"- **WEIGHT_NV3:** {WEIGHT_NV3}\n")
            md_file.write(f"- **TOP_NV1:** {TOP_NV1}\n")
            md_file.write(f"- **TOP_NV2:** {TOP_NV2}\n")
            md_file.write(f"- **TOP_NV3:** {TOP_NV3}\n\n")
            
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
                item_desc_reformulado = row.get('texto_reformulado', row.get('objetoCompra', 'Sem descrição'))
                item_desc_original = row.get('texto_original', row.get('objetoCompra_original', row.get('descrição', 'Sem descrição')))
                md_file.write(f"### ITEM {i+1}\n\n")
                md_file.write(f"**Reformulado:** {item_desc_reformulado}\n\n")
                md_file.write(f"**Original:** {item_desc_original}\n\n")
                                
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
                
                # Candidatos do nível 2
                md_file.write("\n#### Candidatos Nível 2\n\n")
                nv2_present = False
                for j in range(1, TOP_NV2 + 1):
                    if f"TOP_NV2_{j}" in row and pd.notna(row[f"TOP_NV2_{j}"]):
                        nv2_present = True
                        md_file.write(f"- **NV2_{j}:** {row[f'TOP_NV2_{j}']} - Score: {row.get(f'SCORE_NV2_{j}', 'N/A')}\n")
                
                if not nv2_present:
                    md_file.write("*Informações de candidatos NV2 não disponíveis*\n")
                
                # Candidatos do nível 3
                md_file.write("\n#### Candidatos Nível 3\n\n")
                nv3_present = False
                for j in range(1, TOP_NV3 + 1):
                    if f"TOP_NV3_{j}" in row and pd.notna(row[f"TOP_NV3_{j}"]):
                        nv3_present = True
                        md_file.write(f"- **NV3_{j}:** {row[f'TOP_NV3_{j}']} - Score: {row.get(f'SCORE_NV3_{j}', 'N/A')}\n")
                
                if not nv3_present:
                    md_file.write("*Informações de candidatos NV3 não disponíveis*\n")
                
                md_file.write("\n---\n\n")  # Separador entre itens
            
            md_file.write("## Conclusões\n\n")
            md_file.write("Esta análise de debug permite visualizar como os diferentes níveis hierárquicos contribuem para a classificação final, comparando com a abordagem direta.\n\n")
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
        all_files_exist = True
        
        console.print("[bold magenta]Verificando embeddings e índices hierárquicos existentes...[/bold magenta]")
        
        for level in ['NV1', 'NV2', 'NV3', 'NV4']:
            level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
            level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
            
            if not os.path.exists(level_index_file) or not os.path.exists(level_embed_file):
                all_files_exist = False
                console.print(f"[yellow]Arquivos para nível {level} não encontrados.[/yellow]")
                break
        
        if all_files_exist:
            console.print("[cyan]Todos os arquivos de embedding e índices encontrados. Tentando carregar...[/cyan]")
            
            loading_success = True
            for level in ['NV1', 'NV2', 'NV3', 'NV4']:
                level_index_file = EMBEDDINGS_PATH + f"FAISS_INDEX_{level}.index"
                level_embed_file = EMBEDDINGS_PATH + f"CAT_EMBED_{level}_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
                
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
                    metadata_file = EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl"
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
                
                with open(EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                    pickle.dump(cat_meta_by_level, f)
                console.print("[green]Metadados do catálogo salvos.[/green]")
                
                indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        else:
            console.print("[yellow]Arquivos de embedding ou índices não encontrados. Gerando novos...[/yellow]")
            
            catalog_file = NOVA_CAT_FILE
            cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
            console.print(f"[green]Carregadas {len(cat_df)} entradas do catálogo.[/green]")
            
            cat_texts_by_level, cat_meta_by_level = prepare_catalog_entries(cat_df)
            
            with open(EMBEDDINGS_PATH + "CAT_META_BY_LEVEL.pkl", 'wb') as f:
                pickle.dump(cat_meta_by_level, f)
            console.print("[green]Metadados do catálogo salvos.[/green]")
            
            indices, cat_embeddings_by_level = create_hierarchical_indices(cat_texts_by_level)
        
            
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
        save_cache()

    except Exception as e:
        console.print(f"[bold red]Pipeline principal falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    # Carregar o cache no início do programa
    # Adicionar no início do arquivo, após as inicializações
    load_cache()
    main()


