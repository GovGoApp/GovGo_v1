
#!/usr/bin/env python3
"""
GovGo V1 - Setup do Banco de Dados V1 (clean, camelCase, V0-faithful)
Cria apenas as tabelas aprovadas, campos e tipos conforme db/table_schemas.py
"""

import os
import psycopg2
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

def connect():
    try:
        conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            database=os.getenv("SUPABASE_DBNAME"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=int(os.getenv("SUPABASE_PORT", "5432"))
        )
        console.print("✅ Conectado ao Supabase com sucesso!")
        return conn
    except Exception as e:
        console.print(f"❌ Erro ao conectar: {e}")
        return None

def run_sql(conn, sql, label):
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            conn.commit()
            console.print(f"✅ {label}")
    except Exception as e:
        console.print(f"❌ {label}: {e}")
        raise

def main():
    conn = connect()
    if not conn:
        return

    # Habilitar extensão vector
    run_sql(conn, "CREATE EXTENSION IF NOT EXISTS vector;", "Extensão 'vector' habilitada")

    # Tabela categoria fiel ao v0/v1
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS categoria (
            id_categoria BIGSERIAL PRIMARY KEY,
            cod_cat TEXT UNIQUE NOT NULL,
            nom_cat TEXT,
            cod_nv0 TEXT,
            nom_nv0 TEXT,
            cod_nv1 TEXT,
            nom_nv1 TEXT,
            cod_nv2 TEXT,
            nom_nv2 TEXT,
            cod_nv3 TEXT,
            nom_nv3 TEXT,
            cat_embeddings vector(3072),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_categoria_cod_cat ON categoria(cod_cat);
        CREATE INDEX IF NOT EXISTS idx_categoria_nom_cat ON categoria(nom_cat);
        CREATE INDEX IF NOT EXISTS idx_categoria_cod_nv0 ON categoria(cod_nv0);
        CREATE INDEX IF NOT EXISTS idx_categoria_cod_nv1 ON categoria(cod_nv1);
        -- Não criar índice hnsw para cat_embeddings (>2000 dimensões)
    ''', "Tabela 'categoria' criada")

    # Tabela contratacao fiel ao DBL/v1
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS contratacao (
            id_contratacao BIGSERIAL PRIMARY KEY,
            numero_controle_pncp TEXT UNIQUE,
            modo_disputa_id TEXT,
            amparo_legal_codigo TEXT,
            data_abertura_proposta TEXT,
            data_encerramento_proposta TEXT,
            srp TEXT,
            orgao_entidade_cnpj TEXT,
            orgao_entidade_razao_social TEXT,
            orgao_entidade_poder_id TEXT,
            orgao_entidade_esfera_id TEXT,
            ano_compra TEXT,
            sequencial_compra TEXT,
            processo TEXT,
            objeto_compra TEXT,
            valor_total_homologado DECIMAL(15,2),
            data_inclusao TEXT,
            data_publicacao_pncp TEXT,
            data_atualizacao TEXT,
            numero_compra TEXT,
            unidade_orgao_uf_nome TEXT,
            unidade_orgao_uf_sigla TEXT,
            unidade_orgao_municipio_nome TEXT,
            unidade_orgao_codigo_unidade TEXT,
            unidade_orgao_nome_unidade TEXT,
            unidade_orgao_codigo_ibge TEXT,
            modalidade_id TEXT,
            data_atualizacao_global TEXT,
            tipo_instrumento_convocatorio_codigo TEXT,
            valor_total_estimado TEXT,
            situacao_compra_id TEXT,
            cod_cat TEXT REFERENCES categoria(cod_cat),
            score DECIMAL(15,4),
            informacao_complementar TEXT,
            justificativa_presencial TEXT,
            link_sistema_origem TEXT,
            link_processo_eletronico TEXT,
            amparo_legal_nome TEXT,
            amparo_legal_descricao TEXT,
            modalidade_nome TEXT,
            modo_disputa_nome TEXT,
            tipo_instrumento_convocatorio_nome TEXT,
            situacao_compra_nome TEXT,
            existe_resultado BOOLEAN,
            orcamento_sigiloso_codigo INTEGER,
            orcamento_sigiloso_descricao TEXT,
            orgao_subrogado_cnpj TEXT,
            orgao_subrogado_razao_social TEXT,
            orgao_subrogado_poder_id TEXT,
            orgao_subrogado_esfera_id TEXT,
            unidade_subrogada_uf_nome TEXT,
            unidade_subrogada_uf_sigla TEXT,
            unidade_subrogada_municipio_nome TEXT,
            unidade_subrogada_codigo_unidade TEXT,
            unidade_subrogada_nome_unidade TEXT,
            unidade_subrogada_codigo_ibge TEXT,
            usuario_nome TEXT,
            fontes_orcamentarias TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_contratacao_numero_controle_pncp ON contratacao(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_contratacao_ano_compra ON contratacao(ano_compra);
        CREATE INDEX IF NOT EXISTS idx_contratacao_municipio ON contratacao(unidade_orgao_municipio_nome);
        CREATE INDEX IF NOT EXISTS idx_contratacao_uf ON contratacao(unidade_orgao_uf_sigla);
        CREATE INDEX IF NOT EXISTS idx_contratacao_modalidade ON contratacao(modalidade_id);
        CREATE INDEX IF NOT EXISTS idx_contratacao_valor ON contratacao(valor_total_estimado);
        CREATE INDEX IF NOT EXISTS idx_contratacao_cod_cat ON contratacao(cod_cat);
        CREATE INDEX IF NOT EXISTS idx_contratacao_objeto_gin ON contratacao USING gin(to_tsvector('portuguese', objeto_compra));
    ''', "Tabela 'contratacao' criada")

    # Tabela contrato fiel ao DBL/v1
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS contrato (
            id_contrato BIGSERIAL PRIMARY KEY,
            numero_controle_pncp_compra TEXT,
            numero_controle_pncp TEXT REFERENCES contratacao(numero_controle_pncp),
            numero_contrato_empenho TEXT,
            ano_contrato TEXT,
            data_assinatura TEXT,
            data_vigencia_inicio TEXT,
            data_vigencia_fim TEXT,
            ni_fornecedor TEXT,
            tipo_pessoa TEXT,
            sequencial_contrato TEXT,
            processo TEXT,
            nome_razao_social_fornecedor TEXT,
            numero_parcelas TEXT,
            numero_retificacao TEXT,
            objeto_contrato TEXT,
            valor_inicial DECIMAL(15,2),
            valor_parcela DECIMAL(15,2),
            valor_global DECIMAL(15,2),
            data_atualizacao_global TEXT,
            tipo_contrato_id TEXT,
            tipo_contrato_nome TEXT,
            orgao_entidade_cnpj TEXT,
            orgao_entidade_razaosocial TEXT,
            orgao_entidade_poder_id TEXT,
            orgao_entidade_esfera_id TEXT,
            categoria_processo_id TEXT,
            categoria_processo_nome TEXT,
            unidade_orgao_uf_nome TEXT,
            unidade_orgao_codigo_unidade TEXT,
            unidade_orgao_nome_unidade TEXT,
            unidade_orgao_uf_sigla TEXT,
            unidade_orgao_municipio_nome TEXT,
            unidade_orgao_codigo_ibge TEXT,
            vigencia_ano TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_contrato_numero_controle_pncp ON contrato(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_contrato_valor_global ON contrato(valor_global);
        CREATE INDEX IF NOT EXISTS idx_contrato_ano_contrato ON contrato(ano_contrato);
        CREATE INDEX IF NOT EXISTS idx_contrato_fornecedor_cnpj ON contrato(orgao_entidade_cnpj);
    ''', "Tabela 'contrato' criada")

    # Tabela item_contratacao
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS item_contratacao (
            id_item BIGSERIAL PRIMARY KEY,
            numero_controle_pncp TEXT REFERENCES contratacao(numero_controle_pncp),
            numero_item TEXT,
            descricao_item TEXT,
            material_ou_servico TEXT,
            valor_unitario_estimado DECIMAL(15,4),
            valor_total_estimado DECIMAL(15,4),
            quantidade_item DECIMAL(15,4),
            unidade_medida TEXT,
            item_categoria_id TEXT,
            item_categoria_nome TEXT,
            criterio_julgamento_id TEXT,
            situacao_item TEXT,
            tipo_beneficio TEXT,
            data_inclusao TEXT,
            data_atualizacao TEXT,
            ncm_nbs_codigo TEXT,
            catalogo TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_numero_controle_pncp ON item_contratacao(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_valor_total_estimado ON item_contratacao(valor_total_estimado);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_numero_item ON item_contratacao(numero_item);
    ''', "Tabela 'item_contratacao' criada")

    # Tabela item_classificacao
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS item_classificacao (
            id_item_classificacao BIGSERIAL PRIMARY KEY,
            numero_controle_pncp TEXT,
            numero_item TEXT,
            id_item TEXT,
            descricao TEXT,
            item_type TEXT,
            top_1 TEXT,
            top_2 TEXT,
            top_3 TEXT,
            top_4 TEXT,
            top_5 TEXT,
            score_1 DECIMAL(15,4),
            score_2 DECIMAL(15,4),
            score_3 DECIMAL(15,4),
            score_4 DECIMAL(15,4),
            score_5 DECIMAL(15,4),
            confidence DECIMAL(15,4),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_id_item ON item_classificacao(id_item);
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_numero_controle_pncp ON item_classificacao(numero_controle_pncp);
    ''', "Tabela 'item_classificacao' criada")

    # Tabela contratacao_emb fiel ao v0/v1
    run_sql(conn, '''
        CREATE TABLE IF NOT EXISTS contratacao_emb (
            id_contratacao_emb BIGSERIAL PRIMARY KEY,
            numero_controle_pncp TEXT REFERENCES contratacao(numero_controle_pncp),
            modelo_embedding TEXT,
            confidence DECIMAL(15,4),
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            top_categories TEXT[],
            top_similarities TEXT[],
            embeddings vector(3072)
        );
        CREATE INDEX IF NOT EXISTS idx_contratacao_emb_numero_controle_pncp ON contratacao_emb(numero_controle_pncp);
        -- Não criar índice hnsw para embeddings (>2000 dimensões)
    ''', "Tabela 'contratacao_emb' criada")

    conn.close()
    console.print("\n🎉 [bold green]Setup do banco de dados V1 concluído com sucesso![/bold green]")

if __name__ == "__main__":
    main()
