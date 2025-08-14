"""
GvG_SP_Search_Terminal_v6.py
Sistema Avançado de Busca PNCP - Versão 6.0

Características principais da V6:
• NOVA LÓGICA DE BUSCA: Busca baseada em categorias
• Embeddar a query e buscar TOP N categorias (N=5 padrão)
• Mostrar tabela com as TOP N categorias da query ANTES da busca
• Buscar apenas contratações que tenham pelo menos uma dessas TOP N categorias
• Ordenação por multiplicação de similarities (query→categoria × contratação→categoria)
• Exibir categoria mais importante (codcat - nomcat) nos detalhes de cada resultado
• Integração completa com sistema de categorização pré-processado

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
import pandas as pd
import time
import locale
import numpy as np
import json
import math
import re
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
        summarize_document
    )
except ImportError:
    print("ERRO: Não foi possível importar as funções de busca de gvg_search_utils.")
    sys.exit(1)

# Importações adicionais para categorização (V6)
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

# Tipos de busca
SEARCH_TYPES = {
    1: {"name": "Categorias V6", "description": "Nova busca baseada em categorias (TOP N)"},
    2: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    3: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    4: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
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
last_query_categories = None  # V6: Armazenar categorias da query

current_search_type = 1  # Tipo de busca padrão: Categorias V6
current_sort_mode = 1  # Modo de ordenação padrão: Similaridade
filter_expired = True  # Filtro para ocultar contratações encerradas

# Configurações para categorização V6
num_top_categories = 5  # Número padrão de TOP categorias para buscar (N=5)
category_search_enabled = True  # Busca por categorias ativada por padrão


# ====================================================================================
# FUNÇÕES DE CATEGORIZAÇÃO E BUSCA V6
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
    V6: Embedda a query e busca as TOP N categorias mais similares.
    
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
    V6: Exibe uma tabela rica com as TOP N categorias da query.
    
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

def category_based_search(query_text, top_categories, limit=MAX_RESULTS, filter_expired=True):
    """
    V6: Nova busca baseada em categorias.
    Busca apenas contratações que tenham pelo menos uma das TOP N categorias.
    Ordena por multiplicação de similarities (query→categoria × contratação→categoria).
    
    Args:
        query_text: Texto da consulta
        top_categories: Lista das TOP N categorias da query
        limit: Limite de resultados
        filter_expired: Filtrar contratações encerradas
        
    Returns:
        Tuple (resultados_formatados, confiança)
    """
    try:
        # Extrair códigos das categorias para busca
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # Conectar ao banco
        connection = create_connection()
        cursor = connection.cursor()
        
        # Query SQL V6: Busca contratações que tenham pelo menos uma das TOP N categorias
        search_query = """
        SELECT 
            c.numeroControlePNCP,
            c.anoCompra,
            c.descricaoCompleta,
            c.valorTotalHomologado,
            c.valorTotalEstimado,
            c.dataAberturaProposta,
            c.dataEncerramentoProposta,
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
        
        # Processar resultados e calcular similarity score V6
        formatted_results = []
        for row in results:
            result_dict = dict(zip(column_names, row))
            
            # Calcular similarity score V6 (multiplicação de similarities)
            v6_similarity = calculate_v6_similarity_score(
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
                "similarity": v6_similarity,
                "v6_similarity": v6_similarity,
                "top_category_info": top_category_info,
                "details": result_dict
            })
        
        # Ordenar por similarity V6 (decrescente)
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
        console.print(f"[red]Erro na busca baseada em categorias V6: {e}[/red]")
        return [], 0.0

def calculate_v6_similarity_score(query_categories, result_categories, result_similarities):
    """
    V6: Calcula o score de similaridade pela multiplicação:
    similarity(query→categoria) × similarity(contratação→categoria)
    
    Args:
        query_categories: TOP N categorias da query com suas similarities
        result_categories: Categorias do resultado (array de códigos)
        result_similarities: Similarities do resultado (array de scores)
        
    Returns:
        Score final V6 (float)
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
                    
                    # Calcular score V6: multiplicação das similarities
                    v6_score = float(query_similarity) * float(result_similarity)
                    
                    # Manter o maior score encontrado
                    max_score = max(max_score, v6_score)
                    
                except (IndexError, ValueError, TypeError):
                    continue
        
        return max_score
        
    except Exception as e:
        return 0.0

def find_top_category_for_result(query_categories, result_categories, result_similarities):
    """
    V6: Encontra a categoria mais importante para um resultado específico.
    Retorna a categoria com maior score V6 (multiplicação).
    
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
                    
                    # Calcular score V6
                    v6_score = float(query_similarity) * float(result_similarity)
                    
                    # Verificar se é o melhor score
                    if v6_score > best_score:
                        best_score = v6_score
                        best_category = {
                            'codigo': query_cat['codigo'],
                            'descricao': query_cat['descricao'],
                            'query_similarity': query_similarity,
                            'result_similarity': result_similarity,
                            'v6_score': v6_score
                        }
                        
                except (IndexError, ValueError, TypeError):
                    continue
        
        return best_category
        
    except Exception as e:
        return None

