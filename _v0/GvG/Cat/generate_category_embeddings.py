# =======================================================================
# GERAÇÃO DE EMBEDDINGS PARA CATEGORIAS - SUPABASE
# =======================================================================
# Este script gera embeddings para os nomes das categorias (NOMCAT) usando
# o mesmo processo de pré-processamento utilizado para as contratações.
# 
# Funcionalidades:
# - Carregamento das categorias existentes na tabela
# - Pré-processamento de texto dos nomes das categorias (NOMCAT)
# - Geração de embeddings via API OpenAI com processamento paralelo
# - Atualização do campo cat_embeddings na tabela categorias
# - Monitoramento detalhado do processamento
# 
# Resultado: Tabela categorias com embeddings para busca semântica.
# =======================================================================

import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import threading
import random
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from openai import OpenAI

import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Configure Rich console
console = Console()

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))
load_dotenv(os.path.join(script_dir, "openai.env"))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))

# Caminho da pasta onde está o arquivo Excel (onde salvaremos os PKL)
CAT_DATA_PATH = os.getenv("CAT_DATA_PATH", "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/CAT/NOVA")

# Fetch connection variables
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Log conexão (sem mostrar senha completa)
console.print(Panel("[bold yellow]DADOS DE CONEXÃO[/bold yellow]"))
console.print(f"[blue]USER: {USER}")
console.print(f"[blue]PASSWORD: {'*'*(len(PASSWORD)-4) + PASSWORD[-4:] if PASSWORD else 'Não definida'}")
console.print(f"[blue]HOST: {HOST}")
console.print(f"[blue]PORT: {PORT}")
console.print(f"[blue]DBNAME: {DBNAME}")

# Configurações para processamento paralelo
MAX_WORKERS = 8  # Aumentado com solução para problemas de concorrência NLTK
BATCH_SIZE = 50   # Batch maior para melhor performance

# Lock para controle de concorrência
stats_lock = threading.Lock()
embedding_lock = threading.Lock()

# Configuração OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Estatísticas globais
global_stats = {
    'embeddings_gerados': 0,
    'embeddings_atualizados': 0,
    'embeddings_pulados': 0,
    'erros': 0
}

# Garantir que os recursos NLTK necessários estão disponíveis
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    
    # Inicializar recursos NLTK de forma thread-safe usando importação direta
    try:
        from nltk.corpus import stopwords
        _stopwords = set(stopwords.words('portuguese'))
    except:
        _stopwords = set()
    
    # Para lematização, usar estratégia diferente para thread-safety
    _lemmatizer = None
    try:
        from nltk.stem import WordNetLemmatizer
        # Não inicializar aqui para evitar problemas de thread
        _lemmatizer_class = WordNetLemmatizer
    except:
        _lemmatizer_class = None
    
    console.print("[green]✅ Recursos NLTK configurados com sucesso[/green]")
except Exception as e:
    console.print(f"[yellow]⚠️ Aviso ao carregar NLTK: {e}[/yellow]")
    _stopwords = set()
    _lemmatizer_class = None

# Configurações de embedding (mesmas do script 06)
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # Dimensão para text-embedding-3-large

# Opções de pré-processamento (mesmas usadas no script 06)
preprocessing_options = {
    "remove_special_chars": True,
    "keep_separators": False,
    "remove_accents": True,
    "case": "lower",
    "remove_stopwords": True,
    "lemmatize": True
}

############################################
# FUNÇÕES DE PRÉ-PROCESSAMENTO (DO SCRIPT 06)
############################################

