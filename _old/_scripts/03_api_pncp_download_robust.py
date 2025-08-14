# =======================================================================
# [3/7] DOWNLOAD ROBUSTO DA API PNCP PARA POSTGRESQL - VERSÃO MELHORADA
# =======================================================================
# Este script é uma versão melhorada que resolve problemas de timeout e 
# erro HTTP 408 com a API PNCP através de:
# - Retry automático com backoff exponencial
# - Rate limiting inteligente
# - Timeouts adaptativos
# - Pool de conexões reutilizável
# - Menor paralelismo para reduzir sobrecarga do servidor
# - Circuit breaker pattern para modalidades problemáticas
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
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import threading
from collections import defaultdict

# Configuração do console Rich
console = Console()

# Configuração de logging para arquivo
import logging
script_dir = os.path.dirname(os.path.abspath(__file__))

# Gerar timestamp para o nome do arquivo de log
start_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(script_dir, f"pncp_download_{start_timestamp}.log")

# Configurar logger
logger = logging.getLogger('pncp_download')
logger.setLevel(logging.DEBUG)

MAX_WORKERS =30

# Formatter para o arquivo de log
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler para arquivo (sempre ativo)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
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
    logger.info("=" * 80)
    logger.info("NOVA SESSÃO DE DOWNLOAD PNCP INICIADA")
    logger.info("=" * 80)
    logger.info(f"Horário de início: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Argumentos: {vars(args)}")
    logger.info(f"Versão Python: {sys.version}")
    logger.info(f"Diretório de trabalho: {os.getcwd()}")
    logger.info(f"Arquivo de log: {LOG_FILE}")
    logger.info("-" * 80)

def log_session_end(total_contratacoes, total_itens, dates, error_counts):
    """Finaliza a sessão de log com resumo"""
    logger.info("-" * 80)
    logger.info("SESSÃO DE DOWNLOAD PNCP FINALIZADA")
    logger.info(f"Horário de término: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Datas processadas: {len(dates)}")
    logger.info(f"Contratações inseridas: {total_contratacoes:,}")
    logger.info(f"Itens inseridos: {total_itens:,}")
    logger.info(f"Endpoints com problemas: {len([k for k, v in error_counts.items() if v > 0])}")
    logger.info(f"Circuit breakers ativos: {len([k for k, v in error_counts.items() if v >= 8])}")
    if dates:
        logger.info(f"Período processado: {dates[0]} até {dates[-1]}")
    logger.info("=" * 80)

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

# Arquivo de controle da última data processada (LEGADO - mantido para migração)
LAST_DATE_FILE = os.path.join(script_dir, "last_pncp_download_date.log")

# =======================================================================
# CONFIGURAÇÕES ROBUSTAS PARA API REQUESTS
# =======================================================================

