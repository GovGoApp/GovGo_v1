# =======================================================================
# [05G_CLEAN] CATEGORIZAÇÃO INDIVIDUAL - VERSÃO LIMPA E PROTEGIDA
# =======================================================================

import os
import sys
import time
import math
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'port': os.getenv('SUPABASE_PORT', 5432)
}

TOP_K = 5

def create_connection():
    """Cria conexão com o banco"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except:
        return None

def calculate_confidence(similarities):
    """Calcula confiança"""
    if len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    
    top_score = similarities[0]
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    return round((1 - math.exp(-10 * weighted_gap)), 4)

def categorize_single_contract_fast(numero_controle_pncp):
    """Categoriza um contrato individual com proteção anti-duplicação"""
    connection = create_connection()
    if not connection:
        return {'success': False, 'error': 'Connection failed'}
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Buscar embedding
        cursor.execute("""
            SELECT id_contratacao_emb, embeddings
            FROM contratacao_emb 
            WHERE numero_controle_pncp = %s AND embeddings IS NOT NULL
        """, (numero_controle_pncp,))
        
        embedding_result = cursor.fetchone()
        if not embedding_result:
            cursor.close()
            connection.close()
            return {'success': False, 'error': 'No embedding'}
        
        # Buscar categorias similares
        cursor.execute("""
            SELECT cod_cat, 1 - (cat_embeddings <=> %s::vector) AS similarity
            FROM categoria
            WHERE cat_embeddings IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s
        """, (embedding_result['embeddings'], TOP_K))
        
        category_results = cursor.fetchall()
        if not category_results:
            cursor.close()
            connection.close()
            return {'success': False, 'error': 'No categories'}
        
        # Processar resultados
        top_categories = [row['cod_cat'] for row in category_results]
        top_similarities = [round(float(row['similarity']), 4) for row in category_results]
        confidence = calculate_confidence(top_similarities)
        
        # Update com proteção anti-duplicação
        cursor.execute("""
            UPDATE contratacao_emb 
            SET top_categories = %s, top_similarities = %s, confidence = %s
            WHERE id_contratacao_emb = %s AND top_categories IS NULL
        """, (top_categories, top_similarities, confidence, embedding_result['id_contratacao_emb']))
        
        # Verificar se realmente atualizou (proteção)
        updated_rows = cursor.rowcount
        connection.commit()
        cursor.close()
        connection.close()
        
        if updated_rows == 0:
            return {'success': True, 'skipped': True, 'error': 'Already categorized'}
        
        return {
            'success': True,
            'best_category': top_categories[0],
            'best_similarity': top_similarities[0],
            'confidence': confidence,
            'skipped': False
        }
        
    except Exception as e:
        connection.rollback()
        connection.close()
        return {'success': False, 'error': str(e)}

def get_contracts_count_by_date(date_str):
    """Conta quantos contratos existem em uma data específica"""
    connection = create_connection()
    if not connection:
        return 0
    
    try:
        cursor = connection.cursor()
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        next_date_obj = date_obj + timedelta(days=1)
        next_date_formatted = next_date_obj.strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL
            AND DATE(data_publicacao_pncp) = %s::date
        """, (next_date_formatted,))
        
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return count
        
    except:
        connection.close()
        return 0

def get_sample_contracts(date_str, sample_size=10):
    """Busca amostra de contratos para teste de performance"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        next_date_obj = date_obj + timedelta(days=1)
        next_date_formatted = next_date_obj.strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT numero_controle_pncp 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL
            AND DATE(data_publicacao_pncp) = %s::date
            LIMIT %s
        """, (next_date_formatted, sample_size))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return [row[0] for row in results]
        
    except:
        connection.close()
        return []

def get_last_categorization_date():
    """Busca última data de categorização"""
    connection = create_connection()
    if not connection:
        return "20250101"
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_categorization_date'")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result[0] if result else "20250101"
    except:
        connection.close()
        return "20250101"

