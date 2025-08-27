#!/usr/bin/env python3
"""
Aplica a migration 2025-08-26_user_prompts_config_and_defaults.sql usando variáveis do .env/supabase_v1.env.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

HERE = os.path.dirname(__file__)
SQL_FILE = os.path.join(HERE, '2025-08-26_user_prompts_config_and_defaults.sql')

# Carregar env com a mesma prioridade do projeto
for candidate in (os.path.join(os.path.dirname(HERE), '..', 'search', 'gvg_browser', 'supabase_v1.env'),
                  os.path.join(os.path.dirname(HERE), '..', 'search', 'gvg_browser', '.env'),
                  'supabase_v1.env', '.env', os.path.join(os.path.dirname(HERE), '..', 'supabase_v1.env')):
    if os.path.exists(candidate):
        load_dotenv(candidate, override=False)

host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
user = os.getenv('SUPABASE_USER')
password = os.getenv('SUPABASE_PASSWORD')
port = os.getenv('SUPABASE_PORT', '6543')
dbname = os.getenv('SUPABASE_DBNAME', os.getenv('SUPABASE_DB_NAME', 'postgres'))

if not (user and password):
    print('Credenciais do Supabase não encontradas em variáveis de ambiente.')
    sys.exit(1)

conn = None
cur = None
try:
    conn = psycopg2.connect(
        host=host, database=dbname, user=user, password=password, port=port
    )
    cur = conn.cursor()
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    print('Migration aplicada com sucesso.')
except Exception as e:
    if conn:
        try:
            conn.rollback()
        except Exception:
            pass
    print(f'Erro ao aplicar migration: {e}')
    sys.exit(1)
finally:
    try:
        if cur:
            cur.close()
    finally:
        if conn:
            conn.close()
