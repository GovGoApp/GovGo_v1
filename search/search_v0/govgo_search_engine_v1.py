"""
govgo_search_engine_v1.py
Módulo Unificado de Busca GovGo V1 - Sistema Completo de Busca PNCP
=================================================================

Este módulo unifica TODAS as funcionalidades dos sistemas V0:
• gvg_search_utils_v2.py (base)
• gvg_search_utils_v3.py (inteligente)  
• gvg_pre_processing_v3.py (processamento)
• gvg_document_utils_v3_o.py / v2.py (documentos)

🎯 FUNCIONALIDADES PRINCIPAIS:
• Busca semântica, palavras-chave e híbrida
• Sistema de relevância 3 níveis com IA
• Processamento inteligente de consultas
• Análise e sumarização de documentos
• Conexão unificada com Supabase V1
• Compatibilidade com sistema V0

🔧 CONFIGURAÇÃO V1:
• Nova base Supabase V1: hemztmtbejcbhgfmsvfq
• Configurações atualizadas do .env V1
• Estrutura de diretórios V1
• Modelos OpenAI atualizados
"""

import os
import sys
import time
import json
import locale
import re
import math
import requests
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

# Importações OpenAI e outros
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Rich para interface (opcional)
try:
    from rich.console import Console
    from rich.progress import Progress
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# ============================================================================
# CONFIGURAÇÕES V1
# ============================================================================

# Carregar configurações V1 do .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configurações de Banco V1
SUPABASE_V1_HOST = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
SUPABASE_V1_PORT = os.getenv('SUPABASE_PORT', '6543')
SUPABASE_V1_USER = os.getenv('SUPABASE_USER', 'postgres.hemztmtbejcbhgfmsvfq')
SUPABASE_V1_PASSWORD = os.getenv('SUPABASE_PASSWORD', 'GovGoApp2025!')
SUPABASE_V1_DBNAME = os.getenv('SUPABASE_DBNAME', 'postgres')
SUPABASE_V1_URL = os.getenv('SUPABASE_URL', 'https://hemztmtbejcbhgfmsvfq.supabase.co')
SUPABASE_V1_KEY = os.getenv('SUPABASE_KEY', 'sua_chave_supabase_v1_aqui')

# Configurações OpenAI V1
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL_EMBEDDINGS = os.getenv('OPENAI_MODEL_EMBEDDINGS', 'text-embedding-3-large')
OPENAI_MODEL_CHAT = os.getenv('OPENAI_MODEL_CHAT', 'gpt-4o')

# IDs dos Assistants V1
OPENAI_ASSISTANT_FLEXIBLE = os.getenv('OPENAI_ASSISTANT_FLEXIBLE', 'asst_tfD5oQxSgoGhtqdKQHK9UwRi')
OPENAI_ASSISTANT_RESTRICTIVE = os.getenv('OPENAI_ASSISTANT_RESTRICTIVE', 'asst_XmsefQEKbuVWu51uNST7kpYT')
OPENAI_ASSISTANT_PREPROCESSING = os.getenv('OPENAI_ASSISTANT_PREPROCESSING', 'asst_argxuo1SK6KE3HS5RGo4VRBV')
OPENAI_ASSISTANT_SEARCH_FILTER = os.getenv('OPENAI_ASSISTANT_SEARCH_FILTER', 'asst_sc5so6LwQEhB6G9FcVSten0S')

# Configurações de Busca V1
SEARCH_MAX_RESULTS = int(os.getenv('SEARCH_MAX_RESULTS', '50'))
SEARCH_SIMILARITY_THRESHOLD = float(os.getenv('SEARCH_SIMILARITY_THRESHOLD', '0.7'))
SEARCH_ENABLE_HYBRID = os.getenv('SEARCH_ENABLE_HYBRID', 'true').lower() == 'true'
SEARCH_ENABLE_FTS = os.getenv('SEARCH_ENABLE_FTS', 'true').lower() == 'true'

