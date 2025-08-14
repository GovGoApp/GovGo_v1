# =======================================================================
# [5/7] CATEGORIZAÇÃO AUTOMÁTICA INCREMENTAL - VERSÃO V1
# =======================================================================
# Este script categoriza automaticamente as contratações usando busca
# semântica com pgvector na base Supabase v1.
# 
# MODO INCREMENTAL DIÁRIO (como 04D):
# - Processa dia por dia desde last_categorization_date
# - Modo --test processa próximo dia e atualiza a data
# - Lê embeddings da data específica
# - Busca TOP 5 categorias similares usando pgvector
# - Calcula confidence score baseado nas similaridades
# - Atualiza contratacao_emb e contratacao.cod_cat
# - Atualiza system_config com última data de categorização
# 
# Resultado: Contratações categorizadas automaticamente por data
# =======================================================================

import os
import sys
import time
import json
import math
import threading
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel

# Configure Rich console
console = Console()

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Categorização Automática v1 Incremental')
    parser.add_argument('--test', 
                       action='store_true',
                       help='Executar para próximo dia após last_categorization_date')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Ativar modo debug com logs detalhados')
    return parser.parse_args()

def format_date_for_display(date_str):
    """Converte YYYYMMDD para DD/MM/YYYY apenas para display"""
    if len(date_str) == 8:
        return f"{date_str[6:8]}/{date_str[4:6]}/{date_str[:4]}"
    return date_str

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
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

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),  # Corrigido
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'port': os.getenv('SUPABASE_PORT', 5432)
}

# Configurações de categorização
TOP_K = 5
MAX_WORKERS = 16
BATCH_SIZE = 100
# CONFIDENCE_THRESHOLD = 0.0  # Mínimo para aplicar cod_cat - DESABILITADO

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
# FUNÇÕES DE BANCO DE DADOS
#############################################

def create_connection():
    """Cria conexão com o banco PostgreSQL/Supabase"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        log_message(f"Erro ao conectar ao banco: {e}", "error")
        return None

def get_last_categorization_date():
    """Obtém a última data de categorização do system_config"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT value FROM system_config 
            WHERE key = 'last_categorization_date'
        """)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return result[0]
        else:
            return "20250101"
            
    except Exception as e:
        log_message(f"Erro ao obter última data de categorização: {e}", "error")
        connection.close()
        return "20250101"

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
            return datetime.now().strftime("%Y%m%d")  # Data atual se não encontrar
            
    except Exception as e:
        log_message(f"Erro ao obter última data de embedding: {e}", "error")
        connection.close()
        return datetime.now().strftime("%Y%m%d")

def generate_dates_for_categorization(last_categorization_date, test_mode=False, last_embedding_date=None):
    """
    Gera lista de datas para categorização - IGUAL ao 04D
    """
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

def get_embeddings_by_date(date_str):
    """Obtém embeddings de uma data específica que precisam ser categorizados"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Query otimizada: embeddings da data que não foram categorizados
        query = """
        SELECT 
            ce.id_contratacao_emb,
            ce.numero_controle_pncp,
            ce.embeddings
        FROM contratacao_emb ce
        INNER JOIN contratacao c ON c.numero_controle_pncp = ce.numero_controle_pncp
        WHERE c.data_publicacao_pncp IS NOT NULL
          AND DATE(c.data_publicacao_pncp) = %s::date
          AND ce.embeddings IS NOT NULL
          AND (ce.top_categories IS NULL OR ce.confidence IS NULL)
        --ORDER BY ce.id_contratacao_emb
        """
        
        cursor.execute(query, (date_formatted,))
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        log_message(f"Data {format_date_for_display(date_str)}: encontrados {len(results)} embeddings para categorizar", "info")
        return results
        
    except Exception as e:
        log_message(f"Erro ao buscar embeddings da data {date_str}: {e}", "error")
        connection.close()
        return []

def update_last_categorization_date(date_str):
    """Atualiza a última data de categorização no system_config"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO system_config (key, value, description) 
            VALUES ('last_categorization_date', %s, 'Última data processada para categorização automática')
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (date_str,))
        connection.commit()
        cursor.close()
        connection.close()
        log_message(f"Data de categorização atualizada para: {date_str}", "success")
        return True
        
    except Exception as e:
        log_message(f"Erro ao atualizar data de categorização: {e}", "error")
        connection.close()
        return False

def get_embeddings_to_categorize(last_date):
    """FUNÇÃO DEPRECATED - Usar get_embeddings_by_date() para processamento diário"""
    log_message("Função get_embeddings_to_categorize() é deprecated - usando processamento diário", "warning")
    return []

def check_categoria_embeddings():
    """Verifica se existem embeddings de categorias na base"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM categoria 
            WHERE cat_embeddings IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        
        log_message(f"Encontradas {count} categorias com embeddings", "info")
        return count > 0
        
    except Exception as e:
        log_message(f"Erro ao verificar embeddings de categorias: {e}", "error")
        connection.close()
        return False

