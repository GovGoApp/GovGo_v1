#!/usr/bin/env python3
"""
Teste Específico da Query Problemática - 04B
Replica exatamente a função get_dates_needing_embeddings() que está dando timeout
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

# Configurações de conexão (mesmas do 04B)
DB_PARAMS = {
    'host': os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DATABASE', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres.xrcqjnvltvhkwrqvvddf'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'sslmode': 'require',
    'connect_timeout': 10,
    'options': '-c statement_timeout=120000'  # 2 minutos
}

def get_system_dates():
    """Replica as funções get_last_embedding_date() e get_last_processed_date()"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # get_last_embedding_date()
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_embedding_date'")
        result = cursor.fetchone()
        last_embedding_date = result[0] if result else "20200101"
        
        # get_last_processed_date()
        cursor.execute("SELECT value FROM system_config WHERE key = 'last_processed_date'")
        result = cursor.fetchone()
        last_processed_date = result[0] if result else datetime.now().strftime("%Y%m%d")
        
        cursor.close()
        conn.close()
        
        return last_embedding_date, last_processed_date
        
    except Exception as e:
        print(f"❌ Erro ao obter datas do system: {e}")
        return None, None

def test_exact_04B_query(last_embedding_date, last_processed_date):
    """
    Replica EXATAMENTE a função get_dates_needing_embeddings() do 04B
    """
    print(f"🔥 Testando query EXATA do 04B...")
    print(f"📅 Parâmetros: last_embedding_date={last_embedding_date}, last_processed_date={last_processed_date}")
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Converter datas para formato SQL
        last_embedding_date_formatted = f"{last_embedding_date[:4]}-{last_embedding_date[4:6]}-{last_embedding_date[6:8]}"
        last_processed_date_formatted = f"{last_processed_date[:4]}-{last_processed_date[4:6]}-{last_processed_date[6:8]}"
        
        print(f"🗓️ Datas formatadas: {last_embedding_date_formatted} até {last_processed_date_formatted}")
        
        # Query EXATA do 04B (modo normal com last_processed_date)
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
        
        print("⏳ Executando query (pode demorar até 2 minutos)...")
        start_time = time.time()
        
        cursor.execute(query, (last_embedding_date_formatted, last_processed_date_formatted))
        dates = [row[0].strftime('%Y%m%d') for row in cursor.fetchall()]
        
        elapsed = time.time() - start_time
        
        print(f"✅ Query executada com sucesso!")
        print(f"📅 Datas encontradas: {len(dates)}")
        print(f"⏱️ Tempo de execução: {elapsed:.2f}s")
        
        if dates:
            print(f"🗓️ Primeiras 5 datas: {dates[:5]}")
            print(f"🗓️ Últimas 5 datas: {dates[-5:] if len(dates) > 5 else dates}")
        
        cursor.close()
        conn.close()
        
        return dates, elapsed
        
    except psycopg2.OperationalError as e:
        if "statement timeout" in str(e):
            print(f"⏰ TIMEOUT! Query cancelada após 2 minutos: {e}")
        else:
            print(f"❌ Erro operacional: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Erro na query: {e}")
        return None, None

