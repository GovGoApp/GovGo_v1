#!/usr/bin/env python3
"""
govgo_search_terminal_v1_part1.py - PARTE 1/4
Sistema de Busca PNCP V1 - Interface Terminal Interativa 
========================================================

🚀 MIGRAÇÃO V0 → V1 (PARTE 1/4):
• Baseado no GvG_SP_Search_Terminal_v9.py
• Sistema unificado de busca para GovGo V1  
• Nova base Supabase V1: hemztmtbejcbhgfmsvfq
• Interface Rich modernizada
• Código modular em 4 partes

📋 ESTRUTURA MODULAR:
• PARTE 1: Configurações, imports, classes básicas
• PARTE 2: Funções de menu e interface
• PARTE 3: Funções de busca e processamento  
• PARTE 4: Função principal e execução

🎯 FUNCIONALIDADES V1:
• Interface interativa Rich com menus coloridos
• Busca semântica, palavras-chave e híbrida
• Sistema de relevância 3 níveis com IA
• Processamento inteligente de consultas V1
• Exportação JSON/PDF/Excel/LOG
• Análise de documentos com docling V1
• Configurações dinâmicas e histórico de buscas
"""

import os
import sys
import time
import json
import locale
import argparse
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
sys.path.insert(0, str(current_dir))

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

if __name__ == "__main__":
    print("🚀 GovGo Search Terminal V1 - PARTE 1/4")
    print("📋 Configurações, imports e classes básicas carregadas!")
    print("⚠️ Execute o arquivo principal govgo_search_terminal_v1.py")
