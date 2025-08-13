#!/usr/bin/env python3
"""
GvG_Search_Prompt_v0.py
Sistema de Busca PNCP via Linha de Comando - Baseado no Terminal v9

🚀 INTERFACE DE LINHA DE COMANDO PARA O SISTEMA v9
Este script permite executar buscas do GvG Search Terminal v9 diretamente 
pela linha de comando, ideal para automação, scripts e integração com outros sistemas.

🎯 FUNCIONALIDADES PRINCIPAIS:
• Busca semântica, palavras-chave e híbrida com IA
• Sistema de relevância 3 níveis (sem filtro, flexível, restritivo)
• Três abordagens: direta, correspondência, filtro por categorias
• Processamento inteligente v3 com condições SQL automáticas
• Exportação automática em JSON e LOG detalhado
• Suporte a negation embeddings e filtros avançados

🔧 USO BÁSICO:
    python GvG_Search_Prompt_v0.py --prompt "sua consulta aqui"

📋 PARÂMETROS DISPONÍVEIS:
    --prompt TEXT              🔍 Query de busca (OBRIGATÓRIO)
    --search {1,2,3}, -S, -s  🤖 Tipo: 1=Semântica, 2=Palavras-chave, 3=Híbrida (padrão: 1)
    --approach {1,2,3}, -A, -a 📊 Abordagem: 1=Direta, 2=Correspondência, 3=Filtro (padrão: 3)
    --relevance {1,2,3}, -R, -r 🎯 Relevância: 1=sem filtro, 2=flexível, 3=restritivo (padrão: 1)
    --order {1,2,3}, -O, -o    📈 Ordenação: 1=Similaridade, 2=Data, 3=Valor (padrão: 3)
    --intelligent, -I, -i      🧠 Toggle processamento inteligente (flag)
    --max_results INT         📝 Número máximo de resultados (padrão: 30)
    --top_cat INT             🏷️  Número de TOP categorias (padrão: 10)
    --doc_processor {v2,v3}   📄 Processador: v2=MarkItDown, v3=Docling (padrão: v3)
    --filter_expired          ⏰ Filtrar contratações encerradas (flag, padrão: ativo)
    --negation_emb            🚫 Usar negation embeddings (flag, padrão: ativo)
    --debug                   🐛 Interface visual com barras de progresso [1/6] até [6/6] (flag, padrão: inativo)
    --output_dir PATH         📁 Diretório de saída (padrão: pasta Relatórios)
    --help                    ❓ Mostrar ajuda completa

💾 ARQUIVOS DE SAÍDA:
    - JSON: Resultados estruturados para análise/importação
    - LOG: Arquivo detalhado com tabelas, metadados e parâmetros

🎯 EXEMPLOS PRÁTICOS:
    # Busca semântica simples
    python GvG_Search_Prompt_v0.py --prompt "notebooks para escolas"
    
    # Busca híbrida com filtro restritivo e interface visual (usando aliases)
    python GvG_Search_Prompt_v0.py --prompt "limpeza hospitalar" -s 3 -r 3 --debug
    
    # Busca com negation embeddings e toggle do processamento inteligente
    python GvG_Search_Prompt_v0.py --prompt "TI --terceirização --outsourcing" -i --debug
    
    # Busca por correspondência de categorias com aliases curtos
    python GvG_Search_Prompt_v0.py --prompt "uniformes escolares" -a 2 -o 1 --debug
    
    # Exemplo completo com todos os aliases
    python GvG_Search_Prompt_v0.py --prompt "medicamentos" -s 3 -a 3 -r 2 -o 3 -i

⚙️ REQUISITOS:
• Sistema v9 configurado (gvg_search_utils_v3.py)
• Banco PostgreSQL com pgvector
• OpenAI API key para processamento inteligente
• Rich library para interface visual (opcional: pip install rich)
"""

import os
import sys
import time
import json
import locale
import argparse
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import pandas as pd
import numpy as np
import locale

# Importar módulos necessários
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Rich imports para interface visual (barras de progresso)
try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️ Rich não disponível - modo texto simples ativado")

# Configurações padrão (herdadas do v9)
DEFAULT_PREPROC_PARAMS = {
    "remove_special_chars": True,
    "keep_separators": True,
    "remove_accents": False,
    "case": "lower",
    "remove_stopwords": False,
    "lemmatize": True
}



# Importar funções de busca (apenas v3)
from gvg_search_utils_v3 import (
    create_connection,
    intelligent_semantic_search as semantic_search,
    intelligent_keyword_search as keyword_search,
    intelligent_hybrid_search as hybrid_search,
    calculate_confidence,
    format_currency,
    test_connection,
    get_embedding,
    parse_numero_controle_pncp,
    fetch_documentos,
    generate_keywords,
    decode_poder,
    decode_esfera,
    format_date,
    extract_pos_neg_terms,
    get_negation_embedding,
    # Funções específicas do v3
    toggle_intelligent_processing,
    toggle_intelligent_debug,
    get_intelligent_status,
    # Funções do filtro de relevância (sistema de 3 níveis)
    set_relevance_filter_level,
    get_relevance_filter_status
)

# Configurar locale para formatação de valores
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass


# Carregar variáveis de diretório do dir.env (se existir)
from dotenv import load_dotenv
dir_env_path = os.path.join(os.path.dirname(__file__), 'dir.env')
if os.path.exists(dir_env_path):
    load_dotenv(dir_env_path)

# Diretórios padrão lidos do dir.env ou fallback para os antigos
BASE_PATH = os.environ.get('BASE_PATH', "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\Terminal\\")
RESULTS_PATH = os.environ.get('RESULTS_PATH', BASE_PATH + "Relatórios\\")

# Constantes padrão (herdadas do v9)
MIN_RESULTS = 5
MAX_RESULTS = 30
MAX_TOKENS = 2000
SEMANTIC_WEIGHT = 0.75

# Estruturas de configuração (herdadas do v9)
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

SEARCH_APPROACHES = {
    1: {"name": "Direta", "description": "Busca tradicional diretamente nos textos (sem categorias)"},
    2: {"name": "Correspondência", "description": "Busca por correspondência categórica (multiplicação de similarities)"},
    3: {"name": "Filtro", "description": "Usa categorias para restringir universo + busca textual"}
}

