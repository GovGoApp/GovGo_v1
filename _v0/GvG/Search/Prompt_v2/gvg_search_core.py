"""
gvg_search_core.py
Módulo otimizado para funções de busca principais GvG
Contém apenas as funções de busca realmente utilizadas com IA integrada
"""

import os
import time
import numpy as np
from typing import Dict, List, Tuple, Any
import psycopg2

# ============================================================================
# NOTA: Este módulo foi atualizado para replicar as queries e funcionalidades
#       avançadas do antigo gvg_search_utils_v3 (semantic / keyword / hybrid)
#       mantendo compatibilidade com o schema atual (snake_case) e provendo
#       fallbacks seguros quando features (tsvector ou colunas) não existirem.
# ============================================================================

# Importações dos módulos otimizados
from gvg_database import create_connection
from gvg_ai_utils import get_embedding, get_negation_embedding, calculate_confidence, has_negation, extract_pos_neg_terms

# ============================================================================
# Filtro de Relevância interno (removida dependência de gvg_search_utils_v3)
# Implementa sistema de 3 níveis com uso opcional de OpenAI Assistant.
# Nível 1: desativado | Nível 2: flexível | Nível 3: restritivo
# ============================================================================
RELEVANCE_FILTER_LEVEL = 1  # 1=sem filtro, 2=flexível, 3=restritivo
DEBUG_RELEVANCE_FILTER = False
USE_PARTIAL_DESCRIPTION = True

# IDs (mantenha/atualize conforme necessidade)
RELEVANCE_ASSISTANT_FLEXIBLE = "asst_tfD5oQxSgoGhtqdKQHK9UwRi"
RELEVANCE_ASSISTANT_RESTRICTIVE = "asst_XmsefQEKbuVWu51uNST7kpYT"

try:
    from openai import OpenAI  # type: ignore
    _openai_key = os.getenv("OPENAI_API_KEY")
    if _openai_key:
        _openai_client = OpenAI(api_key=_openai_key)
        _relevance_thread = None
        _RELEVANCE_AVAILABLE = True
    else:
        _openai_client = None
        _relevance_thread = None
        _RELEVANCE_AVAILABLE = False
except Exception as _e:
    _openai_client = None
    _relevance_thread = None
    _RELEVANCE_AVAILABLE = False

def _get_current_assistant_id():
    if RELEVANCE_FILTER_LEVEL == 2:
        return RELEVANCE_ASSISTANT_FLEXIBLE
    if RELEVANCE_FILTER_LEVEL == 3:
        return RELEVANCE_ASSISTANT_RESTRICTIVE
    return None

def _get_relevance_thread():
    global _relevance_thread
    if not _RELEVANCE_AVAILABLE or not _openai_client:
        return None
    if _relevance_thread is None:
        try:
            _relevance_thread = _openai_client.beta.threads.create()
        except Exception as e:
            if DEBUG_RELEVANCE_FILTER:
                print(f"❌ Erro criando thread relevância: {e}")
            return None
    return _relevance_thread

def _poll_run(thread_id, run_id, timeout=30):
    if not _openai_client:
        raise RuntimeError("Cliente OpenAI indisponível")
    start = time.time()
    while time.time() - start < timeout:
        run = _openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status == 'completed':
            msgs = _openai_client.beta.threads.messages.list(thread_id=thread_id, limit=1)
            if msgs.data and msgs.data[0].role == 'assistant':
                content = msgs.data[0].content[0].text.value
                return content
            break
        if run.status in ('failed','cancelled','expired'):
            raise RuntimeError(f"Run falhou: {run.status}")
        time.sleep(1)
    raise TimeoutError("Timeout aguardando resposta do Assistant")

def _call_relevance_assistant(assistant_id, payload_json):
    if not _openai_client:
        raise RuntimeError("Cliente OpenAI indisponível")
    thread = _get_relevance_thread()
    if not thread:
        raise RuntimeError("Thread de relevância indisponível")
    _openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=payload_json
    )
    run = _openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    return _poll_run(thread.id, run.id, timeout=60)

def _extract_json_block(text: str) -> str:
    if "```json" in text:
        try:
            return text.split("```json",1)[1].split("```",1)[0].strip()
        except Exception:
            pass
    if "```" in text:
        try:
            return text.split("```",1)[1].split("```",1)[0].strip()
        except Exception:
            pass
    return text.strip()

