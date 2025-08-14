#!/usr/bin/env python3
"""
Teste de Índices e Performance - 04B
Verifica índices existentes e sugere otimizações
"""

import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

# Carregar .env da pasta v1 (pasta pai)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# Configurações de conexão
DB_PARAMS = {
    'host': os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DATABASE', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres.xrcqjnvltvhkwrqvvddf'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'sslmode': 'require',
    'connect_timeout': 10,
    'options': '-c statement_timeout=30000'
}

def check_table_stats():
    """Verifica estatísticas das tabelas"""
    print("📊 ESTATÍSTICAS DAS TABELAS")
    print("-" * 40)
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Estatísticas da tabela contratacao
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables 
            WHERE tablename IN ('contratacao', 'contratacao_emb')
            ORDER BY tablename
        """)
        
        stats = cursor.fetchall()
        for stat in stats:
            table = stat[1]
            live_rows = stat[5]
            dead_rows = stat[6]
            last_analyze = stat[9]
            
            print(f"\n🗂️ Tabela: {table}")
            print(f"   📈 Linhas vivas: {live_rows:,}")
            print(f"   💀 Linhas mortas: {dead_rows:,}")
            print(f"   🔍 Última análise: {last_analyze}")
            
            if dead_rows > live_rows * 0.1:
                print(f"   ⚠️ Muitas linhas mortas! Considere VACUUM.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar estatísticas: {e}")
        return False

def check_existing_indexes():
    """Verifica índices existentes"""
    print("\n🏗️ ÍNDICES EXISTENTES")
    print("-" * 40)
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Índices das tabelas relevantes
        cursor.execute("""
            SELECT 
                t.tablename,
                i.indexname,
                i.indexdef,
                s.idx_tup_read,
                s.idx_tup_fetch
            FROM pg_indexes i
            JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
            JOIN pg_tables t ON i.tablename = t.tablename
            WHERE i.tablename IN ('contratacao', 'contratacao_emb')
            ORDER BY t.tablename, i.indexname
        """)
        
        indexes = cursor.fetchall()
        current_table = None
        
        for idx in indexes:
            table, idx_name, idx_def, reads, fetches = idx
            
            if table != current_table:
                print(f"\n📋 Tabela: {table}")
                current_table = table
            
            print(f"   • {idx_name}")
            print(f"     📖 Leituras: {reads:,}")
            print(f"     🔍 Definição: {idx_def[:80]}...")
            
            # Verificar se é índice relevante para nossa query
            if any(col in idx_def.lower() for col in ['data_publicacao', 'numero_controle']):
                print(f"     ✅ RELEVANTE para query 04B")
            else:
                print(f"     ℹ️ Não relevante para query 04B")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar índices: {e}")
        return False

def test_query_plans():
    """Testa planos de execução das queries"""
    print("\n📋 PLANOS DE EXECUÇÃO")
    print("-" * 40)
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # 1. Plano da query simples
        print("\n1️⃣ Query simples (contagem por intervalo):")
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS) 
            SELECT COUNT(*) 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD') > '2025-07-01'::date
              AND TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD') <= '2025-07-07'::date
        """)
        
        plan = cursor.fetchall()
        for line in plan:
            print(f"   {line[0]}")
        
        # 2. Plano da subquery NOT IN
        print("\n2️⃣ Subquery NOT IN:")
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS) 
            SELECT COUNT(DISTINCT numero_controle_pncp) 
            FROM contratacao_emb 
            WHERE numero_controle_pncp IS NOT NULL
        """)
        
        plan = cursor.fetchall()
        for line in plan:
            print(f"   {line[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar planos: {e}")
        return False

def suggest_missing_indexes():
    """Sugere índices que podem estar faltando"""
    print("\n💡 SUGESTÕES DE ÍNDICES")
    print("-" * 40)
    
    suggestions = [
        {
            "table": "contratacao",
            "column": "TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD')",
            "index": "CREATE INDEX CONCURRENTLY idx_contratacao_data_pub_func ON contratacao (TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD'));",
            "benefit": "Acelera filtros por data de publicação"
        },
        {
            "table": "contratacao",
            "column": "numero_controle_pncp",
            "index": "CREATE INDEX CONCURRENTLY idx_contratacao_numero_controle ON contratacao (numero_controle_pncp);",
            "benefit": "Acelera junções e NOT IN"
        },
        {
            "table": "contratacao_emb",
            "column": "numero_controle_pncp",
            "index": "CREATE INDEX CONCURRENTLY idx_contratacao_emb_numero_controle ON contratacao_emb (numero_controle_pncp);",
            "benefit": "Acelera NOT IN e verificações de duplicatas"
        },
        {
            "table": "contratacao",
            "column": "(data_publicacao_pncp, numero_controle_pncp)",
            "index": "CREATE INDEX CONCURRENTLY idx_contratacao_composite ON contratacao (TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD'), numero_controle_pncp);",
            "benefit": "Índice composto para query complexa"
        }
    ]
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}️⃣ Tabela: {suggestion['table']}")
        print(f"   🎯 Coluna: {suggestion['column']}")
        print(f"   📈 Benefício: {suggestion['benefit']}")
        print(f"   💻 Comando: {suggestion['index']}")
        print(f"   ⚠️ AVISO: Use CONCURRENTLY para não bloquear a tabela!")

def test_alternative_queries():
    """Testa queries alternativas mais eficientes"""
    print("\n🔄 QUERIES ALTERNATIVAS")
    print("-" * 40)
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Query alternativa usando NOT EXISTS ao invés de NOT IN
        print("\n1️⃣ Query com NOT EXISTS (ao invés de NOT IN):")
        start_time = time.time()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD'))
            FROM contratacao c
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > '2025-07-01'::date
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= '2025-07-07'::date
              AND NOT EXISTS (
                  SELECT 1 FROM contratacao_emb e
                  WHERE e.numero_controle_pncp = c.numero_controle_pncp
              )
        """)
        
        result1 = cursor.fetchone()[0]
        elapsed1 = time.time() - start_time
        print(f"   📊 Resultado: {result1} datas")
        print(f"   ⏱️ Tempo: {elapsed1:.2f}s")
        
        # Query usando LEFT JOIN
        print("\n2️⃣ Query com LEFT JOIN:")
        start_time = time.time()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD'))
            FROM contratacao c
            LEFT JOIN contratacao_emb e ON c.numero_controle_pncp = e.numero_controle_pncp
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > '2025-07-01'::date
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= '2025-07-07'::date
              AND e.numero_controle_pncp IS NULL
        """)
        
        result2 = cursor.fetchone()[0]
        elapsed2 = time.time() - start_time
        print(f"   📊 Resultado: {result2} datas")
        print(f"   ⏱️ Tempo: {elapsed2:.2f}s")
        
        cursor.close()
        conn.close()
        
        print(f"\n📈 Comparação:")
        print(f"   • NOT EXISTS: {elapsed1:.2f}s")
        print(f"   • LEFT JOIN: {elapsed2:.2f}s")
        
        if elapsed2 < elapsed1:
            print(f"   ✅ LEFT JOIN é mais rápido!")
        elif elapsed1 < elapsed2:
            print(f"   ✅ NOT EXISTS é mais rápido!")
        else:
            print(f"   ➡️ Performance similar")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar queries alternativas: {e}")
        return False

def main():
    """Executa análise completa de performance"""
    print("🔍 ANÁLISE DE PERFORMANCE E ÍNDICES - 04B")
    print("=" * 60)
    
    # 1. Verificar estatísticas das tabelas
    check_table_stats()
    
    # 2. Verificar índices existentes
    check_existing_indexes()
    
    # 3. Testar planos de execução
    test_query_plans()
    
    # 4. Sugerir índices
    suggest_missing_indexes()
    
    # 5. Testar queries alternativas
    test_alternative_queries()
    
    print(f"\n" + "="*60)
    print(f"✅ ANÁLISE DE PERFORMANCE CONCLUÍDA")
    print(f"\n🚀 PRÓXIMOS PASSOS RECOMENDADOS:")
    print(f"   1. Criar os índices sugeridos (com CONCURRENTLY)")
    print(f"   2. Executar ANALYZE nas tabelas após criar índices")
    print(f"   3. Testar query alternativa mais eficiente")
    print(f"   4. Considerar processar em chunks menores")

if __name__ == "__main__":
    main()
