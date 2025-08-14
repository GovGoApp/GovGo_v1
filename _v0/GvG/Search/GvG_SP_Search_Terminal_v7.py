"""
GvG_SP_Search_Terminal.py
Sistema Avançado de Busca PNCP

Características principais:
• ESTRUTURA DE MENU SEPARADA:
  - Tipo de Busca: Semântica, Palavras-chave, Híbrida
  - Abordagem: Direta, Correspondência, Filtro
  - Ordenação: Similaridade, Data, Valor
  - Filtro de contratações encerradas
  - Configurações do sistema

• TRÊS ABORDAGENS DISTINTAS:
  1. DIRETA: Busca tradicional (sem categorias) - semântica/palavras-chave/híbrida diretamente nos textos
  2. CORRESPONDÊNCIA: Busca por correspondência categórica - multiplicação de similarities
  3. FILTRO: Busca com filtro categórico - usa categorias para restringir universo + busca textual

• CAMPOS ADICIONAIS INCLUÍDOS (v7+):
  - dataInclusao: Data de inclusão no sistema
  - linkSistemaOrigem: Link para o sistema de origem
  - modalidadeId/modalidadeNome: Código e nome da modalidade
  - modaDisputaId/modaDisputaNome: Código e nome do modo de disputa
  - usuarioNome: Nome do usuário responsável
  - orgaoEntidade_poderId: Código do poder (Executivo, Legislativo, etc.)
  - orgaoEntidade_esferaId: Código da esfera (Federal, Estadual, Municipal)

IMPORTANTE: Para funcionar corretamente, o gvg_search_utils.py deve retornar estes campos
nas funções semantic_search(), keyword_search() e hybrid_search().

Funcionalidades herdadas:
• Busca semântica, por palavras-chave e híbrida em contratos públicos
• Integração completa com banco Supabase para dados do PNCP
• Interface terminal interativa com Rich para visualização aprimorada
• Exportação de resultados em Excel e PDF formatado
• Análise de documentos com sumarização automática via IA
• Geração inteligente de palavras-chave usando OpenAI GPT
• Sistema de filtros e ordenação personalizável
• Links diretos para documentos oficiais do PNCP
• Menu contextual que adapta opções conforme disponibilidade de resultados
"""
import os
import sys
import time
import locale
import re
import pandas as pd
import numpy as np
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm

# Imports para geração de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configurações padrão
DEFAULT_PREPROC_PARAMS = {
    "remove_special_chars": True,
    "keep_separators": True,
    "remove_accents": False,
    "case": "lower",
    "remove_stopwords": True,
    "lemmatize": True
}

# Importar funções do módulo de pré-processamento
try:
    from gvg_pre_processing import (
        gvg_pre_processing,
        EMBEDDING_MODELS,
        EMBEDDING_MODELS_REVERSE
    )
except ImportError:
    print("ERRO: Não foi possível importar o módulo de pré-processamento.")
    sys.exit(1)

# Importar funções de busca (agora de gvg_search_utils)
try:
    from gvg_search_utils import (
        create_connection,
        semantic_search,
        keyword_search,
        hybrid_search,
        calculate_confidence,
        format_currency,
        test_connection,
        get_embedding,
        parse_numero_controle_pncp,
        fetch_documentos,
        generate_keywords,
        summarize_document,
        decode_poder,
        decode_esfera,
        format_date
    )
    
except ImportError:
    print("ERRO: Não foi possível importar as funções de busca de gvg_search_utils.")
    sys.exit(1)

# Importações adicionais para categorização
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure Rich console
console = Console()

# Configurar locale para formatação de valores em reais
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        console.print("[yellow]Aviso: Não foi possível configurar o locale para formatação monetária.[/yellow]")

# Configurações de busca
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
RESULTS_PATH = BASE_PATH + "GvG\\SS\\RESULTADOS\\"

# Constantes para configuração de busca
MIN_RESULTS = 5      # Número mínimo de resultados que serão retornados
MAX_RESULTS = 30    # Número máximo de resultados que serão retornados
SEMANTIC_WEIGHT = 0.75  # Peso padrão para busca semântica em busca híbrida

# ESTRUTURA DE CONFIGURAÇÕES
# Tipos de busca (algoritmos)
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

# Abordagens de busca (metodologias)
SEARCH_APPROACHES = {
    1: {"name": "Direta", "description": "Busca tradicional diretamente nos textos (sem categorias)"},
    2: {"name": "Correspondência", "description": "Busca por correspondência categórica (multiplicação de similarities)"},
    3: {"name": "Filtro", "description": "Usa categorias para restringir universo + busca textual"}
}

# Modos de ordenação
SORT_MODES = {
    1: {"name": "Similaridade", "description": "Ordenar por relevância (decrescente)"},
    2: {"name": "Data de Encerramento", "description": "Ordenar por data (ascendente)"},
    3: {"name": "Valor Estimado", "description": "Ordenar por valor (decrescente)"}
}

# Variáveis para armazenar estado global
last_results = None
last_query = None
last_query_categories = None  # Armazenar categorias da query

# VARIÁVEIS DE ESTADO
current_search_type = 1  # Tipo de busca padrão: Semântica
current_search_approach = 1  # Abordagem padrão: Direta
current_sort_mode = 1  # Modo de ordenação padrão: Similaridade
filter_expired = True  # Filtro para ocultar contratações encerradas

# Configurações para categorização
num_top_categories = 5  # Número padrão de TOP categorias para buscar (N=5)

# ====================================================================================
# FUNÇÕES DE CATEGORIZAÇÃO E BUSCA
# ====================================================================================

def create_engine_connection():
    """Cria engine SQLAlchemy usando as mesmas credenciais do gvg_search_utils"""
    try:
        # Carregar variáveis de ambiente usando caminho absoluto
        env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
        
        if not os.path.exists(env_path):
            console.print(f"[red]Arquivo de configuração não encontrado: {env_path}[/red]")
            return None
            
        load_dotenv(env_path)
        
        # Configurações do banco com valores padrão
        host = os.getenv('host', 'localhost')
        database = os.getenv('dbname', 'postgres')
        user = os.getenv('user', 'postgres')
        password = os.getenv('password', '')
        port = os.getenv('port', '5432')
        
        # Debug: mostrar valores carregados (sem senha)
        console.print(f"[dim]Debug - Host: {host}, Database: {database}, User: {user}, Port: {port}[/dim]")
        
        # Verificar se port é válido
        if port is None or port == 'None' or port == '':
            port = '5432'
        
        # Verificar se as credenciais essenciais estão disponíveis
        if not all([host, database, user]):
            console.print("[red]Erro: Credenciais do banco de dados não configuradas corretamente.[/red]")
            console.print("[yellow]Verifique o arquivo supabase_v0.env[/yellow]")
            return None
        
        # Criar connection string
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Criar engine
        engine = create_engine(connection_string)
        
        # Testar conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        console.print("[green]✓ Engine SQLAlchemy criada com sucesso![/green]")
        return engine
        
    except Exception as e:
        console.print(f"[red]Erro ao criar engine SQLAlchemy: {e}[/red]")
        console.print(f"[yellow]Verifique as configurações do banco de dados em supabase_v0.env[/yellow]")
        return None