def _prepare_relevance_payload(results, query, search_metadata=None):
    data = []
    for r in results:
        details = r.get('details', {})
        desc = details.get('descricaocompleta', '')
        if USE_PARTIAL_DESCRIPTION and '::' in desc:
            desc = desc.split('::')[0].strip()
        data.append({
            'position': r.get('rank', 0) or r.get('details',{}).get('rank',0),
            'description': desc
        })
    return {
        'query': query,
        'search_type': (search_metadata or {}).get('search_type','Desconhecido'),
        'results': data
    }

def _process_relevance_response(response_text, original_results):
    try:
        block = _extract_json_block(response_text)
        import json as _json
        try:
            positions = _json.loads(block)
        except Exception:
            cleaned = block.replace('[','').replace(']','').replace(',',' ')
            positions = [int(x) for x in cleaned.split() if x.isdigit()]
        if not positions:
            return original_results
        pos_set = set(positions)
        filtered = [r for r in original_results if (r.get('rank') in pos_set)]
        # Reordenar conforme ordem de positions
        order = {p:i for i,p in enumerate(positions)}
        filtered.sort(key=lambda r: order.get(r.get('rank'), 999))
        for i,r in enumerate(filtered,1):
            r['rank'] = i
        return filtered
    except Exception as e:
        if DEBUG_RELEVANCE_FILTER:
            print(f"⚠️ Erro processando resposta relevância: {e}")
        return original_results

def apply_relevance_filter(results, query, search_metadata=None):
    if RELEVANCE_FILTER_LEVEL == 1 or not results:
        return results, {'filter_applied': False, 'level': RELEVANCE_FILTER_LEVEL}
    if not _RELEVANCE_AVAILABLE:
        return results, {'filter_applied': False, 'reason':'OpenAI indisponível','level':RELEVANCE_FILTER_LEVEL}
    assistant_id = _get_current_assistant_id()
    if not assistant_id:
        return results, {'filter_applied': False, 'reason':'Assistant não definido','level':RELEVANCE_FILTER_LEVEL}
    try:
        import json as _json
        payload = _prepare_relevance_payload(results, query, search_metadata)
        if DEBUG_RELEVANCE_FILTER:
            print(f"🔍 Relevância Nível {RELEVANCE_FILTER_LEVEL} - Enviando {len(payload['results'])} resultados")
        response = _call_relevance_assistant(assistant_id, _json.dumps(payload, ensure_ascii=False))
        filtered = _process_relevance_response(response, results)
        return filtered, {
            'filter_applied': True,
            'original_count': len(results),
            'filtered_count': len(filtered),
            'level': RELEVANCE_FILTER_LEVEL
        }
    except Exception as e:
        if DEBUG_RELEVANCE_FILTER:
            print(f"⚠️ Filtro relevância falhou: {e}")
        return results, {'filter_applied': False, 'reason': str(e), 'level': RELEVANCE_FILTER_LEVEL}

def set_relevance_filter_level(level: int):
    global RELEVANCE_FILTER_LEVEL
    if level not in (1,2,3):
        raise ValueError('Nível deve ser 1,2 ou 3')
    RELEVANCE_FILTER_LEVEL = level
    if DEBUG_RELEVANCE_FILTER:
        names={1:'Sem filtro',2:'Flexível',3:'Restritivo'}
        print(f"🎯 Filtro de Relevância: {names[level]} (nível {level})")

def toggle_relevance_filter(enable: bool=True):
    if enable:
        if RELEVANCE_FILTER_LEVEL==1:
            set_relevance_filter_level(2)
    else:
        set_relevance_filter_level(1)

def get_relevance_filter_status():
    return {
        'level': RELEVANCE_FILTER_LEVEL,
        'enabled': RELEVANCE_FILTER_LEVEL>1,
        'openai_available': _RELEVANCE_AVAILABLE,
        'partial_description': USE_PARTIAL_DESCRIPTION
    }

def toggle_relevance_filter_debug(enable: bool=True):
    global DEBUG_RELEVANCE_FILTER
    DEBUG_RELEVANCE_FILTER = enable
    print(f"🐛 Debug Relevância: {'ATIVADO' if enable else 'DESATIVADO'}")

