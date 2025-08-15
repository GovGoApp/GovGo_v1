"""
gvg_search_utils.py
Módulo utilitário centralizado para funções de busca
- Conexão e testes com banco Supabase/PostgreSQL
- Implementação de busca semântica, palavras-chave e híbrida
- Integração com OpenAI para embeddings e GPT
- Funções para busca de documentos PNCP
- Geração de palavras-chave e sumarização automática
- Cálculo de confiança e formatação de resultados
"""

import os
import pandas as pd
import numpy as np
import psycopg2
import re
import requests
import time
import locale
import json
import math
from openai import OpenAI
from dotenv import load_dotenv


# Carregar configurações do DB diretamente do arquivo .env
env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
config = {}
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

# Fetch connection variables diretamente do config
USER = config.get("user")
PASSWORD = config.get("password") 
HOST = config.get("host")  # Usar host direto do arquivo
PORT = config.get("port")  # Usar port direto do arquivo
DBNAME = config.get("dbname")

# Cliente OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Configurações
EMBEDDING_MODEL = "text-embedding-3-large"
MIN_RESULTS = 5
MAX_RESULTS = 50
SEMANTIC_WEIGHT = 0.8
DEFAULT_FILTER_EXPIRED = True  # Por padrão, filtrar registros expirados

# Configurações para Negation Embeddings
NEG_WEIGHT = 0.8  # Fator de subtração para termos negativos
DEFAULT_USE_NEGATION = True  # Por padrão, usar negation embeddings

def create_connection():
    """Cria uma conexão com o banco de dados Supabase"""
    try:
        connection = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME,
            connect_timeout=30
        )
        return connection
    except Exception as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {e}")

def test_connection():
    """Testa a conexão com o banco de dados"""
    try:
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        count = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        return count == 2
    except:
        return False


def get_embedding(text, model=EMBEDDING_MODEL):
    """Gera embedding para um texto usando a API da OpenAI"""
    if not text or not text.strip():
        text = " "
    
    if len(text) > 8000:
        text = text[:8000]
    
    response = client.embeddings.create(
        model=model,
        input=[text]
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def extract_pos_neg_terms(prompt: str) -> tuple:
    """
    Retorna (termos_positivos, termos_negativos) dado o prompt.
    Ex: "CACHORRO PRETO SEM MANCHAS BRANCAS" → ("CACHORRO PRETO", "MANCHAS BRANCAS")
    
    Args:
        prompt (str): Consulta do usuário
        
    Returns:
        tuple: (termos_positivos, termos_negativos)
    """
    try:
        system = """Você é um analisador de consultas especializado em separar termos afirmativos e negados.

INSTRUÇÕES:
1. Identifique os termos que o usuário QUER encontrar (positive)
2. Identifique os termos que o usuário NÃO QUER encontrar (negative)
3. Palavras como "sem", "não", "NOT", "NO", "--" "exceto", "menos", "nunca" indicam negação
4. O que vem DEPOIS dessas palavras deve ir para "negative"
5. O que vem ANTES deve ir para "positive"

EXEMPLOS:
- "cachorro preto sem manchas brancas" → positive: "cachorro preto", negative: "manchas brancas"
- "carros novos não usados utilitários" → positive: "carros novos", negative: "usados utilitários"
- "merenda escolar sem aquisição de gêneros" → positive: "merenda escolar", negative: "aquisição de gêneros"
- "materiais NOT cimento" → positive: "materiais", negative: "cimento"
- "apenas notebook --desktop -- tablet" → positive: "notebook", negative: "desktop tablet"
"""
        user = f'Consulta: "{prompt}"\nRetorne JSON com campos "positive" e "negative".'
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.1
        )
        
        data = resp.choices[0].message.content
        
        # Tentar extrair JSON do conteúdo (pode vir com markdown)
        if "```json" in data:
            data = data.split("```json")[1].split("```")[0].strip()
        elif "```" in data:
            data = data.split("```")[1].split("```")[0].strip()
            
        obj = json.loads(data)
        
        # Extrair termos positivos
        positive_raw = obj.get("positive", prompt)
        if isinstance(positive_raw, list):
            positive = " ".join(str(item) for item in positive_raw).strip()
        else:
            positive = str(positive_raw).strip()
        
        # Extrair termos negativos
        negative_raw = obj.get("negative", "")
        if isinstance(negative_raw, list):
            negative = " ".join(str(item) for item in negative_raw).strip()
        else:
            negative = str(negative_raw).strip()
        
        return positive, negative
        
    except Exception as e:
        print(f"Erro ao separar termos positivos/negativos: {e}")
        # Em caso de erro, retorna o prompt original como positivo
        return prompt, ""

