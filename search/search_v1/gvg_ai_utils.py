"""
gvg_ai_utils.py
Módulo otimizado para utilitários de IA/Embeddings GvG
Contém apenas as funções de IA e embeddings realmente utilizadas
"""

import os
import re
import json
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# Configurações
load_dotenv()
EMBEDDING_MODEL = "text-embedding-3-large"
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
(default 0.40). O vetor final é normalizado para manter escala consistente.
"""

NEGATION_EMB_WEIGHT = float(os.getenv("NEGATION_EMB_WEIGHT", "0.40"))

def get_embedding(text, model=EMBEDDING_MODEL):
    """
    Gera embedding para texto usando OpenAI
    
    Args:
        text (str): Texto para gerar embedding
        model (str): Modelo de embedding a usar
        
    Returns:
        list: Vetor embedding do texto
    """
    try:
        response = openai_client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
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
        print(f"Erro get_negation_embedding: {e}")
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
            model="gpt-3.5-turbo",
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
        print(f"Erro ao gerar palavras-chave: {e}")
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

__all__ = ['get_embedding','get_negation_embedding','generate_keywords','calculate_confidence']