class RobustAPIClient:
    """Cliente robusto para API PNCP com retry, rate limiting e timeouts adaptativos"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        self.rate_limiter = threading.Semaphore(40)  # Máximo 3 requisições simultâneas
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
            pool_connections=10,
            pool_maxsize=10
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
            
    def robust_get(self, url, params=None, endpoint_key=None, debug_mode=False):
        """GET request robusto com rate limiting e backoff"""
        if endpoint_key is None:
            endpoint_key = url
            
        # Circuit breaker
        if self.should_circuit_break(endpoint_key):
            log_message(f"Circuit breaker ativo para {endpoint_key} - pulando", "warning", debug_mode)
            return None
            
        # Rate limiting
        with self.rate_limiter:
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

# Cliente global
api_client = RobustAPIClient()

# =======================================================================
# FUNÇÕES AUXILIARES (mantidas do script original)
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
    response = api_client.robust_get(base_url, params=params, endpoint_key=endpoint_key, debug_mode=debug_mode)
    
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
                
                response = api_client.robust_get(base_url, params=params, endpoint_key=page_endpoint_key, debug_mode=debug_mode)
                
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
                
                # Pequeno delay entre páginas para não sobrecarregar
                time.sleep(0.5)
                
            if debug_mode and total_paginas > 1:
                progress.remove_task(task_id)
        
        return all_data
        
    except Exception as e:
        log_message(f"Erro ao processar resposta do código {codigo}: {str(e)}", "error", debug_mode)
        return all_data

def fetch_items_for_contract_robust(numero_controle_pncp, debug_mode=False):
    """Busca itens para uma contratação específica com retry robusto"""
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
        
        response = api_client.robust_get(url, endpoint_key=endpoint_key, debug_mode=debug_mode)
        
        if response is None:
            log_message(f"Falha ao buscar itens para {numero_controle_pncp}", "debug", debug_mode)
            return []
            
        if response.status_code == 200:
            items_data = response.json()
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
# FUNÇÕES DE INSERÇÃO NO BANCO (mantidas do script original)
# =======================================================================

def create_constraints_if_not_exists(conn):
    """Cria constraints se não existirem"""
    cursor = conn.cursor()
    
    try:
        # Constraint para contratacao
        cursor.execute("""
            DO $$ BEGIN
                ALTER TABLE contratacao ADD CONSTRAINT contratacao_numero_controle_unique 
                UNIQUE (numero_controle_pncp);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        """)
        
        # Constraint para item_contratacao
        cursor.execute("""
            DO $$ BEGIN
                ALTER TABLE item_contratacao ADD CONSTRAINT item_contratacao_unique 
                UNIQUE (numero_controle_pncp, numero_item);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        """)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        log_message(f"Aviso ao criar constraints: {str(e)}", "warning")

def insert_contratacoes(conn, contratacoes_data):
    """Insere contratações no banco com tratamento de duplicatas"""
    if not contratacoes_data:
        return 0
        
    create_constraints_if_not_exists(conn)
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
                    import json
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
            for col in columns:
                value = contratacoes_data[0].get(col)
                log_message(f"  {col}: {type(value).__name__} = {repr(value)[:100]}", "error")
        raise

def insert_itens(conn, itens_data):
    """Insere itens no banco com tratamento de duplicatas e lotes para evitar stack overflow"""
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
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        values = []
        json_conversions = 0
        for idx, item in enumerate(itens_data):
            row = []
            for col in columns:
                value = item.get(col)
                # Converter dicionários e listas para JSON string
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value) if value else None
                    json_conversions += 1
                row.append(value)
            values.append(tuple(row))
        
        if json_conversions > 0:
            logger.info(f"Convertidas {json_conversions} estruturas complexas para JSON")
        
        # Verificar se há muitos itens - processar em lotes para evitar stack overflow
        batch_size = 2000  # Reduzir tamanho do lote para evitar problemas de stack
        total_inserted = 0
        
        if len(values) > batch_size:
            logger.info(f"Processando {len(values)} itens em lotes de {batch_size} para evitar stack overflow")
            
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
                
                # Usar page_size menor para reduzir pressão na stack
                execute_values(cursor, sql, batch, template=None, page_size=500)
                
                cursor.execute("SELECT COUNT(*) FROM item_contratacao")
                count_after = cursor.fetchone()[0]
                
                batch_inserted = count_after - count_before
                total_inserted += batch_inserted
                
                logger.debug(f"Lote {i//batch_size + 1}: {batch_inserted} itens inseridos")
                
                # Commit incremental para evitar transações muito longas
                conn.commit()
        else:
            # Para quantidades menores, processar normalmente
            sql = f"""
            INSERT INTO item_contratacao ({columns_str})
            VALUES %s
            ON CONFLICT (numero_controle_pncp, numero_item) DO NOTHING
            """
            
            cursor.execute("SELECT COUNT(*) FROM item_contratacao")
            count_before = cursor.fetchone()[0]
            
            execute_values(cursor, sql, values, template=None, page_size=500)
            
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
        if itens_data:
            logger.error(f"Total de itens na tentativa: {len(itens_data)}")
            logger.error(f"Primeiro item problemático: {itens_data[0]}")
            for col in columns:
                value = itens_data[0].get(col)
                logger.error(f"  {col}: {type(value).__name__} = {repr(value)[:100]}")
        raise

# =======================================================================
# PROCESSAMENTO PRINCIPAL COM MENOR PARALELISMO
# =======================================================================

def process_day_robust(progress, date_str, conn, debug_mode=False):
    """Processa os dados para um dia específico com abordagem robusta"""
    
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
        log_message(f"Iniciando download ROBUSTO para {date_str} (14 modalidades)", "info", debug_mode)
    
    # Criar task para contratações
    contracts_task_id = progress.add_task("Contratações", total=14)
    
    # AUMENTADO: max_workers=MAX_WORKERS para melhor performance
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_by_code_robust, date_str, codigo, progress, debug_mode): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            codigo = futures[future]
            try:
                code_data = future.result()
                all_contracts.extend(code_data)
                log_message(f"Código {codigo}: {len(code_data)} contratos", "debug", debug_mode)
            except Exception as e:
                log_message(f"Erro ao processar código {codigo}: {str(e)}", "error", debug_mode)
            progress.update(contracts_task_id, advance=1)
            if debug_mode:
                progress.update(day_task_id, advance=1)
    
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
    log_message(f"Após remoção de duplicatas: {len(all_contracts)} contratos únicos", "info", debug_mode)
    
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
            log_message(f"Encontrados {len(existing_contracts)} contratos já existentes no banco (itens serão verificados)", "info", debug_mode)
    
    # Processar contratações (apenas as novas)
    inserted_contratacoes = 0
    if new_contracts:
        log_message(f"Processando {len(new_contracts)} contratos novos para inserção", "info", debug_mode)
        
        # Normalizar dados de contratações (apenas contratos novos)
        contratacoes_data = []
        for contract in new_contracts:
            try:
                normalized = normalize_contratacao_data(contract)
                contratacoes_data.append(normalized)
            except Exception as e:
                log_message(f"Erro ao normalizar contrato: {str(e)}", "warning", debug_mode)
                continue
        
        # Inserir contratações
        inserted_contratacoes = insert_contratacoes(conn, contratacoes_data)
    else:
        log_message("Nenhum contrato novo para inserir, mas processando itens dos contratos existentes", "info", debug_mode)
    
    # Processar itens para TODOS os contratos do dia (novos e existentes)
    all_items = []
    
    if debug_mode:
        items_task_id = progress.add_task(f"[bold cyan]    Baixando itens", total=len(all_numeros_controle))
        log_message(f"Iniciando busca de itens para {len(all_numeros_controle)} contratações (incluindo existentes)", "info", debug_mode)
    
    # Criar task para itens
    items_progress_task_id = progress.add_task("Itens Contratações", total=len(all_numeros_controle))
    
    # AUMENTADO: max_workers=MAX_WORKERS para itens (mais linhas)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for numero_controle in all_numeros_controle:
            future = executor.submit(fetch_items_for_contract_robust, numero_controle, debug_mode)
            futures[future] = numero_controle
        
        items_found = 0
        contracts_with_items = 0
        
        for future in concurrent.futures.as_completed(futures):
            numero_controle = futures[future]
            try:
                items_data = future.result()
                if items_data:
                    contracts_with_items += 1
                    for item in items_data:
                        try:
                            normalized_item = normalize_item_data(item, numero_controle)
                            all_items.append(normalized_item)
                            items_found += 1
                        except Exception as e:
                            log_message(f"Erro ao normalizar item {item.get('numeroItem', 'N/A')} do contrato {numero_controle}: {str(e)}", "warning", debug_mode)
                            continue
            except Exception as e:
                log_message(f"Erro ao processar itens para {numero_controle}: {str(e)}", "warning", debug_mode)
            
            progress.update(items_progress_task_id, advance=1)
            if debug_mode:
                progress.update(items_task_id, advance=1)
    
    progress.remove_task(items_progress_task_id)
    if debug_mode:
        progress.remove_task(items_task_id)
        log_message(f"Busca de itens concluída: {items_found} itens encontrados em {contracts_with_items} contratações", "success", debug_mode)
    
    # VERIFICAÇÃO DE DUPLICATAS PARA ITENS: Remover itens duplicados antes da inserção
    if all_items:
        log_message(f"Processando {len(all_items)} itens para verificação de duplicatas", "info", debug_mode)
        
        # Remover duplicatas locais (mesmo numeroControlePNCP + numeroItem)
        unique_items = {}
        for item in all_items:
            numero_controle = item.get('numero_controle_pncp')
            numero_item = str(item.get('numero_item')) if item.get('numero_item') is not None else None
            if numero_controle and numero_item:
                key = f"{numero_controle}_{numero_item}"
                if key not in unique_items:
                    unique_items[key] = item
        
        all_items = list(unique_items.values())
        log_message(f"Após remoção de duplicatas locais: {len(all_items)} itens únicos", "info", debug_mode)
        
        # Verificar duplicatas já existentes no banco para itens - processar em lotes para evitar stack overflow
        if all_items:
            # Dividir verificação em lotes menores para evitar stack overflow
            batch_size = 1000
            new_items = []
            
            for i in range(0, len(all_items), batch_size):
                batch_items = all_items[i:i + batch_size]
                item_keys = [(item.get('numero_controle_pncp'), str(item.get('numero_item'))) for item in batch_items 
                            if item.get('numero_controle_pncp') and item.get('numero_item')]
                
                if item_keys:
                    # Construir query para verificar itens existentes em lote menor
                    placeholders = ','.join(['(%s,%s)'] * len(item_keys))
                    flat_values = [val for pair in item_keys for val in pair]
                    cursor.execute(f"""
                        SELECT numero_controle_pncp, numero_item 
                        FROM item_contratacao 
                        WHERE (numero_controle_pncp, numero_item::text) IN ({placeholders})
                    """, flat_values)
                    
                    existing_items = {(row[0], str(row[1])) for row in cursor.fetchall()}
                    
                    # Filtrar itens que já existem no banco
                    batch_new_items = [item for item in batch_items 
                                     if (item.get('numero_controle_pncp'), str(item.get('numero_item'))) not in existing_items]
                    
                    new_items.extend(batch_new_items)
            
            all_items = new_items
            log_message(f"Itens novos para inserção: {len(all_items)}", "info", debug_mode)
    
    # Inserir itens
    inserted_itens = 0
    if all_items:
        inserted_itens = insert_itens(conn, all_items)
    
    log_message(f"Inseridos: {inserted_contratacoes} contratações, {inserted_itens} itens", "success", debug_mode)
    
    return inserted_contratacoes, inserted_itens

# =======================================================================
# FUNÇÕES AUXILIARES (mantidas do script original)
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
            VALUES ('last_processed_date', %s, 'Última data processada pelo script de download PNCP', CURRENT_TIMESTAMP) 
            ON CONFLICT (key) 
            DO UPDATE SET 
                value = EXCLUDED.value, 
                updated_at = CURRENT_TIMESTAMP
        """, (date_str,))
        conn.commit()
        logger.info(f"Data {date_str} salva no banco com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar data no banco: {e}")
        conn.rollback()

