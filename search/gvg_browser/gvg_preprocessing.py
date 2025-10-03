"""
gvg_preprocessing.py  
Módulo otimizado de pré-processamento inteligente para consultas GvG
Contém apenas as funcionalidades essenciais realmente utilizadas
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any
from gvg_ai_utils import ai_assistant_run_text
from dotenv import load_dotenv

# Configurações
load_dotenv()

# Assistant IDs
ASSISTANT_ID = os.getenv("GVG_PREPROCESSING_QUERY_v1")
ASSISTANT_ID_V2 = os.getenv("GVG_PREPROCESSING_QUERY_v2")
ENABLE_SEARCH_V2 = (os.getenv("GVG_ENABLE_SEARCH_V2", "false").strip().lower() in ("1","true","yes","on"))
MAX_RETRIES = 3

def get_preprocessing_thread():
	"""Mantido por compatibilidade; threads agora são gerenciadas por gvg_ai_utils."""
	return None

class SearchQueryProcessor:
	"""
	Processador inteligente otimizado para consultas de busca
	Separa termos de busca de condicionantes SQL usando OpenAI Assistant
	"""
    
	def __init__(self):
		self.assistant_id = ASSISTANT_ID
		# Threads agora são internas ao wrapper; mantemos API
		self.thread = None
        
	def process_query(self, user_query: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
		"""
		Processa uma consulta separando termos de busca de condicionantes SQL
        
		Args:
			user_query (str): Consulta do usuário em linguagem natural
			max_retries (int): Número máximo de tentativas
            
		Returns:
			Dict[str, Any]: Resultado com search_terms, sql_conditions, explanation
		"""
		if not user_query or not user_query.strip():
			return {
				'search_terms': '',
				'sql_conditions': [],
				'explanation': 'Query vazia'
			}
		
		for attempt in range(max_retries):
			try:
				prompt = f"Consulta: {user_query}"
				response_content = ai_assistant_run_text(self.assistant_id or '', prompt, context_key='preproc', timeout=40)
                
				# Processar resposta
				return self._parse_response(response_content, user_query)
                
			except Exception as e:
				try:
					from gvg_debug import debug_log as dbg
					dbg('PRE', f"Tentativa {attempt + 1} falhou: {e}")
				except Exception:
					pass
				if attempt == max_retries - 1:
					# Última tentativa falhou, retornar query original
					return {
						'search_terms': user_query,
						'sql_conditions': [],
						'explanation': f'Processamento falhou após {max_retries} tentativas'
					}
                
				time.sleep(1)  # Aguardar antes da próxima tentativa
        
		# Fallback - nunca deveria chegar aqui
		return {
			'search_terms': user_query,
			'sql_conditions': [],
			'explanation': 'Processamento não disponível'
		}

	def process_query_v2(self, user_input: str, filters: list[str] | None = None, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
		"""
		Processa consulta no formato V2: entrada JSON {input, filter[]} e saída com embeddings.
		Cai no V1 caso o ID do v2 não esteja configurado.
		"""
		# Se não há v2 configurado, usar v1 como fallback
		if not ASSISTANT_ID_V2:
			return self.process_query(user_input or '')

		payload = {
			'input': (user_input or '').strip(),
			'filter': list(filters or []),
		}
		# Se input e filter ambos vazios, retornar resultado trivial
		if not payload['input'] and not payload['filter']:
			return {
				'search_terms': '',
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Entrada e filtros vazios',
				'embeddings': False
			}
		content = json.dumps(payload, ensure_ascii=False)
		# DEBUG de entrada do pré-processamento [FILTER]
		try:
			from gvg_debug import debug_log as dbg
			dbg('PRE', f"[FILTER] assistant.input={payload}")
		except Exception:
			pass

		for attempt in range(max_retries):
			try:
				response_content = ai_assistant_run_text(ASSISTANT_ID_V2 or '', content, context_key='preproc_v2', timeout=50)
				data = self._parse_response(response_content, user_input)
				# DEBUG de saída do pré-processamento [FILTER]
				try:
					from gvg_debug import debug_log as dbg
					dbg('PRE', f"[FILTER] assistant.output={data}")
				except Exception:
					pass
				# Se v2 não retornou embeddings, inferir conforme regra (termos presentes)
				if 'embeddings' not in data:
					st = (data.get('search_terms') or '').strip()
					nt = (data.get('negative_terms') or '').strip()
					data['embeddings'] = bool(st or nt)
				return data
			except Exception as e:
				try:
					from gvg_debug import debug_log as dbg
					dbg('PRE', f"V2 tentativa {attempt + 1} falhou: {e}")
				except Exception:
					pass
				if attempt == max_retries - 1:
					# fallback definitivo: usar v1
					return self.process_query(user_input or '')
				time.sleep(1)
    
	def _wait_for_response(self, run_id: str, max_wait: int = 30) -> str:
		"""Compat leftover: no-op since wrappers return final text."""
		return ""
    
	def _parse_response(self, response_content: str, original_query: str) -> Dict[str, Any]:
		"""
		Processa resposta do Assistant extraindo JSON
        
		Args:
			response_content (str): Resposta do Assistant
			original_query (str): Query original (fallback)
            
		Returns:
			Dict[str, Any]: Dados estruturados
		"""
		try:
			# Tentar extrair JSON da resposta
			json_start = response_content.find('{')
			json_end = response_content.rfind('}') + 1
            
			if json_start >= 0 and json_end > json_start:
				json_str = response_content[json_start:json_end]
				data = json.loads(json_str)
                
				# Validar estrutura
				if 'search_terms' in data and 'sql_conditions' in data:
					if not isinstance(data['sql_conditions'], list):
						data['sql_conditions'] = []
					negative_terms = data.get('negative_terms', '') or ''
					embeddings = data.get('embeddings', None)
					if embeddings is None:
						# Inferir embeddings conforme regra: termos positivos ou negativos presentes
						st = (data.get('search_terms') or '').strip()
						nt = (data.get('negative_terms') or '').strip()
						embeddings = bool(st or nt)
					return {
						'search_terms': (data.get('search_terms') or original_query).strip(),
						'negative_terms': negative_terms.strip(),
						'sql_conditions': data.get('sql_conditions', []),
						'explanation': data.get('explanation', 'Processamento concluído'),
						'embeddings': embeddings
					}
            
			# Se não conseguiu extrair JSON válido
			return {
				'search_terms': original_query,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Não foi possível processar a resposta do Assistant',
				'embeddings': bool((original_query or '').strip())
			}
            
		except json.JSONDecodeError:
			return {
				'search_terms': original_query,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Resposta inválida do Assistant',
				'embeddings': bool((original_query or '').strip())
			}

def process_search_query(user_query: str) -> Dict[str, Any]:
	"""
	Função de conveniência para processamento de query
    
	Args:
		user_query (str): Consulta do usuário
        
	Returns:
		Dict[str, Any]: Resultado processado
	"""
	processor = SearchQueryProcessor()
	return processor.process_query(user_query)

# -------------------------------------------------------------
# Formatters migrados de gvg_formatters.py (consolidação v3)
# -------------------------------------------------------------
def format_currency(value: Any) -> str:
	try:
		if value in (None, ''):
			return ''
		v = float(value)
		return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
	except Exception:
		return str(value) if value is not None else ''


def format_date(value: Any) -> str:
	if not value or value in ('N/A', 'None'):
		return ''
	try:
		if isinstance(value, str) and 'T' in value:
			return value.split('T')[0]
		if isinstance(value, str) and len(value) >= 10:
			return value[:10]
		if isinstance(value, datetime):
			return value.strftime('%Y-%m-%d')
		return str(value)
	except Exception:
		return str(value)


def decode_poder(code: Any) -> str:
	mapping = {1: 'Executivo', 2: 'Legislativo', 3: 'Judiciário'}
	try:
		return mapping.get(int(code), '') if code is not None else ''
	except Exception:
		return ''


def decode_esfera(code: Any) -> str:
	mapping = {1: 'Federal', 2: 'Estadual', 3: 'Municipal'}
	try:
		return mapping.get(int(code), '') if code is not None else ''
	except Exception:
		return ''

__all__ = [
	'SearchQueryProcessor',
	'get_preprocessing_thread',
	'process_search_query',
	'format_currency',
	'format_date',
	'decode_poder',
	'decode_esfera'
]
