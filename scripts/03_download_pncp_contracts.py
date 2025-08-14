# =======================================================================
# DOWNLOAD PARALELO OTIMIZADO DA API PNCP PARA POSTGRESQL V1
# =======================================================================
# Esta é uma versão otimizada do script 03 com paralelismo real para itens:
# - Divisão balanceada de contratações entre workers (MAX_WORKERS = 20)
# - Remoção do Semaphore para máximo throughput
# - Paralelismo verdadeiro: cada worker processa lote completo
# - Constraints otimizadas com verificação prévia
# - Logs organizados na pasta logs/
# - Rate limiting removido para máxima performance
# =======================================================================

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import os
import datetime
import re
import concurrent.futures
import sys
import json
import time
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TaskProgressColumn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import threading
from collections import defaultdict
import argparse

# =======================================================================
# CONFIGURAÇÕES GLOBAIS
# =======================================================================

MAX_WORKERS = 20  # Paralelismo otimizado para itens de contratação

# Configuração do console Rich
console = Console()

# =======================================================================
# CONFIGURAÇÃO DE LOGGING OTIMIZADA
# =======================================================================

import logging

# Configuração de logging unificado
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_dir = os.path.dirname(script_dir)  # v1/
logs_dir = os.path.join(v1_dir, "logs")  # v1/logs/
os.makedirs(logs_dir, exist_ok=True)

# Usar timestamp do pipeline (passado via variável de ambiente) ou gerar novo
pipeline_timestamp = os.getenv('PIPELINE_TIMESTAMP')
pipeline_step = os.getenv('PIPELINE_STEP', 'ETAPA_1_DOWNLOAD')

if not pipeline_timestamp:
    pipeline_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_FILE = os.path.join(logs_dir, f"log_{pipeline_timestamp}.log")

# Configurar logger
logger = logging.getLogger('pncp_parallel_download')
logger.setLevel(logging.DEBUG)

# Formatter limpo sem timestamp/nível e sem prefixo de etapa
file_formatter = logging.Formatter('%(message)s')

# Handler para arquivo (modo append para log compartilhado)
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def log_message(message, log_type="info", debug_mode=False):
    """Log padronizado para o pipeline com modo debug e arquivo de log"""
    
    # Sempre escrever no arquivo de log
    if log_type == "info":
        logger.info(message)
    elif log_type == "success":
        logger.info(f"SUCCESS: {message}")
    elif log_type == "warning":
        logger.warning(message)
    elif log_type == "error":
        logger.error(message)
    elif log_type == "debug":
        logger.debug(message)
    
    # Mostrar no console apenas se for modo debug ou não for debug message
    if not debug_mode and log_type == "debug":
        return  # Não mostra mensagens debug se modo debug estiver desativado
        
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

