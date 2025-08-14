#!/usr/bin/env python3
"""
Teste de conexão com o banco Supabase V1
"""

import os
import psycopg2
from dotenv import load_dotenv

# Carregar variáveis de ambiente
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(v1_root, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'port': os.getenv('SUPABASE_PORT'),
    'database': os.getenv('SUPABASE_DBNAME'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD')
}

print("Configurações do banco:")
for key, value in DB_CONFIG.items():
    if key == 'password':
        print(f"  {key}: {'*' * len(str(value)) if value else 'VAZIO'}")
    else:
        print(f"  {key}: {value}")

try:
    print("\nTentando conectar...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Conexão bem-sucedida!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT current_database(), version()")
    db_name, version = cursor.fetchone()
    print(f"Banco: {db_name}")
    print(f"Versão: {version}")
    
    # Verificar tabelas existentes
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print(f"\nTabelas encontradas ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()
    print("\n✅ Teste concluído com sucesso!")
    
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
