#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EmbedForge Pro - Sistema Unificado de Embeddings e Comparativo

Um sistema completo para geração, análise e comparação de embeddings usando múltiplos providers:
  • OpenAI API
  • Sentence-Transformers 
  • LM Studio via API HTTP
  • Ollama
  • Hugging Face Transformers
  • Modelos GitHub
  • spaCy

Características:
- Processamento em lotes com paralelismo otimizado (ThreadPoolExecutor)
- Suporte para múltiplos modelos por provider com dimensões específicas
- Cache de embeddings para reutilização
- Sistema de checkpoint para recuperação de processamento
- Análise comparativa com métricas de performance
- Geração automática de relatórios em Excel
"""

import os
import json
import time
import pickle
import threading
import concurrent.futures
from datetime import datetime
import numpy as np
import pandas as pd
import requests
from openai import OpenAI
import ollama
import spacy
import logging

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Configurar o logging para evitar que as mensagens HTTP interrompam as barras de progresso
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ===============================================================================
# CONFIGURAÇÕES E CAMINHOS
# ===============================================================================
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT\\")
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS\\")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO\\")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING\\")
ITEMS_EMBED_PATH = os.path.join(EMBEDDING_PATH, "items\\")

INPUT_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
INPUT_SHEET = "OBJETOS"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV3"

GABARITO_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES_GABARITO_NOVA.xlsx")
GABARITO_SHEET = "GABARITO"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = os.path.join(REPORTS_PATH, f"TESTE_SIMPLES_ITENS_{NOVA_CAT_SHEET}_{TIMESTAMP}.xlsx")
CHECKPOINT_FILE = os.path.join(REPORTS_PATH, f"CHECKPOINT_TESTE_SIMPLES_ITENS_{TIMESTAMP}.pkl")


BATCH_SIZE = 10000
TOP_N = 10
MAX_WORKERS = os.cpu_count() * 4

# Define os modelos para cada provider
providers_models = {
    "openai": [
        {"name": "text-embedding-ada-002", "dim": 1536},
        {"name": "text-embedding-3-small", "dim": 1536},
        {"name": "text-embedding-3-large", "dim": 3072}
    ],
    "sentence_transformers": [
        {"name": "paraphrase-multilingual-MiniLM-L12-v2", "dim": 384},
        {"name": "paraphrase-multilingual-mpnet-base-v2", "dim": 768}
    ],
    "lm_studio": [
        {"name": "text-embedding-nomic-embed-text-v1.5", "dim": 768},
        {"name": "text-embedding-granite-embedding-278m-multilingual", "dim": 768},
        {"name": "text-embedding-granite-embedding-107m-multilingual", "dim": 512}
    ],
    #"ollama": [
        #{"name": "llama3.2", "dim": 4096},
        #{"name": "bge-m3", "dim": 1024},
        #{"name": "mxbai-embed-large", "dim": 1024}
    #],
    # Descomente para testar outros métodos
    #"hugging_face": [{"name": "intfloat/multilingual-e5-large", "dim": 1024}],
    #"github": [{"name": "microsoft/mdeberta-v3-base", "dim": 768}],
    #"spacy": [{"name": "pt_core_news_md", "dim": 300}]
}

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Criação de diretórios, se necessário
for d in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(d):
        os.makedirs(d)

# Locks para acesso concorrente
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
ollama_lock = threading.RLock()  # Lock global para acesso ao ollama

# Inicializa o console para exibição
console = Console()

# ===============================================================================
# FUNÇÕES DE UTILIDADE GERAIS
# ===============================================================================
def provider_progress(provider_name, total):
    """Cria uma barra de progresso padronizada para todos os providers."""
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]({provider_name})..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )

def comparing_progress(text, total):
    """Cria uma barra de progresso padrão para comparações."""
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]{text}..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
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
    """Carrega embeddings de arquivo pickle se existir."""
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
    """Carregar dados do Excel e o catálogo unificado."""
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
        catalog_file = os.path.join(NOVA_CAT_PATH, NOVA_CAT_FILE)
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
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
    """Preparar entradas de catálogo para embedding."""
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

# ===============================================================================
# IMPLEMENTAÇÕES DOS MÉTODOS DE EMBEDDINGS
# ===============================================================================

def get_embeddings_openai(texts, model):
    """Gera embeddings para um batch de textos usando a API OpenAI."""
    max_retries = 5
    retry_delay = 5
    model_dim = 3072 if model == "text-embedding-3-large" else 1536  # Valores padrão
    
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
    
    return [np.zeros(model_dim) for _ in range(len(texts))]

def get_embeddings_sentence_transformers(texts, model):
    """Gera embeddings para um batch de textos usando Sentence Transformers."""
    from sentence_transformers import SentenceTransformer
    
    # Armazenar o modelo como atributo da função para reutilização
    if not hasattr(get_embeddings_sentence_transformers, "_models"):
        get_embeddings_sentence_transformers._models = {}
    
    if model not in get_embeddings_sentence_transformers._models:
        get_embeddings_sentence_transformers._models[model] = SentenceTransformer(model)
    
    st_model = get_embeddings_sentence_transformers._models[model]
    batch_embeddings = st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    
    return [np.array(emb) for emb in batch_embeddings]

def get_embeddings_lm_studio(texts, model="jina-embeddings-v3"):
    """Gera embeddings para um batch de textos usando LM Studio API."""
    API_URL = "http://127.0.0.1:1234/v1/embeddings"
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
            get_embeddings_lm_studio._connection_tested = True
            get_embeddings_lm_studio._actual_dim = actual_dim
        
        # Processar cada texto no batch
        for text in texts:
            if not text or text.isspace():
                embeddings.append(np.zeros(get_embeddings_lm_studio._actual_dim 
                                           if hasattr(get_embeddings_lm_studio, "_actual_dim") 
                                           else 768))
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
                          else 768) 
                for _ in range(len(texts))]

def get_embeddings_ollama(texts, model="mxbai-embed-large"):
    """
    Gera embeddings para um batch de textos usando a biblioteca Ollama.
    Usa um lock para garantir acesso thread-safe ao servidor Ollama.
    """
    expected_dim = 1024  # Dimensão padrão para o modelo mxbai-embed-large
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

def get_embeddings_hugging_face(texts, model="sentence-transformers/paraphrase-mpnet-base-v2"):
    """Gera embeddings para um batch de textos usando modelos do Hugging Face."""
    from transformers import AutoTokenizer, AutoModel
    import torch
    
    expected_dim = 768  # Dimensão padrão para vários modelos do HuggingFace
    
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
        
        return [np.array(emb) for emb in batch_embeddings]
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embeddings com Hugging Face: {str(e)}[/bold red]")
        return [np.zeros(expected_dim) for _ in range(len(texts))]

def get_embeddings_github(texts, model="sentence-transformers/all-MiniLM-L6-v2"):
    """Gera embeddings para um batch de textos usando modelos do GitHub/Hugging Face."""
    from transformers import AutoTokenizer, AutoModel
    import torch
    
    expected_dim = 384  # Dimensão padrão para o modelo all-MiniLM-L6-v2
    
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
        
        return [np.array(emb) for emb in batch_embeddings]
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embeddings com GitHub model: {str(e)}[/bold red]")
        return [np.zeros(expected_dim) for _ in range(len(texts))]
    
def get_embeddings_spacy(texts, model="pt_core_news_md"):
    """Gera embeddings para um batch de textos usando spaCy."""
    expected_dim = 300  # Dimensão padrão para modelos spaCy
    
    # Carregar o modelo apenas uma vez e armazenar
    if not hasattr(get_embeddings_spacy, "_models"):
        get_embeddings_spacy._models = {}
    
    if model not in get_embeddings_spacy._models:
        try:
            nlp = spacy.load(model)
            get_embeddings_spacy._models[model] = nlp
            
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

# ===============================================================================
# FUNÇÃO UNIFICADA PARA OBTER EMBEDDINGS COM PARALELISMO
# ===============================================================================
def get_embeddings(texts, method="openai", batch_size=32, show_progress=True, model=None, dim=None):
    """
    Função unificada para obtenção de embeddings usando o método especificado,
    com processamento paralelo através de ThreadPoolExecutor.
    """
    # Selecionar a função específica de embedding com base no método
    if method == "openai": 
        embed_function = lambda batch: get_embeddings_openai(batch, model=model if model else "text-embedding-3-large")
    elif method == "sentence_transformers": 
        embed_function = lambda batch: get_embeddings_sentence_transformers(batch, model=model if model else "paraphrase-multilingual-mpnet-base-v2")
    elif method == "lm_studio": 
        embed_function = lambda batch: get_embeddings_lm_studio(batch, model=model if model else "jina-embeddings-v3")
    elif method == "ollama": 
        embed_function = lambda batch: get_embeddings_ollama(batch, model=model if model else "mxbai-embed-large")
    elif method == "hugging_face": 
        embed_function = lambda batch: get_embeddings_hugging_face(batch, model=model if model else "sentence-transformers/paraphrase-mpnet-base-v2")
    elif method == "github": 
        embed_function = lambda batch: get_embeddings_github(batch, model=model if model else "sentence-transformers/all-MiniLM-L6-v2")
    elif method == "spacy": 
        embed_function = lambda batch: get_embeddings_spacy(batch, model=model if model else "pt_core_news_md")
    else: 
        raise ValueError(f"Método de embeddings não suportado: {method}")
    
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

# ===============================================================================
# FUNÇÃO DE CLASSIFICAÇÃO 
# ===============================================================================
def classify_items_batched(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens
    e compara com os embeddings do catálogo unificado para classificação.
    """
    answers = []
    
    # Obtém os textos dos itens
    item_texts = df_items["objetoCompra"].fillna("").tolist()
    
    # Calcula os embeddings dos textos dos itens
    item_embeds = embedding_function(item_texts)
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Para cada item, calcula a similaridade com todos os embeddings do catálogo
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