def log_session_start(args):
    """Inicia uma nova sessão de log com informações do contexto"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[1/3] DOWNLOAD PNCP PARALELO INICIADO")
    logger.info("=" * 80)
    logger.info(f"MAX_WORKERS configurado: {MAX_WORKERS}")
    logger.info(f"Argumentos: {vars(args)}")
    logger.info("-" * 80)

def log_session_end(total_contratacoes, total_itens, dates, error_counts):
    """Finaliza a sessão de log com resumo"""
    logger.info("-" * 80)
    logger.info("DOWNLOAD PNCP PARALELO FINALIZADO")
    logger.info(f"Datas processadas: {len(dates)}")
    logger.info(f"Contratações inseridas: {total_contratacoes:,}")
    logger.info(f"Itens inseridos: {total_itens:,}")
    if dates:
        logger.info(f"Período processado: {dates[0]} até {dates[-1]}")
    logger.info("=" * 80)

# =======================================================================
# CONFIGURAÇÕES DE AMBIENTE
# =======================================================================

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
db_dir = os.path.join(v1_root, "db")

# Adicionar db ao path para importar o mapeamento
sys.path.insert(0, db_dir)

load_dotenv(os.path.join(v1_root, ".env"))

# Importar mapeamento PNCP
from de_para_pncp_v1 import DE_PARA_PNCP, apply_field_transformation, get_table_fields

# Configurações do banco PostgreSQL V1 (Supabase)
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}


# =======================================================================
# CLIENTE API OTIMIZADO (SEM RATE LIMITING)
# =======================================================================

class OptimizedAPIClient:
    """Cliente otimizado para API PNCP sem rate limiting para máximo throughput"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        # REMOVIDO: self.rate_limiter = threading.Semaphore(3) 
        self.error_counts = defaultdict(int)  # Contador de erros por endpoint
        self.backoff_delays = defaultdict(float)  # Delays por endpoint
        self.lock = threading.Lock()
        
    def setup_session(self):
        """Configura session com retry strategy robusta"""
        # Estratégia de retry mais agressiva
        retry_strategy = Retry(
            total=5,  # Total de tentativas
            status_forcelist=[408, 429, 500, 502, 503, 504],  # Status codes para retry
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Atualizado para versões recentes
            backoff_factor=2,  # Backoff exponencial: 2, 4, 8, 16 segundos
            raise_on_status=False
        )
        
        # Adapter com retry
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,  # Aumentado para suportar mais workers
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers para parecer mais humano
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
    def adaptive_timeout(self, endpoint_key):
        """Calcula timeout adaptativo baseado no histórico de erros"""
        error_count = self.error_counts[endpoint_key]
        base_timeout = 45  # Timeout base aumentado
        
        if error_count == 0:
            return base_timeout
        elif error_count <= 2:
            return base_timeout + 15  # 60s
        elif error_count <= 5:
            return base_timeout + 30  # 75s
        else:
            return base_timeout + 60  # 105s
            
    def should_circuit_break(self, endpoint_key):
        """Determina se deve aplicar circuit breaker"""
        return self.error_counts[endpoint_key] >= 8
        
    def get_backoff_delay(self, endpoint_key):
        """Calcula delay de backoff para o endpoint"""
        with self.lock:
            current_delay = self.backoff_delays[endpoint_key]
            if current_delay == 0:
                self.backoff_delays[endpoint_key] = 1
                return 1
            else:
                new_delay = min(current_delay * 1.5, 30)  # Máximo 30s
                self.backoff_delays[endpoint_key] = new_delay
                return new_delay
                
    def reset_backoff(self, endpoint_key):
        """Reset do backoff após sucesso"""
        with self.lock:
            self.backoff_delays[endpoint_key] = 0
            
    def optimized_get(self, url, params=None, endpoint_key=None, debug_mode=False):
        """GET request otimizado SEM rate limiting"""
        if endpoint_key is None:
            endpoint_key = url
            
        # Circuit breaker
        if self.should_circuit_break(endpoint_key):
            log_message(f"Circuit breaker ativo para {endpoint_key} - pulando", "warning", debug_mode)
            return None
            
        # REMOVIDO: Rate limiting - agora sem semáforo para máximo throughput
        # Backoff delay se necessário
        delay = self.get_backoff_delay(endpoint_key)
        if delay > 1:
            log_message(f"Aguardando {delay:.1f}s antes de tentar {endpoint_key}", "debug", debug_mode)
            time.sleep(delay)
            
        timeout = self.adaptive_timeout(endpoint_key)
        
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                # Sucesso - reset do backoff
                self.reset_backoff(endpoint_key)
                with self.lock:
                    if self.error_counts[endpoint_key] > 0:
                        self.error_counts[endpoint_key] -= 1  # Decrementa gradualmente
                return response
                
            elif response.status_code == 204:
                # Sem dados - também é sucesso
                self.reset_backoff(endpoint_key)
                return response
                
            elif response.status_code in [408, 429]:
                # Timeouts específicos - espera mais
                with self.lock:
                    self.error_counts[endpoint_key] += 1
                log_message(f"HTTP {response.status_code} para {endpoint_key} - timeout do servidor", "warning", debug_mode)
                time.sleep(5)  # Espera adicional para 408/429
                return None
                
            else:
                with self.lock:
                    self.error_counts[endpoint_key] += 1
                log_message(f"HTTP {response.status_code} para {endpoint_key}", "warning", debug_mode)
                return None
                
        except requests.exceptions.Timeout:
            with self.lock:
                self.error_counts[endpoint_key] += 1
            log_message(f"Timeout ({timeout}s) para {endpoint_key}", "warning", debug_mode)
            return None
            
        except requests.exceptions.ConnectionError as e:
            with self.lock:
                self.error_counts[endpoint_key] += 1
            log_message(f"Erro de conexão para {endpoint_key}: {str(e)}", "error", debug_mode)
            time.sleep(2)
            return None
            
        except Exception as e:
            with self.lock:
                self.error_counts[endpoint_key] += 1
            log_message(f"Erro inesperado para {endpoint_key}: {str(e)}", "error", debug_mode)
            return None

# Cliente global otimizado
api_client = OptimizedAPIClient()

# =======================================================================
# FUNÇÕES AUXILIARES
# =======================================================================

def connect_to_db(max_attempts=3, retry_delay=5):
    """Conecta ao banco PostgreSQL V1 com tentativas múltiplas"""
    attempt = 1
    while attempt <= max_attempts:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.set_session(autocommit=False)
            return conn
        except psycopg2.Error as e:
            console.print(f"[bold red]Erro ao conectar ao banco (tentativa {attempt}/{max_attempts}): {e}[/bold red]")
            if attempt < max_attempts:
                console.print(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)
                attempt += 1
            else:
                console.print("[bold red]Falha ao conectar ao banco após múltiplas tentativas.[/bold red]")
                raise

def remove_illegal_chars(value):
    """Remove caracteres ilegais de strings"""
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

def clean_data(data):
    """Limpa dados removendo caracteres ilegais"""
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(item) for item in data]
    else:
        return remove_illegal_chars(data)

def normalize_contratacao_data(contract):
    """Normaliza dados de contratação da API para o schema V1"""
    return apply_field_transformation(contract, 'contratacao')

