#!/usr/bin/env python3
"""
GovGo V1 - Esquemas das Tabelas Compartilhados
==============================================
Definições centralizadas das estruturas das tabelas
Baseado no 01_setup_database.py
"""

from typing import Dict, List, Any

# Estruturas das tabelas baseadas no 01_setup_database.py
TABLE_SCHEMAS = {
    'categoria': {
        'columns': [
            {'name': 'id', 'type': 'bigserial', 'primary_key': True},
            {'name': 'codcat', 'type': 'text', 'unique': True, 'not_null': True},
            {'name': 'nomcat', 'type': 'text'},
            {'name': 'codnv0', 'type': 'text'},
            {'name': 'nomnv0', 'type': 'text'},
            {'name': 'codnv1', 'type': 'text'},
            {'name': 'nomnv1', 'type': 'text'},
            {'name': 'codnv2', 'type': 'text'},
            {'name': 'nomnv2', 'type': 'text'},
            {'name': 'codnv3', 'type': 'text'},
            {'name': 'nomnv3', 'type': 'text'},
            {'name': 'cat_embeddings', 'type': 'vector(1536)'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ],
        'test_data': ['TEST001', 'Categoria Teste', 'CNV0001', 'Nível 0 Teste', 'CNV1001', 'Nível 1 Teste', 'CNV2001', 'Nível 2 Teste', 'CNV3001', 'Nível 3 Teste', [0.1]*1536]
    },
    
    'contratacao': {
        'columns': [
            {'name': 'id_contratacao', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numerocontrolepncp', 'type': 'text', 'unique': True},
            {'name': 'modadisputaid', 'type': 'text'},
            {'name': 'amparolegal_codigo', 'type': 'text'},
            {'name': 'dataaberturaproposta', 'type': 'text'},
            {'name': 'dataencerramentoproposta', 'type': 'text'},
            {'name': 'srp', 'type': 'text'},
            {'name': 'orgaoentidade_cnpj', 'type': 'text'},
            {'name': 'orgaoentidade_razaosocial', 'type': 'text'},
            {'name': 'orgaoentidade_poderid', 'type': 'text'},
            {'name': 'orgaoentidade_esferaid', 'type': 'text'},
            {'name': 'anocompra', 'type': 'text'},
            {'name': 'sequencialcompra', 'type': 'text'},
            {'name': 'processo', 'type': 'text'},
            {'name': 'objetocompra', 'type': 'text'},
            {'name': 'valortotalhomologado', 'type': 'decimal(15,2)'},
            {'name': 'datainclusao', 'type': 'text'},
            {'name': 'datapublicacaopncp', 'type': 'text'},
            {'name': 'dataatualizacao', 'type': 'text'},
            {'name': 'numerocompra', 'type': 'text'},
            {'name': 'unidadeorgao_ufnome', 'type': 'text'},
            {'name': 'unidadeorgao_ufsigla', 'type': 'text'},
            {'name': 'unidadeorgao_municipionome', 'type': 'text'},
            {'name': 'unidadeorgao_codigounidade', 'type': 'text'},
            {'name': 'unidadeorgao_nomeunidade', 'type': 'text'},
            {'name': 'unidadeorgao_codigoibge', 'type': 'text'},
            {'name': 'modalidadeid', 'type': 'text'},
            {'name': 'dataatualizacaoglobal', 'type': 'text'},
            {'name': 'tipoinstrumentoconvocatoriocodigo', 'type': 'text'},
            {'name': 'valortotalestimado', 'type': 'text'},
            {'name': 'situacaocompraid', 'type': 'text'},
            {'name': 'codcat', 'type': 'text', 'foreign_key': 'categoria(codcat)'},
            {'name': 'score', 'type': 'decimal(6,4)'},
            {'name': 'informacaocomplementar', 'type': 'text'},
            {'name': 'justificativapresencial', 'type': 'text'},
            {'name': 'linksistemaorigem', 'type': 'text'},
            {'name': 'linkprocessoeletronico', 'type': 'text'},
            {'name': 'amparolegal_nome', 'type': 'text'},
            {'name': 'amparolegal_descricao', 'type': 'text'},
            {'name': 'modalidadenome', 'type': 'text'},
            {'name': 'modadisputanome', 'type': 'text'},
            {'name': 'tipoinstrumentoconvocatorionome', 'type': 'text'},
            {'name': 'situacaocompranome', 'type': 'text'},
            {'name': 'existeresultado', 'type': 'boolean'},
            {'name': 'orcamentosigilosocodigo', 'type': 'integer'},
            {'name': 'orcamentosigioso_descricao', 'type': 'text'},
            {'name': 'orgaosurogado_cnpj', 'type': 'text'},
            {'name': 'orgaosurogado_razaosocial', 'type': 'text'},
            {'name': 'orgaosurogado_poderid', 'type': 'text'},
            {'name': 'orgaosurogado_esferaid', 'type': 'text'},
            {'name': 'unidadesurogada_ufnome', 'type': 'text'},
            {'name': 'unidadesurogada_ufsigla', 'type': 'text'},
            {'name': 'unidadesurogada_municipionome', 'type': 'text'},
            {'name': 'unidadesurogada_codigounidade', 'type': 'text'},
            {'name': 'unidadesurogada_nomeunidade', 'type': 'text'},
            {'name': 'unidadesurogada_codigoibge', 'type': 'text'},
            {'name': 'usuarionome', 'type': 'text'},
            {'name': 'fontesorcamentarias', 'type': 'text'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'},
            {'name': 'updated_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ],
        'test_data': ['TEST123456789', '1', 'AMP001', '2024-01-01', '2024-01-15', 'S', '12345678901234', 'Órgão Teste LTDA', '1', '1', '2024', '001', 'PROC001', 'Aquisição de materiais de teste', 100.50, '2024-01-01', '2024-01-01', '2024-01-01', 'COMP001', 'Rio Grande do Norte', 'RN', 'Natal', 'UNI001', 'Unidade Teste', '240101001', 'MOD001', '2024-01-01', 'TIP001', '150.00', 'SIT001', 'TEST001', 0.85, 'Informação complementar teste', 'Justificativa teste', 'http://sistema.teste.com', 'http://processo.teste.com', 'Amparo Legal Teste', 'Descrição do amparo legal', 'Modalidade Teste', 'Modalidade Disputa Teste', 'Instrumento Teste', 'Situação Teste', True, 1, 'Orçamento público', '98765432101234', 'Órgão Surogado Teste', '2', '2', 'Estado Teste', 'ET', 'Cidade Teste', 'UNI002', 'Unidade Surogada Teste', '240102001', 'Usuario Teste', 'Fonte Orçamentária Teste']
    },
    
    'contratacao_emb': {
        'columns': [
            {'name': 'id_embedding', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numerocontrolepncp', 'type': 'text', 'foreign_key': 'contratacao(numerocontrolepncp)'},
            {'name': 'embedding', 'type': 'vector(1536)'},
            {'name': 'modelo_embedding', 'type': 'text'},
            {'name': 'data_processamento', 'type': 'timestamptz'},
            {'name': 'versao_modelo', 'type': 'text'},
            {'name': 'confidence', 'type': 'decimal(5,4)'},
            {'name': 'metadata', 'type': 'jsonb'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'},
            {'name': 'updated_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ],
        'test_data': ['TEST123456789', [0.1]*1536, 'text-embedding-3-large', '2024-01-01 10:00:00', 'v1.0', 0.95, '{"fonte": "teste"}']
    },
    
    'item_contratacao': {
        'columns': [
            {'name': 'id_item', 'type': 'bigserial', 'primary_key': True},
            {'name': 'numerocontrolepncp', 'type': 'text', 'foreign_key': 'contratacao(numerocontrolepncp)'},
            {'name': 'sequencialitem', 'type': 'integer'},
            {'name': 'descricaoitem', 'type': 'text'},
            {'name': 'quantidadeitem', 'type': 'decimal(15,4)'},
            {'name': 'unidademedida', 'type': 'text'},
            {'name': 'valorunitarioestimado', 'type': 'decimal(15,4)'},
            {'name': 'valortotalestimado', 'type': 'decimal(15,4)'},
            {'name': 'marcaitem', 'type': 'text'},
            {'name': 'situacaoitem', 'type': 'text'},
            {'name': 'beneficiostipo', 'type': 'text'},
            {'name': 'beneficiosdescricao', 'type': 'text'},
            {'name': 'incentivosprodu', 'type': 'text'},
            {'name': 'catmatservid', 'type': 'text'},
            {'name': 'catmatservnome', 'type': 'text'},
            {'name': 'sustentavelid', 'type': 'text'},
            {'name': 'sustentavelnome', 'type': 'text'},
            {'name': 'codigoclassificacaopdm', 'type': 'text'},
            {'name': 'codigoclassificacaocusteio', 'type': 'text'},
            {'name': 'created_at', 'type': 'timestamptz', 'default': 'CURRENT_TIMESTAMP'}
        ],
        'test_data': ['TEST123456789', 1, 'Item de teste para contratação', 10.0, 'UN', 50.25, 502.50, 'Marca Teste', 'ATIVO', 'BENEFICIO_TESTE', 'Descrição do benefício', 'INCENTIVO_TESTE', 'CAT001', 'Categoria Material Teste', 'SUST001', 'Sustentável Teste', 'PDM001', 'CUSTEIO001']
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
    
    # Excluir colunas auto-geradas
    excluded = ['id', 'id_contratacao', 'id_item', 'id_embedding', 'created_at', 'updated_at']
    
    return [col for col in schema['columns'] if col['name'] not in excluded]

def get_test_data(table_name: str) -> List[Any]:
    """Retorna dados de teste para uma tabela"""
    schema = get_table_schema(table_name)
    if not schema or 'test_data' not in schema:
        return []
    
    insertable_columns = get_insertable_columns(table_name)
    test_data = schema['test_data']
    
    # Ajustar dados de teste para o número de colunas inseríveis
    return test_data[:len(insertable_columns)]

def generate_insert_query(table_name: str) -> str:
    """Gera query de inserção para uma tabela"""
    insertable_columns = get_insertable_columns(table_name)
    if not insertable_columns:
        return ""
    
    column_names = [col['name'] for col in insertable_columns]
    placeholders = ','.join(['%s'] * len(column_names))
    
    return f"""
        INSERT INTO {table_name} ({','.join(column_names)})
        VALUES ({placeholders})
    """

def validate_data_types(table_name: str, data: List[Any]) -> bool:
    """Valida se os dados correspondem aos tipos esperados"""
    insertable_columns = get_insertable_columns(table_name)
    
    if len(data) != len(insertable_columns):
        return False
    
    for i, (value, col) in enumerate(zip(data, insertable_columns)):
        col_type = col['type'].lower()
        
        # Validações básicas de tipo
        if 'text' in col_type and not isinstance(value, str):
            return False
        elif 'integer' in col_type and not isinstance(value, int):
            return False
        elif 'decimal' in col_type and not isinstance(value, (int, float)):
            return False
        elif 'boolean' in col_type and not isinstance(value, bool):
            return False
        elif 'vector' in col_type and not isinstance(value, list):
            return False
        elif 'jsonb' in col_type and not isinstance(value, (str, dict)):
            return False
    
    return True
