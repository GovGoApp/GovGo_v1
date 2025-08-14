# =======================================================================
# [4/7] GERAÇÃO DE EMBEDDINGS - VERSÃO V1
# =======================================================================
# Este script gera embeddings das contratações usando OpenAI API
# e os armazena na base Supabase v1.
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
import psycopg2
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

# Configure Rich console
console = Console()

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Geração de Embeddings v1')
    parser.add_argument('--test', 
                       help='Executar para data específica (formato YYYYMMDD)',
                       type=str)
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Ativar modo debug com logs detalhados')
    return parser.parse_args()

def setup_logging(debug_mode=False):
    """Configura sistema de logging igual ao script 03"""
    global logger
    
    # Gerar timestamp para o nome do arquivo de log
    start_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = os.path.join(script_dir, f"04_embeddings_{start_timestamp}.log")
    
    # Configurar logger principal
    logger = logging.getLogger('embedding_generation')
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
    
    # REDUZIR DEBUG EXCESSIVO DA OPENAI - configurar loggers específicos para nível ERROR
    openai_loggers = [
        'openai',
        'httpx',
        'httpcore',
        'httpcore.http11',
        'httpcore.connection',
        'urllib3.connectionpool',
        'requests.packages.urllib3.connectionpool'
    ]
    
    for logger_name in openai_loggers:
        openai_logger = logging.getLogger(logger_name)
        openai_logger.setLevel(logging.ERROR)  # Só mostra erros, não debug
        openai_logger.propagate = False  # Não propaga para loggers pais
    
    logger.info("=" * 80)
    logger.info("NOVA SESSÃO DE GERAÇÃO DE EMBEDDINGS INICIADA")
    logger.info("=" * 80)
    logger.info(f"Horário de início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Modo debug: {'Ativado' if debug_mode else 'Desativado'}")
    logger.info(f"Arquivo de log: {LOG_FILE}")
    logger.info("-" * 80)
    
    return logger, os.path.basename(LOG_FILE)

def log_session_end(stats, tempo_total):
    """Finaliza a sessão de log com resumo"""
    if logger:
        logger.info("-" * 80)
        logger.info("SESSÃO DE GERAÇÃO DE EMBEDDINGS FINALIZADA")
        logger.info(f"Horário de término: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Tempo total: {tempo_total:.1f}s")
        logger.info(f"Datas processadas: {stats['datas_processadas']}")
        logger.info(f"Contratações processadas: {stats['contratacoes_processadas']:,}")
        logger.info(f"Embeddings gerados: {stats['embeddings_gerados']:,}")
        logger.info(f"Embeddings em cache: {stats['embeddings_cache']:,}")
        logger.info(f"Erros encontrados: {stats['erros']:,}")
        logger.info("=" * 80)

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline - sempre salva em arquivo"""
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
        return  # Não mostra mensagens debug se modo debug estiver desativado
    
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

# Configurações do banco PostgreSQL V1 (Supabase) - mesmo padrão do script 03
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

# Configurações OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configurações de embedding
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
MAX_WORKERS = 16  # Aumentando workers para compensar remoção de sublotes
BATCH_SIZE = 50

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
# FUNÇÕES DE BANCO DE DADOS
#############################################

def create_connection():
    """Cria conexão com o banco PostgreSQL/Supabase - mesmo padrão do script 03"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        connection.set_session(autocommit=False)
        return connection
    except Exception as e:
        log_message(f"Erro ao conectar ao banco: {e}", "error")
        return None

def create_embedding_constraints_if_not_exists(conn):
    """Cria constraints se não existirem na tabela contratacao_emb"""
    cursor = conn.cursor()
    
    try:
        # Constraint para contratacao_emb - evitar duplicatas por numero_controle_pncp
        cursor.execute("""
            DO $$ BEGIN
                ALTER TABLE contratacao_emb ADD CONSTRAINT contratacao_emb_numero_controle_unique 
                UNIQUE (numero_controle_pncp);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        """)
        
        conn.commit()
        # Remover log debug para evitar spam nos workers
        
    except Exception as e:
        conn.rollback()
        log_message(f"Aviso ao criar constraint de embeddings: {str(e)}", "warning")

