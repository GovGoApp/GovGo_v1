"""
GvG_Search_Terminal_v2_optimized.py
Sistema Otimizado de Busca PNCP - Versão 2 Otimizada

🚀 VERSÃO OTIMIZADA - CARACTERÍSTICAS:
• Herda apenas de gvg_utils e gvg_documents (módulos otimizados)
• Importações seletivas - apenas funções realmente utilizadas
• Código limpo sem bloating de funções não utilizadas
• Modularização especializada por funcionalidade
• Performance aprimorada com menos overhead

🎯 FUNCIONALIDADES MANTIDAS:
• Sistema de busca inteligente com 3 tipos (Semântica, Palavras-chave, Híbrida)
• 3 Abordagens de busca (Direta, Correspondência, Filtro) 
• Interface Rica com tabelas e painéis coloridos
• Exportação Excel, PDF e JSON
• Processamento inteligente de queries via IA
• Sistema de configurações completo
• Visualização e processamento de documentos
• Geração de palavras-chave inteligentes

📦 MÓDULOS UTILIZADOS:
• gvg_utils: Módulo unificado com importações seletivas
• gvg_documents: Processamento simplificado de documentos
• Rich: Interface terminal avançada
• Pandas: Manipulação de dados
• ReportLab: Geração de PDF
"""

import json
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
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# ========================================================================================
# IMPORTAÇÕES OTIMIZADAS - APENAS FUNÇÕES UTILIZADAS
# ========================================================================================

try:
    # IMPORTAÇÕES DIRETAS - Eliminando gvg_utils para evitar dependência circular
    # Importações seletivas dos módulos especializados
    from gvg_formatters import (
        format_currency,
        format_date, 
        decode_poder,
        decode_esfera
    )

    from gvg_ai_utils import (
        get_embedding,
        get_negation_embedding,
        extract_pos_neg_terms,
        generate_keywords,
        calculate_confidence
    )

    from gvg_database import (
        create_connection,
        create_engine_connection,
        fetch_documentos
    )

    from gvg_search_core import (
            # Funções principais
            semantic_search,
            keyword_search,
            hybrid_search,
            # Controle inteligente
            toggle_intelligent_processing,
            toggle_intelligent_debug,
            get_intelligent_status,
            # Filtro de relevância real
            set_relevance_filter_level,
            get_relevance_filter_status,
            toggle_relevance_filter_debug
        )

    # Novo módulo de categorias (replica lógica avançada v9)
    from gvg_categories import (
        get_top_categories_for_query,
        correspondence_search as categories_correspondence_search,
        category_filtered_search as categories_category_filtered_search
    )

    from gvg_preprocessing import (
        SearchQueryProcessor,
        process_search_query
    )

    # Importar preprocessor para compatibilidade
    import gvg_preprocessing as preprocessor
    
    UTILS_AVAILABLE = True
    print("✅ Módulos carregados com importações diretas")
    
    from gvg_documents import (
        summarize_document,
        process_pncp_document
    )
    
    DOCUMENTS_AVAILABLE = True
    print("✅ gvg_documents carregado com sucesso")
    
except ImportError as e:
    print(f"⚠️ Módulo de documentos não disponível: {e}")
    print("📄 Processamento de documentos será desativado")
    DOCUMENTS_AVAILABLE = False
    summarize_document = None

# ========================================================================================
# CONFIGURAÇÕES GLOBAIS
# ========================================================================================
# Configurações globais (reexportadas para compatibilidade)
MAX_RESULTS = 30
MIN_RESULTS = 5
MAX_KEYWORDS = 15
SEMANTIC_WEIGHT = 0.75
DEFAULT_FILTER_EXPIRED = True
DEFAULT_USE_NEGATION = True

## Filtro de relevância: usando apenas implementação de gvg_search_core

# Configurar locale para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# Console Rich
console = Console(width=120)

# Configurações de busca (estado global)
current_search_type = 1        # 1=Semântica, 2=Palavras-chave, 3=Híbrida
current_search_approach = 1    # 1=Direta, 2=Correspondência, 3=Filtro  
current_sort_mode = 1          # 1=Similaridade, 2=Data, 3=Valor
max_results = MAX_RESULTS
num_top_categories = 10

# Configurações de sistema
filter_expired = DEFAULT_FILTER_EXPIRED
use_negation_embeddings = DEFAULT_USE_NEGATION
intelligent_processing = True
# REMOVIDO: intelligent_debug local (causava conflito com implementação core).
# O status de debug agora é obtido exclusivamente via get_intelligent_status() do gvg_search_core.

# Resultados da última busca
last_results = []
last_query = ""
last_query_categories = []  # Armazena dicionários completos das categorias

# ========================================================================================
# FUNÇÕES DE CONFIGURAÇÃO SIMPLIFICADAS
# ========================================================================================

## Removido toggle_intelligent_debug local que sobrescrevia a função importada do core.
## Agora usamos diretamente a função importada (mantendo mesma assinatura) para refletir
## corretamente DEBUG_INTELLIGENT_QUERIES em gvg_search_core.

# Removidas versões locais de set/get relevance filter (usar importadas)

# Dicionários de configuração
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada em significado (IA)", "emoji": "🧠"},
    2: {"name": "Palavras-chave", "description": "Busca textual tradicional", "emoji": "🔤"},
    3: {"name": "Híbrida", "description": "Combinação semântica + texto", "emoji": "🔀"}
}

SEARCH_APPROACHES = {
    1: {"name": "Direta", "description": "Busca tradicional no banco", "emoji": "⚡"},
    2: {"name": "Correspondência", "description": "Busca através de categorias", "emoji": "📊"},
    3: {"name": "Filtro", "description": "Filtra por categorias relevantes", "emoji": "🔍"}
}

SORT_MODES = {
    1: {"name": "Similaridade", "description": "Ordenar por relevância", "emoji": "🎯"},
    2: {"name": "Data", "description": "Ordenar por data de encerramento", "emoji": "📅"},
    3: {"name": "Valor", "description": "Ordenar por valor do contrato", "emoji": "💰"}
}

RELEVANCE_LEVELS = {
    1: {"name": "Sem filtro", "description": "Todos os resultados", "emoji": "📄"},
    2: {"name": "Flexível", "description": "Filtro suave de relevância", "emoji": "🟡"},
    3: {"name": "Restritivo", "description": "Filtro rigoroso", "emoji": "🔴"}
}

# Configurações de exportação
BASE_PATH = os.getcwd()
RESULTS_PATH = os.path.join(BASE_PATH, "Resultados_Busca")
FILES_PATH = os.path.join(BASE_PATH, "Files")

# Criar diretórios se não existirem
os.makedirs(RESULTS_PATH, exist_ok=True)
os.makedirs(FILES_PATH, exist_ok=True)

# ========================================================================================
# FUNÇÕES DE INTERFACE
# ========================================================================================

def display_header():
    """Exibe cabeçalho do sistema"""
    header_text = """
[bold cyan]🚀 GvG Search Terminal v2 - VERSÃO OTIMIZADA[/bold cyan]
[yellow]Sistema Avançado de Busca PNCP com IA[/yellow]

[green]✨ Recursos Otimizados:[/green]
• Módulos especializados por funcionalidade
• Importações seletivas (apenas funções utilizadas)  
• Performance aprimorada com menos overhead
• 3 Tipos de Busca + 3 Abordagens + Sistema Inteligente
"""
    
    console.print(Panel(header_text, border_style="blue", padding=(1, 2)))