def get_last_processed_date():
    """Obtém a última data processada (função legada - mantida para compatibilidade)"""
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_processed_date(date_str):
    """Salva a última data processada (função legada - mantida para compatibilidade)"""
    with open(LAST_DATE_FILE, "w") as f:
        f.write(date_str)

def get_date_range(start_date=None, end_date=None):
    """Gera lista de datas para processar"""
    # Se não foi fornecida data inicial, usar 01/01/2025 como padrão
    if start_date is None:
        start_date = "20250101"
    
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
# FUNÇÃO PRINCIPAL
# =======================================================================

def main():
    """Função principal robusta"""
    console.print(Panel("[bold blue]🔄 DOWNLOAD ROBUSTO DA API PNCP PARA POSTGRESQL V1[/bold blue]"))
    
    # Log inicial informando o arquivo de log que está sendo usado
    log_message(f"Arquivo de log criado: {os.path.basename(LOG_FILE)}", "info")
    
    import argparse
    parser = argparse.ArgumentParser(description="Download robusto de dados da API PNCP")
    parser.add_argument("--start", help="Data inicial (YYYYMMDD). Se não especificada, continua da última data processada")
    parser.add_argument("--end", help="Data final (YYYYMMDD). Se não especificada, usa a data atual")
    parser.add_argument("--test", help="Testar com uma data específica (YYYYMMDD)")
    parser.add_argument("--debug", action="store_true", help="Ativar modo debug com logs detalhados")
    args = parser.parse_args()
    
    try:
        # Conectar ao banco
        conn = connect_to_db()
        log_message("Conexão com banco estabelecida", "success", args.debug)
        
        # Determinar datas para processar
        if args.test:
            dates = [args.test]
            log_message(f"Modo TESTE: processando apenas {args.test}", "info", args.debug)
        else:
            # Se não foi especificado --start, tentar ler a última data processada do banco
            start_date = args.start
            if not start_date:
                last_date = get_last_processed_date_from_db(conn)
                if last_date:
                    # Continuar do dia seguinte à última data processada
                    next_date = datetime.datetime.strptime(last_date, "%Y%m%d") + datetime.timedelta(days=1)
                    start_date = next_date.strftime("%Y%m%d")
                    log_message(f"Continuando do dia seguinte à última data processada no banco: {last_date}", "info", args.debug)
                    log_message(f"Iniciando processamento a partir de: {start_date}", "info", args.debug)
                else:
                    # Se não há histórico no banco, verificar arquivo local (migração)
                    file_last_date = get_last_processed_date()
                    if file_last_date:
                        # Migrar do arquivo para o banco
                        save_last_processed_date_to_db(conn, file_last_date)
                        next_date = datetime.datetime.strptime(file_last_date, "%Y%m%d") + datetime.timedelta(days=1)
                        start_date = next_date.strftime("%Y%m%d")
                        log_message(f"Dados migrados do arquivo para o banco. Última data: {file_last_date}", "info", args.debug)
                        log_message(f"Iniciando processamento a partir de: {start_date}", "info", args.debug)
                    else:
                        # Se não há histórico, começar de 01/01/2025
                        start_date = "20250101"
                        log_message(f"Nenhum histórico encontrado, iniciando de: {start_date}", "info", args.debug)
            else:
                log_message(f"Data inicial especificada via --start: {start_date}", "info", args.debug)
            
            dates = get_date_range(start_date, args.end)
            if dates:
                log_message(f"Processando {len(dates)} dias: {dates[0]} até {dates[-1]}", "info", args.debug)
            else:
                log_message("Nenhuma data para processar (já está atualizado)", "info", args.debug)
                return
        
        # Mostrar estatísticas da API apenas em modo debug
        if args.debug:
            console.print("\n[bold cyan]📊 STATUS DO CLIENTE ROBUSTO:[/bold cyan]")
            console.print(f"   • Rate limit: 40 requisições simultâneas")
            console.print(f"   • Paralelismo aumentado: 20 workers para contratos, 20 para itens")
            console.print(f"   • Timeout adaptativo: 45-105s baseado no histórico")
            console.print(f"   • Retry automático: até 5 tentativas com backoff exponencial")
            console.print(f"   • Circuit breaker: ativado após 8 falhas consecutivas")
        
        # Processar cada data
        total_contratacoes = 0
        total_itens = 0
        processed_dates = 0
        failed_dates = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=1
        ) as progress:
            
            if args.debug:
                main_task = progress.add_task("[bold green]Processamento geral", total=len(dates))
            
            for date_str in dates:
                try:
                    # Log início do processamento da data
                    logger.info(f"Iniciando processamento da data: {date_str}")
                    
                    contratacoes, itens = process_day_robust(progress, date_str, conn, args.debug)
                    total_contratacoes += contratacoes
                    total_itens += itens
                    processed_dates += 1
                    
                    # Log sucesso do processamento da data
                    logger.info(f"Data {date_str} processada com sucesso: {contratacoes} contratações, {itens} itens")
                    
                    if not args.test:
                        save_last_processed_date_to_db(conn, date_str)
                        
                    if args.debug:
                        progress.update(main_task, advance=1)
                    
                except psycopg2.Error as db_error:
                    # Erro específico do PostgreSQL
                    error_msg = f"Erro de banco ao processar {date_str}: {str(db_error)}"
                    log_message(error_msg, "error", args.debug)
                    logger.error(error_msg)
                    failed_dates.append((date_str, f"DB Error: {str(db_error)}"))
                    
                    # Tentar reconectar ao banco
                    try:
                        conn.close()
                    except:
                        pass
                    
                    try:
                        conn = connect_to_db()
                        log_message(f"Conexão com banco reinicializada após erro em {date_str}", "warning", args.debug)
                        logger.info(f"Conexão com banco reinicializada após erro em {date_str}")
                    except Exception as reconnect_error:
                        error_msg = f"Falha crítica ao reconectar ao banco após erro em {date_str}: {str(reconnect_error)}"
                        log_message(error_msg, "error", args.debug)
                        logger.error(error_msg)
                        break  # Para o processamento se não conseguir reconectar
                        
                    if args.debug:
                        progress.update(main_task, advance=1)
                    continue
                    
                except Exception as e:
                    # Outros erros
                    error_msg = f"Erro geral ao processar {date_str}: {str(e)}"
                    log_message(error_msg, "error", args.debug)
                    logger.error(error_msg)
                    logger.error(f"Tipo do erro: {type(e).__name__}")
                    failed_dates.append((date_str, str(e)))
                    
                    if args.debug:
                        progress.update(main_task, advance=1)
                    continue
        
        # Relatório final
        success_rate = (processed_dates / len(dates) * 100) if dates else 0
        
        # Log final detalhado
        logger.info(f"Processamento concluído - Sucesso: {processed_dates}/{len(dates)} ({success_rate:.1f}%)")
        if failed_dates:
            logger.warning(f"Datas com falha: {len(failed_dates)}")
            for failed_date, error in failed_dates:
                logger.warning(f"  {failed_date}: {error}")
        
        # Preparar relatório de falhas para exibição
        failed_report = ""
        if failed_dates:
            failed_report = f"""
[red]⚠️  Falhas encontradas:[/red]
   • Datas com problemas: {len(failed_dates)}"""
            for failed_date, error in failed_dates[:5]:  # Mostrar apenas as primeiras 5
                failed_report += f"\n   • {failed_date}: {error[:80]}..."
            if len(failed_dates) > 5:
                failed_report += f"\n   • ... e mais {len(failed_dates) - 5} falhas (veja o log completo)"
        
        console.print(Panel(f"""
[bold green]✅ PROCESSAMENTO ROBUSTO CONCLUÍDO[/bold green]

[cyan]📈 Resumo:[/cyan]
   • Datas processadas com sucesso: {processed_dates}/{len(dates)} ({success_rate:.1f}%)
   • Contratações inseridas: {total_contratacoes:,}
   • Itens inseridos: {total_itens:,}

[yellow]🔧 Estatísticas da API:[/yellow]
   • Endpoints com problemas: {len([k for k, v in api_client.error_counts.items() if v > 0])}
   • Circuit breakers ativos: {len([k for k, v in api_client.error_counts.items() if v >= 8])}

[blue]📅 Período processado:[/blue]
   • Data inicial: {dates[0] if dates else 'N/A'}
   • Data final: {dates[-1] if dates else 'N/A'}
{failed_report}

[green]💾 Status do banco: Conectado e atualizado[/green]
        """))
        
    except Exception as e:
        log_message(f"Erro crítico: {str(e)}", "error", args.debug)
        raise
        
    finally:
        if 'conn' in locals():
            conn.close()
            log_message("Conexão com banco fechada", "info", args.debug)

if __name__ == "__main__":
    main()