# Configurações
MAX_RESULTS = 30
MIN_RESULTS = 5
SEMANTIC_WEIGHT = 0.75
DEFAULT_FILTER_EXPIRED = True
DEFAULT_USE_NEGATION = True

# Flags globais para funcionalidades inteligentes
ENABLE_INTELLIGENT_PROCESSING = True
DEBUG_INTELLIGENT_QUERIES = False


def _safe_close(cursor, conn):
    try:
        if cursor: cursor.close()
    finally:
        if conn: conn.close()

def _get_processed(query_text: str):
    """Executa processamento inteligente com fallback simples."""
    processed = {
        'original_query': query_text,
        'search_terms': query_text,
        'sql_conditions': [],
        'explanation': 'Processamento não aplicado'
    }
    try:
        if ENABLE_INTELLIGENT_PROCESSING:
            from gvg_preprocessing import SearchQueryProcessor
            processor = SearchQueryProcessor()
            candidate = processor.process_query(query_text)
            if isinstance(candidate, dict):
                aliases = {
                    'original_query': ['original_query','raw_query','query_original'],
                    'search_terms': ['search_terms','terms','termos_busca'],
                    'sql_conditions': ['sql_conditions','conditions','condicoes_sql'],
                    'explanation': ['explanation','explicacao','explain']
                }
                for target, keys in aliases.items():
                    for k in keys:
                        if k in candidate and candidate[k] is not None:
                            processed[target] = candidate[k]
                            break
                if not isinstance(processed.get('sql_conditions'), list):
                    processed['sql_conditions'] = []
                if not processed.get('search_terms'):
                    processed['search_terms'] = query_text
                if not processed.get('original_query'):
                    processed['original_query'] = query_text
                if not processed.get('explanation'):
                    processed['explanation'] = 'Processamento aplicado'
            else:
                if DEBUG_INTELLIGENT_QUERIES:
                    print(f"⚠️ Preprocessor retorno inesperado: {type(candidate)}")
    except Exception as e:
        if DEBUG_INTELLIGENT_QUERIES:
            print(f"⚠️ Falha preprocessamento: {e}")
    return processed

def _ensure_vector_cast(param_placeholder: str = "%s"):
    """Retorna expressão de cast para vetor (compat pgvector)."""
    return f"{param_placeholder}::vector"

