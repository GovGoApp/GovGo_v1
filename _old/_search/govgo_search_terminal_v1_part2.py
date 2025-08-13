#!/usr/bin/env python3
"""
govgo_search_terminal_v1_part2.py - PARTE 2/4
Sistema de Busca PNCP V1 - Funções de Menu e Interface
======================================================

🚀 PARTE 2/4 - INTERFACE E MENUS:
• Funções de menu principal e submenus
• Interface Rich interativa V1
• Configuração dinâmica de parâmetros
• Visualização de resultados e histórico
• Funcões de navegação e controle

📋 CONTEÚDO DESTA PARTE:
• Menu principal com opções Rich
• Menu de configurações avançadas
• Visualização de histórico e estatísticas
• Funções de exibição de resultados
• Controles de navegação e help
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.columns import Columns
from rich.rule import Rule
from rich.tree import Tree

# Importar PARTE 1
try:
    from govgo_search_terminal_v1_part1 import (
        TerminalConfig, TerminalState, VERSION,
        SEARCH_TYPES, SEARCH_APPROACHES, SORT_MODES, RELEVANCE_LEVELS,
        create_header_panel, create_config_table, create_status_table, create_search_summary_table,
        validate_search_type, validate_search_approach, validate_relevance_level,
        validate_max_results, validate_top_categories,
        MIN_RESULTS, MAX_RESULTS, DEFAULT_RESULTS, MAX_CATEGORIES, DEFAULT_CATEGORIES
    )
except ImportError as e:
    print(f"❌ ERRO: Não foi possível importar PARTE 1: {e}")
    print("💡 Certifique-se que govgo_search_terminal_v1_part1.py está na mesma pasta!")
    sys.exit(1)

# ============================================================================
# FUNÇÕES DE MENU PRINCIPAL V1
# ============================================================================

def show_main_menu(console: Console, state: TerminalState) -> str:
    """Exibe menu principal V1 e retorna opção escolhida"""
    console.clear()
    
    # Cabeçalho
    header = create_header_panel(
        "Sistema de Busca PNCP V1",
        "Interface Terminal Interativa - Menu Principal"
    )
    console.print(header)
    console.print()
    
    # Menu de opções
    menu_table = Table(show_header=False, box=None, padding=(0, 2))
    menu_table.add_column("Opção", style="bold cyan", width=3)
    menu_table.add_column("Descrição", style="white", width=50)
    menu_table.add_column("Status", style="dim", width=25)
    
    menu_table.add_row("1", "🔍 [bold]Nova Busca PNCP V1[/bold]", "Busca semântica/híbrida")
    menu_table.add_row("2", "⚙️ [bold]Configurações[/bold]", "Ajustar parâmetros")
    menu_table.add_row("3", "📊 [bold]Status do Sistema[/bold]", "Ver componentes V1")
    menu_table.add_row("4", "📋 [bold]Histórico de Buscas[/bold]", f"{len(state.search_history)} registros")
    menu_table.add_row("5", "📈 [bold]Últimos Resultados[/bold]", f"{len(state.last_results)} resultados")
    menu_table.add_row("6", "🏷️ [bold]TOP Categorias[/bold]", f"{len(state.last_categories)} categorias")
    menu_table.add_row("7", "📄 [bold]Análise de Documento[/bold]", "Upload e análise")
    menu_table.add_row("8", "🧠 [bold]Proc. Inteligente[/bold]", "Toggle ON/OFF")
    menu_table.add_row("9", "🎯 [bold]Filtro Relevância[/bold]", "Ajustar níveis")
    menu_table.add_row("0", "❌ [bold]Sair[/bold]", "Encerrar aplicação")
    
    menu_panel = Panel(menu_table, title="[bold]🎮 Menu Principal V1[/bold]", border_style="blue")
    console.print(menu_panel)
    console.print()
    
    # Informações da sessão
    session = state.get_session_summary()
    session_info = f"📊 Sessão: [cyan]{session['searches_performed']}[/cyan] buscas | " \
                   f"⏱️ [yellow]{session['duration_minutes']:.1f}min[/yellow] | " \
                   f"📝 [green]{session['total_results']}[/green] resultados"
    console.print(Panel(session_info, border_style="dim", title="[dim]Estatísticas[/dim]"))
    console.print()
    
    # Prompt para escolha
    while True:
        try:
            choice = Prompt.ask(
                "[bold cyan]Escolha uma opção[/bold cyan]",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                default="1"
            )
            return choice
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada pelo usuário[/yellow]")
            return "0"

def show_search_menu(console: Console, config: TerminalConfig) -> Dict:
    """Menu de configuração de busca V1"""
    console.clear()
    
    header = create_header_panel(
        "Nova Busca PNCP V1",
        "Configure os parâmetros de busca"
    )
    console.print(header)
    console.print()
    
    # Mostrar configuração atual
    config_table = create_config_table(config)
    console.print(config_table)
    console.print()
    
    # Prompt para query
    console.print("[bold cyan]📝 Digite sua consulta de busca:[/bold cyan]")
    console.print("[dim]Exemplo: notebooks para escolas públicas[/dim]")
    console.print()
    
    query = Prompt.ask("🔍 [bold]Query de busca[/bold]", default="")
    
    if not query or query.strip() == "":
        console.print("[red]❌ Query não pode estar vazia![/red]")
        return None
    
    # Menu rápido de opções
    console.print()
    console.print("[bold yellow]⚡ Configuração Rápida:[/bold yellow]")
    
    quick_options = Table(show_header=False, box=None)
    quick_options.add_column("Opção", style="bold cyan", width=3)
    quick_options.add_column("Descrição", style="white", width=40)
    
    quick_options.add_row("1", "Usar configuração atual (recomendado)")
    quick_options.add_row("2", "Configuração personalizada")
    quick_options.add_row("0", "Voltar ao menu principal")
    
    console.print(quick_options)
    console.print()
    
    quick_choice = Prompt.ask(
        "[cyan]Escolha[/cyan]",
        choices=["0", "1", "2"],
        default="1"
    )
    
    if quick_choice == "0":
        return None
    elif quick_choice == "1":
        # Usar configuração atual
        return {
            'query': query.strip(),
            'search_type': config.search_type,
            'search_approach': config.search_approach,
            'relevance_level': config.relevance_level,
            'sort_mode': config.sort_mode,
            'max_results': config.max_results,
            'top_categories': config.top_categories,
            'filter_expired': config.filter_expired,
            'use_negation_embeddings': config.use_negation_embeddings
        }
    else:
        # Configuração personalizada
        return show_custom_search_config(console, query, config)

def show_custom_search_config(console: Console, query: str, config: TerminalConfig) -> Dict:
    """Menu de configuração personalizada V1"""
    console.print()
    console.print("[bold yellow]🔧 Configuração Personalizada V1[/bold yellow]")
    console.print()
    
    try:
        # Tipo de busca
        console.print("[bold]1. Tipo de Busca:[/bold]")
        for key, value in SEARCH_TYPES.items():
            current = "✅" if key == config.search_type else "  "
            console.print(f"   {current} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
        
        search_type = IntPrompt.ask(
            "   Escolha o tipo",
            choices=[1, 2, 3],
            default=config.search_type
        )
        console.print()
        
        # Abordagem
        console.print("[bold]2. Abordagem de Busca:[/bold]")
        for key, value in SEARCH_APPROACHES.items():
            current = "✅" if key == config.search_approach else "  "
            console.print(f"   {current} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
        
        search_approach = IntPrompt.ask(
            "   Escolha a abordagem",
            choices=[1, 2, 3],
            default=config.search_approach
        )
        console.print()
        
        # Nível de relevância
        console.print("[bold]3. Nível de Relevância:[/bold]")
        for key, value in RELEVANCE_LEVELS.items():
            current = "✅" if key == config.relevance_level else "  "
            console.print(f"   {current} {key}. [cyan]Nível {key}[/cyan] - {value['description']}")
        
        relevance_level = IntPrompt.ask(
            "   Escolha o nível",
            choices=[1, 2, 3],
            default=config.relevance_level
        )
        console.print()
        
        # Ordenação
        console.print("[bold]4. Modo de Ordenação:[/bold]")
        for key, value in SORT_MODES.items():
            current = "✅" if key == config.sort_mode else "  "
            console.print(f"   {current} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
        
        sort_mode = IntPrompt.ask(
            "   Escolha a ordenação",
            choices=[1, 2, 3],
            default=config.sort_mode
        )
        console.print()
        
        # Número de resultados
        max_results = IntPrompt.ask(
            f"5. [bold]Máximo de resultados[/bold] ({MIN_RESULTS}-{MAX_RESULTS})",
            default=config.max_results
        )
        
        if max_results < MIN_RESULTS or max_results > MAX_RESULTS:
            console.print(f"[yellow]Ajustando para faixa válida: {MIN_RESULTS}-{MAX_RESULTS}[/yellow]")
            max_results = max(MIN_RESULTS, min(MAX_RESULTS, max_results))
        console.print()
        
        # TOP categorias (para abordagens 2 e 3)
        if search_approach in [2, 3]:
            top_categories = IntPrompt.ask(
                f"6. [bold]TOP categorias[/bold] (1-{MAX_CATEGORIES})",
                default=config.top_categories
            )
            
            if top_categories < 1 or top_categories > MAX_CATEGORIES:
                console.print(f"[yellow]Ajustando para faixa válida: 1-{MAX_CATEGORIES}[/yellow]")
                top_categories = max(1, min(MAX_CATEGORIES, top_categories))
        else:
            top_categories = config.top_categories
        console.print()
        
        # Opções adicionais
        filter_expired = Confirm.ask(
            "7. [bold]Filtrar contratações encerradas?[/bold]",
            default=config.filter_expired
        )
        console.print()
        
        use_negation_embeddings = Confirm.ask(
            "8. [bold]Usar negation embeddings?[/bold]",
            default=config.use_negation_embeddings
        )
        console.print()
        
        return {
            'query': query,
            'search_type': search_type,
            'search_approach': search_approach,
            'relevance_level': relevance_level,
            'sort_mode': sort_mode,
            'max_results': max_results,
            'top_categories': top_categories,
            'filter_expired': filter_expired,
            'use_negation_embeddings': use_negation_embeddings
        }
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Configuração cancelada pelo usuário[/yellow]")
        return None

def show_config_menu(console: Console, config: TerminalConfig) -> None:
    """Menu de configurações gerais V1"""
    console.clear()
    
    header = create_header_panel(
        "Configurações do Sistema V1",
        "Ajustar parâmetros padrão"
    )
    console.print(header)
    console.print()
    
    while True:
        # Mostrar configuração atual
        config_table = create_config_table(config)
        console.print(config_table)
        console.print()
        
        # Menu de opções
        options_table = Table(show_header=False, box=None)
        options_table.add_column("Opção", style="bold cyan", width=3)
        options_table.add_column("Configuração", style="white", width=35)
        options_table.add_column("Atual", style="green", width=20)
        
        options_table.add_row("1", "Tipo de Busca Padrão", SEARCH_TYPES[config.search_type]['name'])
        options_table.add_row("2", "Abordagem Padrão", SEARCH_APPROACHES[config.search_approach]['name'])
        options_table.add_row("3", "Nível Relevância Padrão", f"Nível {config.relevance_level}")
        options_table.add_row("4", "Ordenação Padrão", SORT_MODES[config.sort_mode]['name'])
        options_table.add_row("5", "Max Resultados Padrão", str(config.max_results))
        options_table.add_row("6", "TOP Categorias Padrão", str(config.top_categories))
        options_table.add_row("7", "Filtrar Encerradas", "Sim" if config.filter_expired else "Não")
        options_table.add_row("8", "Negation Embeddings", "Sim" if config.use_negation_embeddings else "Não")
        options_table.add_row("9", "Diretório de Saída", config.output_directory)
        options_table.add_row("0", "Voltar ao Menu Principal", "")
        
        menu_panel = Panel(options_table, title="[bold]⚙️ Configurações Disponíveis[/bold]", border_style="blue")
        console.print(menu_panel)
        console.print()
        
        choice = Prompt.ask(
            "[cyan]Escolha uma opção para alterar[/cyan]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="0"
        )
        
        if choice == "0":
            break
        elif choice == "1":
            config.search_type = change_search_type(console, config.search_type)
        elif choice == "2":
            config.search_approach = change_search_approach(console, config.search_approach)
        elif choice == "3":
            config.relevance_level = change_relevance_level(console, config.relevance_level)
        elif choice == "4":
            config.sort_mode = change_sort_mode(console, config.sort_mode)
        elif choice == "5":
            config.max_results = change_max_results(console, config.max_results)
        elif choice == "6":
            config.top_categories = change_top_categories(console, config.top_categories)
        elif choice == "7":
            config.filter_expired = not config.filter_expired
            status = "Sim" if config.filter_expired else "Não"
            console.print(f"✅ Filtrar encerradas: [green]{status}[/green]")
        elif choice == "8":
            config.use_negation_embeddings = not config.use_negation_embeddings
            status = "Sim" if config.use_negation_embeddings else "Não"
            console.print(f"✅ Negation embeddings: [green]{status}[/green]")
        elif choice == "9":
            config.output_directory = change_output_directory(console, config.output_directory)
        
        console.print()
        time.sleep(1)  # Pausa para ler a confirmação

# ============================================================================
# FUNÇÕES AUXILIARES DE CONFIGURAÇÃO V1
# ============================================================================

def change_search_type(console: Console, current: int) -> int:
    """Alterar tipo de busca"""
    console.print("\n[bold]🔍 Tipos de Busca Disponíveis V1:[/bold]")
    for key, value in SEARCH_TYPES.items():
        current_marker = "✅" if key == current else "  "
        console.print(f"   {current_marker} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
    
    new_type = IntPrompt.ask("Novo tipo", choices=[1, 2, 3], default=current)
    console.print(f"✅ Tipo alterado para: [green]{SEARCH_TYPES[new_type]['name']}[/green]")
    return new_type

def change_search_approach(console: Console, current: int) -> int:
    """Alterar abordagem de busca"""
    console.print("\n[bold]📊 Abordagens de Busca Disponíveis V1:[/bold]")
    for key, value in SEARCH_APPROACHES.items():
        current_marker = "✅" if key == current else "  "
        console.print(f"   {current_marker} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
    
    new_approach = IntPrompt.ask("Nova abordagem", choices=[1, 2, 3], default=current)
    console.print(f"✅ Abordagem alterada para: [green]{SEARCH_APPROACHES[new_approach]['name']}[/green]")
    return new_approach

def change_relevance_level(console: Console, current: int) -> int:
    """Alterar nível de relevância"""
    console.print("\n[bold]🎯 Níveis de Relevância Disponíveis V1:[/bold]")
    for key, value in RELEVANCE_LEVELS.items():
        current_marker = "✅" if key == current else "  "
        console.print(f"   {current_marker} {key}. [cyan]Nível {key}[/cyan] - {value['description']}")
    
    new_level = IntPrompt.ask("Novo nível", choices=[1, 2, 3], default=current)
    console.print(f"✅ Nível alterado para: [green]Nível {new_level}[/green]")
    return new_level

def change_sort_mode(console: Console, current: int) -> int:
    """Alterar modo de ordenação"""
    console.print("\n[bold]📈 Modos de Ordenação Disponíveis V1:[/bold]")
    for key, value in SORT_MODES.items():
        current_marker = "✅" if key == current else "  "
        console.print(f"   {current_marker} {key}. [cyan]{value['name']}[/cyan] - {value['description']}")
    
    new_mode = IntPrompt.ask("Novo modo", choices=[1, 2, 3], default=current)
    console.print(f"✅ Ordenação alterada para: [green]{SORT_MODES[new_mode]['name']}[/green]")
    return new_mode

def change_max_results(console: Console, current: int) -> int:
    """Alterar número máximo de resultados"""
    console.print(f"\n[bold]📝 Número Máximo de Resultados V1:[/bold]")
    console.print(f"   Atual: [yellow]{current}[/yellow]")
    console.print(f"   Faixa válida: [dim]{MIN_RESULTS} a {MAX_RESULTS}[/dim]")
    
    new_max = IntPrompt.ask("Novo máximo", default=current)
    
    if new_max < MIN_RESULTS or new_max > MAX_RESULTS:
        console.print(f"[yellow]Valor ajustado para faixa válida: {MIN_RESULTS}-{MAX_RESULTS}[/yellow]")
        new_max = max(MIN_RESULTS, min(MAX_RESULTS, new_max))
    
    console.print(f"✅ Max resultados alterado para: [green]{new_max}[/green]")
    return new_max

def change_top_categories(console: Console, current: int) -> int:
    """Alterar número de TOP categorias"""
    console.print(f"\n[bold]🏷️ Número de TOP Categorias V1:[/bold]")
    console.print(f"   Atual: [yellow]{current}[/yellow]")
    console.print(f"   Faixa válida: [dim]1 a {MAX_CATEGORIES}[/dim]")
    
    new_top = IntPrompt.ask("Novo número", default=current)
    
    if new_top < 1 or new_top > MAX_CATEGORIES:
        console.print(f"[yellow]Valor ajustado para faixa válida: 1-{MAX_CATEGORIES}[/yellow]")
        new_top = max(1, min(MAX_CATEGORIES, new_top))
    
    console.print(f"✅ TOP categorias alterado para: [green]{new_top}[/green]")
    return new_top

def change_output_directory(console: Console, current: str) -> str:
    """Alterar diretório de saída"""
    console.print(f"\n[bold]📁 Diretório de Saída V1:[/bold]")
    console.print(f"   Atual: [yellow]{current}[/yellow]")
    
    new_dir = Prompt.ask("Novo diretório", default=current)
    
    # Validar se diretório existe ou pode ser criado
    try:
        Path(new_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"✅ Diretório alterado para: [green]{new_dir}[/green]")
        return new_dir
    except Exception as e:
        console.print(f"[red]❌ Erro ao acessar diretório: {e}[/red]")
        console.print(f"[yellow]Mantendo diretório atual: {current}[/yellow]")
        return current

# ============================================================================
# EXPORTAÇÃO DA PARTE 2
# ============================================================================

if __name__ == "__main__":
    print("🚀 GovGo Search Terminal V1 - PARTE 2/4")
    print("🎮 Funções de menu e interface carregadas!")
    print("⚠️ Execute o arquivo principal govgo_search_terminal_v1.py")
