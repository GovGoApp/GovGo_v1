"""
GvG_SP_Search_Terminal_v5.py
Sistema Avançado de Busca PNCP - Versão 5.0

Características principais:
• Busca semântica, por palavras-chave e híbrida em contratos públicos
• Integração completa com banco Supabase para dados do PNCP
• Interface terminal interativa com Rich para visualização aprimorada
• Exportação de resultados em Excel e PDF formatado
• Análise de documentos com sumarização automática via IA
• Geração inteligente de palavras-chave usando OpenAI GPT
• Sistema de filtros e ordenação personalizável
• Links diretos para documentos oficiais do PNCP
• Menu contextual que adapta opções conforme disponibilidade de resultados

Funcionalidades avançadas V5:
- Categorização automática individual de cada resultado
- Análise da TOP 1 categoria mais similar para cada descrição
- Configuração flexível de ativação via menu
- Busca semântica em categorias para consultas
- Exibição da categoria nos detalhes de cada resultado

Funcionalidades avançadas V4:
- Pré-processamento inteligente de consultas
- Cálculo automático de índices de confiança
- Formatação monetária e de datas
- Controle de expiração de contratos
- Interface responsiva com feedback visual em tempo real
"""

import os
import sys
import pandas as pd
import time
import locale
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table  # Importação original do Rich
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

# Importações adicionais para categorização (V5)
import numpy as np
import json
import math
from sqlalchemy import create_engine
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
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

# Variáveis para ordenação e filtro
SORT_MODES = {
    1: {"name": "Similaridade", "description": "Ordenar por relevância (decrescente)"},
    2: {"name": "Data de Encerramento", "description": "Ordenar por data (ascendente)"},
    3: {"name": "Valor Estimado", "description": "Ordenar por valor (decrescente)"}
}


# Variáveis para armazenar estado global
last_results = None
last_query = None

current_search_type = 1  # Tipo de busca padrão: Semântica
current_sort_mode = 3  # Modo de ordenação padrão: Similaridade
filter_expired = True  # Filtro para ocultar contratações encerradas

# Configurações para categorização automática (V5)
categorization_enabled = True  # Categorização ativada por padrão
num_categories = 5  # Número padrão de categorias para mostrar (TOP X)


# ====================================================================================
# FUNÇÕES DE CATEGORIZAÇÃO AUTOMÁTICA (V5)
# ====================================================================================

def create_engine_connection():
    """Cria engine SQLAlchemy usando as mesmas credenciais do gvg_search_utils"""
    try:
        # Carregar variáveis de ambiente
        load_dotenv('supabase_v0.env')
        
        # Configurações do banco
        db_config = {
            'host': os.getenv('host'),
            'database': os.getenv('dbname'),
            'user': os.getenv('user'),
            'password': os.getenv('password'),
            'port': os.getenv('port')
        }
        
        # Criar connection string
        connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        
        # Criar engine
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        console.print(f"[red]Erro ao criar engine SQLAlchemy: {e}[/red]")
        return None

def parse_embedding(embedding_str):
    """
    Converte string de embedding para array numpy.
    
    Args:
        embedding_str: String do embedding (pode ser JSON ou array)
    
    Returns:
        Array numpy do embedding
    """
    try:
        if isinstance(embedding_str, str):
            # Tenta fazer parse como JSON
            embedding = json.loads(embedding_str)
        else:
            embedding = embedding_str
        
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        console.print(f"[red]Erro ao converter embedding: {e}[/red]")
        return None

def semantic_categorization_search(query_embedding, top_k=5):
    """
    Realiza busca semântica de categorias usando embedding da consulta.
    
    Args:
        query_embedding: Embedding da consulta (array numpy)
        top_k: Número de categorias top a retornar
        
    Returns:
        Lista de dicionários com as top categorias e suas similaridades
    """
    try:
        # Criar engine
        engine = create_engine_connection()
        if not engine:
            return []
        
        # Converte embedding para lista para usar na query
        query_embedding_list = query_embedding.tolist()
        
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
                'limit': top_k
            }
        )
        
        # Formata os resultados
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
        console.print(f"[red]Erro ao realizar busca semântica de categorias: {e}[/red]")
        return []

