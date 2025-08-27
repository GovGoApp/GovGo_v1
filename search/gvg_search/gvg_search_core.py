"""
gvg_search_core.py
Módulo otimizado para funções de busca principais GvG
Contém apenas as funções de busca realmente utilizadas com IA integrada
"""

import os
import re
import time
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import psycopg2

# ============================================================================
# NOTA: Este módulo foi atualizado para replicar as queries e funcionalidades
#       avançadas do antigo gvg_search_utils_v3 (semantic / keyword / hybrid)
#       mantendo compatibilidade com o schema atual (snake_case) e provendo
#       fallbacks seguros quando features (tsvector ou colunas) não existirem.
# ============================================================================

# Importações dos módulos otimizados
from gvg_database import create_connection
from gvg_ai_utils import get_embedding, get_negation_embedding, calculate_confidence
from gvg_schema import (
	CONTRATACAO_TABLE, CONTRATACAO_EMB_TABLE, CATEGORIA_TABLE,
	PRIMARY_KEY, EMB_VECTOR_FIELD, CATEGORY_VECTOR_FIELD,
	build_semantic_select, get_contratacao_core_columns, build_category_similarity_select,
	CONTRATACAO_FIELDS
)

# ============================================================================
# Filtro de Relevância interno (removida dependência de gvg_search_utils_v3)
# Implementa sistema de 3 níveis com uso opcional de OpenAI Assistant.
# Nível 1: desativado | Nível 2: flexível | Nível 3: restritivo
# ============================================================================
RELEVANCE_FILTER_LEVEL = 1  # 1=sem filtro, 2=flexível, 3=restritivo
DEBUG_RELEVANCE_FILTER = False
USE_PARTIAL_DESCRIPTION = True

# IDs de assistants de relevância (Flexível e Restritivo)
RELEVANCE_ASSISTANT_FLEXIBLE = os.getenv("GVG_RELEVANCE_FLEXIBLE", "asst_tfD5oQxSgoGhtqdKQHK9UwRi")
RELEVANCE_ASSISTANT_RESTRICTIVE = os.getenv("GVG_RELEVANCE_RESTRICTIVE", "asst_XmsefQEKbuVWu51uNST7kpYT")

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
except Exception:
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
		desc = details.get('objeto_compra', '')
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
					'negative_terms': ['negative_terms','negatives','termos_negativos'],
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

# --------------------------------------------------------------
# Sanitização de condições SQL retornadas pelo Assistant
# - Escapa placeholders "%s" para não conflitar com psycopg2
# - Ajusta c.ano_compra comparando com números (ano_compra é TEXT)
# - BETWEEN/IN com anos numéricos -> strings
# - No modo keyword, remove referências a ce.* (sem JOIN de embeddings)
# --------------------------------------------------------------
def _sanitize_sql_conditions(sql_conditions, context: str = 'generic'):
	if not isinstance(sql_conditions, (list, tuple)):
		return []
	out = []
	for cond in sql_conditions:
		if not isinstance(cond, str):
			continue
		c = cond
		# Escapar placeholders literais
		if '%s' in c:
			c = c.replace('%s', '%%s')
		# ano_compra comparações numéricas -> strings
		# ex: c.ano_compra <= 2026  => c.ano_compra <= '2026'
		c = re.sub(r"\bc\.ano_compra\s*(=|<>|!=|<=|>=|<|>)\s*(\d{4})\b", lambda m: f"c.ano_compra {m.group(1)} '{m.group(2)}'", c, flags=re.IGNORECASE)
		# BETWEEN
		c = re.sub(r"\bc\.ano_compra\s+BETWEEN\s+(\d{4})\s+AND\s+(\d{4})\b", lambda m: f"c.ano_compra BETWEEN '{m.group(1)}' AND '{m.group(2)}'", c, flags=re.IGNORECASE)
		# IN (anos)
		def _quote_in_years(match):
			inside = match.group(1)
			nums = re.findall(r"\d{4}", inside)
			if nums:
				quoted = ",".join(f"'{n}'" for n in nums)
				return f"c.ano_compra IN ({quoted})"
			return match.group(0)
		c = re.sub(r"\bc\.ano_compra\s+IN\s*\(([^)]*)\)", _quote_in_years, c, flags=re.IGNORECASE)
		# No keyword mode, evitar ce.*
		if context == 'keyword' and re.search(r"\bce\.", c, flags=re.IGNORECASE):
			continue
		out.append(c)
	return out