def normalize_item_data(item, numero_controle_pncp):
    """Normaliza dados de item da API para o schema V1"""
    return apply_field_transformation(item, 'item_contratacao', numero_controle_pncp)

# =======================================================================
# FUNÇÕES DE BUSCA ROBUSTAS
# =======================================================================

def fetch_by_code_robust(date_str, codigo, progress, debug_mode=False):
    """Busca dados para um único dia e código com retry robusto"""
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    endpoint_key = f"contratacoes_codigo_{codigo}"
    
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50
    }
    
    # Primeira requisição (página 1)
    response = api_client.optimized_get(base_url, params=params, endpoint_key=endpoint_key, debug_mode=debug_mode)
    
    if response is None:
        log_message(f"Falha ao buscar código {codigo} após todas as tentativas", "error", debug_mode)
        return all_data
        
    if response.status_code == 204:
        return all_data
    elif response.status_code != 200:
        return all_data
    
    try:
        json_response = response.json()
        all_data.extend(json_response.get("data", []))
        total_paginas = json_response.get("totalPaginas", 1)
        
        if total_paginas > 1:
            if debug_mode:
                task_id = progress.add_task(f"        Código {codigo}", total=total_paginas - 1)
            for page in range(2, total_paginas + 1):
                params["pagina"] = page
                page_endpoint_key = f"{endpoint_key}_page_{page}"
                
                response = api_client.optimized_get(base_url, params=params, endpoint_key=page_endpoint_key, debug_mode=debug_mode)
                
                if response is None:
                    log_message(f"Falha na página {page} para código {codigo}", "warning", debug_mode)
                    break
                    
                if response.status_code == 204:
                    break
                elif response.status_code != 200:
                    break
                    
                json_response = response.json()
                all_data.extend(json_response.get("data", []))
                if debug_mode:
                    progress.update(task_id, advance=1)
                
                # REMOVIDO: Delay entre páginas para máximo throughput
                # time.sleep(0.5)  
                
            if debug_mode and total_paginas > 1:
                progress.remove_task(task_id)
        
        return all_data
        
    except Exception as e:
        log_message(f"Erro ao processar resposta do código {codigo}: {str(e)}", "error", debug_mode)
        return all_data

def fetch_items_for_contract_batch(contracts_batch, worker_id, debug_mode=False):
    """Busca itens para um lote de contratações - NOVA FUNÇÃO PARA PARALELISMO REAL"""
    batch_items = []
    contracts_processed = 0
    contracts_with_items = 0
    items_found = 0
    
    log_message(f"Worker {worker_id}: Processando lote de {len(contracts_batch)} contratações", "debug", debug_mode)
    
    for numero_controle_pncp in contracts_batch:
        try:
            # Extrair informações do número de controle
            if not re.match(r'^\d+-\d+-\d+/\d+$', numero_controle_pncp):
                contracts_processed += 1
                continue
                
            parts = numero_controle_pncp.split("-")
            if len(parts) != 3:
                contracts_processed += 1
                continue
            
            cnpj = parts[0]
            seq_and_year = parts[2].split("/")
            if len(seq_and_year) != 2:
                contracts_processed += 1
                continue
            
            seq = seq_and_year[0]
            ano_compra = seq_and_year[1]
            sequencial_compra = str(int(seq))  # Remove zeros à esquerda
            
            # Montar URL da API de itens
            url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
            endpoint_key = f"itens_{cnpj}_{ano_compra}_{sequencial_compra}"
            
            response = api_client.optimized_get(url, endpoint_key=endpoint_key, debug_mode=debug_mode)
            
            if response is None:
                log_message(f"Worker {worker_id}: Falha ao buscar itens para {numero_controle_pncp}", "debug", debug_mode)
                contracts_processed += 1
                continue
                
            if response.status_code == 200:
                items_data = response.json()
                if items_data:
                    # CRÍTICO: Associar numero_controle_pncp a cada item
                    for item in items_data:
                        item['numero_controle_pncp'] = numero_controle_pncp  # Adicionar número de controle ao item
                    
                    batch_items.extend(items_data)
                    contracts_with_items += 1
                    items_found += len(items_data)
                    log_message(f"Worker {worker_id}: Encontrados {len(items_data)} itens para {numero_controle_pncp}", "debug", debug_mode)
            elif response.status_code == 404:
                log_message(f"Worker {worker_id}: Nenhum item encontrado para {numero_controle_pncp}", "debug", debug_mode)
            else:
                log_message(f"Worker {worker_id}: Status {response.status_code} ao buscar itens para {numero_controle_pncp}", "warning", debug_mode)
                
            contracts_processed += 1
                
        except Exception as e:
            log_message(f"Worker {worker_id}: Erro ao processar itens para {numero_controle_pncp}: {str(e)}", "warning", debug_mode)
            contracts_processed += 1
            continue
    
    log_message(f"Worker {worker_id}: Concluído - {contracts_processed} contratos processados, {items_found} itens encontrados em {contracts_with_items} contratações", "debug", debug_mode)
    
    return batch_items, contracts_processed, contracts_with_items, items_found

