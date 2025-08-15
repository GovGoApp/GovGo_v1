"""
De-Para API PNCP → V1 (snake_case)
Mapeamento dos campos da API PNCP para o schema V1
Estrutura similar ao de_para_v0_v1.py para manter consistência
"""

# ============================
# FUNÇÕES DE TRANSFORMAÇÃO DE TIPOS (compartilhadas)
# ============================

def transform_to_integer(value):
    """Converte valores para integer, retorna None para vazios/nulos"""
    if value == '' or value is None:
        return None
    try:
        return int(float(value))  # float primeiro para casos como "1.0" → 1
    except (ValueError, TypeError):
        return None

def transform_to_decimal(value):
    """Converte valores para decimal/float, retorna None para vazios/nulos ou valores muito grandes"""
    if value == '' or value is None:
        return None
    try:
        decimal_value = float(value)
        # PostgreSQL NUMERIC(15,4) máximo: 10^11 (99999999999.9999)
        if abs(decimal_value) > 99999999999:
            return None  # Retorna NULL para valores que excedem limite
        return decimal_value
    except (ValueError, TypeError):
        return None

def transform_to_boolean(value):
    """Converte valores para boolean, retorna None para vazios/nulos"""
    if value == '' or value is None:
        return None
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 't', 'sim']
    return bool(value)

def transform_fontes_orcamentarias(value):
    """Converte fontes orçamentárias para JSON string"""
    import json
    if isinstance(value, list) and value:
        try:
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        except:
            return str(value)
    return None

# Mapeamento de transformações por tipo
TRANSFORMATIONS = {
    'integer': transform_to_integer,
    'decimal': transform_to_decimal,
    'boolean': transform_to_boolean,
    'json': transform_fontes_orcamentarias,
}

# ============================
# MAPEAMENTOS API PNCP → V1
# ============================

DE_PARA_PNCP = {
    'contratacao': {
        'fonte': 'API_PNCP',
        'origem': 'contratacoes/publicacao',
        'destino': 'contratacao',
        'campos': [
            # Campos básicos
            ('numeroControlePNCP', 'numero_controle_pncp'),
            ('modoDisputaId', 'modo_disputa_id'),
            ('dataAberturaProposta', 'data_abertura_proposta'),
            ('dataEncerramentoProposta', 'data_encerramento_proposta'),
            ('srp', 'srp'),
            ('anoCompra', 'ano_compra'),
            ('sequencialCompra', 'sequencial_compra'),
            ('processo', 'processo'),
            ('objetoCompra', 'objeto_compra'),
            ('valorTotalHomologado', 'valor_total_homologado', 'decimal'),
            ('dataInclusao', 'data_inclusao'),
            ('dataPublicacaoPncp', 'data_publicacao_pncp'),
            ('dataAtualizacao', 'data_atualizacao'),
            ('numeroCompra', 'numero_compra'),
            ('modalidadeId', 'modalidade_id'),
            ('dataAtualizacaoGlobal', 'data_atualizacao_global'),
            ('tipoInstrumentoConvocatorioCodigo', 'tipo_instrumento_convocatorio_codigo'),
            ('valorTotalEstimado', 'valor_total_estimado'),
            ('situacaoCompraId', 'situacao_compra_id'),
            ('informacaoComplementar', 'informacao_complementar'),
            ('justificativaPresencial', 'justificativa_presencial'),
            ('linkSistemaOrigem', 'link_sistema_origem'),
            ('linkProcessoEletronico', 'link_processo_eletronico'),
            ('modalidadeNome', 'modalidade_nome'),
            ('modoDisputaNome', 'modo_disputa_nome'),
            ('tipoInstrumentoConvocatorioNome', 'tipo_instrumento_convocatorio_nome'),
            ('situacaoCompraNome', 'situacao_compra_nome'),
            ('existeResultado', 'existe_resultado', 'boolean'),
            ('orcamentoSigilosoCodigo', 'orcamento_sigiloso_codigo', 'integer'),
            ('orcamentoSigilosoDescricao', 'orcamento_sigiloso_descricao'),
            ('usuarioNome', 'usuario_nome'),
            ('fontesOrcamentarias', 'fontes_orcamentarias', 'json'),
            
            # Campos aninhados - Amparo Legal
            ('amparoLegal.codigo', 'amparo_legal_codigo'),
            ('amparoLegal.nome', 'amparo_legal_nome'),
            ('amparoLegal.descricao', 'amparo_legal_descricao'),
            
            # Campos aninhados - Órgão Entidade
            ('orgaoEntidade.cnpj', 'orgao_entidade_cnpj'),
            ('orgaoEntidade.razaoSocial', 'orgao_entidade_razao_social'),
            ('orgaoEntidade.poderId', 'orgao_entidade_poder_id'),
            ('orgaoEntidade.esferaId', 'orgao_entidade_esfera_id'),
            
            # Campos aninhados - Unidade Órgão
            ('unidadeOrgao.ufNome', 'unidade_orgao_uf_nome'),
            ('unidadeOrgao.ufSigla', 'unidade_orgao_uf_sigla'),
            ('unidadeOrgao.municipioNome', 'unidade_orgao_municipio_nome'),
            ('unidadeOrgao.codigoUnidade', 'unidade_orgao_codigo_unidade'),
            ('unidadeOrgao.nomeUnidade', 'unidade_orgao_nome_unidade'),
            ('unidadeOrgao.codigoIbge', 'unidade_orgao_codigo_ibge'),
            
            # Campos aninhados - Órgão Sub-rogado
            ('orgaoSubRogado.cnpj', 'orgao_subrogado_cnpj'),
            ('orgaoSubRogado.razaoSocial', 'orgao_subrogado_razao_social'),
            ('orgaoSubRogado.poderId', 'orgao_subrogado_poder_id'),
            ('orgaoSubRogado.esferaId', 'orgao_subrogado_esfera_id'),
            
            # Campos aninhados - Unidade Sub-rogada
            ('unidadeSubRogada.ufNome', 'unidade_subrogada_uf_nome'),
            ('unidadeSubRogada.ufSigla', 'unidade_subrogada_uf_sigla'),
            ('unidadeSubRogada.municipioNome', 'unidade_subrogada_municipio_nome'),
            ('unidadeSubRogada.codigoUnidade', 'unidade_subrogada_codigo_unidade'),
            ('unidadeSubRogada.nomeUnidade', 'unidade_subrogada_nome_unidade'),
            ('unidadeSubRogada.codigoIbge', 'unidade_subrogada_codigo_ibge'),
        ]
    },
    'item_contratacao': {
        'fonte': 'API_PNCP',
        'origem': 'orgaos/{cnpj}/compras/{ano}/{sequencial}/itens',
        'destino': 'item_contratacao',
        'campos': [
            # Campo de referência (adicionado automaticamente)
            # ('numero_controle_pncp', 'numero_controle_pncp'),  # Injetado pelo script
            
            # Campos básicos do item
            ('numeroItem', 'numero_item'),
            ('descricao', 'descricao_item'),
            ('materialOuServico', 'material_ou_servico'),
            ('valorUnitarioEstimado', 'valor_unitario_estimado', 'decimal'),
            ('valorTotal', 'valor_total_estimado', 'decimal'),
            ('quantidade', 'quantidade_item', 'decimal'),
            ('unidadeMedida', 'unidade_medida'),
            ('itemCategoriaId', 'item_categoria_id'),
            ('itemCategoriaNome', 'item_categoria_nome'),
            ('criterioJulgamentoId', 'criterio_julgamento_id'),
            ('situacaoCompraItem', 'situacao_item'),
            ('tipoBeneficio', 'tipo_beneficio'),
            ('dataInclusao', 'data_inclusao'),
            ('dataAtualizacao', 'data_atualizacao'),
            ('ncmNbsCodigo', 'ncm_nbs_codigo'),
            ('catalogo', 'catalogo'),
        ]
    }
}

