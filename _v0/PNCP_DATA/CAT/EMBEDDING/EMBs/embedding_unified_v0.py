### EMBEDDING UNIFIED - Sistema unificado de geração de embeddings ###

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import logging
import argparse
import sys

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('embedding_unified')

# Console formatado para exibição
console = Console()

# Configuração de caminhos
PATH = os.path.expanduser("~")
BASE_PATH = os.path.join(PATH, "Desktop", "GOvGO", "v0", "#DATA", "PNCP")
CAT_PATH = os.path.join(BASE_PATH, "CAT")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING")
ITEMS_EMBED_PATH = os.path.join(EMBEDDING_PATH, "ITENS")

# Criar diretórios se não existirem
for directory in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Arquivos padrão (podem ser alterados via argumentos)
EXCEL_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
CATMAT_FILE = os.path.join(CAT_PATH, "CATMAT_nv2.json")
CATSER_FILE = os.path.join(CAT_PATH, "CATSER_nv2.json")
SHEET = "OBJETOS"

# Timestamp para nomes de arquivos
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

# Constantes operacionais
BATCH_SIZE = 1000
MAX_WORKERS = min(32, os.cpu_count() * 4)
TOP_N = 10
SAVE_ITEM_EMBEDDINGS = False

# Locks para operações thread-safe
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
model_lock = threading.Lock()

# Classes para os diferentes provedores de embeddings

class EmbeddingProvider:
    """Classe base para provedores de embeddings"""
    
    def __init__(self, model_name, dimension=None):
        self.model_name = model_name
        self.dimension = dimension
        self.model = None
        self.initialized = False
    
    def initialize(self):
        """Inicializa o modelo (implementado por subclasses)"""
        raise NotImplementedError
    
    def embed(self, texts, batch_size=32, show_progress=True):
        """Gera embeddings para uma lista de textos"""
        raise NotImplementedError
    
    def get_embedding_dimension(self):
        """Retorna a dimensão dos embeddings gerados"""
        return self.dimension
    
    def get_model_name(self):
        """Retorna o nome do modelo usado"""
        return self.model_name

    def get_provider_name(self):
        """Retorna o nome do provedor"""
        return self.__class__.__name__.replace('Provider', '')


