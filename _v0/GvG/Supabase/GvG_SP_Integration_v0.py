import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import threading
import random
import shutil
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

# Adicionar caminho para importar módulos de pré-processamento
sys.path.append("C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\#GOvGO\\python\\GvG\\Boletim\\PP\\")

# Importar funções de pré-processamento do GvG_PP_v0
try:
    from GvG_PP_v0 import (
        gvg_pre_processing, 
        gvg_create_embedding_filename,
        gvg_parse_embedding_filename, 
        EMBEDDING_MODELS, 
        EMBEDDING_MODELS_REVERSE
    )
except ImportError:
    print("ERRO: Não foi possível importar o módulo de pré-processamento.")
    sys.exit(1)

# Configure Rich console
console = Console()

# Load environment variables from .env
env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
console.print(f"[blue]Buscando arquivo .env em: {env_path}")
load_dotenv(dotenv_path=env_path)

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

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
NEW_PATH = BASE_PATH + "INPUT\\NEW\\"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\USING\\"

# Configurações para processamento paralelo
MAX_WORKERS = 10
BATCH_SIZE = 100

# Lock para controle de concorrência
stats_lock = threading.Lock()
embedding_lock = threading.Lock()

# Configurações OpenAI
client = OpenAI(api_key="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")

# Estatísticas globais
global_stats = {
    'contratacoes_inseridas': 0,
    'embeddings_inseridos': 0,
    'contratacoes_duplicadas': 0,
    'embeddings_duplicados': 0,
    'embeddings_gerados': 0,
    'embeddings_pulados': 0,
    'erros': 0
}

# Configurações de embedding
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_MODEL_INDEX = EMBEDDING_MODELS_REVERSE.get(EMBEDDING_MODEL, 0)
EMBEDDING_DIM = 3072  # Dimensão para text-embedding-3-large

preprocessing_options = None

# Arquivo de embeddings
GVG_EMBEDDINGS_FILE = None

#############################################
# FUNÇÕES REUTILIZADAS DE GvG_EG_v1_4
#############################################

def get_embedding_dimension(model_name):
    """Retorna a dimensão do modelo de embedding"""
    models_dims = {
        "text-embedding-3-large": 3072,
        "text-embedding-3-small": 1536,
        "text-embedding-ada-002": 1536
    }
    return models_dims.get(model_name, 1536)

def prepare_vector_for_postgres(numpy_array):
    """Converte numpy array para lista Python"""
    return numpy_array.tolist()

