"""
gvg_ai_utils.py
Utilitários centrais de IA para o GvG.

Separação de responsabilidades:
- Funções básicas (infra OpenAI): cliente, threads, assistants, chat, embeddings.
- Funções específicas (domínio GovGo): keywords, rótulo, métricas auxiliares.

Todas as chamadas à biblioteca OpenAI devem passar por este módulo.
Inclui instrumentação: tokens e tempo por utilização, quando disponível.
"""

import os
import re
import json
import time
from typing import Dict, Any, List, Optional

import numpy as np
from dotenv import load_dotenv
from gvg_debug import debug_log as dbg

try:
	from openai import OpenAI  # type: ignore
except Exception:
	OpenAI = None  # type: ignore

EMBEDDING_MODEL = os.getenv("GVG_EMBEDDING_MODEL", "text-embedding-3-large")
NEGATION_EMB_WEIGHT = float(os.getenv('NEGATION_EMB_WEIGHT', 1.0))

# ======================================================
# Básicas: Cliente/Threads/Assistants/Chat/Embeddings
# ======================================================

_OPENAI_CLIENT = None
_THREADS: Dict[str, Any] = {}

def ai_get_client():
	"""Retorna singleton do cliente OpenAI (ou None se indisponível)."""
	global _OPENAI_CLIENT
	if _OPENAI_CLIENT is not None:
		return _OPENAI_CLIENT
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key or OpenAI is None:
		return None
	try:
		_OPENAI_CLIENT = OpenAI(api_key=api_key)
	except Exception as e:
		dbg('ASSISTANT', f"OpenAI client init error: {e}")
		_OPENAI_CLIENT = None
	return _OPENAI_CLIENT

def ai_get_thread(context_key: str = "default"):
	"""Retorna (ou cria) uma thread de Assistant por contexto lógico."""
	client = ai_get_client()
	if client is None:
		return None
	thread = _THREADS.get(context_key)
	if thread is None:
		try:
			thread = client.beta.threads.create()
			_THREADS[context_key] = thread
		except Exception as e:
			dbg('ASSISTANT', f"Create thread failed [{context_key}]: {e}")
			return None
	return thread

def _extract_assistant_text_from_messages(client, thread_id: str, limit: int = 10) -> str:
	try:
		msgs = client.beta.threads.messages.list(thread_id=thread_id, order='desc', limit=limit)
		for m in getattr(msgs, 'data', []):
			if getattr(m, 'role', '') == 'assistant':
				for p in getattr(m, 'content', []) or []:
					if getattr(p, 'type', '') == 'text':
						val = getattr(getattr(p, 'text', {}), 'value', '')
						if isinstance(val, str) and val.strip():
							return val.strip()
		return ""
	except Exception:
		return ""

def ai_assistant_run_text(assistant_id: str, content: str, context_key: str = 'default', timeout: int = 60) -> str:
	"""Executa um Assistant com entrada de texto e retorna o texto do assistant.

	Instrumenta tokens (se disponíveis) e tempo de execução.
	"""
	client = ai_get_client()
	if client is None or not assistant_id:
		dbg('ASSISTANT', f"assistant unavailable (assistant_id? {bool(assistant_id)})")
		return ""
	thread = ai_get_thread(context_key)
	if thread is None:
		return ""
	t0 = time.time()
	tokens_in = tokens_out = total_tokens = None
	try:
		client.beta.threads.messages.create(thread_id=thread.id, role='user', content=content)
		run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
		while True:
			cur = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
			status = getattr(cur, 'status', '')
			if status in ('completed', 'failed', 'cancelled', 'expired', 'requires_action'):
				run = cur
				break
			if time.time() - t0 > timeout:
				dbg('ASSISTANT', f"timeout ({timeout}s) [{context_key}]")
				return ""
			time.sleep(0.8)
		# usage (nem sempre disponível nos Assistants)
		try:
			usage = getattr(run, 'usage', None)
			if usage:
				# diferentes SDKs: input_tokens/output_tokens/total_tokens
				tokens_in = getattr(usage, 'input_tokens', None)
				tokens_out = getattr(usage, 'output_tokens', None)
				total_tokens = getattr(usage, 'total_tokens', None)
		except Exception:
			pass
		out = _extract_assistant_text_from_messages(client, thread.id)
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('IA', f"assistant.run context={context_key} tokens_in={tokens_in} tokens_out={tokens_out} total={total_tokens} time_ms={elapsed_ms}")
		return out
	except Exception as e:
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('ASSISTANT', f"assistant.error context={context_key} err={e} time_ms={elapsed_ms}")
		return ""

