# =======================================================================
# [4D/7] GERAÇÃO DE EMBEDDINGS ULTRA OTIMIZADA - VERSÃO V1
# =======================================================================
# Versão ultra otimizada do script 04C com melhorias de performance críticas
# 
# CORREÇÕES PRINCIPAIS V4D:
# - Eliminada verificação desnecessária de constraints DDL
# - Removida verificação redundante de duplicatas (já filtrada na query)
# - Query principal otimizada com LEFT JOIN ao invés de subconsulta
# - Batch size aumentado para 200 (era 50)
# - Workers reduzidos para 12 (era 20) - menos contenção
# - Pool de conexões otimizado para 14 conexões (era 22)
# - Statement timeout aumentado para 60s em inserções
# - Metadata simplificado sem JSON encoding desnecessário
# 
# PRINCIPAIS OTIMIZAÇÕES MANTIDAS:
# - Pool de conexões reutilizáveis para evitar timeouts SSL
# - Rate limiting inteligente para API OpenAI
# - Circuit breaker para recuperação de erros
# - Batch size adaptativo baseado no tamanho do texto
# 
# Funcionalidades:
# - Lê contratações não processadas da base v1
# - Concatena objeto_compra + descrições dos itens
# - Gera embeddings usando text-embedding-3-large (3072 dimensões)
# - Armazena na tabela contratacao_emb
# - Atualiza system_config com última data processada
# 
# Resultado: Embeddings prontos para categorização (script 05)
# =======================================================================

import os
import sys
import time
import json
import pickle
import threading
import argparse
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from openai import OpenAI

# Configuração global
debug_mode = False
logger = None
connection_pool = None

# Configure Rich console
console = Console()

# Configurações de embedding ULTRA OTIMIZADAS V4E - CORRIGIDAS
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
MIN_WORKERS = 5
MAX_WORKERS = 16   # REDUZIDO: Menos contenção, mais estabilidade
BATCH_SIZE = 25   # REDUZIDO: Melhor para API OpenAI e timeouts
NUM_CONN = MAX_WORKERS + 4

#############################################
# CLASSES DE OTIMIZAÇÃO
#############################################

class RateLimiter:
    """Rate limiter inteligente para API OpenAI - CORRIGIDO V4E"""
    def __init__(self, rpm=3000):  # REDUZIDO: Margem mais conservadora
        self.rpm = rpm
        self.calls = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Aguarda se necessário para não exceder rate limit"""
        with self.lock:
            now = time.time()
            # Remover calls antigas (> 1 minuto)
            self.calls = [t for t in self.calls if now - t < 60]
            
            if len(self.calls) >= self.rpm:
                sleep_time = 60 - (now - self.calls[0]) + 0.5  # Margem extra aumentada
                if sleep_time > 0:
                    log_message(f"Rate limit: aguardando {sleep_time:.1f}s", "warning")
                    time.sleep(sleep_time)
                    # Limpar calls antigas após o sleep
                    self.calls = [t for t in self.calls if time.time() - t < 60]
            
            self.calls.append(time.time())

class CircuitBreaker:
    """Circuit breaker para recuperação de erros"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Executa função com circuit breaker"""
        with self.lock:
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = 'half-open'
                    log_message("Circuit breaker: mudando para half-open", "info")
                else:
                    raise Exception("Circuit breaker aberto - muitas falhas recentes")
        
        try:
            result = func(*args, **kwargs)
            with self.lock:
                if self.state == 'half-open':
                    self.state = 'closed'
                    self.failure_count = 0
                    log_message("Circuit breaker: voltando para closed", "success")
            return result
            
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                    log_message(f"Circuit breaker: abrindo após {self.failure_count} falhas", "error")
                
            raise e

# Instâncias globais
rate_limiter = RateLimiter()
circuit_breaker = CircuitBreaker()

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Geração de Embeddings v1 Otimizada')
    parser.add_argument('--test', 
                       help='Executar para data específica (formato YYYYMMDD)',
                       type=str)
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
    
    LOG_FILE = os.path.join(logs_dir, f"04D_embeddings_ultra_optimized_{start_timestamp}.log")
    
    # Configurar logger principal
    logger = logging.getLogger('embedding_generation_ultra_optimized')
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
    
    # REDUZIR DEBUG EXCESSIVO DA OPENAI
    openai_loggers = [
        'openai', 'httpx', 'httpcore', 'httpcore.http11', 'httpcore.connection',
        'urllib3.connectionpool', 'requests.packages.urllib3.connectionpool'
    ]
    
    for logger_name in openai_loggers:
        openai_logger = logging.getLogger(logger_name)
        openai_logger.setLevel(logging.ERROR)
        openai_logger.propagate = False
    
    logger.info("=" * 80)
    logger.info("NOVA SESSÃO DE GERAÇÃO DE EMBEDDINGS ULTRA OTIMIZADA V4D INICIADA")
    logger.info("=" * 80)
    logger.info(f"Horário de início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Modo debug: {'Ativado' if debug_mode else 'Desativado'}")
    logger.info(f"Arquivo de log: {LOG_FILE}")
    logger.info(f"OTIMIZAÇÕES V4D: Workers={MAX_WORKERS}, BatchSize={BATCH_SIZE}, Pool={MAX_WORKERS} conexões")
    logger.info("-" * 80)
    
    return logger, os.path.basename(LOG_FILE)

