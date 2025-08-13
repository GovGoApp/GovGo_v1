#!/usr/bin/env python3
"""
Teste de Verificação de Conexões Ativas
Verifica quantas conexões estão abertas no PostgreSQL
"""

import os
import sys
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
    'connect_timeout': 10
}

def check_active_connections():
    """Verifica conexões ativas no PostgreSQL"""
    print("🔍 VERIFICANDO CONEXÕES ATIVAS NO POSTGRESQL")
    print("="*50)
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # 1. Total de conexões ativas
        cursor.execute("""
            SELECT count(*) as total_connections
            FROM pg_stat_activity 
            WHERE state = 'active' OR state = 'idle'
        """)
        total_connections = cursor.fetchone()[0]
        print(f"📊 Total de conexões ativas/idle: {total_connections}")
        
        # 2. Conexões por estado
        cursor.execute("""
            SELECT state, count(*) 
            FROM pg_stat_activity 
            GROUP BY state
            ORDER BY count(*) DESC
        """)
        states = cursor.fetchall()
        print(f"\n📋 Conexões por estado:")
        for state, count in states:
            print(f"   • {state}: {count}")
        
        # 3. Conexões do nosso usuário específico
        cursor.execute("""
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE usename = %s 
              AND (state = 'active' OR state = 'idle')
        """, (DB_PARAMS['user'].split('.')[1] if '.' in DB_PARAMS['user'] else DB_PARAMS['user'],))
        user_connections = cursor.fetchone()[0]
        print(f"\n👤 Conexões do nosso usuário: {user_connections}")
        
        # 4. Detalhes das conexões do nosso usuário
        cursor.execute("""
            SELECT 
                pid,
                state,
                query_start,
                state_change,
                left(query, 50) as query_preview
            FROM pg_stat_activity 
            WHERE usename = %s 
              AND (state = 'active' OR state = 'idle')
            ORDER BY state_change DESC
            LIMIT 10
        """, (DB_PARAMS['user'].split('.')[1] if '.' in DB_PARAMS['user'] else DB_PARAMS['user'],))
        
        user_details = cursor.fetchall()
        print(f"\n🔍 Detalhes das conexões do usuário:")
        for pid, state, query_start, state_change, query in user_details:
            print(f"   • PID {pid}: {state} | Início: {query_start} | Query: {query}...")
        
        # 5. Limite de conexões
        cursor.execute("SHOW max_connections")
        max_conn = cursor.fetchone()[0]
        print(f"\n⚙️ Limite máximo de conexões: {max_conn}")
        
        # 6. Conexões por aplicação
        cursor.execute("""
            SELECT application_name, count(*) 
            FROM pg_stat_activity 
            WHERE application_name IS NOT NULL
            GROUP BY application_name
            ORDER BY count(*) DESC
        """)
        apps = cursor.fetchall()
        print(f"\n📱 Conexões por aplicação:")
        for app, count in apps:
            print(f"   • {app}: {count}")
        
        cursor.close()
        conn.close()
        
        # Análise
        print(f"\n📈 ANÁLISE:")
        percentage = (total_connections / int(max_conn)) * 100
        print(f"   • Uso de conexões: {percentage:.1f}% ({total_connections}/{max_conn})")
        
        if user_connections > 5:
            print(f"   ⚠️ Muitas conexões do nosso usuário ({user_connections})! Possível vazamento.")
        elif user_connections == 0:
            print(f"   ✅ Nenhuma conexão órfã detectada.")
        else:
            print(f"   ✅ Conexões do usuário em nível normal ({user_connections}).")
            
        if percentage > 80:
            print(f"   🚨 PostgreSQL próximo do limite de conexões!")
        elif percentage > 50:
            print(f"   ⚠️ Uso moderado de conexões.")
        else:
            print(f"   ✅ Uso baixo de conexões.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar conexões: {e}")
        return False

def test_connection_lifecycle():
    """Testa ciclo de vida das conexões"""
    print(f"\n🔄 TESTANDO CICLO DE VIDA DAS CONEXÕES")
    print("-"*40)
    
    connections = []
    try:
        # Criar várias conexões
        print("📤 Criando 5 conexões...")
        for i in range(5):
            conn = psycopg2.connect(**DB_PARAMS)
            connections.append(conn)
            print(f"   ✅ Conexão {i+1} criada")
        
        # Verificar se apareceram no PostgreSQL
        print("\n🔍 Verificando no PostgreSQL...")
        check_conn = psycopg2.connect(**DB_PARAMS)
        cursor = check_conn.cursor()
        cursor.execute("""
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE usename = %s 
              AND (state = 'active' OR state = 'idle')
        """, (DB_PARAMS['user'].split('.')[1] if '.' in DB_PARAMS['user'] else DB_PARAMS['user'],))
        active_count = cursor.fetchone()[0]
        print(f"📊 Conexões ativas detectadas: {active_count}")
        cursor.close()
        check_conn.close()
        
    finally:
        # Fechar conexões corretamente
        print(f"\n🔒 Fechando conexões...")
        for i, conn in enumerate(connections):
            conn.close()
            print(f"   🔒 Conexão {i+1} fechada")

def main():
    """Executa verificação completa de conexões"""
    check_active_connections()
    test_connection_lifecycle()
    
    print(f"\n🔄 Executando verificação final...")
    check_active_connections()

if __name__ == "__main__":
    main()