def get_last_embedding_date():
    """Obtém a última data de processamento de embeddings do system_config"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT value FROM system_config 
            WHERE key = 'last_embedding_date'
        """)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return result[0]
        else:
            # Se não existir, criar com data bem antiga
            return "20200101"
            
    except Exception as e:
        log_message(f"Erro ao obter última data de embedding: {e}", "error")
        connection.close()
        return "20200101"

def get_last_processed_date():
    """Obtém a última data de processamento geral do system_config"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT value FROM system_config 
            WHERE key = 'last_processed_date'
        """)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return result[0]
        else:
            # Se não existir, usar data atual como fallback
            return datetime.now().strftime("%Y%m%d")
            
    except Exception as e:
        log_message(f"Erro ao obter última data processada: {e}", "error")
        connection.close()
        return datetime.now().strftime("%Y%m%d")

def update_last_embedding_date(date_str):
    """Atualiza a última data de processamento de embeddings no system_config"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO system_config (key, value, description) 
            VALUES ('last_embedding_date', %s, 'Última data processada para geração de embeddings')
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (date_str,))
        connection.commit()
        cursor.close()
        connection.close()
        log_message(f"Data de embedding atualizada para: {date_str}", "success")
        return True
        
    except Exception as e:
        log_message(f"Erro ao atualizar data de embedding: {e}", "error")
        connection.close()
        return False

def get_dates_needing_embeddings(last_embedding_date, test_date=None, last_processed_date=None):
    """Obtém datas que precisam de processamento de embeddings"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        
        if test_date:
            # Modo teste: verificar se a data tem contratações
            # Usar data_publicacao_pncp ao invés de created_at
            query = """
                SELECT DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') as data_processamento
                FROM contratacao c
                WHERE c.data_publicacao_pncp IS NOT NULL 
                  AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') = %s::date
                ORDER BY data_processamento
            """
            # Converter YYYYMMDD para formato de data
            test_date_formatted = f"{test_date[:4]}-{test_date[4:6]}-{test_date[6:8]}"
            cursor.execute(query, (test_date_formatted,))
            
        else:
            # Modo normal: processar datas no intervalo [last_embedding_date + 1 dia, last_processed_date]
            if last_processed_date:
                query = """
                    SELECT DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') as data_processamento
                    FROM contratacao c
                    WHERE c.data_publicacao_pncp IS NOT NULL 
                      AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
                      AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
                      AND EXISTS (
                          SELECT 1 FROM contratacao c2
                          WHERE TO_DATE(c2.data_publicacao_pncp, 'YYYY-MM-DD') = TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD')
                            AND c2.numero_controle_pncp NOT IN (
                                SELECT DISTINCT numero_controle_pncp 
                                FROM contratacao_emb 
                                WHERE numero_controle_pncp IS NOT NULL
                            )
                      )
                    ORDER BY data_processamento
                """
                # Converter YYYYMMDD para formato de data  
                last_embedding_date_formatted = f"{last_embedding_date[:4]}-{last_embedding_date[4:6]}-{last_embedding_date[6:8]}"
                last_processed_date_formatted = f"{last_processed_date[:4]}-{last_processed_date[4:6]}-{last_processed_date[6:8]}"
                cursor.execute(query, (last_embedding_date_formatted, last_processed_date_formatted))
            else:
                # Fallback: modo antigo (processar datas após last_embedding_date sem limite superior)
                query = """
                    SELECT DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') as data_processamento
                    FROM contratacao c
                    WHERE c.data_publicacao_pncp IS NOT NULL 
                      AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
                      AND EXISTS (
                          SELECT 1 FROM contratacao c2
                          WHERE TO_DATE(c2.data_publicacao_pncp, 'YYYY-MM-DD') = TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD')
                            AND c2.numero_controle_pncp NOT IN (
                                SELECT DISTINCT numero_controle_pncp 
                                FROM contratacao_emb 
                                WHERE numero_controle_pncp IS NOT NULL
                            )
                      )
                    ORDER BY data_processamento
                """
                # Converter YYYYMMDD para formato de data  
                last_embedding_date_formatted = f"{last_embedding_date[:4]}-{last_embedding_date[4:6]}-{last_embedding_date[6:8]}"
                cursor.execute(query, (last_embedding_date_formatted,))
        
        dates = [row[0].strftime('%Y%m%d') for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        return dates
        
    except Exception as e:
        log_message(f"Erro ao buscar datas para processamento: {e}", "error")
        connection.close()
        return []

def count_contratacoes_by_date(date_str):
    """Conta contratações que precisam de embedding para uma data específica"""
    connection = create_connection()
    if not connection:
        return 0
    
    try:
        cursor = connection.cursor()
        
        # Converter YYYYMMDD para formato de data
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        query = """
            SELECT COUNT(DISTINCT c.numero_controle_pncp)
            FROM contratacao c
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') = %s::date
              AND c.numero_controle_pncp NOT IN (
                  SELECT DISTINCT numero_controle_pncp 
                  FROM contratacao_emb 
                  WHERE numero_controle_pncp IS NOT NULL
              )
        """
        
        cursor.execute(query, (date_formatted,))
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        
        return count
        
    except Exception as e:
        log_message(f"Erro ao contar contratações da data {date_str}: {e}", "error")
        connection.close()
        return 0

def get_contratacoes_by_date(date_str):
    """
    Obtém contratações de uma data específica para processamento de embeddings
    Concatena: objeto_compra || ' :: ' || string_agg(descricao_item, ' :: ')
    """
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Converter YYYYMMDD para formato de data
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Query que replica a view vw_contratacoes para uma data específica usando data_publicacao_pncp
        query = """
        SELECT 
            c.numero_controle_pncp,
            c.objeto_compra || ' :: ' || COALESCE(string_agg(COALESCE(i.descricao_item, ''), ' :: '), '') AS descricao_completa
        FROM contratacao c
        LEFT JOIN item_contratacao i ON c.numero_controle_pncp = i.numero_controle_pncp
        WHERE c.data_publicacao_pncp IS NOT NULL 
          AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') = %s::date
          AND c.numero_controle_pncp NOT IN (
              SELECT DISTINCT numero_controle_pncp 
              FROM contratacao_emb 
              WHERE numero_controle_pncp IS NOT NULL
          )
        GROUP BY c.numero_controle_pncp, c.objeto_compra
        ORDER BY c.numero_controle_pncp
        """
        
        cursor.execute(query, (date_formatted,))
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        log_message(f"Erro ao buscar contratações da data {date_str}: {e}", "error")
        connection.close()
        return []

def process_embeddings_for_date(date_str):
    """Processa embeddings para todas as contratações de uma data específica"""
    log_message(f"Processando embeddings para data: {date_str}")
    
    # Obter contratações da data
    contratacoes = get_contratacoes_by_date(date_str)
    
    if not contratacoes:
        log_message(f"Nenhuma contratação para processar na data {date_str}", "warning")
        return {
            'data': date_str,
            'contratacoes_processadas': 0,
            'embeddings_gerados': 0,
            'embeddings_cache': 0,
            'erros': 0
        }
    
    log_message(f"Data {date_str}: processando {len(contratacoes)} contratações")
    
    # Verificar embeddings existentes
    existing_embeddings = check_existing_embeddings()
    
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
    
    # Processar com workers paralelos usando um único Progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Progress bar geral destacado (azul) - baseado no total de tarefas dos workers
        total_worker_tasks = len(partitions) * 100  # Cada worker tem 100% de progresso
        main_task = progress.add_task(
            f"[bold blue]📊 GERAL: Data {date_str} - Iniciando workers...", 
            total=total_worker_tasks
        )
        
        # Tasks individuais por worker (inicialmente invisíveis - apenas em modo debug)
        worker_tasks = {}
        if debug_mode:
            for i, partition in enumerate(partitions):
                worker_tasks[i + 1] = progress.add_task(
                    f"[cyan]🔧 Worker {i + 1}: Aguardando...",
                    total=100,  # 100% para cada worker
                    visible=False
                )
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Dicionário para rastrear progresso atual de cada worker
            worker_progress_tracking = {i + 1: 0 for i in range(len(partitions))}
            
            def update_general_progress():
                """Atualiza o progress geral baseado na soma dos progressos dos workers"""
                total_progress = sum(worker_progress_tracking.values())
                # Descrição simples quando não está em debug mode
                if debug_mode:
                    progress.update(main_task, 
                        completed=total_progress,
                        description=f"[bold blue]📊 GERAL: Data {date_str} - {total_progress:.0f}/{total_worker_tasks} tarefas concluídas"
                    )
                else:
                    # Progress simples - apenas nome da data e barra de progresso
                    progress.update(main_task, 
                        completed=total_progress,
                        description=f"[bold blue]📊 GERAL: Data {date_str}"
                    )
            
            # Função wrapper que atualiza progress dinamicamente
            def process_with_progress(worker_id, partition, existing_embeddings, date_str):
                task_id = worker_tasks.get(worker_id) if debug_mode else None
                
                # Callback para atualizar progresso geral quando worker progride
                def worker_progress_callback(completed_percent):
                    worker_progress_tracking[worker_id] = completed_percent
                    update_general_progress()
                
                try:
                    # Mostrar worker progress apenas em debug mode
                    if debug_mode and task_id:
                        progress.update(task_id, visible=True)
                    
                    # Processar com atualização de etapas
                    if debug_mode and task_id:
                        result = process_embedding_batch_for_date_with_progress(
                            worker_id, partition, existing_embeddings, date_str, 
                            progress, task_id, worker_progress_callback
                        )
                    else:
                        # Modo simplificado sem progress detalhado por worker
                        result = process_embedding_batch_for_date_simple(
                            worker_id, partition, existing_embeddings, date_str, worker_progress_callback
                        )
                    
                    return result
                    
                except Exception as e:
                    # Marcar como erro e completar
                    if debug_mode and task_id:
                        progress.update(task_id, 
                            description=f"[red]🔧 Worker {worker_id}: ERRO - {str(e)[:30]}...",
                            completed=100
                        )
                    worker_progress_callback(100)  # Worker completou (com erro)
                    raise e
                finally:
                    # Aguardar um pouco antes de ocultar (apenas em debug mode)
                    if debug_mode and task_id:
                        time.sleep(0.5)
                        progress.update(task_id, visible=False)
            
            futures = []
            for i, partition in enumerate(partitions):
                future = executor.submit(
                    process_with_progress,
                    i + 1,
                    partition,
                    existing_embeddings,
                    date_str
                )
                futures.append(future)
            
            # Aguardar conclusão e coletar estatísticas
            for future in futures:
                try:
                    local_stats = future.result()
                    date_stats['contratacoes_processadas'] += local_stats['contratacoes_processadas']
                    date_stats['embeddings_gerados'] += local_stats['embeddings_gerados']
                    date_stats['embeddings_cache'] += local_stats['embeddings_cache']
                    date_stats['erros'] += local_stats['erros']
                    
                except Exception as e:
                    log_message(f"Erro em worker para data {date_str}: {e}", "error")
                    # Erro já foi tratado no callback do worker
    
    # Log do resultado da data
    log_message(f"Data {date_str} concluída: {date_stats['embeddings_gerados']} embeddings gerados, {date_stats['erros']} erros", 
                "success" if date_stats['erros'] == 0 else "warning")
    
    return date_stats

#############################################
# FUNÇÕES DE EMBEDDING
#############################################

def check_existing_embeddings():
    """Verifica embeddings já existentes para evitar duplicatas"""
    connection = create_connection()
    if not connection:
        return set()
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT numero_controle_pncp FROM contratacao_emb WHERE numero_controle_pncp IS NOT NULL")
        existing = set(row[0] for row in cursor.fetchall())
        cursor.close()
        connection.close()
        
        log_message(f"Encontrados {len(existing)} embeddings existentes", "info")
        return existing
        
    except Exception as e:
        log_message(f"Erro ao verificar embeddings existentes: {e}", "error")
        connection.close()
        return set()

#############################################
# FUNÇÕES DE EMBEDDING
#############################################

def generate_embeddings_batch(texts, max_retries=3):
    """Gera embeddings para um lote de textos usando OpenAI API"""
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
    
    # Gerar embeddings com retry
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=validated_texts
            )
            
            embeddings = []
            dimensoes_corretas = 0
            dimensoes_incorretas = 0
            
            for item in response.data:
                emb = np.array(item.embedding, dtype=np.float32)
                
                # Verificar dimensão
                if emb.shape[0] == EMBEDDING_DIM:
                    dimensoes_corretas += 1
                else:
                    dimensoes_incorretas += 1
                    log_message(f"Embedding com dimensão incorreta: {emb.shape[0]} != {EMBEDDING_DIM}", "warning")
                    # Ajustar dimensão se necessário
                    if len(emb) > EMBEDDING_DIM:
                        emb = emb[:EMBEDDING_DIM]
                    else:
                        padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                        padded[:len(emb)] = emb
                        emb = padded
                
                embeddings.append(emb)
            
            # Log resumido sobre as dimensões (apenas se houver problemas)
            if dimensoes_incorretas > 0:
                log_message(f"Embeddings: {dimensoes_corretas} corretas ({EMBEDDING_DIM}D), {dimensoes_incorretas} ajustadas", "warning")
            
            return embeddings
            
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                log_message(f"Rate limit atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {wait_time}s", "warning")
                time.sleep(wait_time)
            else:
                log_message(f"Erro na API OpenAI: {e}", "error")
                raise
    
    return []

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