def categorize_query(query):
    """
    Categoriza uma consulta mostrando as TOP X categorias mais similares.
    
    Args:
        query: Texto da consulta
        
    Returns:
        Lista de categorias ou None se erro
    """
    try:
        # Gerar embedding da consulta usando gvg_search_utils
        query_embedding = get_embedding(query)
        if query_embedding is None:
            console.print("[yellow]Não foi possível gerar embedding da consulta.[/yellow]")
            return None
        
        # Converter para numpy array se necessário
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding, dtype=np.float32)
        
        # Buscar categorias similares
        categories = semantic_categorization_search(query_embedding, top_k=5)
        
        if not categories:
            console.print("[yellow]Nenhuma categoria encontrada para a consulta.[/yellow]")
            return None
        
        return categories
        
    except Exception as e:
        console.print(f"[red]Erro ao categorizar consulta: {e}[/red]")
        return None

def categorize_individual_result(description):
    """
    Categoriza uma descrição individual e retorna a TOP 1 categoria.
    
    Args:
        description: Texto da descrição
        
    Returns:
        Dicionário com a categoria ou None se erro
    """
    try:
        if not description or not description.strip():
            return None
        
        # Gerar embedding da descrição
        desc_embedding = get_embedding(description)
        if desc_embedding is None:
            return None
        
        # Converter para numpy array se necessário
        if isinstance(desc_embedding, list):
            desc_embedding = np.array(desc_embedding, dtype=np.float32)
        
        # Buscar TOP 1 categoria similar
        categories = semantic_categorization_search(desc_embedding, top_k=1)
        
        if categories:
            return categories[0]  # Retorna apenas a primeira (TOP 1)
        
        return None
        
    except Exception as e:
        return None

def categorize_results(results):
    """
    Categoriza cada resultado individualmente, adicionando a TOP 1 categoria aos detalhes.
    
    Args:
        results: Lista de resultados da busca
        
    Returns:
        None (modifica os resultados in-place)
    """
    try:
        if not results:
            return None
        
        # Categorizar cada resultado individualmente
        for result in results:
            details = result.get("details", {})
            if details:
                desc = details.get("descricaocompleta", "")
                if desc and desc.strip():
                    # Categorizar esta descrição específica
                    top_category = categorize_individual_result(desc)
                    if top_category:
                        # Adicionar categoria aos detalhes do resultado
                        result["top_category"] = top_category
                    else:
                        result["top_category"] = None
                else:
                    result["top_category"] = None
            else:
                result["top_category"] = None
        
        return True
        
    except Exception as e:
        console.print(f"[red]Erro ao categorizar resultados: {e}[/red]")
        return None

# ====================================================================================
# FIM DAS FUNÇÕES DE CATEGORIZAÇÃO AUTOMÁTICA (V5)
# ====================================================================================


def highlight_key_terms(text, query_terms, max_length=500):
    """Destaca termos da consulta no texto e limita o comprimento."""
    if not text:
        return "N/A"
        
    # Limitar comprimento se for muito longo
    if len(text) > max_length:
        text = text[:max_length] + "..."
        
    # Substituir :: por quebras de linha para melhorar legibilidade
    text = text.replace(" :: ", "\n• ")
    if not text.startswith("•"):
        text = "• " + text
        
    return text