def log_session_end(stats, tempo_total):
    """Finaliza a sessão de log com resumo - V4D"""
    if logger:
        logger.info("-" * 80)
        logger.info("SESSÃO DE GERAÇÃO DE EMBEDDINGS ULTRA OTIMIZADA V4D FINALIZADA")
        logger.info(f"Horário de término: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Tempo total: {tempo_total:.1f}s")
        logger.info(f"Datas processadas: {stats['datas_processadas']}")
        logger.info(f"Contratações processadas: {stats['contratacoes_processadas']:,}")
        logger.info(f"Embeddings gerados: {stats['embeddings_gerados']:,}")
        logger.info(f"Embeddings em cache: {stats['embeddings_cache']:,}")
        logger.info(f"Erros encontrados: {stats['erros']:,}")
        logger.info("OTIMIZAÇÕES V4D APLICADAS: Sem constraints, sem duplicatas redundantes, LEFT JOIN, batch size maior")
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
    
    # Mostrar no console apenas se for modo debug ou não for debug message
    if not debug_mode and log_type == "debug":
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

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configurações do banco PostgreSQL V1 (Supabase) - ULTRA OTIMIZADAS V4E
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', ''),
    'connect_timeout': 15,
    'options': '-c statement_timeout=45000',  # 45s timeout para SELECTs
    'keepalives_idle': 600,      # 10 minutos antes do keepalive
    'keepalives_interval': 30,   # Interval entre keepalives
    'keepalives_count': 3,       # Máximo keepalives antes de considerar morto
    'sslmode': 'require'         # SSL obrigatório mas sem verificação rigorosa
}

# Config separada para inserções com timeout maior
DB_CONFIG_INSERT = {
    **DB_CONFIG,
    'options': '-c statement_timeout=120000',  # 120s timeout para INSERTs
    'keepalives_idle': 300,      # 5 minutos para inserções
}

# Configurações OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Cache e controle de concorrência
cache_lock = threading.Lock()
stats_lock = threading.Lock()

# Estatísticas globais
global_stats = {
    'contratacoes_processadas': 0,
    'embeddings_gerados': 0,
    'embeddings_cache': 0,
    'erros': 0
}

#############################################
# POOL DE CONEXÕES OTIMIZADO
#############################################

def initialize_connection_pool():
    """Inicializa pool de conexões thread-safe ULTRA OTIMIZADO V4E"""
    global connection_pool
    try:
        # CORREÇÃO V4E: Pool menor e mais estável
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=MIN_WORKERS,
            maxconn=NUM_CONN,  # Pequena margem extra
            **DB_CONFIG
        )
        log_message(f"Pool de conexões ESTÁVEL criado: {NUM_CONN} conexões máximas", "success")
        return True
    except Exception as e:
        log_message(f"Erro ao criar pool de conexões: {e}", "error")
        return False

def close_connection_pool():
    """Fecha pool de conexões com segurança total"""
    global connection_pool
    if connection_pool:
        try:
            # Fechar todas as conexões ativas
            connection_pool.closeall()
            log_message("🔒 Pool de conexões fechado com segurança", "info")
        except Exception as e:
            log_message(f"⚠️ Erro ao fechar pool: {e}", "warning")
        finally:
            connection_pool = None

@contextmanager
def get_db_connection():
    """Context manager para obter conexão do pool com tratamento robusto V4E"""
    global connection_pool
    if not connection_pool:
        raise Exception("Pool de conexões não inicializado")
    
    conn = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = connection_pool.getconn()
            if conn and not conn.closed:
                # Testar conexão com ping simples
                with conn.cursor() as test_cursor:
                    test_cursor.execute("SELECT 1")
                yield conn
                break
            else:
                # Conexão fechada, tentar nova
                if conn:
                    connection_pool.putconn(conn, close=True)
                retry_count += 1
                if retry_count < max_retries:
                    log_message(f"Conexão fechada detectada, tentativa {retry_count}/{max_retries}", "warning")
                    time.sleep(1)
                    continue
                else:
                    raise Exception("Falha ao obter conexão válida após múltiplas tentativas")
                    
        except Exception as e:
            if conn:
                try:
                    if not conn.closed:
                        conn.rollback()
                except:
                    pass
                try:
                    connection_pool.putconn(conn, close=True)
                except:
                    pass
                conn = None
            
            retry_count += 1
            if retry_count < max_retries:
                log_message(f"Erro na conexão, tentativa {retry_count}/{max_retries}: {e}", "warning")
                time.sleep(1)
            else:
                raise e
    
    # Finally block
    if conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            log_message(f"⚠️ Erro ao devolver conexão ao pool: {e}", "warning")