# ===============================================================================
# FUNÇÕES DE PONTUAÇÃO E AVALIAÇÃO
# ===============================================================================
def simplified_score_answer(method_answer: str, expected_type: str, ref_top_list: list) -> int:
    """Calcula uma pontuação simplificada para a resposta."""
    score = 0
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if not parts:
        return 0
        
    method_type = parts[0].upper()
    expected = expected_type.upper()
    
    if method_type == expected:
        score += 1
        
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        if len(parts) == len(ref_parts):
            score += 1
            
    ranking_position = None
    for i, ref_ans in enumerate(ref_top_list):
        if method_answer.strip().upper() == ref_ans.strip().upper():
            ranking_position = i + 1
            break
            
    if ranking_position is not None:
        score += 1
        if ranking_position <= 5:
            score += 1
        if ranking_position == 1:
            score += 1
            
    return min(score, 5)

def process_row_intermediate(row: pd.Series, method_cols: list, top_cols: list) -> list:
    """Processa uma linha do DataFrame para gerar resultados intermediários."""
    intermediate_results = []
    expected_type = row.get("tipoDetectado", "")
    record_id = row.get("id_pncp", row.get("id", ""))
    ref_top_list = [str(row.get(col, "")) for col in top_cols if col in row.index and pd.notnull(row.get(col))]
    
    for method in method_cols:
        if method not in row.index:
            continue
            
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
        ranking_position = None
        
        for i, ref_ans in enumerate(ref_top_list):
            if method_answer.strip().upper() == ref_ans.strip().upper():
                ranking_position = i + 1
                break
                
        final_score = simplified_score_answer(method_answer, expected_type, ref_top_list)
        
        entry = {
            "id_pncp": record_id,
            "method": method,
            "method_answer": method_answer,
            "expected_type": expected_type,
            "ranking_position": ranking_position,
            "final_score": final_score
        }
        
        intermediate_results.append(entry)
        
    return intermediate_results