def display_results(results, confidence, query, search_type_id):
    """Exibe os resultados da busca em formato detalhado"""
    if not results:
        console.print("\n[bold yellow]Nenhum resultado encontrado para esta consulta.[/bold yellow]")
        return
    
    # Apenas indicar se o filtro está ativo ou não
    if filter_expired:
        filter_message = "[yellow]Filtro ativo: mostrando apenas contratações não encerradas[/yellow]"
    else:
        filter_message = "[dim]Filtro inativo: mostrando todas as contratações[/dim]"
    
    # Aplicar ordenação conforme modo selecionado
    if current_sort_mode == 1:  # Por similaridade (padrão)
        # Já está ordenado por similaridade
        sort_message = "[dim]Ordenação: por similaridade (decrescente)[/dim]"
    elif current_sort_mode == 2:  # Por data de encerramento
        # Ordenar por data de encerramento (ascendente)
        results.sort(key=lambda x: x.get("details", {}).get("dataencerramentoproposta", "9999-12-31"))
        sort_message = "[dim]Ordenação: por data de encerramento (ascendente)[/dim]"
    elif current_sort_mode == 3:  # Por valor estimado
        # Ordenar por valor estimado (decrescente)
        results.sort(key=lambda x: float(x.get("details", {}).get("valortotalestimado", 0) or 0), reverse=True)
        sort_message = "[dim]Ordenação: por valor estimado (decrescente)[/dim]"
    
    # Atualizar ranks após ordenação
    for i, result in enumerate(results, 1):
        result["rank"] = i
    
    if not results:
        console.print("\n[bold yellow]Nenhum resultado encontrado após aplicar filtros.[/bold yellow]")
        return
    
    search_type_name = SEARCH_TYPES[search_type_id]["name"]
    
    console.print(f"\n[bold green]Resultados para a consulta: [italic]\"{query}\"[/italic][/bold green]")
    console.print(f"[bold cyan]Tipo de busca: {search_type_name}[/bold cyan]")
    console.print(f"[bold cyan]Índice de confiança: {confidence:.2f}%[/bold cyan]")
    console.print(sort_message)
    console.print(filter_message)
    console.print()
    
    # Primeiro, mostrar uma tabela resumida
    table = Table(title="Resumo dos Resultados", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6, justify="center")
    table.add_column("Órgão", style="cyan", width=40)  # Nova coluna "Órgão"
    table.add_column("Local", style="cyan", width=30)  # Nova coluna "Local"
    table.add_column("Similaridade", justify="right", width=12)
    table.add_column("Valor (R$)", justify="right", width=17)
    table.add_column("Data Encerramento", width=12)
    
    for result in results:
        details = result.get("details", {})
        
        # Formatar valor usando função de gvg_search_utils
        valor = format_currency(details.get("valortotalestimado", 0)) if details else "N/A"
        
        # Formatar data
        data_encerramento = details.get("dataencerramentoproposta", "N/A") if details else "N/A"
        
        # Preparar informações de órgão e local
        #orgao = f"{details.get('orgaoentidade_razaosocial', 'N/A')[:25]}..." if len(details.get('orgaoentidade_razaosocial', 'N/A')) > 20 else details.get('orgaoentidade_razaosocial', 'N/A')
        unidade = details.get('unidadeorgao_nomeunidade', 'N/A')
        unidade = f"{unidade[:35]}..." if len(unidade) > 35 else unidade
    
        municipio = details.get('unidadeorgao_municipionome', 'N/A')
        uf = details.get('unidadeorgao_ufsigla', '')
        local = f"{municipio}/{uf}" if uf else municipio
        
        table.add_row(
            f"{result['rank']}", 
            #orgao,  # Órgão / Unidade
            unidade,  # Unidade/Órgão
            local,  # Município/UF
            f"{result['similarity']:.4f}",
            valor,
            str(data_encerramento)
        )

    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    
    # Depois, mostrar detalhes de cada resultado
    for result in results:
        details = result.get("details", {})
        
        if not details:
            continue
            
        # Preparar o texto da descrição com destaque
        descricao = highlight_key_terms(
            details.get("descricaocompleta", "N/A"),
            query.split()
        )
        
        # Criar painel com informações detalhadas
        panel_title = f"#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})"
        
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
        
        # Adicionar categoria se disponível
        if "top_category" in result and result["top_category"]:
            cat = result["top_category"]
            category_text = f"{cat['codigo']} - {cat['descricao']} (Similaridade: {cat['similarity_score']:.3f})"
            content.append(f"[bold yellow]🎯 Categoria:[/bold yellow] {category_text}")
        
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
            
            choice = input("> ").strip()
            
            if choice == "0":
                break
            
            try:
                doc_num = int(choice)
                if 1 <= doc_num <= len(documentos):
                    doc = documentos[doc_num - 1]
                    doc_url = doc.get('url')
                    doc_title = doc.get('titulo', 'Documento')
                    
                    if doc_url:
                        console.print(f"\n[bold green]Sumarizando: {doc_title}[/bold green]")
                        console.print(f"[dim]URL: {doc_url}[/dim]")
                        
                        with console.status("[bold green]Gerando resumo..."):
                            summary = summarize_document(doc_url)
                        
                        # Exibir resumo em painel
                        panel = Panel(
                            summary,
                            title=f"Resumo: {doc_title}",
                            border_style="green"
                        )
                        console.print(panel)
                    else:
                        console.print("[red]URL do documento não disponível.[/red]")
                else:
                    console.print("[red]Número inválido![/red]")
            except ValueError:
                console.print("[red]Digite apenas números![/red]")
    
    except Exception as e:
        console.print(f"[red]Erro ao buscar documentos: {str(e)}[/red]")