def gvg_pre_processing(text, 
           remove_special_chars=True, 
           keep_separators=False, 
           remove_accents=True, 
           case="lower", 
           remove_stopwords=True, 
           lemmatize=True):
    """
    Normaliza e limpa o texto para processamento de acordo com as opções fornecidas.
    (Função idêntica à do script 06_supabase_embeddings.py - versão thread-safe)
    """
    try:
        # Converter para string se não for
        text = str(text)
        
        # Remover acentos se configurado
        if remove_accents:
            text = unidecode.unidecode(text)
        
        # Aplicar transformação de caixa conforme configurado
        if case == 'lower':
            text = text.lower()
        elif case == 'upper':
            text = text.upper()
        # Se 'original', não faz nada
        
        # Remover caracteres especiais conforme configurado
        if remove_special_chars:
            if keep_separators:
                # Definir padrão regex baseado na configuração de caixa e manutenção de acentos
                if remove_accents:
                    # Se acentos forem removidos, usar apenas letras ASCII
                    if case == 'lower':
                        pattern = r'[^a-z0-9\s:;,.!?_\-]'
                    elif case == 'upper':
                        pattern = r'[^A-Z0-9\s:;,.!?_\-]'
                    else:  # original
                        pattern = r'[^a-zA-Z0-9\s:;,.!?_\-]'
                else:
                    # Se acentos forem mantidos, incluir caracteres acentuados
                    if case == 'lower':
                        pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s:;,.!?_\-]'
                    elif case == 'upper':
                        pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
                    else:  # original
                        pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
                
                # Manter letras, números, espaços e separadores gráficos comuns
                text = re.sub(pattern, '', text)
            else:
                # Padrão para remover tudo exceto letras, números e espaços
                if remove_accents:
                    # Se acentos forem removidos, usar apenas letras ASCII
                    if case == 'lower':
                        pattern = r'[^a-z0-9\s]'
                    elif case == 'upper':
                        pattern = r'[^A-Z0-9\s]'
                    else:  # original
                        pattern = r'[^a-zA-Z0-9\s]'
                else:
                    # Se acentos forem mantidos, incluir caracteres acentuados
                    if case == 'lower':
                        pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s]'
                    elif case == 'upper':
                        pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
                    else:  # original
                        pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
                
                # Remover tudo exceto letras, números e espaços
                text = re.sub(pattern, '', text)
        
        # Dividir o texto em palavras
        words = text.split()
        
        # Remover stopwords se configurado (usando variável global thread-safe)
        if remove_stopwords and _stopwords:
            # Considerar a caixa das stopwords
            if case == 'lower':
                words = [word for word in words if word.lower() not in _stopwords]
            elif case == 'upper':
                words = [word for word in words if word.lower() not in _stopwords]
            else:  # original
                words = [word for word in words if word.lower() not in _stopwords]
          # Aplicar lematização se configurado (usando nova estratégia thread-safe)
        if lemmatize and _lemmatizer_class:
            try:
                # Criar instância local para cada thread
                local_lemmatizer = _lemmatizer_class()
                words = [local_lemmatizer.lemmatize(word) for word in words]
            except Exception as lemma_error:
                # Se falhar a lematização, continuar sem ela
                pass  # Removido log para não poluir saída
        
        return ' '.join(words)
    
    except Exception as e:
        # Em caso de erro, retornar o texto original com processamento mínimo
        console.print(f"[yellow]Erro no pré-processamento, usando processamento mínimo: {e}[/yellow]")
        try:
            # Processamento de fallback mais simples
            text = str(text)
            if remove_accents:
                text = unidecode.unidecode(text)
            if case == 'lower':
                text = text.lower()
            elif case == 'upper':
                text = text.upper()
            # Remover caracteres especiais básicos
            text = re.sub(r'[^\w\s]', ' ', text)
            # Remover espaços múltiplos
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except:
            # Último recurso: retornar texto original
            return str(text)

############################################
# FUNÇÕES DE EMBEDDING (ADAPTADAS DO SCRIPT 06)
############################################

