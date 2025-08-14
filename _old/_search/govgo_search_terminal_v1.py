#!/usr/bin/env python3
"""
govgo_search_terminal_v1.py
Sistema de Busca PNCP V1 - Interface Terminal Interativa 
========================================================

🚀 MIGRAÇÃO V0 → V1:
• Baseado no GvG_SP_Search_Terminal_v9.py
• Sistema unificado de busca para GovGo V1  
• Nova base Supabase V1
• Interface Rich modernizada e código modular

🎯 FUNCIONALIDADES V1:
• Interface interativa Rich com menus coloridos
• Busca semântica, palavras-chave e híbrida
• Sistema de relevância 3 níveis com IA
• Processamento inteligente de consultas V1
• Exportação JSON/PDF/Excel/LOG
• Análise de documentos com docling V1
• Configurações dinâmicas e histórico de buscas
• Loop principal com controles de sistema
• Gerenciamento de sessão e cleanup automático
"""


import os
import sys
import time
import json
import locale
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Rich imports - Interface visual
from rich.console import Console
from rich.panel import Panel  
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich.tree import Tree
from rich.rule import Rule
from rich.status import Status
from rich.live import Live
from rich.markdown import Markdown


# Adicionar path do módulo V1
current_dir = Path(__file__).parent
parent_dir = current_dir.parent / 'search'  # Apontar para a pasta search
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(parent_dir))

# Importar motor de busca V1
try:
    from govgo_search_engine_v1 import (
        GovGoSearchEngine,
        SearchConfig,
        SEARCH_TYPES,
        SEARCH_APPROACHES,  
        SORT_MODES,
        RELEVANCE_LEVELS,
        # Funções de compatibilidade V0
        format_currency,
        format_date,
        decode_poder,
        decode_esfera,
        toggle_intelligent_processing,
        get_intelligent_status,
        set_relevance_filter_level,
        get_relevance_filter_status
    )
    SEARCH_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Motor de busca V1 não disponível: {e}")
    sys.exit(1)

# Importar processador de documentos V1
try:
    from govgo_document_processor_v1 import (
        SearchQueryProcessor,
        get_query_processor,
        DocumentProcessor,
        get_document_processor
    )
    DOCUMENT_PROCESSOR_AVAILABLE = True
except ImportError:
    print("⚠️ Processador de documentos V1 não disponível")
    DOCUMENT_PROCESSOR_AVAILABLE = False

# Carregar configurações V1 do .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# ============================================================================
# CONFIGURAÇÕES E CONSTANTES V1
# ============================================================================

# Diretórios V1
BASE_PATH = os.getenv('BASE_PATH', str(Path(__file__).parent.parent / 'data'))
RESULTS_PATH = os.getenv('RESULTS_PATH', str(Path(BASE_PATH) / 'reports'))
FILES_PATH = os.getenv('FILES_PATH', str(Path(BASE_PATH) / 'files'))

# Constantes V1
VERSION = "1.0.0"
MIN_RESULTS = 5
MAX_RESULTS = 100  # Aumentado para V1
DEFAULT_RESULTS = 30
MAX_CATEGORIES = 20
DEFAULT_CATEGORIES = 10
SEMANTIC_WEIGHT = 0.75

# Configurar locale para formatação
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

# ============================================================================
# CLASSES PRINCIPAIS V1
# ============================================================================