def get_negation_embedding(query: str) -> np.ndarray:
    """
    Gera embedding com negação aplicada.
    
    Args:
        query (str): Consulta do usuário
        
    Returns:
        np.ndarray: Embedding final com negação aplicada
    """
    try:
        pos_txt, neg_txt = extract_pos_neg_terms(query)
        
        # Gerar embeddings
        pos_emb = get_embedding(pos_txt)
        neg_emb = get_embedding(neg_txt) if neg_txt.strip() else np.zeros_like(pos_emb)
        
        # Normalizar antes da subtração (opcional mas recomendado)
        pos_emb = pos_emb / np.linalg.norm(pos_emb) if np.linalg.norm(pos_emb) > 0 else pos_emb
        
        if neg_txt.strip() and np.linalg.norm(neg_emb) > 0:
            neg_emb = neg_emb / np.linalg.norm(neg_emb)
            # Aplicar negação
            final = pos_emb - NEG_WEIGHT * neg_emb
        else:
            final = pos_emb
        
        # Normalizar embedding final
        final_norm = np.linalg.norm(final)
        if final_norm > 0:
            final = final / final_norm
            
        return final
        
    except Exception as e:
        print(f"Erro ao gerar negation embedding: {e}")
        # Em caso de erro, retorna embedding normal
        return get_embedding(query)

def semantic_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, filter_expired=DEFAULT_FILTER_EXPIRED, use_negation=DEFAULT_USE_NEGATION):
    """Realiza busca semântica usando embeddings no Supabase
    
    Args:
        query_text (str): Texto da consulta
        limit (int): Limite de resultados
        min_results (int): Mínimo de resultados
        filter_expired (bool): Filtrar contratações encerradas
        use_negation (bool): Usar negation embeddings
    """
    connection = create_connection()
    cursor = connection.cursor()
    
    try:
        # Escolher tipo de embedding baseado na configuração
        if use_negation:
            query_embedding = get_negation_embedding(query_text)
        else:
            query_embedding = get_embedding(query_text)
            
        query_embedding_list = query_embedding.tolist()
        
        search_query = """
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
            1 - (e.embedding_vector <=> %s::vector) AS similarity
        FROM 
            contratacoes c
        JOIN 
            contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
        WHERE 
            e.embedding_vector IS NOT NULL
        """

        # Adicionar condição de filtro se filter_expired estiver ativo
        if filter_expired:
            search_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

        search_query += """
        ORDER BY 
            similarity DESC
        LIMIT %s
        """

        cursor.execute(search_query, (query_embedding_list, limit))
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            
            # Formatar datas para string
            if 'datainclusao' in result_dict:
                result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
            if 'dataaberturaproposta' in result_dict:
                result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
            if 'dataencerramentoproposta' in result_dict:
                result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
            
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": float(result_dict["similarity"]),
                "details": result_dict
            })
        
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        return formatted_results, confidence
    
    finally:
        cursor.close()
        connection.close()

