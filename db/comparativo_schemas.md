# Comparativo de Schemas GovGo V0/DBL vs V1

## categoria
| V0/DBL                | V1           |
|-----------------------|--------------|
| CODCAT                | cod_cat      |
| NOMCAT                | nom_cat      |
| CODNV0                | cod_nv0      |
| NOMNV0                | nom_nv0      |
| CODNV1                | cod_nv1      |
| NOMNV1                | nom_nv1      |
| CODNV2                | cod_nv2      |
| NOMNV2                | nom_nv2      |
| CODNV3                | cod_nv3      |
| NOMNV3                | nom_nv3      |

## contratacao
| V0/DBL                    | V1                        |
|---------------------------|---------------------------|
| ID_CONTRATACAO            | id_contratacao            |
| numeroControlePNCP        | numero_controle_pncp      |
| modoDisputaId             | moda_disputa_id           |
| amparoLegal_codigo        | amparo_legal_codigo       |
| dataAberturaProposta      | data_abertura_proposta    |
| dataEncerramentoProposta  | data_encerramento_proposta|
| srp                       | srp                       |
| orgaoEntidade_cnpj        | orgao_entidade_cnpj       |
| orgaoEntidade_razaosocial | orgao_entidade_razao_social|
| orgaoEntidade_poderId     | orgao_entidade_poder_id   |
| orgaoEntidade_esferaId    | orgao_entidade_esfera_id  |
| anoCompra                 | ano_compra                |
| sequencialCompra          | sequencial_compra         |
| processo                  | processo                  |
| objetoCompra              | objeto_compra             |
| valorTotalHomologado      | valor_total_homologado    |
| dataInclusao              | data_inclusao             |
| dataPublicacaoPncp        | data_publicacao_pncp      |
| dataAtualizacao           | data_atualizacao          |
| numeroCompra              | numero_compra             |
| unidadeOrgao_ufNome       | unidade_orgao_uf_nome     |
| unidadeOrgao_ufSigla      | unidade_orgao_uf_sigla    |
| unidadeOrgao_municipioNome| unidade_orgao_municipio_nome|
| unidadeOrgao_codigoUnidade| unidade_orgao_codigo_unidade|
| unidadeOrgao_nomeUnidade  | unidade_orgao_nome_unidade|
| unidadeOrgao_codigoIbge   | unidade_orgao_codigo_ibge |
| modalidadeId              | modalidade_id             |
| dataAtualizacaoGlobal     | data_atualizacao_global   |
| tipoInstrumentoConvocatorioCodigo| tipo_instrumento_convocatorio_codigo|
| valorTotalEstimado        | valor_total_estimado      |
| situacaoCompraId          | situacao_compra_id        |
| CODCAT                    | cod_cat                   |
| SCORE                     | score                     |
| informacaoComplementar    | informacao_complementar   |
| justificativaPresencial   | justificativa_presencial  |
| linkSistemaOrigem         | link_sistema_origem       |
| linkProcessoEletronico    | link_processo_eletronico  |
| amparoLegal_nome          | amparo_legal_nome         |
| amparoLegal_descricao     | amparo_legal_descricao    |
| modalidadeNome            | modalidade_nome           |
| modoDisputaNome           | moda_disputa_nome         |
| tipoInstrumentoConvocatorioNome| tipo_instrumento_convocatorio_nome|
| situacaoCompraNome        | situacao_compra_nome      |
| existeResultado           | existe_resultado          |
| orcamentoSigilosoCodigo   | orcamento_sigiloso_codigo |
| orcamentoSigilosoDescricao| orcamento_sigiloso_descricao|
| orgaoSubRogado_cnpj       | orgao_surogado_cnpj       |
| orgaoSubRogado_razaoSocial| orgao_surogado_razao_social|
| orgaoSubRogado_poderId    | orgao_surogado_poder_id   |
| orgaoSubRogado_esferaId   | orgao_surogado_esfera_id  |
| unidadeSubRogada_ufNome   | unidade_surogada_uf_nome  |
| unidadeSubRogada_ufSigla  | unidade_surogada_uf_sigla |
| unidadeSubRogada_municipioNome| unidade_surogada_municipio_nome|
| unidadeSubRogada_codigoUnidade| unidade_surogada_codigo_unidade|
| unidadeSubRogada_nomeUnidade| unidade_surogada_nome_unidade|
| unidadeSubRogada_codigoIbge| unidade_surogada_codigo_ibge|
| usuarioNome               | usuario_nome              |
| fontesOrcamentarias       | fontes_orcamentarias      |

## item_classificacao
| V0/DBL                | V1                  |
|-----------------------|---------------------|
| ID                    | id_item_classificacao|
| numeroControlePNCP    | numero_controle_pncp|
| numeroItem            | numero_item         |
| ID_ITEM_CONTRATACAO   | id_item             |
| descrição             | descricao           |
| item_type             | item_type           |
| TOP_1                 | top_1               |
| TOP_2                 | top_2               |
| TOP_3                 | top_3               |
| TOP_4                 | top_4               |
| TOP_5                 | top_5               |
| SCORE_1               | score_1             |
| SCORE_2               | score_2             |
| SCORE_3               | score_3             |
| SCORE_4               | score_4             |
| SCORE_5               | score_5             |
| CONFIDENCE            | confidence          |
|                       | created_at          |

## item_contratacao
| V0/DBL                | V1                      |
|-----------------------|-------------------------|
| ID_ITEM_CONTRATACAO   | id_item                 |
| numeroControlePNCP    | numero_controle_pncp    |
| descricao             | descricao_item          |
| quantidade            | quantidade_item         |
| unidadeMedida         | unidade_medida          |
| valorUnitarioEstimado | valor_unitario_estimado |
| valorTotal            | valor_total_estimado    |
| marcaItem             | marca_item              |
| situacaoCompraItem    | situacao_item           |
| beneficiosTipo        | beneficios_tipo         |
| beneficiosDescricao   | beneficios_descricao    |
| incentivosProdu       | incentivos_produ        |
| catmatServId          | catmat_serv_id          |
| catmatServNome        | catmat_serv_nome        |
| sustentavelId         | sustentavel_id          |
| sustentavelNome       | sustentavel_nome        |
| codigoClassificacaoPdm| codigo_classificacao_pdm|
| codigoClassificacaoCusteio| codigo_classificacao_custeio|
| createdAt             | created_at              |

## contrato
| V0/DBL                | V1                      |
|-----------------------|-------------------------|
| ID_CONTRATO           | id_contrato             |
| numeroControlePNCP    | numero_controle_pncp    |
| numeroContratoEmpenho | numero_contrato         |
| dataAssinatura        | data_assinatura         |
| dataVigenciaInicio    | data_vigencia_inicio    |
| dataVigenciaFim       | data_vigencia_fim       |
| valorGlobal           | valor_total             |
| objetoContrato        | objeto_contrato         |
| orgaoEntidade_cnpj    | fornecedor_cnpj         |
| orgaoEntidade_razaosocial| fornecedor_razao_social|
| createdAt             | created_at              |

## contratacao_emb (embeddings)
| V0/DBL                | V1                      |
|-----------------------|-------------------------|
| id                    | id_contratacao_emb      |
| numerocontrolepncp    | numero_controle_pncp    |
| embedding_vector      | embeddings              |
| modelo_embedding      | modelo_embedding        |
| metadata              | metadata                |
| created_at            | created_at              |
| confidence            | confidence              |
| top_categories        | top_categories          |
| top_similarities      | top_similarities        |

