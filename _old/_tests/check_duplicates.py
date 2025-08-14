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

# Verificar duplicatas
cursor.execute('SELECT codcat, COUNT(*) as count FROM categorias GROUP BY codcat HAVING COUNT(*) > 1 ORDER BY count DESC LIMIT 10')
duplicates = cursor.fetchall()
print('DUPLICATAS ENCONTRADAS:')
for row in duplicates:
    print(f'  codcat="{row["codcat"]}" aparece {row["count"]} vezes')

# Estatísticas gerais
cursor.execute('SELECT COUNT(*) as total FROM categorias')
total = cursor.fetchone()['total']
print(f'TOTAL DE REGISTROS: {total}')

cursor.execute('SELECT COUNT(DISTINCT codcat) as unique_count FROM categorias')
unique = cursor.fetchone()['unique_count']
print(f'VALORES ÚNICOS DE codcat: {unique}')

# Verificar valores vazios especificamente
cursor.execute("SELECT COUNT(*) as empty_count FROM categorias WHERE codcat = '' OR codcat IS NULL")
empty = cursor.fetchone()['empty_count']
print(f'VALORES VAZIOS/NULL: {empty}')