def semantic_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS,
                    filter_expired=DEFAULT_FILTER_EXPIRED,
                    use_negation=DEFAULT_USE_NEGATION,
                    intelligent_mode=True):
    """Busca semântica (equivalente ao intelligent_semantic_search do v3 sem o prefixo).
    Inclui processamento inteligente, aplicação opcional de condições SQL, filtro de relevância (se disponível)
    e detecção dinâmica de schema (CamelCase vs snake_case)."""
    conn = None; cursor = None
    try:
        processed = _get_processed(query_text) if (intelligent_mode and ENABLE_INTELLIGENT_PROCESSING) else {
            'original_query': query_text,
            'search_terms': query_text,
            'sql_conditions': [],
            'explanation': 'Processamento desativado'
        }
        # Guardar termos originais (para embedding com negação)
        original_terms_for_embedding = (processed.get('search_terms') or processed.get('original_query') or query_text)
        search_terms = processed['search_terms'] or query_text
        # Usar somente termos positivos para condições SQL sem perder negativos para embedding
        if ENABLE_INTELLIGENT_PROCESSING and search_terms:
            pos_only, _neg = extract_pos_neg_terms(original_terms_for_embedding)
            if pos_only and pos_only.strip():
                processed['search_terms'] = pos_only.strip()
                search_terms = processed['search_terms']
        embedding_input = original_terms_for_embedding  # mantém negativos
        sql_conditions = processed.get('sql_conditions', [])

        # Embedding com suporte avançado a negação (não depende apenas de '--')
        if use_negation:
            emb = get_negation_embedding(embedding_input)
        else:
            emb = get_embedding(embedding_input)
        if emb is None:
            return [], 0.0
        if isinstance(emb, np.ndarray):
            emb_vec = emb.tolist()
        else:
            emb_vec = emb

        conn = create_connection()
        if not conn:
            return [], 0.0
        cursor = conn.cursor()

        # Query idêntica ao v3 (lista de colunas CamelCase + embedding_vector)
        base_query = [
            "SELECT",
            "  c.numeroControlePNCP,",
            "  c.anoCompra,",
            "  c.descricaoCompleta,",
            "  c.valorTotalHomologado,",
            "  c.valorTotalEstimado,",
            "  c.dataAberturaProposta,",
            "  c.dataEncerramentoProposta,",
            "  c.dataInclusao,",
            "  c.linkSistemaOrigem,",
            "  c.modalidadeId,",
            "  c.modalidadeNome,",
            "  c.modaDisputaId,",
            "  c.modaDisputaNome,",
            "  c.usuarioNome,",
            "  c.orgaoEntidade_poderId,",
            "  c.orgaoEntidade_esferaId,",
            "  c.unidadeOrgao_ufSigla,",
            "  c.unidadeOrgao_municipioNome,",
            "  c.unidadeOrgao_nomeUnidade,",
            "  c.orgaoEntidade_razaosocial,",
            "  1 - (e.embedding_vector <=> %s::vector) AS similarity",
            "FROM contratacoes c",
            "JOIN contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP",
            "WHERE e.embedding_vector IS NOT NULL"
        ]
        params = [emb_vec]
        if filter_expired:
            base_query.append("AND c.dataEncerramentoProposta >= CURRENT_DATE")
        for cond in sql_conditions:
            base_query.append(f"AND {cond}")
        base_query.append("ORDER BY similarity DESC")
        base_query.append("LIMIT %s")
        params.append(limit)
        final_sql = "\n".join(base_query)

        cursor.execute(final_sql, params)
        rows = cursor.fetchall()

        column_names = [d[0] for d in cursor.description]
        results = []
        sims = []
        for idx, row in enumerate(rows):
            record = dict(zip(column_names, row))
            similarity = float(record['similarity'])
            sims.append(similarity)
            out = {
                'id': record.get('numerocontrolepncp'),
                'numero_controle': record.get('numerocontrolepncp'),
                'similarity': similarity,
                'rank': idx + 1,
                'details': record
            }
            if intelligent_mode:
                out['details']['intelligent_processing'] = {
                    'original_query': processed.get('original_query', query_text),
                    'processed_terms': processed.get('search_terms', query_text),
                    'applied_conditions': len(sql_conditions),
                    'explanation': processed.get('explanation','')
                }
            results.append(out)
        # Aplicar filtro de relevância se disponível
        if apply_relevance_filter and RELEVANCE_FILTER_LEVEL > 1 and results:
            meta = {
                'search_type': 'Semântica' + (' (Inteligente)' if intelligent_mode else ''),
                'search_approach': 'Direta',
                'sort_mode': 'Similaridade'
            }
            try:
                filtered, _filter_info = apply_relevance_filter(results, query_text, meta)
                if filtered:
                    results = filtered
            except Exception as rf_err:
                if DEBUG_INTELLIGENT_QUERIES:
                    print(f"⚠️ Filtro de relevância falhou: {rf_err}")
        return results, calculate_confidence([r['similarity'] for r in results])
    except Exception as e:
        print(f"Erro na busca semântica: {e}")
        return [], 0.0
    finally:
        _safe_close(cursor, conn)