def display_menu():
    """Exibe o menu principal no formato estilo v9 (lista textual com indicadores)."""
    intelligent_status = get_intelligent_status()
    relevance_status = get_relevance_filter_status()

    search_info = SEARCH_TYPES[current_search_type]
    approach_info = SEARCH_APPROACHES[current_search_approach]
    sort_info = SORT_MODES[current_sort_mode]
    relevance_info = RELEVANCE_LEVELS[relevance_status['level']]

    console.print("\n" + "=" * 80)
    console.print("[bold cyan]MENU DE OPÇÕES[/bold cyan]")
    console.print(f"1. Tipo de busca: [bold]{search_info['name']}[/bold] ({search_info['description']})")
    console.print(f"2. Abordagem: [bold]{approach_info['name']}[/bold] ({approach_info['description']})")
    console.print(f"3. Relevância: [bold]{relevance_info['name']}[/bold] ({relevance_info['description']})")
    console.print(f"4. Ordenação: [bold]{sort_info['name']}[/bold] ({sort_info['description']})")
    console.print(f"5. Configurações do sistema")

    if last_results:
        console.print(f"6. Processar documentos (Resultados: {len(last_results)})")
        console.print("7. Gerar palavras-chave")
        console.print("8. Exportar resultados")
    else:
        console.print("[dim]6. Processar documentos (indisponível sem resultados)\n7. Gerar palavras-chave (indisponível)\n8. Exportar resultados (indisponível)[/dim]")

    console.print("-" * 80)
    console.print("Digite um número para mudar configuração ou digite sua consulta.")
    console.print("[dim]Comandos: quit / exit / q para sair[/dim]")

def select_search_type():
    """Seleciona tipo de busca (formato lista estilo v9)."""
    global current_search_type
    console.print("\n[bold yellow]🔍 Tipos de Busca Disponíveis:[/bold yellow]")
    for key, value in SEARCH_TYPES.items():
        indicator = "👉" if key == current_search_type else "  "
        console.print(f"{indicator} {key}. {value['name']} - {value['description']}")
    choice = Prompt.ask("\nEscolha o tipo de busca", choices=[str(i) for i in SEARCH_TYPES.keys()], default=str(current_search_type))
    current_search_type = int(choice)
    console.print(f"[green]✓ Tipo de busca alterado para: {SEARCH_TYPES[current_search_type]['name']}[/green]")

def select_search_approach():
    """Seleciona abordagem de busca (formato lista estilo v9)."""
    global current_search_approach
    console.print("\n[bold yellow]📊 Abordagens de Busca Disponíveis:[/bold yellow]")
    for key, value in SEARCH_APPROACHES.items():
        indicator = "👉" if key == current_search_approach else "  "
        console.print(f"{indicator} {key}. {value['name']} - {value['description']}")
    choice = Prompt.ask("\nEscolha a abordagem de busca", choices=[str(i) for i in SEARCH_APPROACHES.keys()], default=str(current_search_approach))
    current_search_approach = int(choice)
    console.print(f"[green]✓ Abordagem alterada para: {SEARCH_APPROACHES[current_search_approach]['name']}[/green]")

def select_relevance_level():
    """Seleciona nível de relevância (formato lista estilo v9)."""
    current_level = get_relevance_filter_status()['level']
    console.print("\n[bold yellow]🎯 Níveis de Relevância Disponíveis:[/bold yellow]")
    for key, value in RELEVANCE_LEVELS.items():
        indicator = "👉" if key == current_level else "  "
        console.print(f"{indicator} {key}. {value['name']} - {value['description']}")
    choice = Prompt.ask("\nEscolha o nível de relevância", choices=[str(i) for i in RELEVANCE_LEVELS.keys()], default=str(current_level))
    set_relevance_filter_level(int(choice))
    console.print(f"[green]✓ Nível de relevância alterado para: {RELEVANCE_LEVELS[int(choice)]['name']}[/green]")

def select_sort_mode():
    """Seleciona modo de ordenação (formato lista estilo v9)."""
    global current_sort_mode
    console.print("\n[bold yellow]🗂️ Modos de Ordenação Disponíveis:[/bold yellow]")
    for key, value in SORT_MODES.items():
        indicator = "👉" if key == current_sort_mode else "  "
        console.print(f"{indicator} {key}. {value['name']} - {value['description']}")
    choice = Prompt.ask("\nEscolha o modo de ordenação", choices=[str(i) for i in SORT_MODES.keys()], default=str(current_sort_mode))
    current_sort_mode = int(choice)
    console.print(f"[green]✓ Ordenação alterada para: {SORT_MODES[current_sort_mode]['name']}[/green]")

def configure_system():
    """Menu de configurações do sistema"""
    while True:
        console.print("\n[bold cyan]⚙️ CONFIGURAÇÕES DO SISTEMA[/bold cyan]")
        # Status atual
        intelligent_status = get_intelligent_status()
        doc_status = {'version': 'Docling v3' if DOCUMENTS_AVAILABLE else 'indisponível'}

        config_text = f"""
[yellow]📊 STATUS ATUAL:[/yellow]
• Máximo de resultados: {max_results}
• TOP categorias: {num_top_categories}
• Processador documentos: {doc_status['version']}
• Filtrar expirados: {'🟢 Ativo' if filter_expired else '🔴 Inativo'}
• Negation embeddings: {'🟢 Ativo' if use_negation_embeddings else '🔴 Inativo'}
• Processamento IA: {'🟢 Ativo' if intelligent_status['intelligent_processing'] else '🔴 Inativo'}
• Debug IA: {'🟢 Ativo' if intelligent_status['debug_mode'] else '🔴 Inativo'}

[green]📋 OPÇÕES:[/green]
[bold]1[/bold] - Alterar max resultados    [bold]2[/bold] - Alterar TOP categorias
[bold]3[/bold] - Toggle processador docs  [bold]4[/bold] - Toggle filtro expirados
[bold]5[/bold] - Toggle negation          [bold]6[/bold] - Toggle IA
[bold]7[/bold] - Toggle debug IA          [bold]8[/bold] - Voltar menu principal
"""
        
        console.print(Panel(config_text, border_style="yellow"))
        
        choice = Prompt.ask("Escolha uma opção", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="8")
        
        if choice == "1":
            new_max = Prompt.ask("Novo máximo de resultados (5-100)", default=str(max_results))
            try:
                new_max = int(new_max)
                if 5 <= new_max <= 100:
                    globals()['max_results'] = new_max
                    console.print(f"✅ Máximo de resultados alterado para {new_max}")
                else:
                    console.print("❌ Valor deve estar entre 5 e 100")
            except ValueError:
                console.print("❌ Valor inválido")
                
        elif choice == "2":
            new_cats = Prompt.ask("Novo número de TOP categorias (5-50)", default=str(num_top_categories))
            try:
                new_cats = int(new_cats)
                if 5 <= new_cats <= 50:
                    globals()['num_top_categories'] = new_cats
                    console.print(f"✅ TOP categorias alterado para {new_cats}")
                else:
                    console.print("❌ Valor deve estar entre 5 e 50")
            except ValueError:
                console.print("❌ Valor inválido")
                
        elif choice == "3":
            console.print("ℹ️ Processador fixo: Docling v3 (sem alternância nesta versão)")
                
        elif choice == "4":
            globals()['filter_expired'] = not filter_expired
            status = "ativado" if filter_expired else "desativado"
            console.print(f"✅ Filtro de expirados {status}")
            
        elif choice == "5":
            globals()['use_negation_embeddings'] = not use_negation_embeddings
            status = "ativado" if use_negation_embeddings else "desativado"
            console.print(f"✅ Negation embeddings {status}")
            
        elif choice == "6":
                toggle_intelligent_processing(not intelligent_status['intelligent_processing'])
                intelligent_status = get_intelligent_status()
            
        elif choice == "7":
                toggle_intelligent_debug(not intelligent_status['debug_mode'])
                intelligent_status = get_intelligent_status()
            
        elif choice == "8":
            break