# Configurações de Diretórios V1
BASE_PATH = os.getenv('BASE_PATH', 'C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v1\\data\\')
RESULTS_PATH = os.getenv('RESULTS_PATH', os.path.join(BASE_PATH, 'reports'))
FILES_PATH = os.getenv('FILES_PATH', os.path.join(BASE_PATH, 'files'))
TEMP_PATH = os.getenv('TEMP_PATH', os.path.join(BASE_PATH, 'temp'))

# Configurações de Processamento V1
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CACHE_EMBEDDINGS = os.getenv('CACHE_EMBEDDINGS', 'true').lower() == 'true'

# Sistema de Relevância V1
RELEVANCE_SYSTEM_ENABLED = os.getenv('RELEVANCE_SYSTEM_ENABLED', 'true').lower() == 'true'
RELEVANCE_DEFAULT_LEVEL = int(os.getenv('RELEVANCE_DEFAULT_LEVEL', '2'))

# ============================================================================
# CLASSES DE CONFIGURAÇÃO
# ============================================================================

@dataclass
class SearchConfig:
    """Configuração de busca unificada"""
    max_results: int = SEARCH_MAX_RESULTS
    similarity_threshold: float = SEARCH_SIMILARITY_THRESHOLD
    enable_hybrid: bool = SEARCH_ENABLE_HYBRID
    enable_fts: bool = SEARCH_ENABLE_FTS
    relevance_level: int = RELEVANCE_DEFAULT_LEVEL
    use_negation_embeddings: bool = True
    filter_expired: bool = True
    semantic_weight: float = 0.75

@dataclass
class ProcessingConfig:
    """Configuração de processamento inteligente"""
    enable_intelligent: bool = True
    enable_debug: bool = False
    max_tokens: int = 2000
    batch_size: int = BATCH_SIZE
    max_workers: int = MAX_WORKERS
    chunk_size: int = CHUNK_SIZE

# ============================================================================
# CONSTANTES E ESTRUTURAS DE DADOS
# ============================================================================

# Tipos de busca
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

# Abordagens de busca
SEARCH_APPROACHES = {
    1: {"name": "Direta", "description": "Busca tradicional diretamente nos textos"},
    2: {"name": "Correspondência", "description": "Busca por correspondência categórica"},
    3: {"name": "Filtro", "description": "Usa categorias para restringir universo + busca textual"}
}

# Níveis de relevância
RELEVANCE_LEVELS = {
    1: {"name": "Sem filtro", "description": "Não aplica filtro de relevância"},
    2: {"name": "Flexível", "description": "Filtro flexível - inclui mais resultados"},
    3: {"name": "Restritivo", "description": "Filtro restritivo - apenas resultados muito relevantes"}
}

# Modos de ordenação
SORT_MODES = {
    1: {"name": "Similaridade", "description": "Ordenar por relevância (decrescente)"},
    2: {"name": "Data de Encerramento", "description": "Ordenar por data (ascendente)"},
    3: {"name": "Valor Estimado", "description": "Ordenar por valor (decrescente)"}
}

# ============================================================================
# INICIALIZAÇÃO DE CLIENTES
# ============================================================================

# Cliente OpenAI V1
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
    except Exception as e:
        print(f"⚠️ Erro ao inicializar OpenAI: {e}")
        OPENAI_AVAILABLE = False
else:
    print("⚠️ OPENAI_API_KEY não configurada")
    OPENAI_AVAILABLE = False

# Configurar locale
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

# ============================================================================
# CLASSES PRINCIPAIS
# ============================================================================