#############################################
# FUNÇÕES DE CATEGORIZAÇÃO
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

def categorize_embedding_batch(worker_id, embedding_batch, progress, task_id):
    """Categoriza um lote de embeddings usando busca pgvector"""
    local_stats = {
        'embeddings_processados': 0,
        'categorizacoes_aplicadas': 0,
        'baixa_confianca': 0,
        'erros': 0
    }
    
    connection = create_connection()
    if not connection:
        local_stats['erros'] = len(embedding_batch)
        return local_stats
    
    try:
        cursor = connection.cursor()
        
        for embedding_data in embedding_batch:
            try:
                id_emb = embedding_data['id_contratacao_emb']
                numero_controle = embedding_data['numero_controle_pncp']
                embedding_vector = embedding_data['embeddings']
                
                # Buscar TOP K categorias usando pgvector
                search_query = """
                SELECT 
                    cod_cat,
                    nom_cat,
                    1 - (cat_embeddings <=> %s::vector) AS similarity
                FROM categoria
                WHERE cat_embeddings IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
                """
                
                cursor.execute(search_query, (embedding_vector, TOP_K))
                category_results = cursor.fetchall()
                
                if category_results:
                    # Extrair códigos e similaridades
                    top_categories = [row[0] for row in category_results]
                    top_similarities = [round(float(row[2]), 4) for row in category_results]
                    
                    # Calcular confiança
                    confidence = calculate_confidence(top_similarities)
                    
                    # Atualizar contratacao_emb
                    update_embedding_query = """
                        UPDATE contratacao_emb 
                        SET 
                            top_categories = %s,
                            top_similarities = %s,
                            confidence = %s
                        WHERE id_contratacao_emb = %s
                    """
                    
                    cursor.execute(update_embedding_query, (
                        top_categories,
                        top_similarities,
                        confidence,
                        id_emb
                    ))
                    
                    # TODO: Desabilitado temporariamente - atualizar cod_cat na contratacao
                    # Se confiança for alta, atualizar cod_cat na contratacao
                    # if confidence >= CONFIDENCE_THRESHOLD:
                    #     best_category = top_categories[0]
                    #     
                    #     update_contratacao_query = """
                    #         UPDATE contratacao 
                    #         SET cod_cat = %s, score = %s
                    #         WHERE numero_controle_pncp = %s
                    #     """
                    #     
                    #     cursor.execute(update_contratacao_query, (
                    #         best_category,
                    #         top_similarities[0],
                    #         numero_controle
                    #     ))
                    #     
                    #     local_stats['categorizacoes_aplicadas'] += 1
                    # else:
                    #     local_stats['baixa_confianca'] += 1
                    
                    # Por enquanto, contabilizar apenas como processado
                    local_stats['categorizacoes_aplicadas'] += 1
                
                else:
                    # Não encontrou categorias
                    local_stats['erros'] += 1
                    log_message(f"Worker {worker_id}: Nenhuma categoria encontrada para {numero_controle}", "warning")
                
                local_stats['embeddings_processados'] += 1
                
            except Exception as e:
                log_message(f"Worker {worker_id}: Erro ao categorizar embedding {id_emb}: {e}", "error")
                local_stats['erros'] += 1
        
        # Commit das alterações
        connection.commit()
        
        # Atualizar progresso
        progress.update(task_id, advance=len(embedding_batch))
        
    except Exception as e:
        log_message(f"Worker {worker_id}: Erro geral na categorização: {e}", "error")
        connection.rollback()
        local_stats['erros'] += len(embedding_batch)
    
    finally:
        cursor.close()
        connection.close()
    
    return local_stats

def update_global_stats(**kwargs):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        for key, value in kwargs.items():
            if key in global_stats:
                global_stats[key] += value

def partition_embeddings(embeddings, num_workers):
    """Divide os embeddings em partições para processamento paralelo"""
    if not embeddings:
        return []
    
    partition_size = len(embeddings) // num_workers
    remainder = len(embeddings) % num_workers
    
    partitions = []
    start = 0
    
    for i in range(num_workers):
        end = start + partition_size + (1 if i < remainder else 0)
        if start < len(embeddings):
            partitions.append(embeddings[start:end])
        start = end
    
    return [p for p in partitions if p]

#############################################
# FUNÇÃO PRINCIPAL
#############################################

