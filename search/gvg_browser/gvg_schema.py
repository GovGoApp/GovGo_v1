"""
gvg_schema.py
Fase 1 – Centralização de esquema (V1 apenas)

Objetivo:
  Fornecer uma única fonte da verdade para nomes de tabelas, colunas, tipos lógicos
  e conjuntos mínimos de campos usados pelos mecanismos de busca (semântica,
  palavras‑chave e híbrida), exportação e exibição.

Escopo desta fase:
  • SOMENTE Base V1 (BDS1). Nenhuma compatibilidade ou detecção de V0.
  • Metadados de tabelas principais: contratacao, contratacao_emb, categoria.
  • Listas de campos “core” para SELECT de busca (contratacao) e de categorias.
  • Funções helper para (a) obter listas de colunas, (b) construir pedaços de
    SELECT reutilizáveis (sem cláusulas WHERE/ORDER) e (c) normalizar rows.
  • NÃO altera queries existentes ainda (será feito na Fase 2).

Design:
  1. Cada campo possui metadados: nome físico, tipo lógico simplificado,
     descrição curta e flags de uso (search, export, fts, category).
  2. Funções utilitárias retornam apenas as colunas estritamente necessárias
     para reduzir I/O em tabelas grandes.
  3. Campo de texto base para FTS: objeto_compra (futuro: poderá gerar
     tsvector indexado fora do código). Fornecemos constante FTS_SOURCE_FIELD.
  4. Campos de data são armazenados como TEXT no schema; funções de query
     futuras deverão aplicar TO_DATE seguro. Aqui só marcamos type='date_text'.

Extensibilidade:
  • Para acrescentar novos campos, adicionar em CONTRACTACAO_FIELDS.
  • Para otimizações futuras (projeções distintas por tipo de busca), ajustar
    FIELD_GROUPS.

Uso previsto (Fase 2+):
  from gvg_schema import CONTRACTACAO_CORE_SELECT, build_semantic_select
  sql_head = build_semantic_select()

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Iterable

# =============================
# Metadados de Campos – CONTRATACAO
# =============================

@dataclass(frozen=True)
class FieldMeta:
    name: str                 # nome físico na tabela
    logical: str              # nome lógico (snake_case canônico interno)
    type: str                 # tipo lógico simplificado (text, numeric, date_text, json, vector, bool)
    description: str          # breve descrição
    roles: Iterable[str]      # marcadores de uso (ex: search, export, category)


# Campos mínimos necessários para a experiência atual 
CONTRATACAO_FIELDS: Dict[str, FieldMeta] = {
    'numero_controle_pncp': FieldMeta('numero_controle_pncp', 'numero_controle_pncp', 'text', 'Identificador único do processo', ['pk','search','export']),
    'ano_compra': FieldMeta('ano_compra', 'ano_compra', 'text', 'Ano da compra', ['search']),
    'objeto_compra': FieldMeta('objeto_compra', 'objeto_compra', 'text', 'Objeto principal da contratação (fonte FTS)', ['search','export','fts']),
    'valor_total_homologado': FieldMeta('valor_total_homologado', 'valor_total_homologado', 'numeric', 'Valor total homologado', ['search','export']),
    'valor_total_estimado': FieldMeta('valor_total_estimado', 'valor_total_estimado', 'numeric_text', 'Valor total estimado (text → numeric)', ['search','export']),
    'data_abertura_proposta': FieldMeta('data_abertura_proposta', 'data_abertura_proposta', 'date_text', 'Data de abertura das propostas', ['search']),
    'data_encerramento_proposta': FieldMeta('data_encerramento_proposta', 'data_encerramento_proposta', 'date_text', 'Data de encerramento das propostas', ['search','export','ordering']),
    'data_inclusao': FieldMeta('data_inclusao', 'data_inclusao', 'date_text', 'Data de inclusão', ['search']),
    'link_sistema_origem': FieldMeta('link_sistema_origem', 'link_sistema_origem', 'text', 'Link do sistema de origem', ['export']),
    'modalidade_id': FieldMeta('modalidade_id', 'modalidade_id', 'text', 'Código modalidade', ['search']),
    'modalidade_nome': FieldMeta('modalidade_nome', 'modalidade_nome', 'text', 'Nome modalidade', ['search','export']),
    'modo_disputa_id': FieldMeta('modo_disputa_id', 'modo_disputa_id', 'text', 'Código modo disputa', ['search']),
    'modo_disputa_nome': FieldMeta('modo_disputa_nome', 'modo_disputa_nome', 'text', 'Nome modo disputa', ['search','export']),
    'usuario_nome': FieldMeta('usuario_nome', 'usuario_nome', 'text', 'Nome do usuário', ['search']),
    'orgao_entidade_poder_id': FieldMeta('orgao_entidade_poder_id', 'orgao_entidade_poder_id', 'text', 'Poder do órgão', ['search','export']),
    'orgao_entidade_esfera_id': FieldMeta('orgao_entidade_esfera_id', 'orgao_entidade_esfera_id', 'text', 'Esfera do órgão', ['search','export']),
    'unidade_orgao_uf_sigla': FieldMeta('unidade_orgao_uf_sigla', 'unidade_orgao_uf_sigla', 'text', 'UF da unidade', ['search','export']),
    'unidade_orgao_municipio_nome': FieldMeta('unidade_orgao_municipio_nome', 'unidade_orgao_municipio_nome', 'text', 'Município da unidade', ['search','export']),
    'unidade_orgao_nome_unidade': FieldMeta('unidade_orgao_nome_unidade', 'unidade_orgao_nome_unidade', 'text', 'Nome da unidade', ['search','export']),
    'orgao_entidade_razao_social': FieldMeta('orgao_entidade_razao_social', 'orgao_entidade_razao_social', 'text', 'Razão social do órgão', ['search','export']),
}

# Campos da tabela de embeddings (contratacao_emb)
CONTRATACAO_EMB_FIELDS: Dict[str, FieldMeta] = {
    'numero_controle_pncp': FieldMeta('numero_controle_pncp', 'numero_controle_pncp', 'text', 'FK para contratacao', ['join']),
    'embeddings': FieldMeta('embeddings', 'embeddings', 'vector', 'Vetor de embedding do processo (LEGADO)', ['semantic']),
    # Novo campo HV (halfvec) – utilizado nas buscas
    'embeddings_hv': FieldMeta('embeddings_hv', 'embeddings_hv', 'halfvec', 'Vetor de embedding em halfvec(3072)', ['semantic']),
    'modelo_embedding': FieldMeta('modelo_embedding', 'modelo_embedding', 'text', 'Modelo usado', ['meta']),
    'confidence': FieldMeta('confidence', 'confidence', 'numeric', 'Confiança do embedding', ['meta']),
    'top_categories': FieldMeta('top_categories', 'top_categories', 'array_text', 'Códigos de categorias top', ['category']),
    'top_similarities': FieldMeta('top_similarities', 'top_similarities', 'array_numeric', 'Scores das categorias top', ['category']),
}

# Campos da tabela categoria
CATEGORIA_FIELDS: Dict[str, FieldMeta] = {
    'cod_cat': FieldMeta('cod_cat', 'cod_cat', 'text', 'Código da categoria', ['pk','category']),
    'nom_cat': FieldMeta('nom_cat', 'nom_cat', 'text', 'Nome da categoria', ['category','export']),
    'cod_nv0': FieldMeta('cod_nv0', 'cod_nv0', 'text', 'Código nível 0', ['category']),
    'nom_nv0': FieldMeta('nom_nv0', 'nom_nv0', 'text', 'Nome nível 0', ['category']),
    'cod_nv1': FieldMeta('cod_nv1', 'cod_nv1', 'text', 'Código nível 1', ['category']),
    'nom_nv1': FieldMeta('nom_nv1', 'nom_nv1', 'text', 'Nome nível 1', ['category']),
    'cod_nv2': FieldMeta('cod_nv2', 'cod_nv2', 'text', 'Código nível 2', ['category']),
    'nom_nv2': FieldMeta('nom_nv2', 'nom_nv2', 'text', 'Nome nível 2', ['category']),
    'cod_nv3': FieldMeta('cod_nv3', 'cod_nv3', 'text', 'Código nível 3', ['category']),
    'nom_nv3': FieldMeta('nom_nv3', 'nom_nv3', 'text', 'Nome nível 3', ['category']),
    'cat_embeddings': FieldMeta('cat_embeddings', 'cat_embeddings', 'vector', 'Vetor embedding da categoria (LEGADO)', ['semantic','category']),
    # Novo campo HV em categorias
    'cat_embeddings_hv': FieldMeta('cat_embeddings_hv', 'cat_embeddings_hv', 'halfvec', 'Vetor embedding da categoria em halfvec(3072)', ['semantic','category']),
}

# =============================
# Agrupamentos & Constantes
# =============================

CONTRATACAO_TABLE = 'contratacao'
CONTRATACAO_EMB_TABLE = 'contratacao_emb'
CATEGORIA_TABLE = 'categoria'
ITEM_CONTRATACAO_TABLE = 'item_contratacao'

PRIMARY_KEY = 'numero_controle_pncp'
EMB_VECTOR_FIELD = 'embeddings_hv'
CATEGORY_VECTOR_FIELD = 'cat_embeddings_hv'
FTS_SOURCE_FIELD = 'objeto_compra'

# Grupo mínimo de colunas para SELECT em buscas (ordem importante para zips atuais)
CONTRATACAO_CORE_ORDER: List[str] = [
    'numero_controle_pncp', 'ano_compra', 'objeto_compra', 'valor_total_homologado', 'valor_total_estimado',
    'data_abertura_proposta', 'data_encerramento_proposta', 'data_inclusao', 'link_sistema_origem',
    'modalidade_id', 'modalidade_nome', 'modo_disputa_id', 'modo_disputa_nome', 'usuario_nome',
    'orgao_entidade_poder_id', 'orgao_entidade_esfera_id', 'unidade_orgao_uf_sigla', 'unidade_orgao_municipio_nome',
    'unidade_orgao_nome_unidade', 'orgao_entidade_razao_social'
]

def get_contratacao_core_columns(alias: str = 'c') -> List[str]:
    """Retorna lista de expressões SELECT (sem alias AS redundante) na mesma
    ordem de CONTRATACAO_CORE_ORDER para uso em queries manuais.
    """
    cols = []
    for logical in CONTRATACAO_CORE_ORDER:
        meta = CONTRATACAO_FIELDS[logical]
        cols.append(f"{alias}.{meta.name}")
    return cols


def build_core_select_clause(alias: str = 'c') -> str:
    """Constrói a cláusula SELECT principal (sem DISTINCT / sem joins) para a
    tabela contratacao, retornando todas as colunas core já na ordem exigida.
    """
    cols = get_contratacao_core_columns(alias)
    return ",\n  ".join(cols)


def build_semantic_select(embedding_param_placeholder: str = '%s', semantic_alias: str = 'sim') -> str:
    """Retorna trecho base do SELECT semântico (sem WHERE/ORDER) para futura
    montagem em gvg_search_core. Inclui cálculo de similarity.

    A métrica usada: 1 - (ce.embeddings_hv <=> %s::halfvec(3072))
    """
    select_cols = build_core_select_clause('c')
    similarity_expr = f"1 - (ce.{EMB_VECTOR_FIELD} <=> {embedding_param_placeholder}::halfvec(3072)) AS similarity"
    return (
        "SELECT\n  " + select_cols + ",\n  " + similarity_expr + "\n"
        f"FROM {CONTRATACAO_TABLE} c\nJOIN {CONTRATACAO_EMB_TABLE} ce ON c.{PRIMARY_KEY} = ce.{PRIMARY_KEY}\n"
        f"WHERE ce.{EMB_VECTOR_FIELD} IS NOT NULL\n"
    )


def build_category_similarity_select(embedding_param_placeholder: str = '%s') -> str:
    """SELECT para top categorias dado um embedding (%s placeholder)."""
    return (
        "SELECT id_categoria, cod_cat, nom_cat, cod_nv0, nom_nv0, cod_nv1, nom_nv1, "
        "cod_nv2, nom_nv2, cod_nv3, nom_nv3, "
        f"1 - ({CATEGORIA_TABLE}.{CATEGORY_VECTOR_FIELD} <=> {embedding_param_placeholder}::halfvec(3072)) AS similarity\n"
        f"FROM {CATEGORIA_TABLE}\nWHERE {CATEGORIA_TABLE}.{CATEGORY_VECTOR_FIELD} IS NOT NULL\n"
    )


# =============================
# Schema – ITEM_CONTRATACAO (campos essenciais)
# =============================
ITEM_CONTRATACAO_FIELDS: Dict[str, FieldMeta] = {
    'numero_controle_pncp': FieldMeta('numero_controle_pncp', 'numero_controle_pncp', 'text', 'FK para contratacao', ['pk','join','export']),
    'numero_item': FieldMeta('numero_item', 'numero_item', 'text', 'Número do item', ['export','search']),
    'descricao_item': FieldMeta('descricao_item', 'descricao_item', 'text', 'Descrição do item', ['export','search']),
    'material_ou_servico': FieldMeta('material_ou_servico', 'material_ou_servico', 'text', 'Tipo (M/S)', ['export']),
    'quantidade_item': FieldMeta('quantidade_item', 'quantidade_item', 'numeric', 'Quantidade', ['export']),
    'unidade_medida': FieldMeta('unidade_medida', 'unidade_medida', 'text', 'Unidade de medida', ['export']),
    'valor_unitario_estimado': FieldMeta('valor_unitario_estimado', 'valor_unitario_estimado', 'numeric', 'Valor unitário estimado', ['export']),
    'valor_total_estimado': FieldMeta('valor_total_estimado', 'valor_total_estimado', 'numeric', 'Valor total estimado', ['export'])
}

# Ordem canônica de colunas para SELECT de itens
ITEM_CONTRATACAO_ORDER: List[str] = [
    'numero_controle_pncp', 'numero_item', 'descricao_item', 'material_ou_servico',
    'quantidade_item', 'unidade_medida', 'valor_unitario_estimado', 'valor_total_estimado'
]

def get_item_contratacao_columns(alias: str = 'i') -> List[str]:
    cols = []
    for logical in ITEM_CONTRATACAO_ORDER:
        meta = ITEM_CONTRATACAO_FIELDS[logical]
        cols.append(f"{alias}.{meta.name}")
    return cols

def build_itens_by_pncp_select(limit_placeholder: str = '%s') -> str:
    """SELECT de itens por numero_controle_pncp (com ORDER básico e LIMIT)."""
    cols = ",\n  ".join(get_item_contratacao_columns('i'))
    return (
        "SELECT\n  " + cols + "\n"
        f"FROM {ITEM_CONTRATACAO_TABLE} i\n"
        "WHERE i.numero_controle_pncp = %s\n"
    # ordenação: tenta numérica do numero_item, caindo para ordem lexical
    "ORDER BY NULLIF(regexp_replace(i.numero_item,'[^0-9]','','g'),'')::int NULLS LAST, i.numero_item ASC\n"
        f"LIMIT {limit_placeholder}"
    )

def normalize_item_contratacao_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for logical, meta in ITEM_CONTRATACAO_FIELDS.items():
        if meta.name in row:
            out[logical] = row[meta.name]
    return out


def normalize_contratacao_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza um dicionário de linha da contratacao para chaves lógicas.
    Assumimos que a query já selecionou nomes físicos (sem alias)."""
    out = {}
    for logical, meta in CONTRATACAO_FIELDS.items():
        if meta.name in row:
            out[logical] = row[meta.name]
    return out


def project_result_for_output(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara dicionário final de 'details' usado pelos exportadores / UI.
    Nesta fase mantemos apenas snake_case (nenhum camelCase)."""
    return dict(normalized)  # cópia simples (futuras derivadas podem ser adicionadas)


__all__ = [
    'CONTRATACAO_TABLE','CONTRATACAO_EMB_TABLE','CATEGORIA_TABLE',
    'CONTRATACAO_FIELDS','CONTRATACAO_EMB_FIELDS','CATEGORIA_FIELDS',
    'ITEM_CONTRATACAO_TABLE','ITEM_CONTRATACAO_FIELDS','ITEM_CONTRATACAO_ORDER',
    'FTS_SOURCE_FIELD','PRIMARY_KEY','EMB_VECTOR_FIELD','CATEGORY_VECTOR_FIELD',
    'get_contratacao_core_columns','build_core_select_clause','build_semantic_select',
    'build_category_similarity_select','build_itens_by_pncp_select','get_item_contratacao_columns',
    'normalize_contratacao_row','normalize_item_contratacao_row','project_result_for_output'
]