#############################################
# PROCESSAMENTO PARALELO
#############################################

def process_embedding_batch_for_date_simple(worker_id, batch_contratacoes, existing_embeddings, date_str, progress_callback=None):
    """Processa um lote de contratações para gerar embeddings (modo simplificado sem progress detalhado)"""
    local_stats = {
        'contratacoes_processadas': 0,
        'embeddings_gerados': 0,
        'embeddings_cache': 0,
        'erros': 0
    }
    
    try:
        # Atualizar callback - iniciando
        if progress_callback:
            progress_callback(0)
        
        # Filtrar contratações que ainda não têm embedding
        to_process = []
        cache_count = 0
        
        for contratacao in batch_contratacoes:
            numero_controle = contratacao['numero_controle_pncp']
            if numero_controle not in existing_embeddings:
                to_process.append(contratacao)
            else:
                cache_count += 1
        
        local_stats['embeddings_cache'] = cache_count
        
        if not to_process:
            if progress_callback:
                progress_callback(100)
            return local_stats
        
        # Atualizar callback - meio do processamento
        if progress_callback:
            progress_callback(50)
        
        # Processar todas as contratações do worker de uma vez
        texts = [item['descricao_completa'] for item in to_process]
        
        # Gerar embeddings
        embeddings = generate_embeddings_batch(texts)
        
        # Inserir no banco
        success_count = insert_embeddings_batch(to_process, embeddings, worker_id)
        
        local_stats['embeddings_gerados'] = success_count
        local_stats['contratacoes_processadas'] = len(to_process)
        
        # Atualizar callback - finalizado
        if progress_callback:
            progress_callback(100)
        
        return local_stats
        
    except Exception as e:
        log_message(f"Worker {worker_id}: Erro no processamento: {e}", "error")
        local_stats['erros'] = len(batch_contratacoes)
        if progress_callback:
            progress_callback(100)
        return local_stats

