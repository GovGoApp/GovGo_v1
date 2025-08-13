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

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Adicione após as importações e antes das configurações
import logging

# Configurar o logging para evitar que as mensagens HTTP interrompam as barras de progresso
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# Configurações e caminhos (mantidos conforme versões originais)
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT\\")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS\\")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO\\")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING\\")
ITEMS_EMBED_PATH = os.path.join(EMBEDDING_PATH, "items\\")

INPUT_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
INPUT_SHEET = "OBJETOS"
GABARITO_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES_GABARITO.xlsx")
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
        TextColumn(f"[bold green]Processando embeddings ({provider_name})..."),
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
            #console.print(f"[green]Embeddings salvos em {filepath}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
            return False

def load_embeddings(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            #console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def save_checkpoint(last_processed, output_file):
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def load_data():
    console.print("[bold magenta]Carregando dados e catálogos...[/bold magenta]")
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
        with open(os.path.join(CAT_PATH, "CATMAT_nv2.json"), 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(os.path.join(CAT_PATH, "CATSER_nv2.json"), 'r', encoding='utf-8') as f:
            catser = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogos: {str(e)}[/bold red]")
        raise e
    existing_results = pd.DataFrame()
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
    return df_items, catmat, catser, existing_results, checkpoint

def prepare_catalog_entries(catmat, catser):
    console.print("[bold magenta]Preparando textos de catálogo...[/bold magenta]")
    catmat_texts = []
    catmat_meta = []
    for group in catmat:
        grp_code = group.get('codGrupo')
        grp_name = group.get('Grupo')
        for cls in group.get('Classes', []):
            class_code = cls.get('codClasse')
            class_name = cls.get('Classe')
            combined_text = f"{grp_name} - {class_name}"
            catmat_texts.append(combined_text)
            catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
    catser_texts = []
    catser_meta = []
    for group in catser:
        grp_code = group.get('codGrupo')
        grp_name = group.get('Grupo')
        for cls in group.get('Classes', []):
            class_code = cls.get('codClasse')
            class_name = cls.get('Classe')
            combined_text = f"{grp_name} - {class_name}"
            catser_texts.append(combined_text)
            catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
    console.print(f"[magenta]Preparados {len(catmat_texts)} textos CATMAT e {len(catser_texts)} textos CATSER.\n[/magenta]")
    return catmat_texts, catmat_meta, catser_texts, catser_meta

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
        console.print("[bold yellow]Testando conexão com Ollama...[/bold yellow]")
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
        console.print(f"[green]Conexão com Ollama estabelecida. Dimensão: {embedding_dim}[/green]")
        
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
                    print(f"Processando texto {i}: {text}")
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
    import spacy
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
        raise ValueError("Método de embeddings não suportado")

# =============================================================================
# FUNÇÃO DE CLASSIFICAÇÃO (mantida a lógica original)
# =============================================================================
def classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, get_embeddings_func, existing_results=None, last_processed=0, top_n=TOP_N):
    # Pré-computação das matrizes dos catálogos
    catmat_matrix = np.vstack(catmat_embeddings)
    catser_matrix = np.vstack(catser_embeddings)
    all_results = existing_results if existing_results is not None else pd.DataFrame()
    total_items = len(df_items)
    results = []
    for batch_start in range(0, total_items, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        df_batch = df_items.iloc[batch_start:batch_end]
        descriptions = []
        item_ids = []
        indices = []
        for idx, row in df_batch.iterrows():
            item_id = row.get("id") or row.get("id_pncp")
            description = str(row.get("objetoCompra") or "")
            if not description or pd.isna(description) or description.lower() in ["nan", "none"]:
                descriptions.append("")
            else:
                descriptions.append(description)
            item_ids.append(item_id)
            indices.append(idx)
        valid_indices = [i for i, desc in enumerate(descriptions) if desc]
        valid_descriptions = [descriptions[i] for i in valid_indices]
        if valid_descriptions:
            item_embeddings = get_embeddings_func(valid_descriptions)
            all_item_embeddings = [None] * len(descriptions)
            for i, emb in zip(valid_indices, item_embeddings):
                all_item_embeddings[i] = emb
        else:
            all_item_embeddings = [None] * len(descriptions)
        
        # Para cada item com embedding válido, calcula a similaridade com CATMAT e CATSER
        # Para cada item com embedding válido, calcula a similaridade com CATMAT e CATSER
    for i in range(len(descriptions)):
        if descriptions[i] and all_item_embeddings[i] is not None:
            emb = all_item_embeddings[i]
            # Normalizar o vetor de embedding do item (importante para Ollama)
            norm_emb = np.linalg.norm(emb) + 1e-10
            emb_normalized = emb / norm_emb
            
            # Pré-normalização dos vetores do catálogo (uma vez por batch)
            if i == 0:  # Só fazemos isso na primeira iteração do batch
                norms_catmat = np.linalg.norm(catmat_matrix, axis=1) + 1e-10
                norms_catser = np.linalg.norm(catser_matrix, axis=1) + 1e-10
                catmat_normalized = catmat_matrix / norms_catmat[:, np.newaxis]
                catser_normalized = catser_matrix / norms_catser[:, np.newaxis]
            
            # Similaridade com vetores normalizados (produto escalar direto)
            sims_catmat = np.dot(catmat_normalized, emb_normalized)
            sims_catser = np.dot(catser_normalized, emb_normalized)
            
            max_catmat = np.max(sims_catmat)
            max_catser = np.max(sims_catser)
            
            if max_catmat >= max_catser:
                idx_best = int(np.argmax(sims_catmat))
                catalog_type, grp_code, grp_name, class_code, class_name = catmat_meta[idx_best]
                answer = f"{catalog_type}; {grp_code}-{grp_name}; {class_code}-{class_name}"
            else:
                idx_best = int(np.argmax(sims_catser))
                catalog_type, grp_code, grp_name, class_code, class_name = catser_meta[idx_best]
                answer = f"{catalog_type}; {grp_code}-{grp_name}; {class_code}-{class_name}"
        else:
            answer = ""
        results.append({"index": indices[i], "id": item_ids[i], "answer": answer})
    df_results = pd.DataFrame(results)
    all_results = pd.concat([all_results, df_results], ignore_index=True)
    return all_results

# =============================================================================
# FUNÇÃO PRINCIPAL – EXECUÇÃO UNIFICADA
# =============================================================================
def main_unified(embedding_method="openai", model=None):
    df_items, catmat, catser, existing_results, checkpoint = load_data()
    catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
    console.print("[bold cyan]Gerando embeddings para os catálogos...[/bold cyan]")
    catmat_embeddings = get_embeddings(catmat_texts, method=embedding_method, model=model)
    catser_embeddings = get_embeddings(catser_texts, method=embedding_method, model=model)
    console.print("[bold cyan]Iniciando classificação dos itens...[/bold cyan]")
    df_results = classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta,
                                          lambda texts: get_embeddings(texts, method=embedding_method, model=model))
    df_full = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)
    df_final = df_full.merge(df_results, left_index=True, right_on="index", how="left")
    df_final.to_excel(OUTPUT_FILE, index=False)
    console.print(f"[green]Resultados salvos em {OUTPUT_FILE}[/green]")

if __name__ == "__main__":
    # Para testar um método específico e modelo, altere os parâmetros abaixo.
    # Exemplo: main_unified(embedding_method="openai", model="text-embedding-3-large")
    main_unified(embedding_method="openai", model="text-embedding-3-large")
