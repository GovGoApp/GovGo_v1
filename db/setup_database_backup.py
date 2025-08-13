#!/usr/bin/env python3
"""
GovGo V1 - Setup do Banco de Dados BACKUP
BACKUP do arquivo original antes da reestruturação
"""

from supabase import create_client, Client
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Adicionar o diretório pai ao path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from core.database import DatabaseManager

# Carregar variáveis de ambiente
load_dotenv()

def setup_supabase_tables():
    """Cria todas as tabelas necessárias no Supabase"""
    
    # Conectar ao Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_ANON_KEY devem estar definidos no .env")
    
    supabase: Client = create_client(url, key)
    
    print("🚀 Iniciando setup das tabelas do Supabase...")
    
    # SQL para criar tabela unificada de documentos PNCP
    create_documentos_sql = """
    CREATE TABLE IF NOT EXISTS documentos_pncp (
        id BIGSERIAL PRIMARY KEY,
        
        -- Identificação básica
        numero_controle_pncp TEXT UNIQUE NOT NULL,
        tipo_documento TEXT NOT NULL CHECK (tipo_documento IN ('contratacao', 'contrato', 'ata', 'pca')),
        
        -- Dados do órgão
        orgao_cnpj TEXT NOT NULL,
        orgao_razao_social TEXT,
        orgao_poder_id TEXT,
        orgao_esfera_id TEXT,
        
        -- Dados temporais
        ano_documento INTEGER,
        sequencial_documento INTEGER,
        data_inclusao TIMESTAMPTZ,
        data_publicacao_pncp TIMESTAMPTZ,
        data_atualizacao TIMESTAMPTZ,
        
        -- Valores financeiros
        valor_total_estimado DECIMAL(15,2),
        valor_total_homologado DECIMAL(15,2),
        
        -- Dados específicos (JSONB para flexibilidade)
        dados_especificos JSONB,
        
        -- Metadados
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        
        -- Índices
        CONSTRAINT idx_numero_controle_unique UNIQUE (numero_controle_pncp)
    );
    """
    
    # SQL para criar tabela de itens
    create_itens_sql = """
    CREATE TABLE IF NOT EXISTS itens_documentos_pncp (
        id BIGSERIAL PRIMARY KEY,
        documento_id BIGINT REFERENCES documentos_pncp(id) ON DELETE CASCADE,
        numero_controle_pncp TEXT NOT NULL,
        numero_item TEXT NOT NULL,
        
        -- Dados do item
        descricao TEXT,
        material_ou_servico TEXT,
        valor_unitario_estimado DECIMAL(15,2),
        valor_total DECIMAL(15,2),
        quantidade DECIMAL(15,3),
        unidade_medida TEXT,
        
        -- Categoria
        item_categoria_id TEXT,
        item_categoria_nome TEXT,
        
        -- Metadados
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        
        -- Constraint de combinação única
        CONSTRAINT idx_item_documento_unique UNIQUE (numero_controle_pncp, numero_item)
    );
    """
    
    # SQL para criar tabela de classificações
    create_classificacoes_sql = """
    CREATE TABLE IF NOT EXISTS classificacoes_itens (
        id BIGSERIAL PRIMARY KEY,
        numero_controle_pncp TEXT NOT NULL,
        numero_item TEXT NOT NULL,
        
        -- Classificação
        descricao TEXT,
        item_type TEXT,
        
        -- Top 5 classificações
        top_1 TEXT,
        top_2 TEXT,
        top_3 TEXT,
        top_4 TEXT,
        top_5 TEXT,
        
        -- Scores
        score_1 DECIMAL(5,4),
        score_2 DECIMAL(5,4),
        score_3 DECIMAL(5,4),
        score_4 DECIMAL(5,4),
        score_5 DECIMAL(5,4),
        confidence DECIMAL(5,4),
        
        -- Metadados
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        
        -- Constraint de combinação única
        CONSTRAINT idx_classificacao_item_unique UNIQUE (numero_controle_pncp, numero_item)
    );
    """
    
    # SQL para criar tabela de categorias
    create_categorias_sql = """
    CREATE TABLE IF NOT EXISTS categorias (
        id BIGSERIAL PRIMARY KEY,
        codigo_categoria TEXT UNIQUE NOT NULL,
        nome_categoria TEXT NOT NULL,
        
        -- Hierarquia de categorias (até 4 níveis)
        codigo_nivel_0 TEXT,
        nome_nivel_0 TEXT,
        codigo_nivel_1 TEXT,
        nome_nivel_1 TEXT,
        codigo_nivel_2 TEXT,
        nome_nivel_2 TEXT,
        codigo_nivel_3 TEXT,
        nome_nivel_3 TEXT,
        
        -- Metadados
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    # SQL para criar índices
    create_indexes_sql = """
    -- Índices para performance
    CREATE INDEX IF NOT EXISTS idx_documentos_tipo ON documentos_pncp(tipo_documento);
    CREATE INDEX IF NOT EXISTS idx_documentos_orgao ON documentos_pncp(orgao_cnpj);
    CREATE INDEX IF NOT EXISTS idx_documentos_ano ON documentos_pncp(ano_documento);
    CREATE INDEX IF NOT EXISTS idx_itens_documento ON itens_documentos_pncp(documento_id);
    CREATE INDEX IF NOT EXISTS idx_itens_categoria ON itens_documentos_pncp(item_categoria_id);
    CREATE INDEX IF NOT EXISTS idx_classificacoes_confidence ON classificacoes_itens(confidence);
    """
    
    # SQL para habilitar RLS (Row Level Security)
    enable_rls_sql = """
    ALTER TABLE documentos_pncp ENABLE ROW LEVEL SECURITY;
    ALTER TABLE itens_documentos_pncp ENABLE ROW LEVEL SECURITY;
    ALTER TABLE classificacoes_itens ENABLE ROW LEVEL SECURITY;
    ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
    """
    
    try:
        # Executar SQLs de criação
        print("📋 Criando tabela documentos_pncp...")
        supabase.rpc('execute_sql', {'sql': create_documentos_sql}).execute()
        
        print("📋 Criando tabela itens_documentos_pncp...")
        supabase.rpc('execute_sql', {'sql': create_itens_sql}).execute()
        
        print("📋 Criando tabela classificacoes_itens...")
        supabase.rpc('execute_sql', {'sql': create_classificacoes_sql}).execute()
        
        print("📋 Criando tabela categorias...")
        supabase.rpc('execute_sql', {'sql': create_categorias_sql}).execute()
        
        print("📈 Criando índices...")
        supabase.rpc('execute_sql', {'sql': create_indexes_sql}).execute()
        
        print("🔒 Habilitando Row Level Security...")
        supabase.rpc('execute_sql', {'sql': enable_rls_sql}).execute()
        
        print("✅ Setup do banco de dados concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante o setup: {e}")
        raise

def main():
    """Função principal"""
    print("🚀 GovGo V1 - Setup do Banco de Dados")
    print("=" * 50)
    
    try:
        setup_supabase_tables()
        print("\n🎉 Banco de dados configurado com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Falha no setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
