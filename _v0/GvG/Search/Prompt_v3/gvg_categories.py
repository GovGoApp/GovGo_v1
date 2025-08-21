"""DEPRECIADO: funcionalidades de categorias foram consolidadas em gvg_search_core.

Importe diretamente de `gvg_search_core`:
    from gvg_search_core import (
        get_top_categories_for_query,
        correspondence_search,
        category_filtered_search,
    )

Este módulo permanece apenas para compatibilidade temporária.
"""
from __future__ import annotations

from typing import List, Dict, Tuple, Any
import numpy as np
import pandas as pd

from gvg_database import create_engine_connection, create_connection
from gvg_ai_utils import get_embedding, get_negation_embedding, calculate_confidence, has_negation
from gvg_search_core import (
    semantic_search,
    keyword_search,
    hybrid_search,
)

# =====================================================================================
# CATEGORIAS
# =====================================================================================

def get_top_categories_for_query(
    query_text: str,
    top_n: int = 10,
    use_negation: bool = True,
    search_type: int = 1,
    console=None
) -> List[Dict[str, Any]]:
    """Embedda a query e retorna TOP-N categorias mais similares.

    Args:
        query_text: Texto (já pré-processado) para gerar embedding.
        top_n: Número de categorias.
        use_negation: Se deve usar embedding com prompt negativo.
        search_type: 1=Semântica, 3=Híbrida (aplica negation). Outros tipos ignoram.
        console: Rich console opcional para mensagens.
    """
    try:
        # Importante: Para categorias queremos sempre foco em termos POSITIVOS.
        # Mesmo que use_negation=True, a chamada do terminal já envia False.
        # Mantemos a condicional para compatibilidade futura.
        if use_negation and search_type in (1, 3):
            emb = get_embedding(query_text)  # deliberadamente NÃO aplica negation
        else:
            emb = get_embedding(query_text)
        if emb is None:
            if console:
                console.print("[yellow]Não foi possível gerar embedding da consulta para categorias.[/yellow]")
            return []
        if isinstance(emb, np.ndarray):
            emb_list = emb.tolist()
        else:
            emb_list = emb

        engine = create_engine_connection()
        if not engine:
            if console:
                console.print("[red]Engine indisponível para busca de categorias[/red]")
            return []

        query = """
        SELECT 
            id,
            codcat,
            nomcat,
            codnv0,
            nomnv0,
            codnv1,
            nomnv1,
            codnv2,
            nomnv2,
            codnv3,
            nomnv3,
            1 - (cat_embeddings <=> %(embedding)s::vector) AS similarity
        FROM categorias
        WHERE cat_embeddings IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %(limit)s
        """

        df = pd.read_sql_query(query, engine, params={"embedding": emb_list, "limit": top_n})
        out: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            out.append({
                "rank": idx + 1,
                "categoria_id": row.get("id"),
                "codigo": row.get("codcat"),
                "descricao": row.get("nomcat"),
                "nivel0_cod": row.get("codnv0"),
                "nivel0_nome": row.get("nomnv0"),
                "nivel1_cod": row.get("codnv1"),
                "nivel1_nome": row.get("nomnv1"),
                "nivel2_cod": row.get("codnv2"),
                "nivel2_nome": row.get("nomnv2"),
                "nivel3_cod": row.get("codnv3"),
                "nivel3_nome": row.get("nomnv3"),
                "similarity_score": float(row.get("similarity", 0.0))
            })
        return out
    except Exception as e:
        if console:
            console.print(f"[red]Erro ao buscar categorias: {e}[/red]")
        return []


def _calculate_correspondence_similarity_score(
    query_categories: List[Dict[str, Any]],
    result_categories: List[str],
    result_similarities: List[float]
) -> float:
    """Multiplicação similarity(query→categoria) * similarity(contratação→categoria)."""
    try:
        if not query_categories or not result_categories or not result_similarities:
            return 0.0
        best = 0.0
        for qc in query_categories:
            code = qc.get("codigo")
            qsim = qc.get("similarity_score", 0) or 0
            if not code or not qsim:
                continue
            if code in result_categories:
                idx = result_categories.index(code)
                rsim = result_similarities[idx] if idx < len(result_similarities) else 0
                if rsim:
                    best = max(best, float(qsim) * float(rsim))
        return float(best)
    except Exception:
        return 0.0


def _find_top_category_for_result(
    query_categories: List[Dict[str, Any]],
    result_categories: List[str],
    result_similarities: List[float]
) -> Dict[str, Any] | None:
    try:
        if not query_categories or not result_categories or not result_similarities:
            return None
        best_cat = None
        best_score = 0.0
        for qc in query_categories:
            code = qc.get("codigo")
            qsim = qc.get("similarity_score", 0) or 0
            if not code or not qsim:
                continue
            if code in result_categories:
                idx = result_categories.index(code)
                rsim = result_similarities[idx] if idx < len(result_similarities) else 0
                if not rsim:
                    continue
                score = float(qsim) * float(rsim)
                if score > best_score:
                    best_score = score
                    best_cat = {
                        "codigo": code,
                        "descricao": qc.get("descricao"),
                        "query_similarity": qsim,
                        "result_similarity": rsim,
                        "correspondence_score": score
                    }
        return best_cat
    except Exception:
        return None