# --------------------------------------------------------------
# Compatibilidade: gerar aliases adicionais nos detalhes para que
# código legado que procura chaves sem underscore ou variantes
# (ex: modadisputanome) não resulte em N/A.
# --------------------------------------------------------------
_ALIAS_SPECIAL = {
	'modo_disputa_id': ['modadisputaid','modaDisputaId'],
	'modo_disputa_nome': ['modadisputanome','modaDisputaNome'],
	'orgao_entidade_razao_social': ['orgaoentidade_razaosocial','nomeorgaoentidade','orgaoEntidade_razaosocial'],
	'unidade_orgao_nome_unidade': ['unidadeorgao_nomeunidade','unidadeOrgao_nomeUnidade'],
	'unidade_orgao_municipio_nome': ['unidadeorgao_municipionome','unidadeorgao_municipioNome','unidadeOrgao_municipioNome','municipioentidade'],
	'unidade_orgao_uf_sigla': ['unidadeorgao_ufsigla','unidadeOrgao_ufSigla','uf'],
	'objeto_compra': ['objeto','descricaoCompleta'],
	'valor_total_estimado': ['valortotalestimado','valorTotalEstimado'],
	'valor_total_homologado': ['valortotalhomologado','valorTotalHomologado','valorfinal','valorFinal'],
	'data_encerramento_proposta': ['dataencerramentoproposta','dataEncerramentoProposta','dataEncerramento'],
	'data_abertura_proposta': ['dataaberturaproposta','dataAberturaProposta'],
	'modalidade_nome': ['modalidadenome','modalidadeNome'],
	'modalidade_id': ['modalidadeid','modalidadeId']
}
def _augment_aliases(d: dict):
	try:
		items = list(d.items())
		for k,v in items:
			if v in (None,''):
				continue
			flat = k.replace('_','')
			if flat not in d:
				d[flat] = v
			if k in _ALIAS_SPECIAL:
				for alt in _ALIAS_SPECIAL[k]:
					if alt not in d:
						d[alt] = v
	except Exception:
		pass
	return d