def create_connection():
    """DEPRECATED: Usar get_db_connection() context manager"""
    log_message("Aviso: create_connection() é deprecated, use get_db_connection()", "warning")
    return psycopg2.connect(**DB_CONFIG)

#############################################
# FUNÇÕES DE BANCO DE DADOS ULTRA OTIMIZADAS V4D
#############################################

# OTIMIZAÇÃO V4D: Função de constraints removida - DDL desnecessário a cada execução

def get_last_embedding_date():
    """Obtém a última data de processamento de embeddings do system_config"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM system_config 
                WHERE key = 'last_embedding_date'
            """)
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                return "20200101"
                
    except Exception as e:
        log_message(f"Erro ao obter última data de embedding: {e}", "error")
        return "20200101"

def get_last_processed_date():
    """Obtém a última data de processamento geral do system_config"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM system_config 
                WHERE key = 'last_processed_date'
            """)
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                return datetime.now().strftime("%Y%m%d")
                
    except Exception as e:
        log_message(f"Erro ao obter última data processada: {e}", "error")
        return datetime.now().strftime("%Y%m%d")

def update_last_embedding_date(date_str):
    """Atualiza a última data de processamento de embeddings no system_config"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_config (key, value, description) 
                VALUES ('last_embedding_date', %s, 'Última data processada para geração de embeddings')
                ON CONFLICT (key) 
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """, (date_str,))
            conn.commit()
            log_message(f"Data de embedding atualizada para: {date_str}", "success")
            return True
        
    except Exception as e:
        log_message(f"Erro ao atualizar data de embedding: {e}", "error")
        return False

def generate_dates_for_processing(last_embedding_date, test_date=None, last_processed_date=None):
    """
    NOVA FUNÇÃO V4C: Gera lista de datas usando loop simples ao invés de query pesada
    """
    try:
        if test_date:
            # Modo teste: apenas uma data
            log_message(f"Modo teste: processando apenas data {format_date_for_display(test_date)}", "info")
            return [test_date]
        
        if not last_processed_date:
            log_message("Última data processada não encontrada", "warning")
            return []
        
        # Converter strings YYYYMMDD para objetos datetime
        try:
            start_date = datetime.strptime(last_embedding_date, '%Y%m%d') + timedelta(days=1)
            end_date = datetime.strptime(last_processed_date, '%Y%m%d')
        except ValueError as e:
            log_message(f"Erro ao converter datas: {e}", "error")
            return []
        
        # Verificar se há intervalo válido
        if start_date > end_date:
            log_message(f"Última data de embedding ({last_embedding_date}) já está atualizada", "info")
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
        log_message(f"Erro ao gerar datas para processamento: {e}", "error")
        return []

def count_contratacoes_by_date(date_str):
    """Conta contratações que precisam de embedding para uma data específica"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            
            query = """
                SELECT COUNT(*)
                FROM contratacao c
                WHERE c.data_publicacao_pncp IS NOT NULL 
                  AND DATE(c.data_publicacao_pncp) = %s::date
                  AND NOT EXISTS (
                      SELECT 1 FROM contratacao_emb e 
                      WHERE e.numero_controle_pncp = c.numero_controle_pncp
                  )
            """
            
            cursor.execute(query, (date_formatted,))
            count = cursor.fetchone()[0]
            return count
        
    except Exception as e:
        log_message(f"Erro ao contar contratações da data {date_str}: {e}", "error")
        return 0

def get_contratacoes_by_date(date_str):
    """Obtém contratações de uma data específica - ULTRA OTIMIZADO V4D"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            
            # QUERY ULTRA OTIMIZADA V4D: LEFT JOIN ao invés de subconsulta correlacionada
            query = """
            SELECT 
                c.numero_controle_pncp,
                c.objeto_compra,
                COALESCE(string_agg(COALESCE(i.descricao_item, ''), ' :: '), '') as itens_concatenados
            FROM contratacao c
            LEFT JOIN item_contratacao i ON i.numero_controle_pncp = c.numero_controle_pncp
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND DATE(c.data_publicacao_pncp) = %s::date
              AND NOT EXISTS (
                  SELECT 1 FROM contratacao_emb e 
                  WHERE e.numero_controle_pncp = c.numero_controle_pncp
              )
            GROUP BY c.numero_controle_pncp, c.objeto_compra
            ORDER BY c.numero_controle_pncp
            """
            
            cursor.execute(query, (date_formatted,))
            results = cursor.fetchall()
            
            # Reformatar para manter compatibilidade
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'numero_controle_pncp': row['numero_controle_pncp'],
                    'descricao_completa': f"{row['objeto_compra']} :: {row['itens_concatenados']}"
                })
            
            return formatted_results
        
    except Exception as e:
        log_message(f"Erro ao buscar contratações da data {date_str}: {e}", "error")
        return []

