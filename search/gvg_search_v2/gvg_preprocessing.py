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
from openai import OpenAI
from dotenv import load_dotenv

# Configurações
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Assistant ID (V1) carregado via variável cujo nome = arquivo
ASSISTANT_ID = os.getenv("GVG_PREPROCESSING_QUERY_v1", "asst_5g1S4zRk5IOjBuZIPCBxnmVo")
MAX_RETRIES = 3

# Thread global para reutilização
_thread = None

def get_preprocessing_thread():
	"""
	Retorna thread global para preprocessamento, criando se necessário
    
	Returns:
		thread: Thread do OpenAI Assistant
	"""
	global _thread
	if _thread is None:
		_thread = client.beta.threads.create()
	return _thread

class SearchQueryProcessor:
	"""
	Processador inteligente otimizado para consultas de busca
	Separa termos de busca de condicionantes SQL usando OpenAI Assistant
	"""
    
	def __init__(self):
		self.assistant_id = ASSISTANT_ID
		self.thread = get_preprocessing_thread()
        
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
				# Preparar prompt para o Assistant
				# Prompt mínimo – a lógica principal está no arquivo de especificação do Assistant (GVG_PREPROCESSING_QUERY_v1)
				# O assistant já sabe retornar: search_terms, negative_terms, sql_conditions, explanation, requires_join_embeddings
				prompt = f"Consulta: {user_query}"
                
				# Enviar mensagem
				client.beta.threads.messages.create(
					thread_id=self.thread.id,
					role="user",
					content=prompt
				)
                
				# Executar Assistant
				run = client.beta.threads.runs.create(
					thread_id=self.thread.id,
					assistant_id=self.assistant_id
				)
                
				# Aguardar resposta
				response_content = self._wait_for_response(run.id)
                
				# Processar resposta
				return self._parse_response(response_content, user_query)
                
			except Exception as e:
				print(f"Tentativa {attempt + 1} falhou: {e}")
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
    
	def _wait_for_response(self, run_id: str, max_wait: int = 30) -> str:
		"""
		Aguarda resposta do Assistant
        
		Args:
			run_id (str): ID do run
			max_wait (int): Tempo máximo de espera
            
		Returns:
			str: Conteúdo da resposta
		"""
		start_time = time.time()
        
		while time.time() - start_time < max_wait:
			run = client.beta.threads.runs.retrieve(
				thread_id=self.thread.id,
				run_id=run_id
			)
            
			if run.status == 'completed':
				# Buscar última mensagem do assistant
				messages = client.beta.threads.messages.list(
					thread_id=self.thread.id,
					limit=1
				)
                
				if messages.data and messages.data[0].role == 'assistant':
					return messages.data[0].content[0].text.value
                    
			elif run.status in ['failed', 'cancelled', 'expired']:
				raise Exception(f"Run falhou: {run.status}")
                
			time.sleep(1)
        
		raise Exception("Timeout aguardando resposta")
    
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
					requires_join_embeddings = bool(data.get('requires_join_embeddings'))
					return {
						'search_terms': (data.get('search_terms') or original_query).strip(),
						'negative_terms': negative_terms.strip(),
						'sql_conditions': data.get('sql_conditions', []),
						'explanation': data.get('explanation', 'Processamento concluído'),
						'requires_join_embeddings': requires_join_embeddings
					}
            
			# Se não conseguiu extrair JSON válido
			return {
				'search_terms': original_query,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Não foi possível processar a resposta do Assistant',
				'requires_join_embeddings': False
			}
            
		except json.JSONDecodeError:
			return {
				'search_terms': original_query,
				'negative_terms': '',
				'sql_conditions': [],
				'explanation': 'Resposta inválida do Assistant',
				'requires_join_embeddings': False
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