def ai_assistant_run_with_files(assistant_id: str, file_paths: List[str], user_message: str, timeout: int = 180) -> str:
	"""Executa Assistant anexando arquivos (purpose='assistants') e retorna texto.

	Instrumenta tokens (se disponíveis) e tempo de execução.
	"""
	client = ai_get_client()
	if client is None or not assistant_id:
		dbg('ASSISTANT', f"assistant unavailable (files)")
		return ""
	thread = ai_get_thread('documents')
	if thread is None:
		return ""
	t0 = time.time()
	tokens_in = tokens_out = total_tokens = None
	try:
		attachments = []
		for p in file_paths or []:
			try:
				with open(p, 'rb') as f:
					up = client.files.create(purpose='assistants', file=f)
					attachments.append({'file_id': up.id, 'tools': [{'type': 'file_search'}]})
			except Exception as e:
				dbg('ASSISTANT', f"file.upload.error path={os.path.basename(p)} err={e}")
		if not attachments:
			return ""
		client.beta.threads.messages.create(thread_id=thread.id, role='user', content=[{"type": "text", "text": user_message}], attachments=attachments)  # type: ignore
		run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
		while True:
			cur = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
			status = getattr(cur, 'status', '')
			if status in ('completed', 'failed', 'cancelled', 'expired', 'requires_action'):
				run = cur
				break
			if time.time() - t0 > timeout:
				dbg('ASSISTANT', f"timeout ({timeout}s) [documents]")
				return ""
			time.sleep(1.0)
		try:
			usage = getattr(run, 'usage', None)
			if usage:
				tokens_in = getattr(usage, 'input_tokens', None)
				tokens_out = getattr(usage, 'output_tokens', None)
				total_tokens = getattr(usage, 'total_tokens', None)
		except Exception:
			pass
		out = _extract_assistant_text_from_messages(client, thread.id)
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('IA', f"assistant.files tokens_in={tokens_in} tokens_out={tokens_out} total={total_tokens} time_ms={elapsed_ms}")
		return out
	except Exception as e:
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('ASSISTANT', f"assistant.files.error err={e} time_ms={elapsed_ms}")
		return ""

def ai_chat_complete(model: str, messages: List[Dict[str, Any]], max_tokens: Optional[int] = None, temperature: float = 0.2) -> str:
	"""Wrapper para chat.completions com métricas de tokens/tempo."""
	client = ai_get_client()
	if client is None:
		return ""
	t0 = time.time()
	try:
		resp = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
		elapsed_ms = int((time.time() - t0) * 1000)
		try:
			usage = getattr(resp, 'usage', None)
			pt = getattr(usage, 'prompt_tokens', None)
			ct = getattr(usage, 'completion_tokens', None)
			tt = getattr(usage, 'total_tokens', None)
		except Exception:
			pt = ct = tt = None
		dbg('IA', f"chat.complete model={model} prompt_t={pt} completion_t={ct} total={tt} time_ms={elapsed_ms}")
		return (resp.choices[0].message.content or '').strip()
	except Exception as e:
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('ASSISTANT', f"chat.error model={model} err={e} time_ms={elapsed_ms}")
		return ""


def get_embedding(text, model=EMBEDDING_MODEL):
	"""Gera embedding para texto usando OpenAI e retorna lista (ou None em erro).

	Instrumenta tempo e tokens (se disponíveis no SDK).
	"""
	client = ai_get_client()
	if client is None:
		return None
	t0 = time.time()
	try:
		response = client.embeddings.create(input=text, model=model)
		elapsed_ms = int((time.time() - t0) * 1000)
		# Nem todos os SDKs/planos retornam usage no embeddings
		try:
			usage = getattr(response, 'usage', None)
			tt = getattr(usage, 'total_tokens', None) if usage else None
		except Exception:
			tt = None
		dbg('IA', f"embeddings model={model} total_tokens={tt} time_ms={elapsed_ms}")
		return response.data[0].embedding
	except Exception as e:
		elapsed_ms = int((time.time() - t0) * 1000)
		dbg('ASSISTANT', f"embedding.error model={model} err={e} time_ms={elapsed_ms}")
		return None

def _normalize(vec: np.ndarray):
	norm = np.linalg.norm(vec)
	if norm == 0:
		return vec
	return vec / norm

def get_negation_embedding(query: str, model: str = EMBEDDING_MODEL, weight: float = None):
	"""
	Gera embedding combinado com suporte a negação.

	Espera texto no formato "positivo -- negativo". Caso não exista `--`,
	retorna embedding simples da consulta inteira.

	Fórmula: emb_final = emb_pos - weight * emb_neg (normalizado ao final)

	Args:
		query (str): Texto possivelmente contendo "--" separando termos.
		model (str): Modelo de embedding.
		weight (float): Peso da parte negativa (override opcional).

	Returns:
		np.ndarray | None: Vetor embedding (list compat ao final) ou None se falha.
	"""
	try:
		if weight is None:
			weight = NEGATION_EMB_WEIGHT

		if not query or not query.strip():
			return None

		if '--' in query:
			pos_raw, neg_raw = query.split('--', 1)
			pos_text = pos_raw.strip()
			neg_text = neg_raw.strip()
		else:
			pos_text = query.strip()
			neg_text = ''

		# Embedding positivo
		pos_emb = get_embedding(pos_text, model=model)
		if pos_emb is None:
			return None
		pos_emb = np.array(pos_emb, dtype=np.float32)

		if not neg_text:
			return pos_emb

		# Embedding negativo
		neg_emb = get_embedding(neg_text, model=model)
		if neg_emb is None:
			# Falhou negativo -> usar somente positivo
			return pos_emb
		neg_emb = np.array(neg_emb, dtype=np.float32)
		combined = pos_emb - (weight * neg_emb)
		combined = _normalize(combined)
		return combined
	except Exception as e:
		dbg('ASSISTANT', f"Erro get_negation_embedding: {e}")
		return None