def fetch_items_for_contract_robust(numero_controle_pncp, debug_mode=False):
    """Busca itens para uma contratação específica - MANTIDA PARA COMPATIBILIDADE"""
    try:
        # Extrair informações do número de controle
        if not re.match(r'^\d+-\d+-\d+/\d+$', numero_controle_pncp):
            return []
            
        parts = numero_controle_pncp.split("-")
        if len(parts) != 3:
            return []
        
        cnpj = parts[0]
        seq_and_year = parts[2].split("/")
        if len(seq_and_year) != 2:
            return []
        
        seq = seq_and_year[0]
        ano_compra = seq_and_year[1]
        sequencial_compra = str(int(seq))  # Remove zeros à esquerda
        
        # Montar URL da API de itens
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
        endpoint_key = f"itens_{cnpj}_{ano_compra}_{sequencial_compra}"
        
        response = api_client.optimized_get(url, endpoint_key=endpoint_key, debug_mode=debug_mode)
        
        if response is None:
            log_message(f"Falha ao buscar itens para {numero_controle_pncp}", "debug", debug_mode)
            return []
            
        if response.status_code == 200:
            items_data = response.json()
            # CRÍTICO: Associar numero_controle_pncp a cada item
            for item in items_data:
                item['numero_controle_pncp'] = numero_controle_pncp  # Adicionar número de controle ao item
            log_message(f"Encontrados {len(items_data)} itens para {numero_controle_pncp}", "debug", debug_mode)
            return items_data
        elif response.status_code == 404:
            log_message(f"Nenhum item encontrado para {numero_controle_pncp}", "debug", debug_mode)
            return []  # Sem itens disponíveis
        else:
            log_message(f"Status {response.status_code} ao buscar itens para {numero_controle_pncp}", "warning", debug_mode)
            return []
            
    except Exception as e:
        log_message(f"Erro ao processar itens para {numero_controle_pncp}: {str(e)}", "warning", debug_mode)
        return []

# =======================================================================
# FUNÇÕES DE INSERÇÃO NO BANCO OTIMIZADAS
# =======================================================================

def constraint_exists(conn, constraint_name, table_name):
    """Verifica se uma constraint já existe"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_name = %s AND table_name = %s
        """, (constraint_name, table_name))
        
        result = cursor.fetchone()
        return result[0] > 0 if result else False
        
    except Exception as e:
        log_message(f"Erro ao verificar constraint {constraint_name}: {e}", "warning")
        return False
    finally:
        cursor.close()

def create_constraints_optimized(conn):
    """Cria constraints otimizadas com verificação prévia e CONCURRENTLY"""
    cursor = conn.cursor()
    
    try:
        # Verificar e criar constraint para contratacao apenas se não existir
        if not constraint_exists(conn, 'contratacao_numero_controle_unique', 'contratacao'):
            log_message("Criando constraint única para contratacao - pode demorar alguns minutos...", "info")
            
            # Usar CREATE INDEX CONCURRENTLY para não bloquear tabela
            cursor.execute("""
                CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_contratacao_numero_controle 
                ON contratacao (numero_controle_pncp)
            """)
            
            # Depois adicionar constraint usando o índice
            cursor.execute("""
                ALTER TABLE contratacao 
                ADD CONSTRAINT contratacao_numero_controle_unique 
                UNIQUE USING INDEX idx_contratacao_numero_controle
            """)
            
            log_message("Constraint para contratacao criada com sucesso", "success")
        else:
            log_message("Constraint para contratacao já existe - pulando", "debug")
        
        # Verificar e criar constraint para item_contratacao apenas se não existir
        if not constraint_exists(conn, 'item_contratacao_unique', 'item_contratacao'):
            log_message("Criando constraint única para item_contratacao...", "info")
            
            cursor.execute("""
                CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_item_contratacao_unique 
                ON item_contratacao (numero_controle_pncp, numero_item)
            """)
            
            cursor.execute("""
                ALTER TABLE item_contratacao 
                ADD CONSTRAINT item_contratacao_unique 
                UNIQUE USING INDEX idx_item_contratacao_unique
            """)
            
            log_message("Constraint para item_contratacao criada com sucesso", "success")
        else:
            log_message("Constraint para item_contratacao já existe - pulando", "debug")
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        log_message(f"Aviso ao criar constraints otimizadas: {str(e)}", "warning")
    finally:
        cursor.close()

