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
def get_embeddings_openai(texts, batch_size=100, show_progress=True, model="text-embedding-3-large"):
    
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    max_retries = 5
    if show_progress:
        with provider_progress("OpenAI", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                retry_delay = 5
                for attempt in range(max_retries):
                    try:
                        response = client.embeddings.create(model=model, input=batch)
                        batch_embeddings = [np.array(item.embedding, dtype=float) for item in response.data]
                        embeddings.extend(batch_embeddings)
                        break
                    except Exception as e:
                        if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                            progress.console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                            time.sleep(retry_delay)
                            retry_delay += attempt * 2
                        else:
                            raise e
                progress.update(task, advance=1)
    else:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            retry_delay = 5
            for attempt in range(max_retries):
                try:
                    response = client.embeddings.create(model=model, input=batch)
                    batch_embeddings = [np.array(item.embedding, dtype=float) for item in response.data]
                    embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay += attempt * 2
                    else:
                        raise e
    return embeddings

# 2. Sentence-Transformers (v5)
def get_embeddings_sentence_transformers(texts, batch_size=32, show_progress=True, model="paraphrase-multilingual-mpnet-base-v2"):
    from sentence_transformers import SentenceTransformer
    st_model = SentenceTransformer(model)
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    if show_progress:
        with provider_progress("Sentence-Transformers", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = st_model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                embeddings.extend([np.array(emb) for emb in batch_embeddings])
                progress.update(task, advance=1)
    else:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = st_model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            embeddings.extend([np.array(emb) for emb in batch_embeddings])
    return embeddings

# 3. LM Studio via API HTTP (v6.2)
def get_embeddings_lm_studio(texts, batch_size=32, show_progress=True, model="jina-embeddings-v3"):
    API_URL = "http://127.0.0.1:1234/v1/embeddings"
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    try:
        test_resp = requests.post(API_URL, headers={"Content-Type": "application/json"},
                                  json={"model": model, "input": "Teste de conexão"})
        test_resp.raise_for_status()
    except Exception as e:
        console.print(f"[bold red]Erro na conexão com LM Studio: {str(e)}[/bold red]")
        raise e
    if show_progress:
        with provider_progress("LM Studio", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = []
                for text in batch:
                    data = {"model": model, "input": text}
                    resp = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=data)
                    resp.raise_for_status()
                    result = resp.json()
                    batch_embeddings.append(np.array(result["data"][0]["embedding"]))
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            for text in batch:
                data = {"model": model, "input": text}
                resp = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=data)
                resp.raise_for_status()
                result = resp.json()
                embeddings.append(np.array(result["data"][0]["embedding"]))
    return embeddings

# 4. Ollama (v7)
def get_embeddings_ollama(texts, batch_size=32, show_progress=True, model="mxbai-embed-large"):
    """Gera embeddings para uma lista de textos usando a biblioteca Ollama"""
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    embedding_dim = 1024  # Dimensão padrão para mxbai-embed-large
    
    # Testar a conexão primeiro
    try:
        #console.print("\n[yellow]Testando conexão com Ollama...[/yellow]")
        test_response = ollama.embed(model=model, input="Teste de conexão")
        
        # Função interna para extrair embedding da resposta
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
        
        # Determinar dimensão do embedding do teste
        test_emb = extract_embedding(test_response)
        embedding_dim = test_emb.shape[0]
        #console.print(f"\n[green]Conexão com Ollama estabelecida. Dimensão: {embedding_dim}[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro ao testar conexão com Ollama: {str(e)}[/bold red]")
        raise
    
    # Processamento em lotes com barra de progresso
    if show_progress:
        with provider_progress("Ollama", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = []
                
                for text in batch:
                    console.print(f"\n[yellow]{text}[/yellow]")
                    if not text or text.isspace():
                        batch_embeddings.append(np.zeros(embedding_dim))
                        continue
                        
                    try:
                        response = ollama.embed(model=model, input=text)
                        emb = extract_embedding(response)
                        batch_embeddings.append(emb)
                    except Exception as e:
                        console.print(f"[bold red]Erro: {str(e)}[/bold red]")
                        batch_embeddings.append(np.zeros(embedding_dim))
                
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        # Código para processamento sem barra de progresso (similar)
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = []
            
            for text in batch:
                if not text or text.isspace():
                    batch_embeddings.append(np.zeros(embedding_dim))
                    continue
                
                try:
                    response = ollama.embed(model=model, input=text)
                    emb = extract_embedding(response)
                    batch_embeddings.append(emb)
                except Exception as e:
                    console.print(f"[bold red]Erro: {str(e)}[/bold red]")
                    batch_embeddings.append(np.zeros(embedding_dim))
            
            embeddings.extend(batch_embeddings)
    
    return embeddings

# 5. Hugging Face (com transformers)
def get_embeddings_hugging_face(texts, batch_size=32, show_progress=True, model="sentence-transformers/paraphrase-mpnet-base-v2"):
    from transformers import AutoTokenizer, AutoModel
    import torch
    tokenizer = AutoTokenizer.from_pretrained(model)
    hf_model = AutoModel.from_pretrained(model)
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    if show_progress:
        with provider_progress("Hugging Face", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                encoded_input = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
                with torch.no_grad():
                    model_output = hf_model(**encoded_input)
                batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
                embeddings.extend([np.array(emb) for emb in batch_embeddings])
                progress.update(task, advance=1)
    else:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            encoded_input = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
            with torch.no_grad():
                model_output = hf_model(**encoded_input)
            batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
            embeddings.extend([np.array(emb) for emb in batch_embeddings])
    return embeddings

# 6. GitHub – exemplo com outro modelo do Hugging Face
def get_embeddings_github(texts, batch_size=32, show_progress=True, model="sentence-transformers/all-MiniLM-L6-v2"):
    from transformers import AutoTokenizer, AutoModel
    import torch
    tokenizer = AutoTokenizer.from_pretrained(model)
    gh_model = AutoModel.from_pretrained(model)
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    if show_progress:
        with provider_progress("GitHub", total_batches) as progress:
            task = progress.add_task("", total=total_batches)
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                encoded_input = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
                with torch.no_grad():
                    model_output = gh_model(**encoded_input)
                batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
                embeddings.extend([np.array(emb) for emb in batch_embeddings])
                progress.update(task, advance=1)
    else:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            encoded_input = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
            with torch.no_grad():
                model_output = gh_model(**encoded_input)
            batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()
            embeddings.extend([np.array(emb) for emb in batch_embeddings])
    return embeddings

# 7. spaCy (modelo de português)
def get_embeddings_spacy(texts, batch_size=32, show_progress=True, model="pt_core_news_md"):
    
    nlp = spacy.load(model)
    embeddings = []
    total = len(texts)
    if show_progress:
        with provider_progress("spaCy", total) as progress:
            task = progress.add_task("", total=total)
            for text in texts:
                doc = nlp(text)
                embeddings.append(doc.vector)
                progress.update(task, advance=1)
    else:
        for text in texts:
            doc = nlp(text)
            embeddings.append(doc.vector)
    return embeddings

# Função unificada que seleciona o método de embeddings e repassa o parâmetro "model"
def get_embeddings(texts, method="openai", batch_size=32, show_progress=True, model=None):
    """
    Função unificada para obtenção de embeddings usando o método especificado.
    
    Args:
        texts: Lista de textos para gerar embeddings
        method: Método de embeddings a utilizar (openai, sentence_transformers, etc.)
        batch_size: Tamanho do lote para processamento
        show_progress: Se deve mostrar barra de progresso
        model: Modelo específico a utilizar (se None, usa o modelo default)
        
    Returns:
        Lista de arrays numpy representando os embeddings dos textos
    """
    #console.print(f"[bold cyan]Gerando embeddings com método: {method}, modelo: {model or 'default'}[/bold cyan]")
    
    if method == "openai":
        return get_embeddings_openai(texts, batch_size, show_progress, model=model if model else "text-embedding-3-large")
    elif method == "sentence_transformers":
        return get_embeddings_sentence_transformers(texts, batch_size, show_progress, model=model if model else "paraphrase-multilingual-mpnet-base-v2")
    elif method == "lm_studio":
        return get_embeddings_lm_studio(texts, batch_size, show_progress, model=model if model else "jina-embeddings-v3")
    elif method == "ollama":
        return get_embeddings_ollama(texts, batch_size, show_progress, model=model if model else "mxbai-embed-large")
    elif method == "hugging_face":
        return get_embeddings_hugging_face(texts, batch_size, show_progress, model=model if model else "sentence-transformers/paraphrase-mpnet-base-v2")
    elif method == "github":
        return get_embeddings_github(texts, batch_size, show_progress, model=model if model else "sentence-transformers/all-MiniLM-L6-v2")
    elif method == "spacy":
        return get_embeddings_spacy(texts, batch_size, show_progress, model=model if model else "pt_core_news_md")
    else:
        raise ValueError(f"Método de embeddings não suportado: {method}")
    
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
