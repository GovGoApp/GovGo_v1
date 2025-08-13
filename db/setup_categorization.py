# =======================================================================
# SETUP INICIAL PARA CATEGORIZAÇÃO
# =======================================================================
# Script para configurar a data inicial de categorização no system_config

import os
import psycopg2
from dotenv import load_dotenv

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),  # Corrigido
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'port': os.getenv('SUPABASE_PORT', 5432)
}

def setup_initial_categorization_date():
    """Configura a data inicial de categorização para processar TODOS os embeddings"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Inserir data inicial (1 de janeiro de 2020 para pegar todos os registros)
        initial_date = "20200101"
        
        cursor.execute("""
            INSERT INTO system_config (key, value, description) 
            VALUES ('last_categorization_date', %s, 'Última data processada para categorização automática - SETUP INICIAL')
            ON CONFLICT (key) 
            DO UPDATE SET 
                value = EXCLUDED.value, 
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
        """, (initial_date,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Data inicial de categorização configurada: {initial_date}")
        print("📋 Isso fará com que TODOS os embeddings sejam processados na próxima execução")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao configurar data inicial: {e}")
        return False

def check_embeddings_status():
    """Verifica o status atual dos embeddings na base"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Contar total de embeddings
        cursor.execute("SELECT COUNT(*) FROM contratacao_emb WHERE embeddings IS NOT NULL")
        total_embeddings = cursor.fetchone()[0]
        
        # Contar embeddings já categorizados
        cursor.execute("""
            SELECT COUNT(*) FROM contratacao_emb 
            WHERE embeddings IS NOT NULL 
            AND top_categories IS NOT NULL 
            AND confidence IS NOT NULL
        """)
        categorizados = cursor.fetchone()[0]
        
        # Contar embeddings pendentes
        pendentes = total_embeddings - categorizados
        
        # Verificar se existem embeddings de categorias
        cursor.execute("SELECT COUNT(*) FROM categoria WHERE cat_embeddings IS NOT NULL")
        categorias_com_embeddings = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("📊 STATUS ATUAL DOS EMBEDDINGS")
        print("="*60)
        print(f"📦 Total de embeddings: {total_embeddings:,}")
        print(f"✅ Já categorizados: {categorizados:,}")
        print(f"⏳ Pendentes: {pendentes:,}")
        print(f"🏷️  Categorias com embeddings: {categorias_com_embeddings}")
        print("="*60)
        
        if categorias_com_embeddings == 0:
            print("⚠️  ATENÇÃO: Não há embeddings de categorias!")
            print("📋 Você precisa executar o script de geração de embeddings de categorias primeiro")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return False

if __name__ == "__main__":
    print("🚀 CONFIGURAÇÃO INICIAL PARA CATEGORIZAÇÃO")
    print("=" * 50)
    
    # Verificar status atual
    if not check_embeddings_status():
        print("\n❌ Problemas encontrados. Resolva antes de continuar.")
        exit(1)
    
    # Configurar data inicial
    if setup_initial_categorization_date():
        print("\n🎉 Configuração concluída com sucesso!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. ✅ Data inicial configurada")
        print("2. 🔄 Execute o script 05_categorization.py")
        print("3. 📊 Monitore o progresso da categorização")
    else:
        print("\n❌ Falha na configuração. Verifique a conexão com o banco.")