def analyze_subqueries(last_embedding_date, last_processed_date):
    """
    Analisa as partes da query separadamente para identificar o gargalo
    """
    print(f"\n🔍 ANÁLISE DAS SUBQUERIES...")
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        last_embedding_date_formatted = f"{last_embedding_date[:4]}-{last_embedding_date[4:6]}-{last_embedding_date[6:8]}"
        last_processed_date_formatted = f"{last_processed_date[:4]}-{last_processed_date[4:6]}-{last_processed_date[6:8]}"
        
        # 1. Teste da parte principal (sem EXISTS)
        print("\n1️⃣ Testando parte principal (sem EXISTS):")
        start_time = time.time()
        query1 = """
            SELECT COUNT(DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD'))
            FROM contratacao c
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
        """
        cursor.execute(query1, (last_embedding_date_formatted, last_processed_date_formatted))
        count1 = cursor.fetchone()[0]
        elapsed1 = time.time() - start_time
        print(f"   📊 Datas únicas no intervalo: {count1}")
        print(f"   ⏱️ Tempo: {elapsed1:.2f}s")
        
        # 2. Teste da subquery NOT IN
        print("\n2️⃣ Testando subquery NOT IN:")
        start_time = time.time()
        query2 = """
            SELECT COUNT(DISTINCT numero_controle_pncp) 
            FROM contratacao_emb 
            WHERE numero_controle_pncp IS NOT NULL
        """
        cursor.execute(query2)
        count2 = cursor.fetchone()[0]
        elapsed2 = time.time() - start_time
        print(f"   📊 Embeddings já processados: {count2}")
        print(f"   ⏱️ Tempo: {elapsed2:.2f}s")
        
        # 3. Teste de registros no intervalo (sem NOT IN)
        print("\n3️⃣ Testando registros no intervalo:")
        start_time = time.time()
        query3 = """
            SELECT COUNT(*)
            FROM contratacao c
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
        """
        cursor.execute(query3, (last_embedding_date_formatted, last_processed_date_formatted))
        count3 = cursor.fetchone()[0]
        elapsed3 = time.time() - start_time
        print(f"   📊 Total de registros no intervalo: {count3:,}")
        print(f"   ⏱️ Tempo: {elapsed3:.2f}s")
        
        # 4. Análise de registros que ainda precisam de embeddings
        print("\n4️⃣ Testando registros que precisam de embeddings (APROXIMADO):")
        start_time = time.time()
        query4 = """
            SELECT COUNT(*)
            FROM contratacao c
            WHERE c.data_publicacao_pncp IS NOT NULL 
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
              AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
              AND c.numero_controle_pncp NOT IN (
                  SELECT numero_controle_pncp 
                  FROM contratacao_emb 
                  WHERE numero_controle_pncp IS NOT NULL
              )
        """
        cursor.execute(query4, (last_embedding_date_formatted, last_processed_date_formatted))
        count4 = cursor.fetchone()[0]
        elapsed4 = time.time() - start_time
        print(f"   📊 Registros sem embedding: {count4:,}")
        print(f"   ⏱️ Tempo: {elapsed4:.2f}s")
        
        cursor.close()
        conn.close()
        
        print(f"\n📈 RESUMO DA ANÁLISE:")
        print(f"   • Datas únicas no intervalo: {count1}")
        print(f"   • Total de registros no intervalo: {count3:,}")
        print(f"   • Embeddings já processados: {count2:,}")
        print(f"   • Registros sem embedding: {count4:,}")
        print(f"   • Percentual processado: {(count2/(count2+count4)*100):.1f}%" if count4 > 0 else "   • Todos processados!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return False

def suggest_optimizations():
    """Sugere otimizações baseadas nos testes"""
    print(f"\n💡 SUGESTÕES DE OTIMIZAÇÃO:")
    print(f"   1. Adicionar índice: CREATE INDEX idx_contratacao_data_pub ON contratacao (TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD'));")
    print(f"   2. Adicionar índice: CREATE INDEX idx_contratacao_numero_controle ON contratacao (numero_controle_pncp);")
    print(f"   3. Adicionar índice: CREATE INDEX idx_contratacao_emb_numero ON contratacao_emb (numero_controle_pncp);")
    print(f"   4. Trocar NOT IN por NOT EXISTS (melhor performance)")
    print(f"   5. Processar em chunks menores (ex: 1 mês por vez)")
    print(f"   6. Aumentar statement_timeout para 5-10 minutos")

def main():
    """Executa o teste específico da query problemática"""
    print("🩺 TESTE ESPECÍFICO DA QUERY PROBLEMÁTICA - 04B")
    print("=" * 60)
    
    # Obter as datas do sistema
    last_embedding, last_processed = get_system_dates()
    
    if not last_embedding or not last_processed:
        print("❌ Erro ao obter datas do sistema. Parando teste.")
        return
    
    print(f"📅 Datas obtidas do sistema:")
    print(f"   • last_embedding_date: {last_embedding}")
    print(f"   • last_processed_date: {last_processed}")
    
    # Verificar se há trabalho a fazer
    if last_embedding >= last_processed:
        print("✅ Embeddings já estão atualizados. Nenhum processamento necessário.")
        return
    
    # Análise das subqueries
    if analyze_subqueries(last_embedding, last_processed):
        print("\n" + "="*60)
    
    # Teste da query completa
    dates, elapsed = test_exact_04B_query(last_embedding, last_processed)
    
    if dates is not None:
        print(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        print(f"   📊 {len(dates)} datas encontradas em {elapsed:.2f}s")
    else:
        print(f"\n❌ TESTE FALHOU - TIMEOUT OU ERRO")
        suggest_optimizations()

if __name__ == "__main__":
    main()
