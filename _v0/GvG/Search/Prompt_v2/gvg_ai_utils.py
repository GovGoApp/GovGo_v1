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

# Parâmetros de negação (alinhados ao v9)
NEG_WEIGHT = 0.8  # peso aplicado ao vetor negativo (pos - 0.8*neg)
NEGATION_MARKERS = ["--", " sem ", " não ", " nao ", " not ", " no ", " exceto ", " menos ", " nunca "]
USE_LLM_NEGATION = True  # Mantém ligado como v9 (sempre tenta LLM)

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

def _has_negation_markers(text: str) -> bool:
    t = f" {text.lower()} "
    for mk in NEGATION_MARKERS:
        if mk.strip() == "--":
            if "--" in t:
                return True
        elif mk in t:
            return True
    return False

def extract_pos_neg_terms(prompt: str) -> tuple:
    """Extrai termos positivos/negativos via LLM (modelo v9) com fallback simples.

    Mantém a lógica original do v9:
      - Sempre tenta LLM com instruções detalhadas
      - Se usar '--' divide primeiro para simplificar JSON
      - Em qualquer erro, retorna (prompt, '')
    """
    if not prompt or not prompt.strip():
        return "", ""
    text = prompt.strip()
    # Pré-split se '--'
    if '--' in text:
        left, right = text.split('--', 1)
        if not USE_LLM_NEGATION:
            return left.strip(), right.strip()
    system = """Você é um analisador de consultas especializado em separar termos afirmativos e negados.\n\nINSTRUÇÕES:\n1. Identifique os termos que o usuário QUER encontrar (positive)\n2. Identifique os termos que o usuário NÃO QUER encontrar (negative)\n3. Palavras como 'sem', 'não', 'nao', 'NOT', 'NO', '--', 'exceto', 'menos', 'nunca' indicam negação\n4. O que vem DEPOIS dessas palavras vai para 'negative'\n5. O que vem ANTES permanece em 'positive'\n6. Retorne apenas JSON válido sem texto extra.\n\nExemplos:\n- 'cachorro preto sem manchas brancas' → {\"positive\": \"cachorro preto\", \"negative\": \"manchas brancas\"}\n- 'carros novos não usados utilitários' → {\"positive\": \"carros novos\", \"negative\": \"usados utilitários\"}\n- 'merenda escolar sem aquisição de gêneros' → {\"positive\": \"merenda escolar\", \"negative\": \"aquisição de gêneros\"}\n- 'materiais NOT cimento' → {\"positive\": \"materiais\", \"negative\": \"cimento\"}\n- 'apenas notebook --desktop -- tablet' → {\"positive\": \"notebook\", \"negative\": \"desktop tablet\"}\n"""
    user = f'Consulta: "{text}"\nJSON:'
    if USE_LLM_NEGATION and openai_client:
        try:
            resp = openai_client.chat.completions.create(
                model=os.getenv('NEGATION_LLM_MODEL', 'gpt-4o-mini'),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.05,
                max_tokens=200
            )
            data = resp.choices[0].message.content
            if '```' in data:
                data = re.sub(r"```[a-zA-Z]*", "", data)
                data = data.replace('```', '').strip()
            obj = json.loads(data)
            pos_raw = obj.get('positive', text)
            neg_raw = obj.get('negative', '')
            if isinstance(pos_raw, list):
                pos = " ".join(map(str, pos_raw)).strip()
            else:
                pos = str(pos_raw).strip()
            if isinstance(neg_raw, list):
                neg = " ".join(map(str, neg_raw)).strip()
            else:
                neg = str(neg_raw).strip()
            return pos or text, neg
        except Exception:
            return text, ""
    # Fallback sem LLM
    if '--' in text:
        l, r = text.split('--', 1)
        return l.strip(), r.strip()
    if _has_negation_markers(text):
        # heurística mínima: separa no primeiro marcador
        lower = text.lower()
        best = None; mlen = 0
        for mk in [m for m in NEGATION_MARKERS if m != '--']:
            idx = lower.find(mk)
            if idx != -1 and (best is None or idx < best):
                best = idx; mlen = len(mk)
        if best is not None:
            return text[:best].strip(), re.sub(r"^(sem|não|nao|not|no|exceto|menos|nunca)\s+","", text[best+mlen:].strip(), flags=re.IGNORECASE)
    return text, ""

def get_negation_embedding(query: str) -> np.ndarray:
    """Gera embedding com suporte a termos negativos (paridade v9).

    Processo:
    1. Extrai termos (positive, negative)
    2. Gera embeddings individuais
    3. Normaliza cada vetor
    4. final = pos_vec - NEG_WEIGHT * neg_vec (se houver negativo)
    5. Normaliza final.
    6. Se falhar, fallback para embedding normal.
    """
    try:
        pos_txt, neg_txt = extract_pos_neg_terms(query)
        pos_emb = get_embedding(pos_txt) if pos_txt else None
        if pos_emb is None:
            return None
        pos_vec = np.array(pos_emb, dtype=np.float32)
        pos_norm = np.linalg.norm(pos_vec)
        if pos_norm > 0:
            pos_vec = pos_vec / pos_norm

        if neg_txt and neg_txt.strip():
            neg_emb = get_embedding(neg_txt)
            if neg_emb is not None:
                neg_vec = np.array(neg_emb, dtype=np.float32)
                neg_norm = np.linalg.norm(neg_vec)
                if neg_norm > 0:
                    neg_vec = neg_vec / neg_norm
                final = pos_vec - NEG_WEIGHT * neg_vec
                f_norm = np.linalg.norm(final)
                if f_norm > 0:
                    final = final / f_norm
                return final
        # Sem negativo ou embedding negativo indisponível
        return pos_vec
    except Exception:
        emb = get_embedding(query)
        return np.array(emb) if emb else None

def has_negation(query: str) -> bool:
    # Mantido para compatibilidade; v9 sempre tenta extrair mesmo se não detectar, mas isto permite gating opcional.
    return _has_negation_markers(query or "")

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
