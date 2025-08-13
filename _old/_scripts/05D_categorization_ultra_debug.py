# =======================================================================
# [5D/7] CATEGORIZAÇÃO AUTOMÁTICA ULTRA DEBUG - VERSÃO V3
# =======================================================================
# Versão de debug extremamente detalhada do 05C que combina:
# - Query rápida do 05 original (com JOIN)
# - Batch pgvector search do 05C
# - Debug ultra detalhado com progress por etapa
# - Logs de timing para cada operação
# 
# PRINCIPAIS OTIMIZAÇÕES V5D:
# - Query única otimizada (como 05 original) - RÁPIDA!
# - BATCH PGVECTOR SEARCH: 1 query para múltiplos embeddings
# - Progress bars detalhados para cada etapa do worker
# - Timing logs para identificar gargalos
# - Debug ultra verboso
# 
# OBJETIVO: Identificar exatamente onde está o gargalo restante
# =======================================================================

import os
import sys
import time
import math
import threading
import argparse
import logging
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Configuração global
debug_mode = False
logger = None
connection_pool = None

# Configure Rich console
console = Console()

# Configurações de categorização ULTRA DEBUG V5D
TOP_K = 5
MIN_WORKERS = 3
MAX_WORKERS = 8   # Reduzido para debug mais claro
BATCH_SIZE = 50   
UPDATE_BATCH_SIZE = 100
NUM_CONN = MAX_WORKERS + 4

# CONFIGURAÇÃO DEBUG V5D: Batch size para pgvector search
PGVECTOR_BATCH_SIZE = 50  # Reduzido para debug

#############################################
# SETUP DE LOGGING E CONFIGURAÇÕES
#############################################

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Categorização Automática Ultra Debug v3')
    parser.add_argument('--test', 
                       action='store_true',
                       help='Executar para próximo dia após last_categorization_date')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Ativar modo debug com logs detalhados')
    return parser.parse_args()

def setup_logging(debug_mode=False):
    """Configura sistema de logging"""
    global logger
    
    # Gerar timestamp para o nome do arquivo de log
    start_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Criar pasta de logs se não existir
    logs_dir = os.path.join(os.path.dirname(script_dir), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    LOG_FILE = os.path.join(logs_dir, f"05D_categorization_ultra_debug_{start_timestamp}.log")
    
    # Configurar logger principal
    logger = logging.getLogger('categorization_ultra_debug')
    logger.setLevel(logging.DEBUG)
    
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
    
    logger.info("=" * 80)
    logger.info("NOVA SESSÃO DE CATEGORIZAÇÃO ULTRA DEBUG V5D INICIADA")
    logger.info("=" * 80)
    logger.info(f"Horário de início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Modo debug: {'Ativado' if debug_mode else 'Desativado'}")
    logger.info(f"Arquivo de log: {LOG_FILE}")
    logger.info(f"CONFIGURAÇÕES DEBUG V5D: Workers={MAX_WORKERS}, PGVector Batch={PGVECTOR_BATCH_SIZE}")
    logger.info("-" * 80)
    
    return logger, os.path.basename(LOG_FILE)

def log_session_end(stats, tempo_total):
    """Finaliza a sessão de log com resumo"""
    if logger:
        logger.info("-" * 80)
        logger.info("SESSÃO DE CATEGORIZAÇÃO ULTRA DEBUG V5D FINALIZADA")
        logger.info(f"Horário de término: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Tempo total: {tempo_total:.1f}s")
        logger.info(f"Datas processadas: {stats['datas_processadas']}")
        logger.info(f"Embeddings processados: {stats['embeddings_processados']:,}")
        logger.info(f"Categorizações aplicadas: {stats['categorizacoes_aplicadas']:,}")
        logger.info(f"Erros encontrados: {stats['erros']:,}")
        logger.info("=" * 80)

def format_date_for_display(date_str):
    """Converte YYYYMMDD para DD/MM/YYYY apenas para display"""
    if len(date_str) == 8:
        return f"{date_str[6:8]}/{date_str[4:6]}/{date_str[:4]}"
    return date_str

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    # SEMPRE escrever no arquivo de log
    if logger:
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
        elif log_type == "sql_debug":
            logger.debug(f"SQL_DEBUG: {message}")
    
    # Log no console APENAS se debug estiver ativado para debug messages
    if log_type == "debug" and not debug_mode:
        return
    if log_type == "sql_debug":  # SILENCIAR sql_debug temporariamente
        return
    if log_type == "conn_debug":  # SILENCIAR conn_debug temporariamente
        return
    
    # Log no console
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
    elif log_type == "sql_debug":
        console.print(f"[magenta]🗄️  SQL: {message}[/magenta]")
    elif log_type == "conn_debug":
        console.print(f"[blue]🔗 CONN: {message}[/blue]")

def log_timing(operation, start_time, details=""):
    """Log especializado para timing de operações"""
    elapsed = time.time() - start_time
    message = f"⏱️ {operation}: {elapsed:.2f}s"
    if details:
        message += f" - {details}"
    log_message(message, "debug")
    return elapsed

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configurações do banco PostgreSQL V1 (Supabase) - DEBUG V5D
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', ''),
    'connect_timeout': 15,
    'options': '-c statement_timeout=120000',  # 120s timeout
    'keepalives_idle': 600,
    'keepalives_interval': 30,
    'keepalives_count': 3,
    'sslmode': 'require'
}

# Controle de concorrência
stats_lock = threading.Lock()

# Estatísticas globais
global_stats = {
    'embeddings_processados': 0,
    'categorizacoes_aplicadas': 0,
    'baixa_confianca': 0,
    'erros': 0
}

#############################################
# POOL DE CONEXÕES DEBUG V5D
#############################################

def initialize_connection_pool():
    """Inicializa pool de conexões thread-safe DEBUG V5D"""
    global connection_pool
    pool_start = time.time()
    
    if debug_mode:
        log_message("🔗 POOL DEBUG: Iniciando criação do pool de conexões", "debug")
        log_message(f"🔗 POOL DEBUG: Configurações - Min: {MIN_WORKERS}, Max: {NUM_CONN}", "debug")
        log_message(f"🔗 POOL DEBUG: Config DB - Host: {DB_CONFIG['host']}, Port: {DB_CONFIG['port']}, DB: {DB_CONFIG['database']}", "debug")
    
    try:
        if debug_mode:
            log_message("🔗 POOL DEBUG: Criando ThreadedConnectionPool...", "debug")
        
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=MIN_WORKERS,
            maxconn=NUM_CONN,
            **DB_CONFIG
        )
        
        pool_time = time.time() - pool_start
        
        if debug_mode:
            log_message(f"🔗 POOL DEBUG: Pool criado com sucesso em {pool_time:.3f}s", "debug")
            log_message(f"🔗 POOL DEBUG: Testando primeira conexão...", "debug")
            
            # Testar primeira conexão
            test_start = time.time()
            test_conn = connection_pool.getconn()
            test_cursor = test_conn.cursor()
            test_cursor.execute("SELECT 1, current_timestamp, version()")
            test_result = test_cursor.fetchone()
            test_cursor.close()
            connection_pool.putconn(test_conn)
            test_time = time.time() - test_start
            
            log_message(f"🔗 POOL DEBUG: Teste de conexão OK em {test_time:.3f}s - Resultado: {test_result[0]}, Timestamp: {test_result[1]}", "debug")
            log_message(f"🔗 POOL DEBUG: Versão PostgreSQL: {test_result[2][:50]}...", "debug")
        
        log_message(f"Pool de conexões DEBUG V5D criado: {NUM_CONN} conexões máximas em {pool_time:.3f}s", "success")
        return True
        
    except Exception as e:
        log_message(f"❌ POOL DEBUG: Erro ao criar pool: {e}", "error")
        if debug_mode:
            import traceback
            log_message(f"🔗 POOL DEBUG: Traceback completo: {traceback.format_exc()}", "debug")
        return False