class OpenAIProvider(EmbeddingProvider):
    """Provedor para embeddings via OpenAI API"""
    
    def __init__(self, model_name="text-embedding-3-large", api_key=None):
        dimension_map = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
        super().__init__(model_name, dimension_map.get(model_name, 1536))
        self.api_key = api_key
    
    def initialize(self):
        """Inicializa o cliente OpenAI"""
        try:
            from openai import OpenAI
            if not self.api_key:
                console.print("[yellow]API key não fornecida. Tentando usar variável de ambiente OPENAI_API_KEY[/yellow]")
            
            self.client = OpenAI(api_key=self.api_key)
            self.initialized = True
            console.print(f"[green]Cliente OpenAI inicializado com sucesso para o modelo {self.model_name}[/green]")
        except ImportError:
            console.print("[bold red]Falha ao importar o módulo OpenAI. Execute 'pip install openai'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao inicializar cliente OpenAI: {str(e)}[/bold red]")
            raise
    
    def embed(self, texts, batch_size=32, show_progress=True):
        """Gera embeddings via API da OpenAI"""
        if not self.initialized:
            self.initialize()
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings via OpenAI..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=total_batches)
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i+batch_size]
                        batch_embeddings = self._process_batch(batch)
                        embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
            else:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    batch_embeddings = self._process_batch(batch)
                    embeddings.extend(batch_embeddings)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings via OpenAI: {str(e)}[/bold red]")
            raise
    
    def _process_batch(self, batch):
        """Processa um lote de textos para embeddings, com tentativas em caso de erro"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                return [np.array(item.embedding, dtype=float) for item in response.data]
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    retry_delay += attempt * 2  # Backoff exponencial
                    console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                    time.sleep(retry_delay)
                else:
                    if attempt == max_retries - 1:
                        console.print(f"[bold red]Erro após {max_retries} tentativas: {str(e)}[/bold red]")
                    else:
                        console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                    raise


class SentenceTransformerProvider(EmbeddingProvider):
    """Provedor para embeddings via biblioteca sentence-transformers"""
    
    def __init__(self, model_name="paraphrase-multilingual-mpnet-base-v2"):
        dimension_map = {
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
            "paraphrase-multilingual-mpnet-base-v2": 768,
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "distiluse-base-multilingual-cased-v2": 512
        }
        super().__init__(model_name, dimension_map.get(model_name))
        
    def initialize(self):
        """Carrega o modelo SentenceTransformer"""
        try:
            from sentence_transformers import SentenceTransformer
            with model_lock:
                console.print(f"[bold magenta]Carregando modelo SentenceTransformer: {self.model_name}...[/bold magenta]")
                self.model = SentenceTransformer(self.model_name)
                # Atualizar dimensão conforme modelo carregado
                self.dimension = self.model.get_sentence_embedding_dimension()
                console.print(f"[green]Modelo carregado com sucesso! (dimensão: {self.dimension})[/green]")
                self.initialized = True
        except ImportError:
            console.print("[bold red]Falha ao importar o módulo sentence_transformers. Execute 'pip install sentence-transformers'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar modelo SentenceTransformer: {str(e)}[/bold red]")
            raise
    
    def embed(self, texts, batch_size=64, show_progress=True):
        """Gera embeddings usando sentence-transformers"""
        if not self.initialized:
            self.initialize()
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings localmente..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=total_batches)
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i+batch_size]
                        batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                        batch_embeddings = [np.array(emb) for emb in batch_embeddings]
                        embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
            else:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                    batch_embeddings = [np.array(emb) for emb in batch_embeddings]
                    embeddings.extend(batch_embeddings)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings com SentenceTransformer: {str(e)}[/bold red]")
            raise


class LMStudioProvider(EmbeddingProvider):
    """Provedor para embeddings via API HTTP do LM Studio"""
    
    def __init__(self, model_name="text-embedding-nomic-embed-text-v1.5", api_url="http://127.0.0.1:1234/v1/embeddings"):
        dimension_map = {
            "text-embedding-nomic-embed-text-v1.5": 768,
            "text-embedding-granite-embedding-107m-multilingual": 768,
            "text-embedding-granite-embedding-278m-multilingual": 768,
            "jina-embeddings-v3": 768,
            "qwen-2.5-1.5b-embedding-entropy-rl-1": 1024
        }
        super().__init__(model_name, dimension_map.get(model_name))
        self.api_url = api_url
        self.http_lock = threading.Lock()
    
    def initialize(self):
        """Verifica a conexão com o servidor LM Studio"""
        try:
            import requests
            
            # Testar a conexão
            console.print("[bold yellow]Testando conexão com servidor LM Studio...[/bold yellow]")
            
            headers = {"Content-Type": "application/json"}
            data = {
                "model": self.model_name,
                "input": "Teste de conexão"
            }
            
            with self.http_lock:
                response = requests.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
            
            # Verificar a dimensão do resultado
            if "data" in result and len(result["data"]) > 0 and "embedding" in result["data"][0]:
                test_emb = np.array(result["data"][0]["embedding"])
                self.dimension = len(test_emb)
                console.print(f"[green]Conexão bem sucedida! (dimensão do embedding: {self.dimension})[/green]")
                self.initialized = True
            else:
                console.print(f"[bold red]Resposta inválida do servidor: {result}[/bold red]")
                raise ValueError("A resposta do servidor não contém embeddings válidos")
                
        except ImportError:
            console.print("[bold red]Falha ao importar o módulo requests. Execute 'pip install requests'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao testar conexão com LM Studio: {str(e)}[/bold red]")
            console.print("\n[bold yellow]INSTRUÇÕES PARA RESOLVER:[/bold yellow]")
            console.print("1. Verifique se o LM Studio está aberto")
            console.print("2. Na opção Embeddings, selecione o modelo e clique em START")
            console.print("3. Certifique-se que o servidor está rodando em http://127.0.0.1:1234")
            console.print("4. Tente novamente após iniciar o servidor\n")
            raise
    
    def embed(self, texts, batch_size=32, show_progress=True):
        """Gera embeddings via API HTTP do LM Studio"""
        if not self.initialized:
            self.initialize()
        
        import requests
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings via LM Studio..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        headers = {"Content-Type": "application/json"}
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=total_batches)
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i+batch_size]
                        batch_embeddings = []
                        
                        for text in batch:
                            if not text or text.isspace():
                                batch_embeddings.append(np.zeros(self.dimension))
                                continue
                            
                            data = {
                                "model": self.model_name,
                                "input": text
                            }
                            
                            with self.http_lock:
                                response = requests.post(self.api_url, headers=headers, json=data)
                                response.raise_for_status()
                                result = response.json()
                                
                            emb = np.array(result["data"][0]["embedding"])
                            batch_embeddings.append(emb)
                        
                        embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
            else:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    batch_embeddings = []
                    
                    for text in batch:
                        if not text or text.isspace():
                            batch_embeddings.append(np.zeros(self.dimension))
                            continue
                        
                        data = {
                            "model": self.model_name,
                            "input": text
                        }
                        
                        with self.http_lock:
                            response = requests.post(self.api_url, headers=headers, json=data)
                            response.raise_for_status()
                            result = response.json()
                            
                        emb = np.array(result["data"][0]["embedding"])
                        batch_embeddings.append(emb)
                    
                    embeddings.extend(batch_embeddings)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings via LM Studio: {str(e)}[/bold red]")
            raise


class OllamaProvider(EmbeddingProvider):
    """Provedor para embeddings via Ollama"""
    
    def __init__(self, model_name="mxbai-embed-large"):
        dimension_map = {
            "mxbai-embed-large": 1024,
            "bge-m3": 1024,
            "nomic-embed-text": 768
        }
        super().__init__(model_name, dimension_map.get(model_name, 1024))
    
    def initialize(self):
        """Verifica se o Ollama está acessível e carrega o modelo"""
        try:
            import ollama
            
            console.print("[bold yellow]Testando conexão com Ollama...[/bold yellow]")
            
            # Mostrar a versão da biblioteca Ollama para debug
            console.print(f"[cyan]Usando biblioteca Ollama versão: {ollama.__version__ if hasattr(ollama, '__version__') else 'desconhecida'}[/cyan]")
            
            # Determinar qual é o formato de chamada compatível
            test_text = "Teste de conexão"
            try:
                test_response = ollama.embed(model=self.model_name, input=test_text)
                self.embed_method = lambda text: ollama.embed(model=self.model_name, input=text)
                console.print("[green]API usa parâmetro 'input'[/green]")
            except Exception:
                try:
                    test_response = ollama.embed(self.model_name, test_text)
                    self.embed_method = lambda text: ollama.embed(self.model_name, text)
                    console.print("[green]API usa parâmetros posicionais[/green]")
                except Exception:
                    try:
                        test_response = ollama.embeddings(model=self.model_name, prompt=test_text)
                        self.embed_method = lambda text: ollama.embeddings(model=self.model_name, prompt=text)
                        console.print("[green]API usa método 'embeddings'[/green]")
                    except Exception as e:
                        console.print(f"[bold red]Todas as tentativas falharam: {str(e)}[/bold red]")
                        raise
            
            # Extrair o embedding da resposta para determinar a dimensão
            embedding = self._extract_embedding(test_response)
            self.dimension = embedding.shape[0]
            console.print(f"[green]Conexão com Ollama estabelecida! (dimensão do embedding: {self.dimension})[/green]")
            self.initialized = True
            
        except ImportError:
            console.print("[bold red]Falha ao importar o módulo ollama. Execute 'pip install ollama'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao testar conexão com Ollama: {str(e)}[/bold red]")
            console.print("\n[bold yellow]INSTRUÇÕES PARA RESOLVER PROBLEMAS COM OLLAMA:[/bold yellow]")
            console.print("1. Verifique se o servidor Ollama está em execução")
            console.print(f"2. Certifique-se que o modelo foi baixado: ollama pull {self.model_name}")
            console.print(f"3. Teste manualmente no terminal: ollama embed -m {self.model_name} \"teste\"")
            console.print("4. Verifique a documentação do Ollama para o formato correto dos comandos")
            raise
    
    def _extract_embedding(self, response):
        """Função auxiliar para extrair embedding da resposta do Ollama"""
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
    
    def embed(self, texts, batch_size=32, show_progress=True):
        """Gera embeddings via Ollama"""
        if not self.initialized:
            self.initialize()
        
        import ollama
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings via Ollama..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=total_batches)
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i+batch_size]
                        batch_embeddings = []
                        
                        for text in batch:
                            if not text or text.isspace():
                                batch_embeddings.append(np.zeros(self.dimension))
                                continue
                                
                            try:
                                response = self.embed_method(text)
                                emb = self._extract_embedding(response)
                                batch_embeddings.append(emb)
                            except Exception as e:
                                console.print(f"[bold red]Erro ao processar texto: {str(e)}[/bold red]")
                                batch_embeddings.append(np.zeros(self.dimension))
                        
                        embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
            else:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    batch_embeddings = []
                    
                    for text in batch:
                        if not text or text.isspace():
                            batch_embeddings.append(np.zeros(self.dimension))
                            continue
                            
                        try:
                            response = self.embed_method(text)
                            emb = self._extract_embedding(response)
                            batch_embeddings.append(emb)
                        except Exception as e:
                            console.print(f"[bold red]Erro ao processar texto: {str(e)}[/bold red]")
                            batch_embeddings.append(np.zeros(self.dimension))
                    
                    embeddings.extend(batch_embeddings)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings via Ollama: {str(e)}[/bold red]")
            raise


class HuggingFaceProvider(EmbeddingProvider):
    """Provedor para embeddings via biblioteca transformers do HuggingFace"""
    
    def __init__(self, model_name="intfloat/multilingual-e5-large"):
        dimension_map = {
            "intfloat/multilingual-e5-large": 1024,
            "intfloat/multilingual-e5-base": 768,
            "intfloat/multilingual-e5-small": 384,
            "BAAI/bge-m3": 1024,
            "BAAI/bge-small-en": 384,
            "sentence-transformers/all-mpnet-base-v2": 768
        }
        super().__init__(model_name, dimension_map.get(model_name))
        
    def initialize(self):
        """Carrega o modelo HuggingFace transformers"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            with model_lock:
                console.print(f"[bold magenta]Carregando modelo HuggingFace: {self.model_name}...[/bold magenta]")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                console.print(f"[green]Usando dispositivo: {self.device}[/green]")
                self.model.to(self.device)
                
                # Teste para determinar a dimensão
                with torch.no_grad():
                    inputs = self.tokenizer("Teste", padding=True, truncation=True, return_tensors="pt").to(self.device)
                    outputs = self.model(**inputs)
                    self.dimension = outputs.last_hidden_state.shape[-1]
                
                console.print(f"[green]Modelo carregado com sucesso! (dimensão: {self.dimension})[/green]")
                self.initialized = True
        except ImportError:
            console.print("[bold red]Falha ao importar os módulos necessários. Execute 'pip install transformers torch'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar modelo HuggingFace: {str(e)}[/bold red]")
            raise
    
    def embed(self, texts, batch_size=8, show_progress=True):
        """Gera embeddings usando HuggingFace transformers"""
        if not self.initialized:
            self.initialize()
        
        import torch
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings via HuggingFace..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=total_batches)
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i+batch_size]
                        batch_embeddings = self._process_batch(batch)
                        embeddings.extend(batch_embeddings)
                        progress.update(task, advance=1)
            else:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    batch_embeddings = self._process_batch(batch)
                    embeddings.extend(batch_embeddings)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings com HuggingFace: {str(e)}[/bold red]")
            raise
    
    def _process_batch(self, texts):
        """Processa um lote de textos para embeddings"""
        import torch
        
        # Lidar com textos vazios
        valid_indices = [i for i, text in enumerate(texts) if text and not text.isspace()]
        if not valid_indices:
            return [np.zeros(self.dimension) for _ in texts]
        
        valid_texts = [texts[i] for i in valid_indices]
        result_embeddings = [np.zeros(self.dimension) for _ in texts]
        
        with torch.no_grad():
            inputs = self.tokenizer(valid_texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
            outputs = self.model(**inputs)
            
            # Usar média dos tokens ou token CLS dependendo do modelo
            if "e5" in self.model_name.lower():
                # E5 usa média dos tokens com máscara de atenção
                attention_mask = inputs['attention_mask']
                embeddings = outputs.last_hidden_state
                mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
                masked_embeddings = embeddings * mask
                sum_embeddings = torch.sum(masked_embeddings, dim=1)
                sum_mask = torch.clamp(torch.sum(mask, dim=1), min=1e-9)
                batch_embeddings = (sum_embeddings / sum_mask).cpu().numpy()
            else:
                # Usar token CLS (primeiro token)
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            # Normalizar os vetores
            for i, emb in enumerate(batch_embeddings):
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                result_embeddings[valid_indices[i]] = emb
                
        return result_embeddings


class SpacyProvider(EmbeddingProvider):
    """Provedor para embeddings via biblioteca spaCy"""
    
    def __init__(self, model_name="pt_core_news_lg"):
        # Dimensões comuns de modelos spaCy
        dimension_map = {
            "pt_core_news_sm": 96,
            "pt_core_news_md": 300,
            "pt_core_news_lg": 300,
            "en_core_web_sm": 96,
            "en_core_web_md": 300,
            "en_core_web_lg": 300,
            "xx_ent_wiki_sm": 300
        }
        super().__init__(model_name, dimension_map.get(model_name, 300))
        
    def initialize(self):
        """Carrega o modelo spaCy"""
        try:
            import spacy
            
            with model_lock:
                console.print(f"[bold magenta]Carregando modelo spaCy: {self.model_name}...[/bold magenta]")
                try:
                    self.nlp = spacy.load(self.model_name)
                except OSError:
                    console.print(f"[yellow]Modelo {self.model_name} não encontrado, tentando baixar...[/yellow]")
                    import subprocess
                    subprocess.call([
                        "python", "-m", "spacy", "download", self.model_name
                    ])
                    self.nlp = spacy.load(self.model_name)
                
                # Verificar se o modelo tem vetores
                if not self.nlp.has_pipe("tok2vec") and not self.nlp.has_pipe("vectors"):
                    console.print(f"[bold red]O modelo {self.model_name} não suporta vetores![/bold red]")
                    raise ValueError(f"O modelo {self.model_name} não suporta vetores")
                
                # Verificar dimensão dos vetores
                self.dimension = self.nlp("teste").vector.shape[0]
                console.print(f"[green]Modelo spaCy carregado com sucesso! (dimensão: {self.dimension})[/green]")
                self.initialized = True
                
        except ImportError:
            console.print("[bold red]Falha ao importar o módulo spacy. Execute 'pip install spacy'.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar modelo spaCy: {str(e)}[/bold red]")
            raise
    
    def embed(self, texts, batch_size=64, show_progress=True):
        """Gera embeddings usando spaCy"""
        if not self.initialized:
            self.initialize()
        
        embeddings = []
        total_batches = int(np.ceil(len(texts) / batch_size))
        
        progress_context = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings via spaCy..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) if show_progress else None
        
        try:
            if progress_context:
                with progress_context as progress:
                    task = progress.add_task("", total=len(texts))
                    for text in texts:
                        if not text or text.isspace():
                            embeddings.append(np.zeros(self.dimension))
                        else:
                            doc = self.nlp(text)
                            embeddings.append(doc.vector)
                        progress.update(task, advance=1)
            else:
                for text in texts:
                    if not text or text.isspace():
                        embeddings.append(np.zeros(self.dimension))
                    else:
                        doc = self.nlp(text)
                        embeddings.append(doc.vector)
                    
            return embeddings
        
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings com spaCy: {str(e)}[/bold red]")
            raise


