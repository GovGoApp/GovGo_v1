# =======================================================================
# [05H_BATCH_PARALLEL] CATEGORIZAÇÃO EM LOTE PARALELA POR DATA
# =======================================================================
# Processa contratos entre last_categorization_date e last_embedding_date
# Paraleliza por dia usando MAX_WORKERS e chama 05G para cada lista
# =======================================================================

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn

# Importar função do 05G
import importlib.util
spec = importlib.util.spec_from_file_location("categorizer_05G", "05G_fast_benchmark.py")
categorizer_05G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(categorizer_05G)

# Configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'port': os.getenv('SUPABASE_PORT', 5432)
}

MAX_WORKERS = 32  # Máximo de workers
BATCH_SIZE = 100
MIN_CONTRACTS_FOR_FULL_WORKERS = 1000  # Usar todos os workers só se tiver mais de 1000 contratos

# Stats globais com lock
lock = threading.Lock()
console = Console()
stats = {
    'processed': 0,
    'success': 0,
    'skipped': 0,
    'errors': 0,
    'start_time': None
}

def create_connection():
    """Cria conexão com o banco"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def get_system_dates():
    """Busca last_categorization_date (LCD) e last_embedding_date (LED)"""
    connection = create_connection()
    if not connection:
        return None, None
    
    try:
        cursor = connection.cursor()
        
        # Buscar LCD
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_categorization_date'")
        lcd_result = cursor.fetchone()
        lcd = lcd_result[0] if lcd_result else "20250101"
        
        # Buscar LED
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_embedding_date'")
        led_result = cursor.fetchone()
        led = led_result[0] if led_result else "20250101"
        
        cursor.close()
        connection.close()
        return lcd, led
        
    except Exception as e:
        print(f"❌ Erro ao buscar datas do sistema: {e}")
        if connection:
            connection.close()
        return None, None

def get_contracts_by_date(target_date):
    """Busca apenas contratos NÃO CATEGORIZADOS com embeddings de uma data específica"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        
        # Query otimizada: apenas contratos SEM categorização da data específica
        cursor.execute("""
            SELECT ce.numero_controle_pncp 
            FROM contratacao_emb ce
            INNER JOIN contratacao c ON ce.numero_controle_pncp = c.numero_controle_pncp
            WHERE c.data_publicacao_pncp IS NOT NULL
            AND DATE(c.data_publicacao_pncp) = %s::date
            AND ce.embeddings IS NOT NULL
            AND ce.top_categories IS NULL
            ORDER BY ce.numero_controle_pncp
        """, (target_date,))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return [row[0] for row in results]
        
    except Exception as e:
        print(f"❌ Erro ao buscar contratos da data {target_date}: {e}")
        if connection:
            connection.close()
        return []

