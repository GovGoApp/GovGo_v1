import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('SUPABASE_V0_HOST'),
    database=os.getenv('SUPABASE_V0_DBNAME'),
    user=os.getenv('SUPABASE_V0_USER'),
    password=os.getenv('SUPABASE_V0_PASSWORD'),
    port=int(os.getenv('SUPABASE_V0_PORT', '6543'))
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# Verificar registros com codcat vazio
print("=== VERIFICANDO REGISTROS COM codcat VAZIO ===")
cursor.execute("SELECT COUNT(*) as count FROM categorias WHERE codcat = '' OR codcat IS NULL")
empty_count = cursor.fetchone()['count']
print(f"Registros com codcat vazio/NULL: {empty_count}")

if empty_count > 0:
    print("\n=== PRIMEIROS 5 REGISTROS COM codcat VAZIO ===")
    cursor.execute("SELECT id, codcat, nomcat FROM categorias WHERE codcat = '' OR codcat IS NULL LIMIT 5")
    empty_records = cursor.fetchall()
    for record in empty_records:
        print(f"ID: {record['id']}, codcat: '{record['codcat']}', nomcat: '{record['nomcat'][:50]}...'")

# Verificar se há duplicatas (mesmo que não vazio)
print("\n=== VERIFICANDO DUPLICATAS GERAIS ===")
cursor.execute("""
    SELECT codcat, COUNT(*) as count 
    FROM categorias 
    GROUP BY codcat 
    HAVING COUNT(*) > 1 
    ORDER BY count DESC 
    LIMIT 5
""")
duplicates = cursor.fetchall()
if duplicates:
    print("Duplicatas encontradas:")
    for dup in duplicates:
        print(f"  codcat: '{dup['codcat']}' aparece {dup['count']} vezes")
else:
    print("Nenhuma duplicata encontrada")

# Verificar os primeiros registros da migração (offset 0, limit 100)
print("\n=== PRIMEIROS 100 REGISTROS (que estão causando erro) ===")
cursor.execute("SELECT codcat, COUNT(*) as count FROM categorias GROUP BY codcat ORDER BY codcat LIMIT 5")
first_records = cursor.fetchall()
for record in first_records:
    print(f"codcat: '{record['codcat']}' (count: {record['count']})")