def process_embedding_batch_for_date_with_progress(worker_id, batch_contratacoes, existing_embeddings, date_str, progress, task_id, progress_callback=None):
    """Processa um lote de contratações para gerar embeddings com progress dinâmico"""
    local_stats = {
        'contratacoes_processadas': 0,
        'embeddings_gerados': 0,
        'embeddings_cache': 0,
        'erros': 0
    }
    
    def update_progress(completed, description):
        """Helper para atualizar progress do worker e callback geral"""
        progress.update(task_id, description=description, completed=completed)
        if progress_callback:
            progress_callback(completed)
    
    try:
        # ETAPA 1: Filtrar contratações (0-25%)
        update_progress(0, f"[cyan]🔧 Worker {worker_id}: Filtrando {len(batch_contratacoes)} contratações...")
        
        to_process = []
        cache_count = 0
        
        for i, contratacao in enumerate(batch_contratacoes):
            numero_controle = contratacao['numero_controle_pncp']
            if numero_controle not in existing_embeddings:
                to_process.append(contratacao)
            else:
                cache_count += 1
            
            # Atualizar progress da filtragem
            current_progress = int((i + 1) / len(batch_contratacoes) * 25)
            update_progress(current_progress, f"[cyan]🔧 Worker {worker_id}: Filtrando {len(batch_contratacoes)} contratações...")
        
        local_stats['embeddings_cache'] = cache_count
        
        if not to_process:
            update_progress(100, f"[green]🔧 Worker {worker_id}: Concluído - {cache_count} já existiam")
            return local_stats
        
        # ETAPA 2: Preparar textos (25-50%)
        update_progress(25, f"[cyan]🔧 Worker {worker_id}: Preparando {len(to_process)} textos...")
        
        texts = [item['descricao_completa'] for item in to_process]
        update_progress(50, f"[cyan]🔧 Worker {worker_id}: Textos preparados")
        
        # ETAPA 3: Gerar embeddings (50-75%)
        update_progress(50, f"[cyan]🔧 Worker {worker_id}: Gerando embeddings para {len(texts)} textos...")
        
        embeddings = generate_embeddings_batch(texts)
        update_progress(75, f"[cyan]🔧 Worker {worker_id}: Embeddings gerados")
        
        # ETAPA 4: Inserir no banco (75-100%)
        update_progress(75, f"[cyan]🔧 Worker {worker_id}: Inserindo {len(embeddings)} embeddings no banco...")
        
        success_count = insert_embeddings_batch(to_process, embeddings, worker_id)
        
        local_stats['embeddings_gerados'] = success_count
        local_stats['contratacoes_processadas'] = len(to_process)
        
        # FINALIZAÇÃO
        update_progress(100, f"[green]🔧 Worker {worker_id}: Concluído - {success_count} embeddings inseridos")
        
        return local_stats
        
    except Exception as e:
        log_message(f"Worker {worker_id}: Erro no processamento: {e}", "error")
        update_progress(100, f"[red]🔧 Worker {worker_id}: ERRO - {str(e)[:40]}...")
        local_stats['erros'] = len(batch_contratacoes)
        return local_stats