def generate_process_keywords(process_number):
    """Gera palavras-chave da descrição de um processo específico"""
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
    
    # Se não encontrou nos details, tentar no result principal
    if not numero_controle and 'id' in result and result['id']:
        numero_controle = result['id']
    
    if not numero_controle:
        numero_controle = 'N/A'
    
    descricao = details.get('descricaocompleta', '')
    
    if not descricao or descricao.strip() == '':
        console.print("[yellow]Descrição não disponível para gerar palavras-chave.[/yellow]")
        return
    
    console.print(f"\n[bold green]Gerando palavras-chave para: {numero_controle}[/bold green]")
    
    try:
        with console.status("[bold green]Gerando palavras-chave..."):
            keywords = generate_keywords(descricao)
        
        # Exibir palavras-chave em painel
        panel_content = f"""
[bold cyan]Processo:[/bold cyan] {numero_controle}

[bold yellow]Descrição Original:[/bold yellow]
{descricao[:300]}{'...' if len(descricao) > 300 else ''}

[bold green]Palavras-chave Geradas:[/bold green]
{keywords}
        """
        
        panel = Panel(
            panel_content,
            title="Palavras-chave do Processo",
            border_style="green"
        )
        console.print(panel)
    
    except Exception as e:
        console.print(f"[red]Erro ao gerar palavras-chave: {str(e)}[/red]")

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
                    "Data Abertura": details.get("dataaberturaproposta", "N/A"),
                    "Data Encerramento": details.get("dataencerramentoproposta", "N/A"),
                    "Descrição": details.get("descricaocompleta", "N/A")
                }
                
                # Adicionar scores específicos para busca híbrida
                if "semantic_score" in result and "keyword_score" in result:
                    result_data["Score Semântico"] = result["semantic_score"]
                    result_data["Score Palavra-chave"] = result["keyword_score"]
                
                data.append(result_data)
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Gerar nome do arquivo baseado na data e hora
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
    """Exporta os resultados da busca para um arquivo PDF formatado como no terminal."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return False
    
    try:
        # Gerar nome do arquivo baseado na data e hora
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
        elements.append(Paragraph(f"BUSCA: \"{query.upper()}\"", title_style))
        
        # Informações da busca
        elements.append(Paragraph(f"Tipo de busca: {SEARCH_TYPES[search_type_id]['name']}", normal_style))
        elements.append(Paragraph(f"Ordenação: {SORT_MODES[current_sort_mode]['name']}", normal_style))
        elements.append(Paragraph(f"Data da pesquisa: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Tabela resumida com margem e fonte menor
        table_data = [
            ["Rank", "Unidade", "Local", "Similaridade", "Valor (R$)", "Data Proposta"]
        ]
        
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
            
            table_data.append([
                str(result['rank']),
                unidade,
                local,
                f"{result['similarity']:.4f}",
                valor,
                str(data_encerramento)
            ])
        
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

def select_search_type():
    """Permite ao usuário selecionar o tipo de busca"""
    console.print("\n[bold magenta]Tipos de Busca Disponíveis[/bold magenta]")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Tipo", style="green")
    table.add_column("Descrição", style="magenta")
    
    for id, search_type in SEARCH_TYPES.items():
        table.add_row(
            str(id),
            search_type["name"],
            search_type["description"]
        )
    
    console.print(table)
    
    choice = Prompt.ask(
        "\nSelecione o tipo de busca",
        choices=["1", "2", "3"],
        default="1"
    )
    
    return int(choice)

def select_sort_mode():
    """Permite ao usuário selecionar o modo de ordenação"""
    console.print("\n[bold magenta]Modos de Ordenação Disponíveis[/bold magenta]")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Modo", style="green")
    table.add_column("Descrição", style="magenta")
    
    for id, sort_mode in SORT_MODES.items():
        table.add_row(
            str(id),
            sort_mode["name"],
            sort_mode["description"]
        )
    
    console.print(table)
    
    choice = Prompt.ask(
        "\nSelecione o modo de ordenação",
        choices=["1", "2", "3"],
        default="1"
    )
    
    return int(choice)

def toggle_filter():
    """Alterna o filtro de contratações encerradas"""
    global filter_expired
    filter_expired = not filter_expired
    status = "ATIVADO" if filter_expired else "DESATIVADO"
    console.print(f"\n[bold {'green' if filter_expired else 'yellow'}]Filtro de contratações encerradas: {status}[/bold {'green' if filter_expired else 'yellow'}]")
    if filter_expired:
        console.print("[green]Mostrando apenas contratações com data de encerramento >= data atual[/green]")
    else:
        console.print("[yellow]Mostrando todas as contratações, independente da data de encerramento[/yellow]")

def configure_categorization():
    """Configura as opções de categorização automática"""
    global categorization_enabled
    
    console.print("\n[bold magenta]Configuração de Categorização Automática[/bold magenta]")
    console.print(f"[bold cyan]Status atual:[/bold cyan] {'ATIVADA' if categorization_enabled else 'DESATIVADA'}")
    console.print("\n[dim]A categorização mostrará a TOP 1 categoria mais similar para cada resultado individual.[/dim]")
    console.print()
    
    # Pergunta se quer ativar/desativar
    current_status = "s" if categorization_enabled else "n"
    enable_choice = Prompt.ask(
        "Ativar categorização automática? (s/n)",
        choices=["s", "n"],
        default=current_status
    )
    
    categorization_enabled = enable_choice == "s"
    
    # Mostrar configuração final
    status = "ATIVADA" if categorization_enabled else "DESATIVADA"
    console.print(f"\n[bold green]Categorização automática: {status}[/bold green]")
    if categorization_enabled:
        console.print(f"[bold green]Cada resultado mostrará sua categoria mais similar[/bold green]")

def perform_search(query, search_type_id):
    """Realiza a busca de acordo com o tipo selecionado usando funções de gvg_search_utils"""
    global last_results, last_query, current_search_type
    
    # Pré-processar a consulta antes da busca
    original_query = query  # Guardar consulta original
    processed_query = gvg_pre_processing(
        query, 
        remove_special_chars=DEFAULT_PREPROC_PARAMS["remove_special_chars"],
        keep_separators=DEFAULT_PREPROC_PARAMS["keep_separators"],
        remove_accents=DEFAULT_PREPROC_PARAMS["remove_accents"],
        case=DEFAULT_PREPROC_PARAMS["case"],
        remove_stopwords=DEFAULT_PREPROC_PARAMS["remove_stopwords"],
        lemmatize=DEFAULT_PREPROC_PARAMS["lemmatize"]
    )
    
    console.print(f"[bold blue]Realizando busca {SEARCH_TYPES[search_type_id]['name']} para: \"{original_query}\"[/bold blue]")
    console.print(f"[dim]Consulta pré-processada: \"{processed_query}\"[/dim]")
    
    # V5: Categorização automática da consulta (ANTES da busca)
    if categorization_enabled:
        console.print(f"\n[bold yellow]🎯 Analisando TOP 5 categorias da consulta...[/bold yellow]")
        
        with console.status("[bold yellow]Categorizando consulta..."):
            query_categories = categorize_query(original_query)
        
        if query_categories:
            console.print(f"[green]✓ Consulta categorizada! TOP 5 categorias:[/green]")
            for i, cat in enumerate(query_categories, 1):
                console.print(f"[cyan]{i}.[/cyan] {cat['codigo']} - {cat['descricao']} (Similaridade: {cat['similarity_score']:.3f})")
        else:
            console.print("[yellow]Não foi possível categorizar a consulta.[/yellow]")
        
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Buscando resultados..."),
        BarColumn(),
        TaskProgressColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Processando", total=1)
        
        try:
            # Usar funções importadas de gvg_search_utils
            if search_type_id == 1:
                # Busca semântica
                results, confidence = semantic_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS, filter_expired=filter_expired)
            elif search_type_id == 2:
                # Busca por palavras-chave
                results, confidence = keyword_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS, filter_expired=filter_expired)
            elif search_type_id == 3:
                # Busca híbrida
                results, confidence = hybrid_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS, semantic_weight=SEMANTIC_WEIGHT, filter_expired=filter_expired)
            else:
                # Tipo inválido, usar semântica por padrão
                results, confidence = semantic_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS, filter_expired=filter_expired)
            
            progress.update(task, advance=1)
            
        except Exception as e:
            console.print(f"[bold red]Erro durante a busca: {str(e)}[/bold red]")
            results, confidence = [], 0.0
    
    end_time = time.time()
    search_time = end_time - start_time
    
    results = [r for r in results if not pd.isna(r.get('similarity', float('nan')))]

    # Armazenar resultados para possível exportação
    last_results = results
    last_query = original_query  # Armazenar a consulta original para referência
    current_search_type = search_type_id
    
    # V5: Se categorização estiver ativada, categorizar cada resultado individualmente (ANTES de exibir)
    if categorization_enabled and results:
        console.print(f"\n[bold yellow]🎯 Categorizando cada resultado individualmente...[/bold yellow]")
        
        with console.status("[bold yellow]Categorizando resultados..."):
            categorization_success = categorize_results(results)
        
        if categorization_success:
            categorized_count = sum(1 for r in results if r.get("top_category"))
            console.print(f"[green]✓ {categorized_count} resultados categorizados com sucesso![/green]")
        else:
            console.print("[yellow]Não foi possível categorizar os resultados.[/yellow]")
    
    # Exibir resultados uma única vez (já com categorias se ativado, sem categorias se desativado)
    display_results(results, confidence, original_query, search_type_id)
    console.print(f"[dim]Tempo de busca: {search_time:.4f} segundos[/dim]")

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
    """Exibe o menu principal"""
    console.print("\n[bold magenta]" + "="*80 + "[/bold magenta]")
    console.print("\n[bold cyan]Digite sua consulta ou escolha uma opção:[/bold cyan]")
    
    # Opções com as escolhas atuais em cyan bold, descrições em texto normal
    console.print(f"[cyan]1[/cyan] - Alterar tipo de busca ([bold cyan]{SEARCH_TYPES[current_search_type]['name']}[/bold cyan])")
    console.print(f"[cyan]2[/cyan] - Alterar modo de ordenação ([bold cyan]{SORT_MODES[current_sort_mode]['name']}[/bold cyan])")
    console.print(f"[cyan]3[/cyan] - Alternar filtro de contratações encerradas ([bold cyan]{'ATIVADO' if filter_expired else 'DESATIVADO'}[/bold cyan])")
    console.print(f"[cyan]4[/cyan] - Configurar categorização automática ([bold cyan]{'ATIVADA' if categorization_enabled else 'DESATIVADA'}[/bold cyan])")
    
    # Só mostrar opções dependentes de resultados SE houver resultados
    if last_results:
        console.print("[cyan]5[/cyan] - Exportar últimos resultados")
        console.print("[cyan]6[/cyan] - Ver documentos de um processo específico")
        console.print("[cyan]7[/cyan] - Gerar palavras-chave de um processo específico")
        console.print("[cyan]8[/cyan] - Encerrar o programa")
        console.print(f"\n[dim]Última busca: \"{last_query}\" - {len(last_results)} resultados encontrados[/dim]")
    else:
        console.print("[cyan]5[/cyan] - Encerrar o programa")
        console.print("\n[dim]Nenhuma busca realizada ainda[/dim]")
    
    console.print("\n[cyan]Digite qualquer outro texto para realizar uma nova busca[/cyan]")


def main():
    """Função principal do programa"""
    global current_search_type, current_sort_mode, filter_expired
    
    console.print(Panel(
        "[bold cyan]Conecta ao Supabase e realiza diferentes tipos de busca[/bold cyan]\n[bold yellow]NOVO: Categorização automática de consultas e resultados![/bold yellow]",
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE v5.0[/bold magenta]",
        subtitle="[bold cyan]Semântica, Palavras-chave, Híbrida + Categorização Inteligente[/bold cyan]",
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
            # V5: Configurar categorização automática
            configure_categorization()
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
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo![/bold green]")
                return
        
        # Se NÃO há resultados, usar numeração simplificada
        else:
            if query == "5":
                # Sair do programa
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo![/bold green]")
                return
        
        # Verificar consulta vazia
        if not query:
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
            
        # Se chegou aqui, realizar busca normal
        perform_search(query, current_search_type)
        
if __name__ == "__main__":
    main()
