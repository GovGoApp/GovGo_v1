"""
GovGo V1 - Modelos de Dados
===========================

Define os modelos de dados baseados na estrutura existente do PNCP_DB_v2
e sistema Supabase atual, respeitando nomes e estruturas já estabelecidas.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

class TipoDocumento(str, Enum):
    """Tipos de documento PNCP - baseado na estrutura existente"""
    CONTRATACAO = "contratacao"
    CONTRATO = "contrato"
    ATA = "ata"
    PCA = "pca"

class StatusProcessamento(str, Enum):
    """Status de processamento"""
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    PROCESSADO = "processado"
    ERRO = "erro"

# ===============================
# MODELOS BASEADOS NA ESTRUTURA EXISTENTE PNCP_DB_v2
# ===============================

class Categoria(BaseModel):
    """Modelo para categorias - estrutura original do PNCP_DB_v2"""
    CODCAT: str = Field(..., description="Código da categoria")
    NOMCAT: str = Field(..., description="Nome da categoria")
    CODNV0: Optional[str] = Field(None, description="Código nível 0")
    NOMNV0: Optional[str] = Field(None, description="Nome nível 0")
    CODNV1: Optional[str] = Field(None, description="Código nível 1")
    NOMNV1: Optional[str] = Field(None, description="Nome nível 1")
    CODNV2: Optional[str] = Field(None, description="Código nível 2")
    NOMNV2: Optional[str] = Field(None, description="Nome nível 2")
    CODNV3: Optional[str] = Field(None, description="Código nível 3")
    NOMNV3: Optional[str] = Field(None, description="Nome nível 3")

class ContratacaoSupabase(BaseModel):
    """Modelo para contratações - baseado na estrutura atual do Supabase"""
    numeroControlePNCP: str = Field(..., description="Número de controle PNCP único")
    anoCompra: Optional[int] = Field(None, description="Ano da compra")
    sequencialCompra: Optional[int] = Field(None, description="Sequencial da compra")
    numeroCompra: Optional[str] = Field(None, description="Número da compra")
    processo: Optional[str] = Field(None, description="Número do processo")
    
    # Valores
    valorTotalEstimado: Optional[Decimal] = Field(None, description="Valor total estimado")
    valorTotalHomologado: Optional[Decimal] = Field(None, description="Valor total homologado")
    orcamentoSigilosoCodigo: Optional[str] = Field(None, description="Código orçamento sigiloso")
    orcamentoSigilosoDescricao: Optional[str] = Field(None, description="Descrição orçamento sigiloso")
    
    # Modalidade e disputa
    modalidadeId: Optional[int] = Field(None, description="ID da modalidade")
    modalidadeNome: Optional[str] = Field(None, description="Nome da modalidade")
    modoDisputaId: Optional[int] = Field(None, description="ID do modo de disputa")
    modoDisputaNome: Optional[str] = Field(None, description="Nome do modo de disputa")
    tipoInstrumentoConvocatorioCodigo: Optional[str] = Field(None, description="Código do instrumento")
    tipoInstrumentoConvocatorioNome: Optional[str] = Field(None, description="Nome do instrumento")
    
    # Amparo legal
    amparoLegal_codigo: Optional[str] = Field(None, description="Código amparo legal")
    amparoLegal_nome: Optional[str] = Field(None, description="Nome amparo legal")
    amparoLegal_descricao: Optional[str] = Field(None, description="Descrição amparo legal")
    
    # Objeto e informações
    objetoCompra: Optional[str] = Field(None, description="Objeto da compra")
    informacaoComplementar: Optional[str] = Field(None, description="Informações complementares")
    justificativaPresencial: Optional[str] = Field(None, description="Justificativa presencial")
    srp: Optional[int] = Field(None, description="Sistema de Registro de Preços")
    
    # Links
    linkSistemaOrigem: Optional[str] = Field(None, description="Link sistema origem")
    linkProcessoEletronico: Optional[str] = Field(None, description="Link processo eletrônico")
    
    # Situação
    situacaoCompraId: Optional[int] = Field(None, description="ID situação compra")
    situacaoCompraNome: Optional[str] = Field(None, description="Nome situação compra")
    existeResultado: Optional[int] = Field(None, description="Existe resultado")
    
    # Datas
    dataPublicacaoPncp: Optional[str] = Field(None, description="Data publicação PNCP")
    dataAberturaProposta: Optional[str] = Field(None, description="Data abertura proposta")
    dataEncerramentoProposta: Optional[str] = Field(None, description="Data encerramento proposta")
    dataInclusao: Optional[str] = Field(None, description="Data inclusão")
    
    # Órgão e entidade
    orgaoEntidade_razaoSocial: Optional[str] = Field(None, description="Razão social órgão")
    orgaoEntidade_nomeFantasia: Optional[str] = Field(None, description="Nome fantasia")
    orgaoEntidade_cnpj: Optional[str] = Field(None, description="CNPJ órgão")
    orgaoEntidade_municipio_nome: Optional[str] = Field(None, description="Município órgão")
    orgaoEntidade_municipio_ibge: Optional[str] = Field(None, description="IBGE município")
    orgaoEntidade_municipio_uf_sigla: Optional[str] = Field(None, description="UF sigla")
    orgaoEntidade_municipio_uf_nome: Optional[str] = Field(None, description="UF nome")
    orgaoEntidade_poder_codigo: Optional[int] = Field(None, description="Código poder")
    orgaoEntidade_poder_nome: Optional[str] = Field(None, description="Nome poder")
    orgaoEntidade_esferaId: Optional[int] = Field(None, description="ID esfera")
    orgaoEntidade_esfera: Optional[str] = Field(None, description="Esfera")
    
    # Unidade órgão
    unidadeOrgao_nome: Optional[str] = Field(None, description="Nome unidade")
    unidadeOrgao_codigoUnidade: Optional[str] = Field(None, description="Código unidade")
    unidadeOrgao_nomeUnidade: Optional[str] = Field(None, description="Nome unidade")
    unidadeOrgao_municipio_nome: Optional[str] = Field(None, description="Município unidade")
    unidadeOrgao_municipio_ibge: Optional[str] = Field(None, description="IBGE unidade")
    unidadeOrgao_municipio_uf_sigla: Optional[str] = Field(None, description="UF sigla unidade")
    unidadeOrgao_municipio_uf_nome: Optional[str] = Field(None, description="UF nome unidade")
    
    # Usuário
    usuarioNome: Optional[str] = Field(None, description="Nome usuário")
    usuarioId: Optional[int] = Field(None, description="ID usuário")
    
    # Campos específicos
    tipoRecurso: Optional[str] = Field(None, description="Tipo recurso")
    isSrp: Optional[int] = Field(None, description="É SRP")
    isOrcamentoSigiloso: Optional[int] = Field(None, description="É orçamento sigiloso")
    existeContratoAssociado: Optional[int] = Field(None, description="Existe contrato associado")
    
    # Descrição completa (campo derivado para busca)
    descricaoCompleta: Optional[str] = Field(None, description="Descrição completa")
    
    # Campos de controle
    created_at: Optional[datetime] = Field(None, description="Data criação")

class ContratacaoEmbedding(BaseModel):
    """Modelo para embeddings - baseado na estrutura atual do Supabase"""
    id: Optional[int] = Field(None, description="ID do embedding")
    numeroControlePNCP: str = Field(..., description="Número controle PNCP")
    embedding_vector: Optional[List[float]] = Field(None, description="Vetor embedding")
    modelo_embedding: Optional[str] = Field(None, description="Modelo usado")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados")
    created_at: Optional[datetime] = Field(None, description="Data criação")

class ContratoOriginal(BaseModel):
    """Modelo para contratos - baseado na estrutura original PNCP_DB_v2"""
    ID_CONTRATO: Optional[int] = Field(None, description="ID do contrato")
    numeroControlePncpCompra: Optional[str] = Field(None, description="Número controle PNCP compra")
    numeroControlePNCP: str = Field(..., description="Número controle PNCP")
    numeroContratoEmpenho: Optional[str] = Field(None, description="Número contrato empenho")
    anoContrato: Optional[str] = Field(None, description="Ano contrato")
    dataAssinatura: Optional[str] = Field(None, description="Data assinatura")
    dataVigenciaInicio: Optional[str] = Field(None, description="Data início vigência")
    dataVigenciaFim: Optional[str] = Field(None, description="Data fim vigência")
    niFornecedor: Optional[str] = Field(None, description="NI fornecedor")
    tipoPessoa: Optional[str] = Field(None, description="Tipo pessoa")
    sequencialContrato: Optional[str] = Field(None, description="Sequencial contrato")
    processo: Optional[str] = Field(None, description="Processo")
    nomeRazaoSocialFornecedor: Optional[str] = Field(None, description="Nome fornecedor")
    numeroParcelas: Optional[str] = Field(None, description="Número parcelas")
    numeroRetificacao: Optional[str] = Field(None, description="Número retificação")
    objetoContrato: Optional[str] = Field(None, description="Objeto contrato")
    valorInicial: Optional[Decimal] = Field(None, description="Valor inicial")
    valorParcela: Optional[Decimal] = Field(None, description="Valor parcela")
    valorGlobal: Optional[Decimal] = Field(None, description="Valor global")
    tipoContrato_id: Optional[str] = Field(None, description="ID tipo contrato")
    tipoContrato_nome: Optional[str] = Field(None, description="Nome tipo contrato")
    orgaoEntidade_cnpj: Optional[str] = Field(None, description="CNPJ órgão")
    orgaoEntidade_razaosocial: Optional[str] = Field(None, description="Razão social órgão")
    categoriaProcesso_id: Optional[str] = Field(None, description="ID categoria processo")
    categoriaProcesso_nome: Optional[str] = Field(None, description="Nome categoria processo")

class ItemContratacao(BaseModel):
    """Modelo para itens - baseado na estrutura original PNCP_DB_v2"""
    ID_ITEM_CONTRATACAO: Optional[int] = Field(None, description="ID item contratação")
    numeroControlePNCP: str = Field(..., description="Número controle PNCP")
    numeroItem: Optional[str] = Field(None, description="Número item")
    descricao: Optional[str] = Field(None, description="Descrição")
    materialOuServico: Optional[str] = Field(None, description="Material ou serviço")
    valorUnitarioEstimado: Optional[Decimal] = Field(None, description="Valor unitário estimado")
    valorTotal: Optional[Decimal] = Field(None, description="Valor total")
    quantidade: Optional[Decimal] = Field(None, description="Quantidade")
    unidadeMedida: Optional[str] = Field(None, description="Unidade medida")
    itemCategoriaId: Optional[str] = Field(None, description="ID categoria item")
    itemCategoriaNome: Optional[str] = Field(None, description="Nome categoria item")
    ncmNbsCodigo: Optional[str] = Field(None, description="Código NCM/NBS")

class ItemClassificacao(BaseModel):
    """Modelo para classificação de itens - estrutura original"""
    ID: Optional[int] = Field(None, description="ID")
    numeroControlePNCP: str = Field(..., description="Número controle PNCP")
    numeroItem: Optional[str] = Field(None, description="Número item")
    ID_ITEM_CONTRATACAO: Optional[str] = Field(None, description="ID item contratação")
    descricao: Optional[str] = Field(None, description="Descrição")
    item_type: Optional[str] = Field(None, description="Tipo item")
    TOP_1: Optional[str] = Field(None, description="Top 1")
    TOP_2: Optional[str] = Field(None, description="Top 2")
    TOP_3: Optional[str] = Field(None, description="Top 3")
    TOP_4: Optional[str] = Field(None, description="Top 4")
    TOP_5: Optional[str] = Field(None, description="Top 5")
    SCORE_1: Optional[float] = Field(None, description="Score 1")
    SCORE_2: Optional[float] = Field(None, description="Score 2")
    SCORE_3: Optional[float] = Field(None, description="Score 3")
    SCORE_4: Optional[float] = Field(None, description="Score 4")
    SCORE_5: Optional[float] = Field(None, description="Score 5")
    CONFIDENCE: Optional[float] = Field(None, description="Confidence")

# ===============================
# MODELOS UNIFICADOS PARA V1
# ===============================

class DocumentoPNCP(BaseModel):
    """Modelo unificado para todos os tipos de documento PNCP na v1"""
    # Identificação universal
    id: Optional[str] = Field(None, description="UUID do documento")
    numeroControlePNCP: str = Field(..., description="Número controle PNCP único")
    tipo_documento: TipoDocumento = Field(..., description="Tipo do documento")
    
    # Metadados temporais
    data_criacao: Optional[datetime] = Field(None, description="Data criação")
    data_atualizacao: Optional[datetime] = Field(None, description="Data atualização")
    data_publicacao_pncp: Optional[date] = Field(None, description="Data publicação PNCP")
    data_inclusao_sistema: Optional[date] = Field(None, description="Data inclusão sistema")
    ano_referencia: Optional[int] = Field(None, description="Ano referência")
    
    # Dados principais (JSONB flexível - preserva estrutura original)
    dados_principais: Dict[str, Any] = Field(..., description="Dados principais em JSON")
    
    # Busca semântica
    texto_busca: Optional[str] = Field(None, description="Texto consolidado para busca")
    embedding: Optional[List[float]] = Field(None, description="Vetor embedding")
    
    # Categorização (mantém compatibilidade com sistema existente)
    categoria_codigo: Optional[str] = Field(None, description="CODCAT da categoria")
    categoria_score: Optional[float] = Field(None, description="SCORE da categorização")
    
    # Índices de performance (extraídos dos dados principais)
    orgao_cnpj: Optional[str] = Field(None, description="CNPJ órgão")
    unidade_codigo: Optional[str] = Field(None, description="Código unidade")
    modalidade_id: Optional[int] = Field(None, description="ID modalidade")
    valor_estimado: Optional[Decimal] = Field(None, description="Valor estimado")
    valor_homologado: Optional[Decimal] = Field(None, description="Valor homologado")
    situacao_codigo: Optional[str] = Field(None, description="Código situação")
    
    # Controle de processamento
    status_processamento: StatusProcessamento = Field(StatusProcessamento.PENDENTE)
    tentativas_processamento: int = Field(0, description="Tentativas processamento")
    erro_processamento: Optional[str] = Field(None, description="Erro processamento")

class ResultadoBuscaCompativel(BaseModel):
    """Modelo para resultados de busca - compatível com sistema existente"""
    rank: int = Field(..., description="Posição no ranking")
    id: str = Field(..., description="numeroControlePNCP")
    similarity: float = Field(..., description="Score de similaridade")
    details: Dict[str, Any] = Field(..., description="Detalhes completos")

# ===============================
# FUNÇÕES DE MIGRAÇÃO E CONVERSÃO
# ===============================

def contratacao_supabase_para_documento(contratacao: ContratacaoSupabase) -> DocumentoPNCP:
    """Converte ContratacaoSupabase para DocumentoPNCP unificado"""
    return DocumentoPNCP(
        numeroControlePNCP=contratacao.numeroControlePNCP,
        tipo_documento=TipoDocumento.CONTRATACAO,
        dados_principais=contratacao.dict(exclude_none=True),
        orgao_cnpj=contratacao.orgaoEntidade_cnpj,
        unidade_codigo=contratacao.unidadeOrgao_codigoUnidade,
        modalidade_id=contratacao.modalidadeId,
        valor_estimado=contratacao.valorTotalEstimado,
        valor_homologado=contratacao.valorTotalHomologado,
        situacao_codigo=str(contratacao.situacaoCompraId) if contratacao.situacaoCompraId else None,
        texto_busca=contratacao.descricaoCompleta,
        data_inclusao_sistema=datetime.strptime(contratacao.dataInclusao, "%Y-%m-%d").date() if contratacao.dataInclusao else None
    )

def contrato_original_para_documento(contrato: ContratoOriginal) -> DocumentoPNCP:
    """Converte ContratoOriginal para DocumentoPNCP unificado"""
    return DocumentoPNCP(
        numeroControlePNCP=contrato.numeroControlePNCP,
        tipo_documento=TipoDocumento.CONTRATO,
        dados_principais=contrato.dict(exclude_none=True),
        orgao_cnpj=contrato.orgaoEntidade_cnpj,
        valor_estimado=contrato.valorInicial,
        valor_homologado=contrato.valorGlobal,
        texto_busca=contrato.objetoContrato,
        ano_referencia=int(contrato.anoContrato) if contrato.anoContrato else None
    )

def extrair_texto_busca_compativel(documento: DocumentoPNCP) -> str:
    """Extrai texto consolidado para busca - compatível com sistema existente"""
    if documento.tipo_documento == TipoDocumento.CONTRATACAO:
        dados = documento.dados_principais
        textos = [
            dados.get('objetoCompra', ''),
            dados.get('informacaoComplementar', ''),
            dados.get('orgaoEntidade_razaoSocial', ''),
            dados.get('modalidadeNome', ''),
            dados.get('descricaoCompleta', '')  # Campo principal do sistema atual
        ]
    elif documento.tipo_documento == TipoDocumento.CONTRATO:
        dados = documento.dados_principais
        textos = [
            dados.get('objetoContrato', ''),
            dados.get('orgaoEntidade_razaosocial', ''),
            dados.get('nomeRazaoSocialFornecedor', '')
        ]
    else:
        # Para novos tipos (ATA, PCA)
        textos = [str(documento.dados_principais)]
    
    # Remove textos vazios e junta
    textos_limpos = [texto.strip() for texto in textos if texto and texto.strip()]
    return " ".join(textos_limpos)
