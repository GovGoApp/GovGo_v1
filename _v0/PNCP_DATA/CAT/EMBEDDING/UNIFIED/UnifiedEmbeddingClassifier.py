#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UnifiedEmbeddingClassifier.py
--------------------------------
Unifica múltiplos métodos de geração de embeddings para classificação de itens de compras em categorias.
Métodos disponíveis:
  - openai: API da OpenAI (ex.: text-embedding-3-large)
  - sentence_transformers: Biblioteca local (ex.: paraphrase-multilingual-mpnet-base-v2)
  - lm_studio: API HTTP para LM Studio
  - ollama: Geração via Ollama (ex.: mxbai-embed-large)
  - hf_transformers: Modelos da Hugging Face com pooling (ex.: distilbert-base-uncased)
  - spacy: Extração de vetores com spaCy (ex.: pt_core_news_md)
  
A classificação é feita comparando o embedding do item com os embeddings dos catálogos CATMAT e CATSER,
atribuindo o tipo (MATERIAL ou SERVIÇO) de acordo com a maior similaridade.
"""

import os
import json
import pickle
import time
from datetime import datetime

import numpy as np
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Configurações gerais e caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
EXCEL_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
SHEET = "OBJETOS"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = os.path.join(REPORTS_PATH, f"TESTE_SIMPLES_ITENS_{TIMESTAMP}.xlsx")
CHECKPOINT_FILE = os.path.join(REPORTS_PATH, f"CHECKPOINT_TESTE_SIMPLES_ITENS_{TIMESTAMP}.pkl")

# Arquivos dos catálogos
CATMAT_FILE = os.path.join(CAT_PATH, "CATMAT_nv2.json")
CATSER_FILE = os.path.join(CAT_PATH, "CATSER_nv2.json")

# Parâmetros de processamento
BATCH_SIZE = 10000  # itens por lote
TOP_N = 10  # número de categorias retornadas
MAX_WORKERS = 8  # ajuste conforme o seu sistema

# Configurações específicas para cada método
# --- OpenAI
OPENAI_API_KEY = "SUA_CHAVE_OPENAI_AQUI"
OPENAI_MODEL = "text-embedding-3-large"

# --- Sentence Transformers
ST_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# --- LM Studio
LMSTUDIO_API_URL = "http://127.0.0.1:1234/v1/embeddings"
LMSTUDIO_MODEL = "jina-embeddings-v3"

# --- Ollama
OLLAMA_MODEL = "mxbai-embed-large"

# --- Hugging Face Transformers
HF_MODEL_NAME = "distilbert-base-uncased"

# --- spaCy
SPACY_MODEL_NAME = "pt_core_news_md"  # Certifique-se de ter o modelo instalado

# Imports específicos (importa somente os necessários se disponíveis)
try:
    import openai
    openai.api_key = OPENAI_API_KEY
except ImportError:
    openai = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

import requests
try:
    import ollama
except ImportError:
    ollama = None

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
except ImportError:
    AutoTokenizer, AutoModel, torch = None, None, None

try:
    import spacy
except ImportError:
    spacy = None

# Console para feedback visual
console = Console()

# Dicionários globais para modelos carregados (lazy loading)
_models = {}

def get_embedding(text, method="openai"):
    """
    Retorna o embedding para um texto usando o método especificado.
    """
    if method == "openai":
        if openai is None:
            raise ImportError("Módulo openai não está instalado.")
        # Processamento em lote pode ser implementado; aqui, simples chamada individual:
        response = openai.Embedding.create(input=[text], model=OPENAI_MODEL)
        return np.array(response["data"][0]["embedding"], dtype=float)
    
    elif method == "sentence_transformers":
        if SentenceTransformer is None:
            raise ImportError("Módulo sentence_transformers não está instalado.")
        if "st" not in _models:
            console.print(f"[bold magenta]Carregando modelo SentenceTransformer: {ST_MODEL_NAME}...[/bold magenta]")
            _models["st"] = SentenceTransformer(ST_MODEL_NAME)
        model = _models["st"]
        emb = model.encode(text, convert_to_numpy=True)
        return np.array(emb, dtype=float)
    
    elif method == "lm_studio":
        # Utiliza a API HTTP do LM Studio
        headers = {"Content-Type": "application/json"}
        data = {"model": LMSTUDIO_MODEL, "input": text}
        try:
            response = requests.post(LMSTUDIO_API_URL, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return np.array(result["data"][0]["embedding"], dtype=float)
        except Exception as e:
            console.print(f"[bold red]Erro no LM Studio: {str(e)}[/bold red]")
            raise
    
    elif method == "ollama":
        if ollama is None:
            raise ImportError("Módulo ollama não está instalado.")
        try:
            result = ollama.embed(model=OLLAMA_MODEL, input=text)
            if isinstance(result, dict) and "embedding" in result:
                return np.array(result["embedding"], dtype=float)
            elif isinstance(result, list):
                return np.array(result, dtype=float)
            else:
                raise ValueError("Formato de resposta inesperado do Ollama")
        except Exception as e:
            console.print(f"[bold red]Erro no Ollama: {str(e)}[/bold red]")
            raise
    
    elif method == "hf_transformers":
        if AutoTokenizer is None or AutoModel is None:
            raise ImportError("Transformers não está instalado.")
        if "hf" not in _models:
            console.print(f"[bold magenta]Carregando modelo HF Transformers: {HF_MODEL_NAME}...[/bold magenta]")
            _models["hf_tokenizer"] = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
            _models["hf_model"] = AutoModel.from_pretrained(HF_MODEL_NAME)
        tokenizer = _models["hf_tokenizer"]
        model = _models["hf_model"]
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
        # Mean pooling dos tokens
        token_embeddings = outputs.last_hidden_state.squeeze(0)
        attention_mask = inputs["attention_mask"].squeeze(0)
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        summed = torch.sum(token_embeddings * mask, dim=0)
        counts = torch.clamp(mask.sum(dim=0), min=1e-9)
        mean_pooled = summed / counts
        return mean_pooled.numpy()
    
    elif method == "spacy":
        if spacy is None:
            raise ImportError("spaCy não está instalado.")
        if "spacy" not in _models:
            console.print(f"[bold magenta]Carregando modelo spaCy: {SPACY_MODEL_NAME}...[/bold magenta]")
            _models["spacy"] = spacy.load(SPACY_MODEL_NAME)
        nlp = _models["spacy"]
        doc = nlp(text)
        return doc.vector
    else:
        raise ValueError("Método de embedding desconhecido: " + method)

def get_embeddings_batch(texts, method="openai", batch_size=32):
    """
    Processa uma lista de textos em lotes para gerar embeddings.
    """
    embeddings = []
    total = len(texts)
    with Progress(SpinnerColumn(), TextColumn(f"[bold cyan]Processando embeddings ({method})..."),
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
        task = progress.add_task("", total=(total + batch_size - 1) // batch_size)
        for i in range(0, total, batch_size):
            batch = texts[i:i+batch_size]
            batch_embs = [get_embedding(text, method) for text in batch]
            embeddings.extend(batch_embs)
            progress.update(task, advance=1)
    return embeddings

def cosine_similarity(a, b):
    """Calcula a similaridade por cosseno entre dois vetores."""
    if np.linalg.norm(a)==0 or np.linalg.norm(b)==0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def prepare_catalog_entries():
    """
    Lê os arquivos de catálogo e prepara listas de textos e metadados.
    Retorna: catmat_texts, catmat_meta, catser_texts, catser_meta.
    """
    console.print("[bold magenta]Carregando catálogos...[/bold magenta]")
    with open(CATMAT_FILE, "r", encoding="utf-8") as f:
        catmat = json.load(f)
    with open(CATSER_FILE, "r", encoding="utf-8") as f:
        catser = json.load(f)
    
    catmat_texts = []
    catmat_meta = []
    for group in catmat:
        grp_code = group.get("codGrupo")
        grp_name = group.get("Grupo")
        for cls in group.get("Classes", []):
            class_code = cls.get("codClasse")
            class_name = cls.get("Classe")
            combined = f"{grp_name} - {class_name}"
            catmat_texts.append(combined)
            catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
    
    catser_texts = []
    catser_meta = []
    for group in catser:
        grp_code = group.get("codGrupo")
        grp_name = group.get("Grupo")
        for cls in group.get("Classes", []):
            class_code = cls.get("codClasse")
            class_name = cls.get("Classe")
            combined = f"{grp_name} - {class_name}"
            catser_texts.append(combined)
            catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
    
    console.print(f"[green]Preparados {len(catmat_texts)} textos de CATMAT e {len(catser_texts)} de CATSER.[/green]")
    return catmat_texts, catmat_meta, catser_texts, catser_meta

def classify_item(item_text, catmat_embs, catmat_meta, catser_embs, catser_meta, method="openai"):
    """
    Para um único item (descrição), gera seu embedding e compara com os catálogos.
    Retorna uma string resposta no formato: "TIPO; [descrição do grupo - classe]".
    """
    emb = get_embedding(item_text, method)
    # Cálculo de similaridade com CATMAT
    sim_catmat = [cosine_similarity(emb, cat_emb) for cat_emb in catmat_embs]
    max_idx_catmat = np.argmax(sim_catmat) if sim_catmat else -1
    score_catmat = sim_catmat[max_idx_catmat] if max_idx_catmat >= 0 else 0
    
    # Cálculo de similaridade com CATSER
    sim_catser = [cosine_similarity(emb, cat_emb) for cat_emb in catser_embs]
    max_idx_catser = np.argmax(sim_catser) if sim_catser else -1
    score_catser = sim_catser[max_idx_catser] if max_idx_catser >= 0 else 0
    
    # Escolhe o tipo com maior similaridade
    if score_catmat >= score_catser:
        tipo = "MATERIAL"
        details = catmat_meta[max_idx_catmat][2] + " - " + catmat_meta[max_idx_catmat][4]
    else:
        tipo = "SERVIÇO"
        details = catser_meta[max_idx_catser][2] + " - " + catser_meta[max_idx_catser][4]
    
    return f"{tipo}; {details}"

def classify_items(df_items, method="openai"):
    """
    Classifica os itens (DataFrame) em lotes utilizando o método de embeddings escolhido.
    Retorna uma lista de respostas para cada item.
    """
    # Preparar catálogos e calcular embeddings dos textos de catálogo
    catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries()
    console.print(f"[bold cyan]Gerando embeddings para os catálogos com método {method}...[/bold cyan]")
    catmat_embs = get_embeddings_batch(catmat_texts, method=method, batch_size=32)
    catser_embs = get_embeddings_batch(catser_texts, method=method, batch_size=32)
    
    respostas = []
    texts = df_items["objetoCompra"].astype(str).tolist()
    total = len(texts)
    console.print(f"[bold cyan]Classificando {total} itens usando {method}...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Processando itens...[/bold cyan]"),
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
        task = progress.add_task("", total=total)
        for text in texts:
            # Se o item estiver vazio, resposta vazia
            if not text or text.lower() in ["nan", "none"]:
                respostas.append("")
            else:
                resposta = classify_item(text, catmat_embs, catmat_meta, catser_embs, catser_meta, method)
                respostas.append(resposta)
            progress.update(task, advance=1)
    return respostas

def load_items():
    """Carrega os itens do Excel."""
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
        console.print(f"[green]Carregados {len(df)} itens do Excel.[/green]")
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar o Excel: {str(e)}[/bold red]")
        raise

# Se desejar salvar checkpoints ou os embeddings dos itens, funções adicionais podem ser implementadas.

if __name__ == "__main__":
    # Exemplo de uso: classificar usando um método escolhido (ex.: "sentence_transformers")
    metodo = "sentence_transformers"  # altere para: "openai", "lm_studio", "ollama", "hf_transformers", "spacy"
    df_items = load_items()
    respostas = classify_items(df_items, method=metodo)
    df_items["Resposta_" + metodo] = respostas
    # Salvar resultados
    df_items.to_excel(OUTPUT_FILE, index=False)
    console.print(f"[green]Resultados salvos em {OUTPUT_FILE}[/green]")
