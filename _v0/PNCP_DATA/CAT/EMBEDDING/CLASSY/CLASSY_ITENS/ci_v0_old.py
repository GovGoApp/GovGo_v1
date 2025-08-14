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

# Definir caminhos e arquivos - atualizar estas definições
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
NOVA_CAT_PATH = BASE_PATH + "CAT\\NOVA\\"
CLASSY_PATH = BASE_PATH + "CLASSY\\"
ITENS_PATH = CLASSY_PATH + "CLASSY_ITENS\\"

# Novos caminhos para INPUT_ITENS
INPUT_ITENS_PATH = ITENS_PATH + "INPUT_ITENS\\"
OUTPUT_ITENS_PATH = ITENS_PATH + "OUTPUT_ITENS\\"

# Manter os caminhos existentes para embeddings
EMBEDDINGS_PATH = CLASSY_PATH + "EMBEDDING\\"

# Novo caminho para embeddings dos itens
INPUT_ITENS_EMBEDDINGS_PATH = ITENS_PATH + "INPUT_ITENS_EMBEDDINGS\\"
SAVE_INPUT_EMBED = True

# Criar diretórios se não existirem
os.makedirs(OUTPUT_ITENS_PATH, exist_ok=True)
os.makedirs(INPUT_ITENS_EMBEDDINGS_PATH, exist_ok=True)

SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

MAX_WORKERS = 8  # Número de threads para processamento paralelo
BATCH_SIZE = 200  # Tamanho do lote para processamento de embeddings

PAGE_BEGIN = 15  # Página inicial para leitura do Excel
PAGE_END = 15 # Página final para leitura do Excel 

EMBEDDING_MODEL = "text-embedding-3-large"

OUTPUT_DEBUG = False  # Controla o modo de depuração da saída

TOP_N = 10  # Número de categorias mais relevantes a serem retornadas
TOP_NV1 = 5  # Número de candidatos NV1 a manter
TOP_NV2 = 5  # Número de candidatos NV2 a manter por NV1
TOP_NV3 = 10   # Número de candidatos NV3 a manter por NV2


# Pesos para combinação das abordagens
WEIGHT_HIERARCHICAL = 0.5  # Peso para abordagem hierárquica
WEIGHT_DIRECT = 0.5       # Peso para abordagem direta

WEIGHT_NV1 = 0.2
WEIGHT_NV2 = 0.3
WEIGHT_NV3 = 0.5

# Caminhos para armazenamento de embeddings hierárquicos

CAT_EMBED_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"
CAT_EMBED_NV4_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV4_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV3_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV3_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
CAT_EMBED_NV2_FILE = EMBEDDINGS_PATH + f"{NOVA_CAT_SHEET}_NV2_{EMBEDDING_MODEL.replace('-', '_')}.pkl"
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
            dim = embeddings_array.shape[1]
            
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
    """Versão otimizada que usa o índice FAISS para busca direta e respeita o tipo (M/S)."""
    # Normalizar embedding de consulta
    query_embed = np.array([item_embed], dtype=np.float32)
    faiss.normalize_L2(query_embed)
    
    # Configurar nprobe para índices aproximados para balancear velocidade/precisão
    # Isso é fundamental para obter bons resultados com IndexIVFFlat
    if hasattr(indices['NV4'], 'nprobe'):
        total_vectors = indices['NV4'].ntotal
        # Ajuste dinâmico de nprobe baseado no tamanho do índice
        if total_vectors > 10000:
            indices['NV4'].nprobe = min(32, max(8, int(total_vectors / 1000)))
        else:
            indices['NV4'].nprobe = min(16, max(4, int(total_vectors / 500)))
        
        console.print(f"[cyan]Usando nprobe={indices['NV4'].nprobe} para busca em {total_vectors} vetores[/cyan]")
    
    # Usar índice FAISS existente - buscar mais itens para depois filtrar
    search_k = TOP_N * 3 if item_type else TOP_N
    D, I = indices['NV4'].search(query_embed, search_k)
    
    results = []
    for i, (idx, distance) in enumerate(zip(I[0], D[0])):
        # Verificar se o índice é válido
        if idx < 0 or idx >= len(cat_meta_nv4):
            continue
            
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