def close_connection_pool():
    """Fecha pool de conexões com segurança total"""
    global connection_pool
    if connection_pool:
        close_start = time.time()
        
        if debug_mode:
            log_message("🔗 POOL DEBUG: Iniciando fechamento do pool de conexões", "debug")
            
            # Estatísticas do pool antes de fechar
            try:
                # Tentar obter informações do pool (nem todos os pools têm essas propriedades)
                if hasattr(connection_pool, '_pool'):
                    active_connections = len(connection_pool._used)
                    available_connections = len(connection_pool._pool)
                    log_message(f"🔗 POOL DEBUG: Estado antes do fechamento - Ativas: {active_connections}, Disponíveis: {available_connections}", "debug")
            except Exception as e:
                log_message(f"🔗 POOL DEBUG: Não foi possível obter estatísticas do pool: {e}", "debug")
        
        try:
            connection_pool.closeall()
            close_time = time.time() - close_start
            
            if debug_mode:
                log_message(f"🔗 POOL DEBUG: Pool fechado com sucesso em {close_time:.3f}s", "debug")
            
            log_message("🔒 Pool de conexões fechado com segurança", "info")
            
        except Exception as e:
            close_time = time.time() - close_start
            log_message(f"⚠️ Erro ao fechar pool (tempo: {close_time:.3f}s): {e}", "warning")
            
            if debug_mode:
                import traceback
                log_message(f"🔗 POOL DEBUG: Traceback do erro: {traceback.format_exc()}", "debug")
                
        finally:
            connection_pool = None
            if debug_mode:
                log_message("🔗 POOL DEBUG: Variável connection_pool definida como None", "debug")

def get_db_connection():
    """Obter conexão do pool - DEBUG COMPLETO V5D"""
    global connection_pool
    if not connection_pool:
        raise Exception("Pool de conexões não inicializado")
    
    conn_start = time.time()
    thread_id = threading.get_ident()
    
    if debug_mode:
        log_message(f"🔗 CONN DEBUG: Thread {thread_id} solicitando conexão do pool", "debug")
    
    try:
        # Obter conexão do pool
        get_start = time.time()
        conn = connection_pool.getconn()
        get_time = time.time() - get_start
        
        if debug_mode:
            log_message(f"🔗 CONN DEBUG: connection_pool.getconn() executado em {get_time:.3f}s", "debug")
        
        # Verificar se conexão é válida
        if conn and not conn.closed:
            if debug_mode:
                log_message(f"🔗 CONN DEBUG: Conexão obtida com sucesso - Status: {conn.status}, Thread: {thread_id}", "debug")
                log_message(f"🔗 CONN DEBUG: Info da conexão - PID: {conn.info.backend_pid if hasattr(conn, 'info') and hasattr(conn.info, 'backend_pid') else 'N/A'}", "debug")
            
            total_time = time.time() - conn_start
            if debug_mode:
                log_message(f"🔗 CONN DEBUG: Conexão pronta em {total_time:.3f}s", "debug")
            
            return conn
        else:
            if conn:
                if debug_mode:
                    log_message(f"🔗 CONN DEBUG: Conexão inválida detectada (closed: {conn.closed}), descartando", "debug")
                connection_pool.putconn(conn, close=True)
            raise Exception("Conexão inválida obtida do pool")
            
    except Exception as e:
        total_time = time.time() - conn_start
        log_message(f"❌ CONN DEBUG: Erro ao obter conexão após {total_time:.3f}s: {e}", "error")
        if debug_mode:
            import traceback
            log_message(f"🔗 CONN DEBUG: Traceback: {traceback.format_exc()}", "debug")
        raise

def return_db_connection(conn):
    """Devolver conexão ao pool - DEBUG COMPLETO V5D"""
    global connection_pool
    return_start = time.time()
    thread_id = threading.get_ident()
    
    if connection_pool and conn:
        if debug_mode:
            log_message(f"🔗 CONN DEBUG: Thread {thread_id} devolvendo conexão ao pool", "debug")
            log_message(f"🔗 CONN DEBUG: Status da conexão antes de devolver - Closed: {conn.closed}, Status: {conn.status}", "debug")
        
        try:
            connection_pool.putconn(conn)
            return_time = time.time() - return_start
            
            if debug_mode:
                log_message(f"🔗 CONN DEBUG: Conexão devolvida com sucesso em {return_time:.3f}s", "debug")
                
        except Exception as e:
            return_time = time.time() - return_start
            log_message(f"⚠️ CONN DEBUG: Erro ao devolver conexão (tempo: {return_time:.3f}s): {e}", "warning")
            
            if debug_mode:
                import traceback
                log_message(f"🔗 CONN DEBUG: Traceback do erro: {traceback.format_exc()}", "debug")
    else:
        if debug_mode:
            log_message(f"🔗 CONN DEBUG: Conexão não devolvida - Pool: {connection_pool is not None}, Conn: {conn is not None}", "debug")

#############################################
# FUNÇÕES DE BANCO DE DADOS DEBUG V5D
#############################################