def process_embedding_batch_for_date(worker_id, batch_contratacoes, existing_embeddings, date_str):
    """Processa um lote de contratações para gerar embeddings (versão simplificada)"""
    local_stats = {
        'contratacoes_processadas': 0,
        'embeddings_gerados': 0,
        'embeddings_cache': 0,
        'erros': 0
    }
    
    try:
        # Filtrar contratações que ainda não têm embedding
        to_process = []
        cache_count = 0
        
        for contratacao in batch_contratacoes:
            numero_controle = contratacao['numero_controle_pncp']
            if numero_controle not in existing_embeddings:
                to_process.append(contratacao)
            else:
                cache_count += 1
        
        local_stats['embeddings_cache'] = cache_count
        
        if not to_process:
            return local_stats
        
        # Processar todas as contratações do worker de uma vez (sem sublotes)
        texts = [item['descricao_completa'] for item in to_process]
        
        # Gerar embeddings
        embeddings = generate_embeddings_batch(texts)
        
        # Inserir no banco
        success_count = insert_embeddings_batch(to_process, embeddings, worker_id)
        
        local_stats['embeddings_gerados'] = success_count
        local_stats['contratacoes_processadas'] = len(to_process)
        
        return local_stats
        
    except Exception as e:
        log_message(f"Worker {worker_id}: Erro no processamento: {e}", "error")
        local_stats['erros'] = len(batch_contratacoes)
        return local_stats