def keyword_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, filter_expired=DEFAULT_FILTER_EXPIRED):
    """Realiza busca por palavras-chave usando full-text search do PostgreSQL"""
    connection = create_connection()
    cursor = connection.cursor()
    
    try:
        tsquery = " & ".join(query_text.split())
        tsquery_prefix = ":* & ".join(query_text.split()) + ":*"
        
        search_query = """
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
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank,
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank_prefix
        FROM 
            contratacoes c
        WHERE 
            (to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)
            OR to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s))
        """

        # Adicionar condição de filtro se filter_expired estiver ativo
        if filter_expired:
            search_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

        search_query += """
        ORDER BY 
            (ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.7 + 
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.3) DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, (
            tsquery, tsquery_prefix, tsquery, tsquery_prefix, 
            tsquery, tsquery_prefix, limit
        ))
        
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            score = float(result_dict["rank"]) * 0.7 + float(result_dict["rank_prefix"]) * 0.3
            max_possible_score = len(query_text.split()) * 0.1
            normalized_score = min(score / max_possible_score, 1.0)
            
            # Formatar datas para string
            if 'datainclusao' in result_dict:
                result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
            if 'dataaberturaproposta' in result_dict:
                result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
            if 'dataencerramentoproposta' in result_dict:
                result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
            
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": normalized_score,
                "details": result_dict
            })
        
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        return formatted_results, confidence
    
    finally:
        cursor.close()
        connection.close()

def hybrid_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, semantic_weight=SEMANTIC_WEIGHT, filter_expired=DEFAULT_FILTER_EXPIRED, use_negation=DEFAULT_USE_NEGATION):
    """Realiza busca híbrida combinando semântica e palavras-chave
    
    Args:
        query_text (str): Texto da consulta
        limit (int): Limite de resultados
        min_results (int): Mínimo de resultados
        semantic_weight (float): Peso da busca semântica
        filter_expired (bool): Filtrar contratações encerradas
        use_negation (bool): Usar negation embeddings
    """
    connection = create_connection()
    cursor = connection.cursor()
    
    try:
        # Escolher tipo de embedding baseado na configuração
        if use_negation:
            query_embedding = get_negation_embedding(query_text)
        else:
            query_embedding = get_embedding(query_text)
            
        query_embedding_list = query_embedding.tolist()
        
        tsquery = " & ".join(query_text.split())
        tsquery_prefix = ":* & ".join(query_text.split()) + ":*"
        
        search_query = """
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
            (1 - (e.embedding_vector <=> %s::vector)) AS semantic_score,
            COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_score,
            COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_prefix_score,
            (
                %s * (1 - (e.embedding_vector <=> %s::vector)) + 
                (1 - %s) * (
                    LEAST(
                        (0.7 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) + 
                        0.3 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0)) 
                        / (%s), 1.0
                    )
                )
            ) AS combined_score
        FROM 
            contratacoes c
        JOIN 
            contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
        WHERE 
            e.embedding_vector IS NOT NULL
        """

        # Adicionar condição de filtro se filter_expired estiver ativo
        if filter_expired:
            search_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

        search_query += """
        ORDER BY 
            combined_score DESC
        LIMIT %s
        """

        max_possible_keyword_score = len(query_text.split()) * 0.1
        
        cursor.execute(search_query, (
            query_embedding_list, tsquery, tsquery_prefix,
            semantic_weight, query_embedding_list, semantic_weight,
            tsquery, tsquery_prefix, max_possible_keyword_score, limit
        ))
        
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            
            # Formatar datas para string
            if 'datainclusao' in result_dict:
                result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
            if 'dataaberturaproposta' in result_dict:
                result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
            if 'dataencerramentoproposta' in result_dict:
                result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
            
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": float(result_dict["combined_score"]),
                "semantic_score": float(result_dict["semantic_score"]),
                "keyword_score": float(result_dict["keyword_score"]) if result_dict["keyword_score"] else 0,
                "details": result_dict
            })
        
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        return formatted_results, confidence
    
    finally:
        cursor.close()
        connection.close()

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações"""
    import math
    
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    
    # Verificar se top_score é zero para evitar divisão por zero
    if top_score == 0.0:
        return 0.0
    
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

def format_currency(value):
    """Formata um valor como moeda brasileira"""
    try:
        if pd.isna(value):
            return "N/A"
        return locale.currency(float(value), grouping=True, symbol=True)
    except:
        return str(value)

def export_results_to_excel(results, query, search_type_id):
    """Exporta resultados para Excel"""
    # Esta função será implementada no callback do Dash
    pass

def parse_numero_controle_pncp(numero_controle):
    """
    Extrai CNPJ, sequencial e ano do numeroControlePNCP.
    
    Formato esperado: {cnpj}-1-{sequencial}/{ano}
    Exemplo: 14105225000117-1-000040/2025
    
    Args:
        numero_controle (str): Número de controle no formato padrão PNCP
        
    Returns:
        tuple: (cnpj, sequencial, ano) ou (None, None, None) se inválido
        
    Raises:
        ValueError: Se o formato não for válido
    """
    if not numero_controle or not isinstance(numero_controle, str):
        raise ValueError("Número de controle deve ser uma string não vazia")
    
    # Padrão regex: {cnpj}-1-{sequencial}/{ano}
    pattern = r'^(\d{14})-1-(\d+)/(\d{4})$'
    match = re.match(pattern, numero_controle.strip())
    
    if not match:
        raise ValueError(f"Formato inválido do numeroControlePNCP: {numero_controle}. Formato esperado: CNPJ-1-SEQUENCIAL/ANO")
    
    cnpj = match.group(1)
    sequencial = match.group(2)
    ano = match.group(3)
    
    return cnpj, sequencial, ano

