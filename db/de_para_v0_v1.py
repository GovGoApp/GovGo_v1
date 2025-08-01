"""
De-Para DBL/v0 → v1 (snake_case)
Mapeamento fiel campo a campo para migração GovGo V1
"""

# ============================
# FUNÇÕES DE TRANSFORMAÇÃO DE TIPOS
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

# Mapeamento de transformações por tipo
TRANSFORMATIONS = {
    'integer': transform_to_integer,
    'decimal': transform_to_decimal,
    'boolean': transform_to_boolean,
}

DE_PARA = {
    'categoria': {
        'fonte': 'SUPABASE_v0',
        'origem': 'categorias',
        'destino': 'categoria',
        'campos': [
            ('codcat', 'cod_cat'),
            ('nomcat', 'nom_cat'),
            ('codnv0', 'cod_nv0'),
            ('nomnv0', 'nom_nv0'),
            ('codnv1', 'cod_nv1'),
            ('nomnv1', 'nom_nv1'),
            ('codnv2', 'cod_nv2'),
            ('nomnv2', 'nom_nv2'),
            ('codnv3', 'cod_nv3'),
            ('nomnv3', 'nom_nv3'),
            ('cat_embeddings', 'cat_embeddings'),
            # ('id', 'id_categoria'), # REMOVIDO: bigserial auto-gerado
            # ('created_at', 'created_at'), # REMOVIDO: timestamptz auto-gerado
        ]
    },
    'contratacao': {
        'fonte': 'SQLITE_v0',
        'origem': 'contratacao',
        'destino': 'contratacao',
        'campos': [
            # ('ID_CONTRATACAO', 'id_contratacao'), # REMOVIDO: bigserial auto-gerado
            ('numeroControlePNCP', 'numero_controle_pncp'),
            ('modoDisputaId', 'modo_disputa_id'),
            ('amparoLegal_codigo', 'amparo_legal_codigo'),
            ('dataAberturaProposta', 'data_abertura_proposta'),
            ('dataEncerramentoProposta', 'data_encerramento_proposta'),
            ('srp', 'srp'),
            ('orgaoEntidade_cnpj', 'orgao_entidade_cnpj'),
            ('orgaoEntidade_razaosocial', 'orgao_entidade_razao_social'),
            ('orgaoEntidade_poderId', 'orgao_entidade_poder_id'),
            ('orgaoEntidade_esferaId', 'orgao_entidade_esfera_id'),
            ('anoCompra', 'ano_compra'),
            ('sequencialCompra', 'sequencial_compra'),
            ('processo', 'processo'),
            ('objetoCompra', 'objeto_compra'),
            ('valorTotalHomologado', 'valor_total_homologado', 'decimal'),
            ('dataInclusao', 'data_inclusao'),
            ('dataPublicacaoPncp', 'data_publicacao_pncp'),
            ('dataAtualizacao', 'data_atualizacao'),
            ('numeroCompra', 'numero_compra'),
            ('unidadeOrgao_ufNome', 'unidade_orgao_uf_nome'),
            ('unidadeOrgao_ufSigla', 'unidade_orgao_uf_sigla'),
            ('unidadeOrgao_municipioNome', 'unidade_orgao_municipio_nome'),
            ('unidadeOrgao_codigoUnidade', 'unidade_orgao_codigo_unidade'),
            ('unidadeOrgao_nomeUnidade', 'unidade_orgao_nome_unidade'),
            ('unidadeOrgao_codigoIbge', 'unidade_orgao_codigo_ibge'),
            ('modalidadeId', 'modalidade_id'),
            ('dataAtualizacaoGlobal', 'data_atualizacao_global'),
            ('tipoInstrumentoConvocatorioCodigo', 'tipo_instrumento_convocatorio_codigo'),
            ('valorTotalEstimado', 'valor_total_estimado'),
            ('situacaoCompraId', 'situacao_compra_id'),
            ('CODCAT', 'cod_cat'),
            ('SCORE', 'score', 'decimal'),
            ('informacaoComplementar', 'informacao_complementar'),
            ('justificativaPresencial', 'justificativa_presencial'),
            ('linkSistemaOrigem', 'link_sistema_origem'),
            ('linkProcessoEletronico', 'link_processo_eletronico'),
            ('amparoLegal_nome', 'amparo_legal_nome'),
            ('amparoLegal_descricao', 'amparo_legal_descricao'),
            ('modalidadeNome', 'modalidade_nome'),
            ('modoDisputaNome', 'modo_disputa_nome'),
            ('tipoInstrumentoConvocatorioNome', 'tipo_instrumento_convocatorio_nome'),
            ('situacaoCompraNome', 'situacao_compra_nome'),
            ('existeResultado', 'existe_resultado', 'boolean'),
            ('orcamentoSigilosoCodigo', 'orcamento_sigiloso_codigo', 'integer'),
            ('orcamentoSigilosoDescricao', 'orcamento_sigiloso_descricao'),
            ('orgaoSubRogado_cnpj', 'orgao_subrogado_cnpj'),
            ('orgaoSubRogado_razaoSocial', 'orgao_subrogado_razao_social'),
            ('orgaoSubRogado_poderId', 'orgao_subrogado_poder_id'),
            ('orgaoSubRogado_esferaId', 'orgao_subrogado_esfera_id'),
            ('unidadeSubRogada_ufNome', 'unidade_subrogada_uf_nome'),
            ('unidadeSubRogada_ufSigla', 'unidade_subrogada_uf_sigla'),
            ('unidadeSubRogada_municipioNome', 'unidade_subrogada_municipio_nome'),
            ('unidadeSubRogada_codigoUnidade', 'unidade_subrogada_codigo_unidade'),
            ('unidadeSubRogada_nomeUnidade', 'unidade_subrogada_nome_unidade'),
            ('unidadeSubRogada_codigoIbge', 'unidade_subrogada_codigo_ibge'),
            ('usuarioNome', 'usuario_nome'),
            ('fontesOrcamentarias', 'fontes_orcamentarias'),
        ]
    },
    'contrato': {
        'fonte': 'SQLITE_v0',
        'origem': 'contrato',
        'destino': 'contrato',
        'campos': [
            #('ID_CONTRATO', 'id_contrato'),
            ('numeroControlePncpCompra', 'numero_controle_pncp_compra'),
            ('numeroControlePNCP', 'numero_controle_pncp'),
            ('numeroContratoEmpenho', 'numero_contrato_empenho'),
            ('anoContrato', 'ano_contrato'),
            ('dataAssinatura', 'data_assinatura'),
            ('dataVigenciaInicio', 'data_vigencia_inicio'),
            ('dataVigenciaFim', 'data_vigencia_fim'),
            ('niFornecedor', 'ni_fornecedor'),
            ('tipoPessoa', 'tipo_pessoa'),
            ('sequencialContrato', 'sequencial_contrato'),
            ('processo', 'processo'),
            ('nomeRazaoSocialFornecedor', 'nome_razao_social_fornecedor'),
            ('numeroParcelas', 'numero_parcelas'),
            ('numeroRetificacao', 'numero_retificacao'),
            ('objetoContrato', 'objeto_contrato'),
            ('valorInicial', 'valor_inicial'),
            ('valorParcela', 'valor_parcela'),
            ('valorGlobal', 'valor_global'),
            ('dataAtualizacaoGlobal', 'data_atualizacao_global'),
            ('tipoContrato_id', 'tipo_contrato_id'),
            ('tipoContrato_nome', 'tipo_contrato_nome'),
            ('orgaoEntidade_cnpj', 'orgao_entidade_cnpj'),
            ('orgaoEntidade_razaosocial', 'orgao_entidade_razaosocial'),
            ('orgaoEntidade_poderId', 'orgao_entidade_poder_id'),
            ('orgaoEntidade_esferaId', 'orgao_entidade_esfera_id'),
            ('categoriaProcesso_id', 'categoria_processo_id'),
            ('categoriaProcesso_nome', 'categoria_processo_nome'),
            ('unidadeOrgao_ufNome', 'unidade_orgao_uf_nome'),
            ('unidadeOrgao_codigoUnidade', 'unidade_orgao_codigo_unidade'),
            ('unidadeOrgao_nomeUnidade', 'unidade_orgao_nome_unidade'),
            ('unidadeOrgao_ufSigla', 'unidade_orgao_uf_sigla'),
            ('unidadeOrgao_municipioNome', 'unidade_orgao_municipio_nome'),
            ('unidadeOrgao_codigoIbge', 'unidade_orgao_codigo_ibge'),
            ('vigenciaAno', 'vigencia_ano'),
            ('created_at', 'created_at'),
        ]
    },
    'item_contratacao': {
        'fonte': 'SQLITE_v0',
        'origem': 'item_contratacao',
        'destino': 'item_contratacao',
        'campos': [
            #('ID_ITEM_CONTRATACAO', 'id_item'),
            ('numeroControlePNCP', 'numero_controle_pncp'),
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
    },
    'item_classificacao': {
        'fonte': 'SQLITE_v0',
        'origem': 'item_classificacao',
        'destino': 'item_classificacao',
        'campos': [
            #('ID', 'id_item_classificacao'),
            ('numeroControlePNCP', 'numero_controle_pncp'),
            ('numeroItem', 'numero_item'),
            ('ID_ITEM_CONTRATACAO', 'id_item'),
            ('descrição', 'descricao'),
            ('item_type', 'item_type'),
            ('TOP_1', 'top_1'),
            ('TOP_2', 'top_2'),
            ('TOP_3', 'top_3'),
            ('TOP_4', 'top_4'),
            ('TOP_5', 'top_5'),
            ('SCORE_1', 'score_1', 'decimal'),
            ('SCORE_2', 'score_2', 'decimal'),
            ('SCORE_3', 'score_3', 'decimal'),
            ('SCORE_4', 'score_4', 'decimal'),
            ('SCORE_5', 'score_5', 'decimal'),
            ('CONFIDENCE', 'confidence', 'decimal'),
        ]
    },
    'contratacoes_embeddings': {
        'fonte': 'SUPABASE_v0',
        'origem': 'contratacoes_embeddings',
        'destino': 'contratacao_emb',
        'campos': [
            #('id', 'id_contratacao_emb'),
            ('numerocontrolepncp', 'numero_controle_pncp'),
            ('embedding_vector', 'embeddings'),
            ('modelo_embedding', 'modelo_embedding'),
            ('metadata', 'metadata'),
            ('created_at', 'created_at'),
            ('confidence', 'confidence'),
            ('top_categories', 'top_categories'),
            ('top_similarities', 'top_similarities'),
        ]
    },
}