# ========================================================================================
# FUNÇÕES DE BUSCA (OTIMIZADAS)
# ========================================================================================

def perform_search(query: str):
    """Executa busca replicando fluxo v9 (categorias para abordagens 2 e 3)."""
    global last_results, last_query, last_query_categories

    console.print(f"\n[bold cyan]🔍 Executando Busca:[/bold cyan] [yellow]{query}[/yellow]")
    start_time = time.time()

    try:
        # Pré-processamento inteligente já ocorre nas funções core; aqui apenas fluxo de categorias
        # 1. Extrair termos positivos/negativos iniciais
        pos_terms, neg_terms = extract_pos_neg_terms(query) if use_negation_embeddings else (query, "")

        # 2. Usar processador inteligente (se ativo) para obter termos-base sem condicionantes (regionais, valores, etc.)
        base_category_terms = pos_terms
        if intelligent_processing and 'SearchQueryProcessor' in globals():
            try:
                processor = SearchQueryProcessor()
                processed = processor.process_query(query)
                processed_terms = processed.get('search_terms') or ''
                if processed_terms:
                    # Reaplicar extração de positivos sobre os termos processados (removendo negativos/condicionantes restantes)
                    cat_pos, _cat_neg = extract_pos_neg_terms(processed_terms) if use_negation_embeddings else (processed_terms, '')
                    if cat_pos and cat_pos.strip():
                        base_category_terms = cat_pos.strip()
            except Exception:
                pass  # fallback silencioso

        categories = []
        if current_search_approach in (2, 3):
            console.print(f"[blue]Buscando TOP {num_top_categories} categorias (termos-base: '{base_category_terms}')...[/blue]")
            categories = get_top_categories_for_query(
                query_text=base_category_terms or query,
                top_n=num_top_categories,
                use_negation=False,  # sempre positivo
                search_type=current_search_type,
                console=console
            )
            last_query_categories = categories
            if categories:
                _display_top_categories_table(categories)
            else:
                console.print("[yellow]Nenhuma categoria encontrada. Prosseguindo sem categorias.[/yellow]")

        # Execução conforme abordagem
        if current_search_approach == 1:
            results, confidence = direct_search(query)
        elif current_search_approach == 2:
            results, confidence, _meta = correspondence_search(query, categories)
        elif current_search_approach == 3:
            results, confidence, _meta = category_filtered_search(query, categories)
        else:
            console.print("❌ Abordagem de busca inválida")
            return

        # Ordenação pós-processamento (similaridade já principal)
        if results:
            results = apply_sort_mode(results)
        last_results = results
        last_query = query

        elapsed = time.time() - start_time
        if results:
            console.print(f"\n✅ Busca concluída em {elapsed:.2f}s")
            console.print(f"📊 Encontrados: [bold green]{len(results)}[/bold green] contratos")
            console.print(f"🎯 Confiança média: [bold yellow]{confidence:.1f}%[/bold yellow]")
            display_results(results, query)
        else:
            console.print(f"\n❌ Nenhum resultado encontrado para: [red]{query}[/red]")
            console.print("💡 Tente:")
            console.print("  • Termos mais específicos ou mais gerais")
            console.print("  • Verificar ortografia")
            console.print("  • Usar sinônimos")
            console.print("  • Alterar tipo ou abordagem de busca")
    except Exception as e:
        console.print(f"❌ Erro na busca: {e}")
        console.print("🔧 Verifique conexão com banco e configurações")

def direct_search(query):
    """Busca direta no banco"""
    if current_search_type == 1:
        return semantic_search(query, limit=max_results, filter_expired=filter_expired, use_negation=use_negation_embeddings)
    elif current_search_type == 2:
        return keyword_search(query, limit=max_results, filter_expired=filter_expired)
    elif current_search_type == 3:
        return hybrid_search(query, limit=max_results, filter_expired=filter_expired, use_negation=use_negation_embeddings)

def correspondence_search(query: str, categories: list):
    """Busca por correspondência categórica (usa módulo de categorias)."""
    if not categories:
        return [], 0.0, {}
    console.print("📊 Executando busca por correspondência categórica...")
    results, confidence, meta = categories_correspondence_search(
        query_text=query,
        top_categories=categories,
        limit=max_results,
        filter_expired=filter_expired,
        console=console
    )
    return results, confidence, meta

def category_filtered_search(query: str, categories: list):
    """Busca com filtro categórico (replica estratégia v9)."""
    if not categories:
        return [], 0.0, {}
    console.print("🔍 Executando busca com filtro categórico...")
    results, confidence, meta = categories_category_filtered_search(
        query_text=query,
        search_type=current_search_type,
        top_categories=categories,
        limit=max_results,
        filter_expired=filter_expired,
        use_negation=use_negation_embeddings,
        console=console
    )
    if meta.get('universe_size'):
        console.print(f"[green]Universo expandido: {meta['universe_size']} resultados[/green]")
        console.print(f"[green]Com categorias: {meta['universe_with_categories']}[/green]")
        console.print(f"[green]Após filtro: {meta['filtered_count']}[/green]")
    return results, confidence, meta

def _display_top_categories_table(categories: list):
    """Exibe tabela Rich para TOP categorias (estilo v9)."""
    if not categories:
        return
    table = Table(title="🎯 TOP Categorias da Query", title_style="bold magenta")
    table.add_column("Rank", style="bold cyan", width=6)
    table.add_column("Código", style="bold yellow", width=12)
    table.add_column("Descrição", style="bold green", width=60)
    table.add_column("Similaridade", style="bold blue", width=12)
    for cat in categories:
        sim = cat.get('similarity_score', 0.0)
        color = "bright_green" if sim > 0.8 else ("yellow" if sim > 0.6 else "white")
        table.add_row(str(cat.get('rank')), cat.get('codigo',''), cat.get('descricao','')[:58], f"[{color}]{sim:.4f}[/{color}]")
    console.print(table)
    console.print()

def apply_sort_mode(results):
    """Aplica ordenação conforme modo selecionado"""
    if not results:
        return results
    
    if current_sort_mode == 1:
        # Ordenar por similaridade (padrão)
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
    elif current_sort_mode == 2:
        # Ordenar por data
        return sorted(results, key=lambda x: x.get('details', {}).get('dataassinatura', ''), reverse=True)
    elif current_sort_mode == 3:
        # Ordenar por valor
        return sorted(results, key=lambda x: x.get('details', {}).get('valorfinal', 0) or 0, reverse=True)
    
    return results

# ========================================================================================
# EXIBIÇÃO DE RESULTADOS (OTIMIZADA)
# ========================================================================================