def get_last_categorization_date():
    """Obtém a última data de categorização do system_config"""
    try:
        log_message("🗄️ INICIANDO get_last_categorization_date", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("get_last_categorization_date - Conexão", conn_start)
        
        cursor = conn.cursor()
        
        query = "SELECT value FROM system_config WHERE key = 'last_categorization_date'"
        log_message(f"🗄️ EXECUTANDO: {query}", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query)
        result = cursor.fetchone()
        query_time = log_timing("get_last_categorization_date - Query", query_start)
        
        log_message(f"🗄️ RESULTADO: {result} (tempo: {query_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        
        if result:
            log_message(f"🗄️ RETORNANDO última data: {result[0]}", "sql_debug")
            return result[0]
        else:
            log_message("🗄️ RETORNANDO data padrão: 20250101", "sql_debug")
            return "20250101"
            
    except Exception as e:
        log_message(f"🗄️ ERRO em get_last_categorization_date: {e}", "error")
        return "20250101"

def get_last_embedding_date():
    """Obtém a última data de processamento de embeddings do system_config"""
    try:
        log_message("🗄️ INICIANDO get_last_embedding_date", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("get_last_embedding_date - Conexão", conn_start)
        
        cursor = conn.cursor()
        
        query = "SELECT value FROM system_config WHERE key = 'last_embedding_date'"
        log_message(f"🗄️ EXECUTANDO: {query}", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query)
        result = cursor.fetchone()
        query_time = log_timing("get_last_embedding_date - Query", query_start)
        
        log_message(f"🗄️ RESULTADO: {result} (tempo: {query_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        
        if result:
            log_message(f"🗄️ RETORNANDO última data embedding: {result[0]}", "sql_debug")
            return result[0]
        else:
            current_date = datetime.now().strftime("%Y%m%d")
            log_message(f"🗄️ RETORNANDO data atual: {current_date}", "sql_debug")
            return current_date
            
    except Exception as e:
        log_message(f"🗄️ ERRO em get_last_embedding_date: {e}", "error")
        return datetime.now().strftime("%Y%m%d")

def update_last_categorization_date(date_str):
    """Atualiza a última data de categorização no system_config"""
    try:
        log_message(f"🗄️ INICIANDO update_last_categorization_date para: {date_str}", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("update_last_categorization_date - Conexão", conn_start)
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO system_config (key, value, description) 
            VALUES ('last_categorization_date', %s, 'Última data processada para categorização automática')
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """
        params = (date_str,)
        
        log_message(f"🗄️ EXECUTANDO UPDATE: {query}", "sql_debug")
        log_message(f"🗄️ PARÂMETROS: {params}", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query, params)
        conn.commit()
        query_time = log_timing("update_last_categorization_date - Update + Commit", query_start)
        
        log_message(f"🗄️ UPDATE CONCLUÍDO (tempo: {query_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        log_message(f"Data de categorização atualizada para: {date_str}", "success")
        return True
        
    except Exception as e:
        log_message(f"🗄️ ERRO em update_last_categorization_date: {e}", "error")
        return False

def generate_dates_for_categorization(last_categorization_date, test_mode=False, last_embedding_date=None):
    """Gera lista de datas para categorização"""
    try:
        if test_mode:
            # Modo teste: apenas próximo dia
            try:
                last_date_obj = datetime.strptime(last_categorization_date, '%Y%m%d')
                next_date_obj = last_date_obj + timedelta(days=1)
                next_date = next_date_obj.strftime('%Y%m%d')
                
                log_message(f"Modo teste: processando apenas data {format_date_for_display(next_date)}", "info")
                return [next_date]
            except ValueError as e:
                log_message(f"Erro ao calcular próxima data para teste: {e}", "error")
                return []
        
        if not last_embedding_date:
            log_message("Última data de embedding não encontrada", "warning")
            return []
        
        # Converter strings YYYYMMDD para objetos datetime
        try:
            start_date = datetime.strptime(last_categorization_date, '%Y%m%d') + timedelta(days=1)
            end_date = datetime.strptime(last_embedding_date, '%Y%m%d')
        except ValueError as e:
            log_message(f"Erro ao converter datas: {e}", "error")
            return []
        
        # Verificar se há intervalo válido
        if start_date > end_date:
            log_message(f"Última data de categorização ({last_categorization_date}) já está atualizada", "info")
            return []
        
        # Gerar lista de datas dia por dia
        dates_to_process = []
        current_date = start_date
        
        while current_date <= end_date:
            dates_to_process.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
        
        # Log do intervalo calculado
        if dates_to_process:
            start_display = format_date_for_display(dates_to_process[0])
            end_display = format_date_for_display(dates_to_process[-1])
            log_message(f"Intervalo calculado: {start_display} até {end_display} ({len(dates_to_process)} dias)", "info")
        
        return dates_to_process
        
    except Exception as e:
        log_message(f"Erro ao gerar datas para categorização: {e}", "error")
        return []

def get_controle_pncp_by_date(date_str):
    """
    DEBUG V5D: Busca apenas os numero_controle_pncp da data (RÁPIDO)
    """
    start_time = time.time()
    try:
        log_message(f"🗄️ INICIANDO get_controle_pncp_by_date para data: {date_str}", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("get_controle_pncp_by_date - Conexão", conn_start)
        
        cursor = conn.cursor()
        
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        log_message(f"🗄️ Data formatada: {date_str} -> {date_formatted}", "sql_debug")
        
        log_message(f"🚀 V5D: Buscando numero_controle_pncp para data {format_date_for_display(date_str)}", "debug")
        
        # QUERY SIMPLES: apenas IDs da data
        query = """
        SELECT DISTINCT numero_controle_pncp
        FROM contratacao 
        WHERE data_publicacao_pncp IS NOT NULL
          AND DATE(data_publicacao_pncp) = %s::date
        ORDER BY numero_controle_pncp
        """
        params = (date_formatted,)
        
        log_message(f"🗄️ EXECUTANDO QUERY CONTROLE_PNCP:", "sql_debug")
        log_message(f"🗄️ SQL: {query.strip()}", "sql_debug")
        log_message(f"🗄️ PARÂMETROS: {params}", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query, params)
        
        log_message(f"🗄️ Query executada, fazendo fetchall()...", "sql_debug")
        fetch_start = time.time()
        results = cursor.fetchall()
        controle_ids = [row[0] for row in results]
        fetch_time = log_timing("get_controle_pncp_by_date - Fetchall", fetch_start)
        
        query_time = log_timing("get_controle_pncp_by_date - Query + Fetch", query_start, f"{len(controle_ids)} controles encontrados")
        
        log_message(f"🗄️ FETCHALL CONCLUÍDO: {len(controle_ids)} controles (tempo: {fetch_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        
        total_time = log_timing("get_controle_pncp_by_date TOTAL", start_time, f"{len(controle_ids)} controles")
        
        log_message(f"Data {format_date_for_display(date_str)}: encontrados {len(controle_ids)} controles (tempo: {total_time:.2f}s)", "info")
        
        # Log detalhado dos primeiros resultados (só no debug)
        if controle_ids:
            sample_size = min(5, len(controle_ids))
            log_message(f"🗄️ AMOSTRA DOS PRIMEIROS {sample_size} CONTROLES:", "sql_debug")
            log_message(f"🗄️ {controle_ids[:sample_size]}", "sql_debug")
        
        return controle_ids
        
    except Exception as e:
        log_message(f"🗄️ ERRO em get_controle_pncp_by_date: {e}", "error")
        return []

def get_embeddings_by_controle_batch(controle_batch):
    """
    DEBUG V5D: Busca embeddings de um batch de numero_controle_pncp
    """
    start_time = time.time()
    try:
        if not controle_batch:
            return []
            
        log_message(f"🗄️ INICIANDO get_embeddings_by_controle_batch para batch: {len(controle_batch)} controles", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("get_embeddings_by_controle_batch - Conexão", conn_start)
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        log_message(f"🚀 V5D: Buscando embeddings para batch de {len(controle_batch)} controles", "debug")
        
        # QUERY SIMPLES: embeddings por batch de controles
        query = """
        SELECT 
            id_contratacao_emb,
            numero_controle_pncp,
            embeddings
        FROM contratacao_emb
        WHERE numero_controle_pncp = ANY(%s)
          AND embeddings IS NOT NULL
          AND (top_categories IS NULL OR confidence IS NULL)
        ORDER BY id_contratacao_emb
        """
        params = (controle_batch,)
        
        log_message(f"🗄️ EXECUTANDO QUERY EMBEDDINGS BATCH:", "sql_debug")
        log_message(f"🗄️ SQL: {query.strip()}", "sql_debug")
        log_message(f"🗄️ BATCH SIZE: {len(controle_batch)}", "sql_debug")
        log_message(f"🗄️ AMOSTRA BATCH: {controle_batch[:3]}...", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query, params)
        
        log_message(f"🗄️ Query executada, fazendo fetchall()...", "sql_debug")
        fetch_start = time.time()
        results = cursor.fetchall()
        fetch_time = log_timing("get_embeddings_by_controle_batch - Fetchall", fetch_start)
        
        query_time = log_timing("get_embeddings_by_controle_batch - Query + Fetch", query_start, f"{len(results)} embeddings encontrados")
        
        log_message(f"🗄️ FETCHALL CONCLUÍDO: {len(results)} embeddings (tempo: {fetch_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        
        total_time = log_timing("get_embeddings_by_controle_batch TOTAL", start_time, f"{len(results)} embeddings")
        
        log_message(f"Batch de {len(controle_batch)} controles: encontrados {len(results)} embeddings (tempo: {total_time:.2f}s)", "debug")
        
        # Log detalhado dos primeiros resultados (só no debug)
        if results:
            sample_size = min(3, len(results))
            log_message(f"🗄️ AMOSTRA DOS PRIMEIROS {sample_size} EMBEDDINGS:", "sql_debug")
            for i, row in enumerate(results[:sample_size]):
                log_message(f"🗄️ [{i+1}] ID: {row['id_contratacao_emb']}, Controle: {row['numero_controle_pncp']}, Embedding size: {len(row['embeddings']) if row['embeddings'] else 0}", "sql_debug")
        
        return results
        
    except Exception as e:
        log_message(f"🗄️ ERRO em get_embeddings_by_controle_batch: {e}", "error")
        return []

def check_categoria_embeddings():
    """Verifica se existem embeddings de categorias na base"""
    try:
        log_message("🗄️ INICIANDO check_categoria_embeddings", "sql_debug")
        
        conn_start = time.time()
        conn = get_db_connection()
        log_timing("check_categoria_embeddings - Conexão", conn_start)
        
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM categoria WHERE cat_embeddings IS NOT NULL"
        log_message(f"🗄️ EXECUTANDO: {query}", "sql_debug")
        
        query_start = time.time()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        query_time = log_timing("check_categoria_embeddings - Query", query_start)
        
        log_message(f"🗄️ RESULTADO COUNT: {count} (tempo: {query_time:.3f}s)", "sql_debug")
        
        cursor.close()
        return_db_connection(conn)
        
        log_message(f"Encontradas {count} categorias com embeddings", "info")
        return count > 0
        
    except Exception as e:
        log_message(f"🗄️ ERRO em check_categoria_embeddings: {e}", "error")
        return False

#############################################
# FUNÇÕES DE CATEGORIZAÇÃO DEBUG V5D - BATCH PGVECTOR
#############################################

def calculate_confidence(similarities):
    """Calcula o nível de confiança baseado na diferença entre as similaridades"""
    if len(similarities) < 2:
        return 0.0
    
    top_score = similarities[0]
    
    if top_score == 0.0:
        return 0.0
    
    # Calcular gaps entre scores
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = (1 - math.exp(-10 * weighted_gap))
    
    return round(confidence, 4)

def batch_pgvector_similarity_search_debug(cursor, embeddings_batch):
    """
    DEBUG V5D: Batch pgvector search com DEBUG COMPLETO de SQL
    """
    if not embeddings_batch:
        return {}
    
    start_time = time.time()
    log_message(f"🚀 V5D BATCH: Iniciando batch pgvector para {len(embeddings_batch)} embeddings", "debug")
    log_message(f"🗄️ INICIANDO batch_pgvector_similarity_search_debug", "sql_debug")
    
    try:
        # Preparar arrays para batch processing
        prep_start = time.time()
        embedding_vectors = []
        embedding_ids = []
        
        log_message(f"🗄️ Preparando arrays para {len(embeddings_batch)} embeddings", "sql_debug")
        
        for i, emb_data in enumerate(embeddings_batch):
            embedding_vectors.append(emb_data['embeddings'])
            embedding_ids.append(emb_data['id_contratacao_emb'])
            
            # Log detalhado dos primeiros embeddings (só no debug)
            if i < 3:
                log_message(f"🗄️ [{i+1}] ID: {emb_data['id_contratacao_emb']}, Controle: {emb_data['numero_controle_pncp']}, Vector size: {len(emb_data['embeddings'])}", "sql_debug")
        
        prep_time = log_timing("Preparação arrays", prep_start, f"{len(embedding_vectors)} vectors")
        log_message(f"🗄️ Arrays preparados: {len(embedding_vectors)} vectors, {len(embedding_ids)} IDs (tempo: {prep_time:.3f}s)", "sql_debug")
        
        # BATCH PGVECTOR QUERY V5D
        query_start = time.time()
        batch_similarity_query = """
        WITH embedding_batch AS (
            SELECT 
                unnest(%s::vector[]) as query_embedding,
                unnest(%s::bigint[]) as emb_id
        ),
        similarities AS (
            SELECT 
                eb.emb_id,
                c.cod_cat,
                c.nom_cat,
                1 - (c.cat_embeddings <=> eb.query_embedding) as similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY eb.emb_id 
                    ORDER BY (c.cat_embeddings <=> eb.query_embedding) ASC
                ) as rank
            FROM embedding_batch eb
            CROSS JOIN categoria c
            WHERE c.cat_embeddings IS NOT NULL
        )
        SELECT emb_id, cod_cat, nom_cat, similarity
        FROM similarities 
        WHERE rank <= %s
        ORDER BY emb_id, similarity DESC
        """
        params = (embedding_vectors, embedding_ids, TOP_K)
        
        log_message(f"🗄️ EXECUTANDO BATCH PGVECTOR QUERY:", "sql_debug")
        log_message(f"🗄️ SQL: {batch_similarity_query.strip()}", "sql_debug")
        log_message(f"🗄️ PARÂMETROS: vectors={len(embedding_vectors)}, ids={len(embedding_ids)}, top_k={TOP_K}", "sql_debug")
        
        try:
            cursor.execute(batch_similarity_query, params)
            
            log_message(f"🗄️ Query executada, fazendo fetchall()...", "sql_debug")
            fetch_start = time.time()
            batch_results = cursor.fetchall()
            fetch_time = log_timing("Batch PGVector Fetchall", fetch_start)
            
            query_time = log_timing("Batch PGVector Query", query_start, f"{len(batch_results)} resultados")
            log_message(f"🗄️ FETCHALL CONCLUÍDO: {len(batch_results)} resultados (tempo: {fetch_time:.3f}s)", "sql_debug")
            
            if not batch_results and debug_mode:
                log_message(f"🚨 DEBUG: BATCH PGVECTOR NÃO RETORNOU RESULTADOS!", "debug")
                log_message(f"🔍 DEBUG: Testando query individual para o primeiro embedding...", "debug")
                
                # Testar query individual
                test_vector = embedding_vectors[0]
                test_id = embedding_ids[0]
                
                cursor.execute("""
                    SELECT cod_cat, nom_cat, 1 - (cat_embeddings <=> %s::vector) as similarity
                    FROM categoria
                    WHERE cat_embeddings IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT 3
                """, (test_vector,))
                individual_test = cursor.fetchall()
                
                log_message(f"🔍 DEBUG: Query individual para ID {test_id} encontrou {len(individual_test)} resultados:", "debug")
                for result in individual_test[:3]:
                    log_message(f"🔍 DEBUG:   {result[0]} - sim: {result[2]:.4f}", "debug")
                    
        except Exception as batch_error:
            log_message(f"🚨 ERRO na execução da batch pgvector query: {batch_error}", "error")
            
            # ROLLBACK da transação corrompida
            try:
                cursor.execute("ROLLBACK")
                log_message(f"🔄 Transação resetada após erro batch", "debug")
            except:
                pass
            
            log_message(f"🔄 Tentando fallback para queries individuais...", "debug")
            
            # FALLBACK: Processar individualmente com nova transação
            batch_results = []
            for i, (emb_vector, emb_id) in enumerate(zip(embedding_vectors, embedding_ids)):
                try:
                    # Começar nova transação para cada query individual
                    cursor.execute("BEGIN")
                    cursor.execute("""
                        SELECT %s as emb_id, cod_cat, nom_cat, 
                               1 - (cat_embeddings <=> %s::vector) as similarity
                        FROM categoria
                        WHERE cat_embeddings IS NOT NULL
                        ORDER BY similarity DESC
                        LIMIT %s
                    """, (emb_id, emb_vector, TOP_K))
                    individual_results = cursor.fetchall()
                    cursor.execute("COMMIT")
                    
                    batch_results.extend(individual_results)
                    
                    if debug_mode and i < 2:  # Log apenas dos primeiros
                        log_message(f"🔄 DEBUG: Fallback individual emb_id {emb_id}: {len(individual_results)} resultados", "debug")
                        
                except Exception as individual_error:
                    try:
                        cursor.execute("ROLLBACK")
                    except:
                        pass
                    log_message(f"🚨 DEBUG: Erro na query individual para {emb_id}: {individual_error}", "debug")
            
            query_time = log_timing("Batch PGVector Fallback", query_start, f"{len(batch_results)} resultados")
            log_message(f"🔄 DEBUG: Fallback concluído: {len(batch_results)} resultados", "debug")
        
        # Organizar resultados por embedding ID
        organize_start = time.time()
        results_by_embedding = {}
        
        log_message(f"🗄️ Organizando {len(batch_results)} resultados por embedding ID", "sql_debug")
        
        for i, row in enumerate(batch_results):
            emb_id, cod_cat, nom_cat, similarity = row
            if emb_id not in results_by_embedding:
                results_by_embedding[emb_id] = []
            results_by_embedding[emb_id].append((cod_cat, nom_cat, similarity))
            
            # Log detalhado dos primeiros resultados
            if i < 10:
                log_message(f"🗄️ [{i+1}] EmbID: {emb_id}, Cat: {cod_cat}, Sim: {similarity:.4f}", "sql_debug")
        
        organize_time = log_timing("Organização resultados", organize_start, f"{len(results_by_embedding)} embeddings processados")
        log_message(f"🗄️ Organização concluída: {len(results_by_embedding)} embeddings (tempo: {organize_time:.3f}s)", "sql_debug")
        
        # Estatísticas detalhadas
        total_categories_found = sum(len(cats) for cats in results_by_embedding.values())
        avg_categories_per_embedding = total_categories_found / len(results_by_embedding) if results_by_embedding else 0
        
        log_message(f"🗄️ ESTATÍSTICAS: Total cats: {total_categories_found}, Avg por emb: {avg_categories_per_embedding:.2f}", "sql_debug")
        
        total_time = log_timing("batch_pgvector_similarity_search_debug TOTAL", start_time, 
                              f"{len(results_by_embedding)} embeddings, query: {query_time:.2f}s")
        
        log_message(f"🚀 V5D BATCH: Concluído - {len(results_by_embedding)} embeddings em {total_time:.2f}s", "debug")
        
        return results_by_embedding
        
    except Exception as e:
        log_message(f"🗄️ ERRO no batch pgvector search: {e}", "error")
        return {}

def categorize_embedding_batch_debug(worker_id, embedding_batch, progress_callback=None):
    """
    DEBUG V5D: Categoriza lote com progress detalhado por etapa
    """
    local_stats = {
        'embeddings_processados': 0,
        'categorizacoes_aplicadas': 0,
        'baixa_confianca': 0,
        'erros': 0
    }
    
    worker_start_time = time.time()
    
    try:
        log_message(f"👷 Worker {worker_id}: INICIANDO processamento de {len(embedding_batch)} embeddings", "debug")
        
        # ETAPA 1: Conexão
        if progress_callback:
            progress_callback(5, f"🔌 Conectando...")
        
        conn_start = time.time()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Resetar qualquer transação anterior
        try:
            cursor.execute("ROLLBACK")
            cursor.execute("BEGIN")
            log_message(f"Worker {worker_id}: Transação limpa iniciada", "debug")
        except:
            try:
                cursor.execute("BEGIN")
            except:
                pass
                
        conn_time = log_timing(f"Worker {worker_id} - Conexão", conn_start)
        log_message(f"🗄️ Worker {worker_id}: Conexão estabelecida (tempo: {conn_time:.3f}s)", "sql_debug")
        
        if progress_callback:
            progress_callback(10, f"🔧 Processando chunks...")
        
        # ETAPA 2: Processar em chunks para batch pgvector
        update_data = []
        processed_count = 0
        
        # Dividir em chunks para batch pgvector processing
        embedding_chunks = [embedding_batch[i:i + PGVECTOR_BATCH_SIZE] 
                          for i in range(0, len(embedding_batch), PGVECTOR_BATCH_SIZE)]
        
        log_message(f"👷 Worker {worker_id}: Dividido em {len(embedding_chunks)} chunks de {PGVECTOR_BATCH_SIZE}", "debug")
        
        total_chunks = len(embedding_chunks)
        
        for chunk_idx, chunk in enumerate(embedding_chunks):
            try:
                chunk_start_time = time.time()
                
                # Progress para chunk atual
                base_progress = 10 + (chunk_idx / total_chunks) * 70  # 10% a 80% para processamento
                if progress_callback:
                    progress_callback(int(base_progress), f"🚀 Chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} emb)")
                
                log_message(f"👷 Worker {worker_id}: Processando chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} embeddings)", "debug")
                
                # BATCH PGVECTOR SEARCH V5D
                pgvector_start = time.time()
                similarity_results = batch_pgvector_similarity_search_debug(cursor, chunk)
                pgvector_time = log_timing(f"Worker {worker_id} - Chunk {chunk_idx + 1} PGVector", pgvector_start)
                
                # Processar resultados do batch
                process_start = time.time()
                for embedding_data in chunk:
                    id_emb = embedding_data['id_contratacao_emb']
                    numero_controle = embedding_data['numero_controle_pncp']
                    
                    if id_emb in similarity_results:
                        category_results = similarity_results[id_emb]
                        
                        if category_results:  # Verificar se há resultados não-vazios
                            # Extrair códigos e similaridades
                            top_categories = [row[0] for row in category_results]
                            top_similarities = [round(float(row[2]), 4) for row in category_results]
                            
                            # Calcular confiança
                            confidence = calculate_confidence(top_similarities)
                            
                            # Preparar dados para batch update
                            update_data.append({
                                'id': id_emb,
                                'top_categories': top_categories,
                                'top_similarities': top_similarities,
                                'confidence': confidence
                            })
                            
                            local_stats['categorizacoes_aplicadas'] += 1
                            
                            if debug_mode and local_stats['categorizacoes_aplicadas'] <= 3:
                                log_message(f"✅ Worker {worker_id}: {numero_controle} → {top_categories[0]} (sim: {top_similarities[0]:.4f})", "debug")
                        else:
                            if debug_mode:
                                log_message(f"🚨 Worker {worker_id}: ID {id_emb} ({numero_controle}) - similarity_results vazio!", "debug")
                            log_message(f"Worker {worker_id}: Nenhuma categoria encontrada para {numero_controle} (resultados vazios)", "warning")
                            local_stats['erros'] += 1
                    else:
                        if debug_mode:
                            log_message(f"🚨 Worker {worker_id}: ID {id_emb} ({numero_controle}) não encontrado em similarity_results!", "debug")
                            log_message(f"🚨 DEBUG: similarity_results tem {len(similarity_results)} chaves: {list(similarity_results.keys())[:5]}...", "debug")
                        log_message(f"Worker {worker_id}: Nenhuma categoria encontrada para {numero_controle} (não está nos resultados)", "warning")
                        local_stats['erros'] += 1
                    
                    local_stats['embeddings_processados'] += 1
                    processed_count += 1
                
                process_time = log_timing(f"Worker {worker_id} - Chunk {chunk_idx + 1} Processamento", process_start)
                chunk_total = log_timing(f"Worker {worker_id} - Chunk {chunk_idx + 1} TOTAL", chunk_start_time, 
                                       f"PGVector: {pgvector_time:.2f}s, Process: {process_time:.2f}s")
                
                # Progress para chunk concluído
                end_progress = 10 + ((chunk_idx + 1) / total_chunks) * 70
                if progress_callback:
                    progress_callback(int(end_progress), f"✅ Chunk {chunk_idx + 1}/{total_chunks} em {chunk_total:.2f}s")
                        
            except Exception as e:
                log_message(f"Worker {worker_id}: Erro ao processar chunk {chunk_idx + 1}: {e}", "error")
                local_stats['erros'] += len(chunk)
        
        # ETAPA 3: Batch update
        if update_data:
            if progress_callback:
                progress_callback(85, f"💾 Salvando {len(update_data)} resultados...")
            
            update_start = time.time()
            log_message(f"👷 Worker {worker_id}: Executando batch update de {len(update_data)} registros", "debug")
            
            # Preparar dados para execute_values
            update_values = []
            for item in update_data:
                update_values.append((
                    item['id'],
                    item['top_categories'],
                    item['top_similarities'], 
                    item['confidence']
                ))
            
            # BATCH UPDATE
            update_query = """
                UPDATE contratacao_emb SET
                    top_categories = data.top_categories::text[],
                    top_similarities = data.top_similarities::numeric[],
                    confidence = data.confidence::numeric
                FROM (VALUES %s) AS data(id, top_categories, top_similarities, confidence)
                WHERE contratacao_emb.id_contratacao_emb = data.id::bigint
                  AND contratacao_emb.top_categories IS NULL
            """
            
            log_message(f"🗄️ Worker {worker_id}: EXECUTANDO BATCH UPDATE", "sql_debug")
            log_message(f"🗄️ SQL: {update_query.strip()}", "sql_debug")
            log_message(f"🗄️ Registros para update: {len(update_values)}", "sql_debug")
            
            # Log amostra dos dados (só primeiros 3)
            for i, sample in enumerate(update_values[:3]):
                log_message(f"🗄️ [{i+1}] ID: {sample[0]}, Cats: {sample[1]}, Sims: {sample[2]}, Conf: {sample[3]}", "sql_debug")
            
            execute_values(
                cursor,
                update_query,
                update_values,
                template='(%s, %s, %s, %s)',
                page_size=200
            )
            
            log_message(f"🗄️ Worker {worker_id}: execute_values concluído, fazendo commit...", "sql_debug")
            commit_start = time.time()
            conn.commit()
            commit_time = log_timing(f"Worker {worker_id} - Commit", commit_start)
            
            update_time = log_timing(f"Worker {worker_id} - Batch Update", update_start, f"{len(update_data)} registros")
            log_message(f"🗄️ Worker {worker_id}: COMMIT CONCLUÍDO (tempo: {commit_time:.3f}s)", "sql_debug")
            
            if progress_callback:
                progress_callback(95, f"✅ Salvos {len(update_data)} em {update_time:.2f}s")
        
        # ETAPA 4: Finalização
        if progress_callback:
            progress_callback(100, f"🎉 Concluído!")
        
        cursor.close()
        return_db_connection(conn)
        
        close_time = log_timing(f"Worker {worker_id} - Fechamento conexão", time.time())
        log_message(f"🗄️ Worker {worker_id}: Conexão fechada (tempo: {close_time:.3f}s)", "sql_debug")
        
        worker_total = log_timing(f"Worker {worker_id} TOTAL", worker_start_time, 
                                f"{local_stats['categorizacoes_aplicadas']} categorizações, {local_stats['erros']} erros")
        
        log_message(f"👷 Worker {worker_id}: CONCLUÍDO em {worker_total:.2f}s - {local_stats['categorizacoes_aplicadas']} categorizações de {local_stats['embeddings_processados']} embeddings", "debug")
        
        return local_stats
        
    except Exception as e:
        log_message(f"❌ Worker {worker_id}: ERRO GERAL: {e}", "error")
        
        # Tentar fazer rollback da transação corrompida
        try:
            if 'cursor' in locals():
                cursor.execute("ROLLBACK")
                log_message(f"Worker {worker_id}: Transação revertida após erro", "debug")
        except:
            pass
            
        local_stats['erros'] += len(embedding_batch) - local_stats['embeddings_processados']
        if progress_callback:
            progress_callback(100, f"❌ Erro: {str(e)[:30]}...")
        return local_stats
    finally:
        # SEMPRE tentar fechar conexões
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                return_db_connection(conn)
        except:
            pass

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

def partition_embeddings_optimized(embeddings, num_workers):
    """Divide os embeddings em partições otimizadas para processamento paralelo"""
    if not embeddings:
        return []
    
    total_items = len(embeddings)
    partition_size = max(1, total_items // num_workers)
    
    partitions = []
    for i in range(0, total_items, partition_size):
        partition = embeddings[i:i + partition_size]
        if partition:
            partitions.append(partition)
    
    # Se criamos mais partições que workers, mesclar as últimas
    while len(partitions) > num_workers:
        last_partition = partitions.pop()
        partitions[-1].extend(last_partition)
    
    return partitions

def process_categorization_for_date_debug(date_str):
    """Processa categorização para uma data - DEBUG V5D com estratégia de batches por worker"""
    date_start_time = time.time()
    log_message(f"📅 Processando categorização DEBUG V5D para data: {format_date_for_display(date_str)}")
    
    # ETAPA 1: Obter apenas os numero_controle_pncp da data (RÁPIDO)
    controles_start = time.time()
    controle_ids = get_controle_pncp_by_date(date_str)
    controles_time = log_timing("Busca controles", controles_start)
    
    if not controle_ids:
        log_message(f"Nenhum controle para processar na data {format_date_for_display(date_str)}", "warning")
        return {
            'data': date_str,
            'embeddings_processados': 0,
            'categorizacoes_aplicadas': 0,
            'baixa_confianca': 0,
            'erros': 0
        }
    
    log_message(f"Data {format_date_for_display(date_str)}: encontrados {len(controle_ids)} controles (busca: {controles_time:.2f}s)")
    
    # ETAPA 2: Dividir controles em batches para workers
    batch_start = time.time()
    
    # Calcular tamanho do batch por worker (mais granular)
    controles_per_worker = max(50, len(controle_ids) // MAX_WORKERS)  # Mínimo 50, máximo total/workers
    controle_batches = []
    
    for i in range(0, len(controle_ids), controles_per_worker):
        batch = controle_ids[i:i + controles_per_worker]
        controle_batches.append(batch)
    
    log_timing("Criação batches", batch_start, f"{len(controle_batches)} batches de ~{controles_per_worker} controles")
    
    log_message(f"📊 Estratégia V5D: {len(controle_ids)} controles → {len(controle_batches)} batches de ~{controles_per_worker} controles", "info")
    
    # Estatísticas da data
    date_stats = {
        'data': date_str,
        'embeddings_processados': 0,
        'categorizacoes_aplicadas': 0,
        'baixa_confianca': 0,
        'erros': 0
    }
    
    # ETAPA 3: Processamento com workers independentes
    processing_start = time.time()
    
    # Progress bars individuais para cada worker
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Tasks individuais por worker
        worker_tasks = {}
        for i in range(len(controle_batches)):
            worker_id = i + 1
            batch_size = len(controle_batches[i])
            worker_tasks[worker_id] = progress.add_task(
                f"[cyan]👷 Worker {worker_id}: Preparando... ({batch_size} controles)",
                total=100
            )
        
        # Progress tracking
        worker_progress_tracking = {i + 1: {'progress': 0, 'status': 'Preparando...'} for i in range(len(controle_batches))}
        
        def process_controle_batch_worker(worker_id, controle_batch, date_str):
            """Worker que processa um batch de controles"""
            def worker_progress_callback(completed_percent, status="Processando..."):
                worker_progress_tracking[worker_id]['progress'] = completed_percent
                worker_progress_tracking[worker_id]['status'] = status
                progress.update(worker_tasks[worker_id], 
                    completed=completed_percent,
                    description=f"[cyan]👷 Worker {worker_id}: {status} ({len(controle_batch)} controles)"
                )
            
            try:
                worker_start = time.time()
                
                # PASSO 1: Buscar embeddings do batch
                worker_progress_callback(10, "🔍 Buscando embeddings...")
                embeddings = get_embeddings_by_controle_batch(controle_batch)
                
                if not embeddings:
                    worker_progress_callback(100, "✅ Sem embeddings")
                    return {
                        'embeddings_processados': 0,
                        'categorizacoes_aplicadas': 0,
                        'baixa_confianca': 0,
                        'erros': 0
                    }
                
                worker_progress_callback(30, f"🚀 Categorizando {len(embeddings)} embeddings...")
                
                # PASSO 2: Categorizar embeddings usando o batch pgvector
                result = categorize_embedding_batch_debug(
                    worker_id, embeddings, 
                    lambda p, s=None: worker_progress_callback(30 + int(p * 0.7), s or "🚀 Categorizando...")
                )
                
                worker_time = log_timing(f"Worker {worker_id} TOTAL", worker_start, 
                                       f"{len(controle_batch)} controles → {result['categorizacoes_aplicadas']} categorizações")
                
                progress.update(worker_tasks[worker_id], 
                    completed=100,
                    description=f"[green]✅ Worker {worker_id}: {worker_time:.1f}s ({len(controle_batch)} controles)"
                )
                
                return result
                
            except Exception as e:
                log_message(f"❌ Erro em worker {worker_id}: {e}", "error")
                progress.update(worker_tasks[worker_id], 
                    completed=100,
                    description=f"[red]❌ Worker {worker_id}: Erro ({len(controle_batch)} controles)"
                )
                return {
                    'embeddings_processados': 0,
                    'categorizacoes_aplicadas': 0,
                    'baixa_confianca': 0,
                    'erros': len(controle_batch)
                }
        
        # Executar workers em paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for i, controle_batch in enumerate(controle_batches):
                future = executor.submit(
                    process_controle_batch_worker,
                    i + 1,
                    controle_batch,
                    date_str
                )
                futures.append(future)
            
            # Coletar resultados com timeout
            for future in futures:
                try:
                    # Timeout de 5 minutos por worker
                    local_stats = future.result(timeout=300)
                    date_stats['embeddings_processados'] += local_stats['embeddings_processados']
                    date_stats['categorizacoes_aplicadas'] += local_stats['categorizacoes_aplicadas']
                    date_stats['baixa_confianca'] += local_stats['baixa_confianca']
                    date_stats['erros'] += local_stats['erros']
                    
                except FutureTimeoutError:
                    log_message(f"⚠️ Worker timeout após 5min para data {date_str}", "warning")
                    future.cancel()
                    date_stats['erros'] += 50  # Estimar erros perdidos
                    
                except Exception as e:
                    log_message(f"❌ Erro em worker DEBUG para data {date_str}: {e}", "error")
                    date_stats['erros'] += 50  # Estimar erros perdidos
    
    processing_time = log_timing("Processamento workers", processing_start)
    
    # Log do resultado da data
    date_display = format_date_for_display(date_str)
    date_total = log_timing(f"Data {date_display} TOTAL", date_start_time, 
                           f"Controles: {controles_time:.2f}s, Process: {processing_time:.2f}s")
    
    log_message(f"✅ Data {date_display} DEBUG V5D concluída em {date_total:.2f}s: {date_stats['categorizacoes_aplicadas']} categorizações, {date_stats['erros']} erros", 
                "success" if date_stats['erros'] == 0 else "warning")
    
    return date_stats

#############################################
# FUNÇÃO PRINCIPAL DEBUG V5D
#############################################

def main():
    """Função principal da categorização automática DEBUG V5D"""
    global debug_mode
    
    # Parse dos argumentos
    args = parse_arguments()
    debug_mode = args.debug  # DEBUG só ativa se --debug for passado
    test_mode = args.test
    
    # Setup do logging
    logger, log_filename = setup_logging(debug_mode)
    
    console.print(Panel("[bold blue][5D/7] CATEGORIZAÇÃO AUTOMÁTICA ULTRA DEBUG V3[/bold blue]"))
    
    log_message(f"Arquivo de log criado: {log_filename}", "info")
    log_message(f"Configurações DEBUG V5D: {MAX_WORKERS} workers, pgvector batch {PGVECTOR_BATCH_SIZE}", "info")
    log_message("🔧 MODO DEBUG EXTREMO ATIVADO - Todos os timings serão registrados", "warning")
    
    if test_mode:
        log_message("Modo TESTE ativado: processando próximo dia", "warning")
    
    # Inicializar pool de conexões
    if not initialize_connection_pool():
        log_message("Falha ao inicializar pool de conexões", "error")
        return
    
    try:
        # Verificar se existem embeddings de categorias
        if not check_categoria_embeddings():
            log_message("Não foram encontrados embeddings de categorias na base", "error")
            log_message("Execute primeiro o script de geração de embeddings de categorias", "warning")
            return
        
        # Obter datas para processar
        last_categorization_date = get_last_categorization_date()
        log_message(f"Última data de categorização: {format_date_for_display(last_categorization_date)}")
        
        if not test_mode:
            last_embedding_date = get_last_embedding_date()
            log_message(f"Última data de embeddings: {format_date_for_display(last_embedding_date)}")
            
            # Verificar se há intervalo válido para processar
            if last_categorization_date >= last_embedding_date:
                log_message(f"Categorizações já estão atualizadas até {last_categorization_date} (>= {last_embedding_date})", "success")
                return
                
            log_message(f"Processando categorização DEBUG V5D do intervalo: {last_categorization_date} (exclusivo) até {last_embedding_date} (inclusivo)")
        else:
            last_embedding_date = None
        
        # Gerar lista de datas para processar
        dates_to_process = generate_dates_for_categorization(last_categorization_date, test_mode, last_embedding_date)
        
        if not dates_to_process:
            log_message("Nenhuma data nova para processar", "success")
            return
        
        log_message(f"Processando {len(dates_to_process)} datas com DEBUG V5D EXTREMO")
        
        # Estatísticas globais
        global_stats_total = {
            'datas_processadas': 0,
            'embeddings_processados': 0,
            'categorizacoes_aplicadas': 0,
            'baixa_confianca': 0,
            'erros': 0
        }
        
        # Processar cada data
        inicio = time.time()
        
        for date_str in dates_to_process:
            try:
                # Separador visual entre datas
                if global_stats_total['datas_processadas'] > 0:
                    log_message("-" * 80, "info")
                
                date_display = format_date_for_display(date_str)
                log_message("")
                log_message(f"📅 [bold blue]Data {date_display} - DEBUG V5D EXTREMO[/bold blue]: categorizando...")
                
                # Reset estatísticas para esta data
                global global_stats
                global_stats = {
                    'embeddings_processados': 0,
                    'categorizacoes_aplicadas': 0,
                    'baixa_confianca': 0,
                    'erros': 0
                }
                
                # Processar categorização para a data com DEBUG V5D
                date_stats = process_categorization_for_date_debug(date_str)
                
                # Atualizar estatísticas globais
                global_stats_total['datas_processadas'] += 1
                global_stats_total['embeddings_processados'] += date_stats['embeddings_processados']
                global_stats_total['categorizacoes_aplicadas'] += date_stats['categorizacoes_aplicadas']
                global_stats_total['baixa_confianca'] += date_stats['baixa_confianca']
                global_stats_total['erros'] += date_stats['erros']
                
                # Atualizar última data processada APENAS se não houve erros críticos
                if date_stats['erros'] == 0:
                    update_last_categorization_date(date_str)
                    log_message(f"✅ Data {date_display} DEBUG V5D concluída com sucesso: {date_stats['categorizacoes_aplicadas']} categorizações", "success")
                else:
                    log_message(f"⚠️  Data {date_display} DEBUG V5D concluída com {date_stats['erros']} erros - data NÃO atualizada", "warning")
                    
            except Exception as e:
                date_display = format_date_for_display(date_str)
                log_message(f"❌ Erro ao processar data {date_display} DEBUG V5D: {e}", "error")
                global_stats_total['erros'] += 1
        
        # Relatório final
        tempo_total = time.time() - inicio
        
        # Log de finalização detalhado no arquivo
        log_session_end(global_stats_total, tempo_total)
        
        log_message(f"Categorização DEBUG V5D concluída em {tempo_total:.1f}s", "success")
        log_message(f"Datas processadas: {global_stats_total['datas_processadas']}")
        log_message(f"Embeddings processados: {global_stats_total['embeddings_processados']}")
        log_message(f"Categorizações aplicadas: {global_stats_total['categorizacoes_aplicadas']}")
        log_message(f"Erros: {global_stats_total['erros']}")
        
        # Calcular taxa de sucesso
        if global_stats_total['embeddings_processados'] > 0:
            taxa_sucesso = (global_stats_total['categorizacoes_aplicadas'] / global_stats_total['embeddings_processados']) * 100
            log_message(f"Taxa de categorização: {taxa_sucesso:.1f}%")
        
        # Mostrar tabela de performance
        table = Table(title="📊 ANÁLISE DE PERFORMANCE DEBUG V5D")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        if global_stats_total['embeddings_processados'] > 0:
            emb_por_segundo = global_stats_total['embeddings_processados'] / tempo_total
            table.add_row("Embeddings/segundo", f"{emb_por_segundo:.2f}")
        
        console.print(table)
        
        if global_stats_total['erros'] == 0:
            console.print(Panel("[bold green]✅ CATEGORIZAÇÃO DEBUG V5D CONCLUÍDA[/bold green]"))
        else:
            console.print(Panel("[bold yellow]⚠️ DEBUG V5D CONCLUÍDA COM ALGUNS ERROS[/bold yellow]"))
    
    except KeyboardInterrupt:
        log_message("⚠️ Script DEBUG interrompido pelo usuário (Ctrl+C)", "warning")
        console.print(Panel("[bold yellow]⚠️ DEBUG INTERROMPIDO PELO USUÁRIO[/bold yellow]"))
    except Exception as e:
        log_message(f"❌ Erro crítico no DEBUG V5D: {e}", "error")
        console.print(Panel("[bold red]❌ ERRO CRÍTICO NO DEBUG V5D[/bold red]"))
    finally:
        # SEMPRE fechar pool de conexões
        close_connection_pool()
        log_message("🔒 Pool de conexões fechado com segurança", "info")

if __name__ == "__main__":
    main()