def get_nested_value(data, key_path):
    """Obtém valor aninhado usando notação de ponto (ex: 'orgaoEntidade.cnpj')"""
    if '.' not in key_path:
        return data.get(key_path)
    
    keys = key_path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value

def apply_field_transformation(api_data, table_key, numero_controle_pncp=None):
    """
    Aplica as transformações de campos da API PNCP para o formato V1
    
    Args:
        api_data: Dados originais da API PNCP
        table_key: Chave da tabela ('contratacao' ou 'item_contratacao')
        numero_controle_pncp: Para itens, o número de controle da contratação pai
    
    Returns:
        dict: Dados transformados prontos para inserção no banco V1
    """
    if table_key not in DE_PARA_PNCP:
        raise ValueError(f"Tabela '{table_key}' não encontrada no mapeamento PNCP")
    
    config = DE_PARA_PNCP[table_key]
    transformed_data = {}
    
    # Para itens, adicionar o campo de referência
    if table_key == 'item_contratacao' and numero_controle_pncp:
        transformed_data['numero_controle_pncp'] = numero_controle_pncp
    
    # Processar cada campo do mapeamento
    for field_config in config['campos']:
        if len(field_config) == 2:
            api_field, db_field = field_config
            transformation = None
        elif len(field_config) == 3:
            api_field, db_field, transformation = field_config
        else:
            continue
        
        # Obter valor da API (pode ser aninhado)
        value = get_nested_value(api_data, api_field)
        
        # Aplicar transformação se especificada
        if transformation and transformation in TRANSFORMATIONS:
            value = TRANSFORMATIONS[transformation](value)
        
        transformed_data[db_field] = value
    
    return transformed_data

def get_table_fields(table_key):
    """Retorna a lista de campos de destino para uma tabela"""
    if table_key not in DE_PARA_PNCP:
        return []
    
    config = DE_PARA_PNCP[table_key]
    fields = []
    
    # Para itens, adicionar campo de referência
    if table_key == 'item_contratacao':
        fields.append('numero_controle_pncp')
    
    # Adicionar campos do mapeamento
    for field_config in config['campos']:
        if len(field_config) >= 2:
            fields.append(field_config[1])  # db_field
    
    return fields

def get_api_endpoint_info(table_key):
    """Retorna informações sobre o endpoint da API para uma tabela"""
    if table_key not in DE_PARA_PNCP:
        return None
    
    config = DE_PARA_PNCP[table_key]
    return {
        'fonte': config['fonte'],
        'origem': config['origem'],
        'destino': config['destino']
    }