def load_embeddings(filepath):
    """Carrega dicionário de embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings_dict = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath} ({len(embeddings_dict)} registros)[/green]")
            return embeddings_dict
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return {}

def save_embeddings(embeddings_dict, filepath):
    """Salva dicionário de embeddings em arquivo pickle."""
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(embeddings_dict, f)
        console.print(f"[green]Embeddings salvos em {filepath} ({len(embeddings_dict)} registros)[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
        return False

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

def partition_list(lst, n):
    """Divide uma lista em n partições aproximadamente iguais."""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n)]

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

#############################################
# FUNÇÕES REUTILIZADAS DE GvG_SP_Import_v2
#############################################

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

def execute_with_retry(cursor, sql, params, max_retries=3, worker_id=None):
    """Executa SQL com retry e backoff exponencial"""
    for attempt in range(max_retries):
        try:
            cursor.execute(sql, params)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    if worker_id:
                        console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            if worker_id:
                console.print(f"[red]Worker {worker_id} - Erro definitivo: {e}[/red]")
            raise
    return False

def execute_batch_with_retry(cursor, sql, data_list, worker_id, max_retries=3):
    """Executa inserção em lote com retry"""
    for attempt in range(max_retries):
        try:
            # Usar batch_size igual ao tamanho da lista para inserção única
            execute_values(cursor, sql, data_list, template=None, page_size=len(data_list))
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            console.print(f"[red]Worker {worker_id} - Erro definitivo em lote: {e}[/red]")
            raise
    return False

def load_existing_records(connection):
    """Carrega registros existentes para verificação de duplicatas"""
    cursor = connection.cursor()
    try:
        # Carregar IDs com commit read
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        
        # Carregar IDs de contratações existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes")
        existing_contracts = set(row[0] for row in cursor.fetchall())
        
        # Carregar IDs de embeddings existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes_embeddings")
        existing_embeddings = set(row[0] for row in cursor.fetchall())
        
        # Finalizar a transação de leitura
        connection.commit()
        
        console.print(f"[cyan]Contratações existentes: {len(existing_contracts)}[/cyan]")
        console.print(f"[cyan]Embeddings existentes: {len(existing_embeddings)}[/cyan]")
        
        return existing_contracts, existing_embeddings
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao carregar registros existentes: {e}[/bold red]")
        return set(), set()
    finally:
        cursor.close()

# Função para criar nome de arquivo de embeddings baseado nas opções
def find_latest_embeddings():
    """Encontra o arquivo de embeddings mais recente e extrai suas opções de pré-processamento"""
    global preprocessing_options
    
    try:
        # Buscar todos os arquivos de embeddings existentes
        embedding_files = [f for f in os.listdir(EMBEDDINGS_PATH) if f.endswith('.pkl') and f.startswith("GvG_embeddings_")]
        
        if not embedding_files:
            # Se não existem arquivos, definir opções padrão
            preprocessing_options = {
                "remove_special_chars": True,     # a: True
                "keep_separators": False,         # X: False
                "remove_accents": True,           # S: True
                "case": "lower",                  # o: lower
                "remove_stopwords": True,         # w: True
                "lemmatize": True                 # l: True
            }
            console.print("[yellow]Nenhum arquivo de embeddings encontrado. Usando configurações padrão (aXSowl).[/yellow]")
            
            # Criar nome de arquivo baseado nas configurações padrão
            new_filename = gvg_create_embedding_filename(EMBEDDINGS_PATH, EMBEDDING_MODEL_INDEX, preprocessing_options)
            return new_filename
        
        # Ordenar por data de modificação (mais recente primeiro)
        embedding_files.sort(key=lambda f: os.path.getmtime(os.path.join(EMBEDDINGS_PATH, f)), reverse=True)
        
        # Tentar usar o arquivo mais recente
        latest_file = embedding_files[0]
        latest_path = os.path.join(EMBEDDINGS_PATH, latest_file)
        
        # Extrair configurações do nome do arquivo
        try:
            model_name, model_idx, detected_options = gvg_parse_embedding_filename(latest_path)
            
            # Verificar se o modelo do arquivo é compatível com o modelo que queremos usar
            if model_idx == EMBEDDING_MODEL_INDEX:
                # Modelo compatível - usar as configurações do arquivo
                preprocessing_options = detected_options
                console.print(f"[green]Encontrado arquivo de embeddings: {latest_file}[/green]")
                console.print(f"[green]Usando configurações detectadas: {preprocessing_options}[/green]")
                return latest_path
            else:
                # Modelo incompatível - procurar outro arquivo com o modelo correto
                console.print(f"[yellow]Arquivo mais recente usa modelo incompatível: {model_name} (índice {model_idx})[/yellow]")
                console.print(f"[yellow]Procurando outro arquivo com o modelo {EMBEDDING_MODEL} (índice {EMBEDDING_MODEL_INDEX})...[/yellow]")
                
                # Procurar nos outros arquivos
                for file in embedding_files[1:]:
                    file_path = os.path.join(EMBEDDINGS_PATH, file)
                    try:
                        file_model_name, file_model_idx, file_options = gvg_parse_embedding_filename(file_path)
                        if file_model_idx == EMBEDDING_MODEL_INDEX:
                            # Encontramos um arquivo com o modelo correto
                            preprocessing_options = file_options
                            console.print(f"[green]Encontrado arquivo compatível: {file}[/green]")
                            console.print(f"[green]Usando configurações detectadas: {preprocessing_options}[/green]")
                            return file_path
                    except Exception as e:
                        console.print(f"[yellow]Erro ao analisar arquivo {file}: {e}[/yellow]")
                        continue
        
        except Exception as e:
            console.print(f"[yellow]Erro ao analisar o arquivo mais recente: {e}[/yellow]")
            # Tentativa de fallback: usar qualquer arquivo válido
            for file in embedding_files[1:]:
                try:
                    file_path = os.path.join(EMBEDDINGS_PATH, file)
                    model_name, model_idx, detected_options = gvg_parse_embedding_filename(file_path)
                    preprocessing_options = detected_options
                    console.print(f"[yellow]Usando arquivo alternativo: {file}[/yellow]")
                    console.print(f"[yellow]Configurações detectadas: {preprocessing_options}[/yellow]")
                    return file_path
                except Exception:
                    continue
        
        # Se chegou aqui, não encontrou nenhum arquivo válido ou compatível
        # Definir opções padrão
        preprocessing_options = {
            "remove_special_chars": True,     # a: True
            "keep_separators": False,         # X: False
            "remove_accents": True,           # S: True
            "case": "lower",                  # o: lower
            "remove_stopwords": True,         # w: True
            "lemmatize": True                 # l: True
        }
        console.print("[yellow]Não foi possível encontrar um arquivo compatível. Usando configurações padrão (aXSowl).[/yellow]")
        
        # Criar novo arquivo com o modelo desejado e opções padrão
        new_filename = gvg_create_embedding_filename(EMBEDDINGS_PATH, EMBEDDING_MODEL_INDEX, preprocessing_options)
        return new_filename
        
    except Exception as e:
        # Em caso de erro, definir opções padrão
        preprocessing_options = {
            "remove_special_chars": True,
            "keep_separators": False,
            "remove_accents": True,
            "case": "lower",
            "remove_stopwords": True,
            "lemmatize": True
        }
        console.print(f"[bold red]Erro ao buscar embeddings: {e}[/bold red]")
        
        # Criar nome de arquivo padrão
        default_filename = gvg_create_embedding_filename(EMBEDDINGS_PATH, EMBEDDING_MODEL_INDEX, preprocessing_options)
        return default_filename
    
def partition_dataframe(df, n_partitions):
    """Divide DataFrame em partições equilibradas"""
    k, m = divmod(len(df), n_partitions)
    return [df.iloc[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n_partitions)]

def check_tables_exist():
    """Verifica se as tabelas necessárias existem"""
    connection = create_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        count = cursor.fetchone()[0]
        connection.commit()
        return count == 2
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao verificar tabelas: {e}[/bold red]")
        return False
    
    finally:
        cursor.close()
        connection.close()

#############################################
# NOVAS FUNÇÕES INTEGRADAS
#############################################


# Substitua a função process_embedding_batch por completo:
def process_embedding_batch(worker_id, batch_df, embeddings_dict, progress, task_id):
    """Processa um lote de descrições para geração de embeddings"""
    local_embeddings = {}
    local_stats = {'embeddings_gerados': 0, 'embeddings_pulados': 0, 'erros': 0}
    
    try:
        # Preparar textos para processamento em sublotes de BATCH_SIZE
        texts_to_process = []
        ids_to_process = []
        
        # Pré-processar as descrições e preparar para embeddings
        for idx, row in batch_df.iterrows():
            try:
                numero_controle = str(row['numeroControlePNCP'])
                
                # VERIFICAR SE JÁ EXISTE NO DICIONÁRIO DE EMBEDDINGS
                if numero_controle in embeddings_dict:
                    # Já temos o embedding para este ID, pular
                    local_stats['embeddings_pulados'] += 1
                    # Atualizar progresso mesmo para itens pulados
                    progress.update(task_id, advance=1)
                    continue
                
                # Pré-processar o texto usando as opções configuradas
                processed_text = gvg_pre_processing(
                    row['descricaoCompleta'],
                    remove_special_chars=preprocessing_options['remove_special_chars'],
                    keep_separators=preprocessing_options['keep_separators'],
                    remove_accents=preprocessing_options['remove_accents'],
                    case=preprocessing_options['case'],
                    remove_stopwords=preprocessing_options['remove_stopwords'],
                    lemmatize=preprocessing_options['lemmatize']
                )
                
                texts_to_process.append(processed_text)
                ids_to_process.append(numero_controle)
                
            except Exception as e:
                console.print(f"[red]Worker {worker_id} - Erro ao pré-processar texto {idx}: {e}[/red]")
                local_stats['erros'] += 1
                progress.update(task_id, advance=1)  # Atualizar progresso mesmo para erros
        
        # Se não há textos para processar, retornar
        if not texts_to_process:
            console.print(f"[yellow]Worker {worker_id} - Nenhum texto novo para processar (todos já existem)[/yellow]")
            return local_embeddings, local_stats
        
        # Processar os textos em lotes para evitar limites da API
        for i in range(0, len(texts_to_process), BATCH_SIZE):
            batch_texts = texts_to_process[i:i+BATCH_SIZE]
            batch_ids = ids_to_process[i:i+BATCH_SIZE]
            
            try:
                # Obter embeddings para o lote atual
                batch_embeddings = process_batch(batch_texts, model=EMBEDDING_MODEL)
                
                # Mapear embeddings para seus IDs
                for j, embedding in enumerate(batch_embeddings):
                    if embedding is not None and not np.all(embedding == 0):  # Verificar se não é um embedding vazio
                        local_embeddings[batch_ids[j]] = embedding
                        local_stats['embeddings_gerados'] += 1
                    else:
                        local_stats['erros'] += 1
                
                # Atualizar progresso
                progress.update(task_id, advance=len(batch_texts))
                
            except Exception as e:
                console.print(f"[bold red]Worker {worker_id} - Erro ao processar lote de embeddings: {e}[/bold red]")
                local_stats['erros'] += len(batch_texts)
                progress.update(task_id, advance=len(batch_texts))
        
        # Adicionar embeddings ao dicionário global de forma thread-safe
        with embedding_lock:
            embeddings_dict.update(local_embeddings)
        
        # Atualizar estatísticas globais
        update_global_stats(
            embeddings_gerados=local_stats['embeddings_gerados'],
            embeddings_pulados=local_stats['embeddings_pulados'],
            erros=local_stats['erros']
        )
        
        # Log de resumo do worker
        console.print(f"[cyan]Worker {worker_id} - Gerados: {local_stats['embeddings_gerados']}, " +
                      f"Pulados: {local_stats['embeddings_pulados']}, Erros: {local_stats['erros']}[/cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Worker {worker_id} - Erro geral ao processar embeddings: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
        progress.update(task_id, advance=len(batch_df))
    
    return local_embeddings, local_stats

def process_db_batch(worker_id, batch_df, embeddings_dict, existing_contracts, existing_embeddings, progress, task_id):
    """Processa um lote para inserção no banco de dados"""
    # Criar conexão dedicada para este worker
    connection = create_connection()
    if not connection:
        console.print(f"[bold red]Worker {worker_id} não conseguiu criar conexão![/bold red]")
        return {
            'contratacoes_inseridas': 0,
            'embeddings_inseridos': 0,
            'contratacoes_duplicadas': 0,
            'embeddings_duplicados': 0,
            'erros': len(batch_df)
        }
    
    cursor = connection.cursor()
    
    # Estatísticas locais para este worker
    local_stats = {
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'erros': 0
    }
    
    try:
        # Processar registros em lotes menores para atualizar o progresso frequentemente
        for i in range(0, len(batch_df), BATCH_SIZE):
            sublote = batch_df.iloc[i:i+BATCH_SIZE]
            
            contract_data = []
            embedding_data = []
            
            # Preparar dados para inserção
            for _, row in sublote.iterrows():
                try:
                    numero_controle = str(row['numeroControlePNCP'])
                    
                    # Preparar contratação se não existir
                    if numero_controle not in existing_contracts:
                        try:
                            contract_data.append((
                                numero_controle,
                                int(row['anoCompra']),
                                row['descricaoCompleta'],
                                float(row['valorTotalHomologado']),
                                row['dataAberturaProposta'],
                                row['dataEncerramentoProposta'],
                                row['unidadeOrgao_ufSigla'],
                                row['unidadeOrgao_municipioNome'],
                                row['unidadeOrgao_nomeUnidade'],
                                row['orgaoEntidade_razaosocial']
                            ))
                            existing_contracts.add(numero_controle)
                            local_stats['contratacoes_inseridas'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar contratação {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    else:
                        local_stats['contratacoes_duplicadas'] += 1
                    
                    # Preparar embedding se disponível
                    if (numero_controle in embeddings_dict and 
                        numero_controle not in existing_embeddings):
                        try:
                            embedding_vector = embeddings_dict[numero_controle]
                            vector_list = prepare_vector_for_postgres(embedding_vector)
                            
                            metadata = {
                                'dimensoes': len(embedding_vector),
                                'data_geracao': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            embedding_data.append((
                                numero_controle,
                                vector_list,
                                EMBEDDING_MODEL,
                                json.dumps(metadata)
                            ))
                            existing_embeddings.add(numero_controle)
                            local_stats['embeddings_inseridos'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar embedding {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    elif numero_controle in embeddings_dict:
                        local_stats['embeddings_duplicados'] += 1
                
                except Exception as e:
                    local_stats['erros'] += 1
                    console.print(f"[red]Worker {worker_id} - Erro geral em {numero_controle}: {e}[/red]")
            
            # INSERÇÕES EM TRANSAÇÃO ÚNICA
            try:
                # Inserir contratações em lote
                if contract_data:
                    contract_sql = """
                        INSERT INTO contratacoes (
                            numeroControlePNCP, anoCompra, descricaoCompleta,
                            valorTotalHomologado, dataAberturaProposta, dataEncerramentoProposta,
                            unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                            unidadeOrgao_nomeUnidade, orgaoEntidade_razaosocial
                        ) VALUES %s
                    """
                    
                    execute_batch_with_retry(cursor, contract_sql, contract_data, worker_id)
                
                # Inserir embeddings individualmente (devido ao pgvector)
                if embedding_data:
                    for emb_data in embedding_data:
                        single_emb_sql = """
                            INSERT INTO contratacoes_embeddings (
                                numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                            ) VALUES (%s, %s::vector, %s, %s)
                        """
                        execute_with_retry(cursor, single_emb_sql, emb_data, worker_id=worker_id)
                
                # Commit da transação
                connection.commit()
                
                # Atualizar progresso
                progress.update(task_id, advance=len(sublote))
                
                # Breve pausa para reduzir contenção
                time.sleep(0.05)
                
            except Exception as e:
                connection.rollback()
                console.print(f"[bold red]Worker {worker_id} - Erro na transação: {e}[/bold red]")
                local_stats['erros'] += len(sublote)
                progress.update(task_id, advance=len(sublote))
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Worker {worker_id} - Erro geral: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
    
    finally:
        cursor.close()
        connection.close()
    
    # Atualizar estatísticas globais
    update_global_stats(
        contratacoes_inseridas=local_stats['contratacoes_inseridas'],
        embeddings_inseridos=local_stats['embeddings_inseridos'],
        contratacoes_duplicadas=local_stats['contratacoes_duplicadas'],
        embeddings_duplicados=local_stats['embeddings_duplicados'],
        erros=local_stats['erros']
    )
    
    return local_stats

def process_excel_file(file_path):
    """Processa um arquivo Excel: gera embeddings e insere no banco de dados"""
    try:
        # Verificar se as tabelas existem no banco
        if not check_tables_exist():
            console.print("[bold red]As tabelas necessárias não existem no banco de dados![/bold red]")
            return False
        
        # Carregar o arquivo Excel
        df = pd.read_excel(file_path)
        console.print(f"[green]Arquivo carregado: {len(df)} registros[/green]")
        
        # Verificar colunas necessárias
        required_columns = [
            'numeroControlePNCP', 'anoCompra', 'descricaoCompleta', 
            'valorTotalHomologado', 'dataAberturaProposta', 'dataEncerramentoProposta', 
            'unidadeOrgao_ufSigla', 'unidadeOrgao_municipioNome', 
            'unidadeOrgao_nomeUnidade', 'orgaoEntidade_razaosocial'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            console.print(f"[bold red]Colunas faltando: {', '.join(missing_columns)}[/bold red]")
            return False
        
        # Processar tipos de dados
        df['anoCompra'] = pd.to_numeric(df['anoCompra'], errors='coerce').fillna(0).astype(int)
        
        if len(df) > 0 and isinstance(df['valorTotalHomologado'].iloc[0], str):
            df['valorTotalHomologado'] = df['valorTotalHomologado'].str.replace(',', '.').astype(float)
        
        date_columns = ['dataAberturaProposta', 'dataEncerramentoProposta']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Encontrar e carregar arquivo de embeddings existente
        global GVG_EMBEDDINGS_FILE
        GVG_EMBEDDINGS_FILE = find_latest_embeddings()

        # Verificar se temos um arquivo válido e opções de pré-processamento
        if GVG_EMBEDDINGS_FILE is None or preprocessing_options is None:
            console.print("[bold red]Erro crítico: Não foi possível determinar o arquivo de embeddings ou as opções de pré-processamento![/bold red]")
            return False
        
        # Carregar embeddings existentes
        embeddings_dict = load_embeddings(GVG_EMBEDDINGS_FILE) if os.path.exists(GVG_EMBEDDINGS_FILE) else {}
        
        # Criar conexão para verificar registros existentes
        connection = create_connection()
        if not connection:
            console.print("[bold red]Não foi possível conectar ao banco![/bold red]")
            return False
        
        # Carregar registros existentes para verificação de duplicatas
        existing_contracts, existing_embeddings = load_existing_records(connection)
        connection.close()
        
        # Dividir em partições para processamento paralelo
        partitions = partition_dataframe(df, MAX_WORKERS)
        partitions = [p for p in partitions if len(p) > 0]  # Remover partições vazias
        
        console.print(f"[cyan]Processando {len(df)} registros com {len(partitions)} workers[/cyan]")
        
        # FASE 1: Gerar embeddings em paralelo
        console.print("\n[bold magenta]FASE 1: Gerando Embeddings[/bold magenta]")
        
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
                        process_embedding_batch,
                        worker_id + 1,               # ID do worker
                        partition,                   # Dados a processar
                        embeddings_dict,             # Dicionário de embeddings
                        progress,                    # Objeto de progresso
                        tasks[worker_id]             # ID da tarefa visual
                    )
                    futures.append(future)
                
                # Aguardar conclusão de todos os workers
                for future in futures:
                    try:
                        _, _ = future.result()
                    except Exception as e:
                        console.print(f"[bold red]Erro em worker de embedding: {e}[/bold red]")
        
        # Salvar embeddings após processamento
        save_embeddings(embeddings_dict, GVG_EMBEDDINGS_FILE)
        console.print(f"[green]Embeddings salvos em {os.path.basename(GVG_EMBEDDINGS_FILE)}[/green]")
        
        # FASE 2: Inserir dados no banco
        console.print("\n[bold magenta]FASE 2: Inserindo Dados no Banco[/bold magenta]")
        
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
                    f"Worker {worker_id+1}/{len(partitions)} - Inserindo no banco", 
                    total=len(partitions[worker_id])
                )
                tasks.append(task)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for worker_id, partition in enumerate(partitions):
                    future = executor.submit(
                        process_db_batch,
                        worker_id + 1,               # ID do worker
                        partition,                   # Dados a processar
                        embeddings_dict,             # Embeddings
                        existing_contracts.copy(),   # Cópia para evitar conflitos
                        existing_embeddings.copy(),  # Cópia para evitar conflitos
                        progress,                    # Objeto de progresso
                        tasks[worker_id]             # ID da tarefa visual
                    )
                    futures.append(future)
                
                # Aguardar conclusão de todos os workers
                results = []
                for future in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        console.print(f"[bold red]Erro em worker de banco: {e}[/bold red]")
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file_path)}: {e}[/bold red]")
        return False

def main():
    """Função principal que orquestra o processamento"""
    console.print(Panel("[bold magenta]SISTEMA INTEGRADO DE EMBEDDINGS E IMPORTAÇÃO PARA SUPABASE[/bold magenta]"))
    console.print(f"[cyan]Configuração: {MAX_WORKERS} Workers | Batch Size: {BATCH_SIZE} | Modelo: {EMBEDDING_MODEL}[/cyan]")
    
    # Verificar se os diretórios existem
    os.makedirs(NEW_PATH, exist_ok=True)
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    # Buscar arquivos Excel no diretório NEW_PATH
    excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        console.print("[yellow]Nenhum arquivo Excel encontrado em {}[/yellow]".format(NEW_PATH))
        return
    
    console.print(f"[green]Encontrados {len(excel_files)} arquivos para processamento.[/green]")
    
    # Resetar estatísticas globais
    global_stats.update({
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'embeddings_gerados': 0,
        'erros': 0
    })
    
    # Iniciar cronômetro
    inicio = time.time()
    
    # Processar cada arquivo Excel
    for i, excel_file in enumerate(excel_files, 1):
        excel_path = os.path.join(NEW_PATH, excel_file)
        console.print(f"\n[bold blue][{i}/{len(excel_files)}] Processando: {excel_file}[/bold blue]")
        
        # Processar o arquivo
        process_excel_file(excel_path)
    
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

    stats_table.add_row("Embeddings Gerados", str(global_stats['embeddings_gerados']))
    stats_table.add_row("Embeddings Pulados (já existiam)", str(global_stats['embeddings_pulados']))
    stats_table.add_row("Contratações Inseridas", str(global_stats['contratacoes_inseridas']))
    stats_table.add_row("Embeddings Inseridos", str(global_stats['embeddings_inseridos']))
    stats_table.add_row("Contratações Duplicadas", str(global_stats['contratacoes_duplicadas']))
    stats_table.add_row("Embeddings Duplicados", str(global_stats['embeddings_duplicados']))
    stats_table.add_row("Erros", str(global_stats['erros']))
    console.print(stats_table)
    
    console.print(f"\n[green]Arquivos processados: {len(excel_files)}[/green]")
    console.print(f"[green]Tempo total: {tempo_total:.2f} segundos[/green]")
    
    # Perguntar se deseja mover os arquivos para outro diretório
    resposta = input("\nDeseja mover os arquivos processados para outro diretório? (s/n): ").strip().lower()
    if resposta in ['s', 'sim']:
        old_path = BASE_PATH + "INPUT\\OLD\\"
        os.makedirs(old_path, exist_ok=True)
        
        for excel_file in excel_files:
            source = os.path.join(NEW_PATH, excel_file)
            
            # Verificar se já existe um arquivo com o mesmo nome no destino
            destino = os.path.join(old_path, excel_file)
            if os.path.exists(destino):
                # Adicionar timestamp para evitar sobrescrever
                nome, ext = os.path.splitext(excel_file)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                destino = os.path.join(old_path, f"{nome}_{timestamp}{ext}")
            
            try:
                shutil.move(source, destino)
                console.print(f"[green]Arquivo movido: {excel_file} -> {os.path.basename(destino)}[/green]")
            except Exception as e:
                console.print(f"[red]Erro ao mover arquivo {excel_file}: {e}[/red]")

if __name__ == "__main__":
    main()