def get_top_categories_for_query(query_text, top_n=5):
    """
    Embedda a query e busca as TOP N categorias mais similares.
    
    Args:
        query_text: Texto da consulta
        top_n: Número de TOP categorias para retornar (padrão 5)
        
    Returns:
        Lista de dicionários com as categorias e suas similaridades
    """
    try:
        # Gerar embedding da consulta
        query_embedding = get_embedding(query_text)
        if query_embedding is None:
            console.print("[yellow]Não foi possível gerar embedding da consulta.[/yellow]")
            return []
        
        # Converter para lista para usar na query
        if isinstance(query_embedding, np.ndarray):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = query_embedding
        
        # Criar engine
        engine = create_engine_connection()
        if not engine:
            return []
        
        # Query SQL usando operador de similaridade coseno do pgvector
        query = """
        SELECT 
            id,
            codcat,
            nomcat,
            codnv0,
            nomnv0,
            codnv1,
            nomnv1,
            codnv2,
            nomnv2,
            codnv3,
            nomnv3,
            1 - (cat_embeddings <=> %(embedding)s::vector) AS similarity
        FROM 
            categorias
        WHERE 
            cat_embeddings IS NOT NULL
        ORDER BY 
            similarity DESC
        LIMIT %(limit)s
        """
        
        # Executa a query
        df = pd.read_sql_query(
            query, 
            engine, 
            params={
                'embedding': query_embedding_list,
                'limit': top_n
            }
        )
        
        # Formatar os resultados
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
        console.print(f"[red]Erro ao buscar TOP categorias para query: {e}[/red]")
        return []

def display_top_categories_table(categories):
    """
    Exibe uma tabela rica com as TOP N categorias da query.
    
    Args:
        categories: Lista de categorias com similaridades
    """
    if not categories:
        console.print("[yellow]Nenhuma categoria encontrada para a consulta.[/yellow]")
        return
    
    # Criar tabela Rica
    table = Table(title="🎯 TOP Categorias da Query", title_style="bold magenta")
    
    table.add_column("Rank", style="bold cyan", width=6)
    table.add_column("Código", style="bold yellow", width=12)
    table.add_column("Descrição", style="bold green", width=60)
    table.add_column("Similaridade", style="bold blue", width=12)
    
    for cat in categories:
        similarity_color = "bright_green" if cat['similarity_score'] > 0.8 else \
                          "yellow" if cat['similarity_score'] > 0.6 else "white"
        
        # Mostrar código e descrição completos
        codigo_completo = cat['codigo']
        descricao_completa = cat['descricao']
        
        table.add_row(
            str(cat['rank']),
            codigo_completo,
            descricao_completa,
            f"[{similarity_color}]{cat['similarity_score']:.4f}[/{similarity_color}]"
        )
    
    console.print()
    console.print(table)
    console.print()

# ====================================================================================
# FUNÇÕES DAS TRÊS ABORDAGENS DE BUSCA
# ====================================================================================

def direct_search(query_text, search_type, limit=MAX_RESULTS, filter_expired=True):
    """
    ABORDAGEM 1 - BUSCA DIRETA
    Busca tradicional (sem categorias) usando semântica/palavras-chave/híbrida diretamente nos textos.
    
    Args:
        query_text: Texto da consulta
        search_type: Tipo de busca (1=Semântica, 2=Palavras-chave, 3=Híbrida)
        limit: Limite de resultados
        filter_expired: Filtrar contratações encerradas
        
    Returns:
        Tuple (resultados_formatados, confiança)
    """
    try:
        console.print(f"[blue]Executando busca direta ({SEARCH_TYPES[search_type]['name']})...[/blue]")
        
        if search_type == 1:  # Semântica
            results, confidence = semantic_search(query_text, limit, MIN_RESULTS, filter_expired)
        elif search_type == 2:  # Palavras-chave
            results, confidence = keyword_search(query_text, limit, MIN_RESULTS, filter_expired)
        elif search_type == 3:  # Híbrida
            results, confidence = hybrid_search(query_text, limit, MIN_RESULTS, SEMANTIC_WEIGHT, filter_expired)
        else:
            console.print("[red]Tipo de busca inválido![/red]")
            return [], 0.0
        
        # Adicionar flag de abordagem nos resultados
        for result in results:
            result["search_approach"] = "direct"
            result["search_type"] = search_type
        
        return results, confidence
        
    except Exception as e:
        console.print(f"[red]Erro na busca direta: {e}[/red]")
        return [], 0.0