#############################################
# FUNÇÕES DE EMBEDDING ULTRA OTIMIZADAS V4D
#############################################

# OTIMIZAÇÃO V4D: check_batch_duplicates REMOVIDA - já filtrada na query principal

def calculate_optimal_batch_size(texts):
    """Calcula batch size ótimo baseado no tamanho dos textos - CORRIGIDO V4E"""
    if not texts:
        return BATCH_SIZE
    
    avg_length = sum(len(str(t)) for t in texts) / len(texts)
    
    # Batch sizes MENORES para maior estabilidade V4E
    if avg_length > 4000:
        return min(10, len(texts))   # REDUZIDO: Era 50, agora 10
    elif avg_length > 2000:
        return min(20, len(texts))   # REDUZIDO: Era 100, agora 20  
    else:
        return min(50, len(texts))   # REDUZIDO: Era 200, agora 50

def generate_embeddings_batch_optimized(texts, max_retries=3):
    """Gera embeddings com rate limiting e circuit breaker"""
    if not texts:
        return []
    
    # Validar e limpar textos
    validated_texts = []
    for text in texts:
        if not isinstance(text, str):
            text = str(text)
        
        if not text.strip():
            text = "sem descrição"
        
        # Limitar tamanho do texto
        if len(text) > 8000:
            text = text[:8000]
            
        validated_texts.append(text)
    
    # Função interna para geração (será chamada pelo circuit breaker)
    def _generate_embeddings():
        # Aguardar rate limit
        rate_limiter.wait_if_needed()
        
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=validated_texts
        )
        
        embeddings = []
        for item in response.data:
            emb = np.array(item.embedding, dtype=np.float32)
            
            # Verificar e ajustar dimensão se necessário
            if emb.shape[0] != EMBEDDING_DIM:
                log_message(f"Embedding com dimensão incorreta: {emb.shape[0]} != {EMBEDDING_DIM}", "warning")
                if len(emb) > EMBEDDING_DIM:
                    emb = emb[:EMBEDDING_DIM]
                else:
                    padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                    padded[:len(emb)] = emb
                    emb = padded
            
            embeddings.append(emb)
        
        return embeddings
    
    # Retry com circuit breaker
    for attempt in range(max_retries):
        try:
            return circuit_breaker.call(_generate_embeddings)
            
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                log_message(f"Rate limit atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {wait_time}s", "warning")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                log_message(f"Erro na API OpenAI (tentativa {attempt+1}): {e}", "warning")
                time.sleep(1)  # Breve pausa antes de retry
            else:
                log_message(f"Erro final na API OpenAI: {e}", "error")
                raise
    
    return []

#############################################
# PROCESSAMENTO PARALELO OTIMIZADO
#############################################