def process_all_rows(df: pd.DataFrame, method_cols: list, top_cols: list) -> tuple:
    """Processa todas as linhas do DataFrame e gera resultados finais e intermediários."""
    final_scores_list = []
    intermediate_list = []
    
    with comparing_progress("Pontuação de linhas", len(df)) as progress:
        task = progress.add_task("", total=len(df))
        
        for idx, row in df.iterrows():
            record_id = row["id_pncp"]
            row_final = {"id_pncp": record_id}
            row_intermediate = process_row_intermediate(row, method_cols, top_cols)
            
            for entry in row_intermediate:
                m = entry["method"]
                row_final[f"Score_{m}"] = entry["final_score"]
                
            final_scores_list.append(row_final)
            intermediate_list.extend(row_intermediate)
            progress.update(task, advance=1)
            
    df_final = pd.DataFrame(final_scores_list)
    df_intermediate = pd.DataFrame(intermediate_list)
    
    return df_final, df_intermediate

# ===============================================================================
# FUNÇÃO PRINCIPAL DO MODO COMPARATIVO  
# ===============================================================================
def run_comparative_mode():
    console.print("[bold cyan]===== MODO COMPARATIVO DE EMBEDDINGS =====")
    

    results_dict = {}

    # Carrega os dados de itens e o catálogo unificado
    df_items, cat, _, _ = load_data()
    cat_texts, cat_meta = prepare_catalog_entries(cat)

    # Número total de combinações para a barra de progresso
    total_combos = sum(len(models) for models in providers_models.values())

    for provider, models in providers_models.items():
        for model_info in models:
            model_name = model_info["name"]
            model_dim = model_info["dim"]
            combo_name = f"{provider}_{model_name}"
            
            # Define o caminho para cache dos embeddings do catálogo unificado
            model_safe_name = model_name.replace("/", "_").replace("-", "_").replace(".", "_").lower()
            provider_safe_name = provider.lower()
            cat_embed_file = os.path.join(EMBEDDING_PATH, f"cat_{provider_safe_name}_{model_safe_name}.pkl")
            
            console.print(f"\n[bold green]Processando: {provider_safe_name}_{model_safe_name} (dim={model_dim})[/bold green]")
            
            try:
                # Tenta carregar os embeddings do catálogo do cache
                cat_embeds = load_embeddings(cat_embed_file)
                if cat_embeds is None or len(cat_embeds) != len(cat_texts):
                    console.print(f"[yellow]Embeddings para {combo_name} não encontrados. Gerando novos...[/yellow]")
                    cat_embeds = get_embeddings(
                        cat_texts, 
                        method=provider, 
                        model=model_name,
                        dim=model_dim,
                        show_progress=True
                    )
                    save_embeddings(cat_embeds, cat_embed_file)
                else:
                    console.print(f"[green]Embeddings {combo_name} carregados do cache.[/green]")
                
                # Processa os itens utilizando os embeddings do catálogo unificado
                df_results = classify_items_batched(
                    df_items, cat_embeds, cat_meta,
                    lambda texts: get_embeddings(
                        texts, 
                        method=provider, 
                        model=model_name, 
                        dim=model_dim,
                        show_progress=True
                    )
                )
                
                # Armazena a resposta (coluna "answer") para esta combinação provider_model
                results_dict[combo_name] = df_results["answer"]
                console.print(f"[bold green]{combo_name} concluído com {len(df_results)} respostas.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Erro em {combo_name}: {str(e)}[/bold red]")
                results_dict[combo_name] = pd.Series([""] * len(df_items))

    # Recarrega a planilha original para anexar as respostas
    console.print("[bold magenta]Gerando planilha comparativa...[/bold magenta]")
    df_full = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)

    # Adiciona, para cada combinação, uma coluna com a resposta gerada
    for combo, series in results_dict.items():
        df_full[f"Resposta_{combo}"] = series

    # Carrega o gabarito e faz merge com os dados
    console.print(f"[bold cyan]Carregando gabarito de {GABARITO_FILE}...[/bold cyan]")
    try:
        df_gabarito = pd.read_excel(GABARITO_FILE, sheet_name=GABARITO_SHEET)
        if "id_pncp" in df_gabarito.columns and "id_pncp" in df_full.columns:
            df_gabarito["id_pncp"] = df_gabarito["id_pncp"].astype(str)
            df_full["id_pncp"] = df_full["id_pncp"].astype(str)
            gabarito_cols = ["id_pncp", "tipoDetectado"]
            for i in range(1, 11):
                col = f"TOP_{i}"
                if col in df_gabarito.columns:
                    gabarito_cols.append(col)
            df_full = pd.merge(
                df_full, 
                df_gabarito[gabarito_cols],
                on="id_pncp", 
                how="left"
            )
            matched_count = df_full["tipoDetectado"].notna().sum()
            console.print(f"[green]Gabarito mesclado com sucesso - {matched_count}/{len(df_full)} registros com correspondência.[/green]")
        else:
            console.print(f"[bold red]Coluna 'id_pncp' não encontrada no gabarito ou nos dados.[/bold red]")
            console.print("[yellow]Tentando usar 'id' como alternativa...[/yellow]")
            if "id" in df_gabarito.columns and "id" in df_full.columns:
                df_gabarito["id"] = df_gabarito["id"].astype(str)
                df_full["id"] = df_full["id"].astype(str)
                gabarito_cols = ["id", "tipoDetectado"] + [f"TOP_{i}" for i in range(1, 11) if f"TOP_{i}" in df_gabarito.columns]
                df_full = pd.merge(
                    df_full, 
                    df_gabarito[gabarito_cols],
                    on="id", 
                    how="left"
                )
                console.print(f"[green]Gabarito mesclado usando coluna 'id'.[/green]")
            else:
                console.print(f"[bold red]Nem 'id_pncp' nem 'id' encontrados. Não será possível usar o gabarito.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar gabarito: {str(e)}[/bold red]")
        console.print("[yellow]Continuando sem gabarito para pontuação. Os resultados podem não ser precisos.[/yellow]")

    # Processa as pontuações
    method_cols = [col for col in df_full.columns if col.startswith("Resposta_")]
    top_cols = [f"TOP_{i}" for i in range(1, 11)]

    console.print("[bold cyan]Processando pontuações...[/bold cyan]")
    df_scores_final, df_scores_intermediate = process_all_rows(df_full, method_cols, top_cols)

    # Salva os resultados em Excel
    TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
    OUTPUT_FILE = os.path.join(os.path.dirname(INPUT_FILE), f"COMPARATIVO_METODOS_{TIMESTAMP}.xlsx")
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df_full.to_excel(writer, sheet_name="Respostas", index=False)
        df_scores_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
        df_scores_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)

    console.print(f"[bold green]Comparativo salvo em {OUTPUT_FILE}[/bold green]")