def fetch_documentos(numero_controle):
    """
    Busca documentos de um processo PNCP usando o numeroControlePNCP.
    
    Args:
        numero_controle (str): Número de controle no formato CNPJ-1-SEQUENCIAL/ANO
        
    Returns:
        list: Lista de documentos encontrados ou lista vazia se erro/não encontrado
        
    Raises:
        ValueError: Se o formato do número de controle for inválido
    """
    try:
        cnpj, sequencial, ano = parse_numero_controle_pncp(numero_controle)
        
        base_url = "https://pncp.gov.br/api/pncp/v1"
        url = f"{base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Adaptar estrutura para o formato esperado
            if isinstance(data, list):
                documentos = []
                for item in data:
                    if isinstance(item, dict):
                        # Mapear campos da API PNCP para formato esperado
                        doc_formatted = {
                            'nome': item.get('titulo') or f"Documento_{item.get('sequencialDocumento', len(documentos)+1)}",
                            'url': item.get('url') or item.get('uri') or "",
                            'tipo': item.get('tipoDocumentoNome') or item.get('tipoDocumentoDescricao') or "N/A",
                            'sequencial': item.get('sequencialDocumento', 0),
                            'data_publicacao': item.get('dataPublicacaoPncp', "N/A"),
                            'ativo': item.get('statusAtivo', True),
                            'descricao': item.get('tipoDocumentoDescricao', ""),
                            'original': item  # Manter dados originais para debug
                        }
                        documentos.append(doc_formatted)
                return documentos
            else:
                return []
        else:
            print(f"Erro na consulta de documentos para {numero_controle}: {response.status_code}")
            return []
            
    except ValueError as e:
        raise e
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao buscar documentos: {e}")
        return []
    except Exception as e:
        print(f"Erro inesperado ao buscar documentos: {e}")
        return []

def generate_keywords(text, max_keywords=10, max_chars=200):
    """
    Gera palavras-chave para um texto usando OpenAI GPT.
    
    Args:
        text (str): Texto para gerar palavras-chave
        max_keywords (int): Número máximo de palavras-chave (padrão: 10)
        max_chars (int): Limite de caracteres para as palavras-chave (padrão: 200)
        
    Returns:
        str: Palavras-chave separadas por ponto e vírgula ou mensagem de erro
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "Texto não fornecido"
    
    # Limitar tamanho do texto para evitar tokens excessivos
    if len(text) > 2000:
        text = text[:2000] + "..."
    
    prompt = f"""
Resuma o conteúdo a seguir em 5 a {max_keywords} tópicos de palavras-chave separados por ponto e vírgula, sem numeração.
Comece com o título, o tipo e o propósito, e depois destaque os principais tópicos abordados.
Use apenas palavras-chave. Limite: {max_chars} caracteres.
Texto: {text}
Exemplo: "Edital; Pregão Eletrônico; Aquisição de Equipamentos; Especificações Técnicas; Critérios de Avaliação"
"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que resume textos em palavras-chave relevantes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=150
        )
        
        keywords = completion.choices[0].message.content.strip()
        
        # Verificar se excede o limite de caracteres
        if len(keywords) > max_chars:
            keywords = keywords[:max_chars-3] + "..."
            
        return keywords
        
    except Exception as e:
        print(f"Erro ao gerar palavras-chave: {e}")
        return "Erro ao gerar palavras-chave"

def format_date(date_value):
    """Formata uma data para string no formato DD/MM/YYYY"""
    if date_value is None or date_value == "N/A":
        return "N/A"
    
    # Se já é string no formato YYYY-MM-DD
    if isinstance(date_value, str):
        # Primeiro garantir que está no formato ISO
        date_str = date_value[:10] if len(date_value) >= 10 else date_value
        
        # Verificar se está no formato YYYY-MM-DD
        if len(date_str) == 10 and date_str.count('-') == 2:
            try:
                year, month, day = date_str.split('-')
                return f"{day}/{month}/{year}"
            except:
                return date_str
        return date_str
    
    # Se é datetime, converter para DD/MM/YYYY
    if hasattr(date_value, 'strftime'):
        return date_value.strftime('%d/%m/%Y')
    
    # Para qualquer outro tipo, tentar converter
    try:
        date_str = str(date_value)[:10]
        if len(date_str) == 10 and date_str.count('-') == 2:
            year, month, day = date_str.split('-')
            return f"{day}/{month}/{year}"
        return date_str
    except:
        return "N/A"

def decode_poder(poder_code):
    """Decodifica o código do poder para nome completo"""
    poder_map = {
        'E': 'Executivo',
        'L': 'Legislativo', 
        'J': 'Judiciário',
        'N': 'Não especificado'
    }
    
    if not poder_code or poder_code == 'N/A':
        return 'N/A'
    
    # Converter para string e pegar primeiro caractere em maiúsculo
    code = str(poder_code).upper().strip()
    return poder_map.get(code, f'Desconhecido ({code})')

def decode_esfera(esfera_code):
    """Decodifica o código da esfera para nome completo"""
    esfera_map = {
        'F': 'Federal',
        'E': 'Estadual',
        'M': 'Municipal',
        'N': 'Não especificado'
    }
    
    if not esfera_code or esfera_code == 'N/A':
        return 'N/A'
    
    # Converter para string e pegar primeiro caractere em maiúsculo
    code = str(esfera_code).upper().strip()
    return esfera_map.get(code, f'Desconhecido ({code})')



