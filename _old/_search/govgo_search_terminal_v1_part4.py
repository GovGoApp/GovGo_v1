#!/usr/bin/env python3
"""
govgo_search_terminal_v1_part4.py - PARTE 4/4
Sistema de Busca PNCP V1 - Função Principal e Controles
=======================================================

🚀 PARTE 4/4 - FUNÇÃO PRINCIPAL:
• Loop principal do terminal V1
• Controles de sistema e configuração
• Funções de análise de documentos
• Gerenciamento de sessão e cleanup
• Integração de todas as partes

📋 CONTEÚDO DESTA PARTE:
• Função principal main() V1
• Controles de processamento inteligente
• Análise de documentos via upload
• Gerenciamento de filtros de relevância
• Cleanup e finalização de sessão
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.status import Status

# Importar todas as partes anteriores
try:
    from govgo_search_terminal_v1_part1 import (
        TerminalConfig, TerminalState, VERSION,
        SEARCH_ENGINE_AVAILABLE, DOCUMENT_PROCESSOR_AVAILABLE,
        create_header_panel, create_status_table,
        toggle_intelligent_processing, get_intelligent_status,
        set_relevance_filter_level, get_relevance_filter_status
    )
    
    from govgo_search_terminal_v1_part2 import (
        show_main_menu, show_search_menu, show_config_menu
    )
    
    from govgo_search_terminal_v1_part3 import (
        perform_search_with_ui, show_detailed_results, show_categories_detail,
        show_search_history
    )
except ImportError as e:
    print(f"❌ ERRO: Não foi possível importar partes anteriores: {e}")
    print("💡 Certifique-se que todas as partes (1-3) estão na mesma pasta!")
    sys.exit(1)

# Importar processador de documentos V1 se disponível
if DOCUMENT_PROCESSOR_AVAILABLE:
    try:
        from govgo_document_processor_v1 import get_document_processor
    except ImportError:
        DOCUMENT_PROCESSOR_AVAILABLE = False

# ============================================================================
# FUNÇÕES DE CONTROLE DE SISTEMA V1
# ============================================================================

def show_system_status(console: Console, state: TerminalState) -> None:
    """Mostra status detalhado do sistema V1"""
    console.clear()
    
    header = create_header_panel("Status do Sistema V1", "Informações detalhadas dos componentes")
    console.print(header)
    console.print()
    
    # Tabela de status
    status_table = create_status_table(state)
    console.print(status_table)
    console.print()
    
    # Informações adicionais
    additional_info = Panel(
        "[bold cyan]Informações Técnicas V1:[/bold cyan]\n\n"
        f"• Sistema: [white]GovGo Search V1[/white]\n"
        f"• Versão: [green]{VERSION}[/green]\n"
        f"• Base de Dados: [yellow]Supabase V1[/yellow]\n"
        f"• Engine: [blue]govgo_search_engine_v1.py[/blue]\n"
        f"• Processador: [magenta]govgo_document_processor_v1.py[/magenta]\n"
        f"• Interface: [cyan]Rich Terminal UI[/cyan]",
        title="[bold]🔧 Detalhes Técnicos[/bold]",
        border_style="blue"
    )
    console.print(additional_info)
    console.print()
    
    Prompt.ask("Pressione [Enter] para voltar", default="")

def toggle_intelligent_processing_ui(console: Console, state: TerminalState) -> None:
    """Interface para toggle do processamento inteligente V1"""
    console.clear()
    
    header = create_header_panel("Processamento Inteligente V1", "Ativar/Desativar sistema de IA")
    console.print(header)
    console.print()
    
    # Status atual
    current_status = get_intelligent_status()
    is_enabled = current_status.get('intelligent_processing_enabled', False)
    
    current_panel = Panel(
        f"[bold]Status Atual:[/bold] {'🧠 Ativo' if is_enabled else '💤 Inativo'}\n\n"
        f"[dim]Funcionalidades do Processamento Inteligente V1:[/dim]\n"
        f"• Análise semântica avançada de queries\n"
        f"• Extração automática de condições SQL\n"
        f"• Identificação de entidades (UF, valores, datas)\n"
        f"• Preprocessamento de termos de negação\n"
        f"• Otimização contextual de buscas",
        title=f"[bold]{'🧠' if is_enabled else '💤'} Processamento Inteligente V1[/bold]",
        border_style="green" if is_enabled else "yellow"
    )
    console.print(current_panel)
    console.print()
    
    # Confirmar alteração
    action = "desativar" if is_enabled else "ativar"
    if Confirm.ask(f"Deseja {action} o processamento inteligente?"):
        try:
            with Status(f"Alterando processamento inteligente V1...", console=console):
                new_status = toggle_intelligent_processing()
                new_enabled = new_status.get('intelligent_processing_enabled', False)
                state.intelligent_status = new_status
            
            # Mostrar resultado
            if new_enabled != is_enabled:
                result_text = "🧠 Ativado" if new_enabled else "💤 Desativado"
                console.print(f"\n✅ Processamento inteligente V1: [bold green]{result_text}[/bold green]")
            else:
                console.print(f"\n⚠️ Status mantido: {'🧠 Ativo' if new_enabled else '💤 Inativo'}")
                
        except Exception as e:
            console.print(f"\n[red]❌ Erro ao alterar processamento inteligente: {e}[/red]")
    else:
        console.print(f"\n[yellow]Operação cancelada - Status mantido[/yellow]")
    
    console.print()
    Prompt.ask("Pressione [Enter] para voltar", default="")

def manage_relevance_filter_ui(console: Console, state: TerminalState) -> None:
    """Interface para gerenciar filtro de relevância V1"""
    console.clear()
    
    header = create_header_panel("Filtro de Relevância V1", "Configurar níveis de filtragem IA")
    console.print(header)
    console.print()
    
    # Status atual
    current_status = get_relevance_filter_status()
    current_level = current_status.get('relevance_filter_level', 1)
    
    # Informações dos níveis
    level_info = {
        1: {"name": "🔓 Sem Filtro", "description": "Todos os resultados são retornados", "color": "blue"},
        2: {"name": "⚖️ Flexível", "description": "Filtragem moderada baseada em IA", "color": "yellow"},
        3: {"name": "🔒 Restritivo", "description": "Filtragem rigorosa - apenas alta relevância", "color": "red"}
    }
    
    # Painel atual
    current_info = level_info[current_level]
    current_panel = Panel(
        f"[bold]Nível Atual:[/bold] {current_info['name']}\n"
        f"[dim]{current_info['description']}[/dim]\n\n"
        f"[bold cyan]Como funciona o Filtro V1:[/bold cyan]\n"
        f"• [dim]Nível 1:[/dim] Retorna todos os resultados encontrados\n"
        f"• [dim]Nível 2:[/dim] IA analisa e remove resultados pouco relevantes\n"
        f"• [dim]Nível 3:[/dim] IA aplica critérios rigorosos de relevância\n\n"
        f"[yellow]💡 Recomendação: Use Nível 2 para a maioria das buscas[/yellow]",
        title=f"[bold]{current_info['name']} - Nível {current_level}[/bold]",
        border_style=current_info['color']
    )
    console.print(current_panel)
    console.print()
    
    # Menu de opções
    console.print("[bold]Escolha o novo nível de relevância:[/bold]")
    for level, info in level_info.items():
        current_marker = "✅" if level == current_level else "  "
        console.print(f"   {current_marker} {level}. {info['name']} - {info['description']}")
    console.print("   0. Manter atual e voltar")
    console.print()
    
    # Escolha do usuário
    choice = Prompt.ask("Nível desejado", choices=["0", "1", "2", "3"], default="0")
    
    if choice == "0":
        console.print("[yellow]Nível mantido[/yellow]")
    else:
        new_level = int(choice)
        if new_level != current_level:
            try:
                with Status(f"Configurando filtro de relevância V1...", console=console):
                    set_relevance_filter_level(new_level)
                    new_status = get_relevance_filter_status()
                    state.relevance_status = new_status
                
                new_info = level_info[new_level]
                console.print(f"\n✅ Filtro configurado: [bold green]{new_info['name']}[/bold green]")
                
            except Exception as e:
                console.print(f"\n[red]❌ Erro ao configurar filtro: {e}[/red]")
        else:
            console.print(f"\n[yellow]Nível {new_level} já estava ativo[/yellow]")
    
    console.print()
    Prompt.ask("Pressione [Enter] para voltar", default="")

def analyze_document_ui(console: Console, state: TerminalState) -> None:
    """Interface para análise de documentos V1"""
    console.clear()
    
    header = create_header_panel("Análise de Documentos V1", "Upload e processamento de arquivos")
    console.print(header)
    console.print()
    
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        error_panel = Panel(
            "[red]❌ Processador de documentos V1 não disponível![/red]\n\n"
            "[dim]Verifique se o módulo govgo_document_processor_v1.py está instalado corretamente.[/dim]",
            title="[bold red]Módulo Indisponível[/bold red]",
            border_style="red"
        )
        console.print(error_panel)
        Prompt.ask("Pressione [Enter] para voltar", default="")
        return
    
    # Informações sobre análise de documentos
    info_panel = Panel(
        "[bold cyan]Funcionalidades de Análise V1:[/bold cyan]\n\n"
        "• [white]Extração de texto[/white] de PDFs, Word, Excel, etc.\n"
        "• [white]Sumarização automática[/white] com IA\n"
        "• [white]Identificação de entidades[/white] (valores, datas, órgãos)\n"
        "• [white]Geração de queries[/white] otimizadas para busca\n"
        "• [white]Análise de relevância[/white] contextual\n\n"
        "[yellow]🔧 Engines suportados:[/yellow]\n"
        "• Docling V3 (preferencial)\n"
        "• MarkItDown V2 (fallback)",
        title="[bold]📄 Análise de Documentos V1[/bold]",
        border_style="blue"
    )
    console.print(info_panel)
    console.print()
    
    # Solicitar caminho do arquivo
    file_path = Prompt.ask("📁 [bold]Caminho do arquivo para análise[/bold]", default="")
    
    if not file_path or file_path.strip() == "":
        console.print("[yellow]Operação cancelada[/yellow]")
        return
    
    file_path = file_path.strip()
    
    # Verificar se arquivo existe
    if not Path(file_path).exists():
        console.print(f"[red]❌ Arquivo não encontrado: {file_path}[/red]")
        Prompt.ask("Pressione [Enter] para voltar", default="")
        return
    
    # Processar documento
    try:
        with Status("Analisando documento V1...", console=console) as status:
            processor = get_document_processor()
            
            status.update("Extraindo texto...")
            result = processor.analyze_document(file_path)
            
            status.update("Processando análise...")
            time.sleep(1)  # Simular processamento
        
        if result:
            # Mostrar resultados da análise
            console.print("\n[bold green]✅ Análise concluída![/bold green]")
            console.print()
            
            # Resumo do documento
            summary_text = result.get('summary', 'Resumo não disponível')[:500] + "..." if len(result.get('summary', '')) > 500 else result.get('summary', 'Resumo não disponível')
            
            result_panel = Panel(
                f"[bold]📄 Arquivo:[/bold] {Path(file_path).name}\n"
                f"[bold]📏 Tamanho:[/bold] {result.get('text_length', 0)} caracteres\n"
                f"[bold]🎯 Confiança:[/bold] {result.get('confidence', 0):.2f}\n\n"
                f"[bold cyan]📝 Resumo:[/bold cyan]\n{summary_text}",
                title="[bold]📊 Resultado da Análise V1[/bold]",
                border_style="green"
            )
            console.print(result_panel)
            
            # Queries sugeridas
            if 'suggested_queries' in result and result['suggested_queries']:
                console.print()
                console.print("[bold yellow]💡 Queries sugeridas para busca:[/bold yellow]")
                for i, query in enumerate(result['suggested_queries'][:5], 1):
                    console.print(f"   {i}. [cyan]{query}[/cyan]")
            
        else:
            console.print("\n[red]❌ Falha na análise do documento[/red]")
            
    except Exception as e:
        console.print(f"\n[red]❌ Erro durante a análise: {e}[/red]")
    
    console.print()
    Prompt.ask("Pressione [Enter] para voltar", default="")

# ============================================================================
# FUNÇÃO PRINCIPAL V1
# ============================================================================

def main():
    """Função principal do Terminal V1"""
    console = Console()
    state = TerminalState()
    
    # Cabeçalho inicial
    console.clear()
    welcome_header = create_header_panel(
        "🚀 Bem-vindo ao GovGo Search V1!",
        "Sistema Avançado de Busca PNCP com IA"
    )
    console.print(welcome_header)
    console.print()
    
    # Verificações iniciais
    console.print("[bold yellow]🔍 Verificando componentes V1...[/bold yellow]")
    
    if not SEARCH_ENGINE_AVAILABLE:
        console.print("[red]❌ Motor de busca V1 indisponível![/red]")
        console.print("[dim]Verifique govgo_search_engine_v1.py[/dim]")
        return
    else:
        console.print("[green]✅ Motor de busca V1 carregado[/green]")
    
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        console.print("[yellow]⚠️ Processador de documentos V1 indisponível[/yellow]")
        console.print("[dim]Algumas funcionalidades podem estar limitadas[/dim]")
    else:
        console.print("[green]✅ Processador de documentos V1 carregado[/green]")
    
    console.print()
    time.sleep(2)
    
    # Atualizar status inicial
    try:
        state.intelligent_status = get_intelligent_status()
        state.relevance_status = get_relevance_filter_status()
    except Exception as e:
        console.print(f"[yellow]⚠️ Falha ao obter status inicial: {e}[/yellow]")
    
    # Loop principal
    try:
        while True:
            choice = show_main_menu(console, state)
            
            if choice == "0":  # Sair
                break
                
            elif choice == "1":  # Nova Busca
                search_params = show_search_menu(console, state.config)
                if search_params:
                    success = perform_search_with_ui(console, state, search_params)
                    if success and state.last_results:
                        # Menu pós-busca
                        while True:
                            post_choice = Prompt.ask(
                                "[cyan]Ação[/cyan]",
                                choices=["enter", "e", "c", "s", "m"],
                                default="enter"
                            ).lower()
                            
                            if post_choice == "enter":
                                show_detailed_results(console, state.last_results)
                                break
                            elif post_choice == "e":
                                # Exportação manual (TODO: implementar menu de exportação)
                                console.print("[yellow]Funcionalidade de exportação manual em desenvolvimento[/yellow]")
                                time.sleep(1)
                                break
                            elif post_choice == "c":
                                show_categories_detail(console, state.last_categories)
                                break
                            elif post_choice == "s":
                                # Estatísticas detalhadas (TODO: implementar)
                                console.print("[yellow]Estatísticas detalhadas em desenvolvimento[/yellow]")
                                time.sleep(1)
                                break
                            elif post_choice == "m":
                                break
            
            elif choice == "2":  # Configurações
                show_config_menu(console, state.config)
            
            elif choice == "3":  # Status do Sistema
                show_system_status(console, state)
            
            elif choice == "4":  # Histórico
                show_search_history(console, state)
            
            elif choice == "5":  # Últimos Resultados
                if state.last_results:
                    show_detailed_results(console, state.last_results)
                else:
                    console.clear()
                    console.print(Panel(
                        "[yellow]📭 Nenhum resultado disponível[/yellow]\n\n"
                        "[dim]Realize uma busca primeiro para ver os resultados aqui[/dim]",
                        title="[bold]Sem Resultados[/bold]",
                        border_style="yellow"
                    ))
                    Prompt.ask("Pressione [Enter] para voltar", default="")
            
            elif choice == "6":  # TOP Categorias
                if state.last_categories:
                    show_categories_detail(console, state.last_categories)
                else:
                    console.clear()
                    console.print(Panel(
                        "[yellow]📭 Nenhuma categoria disponível[/yellow]\n\n"
                        "[dim]Realize uma busca com filtro categórico primeiro[/dim]",
                        title="[bold]Sem Categorias[/bold]",
                        border_style="yellow"
                    ))
                    Prompt.ask("Pressione [Enter] para voltar", default="")
            
            elif choice == "7":  # Análise de Documento
                analyze_document_ui(console, state)
            
            elif choice == "8":  # Processamento Inteligente
                toggle_intelligent_processing_ui(console, state)
            
            elif choice == "9":  # Filtro de Relevância
                manage_relevance_filter_ui(console, state)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operação cancelada pelo usuário[/yellow]")
    
    except Exception as e:
        console.print(f"\n[red]❌ Erro inesperado: {e}[/red]")
    
    finally:
        # Cleanup e despedida
        console.clear()
        
        # Resumo da sessão
        session = state.get_session_summary()
        
        goodbye_panel = Panel(
            f"[bold cyan]Obrigado por usar o GovGo Search V1![/bold cyan]\n\n"
            f"📊 [white]Resumo da Sessão:[/white]\n"
            f"• Buscas realizadas: [green]{session['searches_performed']}[/green]\n"
            f"• Resultados encontrados: [yellow]{session['total_results']}[/yellow]\n"
            f"• Tempo de sessão: [blue]{session['duration_minutes']:.1f} minutos[/blue]\n"
            f"• Média de resultados: [magenta]{session['avg_results_per_search']:.1f}[/magenta]\n\n"
            f"[dim]Até a próxima! 👋[/dim]",
            title="[bold]🚀 GovGo Search V1 - Sessão Encerrada[/bold]",
            border_style="cyan"
        )
        console.print(goodbye_panel)

# ============================================================================
# EXPORTAÇÃO DA PARTE 4
# ============================================================================

if __name__ == "__main__":
    print("🚀 GovGo Search Terminal V1 - PARTE 4/4")
    print("🎮 Função principal e controles carregados!")
    print("⚠️ Execute o arquivo principal govgo_search_terminal_v1.py")
    print()
    print("🔧 Ou execute diretamente com: python -c 'from govgo_search_terminal_v1_part4 import main; main()'")