# ===============================================================================
# FUNÇÃO PRINCIPAL DO MODO CLASSIFICAÇÃO
# ===============================================================================
def run_classification_mode():
    """Executa o pipeline de classificação."""
    console.print("[bold cyan]===== MODO CLASSIFICAÇÃO DE ITENS =====")
    start_time = time.time()
    
    try:
        # Carregar dados e verificar se existe checkpoint
        df_items, cat, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Escolha do modelo 
        console.print("[bold magenta]Selecione o provider para embeddings:[/bold magenta]")
        console.print("1. OpenAI (text-embedding-3-large)")
        console.print("2. Sentence-Transformers (paraphrase-multilingual-mpnet-base-v2)")
        console.print("3. LM Studio (jina-embeddings-v3)")
        console.print("4. Ollama (mxbai-embed-large)")
        
        choice = input("Escolha a opção (1-4, default=1): ").strip()
        
        provider = "openai"  # Padrão
        model = "text-embedding-3-large"
        
        if choice == "2":
            provider = "sentence_transformers"
            model = "paraphrase-multilingual-mpnet-base-v2"
        elif choice == "3":
            provider = "lm_studio"
            model = "text-embedding-granite-embedding-278m-multilingual"
        elif choice == "4":
            provider = "ollama"
            model = "mxbai-embed-large"
        
        console.print(f"[green]Utilizando {provider} com modelo {model}[/green]")
        
        # Define o caminho para cache dos embeddings do catálogo unificado
        model_safe_name = model.replace("/", "_").replace("-", "_").replace(".", "_").lower()
        provider_safe_name = provider.lower()
        cat_embed_file = os.path.join(EMBEDDING_PATH, f"cat_{provider_safe_name}_{model_safe_name}.pkl")
        
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        cat_embeds = load_embeddings(cat_embed_file)
        if cat_embeds is None or len(cat_embeds) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeds = get_embeddings(cat_texts, method=provider, model=model)
            save_embeddings(cat_embeds, cat_embed_file)
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Classificar items
        console.print("[bold magenta]Iniciando classificação de itens...[/bold magenta]")
        results = classify_items_batched(
            df_items, 
            cat_embeds, 
            cat_meta,
            lambda texts: get_embeddings(texts, method=provider, model=model)
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

# ===============================================================================
# FUNÇÃO PRINCIPAL
# ===============================================================================
def main():
    """Função principal."""
    console.print("[bold cyan]============================================")
    console.print("[bold yellow]EmbedForge Pro - Sistema Unificado v1.0")
    console.print("[bold cyan]============================================\n")
    
    console.print("[bold magenta]Selecione o modo de operação:[/bold magenta]")
    console.print("1. Classificação de Itens (utiliza um único modelo)")
    console.print("2. Comparativo de Embeddings (compara múltiplos modelos)")
    
    choice = input("Escolha a opção (1 ou 2): ").strip()
    
    if choice == "2":
        run_comparative_mode()
    else:
        run_classification_mode()
        
    console.print("\n[bold green]Processamento concluído![/bold green]")

if __name__ == "__main__":
    main()