def process_multiple_files_parallel(input_files):
    """Processa múltiplos arquivos INPUT_ITEM em paralelo para maior eficiência."""
    console.print(f"[bold magenta]Iniciando processamento paralelo de {len(input_files)} arquivos[/bold magenta]")
    
    # Limitar número de workers para arquivos para evitar sobrecarga de memória
    file_workers = min(3, MAX_WORKERS // 4)
    
    results = []
    with ThreadPoolExecutor(max_workers=file_workers) as executor:
        futures = []
        for input_number in input_files:
            futures.append(executor.submit(process_input_file, input_number))
            
        for i, future in enumerate(futures):
            try:
                result = future.result()
                results.append((input_files[i], result))
                if result:
                    console.print(f"[green]✓ Arquivo INPUT_ITEM_{input_files[i]:03d}.xlsx processado com sucesso[/green]")
                else:
                    console.print(f"[red]✗ Falha no processamento do arquivo INPUT_ITEM_{input_files[i]:03d}.xlsx[/red]")
            except Exception as e:
                console.print(f"[bold red]Erro no processamento do arquivo {input_files[i]}: {str(e)}[/bold red]")
                results.append((input_files[i], False))
    
    success_count = sum(1 for _, result in results if result)
    failure_count = len(results) - success_count
    
    console.print(f"[bold green]Processamento em lote concluído: {success_count} sucesso(s), {failure_count} falha(s)[/bold green]")
    return results
    

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
        # Definir ordem exata das colunas como em cf_v2_1
        ordered_columns = [
            # Colunas iniciais específicas deste sistema
            'numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 'item_type',
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
    # Ajustar nomes de arquivo para INPUT_ITEM
    INPUT_FILE = INPUT_ITENS_PATH + f"INPUT_ITEM_{input_num_str}.xlsx"
    OUTPUT_FILE = OUTPUT_ITENS_PATH + f"OUTPUT_ITEM_{input_num_str}.xlsx"
    INPUT_EMBED_FILE = INPUT_ITENS_EMBEDDINGS_PATH + f"INPUT_ITEM_EMBED_{input_num_str}.pkl"
    
    console.print(f"\n[bold green]{'='*80}[/bold green]")
    console.print(f"[bold green]PROCESSANDO ARQUIVO: {os.path.basename(INPUT_FILE)}[/bold green]")
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
    """Versão que respeita o tipo (M/S) no beam search hierárquico."""
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
    
    # O restante da função continua como antes, já que estamos filtrando no nível NV1
    candidates = []
    
    debug_info = {
        'nv1_results': [],
        'nv2_results': [],
        'nv3_results': [],
        'item_type': item_type  # Adicionar tipo do item para debug
    }
    
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
            
        # O restante do código permanece igual, já que NV2 e NV3 já usam o método do produto escalar
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
                    'rank': rank_nv2 + 1
                }
                debug_info['nv2_results'].append(nv2_info)
            
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
                    # Montar o código com o formato correto {M/S}{0000}{00000}{00000}
                    codnv0 = str(nv3_meta.get('CODNV0', ''))
                    codnv1 = str(nv3_meta.get('CODNV1', '')).zfill(4)  # 4 dígitos
                    codnv2 = str(nv3_meta.get('CODNV2', '')).zfill(5)  # 5 dígitos
                    codnv3 = str(nv3_meta.get('CODNV3', '')).zfill(5)  # 5 dígitos
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
                        'rank': rank_nv3 + 1,
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
                        'NV1': float(nv1_similarity),
                        'NV2': float(nv2_similarity),
                        'NV3': float(nv3_similarity)
                    },
                    'score_calculation': score_calc if OUTPUT_DEBUG else ""
                })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = candidates[:TOP_N]
    
    if OUTPUT_DEBUG and top_candidates:
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
        
    except Exception as e:
        console.print(f"[bold red]Pipeline principal falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
