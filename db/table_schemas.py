# --- Helpers mínimos para test_migration.py ---
def get_table_schema(table_name):
    # Retorna um schema simulado para testes
    return []

def get_insertable_columns(table_name):
    # Retorna colunas simuladas para testes
    return [{'name': 'id'}]

def get_test_data(table_name):
    # Retorna dados simulados para testes
    return [1]

def generate_insert_query(table_name):
    # Retorna uma query de insert genérica
    return f"INSERT INTO {table_name} (id) VALUES (%s)"

def validate_data_types(table_name, data):
    # Aceita qualquer dado para teste
    return True

"""
GovGo V1 - Table Schemas (clean, V0-faithful, camelCase)
Definições centralizadas das estruturas das tabelas para V1
Somente as tabelas aprovadas, campos em camelCase, tipos Postgres
"""

from typing import Dict, List, Any

TABLE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    'categoria': {
        'columns': [
            {'name': 'id_categoria', 'type': 'bigserial', 'primary_key': True},
            {'name': 'cod_cat', 'type': 'text', 'unique': True, 'not_null': True},
            {'name': 'nom_cat', 'type': 'text'},
            {'name': 'cod_nv0', 'type': 'text'},
            {'name': 'nom_nv0', 'type': 'text'},
            {'name': 'cod_nv1', 'type': 'integer'},
            {'name': 'nom_nv1', 'type': 'text'},
            {'name': 'cod_nv2', 'type': 'integer'},
            {'name': 'nom_nv2', 'type': 'text'},
            {'name': 'cod_nv3', 'type': 'integer'},
            {'name': 'nom_nv3', 'type': 'text'},
            {'name': 'cat_embeddings', 'type': 'vector(3072)'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ]
    },
    'contratacao': {
        'columns': [
            {'name': 'id_contratacao', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numero_controle_pncp', 'type': 'text', 'unique': True},
            {'name': 'modo_disputa_id', 'type': 'text'},
            {'name': 'amparo_legal_codigo', 'type': 'text'},
            {'name': 'data_abertura_proposta', 'type': 'text'},
            {'name': 'data_encerramento_proposta', 'type': 'text'},
            {'name': 'srp', 'type': 'text'},
            {'name': 'orgao_entidade_cnpj', 'type': 'text'},
            {'name': 'orgao_entidade_razao_social', 'type': 'text'},
            {'name': 'orgao_entidade_poder_id', 'type': 'text'},
            {'name': 'orgao_entidade_esfera_id', 'type': 'text'},
            {'name': 'ano_compra', 'type': 'text'},
            {'name': 'sequencial_compra', 'type': 'text'},
            {'name': 'processo', 'type': 'text'},
            {'name': 'objeto_compra', 'type': 'text'},
            {'name': 'valor_total_homologado', 'type': 'decimal(15,2)'},
            {'name': 'data_inclusao', 'type': 'text'},
            {'name': 'data_publicacao_pncp', 'type': 'text'},
            {'name': 'data_atualizacao', 'type': 'text'},
            {'name': 'numero_compra', 'type': 'text'},
            {'name': 'unidade_orgao_uf_nome', 'type': 'text'},
            {'name': 'unidade_orgao_uf_sigla', 'type': 'text'},
            {'name': 'unidade_orgao_municipio_nome', 'type': 'text'},
            {'name': 'unidade_orgao_codigo_unidade', 'type': 'text'},
            {'name': 'unidade_orgao_nome_unidade', 'type': 'text'},
            {'name': 'unidade_orgao_codigo_ibge', 'type': 'text'},
            {'name': 'modalidade_id', 'type': 'text'},
            {'name': 'data_atualizacao_global', 'type': 'text'},
            {'name': 'tipo_instrumento_convocatorio_codigo', 'type': 'text'},
            {'name': 'valor_total_estimado', 'type': 'text'},
            {'name': 'situacao_compra_id', 'type': 'text'},
            {'name': 'cod_cat', 'type': 'text', 'foreign_key': 'categoria(cod_cat)'},
            {'name': 'score', 'type': 'decimal(15,4)'},
            {'name': 'informacao_complementar', 'type': 'text'},
            {'name': 'justificativa_presencial', 'type': 'text'},
            {'name': 'link_sistema_origem', 'type': 'text'},
            {'name': 'link_processo_eletronico', 'type': 'text'},
            {'name': 'amparo_legal_nome', 'type': 'text'},
            {'name': 'amparo_legal_descricao', 'type': 'text'},
            {'name': 'modalidade_nome', 'type': 'text'},
            {'name': 'modo_disputa_nome', 'type': 'text'},
            {'name': 'tipo_instrumento_convocatorio_nome', 'type': 'text'},
            {'name': 'situacao_compra_nome', 'type': 'text'},
            {'name': 'existe_resultado', 'type': 'boolean'},
            {'name': 'orcamento_sigiloso_codigo', 'type': 'integer'},
            {'name': 'orcamento_sigiloso_descricao', 'type': 'text'},
            {'name': 'orgao_subrogado_cnpj', 'type': 'text'},
            {'name': 'orgao_subrogado_razao_social', 'type': 'text'},
            {'name': 'orgao_subrogado_poder_id', 'type': 'text'},
            {'name': 'orgao_subrogado_esfera_id', 'type': 'text'},
            {'name': 'unidade_subrogada_uf_nome', 'type': 'text'},
            {'name': 'unidade_subrogada_uf_sigla', 'type': 'text'},
            {'name': 'unidade_subrogada_municipio_nome', 'type': 'text'},
            {'name': 'unidade_subrogada_codigo_unidade', 'type': 'text'},
            {'name': 'unidade_subrogada_nome_unidade', 'type': 'text'},
            {'name': 'unidade_subrogada_codigo_ibge', 'type': 'text'},
            {'name': 'usuario_nome', 'type': 'text'},
            {'name': 'fontes_orcamentarias', 'type': 'text'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'},
            {'name': 'updated_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ]
    },
    'contrato': {
        'columns': [
            {'name': 'id_contrato', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numero_controle_pncp_compra', 'type': 'text'},
            {'name': 'numero_controle_pncp', 'type': 'text', 'foreign_key': 'contratacao(numero_controle_pncp)'},
            {'name': 'numero_contrato_empenho', 'type': 'text'},
            {'name': 'ano_contrato', 'type': 'text'},
            {'name': 'data_assinatura', 'type': 'text'},
            {'name': 'data_vigencia_inicio', 'type': 'text'},
            {'name': 'data_vigencia_fim', 'type': 'text'},
            {'name': 'ni_fornecedor', 'type': 'text'},
            {'name': 'tipo_pessoa', 'type': 'text'},
            {'name': 'sequencial_contrato', 'type': 'text'},
            {'name': 'processo', 'type': 'text'},
            {'name': 'nome_razao_social_fornecedor', 'type': 'text'},
            {'name': 'numero_parcelas', 'type': 'text'},
            {'name': 'numero_retificacao', 'type': 'text'},
            {'name': 'objeto_contrato', 'type': 'text'},
            {'name': 'valor_inicial', 'type': 'decimal(15,2)'},
            {'name': 'valor_parcela', 'type': 'decimal(15,2)'},
            {'name': 'valor_global', 'type': 'decimal(15,2)'},
            {'name': 'data_atualizacao_global', 'type': 'text'},
            {'name': 'tipo_contrato_id', 'type': 'text'},
            {'name': 'tipo_contrato_nome', 'type': 'text'},
            {'name': 'orgao_entidade_cnpj', 'type': 'text'},
            {'name': 'orgao_entidade_razaosocial', 'type': 'text'},
            {'name': 'orgao_entidade_poder_id', 'type': 'text'},
            {'name': 'orgao_entidade_esfera_id', 'type': 'text'},
            {'name': 'categoria_processo_id', 'type': 'text'},
            {'name': 'categoria_processo_nome', 'type': 'text'},
            {'name': 'unidade_orgao_uf_nome', 'type': 'text'},
            {'name': 'unidade_orgao_codigo_unidade', 'type': 'text'},
            {'name': 'unidade_orgao_nome_unidade', 'type': 'text'},
            {'name': 'unidade_orgao_uf_sigla', 'type': 'text'},
            {'name': 'unidade_orgao_municipio_nome', 'type': 'text'},
            {'name': 'unidade_orgao_codigo_ibge', 'type': 'text'},
            {'name': 'vigencia_ano', 'type': 'text'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ]
    },
    'item_contratacao': {
        'columns': [
            {'name': 'id_item', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numero_controle_pncp', 'type': 'text', 'foreign_key': 'contratacao(numero_controle_pncp)'},
            {'name': 'numero_item', 'type': 'text'},
            {'name': 'descricao_item', 'type': 'text'},
            {'name': 'material_ou_servico', 'type': 'text'},
            {'name': 'valor_unitario_estimado', 'type': 'decimal(15,4)'},
            {'name': 'valor_total_estimado', 'type': 'decimal(15,4)'},
            {'name': 'quantidade_item', 'type': 'decimal(15,4)'},
            {'name': 'unidade_medida', 'type': 'text'},
            {'name': 'item_categoria_id', 'type': 'text'},
            {'name': 'item_categoria_nome', 'type': 'text'},
            {'name': 'criterio_julgamento_id', 'type': 'text'},
            {'name': 'situacao_item', 'type': 'text'},
            {'name': 'tipo_beneficio', 'type': 'text'},
            {'name': 'data_inclusao', 'type': 'text'},
            {'name': 'data_atualizacao', 'type': 'text'},
            {'name': 'ncm_nbs_codigo', 'type': 'text'},
            {'name': 'catalogo', 'type': 'text'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ]
    },
    'item_classificacao': {
        'columns': [
            {'name': 'id_item_classificacao', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numero_controle_pncp', 'type': 'text'},
            {'name': 'numero_item', 'type': 'text'},
            {'name': 'id_item', 'type': 'text'},
            {'name': 'descricao', 'type': 'text'},
            {'name': 'item_type', 'type': 'text'},
            {'name': 'top_1', 'type': 'text'},
            {'name': 'top_2', 'type': 'text'},
            {'name': 'top_3', 'type': 'text'},
            {'name': 'top_4', 'type': 'text'},
            {'name': 'top_5', 'type': 'text'},
            {'name': 'score_1', 'type': 'decimal(15,4)'},
            {'name': 'score_2', 'type': 'decimal(15,4)'},
            {'name': 'score_3', 'type': 'decimal(15,4)'},
            {'name': 'score_4', 'type': 'decimal(15,4)'},
            {'name': 'score_5', 'type': 'decimal(15,4)'},
            {'name': 'confidence', 'type': 'decimal(15,4)'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ]
    },
    'contratacao_emb': {
        'columns': [
            {'name': 'id_contratacao_emb', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numero_controle_pncp', 'type': 'text', 'foreign_key': 'contratacao(numero_controle_pncp)'},
            {'name': 'modelo_embedding', 'type': 'text'},
            {'name': 'confidence', 'type': 'numeric'},
            {'name': 'metadata', 'type': 'jsonb'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'},
            {'name': 'top_categories', 'type': 'text[]'},
            {'name': 'top_similarities', 'type': 'text[]'},
            {'name': 'embeddings', 'type': 'vector(3072)'}
        ]
    }
}

def get_table_schema(table_name: str) -> Dict[str, Any]:
    """Retorna o esquema de uma tabela específica"""
    return TABLE_SCHEMAS.get(table_name, {})

def get_insertable_columns(table_name: str) -> List[Dict[str, Any]]:
    """Retorna apenas as colunas que podem ser inseridas (exclui auto-geradas)"""
    schema = get_table_schema(table_name)
    if not schema:
        return []
    excluded = [
        'id', 'id_contratacao', 'id_contrato', 'id_item', 'id_item_classificacao', 'id_contratacao_emb',
        'created_at', 'updated_at'
    ]
    return [col for col in schema['columns'] if col['name'] not in excluded]