SORT_MODES = {
    1: {"name": "Similaridade", "description": "Ordenar por relevância (decrescente)"},
    2: {"name": "Data de Encerramento", "description": "Ordenar por data (ascendente)"},
    3: {"name": "Valor Estimado", "description": "Ordenar por valor (decrescente)"}
}

# ====================================================================================
# SISTEMA DE PROGRESSO VISUAL (RICH)
# ====================================================================================

def create_progress_display(console=None):
    """Cria interface de progresso visual com Rich usando console compartilhado."""
    if not RICH_AVAILABLE:
        return None
    
    # Se não tiver console passado, criar um novo
    if console is None:
        console = Console()
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,  # Usar o console passado/criado
        expand=True
    )

def safe_print(message, debug_mode=False, console_obj=None):
    """Imprime mensagem de forma segura com ou sem Rich."""
    if debug_mode and RICH_AVAILABLE and console_obj:
        console_obj.print(message)
    else:
        print(message)

# ====================================================================================
# CONFIGURAÇÃO DE LOGGING
# ====================================================================================

def setup_logging(output_path, query):
    """Configura sistema de logging para arquivo."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
    query_clean = query_clean.upper().replace(" ", "_")[:30]
    
    log_filename = os.path.join(output_path, f"Busca_{query_clean}_LOG_{timestamp}.log")
    
    # Configurar logger
    logger = logging.getLogger('GvG_Search')
    logger.setLevel(logging.INFO)
    
    # Remover handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configurar handler para arquivo
    handler = logging.FileHandler(log_filename, encoding='utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger, log_filename

# ====================================================================================
# FUNÇÕES AUXILIARES (ADAPTADAS DO V9)
# ====================================================================================

def create_engine_connection():
    """Cria engine SQLAlchemy usando as mesmas credenciais do gvg_search_utils"""
    try:
        env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
        if not os.path.exists(env_path):
            return None
            
        load_dotenv(env_path)
        
        host = os.getenv('host', 'localhost')
        database = os.getenv('dbname', 'postgres')
        user = os.getenv('user', 'postgres')
        password = os.getenv('password', '')
        port = os.getenv('port', '5432')
        
        if port is None or port == 'None' or port == '':
            port = '5432'
        
        if not all([host, database, user]):
            return None
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return engine
        
    except Exception as e:
        return None

def get_top_categories_for_query(query_text, top_n=10, use_negation_embeddings=True, search_type=1):
    """Busca as TOP N categorias mais similares à query."""
    try:
        if use_negation_embeddings and search_type in [1, 3]:
            query_embedding = get_negation_embedding(query_text)
        else:
            query_embedding = get_embedding(query_text)
            
        if query_embedding is None:
            return []
        
        if isinstance(query_embedding, np.ndarray):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = query_embedding
        
        engine = create_engine_connection()
        if not engine:
            return []
        
        query = """
        SELECT 
            id, codcat, nomcat, codnv0, nomnv0, codnv1, nomnv1, codnv2, nomnv2, codnv3, nomnv3,
            1 - (cat_embeddings <=> %(embedding)s::vector) AS similarity
        FROM categorias
        WHERE cat_embeddings IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %(limit)s
        """
        
        df = pd.read_sql_query(
            query, 
            engine, 
            params={
                'embedding': query_embedding_list,
                'limit': top_n
            }
        )
        
        results = []
        for idx, row in df.iterrows():
            results.append({
                'rank': idx + 1,
                'categoria_id': row['id'],
                'codigo': row['codcat'],
                'descricao': row['nomcat'],
                'nivel0_cod': row['codnv0'],
                'nivel0_nome': row['nomnv0'],
                'nivel1_cod': row['codnv1'],
                'nivel1_nome': row['nomnv1'],
                'nivel2_cod': row['codnv2'],
                'nivel2_nome': row['nomnv2'],
                'nivel3_cod': row['codnv3'],
                'nivel3_nome': row['nomnv3'],
                'similarity_score': float(row['similarity'])
            })
        
        return results
        
    except Exception as e:
        return []

def convert_datetime_to_string(obj):
    """Converte objetos datetime para string formatada."""
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif obj is None:
        return ""
    else:
        return str(obj)

def safe_float_conversion(value):
    """Converte valores para float, tratando NaN como zero."""
    try:
        if value is None:
            return 0.0
        
        float_value = float(value)
        
        if np.isnan(float_value):
            return 0.0
            
        return float_value
    except (ValueError, TypeError):
        return 0.0

# ====================================================================================
# FUNÇÕES DE BUSCA (ADAPTADAS DO V9)
# ====================================================================================

def direct_search(query_text, search_type, limit=MAX_RESULTS, filter_expired=True, use_negation_embeddings=True):
    """Busca direta (sem categorias)."""
    try:
        # Verificar status do processamento inteligente
        intelligent_status = get_intelligent_status()
        enable_intelligent = intelligent_status.get('intelligent_processing_enabled', False) if intelligent_status else False
        
        if search_type == 1:  # Semântica
            results, confidence = semantic_search(query_text, limit, MIN_RESULTS, filter_expired, use_negation_embeddings, enable_intelligent)
        elif search_type == 2:  # Palavras-chave
            results, confidence = keyword_search(query_text, limit, MIN_RESULTS, filter_expired, enable_intelligent)
        elif search_type == 3:  # Híbrida
            results, confidence = hybrid_search(query_text, limit, MIN_RESULTS, SEMANTIC_WEIGHT, filter_expired, use_negation_embeddings, enable_intelligent)
        else:
            return [], 0.0
        
        for result in results:
            result["search_approach"] = "direct"
            result["search_type"] = search_type
        
        return results, confidence
        
    except Exception as e:
        return [], 0.0

def correspondence_search(query_text, top_categories, limit=MAX_RESULTS, filter_expired=True):
    """Busca por correspondência categórica."""
    try:
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # Obter condições SQL se disponíveis (modo inteligente sempre ativado)
        sql_conditions = []
        try:
            from gvg_pre_processing_v3 import SearchQueryProcessor
            processor = SearchQueryProcessor()
            processed = processor.process_query(query_text)
            sql_conditions = processed.get('sql_conditions', [])
        except Exception:
            pass
        
        connection = create_connection()
        cursor = connection.cursor()
        
        search_query = """
        SELECT 
            c.numeroControlePNCP, c.anoCompra, c.descricaoCompleta, c.valorTotalHomologado,
            c.valorTotalEstimado, c.dataAberturaProposta, c.dataEncerramentoProposta,
            c.dataInclusao, c.linkSistemaOrigem, c.modalidadeId, c.modalidadeNome,
            c.modaDisputaId, c.modaDisputaNome, c.usuarioNome, c.orgaoEntidade_poderId,
            c.orgaoEntidade_esferaId, c.unidadeOrgao_ufSigla, c.unidadeOrgao_municipioNome,
            c.unidadeOrgao_nomeUnidade, c.orgaoEntidade_razaosocial,
            ce.top_categories, ce.top_similarities
        FROM contratacoes c
        JOIN contratacoes_embeddings ce ON c.numeroControlePNCP = ce.numeroControlePNCP
        WHERE ce.top_categories IS NOT NULL
            AND ce.top_categories && %s
        """
        
        for condition in sql_conditions:
            search_query += f" AND {condition}"
        
        if filter_expired:
            search_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"
        
        cursor.execute(search_query, (category_codes,))
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        formatted_results = []
        for row in results:
            result_dict = dict(zip(column_names, row))
            
            correspondence_similarity = calculate_correspondence_similarity_score(
                top_categories, 
                result_dict['top_categories'], 
                result_dict['top_similarities']
            )
            
            top_category_info = find_top_category_for_result(
                top_categories,
                result_dict['top_categories'],
                result_dict['top_similarities']
            )
            
            formatted_results.append({
                "rank": 0,
                "id": result_dict["numerocontrolepncp"],
                "similarity": correspondence_similarity,
                "correspondence_similarity": correspondence_similarity,
                "top_category_info": top_category_info,
                "search_approach": "correspondence",
                "details": result_dict
            })
        
        formatted_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        for i, result in enumerate(formatted_results):
            result["rank"] = i + 1
        
        formatted_results = formatted_results[:limit]
        
        similarities = [r["similarity"] for r in formatted_results]
        confidence = calculate_confidence(similarities) if similarities else 0.0
        
        cursor.close()
        connection.close()
        
        return formatted_results, confidence
        
    except Exception as e:
        return [], 0.0

def category_filtered_search(query_text, search_type, top_categories, limit=MAX_RESULTS, filter_expired=True, use_negation_embeddings=True):
    """Busca com filtro categórico."""
    try:
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # Verificar status do processamento inteligente
        intelligent_status = get_intelligent_status()
        enable_intelligent = intelligent_status.get('intelligent_processing_enabled', False) if intelligent_status else False
        
        # Executar busca tradicional
        if search_type == 1:  # Semântica
            all_results, confidence = semantic_search(query_text, limit * 3, MIN_RESULTS, filter_expired, use_negation_embeddings, enable_intelligent)
        elif search_type == 2:  # Palavras-chave
            all_results, confidence = keyword_search(query_text, limit * 3, MIN_RESULTS, filter_expired, enable_intelligent)
        elif search_type == 3:  # Híbrida
            all_results, confidence = hybrid_search(query_text, limit * 3, MIN_RESULTS, SEMANTIC_WEIGHT, filter_expired, use_negation_embeddings, enable_intelligent)
        else:
            return [], 0.0
        
        if not all_results:
            return [], 0.0
        
        # Filtrar por categorias
        connection = create_connection()
        cursor = connection.cursor()
        
        filtered_results = []
        result_ids = [result['id'] for result in all_results]
        
        placeholders = ','.join(['%s'] * len(result_ids))
        category_query = f"""
        SELECT numeroControlePNCP, top_categories
        FROM contratacoes_embeddings
        WHERE numeroControlePNCP IN ({placeholders})
            AND top_categories IS NOT NULL
        """
        
        cursor.execute(category_query, result_ids)
        category_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.close()
        connection.close()
        
        for result in all_results:
            result_id = result['id']
            result_categories = category_data.get(result_id, [])
            
            if result_categories and any(cat_code in result_categories for cat_code in category_codes):
                result["search_approach"] = "category_filtered"
                result["search_type"] = search_type
                result["matched_categories"] = [cat for cat in category_codes if cat in result_categories]
                filtered_results.append(result)
            
            if len(filtered_results) >= limit:
                break
        
        for i, result in enumerate(filtered_results):
            result["rank"] = i + 1
        
        universe_size = len([r for r in all_results if category_data.get(r['id'])])
        for result in filtered_results:
            result["filtered_universe_size"] = universe_size
        
        return filtered_results, confidence
        
    except Exception as e:
        return [], 0.0

def calculate_correspondence_similarity_score(query_categories, result_categories, result_similarities):
    """Calcula score de correspondência."""
    try:
        if not query_categories or not result_categories or not result_similarities:
            return 0.0
        
        max_score = 0.0
        
        for query_cat in query_categories:
            query_code = query_cat['codigo']
            query_similarity = query_cat['similarity_score']
            
            if query_similarity is None or query_similarity == 0:
                continue
            
            if query_code in result_categories:
                try:
                    idx = result_categories.index(query_code)
                    result_similarity = result_similarities[idx]
                    
                    if result_similarity is None or result_similarity == 0:
                        continue
                    
                    correspondence_score = float(query_similarity) * float(result_similarity)
                    max_score = max(max_score, correspondence_score)
                    
                except (IndexError, ValueError, TypeError):
                    continue
        
        return max_score
        
    except Exception:
        return 0.0

def find_top_category_for_result(query_categories, result_categories, result_similarities):
    """Encontra categoria mais importante para resultado."""
    try:
        if not query_categories or not result_categories or not result_similarities:
            return None
        
        best_category = None
        best_score = 0.0
        
        for query_cat in query_categories:
            query_code = query_cat['codigo']
            query_similarity = query_cat['similarity_score']
            
            if query_similarity is None or query_similarity == 0:
                continue
            
            if query_code in result_categories:
                try:
                    idx = result_categories.index(query_code)
                    result_similarity = result_similarities[idx]
                    
                    if result_similarity is None or result_similarity == 0:
                        continue
                    
                    correspondence_score = float(query_similarity) * float(result_similarity)
                    
                    if correspondence_score > best_score:
                        best_score = correspondence_score
                        best_category = {
                            'codigo': query_cat['codigo'],
                            'descricao': query_cat['descricao'],
                            'query_similarity': query_similarity,
                            'result_similarity': result_similarity,
                            'correspondence_score': correspondence_score
                        }
                        
                except (IndexError, ValueError, TypeError):
                    continue
        
        return best_category
        
    except Exception:
        return None

# ====================================================================================
# FUNÇÕES DE EXPORTAÇÃO E LOGGING
# ====================================================================================

def generate_export_filename(query, search_type_id, search_approach, relevance_level, sort_mode, intelligent_enabled, output_path, extension="json"):
    """
    Gera nome padronizado para arquivos de exportação.
    Formato: Busca_{PROMPT}_{Sx}_{Ax}_{Rx}_{Ox}_{Ix}_{timestamp}.{extension}
    
    Args:
        query: Consulta original (PROMPT)
        search_type_id: ID do tipo de busca (S)
        search_approach: Abordagem de busca (A)
        relevance_level: Nível de relevância (R)
        sort_mode: Modo de ordenação (O)
        intelligent_enabled: Status do processamento inteligente (I)
        output_path: Caminho para salvar
        extension: Extensão do arquivo
    
    Returns:
        Caminho completo do arquivo
    """
    try:
        # Limpar e formatar a query (PROMPT em maiúscula)
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean.upper().replace(" ", "_")[:30]
        
        # Gerar timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Garantir que o diretório existe
        os.makedirs(output_path, exist_ok=True)
        
        # Converter intelligent_enabled para 1 ou 0
        intelligent_flag = 1 if intelligent_enabled else 0
        
        # Construir nome do arquivo no formato correto
        filename = f"Busca_{query_clean}_S{search_type_id}_A{search_approach}_R{relevance_level}_O{sort_mode}_I{intelligent_flag}_{timestamp}.{extension}"
        
        return os.path.join(output_path, filename)
    
    except Exception as e:
        # Fallback para formato simples em caso de erro
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"Busca_ERRO_{timestamp}.{extension}"
        return os.path.join(output_path, filename)

def export_results_to_json(results, query, search_type_id, search_approach, relevance_level, sort_mode, output_path):
    """Exporta resultados para JSON."""
    try:
        data = []
        for result in results:
            details = result.get("details", {})
            if details:
                record = {
                    "rank": result.get("rank", 0),
                    "id": result.get("id", ""),
                    "similarity": safe_float_conversion(result.get("similarity", 0)),
                    "orgao": details.get("orgaoentidade_razaosocial", ""),
                    "unidade": details.get("unidadeorgao_nomeunidade", ""),
                    "municipio": details.get("unidadeorgao_municipionome", ""),
                    "uf": details.get("unidadeorgao_ufsigla", ""),
                    "valor_estimado": safe_float_conversion(details.get("valortotalestimado", 0)),
                    "valor_homologado": safe_float_conversion(details.get("valortotalhomologado", 0)),
                    "data_inclusao": convert_datetime_to_string(details.get("datainclusao", "")),
                    "data_abertura": convert_datetime_to_string(details.get("dataaberturaproposta", "")),
                    "data_encerramento": convert_datetime_to_string(details.get("dataencerramentoproposta", "")),
                    "modalidade_id": details.get("modalidadeid", ""),
                    "modalidade_nome": details.get("modalidadenome", ""),
                    "disputa_id": details.get("modadisputaid", ""),
                    "disputa_nome": details.get("modadisputanome", ""),
                    "usuario": details.get("usuarionome", ""),
                    "poder": details.get("orgaoentidade_poderid", ""),
                    "esfera": details.get("orgaoentidade_esferaid", ""),
                    "link_sistema": details.get("linksistemaorigem", ""),
                    "descricao": details.get("descricaocompleta", "")
                }
                data.append(record)
        
        # Usar a função padronizada para gerar o nome do arquivo
        # Verificar status do processamento inteligente
        intelligent_status = get_intelligent_status()
        intelligent_enabled = intelligent_status.get('intelligent_processing_enabled', False) if intelligent_status else False
        
        filename = generate_export_filename(
            query=query,
            search_type_id=search_type_id,
            search_approach=search_approach,
            relevance_level=relevance_level,
            sort_mode=sort_mode,
            intelligent_enabled=intelligent_enabled,
            output_path=output_path,
            extension="json"
        )
        
        json_data = {
            "metadata": {
                "query": query,
                "search_type": SEARCH_TYPES[search_type_id]['name'],
                "search_approach": SEARCH_APPROACHES[search_approach]['name'],
                "sort_mode": SORT_MODES[sort_mode]['name'],
                "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_results": len(data)
            },
            "results": data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    except Exception as e:
        return None

def log_top_categories_table(logger, categories):
    """Adiciona tabela de TOP categorias ao log."""
    if not categories:
        logger.info("TOP CATEGORIAS: Nenhuma categoria encontrada")
        return
    
    logger.info("="*80)
    logger.info("TOP CATEGORIAS DA QUERY")
    logger.info("="*80)
    logger.info(f"{'Rank':<6} {'Código':<12} {'Descrição':<60} {'Similaridade':<12}")
    logger.info("-"*80)
    
    for cat in categories:
        similarity_status = "ALTA" if cat['similarity_score'] > 0.8 else "MÉDIA" if cat['similarity_score'] > 0.6 else "BAIXA"
        logger.info(f"{cat['rank']:<6} {cat['codigo']:<12} {cat['descricao'][:60]:<60} {cat['similarity_score']:.4f} ({similarity_status})")
    
    logger.info("="*80)

def log_results_table(logger, results, search_approach):
    """Adiciona tabela de resultados ao log."""
    if not results:
        logger.info("RESULTADOS: Nenhum resultado encontrado")
        return
    
    logger.info("="*100)
    logger.info(f"RESUMO DOS RESULTADOS - {SEARCH_APPROACHES[search_approach]['name'].upper()}")
    logger.info("="*100)
    logger.info(f"{'Rank':<6} {'Órgão':<40} {'Local':<30} {'Similaridade':<12} {'Valor (R$)':<17} {'Data Encerr.':<12}")
    logger.info("-"*100)
    
    for result in results:
        details = result.get("details", {})
        valor = format_currency(details.get("valortotalestimado", 0)) if details else "N/A"
        data_encerramento = format_date(details.get("dataencerramentoproposta", "N/A")) if details else "N/A"
        
        unidade = details.get('unidadeorgao_nomeunidade', 'N/A')
        if len(unidade) > 40:
            unidade = unidade[:37] + "..."
        
        municipio = details.get('unidadeorgao_municipionome', 'N/A')
        uf = details.get('unidadeorgao_ufsigla', '')
        local = f"{municipio}/{uf}" if uf else municipio
        if len(local) > 30:
            local = local[:27] + "..."
        
        logger.info(f"{result['rank']:<6} {unidade:<40} {local:<30} {result['similarity']:.4f}      {valor:<17} {str(data_encerramento):<12}")
    
    logger.info("="*100)

def log_results_details(logger, results, search_approach):
    """Adiciona detalhes dos resultados ao log."""
    if not results:
        return
    
    logger.info("="*100)
    logger.info("DETALHES DOS RESULTADOS")
    logger.info("="*100)
    
    for result in results:
        details = result.get("details", {})
        
        logger.info(f"\n#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})")
        logger.info("-"*80)
        
        logger.info(f"Órgão: {details.get('orgaoentidade_razaosocial', 'N/A')}")
        logger.info(f"Unidade: {details.get('unidadeorgao_nomeunidade', 'N/A')}")
        logger.info(f"Local: {details.get('unidadeorgao_municipionome', 'N/A')}/{details.get('unidadeorgao_ufsigla', 'N/A')}")
        logger.info(f"Valor: {format_currency(details.get('valortotalestimado', 0))}")
        logger.info(f"Datas: Inclusão: {format_date(details.get('datainclusao', 'N/A'))} | Abertura: {format_date(details.get('dataaberturaproposta', 'N/A'))} | Encerramento: {format_date(details.get('dataencerramentoproposta', 'N/A'))}")
        logger.info(f"Modalidade: {details.get('modalidadeid', 'N/A')} - {details.get('modalidadenome', 'N/A')} | Disputa: {details.get('modadisputaid', 'N/A')} - {details.get('modadisputanome', 'N/A')}")
        logger.info(f"Usuário: {details.get('usuarionome', 'N/A')} | Poder: {decode_poder(details.get('orgaoentidade_poderid', 'N/A'))} | Esfera: {decode_esfera(details.get('orgaoentidade_esferaid', 'N/A'))}")
        
        if details.get('linksistemaorigem'):
            logger.info(f"Link Sistema: {details.get('linksistemaorigem', 'N/A')}")
        
        if search_approach == 2 and "top_category_info" in result and result["top_category_info"]:
            cat = result["top_category_info"]
            category_text = f"{cat['codigo']} - {cat['descricao']} (Score: {cat['correspondence_score']:.3f})"
            logger.info(f"Categoria TOP: {category_text}")
        
        descricao = details.get("descricaocompleta", "N/A")
        if len(descricao) > 500:
            descricao = descricao[:500] + "..."
        logger.info(f"Descrição: {descricao}")
        logger.info("-"*80)

# ====================================================================================
# FUNÇÃO PRINCIPAL DE BUSCA
# ====================================================================================

def perform_search(args, logger):
    """Executa a busca conforme parâmetros fornecidos com progresso visual."""
    start_time = time.time()
    
    # Configurar interface de progresso visual
    progress = None
    console = None
    if args.debug and RICH_AVAILABLE:
        console = Console()  # UMA ÚNICA instância de Console
        progress = create_progress_display(console)  # Passar console para progress
        
        # Mostrar cabeçalho visual
        header = Panel.fit(
            f"🚀 [bold cyan]GvG Search PNCP[/bold cyan]\n"
            f"📝 Query: [yellow]\"{args.prompt}\"[/yellow]\n"
            f"🔍 Tipo: [green]{SEARCH_TYPES[args.search]['name']}[/green] | "
            f"📊 Abordagem: [blue]{SEARCH_APPROACHES[args.approach]['name']}[/blue] | "
            f"🎯 Relevância: [magenta]Nível {args.relevance}[/magenta]",
            title="[bold]Sistema de Busca PNCP[/bold]",
            border_style="cyan"
        )
        console.print(header)
    
    # Log básico (sempre ativo)
    logger.info("="*100)
    logger.info("INICIANDO BUSCA GOVGO")
    logger.info("="*100)
    logger.info(f"Query: \"{args.prompt}\"")
    logger.info(f"Tipo: {SEARCH_TYPES[args.search]['name']}")
    logger.info(f"Abordagem: {SEARCH_APPROACHES[args.approach]['name']}")
    logger.info(f"Ordenação: {SORT_MODES[args.order]['name']}")
    logger.info(f"Max Resultados: {args.max_results}")
    logger.info(f"TOP Categorias: {args.top_cat}")
    logger.info(f"Filtrar Encerradas: {args.filter_expired}")
    logger.info(f"Negation Embeddings: {args.negation_emb}")
    logger.info(f"Nível de Relevância: {args.relevance}")
    logger.info("Processamento Inteligente: ATIVADO (v3)")
    
    try:
        # Inicializar variáveis
        results = []
        confidence = 0.0
        categories = []
        original_query = args.prompt
        processed_query = args.prompt
        intelligent_info = None
        
        if progress and console:
            with progress:
                # [1/6] CONFIGURAÇÃO INICIAL
                task1 = progress.add_task("[bold cyan][1/6][/bold cyan] 🔧 Configuração inicial...", total=100)
                
                # Configurar filtro de relevância
                progress.update(task1, advance=30)
                try:
                    current_relevance_status = get_relevance_filter_status()
                    current_level = current_relevance_status.get('relevance_filter_level', 1) if current_relevance_status else 1
                    
                    if args.relevance != current_level:
                        set_relevance_filter_level(args.relevance)
                        level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                        logger.info(f"Filtro de Relevância: {level_names.get(args.relevance, 'DESCONHECIDO')} (nível {args.relevance})")
                        if args.relevance > 1:
                            logger.info("ℹ️ O filtro de relevância usa IA para eliminar contratos não relacionados")
                    else:
                        level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                        logger.info(f"Filtro de Relevância: {level_names.get(current_level, 'DESCONHECIDO')} (sem alterações)")
                except Exception as e:
                    logger.warning(f"❌ Erro ao configurar filtro de relevância: {e}")
                
                # Processamento inteligente
                progress.update(task1, advance=40)
                try:
                    from gvg_pre_processing_v3 import SearchQueryProcessor
                    processor = SearchQueryProcessor()
                    intelligent_info = processor.process_query(original_query)
                    processed_query = intelligent_info.get('search_terms', original_query)
                    logger.info(f"Query Processada Inteligentemente: \"{processed_query}\"")
                    if intelligent_info.get('sql_conditions'):
                        logger.info(f"Condições SQL Detectadas: {len(intelligent_info['sql_conditions'])}")
                except Exception as e:
                    logger.warning(f"Erro no processamento inteligente: {e}")
                
                progress.update(task1, completed=100)
                
                # [2/6] BUSCA DE CATEGORIAS (se necessário)
                if args.approach in [2, 3]:
                    task2 = progress.add_task("[bold green][2/6][/bold green] 📂 Buscando categorias TOP...", total=100)
                    logger.info(f"\nBuscando TOP {args.top_cat} categorias...")
                    
                    progress.update(task2, advance=30)
                    categories = get_top_categories_for_query(processed_query, args.top_cat, args.negation_emb, args.search)
                    progress.update(task2, advance=70)
                    
                    if not categories:
                        logger.error("Nenhuma categoria encontrada para a query")
                        return None, None, None, 0
                    
                    log_top_categories_table(logger, categories)
                    progress.update(task2, completed=100)
                else:
                    task2 = progress.add_task("[bold yellow][2/6][/bold yellow] 📂 Pulando busca de categorias...", total=100)
                    progress.update(task2, completed=100)
                
                # [3/6] EXECUÇÃO DA BUSCA PRINCIPAL
                task3 = progress.add_task("[bold blue][3/6][/bold blue] 🔎 Executando busca principal...", total=100)
                
                if args.approach == 1:  # DIRETA
                    query_for_search = intelligent_info['search_terms'] if intelligent_info else processed_query
                    logger.info(f"\nExecutando busca direta com: \"{query_for_search}\"")
                    progress.update(task3, advance=50)
                    results, confidence = direct_search(query_for_search, args.search, args.max_results, args.filter_expired, args.negation_emb)
                
                elif args.approach == 2:  # CORRESPONDÊNCIA
                    logger.info(f"\nExecutando busca por correspondência com: \"{original_query}\"")
                    progress.update(task3, advance=50)
                    results, confidence = correspondence_search(original_query, categories, args.max_results, args.filter_expired)
                
                elif args.approach == 3:  # FILTRO DE CATEGORIA
                    logger.info(f"\nExecutando busca com filtro categórico com: \"{original_query}\"")
                    progress.update(task3, advance=50)
                    results, confidence = category_filtered_search(original_query, args.search, categories, args.max_results, args.filter_expired, args.negation_emb)
                
                else:
                    logger.error("Abordagem de busca inválida!")
                    return None, None, None, 0
                
                progress.update(task3, completed=100)
                
                if not results:
                    logger.warning("Nenhum resultado encontrado")
                    return [], categories, 0, time.time() - start_time
                
                # [4/6] FILTRO DE RELEVÂNCIA (já aplicado automaticamente nas funções de busca)
                task4 = progress.add_task("[bold magenta][4/6][/bold magenta] 🎯 Filtro de relevância...", total=100)
                progress.update(task4, advance=50)
                logger.info(f"✅ Filtro de relevância aplicado automaticamente (nível {args.relevance})")
                progress.update(task4, completed=100)
                
                # [5/6] PROCESSAMENTO DOS RESULTADOS
                task5 = progress.add_task("[bold orange][5/6][/bold orange] 📊 Processando resultados...", total=100)
                
                # Aplicar ordenação
                progress.update(task5, advance=33)
                if args.order == 1:
                    logger.info("Ordenação: por similaridade (decrescente)")
                elif args.order == 2:
                    def parse_date_safe(val):
                        from datetime import datetime
                        if not val or val in ("", None):
                            return datetime(9999, 12, 31)
                        if isinstance(val, datetime):
                            return val
                        try:
                            return datetime.strptime(str(val)[:10], "%Y-%m-%d")
                        except Exception:
                            try:
                                return datetime.strptime(str(val), "%d/%m/%Y")
                            except Exception:
                                return datetime(9999, 12, 31)
                    results.sort(key=lambda x: parse_date_safe(x.get("details", {}).get("dataencerramentoproposta", None)))
                    logger.info("Ordenação: por data de encerramento (ascendente)")
                elif args.order == 3:
                    results.sort(key=lambda x: float(x.get("details", {}).get("valortotalestimado", 0) or 0), reverse=True)
                    logger.info("Ordenação: por valor estimado (decrescente)")
                
                # Atualizar ranks
                progress.update(task5, advance=33)
                for i, result in enumerate(results, 1):
                    result["rank"] = i
                
                # Adicionar informações do processamento inteligente
                progress.update(task5, advance=34)
                if intelligent_info and results:
                    for result in results:
                        if 'details' not in result:
                            result['details'] = {}
                        result['details']['intelligent_processing'] = {
                            'original_query': intelligent_info['original_query'],
                            'processed_terms': intelligent_info['search_terms'],
                            'applied_conditions': len(intelligent_info.get('sql_conditions', [])),
                            'explanation': intelligent_info.get('explanation', '')
                        }
                
                progress.update(task5, completed=100)
                
                # [6/6] EXPORTAÇÃO E FINALIZAÇÃO
                task6 = progress.add_task("[bold red][6/6][/bold red] 💾 Finalizando e exportando...", total=100)
                
                progress.update(task6, advance=50)
                search_time = time.time() - start_time
                
                # Log das tabelas
                log_results_table(logger, results, args.approach)
                log_results_details(logger, results, args.approach)
                
                logger.info(f"\nTempo total de busca: {search_time:.4f} segundos")
                logger.info(f"Confiança: {confidence:.4f}")
                
                progress.update(task6, completed=100)
            
            # Mostrar resumo final visual APÓS o contexto do progress
            console.print("\n" + "="*50)
            console.print(Panel.fit(
                f"✅ [bold green]Busca Concluída![/bold green]\n"
                f"📊 Resultados: [cyan]{len(results)}[/cyan]\n"
                f"⏱️ Tempo: [yellow]{search_time:.2f}s[/yellow]\n"
                f"🎯 Confiança: [magenta]{confidence:.2f}[/magenta]",
                title="[bold]Resultado Final[/bold]",
                border_style="green"
            ))
        
        else:
            # Modo sem interface visual (quando debug=False ou Rich não disponível)
            # [1/6] Configuração inicial
            try:
                current_relevance_status = get_relevance_filter_status()
                current_level = current_relevance_status.get('relevance_filter_level', 1) if current_relevance_status else 1
                
                if args.relevance != current_level:
                    set_relevance_filter_level(args.relevance)
                    level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                    logger.info(f"Filtro de Relevância: {level_names.get(args.relevance, 'DESCONHECIDO')} (nível {args.relevance})")
                else:
                    level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                    logger.info(f"Filtro de Relevância: {level_names.get(current_level, 'DESCONHECIDO')} (sem alterações)")
            except Exception as e:
                logger.warning(f"❌ Erro ao configurar filtro de relevância: {e}")
            
            # Processamento inteligente
            try:
                from gvg_pre_processing_v3 import SearchQueryProcessor
                processor = SearchQueryProcessor()
                intelligent_info = processor.process_query(original_query)
                processed_query = intelligent_info.get('search_terms', original_query)
                logger.info(f"Query Processada Inteligentemente: \"{processed_query}\"")
                if intelligent_info.get('sql_conditions'):
                    logger.info(f"Condições SQL Detectadas: {len(intelligent_info['sql_conditions'])}")
            except Exception as e:
                logger.warning(f"Erro no processamento inteligente: {e}")
            
            # [2/6] Buscar categorias se necessário
            if args.approach in [2, 3]:
                logger.info(f"\nBuscando TOP {args.top_cat} categorias...")
                categories = get_top_categories_for_query(processed_query, args.top_cat, args.negation_emb, args.search)
                
                if not categories:
                    logger.error("Nenhuma categoria encontrada para a query")
                    return None, None, None, 0
                
                log_top_categories_table(logger, categories)
            
            # [3/6] Executar busca conforme abordagem
            if args.approach == 1:
                query_for_search = intelligent_info['search_terms'] if intelligent_info else processed_query
                logger.info(f"\nExecutando busca direta com: \"{query_for_search}\"")
                results, confidence = direct_search(query_for_search, args.search, args.max_results, args.filter_expired, args.negation_emb)
            elif args.approach == 2:
                logger.info(f"\nExecutando busca por correspondência com: \"{original_query}\"")
                results, confidence = correspondence_search(original_query, categories, args.max_results, args.filter_expired)
            elif args.approach == 3:
                logger.info(f"\nExecutando busca com filtro categórico com: \"{original_query}\"")
                results, confidence = category_filtered_search(original_query, args.search, categories, args.max_results, args.filter_expired, args.negation_emb)
            else:
                logger.error("Abordagem de busca inválida!")
                return None, None, None, 0
            
            if not results:
                logger.warning("Nenhum resultado encontrado")
                return [], categories, 0, time.time() - start_time
            
            # [4/6] Filtro de relevância (já aplicado)
            logger.info(f"✅ Filtro de relevância aplicado automaticamente (nível {args.relevance})")
            
            # [5/6] Aplicar ordenação e processar
            if args.order == 1:
                logger.info("Ordenação: por similaridade (decrescente)")
            elif args.order == 2:
                def parse_date_safe(val):
                    from datetime import datetime
                    if not val or val in ("", None):
                        return datetime(9999, 12, 31)
                    if isinstance(val, datetime):
                        return val
                    try:
                        return datetime.strptime(str(val)[:10], "%Y-%m-%d")
                    except Exception:
                        try:
                            return datetime.strptime(str(val), "%d/%m/%Y")
                        except Exception:
                            return datetime(9999, 12, 31)
                results.sort(key=lambda x: parse_date_safe(x.get("details", {}).get("dataencerramentoproposta", None)))
                logger.info("Ordenação: por data de encerramento (ascendente)")
            elif args.order == 3:
                results.sort(key=lambda x: float(x.get("details", {}).get("valortotalestimado", 0) or 0), reverse=True)
                logger.info("Ordenação: por valor estimado (decrescente)")
            
            # Atualizar ranks
            for i, result in enumerate(results, 1):
                result["rank"] = i
            
            # Adicionar informações do processamento inteligente
            if intelligent_info and results:
                for result in results:
                    if 'details' not in result:
                        result['details'] = {}
                    result['details']['intelligent_processing'] = {
                        'original_query': intelligent_info['original_query'],
                        'processed_terms': intelligent_info['search_terms'],
                        'applied_conditions': len(intelligent_info.get('sql_conditions', [])),
                        'explanation': intelligent_info.get('explanation', '')
                    }
            
            # [6/6] Finalização
            search_time = time.time() - start_time
            log_results_table(logger, results, args.approach)
            log_results_details(logger, results, args.approach)
            logger.info(f"\nTempo total de busca: {search_time:.4f} segundos")
            logger.info(f"Confiança: {confidence:.4f}")
        
        return results, categories, confidence, time.time() - start_time
        
    except Exception as e:
        logger.error(f"Erro durante a busca: {e}")
        if console:
            console.print(f"[bold red]❌ ERRO: {e}[/bold red]")
        return None, None, None, 0

# ====================================================================================
# FUNÇÃO PRINCIPAL
# ====================================================================================

def main():
    """Função principal do sistema de linha de comando."""
    parser = argparse.ArgumentParser(
        description='Sistema de Busca PNCP via Linha de Comando',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Adicionar suporte para --h e --help
    if '--h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    # Argumentos obrigatórios
    parser.add_argument('--prompt', required=True, help='Query de busca (obrigatório)')
    
    # Argumentos opcionais com defaults do v9
    parser.add_argument('--search', '--S', '--s', type=int, choices=[1, 2, 3], default=1,
                       help='Tipo de busca: 1=Semântica, 2=Palavras-chave, 3=Híbrida (padrão: 1)')
    parser.add_argument('--approach', '--A', '--a', type=int, choices=[1, 2, 3], default=3,
                       help='Abordagem: 1=Direta, 2=Correspondência, 3=Filtro (padrão: 3)')
    parser.add_argument('--relevance', '--R', '--r', type=int, choices=[1, 2, 3], default=1,
                       help='Nível do filtro de relevância: 1=sem filtro, 2=flexível, 3=restritivo (padrão: 1)')
    parser.add_argument('--order', '--O', '--o', type=int, choices=[1, 2, 3], default=3,
                       help='Ordenação: 1=Similaridade, 2=Data, 3=Valor (padrão: 3)')
    parser.add_argument('--intelligent', '--I', '--i', action='store_true', default=False,
                       help='Toggle do processamento inteligente (padrão: False)')
    parser.add_argument('--max_results', type=int, default=30,
                       help='Número máximo de resultados (padrão: 30)')
    parser.add_argument('--top_cat', type=int, default=10,
                       help='Número de TOP categorias (padrão: 10)')
    parser.add_argument('--doc_processor', choices=['v2', 'v3'], default='v3',
                       help='Processador documentos: v2=MarkItDown, v3=Docling (padrão: v3)')
    parser.add_argument('--filter_expired', action='store_true', default=True,
                       help='Filtrar contratações encerradas (padrão: True)')
    parser.add_argument('--negation_emb', action='store_true', default=True,
                       help='Usar negation embeddings (padrão: True)')
    parser.add_argument('--debug', action='store_true', default=False,
                       help='Debug inteligente (padrão: False)')
    parser.add_argument('--output_dir', default=os.environ.get('RESULTS_PATH', RESULTS_PATH),
                       help=f'Diretório de saída (padrão: {os.environ.get('RESULTS_PATH', RESULTS_PATH)})')
    # Parâmetros de modo inteligente removidos: sempre ativado
    
    args = parser.parse_args()
    
    # Verificar se prompt foi fornecido
    if not args.prompt or args.prompt.strip() == '':
        print("ERRO: --prompt é obrigatório")
        parser.print_help()
        sys.exit(1)
    
    # Configurar logging
    try:
        logger, log_filename = setup_logging(args.output_dir, args.prompt)
    except Exception as e:
        print(f"ERRO: Não foi possível configurar logging: {e}")
        sys.exit(1)
    
    # Processar toggle do processamento inteligente se solicitado
    if args.intelligent:
        try:
            current_status = get_intelligent_status()
            current_enabled = current_status.get('intelligent_processing_enabled', False) if current_status else False
            
            # Fazer toggle
            new_status = toggle_intelligent_processing()
            new_enabled = new_status.get('intelligent_processing_enabled', False) if new_status else False
            
            if new_enabled != current_enabled:
                status_text = "ATIVADO" if new_enabled else "DESATIVADO"
                print(f"✅ Processamento Inteligente {status_text}")
                logger.info(f"Processamento Inteligente {status_text} via parâmetro --intelligent")
            else:
                print(f"⚠️ Status do processamento inteligente mantido: {'ATIVADO' if new_enabled else 'DESATIVADO'}")
                logger.info(f"Status do processamento inteligente mantido: {'ATIVADO' if new_enabled else 'DESATIVADO'}")
        except Exception as e:
            print(f"❌ Erro ao processar --intelligent: {e}")
            logger.error(f"Erro ao processar --intelligent: {e}")
    
    # Executar busca
    try:
        console = None  # Inicializar console aqui
        
        if args.debug and RICH_AVAILABLE:
            console = Console()  # UMA ÚNICA instância reutilizada
            console.print("\n🚀 [bold cyan]Iniciando Sistema de Busca PNCP[/bold cyan]")
            console.print("📊 [yellow]Modo DEBUG ativado - Interface visual habilitada[/yellow]\n")
        elif args.debug and not RICH_AVAILABLE:
            print("\n🚀 Iniciando Sistema de Busca PNCP")
            print("⚠️ Rich não disponível - usando modo texto simples\n")
        
        results, categories, confidence, search_time = perform_search(args, logger)
        
        if results is None:
            error_msg = "ERRO: Falha na execução da busca. Verifique o arquivo de log."
            logger.error("Falha na execução da busca")
            if console:
                console.print(f"[bold red]{error_msg}[/bold red]")
            else:
                print(error_msg)
            sys.exit(1)
        
        if not results:
            warning_msg = "AVISO: Busca concluída sem resultados."
            logger.warning("Busca concluída sem resultados")
            if console:
                console.print(f"[bold yellow]{warning_msg}[/bold yellow]")
            else:
                print(warning_msg)
            return
        
        # Exportar JSON
        json_filename = export_results_to_json(
            results, args.prompt, args.search, args.approach, args.relevance, args.order, args.output_dir
        )
        
        if json_filename:
            logger.info(f"\nRESULTADOS EXPORTADOS:")
            logger.info(f"JSON: {json_filename}")
            logger.info(f"LOG: {log_filename}")
            
            success_msg = f"SUCESSO: Busca concluída!\nResultados: {len(results)}\nJSON: {json_filename}\nLOG: {log_filename}"
            
            if console:
                console.print("\n" + "="*50)
                console.print(Panel.fit(
                    f"✅ [bold green]Busca Finalizada![/bold green]\n"
                    f"📁 [cyan]JSON:[/cyan] [white]{os.path.basename(json_filename)}[/white]\n"
                    f"📋 [cyan]LOG:[/cyan] [white]{os.path.basename(log_filename)}[/white]\n"
                    f"📊 [cyan]Resultados:[/cyan] [yellow]{len(results)}[/yellow]\n"
                    f"⏱️ [cyan]Tempo:[/cyan] [magenta]{search_time:.2f}s[/magenta]",
                    title="[bold]Exportação Concluída[/bold]",
                    border_style="green"
                ))
            else:
                print(success_msg)
        else:
            error_msg = "ERRO: Falha ao exportar resultados."
            logger.error("Falha ao exportar resultados para JSON")
            if console:
                console.print(f"[bold red]{error_msg}[/bold red]")
            else:
                print(error_msg)
            sys.exit(1)
    
    except Exception as e:
        error_msg = f"ERRO FATAL: {e}"
        logger.error(f"Erro fatal: {e}")
        console = Console() if args.debug and RICH_AVAILABLE else None
        if console:
            console.print(f"[bold red]{error_msg}[/bold red]")
        else:
            print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
