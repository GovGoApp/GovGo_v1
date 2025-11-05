"""
gvg_schema.py
Fase 2 – Centralização dinâmica de esquema (contratação | contrato)

Objetivo:
    Fornecer uma única fonte da verdade para nomes de tabelas, colunas, tipos lógicos
    e conjuntos mínimos de campos usados pelos mecanismos de busca (semântica,
    palavras‑chave e híbrida), exportação e exibição, agora com alternância dinâmica
    entre as fontes 'contratacao' e 'contrato'.

Pontos‑chave:
    • Alternância via set_current_source('contratacao'|'contrato')
    • Getters dinâmicos de tabela, PK, campo FTS, campo de expiração, campo de embedding
        e cast adequado (::vector | ::halfvec)
    • Colunas core definidas para cada fonte
    • Categorias migram para halfvec (cat_embeddings_hv)

Observação: campos de data são TEXT no esquema; as queries devem aplicar TO_DATE seguro.
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


# Campos mínimos necessários para a experiência atual (Prompt_v3)
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
    'embeddings': FieldMeta('embeddings', 'embeddings', 'vector', 'Vetor de embedding do processo', ['semantic']),
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
    'cat_embeddings': FieldMeta('cat_embeddings', 'cat_embeddings', 'vector', 'Vetor embedding da categoria (legacy)', ['semantic','category']),
}

# =============================
# Agrupamentos & Constantes
# =============================

CONTRATACAO_TABLE = 'contratacao'
CONTRATACAO_EMB_TABLE = 'contratacao_emb'
CONTRATO_TABLE = 'contrato'
CONTRATO_EMB_TABLE = 'contrato_emb'
CATEGORIA_TABLE = 'categoria'

PRIMARY_KEY = 'numero_controle_pncp'
EMB_VECTOR_FIELD = 'embeddings'           # legado (contratação)
EMB_HALFVEC_FIELD = 'embeddings_hv'       # novo (contrato)
CATEGORY_VECTOR_FIELD = 'cat_embeddings'  # legado
CATEGORY_HALFVEC_FIELD = 'cat_embeddings_hv'  # novo
FTS_SOURCE_FIELD = 'objeto_compra'        # legado (contratação)

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
    """Retorna trecho base do SELECT semântico (dinâmico por fonte, sem WHERE/ORDER).

    A métrica usada: 1 - (ce.<emb_field> <=> %s::vector|halfvec)
    NOTA: usa colunas core dinâmicas conforme a fonte atual (contratacao|contrato).
    """
    # Usa o builder DINÂMICO para respeitar a fonte atual
    select_cols = build_core_select_clause_dynamic('c')
    emb_cast = get_embedding_cast(embedding_param_placeholder)
    emb_field = get_embedding_field()
    emb_col_expr = get_embedding_column_expr('ce')
    main = get_main_table(); emb = get_emb_table(); pk = get_primary_key()
    similarity_expr = f"1 - ({emb_col_expr} <=> {emb_cast}) AS similarity"
    return (
        "SELECT\n  " + select_cols + ",\n  " + similarity_expr + "\n"
        f"FROM {main} c\nJOIN {emb} ce ON c.{pk} = ce.{pk}\n"
        f"WHERE ce.{emb_field} IS NOT NULL\n"
    )


def build_category_similarity_select(embedding_param_placeholder: str = '%s') -> str:
    """SELECT para top categorias dado um embedding (%s placeholder), usando halfvec."""
    return (
        "SELECT id_categoria, cod_cat, nom_cat, cod_nv0, nom_nv0, cod_nv1, nom_nv1, "
        "cod_nv2, nom_nv2, cod_nv3, nom_nv3, "
        f"1 - ({CATEGORIA_TABLE}.{CATEGORY_HALFVEC_FIELD} <=> {embedding_param_placeholder}::halfvec) AS similarity\n"
        f"FROM {CATEGORIA_TABLE}\nWHERE {CATEGORIA_TABLE}.{CATEGORY_HALFVEC_FIELD} IS NOT NULL\n"
    )


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


# =============================
# SUPORTE DINÂMICO – contrato
# =============================

# Campos mínimos para contrato
CONTRATO_FIELDS: Dict[str, FieldMeta] = {
    'numero_controle_pncp': FieldMeta('numero_controle_pncp', 'numero_controle_pncp', 'text', 'Identificador único do processo', ['pk','search','export']),
    'objeto_contrato': FieldMeta('objeto_contrato', 'objeto_contrato', 'text', 'Objeto principal do contrato (FTS)', ['search','export','fts']),
    'valor_global': FieldMeta('valor_global', 'valor_global', 'numeric', 'Valor global do contrato', ['search','export']),
    'data_assinatura': FieldMeta('data_assinatura', 'data_assinatura', 'date_text', 'Data de assinatura', ['search']),
    'data_vigencia_fim': FieldMeta('data_vigencia_fim', 'data_vigencia_fim', 'date_text', 'Fim da vigência (usado como expiração)', ['search','export','ordering']),
    'unidade_orgao_uf_sigla': FieldMeta('unidade_orgao_uf_sigla', 'unidade_orgao_uf_sigla', 'text', 'UF da unidade', ['search','export']),
    'unidade_orgao_municipio_nome': FieldMeta('unidade_orgao_municipio_nome', 'unidade_orgao_municipio_nome', 'text', 'Município da unidade', ['search','export']),
    'unidade_orgao_nome_unidade': FieldMeta('unidade_orgao_nome_unidade', 'unidade_orgao_nome_unidade', 'text', 'Nome da unidade', ['search','export']),
    'orgao_entidade_razaosocial': FieldMeta('orgao_entidade_razaosocial', 'orgao_entidade_razaosocial', 'text', 'Razão social do órgão', ['search','export']),
}

CONTRATO_CORE_ORDER: List[str] = [
    'numero_controle_pncp', 'objeto_contrato', 'valor_global', 'data_assinatura', 'data_vigencia_fim',
    'unidade_orgao_uf_sigla', 'unidade_orgao_municipio_nome', 'unidade_orgao_nome_unidade', 'orgao_entidade_razaosocial'
]

# Fonte atual (default: contrato)
CURRENT_SOURCE = 'contrato'

def set_current_source(source: str):
    global CURRENT_SOURCE
    src = (source or '').strip().lower()
    if src not in ('contratacao','contrato'):
        raise ValueError("Fonte inválida: use 'contratacao' ou 'contrato'")
    CURRENT_SOURCE = src

def get_current_source() -> str:
    return CURRENT_SOURCE

def get_main_table() -> str:
    return CONTRATACAO_TABLE if CURRENT_SOURCE == 'contratacao' else CONTRATO_TABLE

def get_emb_table() -> str:
    return CONTRATACAO_EMB_TABLE if CURRENT_SOURCE == 'contratacao' else CONTRATO_EMB_TABLE

def get_primary_key() -> str:
    return PRIMARY_KEY

def get_embedding_field() -> str:
    """Nome do campo físico de embedding.

    Para 'contratacao', usamos embeddings_hv (halfvec) para ativar IVFFLAT.
    """
    return EMB_HALFVEC_FIELD

def get_embedding_cast(placeholder: str = '%s') -> str:
    """Cast do parâmetro de embedding — usa dimensão completa para casar com o índice.
    """
    return f"{placeholder}::halfvec(3072)"

def get_embedding_column_expr(alias: str = 'ce') -> str:
    """Expressão da coluna de embedding com cast adequado para o operador <=>.

    - contratacao: alias.embeddings_hv::halfvec(3072)
    - contrato:    alias.embeddings_hv (já tipado como halfvec)
    """
    if CURRENT_SOURCE == 'contratacao':
        return f"{alias}.{EMB_HALFVEC_FIELD}::halfvec(3072)"
    return f"{alias}.{EMB_HALFVEC_FIELD}"

def get_fts_source_field() -> str:
    return 'objeto_compra' if CURRENT_SOURCE == 'contratacao' else 'objeto_contrato'

def get_expired_date_field() -> str:
    return 'data_encerramento_proposta' if CURRENT_SOURCE == 'contratacao' else 'data_vigencia_fim'

def get_core_fields_dict() -> Dict[str, FieldMeta]:
    return CONTRATACAO_FIELDS if CURRENT_SOURCE == 'contratacao' else CONTRATO_FIELDS

def get_core_columns(alias: str = 'c') -> List[str]:
    cols = []
    order = CONTRATACAO_CORE_ORDER if CURRENT_SOURCE == 'contratacao' else CONTRATO_CORE_ORDER
    fields = get_core_fields_dict()
    for logical in order:
        meta = fields[logical]
        cols.append(f"{alias}.{meta.name}")
    return cols

def build_core_select_clause_dynamic(alias: str = 'c') -> str:
    return ",\n  ".join(get_core_columns(alias))


__all__ = [
    # Legados (contratação)
    'CONTRATACAO_TABLE','CONTRATACAO_EMB_TABLE','CATEGORIA_TABLE',
    'CONTRATACAO_FIELDS','CONTRATACAO_EMB_FIELDS','CATEGORIA_FIELDS',
    'FTS_SOURCE_FIELD','PRIMARY_KEY','EMB_VECTOR_FIELD','CATEGORY_VECTOR_FIELD',
    'get_contratacao_core_columns','build_core_select_clause','build_semantic_select',
    'build_category_similarity_select','normalize_contratacao_row','project_result_for_output',
    # Novos (dinâmicos)
    'set_current_source','get_current_source','get_main_table','get_emb_table','get_primary_key',
    'get_embedding_field','get_embedding_cast','get_embedding_column_expr','get_fts_source_field','get_expired_date_field',
    'get_core_fields_dict','get_core_columns'
]
