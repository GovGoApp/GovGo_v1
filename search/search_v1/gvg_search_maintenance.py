"""gvg_search_maintenance.py
Utilitários de manutenção para o pipeline de busca V1 (BDS1).

Inclui:
- sanity_check: valida colunas retornadas pelas buscas em relação ao schema central.
- index_advice: gera recomendações SQL de índices (pgvector / FTS / filtros de data).
- simple_benchmark: executa rodadas rápidas de cada tipo de busca e mede latência.

Uso não interfere nas funções de UI; tudo é opcional / ad hoc.
"""
from __future__ import annotations
import time
from typing import Dict, List, Callable, Any, Tuple

from gvg_schema import CONTRATACAO_FIELDS, PRIMARY_KEY, FTS_SOURCE_FIELD, EMB_VECTOR_FIELD
from gvg_search_core import semantic_search, keyword_search, hybrid_search

SearchFunc = Callable[[str], Tuple[List[Dict[str, Any]], float]]

EXPECTED_CORE_SET = set(CONTRATACAO_FIELDS.keys())


def sanity_check(sample_query: str = "energia", top_n: int = 5) -> Dict[str, Any]:
    """Executa rapidamente cada função de busca e compara colunas retornadas.
    Retorna estrutura com divergências e status agregado.
    """
    report = {"sample_query": sample_query, "checks": []}
    funcs: List[Tuple[str, SearchFunc]] = [
        ("semantic", lambda q: semantic_search(q, limit=top_n)[0:2]),
        ("keyword", lambda q: keyword_search(q, limit=top_n)[0:2]),
        ("hybrid", lambda q: hybrid_search(q, limit=top_n)[0:2]),
    ]
    problems = 0
    for name, fn in funcs:
        try:
            results, _conf = fn(sample_query)
            returned_keys = set()
            for r in results:
                details = r.get('details', {})
                returned_keys.update(details.keys())
            missing = sorted(list(EXPECTED_CORE_SET - returned_keys))
            unexpected = sorted(list(returned_keys - EXPECTED_CORE_SET))
            report["checks"].append({
                "search": name,
                "result_count": len(results),
                "missing_fields": missing,
                "unexpected_fields": unexpected,
            })
            if missing or unexpected:
                problems += 1
        except Exception as e:
            problems += 1
            report["checks"].append({
                "search": name,
                "error": str(e)
            })
    report["status"] = "OK" if problems == 0 else ("WARN" if problems < 3 else "FAIL")
    return report


def index_advice(include_comments: bool = True) -> str:
    """Retorna string com recomendações de índices não destrutivas.
    Não executa SQL automaticamente.
    """
    lines = []
    c = "-- " if include_comments else ""
    lines.append(f"{c}Recomendações de índices para BDS1 Search")
    lines.append(f"{c}1) Vetorial (pgvector) - busca semântica")
    lines.append(f"CREATE INDEX IF NOT EXISTS idx_contratacao_emb_{EMB_VECTOR_FIELD}_hnsw ON contratacao_emb USING hnsw ({EMB_VECTOR_FIELD});")
    lines.append(f"{c}2) FTS (objeto_compra) - busca keyword")
    lines.append(f"ALTER TABLE contratacao ADD COLUMN IF NOT EXISTS objeto_compra_tsv tsvector;")
    lines.append(f"UPDATE contratacao SET objeto_compra_tsv = to_tsvector('portuguese', coalesce({FTS_SOURCE_FIELD},''));")
    lines.append(f"CREATE INDEX IF NOT EXISTS idx_contratacao_objeto_compra_tsv ON contratacao USING gin(objeto_compra_tsv);")
    lines.append(f"{c}Trigger de manutenção opcional:")
    lines.append("CREATE OR REPLACE FUNCTION contratacao_objeto_compra_tsv_update() RETURNS trigger AS $$\nBEGIN\n  NEW.objeto_compra_tsv := to_tsvector('portuguese', coalesce(NEW.objeto_compra,''));\n  RETURN NEW;\nEND;\n$$ LANGUAGE plpgsql;")
    lines.append("DROP TRIGGER IF EXISTS trg_contratacao_objeto_compra_tsv ON contratacao;")
    lines.append("CREATE TRIGGER trg_contratacao_objeto_compra_tsv BEFORE INSERT OR UPDATE OF objeto_compra ON contratacao FOR EACH ROW EXECUTE FUNCTION contratacao_objeto_compra_tsv_update();")
    lines.append(f"{c}3) Data de encerramento (filtro frequente)")
    lines.append("CREATE INDEX IF NOT EXISTS idx_contratacao_data_encerramento ON contratacao (to_date(NULLIF(data_encerramento_proposta,''),'YYYY-MM-DD'));")
    return "\n".join(lines)


def simple_benchmark(sample_query: str = "energia solar", rounds: int = 3, limit: int = 15) -> Dict[str, Any]:
    """Executa algumas rodadas de cada busca e mede tempos; não verifica relevância.
    Retorna métricas agregadas (avg_ms, min_ms, max_ms) por tipo.
    """
    stats: Dict[str, List[float]] = {"semantic": [], "keyword": [], "hybrid": []}
    for _ in range(rounds):
        t0 = time.perf_counter(); semantic_search(sample_query, limit=limit); stats['semantic'].append((time.perf_counter()-t0)*1000)
        t0 = time.perf_counter(); keyword_search(sample_query, limit=limit); stats['keyword'].append((time.perf_counter()-t0)*1000)
        t0 = time.perf_counter(); hybrid_search(sample_query, limit=limit); stats['hybrid'].append((time.perf_counter()-t0)*1000)
    out = {"sample_query": sample_query, "rounds": rounds, "limit": limit, "metrics": {}}
    for k, arr in stats.items():
        if arr:
            out['metrics'][k] = {
                'avg_ms': sum(arr)/len(arr),
                'min_ms': min(arr),
                'max_ms': max(arr)
            }
    return out

__all__ = [
    'sanity_check', 'index_advice', 'simple_benchmark'
]