def process_embedding_batch_optimized(worker_id, batch_contratacoes, date_str, progress_callback=None):
    """Processa um lote de contratações - ULTRA OTIMIZADO V4D"""
    local_stats = {
        'contratacoes_processadas': 0,
        'embeddings_gerados': 0,
        'embeddings_cache': 0,
        'erros': 0
    }
    
    try:
        # DEBUG: Log inicial do worker
        log_message(f"🔧 Worker {worker_id}: Iniciando processamento de {len(batch_contratacoes)} contratos", "debug")
        
        # Callback - iniciando
        if progress_callback:
            progress_callback(0)
        
        # OTIMIZAÇÃO V4D: Não verificar duplicatas - já filtradas na query principal
        to_process = batch_contratacoes  # Todos os registros já foram filtrados
        
        if not to_process:
            log_message(f"🔧 Worker {worker_id}: Nenhum contrato para processar", "debug")
            if progress_callback:
                progress_callback(100)
            return local_stats
        
        log_message(f"🔧 Worker {worker_id}: Processando {len(to_process)} contratos válidos", "debug")
        
        # Callback - meio do processamento
        if progress_callback:
            progress_callback(30)
        
        # OTIMIZAÇÃO: Batch size adaptativo
        texts = [item['descricao_completa'] for item in to_process]
        optimal_batch_size = calculate_optimal_batch_size(texts)
        
        log_message(f"🔧 Worker {worker_id}: Batch size otimizado: {optimal_batch_size} (de {len(texts)} textos)", "debug")
        
        # Callback - processamento de embeddings
        if progress_callback:
            progress_callback(50)
        
        # Processar em lotes otimizados
        total_generated = 0
        num_batches = (len(to_process) + optimal_batch_size - 1) // optimal_batch_size
        
        log_message(f"🔧 Worker {worker_id}: Processando {num_batches} lotes de embedding", "debug")
        
        for i, batch_start in enumerate(range(0, len(to_process), optimal_batch_size)):
            batch_to_process = to_process[batch_start:batch_start + optimal_batch_size]
            batch_texts = texts[batch_start:batch_start + optimal_batch_size]
            
            log_message(f"🔧 Worker {worker_id}: Lote {i+1}/{num_batches} - {len(batch_texts)} textos", "debug")
            
            # Gerar embeddings com otimizações
            embeddings = generate_embeddings_batch_optimized(batch_texts)
            
            log_message(f"🔧 Worker {worker_id}: Gerados {len(embeddings)} embeddings para lote {i+1}", "debug")
            
            # Inserir no banco com config otimizada
            success_count = insert_embeddings_batch_optimized(batch_to_process, embeddings, worker_id)
            total_generated += success_count
            
            log_message(f"🔧 Worker {worker_id}: Inseridos {success_count} embeddings no lote {i+1}", "debug")
            
            # Update progress incrementalmente
            if progress_callback:
                batch_progress = 50 + (i + 1) * 40 // num_batches
                progress_callback(min(90, batch_progress))
        
        local_stats['embeddings_gerados'] = total_generated
        local_stats['contratacoes_processadas'] = len(to_process)
        
        log_message(f"🔧 Worker {worker_id}: Concluído - {total_generated} embeddings gerados de {len(to_process)} contratos", "debug")
        
        # Callback - finalizado
        if progress_callback:
            progress_callback(100)
        
        return local_stats
        
    except Exception as e:
        log_message(f"❌ Worker {worker_id}: ERRO no processamento: {e}", "error")
        log_message(f"🔧 Worker {worker_id}: Erro detalhado - {len(batch_contratacoes)} contratos afetados", "debug")
        local_stats['erros'] = len(batch_contratacoes)
        if progress_callback:
            progress_callback(100)
        return local_stats

@contextmanager
def get_db_connection_for_insert():
    """Context manager para inserções com timeout maior - CORRIGIDO V4E"""
    global connection_pool
    if not connection_pool:
        raise Exception("Pool de conexões não inicializado")
    
    conn = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = connection_pool.getconn()
            if conn and not conn.closed:
                # Testar e configurar conexão
                with conn.cursor() as test_cursor:
                    test_cursor.execute("SELECT 1")
                    test_cursor.execute("SET statement_timeout = 120000")  # 120s para inserções
                yield conn
                break
            else:
                # Conexão fechada, tentar nova
                if conn:
                    connection_pool.putconn(conn, close=True)
                retry_count += 1
                if retry_count < max_retries:
                    log_message(f"Conexão de inserção fechada, tentativa {retry_count}/{max_retries}", "warning")
                    time.sleep(2)  # Pausa maior para inserções
                    continue
                else:
                    raise Exception("Falha ao obter conexão de inserção após múltiplas tentativas")
                    
        except Exception as e:
            if conn:
                try:
                    if not conn.closed:
                        conn.rollback()
                except:
                    pass
                try:
                    connection_pool.putconn(conn, close=True)
                except:
                    pass
                conn = None
            
            retry_count += 1
            if retry_count < max_retries:
                log_message(f"Erro na conexão de inserção, tentativa {retry_count}/{max_retries}: {e}", "warning")
                time.sleep(2)
            else:
                raise e
    
    # Finally block
    if conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            log_message(f"⚠️ Erro ao devolver conexão de inserção ao pool: {e}", "warning")