def correspondence_search(query_text, top_categories, limit=MAX_RESULTS, filter_expired=True):
    """
    ABORDAGEM 2 - BUSCA POR CORRESPONDÊNCIA CATEGÓRICA
    Busca apenas contratações que tenham pelo menos uma das TOP N categorias.
    Ordena por multiplicação de similarities (query→categoria × contratação→categoria).
    Tipo de busca NÃO importa nesta abordagem.
    
    Args:
        query_text: Texto da consulta
        top_categories: Lista das TOP N categorias da query
        limit: Limite de resultados
        filter_expired: Filtrar contratações encerradas
        
    Returns:
        Tuple (resultados_formatados, confiança)
    """
    try:
        console.print(f"[blue]Executando busca por correspondência categórica...[/blue]")
        
        # Extrair códigos das categorias para busca
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # Conectar ao banco
        connection = create_connection()
        cursor = connection.cursor()
        
        # Query SQL: Busca contratações que tenham pelo menos uma das TOP N categorias
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
            ce.top_categories,
            ce.top_similarities
        FROM 
            contratacoes c
        JOIN 
            contratacoes_embeddings ce ON c.numeroControlePNCP = ce.numeroControlePNCP
        WHERE 
            ce.top_categories IS NOT NULL
            AND ce.top_categories && %s
        """
        
        # Adicionar filtro de data se ativado
        if filter_expired:
            search_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"
        
        # Executar query
        cursor.execute(search_query, (category_codes,))
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        # Processar resultados e calcular similarity score de correspondência
        formatted_results = []
        for row in results:
            result_dict = dict(zip(column_names, row))
            
            # Calcular similarity score de correspondência (multiplicação de similarities)
            correspondence_similarity = calculate_correspondence_similarity_score(
                top_categories, 
                result_dict['top_categories'], 
                result_dict['top_similarities']
            )
            
            # Encontrar a categoria mais importante para este resultado
            top_category_info = find_top_category_for_result(
                top_categories,
                result_dict['top_categories'],
                result_dict['top_similarities']
            )
            
            formatted_results.append({
                "rank": 0,  # Será definido após ordenação
                "id": result_dict["numerocontrolepncp"],
                "similarity": correspondence_similarity,
                "correspondence_similarity": correspondence_similarity,
                "top_category_info": top_category_info,
                "search_approach": "correspondence",
                "details": result_dict
            })
        
        # Ordenar por similarity de correspondência (decrescente)
        formatted_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Definir ranks após ordenação
        for i, result in enumerate(formatted_results):
            result["rank"] = i + 1
        
        # Limitar resultados
        formatted_results = formatted_results[:limit]
        
        # Calcular confiança
        similarities = [r["similarity"] for r in formatted_results]
        confidence = calculate_confidence(similarities) if similarities else 0.0
        
        cursor.close()
        connection.close()
        
        return formatted_results, confidence
        
    except Exception as e:
        console.print(f"[red]Erro na busca por correspondência categórica: {e}[/red]")
        return [], 0.0

def category_filtered_search(query_text, search_type, top_categories, limit=MAX_RESULTS, filter_expired=True):
    """
    ABORDAGEM 3 - BUSCA COM FILTRO CATEGÓRICO
    Fase 1: Encontra TOP N categorias da query para definir o universo restrito
    Fase 2: Aplica busca semântica/palavras-chave/híbrida tradicional
    Fase 3: Filtra os resultados para manter apenas aqueles que tenham PELO MENOS uma das TOP N categorias
    
    Args:
        query_text: Texto da consulta
        search_type: Tipo de busca (1=Semântica, 2=Palavras-chave, 3=Híbrida)
        top_categories: Lista das TOP N categorias da query
        limit: Limite de resultados
        filter_expired: Filtrar contratações encerradas
        
    Returns:
        Tuple (resultados_formatados, confiança)
    """
    try:
        console.print(f"[blue]Executando busca com filtro categórico ({SEARCH_TYPES[search_type]['name']})...[/blue]")
        
        # Extrair códigos das categorias para filtro
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # FASE 1: Executar busca tradicional (sem restrição por categoria)
        console.print(f"[blue]Executando busca {SEARCH_TYPES[search_type]['name']} tradicional...[/blue]")
        
        if search_type == 1:  # Semântica
            all_results, confidence = semantic_search(query_text, limit * 3, MIN_RESULTS, filter_expired)
        elif search_type == 2:  # Palavras-chave
            all_results, confidence = keyword_search(query_text, limit * 3, MIN_RESULTS, filter_expired)
        elif search_type == 3:  # Híbrida
            all_results, confidence = hybrid_search(query_text, limit * 3, MIN_RESULTS, SEMANTIC_WEIGHT, filter_expired)
        else:
            console.print("[red]Tipo de busca inválido![/red]")
            return [], 0.0
        
        if not all_results:
            console.print("[yellow]Nenhum resultado encontrado na busca tradicional.[/yellow]")
            return [], 0.0
        
        # FASE 2: Filtrar resultados por categorias
        console.print(f"[blue]Filtrando resultados por categorias relevantes...[/blue]")
        
        # Conectar ao banco para verificar categorias
        connection = create_connection()
        cursor = connection.cursor()
        
        # Buscar categorias de cada resultado
        filtered_results = []
        result_ids = [result['id'] for result in all_results]
        
        # Query para buscar categorias de múltiplos resultados
        placeholders = ','.join(['%s'] * len(result_ids))
        category_query = f"""
        SELECT 
            numeroControlePNCP,
            top_categories
        FROM 
            contratacoes_embeddings
        WHERE 
            numeroControlePNCP IN ({placeholders})
            AND top_categories IS NOT NULL
        """
        
        cursor.execute(category_query, result_ids)
        category_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.close()
        connection.close()
        
        # Filtrar resultados que tenham pelo menos uma categoria relevante
        for result in all_results:
            result_id = result['id']
            result_categories = category_data.get(result_id, [])
            
            # Verificar se o resultado tem pelo menos uma categoria relevante
            if result_categories and any(cat_code in result_categories for cat_code in category_codes):
                # Adicionar informações de filtro
                result["search_approach"] = "category_filtered"
                result["search_type"] = search_type
                result["matched_categories"] = [cat for cat in category_codes if cat in result_categories]
                filtered_results.append(result)
            
            # Parar quando atingir o limite
            if len(filtered_results) >= limit:
                break
        
        # Reordenar os ranks dos resultados filtrados
        for i, result in enumerate(filtered_results):
            result["rank"] = i + 1
        
        universe_size = len([r for r in all_results if category_data.get(r['id'])])
        console.print(f"[green]Universo com categorias: {universe_size} contratações[/green]")
        console.print(f"[green]Resultados filtrados: {len(filtered_results)} contratações[/green]")
        
        # Adicionar informação do universo filtrado
        for result in filtered_results:
            result["filtered_universe_size"] = universe_size
        
        return filtered_results, confidence
        
    except Exception as e:
        console.print(f"[red]Erro na busca com filtro categórico: {e}[/red]")
        return [], 0.0

def calculate_correspondence_similarity_score(query_categories, result_categories, result_similarities):
    """
    Calcula o score de similaridade pela multiplicação:
    similarity(query→categoria) × similarity(contratação→categoria)
    
    Args:
        query_categories: TOP N categorias da query com suas similarities
        result_categories: Categorias do resultado (array de códigos)
        result_similarities: Similarities do resultado (array de scores)
        
    Returns:
        Score final de correspondência (float)
    """
    try:
        if not query_categories or not result_categories or not result_similarities:
            return 0.0
        
        max_score = 0.0
        
        # Para cada categoria da query
        for query_cat in query_categories:
            query_code = query_cat['codigo']
            query_similarity = query_cat['similarity_score']
            
            # Verificar se valores são válidos
            if query_similarity is None or query_similarity == 0:
                continue
            
            # Verificar se esta categoria está presente no resultado
            if query_code in result_categories:
                # Encontrar o índice da categoria no resultado
                try:
                    idx = result_categories.index(query_code)
                    result_similarity = result_similarities[idx]
                    
                    # Verificar se result_similarity é válido
                    if result_similarity is None or result_similarity == 0:
                        continue
                    
                    # Calcular score de correspondência: multiplicação das similarities
                    correspondence_score = float(query_similarity) * float(result_similarity)
                    
                    # Manter o maior score encontrado
                    max_score = max(max_score, correspondence_score)
                    
                except (IndexError, ValueError, TypeError):
                    continue
        
        return max_score
        
    except Exception as e:
        return 0.0

def find_top_category_for_result(query_categories, result_categories, result_similarities):
    """
    Encontra a categoria mais importante para um resultado específico.
    Retorna a categoria com maior score de correspondência (multiplicação).
    
    Args:
        query_categories: TOP N categorias da query
        result_categories: Categorias do resultado
        result_similarities: Similarities do resultado
        
    Returns:
        Dicionário com informações da categoria mais importante
    """
    try:
        if not query_categories or not result_categories or not result_similarities:
            return None
        
        best_category = None
        best_score = 0.0
        
        # Para cada categoria da query
        for query_cat in query_categories:
            query_code = query_cat['codigo']
            query_similarity = query_cat['similarity_score']
            
            # Verificar se valores são válidos
            if query_similarity is None or query_similarity == 0:
                continue
            
            # Verificar se esta categoria está presente no resultado
            if query_code in result_categories:
                try:
                    idx = result_categories.index(query_code)
                    result_similarity = result_similarities[idx]
                    
                    # Verificar se result_similarity é válido
                    if result_similarity is None or result_similarity == 0:
                        continue
                    
                    # Calcular score de correspondência
                    correspondence_score = float(query_similarity) * float(result_similarity)
                    
                    # Verificar se é o melhor score
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
        
    except Exception as e:
        return None

# ====================================================================================
# FIM DAS FUNÇÕES DE BUSCA
# ====================================================================================

def highlight_key_terms(text, query_terms, max_length=500):
    """Destaca termos da consulta no texto e limita o comprimento."""
    if not text:
        return "N/A"
        
    # Limitar comprimento se for muito longo
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Destacar termos da consulta (case-insensitive)
    for term in query_terms:
        if len(term) > 2:  # Apenas termos com mais de 2 caracteres
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text = pattern.sub(f"[bold yellow]{term}[/bold yellow]", text)
    
    return text

def display_results(results, search_time=0, query="", search_type=1, search_approach=1):
    """Exibe os resultados da busca de forma organizada"""
    if not results:
        console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
        return
    
    console.print(f"\n[bold green]Resultados encontrados: {len(results)}[/bold green]")
    console.print(f"[blue]Tempo de busca: {search_time:.3f}s[/blue]")
    console.print(f"[blue]Tipo de busca: {SEARCH_TYPES[search_type]['name']}[/blue]")
    console.print(f"[blue]Abordagem: {SEARCH_APPROACHES[search_approach]['name']}[/blue]")
    console.print(f"[blue]Ordenação: {SORT_MODES[current_sort_mode]['name']}[/blue]")
    
    # Mostrar informações específicas conforme abordagem
    if search_approach == 2 and last_query_categories:  # Correspondência
        console.print(f"[magenta]Baseado em {len(last_query_categories)} TOP categorias[/magenta]")
    elif search_approach == 3 and last_query_categories:  # Filtro de categoria
        console.print(f"[magenta]Universo filtrado por {len(last_query_categories)} TOP categorias[/magenta]")
        # Mostrar tamanho do universo se disponível
        if results and "filtered_universe_size" in results[0]:
            console.print(f"[yellow]Universo restrito: {results[0]['filtered_universe_size']} contratações[/yellow]")
    
    console.print()
    
    # Tabela resumida adaptada para todas as abordagens
    table = Table(title=f"Resumo dos Resultados - {SEARCH_APPROACHES[search_approach]['name']}", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6, justify="center")
    table.add_column("Órgão", style="cyan", width=40)
    table.add_column("Local", style="cyan", width=30)
    table.add_column("Similaridade", justify="right", width=12)
    table.add_column("Valor (R$)", justify="right", width=17)
    table.add_column("Data Encerramento", width=12)
    
    # Adicionar coluna específica para busca por correspondência
    if search_approach == 2:  # Correspondência
        table.add_column("Score Corresp.", justify="right", width=10, style="bold yellow")
    
    for result in results:
        details = result.get("details", {})
        
        # Formatar valor usando função de gvg_search_utils
        valor = format_currency(details.get("valortotalestimado", 0)) if details else "N/A"
        
        # Formatar data
        data_encerramento = format_date(details.get("dataencerramentoproposta", "N/A")) if details else "N/A"
        
        # Preparar informações de órgão e local
        unidade = details.get('unidadeorgao_nomeunidade', 'N/A')
        
        municipio = details.get('unidadeorgao_municipionome', 'N/A')
        uf = details.get('unidadeorgao_ufsigla', '')
        local = f"{municipio}/{uf}" if uf else municipio
        
        # Preparar row data
        row_data = [
            f"{result['rank']}", 
            unidade,  # Unidade/Órgão
            local,  # Município/UF
            f"{result['similarity']:.4f}",
            valor,
            str(data_encerramento)
        ]
        
        # Adicionar Score de Correspondência se for busca por correspondência
        if search_approach == 2 and "correspondence_similarity" in result:
            row_data.append(f"{result['correspondence_similarity']:.4f}")
        
        table.add_row(*row_data)

    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    
    # Detalhes de cada resultado
    for result in results:
        details = result.get("details", {})
        
        # Destacar termos da consulta na descrição
        descricao = highlight_key_terms(
            details.get("descricaocompleta", "N/A"),
            query.split()
        )
        
        # Criar painel com informações detalhadas
        panel_title = f"#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})"
        
        # Adicionar informações específicas conforme abordagem
        if search_approach == 2 and "correspondence_similarity" in result:  # Correspondência
            panel_title += f" [Score Corresp.: {result['correspondence_similarity']:.4f}]"
        elif search_approach == 3:  # Filtro de categoria
            panel_title += f" [Filtrado por categoria]"
        
        # Adicionar scores específicos para busca híbrida
        if "semantic_score" in result and "keyword_score" in result:
            panel_title += f" [Semântico: {result['semantic_score']:.4f}, Palavra-chave: {result['keyword_score']:.4f}]"
        
        content = [
            f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoentidade_razaosocial', 'N/A')}",
            f"[bold cyan]Unidade:[/bold cyan] {details.get('unidadeorgao_nomeunidade', 'N/A')}",
            f"[bold cyan]Local:[/bold cyan] {details.get('unidadeorgao_municipionome', 'N/A')}/{details.get('unidadeorgao_ufsigla', 'N/A')}",
            f"[bold cyan]Valor:[/bold cyan] {format_currency(details.get('valortotalestimado', 0))}",
            f"[bold cyan]Datas:[/bold cyan] Inclusão: {format_date(details.get('datainclusao', 'N/A'))} | Abertura: {format_date(details.get('dataaberturaproposta', 'N/A'))} | Encerramento: {format_date(details.get('dataencerramentoproposta', 'N/A'))}",
            f"[bold cyan]Modalidade:[/bold cyan] {details.get('modalidadeid', 'N/A')} - {details.get('modalidadenome', 'N/A')} | [bold cyan]Disputa:[/bold cyan] {details.get('modadisputaid', 'N/A')} - {details.get('modadisputanome', 'N/A')}",
            f"[bold cyan]Usuário:[/bold cyan] {details.get('usuarionome', 'N/A')} | [bold cyan]Poder:[/bold cyan] {decode_poder(details.get('orgaoentidade_poderid', 'N/A'))} | [bold cyan]Esfera:[/bold cyan] {decode_esfera(details.get('orgaoentidade_esferaid', 'N/A'))}",
        ]
        
        # Adicionar link do sistema se disponível
        if details.get('linksistemaorigem'):
            content.append(f"[bold cyan]Link Sistema:[/bold cyan] {details.get('linksistemaorigem', 'N/A')}")
        
        # Adicionar categoria mais importante se disponível (correspondência)
        if search_approach == 2 and "top_category_info" in result and result["top_category_info"]:
            cat = result["top_category_info"]
            category_text = f"{cat['codigo']} - {cat['descricao']} (Score: {cat['correspondence_score']:.3f})"
            content.append(f"[bold yellow]🎯 Categoria TOP:[/bold yellow] {category_text}")
        
        content.append(f"[bold cyan]Descrição:[/bold cyan] {descricao[:500]}...")
        
        panel = Panel(
            "\n".join(content),
            title=panel_title,
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print(panel)

# ====================================================================================
# FUNÇÕES DE INTERFACE E MENU
# ====================================================================================

def select_search_type():
    """Interface para seleção do tipo de busca"""
    global current_search_type
    
    console.print("\n[bold yellow]Tipos de busca disponíveis:[/bold yellow]")
    for key, value in SEARCH_TYPES.items():
        marker = "✓" if key == current_search_type else " "
        console.print(f"[cyan]{key}[/cyan] [{marker}] {value['name']} - {value['description']}")
    
    choice = Prompt.ask(
        f"\nEscolha o tipo de busca",
        choices=[str(i) for i in SEARCH_TYPES.keys()],
        default=str(current_search_type)
    )
    
    current_search_type = int(choice)
    console.print(f"[green]✓ Tipo de busca alterado para: {SEARCH_TYPES[current_search_type]['name']}[/green]")
    return current_search_type

def select_search_approach():
    """Interface para seleção da abordagem de busca"""
    global current_search_approach
    
    console.print("\n[bold yellow]Abordagens de busca disponíveis:[/bold yellow]")
    for key, value in SEARCH_APPROACHES.items():
        marker = "✓" if key == current_search_approach else " "
        console.print(f"[cyan]{key}[/cyan] [{marker}] {value['name']} - {value['description']}")
    
    choice = Prompt.ask(
        f"\nEscolha a abordagem de busca",
        choices=[str(i) for i in SEARCH_APPROACHES.keys()],
        default=str(current_search_approach)
    )
    
    current_search_approach = int(choice)
    console.print(f"[green]✓ Abordagem alterada para: {SEARCH_APPROACHES[current_search_approach]['name']}[/green]")
    return current_search_approach

def select_sort_mode():
    """Interface para seleção do modo de ordenação"""
    global current_sort_mode
    
    console.print("\n[bold yellow]Modos de ordenação disponíveis:[/bold yellow]")
    for key, value in SORT_MODES.items():
        marker = "✓" if key == current_sort_mode else " "
        console.print(f"[cyan]{key}[/cyan] [{marker}] {value['name']} - {value['description']}")
    
    choice = Prompt.ask(
        f"\nEscolha o modo de ordenação",
        choices=[str(i) for i in SORT_MODES.keys()],
        default=str(current_sort_mode)
    )
    
    current_sort_mode = int(choice)
    console.print(f"[green]✓ Ordenação alterada para: {SORT_MODES[current_sort_mode]['name']}[/green]")
    return current_sort_mode

def toggle_filter():
    """Alterna o filtro de contratações encerradas"""
    global filter_expired
    filter_expired = not filter_expired
    status = "ativado" if filter_expired else "desativado"
    console.print(f"[green]✓ Filtro de contratações encerradas {status}[/green]")

def configure_system():
    """Configurações gerais do sistema"""
    global num_top_categories, MAX_RESULTS
    
    while True:
        console.print("\n[bold yellow]⚙️ Configurações do Sistema[/bold yellow]")
        console.print(f"1. Número máximo de resultados: [bold cyan]{MAX_RESULTS}[/bold cyan]")
        console.print(f"2. Número de TOP categorias: [bold cyan]{num_top_categories}[/bold cyan]")
        console.print("3. Voltar ao menu principal")
        
        choice = Prompt.ask(
            "\nEscolha uma opção",
            choices=["1", "2", "3"],
            default="3"
        )
        
        if choice == "1":
            new_max = Prompt.ask(
                f"Novo número máximo de resultados (atual: {MAX_RESULTS})",
                default=str(MAX_RESULTS)
            )
            try:
                MAX_RESULTS = int(new_max)
                console.print(f"[green]✓ Número máximo de resultados alterado para: {MAX_RESULTS}[/green]")
            except ValueError:
                console.print("[red]Valor inválido![/red]")
        
        elif choice == "2":
            new_top = Prompt.ask(
                f"Novo número de TOP categorias (atual: {num_top_categories})",
                default=str(num_top_categories)
            )
            try:
                num_top_categories = int(new_top)
                console.print(f"[green]✓ Número de TOP categorias alterado para: {num_top_categories}[/green]")
            except ValueError:
                console.print("[red]Valor inválido![/red]")
        
        elif choice == "3":
            break
    
    console.print("[green]✓ Configurações salvas![/green]")

# ====================================================================================
# FUNÇÃO PRINCIPAL DE BUSCA
# ====================================================================================

def perform_search(query, search_type, search_approach):
    """Executa a busca conforme o tipo e abordagem selecionados"""
    global last_results, last_query, last_query_categories
    
    start_time = time.time()
    
    try:
        console.print(f"\n[bold blue]Iniciando busca...[/bold blue]")
        console.print(f"[blue]Query: \"{query}\"[/blue]")
        console.print(f"[blue]Tipo: {SEARCH_TYPES[search_type]['name']}[/blue]")
        console.print(f"[blue]Abordagem: {SEARCH_APPROACHES[search_approach]['name']}[/blue]")
        
        # Pré-processar a consulta
        original_query = query
        processed_query = gvg_pre_processing(
            query, 
            **DEFAULT_PREPROC_PARAMS
        )
        console.print(f"[dim]Query pré-processada: \"{processed_query}\"[/dim]")
        
        # Inicializar variáveis
        results = []
        confidence = 0.0
        categories = []
        
        # FASE 1: Buscar categorias (se necessário para abordagem)
        if search_approach in [2, 3]:  # Correspondência ou Filtro de categoria
            console.print(f"\n[blue]Buscando TOP {num_top_categories} categorias para a query...[/blue]")
            categories = get_top_categories_for_query(original_query, num_top_categories)
            
            if not categories:
                console.print("[yellow]Não foi possível encontrar categorias para a query.[/yellow]")
                return
            
            # Exibir categorias encontradas
            display_top_categories_table(categories)
            last_query_categories = categories
        
        # FASE 2: Executar busca conforme abordagem
        if search_approach == 1:  # DIRETA
            results, confidence = direct_search(processed_query, search_type, MAX_RESULTS, filter_expired)
        
        elif search_approach == 2:  # CORRESPONDÊNCIA
            results, confidence = correspondence_search(processed_query, categories, MAX_RESULTS, filter_expired)
        
        elif search_approach == 3:  # FILTRO DE CATEGORIA
            results, confidence = category_filtered_search(processed_query, search_type, categories, MAX_RESULTS, filter_expired)
        
        else:
            console.print("[red]Abordagem de busca inválida![/red]")
            return
        
        # Aplicar ordenação conforme modo selecionado
        if current_sort_mode == 1:  # Por similaridade (padrão)
            # Já está ordenado por similaridade
            sort_message = "[dim]Ordenação: por similaridade (decrescente)[/dim]"
        elif current_sort_mode == 2:  # Por data de encerramento
            # Ordenar por data de encerramento (ascendente)
            results.sort(key=lambda x: x.get("details", {}).get("dataencerramentoproposta", "9999-12-31"))
            sort_message = "[dim]Ordenação: por data de encerramento (ascendente)[/dim]"
        elif current_sort_mode == 3:  # Por valor estimado
            # Ordenar por valor estimado (decrescente) - campo em lowercase devido ao PostgreSQL
            results.sort(key=lambda x: float(x.get("details", {}).get("valortotalestimado", 0) or 0), reverse=True)
            sort_message = "[dim]Ordenação: por valor estimado (decrescente)[/dim]"
        
        # Atualizar ranks após ordenação
        for i, result in enumerate(results, 1):
            result["rank"] = i
        
        # Armazenar resultados
        last_results = results
        last_query = original_query
        
        # Calcular tempo de busca
        end_time = time.time()
        search_time = end_time - start_time
        
        # Exibir resultados
        display_results(results, search_time, original_query, search_type, search_approach)
        console.print(f"[dim]Tempo total de busca: {search_time:.4f} segundos[/dim]")
        
    except Exception as e:
        console.print(f"[red]Erro durante a busca: {e}[/red]")

# ====================================================================================
# FUNÇÕES AUXILIARES
# ====================================================================================

def show_process_documents(process_number):
    """Mostra documentos de um processo específico"""
    if not last_results or process_number < 1 or process_number > len(last_results):
        console.print("[red]Número de processo inválido![/red]")
        return
    
    result = last_results[process_number - 1]
    details = result.get("details", {})
    
    # Tentar diferentes campos possíveis para o número de controle PNCP
    numero_controle = None
    possible_fields = [
        'numero_controle_pncp',
        'numerocontrolepncp', 
        'id',
        'numero_processo',
        'numeroprocesso'
    ]
    
    for field in possible_fields:
        if field in details and details[field]:
            numero_controle = details[field]
            break
    
    # Debug: mostrar todos os campos disponíveis se não encontrar
    if not numero_controle:
        console.print("[yellow]Debug - Campos disponíveis no resultado:[/yellow]")
        console.print(f"[dim]Details keys: {list(details.keys())}[/dim]")
        console.print(f"[dim]Result keys: {list(result.keys())}[/dim]")
        
        # Tentar usar o ID do resultado principal
        if 'id' in result and result['id']:
            numero_controle = result['id']
        else:
            console.print("[red]Não foi possível encontrar número de controle PNCP![/red]")
            return
    
    console.print(f"\n[bold cyan]Processo Selecionado: #{process_number} - {numero_controle}[/bold cyan]")
    console.print(f"\n[bold green]Buscando documentos para: {numero_controle}[/bold green]")
    
    try:
        with console.status("[bold green]Carregando documentos..."):
            documentos = fetch_documentos(numero_controle)
        
        if not documentos:
            console.print("[yellow]Nenhum documento encontrado para este processo.[/yellow]")
            return
        
        console.print(f"\n[bold green]Links diretos para os documentos:[/bold green]")
        for i, doc in enumerate(documentos, 1):
            tipo_info = f" ({doc['tipo']})" if doc.get('tipo') and doc['tipo'] != 'N/A' else ""
            data_info = f" - {doc['data_publicacao'][:10]}" if doc.get('data_publicacao') and doc['data_publicacao'] != 'N/A' else ""
            console.print(f"{i}. [link={doc['url']}]{doc['nome']}{tipo_info}{data_info}[/link]")
        
        # Opções para sumarização
        console.print("\n[bold yellow]Opções de análise de documentos:[/bold yellow]")
        console.print("1. Sumarizar um documento específico")
        console.print("2. Sumarizar todos os documentos")
        console.print("3. Voltar ao menu principal")
        
        while True:
            choice = Prompt.ask(
                "\nEscolha uma opção",
                choices=["1", "2", "3"],
                default="3"
            )
            
            if choice == "1":
                doc_choice = Prompt.ask(f"Qual documento sumarizar? (1-{len(documentos)})")
                try:
                    doc_idx = int(doc_choice) - 1
                    if 0 <= doc_idx < len(documentos):
                        with console.status("[bold green]Sumarizando documento..."):
                            summary = summarize_document(documentos[doc_idx]['url'])
                        if summary:
                            console.print(f"\n[bold green]Resumo do documento:[/bold green]\n{summary}")
                        else:
                            console.print("[yellow]Não foi possível sumarizar o documento.[/yellow]")
                    else:
                        console.print("[red]Número de documento inválido![/red]")
                except ValueError:
                    console.print("[red]Entrada inválida![/red]")
            
            elif choice == "2":
                with console.status("[bold green]Sumarizando todos os documentos..."):
                    for i, doc in enumerate(documentos, 1):
                        console.print(f"\n[bold yellow]Resumo do documento {i} - {doc['nome']}:[/bold yellow]")
                        summary = summarize_document(doc['url'])
                        if summary:
                            console.print(summary)
                        else:
                            console.print("[yellow]Não foi possível sumarizar este documento.[/yellow]")
                        
                        if i < len(documentos):
                            console.print("\n" + "-"*50)
            
            elif choice == "3":
                break
    
    except Exception as e:
        console.print(f"[red]Erro ao buscar documentos: {e}[/red]")

def generate_process_keywords(process_number):
    """Gera palavras-chave para um processo específico"""
    if not last_results or process_number < 1 or process_number > len(last_results):
        console.print("[red]Número de processo inválido![/red]")
        return
    
    result = last_results[process_number - 1]
    details = result.get("details", {})
    
    description = details.get("descricaocompleta", "")
    if not description:
        console.print("[yellow]Descrição não disponível para este processo.[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Processo Selecionado: #{process_number} - {result['id']}[/bold cyan]")
    console.print(f"\n[bold green]Gerando palavras-chave...[/bold green]")
    
    try:
        with console.status("[bold green]Analisando descrição..."):
            keywords = generate_keywords(description)
        
        if keywords:
            console.print(f"\n[bold green]Palavras-chave geradas:[/bold green]")
            console.print(f"[cyan]{keywords}[/cyan]")
        else:
            console.print("[yellow]Não foi possível gerar palavras-chave.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Erro ao gerar palavras-chave: {e}[/red]")

def export_results_to_excel(results, query, search_type_id):
    """Exporta os resultados da busca para um arquivo Excel."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return False
    
    try:
        # Criar um dataframe com os resultados
        data = []
        for result in results:
            details = result.get("details", {})
            if details:
                result_data = {
                    "Rank": result["rank"],
                    "ID": result["id"],
                    "Similaridade": result["similarity"],
                    "Órgão": details.get("orgaoentidade_razaosocial", "N/A"),
                    "Unidade": details.get("unidadeorgao_nomeunidade", "N/A"),
                    "Município": details.get("unidadeorgao_municipionome", "N/A"),
                    "UF": details.get("unidadeorgao_ufsigla", "N/A"),
                    "Valor": details.get("valortotalestimado", 0),
                    "Data Inclusão": format_date(details.get("datainclusao", "N/A")),
                    "Data Abertura": format_date(details.get("dataaberturaproposta", "N/A")),
                    "Data Encerramento": format_date(details.get("dataencerramentoproposta", "N/A")),
                    "Modalidade ID": details.get("modalidadeid", "N/A"),
                    "Modalidade Nome": details.get("modalidadenome", "N/A"),
                    "Disputa ID": details.get("modadisputaid", "N/A"),
                    "Disputa Nome": details.get("modadisputanome", "N/A"),
                    "Usuário": details.get("usuarionome", "N/A"),
                    "Poder": decode_poder(details.get("orgaoentidade_poderid", "N/A")),
                    "Esfera": decode_esfera(details.get("orgaoentidade_esferaid", "N/A")),
                    "Link Sistema": details.get("linksistemaorigem", "N/A"),
                    "Descrição": details.get("descricaocompleta", "N/A")
                }
                
                # Adicionar scores específicos para abordagem de correspondência
                if current_search_approach == 2 and "correspondence_similarity" in result:
                    result_data["Score_Correspondencia"] = result["correspondence_similarity"]
                
                # Adicionar informações da categoria TOP
                if "top_category_info" in result and result["top_category_info"]:
                    cat = result["top_category_info"]
                    result_data["Categoria_TOP"] = f"{cat['codigo']} - {cat['descricao']} (Score: {cat['correspondence_score']:.3f})"
                
                # Adicionar scores específicos para busca híbrida
                if "semantic_score" in result and "keyword_score" in result:
                    result_data["Score Semântico"] = result["semantic_score"]
                    result_data["Score Palavra-chave"] = result["keyword_score"]
                
                data.append(result_data)
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Gerar nome do arquivo com formato: BUSCA_{Tipo}_{Abordagem}_{Ordenação}_{Query}_{Data}.xlsx
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type_id]["name"].replace(" ", "_")
        search_approach_name = SEARCH_APPROACHES[current_search_approach]["name"].replace(" ", "_")
        sort_mode_name = SORT_MODES[current_sort_mode]["name"].replace(" ", "_")
        
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:20].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        os.makedirs(RESULTS_PATH, exist_ok=True)
        
        # Nome do arquivo com novo formato
        filename = os.path.join(RESULTS_PATH, f"BUSCA_{search_type_name}_{search_approach_name}_{sort_mode_name}_{query_clean}_{timestamp}.xlsx")
        
        # Salvar para Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        console.print(f"[green]Resultados exportados para: {filename}[/green]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados: {str(e)}[/bold red]")
        return False