def calculate_optimal_workers(total_contracts):
    """Calcula número otimal de workers baseado na quantidade de contratos"""
    if total_contracts == 0:
        return 1
    elif total_contracts < 100:
        return min(4, total_contracts)
    elif total_contracts < 500:
        return min(8, total_contracts // 10)
    elif total_contracts < MIN_CONTRACTS_FOR_FULL_WORKERS:
        return min(16, total_contracts // 50)
    else:
        return MAX_WORKERS

def process_contract_batch(contract_ids, worker_id, date_str, progress, task_id, date_stats_shared):
    """Worker que processa um lote de contratos com progresso em tempo real"""
    batch_stats = {'success': 0, 'skipped': 0, 'errors': 0}
    
    for contract_id in contract_ids:
        result = categorizer_05G.categorize_single_contract_fast(contract_id)
        
        # Atualizar estatísticas locais
        if result['success']:
            if result.get('skipped', False):
                batch_stats['skipped'] += 1
                with lock:
                    date_stats_shared['skipped'] += 1
                    stats['skipped'] += 1
            else:
                batch_stats['success'] += 1
                with lock:
                    date_stats_shared['success'] += 1
                    stats['success'] += 1
        else:
            batch_stats['errors'] += 1
            with lock:
                date_stats_shared['errors'] += 1
                stats['errors'] += 1
        
        # ✅ ATUALIZAR PROGRESSO POR CONTRATO (como tqdm fazia)
        with lock:
            stats['processed'] += 1
            # Atualizar Rich progress COM AS ESTATÍSTICAS ATUAIS
            progress.update(task_id, advance=1,
                           description=f"🚀 {date_str} | ✅ {date_stats_shared['success']} | ⏭️ {date_stats_shared['skipped']} | ❌ {date_stats_shared['errors']}")
    
    return batch_stats

def process_date(target_date):
    """Processa todos os contratos NÃO CATEGORIZADOS de uma data específica"""
    print(f"\n📅 Processando data: {target_date}")
    
    # Buscar apenas contratos NÃO categorizados da data
    contract_ids = get_contracts_by_date(target_date)
    total_contracts = len(contract_ids)
    
    if total_contracts == 0:
        print(f"    ✅ Todos os contratos já categorizados para {target_date}")
        return {'success': 0, 'skipped': 0, 'errors': 0}
    
    # Calcular workers otimizados
    optimal_workers = calculate_optimal_workers(total_contracts)
    
    print(f"    📋 {total_contracts:,} contratos precisam categorização")
    print(f"    ⚡ Usando {optimal_workers} workers (otimizado para {total_contracts} contratos)")
    
    # Dividir contratos em lotes para os workers
    batches = []
    for i in range(0, total_contracts, BATCH_SIZE):
        batch = contract_ids[i:i + BATCH_SIZE]
        batches.append(batch)
    
    print(f"    📦 Dividindo em {len(batches)} lotes de até {BATCH_SIZE} contratos")
    
    # Rich Progress bar para a data
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("/"),
        TimeRemainingColumn(),
        console=console,
        transient=False
    ) as progress:
        
        task_id = progress.add_task(f"🚀 {target_date}", total=total_contracts)
        
        # ✅ ESTATÍSTICAS COMPARTILHADAS ENTRE WORKERS (thread-safe)
        date_stats = {'success': 0, 'skipped': 0, 'errors': 0}
        
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Submeter jobs com PARÂMETROS CORRETOS
            futures = []
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(process_contract_batch, batch, batch_idx, target_date, progress, task_id, date_stats)
                futures.append(future)
            
            # ✅ AGUARDAR CONCLUSÃO (progresso já é atualizado em tempo real pelos workers)
            for future in as_completed(futures):
                try:
                    batch_result = future.result()
                    # Não precisa atualizar aqui - já foi atualizado em tempo real!
                except Exception as e:
                    console.print(f"    ❌ Erro em batch: {e}")
                    with lock:
                        date_stats['errors'] += 1
                        stats['errors'] += 1
    
    console.print(f"    ✅ Concluído: {date_stats['success']} categorizados | {date_stats['skipped']} pulados | {date_stats['errors']} erros")
    return date_stats

def update_last_categorization_date(new_date):
    """Atualiza last_categorization_date no sistema"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO system_config (key, value, updated_at) 
            VALUES ('last_categorization_date', %s, NOW())
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value, 
                updated_at = EXCLUDED.updated_at
        """, (new_date,))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar last_categorization_date: {e}")
        if connection:
            connection.rollback()
            connection.close()
        return False

def generate_date_range(start_date_str, end_date_str):
    """Gera lista de datas entre start e end"""
    try:
        start_date = datetime.strptime(start_date_str, '%Y%m%d')
        end_date = datetime.strptime(end_date_str, '%Y%m%d')
        
        dates = []
        current_date = start_date
        
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        return dates
        
    except Exception as e:
        print(f"❌ Erro ao gerar range de datas: {e}")
        return []