# ====================================================================================
# FIM DAS FUNÇÕES V6
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

def display_results(results, search_time=0, query="", search_type=1):
    """Exibe os resultados da busca de forma organizada"""
    if not results:
        console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
        return
    
    console.print(f"\n[bold green]Resultados encontrados: {len(results)}[/bold green]")
    console.print(f"[blue]Tempo de busca: {search_time:.3f}s[/blue]")
    console.print(f"[blue]Tipo de busca: {SEARCH_TYPES[search_type]['name']}[/blue]")
    
    # V6: Mostrar informações específicas da busca por categorias
    if search_type == 1 and last_query_categories:
        console.print(f"[magenta]Baseado em {len(last_query_categories)} TOP categorias[/magenta]")
    
    console.print()
    
    # V6: Primeiro, mostrar uma tabela resumida (como na v5)
    table = Table(title="Resumo dos Resultados V6", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6, justify="center")
    table.add_column("Órgão", style="cyan", width=40)
    table.add_column("Local", style="cyan", width=30)
    table.add_column("Similaridade", justify="right", width=12)
    table.add_column("Valor (R$)", justify="right", width=17)
    table.add_column("Data Encerramento", width=12)
    
    # V6: Adicionar coluna específica para busca por categorias
    if search_type == 1:
        table.add_column("V6 Score", justify="right", width=10, style="bold yellow")
    
    for result in results:
        details = result.get("details", {})
        
        # Formatar valor usando função de gvg_search_utils
        valor = format_currency(details.get("valortotalestimado", 0)) if details else "N/A"
        
        # Formatar data
        data_encerramento = details.get("dataencerramentoproposta", "N/A") if details else "N/A"
        
        # Preparar informações de órgão e local
        unidade = details.get('unidadeorgao_nomeunidade', 'N/A')
        #unidade = f"{unidade[:35]}..." if len(unidade) > 35 else unidade
        
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
        
        # V6: Adicionar V6 Score se for busca por categorias
        if search_type == 1 and "v6_similarity" in result:
            row_data.append(f"{result['v6_similarity']:.4f}")
        
        table.add_row(*row_data)

    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    
    # V6: Depois, mostrar detalhes de cada resultado
    for result in results:
        details = result.get("details", {})
        
        # Destacar termos da consulta na descrição
        descricao = highlight_key_terms(
            details.get("descricaocompleta", "N/A"),
            query.split()
        )
        
        # Criar painel com informações detalhadas
        panel_title = f"#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})"
        
        # V6: Adicionar informações específicas da busca por categorias
        if search_type == 1 and "v6_similarity" in result:
            panel_title += f" [V6 Score: {result['v6_similarity']:.4f}]"
        
        # Adicionar scores específicos para busca híbrida
        if "semantic_score" in result and "keyword_score" in result:
            panel_title += f" [Semântico: {result['semantic_score']:.4f}, Palavra-chave: {result['keyword_score']:.4f}]"
        
        content = [
            f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoentidade_razaosocial', 'N/A')}",
            f"[bold cyan]Unidade:[/bold cyan] {details.get('unidadeorgao_nomeunidade', 'N/A')}",
            f"[bold cyan]Local:[/bold cyan] {details.get('unidadeorgao_municipionome', 'N/A')}/{details.get('unidadeorgao_ufsigla', 'N/A')}",
            f"[bold cyan]Valor:[/bold cyan] {format_currency(details.get('valortotalestimado', 0))}",
            f"[bold cyan]Datas:[/bold cyan] Abertura: {details.get('dataaberturaproposta', 'N/A')} | Encerramento: {details.get('dataencerramentoproposta', 'N/A')}",
        ]
        
        # V6: Adicionar categoria mais importante se disponível
        if "top_category_info" in result and result["top_category_info"]:
            cat = result["top_category_info"]
            category_text = f"{cat['codigo']} - {cat['descricao']} (V6: {cat['v6_score']:.3f})"
            content.append(f"[bold yellow]🎯 Categoria TOP:[/bold yellow] {category_text}")
        
        content.append(f"[bold cyan]Descrição:[/bold cyan] {descricao[:500]}...")
        
        panel = Panel(
            "\n".join(content),
            title=panel_title,
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print(panel)

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
            console.print("[red]Número de controle PNCP não encontrado para este processo.[/red]")
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
            titulo = doc.get('titulo', 'Documento sem título')
            url = doc.get('url', 'N/A')
            
            # Criar hyperlink clicável (funciona na maioria dos terminais modernos)
            hyperlink = f"[link={url}]{url}[/link]"
            console.print(f"[bold cyan]{i}.[/bold cyan] {titulo}")
            console.print(f"   {hyperlink}")
            console.print()
        
        # Opções para sumarização
        while True:
            console.print("\n[bold yellow]Opções:[/bold yellow]")
            console.print("Digite o número do documento para sumarizar (1-{})".format(len(documentos)))
            console.print("Digite 0 para voltar")
            
            choice = input("\n> ").strip()
            
            if choice == "0":
                break
            
            try:
                doc_num = int(choice)
                if 1 <= doc_num <= len(documentos):
                    doc = documentos[doc_num - 1]
                    console.print(f"\n[bold green]Sumarizando documento: {doc.get('titulo', 'Sem título')}[/bold green]")
                    
                    with console.status("[bold green]Analisando documento..."):
                        summary = summarize_document(doc.get('url', ''))
                    
                    if summary:
                        console.print(Panel(
                            summary,
                            title="📋 Resumo do Documento",
                            border_style="green",
                            padding=(1, 2)
                        ))
                    else:
                        console.print("[yellow]Não foi possível sumarizar o documento.[/yellow]")
                else:
                    console.print("[red]Número inválido![/red]")
            except ValueError:
                console.print("[red]Digite apenas números![/red]")
    
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
            console.print(Panel(
                keywords,
                title="🔍 Palavras-chave Geradas",
                border_style="green",
                padding=(1, 2)
            ))
        else:
            console.print("[yellow]Não foi possível gerar palavras-chave.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Erro ao gerar palavras-chave: {e}[/red]")

def export_results_to_excel(results, query, search_type_id):
    """V6: Exporta os resultados da busca para um arquivo Excel (baseado na v5)."""
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
                    "Data Abertura": details.get("dataaberturaproposta", "N/A"),
                    "Data Encerramento": details.get("dataencerramentoproposta", "N/A"),
                    "Descrição": details.get("descricaocompleta", "N/A")
                }
                
                # V6: Adicionar scores específicos para busca por categorias
                if "v6_similarity" in result:
                    result_data["V6_Score"] = result["v6_similarity"]
                
                # V6: Adicionar informações da categoria TOP
                if "top_category_info" in result and result["top_category_info"]:
                    cat = result["top_category_info"]
                    result_data["Categoria_TOP"] = f"{cat['codigo']} - {cat['descricao']} (V6: {cat['v6_score']:.3f})"
                
                # Adicionar scores específicos para busca híbrida
                if "semantic_score" in result and "keyword_score" in result:
                    result_data["Score Semântico"] = result["semantic_score"]
                    result_data["Score Palavra-chave"] = result["keyword_score"]
                
                data.append(result_data)
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Gerar nome do arquivo baseado na data e hora (como na v5)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type_id]["name"].lower()
        
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:30].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        os.makedirs(RESULTS_PATH, exist_ok=True)
        
        # Nome do arquivo
        filename = os.path.join(RESULTS_PATH, f"busca_{search_type_name}_{query_clean}_{timestamp}.xlsx")
        
        # Salvar para Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        console.print(f"[green]Resultados exportados para: {filename}[/green]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados: {str(e)}[/bold red]")
        return False