def partition_contratacoes(contratacoes, num_workers):
    """Divide as contratações em partições para processamento paralelo"""
    if not contratacoes:
        return []
    
    # Com mais workers, cada um processa menos dados de uma vez
    partition_size = max(1, len(contratacoes) // num_workers)
    
    partitions = []
    for i in range(0, len(contratacoes), partition_size):
        partition = contratacoes[i:i + partition_size]
        if partition:
            partitions.append(partition)
    
    return partitions

def insert_embeddings_batch(contratacoes, embeddings, worker_id):
    """Insere um lote de embeddings no banco de dados com verificação de duplicatas"""
    if len(contratacoes) != len(embeddings):
        log_message(f"Worker {worker_id}: Mismatch entre contratações e embeddings", "error")
        return 0
    
    connection = create_connection()
    if not connection:
        return 0
    
    try:
        # Garantir que constraint existe antes da inserção
        create_embedding_constraints_if_not_exists(connection)
        
        cursor = connection.cursor()
        
        # Preparar dados para inserção
        insert_data = []
        for contratacao, embedding in zip(contratacoes, embeddings):
            metadata = {
                "modelo": EMBEDDING_MODEL,
                "dimensoes": EMBEDDING_DIM,
                "timestamp": datetime.now().isoformat(),
                "worker_id": worker_id
            }
            
            insert_data.append((
                contratacao['numero_controle_pncp'],
                EMBEDDING_MODEL,
                json.dumps(metadata),
                embedding.tolist()  # Converter para lista para PostgreSQL
            ))
        
        # Inserção em lote com ON CONFLICT e contagem precisa de inserções reais
        insert_query = """
            WITH inserted AS (
                INSERT INTO contratacao_emb (
                    numero_controle_pncp, modelo_embedding, metadata, embeddings
                ) VALUES %s
                ON CONFLICT (numero_controle_pncp) DO NOTHING
                RETURNING numero_controle_pncp
            )
            SELECT COUNT(*) FROM inserted
        """
        
        # Executar inserção e obter contagem real de registros inseridos
        execute_values(
            cursor,
            insert_query,
            insert_data,
            template='(%s, %s, %s, %s::vector)',
            page_size=len(insert_data),
            fetch=True
        )
        
        # Obter o resultado da contagem
        result = cursor.fetchone()
        inserted_count = result[0] if result else 0
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return inserted_count
        
    except Exception as e:
        log_message(f"Worker {worker_id}: Erro na inserção: {e}", "error")
        connection.rollback()
        connection.close()
        return 0

#############################################
# FUNÇÃO PRINCIPAL
#############################################

def main():
    """Função principal do processamento de embeddings"""
    global debug_mode
    
    # Parse dos argumentos
    args = parse_arguments()
    debug_mode = args.debug
    test_date = args.test
    
    # Setup do logging
    logger, log_filename = setup_logging(debug_mode)
    
    console.print(Panel("[bold blue][4/7] GERAÇÃO DE EMBEDDINGS V1[/bold blue]"))
    
    # Log inicial informando o arquivo de log que está sendo usado
    log_message(f"Arquivo de log criado: {log_filename}", "info")
    
    # Verificar configurações essenciais
    if not os.getenv("OPENAI_API_KEY"):
        log_message("OPENAI_API_KEY não encontrada", "error")
        return
    
    # Verificar/criar constraints de unicidade para contratacao_emb
    test_conn = create_connection()
    if test_conn:
        create_embedding_constraints_if_not_exists(test_conn)
        test_conn.close()
        log_message("Constraint de unicidade verificada para contratacao_emb", "success")
    else:
        log_message("Falha ao verificar constraints do banco", "error")
        return
    
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
    
    # Buscar datas para processar
    dates_to_process = get_dates_needing_embeddings(last_embedding_date, test_date, last_processed_date)
    
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
            # Contar contratações apenas da data atual (quando necessário)
            count = count_contratacoes_by_date(date_str)
            log_message(f"Data {date_str}: {count} contratações para processar")
            
            # Processar embeddings para a data
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
            log_message(f"Erro ao processar data {date_str}: {e}", "error")
            global_stats['erros'] += count_contratacoes_by_date(date_str)
    
    # Relatório final
    tempo_total = time.time() - inicio
    
    # Log de finalização detalhado no arquivo
    log_session_end(global_stats, tempo_total)
    
    log_message(f"Processamento concluído em {tempo_total:.1f}s", "success")
    log_message(f"Datas processadas: {global_stats['datas_processadas']}")
    log_message(f"Contratações processadas: {global_stats['contratacoes_processadas']}")
    log_message(f"Embeddings gerados: {global_stats['embeddings_gerados']}")
    log_message(f"Embeddings em cache: {global_stats['embeddings_cache']}")
    log_message(f"Erros: {global_stats['erros']}")
    
    if global_stats['erros'] == 0:
        console.print(Panel("[bold green]✅ PROCESSAMENTO DE EMBEDDINGS CONCLUÍDO[/bold green]"))
    else:
        console.print(Panel("[bold yellow]⚠️ PROCESSAMENTO CONCLUÍDO COM ALGUNS ERROS[/bold yellow]"))

if __name__ == "__main__":
    main()
