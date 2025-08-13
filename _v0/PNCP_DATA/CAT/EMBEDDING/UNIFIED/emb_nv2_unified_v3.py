#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
emb_nv2_unified_v0.py – Código unificado para classificação de itens com embeddings

Integra as quatro versões originais:
  • OpenAI API (v4)
  • Sentence-Transformers local (v5)
  • LM Studio via API HTTP (v6)
  • Ollama (v7)

e adiciona novas opções:
  • Hugging Face (com transformers)
  • “GitHub” (exemplo com modelo alternativo do Hugging Face)
  • spaCy

Cada função de obtenção de embeddings agora aceita o parâmetro “model” para permitir a seleção
entre mais de um modelo por provider. Caso não seja informado, utiliza-se um modelo default.
"""

import os
import json
import time
import pickle
import threading
from datetime import datetime
import numpy as np
import pandas as pd
import requests
from openai import OpenAI
import ollama
import spacy

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Adicione após as importações e antes das configurações
import logging

# Configurar o logging para evitar que as mensagens HTTP interrompam as barras de progresso
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# Configurações e caminhos (mantidos conforme versões originais)

# Configurações e caminhos (mantidos conforme versões originais)
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT\\")
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS\\")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO\\")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING\\")
ITEMS_EMBED_PATH = os.path.join(EMBEDDING_PATH, "items\\")

INPUT_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx") #"TESTE_SIMPLES_ITENS.xlsx"
INPUT_SHEET = "OBJETOS"
GABARITO_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES_GABARITO_NOVA.xlsx")
GABARITO_SHEET = "GABARITO"


TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = os.path.join(REPORTS_PATH, f"TESTE_SIMPLES_ITENS_{TIMESTAMP}.xlsx")
CHECKPOINT_FILE = os.path.join(REPORTS_PATH, f"CHECKPOINT_TESTE_SIMPLES_ITENS_{TIMESTAMP}.pkl")

BATCH_SIZE = 10000
TOP_N = 10
MAX_WORKERS = os.cpu_count() * 4

# Configuração da OpenAI
client = OpenAI(api_key="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")


# Criação de diretórios, se necessário
for d in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(d):
        os.makedirs(d)


# Locks para acesso concorrente
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()

# Inicializa o console para exibição
console = Console()

def provider_progress(provider_name, total):
    """Cria uma barra de progresso padronizada para todos os providers.
    
    Args:
        provider_name: Nome do provider para exibição
        total: Número total de batches/itens para processar
        
    Returns:
        Objeto Progress configurado
    """
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]({provider_name})..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )

# Funções de checkpoint e de salvar/carregar embeddings
def save_embeddings(embeddings, filepath):
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings salvos[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
            return False


def load_embeddings(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def load_data():
    console.print("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]")
    checkpoint = load_checkpoint()
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        try:
            skiprows = list(range(1, last_processed + 1))
            df_items = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET, skiprows=skiprows)
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar Excel: {str(e)}[/bold red]")
            raise e
    else:
        try:
            df_items = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar Excel: {str(e)}[/bold red]")
            raise e
    try:
        # Carrega o catálogo unificado a partir do arquivo Excel "NOVA CAT".xlsx
        catalog_file = os.path.join(NOVA_CAT_PATH, "NOVA CAT.xlsx")
        cat_df = pd.read_excel(catalog_file, sheet_name="CAT")
        # Converte o DataFrame para uma lista de dicionários
        cat = cat_df.to_dict(orient="records")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise e
    existing_results = pd.DataFrame()
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
    return df_items, cat, existing_results, checkpoint


def prepare_catalog_entries(cat):
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    cat_texts = []
    cat_meta = []
    for entry in cat:
        # Utiliza as colunas CODCAT e NOMCAT do arquivo Excel
        codcat = entry.get('CODCAT', '')
        nomcat = entry.get('NOMCAT', '')
        # Forma o texto de embedding concatenando os dois campos com um espaço
        combined_text = f"{codcat} {nomcat}"
        cat_texts.append(combined_text)
        cat_meta.append((codcat, nomcat))
    console.print(f"[magenta]Preparados {len(cat_texts)} textos de catálogo unificado.[/magenta]")
    return cat_texts, cat_meta


# =============================================================================
# IMPLEMENTAÇÕES DOS MÉTODOS DE EMBEDDINGS COM PARÂMETRO "model"
# =============================================================================

# 1. OpenAI (v4)
def get_embeddings_openai(texts, model="text-embedding-3-large", dim=None):
    """Gera embeddings para um batch de textos usando a API OpenAI."""
    max_retries = 5
    retry_delay = 5
    model_dim = dim or (3072 if model == "text-embedding-3-large" else 1536)  # Valores padrão conforme o modelo
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model=model, input=texts)
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
                retry_delay += attempt * 2
            else:
                if attempt == max_retries - 1:
                    raise e
    
    # Caso chegue aqui (não deveria), retorne embeddings zeros com a dimensão correta
    return [np.zeros(model_dim) for _ in range(len(texts))]

# 2. Sentence-Transformers (v5)
def get_embeddings_sentence_transformers(texts, model="paraphrase-multilingual-mpnet-base-v2", dim=None):
    """Gera embeddings para um batch de textos usando Sentence Transformers."""
    from sentence_transformers import SentenceTransformer
    
    # Armazenar o modelo como atributo da função para reutilização
    if not hasattr(get_embeddings_sentence_transformers, "_models"):
        get_embeddings_sentence_transformers._models = {}
    
    if model not in get_embeddings_sentence_transformers._models:
        get_embeddings_sentence_transformers._models[model] = SentenceTransformer(model)
    
    st_model = get_embeddings_sentence_transformers._models[model]
    batch_embeddings = st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    
    # Verificar dimensão se fornecida
    if dim and batch_embeddings[0].shape[0] != dim:
        console.print(f"[yellow]Aviso: Dimensão esperada ({dim}) diferente da real ({batch_embeddings[0].shape[0]})[/yellow]")
    
    return [np.array(emb) for emb in batch_embeddings]

# 3. LM Studio via API HTTP (v6.2)
def get_embeddings_lm_studio(texts, model="jina-embeddings-v3", dim=None):
    """Gera embeddings para um batch de textos usando LM Studio API."""
    API_URL = "http://127.0.0.1:1234/v1/embeddings"
    expected_dim = dim or 768  # Dimensão padrão para vários modelos
    embeddings = []
    
    try:
        # Testar conexão se for o primeiro batch
        if not hasattr(get_embeddings_lm_studio, "_connection_tested"):
            test_resp = requests.post(API_URL, headers={"Content-Type": "application/json"},
                                      json={"model": model, "input": "Teste de conexão"})
            test_resp.raise_for_status()
            # Armazenar o resultado do teste para verificar a dimensão real
            result = test_resp.json()
            actual_dim = len(result["data"][0]["embedding"])
            if dim and actual_dim != expected_dim:
                console.print(f"[yellow]Aviso: Dimensão esperada ({expected_dim}) é diferente da real ({actual_dim})[/yellow]")
            get_embeddings_lm_studio._connection_tested = True
            get_embeddings_lm_studio._actual_dim = actual_dim
        
        # Processar cada texto no batch
        for text in texts:
            if not text or text.isspace():
                embeddings.append(np.zeros(get_embeddings_lm_studio._actual_dim 
                                           if hasattr(get_embeddings_lm_studio, "_actual_dim") 
                                           else expected_dim))
                continue
                
            data = {"model": model, "input": text}
            resp = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=data)
            resp.raise_for_status()
            result = resp.json()
            embeddings.append(np.array(result["data"][0]["embedding"]))
        
        return embeddings
    except Exception as e:
        console.print(f"[bold red]Erro na API LM Studio: {str(e)}[/bold red]")
        # Em caso de erro, retornar vetores zerados com a dimensão correta
        return [np.zeros(get_embeddings_lm_studio._actual_dim 
                          if hasattr(get_embeddings_lm_studio, "_actual_dim") 
                          else expected_dim) 
                for _ in range(len(texts))]

# 4. Ollama (v7)
ollama_lock = threading.RLock() # Lock global para acesso ao ollama
def get_embeddings_ollama(texts, model="mxbai-embed-large", dim=None):
    """
    Gera embeddings para um batch de textos usando a biblioteca Ollama.
    Usa um lock para garantir acesso thread-safe ao servidor Ollama.
    """
    expected_dim = dim or 1024  # Dimensão padrão para o modelo mxbai-embed-large
    embeddings = []
    
    # Função interna para extrair embedding da resposta Ollama
    def extract_embedding(response):
        if hasattr(response, "embedding"):
            return np.array(response.embedding)
        elif hasattr(response, "embeddings"):
            return np.array(response.embeddings[0])
        elif isinstance(response, dict):
            if "embedding" in response:
                return np.array(response["embedding"])
            elif "embeddings" in response:
                return np.array(response["embeddings"][0])
        else:
            return np.array(response)
    
    # Testar e armazenar a dimensão real se este for o primeiro uso
    with ollama_lock:
        if not hasattr(get_embeddings_ollama, "_model_dims"):
            get_embeddings_ollama._model_dims = {}
        
        # Se ainda não conhecemos a dimensão deste modelo específico
        if model not in get_embeddings_ollama._model_dims:
            try:
                test_response = ollama.embed(model=model, input="Teste de conexão")
                test_emb = extract_embedding(test_response)
                actual_dim = test_emb.shape[0]
                get_embeddings_ollama._model_dims[model] = actual_dim
                
                if dim and actual_dim != expected_dim:
                    console.print(f"[yellow]Aviso: Dimensão esperada para {model} ({expected_dim}) é diferente da real ({actual_dim})[/yellow]")
                
            except Exception as e:
                console.print(f"[bold red]Erro ao testar modelo Ollama {model}: {str(e)}[/bold red]")
                # Usar a dimensão esperada como fallback
                get_embeddings_ollama._model_dims[model] = expected_dim
    
    # Obter dimensão para este modelo
    actual_dim = get_embeddings_ollama._model_dims.get(model, expected_dim)
    
    # Processar cada texto no batch
    for text in texts:
        if not text or text.isspace():
            embeddings.append(np.zeros(actual_dim))
            continue
        
        # Usar lock para garantir que apenas uma thread acesse o cliente Ollama por vez
        with ollama_lock:
            try:
                response = ollama.embed(model=model, input=text)
                emb = extract_embedding(response)
                embeddings.append(emb)
            except Exception as e:
                console.print(f"[bold red]Erro ao embeddar texto com Ollama: {str(e)}[/bold red]")
                embeddings.append(np.zeros(actual_dim))
    
    return embeddings

# 5. Hugging Face (com transformers)
def get_embeddings_hugging_face(texts, model="sentence-transformers/paraphrase-mpnet-base-v2", dim=None):
    """Gera embeddings para um batch de textos usando modelos do Hugging Face."""
    from transformers import AutoTokenizer, AutoModel
    import torch
    
    expected_dim = dim or 768  # Dimensão padrão para vários modelos do HuggingFace
    
    # Armazenar o modelo e tokenizer como atributos da função para reutilização
    if not hasattr(get_embeddings_hugging_face, "_models"):
        get_embeddings_hugging_face._models = {}
    
    model_key = model  # Usar o nome do modelo como chave
    
    if model_key not in get_embeddings_hugging_face._models:
        tokenizer = AutoTokenizer.from_pretrained(model)
        hf_model = AutoModel.from_pretrained(model)
        get_embeddings_hugging_face._models[model_key] = (tokenizer, hf_model)
    else:
        tokenizer, hf_model = get_embeddings_hugging_face._models[model_key]
    
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    # Processar o batch
    try:
        encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = hf_model(**encoded_input)
        batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
        
        # Verificar dimensão se fornecida
        if dim and batch_embeddings.shape[1] != dim:
            console.print(f"[yellow]Aviso: Dimensão esperada ({dim}) diferente da real ({batch_embeddings.shape[1]})[/yellow]")
        
        return [np.array(emb) for emb in batch_embeddings]
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embeddings com Hugging Face: {str(e)}[/bold red]")
        return [np.zeros(expected_dim) for _ in range(len(texts))]

# 6. GitHub – exemplo com outro modelo do Hugging Face
def get_embeddings_github(texts, model="sentence-transformers/all-MiniLM-L6-v2", dim=None):
    """Gera embeddings para um batch de textos usando modelos do GitHub/Hugging Face."""
    from transformers import AutoTokenizer, AutoModel
    import torch
    
    expected_dim = dim or 384  # Dimensão padrão para o modelo all-MiniLM-L6-v2
    
    # Armazenar o modelo e tokenizer como atributos da função para reutilização
    if not hasattr(get_embeddings_github, "_models"):
        get_embeddings_github._models = {}
    
    model_key = model  # Usar o nome do modelo como chave
    
    if model_key not in get_embeddings_github._models:
        tokenizer = AutoTokenizer.from_pretrained(model)
        gh_model = AutoModel.from_pretrained(model)
        get_embeddings_github._models[model_key] = (tokenizer, gh_model)
    else:
        tokenizer, gh_model = get_embeddings_github._models[model_key]
    
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    # Processar o batch
    try:
        encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = gh_model(**encoded_input)
        batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
        
        # Verificar dimensão se fornecida
        if dim and batch_embeddings.shape[1] != dim:
            console.print(f"[yellow]Aviso: Dimensão esperada ({dim}) diferente da real ({batch_embeddings.shape[1]})[/yellow]")
        
        return [np.array(emb) for emb in batch_embeddings]
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embeddings com GitHub model: {str(e)}[/bold red]")
        return [np.zeros(expected_dim) for _ in range(len(texts))]
    
# 7. spaCy (modelo de português)
def get_embeddings_spacy(texts, model="pt_core_news_md", dim=None):
    """Gera embeddings para um batch de textos usando spaCy."""
    expected_dim = dim or 300  # Dimensão padrão para modelos spaCy
    
    # Carregar o modelo apenas uma vez e armazenar
    if not hasattr(get_embeddings_spacy, "_models"):
        get_embeddings_spacy._models = {}
    
    if model not in get_embeddings_spacy._models:
        try:
            nlp = spacy.load(model)
            get_embeddings_spacy._models[model] = nlp
            
            # Testar dimensão
            test_doc = nlp("Teste")
            actual_dim = test_doc.vector.shape[0]
            if dim and actual_dim != expected_dim:
                console.print(f"[yellow]Aviso: Dimensão esperada para spaCy {model} ({expected_dim}) é diferente da real ({actual_dim})[/yellow]")
            
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar modelo spaCy {model}: {str(e)}[/bold red]")
            return [np.zeros(expected_dim) for _ in range(len(texts))]
    else:
        nlp = get_embeddings_spacy._models[model]
    
    # Processar cada texto no batch
    embeddings = []
    for text in texts:
        try:
            if not text or text.isspace():
                embeddings.append(np.zeros(nlp.vocab.vectors.shape[1]))
                continue
            
            doc = nlp(text)
            embeddings.append(doc.vector)
        except Exception as e:
            console.print(f"[bold red]Erro ao processar texto com spaCy: {str(e)}[/bold red]")
            embeddings.append(np.zeros(nlp.vocab.vectors.shape[1]))
    
    return embeddings

# =============================================================================
# FUNÇÃO UNIFICADA PARA OBTER EMBEDDINGS
# =============================================================================
# Função unificada que seleciona o método de embeddings e repassa o parâmetro "model"
def get_embeddings(texts, method="openai", batch_size=32, show_progress=True, model=None, dim=None):
    """
    Função unificada para obtenção de embeddings usando o método especificado.
    
    Args:
        texts: Lista de textos para gerar embeddings
        method: Método de embeddings a utilizar (openai, sentence_transformers, etc.)
        batch_size: Tamanho do lote para processamento
        show_progress: Se deve mostrar barra de progresso
        model: Modelo específico a utilizar (se None, usa o modelo default)
        dim: Dimensionalidade do modelo (usar apenas no comparative_unified_v3.py)
        
    Returns:
        Lista de arrays numpy representando os embeddings dos textos
    """
    import concurrent.futures
    
    # Selecionar a função específica de embedding com base no método
    if method == "openai": embed_function = lambda batch: get_embeddings_openai(batch, model=model)
    elif method == "sentence_transformers": embed_function = lambda batch: get_embeddings_sentence_transformers(batch, model=model)
    elif method == "lm_studio": embed_function = lambda batch: get_embeddings_lm_studio(batch, model=model)
    elif method == "ollama": embed_function = lambda batch: get_embeddings_ollama(batch, model=model)
    elif method == "hugging_face": embed_function = lambda batch: get_embeddings_hugging_face(batch, model=model)
    elif method == "github": embed_function = lambda batch: get_embeddings_github(batch, model=model)
    elif method == "spacy": embed_function = lambda batch: get_embeddings_spacy(batch, model=model)
    else: raise ValueError(f"Método de embeddings não suportado: {method}")
    
    # Dividir os textos em batches
    batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]
    total_batches = len(batches)
    all_embeddings = []
    
    # Processar os batches com ThreadPoolExecutor para paralelismo
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submeter todos os batches para processamento
        future_to_batch = {executor.submit(embed_function, batch): i for i, batch in enumerate(batches)}
        
        # Configurar barra de progresso se necessário
        if show_progress:
            with provider_progress(f"{method}", total_batches) as progress:
                task = progress.add_task("", total=total_batches)
                
                # Coletar resultados conforme concluídos
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        batch_embeddings = future.result()
                        all_embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro no batch {batch_idx}: {str(e)}[/bold red]")
                        # Determinar dimensão para vetores zeros baseado no primeiro embedding bem-sucedido
                        fallback_dim = 768  # Dimensão padrão em caso de falha completa
                        if all_embeddings:
                            fallback_dim = all_embeddings[0].shape[0]
                        batch_size_actual = len(batches[batch_idx])
                        all_embeddings.extend([np.zeros(fallback_dim) for _ in range(batch_size_actual)])
                        progress.update(task, advance=1)
        else:
            # Versão sem barra de progresso
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_embeddings = future.result()
                    all_embeddings.extend(batch_embeddings)
                except Exception as e:
                    console.print(f"[bold red]Erro no batch {batch_idx}: {str(e)}[/bold red]")
                    fallback_dim = 768
                    if all_embeddings:
                        fallback_dim = all_embeddings[0].shape[0]
                    batch_size_actual = len(batches[batch_idx])
                    all_embeddings.extend([np.zeros(fallback_dim) for _ in range(batch_size_actual)])
    
    # Garantir que estamos retornando embeddings na mesma ordem dos textos de entrada
    if len(all_embeddings) < len(texts):
        console.print(f"[bold yellow]Aviso: Número de embeddings gerados ({len(all_embeddings)}) é menor que o número de textos ({len(texts)})[/bold yellow]")
    
    return all_embeddings[:len(texts)]

# =============================================================================
# FUNÇÃO DE CLASSIFICAÇÃO (mantida a lógica original)
# =============================================================================
def classify_items_batched(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens (usando a coluna "objetoCompra")
    e, para cada item, compara com os embeddings do catálogo unificado (cat_embeds) para selecionar o
    NOMCAT com maior similaridade. Retorna o DataFrame df_items com uma nova coluna "answer".
    """
    #console.print("[bold magenta]Classificando itens com base no catálogo unificado...[/bold magenta]")
    answers = []
    
    # Obtém os textos dos itens; assume que a coluna utilizada é "objetoCompra"
    item_texts = df_items["objetoCompra"].fillna("").tolist()
    
    # Calcula os embeddings dos textos dos itens com barra de progresso incorporada
    #console.print("[bold cyan]Gerando embeddings de itens...[/bold cyan]")
    item_embeds = embedding_function(item_texts)
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Para cada item, calcula a similaridade com todos os embeddings do catálogo
    #console.print("[bold cyan]Calculando similaridades e classificando...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[bold blue]ITENS..."), 
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),transient=False) as progress:
        task = progress.add_task("", total=len(item_embeds))
        
        for item_embed in item_embeds:
            sims = [cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds]
            best_idx = np.argmax(sims) if sims else -1
            if best_idx >= 0:
                # cat_meta contém tuplas (CODCAT, NOMCAT)
                best_cat = cat_meta[best_idx]
                answer = best_cat[1]  # Retorna o NOMCAT como resposta
            else:
                answer = ""
            answers.append(answer)
            progress.update(task, advance=1)
    
    df_items = df_items.copy()
    df_items["answer"] = answers
    return df_items