def semantic_search(query_text,
					limit: int = MAX_RESULTS,
					min_results: int = MIN_RESULTS,
					filter_expired: bool = DEFAULT_FILTER_EXPIRED,
					use_negation: bool = DEFAULT_USE_NEGATION,
					intelligent_mode: bool = True,
					category_codes: Optional[List[str]] = None,
					pre_limit_ids: Optional[int] = None,
					pre_knn_limit: Optional[int] = None):
	"""Busca semântica usando builder centralizado de SELECT.

	Agora utiliza `build_semantic_select` para evitar repetição de lista de colunas.
	"""
	conn = None
	cursor = None
	try:
		processed = _get_processed(query_text) if (intelligent_mode and ENABLE_INTELLIGENT_PROCESSING) else {
			'original_query': query_text,
			'search_terms': query_text,
			'negative_terms': '',
			'sql_conditions': [],
			'explanation': 'Processamento desativado'
		}
		negative_terms = processed.get('negative_terms') or ''
		search_terms = processed.get('search_terms') or query_text
		embedding_input = f"{search_terms} -- {negative_terms}".strip() if negative_terms else search_terms
		sql_conditions = processed.get('sql_conditions', [])

		emb = get_negation_embedding(embedding_input) if use_negation else get_embedding(embedding_input)
		if emb is None:
			return [], 0.0
		emb_vec = emb.tolist() if isinstance(emb, np.ndarray) else emb

		conn = create_connection()
		if not conn:
			return [], 0.0
		cursor = conn.cursor()

		vector_opt_enabled = os.getenv("GVG_VECTOR_OPT", "1") != "0"
		executed_optimized = False
		sql_debug = os.getenv("GVG_SQL_DEBUG", "0") != "0"
		sql_conditions_sanitized = _sanitize_sql_conditions(sql_conditions, context='semantic')

		if vector_opt_enabled:
			try:
				core_cols = get_contratacao_core_columns('c')
				core_cols_expr = ",\n  ".join(core_cols)
				pre_ids = pre_limit_ids if pre_limit_ids is not None else int(os.getenv("GVG_PRE_ID_LIMIT", "50000"))
				pre_knn = pre_knn_limit if pre_knn_limit is not None else int(os.getenv("GVG_PRE_KNN_LIMIT", "5000"))

				where_cand = ["ce.embeddings IS NOT NULL"]
				if filter_expired:
					where_cand.append("to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE")
				for cond in sql_conditions_sanitized:
					where_cand.append(cond)
				include_categories = bool(category_codes)
				if include_categories:
					where_cand.append("ce.top_categories && %s::text[]")

				cte_parts = [
					"WITH candidatos AS (",
					f"  SELECT ce.{PRIMARY_KEY}",
					f"  FROM {CONTRATACAO_EMB_TABLE} ce",
					f"  JOIN {CONTRATACAO_TABLE} c ON c.{PRIMARY_KEY} = ce.{PRIMARY_KEY}",
					"  WHERE " + " AND ".join(where_cand),
					"  LIMIT %s",
					")",
					" , base AS (",
					f"  SELECT ce.{PRIMARY_KEY}, (ce.{EMB_VECTOR_FIELD} <=> %s::vector) AS distance",
					f"  FROM {CONTRATACAO_EMB_TABLE} ce",
					f"  JOIN candidatos x ON x.{PRIMARY_KEY} = ce.{PRIMARY_KEY}",
					"  ORDER BY distance ASC",
					"  LIMIT %s",
					")",
					"SELECT",
					f"  {core_cols_expr},",
					"  (1 - base.distance) AS similarity",
					f"FROM base JOIN {CONTRATACAO_TABLE} c ON c.{PRIMARY_KEY} = base.{PRIMARY_KEY}",
					"ORDER BY similarity DESC",
					"LIMIT %s"
				]
				final_sql = "\n".join(cte_parts)

				params: List[Any] = []
				if include_categories:
					params.append(category_codes)
				params.append(pre_ids)
				params.append(emb_vec)
				params.append(pre_knn)
				params.append(limit)

				if sql_debug or DEBUG_INTELLIGENT_QUERIES:
					print("\n[SQL][semantic_opt]")
					print(final_sql)
					print(f"params: categories={'Y' if include_categories else 'N'}, pre_ids={pre_ids}, pre_knn={pre_knn}, final_limit={limit}, emb_dim=3072")

				cursor.execute(final_sql, params)
				executed_optimized = True
			except Exception as opt_err:
				if DEBUG_INTELLIGENT_QUERIES or sql_debug:
					print(f"⚠️ Vetor otimizado falhou: {opt_err}")
				try:
					if conn:
						conn.rollback()
				except Exception:
					pass
				executed_optimized = False

		if not executed_optimized:
			base_query = [build_semantic_select('%s').rstrip()]
			params = [emb_vec]
			if category_codes:
				base_query.append("AND ce.top_categories && %s::text[]")
				params.append(category_codes)
			if filter_expired:
				base_query.append("AND to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE")
			for cond in sql_conditions_sanitized:
				base_query.append(f"AND {cond}")
			base_query.append("ORDER BY similarity DESC")
			base_query.append("LIMIT %s")
			params.append(limit)
			final_sql = "\n".join(base_query)
			if sql_debug or DEBUG_INTELLIGENT_QUERIES:
				print("\n[SQL][semantic_fallback]")
				print(final_sql)
				print(f"params: categories={'Y' if bool(category_codes) else 'N'}, final_limit={limit}, emb_dim=3072")
			cursor.execute(final_sql, params)

		rows = cursor.fetchall()
		column_names = [d[0] for d in cursor.description]

		results: List[Dict[str, Any]] = []
		core_keys = set(CONTRATACAO_FIELDS.keys())
		for idx, row in enumerate(rows):
			record = dict(zip(column_names, row))
			similarity = float(record['similarity'])
			details = {k: v for k, v in record.items() if k in core_keys}
			details['similarity'] = similarity
			if intelligent_mode:
				details['intelligent_processing'] = {
					'original_query': processed.get('original_query', query_text),
					'processed_terms': processed.get('search_terms', query_text),
					'applied_conditions': len(sql_conditions),
					'explanation': processed.get('explanation','')
				}
			_augment_aliases(details)
			results.append({
				'id': record.get(PRIMARY_KEY),
				'numero_controle': record.get(PRIMARY_KEY),
				'similarity': similarity,
				'rank': idx + 1,
				'details': details
			})

		if RELEVANCE_FILTER_LEVEL > 1 and results:
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
		try:
			if conn:
				conn.rollback()
		except Exception:
			pass
		if os.getenv("GVG_SQL_DEBUG", "0") != "0" or DEBUG_INTELLIGENT_QUERIES:
			print(f"[ERRO][semantic_search] {type(e).__name__}: {e}")
		print(f"Erro na busca semântica: {e}")
		return [], 0.0
	finally:
		_safe_close(cursor, conn)