def export_results_to_pdf(results, query, search_type_id):
    """Exporta os resultados da busca para um arquivo PDF formatado como no terminal."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return False
    
    try:
        # Gerar nome do arquivo com formato: BUSCA_{Tipo}_{Abordagem}_{Ordenação}_{Query}_{Data}.pdf
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type_id]["name"].replace(" ", "_")
        search_approach_name = SEARCH_APPROACHES[current_search_approach]["name"].replace(" ", "_")
        sort_mode_name = SORT_MODES[current_sort_mode]["name"].replace(" ", "_")
        
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:20].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        os.makedirs(RESULTS_PATH, exist_ok=True)
        
        # Nome do arquivo com novo formato
        filename = os.path.join(RESULTS_PATH, f"BUSCA_{search_type_name}_{search_approach_name}_{sort_mode_name}_{query_clean}_{timestamp}.pdf")
        
        # Configurar documento PDF
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=45,
            leftMargin=45,
            topMargin=54,
            bottomMargin=54
        )
        
        # Preparar estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            alignment=1,  # Centralizado
            fontSize=16,
            spaceAfter=20
        )
        heading_style = styles["Heading1"]
        normal_style = styles["Normal"]
        
        # Estilo para descrições
        desc_style = ParagraphStyle(
            "Description",
            parent=normal_style,
            fontSize=11,
            leading=13,
            spaceAfter=6
        )
        
        # Elementos para o PDF
        elements = []
        
        # Título do documento (termo de busca em maiúsculas)
        elements.append(Paragraph(f"BUSCA: \"{query.upper()}\"", title_style))
        
        # Informações da busca
        elements.append(Paragraph(f"Tipo de busca: {SEARCH_TYPES[search_type_id]['name']}", normal_style))
        elements.append(Paragraph(f"Abordagem: {SEARCH_APPROACHES[current_search_approach]['name']}", normal_style))
        elements.append(Paragraph(f"Ordenação: {SORT_MODES[current_sort_mode]['name']}", normal_style))
        elements.append(Paragraph(f"Data da pesquisa: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Informações das categorias se for abordagem por correspondência ou filtro de categoria
        if current_search_approach in [2, 3] and last_query_categories:
            elements.append(Paragraph(f"TOP {len(last_query_categories)} Categorias utilizadas:", normal_style))
            for cat in last_query_categories[:3]:  # Mostrar apenas as 3 primeiras
                elements.append(Paragraph(f"• {cat['codigo']} - {cat['descricao']} ({cat['similarity_score']:.3f})", normal_style))
            elements.append(Spacer(1, 0.1*inch))
        
        # Tabela resumida com margem e fonte menor
        table_data = [
            ["Rank", "Unidade", "Local", "Similaridade", "Valor (R$)", "Data Proposta"]
        ]
        
        # Adicionar coluna Score de Correspondência se for abordagem de correspondência
        if current_search_approach == 2:
            table_data[0].append("Score Corresp.")
        
        # Garantir que os resultados estão em ordem numérica ascendente
        sorted_results = sorted(results, key=lambda x: x.get('rank', 999))
        
        for result in sorted_results:
            details = result.get("details", {})
            if not details:
                continue
                
            valor = format_currency(details.get("valortotalestimado", 0))
            data_encerramento = format_date(details.get("dataencerramentoproposta", "N/A"))
            
            unidade = details.get('unidadeorgao_nomeunidade', 'N/A')
            unidade = f"{unidade[:30]}..." if len(unidade) > 30 else unidade
            
            municipio = details.get('unidadeorgao_municipionome', 'N/A')
            uf = details.get('unidadeorgao_ufsigla', '')
            local = f"{municipio}/{uf}" if uf else municipio
            
            row_data = [
                str(result['rank']),
                unidade,
                local,
                f"{result['similarity']:.4f}",
                valor,
                str(data_encerramento)
            ]
            
            # Adicionar Score de Correspondência se for abordagem de correspondência
            if current_search_approach == 2 and "correspondence_similarity" in result:
                row_data.append(f"{result['correspondence_similarity']:.4f}")
            
            table_data.append(row_data)
        
        # Criar e estilizar a tabela com margens e fonte menor
        table = PDFTable(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            # Azul escuro no cabeçalho em vez de roxo
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # Fonte menor
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),  # Fonte menor nos dados
        ]))
        
        # Adicionar margens na tabela
        elements.append(Spacer(1, 0.1*inch))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Detalhes de cada resultado
        elements.append(Paragraph("Detalhes dos Resultados", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Estilo para título do card (órgão)
        orgao_style = ParagraphStyle(
            "OrgaoStyle",
            parent=styles["Heading2"],
            fontSize=12,
            spaceAfter=2
        )
        
        # Estilo para subtítulo do card (unidade)
        unidade_style = ParagraphStyle(
            "UnidadeStyle",
            parent=styles["Heading3"],
            fontSize=10,
            spaceAfter=5
        )
        
        # Garantir que os resultados estão em ordem numérica ascendente novamente
        for result in sorted_results:
            details = result.get("details", {})
            if not details:
                continue
            
            # Título do card: Órgão
            orgao = escape_html_for_pdf(details.get('orgaoentidade_razaosocial', 'Órgão não informado'))
            elements.append(Paragraph(f"{result['rank']}. {orgao}", orgao_style))
            
            # Subtítulo do card: Unidade
            unidade = escape_html_for_pdf(details.get('unidadeorgao_nomeunidade', 'Unidade não informada'))
            elements.append(Paragraph(f"{unidade}", unidade_style))
            
            # Conteúdo do card
            elements.append(Paragraph(f"<b>ID:</b> {escape_html_for_pdf(result['id'])}", normal_style))
            elements.append(Paragraph(f"<b>Similaridade:</b> {result['similarity']:.4f}", normal_style))
            
            # Adicionar Score de Correspondência se disponível (abordagem de correspondência)
            if current_search_approach == 2 and "correspondence_similarity" in result:
                elements.append(Paragraph(f"<b>Score Correspondência:</b> {result['correspondence_similarity']:.4f}", normal_style))
            
            # Adicionar categoria TOP se disponível
            if "top_category_info" in result and result["top_category_info"]:
                cat = result["top_category_info"]
                elements.append(Paragraph(f"<b>Categoria TOP:</b> {escape_html_for_pdf(cat['codigo'])} - {escape_html_for_pdf(cat['descricao'])} (Score: {cat['correspondence_score']:.3f})", normal_style))
            
            elements.append(Paragraph(f"<b>Local:</b> {escape_html_for_pdf(details.get('unidadeorgao_municipionome', 'N/A'))}/{escape_html_for_pdf(details.get('unidadeorgao_ufsigla', 'N/A'))}", normal_style))
            elements.append(Paragraph(f"<b>Valor:</b> {escape_html_for_pdf(format_currency(details.get('valortotalestimado', 0)))}", normal_style))
            elements.append(Paragraph(f"<b>Datas:</b> Inclusão: {escape_html_for_pdf(format_date(details.get('datainclusao', 'N/A')))} | Abertura: {escape_html_for_pdf(format_date(details.get('dataaberturaproposta', 'N/A')))} | Encerramento: {escape_html_for_pdf(format_date(details.get('dataencerramentoproposta', 'N/A')))}", normal_style))
            elements.append(Paragraph(f"<b>Modalidade:</b> {escape_html_for_pdf(details.get('modalidadeid', 'N/A'))} - {escape_html_for_pdf(details.get('modalidadenome', 'N/A'))} | <b>Disputa:</b> {escape_html_for_pdf(details.get('modadisputaid', 'N/A'))} - {escape_html_for_pdf(details.get('modadisputanome', 'N/A'))}", normal_style))
            elements.append(Paragraph(f"<b>Usuário:</b> {escape_html_for_pdf(details.get('usuarionome', 'N/A'))} | <b>Poder:</b> {escape_html_for_pdf(decode_poder(details.get('orgaoentidade_poderid', 'N/A')))} | <b>Esfera:</b> {escape_html_for_pdf(decode_esfera(details.get('orgaoentidade_esferaid', 'N/A')))}", normal_style))
            
            # Adicionar link do sistema se disponível
            if details.get('linksistemaorigem'):
                elements.append(Paragraph(f"<b>Link Sistema:</b> {escape_html_for_pdf(details.get('linksistemaorigem', 'N/A'))}", normal_style))

            # Descrição (processada para ser legível em PDF)
            descricao = details.get("descricaocompleta", "N/A")
            if len(descricao) > 1000:
                descricao = descricao[:1000] + "..."
            descricao = descricao.replace(" :: ", "\n• ")
            if not descricao.startswith("•"):
                descricao = "• " + descricao

            # Escapar caracteres especiais que podem causar problemas de parsing
            descricao = escape_html_for_pdf(descricao)
            
            elements.append(Paragraph(f"<b>Descrição:</b>", normal_style))
            elements.append(Paragraph(descricao, desc_style))
            
            # Adicionar linha divisória (mas não quebra de página)
            elements.append(Spacer(1, 0.3*inch))
        
        # Construir o PDF
        doc.build(elements)
        
        console.print(f"[green]Resultados exportados para PDF: {filename}[/green]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados para PDF: {str(e)}[/bold red]")
        return False

def export_results(results, query, search_type_id):
    """Permite ao usuário escolher o formato de exportação dos resultados."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return
    
    console.print("\n[bold cyan]Escolha o formato de exportação:[/bold cyan]")
    console.print("[cyan]1[/cyan] - Excel (.xlsx)")
    console.print("[cyan]2[/cyan] - PDF (.pdf)")
    
    choice = Prompt.ask(
        "Formato",
        choices=["1", "2"],
        default="1"
    )
    
    if choice == "1":
        export_results_to_excel(results, query, search_type_id)
    else:
        export_results_to_pdf(results, query, search_type_id)

