import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env')

DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', ''),
    'options': '-c client_encoding=UTF8'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Verificar estrutura da tabela contratacao
    print('=== ESTRUTURA DA TABELA CONTRATACAO ===')
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'contratacao' 
        ORDER BY ordinal_position
    """)
    
    for row in cursor.fetchall():
        print(f'{row[0]}: {row[1]}')
    
    # 2. Verificar se há dados na tabela
    cursor.execute('SELECT COUNT(*) FROM contratacao')
    count = cursor.fetchone()[0]
    print(f'\n=== TOTAL DE CONTRATACOES: {count} ===')
    
    # 3. Ver amostras de datas
    if count > 0:
        cursor.execute("""
            SELECT created_at::date, COUNT(*) 
            FROM contratacao 
            GROUP BY created_at::date 
            ORDER BY created_at::date DESC 
            LIMIT 10
        """)
        
        print('\n=== DATAS DISPONÍVEIS (TOP 10) ===')
        for row in cursor.fetchall():
            print(f'{row[0]}: {row[1]} contratações')
    
        # 4. Testar a consulta atual do script 04
        print('\n=== TESTANDO CONSULTA DO SCRIPT 04 ===')
        test_date = '2025-01-01'  # 20250101 convertido
        
        cursor.execute("""
            SELECT DISTINCT c.created_at::date as data_processamento
            FROM contratacao c
            WHERE c.created_at::date = %s::date
            ORDER BY data_processamento
        """, (test_date,))
        
        result = cursor.fetchall()
        print(f'Consulta para {test_date}: {len(result)} resultados')
        for row in result:
            print(f'  Data encontrada: {row[0]}')
        
        # 5. Ver dados mais recentes
        cursor.execute("""
            SELECT MAX(created_at::date) as data_mais_recente
            FROM contratacao 
        """)
        
        max_date = cursor.fetchone()[0]
        print(f'\nData mais recente: {max_date}')
        
        # 6. Testar com data mais recente
        cursor.execute("""
            SELECT COUNT(*) 
            FROM contratacao c
            WHERE c.created_at::date = %s::date
        """, (max_date,))
        
        count_recent = cursor.fetchone()[0]
        print(f'Contratações na data mais recente ({max_date}): {count_recent}')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Erro: {e}')
