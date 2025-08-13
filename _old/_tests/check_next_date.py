#!/usr/bin/env python3
"""
Teste para verificar qual seria a próxima data inicial a ser processada
"""

import os
import sys
import datetime
import psycopg2
from dotenv import load_dotenv

# Adicionar o diretório db ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
db_dir = os.path.join(v1_root, "db")
sys.path.insert(0, db_dir)

# Carregar configurações
load_dotenv(os.path.join(v1_root, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

def get_last_processed_date(conn=None):
    """Função igual à do script 03"""
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT data_publicacao_pncp 
                FROM contratacao 
                WHERE data_publicacao_pncp IS NOT NULL 
                  AND data_publicacao_pncp ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                ORDER BY data_publicacao_pncp DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                date_from_db = result[0].replace('-', '')
                print(f"✅ Última data encontrada na base: {date_from_db}")
                return date_from_db
        except Exception as e:
            print(f"❌ Erro ao buscar data da base: {str(e)}")
    
    # Data padrão (ontem)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    default_date = yesterday.strftime("%Y%m%d")
    
    print(f"⚠️ Usando data padrão: {default_date}")
    return default_date

def get_date_range(conn=None):
    """Função igual à do script 03"""
    # Obtém a última data processada (do banco ou arquivo)
    last_date_str = get_last_processed_date(conn)
    last_date = datetime.datetime.strptime(last_date_str, "%Y%m%d").date()
    
    # Avança um dia (para começar do dia seguinte ao último processado)
    start_date = last_date + datetime.timedelta(days=1)
    
    # Data atual
    today = datetime.date.today()
    
    print(f"📅 Última data processada: {last_date_str} ({last_date})")
    print(f"📅 Próxima data inicial: {start_date.strftime('%Y%m%d')} ({start_date})")
    print(f"📅 Data atual: {today.strftime('%Y%m%d')} ({today})")
    
    # Gera o intervalo de datas
    date_range = []
    current_date = start_date
    while current_date <= today:
        date_range.append(current_date.strftime("%Y%m%d"))
        current_date += datetime.timedelta(days=1)
    
    return date_range

def main():
    print("🔍 VERIFICANDO PRÓXIMA DATA INICIAL PARA PROCESSAMENTO")
    print("=" * 60)
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Conectado ao banco PostgreSQL V1")
        
        # Verificar intervalo de datas
        date_range = get_date_range(conn)
        
        print("\n📊 RESULTADO:")
        if date_range:
            print(f"   🎯 Próximas datas a processar: {len(date_range)} dia(s)")
            for i, date_str in enumerate(date_range[:5]):  # Mostrar apenas os primeiros 5
                print(f"   {i+1}. {date_str}")
            if len(date_range) > 5:
                print(f"   ... e mais {len(date_range) - 5} dia(s)")
        else:
            print("   ✅ Dados já estão atualizados!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    main()