def insert_embeddings_batch_optimized(contratacoes, embeddings, worker_id):
    """Insere embeddings - ULTRA OTIMIZADO V4E"""
    if len(contratacoes) != len(embeddings):
        log_message(f"Worker {worker_id}: Mismatch entre contratações e embeddings", "error")
        return 0
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with get_db_connection_for_insert() as conn:
                cursor = conn.cursor()
                
                # Preparar dados para inserção - METADATA JSON SIMPLIFICADO V4E
                insert_data = []
                for contratacao, embedding in zip(contratacoes, embeddings):
                    # Metadata JSON mínimo mas válido
                    metadata_json = {
                        "orgao": contratacao.get('nome_orgao_entidade', 'N/A')[:50],
                        "model": EMBEDDING_MODEL
                    }
                    
                    insert_data.append((
                        contratacao['numero_controle_pncp'],
                        EMBEDDING_MODEL,
                        json.dumps(metadata_json),
                        embedding.tolist()
                    ))
                
                # Inserção em lote CORRIGIDA - com retry em lotes menores se necessário
                insert_query = """
                    INSERT INTO contratacao_emb (
                        numero_controle_pncp, modelo_embedding, metadata, embeddings
                    ) VALUES %s
                    ON CONFLICT (numero_controle_pncp) DO NOTHING
                """
                
                cursor.execute("BEGIN")
                
                # Se batch for grande, dividir em lotes menores
                batch_size = min(100, len(insert_data))  # Lotes de no máximo 100
                total_inserted = 0
                
                for i in range(0, len(insert_data), batch_size):
                    batch = insert_data[i:i + batch_size]
                    execute_values(
                        cursor,
                        insert_query,
                        batch,
                        template='(%s, %s, %s, %s::vector)',
                        page_size=50  # Page size menor para estabilidade
                    )
                    total_inserted += cursor.rowcount if cursor.rowcount > 0 else 0
                
                cursor.execute("COMMIT")
                return total_inserted
            
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                log_message(f"Worker {worker_id}: Erro na inserção (tentativa {retry_count}/{max_retries}): {e}", "warning")
                time.sleep(1 * retry_count)  # Backoff progressivo
                continue
            else:
                log_message(f"Worker {worker_id}: Erro final na inserção: {e}", "error")
                return 0
    
    return 0