def process_batch(batch_texts, model=EMBEDDING_MODEL):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro"""
    max_retries = 5
    retry_delay = 5
    
    # Validar batch antes de enviar para API
    validated_batch = []
    for text in batch_texts:
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
        if len(text) > 8000:
            text = text[:8000]
            
        validated_batch.append(text)
    
    # Verificação final: batch não pode estar vazio
    if not validated_batch:
        validated_batch = [" "]
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=validated_batch
            )
            
            # Garantir que cada embedding tenha a dimensão correta
            results = []
            for item in response.data:
                emb = np.array(item.embedding, dtype=np.float32)
                # Verificar dimensão do embedding recebido
                if emb.shape != (EMBEDDING_DIM,):
                    console.print(f"[yellow]Aviso: Embedding recebido com formato {emb.shape} em vez de ({EMBEDDING_DIM},). Ajustando...[/yellow]")
                    if len(emb) > EMBEDDING_DIM:
                        # Truncar se maior
                        emb = emb[:EMBEDDING_DIM]
                    else:
                        # Preencher com zeros se menor
                        padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                        padded[:len(emb)] = emb
                        emb = padded
                results.append(emb)
            return results
            
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                console.print(f"[bold yellow]Detalhes do batch: {len(validated_batch)} itens[/bold yellow]")
                # Retornar embeddings vazios com a dimensão correta
                return [np.zeros(EMBEDDING_DIM, dtype=np.float32) for _ in range(len(validated_batch))]
    
    # Se chegou aqui, é porque todas as tentativas falharam
    return [np.zeros(EMBEDDING_DIM, dtype=np.float32) for _ in range(len(validated_batch))]

def prepare_vector_for_postgres(numpy_array):
    """Converte numpy array para lista Python"""
    return numpy_array.tolist()

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

############################################
# FUNÇÕES DE ARMAZENAMENTO DE EMBEDDINGS
############################################

def save_embeddings_pkl(embeddings_dict, filename_prefix="category_embeddings"):
    """Salva embeddings em arquivo PKL com timestamp na pasta do Excel"""
    if not embeddings_dict:
        console.print("[yellow]Nenhum embedding para salvar[/yellow]")
        return None
    
    try:
        # Criar nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.pkl"
        
        # Salvar na pasta onde está o arquivo Excel
        os.makedirs(CAT_DATA_PATH, exist_ok=True)
        filepath = os.path.join(CAT_DATA_PATH, filename)
        
        # Salvar embeddings
        with open(filepath, 'wb') as f:
            pickle.dump(embeddings_dict, f)
        
        console.print(f"[green]✅ Embeddings salvos em: {filepath}[/green]")
        console.print(f"[green]   ({len(embeddings_dict)} embeddings)[/green]")
        return filepath
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao salvar embeddings PKL: {e}[/red]")
        return None

def load_embeddings_pkl(filepath):
    """Carrega embeddings de arquivo PKL"""
    try:
        # Se o caminho não for absoluto, procurar na pasta do Excel
        if not os.path.isabs(filepath):
            filepath = os.path.join(CAT_DATA_PATH, filepath)
            
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                embeddings_dict = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {os.path.basename(filepath)} ({len(embeddings_dict)} registros)[/green]")
            return embeddings_dict
        else:
            console.print(f"[yellow]Arquivo não encontrado: {filepath}[/yellow]")
            return {}
    except Exception as e:
        console.print(f"[red]Erro ao carregar embeddings PKL: {e}[/red]")
        return {}

############################################
# FUNÇÕES DE BANCO DE DADOS
############################################

def create_connection():
    """Cria uma conexão individual com timeout configurado"""
    try:
        connection = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME,
            connect_timeout=30,
            options="-c statement_timeout=300000"  # 5 minutos para statements
        )
        connection.autocommit = False
        return connection
    except Exception as e:
        console.print(f"[bold red]Erro ao criar conexão: {e}[/bold red]")
        return None

def load_categories_without_embeddings():
    """Carrega categorias que ainda não possuem embeddings"""
    connection = create_connection()
    if not connection:
        return None
    
    cursor = connection.cursor()
    try:
        # Buscar categorias sem embeddings ou com embeddings NULL
        cursor.execute("""
            SELECT codcat, nomcat 
            FROM categorias 
            WHERE cat_embeddings IS NULL 
            ORDER BY codcat
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            df = pd.DataFrame(rows, columns=['codcat', 'nomcat'])
            console.print(f"[green]Encontradas {len(df)} categorias sem embeddings[/green]")
            return df
        else:
            console.print("[yellow]Todas as categorias já possuem embeddings[/yellow]")
            return pd.DataFrame(columns=['codcat', 'nomcat'])
        
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar categorias: {e}[/bold red]")
        return None
    finally:
        cursor.close()
        connection.close()

