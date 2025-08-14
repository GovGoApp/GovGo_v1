import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Verificar schema V1
conn = psycopg2.connect(
    host=os.getenv('SUPABASE_HOST'),
    database=os.getenv('SUPABASE_DBNAME'),
    user=os.getenv('SUPABASE_USER'),
    password=os.getenv('SUPABASE_PASSWORD'),
    port=int(os.getenv('SUPABASE_PORT', '5432'))
)

cursor = conn.cursor()
cursor.execute("""
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'contratacao_emb' 
AND table_schema = 'public'
ORDER BY ordinal_position;
""")

columns = cursor.fetchall()

print('📋 Schema da tabela contratacao_emb (V1):')
for col_name, data_type, is_nullable in columns:
    print(f'  - {col_name}: {data_type} ({"NULL" if is_nullable == "YES" else "NOT NULL"})')

conn.close()