def generate_keywords(text, max_keywords=10, max_chars=200):
	"""
	Gera palavras-chave inteligentes para um texto usando OpenAI
    
	Args:
		text (str): Texto para extrair palavras-chave
		max_keywords (int): Número máximo de palavras-chave
		max_chars (int): Número máximo de caracteres do texto
        
	Returns:
		list: Lista de palavras-chave relevantes
	"""
	if not text or not text.strip():
		return []
    
	# Truncar texto se muito longo
	if len(text) > max_chars:
		text = text[:max_chars] + "..."
    
	try:
		prompt = f"""
		Analise o seguinte texto de um contrato/licitação pública e extraia {max_keywords} palavras-chave mais relevantes:

		TEXTO:
		{text}

		Retorne apenas as palavras-chave separadas por vírgula, focando em:
		- Objeto/serviço principal
		- Características técnicas importantes  
		- Localização/região
		- Valores ou quantidades significativas
		- Termos técnicos específicos

		Palavras-chave:
		"""
		keywords_text = ai_chat_complete(
			model=os.getenv('GVG_CHAT_MODEL', 'gpt-4o'),
			messages=[{"role": "user", "content": prompt}],
			max_tokens=150,
			temperature=0.3,
		)
        
		# Processar resposta - separar por vírgula e limpar
		keywords = []
		for keyword in keywords_text.split(','):
			keyword = keyword.strip()
			if keyword and len(keyword) > 2:  # Mínimo 3 caracteres
				keywords.append(keyword)
        
		return keywords[:max_keywords]
        
	except Exception as e:
		dbg('ASSISTANT', f"Erro ao gerar palavras-chave: {e}")
		return []

def calculate_confidence(scores):
	"""
	Calcula confiança média de um conjunto de scores
    
	Args:
		scores (list): Lista de scores de similaridade
        
	Returns:
		float: Confiança média em percentual (0-100)
	"""
	if not scores:
		return 0.0
	try:
		# Remover scores None ou inválidos
		valid_scores = [float(s) for s in scores if s is not None]
        
		if not valid_scores:
			return 0.0
            
		# Calcular média e converter para percentual
		avg_confidence = sum(valid_scores) / len(valid_scores)
		return round(avg_confidence * 100, 2)
        
	except (ValueError, TypeError):
		return 0.0

def generate_contratacao_label(descricao: str, timeout: float = 6.0) -> str:
	"""Gera rótulo curto para contratação.

	Agora a formatação é delegada ao Assistant (prompt atualizado). Mantemos:
	  1. Tentativa via Assistant (ID em GVG_ROTULO_CONTRATATACAO)
	  2. Fallback chat simples
	  3. Fallback heurístico mínimo (primeiras 4 palavras)
	Limpeza mínima local: strip, remover aspas externas, limitar tamanho.
	"""
	desc = (descricao or '').strip()
	if not desc:
		return 'Indefinido'
	assistant_id = os.getenv('GVG_ROTULO_CONTRATATACAO')
	label_raw = ''
	# 1) Assistant API via wrapper
	if assistant_id:
		try:
			label_raw = ai_assistant_run_text(assistant_id, desc, context_key='label', timeout=int(timeout))
		except Exception as e:
			dbg('ASSISTANT', f"Assistant fallback: {e}")
	# 2) Chat fallback
	if not label_raw:
		try:
			prompt = (
				"Gerar rótulo curto (até 3 palavras) do objeto a seguir. Sem órgão, local, códigos ou números. Apenas o objeto/serviço/material. Sem pontuação!\n" + desc[:600]
			)
			label_raw = ai_chat_complete(
				model=os.getenv('GVG_CHAT_MODEL', 'gpt-4o'),
				messages=[{"role": "user", "content": prompt}],
				max_tokens=20,
				temperature=0.2,
			)
		except Exception as e:
			dbg('ASSISTANT', f"Chat fallback: {e}")
	# 3) Fallback mínimo
	if not label_raw:
		tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{2,}", desc)
		label_raw = ' '.join(tokens[:4]) or 'Indefinido'
	# Limpeza mínima
	label = ' '.join(re.sub(r'[.,;\'"“”‘’]', '', label_raw.strip().replace('\n', ' ')).split())
	# remover aspas externas simples ou duplas
	if len(label) >= 2 and ((label[0] == '"' and label[-1] == '"') or (label[0] == "'" and label[-1] == "'")):
		label = label[1:-1].strip()
	# Cortar em 60 chars preservando palavra
	if len(label) > 60:
		cut = label[:60]
		if ' ' in cut:
			cut = cut.rsplit(' ', 1)[0]
		label = cut
	if not label:
		label = 'Indefinido'
	return label

__all__ = ['get_embedding','get_negation_embedding','generate_keywords','calculate_confidence','generate_contratacao_label']