def keyword_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS,
                   filter_expired=DEFAULT_FILTER_EXPIRED,
                   intelligent_mode=True):
    """Busca por palavras‑chave (equivalente ao intelligent_keyword_search do v3 sem prefixo).
    Usa full‑text (tsvector) + fallback ILIKE + filtro de relevância opcional."""
    conn=None; cursor=None
    try:
        processed = _get_processed(query_text) if (intelligent_mode and ENABLE_INTELLIGENT_PROCESSING) else {
            'original_query': query_text,
            'search_terms': query_text,
            'sql_conditions': [],
            'explanation': 'Processamento desativado'
        }
        original_terms_for_embedding = (processed.get('search_terms') or processed.get('original_query') or query_text)
        search_terms = processed['search_terms'] or query_text
        if ENABLE_INTELLIGENT_PROCESSING and search_terms:
            pos_only, _neg = extract_pos_neg_terms(original_terms_for_embedding)
            if pos_only and pos_only.strip():
                processed['search_terms'] = pos_only.strip()
                search_terms = processed['search_terms']
        embedding_input = original_terms_for_embedding
        sql_conditions = processed.get('sql_conditions', [])

        conn = create_connection()
        if not conn:
            return [], 0.0
        cursor = conn.cursor()

        terms_split = [t for t in search_terms.split() if t]
        if not terms_split:
            return [], 0.0
        tsquery = ' & '.join(terms_split)
        tsquery_prefix = ':* & '.join(terms_split) + ':*'

        # Query full‑text idêntica à usada no v3 (sem join com embeddings)
        base = [
            "SELECT",
            "  c.numeroControlePNCP,",
            "  c.anoCompra,",
            "  c.descricaoCompleta,",
            "  c.valorTotalHomologado,",
            "  c.valorTotalEstimado,",
            "  c.dataAberturaProposta,",
            "  c.dataEncerramentoProposta,",
            "  c.dataInclusao,",
            "  c.linkSistemaOrigem,",
            "  c.modalidadeId,",
            "  c.modalidadeNome,",
            "  c.modaDisputaId,",
            "  c.modaDisputaNome,",
            "  c.usuarioNome,",
            "  c.orgaoEntidade_poderId,",
            "  c.orgaoEntidade_esferaId,",
            "  c.unidadeOrgao_ufSigla,",
            "  c.unidadeOrgao_municipioNome,",
            "  c.unidadeOrgao_nomeUnidade,",
            "  c.orgaoEntidade_razaosocial,",
            "  ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank,",
            "  ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank_prefix",
            "FROM contratacoes c",
            "WHERE (",
            "  to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)",
            "  OR to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)",
            ")"
        ]
        if filter_expired:
            base.append("AND c.dataEncerramentoProposta >= CURRENT_DATE")
        for cond in sql_conditions:
            base.append(f"AND {cond}")
        base.append("ORDER BY (ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.7 + ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.3) DESC")
        base.append("LIMIT %s")
        sql = "\n".join(base)
        params = [tsquery, tsquery_prefix, tsquery, tsquery_prefix, tsquery, tsquery_prefix, limit]
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results=[]; sims=[]
            for i,row in enumerate(rows):
                # Últimos dois valores são rank e rank_prefix
                rank_val = float(row[-2]); rank_prefix_val = float(row[-1])
                max_possible = max(len(terms_split)*0.1, 0.0001)
                combined = (rank_val*0.7 + rank_prefix_val*0.3) / max_possible
                similarity = min(combined, 1.0)
                sims.append(similarity)
                details = {
                    'numerocontrolepncp': row[0],
                    'anocompra': row[1],
                    'descricaocompleta': row[2],
                    'valortotalhomologado': row[3],
                    'valortotalestimado': row[4],
                    'dataaberturaproposta': row[5],
                    'dataencerramentoproposta': row[6],
                    'datainclusao': row[7],
                    'linksistemaorigem': row[8],
                    'modalidadeid': row[9],
                    'modalidadenome': row[10],
                    'modadisputaid': row[11],
                    'modadisputanome': row[12],
                    'usuarionome': row[13],
                    'orgaoentidade_poderid': row[14],
                    'orgaoentidade_esferaid': row[15],
                    'unidadeorgao_ufsigla': row[16],
                    'unidadeorgao_municipionome': row[17],
                    'unidadeorgao_nomeunidade': row[18],
                    'orgaoentidade_razaosocial': row[19],
                    'rank': rank_val,
                    'rank_prefix': rank_prefix_val
                }
                if intelligent_mode:
                    details['intelligent_processing'] = {
                        'original_query': processed.get('original_query', query_text),
                        'processed_terms': processed['search_terms'],
                        'applied_conditions': len(sql_conditions),
                        'explanation': processed.get('explanation','')
                    }
                results.append({
                    'id': row[0],
                    'numero_controle': row[0],
                    'similarity': similarity,
                    'rank': i + 1,
                    'details': details
                })
            if apply_relevance_filter and RELEVANCE_FILTER_LEVEL > 1 and results:
                meta = {
                    'search_type': 'Palavras‑chave' + (' (Inteligente)' if intelligent_mode else ''),
                    'search_approach': 'Direta',
                    'sort_mode': 'Relevância'
                }
                try:
                    filtered, _ = apply_relevance_filter(results, query_text, meta)
                    if filtered:
                        results = filtered
                except Exception as rf_err:
                    if DEBUG_INTELLIGENT_QUERIES:
                        print(f"⚠️ Filtro de relevância falhou: {rf_err}")
            return results, calculate_confidence([r['similarity'] for r in results])
        except Exception as fe:
            # Fallback ILIKE
            if DEBUG_INTELLIGENT_QUERIES:
                print(f"⚠️ Full-text indisponível, fallback ILIKE: {fe}")
            fallback_sql = """
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
                    c.orgaoEntidade_razaosocial
                FROM contratacoes c
                WHERE (LOWER(c.descricaoCompleta) ILIKE %s)
            """
            pattern = f"%{search_terms.lower()}%"
            if filter_expired:
                fallback_sql += " AND c.dataEncerramentoProposta >= CURRENT_DATE"
            for cond in sql_conditions:
                fallback_sql += f" AND {cond}"
            fallback_sql += " ORDER BY c.dataInclusao DESC LIMIT %s"
            cursor.execute(fallback_sql, [pattern, pattern, limit])
            rows = cursor.fetchall(); results=[]; sims=[]
            for i,row in enumerate(rows):
                similarity = max(1.0 - i*0.05, 0.0)
                sims.append(similarity)
                details = {
                    'numerocontrolepncp': row[0],
                    'anocompra': row[1],
                    'descricaocompleta': row[2],
                    'valortotalhomologado': row[3],
                    'valortotalestimado': row[4],
                    'dataaberturaproposta': row[5],
                    'dataencerramentoproposta': row[6],
                    'datainclusao': row[7],
                    'linksistemaorigem': row[8],
                    'modalidadeid': row[9],
                    'modalidadenome': row[10],
                    'modadisputaid': row[11],
                    'modadisputanome': row[12],
                    'usuarionome': row[13],
                    'orgaoentidade_poderid': row[14],
                    'orgaoentidade_esferaid': row[15],
                    'unidadeorgao_ufsigla': row[16],
                    'unidadeorgao_municipionome': row[17],
                    'unidadeorgao_nomeunidade': row[18],
                    'orgaoentidade_razaosocial': row[19]
                }
                results.append({
                    'id': row[0],
                    'numero_controle': row[0],
                    'similarity': similarity,
                    'details': details
                })
            for idx, r in enumerate(results):
                r['rank'] = idx + 1
            if apply_relevance_filter and RELEVANCE_FILTER_LEVEL > 1 and results:
                meta = {
                    'search_type': 'Palavras‑chave (Fallback)',
                    'search_approach': 'Direta',
                    'sort_mode': 'Relevância'
                }
                try:
                    filtered, _ = apply_relevance_filter(results, query_text, meta)
                    if filtered:
                        results = filtered
                except Exception as rf_err:
                    if DEBUG_INTELLIGENT_QUERIES:
                        print(f"⚠️ Filtro de relevância falhou: {rf_err}")
            return results, calculate_confidence([r['similarity'] for r in results])
    except Exception as e:
        print(f"Erro na busca por palavras-chave: {e}")
        return [], 0.0
    finally:
        _safe_close(cursor, conn)