# Factory para criar o provedor apropriado
def get_embedding_provider(provider_type, model_name=None, **kwargs):
    """Factory para criar um provedor de embeddings conforme o tipo solicitado"""
    provider_map = {
        "openai": OpenAIProvider,
        "st": SentenceTransformerProvider,
        "sentence-transformer": SentenceTransformerProvider,
        "lmstudio": LMStudioProvider,
        "ollama": OllamaProvider,
        "huggingface": HuggingFaceProvider,
        "hf": HuggingFaceProvider,
        "spacy": SpacyProvider
    }
    
    if provider_type.lower() not in provider_map:
        raise ValueError(f"Provedor de embedding não suportado: {provider_type}")
    
    provider_class = provider_map[provider_type.lower()]
    
    if model_name:
        return provider_class(model_name=model_name, **kwargs)
    else:
        return provider_class(**kwargs)

# Funções auxiliares para checkpoint e salvamento

def save_checkpoint(checkpoint_file, last_processed, output_file):
    """Salvar checkpoint para continuar processamento posteriormente"""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        
        # Gerar timestamp único para cada checkpoint
        check_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_checkpoint = checkpoint_file.replace('.pkl', f'_{check_timestamp}.pkl')
        
        with open(unique_checkpoint, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo em: {unique_checkpoint}[/green]")

def load_checkpoint(checkpoint_file):
    """Carregar checkpoint se existir"""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'rb') as f:
            return pickle.load(f)
    return None

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle"""
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
    """Carrega embeddings de arquivo pickle se existir"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