class GovGoSearchEngine:
    """
    Motor de Busca Principal do GovGo V1
    
    Unifica todas as funcionalidades de busca:
    • Conexão com Supabase V1
    • Busca semântica, palavras-chave e híbrida  
    • Sistema de relevância 3 níveis
    • Processamento inteligente de consultas
    • Análise de documentos
    """
    
    def __init__(self, config: SearchConfig = None):
        self.config = config or SearchConfig()
        self._connection = None
        self._engine = None
        self.intelligent_enabled = True
        self.debug_enabled = False
        self.relevance_level = self.config.relevance_level
        
    def connect(self) -> bool:
        """Conecta ao banco Supabase V1"""
        try:
            self._connection = psycopg2.connect(
                host=SUPABASE_V1_HOST,
                port=SUPABASE_V1_PORT,
                user=SUPABASE_V1_USER,
                password=SUPABASE_V1_PASSWORD,
                database=SUPABASE_V1_DBNAME
            )
            
            # Criar engine SQLAlchemy também
            connection_string = f"postgresql://{SUPABASE_V1_USER}:{SUPABASE_V1_PASSWORD}@{SUPABASE_V1_HOST}:{SUPABASE_V1_PORT}/{SUPABASE_V1_DBNAME}"
            self._engine = create_engine(connection_string)
            
            if console:
                console.print("[green]✓ Conectado ao Supabase V1[/green]")
            else:
                print("✓ Conectado ao Supabase V1")
                
            return True
            
        except Exception as e:
            error_msg = f"❌ Erro ao conectar com Supabase V1: {e}"
            if console:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(error_msg)
            return False
    
    def test_connection(self) -> bool:
        """Testa a conexão com o banco"""
        try:
            if not self._connection:
                return self.connect()
                
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
            
        except Exception as e:
            if console:
                console.print(f"[red]❌ Falha no teste de conexão: {e}[/red]")
            else:
                print(f"❌ Falha no teste de conexão: {e}")
            return False
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Gera embedding usando OpenAI V1"""
        if not OPENAI_AVAILABLE:
            return None
            
        try:
            response = openai_client.embeddings.create(
                input=text,
                model=OPENAI_MODEL_EMBEDDINGS
            )
            return response.data[0].embedding
            
        except Exception as e:
            if self.debug_enabled:
                error_msg = f"❌ Erro ao gerar embedding: {e}"
                if console:
                    console.print(f"[red]{error_msg}[/red]")
                else:
                    print(error_msg)
            return None
    
    def semantic_search(self, query: str, limit: int = None) -> Tuple[List[Dict], float]:
        """Busca semântica V1"""
        limit = limit or self.config.max_results
        
        # Gerar embedding da query
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return [], 0.0
        
        try:
            cursor = self._connection.cursor()
            
            # Query de busca semântica
            sql_query = """
            SELECT 
                c.numero_controle_pncp,
                c.ano_compra,
                c.objeto_compra as descricaoCompleta,
                c.valor_total_homologado,
                c.valor_total_estimado,
                c.data_abertura_proposta,
                c.data_encerramento_proposta,
                c.data_inclusao,
                c.link_sistema_origem,
                c.modalidade_id,
                c.modalidade_nome,
                c.modo_disputa_id,
                c.modo_disputa_nome,
                c.usuario_nome,
                c.orgao_entidade_poder_id,
                c.orgao_entidade_esfera_id,
                c.unidade_orgao_uf_sigla,
                c.unidade_orgao_municipio_nome,
                c.unidade_orgao_nome_unidade,
                c.orgao_entidade_razao_social,
                1 - (ce.embeddings <=> %s::vector) AS similarity
            FROM 
                contratacao c
            JOIN 
                contratacao_emb ce ON c.numero_controle_pncp = ce.numero_controle_pncp
            WHERE 
                ce.embeddings IS NOT NULL
            """
            
            # Adicionar filtro de data se habilitado
            if self.config.filter_expired:
                sql_query += " AND c.data_encerramento_proposta >= CURRENT_DATE"
            
            sql_query += f"""
            ORDER BY 
                similarity DESC
            LIMIT %s
            """
            
            cursor.execute(sql_query, (query_embedding, limit))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            # Formatar resultados
            formatted_results = []
            for i, row in enumerate(results, 1):
                result_dict = dict(zip(column_names, row))
                formatted_results.append({
                    "rank": i,
                    "id": result_dict["numero_controle_pncp"],
                    "similarity": float(result_dict["similarity"]),
                    "search_type": "semantic",
                    "details": result_dict
                })
            
            # Calcular confiança
            similarities = [r["similarity"] for r in formatted_results]
            confidence = self.calculate_confidence(similarities)
            
            cursor.close()
            return formatted_results, confidence
            
        except Exception as e:
            error_msg = f"❌ Erro na busca semântica: {e}"
            if console:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(error_msg)
            return [], 0.0
    
    def keyword_search(self, query: str, limit: int = None) -> Tuple[List[Dict], float]:
        """Busca por palavras-chave V1"""
        limit = limit or self.config.max_results
        
        try:
            cursor = self._connection.cursor()
            
            # Preparar termos para busca FTS
            search_terms = self.prepare_fts_query(query)
            
            sql_query = """
            SELECT 
                c.numero_controle_pncp,
                c.ano_compra,
                c.objeto_compra as descricaoCompleta,
                c.valor_total_homologado,
                c.valor_total_estimado,
                c.data_abertura_proposta,
                c.data_encerramento_proposta,
                c.data_inclusao,
                c.link_sistema_origem,
                c.modalidade_id,
                c.modalidade_nome,
                c.modo_disputa_id,
                c.modo_disputa_nome,
                c.usuario_nome,
                c.orgao_entidade_poder_id,
                c.orgao_entidade_esfera_id,
                c.unidade_orgao_uf_sigla,
                c.unidade_orgao_municipio_nome,
                c.unidade_orgao_nome_unidade,
                c.orgao_entidade_razao_social,
                ts_rank_cd(to_tsvector('portuguese', c.objeto_compra), to_tsquery('portuguese', %s)) AS relevance
            FROM 
                contratacao c
            WHERE 
                to_tsvector('portuguese', c.objeto_compra) @@ to_tsquery('portuguese', %s)
            """
            
            if self.config.filter_expired:
                sql_query += " AND c.data_encerramento_proposta >= CURRENT_DATE"
            
            sql_query += """
            ORDER BY 
                relevance DESC
            LIMIT %s
            """
            
            cursor.execute(sql_query, (search_terms, search_terms, limit))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            # Formatar resultados
            formatted_results = []
            for i, row in enumerate(results, 1):
                result_dict = dict(zip(column_names, row))
                formatted_results.append({
                    "rank": i,
                    "id": result_dict["numero_controle_pncp"],
                    "similarity": float(result_dict["relevance"]) if result_dict["relevance"] else 0.0,
                    "search_type": "keyword",
                    "details": result_dict
                })
            
            # Calcular confiança
            similarities = [r["similarity"] for r in formatted_results]
            confidence = self.calculate_confidence(similarities)
            
            cursor.close()
            return formatted_results, confidence
            
        except Exception as e:
            error_msg = f"❌ Erro na busca por palavras-chave: {e}"
            if console:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(error_msg)
            return [], 0.0
    
    def hybrid_search(self, query: str, limit: int = None) -> Tuple[List[Dict], float]:
        """Busca híbrida (semântica + palavras-chave) V1"""
        limit = limit or self.config.max_results
        
        # Executar ambas as buscas
        semantic_results, semantic_conf = self.semantic_search(query, limit * 2)
        keyword_results, keyword_conf = self.keyword_search(query, limit * 2)
        
        if not semantic_results and not keyword_results:
            return [], 0.0
        
        # Combinar resultados
        combined_results = {}
        
        # Adicionar resultados semânticos
        for result in semantic_results:
            result_id = result["id"]
            combined_results[result_id] = {
                **result,
                "semantic_score": result["similarity"],
                "keyword_score": 0.0,
                "search_type": "hybrid"
            }
        
        # Adicionar/combinar resultados de palavras-chave
        for result in keyword_results:
            result_id = result["id"]
            if result_id in combined_results:
                combined_results[result_id]["keyword_score"] = result["similarity"]
            else:
                combined_results[result_id] = {
                    **result,
                    "semantic_score": 0.0,
                    "keyword_score": result["similarity"],
                    "search_type": "hybrid"
                }
        
        # Calcular score combinado
        for result in combined_results.values():
            semantic_norm = result["semantic_score"]
            keyword_norm = result["keyword_score"] / max([r["keyword_score"] for r in keyword_results] + [1])
            
            combined_score = (
                self.config.semantic_weight * semantic_norm + 
                (1 - self.config.semantic_weight) * keyword_norm
            )
            result["similarity"] = combined_score
        
        # Ordenar e limitar
        final_results = sorted(
            combined_results.values(), 
            key=lambda x: x["similarity"], 
            reverse=True
        )[:limit]
        
        # Atualizar ranks
        for i, result in enumerate(final_results, 1):
            result["rank"] = i
        
        # Calcular confiança
        similarities = [r["similarity"] for r in final_results]
        confidence = self.calculate_confidence(similarities)
        
        return final_results, confidence
    
    def calculate_confidence(self, similarities: List[float]) -> float:
        """Calcula confiança dos resultados"""
        if not similarities:
            return 0.0
        
        # Algoritmo baseado na versão original
        avg_similarity = np.mean(similarities)
        std_similarity = np.std(similarities)
        
        # Penalizar alta variabilidade
        confidence = avg_similarity * (1 - std_similarity)
        
        # Bonus para múltiplos resultados relevantes
        high_sim_count = sum(1 for sim in similarities if sim > 0.7)
        if high_sim_count > 1:
            confidence *= (1 + 0.1 * min(high_sim_count - 1, 5))
        
        return max(0.0, min(1.0, confidence))
    
    def prepare_fts_query(self, query: str) -> str:
        """Prepara query para Full Text Search"""
        # Remover caracteres especiais e normalizar
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        terms = [term.strip() for term in cleaned.split() if len(term.strip()) > 2]
        
        if not terms:
            return query
        
        # Criar query FTS
        fts_query = ' & '.join(f"{term}:*" for term in terms)
        return fts_query
    
    def get_top_categories(self, query: str, top_n: int = 10) -> List[Dict]:
        """Busca TOP N categorias mais similares à query"""
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        try:
            cursor = self._connection.cursor()
            
            sql_query = """
            SELECT 
                id_categoria, cod_cat, nom_cat, cod_nv0, nom_nv0, cod_nv1, nom_nv1, cod_nv2, nom_nv2, cod_nv3, nom_nv3,
                1 - (cat_embeddings <=> %s::vector) AS similarity
            FROM categoria
            WHERE cat_embeddings IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s
            """
            
            cursor.execute(sql_query, (query_embedding, top_n))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            categories = []
            for i, row in enumerate(results, 1):
                result_dict = dict(zip(column_names, row))
                categories.append({
                    'rank': i,
                    'categoria_id': result_dict['id_categoria'],
                    'codigo': result_dict['cod_cat'],
                    'descricao': result_dict['nom_cat'],
                    'similarity_score': float(result_dict['similarity'])
                })
            
            cursor.close()
            return categories
            
        except Exception as e:
            error_msg = f"❌ Erro ao buscar categorias: {e}"
            if console:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(error_msg)
            return []

# ============================================================================
# FUNÇÕES AUXILIARES (COMPATIBILIDADE V0)
# ============================================================================

def create_connection():
    """Compatibilidade V0 - Cria conexão simples"""
    return psycopg2.connect(
        host=SUPABASE_V1_HOST,
        port=SUPABASE_V1_PORT,
        user=SUPABASE_V1_USER,
        password=SUPABASE_V1_PASSWORD,
        database=SUPABASE_V1_DBNAME
    )

def test_connection() -> bool:
    """Compatibilidade V0 - Testa conexão"""
    engine = GovGoSearchEngine()
    return engine.test_connection()

def format_currency(value) -> str:
    """Formatar valores monetários"""
    try:
        if value is None or value == 0:
            return "R$ 0,00"
        
        # Usar locale se disponível
        try:
            return locale.currency(float(value), grouping=True, symbol=True)
        except:
            # Fallback manual
            return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def format_date(date_value) -> str:
    """Formatar datas"""
    if not date_value or date_value == "N/A":
        return "N/A"
    
    try:
        if isinstance(date_value, str):
            # Tentar diferentes formatos
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    date_obj = datetime.strptime(date_value[:10] if len(date_value) > 10 else date_value, fmt[:10])
                    return date_obj.strftime("%d/%m/%Y")
                except:
                    continue
            return str(date_value)
        elif hasattr(date_value, 'strftime'):
            return date_value.strftime("%d/%m/%Y")
        else:
            return str(date_value)
    except:
        return "N/A"

def decode_poder(poder_id) -> str:
    """Decodificar ID do poder"""
    poder_map = {
        "1": "Executivo",
        "2": "Legislativo", 
        "3": "Judiciário",
        "4": "Ministério Público",
        "5": "Outros"
    }
    return poder_map.get(str(poder_id), f"Poder {poder_id}")

def decode_esfera(esfera_id) -> str:
    """Decodificar ID da esfera"""
    esfera_map = {
        "1": "Federal",
        "2": "Estadual",
        "3": "Distrital", 
        "4": "Municipal"
    }
    return esfera_map.get(str(esfera_id), f"Esfera {esfera_id}")

# ============================================================================
# FUNÇÕES PRINCIPAIS PARA COMPATIBILIDADE V0
# ============================================================================

def intelligent_semantic_search(query: str, limit: int = 30, min_results: int = 5, 
                               filter_expired: bool = True, use_negation_embeddings: bool = True,
                               enable_intelligent: bool = True) -> Tuple[List[Dict], float]:
    """Compatibilidade V0 - Busca semântica inteligente"""
    engine = GovGoSearchEngine()
    engine.config.max_results = limit
    engine.config.filter_expired = filter_expired
    
    if not engine.connect():
        return [], 0.0
    
    return engine.semantic_search(query, limit)

def intelligent_keyword_search(query: str, limit: int = 30, min_results: int = 5,
                              filter_expired: bool = True, enable_intelligent: bool = True) -> Tuple[List[Dict], float]:
    """Compatibilidade V0 - Busca por palavras-chave inteligente"""
    engine = GovGoSearchEngine()
    engine.config.max_results = limit
    engine.config.filter_expired = filter_expired
    
    if not engine.connect():
        return [], 0.0
    
    return engine.keyword_search(query, limit)

def intelligent_hybrid_search(query: str, limit: int = 30, min_results: int = 5, 
                             semantic_weight: float = 0.75, filter_expired: bool = True,
                             use_negation_embeddings: bool = True, enable_intelligent: bool = True) -> Tuple[List[Dict], float]:
    """Compatibilidade V0 - Busca híbrida inteligente"""
    engine = GovGoSearchEngine()
    engine.config.max_results = limit
    engine.config.filter_expired = filter_expired
    engine.config.semantic_weight = semantic_weight
    
    if not engine.connect():
        return [], 0.0
    
    return engine.hybrid_search(query, limit)

def get_embedding(text: str) -> Optional[List[float]]:
    """Compatibilidade V0 - Gerar embedding"""
    engine = GovGoSearchEngine()
    return engine.get_embedding(text)

def calculate_confidence(similarities: List[float]) -> float:
    """Compatibilidade V0 - Calcular confiança"""
    engine = GovGoSearchEngine()
    return engine.calculate_confidence(similarities)

# ============================================================================
# FUNÇÕES DE ESTADO GLOBAL (COMPATIBILIDADE V0)
# ============================================================================

_intelligent_processing_enabled = True
_intelligent_debug_enabled = False
_relevance_filter_level = RELEVANCE_DEFAULT_LEVEL
_relevance_filter_enabled = RELEVANCE_SYSTEM_ENABLED

def toggle_intelligent_processing(new_status: bool = None) -> Dict[str, Any]:
    """Toggle do processamento inteligente"""
    global _intelligent_processing_enabled
    
    if new_status is not None:
        _intelligent_processing_enabled = new_status
    else:
        _intelligent_processing_enabled = not _intelligent_processing_enabled
    
    return {
        'intelligent_processing_enabled': _intelligent_processing_enabled,
        'debug_enabled': _intelligent_debug_enabled
    }

def toggle_intelligent_debug(new_status: bool = None) -> Dict[str, Any]:
    """Toggle do debug inteligente"""
    global _intelligent_debug_enabled
    
    if new_status is not None:
        _intelligent_debug_enabled = new_status
    else:
        _intelligent_debug_enabled = not _intelligent_debug_enabled
    
    return {
        'intelligent_processing_enabled': _intelligent_processing_enabled,
        'debug_enabled': _intelligent_debug_enabled
    }

def get_intelligent_status() -> Dict[str, Any]:
    """Status do processamento inteligente"""
    return {
        'intelligent_processing_enabled': _intelligent_processing_enabled,
        'debug_enabled': _intelligent_debug_enabled
    }

def set_relevance_filter_level(level: int) -> Dict[str, Any]:
    """Definir nível do filtro de relevância"""
    global _relevance_filter_level, _relevance_filter_enabled
    
    if level in RELEVANCE_LEVELS:
        _relevance_filter_level = level
        _relevance_filter_enabled = level > 1
    
    return get_relevance_filter_status()

def get_relevance_filter_status() -> Dict[str, Any]:
    """Status do filtro de relevância"""
    return {
        'relevance_filter_enabled': _relevance_filter_enabled,
        'relevance_filter_level': _relevance_filter_level,
        'level_name': RELEVANCE_LEVELS.get(_relevance_filter_level, {}).get('name', 'Desconhecido')
    }

# ============================================================================
# FUNÇÕES PLACEHOLDER (A IMPLEMENTAR)
# ============================================================================

def parse_numero_controle_pncp(numero: str) -> Dict[str, str]:
    """Parse do número de controle PNCP - TODO: Implementar"""
    return {"numero": numero, "ano": "2025", "sequencia": "000001"}

def fetch_documentos(numero_controle: str) -> List[Dict]:
    """Buscar documentos do PNCP - TODO: Implementar"""
    return []

def generate_keywords(description: str) -> str:
    """Gerar palavras-chave - TODO: Implementar"""
    return "palavras-chave geradas"

def extract_pos_neg_terms(query: str) -> Tuple[str, str]:
    """Extrair termos positivos e negativos - TODO: Implementar"""
    return query, ""

def get_negation_embedding(query: str) -> Optional[List[float]]:
    """Embedding com negação - TODO: Implementar"""
    engine = GovGoSearchEngine()
    return engine.get_embedding(query)

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Teste básico
    print("GovGo Search Engine V1 - Teste de Inicialização")
    
    # Criar engine
    engine = GovGoSearchEngine()
    
    # Testar conexão
    if engine.connect():
        print("✅ Conexão estabelecida com sucesso!")
        
        # Teste de busca simples
        results, confidence = engine.semantic_search("notebooks para escolas", limit=5)
        print(f"📊 Encontrados {len(results)} resultados com confiança {confidence:.3f}")
        
        for result in results[:3]:
            print(f"#{result['rank']} - {result['id']} (sim: {result['similarity']:.3f})")
    else:
        print("❌ Falha na conexão")