def hybrid_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS,
                  semantic_weight=SEMANTIC_WEIGHT,
                  filter_expired=DEFAULT_FILTER_EXPIRED,
                  use_negation=DEFAULT_USE_NEGATION,
                  intelligent_mode=True):
    """Busca híbrida (equivalente ao intelligent_hybrid_search do v3 sem prefixo).
    Combina similaridade + full‑text em SQL único; fallback para fusão Python;
    aplica filtro de relevância se disponível."""
    conn=None; cursor=None
    try:
        processed = _get_processed(query_text) if (intelligent_mode and ENABLE_INTELLIGENT_PROCESSING) else {
            'original_query': query_text,
            'search_terms': query_text,
            'sql_conditions': [],
            'explanation': 'Processamento desativado'
        }
        original_terms_for_embedding = (processed.get('search_terms') or processed.get('original_query') or query_text)
        search_terms = processed['search_terms'] or query_text
        # Limpar termos para condições (somente positivos) sem perder negativos para embedding
        if ENABLE_INTELLIGENT_PROCESSING and search_terms:
            pos_only, _neg = extract_pos_neg_terms(original_terms_for_embedding)
            if pos_only and pos_only.strip():
                processed['search_terms'] = pos_only.strip()
                search_terms = processed['search_terms']
        embedding_input = original_terms_for_embedding
        sql_conditions = processed.get('sql_conditions', [])

        # Embedding com suporte avançado a negação (não depende apenas de '--')
        if use_negation:
            emb = get_negation_embedding(embedding_input)
        else:
            emb = get_embedding(embedding_input)
        if emb is None:
            return [], 0.0
        if isinstance(emb, np.ndarray):
            emb_vec = emb.tolist()
        else:
            emb_vec = emb

        terms_split = [t for t in search_terms.split() if t]
        tsquery = ' & '.join(terms_split) if terms_split else search_terms
        tsquery_prefix = ':* & '.join(terms_split) + ':*' if terms_split else search_terms
        max_possible_keyword_score = max(len(terms_split)*0.1, 0.0001)

        conn = create_connection()
        if not conn:
            return [], 0.0
        cursor = conn.cursor()

        base = [
            "SELECT",
            "  c.numeroControlePNCP,",
            "  c.anoCompra,",
            "  c.descricaoCompleta,",
            "  c.valorTotalHomologado,",
            "  c.valorTotalEstimado,",
            "  c.dataAberturaProposta,",
            "  c.dataEncerramentoProposta,",
            "  c.dataInclusao,",
            "  c.linkSistemaOrigem,",
            "  c.modalidadeId,",
            "  c.modalidadeNome,",
            "  c.modaDisputaId,",
            "  c.modaDisputaNome,",
            "  c.usuarioNome,",
            "  c.orgaoEntidade_poderId,",
            "  c.orgaoEntidade_esferaId,",
            "  c.unidadeOrgao_ufSigla,",
            "  c.unidadeOrgao_municipioNome,",
            "  c.unidadeOrgao_nomeUnidade,",
            "  c.orgaoEntidade_razaosocial,",
            "  (1 - (e.embedding_vector <=> %s::vector)) AS semantic_score,",
            "  COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)),0) AS keyword_score,",
            "  COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)),0) AS keyword_prefix_score,",
            "  ( %s * (1 - (e.embedding_vector <=> %s::vector)) + (1 - %s) * LEAST((0.7 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) + 0.3 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s))) ) / %s, 1.0) ) AS combined_score",
            "FROM contratacoes c",
            "JOIN contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP",
            "WHERE e.embedding_vector IS NOT NULL"
        ]
        if filter_expired:
            base.append("AND c.dataEncerramentoProposta >= CURRENT_DATE")
        for cond in sql_conditions:
            base.append(f"AND {cond}")
        base.append("ORDER BY combined_score DESC")
        base.append("LIMIT %s")
        sql = "\n".join(base)
        params = [emb_vec, tsquery, tsquery_prefix, semantic_weight, emb_vec, semantic_weight, tsquery, tsquery_prefix, max_possible_keyword_score, limit]
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall(); results=[]; sims=[]
            for idx, r in enumerate(rows):
                combined = float(r[-1]); sims.append(combined)
                details = {
                    'numerocontrolepncp': r[0],
                    'anocompra': r[1],
                    'descricaocompleta': r[2],
                    'valortotalhomologado': r[3],
                    'valortotalestimado': r[4],
                    'dataaberturaproposta': r[5],
                    'dataencerramentoproposta': r[6],
                    'datainclusao': r[7],
                    'linksistemaorigem': r[8],
                    'modalidadeid': r[9],
                    'modalidadenome': r[10],
                    'modadisputaid': r[11],
                    'modadisputanome': r[12],
                    'usuarionome': r[13],
                    'orgaoentidade_poderid': r[14],
                    'orgaoentidade_esferaid': r[15],
                    'unidadeorgao_ufsigla': r[16],
                    'unidadeorgao_municipionome': r[17],
                    'unidadeorgao_nomeunidade': r[18],
                    'orgaoentidade_razaosocial': r[19],
                    'semantic_score': r[20],
                    'keyword_score': r[21],
                    'keyword_prefix_score': r[22]
                }
                if intelligent_mode:
                    details['intelligent_processing'] = {
                        'original_query': processed.get('original_query', query_text),
                        'processed_terms': processed['search_terms'],
                        'applied_conditions': len(sql_conditions),
                        'explanation': processed.get('explanation','')
                    }
                results.append({
                    'id': r[0],
                    'numero_controle': r[0],
                    'similarity': combined,
                    'rank': idx + 1,
                    'details': details
                })
            if apply_relevance_filter and RELEVANCE_FILTER_LEVEL > 1 and results:
                meta = {
                    'search_type': 'Híbrida' + (' (Inteligente)' if intelligent_mode else ''),
                    'search_approach': 'Direta',
                    'sort_mode': 'Híbrida'
                }
                try:
                    filtered, _ = apply_relevance_filter(results, query_text, meta)
                    if filtered:
                        results = filtered
                except Exception as rf_err:
                    if DEBUG_INTELLIGENT_QUERIES:
                        print(f"⚠️ Filtro de relevância falhou: {rf_err}")
            return results, calculate_confidence([r['similarity'] for r in results])
        except Exception as fe:
            if DEBUG_INTELLIGENT_QUERIES:
                print(f"⚠️ Híbrida SQL única falhou, fallback dupla: {fe}")
            # Fallback: combinar duas buscas
            sem_results, sem_conf = semantic_search(query_text, limit, min_results, filter_expired, use_negation, intelligent_mode)
            kw_results, kw_conf = keyword_search(query_text, limit, min_results, filter_expired, intelligent_mode)
            combined = {}
            for r in sem_results:
                combined[r['numero_controle']] = {
                    **r,
                    'semantic_similarity': r['similarity'],
                    'keyword_similarity': 0.0,
                    'similarity': r['similarity'] * semantic_weight
                }
            kw_weight = 1 - semantic_weight
            for r in kw_results:
                if r['numero_controle'] in combined:
                    combined[r['numero_controle']]['similarity'] += r['similarity'] * kw_weight
                    combined[r['numero_controle']]['keyword_similarity'] = r['similarity']
                else:
                    combined[r['numero_controle']] = {
                        **r,
                        'semantic_similarity': 0.0,
                        'keyword_similarity': r['similarity'],
                        'similarity': r['similarity'] * kw_weight
                    }
            final = list(combined.values())
            final.sort(key=lambda x: x['similarity'], reverse=True)
            final = final[:limit]
            # Adicionar rank e aplicar filtro de relevância se disponível
            for idx, r in enumerate(final):
                r['rank'] = idx + 1
            if apply_relevance_filter and RELEVANCE_FILTER_LEVEL > 1 and final:
                meta = {
                    'search_type': 'Híbrida (Fallback)',
                    'search_approach': 'Fusão',
                    'sort_mode': 'Híbrida'
                }
                try:
                    filtered, _ = apply_relevance_filter(final, query_text, meta)
                    if filtered:
                        final = filtered
                except Exception as rf_err:
                    if DEBUG_INTELLIGENT_QUERIES:
                        print(f"⚠️ Filtro de relevância falhou: {rf_err}")
            conf = sem_conf*semantic_weight + kw_conf*kw_weight
            return final, conf
    except Exception as e:
        print(f"Erro na busca híbrida: {e}")
        return [], 0.0
    finally:
        _safe_close(cursor, conn)

def toggle_intelligent_processing(enable: bool = True):
    """
    Ativa/desativa o processamento inteligente de queries
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global ENABLE_INTELLIGENT_PROCESSING
    ENABLE_INTELLIGENT_PROCESSING = enable
    status = "ATIVADO" if enable else "DESATIVADO"
    print(f"🧠 Processamento Inteligente: {status}")

def toggle_intelligent_debug(enable: bool = True):
    """
    Ativa/desativa debug das queries inteligentes
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global DEBUG_INTELLIGENT_QUERIES
    DEBUG_INTELLIGENT_QUERIES = enable
    status = "ATIVADO" if enable else "DESATIVADO" 
    print(f"🐛 Debug Inteligente: {status}")

def get_intelligent_status():
    """
    Retorna status atual do sistema inteligente
    
    Returns:
        dict: Status das funcionalidades inteligentes
    """
    return {
        'intelligent_processing': ENABLE_INTELLIGENT_PROCESSING,
        'debug_mode': DEBUG_INTELLIGENT_QUERIES,
        'status': 'ATIVO' if ENABLE_INTELLIGENT_PROCESSING else 'INATIVO'
    }