def insert_contratacoes(conn, contratacoes_data):
    """Insere contratações no banco com tratamento de duplicatas"""
    if not contratacoes_data:
        return 0
        
    create_constraints_optimized(conn)
    cursor = conn.cursor()
    
    try:
        # Preparar dados para inserção
        columns = list(contratacoes_data[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        values = []
        for idx, item in enumerate(contratacoes_data):
            row = []
            for col in columns:
                value = item.get(col)
                # Converter dicionários e listas para JSON string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value) if value else None
                row.append(value)
            values.append(tuple(row))
        
        # SQL com ON CONFLICT
        sql = f"""
        INSERT INTO contratacao ({columns_str})
        VALUES %s
        ON CONFLICT (numero_controle_pncp) DO NOTHING
        """
        
        cursor.execute("SELECT COUNT(*) FROM contratacao")
        count_before = cursor.fetchone()[0]
        
        execute_values(cursor, sql, values, template=None, page_size=1000)
        
        cursor.execute("SELECT COUNT(*) FROM contratacao")
        count_after = cursor.fetchone()[0]
        
        inserted_count = count_after - count_before
        conn.commit()
        
        return inserted_count
        
    except Exception as e:
        conn.rollback()
        # Log detalhado do erro
        log_message(f"Erro ao inserir contratações: {str(e)}", "error")
        if contratacoes_data:
            log_message(f"Primeira contratação problemática: {contratacoes_data[0]}", "error")
        raise
    finally:
        cursor.close()

def insert_itens(conn, itens_data):
    """Insere itens no banco com tratamento otimizado de duplicatas e lotes"""
    if not itens_data:
        return 0
        
    # Garantir que a transação está limpa
    try:
        conn.rollback()  # Limpar qualquer transação pendente
    except:
        pass
        
    cursor = conn.cursor()
    
    try:
        # Log de início do processo
        logger.info(f"Iniciando inserção de {len(itens_data)} itens no banco")
        
        # Preparar dados para inserção
        columns = list(itens_data[0].keys())
        columns_str = ', '.join(columns)
        
        values = []
        json_conversions = 0
        for idx, item in enumerate(itens_data):
            row = []
            for col in columns:
                value = item.get(col)
                # Converter dicionários e listas para JSON string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value) if value else None
                    json_conversions += 1
                row.append(value)
            values.append(tuple(row))
        
        if json_conversions > 0:
            logger.info(f"Convertidas {json_conversions} estruturas complexas para JSON")
        
        # Processar em lotes otimizados para alta performance
        batch_size = 3000  # Aumentado para melhor performance
        total_inserted = 0
        
        if len(values) > batch_size:
            logger.info(f"Processando {len(values)} itens em lotes de {batch_size} para otimizar performance")
            
            for i in range(0, len(values), batch_size):
                batch = values[i:i + batch_size]
                logger.debug(f"Processando lote {i//batch_size + 1}: {len(batch)} itens")
                
                # SQL com ON CONFLICT para cada lote
                sql = f"""
                INSERT INTO item_contratacao ({columns_str})
                VALUES %s
                ON CONFLICT (numero_controle_pncp, numero_item) DO NOTHING
                """
                
                cursor.execute("SELECT COUNT(*) FROM item_contratacao")
                count_before = cursor.fetchone()[0]
                
                # Usar page_size otimizado para melhor throughput
                execute_values(cursor, sql, batch, template=None, page_size=1000)
                
                cursor.execute("SELECT COUNT(*) FROM item_contratacao")
                count_after = cursor.fetchone()[0]
                
                batch_inserted = count_after - count_before
                total_inserted += batch_inserted
                
                logger.debug(f"Lote {i//batch_size + 1}: {batch_inserted} novos itens inseridos")
                
        else:
            # Para quantidades menores, processar normalmente
            sql = f"""
            INSERT INTO item_contratacao ({columns_str})
            VALUES %s
            ON CONFLICT (numero_controle_pncp, numero_item) DO NOTHING
            """
            
            cursor.execute("SELECT COUNT(*) FROM item_contratacao")
            count_before = cursor.fetchone()[0]
            
            execute_values(cursor, sql, values, template=None, page_size=1000)
            
            cursor.execute("SELECT COUNT(*) FROM item_contratacao")
            count_after = cursor.fetchone()[0]
            
            total_inserted = count_after - count_before
        
        conn.commit()
        logger.info(f"Inserção de itens concluída com sucesso: {total_inserted} novos itens")
        return total_inserted
        
    except Exception as e:
        conn.rollback()
        # Log detalhado do erro
        logger.error(f"Erro ao inserir itens: {str(e)}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        raise
    finally:
        cursor.close()

# =======================================================================
# FUNÇÃO DE DIVISÃO DE LOTES PARA PARALELISMO REAL
# =======================================================================

def divide_contracts_into_batches(contracts_list, num_workers):
    """Divide lista de contratações em lotes balanceados para os workers"""
    if not contracts_list:
        return []
    
    total_contracts = len(contracts_list)
    batch_size = max(1, total_contracts // num_workers)
    
    batches = []
    for i in range(0, total_contracts, batch_size):
        batch = contracts_list[i:i + batch_size]
        if batch:  # Apenas adicionar lotes não-vazios
            batches.append(batch)
    
    # Se tivermos mais lotes que workers, combinar os últimos
    while len(batches) > num_workers:
        last_batch = batches.pop()
        batches[-1].extend(last_batch)
    
    log_message(f"Divididas {total_contracts} contratações em {len(batches)} lotes para {num_workers} workers", "debug")
    for i, batch in enumerate(batches):
        log_message(f"Lote {i+1}: {len(batch)} contratações", "debug")
    
    return batches

# =======================================================================
# PROCESSAMENTO PRINCIPAL COM PARALELISMO OTIMIZADO
# =======================================================================

def process_day_optimized(progress, date_str, conn, debug_mode=False):
    """Processa os dados para um dia específico com paralelismo otimizado"""
    
    # Formatação da data para exibição
    display_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]}"
    
    if not debug_mode:
        console.print(f"\n[bold blue]Dia {display_date}:[/bold blue]")
    
    # Verificar se a conexão está saudável e limpar transações pendentes
    try:
        conn.rollback()  # Limpar qualquer transação pendente
        cursor_test = conn.cursor()
        cursor_test.execute("SELECT 1")
        cursor_test.close()
        logger.debug(f"Conexão verificada e limpa para {date_str}")
    except Exception as e:
        logger.warning(f"Problema na conexão detectado para {date_str}: {e}")
        # Tentar reconectar
        try:
            conn.close()
        except:
            pass
        conn = connect_to_db()
        logger.info(f"Conexão reinicializada para {date_str}")
    
    all_contracts = []
    
    if debug_mode:
        day_task_id = progress.add_task(f"[bold yellow]    Processando {date_str} (códigos)", total=14)
        log_message(f"Iniciando download OTIMIZADO para {date_str} (14 modalidades)", "info", debug_mode)
    
    # Criar task para contratações
    contracts_task_id = progress.add_task("Contratações", total=14)
    
    # PARALELISMO PARA CONTRATAÇÕES: MAX_WORKERS/2 para não sobrecarregar
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, MAX_WORKERS//2)) as executor:
        futures = {
            executor.submit(fetch_by_code_robust, date_str, codigo, progress, debug_mode): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                codigo = futures[future]
                data = future.result()
                if data:
                    all_contracts.extend(data)
                    log_message(f"Código {codigo}: {len(data)} contratos", "debug", debug_mode)
                progress.update(contracts_task_id, advance=1)
            except Exception as e:
                codigo = futures[future]
                log_message(f"Erro no código {codigo}: {e}", "error", debug_mode)
                progress.update(contracts_task_id, advance=1)
    
    progress.remove_task(contracts_task_id)
    if debug_mode:
        progress.remove_task(day_task_id)
        log_message(f"Download concluído: {len(all_contracts)} contratos encontrados", "success", debug_mode)
    
    if not all_contracts:
        return 0, 0
    
    # Limpar dados
    all_contracts = clean_data(all_contracts)
    
    # VERIFICAÇÃO DE DUPLICATAS: Remover contratos duplicados antes da normalização
    unique_contracts = {}
    for contract in all_contracts:
        numero_controle = contract.get('numeroControlePNCP')
        if numero_controle and numero_controle not in unique_contracts:
            unique_contracts[numero_controle] = contract
    
    all_contracts = list(unique_contracts.values())
    log_message(f"Baixando {len(all_contracts)} contratatações", "info", debug_mode)
    
    # Guardar TODOS os números de controle para processamento de itens
    all_numeros_controle = set()
    for contract in all_contracts:
        numero_controle = contract.get('numeroControlePNCP')
        if numero_controle:
            all_numeros_controle.add(numero_controle)
    
    # Verificar duplicatas já existentes no banco APENAS para contratações
    cursor = conn.cursor()
    new_contracts = all_contracts  # Por padrão, todos são novos
    existing_contracts = set()
    
    if all_contracts:
        numeros_controle = [contract.get('numeroControlePNCP') for contract in all_contracts if contract.get('numeroControlePNCP')]
        placeholders = ','.join(['%s'] * len(numeros_controle))
        cursor.execute(f"SELECT numero_controle_pncp FROM contratacao WHERE numero_controle_pncp IN ({placeholders})", numeros_controle)
        existing_contracts = {row[0] for row in cursor.fetchall()}
        
        # Filtrar APENAS os contratos que são novos para inserção
        new_contracts = [contract for contract in all_contracts if contract.get('numeroControlePNCP') not in existing_contracts]
        if len(existing_contracts) > 0:
            log_message(f"Encontrados {len(existing_contracts)} contratos já existentes no banco", "info", debug_mode)
    
    cursor.close()
    
    # Processar contratações (apenas as novas)
    inserted_contratacoes = 0
    if new_contracts:
        # Normalizar dados de contratações (apenas contratos novos)
        contratacoes_data = []
        for contract in new_contracts:
            try:
                normalized_contract = normalize_contratacao_data(contract)
                if normalized_contract:
                    contratacoes_data.append(normalized_contract)
            except Exception as e:
                log_message(f"Erro ao normalizar contrato {contract.get('numeroControlePNCP', 'N/A')}: {str(e)}", "error", debug_mode)
        
        # Inserir contratações
        if contratacoes_data:
            inserted_contratacoes = insert_contratacoes(conn, contratacoes_data)
    else:
        log_message("Nenhum contrato novo para inserir, mas processando itens dos contratos existentes", "info", debug_mode)
    
    # =======================================================================
    # PARALELISMO REAL PARA ITENS - NOVA IMPLEMENTAÇÃO OTIMIZADA
    # =======================================================================
    
    all_items = []
    
    if all_numeros_controle:        
        # Converter set para lista para poder dividir
        contracts_list = list(all_numeros_controle)
        
        # Dividir contratos em lotes balanceados para os workers
        contract_batches = divide_contracts_into_batches(contracts_list, MAX_WORKERS)
        
        if debug_mode:
            items_task_id = progress.add_task(f"[bold cyan]    Buscando itens com {MAX_WORKERS} workers", total=len(contract_batches))
        
        # Criar task para itens
        items_progress_task_id = progress.add_task("Itens Contratações", total=len(contract_batches))
        
        # PARALELISMO REAL: MAX_WORKERS processando lotes completos
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            
            # Submeter cada lote para um worker
            for i, batch in enumerate(contract_batches):
                worker_id = i + 1
                future = executor.submit(fetch_items_for_contract_batch, batch, worker_id, debug_mode)
                futures[future] = worker_id
            
            # Coletar resultados
            total_items_found = 0
            total_contracts_with_items = 0
            total_contracts_processed = 0
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    worker_id = futures[future]
                    batch_items, contracts_processed, contracts_with_items, items_found = future.result()
                    
                    if batch_items:
                        all_items.extend(batch_items)
                    
                    total_items_found += items_found
                    total_contracts_with_items += contracts_with_items
                    total_contracts_processed += contracts_processed
                    
                    log_message(f"Worker {worker_id}: {contracts_processed} contratos processados, {items_found} itens encontrados", "debug", debug_mode)
                    
                    progress.update(items_progress_task_id, advance=1)
                    if debug_mode:
                        progress.update(items_task_id, advance=1)
                        
                except Exception as e:
                    worker_id = futures[future]
                    log_message(f"Erro no worker {worker_id}: {e}", "error", debug_mode)
                    progress.update(items_progress_task_id, advance=1)
                    if debug_mode:
                        progress.update(items_task_id, advance=1)
        
        progress.remove_task(items_progress_task_id)
        if debug_mode:
            progress.remove_task(items_task_id)
            
        log_message(f"Baixando {total_items_found} itens encontrados em {total_contracts_processed} contratações", "success", debug_mode)
    
    # VERIFICAÇÃO DE DUPLICATAS PARA ITENS: Remover itens duplicados antes da inserção
    if all_items:
    
        # Normalizar itens antes da verificação de duplicatas
        normalized_items = []
        for item in all_items:
            try:
                # O numero_controle_pncp já foi adicionado ao item durante a busca
                numero_controle = item.get('numero_controle_pncp')
                
                if numero_controle:
                    normalized_item = normalize_item_data(item, numero_controle)
                    if normalized_item:
                        normalized_items.append(normalized_item)
                else:
                    log_message(f"Item sem numero_controle_pncp: {item}", "warning", debug_mode)
                        
            except Exception as e:
                log_message(f"Erro ao normalizar item: {str(e)}", "error", debug_mode)
        
        all_items = normalized_items
        
        
        # Remover duplicatas locais (mesmo numeroControlePNCP + numeroItem)
        if all_items:
            unique_items = {}
            for item in all_items:
                numero_controle = item.get('numero_controle_pncp')
                numero_item = item.get('numero_item')
                
                if numero_controle and numero_item:
                    key = f"{numero_controle}_{numero_item}"
                    if key not in unique_items:
                        unique_items[key] = item
            
            all_items = list(unique_items.values())
            
    # Inserir itens
    inserted_itens = 0
    if all_items:
        inserted_itens = insert_itens(conn, all_items)
    
    log_message(f"Inseridos: {inserted_contratacoes} contratações, {inserted_itens} itens", "success", debug_mode)
    
    return inserted_contratacoes, inserted_itens

# =======================================================================
# FUNÇÕES AUXILIARES DE CONTROLE (mantidas do script original)
# =======================================================================

def get_last_processed_date_from_db(conn):
    """Obtém a última data processada do banco Supabase"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value FROM system_config 
            WHERE key = 'last_processed_date'
        """)
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None
    except Exception as e:
        logger.warning(f"Erro ao buscar última data do banco: {e}")
        return None

def save_last_processed_date_to_db(conn, date_str):
    """Salva a última data processada no banco Supabase"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_config (key, value, description, updated_at) 
            VALUES ('last_processed_date', %s, 'Última data processada pelo script 03B de download PNCP paralelo', CURRENT_TIMESTAMP) 
            ON CONFLICT (key) 
            DO UPDATE SET 
                value = EXCLUDED.value, 
                updated_at = CURRENT_TIMESTAMP
        """, (date_str,))
        conn.commit()
        cursor.close()
        logger.info(f"Data {date_str} salva no banco com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar data no banco: {e}")
        conn.rollback()



def get_date_range(start_date=None, end_date=None):
    """Gera lista de datas para processar"""
    # Se não foi fornecida data inicial, usar 01/01/2025 como padrão
    if start_date is None:
        start_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # Se não foi fornecida data final, usar hoje
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    dates = []
    current = datetime.datetime.strptime(start_date, "%Y%m%d")
    end = datetime.datetime.strptime(end_date, "%Y%m%d")
    
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += datetime.timedelta(days=1)
    
    return dates

# =======================================================================
# FUNÇÃO PRINCIPAL OTIMIZADA
# =======================================================================

def main():
    """Função principal otimizada com paralelismo real"""
    console.print(Panel(f"[bold blue]🚀 [1/3] DOWNLOAD DA API PNCP V1[/bold blue]"))
    

    parser = argparse.ArgumentParser(description="Download paralelo otimizado de dados da API PNCP")
    parser.add_argument("--start", help="Data inicial (YYYYMMDD). Se não especificada, continua da última data processada")
    parser.add_argument("--end", help="Data final (YYYYMMDD). Se não especificada, usa a data atual")
    parser.add_argument("--test", help="Testar com uma data específica (YYYYMMDD)")
    parser.add_argument("--debug", action="store_true", help="Ativar modo debug com logs detalhados")
    args = parser.parse_args()
    
    # Log de início da sessão
    log_session_start(args)
    
    try:
        # Conectar ao banco
        conn = connect_to_db()
        log_message("Conexão com banco estabelecida", "success", args.debug)
        
        # Determinar datas para processar
        if args.test:
            dates = [args.test]
            log_message(f"Modo TESTE: processando apenas {args.test}", "warning")
        else:
            # Obter última data do banco (preferencial) ou arquivo legado
            last_date = get_last_processed_date_from_db(conn)
            if not last_date:
                last_date = datetime.datetime.now().strftime("%Y%m%d")
                if last_date:
                    log_message(f"Migrando controle de data do arquivo para banco: {last_date}", "info")
                    save_last_processed_date_to_db(conn, last_date)
            
            if args.start:
                start_date = args.start
            elif last_date:
                # Continuar do próximo dia após o último processado
                last_dt = datetime.datetime.strptime(last_date, "%Y%m%d")
                start_date = (last_dt + datetime.timedelta(days=1)).strftime("%Y%m%d")
            else:
                start_date = datetime.datetime.now().strftime("%Y%m%d")  # Data de hoje se nada for encontrado
            
            dates = get_date_range(start_date, args.end)
        
        if not dates:
            log_message("Nenhuma data para processar", "info")
            return
        
        log_message(f"Processando {len(dates)} datas com {MAX_WORKERS} workers: {dates[0]} até {dates[-1]}")
        
        # Mostrar estatísticas da API apenas em modo debug
        if args.debug:
            console.print(f"\n[bold cyan]📊 ESTATÍSTICAS DA SESSÃO:[/bold cyan]")
            console.print(f"• Workers configurados: {MAX_WORKERS}")
            console.print(f"• Rate limiting: REMOVIDO (máximo throughput)")
            console.print(f"• Paralelismo: REAL (lotes balanceados)")
            console.print(f"• Constraints: OTIMIZADAS (verificação prévia)")
        
        # Processar cada data
        total_contratacoes = 0
        total_itens = 0
        processed_dates = 0
        failed_dates = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task(f"[bold green]Processando {len(dates)} datas", total=len(dates))
            
            for date_str in dates:
                try:
                    display_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]}"
                    progress.update(main_task, description=f"[bold green]Processando {display_date} com {MAX_WORKERS} workers")
                    
                    contratacoes, itens = process_day_optimized(progress, date_str, conn, args.debug)
                    
                    total_contratacoes += contratacoes
                    total_itens += itens
                    processed_dates += 1
                    
                    # Salvar progresso no banco
                    if not args.test:
                        save_last_processed_date_to_db(conn, date_str)
                    
                    progress.update(main_task, advance=1)
                    
                except Exception as e:
                    log_message(f"Erro ao processar data {date_str}: {str(e)}", "error", args.debug)
                    failed_dates.append(date_str)
                    progress.update(main_task, advance=1)
        
        # Relatório final
        console.print(f"\n[bold green]✅ PROCESSAMENTO PARALELO CONCLUÍDO![/bold green]")
        console.print(f"📅 Datas processadas com sucesso: {processed_dates}/{len(dates)}")
        console.print(f"📋 Contratações inseridas: {total_contratacoes:,}")
        console.print(f"📦 Itens inseridos: {total_itens:,}")
        console.print(f"⚡ Workers utilizados: {MAX_WORKERS}")
        
        if failed_dates:
            console.print(f"\n[bold red]❌ Datas com falhas ({len(failed_dates)}):[/bold red]")
            for date in failed_dates:
                console.print(f"  • {date}")
        
        # Log final da sessão
        log_session_end(total_contratacoes, total_itens, dates, api_client.error_counts)
        
        log_message(f"Sessão concluída com sucesso! Log salvo em: {os.path.basename(LOG_FILE)}", "success")
        
    except Exception as e:
        log_message(f"Erro crítico: {str(e)}", "error")
        console.print(f"[bold red]💥 ERRO CRÍTICO: {str(e)}[/bold red]")
        raise
        
    finally:
        try:
            conn.close()
            log_message("Conexão com banco fechada", "info")
        except:
            pass

if __name__ == "__main__":
    main()