def export_results_to_pdf(results, query, search_type_id):
    """V6: Exporta os resultados da busca para um arquivo PDF formatado como no terminal (baseado na v5)."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return False
    
    try:
        # Gerar nome do arquivo baseado na data e hora (como na v5)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type_id]["name"].lower()
        
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:30].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        os.makedirs(RESULTS_PATH, exist_ok=True)
        
        # Nome do arquivo
        filename = os.path.join(RESULTS_PATH, f"busca_{search_type_name}_{query_clean}_{timestamp}.pdf")
        
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
        elements.append(Paragraph(f"BUSCA V6: \"{query.upper()}\"", title_style))
        
        # Informações da busca
        elements.append(Paragraph(f"Tipo de busca: {SEARCH_TYPES[search_type_id]['name']}", normal_style))
        elements.append(Paragraph(f"Ordenação: {SORT_MODES[current_sort_mode]['name']}", normal_style))
        elements.append(Paragraph(f"Data da pesquisa: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # V6: Informações das categorias se for busca por categorias
        if search_type_id == 1 and last_query_categories:
            elements.append(Paragraph(f"TOP {len(last_query_categories)} Categorias utilizadas:", normal_style))
            for cat in last_query_categories[:3]:  # Mostrar apenas as 3 primeiras
                elements.append(Paragraph(f"• {cat['codigo']} - {cat['descricao']} ({cat['similarity_score']:.3f})", normal_style))
            elements.append(Spacer(1, 0.1*inch))
        
        # Tabela resumida com margem e fonte menor
        table_data = [
            ["Rank", "Unidade", "Local", "Similaridade", "Valor (R$)", "Data Proposta"]
        ]
        
        # V6: Adicionar coluna V6 Score se for busca por categorias
        if search_type_id == 1:
            table_data[0].append("V6 Score")
        
        # Garantir que os resultados estão em ordem numérica ascendente
        sorted_results = sorted(results, key=lambda x: x.get('rank', 999))
        
        for result in sorted_results:
            details = result.get("details", {})
            if not details:
                continue
                
            valor = format_currency(details.get("valortotalestimado", 0))
            data_encerramento = details.get("dataencerramentoproposta", "N/A")
            
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
            
            # V6: Adicionar V6 Score se for busca por categorias
            if search_type_id == 1 and "v6_similarity" in result:
                row_data.append(f"{result['v6_similarity']:.4f}")
            
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
            
            # V6: Adicionar V6 Score se disponível
            if "v6_similarity" in result:
                elements.append(Paragraph(f"<b>V6 Score:</b> {result['v6_similarity']:.4f}", normal_style))
            
            # V6: Adicionar categoria TOP se disponível
            if "top_category_info" in result and result["top_category_info"]:
                cat = result["top_category_info"]
                elements.append(Paragraph(f"<b>Categoria TOP:</b> {escape_html_for_pdf(cat['codigo'])} - {escape_html_for_pdf(cat['descricao'])} (V6: {cat['v6_score']:.3f})", normal_style))
            
            elements.append(Paragraph(f"<b>Local:</b> {escape_html_for_pdf(details.get('unidadeorgao_municipionome', 'N/A'))}/{escape_html_for_pdf(details.get('unidadeorgao_ufsigla', 'N/A'))}", normal_style))
            elements.append(Paragraph(f"<b>Valor:</b> {escape_html_for_pdf(format_currency(details.get('valortotalestimado', 0)))}", normal_style))
            elements.append(Paragraph(f"<b>Datas:</b> Abertura: {escape_html_for_pdf(details.get('dataaberturaproposta', 'N/A'))} | Encerramento: {escape_html_for_pdf(details.get('dataencerramentoproposta', 'N/A'))}", normal_style))

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
    """V6: Permite ao usuário escolher o formato de exportação dos resultados (como na v5)."""
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

def create_pdf_report(data, filepath, query="", search_type=1):
    """Cria um relatório PDF dos resultados"""
    try:
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Título
        title = Paragraph(f"<b>Relatório de Busca GovGo - {SEARCH_TYPES[search_type]['name']}</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Informações da consulta
        if query:
            query_info = Paragraph(f"<b>Consulta:</b> {query}", styles['Normal'])
            story.append(query_info)
        
        search_info = Paragraph(f"<b>Tipo de busca:</b> {SEARCH_TYPES[search_type]['description']}", styles['Normal'])
        story.append(search_info)
        
        timestamp_info = Paragraph(f"<b>Data/Hora:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", styles['Normal'])
        story.append(timestamp_info)
        
        results_info = Paragraph(f"<b>Total de resultados:</b> {len(data)}", styles['Normal'])
        story.append(results_info)
        story.append(Spacer(1, 20))
        
        # V6: Informações das categorias se disponível
        if search_type == 1 and last_query_categories:
            categories_info = Paragraph(f"<b>TOP Categorias utilizadas:</b> {len(last_query_categories)}", styles['Normal'])
            story.append(categories_info)
            
            for cat in last_query_categories[:3]:  # Mostrar apenas as 3 primeiras
                cat_detail = Paragraph(f"• {cat['codigo']} - {cat['descricao']} ({cat['similarity_score']:.3f})", styles['Normal'])
                story.append(cat_detail)
            
            story.append(Spacer(1, 20))
        
        # Tabela de resultados (resumida)
        table_data = [['Rank', 'ID', 'Similaridade', 'Órgão', 'Valor Estimado']]
        
        for item in data[:20]:  # Limitar a 20 primeiros resultados na tabela
            table_data.append([
                str(item['Rank']),
                str(item['ID'])[:15] + "..." if len(str(item['ID'])) > 15 else str(item['ID']),
                item['Similaridade'],
                str(item['Órgão'])[:30] + "..." if len(str(item['Órgão'])) > 30 else str(item['Órgão']),
                format_currency(item['Valor_Estimado'])
            ])
        
        pdf_table = PDFTable(table_data)
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(pdf_table)
        doc.build(story)
        
    except Exception as e:
        console.print(f"[red]Erro ao criar PDF: {e}[/red]")

def perform_search(query, search_type):
    """Executa a busca conforme o tipo selecionado"""
    global last_results, last_query, last_query_categories
    
    start_time = time.time()
    
    try:
        if search_type == 1:
            # V6: Nova busca baseada em categorias
            console.print(f"[bold green]Iniciando busca V6 baseada em categorias...[/bold green]")
            
            # Passo 1: Obter TOP N categorias da query
            console.print(f"[blue]Buscando TOP {num_top_categories} categorias para a query...[/blue]")
            with console.status("[bold green]Analisando categorias da query..."):
                top_categories = get_top_categories_for_query(query, num_top_categories)
            
            if not top_categories:
                console.print("[red]Não foi possível encontrar categorias para a query.[/red]")
                return
            
            # Armazenar categorias da query para uso posterior
            last_query_categories = top_categories
            
            # Passo 2: Exibir tabela com TOP N categorias
            display_top_categories_table(top_categories)
            
            # Passo 3: Realizar busca baseada nessas categorias
            console.print(f"[blue]Buscando contratações com base nas TOP {len(top_categories)} categorias...[/blue]")
            with console.status("[bold green]Executando busca V6..."):
                results, confidence = category_based_search(query, top_categories, MAX_RESULTS, filter_expired)
            
        elif search_type == 2:
            # Busca semântica (herdada)
            console.print("[bold green]Executando busca semântica...[/bold green]")
            with console.status("[bold green]Processando consulta..."):
                results, confidence = semantic_search(query, MAX_RESULTS, MIN_RESULTS, filter_expired)
        
        elif search_type == 3:
            # Busca por palavras-chave (herdada)
            console.print("[bold green]Executando busca por palavras-chave...[/bold green]")
            with console.status("[bold green]Processando consulta..."):
                results, confidence = keyword_search(query, MAX_RESULTS, MIN_RESULTS, filter_expired)
        
        elif search_type == 4:
            # Busca híbrida (herdada)
            console.print("[bold green]Executando busca híbrida...[/bold green]")
            with console.status("[bold green]Processando consulta..."):
                results, confidence = hybrid_search(query, MAX_RESULTS, MIN_RESULTS, SEMANTIC_WEIGHT, filter_expired)
        
        else:
            console.print("[red]Tipo de busca inválido![/red]")
            return
        
        search_time = time.time() - start_time
        
        # Armazenar resultados e query
        last_results = results
        last_query = query
        
        # Exibir resultados
        if results:
            display_results(results, search_time, query, search_type)
            console.print(f"\n[bold blue]Confiança da busca: {confidence:.2f}%[/bold blue]")
        else:
            console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Erro durante a busca: {e}[/red]")

def select_search_type():
    """Interface para seleção do tipo de busca"""
    global current_search_type
    
    console.print("\n[bold yellow]Tipos de busca disponíveis:[/bold yellow]")
    for key, value in SEARCH_TYPES.items():
        marker = "✓" if key == current_search_type else " "
        console.print(f"{marker} {key}. {value['name']} - {value['description']}")
    
    choice = input(f"\nEscolha o tipo de busca (1-{len(SEARCH_TYPES)}): ").strip()
    
    try:
        choice_int = int(choice)
        if choice_int in SEARCH_TYPES:
            current_search_type = choice_int
            console.print(f"[green]✓ Tipo de busca alterado para: {SEARCH_TYPES[choice_int]['name']}[/green]")
        else:
            console.print("[red]Opção inválida![/red]")
    except ValueError:
        console.print("[red]Digite apenas números![/red]")
    
    return current_search_type

def select_sort_mode():
    """Interface para seleção do modo de ordenação"""
    global current_sort_mode
    
    console.print("\n[bold yellow]Modos de ordenação disponíveis:[/bold yellow]")
    for key, value in SORT_MODES.items():
        marker = "✓" if key == current_sort_mode else " "
        console.print(f"{marker} {key}. {value['name']} - {value['description']}")
    
    choice = input(f"\nEscolha o modo de ordenação (1-{len(SORT_MODES)}): ").strip()
    
    try:
        choice_int = int(choice)
        if choice_int in SORT_MODES:
            current_sort_mode = choice_int
            console.print(f"[green]✓ Modo de ordenação alterado para: {SORT_MODES[choice_int]['name']}[/green]")
        else:
            console.print("[red]Opção inválida![/red]")
    except ValueError:
        console.print("[red]Digite apenas números![/red]")
    
    return current_sort_mode

def toggle_filter():
    """Alterna o filtro de contratações encerradas"""
    global filter_expired
    filter_expired = not filter_expired
    status = "ativado" if filter_expired else "desativado"
    console.print(f"[green]✓ Filtro de contratações encerradas {status}[/green]")

def configure_system():
    """V6: Configurações gerais do sistema"""
    global num_top_categories, category_search_enabled, MAX_RESULTS
    
    while True:
        console.print("\n[bold yellow]⚙️ Configurações do Sistema V6[/bold yellow]")
        console.print(f"[cyan]Número máximo de resultados:[/cyan] {MAX_RESULTS}")
        console.print(f"[cyan]Número de TOP categorias:[/cyan] {num_top_categories}")
        console.print(f"[cyan]Busca por categorias:[/cyan] {'Ativada' if category_search_enabled else 'Desativada'}")
        
        console.print("\n[bold cyan]Opções:[/bold cyan]")
        console.print("1. Alterar número máximo de resultados")
        console.print("2. Alterar número de TOP categorias")
        console.print("3. Ativar/Desativar busca por categorias")
        console.print("4. Voltar ao menu principal")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == "1":
            try:
                new_max = int(input(f"Digite o novo número máximo de resultados (atual: {MAX_RESULTS}, recomendado: 10-50): ").strip())
                if 5 <= new_max <= 100:
                    MAX_RESULTS = new_max
                    console.print(f"[green]✓ Número máximo de resultados alterado para: {MAX_RESULTS}[/green]")
                else:
                    console.print("[red]Número deve estar entre 5 e 100![/red]")
            except ValueError:
                console.print("[red]Digite apenas números![/red]")
        
        elif choice == "2":
            try:
                new_num = int(input(f"Digite o novo número de TOP categorias (atual: {num_top_categories}, recomendado: 3-10): ").strip())
                if 1 <= new_num <= 15:
                    num_top_categories = new_num
                    console.print(f"[green]✓ Número de TOP categorias alterado para: {num_top_categories}[/green]")
                else:
                    console.print("[red]Número deve estar entre 1 e 15![/red]")
            except ValueError:
                console.print("[red]Digite apenas números![/red]")
        
        elif choice == "3":
            category_search_enabled = not category_search_enabled
            status = "ativada" if category_search_enabled else "desativada"
            console.print(f"[green]✓ Busca por categorias {status}[/green]")
        
        elif choice == "4":
            break
        
        else:
            console.print("[red]Opção inválida![/red]")
            
        # Dar uma pausa para ver a mensagem
        if choice in ["1", "2", "3"]:
            input("\nPressione Enter para continuar...")
    
    console.print("[green]✓ Configurações salvas![/green]")

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
    console.print(f"1. Alterar tipo de busca (atual: [bold]{SEARCH_TYPES[current_search_type]['name']}[/bold])")
    console.print(f"2. Alterar ordenação (atual: [bold]{SORT_MODES[current_sort_mode]['name']}[/bold])")
    console.print(f"3. Filtro contratações encerradas ({'✓ Ativo' if filter_expired else '✗ Inativo'})")
    console.print("4. ⚙️ Configurações do sistema")  # V6: Nova opção consolidada
    
    # Opções contextuais baseadas em resultados disponíveis
    if last_results:
        console.print("5. Exportar resultados (Excel + PDF)")
        console.print("6. Ver documentos de um processo")
        console.print("7. Gerar palavras-chave de um processo")
        console.print("8. Sair")
        console.print("\n[bold green]Digite sua consulta ou escolha uma opção (1-8):[/bold green]")
    else:
        console.print("5. Sair")
        console.print("\n[bold green]Digite sua consulta ou escolha uma opção (1-5):[/bold green]")

def main():
    """Função principal do sistema"""
    global current_search_type, current_sort_mode, filter_expired
    
    # Cabeçalho do sistema
    console.print(Panel(
        "[bold cyan]Sistema de Busca Inteligente para Contratos Públicos PNCP[/bold cyan]\n" +
        "[bold cyan]Conecta ao Supabase e realiza diferentes tipos de busca[/bold cyan]\n" +
        "[bold yellow]NOVO V6: Busca revolucionária baseada em TOP N categorias![/bold yellow]",
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE v6.0[/bold magenta]",
        subtitle="[bold cyan]Semântica, Palavras-chave, Híbrida + Busca por Categorias V6[/bold cyan]",
        expand=False,
        width=80
    ))
    
    # Verificar conexão com o banco usando função de gvg_search_utils
    console.print("[blue]Testando conexão com o banco de dados...[/blue]")
    if not test_connection():
        console.print("[bold red]Não foi possível conectar ao banco de dados. Verifique:")
        console.print("1. Se o arquivo 'supabase_v0.env' está presente")
        console.print("2. Se as credenciais estão corretas")
        console.print("3. Se as tabelas 'contratacoes' e 'contratacoes_embeddings' existem")
        console.print("Encerrando.[/bold red]")
        return
    
    console.print("[green]✓ Conexão com banco de dados estabelecida com sucesso![/green]")
    
    # Loop principal
    while True:
        display_menu()
        
        # Solicitar entrada do usuário
        query = input("\n> ").strip()
        
        # Verificar opções especiais
        if query == "1":
            # Alterar tipo de busca
            current_search_type = select_search_type()
            continue
            
        elif query == "2":
            # Alterar modo de ordenação
            current_sort_mode = select_sort_mode()
            # Se houver resultados, reexibir com a nova ordenação
            if last_results:
                display_results(last_results, 0, last_query, current_search_type)
            continue
            
        elif query == "3":
            # Alternar filtro de contratações encerradas
            toggle_filter()
            # Se houver resultados, reexibir com o novo filtro
            if last_results:
                display_results(last_results, 0, last_query, current_search_type)
            continue
        
        elif query == "4":
            # V6: Configurações do sistema
            configure_system()
            continue
        
        # Se há resultados, usar numeração ajustada
        elif last_results:
            if query == "5":
                # Exportar resultados
                export_results(last_results, last_query, current_search_type)
                continue
            
            elif query == "6":
                # Ver documentos de um processo específico
                console.print(f"\n[yellow]Processos disponíveis: 1 a {len(last_results)}[/yellow]")
                process_choice = input("Digite o número do processo: ").strip()
                try:
                    process_num = int(process_choice)
                    show_process_documents(process_num)
                except ValueError:
                    console.print("[red]Digite apenas números![/red]")
                continue
                
            elif query == "7":
                # Gerar palavras-chave de um processo específico
                console.print(f"\n[yellow]Processos disponíveis: 1 a {len(last_results)}[/yellow]")
                process_choice = input("Digite o número do processo: ").strip()
                try:
                    process_num = int(process_choice)
                    generate_process_keywords(process_num)
                except ValueError:
                    console.print("[red]Digite apenas números![/red]")
                continue
                
            elif query == "8":
                # Sair do programa
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo V6![/bold green]")
                return
        
        # Se NÃO há resultados, usar numeração simplificada
        else:
            if query == "5":
                # Sair do programa
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo V6![/bold green]")
                return
        
        # Verificar consulta vazia
        if not query:
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
            
        # Se chegou aqui, realizar busca normal
        perform_search(query, current_search_type)
        
if __name__ == "__main__":
    main()