@dataclass
class TerminalConfig:
    """Configuração do Terminal V1"""
    # Configurações de busca
    search_type: int = 1  # 1=Semântica, 2=Palavras-chave, 3=Híbrida
    search_approach: int = 3  # 1=Direta, 2=Correspondência, 3=Filtro
    relevance_level: int = 1  # 1=Sem filtro, 2=Flexível, 3=Restritivo
    sort_mode: int = 3  # 1=Similaridade, 2=Data, 3=Valor
    
    # Configurações de resultados
    max_results: int = DEFAULT_RESULTS
    top_categories: int = DEFAULT_CATEGORIES
    filter_expired: bool = True
    use_negation_embeddings: bool = True
    
    # Configurações de interface
    show_progress: bool = True
    auto_export: bool = True
    verbose_mode: bool = False
    
    # Configurações de arquivo
    output_directory: str = RESULTS_PATH
    
    def to_dict(self) -> dict:
        """Converte configuração para dicionário"""
        return {
            'search_type': self.search_type,
            'search_approach': self.search_approach,
            'relevance_level': self.relevance_level,
            'sort_mode': self.sort_mode,
            'max_results': self.max_results,
            'top_categories': self.top_categories,
            'filter_expired': self.filter_expired,
            'use_negation_embeddings': self.use_negation_embeddings,
            'show_progress': self.show_progress,
            'auto_export': self.auto_export,
            'verbose_mode': self.verbose_mode,
            'output_directory': self.output_directory
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Cria configuração a partir de dicionário"""
        return cls(**data)

class TerminalState:
    """Estado global do Terminal V1"""
    def __init__(self):
        self.config = TerminalConfig()
        self.console = Console()
        self.search_history = []
        self.last_results = []
        self.last_categories = []
        self.current_session = {
            'start_time': datetime.now(),
            'searches_performed': 0,
            'total_results_found': 0,
            'session_id': f"GvG_V1_{int(time.time())}"
        }
        self.intelligent_status = {'intelligent_processing_enabled': False}
        self.relevance_status = {'relevance_filter_level': 1}
        
    def add_to_history(self, query: str, search_type: int, results_count: int):
        """Adiciona busca ao histórico"""
        self.search_history.append({
            'timestamp': datetime.now(),
            'query': query,
            'search_type': SEARCH_TYPES[search_type]['name'],
            'results_count': results_count,
            'session_id': self.current_session['session_id']
        })
        
        # Manter apenas últimas 50 buscas
        if len(self.search_history) > 50:
            self.search_history = self.search_history[-50:]
            
    def update_session_stats(self, results_count: int):
        """Atualiza estatísticas da sessão"""
        self.current_session['searches_performed'] += 1
        self.current_session['total_results_found'] += results_count
        
    def get_session_summary(self) -> dict:
        """Retorna resumo da sessão atual"""
        duration = datetime.now() - self.current_session['start_time']
        return {
            'session_id': self.current_session['session_id'],
            'duration_minutes': duration.total_seconds() / 60,
            'searches_performed': self.current_session['searches_performed'],
            'total_results': self.current_session['total_results_found'],
            'avg_results_per_search': (
                self.current_session['total_results_found'] / 
                max(1, self.current_session['searches_performed'])
            )
        }

# ============================================================================
# FUNÇÕES UTILITÁRIAS V1
# ============================================================================

def create_header_panel(title: str, subtitle: str = None, version: str = VERSION) -> Panel:
    """Cria painel de cabeçalho V1"""
    if subtitle:
        content = f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim]\n[green]Versão {version}[/green]"
    else:
        content = f"[bold cyan]{title}[/bold cyan]\n[green]Versão {version}[/green]"
        
    return Panel.fit(
        content,
        border_style="cyan",
        title="[bold]🚀 GovGo Search V1[/bold]",
        subtitle="[dim]Sistema de Busca PNCP[/dim]"
    )

def create_config_table(config: TerminalConfig) -> Table:
    """Cria tabela de configurações V1"""
    table = Table(title="⚙️ Configurações Ativas V1", show_header=True, header_style="bold magenta")
    table.add_column("Configuração", style="cyan", width=25)
    table.add_column("Valor", style="white", width=30)
    table.add_column("Descrição", style="dim", width=40)
    
    # Configurações de busca
    table.add_row(
        "Tipo de Busca",
        SEARCH_TYPES[config.search_type]['name'],
        SEARCH_TYPES[config.search_type]['description']
    )
    table.add_row(
        "Abordagem",
        SEARCH_APPROACHES[config.search_approach]['name'],
        SEARCH_APPROACHES[config.search_approach]['description']
    )
    table.add_row(
        "Nível Relevância",
        f"Nível {config.relevance_level}",
        RELEVANCE_LEVELS[config.relevance_level]['description']
    )
    table.add_row(
        "Ordenação",
        SORT_MODES[config.sort_mode]['name'],
        SORT_MODES[config.sort_mode]['description']
    )
    
    # Configurações de resultados
    table.add_row("Max Resultados", str(config.max_results), "Número máximo de resultados por busca")
    table.add_row("TOP Categorias", str(config.top_categories), "Categorias mais similares para filtros")
    table.add_row("Filtrar Encerradas", "Sim" if config.filter_expired else "Não", "Ocultar contratações encerradas")
    table.add_row("Negation Embeddings", "Sim" if config.use_negation_embeddings else "Não", "Usar embeddings de negação")
    
    # Configurações de interface
    table.add_row("Mostrar Progresso", "Sim" if config.show_progress else "Não", "Exibir barras de progresso")
    table.add_row("Export Automático", "Sim" if config.auto_export else "Não", "Exportar resultados automaticamente")
    table.add_row("Modo Verboso", "Sim" if config.verbose_mode else "Não", "Informações detalhadas")
    
    return table

def create_status_table(state: TerminalState) -> Table:
    """Cria tabela de status do sistema V1"""
    table = Table(title="📊 Status do Sistema V1", show_header=True, header_style="bold green")
    table.add_column("Componente", style="yellow", width=25)
    table.add_column("Status", style="white", width=20)
    table.add_column("Informação", style="dim", width=40)
    
    # Status do motor de busca
    engine_status = "✅ Conectado" if SEARCH_ENGINE_AVAILABLE else "❌ Indisponível"
    table.add_row("Motor de Busca V1", engine_status, "govgo_search_engine_v1.py")
    
    # Status do processador de documentos
    doc_status = "✅ Disponível" if DOCUMENT_PROCESSOR_AVAILABLE else "❌ Indisponível"
    table.add_row("Proc. Documentos V1", doc_status, "govgo_document_processor_v1.py")
    
    # Status do processamento inteligente
    intelligent_enabled = state.intelligent_status.get('intelligent_processing_enabled', False)
    intelligent_status = "🧠 Ativo" if intelligent_enabled else "💤 Inativo"
    table.add_row("Proc. Inteligente", intelligent_status, "Query preprocessing e SQL conditions")
    
    # Status do filtro de relevância  
    relevance_level = state.relevance_status.get('relevance_filter_level', 1)
    level_names = {1: "🔓 Sem Filtro", 2: "⚖️ Flexível", 3: "🔒 Restritivo"}
    relevance_status = level_names.get(relevance_level, "❓ Desconhecido")
    table.add_row("Filtro Relevância", relevance_status, f"Nível {relevance_level} de filtragem")
    
    # Estatísticas da sessão
    session = state.get_session_summary()
    table.add_row("Sessão Atual", f"⏱️ {session['duration_minutes']:.1f}min", f"{session['searches_performed']} buscas realizadas")
    table.add_row("Histórico", f"📝 {len(state.search_history)} registros", "Últimas buscas da sessão")
    
    return table

def create_search_summary_table(results: List[Dict], categories: List[Dict]) -> Table:
    """Cria tabela de resumo dos resultados V1"""
    table = Table(title="📋 Resumo dos Resultados V1", show_header=True, header_style="bold blue")
    table.add_column("Métrica", style="cyan", width=25)
    table.add_column("Valor", style="white", width=20)
    table.add_column("Detalhes", style="dim", width=40)
    
    if results:
        # Estatísticas básicas
        table.add_row("Total de Resultados", str(len(results)), "Contratações encontradas")
        
        # Similaridade média
        similarities = [r.get('similarity', 0) for r in results]
        avg_similarity = np.mean(similarities) if similarities else 0
        table.add_row("Similaridade Média", f"{avg_similarity:.3f}", "Índice de relevância médio")
        
        # Faixas de similaridade
        high_sim = len([s for s in similarities if s > 0.8])
        med_sim = len([s for s in similarities if 0.6 <= s <= 0.8])
        low_sim = len([s for s in similarities if s < 0.6])
        table.add_row("Alta Similaridade", str(high_sim), "Resultados > 0.8 (Excelente)")
        table.add_row("Média Similaridade", str(med_sim), "Resultados 0.6-0.8 (Boa)")
        table.add_row("Baixa Similaridade", str(low_sim), "Resultados < 0.6 (Regular)")
        
        # Valores
        valores = []
        for result in results:
            details = result.get('details', {})
            valor = details.get('valor_total_estimado', 0) or 0
            try:
                valores.append(float(valor))
            except (ValueError, TypeError):
                valores.append(0)
        
        if valores and any(v > 0 for v in valores):
            valor_total = sum(valores)
            valor_medio = np.mean([v for v in valores if v > 0])
            table.add_row("Valor Total", format_currency(valor_total), "Soma dos valores estimados")
            table.add_row("Valor Médio", format_currency(valor_medio), "Média dos valores > 0")
        
        # Estados mais frequentes
        estados = {}
        for result in results:
            details = result.get('details', {})
            uf = details.get('unidade_orgao_uf_sigla', 'N/A')
            if uf and uf != 'N/A':
                estados[uf] = estados.get(uf, 0) + 1
        
        if estados:
            top_estado = max(estados, key=estados.get)
            table.add_row("Estado Principal", f"{top_estado} ({estados[top_estado]})", "UF com mais resultados")
    else:
        table.add_row("Status", "❌ Sem Resultados", "Nenhuma contratação encontrada")
    
    if categories:
        table.add_row("", "", "")  # Separador
        table.add_row("TOP Categorias", str(len(categories)), "Categorias mais similares")
        if categories:
            top_cat = categories[0]
            table.add_row("Categoria Principal", top_cat.get('codigo', 'N/A'), f"Sim: {top_cat.get('similarity_score', 0):.3f}")
    
    return table

# ============================================================================
# FUNÇÕES DE VALIDAÇÃO V1  
# ============================================================================

def validate_search_type(value: str) -> int:
    """Valida tipo de busca V1"""
    try:
        search_type = int(value)
        if search_type in SEARCH_TYPES:
            return search_type
        else:
            raise ValueError(f"Tipo deve ser 1, 2 ou 3")
    except ValueError as e:
        raise ValueError(f"Tipo de busca inválido: {e}")

def validate_search_approach(value: str) -> int:
    """Valida abordagem de busca V1"""
    try:
        approach = int(value)
        if approach in SEARCH_APPROACHES:
            return approach
        else:
            raise ValueError(f"Abordagem deve ser 1, 2 ou 3")
    except ValueError as e:
        raise ValueError(f"Abordagem inválida: {e}")

def validate_relevance_level(value: str) -> int:
    """Valida nível de relevância V1"""
    try:
        level = int(value)
        if level in RELEVANCE_LEVELS:
            return level
        else:
            raise ValueError(f"Nível deve ser 1, 2 ou 3")
    except ValueError as e:
        raise ValueError(f"Nível de relevância inválido: {e}")

def validate_max_results(value: str) -> int:
    """Valida número máximo de resultados V1"""
    try:
        max_results = int(value)
        if MIN_RESULTS <= max_results <= MAX_RESULTS:
            return max_results
        else:
            raise ValueError(f"Deve estar entre {MIN_RESULTS} e {MAX_RESULTS}")
    except ValueError as e:
        raise ValueError(f"Número de resultados inválido: {e}")

def validate_top_categories(value: str) -> int:
    """Valida número de TOP categorias V1"""
    try:
        top_cat = int(value)
        if 1 <= top_cat <= MAX_CATEGORIES:
            return top_cat
        else:
            raise ValueError(f"Deve estar entre 1 e {MAX_CATEGORIES}")
    except ValueError as e:
        raise ValueError(f"Número de categorias inválido: {e}")

# ============================================================================
# EXPORTAÇÃO DA PARTE 1
# ============================================================================

# Esta é a PARTE 1/4 do Terminal V1
# Contém: configurações, imports, classes básicas e funções utilitárias

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


if __name__ == "__main__":
    main()

