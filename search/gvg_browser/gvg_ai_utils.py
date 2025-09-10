"""
gvg_ai_utils.py
Módulo otimizado para utilitários de IA/Embeddings GvG
Contém apenas as funções de IA e embeddings realmente utilizadas
"""

import os
from gvg_debug import debug_log as dbg
import re
import json
import numpy as np
import time
from openai import OpenAI
from dotenv import load_dotenv
EMBEDDING_MODEL = "text-embedding-3-large"
NEGATION_EMB_WEIGHT = float(os.getenv('NEGATION_EMB_WEIGHT', 1.0))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

"""
Negation Embedding Strategy (mantida):

O novo assistant de pré-processamento (GVG_PREPROCESSING_QUERY_v1) já entrega os
termos negativos separados. Contudo, ainda aplicamos a estratégia vetorial:

	embedding_final = emb_pos - NEG_WEIGHT * emb_neg

Este módulo espera receber no get_negation_embedding um texto possivelmente no
formato "parte_positiva -- parte_negativa" (delimitador `--`). Se não houver
delimitador ou parte negativa, retorna apenas o embedding positivo.

NEG_WEIGHT pode ser ajustado via variável de ambiente `NEGATION_EMB_WEIGHT`
(default 1). O vetor final é normalizado para manter escala consistente.
"""

def get_embedding(text, model=EMBEDDING_MODEL):
	"""Gera embedding para texto usando OpenAI e retorna lista (ou None em erro)."""
	try:
		response = openai_client.embeddings.create(input=text, model=model)
		return response.data[0].embedding
	except Exception as e:
		dbg('ASSISTANT', f"Erro ao gerar embedding: {e}")
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
		# Prompt para gerar palavras-chave
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
        
		response = openai_client.chat.completions.create(
			model="gpt-4o",
			messages=[{"role": "user", "content": prompt}],
			max_tokens=150,
			temperature=0.3
		)
        
		keywords_text = response.choices[0].message.content.strip()
        
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

### Removidas heurísticas complexas de normalização.
### Qualidade agora delegada ao prompt do Assistant.

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
	start = time.time()
	# 1) Assistant API
	if assistant_id:
		try:
			thread = openai_client.beta.threads.create(messages=[{"role": "user", "content": desc}])  # type: ignore
			run = openai_client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)  # type: ignore
			while time.time() - start < timeout:
				run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)  # type: ignore
				if run.status in ('completed', 'failed', 'cancelled'):  # type: ignore
					break
				time.sleep(0.35)
			if getattr(run, 'status', '') == 'completed':  # type: ignore
				msgs = openai_client.beta.threads.messages.list(thread_id=thread.id, order='desc', limit=5)  # type: ignore
				for m in getattr(msgs, 'data', []):  # type: ignore
					if getattr(m, 'role', '') == 'assistant':
						parts = getattr(m, 'content', [])
						for p in parts:
							if getattr(p, 'type', '') == 'text':
								label_raw = getattr(getattr(p, 'text', {}), 'value', '')
								break
						if label_raw:
							break
		except Exception as e:
			try:
				from gvg_debug import debug_log as dbg
				dbg('ASSISTANT', f"Assistant fallback: {e}")
			except Exception:
				pass
	# 2) Chat fallback
	if not label_raw:
		try:
			prompt = (
				"Gerar rótulo curto (até 3 palavras) do objeto a seguir. Sem órgão, local, códigos ou números. Apenas o objeto/serviço/material. Sem pontuação!\n" + desc[:600]
			)
			resp = openai_client.chat.completions.create(
				model='gpt-4o',
				messages=[{"role": "user", "content": prompt}],
				max_tokens=20,
				temperature=0.2
			)
			label_raw = resp.choices[0].message.content.strip()
		except Exception as e:
			try:
				from gvg_debug import debug_log as dbg
				dbg('ASSISTANT', f"Chat fallback: {e}")
			except Exception:
				pass
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