def keyword_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS,
				   filter_expired=DEFAULT_FILTER_EXPIRED,
				   intelligent_mode=True):
	"""Busca por palavras‑chave usando full‑text search.

	Usa builders para colunas core e normaliza uma métrica de similaridade
	baseada nos ranks retornados pelo PostgreSQL.
	"""
	conn = None; cursor = None
	try:
		if intelligent_mode and ENABLE_INTELLIGENT_PROCESSING:
			processed = _get_processed(query_text)
		else:
			processed = {
				'original_query': query_text,
				'search_terms': query_text,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Processamento desativado'
			}
		search_terms = (processed.get('search_terms') or query_text).strip()
		negative_terms = (processed.get('negative_terms') or '').strip()
		sql_conditions = processed.get('sql_conditions', [])
		sql_conditions_sanitized = _sanitize_sql_conditions(sql_conditions, context='keyword')

		conn = create_connection()
		if not conn:
			return [], 0.0
		cursor = conn.cursor()

		terms_split = [t for t in search_terms.split() if t]
		if not terms_split:
			return [], 0.0
		tsquery = ' & '.join(terms_split)
		tsquery_prefix = ':* & '.join(terms_split) + ':*'

		# Parse negative terms -> tokens alfanuméricos únicos
		neg_tokens = []
		if negative_terms:
			raw_tokens = re.findall(r"[\wÀ-ÿ]+", negative_terms.lower())
			# remover duplicados preservando ordem
			seen = set()
			for t in raw_tokens:
				if t and t not in seen:
					seen.add(t)
					neg_tokens.append(t)

		core_cols = get_contratacao_core_columns('c')
		text_field = 'c.objeto_compra'
		base = [
			"SELECT",
			"  " + ",\n  ".join(core_cols) + ",",
			# rank principal (exato)
			f"  ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s)) AS rank_exact,",
			# rank auxiliar (prefixo) com peso menor
			f"  ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s)) AS rank_prefix",
			f"FROM {CONTRATACAO_TABLE} c",
			"WHERE (",
			f"  to_tsvector('portuguese', {text_field}) @@ to_tsquery('portuguese', %s)",
			f"  OR to_tsvector('portuguese', {text_field}) @@ to_tsquery('portuguese', %s)",
			")"
		]
		# Exclusões por termos negativos (prefix match) via NOT @@ (OR de negativos)
		if neg_tokens:
			neg_query = ' | '.join(f"{t}:*" for t in neg_tokens)
			base.append("AND NOT (to_tsvector('portuguese', {tf}) @@ to_tsquery('portuguese', %s))".format(tf=text_field))
		if filter_expired:
			base.append("AND to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE")
		for cond in sql_conditions_sanitized:
			base.append(f"AND {cond}")
		# Ordenação simplificada: combinação linear já calculada em Python; aqui priorizamos exato depois prefixo
		base.append("ORDER BY rank_exact DESC, rank_prefix DESC")
		base.append("LIMIT %s")
		sql = "\n".join(base)
		params = [tsquery, tsquery_prefix, tsquery, tsquery_prefix]
		if neg_tokens:
			params.append(neg_query)
		params.append(limit)
		sql_debug = os.getenv("GVG_SQL_DEBUG", "0") != "0"
		if sql_debug or DEBUG_INTELLIGENT_QUERIES:
			print("\n[SQL][keyword]")
			print(sql)
			print(f"params={params}")
		cursor.execute(sql, params)
		rows = cursor.fetchall()
		column_names = [d[0] for d in cursor.description]
		core_keys = set(CONTRATACAO_FIELDS.keys())
		results = []
		sims = []
		# Normalização simples: similarity = min( (rank_exact + 0.5*rank_prefix) / (0.1 * n_terms + 1e-6), 1.0 )
		denom = (0.1 * len(terms_split)) + 1e-6
		for i, row in enumerate(rows):
			rec = dict(zip(column_names, row))
			rank_exact = float(rec['rank_exact'])
			rank_prefix = float(rec['rank_prefix'])
			combined = rank_exact + 0.5 * rank_prefix
			similarity = combined / denom
			if similarity > 1.0:
				similarity = 1.0
			sims.append(similarity)
			details = {k: v for k, v in rec.items() if k in core_keys}
			details['rank_exact'] = rank_exact
			details['rank_prefix'] = rank_prefix
			details['search_terms'] = search_terms
			if negative_terms:
				details['negative_terms'] = negative_terms
			if intelligent_mode:
				details['intelligent_processing'] = {
					'original_query': processed.get('original_query', query_text),
					'processed_terms': processed['search_terms'],
					'applied_conditions': len(sql_conditions),
					'explanation': processed.get('explanation', '')
				}
			_augment_aliases(details)
			results.append({
				'id': rec.get(PRIMARY_KEY),
				'numero_controle': rec.get(PRIMARY_KEY),
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
	except Exception as e:
		print(f"Erro na busca por palavras‑chave: {e}")
		return [], 0.0
	finally:
		_safe_close(cursor, conn)

def hybrid_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS,
				  semantic_weight=SEMANTIC_WEIGHT,
				  filter_expired=DEFAULT_FILTER_EXPIRED,
				  use_negation=DEFAULT_USE_NEGATION,
				  intelligent_mode=True):
	"""Busca híbrida com eliminação de hardcodes de colunas.

	Usa builders para colunas core e cursor.description para mapear resultados.
	"""
	conn=None; cursor=None
	try:
		if intelligent_mode and ENABLE_INTELLIGENT_PROCESSING:
			processed = _get_processed(query_text)
		else:
			processed = {
				'original_query': query_text,
				'search_terms': query_text,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Processamento desativado'
			}
		negative_terms = processed.get('negative_terms') or ''
		search_terms = processed.get('search_terms') or query_text
		embedding_input = f"{search_terms} -- {negative_terms}".strip() if negative_terms else search_terms
		sql_conditions = processed.get('sql_conditions', [])
		sql_conditions_sanitized = _sanitize_sql_conditions(sql_conditions, context='hybrid')

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

		core_cols = get_contratacao_core_columns('c')  # builder
		text_field = 'c.objeto_compra'
		base = [
			"SELECT",
			"  " + ",\n  ".join(core_cols) + ",",
			f"  (1 - (ce.{EMB_VECTOR_FIELD} <=> %s::vector)) AS semantic_score,",
			f"  COALESCE(ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s)),0) AS keyword_score,",
			f"  COALESCE(ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s)),0) AS keyword_prefix_score,",
			f"  ( %s * (1 - (ce.{EMB_VECTOR_FIELD} <=> %s::vector)) + (1 - %s) * LEAST((0.7 * COALESCE(ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s)) + 0.3 * COALESCE(ts_rank(to_tsvector('portuguese', {text_field}), to_tsquery('portuguese', %s))) ) / %s, 1.0) ) AS combined_score",
			f"FROM {CONTRATACAO_TABLE} c",
			f"JOIN {CONTRATACAO_EMB_TABLE} ce ON c.{PRIMARY_KEY} = ce.{PRIMARY_KEY}",
			f"WHERE ce.{EMB_VECTOR_FIELD} IS NOT NULL"
		]
		if filter_expired:
			base.append("AND to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE")
		for cond in sql_conditions_sanitized:
			base.append(f"AND {cond}")
		base.append("ORDER BY combined_score DESC")
		base.append("LIMIT %s")
		sql = "\n".join(base)
		params = [emb_vec, tsquery, tsquery_prefix, semantic_weight, emb_vec, semantic_weight, tsquery, tsquery_prefix, max_possible_keyword_score, limit]
		try:
			cursor.execute(sql, params)
			rows = cursor.fetchall(); column_names=[d[0] for d in cursor.description]; results=[]; sims=[]; core_keys=set(CONTRATACAO_FIELDS.keys())
			for idx,row in enumerate(rows):
				rec=dict(zip(column_names,row))
				combined=float(rec['combined_score'])
				sims.append(combined)
				details={k:v for k,v in rec.items() if k in core_keys}
				# anexa métricas
				details['semantic_score']=float(rec['semantic_score'])
				details['keyword_score']=float(rec['keyword_score'])
				details['keyword_prefix_score']=float(rec['keyword_prefix_score'])
				if intelligent_mode:
					details['intelligent_processing']={
						'original_query': processed.get('original_query', query_text),
						'processed_terms': processed['search_terms'],
						'applied_conditions': len(sql_conditions),
						'explanation': processed.get('explanation','')
					}
				_augment_aliases(details)
				results.append({
					'id': rec.get(PRIMARY_KEY),
					'numero_controle': rec.get(PRIMARY_KEY),
					'similarity': combined,
					'rank': idx+1,
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
				if 'details' in r:
					_augment_aliases(r['details'])
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

# =============================================================
# CATEGORIAS (migrado de gvg_categories.py para consolidação v3)
# =============================================================
from gvg_database import create_engine_connection
import pandas as pd

def get_top_categories_for_query(query_text: str, top_n: int = 10, use_negation: bool = True, search_type: int = 1, console=None):
	"""Retorna top categorias similares ao embedding da consulta.

	Migrado para usar schema unificado (tabela categoria e campos snake_case).
	Mantém formato de saída legado (keys codigo, descricao, nivelX_) consumido pelo pipeline/UX.
	"""
	try:
		emb = get_embedding(query_text)
		if emb is None:
			return []
		emb_list = emb.tolist() if isinstance(emb, np.ndarray) else emb
		engine = create_engine_connection()
		if not engine:
			return []
		# Usa builder centralizado para garantir consistência de colunas
		base_select = build_category_similarity_select('%(embedding)s')  # já inclui FROM/WHERE
		query = base_select + "ORDER BY similarity DESC LIMIT %(limit)s"  # adiciona ordenação/limite
		df = pd.read_sql_query(query, engine, params={"embedding": emb_list, "limit": top_n})
		out = []
		for idx, row in df.iterrows():
			# Compat: alguns ambientes podem não ter id_categoria; usar fallback
			categoria_id = row.get('id_categoria') if 'id_categoria' in df.columns else row.get('cod_cat')
			out.append({
				'rank': idx + 1,
				'categoria_id': categoria_id,
				'codigo': row.get('cod_cat'),
				'descricao': row.get('nom_cat'),
				'nivel0_cod': row.get('cod_nv0'),
				'nivel0_nome': row.get('nom_nv0'),
				'nivel1_cod': row.get('cod_nv1'),
				'nivel1_nome': row.get('nom_nv1'),
				'nivel2_cod': row.get('cod_nv2'),
				'nivel2_nome': row.get('nom_nv2'),
				'nivel3_cod': row.get('cod_nv3'),
				'nivel3_nome': row.get('nom_nv3'),
				'similarity_score': float(row.get('similarity', 0.0))
			})
		return out
	except Exception as e:
		if console:
			console.print(f"[red]Erro ao buscar categorias: {e}[/red]")
		return []

def _calculate_correspondence_similarity_score(query_categories, result_categories, result_similarities):
	try:
		if not query_categories or not result_categories or not result_similarities:
			return 0.0
		best=0.0
		for qc in query_categories:
			code = qc.get('codigo'); qsim = qc.get('similarity_score',0) or 0
			if not code or not qsim: continue
			if code in result_categories:
				idx = result_categories.index(code)
				rsim = result_similarities[idx] if idx < len(result_similarities) else 0
				if rsim:
					best = max(best, float(qsim)*float(rsim))
		return float(best)
	except Exception:
		return 0.0

def _find_top_category_for_result(query_categories, result_categories, result_similarities):
	try:
		if not query_categories or not result_categories or not result_similarities:
			return None
		best_cat=None; best_score=0.0
		for qc in query_categories:
			code=qc.get('codigo'); qsim=qc.get('similarity_score',0) or 0
			if not code or not qsim: continue
			if code in result_categories:
				idx = result_categories.index(code)
				rsim = result_similarities[idx] if idx < len(result_similarities) else 0
				if not rsim: continue
				score = float(qsim)*float(rsim)
				if score>best_score:
					best_score=score
					best_cat={'codigo':code,'descricao':qc.get('descricao'),'query_similarity':qsim,'result_similarity':rsim,'correspondence_score':score}
		return best_cat
	except Exception:
		return None

def correspondence_search(query_text, top_categories, limit=30, filter_expired=True, console=None):
	"""Busca por correspondência de categorias.

	Atualizada para usar somente tabelas/colunas V1 (contratacao / contratacao_emb).
	"""
	if not top_categories:
		return [], 0.0, {'reason': 'no_categories'}
	try:
		category_codes = [c['codigo'] for c in top_categories if c.get('codigo')]
		if not category_codes:
			return [], 0.0, {'reason': 'empty_codes'}
		conn = create_connection()
		if not conn:
			return [], 0.0, {'reason': 'db_connection_failed'}
		cur = conn.cursor()
		sql = f"""
		SELECT c.numero_controle_pncp,c.ano_compra,c.objeto_compra,c.valor_total_homologado,c.valor_total_estimado,
			   c.data_abertura_proposta,c.data_encerramento_proposta,c.data_inclusao,c.link_sistema_origem,c.modalidade_id,
			   c.modalidade_nome,c.modo_disputa_id,c.modo_disputa_nome,c.usuario_nome,c.orgao_entidade_poder_id,c.orgao_entidade_esfera_id,
			   c.unidade_orgao_uf_sigla,c.unidade_orgao_municipio_nome,c.unidade_orgao_nome_unidade,c.orgao_entidade_razao_social,
			   ce.top_categories, ce.top_similarities
		FROM {CONTRATACAO_TABLE} c
		JOIN {CONTRATACAO_EMB_TABLE} ce ON c.{PRIMARY_KEY} = ce.{PRIMARY_KEY}
		WHERE ce.top_categories && %s
		"""
		params = (category_codes,)
		if filter_expired:
			sql += " AND to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE"
		sql += " LIMIT %s"
		params = (category_codes, limit * 5)
		cur.execute(sql, params)
		rows = cur.fetchall(); colnames = [d[0] for d in cur.description]; cur.close(); conn.close()
		results = []
		for row in rows:
			rec = dict(zip(colnames, row))
			_augment_aliases(rec)
			r_categories = rec.get('top_categories') or []
			r_sims = rec.get('top_similarities') or []
			correspondence_similarity = _calculate_correspondence_similarity_score(top_categories, r_categories, r_sims)
			top_cat_info = _find_top_category_for_result(top_categories, r_categories, r_sims)
			results.append({
				'id': rec.get('numero_controle_pncp'),
				'numero_controle': rec.get('numero_controle_pncp'),
				'similarity': correspondence_similarity,
				'correspondence_similarity': correspondence_similarity,
				'search_approach': 'correspondence',
				'details': rec,
				'top_category_info': top_cat_info
			})
		results.sort(key=lambda x: x['similarity'], reverse=True)
		results = results[:limit]
		for i, r in enumerate(results, 1):
			r['rank'] = i
		confidence = calculate_confidence([r['similarity'] for r in results]) if results else 0.0
		return results, confidence, {'total_raw': len(rows)}
	except Exception as e:
		if console: console.print(f"[red]Erro correspondência: {e}[/red]")
		return [], 0.0, {'error': str(e)}

def category_filtered_search(query_text, search_type, top_categories, limit=30, filter_expired=True, use_negation=True, expanded_factor=3, console=None):
	"""Filtra resultados por interseção com categorias top do usuário.

	Atualizado para apenas schema V1. Mantém forma de saída.
	"""
	if not top_categories:
		return [], 0.0, {'reason': 'no_categories'}
	try:
		expanded_limit = limit * expanded_factor
		if search_type == 1:
			# Extrai códigos e injeta diretamente no SQL semântico para filtrar por categorias
			category_codes = [c['codigo'] for c in top_categories if c.get('codigo')]
			base_results, confidence = semantic_search(
				query_text,
				limit=limit,  # já limitado no SQL final
				filter_expired=filter_expired,
				use_negation=use_negation,
				intelligent_mode=True,
				category_codes=category_codes
			)
			# Resultados já vêm filtrados por categoria no SQL – retornar direto
			if base_results:
				for i, r in enumerate(base_results, 1):
					r['rank'] = i
				meta = {
					'universe_size': len(base_results),
					'universe_with_categories': len(base_results),
					'filtered_count': len(base_results),
					'filtered_by_sql': True
				}
				return base_results, confidence, meta
		elif search_type == 2:
			base_results, confidence = keyword_search(query_text, limit=expanded_limit, filter_expired=filter_expired)
		else:
			base_results, confidence = hybrid_search(query_text, limit=expanded_limit, filter_expired=filter_expired, use_negation=use_negation)
		if not base_results:
			return [], 0.0, {'reason': 'no_base_results'}
		ids = [r['id'] for r in base_results]
		conn = create_connection()
		if not conn:
			return [], 0.0, {'reason': 'db_connection_failed'}
		cur = conn.cursor(); placeholders = ','.join(['%s'] * len(ids))
		cat_sql = f"""
		SELECT {PRIMARY_KEY}, top_categories
		FROM {CONTRATACAO_EMB_TABLE}
		WHERE {PRIMARY_KEY} IN ({placeholders}) AND top_categories IS NOT NULL
		"""
		cur.execute(cat_sql, ids)
		cat_map = {row[0]: row[1] for row in cur.fetchall()}; cur.close(); conn.close()
		query_codes = {c['codigo'] for c in top_categories if c.get('codigo')}
		filtered = []; universe_with_categories = 0
		for r in base_results:
			r_cats = cat_map.get(r['id'])
			if r_cats:
				universe_with_categories += 1
				if any(code in r_cats for code in query_codes):
					r['search_approach'] = 'category_filtered'
					if 'details' in r:
						_augment_aliases(r['details'])
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
		if console: console.print(f"[red]Erro filtro categorias: {e}[/red]")
		return [], 0.0, {'error': str(e)}

__all__ = [
	'semantic_search','keyword_search','hybrid_search',
	'apply_relevance_filter','set_relevance_filter_level','toggle_relevance_filter','get_relevance_filter_status','toggle_relevance_filter_debug',
	'toggle_intelligent_processing','toggle_intelligent_debug','get_intelligent_status',
	'get_top_categories_for_query','correspondence_search','category_filtered_search'
]