def partition_contratacoes(contratacoes, num_workers):
    """Divide as contratações em partições para processamento paralelo - CORRIGIDO V4D"""
    if not contratacoes:
        return []
    
    # CORREÇÃO V4D: Garantir que não criamos mais partições que workers
    total_items = len(contratacoes)
    partition_size = max(1, total_items // num_workers)
    
    partitions = []
    for i in range(0, total_items, partition_size):
        partition = contratacoes[i:i + partition_size]
        if partition:
            partitions.append(partition)
    
    # CORREÇÃO: Se criamos mais partições que workers, mesclar as últimas
    while len(partitions) > num_workers:
        # Mesclar a última partição com a penúltima
        last_partition = partitions.pop()
        partitions[-1].extend(last_partition)
    
    return partitions

def process_embeddings_for_date(date_str):
    """Processa embeddings para todas as contratações de uma data específica"""
    log_message(f"Processando embeddings para data: {format_date_for_display(date_str)}")
    
    # Obter contratações da data
    contratacoes = get_contratacoes_by_date(date_str)
    
    if not contratacoes:
        log_message(f"Nenhuma contratação para processar na data {format_date_for_display(date_str)}", "warning")
        return {
            'data': date_str,
            'contratacoes_processadas': 0,
            'embeddings_gerados': 0,
            'embeddings_cache': 0,
            'erros': 0
        }
    
    log_message(f"Data {format_date_for_display(date_str)}: processando {len(contratacoes)} contratações")
    
    # Dividir em partições para processamento paralelo
    partitions = partition_contratacoes(contratacoes, MAX_WORKERS)
    
    if not partitions:
        log_message(f"Nenhuma partição criada para data {date_str}", "warning")
        return {
            'data': date_str,
            'contratacoes_processadas': 0,
            'embeddings_gerados': 0,
            'embeddings_cache': 0,
            'erros': 0
        }
    
    # Estatísticas da data
    date_stats = {
        'data': date_str,
        'contratacoes_processadas': 0,
        'embeddings_gerados': 0,
        'embeddings_cache': 0,
        'erros': 0
    }
    
    # MODO DEBUG V4D: Progress bars individuais por worker
    if debug_mode:
        log_message(f"🔧 DEBUG MODE: Mostrando {len(partitions)} workers individuais", "debug")
        
        # Progress com bars individuais por worker (DEBUG)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Task principal
            main_task = progress.add_task(
                f"[bold blue]📊 ULTRA DEBUG: Data {date_str}", 
                total=len(partitions) * 100
            )
            
            # Tasks individuais por worker (só no DEBUG)
            worker_tasks = {}
            for i in range(len(partitions)):
                worker_id = i + 1
                partition_size = len(partitions[i])
                worker_tasks[worker_id] = progress.add_task(
                    f"[cyan]🔧 Worker {worker_id}: {partition_size} contratos",
                    total=100
                )
            
            # Progress tracking para modo debug
            worker_progress_tracking = {i + 1: 0 for i in range(len(partitions))}
            
            def update_debug_progress():
                # Atualizar task principal
                total_progress = sum(worker_progress_tracking.values())
                progress.update(main_task, 
                    completed=total_progress,
                    description=f"[bold blue]📊 ULTRA DEBUG: Data {date_str} ({len(partitions)} workers)"
                )
            
            def process_with_debug_progress(worker_id, partition, date_str):
                def worker_progress_callback(completed_percent):
                    worker_progress_tracking[worker_id] = completed_percent
                    # Atualizar progress bar individual do worker
                    progress.update(worker_tasks[worker_id], 
                        completed=completed_percent,
                        description=f"[cyan]🔧 Worker {worker_id}: {completed_percent}% ({len(partition)} contratos)"
                    )
                    update_debug_progress()
                
                try:
                    result = process_embedding_batch_optimized(
                        worker_id, partition, date_str, worker_progress_callback
                    )
                    # Finalizar progress bar do worker
                    progress.update(worker_tasks[worker_id], 
                        completed=100,
                        description=f"[green]✅ Worker {worker_id}: Concluído ({len(partition)} contratos)"
                    )
                    return result
                except Exception as e:
                    progress.update(worker_tasks[worker_id], 
                        completed=100,
                        description=f"[red]❌ Worker {worker_id}: Erro ({len(partition)} contratos)"
                    )
                    worker_progress_callback(100)
                    raise e
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for i, partition in enumerate(partitions):
                    future = executor.submit(
                        process_with_debug_progress,
                        i + 1,
                        partition,
                        date_str
                    )
                    futures.append(future)
                
                # Aguardar conclusão
                for future in futures:
                    try:
                        local_stats = future.result()
                        date_stats['contratacoes_processadas'] += local_stats['contratacoes_processadas']
                        date_stats['embeddings_gerados'] += local_stats['embeddings_gerados']
                        date_stats['embeddings_cache'] += local_stats['embeddings_cache']
                        date_stats['erros'] += local_stats['erros']
                        
                    except Exception as e:
                        log_message(f"Erro em worker para data {date_str}: {e}", "error")
    
    else:
        # MODO NORMAL: Progress bar único (sem debug)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            total_worker_tasks = len(partitions) * 100
            main_task = progress.add_task(
                f"[bold blue]📊 OTIMIZADA: Data {date_str}", 
                total=total_worker_tasks
            )
            
            # Progress tracking otimizado (modo normal)
            worker_progress_tracking = {i + 1: 0 for i in range(len(partitions))}
            
            def update_general_progress():
                total_progress = sum(worker_progress_tracking.values())
                progress.update(main_task, 
                    completed=total_progress,
                    description=f"[bold blue]📊 OTIMIZADA: Data {date_str} ({len(partitions)} workers)"
                )
            
            def process_with_progress(worker_id, partition, date_str):
                def worker_progress_callback(completed_percent):
                    worker_progress_tracking[worker_id] = completed_percent
                    update_general_progress()
                
                try:
                    result = process_embedding_batch_optimized(
                        worker_id, partition, date_str, worker_progress_callback
                    )
                    return result
                except Exception as e:
                    worker_progress_callback(100)
                    raise e
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for i, partition in enumerate(partitions):
                    future = executor.submit(
                        process_with_progress,
                        i + 1,
                        partition,
                        date_str
                    )
                    futures.append(future)
                
                # Aguardar conclusão
                for future in futures:
                    try:
                        local_stats = future.result()
                        date_stats['contratacoes_processadas'] += local_stats['contratacoes_processadas']
                        date_stats['embeddings_gerados'] += local_stats['embeddings_gerados']
                        date_stats['embeddings_cache'] += local_stats['embeddings_cache']
                        date_stats['erros'] += local_stats['erros']
                        
                    except Exception as e:
                        log_message(f"Erro em worker para data {date_str}: {e}", "error")
    
    # Log do resultado da data com formatação bonita
    date_display = format_date_for_display(date_str)
    log_message(f"✅ Data {date_display} concluída: {date_stats['embeddings_gerados']} embeddings gerados, {date_stats['erros']} erros", 
                "success" if date_stats['erros'] == 0 else "warning")
    
    return date_stats

#############################################
# FUNÇÃO PRINCIPAL
#############################################

def main():
    """Função principal ULTRA OTIMIZADA do processamento de embeddings V4D"""
    global debug_mode
    
    # Parse dos argumentos
    args = parse_arguments()
    debug_mode = args.debug
    test_date = args.test
    
    # Setup do logging
    logger, log_filename = setup_logging(debug_mode)
    
    console.print(Panel("[bold blue][4D/7] GERAÇÃO DE EMBEDDINGS ULTRA OTIMIZADA V1[/bold blue]"))
    
    log_message(f"Arquivo de log criado: {log_filename}", "info")
    log_message(f"Configurações CORRIGIDAS V4E: {MAX_WORKERS} workers, batch size {BATCH_SIZE}, pool {MAX_WORKERS + 2} conexões", "info")
    
    # Verificar configurações essenciais
    if not os.getenv("OPENAI_API_KEY"):
        log_message("OPENAI_API_KEY não encontrada", "error")
        return
    
    # Inicializar pool de conexões
    if not initialize_connection_pool():
        log_message("Falha ao inicializar pool de conexões", "error")
        return
    
    try:
        # OTIMIZAÇÃO V4D: Constraints removidas - assumidas já existentes
        log_message("Constraints assumidas como já existentes - otimização V4D", "info")
        
        if test_date:
            log_message(f"Modo TESTE ativado para data: {test_date}", "warning")
        
        # Obter última data de processamento de embeddings
        last_embedding_date = get_last_embedding_date()
        log_message(f"Última data de embedding processada: {last_embedding_date}")
        
        # No modo produção, obter também a última data processada geral
        last_processed_date = None
        if not test_date:
            last_processed_date = get_last_processed_date()
            log_message(f"Última data processada geral: {last_processed_date}")
            
            # Verificar se há intervalo válido para processar
            if last_embedding_date >= last_processed_date:
                log_message(f"Embeddings já estão atualizados até {last_embedding_date} (>= {last_processed_date})", "success")
                return
            
            log_message(f"Processando embeddings do intervalo: {last_embedding_date} (exclusivo) até {last_processed_date} (inclusivo)")
        
        # CORREÇÃO V4C: Usar geração simples de datas ao invés de query pesada
        dates_to_process = generate_dates_for_processing(last_embedding_date, test_date, last_processed_date)
        
        if not dates_to_process:
            log_message("Nenhuma data nova para processar", "success")
            return
        
        log_message(f"Processando {len(dates_to_process)} datas")
        
        # Estatísticas globais
        global_stats = {
            'datas_processadas': 0,
            'contratacoes_processadas': 0,
            'embeddings_gerados': 0,
            'embeddings_cache': 0,
            'erros': 0
        }
        
        # Processar cada data
        inicio = time.time()
        
        for date_str in dates_to_process:
            try:
                # Separador visual entre datas
                if global_stats['datas_processadas'] > 0:
                    log_message("-" * 80, "info")
                
                date_display = format_date_for_display(date_str)
                # Separador visual antes de cada data
                log_message("")
                log_message(f"📅 [bold blue]Data {date_display}[/bold blue]: processando...")
                
                # Processar embeddings para a data (sem count prévio que causa timeout)
                date_stats = process_embeddings_for_date(date_str)
                
                # Atualizar estatísticas globais
                global_stats['datas_processadas'] += 1
                global_stats['contratacoes_processadas'] += date_stats['contratacoes_processadas']
                global_stats['embeddings_gerados'] += date_stats['embeddings_gerados']
                global_stats['embeddings_cache'] += date_stats['embeddings_cache']
                global_stats['erros'] += date_stats['erros']
                
                # Atualizar última data processada (se não for teste)
                if not test_date:
                    update_last_embedding_date(date_str)
                    
            except Exception as e:
                date_display = format_date_for_display(date_str)
                log_message(f"❌ Erro ao processar data {date_display}: {e}", "error")
                # Incrementar erro sem fazer query pesada
                global_stats['erros'] += 1
        
        # Relatório final
        tempo_total = time.time() - inicio
        
        # Log de finalização detalhado no arquivo
        log_session_end(global_stats, tempo_total)
        
        log_message(f"Processamento ULTRA OTIMIZADO V4D concluído em {tempo_total:.1f}s", "success")
        log_message(f"Datas processadas: {global_stats['datas_processadas']}")
        log_message(f"Contratações processadas: {global_stats['contratacoes_processadas']}")
        log_message(f"Embeddings gerados: {global_stats['embeddings_gerados']}")
        log_message(f"Embeddings em cache: {global_stats['embeddings_cache']}")
        log_message(f"Erros: {global_stats['erros']}")
        
        if global_stats['erros'] == 0:
            console.print(Panel("[bold green]✅ PROCESSAMENTO ULTRA OTIMIZADO V4D CONCLUÍDO[/bold green]"))
        else:
            console.print(Panel("[bold yellow]⚠️ PROCESSAMENTO V4D CONCLUÍDO COM ALGUNS ERROS[/bold yellow]"))
    
    except KeyboardInterrupt:
        log_message("⚠️ Script interrompido pelo usuário (Ctrl+C)", "warning")
        console.print(Panel("[bold yellow]⚠️ PROCESSAMENTO INTERROMPIDO PELO USUÁRIO[/bold yellow]"))
    except Exception as e:
        log_message(f"❌ Erro crítico no processamento: {e}", "error")
        console.print(Panel("[bold red]❌ ERRO CRÍTICO NO PROCESSAMENTO[/bold red]"))
    finally:
        # SEMPRE fechar pool de conexões, mesmo em caso de erro/interrupção
        close_connection_pool()
        log_message("🔒 Pool de conexões fechado com segurança", "info")

if __name__ == "__main__":
    main()