def correspondence_search(
    query_text: str,
    top_categories: List[Dict[str, Any]],
    limit: int = 30,
    filter_expired: bool = True,
    console=None
) -> Tuple[List[Dict[str, Any]], float, Dict[str, Any]]:
    """Busca por CORRESPONDÊNCIA CATEGÓRICA.

    Retorna somente contratações que possuam pelo menos uma das categorias.
    Similaridade = max( sim(query→cat) * sim(contratação→cat) ).
    """
    if not top_categories:
        return [], 0.0, {"reason": "no_categories"}
    try:
        category_codes = [c['codigo'] for c in top_categories if c.get('codigo')]
        if not category_codes:
            return [], 0.0, {"reason": "empty_codes"}

        conn = create_connection()
        if not conn:
            return [], 0.0, {"reason": "db_connection_failed"}
        cur = conn.cursor()
        sql = """
        SELECT 
            c.numeroControlePNCP,
            c.anoCompra,
            c.descricaoCompleta,
            c.valorTotalHomologado,
            c.valorTotalEstimado,
            c.dataAberturaProposta,
            c.dataEncerramentoProposta,
            c.dataInclusao,
            c.linkSistemaOrigem,
            c.modalidadeId,
            c.modalidadeNome,
            c.modaDisputaId,
            c.modaDisputaNome,
            c.usuarioNome,
            c.orgaoEntidade_poderId,
            c.orgaoEntidade_esferaId,
            c.unidadeOrgao_ufSigla,
            c.unidadeOrgao_municipioNome,
            c.unidadeOrgao_nomeUnidade,
            c.orgaoEntidade_razaosocial,
            ce.top_categories,
            ce.top_similarities
        FROM contratacoes c
        JOIN contratacoes_embeddings ce ON c.numeroControlePNCP = ce.numeroControlePNCP
        WHERE ce.top_categories && %s
        """
        params = (category_codes,)
        if filter_expired:
            sql += " AND c.dataEncerramentoProposta >= CURRENT_DATE"
        sql += " LIMIT %s"
        params = (category_codes, limit * 5)  # pegar mais e ordenar depois
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]
        cur.close(); conn.close()

        results = []
        for row in rows:
            rec = dict(zip(colnames, row))
            r_categories = rec.get('top_categories') or []
            r_sims = rec.get('top_similarities') or []
            correspondence_similarity = _calculate_correspondence_similarity_score(top_categories, r_categories, r_sims)
            top_cat_info = _find_top_category_for_result(top_categories, r_categories, r_sims)
            results.append({
                'id': rec.get('numerocontrolepncp'),
                'numero_controle': rec.get('numerocontrolepncp'),
                'similarity': correspondence_similarity,
                'correspondence_similarity': correspondence_similarity,
                'search_approach': 'correspondence',
                'details': rec,
                'top_category_info': top_cat_info
            })
        # Ordenar e limitar
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:limit]
        for i, r in enumerate(results, 1):
            r['rank'] = i
        confidence = calculate_confidence([r['similarity'] for r in results]) if results else 0.0
        return results, confidence, {"total_raw": len(rows)}
    except Exception as e:
        if console:
            console.print(f"[red]Erro correspondência: {e}[/red]")
        return [], 0.0, {"error": str(e)}


def category_filtered_search(
    query_text: str,
    search_type: int,
    top_categories: List[Dict[str, Any]],
    limit: int = 30,
    filter_expired: bool = True,
    use_negation: bool = True,
    expanded_factor: int = 3,
    console=None
) -> Tuple[List[Dict[str, Any]], float, Dict[str, Any]]:
    """Executa busca tradicional e filtra resultados que possuam categorias relevantes.

    Estratégia:
      1. Executa busca (semântica/keyword/híbrida) com limite expandido
      2. Consulta as categorias de todos os resultados retornados
      3. Mantém apenas os que possuem interseção com TOP categorias
    """
    if not top_categories:
        return [], 0.0, {"reason": "no_categories"}
    try:
        # 1) Buscar universo expandido
        expanded_limit = limit * expanded_factor
        if search_type == 1:
            base_results, confidence = semantic_search(
                query_text, limit=expanded_limit, filter_expired=filter_expired, use_negation=use_negation
            )
        elif search_type == 2:
            base_results, confidence = keyword_search(
                query_text, limit=expanded_limit, filter_expired=filter_expired
            )
        else:
            base_results, confidence = hybrid_search(
                query_text, limit=expanded_limit, filter_expired=filter_expired, use_negation=use_negation
            )
        if not base_results:
            return [], 0.0, {"reason": "no_base_results"}

        # 2) Buscar categorias de cada resultado
        ids = [r['id'] for r in base_results]
        conn = create_connection()
        if not conn:
            return [], 0.0, {"reason": "db_connection_failed"}
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(ids))
        cat_sql = f"""
        SELECT numeroControlePNCP, top_categories
        FROM contratacoes_embeddings
        WHERE numeroControlePNCP IN ({placeholders}) AND top_categories IS NOT NULL
        """
        cur.execute(cat_sql, ids)
        cat_map = {row[0]: row[1] for row in cur.fetchall()}
        cur.close(); conn.close()
        query_codes = {c['codigo'] for c in top_categories if c.get('codigo')}

        filtered = []
        universe_with_categories = 0
        for r in base_results:
            r_cats = cat_map.get(r['id'])
            if r_cats:
                universe_with_categories += 1
                if any(code in r_cats for code in query_codes):
                    r['search_approach'] = 'category_filtered'
                    filtered.append(r)
            if len(filtered) >= limit:
                break
        for i, r in enumerate(filtered, 1):
            r['rank'] = i
        meta = {
            'universe_size': len(base_results),
            'universe_with_categories': universe_with_categories,
            'filtered_count': len(filtered)
        }
        return filtered, confidence, meta
    except Exception as e:
        if console:
            console.print(f"[red]Erro filtro categorias: {e}[/red]")
        return [], 0.0, {"error": str(e)}


__all__ = [
    'get_top_categories_for_query',
    'correspondence_search',
    'category_filtered_search'
]