def display_results(results, query):
    """Exibe os resultados no formato da versão v9 (tabela + painéis detalhados)."""
    if not results:
        console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
        return

    # Detectar parâmetros de contexto (usar variáveis globais existentes)
    search_type = globals().get('current_search_type', 1)
    search_approach = globals().get('current_search_approach', 1)
    intelligent_status = get_intelligent_status()

    console.print(f"\n[bold green]Resultados encontrados: {len(results)}[/bold green]")
    # Tempo não está sendo passado aqui (mantemos compatibilidade mínima)
    console.print(f"[blue]Tipo de busca: {SEARCH_TYPES[search_type]['name']}[/blue]")
    console.print(f"[blue]Abordagem: {SEARCH_APPROACHES[search_approach]['name']}[/blue]")
    console.print(f"[blue]Ordenação: {SORT_MODES[current_sort_mode]['name']}[/blue]")
    console.print(f"[blue]Termos destacados: [bold cyan]{query}[/bold cyan][/blue]")

    # Informações de processamento inteligente (adaptado v9)
    try:
        if intelligent_status.get('intelligent_processing') and results and 'details' in results[0] and 'intelligent_processing' in results[0]['details']:
            intelligent_info = results[0]['details']['intelligent_processing']
            console.print(f"\n[bold yellow]🤖 PROCESSAMENTO INTELIGENTE:[/bold yellow]")
            console.print(f"[cyan]Original: [dim]'" + intelligent_info.get('original_query', query) + "'[/dim][/cyan]")
            console.print(f"[green]Termos processados: [bold]'" + intelligent_info.get('processed_terms', 'N/A') + "'[/bold][/green]")
            applied_conditions = intelligent_info.get('applied_conditions', 0)
            if applied_conditions > 0:
                console.print(f"[magenta]Condições SQL aplicadas: [bold]{applied_conditions}[/bold][/magenta]")
            explanation = intelligent_info.get('explanation', '')
            if explanation:
                console.print(f"[dim]💡 {explanation}[/dim]")
    except Exception:
        pass

    # Prompt negativo (negation embeddings)
    if globals().get('use_negation_embeddings') and search_type in [1, 3]:
        try:
            pos_terms, neg_terms = extract_pos_neg_terms(query)
            if neg_terms.strip():
                console.print(f"[cyan]🎯 Prompt Negativo ativo: [bold green]↗[/bold green]'" + pos_terms + "'  [bold red]↘[/bold red]'" + neg_terms + "' [/cyan]")
            else:
                console.print(f"[cyan]🎯 Prompt Negativo ativo (sem termos negativos detectados)[/cyan]")
        except Exception:
            console.print(f"[cyan]🎯 Prompt Negativo ativo[/cyan]")

    # Informações específicas por abordagem
    if search_approach == 2 and globals().get('last_query_categories'):
        console.print(f"[magenta]Baseado em {len(last_query_categories)} TOP categorias[/magenta]")
    elif search_approach == 3 and globals().get('last_query_categories'):
        console.print(f"[magenta]Universo filtrado por {len(last_query_categories)} TOP categorias[/magenta]")

    console.print()

    # Tabela resumo (igual v9)
    table = Table(title=f"Resumo dos Resultados - {SEARCH_APPROACHES[search_approach]['name']}", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6, justify="center")
    table.add_column("Órgão", style="cyan", width=40)
    table.add_column("Local", style="cyan", width=30)
    table.add_column("Similaridade", justify="right", width=12)
    table.add_column("Valor (R$)", justify="right", width=17)
    table.add_column("Data Encerramento", width=12)

    for result in results:
        details = result.get("details", {})

        # Valor - suportar múltiplos nomes de campo
        valor_raw = (
            details.get("valortotalestimado") or details.get("valorTotalEstimado") or
            details.get("valorfinal") or details.get("valorFinal") or
            details.get("valorTotalHomologado") or 0
        )
        valor = format_currency(valor_raw)

        # Data Encerramento
        data_enc = (
            details.get("dataencerramentoproposta") or details.get("dataEncerramentoProposta") or
            details.get("dataEncerramento") or details.get("dataassinatura") or details.get("dataAssinatura") or "N/A"
        )
        data_enc_fmt = format_date(data_enc)

        # Órgão / Unidade
        unidade = (
            details.get('unidadeorgao_nomeunidade') or details.get('unidadeOrgao_nomeUnidade') or
            details.get('nomeorgaoentidade') or details.get('orgaoEntidade_razaosocial') or
            details.get('orgaoentidade_razaosocial') or 'N/A'
        )

        municipio = (
            details.get('unidadeorgao_municipionome') or details.get('unidadeOrgao_municipioNome') or
            details.get('municipioentidade') or details.get('unidadeorgao_municipioNome') or 'N/A'
        )
        uf = (
            details.get('unidadeorgao_ufsigla') or details.get('unidadeOrgao_ufSigla') or
            details.get('uf') or ''
        )
        local = f"{municipio}/{uf}" if uf else municipio

        table.add_row(
            f"{result.get('rank', '?')}",
            unidade,
            local,
            f"{result.get('similarity', 0):.4f}",
            valor,
            str(data_enc_fmt)
        )

    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")

    # Painéis detalhados (igual v9, com fallbacks de campos)
    for result in results:
        details = result.get("details", {})

        descricao_full = (
            details.get("descricaocompleta") or details.get("descricaoCompleta") or
            details.get("objeto") or "N/A"
        )
        descricao = highlight_key_terms(descricao_full, query.split())

        panel_title = f"#{result.get('rank', '?')} - {result.get('id', details.get('numerocontrolepncp', details.get('numeroControlePNCP', 'N/A')))} (Similaridade: {result.get('similarity', 0):.4f})"
        if search_approach == 2 and result.get('top_category_info'):
            panel_title += " [Correspondência]"
        elif search_approach == 3:
            panel_title += " [Filtrado por categoria]"
        if "semantic_score" in result and "keyword_score" in result:
            panel_title += f" [Semântico: {result['semantic_score']:.4f}, Palavra-chave: {result['keyword_score']:.4f}]"

        content = []
        content.append(f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoentidade_razaosocial') or details.get('orgaoEntidade_razaosocial') or details.get('nomeorgaoentidade', 'N/A')}")
        content.append(f"[bold cyan]Unidade:[/bold cyan] {unidade}")
        content.append(f"[bold cyan]Local:[/bold cyan] {municipio}/{uf if uf else 'N/A'}")
        content.append(f"[bold cyan]Valor:[/bold cyan] {valor}")
        content.append(
            "[bold cyan]Datas:[/bold cyan] Inclusão: " +
            format_date(details.get('datainclusao') or details.get('dataInclusao') or details.get('dataAssinatura') or details.get('dataassinatura') or 'N/A') +
            " | Abertura: " + format_date(details.get('dataaberturaproposta') or details.get('dataAberturaProposta') or 'N/A') +
            " | Encerramento: " + format_date(data_enc)
        )
        content.append(
            f"[bold cyan]Modalidade:[/bold cyan] {details.get('modalidadeid', details.get('modalidadeId', 'N/A'))} - {details.get('modalidadenome', details.get('modalidadeNome', 'N/A'))} | "
            f"[bold cyan]Disputa:[/bold cyan] {details.get('modadisputaid', details.get('modaDisputaId', 'N/A'))} - {details.get('modadisputanome', details.get('modaDisputaNome', 'N/A'))}"
        )
        content.append(
            f"[bold cyan]Usuário:[/bold cyan] {details.get('usuarionome', details.get('usuarioNome', 'N/A'))} | "
            f"[bold cyan]Poder:[/bold cyan] {decode_poder(details.get('orgaoentidade_poderid', details.get('orgaoEntidade_poderId', 'N/A')))} | "
            f"[bold cyan]Esfera:[/bold cyan] {decode_esfera(details.get('orgaoentidade_esferaid', details.get('orgaoEntidade_esferaId', 'N/A')))}"
        )
        if details.get('linksistemaorigem') or details.get('linkSistemaOrigem'):
            content.append(f"[bold cyan]Link Sistema:[/bold cyan] {details.get('linksistemaorigem', details.get('linkSistemaOrigem', 'N/A'))}")
        if search_approach == 2 and result.get('top_category_info'):
            cat = result['top_category_info']
            category_text = f"{cat.get('codigo')} - {cat.get('descricao')} (Score: {cat.get('correspondence_score', 0):.3f})"
            content.append(f"[bold yellow]🎯 Categoria TOP:[/bold yellow] {category_text}")
        content.append(f"[bold cyan]Descrição:[/bold cyan] {descricao[:500]}...")

        console.print(Panel("\n".join(content), title=panel_title, border_style="blue", padding=(1, 2)))

def display_result_details(result, position, query):
    """Exibe detalhes de um resultado específico"""
    details = result.get('details', {})
    
    # Destacar termos da query
    objeto = highlight_key_terms(details.get('objeto', ''), query)
    descricao = highlight_key_terms(details.get('descricaocompleta', '')[:200], query)
    
    detail_text = f"""
[bold cyan]#{position}[/bold cyan] [yellow]Similarity: {result.get('similarity', 0):.3f}[/yellow]

[bold]📄 Objeto:[/bold] {objeto}
[bold]📝 Descrição:[/bold] {descricao}...

[bold]💰 Valor Final:[/bold] {format_currency(details.get('valorfinal', 0))}
[bold]📅 Data Assinatura:[/bold] {format_date(details.get('dataassinatura', 'N/I'))}
[bold]🏢 Órgão:[/bold] {details.get('nomeorgaoentidade', 'N/I')}
[bold]🌍 Localização:[/bold] {details.get('municipioentidade', 'N/I')} - {details.get('uf', 'N/I')}
[bold]⚖️ Poder:[/bold] {decode_poder(details.get('podernome', ''))}
[bold]🎯 Situação:[/bold] {details.get('situacaocontrato', 'N/I')}

[bold]🔗 PNCP:[/bold] {details.get('numerocontrolepncp', 'N/I')}
"""
    
    console.print(Panel(detail_text, border_style="green", title=f"Resultado {position}"))

def highlight_key_terms(text, query_terms, max_length=500):
    """Destaca termos da consulta (compatível com assinatura v9).

    Aceita query_terms como string ou lista; limita tamanho e aplica destaque case-insensitive.
    """
    if not text:
        return "N/A"

    if isinstance(query_terms, str):
        terms = query_terms.split()
    else:
        terms = query_terms

    if len(text) > max_length:
        text = text[:max_length] + "..."

    for term in terms:
        if len(term) > 2:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text = pattern.sub(f"[bold yellow]{term}[/bold yellow]", text)
    return text

# ========================================================================================
# PROCESSAMENTO DE DOCUMENTOS (OTIMIZADO)
# ========================================================================================

def show_process_documents():
    """Menu de seleção de processo (EXATO estilo v9 para documentos)."""
    if not last_results:
        console.print("❌ Execute uma busca primeiro para ver documentos")
        return

    console.print("\n[bold cyan]📄 PROCESSAR DOCUMENTOS - SELECIONE O PROCESSO[/bold cyan]")
    for i, result in enumerate(last_results[:20], 1):
        d = result.get('details', {})
        pncp = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or 'N/I'
        orgao = (d.get('orgaoentidade_razaosocial') or d.get('orgaoEntidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/I')[:60]
        objeto = d.get('objeto') or d.get('descricaocompleta') or d.get('descricaoCompleta') or 'N/I'
        objeto_short = (objeto[:100] + '...') if len(objeto) > 103 else objeto
        console.print(f"[bold]{i:>2}.[/bold] [green]{pncp}[/green] | [yellow]{orgao}[/yellow]\n    {objeto_short}")

    choice = Prompt.ask(f"Escolha (1-{min(20, len(last_results))}) ou Q para voltar", default="1").strip()
    if choice.lower() in ['q','quit','sair']:
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(last_results):
            process_documents_for_result(last_results[idx])
        else:
            console.print("❌ Seleção inválida")
    except ValueError:
        console.print("❌ Entrada inválida")

def _build_pncp_data(details: dict) -> dict:
    """Constrói dicionário pncp_data conforme esperado pelo pipeline Docling."""
    return {
        'id': details.get('numerocontrolepncp') or details.get('numeroControlePNCP'),
        'municipio': (details.get('unidadeorgao_municipionome') or details.get('municipioentidade') or ''),
        'uf': (details.get('unidadeorgao_ufsigla') or details.get('uf') or ''),
        'orgao': (details.get('orgaoentidade_razaosocial') or details.get('orgaoEntidade_razaosocial') or details.get('nomeorgaoentidade') or ''),
        'data_inclusao': details.get('datainclusao') or details.get('dataInclusao'),
        'data_abertura': details.get('dataaberturaproposta') or details.get('dataAberturaProposta'),
        'data_encerramento': details.get('dataencerramentoproposta') or details.get('dataEncerramentoProposta') or details.get('dataEncerramento'),
        'modalidade_id': details.get('modalidadeid') or details.get('modalidadeId'),
        'modalidade_nome': details.get('modalidadenome') or details.get('modalidadeNome'),
        'disputa_id': details.get('modadisputaid') or details.get('modaDisputaId'),
        'disputa_nome': details.get('modadisputanome') or details.get('modaDisputaNome'),
        'descricao': details.get('descricaocompleta') or details.get('descricaoCompleta') or details.get('objeto'),
        'link': details.get('linksistemaorigem') or details.get('linkSistemaOrigem')
    }

def process_documents_for_result(result):
    """Lista documentos do processo com layout v9 e opções (Nº, A, V, Q)."""
    if not DOCUMENTS_AVAILABLE:
        console.print("❌ Módulo de documentos indisponível")
        return
    d = result.get('details', {})
    numero_controle = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or 'N/I'
    pncp_data = _build_pncp_data(d)
    console.print(f"\n[bold cyan]📂 DOCUMENTOS DO PROCESSO:[/bold cyan] [green]{numero_controle}[/green]")
    documentos = fetch_documentos(numero_controle)
    if not documentos:
        console.print("[yellow]Nenhum documento encontrado.[/yellow]")
        return
    for i, doc in enumerate(documentos, 1):
        nome = doc.get('nome', 'Documento')
        tipo = doc.get('tipo', 'N/I')
        data_doc = doc.get('data') or doc.get('data_publicacao') or ''
        url = doc.get('url', '')
        nome_short = (nome[:110] + '...') if len(nome) > 113 else nome
        tipo_show = f" ({tipo})" if tipo and tipo != 'N/I' else ''
        data_show = f" - {data_doc}" if data_doc else ''
        console.print(f"[bold]{i:>2}.[/bold] {nome_short}{tipo_show}{data_show}")
        if url:
            console.print(f"     🔗 {url}")
    console.print("\n[yellow]Opções:[/yellow] Nº=processar | A=processar todos | V=ver links | Q=voltar")
    choice = Prompt.ask("Opção").strip().upper()
    if choice in ['Q','QUIT','SAIR']:
        return
    if choice == 'V':
        show_document_links(documentos)
        return
    if choice == 'A':
        process_all_documents(documentos, pncp_data)
        return
    try:
        doc_idx = int(choice) - 1
        if 0 <= doc_idx < len(documentos):
            process_single_document(documentos[doc_idx], pncp_data)
        else:
            console.print("❌ Índice inválido")
    except ValueError:
        console.print("❌ Opção não reconhecida")

def show_document_links(documentos):
    """Mostra apenas nomes e links (layout v9)."""
    console.print("\n[bold cyan]🔗 LINKS DOS DOCUMENTOS[/bold cyan]")
    for i, doc in enumerate(documentos, 1):
        nome = doc.get('nome', 'Documento')
        url = doc.get('url', 'N/A')
        console.print(f"[bold]{i:>2}.[/bold] {nome}")
        console.print(f"     {url}\n")

def process_single_document(documento, pncp_data=None):
    """Processa um único documento com pipeline Docling (retorno string)."""
    nome = documento.get('nome', 'Documento')
    url = documento.get('url')
    if not url:
        console.print(f"❌ URL não disponível para: {nome}")
        return
    console.print(f"\n[bold cyan]📝 Processando:[/bold cyan] {nome}")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("Processando documento...", total=None)
        try:
            summary_text = process_pncp_document(url, document_name=nome, pncp_data=pncp_data)
            progress.remove_task(task)
            display_document_summary(summary_text)
        except Exception as e:
            progress.remove_task(task)
            console.print(f"❌ Erro: {e}")

def process_all_documents(documentos, pncp_data=None):
    """Processa todos os documentos sequencialmente (layout v9)."""
    console.print(f"\n[bold cyan]📝 Processando {len(documentos)} documentos...[/bold cyan]")
    with Progress(TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), transient=True) as progress:
        task = progress.add_task("Processando...", total=len(documentos))
        results = []
        for i, doc in enumerate(documentos):
            nome = doc.get('nome', f'Documento {i+1}')
            url = doc.get('url')
            try:
                progress.update(task, description=f"{i+1}/{len(documentos)}: {nome[:40]}...")
                if url:
                    res = process_pncp_document(url, document_name=nome, pncp_data=pncp_data)
                    results.append((nome, res))
                progress.advance(task)
            except Exception as e:
                console.print(f"❌ Erro em {nome}: {e}")
                progress.advance(task)
    console.print(f"\n✅ Concluído: {len(results)} documentos processados")
    for nome, res in results:
        display_document_summary(res, compact=True, title_override=nome)

def display_document_summary(result, compact=False, title_override=None):
    """Exibe resultado do processamento. Aceita string (Docling) ou dict antigo."""
    if isinstance(result, dict):
        summary = result.get('full_summary') or result.get('summary') or 'Sem resumo'
        nome = result.get('filename') or result.get('document_name') or title_override or 'Documento'
    else:
        summary = str(result)
        nome = title_override or 'Documento'
    if compact:
        snippet = summary.split('\n',1)[0]
        console.print(f"\n[bold]📄 {nome}[/bold]\n{snippet[:160]}{'...' if len(snippet)>160 else ''}")
    else:
        console.print(summary[:12000])

# ========================================================================================
# FUNCIONALIDADES AUXILIARES
# ========================================================================================

def generate_process_keywords():
    """Fluxo de geração de palavras-chave (layout v9)."""
    if not last_results:
        console.print("❌ Execute uma busca primeiro para gerar palavras-chave")
        return
    console.print("\n[bold cyan]� GERAR PALAVRAS-CHAVE - SELECIONE O PROCESSO[/bold cyan]")
    for i, result in enumerate(last_results[:20], 1):
        d = result.get('details', {})
        pncp = d.get('numerocontrolepncp') or d.get('numeroControlePNCP') or result.get('id') or 'N/I'
        orgao = (d.get('orgaoentidade_razaosocial') or d.get('orgaoEntidade_razaosocial') or d.get('nomeorgaoentidade') or 'N/I')[:60]
        objeto = d.get('objeto') or d.get('descricaocompleta') or d.get('descricaoCompleta') or ''
        objeto_short = (objeto[:100] + '...') if len(objeto) > 103 else objeto
        console.print(f"[bold]{i:>2}.[/bold] [green]{pncp}[/green] | [yellow]{orgao}[/yellow]\n    {objeto_short}")
    choice = Prompt.ask(f"Escolha (1-{min(20,len(last_results))}) ou Q para voltar", default="1").strip()
    if choice.lower() in ['q','quit','sair']:
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(last_results):
            _generate_keywords_for_process(idx+1)
        else:
            console.print("❌ Número inválido")
    except ValueError:
        console.print("❌ Entrada inválida")

def _generate_keywords_for_process(process_number: int):
    if not last_results or process_number < 1 or process_number > len(last_results):
        console.print("[red]Número de processo inválido![/red]")
        return
    result = last_results[process_number - 1]
    details = result.get('details', {})
    descricao = details.get('descricaocompleta') or details.get('descricaoCompleta') or details.get('objeto') or ''
    if not descricao:
        console.print("[yellow]Descrição não disponível para este processo.[/yellow]")
        return
    process_id = result.get('id') or details.get('numerocontrolepncp') or details.get('numeroControlePNCP') or 'N/I'
    console.print(f"\n[bold cyan]Processo Selecionado: #{process_number} - {process_id}[/bold cyan]")
    console.print(f"\n[bold green]Gerando palavras-chave...[/bold green]")
    try:
        with console.status("[bold green]Analisando descrição..."):
            keywords = generate_keywords(descricao, max_keywords=MAX_KEYWORDS)
        if keywords:
            if isinstance(keywords, (list, tuple)):
                kw_str = ", ".join(keywords)
            else:
                kw_str = str(keywords)
            console.print(f"\n[bold green]Palavras-chave geradas:[/bold green]")
            console.print(f"[cyan]{kw_str}[/cyan]")
        else:
            console.print("[yellow]Não foi possível gerar palavras-chave.[/yellow]")
    except Exception as e:
        console.print(f"[red]Erro ao gerar palavras-chave: {e}[/red]")

# ========================================================================================
# EXPORTAÇÃO DE RESULTADOS (OTIMIZADA)  
# ========================================================================================

def export_results():
    """Exporta resultados em diferentes formatos"""
    if not last_results:
        console.print("❌ Execute uma busca primeiro para exportar resultados")
        return
    
    console.print(f"\n[bold cyan]💾 EXPORTAR {len(last_results)} RESULTADOS[/bold cyan]")
    console.print("\n[yellow]📋 FORMATOS DISPONÍVEIS:[/yellow]")
    console.print("[bold]1[/bold] - Excel (.xlsx) - Planilha completa")
    console.print("[bold]2[/bold] - PDF (.pdf) - Relatório formatado") 
    console.print("[bold]3[/bold] - JSON (.json) - Dados estruturados")
    
    choice = Prompt.ask("Escolha o formato (1-3)", choices=["1", "2", "3"], default="1")
    
    if choice == "1":
        export_results_to_excel()
    elif choice == "2":
        export_results_to_pdf()
    elif choice == "3":
        export_results_to_json()

def export_results_to_excel():
    """Exporta resultados (layout e lógica v9)."""
    results = last_results
    query = last_query
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return
    try:
        data = []
        for result in results:
            details = result.get('details', {})
            if not details:
                continue
            row = {
                'Rank': result.get('rank'),
                'ID': result.get('id'),
                'Similaridade': result.get('similarity'),
                'Órgão': details.get('orgaoentidade_razaosocial','N/A'),
                'Unidade': details.get('unidadeorgao_nomeunidade','N/A'),
                'Município': details.get('unidadeorgao_municipionome','N/A'),
                'UF': details.get('unidadeorgao_ufsigla','N/A'),
                'Valor': details.get('valortotalestimado',0),
                'Data Inclusão': format_date(details.get('datainclusao','N/A')),
                'Data Abertura': format_date(details.get('dataaberturaproposta','N/A')),
                'Data Encerramento': format_date(details.get('dataencerramentoproposta','N/A')),
                'Modalidade ID': details.get('modalidadeid','N/A'),
                'Modalidade Nome': details.get('modalidadenome','N/A'),
                'Disputa ID': details.get('modadisputaid','N/A'),
                'Disputa Nome': details.get('modadisputanome','N/A'),
                'Usuário': details.get('usuarionome','N/A'),
                'Poder': decode_poder(details.get('orgaoentidade_poderid','N/A')),
                'Esfera': decode_esfera(details.get('orgaoentidade_esferaid','N/A')),
                'Link Sistema': details.get('linksistemaorigem','N/A'),
                'Descrição': details.get('descricaocompleta','N/A')
            }
            if current_search_approach == 2 and 'correspondence_similarity' in result:
                row['Score_Correspondencia'] = result['correspondence_similarity']
            if 'top_category_info' in result and result['top_category_info']:
                cat = result['top_category_info']
                row['Categoria_TOP'] = f"{cat['codigo']} - {cat['descricao']} (Score: {cat['correspondence_score']:.3f})"
            if 'semantic_score' in result and 'keyword_score' in result:
                row['Score Semântico'] = result['semantic_score']
                row['Score Palavra-chave'] = result['keyword_score']
            data.append(row)
        df = pd.DataFrame(data)
        os.makedirs(RESULTS_PATH, exist_ok=True)
        filename = generate_export_filename("xlsx")
        filepath = os.path.join(RESULTS_PATH, filename)
        df.to_excel(filepath, index=False, engine='openpyxl')
        console.print(f"[green]Resultados exportados para: {filepath}[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados: {e}[/bold red]")

def export_results_to_pdf():
    """Exporta resultados para PDF replicando layout v9."""
    results = last_results
    query = last_query
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return
    try:
        os.makedirs(RESULTS_PATH, exist_ok=True)
        filename = generate_export_filename("pdf")
        filepath = os.path.join(RESULTS_PATH, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=45,leftMargin=45,topMargin=54,bottomMargin=54)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], alignment=1, fontSize=16, spaceAfter=20)
        heading_style = styles['Heading1']
        normal_style = styles['Normal']
        desc_style = ParagraphStyle('Description', parent=normal_style, fontSize=11, leading=13, spaceAfter=6)
        elements = []
        try:
            if use_negation_embeddings and current_search_type in [1,3]:
                pos_terms,_ = extract_pos_neg_terms(query)
                search_display = pos_terms.strip() if pos_terms.strip() else query
            else:
                search_display = query
        except:
            search_display = query
        elements.append(Paragraph(f'BUSCA: "{search_display.upper()}"', title_style))
        elements.append(Paragraph(f'Tipo de busca: {SEARCH_TYPES[current_search_type]["name"]}', normal_style))
        elements.append(Paragraph(f'Abordagem: {SEARCH_APPROACHES[current_search_approach]["name"]}', normal_style))
        elements.append(Paragraph(f'Ordenação: {SORT_MODES[current_sort_mode]["name"]}', normal_style))
        elements.append(Paragraph(f'Data da pesquisa: {datetime.now().strftime("%d/%m/%Y %H:%M")}', normal_style))
        elements.append(Spacer(1,0.2*inch))
        table_data = [["Rank","Unidade","Local","Similaridade","Valor (R$)","Data Proposta"]]
        sorted_results = sorted(results, key=lambda x: x.get('rank',999))
        for r in sorted_results:
            details = r.get('details',{})
            if not details: continue
            valor = format_currency(details.get('valortotalestimado',0))
            data_prop = format_date(details.get('dataencerramentoproposta','N/A'))
            unidade = details.get('unidadeorgao_nomeunidade','N/A')
            unidade = f"{unidade[:30]}..." if len(unidade)>30 else unidade
            municipio = details.get('unidadeorgao_municipionome','N/A')
            uf = details.get('unidadeorgao_ufsigla','')
            local = f"{municipio}/{uf}" if uf else municipio
            table_data.append([
                str(r.get('rank')),unidade,local,f"{r.get('similarity',0):.4f}",valor,str(data_prop)
            ])
        pdf_table = PDFTable(table_data, repeatRows=1)
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.navy),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('ALIGN',(0,0),(-1,0),'CENTER'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,0),9),
            ('BOTTOMPADDING',(0,0),(-1,0),8),
            ('TOPPADDING',(0,0),(-1,0),8),
            ('BACKGROUND',(0,1),(-1,-1),colors.white),
            ('GRID',(0,0),(-1,-1),1,colors.black),
            ('ALIGN',(0,0),(0,-1),'CENTER'),
            ('ALIGN',(3,0),(3,-1),'RIGHT'),
            ('ALIGN',(4,0),(4,-1),'RIGHT'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('FONTSIZE',(0,1),(-1,-1),8)
        ]))
        elements.append(Spacer(1,0.1*inch))
        elements.append(pdf_table)
        elements.append(Spacer(1,0.3*inch))
        elements.append(Paragraph('Detalhes dos Resultados', heading_style))
        elements.append(Spacer(1,0.1*inch))
        card_style = ParagraphStyle('CardStyle', parent=normal_style, fontSize=10, leading=12, leftIndent=10,rightIndent=10,spaceAfter=3,spaceBefore=3)
        card_title_style = ParagraphStyle('CardTitleStyle', parent=styles['Heading2'], fontSize=14, spaceAfter=5, textColor=colors.navy, alignment=0)
        card_subtitle_style = ParagraphStyle('CardSubtitleStyle', parent=styles['Heading3'], fontSize=11, spaceAfter=8, textColor=colors.darkblue)
        desc_label_style = ParagraphStyle('DescLabelStyle', parent=card_style, fontSize=10, fontName='Helvetica-Bold', spaceAfter=3)
        desc_card_style = ParagraphStyle('DescCardStyle', parent=card_style, fontSize=10, leading=11, leftIndent=15, rightIndent=15)
        def escape_html_for_pdf(text:str)->str:
            if not text: return ''
            return (text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
        for r in sorted_results:
            details = r.get('details', {})
            if not details: continue
            orgao_raw = details.get('orgaoentidade_razaosocial','Órgão não informado')
            orgao = escape_html_for_pdf(orgao_raw.title() if orgao_raw else 'Órgão não informado')
            elements.append(Paragraph(f"#{r.get('rank')} - {orgao}", card_title_style))
            info_data = [
                ["Unidade:", escape_html_for_pdf(details.get('unidadeorgao_nomeunidade','N/A'))],
                ["Local:", f"{escape_html_for_pdf(details.get('unidadeorgao_municipionome','N/A'))}/{escape_html_for_pdf(details.get('unidadeorgao_ufsigla','N/A'))}"],
                ["Valor:", escape_html_for_pdf(format_currency(details.get('valortotalestimado',0)))]
            ]
            datas_text = f"Inclusão: {escape_html_for_pdf(format_date(details.get('datainclusao','N/A')))} | Abertura: {escape_html_for_pdf(format_date(details.get('dataaberturaproposta','N/A')))} | Encerramento: {escape_html_for_pdf(format_date(details.get('dataencerramentoproposta','N/A')))}"
            info_data.append(["Datas:", datas_text])
            modalidade_text = f"{escape_html_for_pdf(details.get('modalidadeid','N/A'))} - {escape_html_for_pdf(details.get('modalidadenome','N/A'))}"
            disputa_text = f"{escape_html_for_pdf(details.get('modadisputaid','N/A'))} - {escape_html_for_pdf(details.get('modadisputanome','N/A'))}"
            info_data.append(["Modalidade:", modalidade_text])
            info_data.append(["Disputa:", disputa_text])
            info_table = PDFTable(info_data, colWidths=[2*inch, 4.5*inch])
            info_table.setStyle(TableStyle([
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
                ('FONTNAME',(1,0),(1,-1),'Helvetica'),
                ('FONTSIZE',(0,0),(-1,-1),9),
                ('LEFTPADDING',(0,0),(-1,-1),10),
                ('RIGHTPADDING',(0,0),(-1,-1),5),
                ('TOPPADDING',(0,0),(-1,-1),3),
                ('BOTTOMPADDING',(0,0),(-1,-1),3),
                ('BACKGROUND',(0,0),(-1,-1),colors.lightgrey),
                ('GRID',(0,0),(-1,-1),0.5,colors.gray)
            ]))
            elements.append(info_table)
            elements.append(Spacer(1,0.1*inch))
            elements.append(Paragraph('Descrição:', desc_label_style))
            descricao = details.get('descricaocompleta','N/A')
            descricao = descricao.replace(' :: ','\n• ')
            if not descricao.startswith('•'):
                descricao = '• ' + descricao
            descricao = escape_html_for_pdf(descricao)
            elements.append(Paragraph(descricao, desc_card_style))
            elements.append(Spacer(1,0.2*inch))
            line_data = [["" for _ in range(10)]]
            line_table = PDFTable(line_data, colWidths=[0.65*inch]*10)
            line_table.setStyle(TableStyle([
                ('LINEBELOW',(0,0),(-1,-1),2,colors.navy),
                ('TOPPADDING',(0,0),(-1,-1),0),
                ('BOTTOMPADDING',(0,0),(-1,-1),0)
            ]))
            elements.append(line_table)
            elements.append(Spacer(1,0.3*inch))
        doc.build(elements)
        console.print(f"[green]Resultados exportados para PDF: {filepath}[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados para PDF: {e}[/bold red]")

def export_results_to_json():
    """Exporta resultados para JSON"""
    try:
        filename = generate_export_filename("json")
        filepath = os.path.join(RESULTS_PATH, filename)
        
        # Preparar dados para JSON
        export_data = {
            'metadata': {
                'query': last_query,
                'timestamp': datetime.now().isoformat(),
                'total_results': len(last_results),
                'search_type': SEARCH_TYPES[current_search_type]['name'],
                'search_approach': SEARCH_APPROACHES[current_search_approach]['name'],
                'system_version': 'GvG_v2_optimized'
            },
            'results': []
        }
        
        for i, result in enumerate(last_results, 1):
            result_data = {
                'position': i,
                'similarity': result.get('similarity', 0),
                'numero_controle': result.get('numero_controle', ''),
                'details': result.get('details', {})
            }
            export_data['results'].append(result_data)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Exportando para JSON...", total=None)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            progress.remove_task(task)
        
        console.print(f"✅ Arquivo JSON criado: [green]{filename}[/green]")
        console.print(f"📁 Local: {filepath}")
        
    except Exception as e:
        console.print(f"❌ Erro ao exportar JSON: {e}")

def generate_export_filename(extension):
    """Gera nome de arquivo para exportação"""
    query = last_query or "BUSCA"
    # Extrair apenas termos positivos se negation embeddings ativo (igual v9)
    try:
        if use_negation_embeddings and current_search_type in (1,3):
            pos_terms, _neg_terms = extract_pos_neg_terms(query)
            if pos_terms and pos_terms.strip():
                query = pos_terms.strip()
    except Exception:
        pass
    clean_query = re.sub(r'[^\w\s-]', '', query)
    clean_query = re.sub(r'\s+', '_', clean_query).upper()[:30]
    search_type = current_search_type
    approach = current_search_approach
    relevance_level = get_relevance_filter_status()['level']
    sort_mode = current_sort_mode
    intelligent_status = 'I' if get_intelligent_status()['intelligent_processing'] else 'N'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Novo padrão: Busca_{QUERY}_Sx_Ax_Rx_Ox_I{I|N}_YYYYMMDD_HHMMSS.ext
    filename = f"Busca_{clean_query}_S{search_type}_A{approach}_R{relevance_level}_O{sort_mode}_I{intelligent_status}_{timestamp}.{extension}"
    return filename

# ========================================================================================
# LOOP PRINCIPAL OTIMIZADO
# ========================================================================================

def main():
    """Loop principal do sistema otimizado"""
    console.clear()
    display_header()
    
    # Verificar status inicial dos módulos
    console.print("\n[bold cyan]🔧 STATUS DOS MÓDULOS:[/bold cyan]")
    console.print(f"• gvg_utils: ✅ Carregado")
    console.print(f"• gvg_documents: {'✅ Carregado' if DOCUMENTS_AVAILABLE else '❌ Indisponível'}")
    
    # Informações sobre otimização
    try:
        from gvg_utils import get_module_info
        module_info = get_module_info()
        console.print(f"• Funções otimizadas: {module_info['total_functions']} (seletivas)")
        console.print(f"• Versão: {module_info['version']}")
    except:
        pass
    
    while True:
        try:
            display_menu()
            
            user_input = Prompt.ask("\n[bold cyan]Digite sua opção ou consulta[/bold cyan]").strip()
            
            if not user_input:
                continue
            
            # Comandos de saída
            if user_input.lower() in ['quit', 'exit', 'q', 'sair']:
                console.print("\n[bold green]👋 Obrigado por usar o GvG Search Terminal Otimizado![/bold green]")
                break
            
            # Opções do menu
            elif user_input == "1":
                select_search_type()
            elif user_input == "2":
                select_search_approach()
            elif user_input == "3":
                select_relevance_level()
            elif user_input == "4":
                select_sort_mode()
            elif user_input == "5":
                configure_system()
            elif user_input == "6" and last_results:
                show_process_documents()
            elif user_input == "7" and last_results:
                generate_process_keywords()
            elif user_input == "8" and last_results:
                export_results()
            elif user_input in ["6", "7", "8"] and not last_results:
                console.print("❌ Execute uma busca primeiro para acessar esta opção")
            else:
                # Assumir que é uma consulta de busca
                if len(user_input) < 3:
                    console.print("❌ Consulta muito curta. Digite pelo menos 3 caracteres.")
                    continue
                
                perform_search(user_input)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Interrompido pelo usuário[/yellow]")
            if Confirm.ask("Deseja sair do sistema?"):
                break
        except Exception as e:
            console.print(f"\n❌ Erro inesperado: {e}")
            console.print("🔄 O sistema continuará funcionando...")

if __name__ == "__main__":
    main()