def escape_html_for_pdf(text):
    """Escapa caracteres HTML para uso seguro em Paragraphs do ReportLab"""
    if not isinstance(text, str):
        text = str(text)
    
    # Substituir caracteres especiais por entidades HTML
    replacements = [
        ('&', '&amp;'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('"', '&quot;'),
        ("'", '&#39;')
    ]
    
    for old, new in replacements:
        text = text.replace(old, new)
    
    return text

def display_menu():
    """Exibe o menu principal com as opções disponíveis"""
    console.print("\n" + "="*80)
    console.print("[bold cyan]MENU DE OPÇÕES:[/bold cyan]")
    console.print(f"1. Tipo de busca: [bold]{SEARCH_TYPES[current_search_type]['name']}[/bold]")
    console.print(f"2. Abordagem: [bold]{SEARCH_APPROACHES[current_search_approach]['name']}[/bold]")
    console.print(f"3. Ordenação: [bold]{SORT_MODES[current_sort_mode]['name']}[/bold]")
    console.print(f"4. Filtro contratações encerradas: [bold]{'✓ Ativo' if filter_expired else '✗ Inativo'}[/bold]")
    console.print("5. Configurações do sistema")
    
    # Opções contextuais baseadas em resultados disponíveis
    if last_results:
        console.print("\n[bold yellow]Opções de resultados:[/bold yellow]")
        console.print("6. 📄 Ver documentos de um processo")
        console.print("7. 🔤 Gerar palavras-chave de um processo") 
        console.print("8. 📊 Exportar resultados")
    else:
        console.print("\n[dim]Realize uma busca para ver opções de resultados[/dim]")
    
    console.print("\n[cyan]Digite qualquer outro texto para realizar uma nova busca[/cyan]")

def main():
    """Função principal do sistema"""
    global current_search_type, current_search_approach, current_sort_mode, filter_expired
    
    # Cabeçalho do sistema
    console.print(Panel(
        "[bold cyan]Sistema de Busca Inteligente para Contratos Públicos PNCP[/bold cyan]\n" +
        "[bold cyan]Conecta ao Supabase e realiza diferentes tipos de busca[/bold cyan]\n" +
        "[bold yellow]Três abordagens distintas de busca com menu separado![/bold yellow]",
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE[/bold magenta]",
        subtitle="[bold cyan]Direta • Correspondência • Filtro[/bold cyan]",
        expand=False,
        width=80
    ))
    
    # Verificar conexão com o banco usando função de gvg_search_utils
    console.print("[blue]Testando conexão com o banco de dados...[/blue]")
    if not test_connection():
        console.print("[red]Falha na conexão com o banco de dados![/red]")
        console.print("[yellow]Verifique as configurações de conexão.[/yellow]")
        return
    
    console.print("[green]✓ Conexão com banco de dados estabelecida com sucesso![/green]")
    
    # Loop principal
    while True:
        display_menu()
        
        user_input = input("\n> ").strip()
        
        if user_input == "1":
            select_search_type()
        
        elif user_input == "2":
            select_search_approach()
        
        elif user_input == "3":
            select_sort_mode()
        
        elif user_input == "4":
            toggle_filter()
        
        elif user_input == "5":
            configure_system()
        
        elif user_input == "6" and last_results:
            try:
                process_num = int(Prompt.ask(f"Número do processo (1-{len(last_results)})"))
                show_process_documents(process_num)
            except ValueError:
                console.print("[red]Número inválido![/red]")
        
        elif user_input == "7" and last_results:
            try:
                process_num = int(Prompt.ask(f"Número do processo (1-{len(last_results)})"))
                generate_process_keywords(process_num)
            except ValueError:
                console.print("[red]Número inválido![/red]")
        
        elif user_input == "8" and last_results:
            export_results(last_results, last_query, current_search_type)
        
        elif user_input.lower() in ['sair', 'exit', 'quit', 'q']:
            console.print("[bold yellow]Encerrando sistema...[/bold yellow]")
            break
        
        elif user_input:  # Qualquer outro texto não vazio = nova busca
            perform_search(user_input, current_search_type, current_search_approach)

if __name__ == "__main__":
    main()