def main():
    """Função principal da categorização automática INCREMENTAL - IGUAL AO 04D"""
    # Parse dos argumentos
    args = parse_arguments()
    test_mode = args.test
    debug_mode = args.debug
    
    console.print(Panel("[bold blue][5/7] CATEGORIZAÇÃO AUTOMÁTICA INCREMENTAL V1[/bold blue]"))
    
    if test_mode:
        log_message("Modo TESTE ativado: processando próximo dia", "warning")
    
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
            
        log_message(f"Processando categorização do intervalo: {last_categorization_date} (exclusivo) até {last_embedding_date} (inclusivo)")
    else:
        last_embedding_date = None
    
    # Gerar lista de datas para processar
    dates_to_process = generate_dates_for_categorization(last_categorization_date, test_mode, last_embedding_date)
    
    if not dates_to_process:
        log_message("Nenhuma data nova para processar", "success")
        return
    
    log_message(f"Processando {len(dates_to_process)} datas")
    
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
            log_message(f"📅 [bold blue]Data {date_display}[/bold blue]: categorizando...")
            
            # Reset estatísticas para esta data
            global global_stats
            global_stats = {
                'embeddings_processados': 0,
                'categorizacoes_aplicadas': 0,
                'baixa_confianca': 0,
                'erros': 0
            }
            
            # Buscar embeddings da data específica
            embeddings = get_embeddings_by_date(date_str)
            
            if not embeddings:
                log_message(f"Nenhum embedding para categorizar na data {date_display}", "warning")
                # Atualizar data mesmo sem embeddings
                update_last_categorization_date(date_str)
                global_stats_total['datas_processadas'] += 1
                continue
            
            log_message(f"Data {date_display}: categorizando {len(embeddings)} embeddings")
            
            # Dividir em partições para processamento paralelo
            partitions = partition_embeddings(embeddings, MAX_WORKERS)
            
            if not partitions:
                log_message(f"Nenhuma partição criada para data {date_str}", "warning")
                continue
            
            # Processar com progresso visual
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                tasks = []
                for i, partition in enumerate(partitions):
                    task = progress.add_task(
                        f"[bold blue]📊 Data {date_display} - Worker {i+1}/{len(partitions)}",
                        total=len(partition)
                    )
                    tasks.append(task)
                
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = []
                    
                    for i, partition in enumerate(partitions):
                        future = executor.submit(
                            categorize_embedding_batch,
                            i + 1,
                            partition,
                            progress,
                            tasks[i]
                        )
                        futures.append(future)
                    
                    # Aguardar conclusão e coletar estatísticas
                    for future in futures:
                        try:
                            local_stats = future.result()
                            update_global_stats(**local_stats)
                        except Exception as e:
                            log_message(f"Erro em worker para data {date_str}: {e}", "error")
            
            # Atualizar estatísticas totais
            global_stats_total['datas_processadas'] += 1
            global_stats_total['embeddings_processados'] += global_stats['embeddings_processados']
            global_stats_total['categorizacoes_aplicadas'] += global_stats['categorizacoes_aplicadas']
            global_stats_total['baixa_confianca'] += global_stats['baixa_confianca']
            global_stats_total['erros'] += global_stats['erros']
            
            # Atualizar data de categorização
            update_last_categorization_date(date_str)
            
            # Log do resultado da data
            log_message(f"✅ Data {date_display} concluída: {global_stats['categorizacoes_aplicadas']} categorizações, {global_stats['erros']} erros", 
                        "success" if global_stats['erros'] == 0 else "warning")
            
        except Exception as e:
            date_display = format_date_for_display(date_str)
            log_message(f"❌ Erro ao processar data {date_display}: {e}", "error")
            global_stats_total['erros'] += 1
    
    # Relatório final
    tempo_total = time.time() - inicio
    
    log_message(f"Categorização INCREMENTAL concluída em {tempo_total:.1f}s", "success")
    log_message(f"Datas processadas: {global_stats_total['datas_processadas']}")
    log_message(f"Embeddings processados: {global_stats_total['embeddings_processados']}")
    log_message(f"Categorizações aplicadas: {global_stats_total['categorizacoes_aplicadas']}")
    log_message(f"Baixa confiança: {global_stats_total['baixa_confianca']}")
    log_message(f"Erros: {global_stats_total['erros']}")
    
    # Calcular taxa de sucesso
    if global_stats_total['embeddings_processados'] > 0:
        taxa_sucesso = (global_stats_total['categorizacoes_aplicadas'] / global_stats_total['embeddings_processados']) * 100
        log_message(f"Taxa de categorização: {taxa_sucesso:.1f}%")
    
    if global_stats_total['erros'] == 0:
        console.print(Panel("[bold green]✅ CATEGORIZAÇÃO INCREMENTAL CONCLUÍDA[/bold green]"))
    else:
        console.print(Panel("[bold yellow]⚠️ CATEGORIZAÇÃO INCREMENTAL CONCLUÍDA COM ALGUNS ERROS[/bold yellow]"))

if __name__ == "__main__":
    main()
