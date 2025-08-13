#!/usr/bin/env python3
"""
govgo_search_terminal_v1_part3.py - PARTE 3/4
Sistema de Busca PNCP V1 - Funções de Busca e Processamento
===========================================================

🚀 PARTE 3/4 - BUSCA E PROCESSAMENTO:
• Funções de busca com interface Rich
• Processamento de resultados V1
• Exportação em múltiplos formatos
• Análise de documentos
• Funcões de histórico e estatísticas

📋 CONTEÚDO DESTA PARTE:
• Execução de buscas com progresso visual
• Formatação e exibição de resultados
• Exportação JSON/Excel/PDF/LOG
• Análise e sumarização de documentos
• Gestão de histórico de buscas
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.status import Status
from rich.tree import Tree
from rich.rule import Rule

# Importar PARTE 1
try:
    from govgo_search_terminal_v1_part1 import (
        TerminalConfig, TerminalState, VERSION,
        SEARCH_TYPES, SEARCH_APPROACHES, SORT_MODES, RELEVANCE_LEVELS,
        create_header_panel, create_search_summary_table,
        format_currency, format_date, decode_poder, decode_esfera,
        SEARCH_ENGINE_AVAILABLE, DOCUMENT_PROCESSOR_AVAILABLE
    )
except ImportError as e:
    print(f"❌ ERRO: Não foi possível importar PARTE 1: {e}")
    sys.exit(1)

# Importar motor de busca V1
if SEARCH_ENGINE_AVAILABLE:
    try:
        from govgo_search_engine_v1 import GovGoSearchEngine
    except ImportError:
        SEARCH_ENGINE_AVAILABLE = False

# Importar processador de documentos V1
if DOCUMENT_PROCESSOR_AVAILABLE:
    try:
        from govgo_document_processor_v1 import get_query_processor, get_document_processor
    except ImportError:
        DOCUMENT_PROCESSOR_AVAILABLE = False

# ============================================================================
# FUNÇÕES DE BUSCA COM INTERFACE V1
# ============================================================================

def perform_search_with_ui(console: Console, state: TerminalState, search_params: Dict) -> bool:
    """Executa busca com interface Rich V1"""
    console.clear()
    
    # Cabeçalho de busca
    header = create_header_panel(
        "Executando Busca PNCP V1",
        f"Query: \"{search_params['query']}\""
    )
    console.print(header)
    console.print()
    
    # Mostrar parâmetros da busca
    params_table = Table(title="🔧 Parâmetros da Busca V1", show_header=True, header_style="bold cyan")
    params_table.add_column("Parâmetro", style="white", width=20)
    params_table.add_column("Valor", style="green", width=25)
    params_table.add_column("Descrição", style="dim", width=35)
    
    params_table.add_row("Tipo", SEARCH_TYPES[search_params['search_type']]['name'], "Algoritmo de busca")
    params_table.add_row("Abordagem", SEARCH_APPROACHES[search_params['search_approach']]['name'], "Estratégia de execução")
    params_table.add_row("Relevância", f"Nível {search_params['relevance_level']}", "Filtro de qualidade")
    params_table.add_row("Ordenação", SORT_MODES[search_params['sort_mode']]['name'], "Critério de classificação")
    params_table.add_row("Max Resultados", str(search_params['max_results']), "Limite de retorno")
    params_table.add_row("TOP Categorias", str(search_params['top_categories']), "Para filtros categóricos")
    
    console.print(params_table)
    console.print()
    
    # Executar busca com progresso
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            expand=True
        ) as progress:
            
            # [1/5] Configuração inicial
            task1 = progress.add_task("[bold cyan][1/5][/bold cyan] 🔧 Configurando busca V1...", total=100)
            
            # Configurar motor de busca
            if not SEARCH_ENGINE_AVAILABLE:
                console.print("[red]❌ Motor de busca V1 não disponível![/red]")
                return False
            
            engine = GovGoSearchEngine()
            progress.update(task1, advance=50)
            
            if not engine.connect():
                console.print("[red]❌ Falha na conexão com Supabase V1![/red]")
                return False
            
            progress.update(task1, completed=100)
            
            # [2/5] Processamento inteligente
            task2 = progress.add_task("[bold green][2/5][/bold green] 🧠 Processamento inteligente V1...", total=100)
            
            processed_query = search_params['query']
            intelligent_info = None
            
            if DOCUMENT_PROCESSOR_AVAILABLE:
                try:
                    processor = get_query_processor()
                    progress.update(task2, advance=50)
                    intelligent_info = processor.process_query(search_params['query'])
                    processed_query = intelligent_info.get('search_terms', search_params['query'])
                    progress.update(task2, completed=100)
                except Exception as e:
                    console.print(f"[yellow]⚠️ Processamento inteligente falhou: {e}[/yellow]")
                    progress.update(task2, completed=100)
            else:
                progress.update(task2, completed=100)
            
            # [3/5] Busca de categorias (se necessário)
            categories = []
            if search_params['search_approach'] in [2, 3]:
                task3 = progress.add_task("[bold magenta][3/5][/bold magenta] 📂 Buscando categorias TOP V1...", total=100)
                
                try:
                    progress.update(task3, advance=30)
                    categories = engine.get_top_categories(
                        processed_query, 
                        search_params['top_categories']
                    )
                    progress.update(task3, completed=100)
                except Exception as e:
                    console.print(f"[red]❌ Erro na busca de categorias: {e}[/red]")
                    progress.update(task3, completed=100)
            else:
                task3 = progress.add_task("[bold yellow][3/5][/bold yellow] 📂 Pulando busca de categorias...", total=100)
                progress.update(task3, completed=100)
            
            # [4/5] Busca principal
            task4 = progress.add_task("[bold blue][4/5][/bold blue] 🔎 Executando busca principal V1...", total=100)
            
            results = []
            confidence = 0.0
            
            try:
                if search_params['search_type'] == 1:  # Semântica
                    progress.update(task4, advance=50)
                    results, confidence = engine.semantic_search(
                        processed_query, 
                        search_params['max_results']
                    )
                elif search_params['search_type'] == 2:  # Palavras-chave
                    progress.update(task4, advance=50)
                    results, confidence = engine.keyword_search(
                        processed_query,
                        search_params['max_results']
                    )
                elif search_params['search_type'] == 3:  # Híbrida
                    progress.update(task4, advance=50)
                    results, confidence = engine.hybrid_search(
                        processed_query,
                        search_params['max_results']
                    )
                
                progress.update(task4, completed=100)
                
            except Exception as e:
                console.print(f"[red]❌ Erro na busca principal: {e}[/red]")
                progress.update(task4, completed=100)
                return False
            
            # [5/5] Processamento dos resultados
            task5 = progress.add_task("[bold red][5/5][/bold red] 📊 Processando resultados V1...", total=100)
            
            if results:
                # Aplicar ordenação
                progress.update(task5, advance=33)
                results = apply_sort_mode(results, search_params['sort_mode'])
                
                # Atualizar ranks
                progress.update(task5, advance=33)
                for i, result in enumerate(results, 1):
                    result["rank"] = i
                
                progress.update(task5, completed=100)
            else:
                progress.update(task5, completed=100)
            
        # Salvar resultados no state
        state.last_results = results
        state.last_categories = categories
        state.add_to_history(
            search_params['query'],
            search_params['search_type'],
            len(results)
        )
        state.update_session_stats(len(results))
        
        # Mostrar resumo
        console.print()
        show_search_results_summary(console, results, categories, confidence, search_params)
        
        # Exportação automática se habilitada
        if state.config.auto_export and results:
            export_results_auto(console, state, results, search_params)
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Erro durante a busca: {e}[/red]")
        return False

def apply_sort_mode(results: List[Dict], sort_mode: int) -> List[Dict]:
    """Aplica modo de ordenação aos resultados V1"""
    if sort_mode == 1:  # Similaridade (padrão)
        return results  # Já vem ordenado por similaridade
    elif sort_mode == 2:  # Data
        def parse_date_safe(val):
            if not val or val in ("", None):
                return datetime(1900, 1, 1)
            if isinstance(val, datetime):
                return val
            try:
                return datetime.strptime(str(val)[:10], "%Y-%m-%d")
            except Exception:
                return datetime(1900, 1, 1)
        
        return sorted(results, key=lambda x: parse_date_safe(
            x.get("details", {}).get("data_encerramento_proposta", None)
        ), reverse=True)
    elif sort_mode == 3:  # Valor
        return sorted(results, key=lambda x: float(
            x.get("details", {}).get("valor_total_estimado", 0) or 0
        ), reverse=True)
    else:
        return results

def show_search_results_summary(console: Console, results: List[Dict], categories: List[Dict], 
                               confidence: float, search_params: Dict) -> None:
    """Mostra resumo dos resultados V1"""
    console.print()
    console.print("[bold green]✅ Busca V1 Concluída![/bold green]")
    console.print()
    
    if not results:
        no_results_panel = Panel(
            "[yellow]📭 Nenhum resultado encontrado[/yellow]\n\n"
            "💡 [dim]Sugestões:[/dim]\n"
            "• Tente termos mais genéricos\n"
            "• Use busca híbrida\n"
            "• Reduza filtros de relevância\n"
            "• Verifique a ortografia",
            title="[bold red]Sem Resultados[/bold red]",
            border_style="red"
        )
        console.print(no_results_panel)
        return
    
    # Tabela de resumo
    summary_table = create_search_summary_table(results, categories)
    console.print(summary_table)
    console.print()
    
    # Estatísticas adicionais
    stats_info = f"🎯 Confiança: [cyan]{confidence:.3f}[/cyan] | " \
                f"📊 Query: [yellow]\"{search_params['query']}\"[/yellow] | " \
                f"🔍 Tipo: [green]{SEARCH_TYPES[search_params['search_type']]['name']}[/green]"
    
    console.print(Panel(stats_info, border_style="blue", title="[bold]📈 Estatísticas da Busca[/bold]"))
    
    # Opções pós-busca
    console.print()
    post_options = Table(show_header=False, box=None, padding=(0, 2))
    post_options.add_column("", style="bold cyan", width=15)
    post_options.add_column("", style="white", width=50)
    
    post_options.add_row("[Enter]", "Ver primeiros resultados detalhados")
    post_options.add_row("[E]", "Exportar resultados")
    post_options.add_row("[C]", "Ver TOP categorias")
    post_options.add_row("[S]", "Estatísticas detalhadas")
    post_options.add_row("[M]", "Voltar ao menu principal")
    
    console.print(Panel(post_options, title="[bold]⚡ Ações Disponíveis[/bold]", border_style="dim"))
    console.print()

# ============================================================================
# FUNÇÕES DE EXIBIÇÃO DE RESULTADOS V1
# ============================================================================

def show_detailed_results(console: Console, results: List[Dict], page_size: int = 5) -> None:
    """Mostra resultados detalhados com paginação V1"""
    if not results:
        console.print("[yellow]📭 Nenhum resultado para exibir[/yellow]")
        return
    
    console.clear()
    header = create_header_panel("Resultados Detalhados V1", f"Total: {len(results)} contratações")
    console.print(header)
    console.print()
    
    current_page = 0
    total_pages = (len(results) - 1) // page_size + 1
    
    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(results))
        page_results = results[start_idx:end_idx]
        
        # Mostrar resultados da página atual
        for i, result in enumerate(page_results, start_idx + 1):
            details = result.get("details", {})
            
            # Cabeçalho do resultado
            result_header = f"#{i:02d} | Similaridade: {result.get('similarity', 0):.3f} | " \
                          f"ID: {result.get('id', 'N/A')}"
            console.print(f"[bold cyan]{result_header}[/bold cyan]")
            console.print()
            
            # Informações principais
            main_table = Table(show_header=False, box=None, padding=(0, 1))
            main_table.add_column("Campo", style="yellow", width=20)
            main_table.add_column("Valor", style="white", width=60)
            
            # Informações básicas
            main_table.add_row("📝 Objeto", details.get('descricaoCompleta', details.get('objeto_compra', 'N/A'))[:80] + "..." if len(str(details.get('descricaoCompleta', details.get('objeto_compra', '')))) > 80 else str(details.get('descricaoCompleta', details.get('objeto_compra', 'N/A'))))
            main_table.add_row("🏢 Órgão", details.get('orgao_entidade_razao_social', 'N/A'))
            main_table.add_row("🏛️ Unidade", details.get('unidade_orgao_nome_unidade', 'N/A'))
            main_table.add_row("📍 Local", f"{details.get('unidade_orgao_municipio_nome', 'N/A')}/{details.get('unidade_orgao_uf_sigla', 'N/A')}")
            
            # Valores e datas
            valor_estimado = format_currency(details.get('valor_total_estimado', 0))
            valor_homologado = format_currency(details.get('valor_total_homologado', 0))
            main_table.add_row("💰 Valor Estimado", valor_estimado)
            main_table.add_row("✅ Valor Homologado", valor_homologado)
            
            data_abertura = format_date(details.get('data_abertura_proposta', 'N/A'))
            data_encerramento = format_date(details.get('data_encerramento_proposta', 'N/A'))
            main_table.add_row("📅 Abertura", str(data_abertura))
            main_table.add_row("🔒 Encerramento", str(data_encerramento))
            
            # Modalidade e usuário
            main_table.add_row("⚖️ Modalidade", details.get('modalidade_nome', 'N/A'))
            main_table.add_row("👤 Usuário", details.get('usuario_nome', 'N/A'))
            
            # Link do sistema
            link = details.get('link_sistema_origem', 'N/A')
            if link and link != 'N/A' and len(link) > 60:
                link = link[:57] + "..."
            main_table.add_row("🔗 Link Sistema", link)
            
            console.print(main_table)
            console.print()
            
            # Separador entre resultados
            if i < end_idx:
                console.print(Rule(style="dim"))
                console.print()
        
        # Navegação
        nav_info = f"Página {current_page + 1}/{total_pages} | " \
                   f"Resultados {start_idx + 1}-{end_idx} de {len(results)}"
        
        nav_options = "[N] Próxima | [P] Anterior | [Q] Voltar" if total_pages > 1 else "[Q] Voltar"
        
        console.print(Panel(
            f"[cyan]{nav_info}[/cyan]\n[dim]{nav_options}[/dim]",
            title="[bold]📄 Navegação[/bold]",
            border_style="blue"
        ))
        
        # Input do usuário
        if total_pages > 1:
            choice = Prompt.ask("Ação", choices=["n", "p", "q", "N", "P", "Q"], default="q").lower()
            
            if choice == "n" and current_page < total_pages - 1:
                current_page += 1
                console.clear()
                continue
            elif choice == "p" and current_page > 0:
                current_page -= 1
                console.clear()
                continue
            elif choice == "q":
                break
            else:
                console.print("[yellow]Opção inválida ou não disponível[/yellow]")
                time.sleep(1)
                console.clear()
                continue
        else:
            Prompt.ask("Pressione [Enter] para voltar", default="")
            break

def show_categories_detail(console: Console, categories: List[Dict]) -> None:
    """Mostra detalhes das TOP categorias V1"""
    if not categories:
        console.print("[yellow]📭 Nenhuma categoria para exibir[/yellow]")
        return
    
    console.clear()
    header = create_header_panel("TOP Categorias V1", f"Total: {len(categories)} categorias encontradas")
    console.print(header)
    console.print()
    
    # Tabela de categorias
    cat_table = Table(title="🏷️ Categorias Mais Similares V1", show_header=True, header_style="bold magenta")
    cat_table.add_column("Rank", style="bold cyan", width=6, justify="center")
    cat_table.add_column("Código", style="yellow", width=12, justify="center")
    cat_table.add_column("Descrição", style="white", width=50)
    cat_table.add_column("Similaridade", style="green", width=12, justify="center")
    cat_table.add_column("Qualidade", style="blue", width=10, justify="center")
    
    for cat in categories:
        similarity = cat.get('similarity_score', 0)
        
        # Definir qualidade baseada na similaridade
        if similarity > 0.8:
            quality = "[green]Excelente[/green]"
        elif similarity > 0.6:
            quality = "[yellow]Boa[/yellow]"
        elif similarity > 0.4:
            quality = "[orange3]Regular[/orange3]"
        else:
            quality = "[red]Baixa[/red]"
        
        cat_table.add_row(
            str(cat.get('rank', 0)),
            cat.get('codigo', 'N/A'),
            cat.get('descricao', 'N/A')[:50],
            f"{similarity:.4f}",
            quality
        )
    
    console.print(cat_table)
    console.print()
    
    # Estatísticas das categorias
    similarities = [cat.get('similarity_score', 0) for cat in categories]
    avg_similarity = np.mean(similarities) if similarities else 0
    max_similarity = max(similarities) if similarities else 0
    min_similarity = min(similarities) if similarities else 0
    
    stats_info = f"📊 Similaridade Média: [cyan]{avg_similarity:.3f}[/cyan] | " \
                f"🔝 Máxima: [green]{max_similarity:.3f}[/green] | " \
                f"🔻 Mínima: [red]{min_similarity:.3f}[/red]"
    
    console.print(Panel(stats_info, title="[bold]📈 Estatísticas das Categorias[/bold]", border_style="magenta"))
    console.print()
    
    Prompt.ask("Pressione [Enter] para voltar", default="")

# ============================================================================
# FUNÇÕES DE EXPORTAÇÃO V1
# ============================================================================

def export_results_auto(console: Console, state: TerminalState, results: List[Dict], search_params: Dict) -> None:
    """Exportação automática de resultados V1"""
    if not results:
        return
    
    console.print()
    console.print("[yellow]💾 Iniciando exportação automática V1...[/yellow]")
    
    try:
        # Gerar nome do arquivo
        query_clean = "".join(c for c in search_params['query'] if c.isalnum() or c in " _").strip()
        query_clean = query_clean.upper().replace(" ", "_")[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        base_filename = f"Busca_{query_clean}_S{search_params['search_type']}_" \
                       f"A{search_params['search_approach']}_R{search_params['relevance_level']}_" \
                       f"O{search_params['sort_mode']}_{timestamp}"
        
        # Exportar JSON
        json_file = export_to_json(results, search_params, state.config.output_directory, base_filename)
        if json_file:
            console.print(f"✅ JSON: [green]{Path(json_file).name}[/green]")
        
        # Exportar LOG
        log_file = export_to_log(results, state.last_categories, search_params, state.config.output_directory, base_filename)
        if log_file:
            console.print(f"✅ LOG: [green]{Path(log_file).name}[/green]")
        
        console.print(f"📁 Diretório: [cyan]{state.config.output_directory}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]❌ Erro na exportação automática: {e}[/red]")

def export_to_json(results: List[Dict], search_params: Dict, output_dir: str, base_filename: str) -> str:
    """Exporta resultados para JSON V1"""
    try:
        # Preparar dados para JSON
        export_data = []
        for result in results:
            details = result.get("details", {})
            record = {
                "rank": result.get("rank", 0),
                "id": result.get("id", ""),
                "similarity": result.get("similarity", 0),
                "search_type": result.get("search_type", ""),
                # Dados principais V1 (campos atualizados)
                "orgao": details.get("orgao_entidade_razao_social", ""),
                "unidade": details.get("unidade_orgao_nome_unidade", ""),
                "municipio": details.get("unidade_orgao_municipio_nome", ""),
                "uf": details.get("unidade_orgao_uf_sigla", ""),
                "valor_estimado": details.get("valor_total_estimado", 0),
                "valor_homologado": details.get("valor_total_homologado", 0),
                "data_inclusao": details.get("data_inclusao", ""),
                "data_abertura": details.get("data_abertura_proposta", ""),
                "data_encerramento": details.get("data_encerramento_proposta", ""),
                "modalidade_nome": details.get("modalidade_nome", ""),
                "modo_disputa_nome": details.get("modo_disputa_nome", ""),
                "usuario": details.get("usuario_nome", ""),
                "link_sistema": details.get("link_sistema_origem", ""),
                "objeto_compra": details.get("objeto_compra", details.get("descricaoCompleta", ""))
            }
            export_data.append(record)
        
        # Metadados
        metadata = {
            "query": search_params['query'],
            "search_type": SEARCH_TYPES[search_params['search_type']]['name'],
            "search_approach": SEARCH_APPROACHES[search_params['search_approach']]['name'],
            "sort_mode": SORT_MODES[search_params['sort_mode']]['name'],
            "export_date": datetime.now().isoformat(),
            "total_results": len(export_data),
            "govgo_version": VERSION,
            "engine": "govgo_search_engine_v1"
        }
        
        # Estrutura final
        json_data = {
            "metadata": metadata,
            "results": export_data
        }
        
        # Salvar arquivo
        json_file = Path(output_dir) / f"{base_filename}.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return str(json_file)
        
    except Exception as e:
        print(f"❌ Erro ao exportar JSON: {e}")
        return None

def export_to_log(results: List[Dict], categories: List[Dict], search_params: Dict, 
                  output_dir: str, base_filename: str) -> str:
    """Exporta log detalhado V1"""
    try:
        log_file = Path(output_dir) / f"{base_filename}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write("="*100 + "\n")
            f.write("GOVGO SEARCH V1 - LOG DETALHADO\n")
            f.write("="*100 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Query: \"{search_params['query']}\"\n")
            f.write(f"Tipo: {SEARCH_TYPES[search_params['search_type']]['name']}\n")
            f.write(f"Abordagem: {SEARCH_APPROACHES[search_params['search_approach']]['name']}\n")
            f.write(f"Ordenação: {SORT_MODES[search_params['sort_mode']]['name']}\n")
            f.write(f"Total de Resultados: {len(results)}\n")
            f.write("="*100 + "\n\n")
            
            # TOP Categorias
            if categories:
                f.write("TOP CATEGORIAS DA QUERY (V1)\n")
                f.write("="*80 + "\n")
                f.write(f"{'Rank':<6} {'Código':<12} {'Descrição':<50} {'Similaridade':<12}\n")
                f.write("-"*80 + "\n")
                
                for cat in categories:
                    similarity = cat.get('similarity_score', 0)
                    f.write(f"{cat.get('rank', 0):<6} {cat.get('codigo', 'N/A'):<12} "
                           f"{cat.get('descricao', 'N/A')[:50]:<50} {similarity:.4f}\n")
                
                f.write("="*80 + "\n\n")
            
            # Resultados detalhados
            if results:
                f.write("RESUMO DOS RESULTADOS V1\n")
                f.write("="*120 + "\n")
                f.write(f"{'Rank':<6} {'Órgão':<40} {'Local':<25} {'Similaridade':<12} {'Valor (R$)':<15} {'Data Encerr.':<12}\n")
                f.write("-"*120 + "\n")
                
                for result in results:
                    details = result.get("details", {})
                    valor = details.get("valor_total_estimado", 0) or 0
                    valor_str = format_currency(valor) if valor > 0 else "N/A"
                    
                    unidade = details.get('unidade_orgao_nome_unidade', 'N/A')[:40]
                    municipio = details.get('unidade_orgao_municipio_nome', 'N/A')
                    uf = details.get('unidade_orgao_uf_sigla', '')
                    local = f"{municipio}/{uf}" if uf else municipio
                    local = local[:25]
                    
                    data_encerramento = format_date(details.get("data_encerramento_proposta", "N/A"))
                    
                    f.write(f"{result['rank']:<6} {unidade:<40} {local:<25} "
                           f"{result['similarity']:.4f}    {valor_str:<15} {str(data_encerramento):<12}\n")
                
                f.write("="*120 + "\n")
        
        return str(log_file)
        
    except Exception as e:
        print(f"❌ Erro ao exportar LOG: {e}")
        return None

# ============================================================================
# FUNÇÕES DE HISTÓRICO E ESTATÍSTICAS V1
# ============================================================================

def show_search_history(console: Console, state: TerminalState) -> None:
    """Mostra histórico de buscas V1"""
    console.clear()
    
    header = create_header_panel("Histórico de Buscas V1", f"Total: {len(state.search_history)} registros")
    console.print(header)
    console.print()
    
    if not state.search_history:
        no_history_panel = Panel(
            "[yellow]📭 Nenhuma busca realizada ainda[/yellow]\n\n"
            "💡 [dim]Realize algumas buscas para ver o histórico aqui[/dim]",
            title="[bold]Histórico Vazio[/bold]",
            border_style="yellow"
        )
        console.print(no_history_panel)
        Prompt.ask("Pressione [Enter] para voltar", default="")
        return
    
    # Tabela de histórico
    history_table = Table(title="📚 Histórico de Buscas V1", show_header=True, header_style="bold green")
    history_table.add_column("#", style="bold cyan", width=4, justify="center")
    history_table.add_column("Data/Hora", style="white", width=16)
    history_table.add_column("Query", style="yellow", width=40)
    history_table.add_column("Tipo", style="blue", width=12)
    history_table.add_column("Resultados", style="green", width=10, justify="center")
    
    for i, entry in enumerate(reversed(state.search_history[-20:]), 1):  # Últimos 20
        timestamp = entry['timestamp'].strftime("%d/%m %H:%M")
        query = entry['query'][:40] + "..." if len(entry['query']) > 40 else entry['query']
        
        history_table.add_row(
            str(i),
            timestamp,
            query,
            entry['search_type'],
            str(entry['results_count'])
        )
    
    console.print(history_table)
    console.print()
    
    # Estatísticas do histórico
    total_searches = len(state.search_history)
    total_results = sum(entry['results_count'] for entry in state.search_history)
    avg_results = total_results / total_searches if total_searches > 0 else 0
    
    # Tipo mais usado
    type_counts = {}
    for entry in state.search_history:
        search_type = entry['search_type']
        type_counts[search_type] = type_counts.get(search_type, 0) + 1
    
    most_used_type = max(type_counts, key=type_counts.get) if type_counts else "N/A"
    
    stats_info = f"🔍 Total de Buscas: [cyan]{total_searches}[/cyan] | " \
                f"📊 Total de Resultados: [green]{total_results}[/green] | " \
                f"📈 Média por Busca: [yellow]{avg_results:.1f}[/yellow] | " \
                f"🏆 Tipo Preferido: [magenta]{most_used_type}[/magenta]"
    
    console.print(Panel(stats_info, title="[bold]📈 Estatísticas do Histórico[/bold]", border_style="green"))
    console.print()
    
    Prompt.ask("Pressione [Enter] para voltar", default="")

# ============================================================================
# EXPORTAÇÃO DA PARTE 3
# ============================================================================

if __name__ == "__main__":
    print("🚀 GovGo Search Terminal V1 - PARTE 3/4")
    print("🔍 Funções de busca e processamento carregadas!")
    print("⚠️ Execute o arquivo principal govgo_search_terminal_v1.py")