############################################
# FUNÇÕES DE PROCESSAMENTO
############################################

def process_category_batch(worker_id, batch_df, progress, task_id):
    """Processa um lote de categorias para geração de embeddings"""
    local_embeddings = {}
    local_stats = {'embeddings_gerados': 0, 'erros': 0}
    
    try:
        # Preparar textos para processamento
        texts_to_process = []
        codes_to_process = []
        
        # Pré-processar os nomes das categorias
        for idx, row in batch_df.iterrows():
            try:
                codcat = str(row['codcat'])
                nomcat = str(row['nomcat'])
                
                # Pré-processar o texto usando as mesmas opções do script 06
                processed_text = gvg_pre_processing(
                    nomcat,
                    remove_special_chars=preprocessing_options['remove_special_chars'],
                    keep_separators=preprocessing_options['keep_separators'],
                    remove_accents=preprocessing_options['remove_accents'],
                    case=preprocessing_options['case'],
                    remove_stopwords=preprocessing_options['remove_stopwords'],
                    lemmatize=preprocessing_options['lemmatize']
                )
                
                texts_to_process.append(processed_text)
                codes_to_process.append(codcat)
                
            except Exception as e:
                console.print(f"[red]Worker {worker_id} - Erro ao pré-processar categoria {idx}: {e}[/red]")
                local_stats['erros'] += 1
                progress.update(task_id, advance=1)
        
        # Se não há textos para processar, retornar
        if not texts_to_process:
            console.print(f"[yellow]Worker {worker_id} - Nenhum texto para processar[/yellow]")
            return local_embeddings, local_stats
        
        # Processar os textos em lotes para evitar limites da API
        for i in range(0, len(texts_to_process), BATCH_SIZE):
            batch_texts = texts_to_process[i:i+BATCH_SIZE]
            batch_codes = codes_to_process[i:i+BATCH_SIZE]
            
            try:
                # Obter embeddings para o lote atual
                batch_embeddings = process_batch(batch_texts, model=EMBEDDING_MODEL)
                
                # Mapear embeddings para seus códigos
                for j, embedding in enumerate(batch_embeddings):
                    if embedding is not None and not np.all(embedding == 0):
                        local_embeddings[batch_codes[j]] = embedding
                        local_stats['embeddings_gerados'] += 1
                    else:
                        local_stats['erros'] += 1
                
                # Atualizar progresso
                progress.update(task_id, advance=len(batch_texts))
                
            except Exception as e:
                console.print(f"[bold red]Worker {worker_id} - Erro ao processar lote de embeddings: {e}[/bold red]")
                local_stats['erros'] += len(batch_texts)
                progress.update(task_id, advance=len(batch_texts))
        
        # Atualizar estatísticas globais
        update_global_stats(
            embeddings_gerados=local_stats['embeddings_gerados'],
            erros=local_stats['erros']
        )
        
        # Log de resumo do worker
        console.print(f"[cyan]Worker {worker_id} - Gerados: {local_stats['embeddings_gerados']}, Erros: {local_stats['erros']}[/cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Worker {worker_id} - Erro geral ao processar embeddings: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
        progress.update(task_id, advance=len(batch_df))
    
    return local_embeddings, local_stats

def update_batch_embeddings(worker_id, batch_embeddings, progress, task_id):
    """Worker para atualizar um lote de embeddings no banco de dados"""
    connection = create_connection()
    if not connection:
        console.print(f"[bold red]Worker {worker_id} não conseguiu criar conexão![/bold red]")
        progress.update(task_id, advance=len(batch_embeddings))
        return {'updated': 0, 'errors': len(batch_embeddings)}
    
    cursor = connection.cursor()
    local_stats = {'updated': 0, 'errors': 0}
    
    try:
        for codcat, embedding in batch_embeddings.items():
            try:
                vector_list = prepare_vector_for_postgres(embedding)
                
                cursor.execute("""
                    UPDATE categorias 
                    SET cat_embeddings = %s::vector 
                    WHERE codcat = %s AND cat_embeddings IS NULL
                """, (vector_list, codcat))
                
                if cursor.rowcount > 0:
                    local_stats['updated'] += 1
                
                # Atualizar progresso
                progress.update(task_id, advance=1)
                
            except Exception as e:
                local_stats['errors'] += 1
                console.print(f"[red]Worker {worker_id} - Erro ao atualizar {codcat}: {e}[/red]")
                progress.update(task_id, advance=1)
                continue
        
        # Commit em lote
        connection.commit()
        console.print(f"[cyan]Worker {worker_id} - Atualizados: {local_stats['updated']}, Erros: {local_stats['errors']}[/cyan]")
        
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Worker {worker_id} - Erro geral: {e}[/bold red]")
        local_stats['errors'] += len(batch_embeddings) - local_stats['updated']
        progress.update(task_id, advance=len(batch_embeddings) - local_stats['updated'])
    
    finally:
        cursor.close()
        connection.close()
    
    return local_stats

def update_categories_with_embeddings_parallel(embeddings_dict):
    """Atualiza a tabela categorias com os embeddings gerados - MÚLTIPLOS WORKERS"""
    if not embeddings_dict:
        console.print("[yellow]Nenhum embedding para atualizar[/yellow]")
        return
    
    console.print(f"[cyan]Atualizando {len(embeddings_dict)} embeddings com {MAX_WORKERS} workers...[/cyan]")
    
    # Dividir embeddings em lotes para processamento paralelo
    embedding_items = list(embeddings_dict.items())
    batch_size = max(1, len(embedding_items) // MAX_WORKERS)
    
    embedding_batches = []
    for i in range(0, len(embedding_items), batch_size):
        batch = dict(embedding_items[i:i+batch_size])
        if batch:
            embedding_batches.append(batch)
    
    console.print(f"[cyan]Dividindo em {len(embedding_batches)} lotes para atualização paralela[/cyan]")
    
    # Usar barra de progresso para atualização do BD
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Criar tasks para cada worker
        tasks = []
        for i in range(len(embedding_batches)):
            task = progress.add_task(
                f"Worker {i+1}/{len(embedding_batches)} - Atualizando BD", 
                total=len(embedding_batches[i])
            )
            tasks.append(task)
        
        # Executar workers em paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for worker_id, batch in enumerate(embedding_batches):
                future = executor.submit(
                    update_batch_embeddings,
                    worker_id + 1,        # ID do worker
                    batch,                # Lote de embeddings
                    progress,             # Objeto de progresso
                    tasks[worker_id]      # ID da tarefa visual
                )
                futures.append(future)
            
            # Coletar resultados
            total_updated = 0
            total_errors = 0
            
            for future in futures:
                try:
                    result = future.result()
                    total_updated += result['updated']
                    total_errors += result['errors']
                except Exception as e:
                    console.print(f"[bold red]Erro em worker de atualização: {e}[/bold red]")
    
    console.print(f"[green]✅ {total_updated} embeddings atualizados com sucesso![/green]")
    if total_errors > 0:
        console.print(f"[yellow]⚠️ {total_errors} erros durante a atualização[/yellow]")
    
    # Atualizar estatísticas globais
    update_global_stats(embeddings_atualizados=total_updated)

def partition_dataframe(df, n_partitions):
    """Divide DataFrame em partições equilibradas - GARANTINDO QUE TODOS OS REGISTROS SEJAM INCLUÍDOS"""
    if len(df) == 0:
        return []
    
    # Calcular tamanho base de cada partição
    base_size = len(df) // n_partitions
    remainder = len(df) % n_partitions
    
    partitions = []
    start_idx = 0
    
    for i in range(n_partitions):
        # Algumas partições terão um registro extra para distribuir o remainder
        partition_size = base_size + (1 if i < remainder else 0)
        end_idx = start_idx + partition_size
        
        if start_idx < len(df):  # Garantir que não ultrapasse o tamanho do DataFrame
            partition = df.iloc[start_idx:end_idx]
            if len(partition) > 0:
                partitions.append(partition)
        
        start_idx = end_idx
    
    # Verificação de segurança: garantir que todos os registros foram incluídos
    total_records_in_partitions = sum(len(p) for p in partitions)
    if total_records_in_partitions != len(df):
        console.print(f"[yellow]⚠️ Aviso: Particionamento incorreto! {total_records_in_partitions}/{len(df)} registros[/yellow]")
        # Fallback: criar partições simples
        chunk_size = max(1, len(df) // n_partitions)
        partitions = [df.iloc[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
    
    console.print(f"[cyan]📊 Particionamento: {len(df)} registros em {len(partitions)} partições[/cyan]")
    for i, partition in enumerate(partitions):
        console.print(f"   Partição {i+1}: {len(partition)} registros")
    
    return partitions

############################################
# FUNÇÕES DE ESCOLHA E CARREGAMENTO
############################################

def list_available_pkl_files():
    """Lista arquivos PKL disponíveis na pasta do Excel"""
    try:
        pkl_files = [f for f in os.listdir(CAT_DATA_PATH) if f.endswith('.pkl') and 'category_embeddings' in f]
        pkl_files.sort(reverse=True)  # Mais recentes primeiro
        return pkl_files
    except Exception as e:
        console.print(f"[red]Erro ao listar arquivos PKL: {e}[/red]")
        return []

def choose_embeddings_source():
    """Permite ao usuário escolher entre gerar novos embeddings ou carregar do PKL"""
    
    # Listar arquivos PKL disponíveis
    pkl_files = list_available_pkl_files()
    
    console.print("\n[bold yellow]ESCOLHA O MODO DE PROCESSAMENTO:[/bold yellow]")
    console.print("[1] 🔄 Gerar novos embeddings (usar API OpenAI)")
    
    if pkl_files:
        console.print("[2] 📁 Carregar embeddings de arquivo PKL existente")
        console.print("\n[cyan]Arquivos PKL disponíveis:[/cyan]")
        for i, pkl_file in enumerate(pkl_files[:5]):  # Mostrar apenas os 5 mais recentes
            file_path = os.path.join(CAT_DATA_PATH, pkl_file)
            try:
                # Tentar carregar para mostrar informações
                temp_dict = load_embeddings_pkl(file_path)
                size_info = f"({len(temp_dict)} embeddings)" if temp_dict else "(arquivo corrompido)"
                console.print(f"   [{i+3}] {pkl_file} {size_info}")
            except:
                console.print(f"   [{i+3}] {pkl_file} (erro ao ler)")
    else:
        console.print("[cyan]Nenhum arquivo PKL encontrado. Apenas geração nova disponível.[/cyan]")
    
    console.print("\n[bold white]Digite sua escolha (1, 2, 3...):[/bold white]")
    
    try:
        choice = input().strip()
        
        if choice == "1":
            return "generate", None
        elif choice == "2" and pkl_files:
            # Usar o arquivo mais recente
            latest_pkl = pkl_files[0]
            console.print(f"[green]Selecionado arquivo mais recente: {latest_pkl}[/green]")
            return "load", latest_pkl
        elif choice.isdigit():
            choice_num = int(choice)
            if choice_num >= 3 and choice_num < 3 + len(pkl_files):
                selected_pkl = pkl_files[choice_num - 3]
                console.print(f"[green]Selecionado: {selected_pkl}[/green]")
                return "load", selected_pkl
        
        console.print("[yellow]Escolha inválida. Usando geração nova como padrão.[/yellow]")
        return "generate", None
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
        return None, None
    except Exception as e:
        console.print(f"[red]Erro na escolha: {e}. Usando geração nova.[/red]")
        return "generate", None

############################################
# FUNÇÃO PRINCIPAL
############################################

def main():
    """Função principal que orquestra o processamento de embeddings das categorias"""
    console.print(Panel("[bold magenta]GERAÇÃO DE EMBEDDINGS PARA CATEGORIAS[/bold magenta]"))
    console.print(f"[cyan]Configuração: {MAX_WORKERS} Workers | Batch Size: {BATCH_SIZE} | Modelo: {EMBEDDING_MODEL}[/cyan]")
    console.print(f"[cyan]Pré-processamento: {preprocessing_options}[/cyan]")
    
    # Escolher fonte dos embeddings
    action, pkl_file = choose_embeddings_source()
    
    if action is None:
        console.print("[yellow]Operação cancelada.[/yellow]")
        return False
    
    # Carregar categorias sem embeddings
    console.print("\n[bold blue]Carregando categorias sem embeddings...[/bold blue]")
    df_categories = load_categories_without_embeddings()
    
    if df_categories is None:
        console.print("[bold red]Erro ao carregar categorias![/bold red]")
        return False
    
    if len(df_categories) == 0:
        console.print("[green]Todas as categorias já possuem embeddings! ✅[/green]")
        return True
    
    console.print(f"[green]Encontradas {len(df_categories)} categorias sem embeddings[/green]")
    
    # Resetar estatísticas globais
    global_stats.update({
        'embeddings_gerados': 0,
        'embeddings_atualizados': 0,
        'embeddings_pulados': 0,
        'erros': 0
    })
    
    # Iniciar cronômetro
    inicio = time.time()
    
    # Dicionário para armazenar todos os embeddings
    all_embeddings = {}
    
    if action == "generate":
        # GERAÇÃO DE NOVOS EMBEDDINGS
        console.print(f"\n[bold magenta]MODO: GERAR NOVOS EMBEDDINGS[/bold magenta]")
        console.print(f"[cyan]Processando {len(df_categories)} categorias[/cyan]")
        
        # Dividir em partições para processamento paralelo
        partitions = partition_dataframe(df_categories, MAX_WORKERS)
        partitions = [p for p in partitions if len(p) > 0]  # Remover partições vazias
        
        console.print(f"[cyan]Dividindo em {len(partitions)} partições para processamento paralelo[/cyan]")
        
        # FASE 1: Gerar embeddings em paralelo
        console.print("\n[bold magenta]FASE 1: Gerando Embeddings das Categorias[/bold magenta]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            tasks = []
            for worker_id in range(len(partitions)):
                task = progress.add_task(
                    f"Worker {worker_id+1}/{len(partitions)} - Gerando embeddings", 
                    total=len(partitions[worker_id])
                )
                tasks.append(task)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for worker_id, partition in enumerate(partitions):
                    future = executor.submit(
                        process_category_batch,
                        worker_id + 1,               # ID do worker
                        partition,                   # Dados a processar
                        progress,                    # Objeto de progresso
                        tasks[worker_id]             # ID da tarefa visual
                    )
                    futures.append(future)
                
                # Aguardar conclusão de todos os workers e coletar embeddings
                for future in futures:
                    try:
                        worker_embeddings, _ = future.result()
                        all_embeddings.update(worker_embeddings)
                    except Exception as e:
                        console.print(f"[bold red]Erro em worker de embedding: {e}[/bold red]")
        
        # FASE 2: Salvar embeddings em PKL
        console.print(f"\n[bold magenta]FASE 2: Salvando Embeddings em PKL ({len(all_embeddings)} embeddings)[/bold magenta]")
        
        pkl_filepath = None
        if all_embeddings:
            pkl_filepath = save_embeddings_pkl(all_embeddings, "category_embeddings")
    
    elif action == "load":
        # CARREGAMENTO DE EMBEDDINGS DE PKL
        console.print(f"\n[bold magenta]MODO: CARREGANDO EMBEDDINGS DE PKL[/bold magenta]")
        console.print(f"[cyan]Arquivo: {pkl_file}[/cyan]")
        
        # Carregar embeddings do arquivo PKL
        pkl_path = os.path.join(CAT_DATA_PATH, pkl_file)
        all_embeddings = load_embeddings_pkl(pkl_path)
        
        if not all_embeddings:
            console.print("[red]❌ Falha ao carregar embeddings do PKL![/red]")
            return False
        
        console.print(f"[green]✅ {len(all_embeddings)} embeddings carregados com sucesso![/green]")
        
        # Filtrar apenas os embeddings das categorias que precisam ser atualizadas
        needed_codes = set(df_categories['codcat'].astype(str))
        filtered_embeddings = {k: v for k, v in all_embeddings.items() if k in needed_codes}
        
        console.print(f"[cyan]📊 Embeddings filtrados para categorias sem embedding no BD: {len(filtered_embeddings)}/{len(all_embeddings)}[/cyan]")
        all_embeddings = filtered_embeddings
        
        # Atualizar estatísticas
        update_global_stats(embeddings_gerados=len(all_embeddings))
    
    # FASE 3: Atualizar banco de dados
    console.print(f"\n[bold magenta]FASE 3: Atualizando Banco de Dados[/bold magenta]")
    
    if all_embeddings:
        update_categories_with_embeddings_parallel(all_embeddings)
    else:
        console.print("[yellow]Nenhum embedding para atualizar no banco![/yellow]")
    
    # Calcular tempo total
    tempo_total = time.time() - inicio
    
    # Relatório final
    console.print("\n[bold green]" + "="*70 + "[/bold green]")
    console.print("[bold green]RELATÓRIO FINAL DE PROCESSAMENTO[/bold green]")
    console.print("[bold green]" + "="*70 + "[/bold green]")
    
    # Criar tabela de estatísticas
    stats_table = Table(show_header=True, header_style="bold cyan")
    stats_table.add_column("Métrica", style="blue")
    stats_table.add_column("Valor", justify="right", style="green")
    
    stats_table.add_row("Modo de Operação", "Gerar Novos" if action == "generate" else f"Carregar PKL: {pkl_file}")
    stats_table.add_row("Embeddings Processados", str(global_stats['embeddings_gerados']))
    stats_table.add_row("Embeddings Atualizados no Banco", str(global_stats['embeddings_atualizados']))
    stats_table.add_row("Erros", str(global_stats['erros']))
    
    if action == "generate" and 'pkl_filepath' in locals() and pkl_filepath:
        stats_table.add_row("Arquivo PKL Salvo", os.path.basename(pkl_filepath))
        stats_table.add_row("Caminho Completo", pkl_filepath)
    elif action == "load":
        stats_table.add_row("Arquivo PKL Carregado", pkl_file)
    
    console.print(stats_table)
    
    console.print(f"\n[green]Categorias processadas: {len(df_categories)}[/green]")
    console.print(f"[green]Tempo total: {tempo_total:.2f} segundos[/green]")
    
    # Verificação final
    console.print("\n[bold blue]Verificando resultado final...[/bold blue]")
    final_categories = load_categories_without_embeddings()
    if final_categories is not None:
        remaining = len(final_categories)
        console.print(f"[{'yellow' if remaining > 0 else 'green'}]Categorias restantes sem embeddings: {remaining}[/{'yellow' if remaining > 0 else 'green'}]")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        console.print("\n[bold green]🎉 Processamento concluído com sucesso![/bold green]")
    else:
        console.print("\n[bold red]❌ Processamento finalizado com erros![/bold red]")