if __name__ == "__main__":
    """EXECUÇÃO PRINCIPAL DO 05H"""
    
    console.print("=" * 80)
    console.print("🚀 05H_BATCH_PARALLEL - CATEGORIZAÇÃO EM LOTE POR DATA")
    console.print("=" * 80)
    
    # FASE 1: Obter datas do sistema
    console.print("\n📊 FASE 1: Verificando datas do sistema...")
    lcd, led = get_system_dates()
    
    if not lcd or not led:
        console.print("❌ Erro ao obter datas do sistema")
        sys.exit(1)
    
    console.print(f"📅 Last Categorization Date (LCD): {lcd}")
    console.print(f"📅 Last Embedded Date (LED): {led}")
    
    # Verificar se há trabalho a fazer
    lcd_date = datetime.strptime(lcd, '%Y%m%d')
    led_date = datetime.strptime(led, '%Y%m%d')
    
    if lcd_date >= led_date:
        print("\n✅ Todas as datas já foram categorizadas!")
        print(f"   LCD ({lcd}) >= LED ({led})")
        sys.exit(0)
    
    # Calcular próxima data para processar
    next_date_to_process = lcd_date + timedelta(days=1)
    next_date_str = next_date_to_process.strftime('%Y%m%d')
    
    print(f"🎯 Próxima data a processar: {next_date_str}")
    
    # FASE 2: Gerar lista de datas para processar
    print(f"\n📋 FASE 2: Gerando lista de datas entre {next_date_str} e {led}...")
    
    dates_to_process = generate_date_range(next_date_str, led)
    total_dates = len(dates_to_process)
    
    if total_dates == 0:
        print("❌ Nenhuma data para processar")
        sys.exit(0)
    
    print(f"📈 Total de datas para processar: {total_dates}")
    for i, date in enumerate(dates_to_process[:5], 1):
        print(f"   {i}. {date}")
    if total_dates > 5:
        print(f"   ... e mais {total_dates - 5}")
    
    # FASE 3: Processar cada data
    print(f"\n⚡ FASE 3: Processando {total_dates} datas com workers adaptativos (máx {MAX_WORKERS})...")
    stats['start_time'] = time.time()
    overall_start = time.time()
    
    total_stats = {'success': 0, 'skipped': 0, 'errors': 0}
    last_processed_date = lcd
    
    try:
        for date_idx, target_date in enumerate(dates_to_process, 1):
            print(f"\n🔄 [{date_idx}/{total_dates}] {target_date}")
            
            date_result = process_date(target_date)
            
            # Acumular estatísticas
            total_stats['success'] += date_result['success']
            total_stats['skipped'] += date_result['skipped'] 
            total_stats['errors'] += date_result['errors']
            
            # Atualizar LCD após cada data processada com sucesso
            target_date_formatted = datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y%m%d')
            if update_last_categorization_date(target_date_formatted):
                last_processed_date = target_date_formatted
                print(f"    ✅ LCD atualizada para: {target_date_formatted}")
            else:
                print(f"    ⚠️  Falha ao atualizar LCD para: {target_date_formatted}")
    
    except KeyboardInterrupt:
        print(f"\n⚠️  Processo interrompido pelo usuário")
        print(f"📅 Última data processada: {last_processed_date}")
    
    except Exception as e:
        print(f"\n❌ Erro durante processamento: {e}")
        print(f"📅 Última data processada: {last_processed_date}")
    
    # FASE 4: Resultados finais
    overall_end = time.time()
    total_time = overall_end - overall_start
    
    print(f"\n" + "=" * 80)
    print("📊 RESULTADOS FINAIS")
    print("=" * 80)
    print(f"⏱️  Tempo total: {total_time/3600:.1f}h ({total_time:.0f}s)")
    print(f"📅 Datas processadas: {date_idx}/{total_dates}")
    print(f"📋 Total de contratos:")
    print(f"   ✅ Categorizados: {total_stats['success']:,}")
    print(f"   ⏭️  Pulados: {total_stats['skipped']:,}")
    print(f"   ❌ Erros: {total_stats['errors']:,}")
    print(f"   📊 Total: {stats['processed']:,}")
    
    if stats['processed'] > 0:
        avg_rate = stats['processed'] / total_time
        print(f"🏃 Taxa média: {avg_rate:.1f} contratos/segundo")
    
    print(f"📅 LCD final: {last_processed_date}")
    print("=" * 80)