# Funções principais para o pipeline de classificação

def load_data(excel_file=EXCEL_FILE, sheet=SHEET, catmat_file=CATMAT_FILE, catser_file=CATSER_FILE):
    """Carregar dados do Excel e arquivos de catálogo"""
    console.print("[bold magenta]Carregando dados...[/bold magenta]")
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint_file = os.path.join(CLASS_PATH, f"CHECKPOINT_EMB_{TIMESTAMP}.pkl")
    checkpoint = load_checkpoint(checkpoint_file)
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        
        # Carregar apenas as linhas ainda não processadas
        try:
            # Primeiro, verificamos o tamanho total para calcular o offset
            total_rows = pd.read_excel(excel_file, sheet_name=sheet, nrows=0).shape[0]
            
            # Depois carregamos apenas as linhas restantes
            skiprows = list(range(1, last_processed + 1))  # Pular cabeçalho + linhas já processadas
            df_items = pd.read_excel(excel_file, sheet_name=sheet, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel (a partir da linha {last_processed+1}).[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    else:
        # Carregar do início
        try:
            df_items = pd.read_excel(excel_file, sheet_name=sheet)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    
    # Carregar catálogos
    try:
        with open(catmat_file, 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(catser_file, 'r', encoding='utf-8') as f:
            catser = json.load(f)
        console.print(f"[green]Carregados {len(catmat)} grupos CATMAT e {len(catser)} grupos CATSER.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivos de catálogo: {str(e)}[/bold red]")
        raise
    
    # Se temos checkpoint, precisamos também carregar os resultados já processados
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Carregados {len(existing_results)} resultados anteriores.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
            existing_results = pd.DataFrame()
    else:
        existing_results = pd.DataFrame()
    
    return df_items, catmat, catser, existing_results, checkpoint

def prepare_catalog_entries(catmat, catser):
    """Preparar entradas de catálogo combinadas para embedding"""
    console.print("[bold magenta]Preparando textos de catálogo...[/bold magenta]")
    
    catmat_texts = []
    catmat_meta = []  # Vai armazenar tuplas (catalog, group_code, group_name, class_code, class_name)
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATMAT..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catmat))
        
        for group in catmat:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (materiais)
                combined_text = f"{grp_name} - {class_name}"
                catmat_texts.append(combined_text)
                catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    catser_texts = []
    catser_meta = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATSER..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catser))
        
        for group in catser:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (serviços)
                combined_text = f"{grp_name} - {class_name}"
                catser_texts.append(combined_text)
                catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    console.print(f"[green]Preparados {len(catmat_texts)} textos de categoria CATMAT para embedding.[/green]")
    console.print(f"[green]Preparados {len(catser_texts)} textos de categoria CATSER para embedding.[/green]")
    
    return catmat_texts, catmat_meta, catser_texts, catser_meta

def classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, 
                          provider, existing_results=None, last_processed=0, top_n=TOP_N):
    """Classificar itens em batches com processamento paralelo eficiente"""
    
    # Pré-computar matrizes numpy para cálculo de similaridade mais rápido
    catmat_matrix = np.vstack(catmat_embeddings)
    catser_matrix = np.vstack(catser_embeddings)
    
    # Inicializar resultados acumulados
    all_results = existing_results if existing_results is not None else pd.DataFrame()
    total_items = len(df_items)
    
    # Nome do arquivo de saída
    provider_name = provider.get_provider_name()
    model_name = provider.get_model_name().replace("/", "_").replace("-", "_")
    output_file = os.path.join(CLASS_PATH, f"CLASSIF_{provider_name}_{model_name}_{TIMESTAMP}.xlsx")
    checkpoint_file = os.path.join(CLASS_PATH, f"CHECKPOINT_EMB_{TIMESTAMP}.pkl")
    
    # Processar em batches para salvar resultados incrementalmente
    for batch_start in range(0, total_items, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        df_batch = df_items.iloc[batch_start:batch_end]
        
        console.print(f"[bold magenta]Processando batch {batch_start//BATCH_SIZE + 1}/{total_items//BATCH_SIZE + 1} "
                     f"(itens {batch_start+1}-{batch_end}/{total_items})[/bold magenta]")
        
        # 1. Primeiro, extrair todas as descrições do batch de uma vez
        descriptions = []
        item_ids = []
        indices = []
        
        for idx, row in df_batch.iterrows():
            item_id = row.get("id") or row.get("id_pncp")
            description = str(row.get("objetoCompra") or "")
            
            if not description or pd.isna(description) or description.lower() in ["nan", "none"]:
                # Itens inválidos ainda precisam de um placeholder
                descriptions.append("")
            else:
                descriptions.append(description)
            
            item_ids.append(item_id)
            indices.append(idx)
        
        # 2. Obter embeddings para todo o batch de uma vez
        console.print("[bold cyan]Obtendo embeddings para todo o batch...[/bold cyan]")
        
        try:
            # Obter embeddings apenas para descrições não vazias
            valid_indices = [i for i, desc in enumerate(descriptions) if desc]
            valid_descriptions = [descriptions[i] for i in valid_indices]
            
            if valid_descriptions:
                item_embeddings = provider.embed(valid_descriptions, batch_size=32, show_progress=True)
                
                # Mapear de volta para o índice original
                all_item_embeddings = [None] * len(descriptions)
                for i, emb in zip(valid_indices, item_embeddings):
                    all_item_embeddings[i] = emb
                
                # Salvar embeddings dos itens se necessário
                if SAVE_ITEM_EMBEDDINGS:
                    embeddings_summary = {
                        'batch': f"{batch_start}_{batch_end}",
                        'timestamp': TIMESTAMP,
                        'provider': provider.get_provider_name(),
                        'model': provider.get_model_name(),
                        'num_items': len(valid_indices),
                        'mean_vector': np.mean([emb for emb in item_embeddings], axis=0).tolist() if item_embeddings else None,
                        'std_vector': np.std([emb for emb in item_embeddings], axis=0).tolist() if item_embeddings else None
                    }
                    
                    summary_file = os.path.join(
                        ITEMS_EMBED_PATH, 
                        f"SUMMARY_{batch_start}_{batch_end}_{provider_name}_{model_name}_{TIMESTAMP}.pkl"
                    )
                    save_embeddings(embeddings_summary, summary_file)
                    console.print(f"[green]Resumo de embeddings salvo em: {summary_file}[/green]")
            else:
                all_item_embeddings = []
                
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings do batch: {str(e)}[/bold red]")
            continue
        
        # 3. Agora vamos distribuir o trabalho de classificação entre os workers
        console.print("[bold cyan]Classificando com processamento paralelo...[/bold cyan]")
        
        # Preparar argumentos para classificação
        classification_args = []
        for i, (idx, item_id, description) in enumerate(zip(indices, item_ids, descriptions)):
            # Se temos embedding válido para este item
            if i < len(all_item_embeddings) and all_item_embeddings[i] is not None:
                item_emb = all_item_embeddings[i]
                classification_args.append((idx, item_id, description, item_emb, catmat_matrix, 
                                         catser_matrix, catmat_meta, catser_meta, top_n))
            else:
                # Item inválido ou sem embedding
                classification_args.append((idx, item_id, description, None, None, None, None, None, top_n))
        
        # Usar ThreadPoolExecutor para classificação paralela
        batch_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Classificando items..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task_items = progress.add_task("", total=len(classification_args))
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(classify_item_local, args) for args in classification_args]
                
                for future in futures:
                    try:
                        idx, item_id, result = future.result()
                        batch_results.append(result)
                        progress.update(task_items, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro em future: {str(e)}[/bold red]")
                        progress.update(task_items, advance=1)
        
        # Converter resultados do batch em DataFrame
        df_batch_results = pd.DataFrame(batch_results)
        
        # Processar as categorias top N e outros campos antes de salvar
        if 'categoriasTopN' in df_batch_results.columns:
            df_batch_results['categoriasTopN'] = df_batch_results['categoriasTopN'].apply(
                lambda x: '\n'.join(x) if isinstance(x, list) else str(x))
        
        # Remover a coluna embedding antes de salvar no Excel
        if 'embedding' in df_batch_results.columns:
            df_batch_results = df_batch_results.drop(columns=['embedding'])
        
        # Adicionar aos resultados acumulados
        all_results = pd.concat([all_results, df_batch_results], ignore_index=True)
        
        # Salvar resultados incrementais
        temp_output = output_file.replace('.xlsx', f'_incremental.xlsx')
        try:
            all_results.to_excel(temp_output, index=False)
            console.print(f"[green]Salvo incrementalmente: {temp_output} "
                         f"({len(all_results)} itens processados)[/green]")
            
            # Atualizar checkpoint para recuperação
            save_checkpoint(
                checkpoint_file,
                last_processed + batch_end,  # Atualizar o número de linhas processadas
                temp_output  # Salvar o caminho do arquivo incremental
            )
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar resultados incrementais: {str(e)}[/bold red]")
    
    # Mover a coluna de score para melhor visualização
    cols = all_results.columns.tolist()
    if "scoreCategoria" in cols:
        cols.remove("scoreCategoria")
        cols.insert(cols.index("categoriasTopN") if "categoriasTopN" in cols else -1, "scoreCategoria")
        all_results = all_results[cols]
    
    # Salvar versão final
    try:
        all_results.to_excel(output_file, index=False)
        console.print(f"[bold green]Resultados finais salvos em: {output_file}[/bold green]")
        
        # Remover arquivo incremental após sucesso
        if os.path.exists(temp_output):
            os.remove(temp_output)
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar resultados finais: {str(e)}[/bold red]")
    
    return all_results, output_file

def classify_item_local(args):
    """Função para classificação local com normalização de vetores"""
    idx, item_id, description, item_emb, catmat_matrix, catser_matrix, catmat_meta, catser_meta, top_n = args
    
    # Se não temos embedding, é um item inválido
    if item_emb is None:
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Não classificado",
            "categoriaMelhor": "Descrição inválida",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            # Criar colunas TOP_N e SCORE_N
            **{f"TOP_{i+1}": "" for i in range(top_n)},
            **{f"SCORE_{i+1}": 0.0 for i in range(top_n)},
            "embedding": None
        }
    
    try:
        # Normalizar o vetor do item para garantir similaridade por cosseno
        item_emb_norm = item_emb / np.linalg.norm(item_emb)
        
        # Calcular similaridade com CATMAT e CATSER
        catmat_scores = catmat_matrix.dot(item_emb_norm)
        catser_scores = catser_matrix.dot(item_emb_norm)
        
        # Identificar melhor correspondência em cada catálogo
        best_mat_idx = int(np.argmax(catmat_scores))
        best_ser_idx = int(np.argmax(catser_scores))
        best_mat_score = float(catmat_scores[best_mat_idx])
        best_ser_score = float(catser_scores[best_ser_idx])
        
        # Determinar tipo pela maior similaridade
        if best_mat_score >= best_ser_score:
            tipo = "Material"
            best_idx = best_mat_idx
            best_meta = catmat_meta[best_idx]
            # Obter top N categorias de material
            top_indices = np.argsort(catmat_scores)[-top_n:][::-1]
            top_matches = [(catmat_meta[i], float(catmat_scores[i])) for i in top_indices]
        else:
            tipo = "Serviço"
            best_idx = best_ser_idx
            best_meta = catser_meta[best_idx]
            # Obter top N categorias de serviço
            top_indices = np.argsort(catser_scores)[-top_n:][::-1]
            top_matches = [(catser_meta[i], float(catser_scores[i])) for i in top_indices]
        
        # Formatar a melhor categoria
        catalog_label, grp_code, grp_name, class_code, class_name = best_meta
        best_category_str = f"{catalog_label}; {grp_code}-{grp_name}; {class_code}-{class_name}"
        
        # Formatar top N categorias e scores
        top_categories = []
        top_scores = []
        top_list_str = []
        
        for meta, score in top_matches:
            cat_label, g_code, g_name, c_code, c_name = meta
            cat_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name}"
            score_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name} (score={score:.3f})"
            top_categories.append(cat_str)
            top_scores.append(score)
            top_list_str.append(score_str)
        
        # Preencher com valores vazios se não tivermos categorias suficientes
        while len(top_categories) < top_n:
            top_categories.append("")
            top_scores.append(0.0)
        
        # Criar dicionários para as colunas TOP-N e SCORE-N
        top_dict = {f"TOP_{i+1}": cat for i, cat in enumerate(top_categories)}
        score_dict = {f"SCORE_{i+1}": score for i, score in enumerate(top_scores)}
        
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),
            "categoriasTopN": top_list_str,
            # Adicionar colunas TOP_N e SCORE_N
            **top_dict,
            **score_dict,
            "embedding": item_emb.tolist()
        }
    except Exception as e:
        console.print(f"[bold red]Erro na classificação do item {item_id}: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Erro",
            "categoriaMelhor": f"Erro: {str(e)}",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            **{f"TOP_{i+1}": "" for i in range(top_n)},
            **{f"SCORE_{i+1}": 0.0 for i in range(top_n)},
            "embedding": None
        }
    

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Sistema unificado de classificação com embeddings')
    
    parser.add_argument('--provider', type=str, default='st',
                        help='Provedor de embeddings: openai, st/sentence-transformer, lmstudio, ollama, hf/huggingface, spacy')
    parser.add_argument('--model', type=str,
                        help='Nome do modelo a ser usado')
    parser.add_argument('--excel', type=str, default=EXCEL_FILE,
                        help='Arquivo Excel com dados dos itens')
    parser.add_argument('--sheet', type=str, default=SHEET,
                        help='Nome da aba no arquivo Excel')
    parser.add_argument('--catmat', type=str, default=CATMAT_FILE,
                        help='Arquivo JSON com categorias CATMAT')
    parser.add_argument('--catser', type=str, default=CATSER_FILE,
                        help='Arquivo JSON com categorias CATSER')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                        help='Tamanho do lote para processamento')
    parser.add_argument('--top-n', type=int, default=TOP_N,
                        help='Número de categorias a retornar')
    parser.add_argument('--openai-key', type=str,
                        help='API Key da OpenAI (se usar provedor openai)')
    parser.add_argument('--api-url', type=str,
                        help='URL da API (para provedores HTTP como lmstudio)')
    
    args = parser.parse_args()
    
    # Modelos padrão para cada provedor se não for especificado
    default_models = {
        'openai': 'text-embedding-3-large',
        'st': 'paraphrase-multilingual-mpnet-base-v2',
        'sentence-transformer': 'paraphrase-multilingual-mpnet-base-v2',
        'lmstudio': 'text-embedding-nomic-embed-text-v1.5',
        'ollama': 'mxbai-embed-large',
        'hf': 'intfloat/multilingual-e5-large',
        'huggingface': 'intfloat/multilingual-e5-large',
        'spacy': 'pt_core_news_lg'
    }
    
    # Verificar se o usuário especificou um modelo ou usar o padrão
    model_name = args.model if args.model else default_models.get(args.provider.lower())
    
    # Atualizar configurações globais
    global BATCH_SIZE, TOP_N
    BATCH_SIZE = args.batch_size
    TOP_N = args.top_n
    
    start_time = time.time()
    try:
        # Criar provedor de embeddings conforme parâmetros
        provider_kwargs = {}
        if args.provider.lower() in ['openai']:
            provider_kwargs['api_key'] = args.openai_key
        elif args.provider.lower() in ['lmstudio']:
            if args.api_url:
                provider_kwargs['api_url'] = args.api_url
        
        console.print(f"[bold blue]Inicializando provedor: {args.provider} com modelo: {model_name}[/bold blue]")
        provider = get_embedding_provider(args.provider, model_name, **provider_kwargs)
        
        # Carregar dados do Excel e catálogos
        df_items, catmat, catser, existing_results, checkpoint = load_data(
            excel_file=args.excel,
            sheet=args.sheet,
            catmat_file=args.catmat,
            catser_file=args.catser
        )
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Preparar os textos de catálogo para embeddings
        catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
        
        # Definir caminhos dos arquivos de embeddings de catálogo
        provider_name = provider.get_provider_name()
        model_id = model_name.replace("/", "_").replace("-", "_")
        catmat_embed_file = os.path.join(EMBEDDING_PATH, f"catmat_{provider_name}_{model_id}.pkl")
        catser_embed_file = os.path.join(EMBEDDING_PATH, f"catser_{provider_name}_{model_id}.pkl")
        
        # Verificar se há embeddings de catálogo já existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        catmat_embeddings = load_embeddings(catmat_embed_file)
        if catmat_embeddings is None or len(catmat_embeddings) != len(catmat_texts):
            console.print(f"[yellow]Embeddings de CATMAT não encontrados ou desatualizados. Gerando novos com {model_name}...[/yellow]")
            catmat_embeddings = provider.embed(catmat_texts)
            save_embeddings(catmat_embeddings, catmat_embed_file)
        
        catser_embeddings = load_embeddings(catser_embed_file)
        if catser_embeddings is None or len(catser_embeddings) != len(catser_texts):
            console.print(f"[yellow]Embeddings de CATSER não encontrados ou desatualizados. Gerando novos com {model_name}...[/yellow]")
            catser_embeddings = provider.embed(catser_texts)
            save_embeddings(catser_embeddings, catser_embed_file)
        
        # Normalizar vetores para cálculo de similaridade por cosseno
        console.print("[cyan]Normalizando vetores para cálculo de similaridade por cosseno...[/cyan]")
        catmat_embeddings = [emb / np.linalg.norm(emb) for emb in catmat_embeddings]
        catser_embeddings = [emb / np.linalg.norm(emb) for emb in catser_embeddings]
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Classificar items em batches com processamento paralelo
        console.print("[bold magenta]Iniciando classificação em batches com processamento paralelo...[/bold magenta]")
        results, output_file = classify_items_batched(
            df_items,
            catmat_embeddings,
            catmat_meta,
            catser_embeddings, 
            catser_meta,
            provider,
            existing_results,
            last_processed,
            args.top_n
        )
        
        # Reportar estatísticas de execução
        end_time = time.time()
        total_time = end_time - start_time
        items_per_second = len(df_items) / total_time
        
        console.print(f"[green]Classificação concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        console.print(f"[green]Velocidade média: {items_per_second:.1f} itens/segundo[/green]")
        console.print(f"[cyan]Resultados salvos em: {output_file}[/cyan]")
        console.print(f"[cyan]Embeddings de catálogo salvos em: {EMBEDDING_PATH}[/cyan]")
        console.print(f"[bold blue]Provedor utilizado: {provider_name}")
        console.print(f"[bold blue]Modelo: {model_name}")
        console.print(f"[bold blue]Dimensão dos embeddings: {provider.get_embedding_dimension()}")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())