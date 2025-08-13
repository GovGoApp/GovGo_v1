#!/usr/bin/env python3
"""
Teste de Diagnóstico do Banco de Dados - 04B Embeddings
Testa exatamente as queries problemáticas do script 04B_embedding_generation_optimized.py
"""

import os
import sys
import time
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Carregar .env da pasta v1 (pasta pai)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# Adicionar o diretório pai ao path para importar as configurações
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Configurações de conexão (mesmas do 04B)
DB_PARAMS = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', ''),
    'sslmode': 'require',
    'connect_timeout': 10,
    'options': '-c statement_timeout=120000'  # 2 minutos para teste
}

def test_connection():
    """Teste básico de conexão"""
    print("🔧 Testando conexão básica...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Conexão OK: {version[:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def test_table_sizes():
    """Testa o tamanho das tabelas"""
    print("\n📊 Testando tamanhos das tabelas...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Tamanho da tabela contratacao
        cursor.execute("SELECT COUNT(*) FROM contratacao;")
        contratacao_count = cursor.fetchone()[0]
        print(f"📋 Tabela contratacao: {contratacao_count:,} registros")
        
        # Tamanho da tabela contratacao_emb
        cursor.execute("SELECT COUNT(*) FROM contratacao_emb;")
        emb_count = cursor.fetchone()[0]
        print(f"🧠 Tabela contratacao_emb: {emb_count:,} registros")
        
        # Registros com data_publicacao_pncp válida
        cursor.execute("SELECT COUNT(*) FROM contratacao WHERE data_publicacao_pncp IS NOT NULL;")
        valid_dates = cursor.fetchone()[0]
        print(f"📅 Registros com data_publicacao_pncp válida: {valid_dates:,}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar tamanhos: {e}")
        return False

def test_system_config():
    """Testa as configurações do sistema"""
    print("\n⚙️ Testando system_config...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Buscar last_embedding_date
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_embedding_date';")
        result = cursor.fetchone()
        last_embedding = result[0] if result else "NÃO ENCONTRADO"
        print(f"📅 last_embedding_date: {last_embedding}")
        
        # Buscar last_processed_date
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_processed_date';")
        result = cursor.fetchone()
        last_processed = result[0] if result else "NÃO ENCONTRADO"
        print(f"📅 last_processed_date: {last_processed}")
        
        cursor.close()
        conn.close()
        return last_embedding, last_processed
        
    except Exception as e:
        print(f"❌ Erro ao verificar system_config: {e}")
        return None, None

def test_date_range_count(start_date, end_date):
    """Testa contagem no intervalo de datas (versão simples)"""
    print(f"\n🔍 Testando contagem no intervalo {start_date} até {end_date}...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        start_time = time.time()
        
        # Query simples de contagem
        query = """
            SELECT COUNT(*) 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
              AND TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
        """
        
        cursor.execute(query, (start_date, end_date))
        count = cursor.fetchone()[0]
        
        elapsed = time.time() - start_time
        print(f"📊 Registros encontrados: {count:,}")
        print(f"⏱️ Tempo de execução: {elapsed:.2f}s")
        
        cursor.close()
        conn.close()
        return count, elapsed
        
    except Exception as e:
        print(f"❌ Erro na contagem simples: {e}")
        return None, None

def test_complex_query(start_date, end_date):
    """Testa a query complexa problemática do 04B"""
    print(f"\n🔥 Testando query complexa (PROBLEMÁTICA) {start_date} até {end_date}...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        start_time = time.time()
        
        # Query complexa exata do 04B
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
        
        print("⏳ Executando query complexa (pode demorar)...")
        cursor.execute(query, (start_date, end_date))
        dates = cursor.fetchall()
        
        elapsed = time.time() - start_time
        print(f"📅 Datas encontradas: {len(dates)}")
        print(f"⏱️ Tempo de execução: {elapsed:.2f}s")
        
        if dates:
            print(f"🗓️ Primeiras 5 datas: {[d[0].strftime('%Y-%m-%d') for d in dates[:5]]}")
        
        cursor.close()
        conn.close()
        return len(dates), elapsed
        
    except Exception as e:
        print(f"❌ ERRO na query complexa: {e}")
        return None, None

def test_indexes():
    """Verifica índices existentes"""
    print("\n🏗️ Verificando índices...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Índices da tabela contratacao
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'contratacao' 
              AND (indexdef ILIKE '%data_publicacao%' OR indexdef ILIKE '%numero_controle%')
        """)
        
        contratacao_indexes = cursor.fetchall()
        print("📋 Índices relevantes em 'contratacao':")
        if contratacao_indexes:
            for idx_name, idx_def in contratacao_indexes:
                print(f"   • {idx_name}: {idx_def[:100]}...")
        else:
            print("   ❌ Nenhum índice relevante encontrado!")
        
        # Índices da tabela contratacao_emb
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'contratacao_emb'
              AND indexdef ILIKE '%numero_controle%'
        """)
        
        emb_indexes = cursor.fetchall()
        print("\n🧠 Índices relevantes em 'contratacao_emb':")
        if emb_indexes:
            for idx_name, idx_def in emb_indexes:
                print(f"   • {idx_name}: {idx_def[:100]}...")
        else:
            print("   ❌ Nenhum índice relevante encontrado!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar índices: {e}")
        return False

def test_sample_dates():
    """Testa algumas datas específicas"""
    print("\n🎯 Testando datas específicas...")
    
    test_dates = [
        ("2025-08-01", "2025-08-02"),  # 1 dia recente
        ("2025-07-01", "2025-07-07"),  # 1 semana
        ("2025-06-01", "2025-06-30"),  # 1 mês
    ]
    
    for start, end in test_dates:
        print(f"\n📅 Testando {start} até {end}:")
        
        # Teste simples
        count, elapsed_simple = test_date_range_count(start, end)
        
        # Teste complexo (apenas se o simples funcionou)
        if count is not None and count < 100000:  # Só testa se não for muito grande
            complex_count, elapsed_complex = test_complex_query(start, end)
        else:
            print("⚠️ Muitos registros, pulando query complexa")

def main():
    """Executa todos os testes de diagnóstico"""
    print("🩺 DIAGNÓSTICO DO BANCO DE DADOS - 04B EMBEDDINGS")
    print("=" * 60)
    
    # 1. Teste básico
    if not test_connection():
        print("❌ Falha na conexão. Parando testes.")
        return
    
    # 2. Tamanhos das tabelas
    test_table_sizes()
    
    # 3. System config
    last_embedding, last_processed = test_system_config()
    
    # 4. Índices
    test_indexes()
    
    # 5. Testes de datas amostrais
    test_sample_dates()
    
    # 6. Teste do intervalo problemático (se as datas foram encontradas)
    if last_embedding and last_processed:
        print(f"\n🔥 TESTE DO INTERVALO PROBLEMÁTICO:")
        print(f"📅 Intervalo: {last_embedding} até {last_processed}")
        
        # Converter formato de data
        start_fmt = f"{last_embedding[:4]}-{last_embedding[4:6]}-{last_embedding[6:8]}"
        end_fmt = f"{last_processed[:4]}-{last_processed[4:6]}-{last_processed[6:8]}"
        
        # Primeiro teste simples
        count, elapsed = test_date_range_count(start_fmt, end_fmt)
        
        if count is not None:
            if count < 500000:  # Só testa query complexa se não for absurdo
                print("🚨 Testando query complexa no intervalo problemático...")
                test_complex_query(start_fmt, end_fmt)
            else:
                print(f"⚠️ Intervalo muito grande ({count:,} registros). Query complexa seria muito lenta!")
    
    print("\n✅ DIAGNÓSTICO CONCLUÍDO")

if __name__ == "__main__":
    main()