if __name__ == "__main__":
    """BENCHMARK E CÁLCULO DE TEMPO TOTAL"""
    
    print("=" * 80)
    print("🚀 BENCHMARK 05G_FAST - CÁLCULO DE TEMPO TOTAL DO PROCESSO")
    print("=" * 80)
    
    # FASE 1: Obter dados para cálculo
    print("\n📊 FASE 1: Coletando dados...")
    last_date = get_last_categorization_date()
    total_contracts = get_contracts_count_by_date(last_date)
    sample_contracts = get_sample_contracts(last_date, 20)  # Amostra de 20
    
    print(f"📅 Última data de categorização: {last_date}")
    print(f"📈 Total de contratos no próximo dia: {total_contracts}")
    print(f"🧪 Amostra para teste: {len(sample_contracts)} contratos")
    
    if not sample_contracts:
        print("❌ Nenhum contrato encontrado para teste")
        sys.exit(1)
    
    # FASE 2: Benchmark da amostra
    print(f"\n⚡ FASE 2: Benchmark da amostra ({len(sample_contracts)} contratos)...")
    
    successful_categorizations = 0
    failed_categorizations = 0
    total_time = 0
    
    start_benchmark = time.time()
    
    for i, contract in enumerate(sample_contracts):
        contract_start = time.time()
        result = categorize_single_contract_fast(contract)
        contract_end = time.time()
        
        contract_time = contract_end - contract_start
        total_time += contract_time
        
        if result['success']:
            successful_categorizations += 1
            if result.get('skipped', False):
                print(f"  ⏭️  {i+1:2d}/20 | {contract:20s} | {contract_time:5.2f}s | JÁ CATEGORIZADO")
            else:
                print(f"  ✅ {i+1:2d}/20 | {contract:20s} | {contract_time:5.2f}s | {result['best_category'][:15]:15s}")
        else:
            failed_categorizations += 1
            print(f"  ❌ {i+1:2d}/20 | {contract:20s} | {contract_time:5.2f}s | ERRO")
    
    end_benchmark = time.time()
    benchmark_time = end_benchmark - start_benchmark
    
    # FASE 3: Cálculos e projeções
    print(f"\n📊 FASE 3: Análise de resultados...")
    print("-" * 80)
    
    if successful_categorizations > 0:
        avg_time_per_contract = total_time / len(sample_contracts)
        avg_success_time = total_time / successful_categorizations
        success_rate = (successful_categorizations / len(sample_contracts)) * 100
        
        print(f"✅ Sucessos: {successful_categorizations}/{len(sample_contracts)} ({success_rate:.1f}%)")
        print(f"❌ Falhas: {failed_categorizations}")
        print(f"⏱️  Tempo médio por contrato: {avg_time_per_contract:.3f}s")
        print(f"⏱️  Tempo médio por sucesso: {avg_success_time:.3f}s")
        print(f"⏱️  Tempo total da amostra: {benchmark_time:.2f}s")
        
        # PROJEÇÕES PARA O DIA COMPLETO
        print(f"\n🎯 PROJEÇÕES PARA {total_contracts} CONTRATOS:")
        print("-" * 80)
        
        # Projeção otimista (tempo médio por contrato)
        projected_time_optimistic = total_contracts * avg_time_per_contract
        
        # Projeção realista (considerando falhas)
        expected_successes = total_contracts * (success_rate / 100)
        projected_time_realistic = expected_successes * avg_success_time
        
        # Projeção com paralelização (16 workers)
        projected_time_parallel = projected_time_realistic / 16
        
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
        
        print(f"⏰ Sequencial (otimista):     {format_time(projected_time_optimistic)} ({projected_time_optimistic:,.0f}s)")
        print(f"⏰ Sequencial (realista):     {format_time(projected_time_realistic)} ({projected_time_realistic:,.0f}s)")
        print(f"🚀 Paralelo (16 workers):     {format_time(projected_time_parallel)} ({projected_time_parallel:,.0f}s)")
        
        # Performance comparison
        print(f"\n📈 COMPARAÇÃO COM 05 ORIGINAL:")
        print("-" * 80)
        print(f"🐌 05 Original (com timeout):  ~125s por tentativa (falha)")
        print(f"⚡ 05G Fast (sem timeout):     {avg_time_per_contract:.3f}s por contrato")
        print(f"🚀 Melhoria de performance:    {125/avg_time_per_contract:.0f}x mais rápido")
        
        # Estimativa de contratos por minuto
        contracts_per_minute_sequential = 60 / avg_time_per_contract
        contracts_per_minute_parallel = contracts_per_minute_sequential * 16
        
        print(f"\n💪 THROUGHPUT:")
        print("-" * 80)
        print(f"📊 Sequencial: {contracts_per_minute_sequential:.0f} contratos/min")
        print(f"🚀 Paralelo:   {contracts_per_minute_parallel:.0f} contratos/min")
        
    else:
        print("❌ Todos os testes falharam - verificar configuração do banco")
    
    print("\n" + "=" * 80)
    print("🏁 BENCHMARK CONCLUÍDO")
    print("=" * 80)
