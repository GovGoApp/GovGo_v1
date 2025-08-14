#!/usr/bin/env python3
"""
govgo_search_prompt_v1.py
Sistema de Busca PNCP V1 via Linha de Comando - Migração do Terminal v9 e Prompt v0
===================================================================================

🚀 MIGRAÇÃO V0 → V1:
• Baseado no GvG_Search_Prompt_v0.py (linha de comando)
• Sistema unificado de busca para GovGo V1
• Nova base Supabase V1: hemztmtbejcbhgfmsvfq
• Configurações atualizadas do .env V1
• Código limpo e modernizado

🎯 FUNCIONALIDADES PRINCIPAIS:
• Busca semântica, palavras-chave e híbrida com IA
• Sistema de relevância 3 níveis (sem filtro, flexível, restritivo)
• Três abordagens: direta, correspondência, filtro por categorias
• Processamento inteligente v1 com condições SQL automáticas
• Exportação automática em JSON e LOG detalhado
• Suporte a negation embeddings e filtros avançados

🔧 USO BÁSICO:
    python govgo_search_prompt_v1.py --prompt "sua consulta aqui"

📋 PARÂMETROS DISPONÍVEIS:
    --prompt TEXT              🔍 Query de busca (OBRIGATÓRIO)
    --search {1,2,3}, -S, -s  🤖 Tipo: 1=Semântica, 2=Palavras-chave, 3=Híbrida (padrão: 1)
    --approach {1,2,3}, -A, -a 📊 Abordagem: 1=Direta, 2=Correspondência, 3=Filtro (padrão: 3)
    --relevance {1,2,3}, -R, -r 🎯 Relevância: 1=sem filtro, 2=flexível, 3=restritivo (padrão: 1)
    --order {1,2,3}, -O, -o    📈 Ordenação: 1=Similaridade, 2=Data, 3=Valor (padrão: 3)
    --intelligent, -I, -i      🧠 Toggle processamento inteligente (flag)
    --max_results INT         📝 Número máximo de resultados (padrão: 30)
    --top_cat INT             🏷️  Número de TOP categorias (padrão: 10)
    --filter_expired          ⏰ Filtrar contratações encerradas (flag, padrão: ativo)
    --negation_emb            🚫 Usar negation embeddings (flag, padrão: ativo)
    --debug                   🐛 Interface visual com barras de progresso (flag)
    --output_dir PATH         📁 Diretório de saída (padrão: pasta reports)
    --help                    ❓ Mostrar ajuda completa

💾 ARQUIVOS DE SAÍDA:
    - JSON: Resultados estruturados para análise/importação
    - LOG: Arquivo detalhado com tabelas, metadados e parâmetros

🎯 EXEMPLOS PRÁTICOS:
    # Busca semântica simples
    python govgo_search_prompt_v1.py --prompt "notebooks para escolas"
    
    # Busca híbrida com filtro restritivo e interface visual
    python govgo_search_prompt_v1.py --prompt "limpeza hospitalar" -s 3 -r 3 --debug
    
    # Busca com negation embeddings
    python govgo_search_prompt_v1.py --prompt "TI --terceirização --outsourcing" -i --debug
    
    # Busca por correspondência de categorias
    python govgo_search_prompt_v1.py --prompt "uniformes escolares" -a 2 -o 1 --debug
    
    # Exemplo completo com todos os aliases
    python govgo_search_prompt_v1.py --prompt "medicamentos" -s 3 -a 3 -r 2 -o 3 -i

⚙️ REQUISITOS:
• Sistema V1 configurado (govgo_search_engine_v1.py)
• Banco PostgreSQL com pgvector (Supabase V1)
• OpenAI API key para processamento inteligente
• Rich library para interface visual (opcional)
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
from pathlib import Path

# Adicionar path do módulo V1
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

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
        intelligent_semantic_search as semantic_search,
        intelligent_keyword_search as keyword_search,
        intelligent_hybrid_search as hybrid_search,
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
    print("💡 Verifique se govgo_search_engine_v1.py está na pasta!")
    sys.exit(1)

# Importar processador de documentos V1
try:
    from govgo_document_processor_v1 import (
        SearchQueryProcessor,
        get_query_processor
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

# Diretórios V1
BASE_PATH = os.getenv('BASE_PATH', str(Path(__file__).parent.parent / 'data'))
RESULTS_PATH = os.getenv('RESULTS_PATH', str(Path(BASE_PATH) / 'reports'))
FILES_PATH = os.getenv('FILES_PATH', str(Path(BASE_PATH) / 'files'))

# Constantes padrão
MIN_RESULTS = 5
MAX_RESULTS = 50  # Aumentado para V1
MAX_TOKENS = 2000
SEMANTIC_WEIGHT = 0.75

# Configurar locale para formatação de valores
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

# ============================================================================
# SISTEMA DE PROGRESSO VISUAL (RICH)
# ============================================================================

def create_progress_display(console=None):
    """Cria interface de progresso visual com Rich usando console compartilhado."""
    if not RICH_AVAILABLE:
        return None
    
    if console is None:
        console = Console()
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
        expand=True
    )

def safe_print(message, debug_mode=False, console_obj=None):
    """Imprime mensagem de forma segura com ou sem Rich."""
    if debug_mode and RICH_AVAILABLE and console_obj:
        console_obj.print(message)
    else:
        print(message)

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def setup_logging(output_path, query):
    """Configura sistema de logging para arquivo."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
    query_clean = query_clean.upper().replace(" ", "_")[:30]
    
    log_filename = Path(output_path) / f"Busca_{query_clean}_LOG_{timestamp}.log"
    
    # Criar diretório se não existir
    log_filename.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar logger
    logger = logging.getLogger('GovGo_V1_Search')
    logger.setLevel(logging.INFO)
    
    # Remover handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configurar handler para arquivo
    handler = logging.FileHandler(log_filename, encoding='utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger, str(log_filename)

# ============================================================================
# FUNÇÕES AUXILIARES PARA BUSCA
# ============================================================================

def get_top_categories_for_query(query_text, top_n=10, use_negation_embeddings=True, search_type=1):
    """Busca as TOP N categorias mais similares à query."""
    try:
        engine = GovGoSearchEngine()
        if not engine.connect():
            return []
        
        categories = engine.get_top_categories(query_text, top_n)
        return categories
        
    except Exception as e:
        print(f"❌ Erro ao buscar TOP categorias: {e}")
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

# ============================================================================
# FUNÇÕES DE BUSCA ADAPTADAS PARA V1
# ============================================================================

def direct_search(query_text, search_type, limit=MAX_RESULTS, filter_expired=True, use_negation_embeddings=True):
    """Busca direta (sem categorias) - V1."""
    try:
        # Verificar status do processamento inteligente
        intelligent_status = get_intelligent_status()
        enable_intelligent = intelligent_status.get('intelligent_processing_enabled', False)
        
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
        print(f"❌ Erro na busca direta: {e}")
        return [], 0.0

def correspondence_search(query_text, top_categories, limit=MAX_RESULTS, filter_expired=True):
    """Busca por correspondência categórica - V1."""
    try:
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        engine = GovGoSearchEngine()
        if not engine.connect():
            return [], 0.0
        
        # Buscar contratos com categorias correspondentes
        # TODO: Implementar lógica específica de correspondência
        # Por enquanto, usar busca semântica como fallback
        results, confidence = engine.semantic_search(query_text, limit)
        
        # Adicionar informações de correspondência
        for result in results:
            result["search_approach"] = "correspondence"
            result["matched_categories"] = category_codes[:3]  # Primeiras 3 categorias
        
        return results, confidence
        
    except Exception as e:
        print(f"❌ Erro na busca por correspondência: {e}")
        return [], 0.0

def category_filtered_search(query_text, search_type, top_categories, limit=MAX_RESULTS, filter_expired=True, use_negation_embeddings=True):
    """Busca com filtro categórico - V1."""
    try:
        category_codes = [cat['codigo'] for cat in top_categories]
        
        if not category_codes:
            return [], 0.0
        
        # Executar busca normal primeiro
        all_results, confidence = direct_search(query_text, search_type, limit * 2, filter_expired, use_negation_embeddings)
        
        if not all_results:
            return [], 0.0
        
        # TODO: Implementar filtro real por categorias
        # Por enquanto, retornar todos os resultados limitados
        filtered_results = all_results[:limit]
        
        for result in filtered_results:
            result["search_approach"] = "category_filtered"
            result["matched_categories"] = category_codes[:3]
        
        return filtered_results, confidence
        
    except Exception as e:
        print(f"❌ Erro na busca com filtro categórico: {e}")
        return [], 0.0

# ============================================================================
# FUNÇÕES DE EXPORTAÇÃO E LOGGING
# ============================================================================

def generate_export_filename(query, search_type_id, search_approach, relevance_level, sort_mode, intelligent_enabled, output_path, extension="json"):
    """Gera nome padronizado para arquivos de exportação V1."""
    try:
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean.upper().replace(" ", "_")[:30]
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Garantir que o diretório existe
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        intelligent_flag = 1 if intelligent_enabled else 0
        
        filename = f"Busca_{query_clean}_S{search_type_id}_A{search_approach}_R{relevance_level}_O{sort_mode}_I{intelligent_flag}_{timestamp}.{extension}"
        
        return str(Path(output_path) / filename)
    
    except Exception as e:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"Busca_ERRO_{timestamp}.{extension}"
        return str(Path(output_path) / filename)

def export_results_to_json(results, query, search_type_id, search_approach, relevance_level, sort_mode, output_path):
    """Exporta resultados para JSON - V1."""
    try:
        data = []
        for result in results:
            details = result.get("details", {})
            if details:
                record = {
                    "rank": result.get("rank", 0),
                    "id": result.get("id", ""),
                    "similarity": safe_float_conversion(result.get("similarity", 0)),
                    "orgao": details.get("orgao_entidade_razao_social", ""),
                    "unidade": details.get("unidade_orgao_nome_unidade", ""),
                    "municipio": details.get("unidade_orgao_municipio_nome", ""),
                    "uf": details.get("unidade_orgao_uf_sigla", ""),
                    "valor_estimado": safe_float_conversion(details.get("valor_total_estimado", 0)),
                    "valor_homologado": safe_float_conversion(details.get("valor_total_homologado", 0)),
                    "data_inclusao": convert_datetime_to_string(details.get("data_inclusao", "")),
                    "data_abertura": convert_datetime_to_string(details.get("data_abertura_proposta", "")),
                    "data_encerramento": convert_datetime_to_string(details.get("data_encerramento_proposta", "")),
                    "modalidade_id": details.get("modalidade_id", ""),
                    "modalidade_nome": details.get("modalidade_nome", ""),
                    "disputa_id": details.get("modo_disputa_id", ""),
                    "disputa_nome": details.get("modo_disputa_nome", ""),
                    "usuario": details.get("usuario_nome", ""),
                    "poder": details.get("orgao_entidade_poder_id", ""),
                    "esfera": details.get("orgao_entidade_esfera_id", ""),
                    "link_sistema": details.get("link_sistema_origem", ""),
                    "descricao": details.get("descricaoCompleta", "")
                }
                data.append(record)
        
        # Verificar status do processamento inteligente
        intelligent_status = get_intelligent_status()
        intelligent_enabled = intelligent_status.get('intelligent_processing_enabled', False)
        
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
                "total_results": len(data),
                "govgo_version": "V1",
                "engine": "govgo_search_engine_v1"
            },
            "results": data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    except Exception as e:
        print(f"❌ Erro ao exportar JSON: {e}")
        return None

def log_top_categories_table(logger, categories):
    """Adiciona tabela de TOP categorias ao log."""
    if not categories:
        logger.info("TOP CATEGORIAS: Nenhuma categoria encontrada")
        return
    
    logger.info("="*80)
    logger.info("TOP CATEGORIAS DA QUERY (V1)")
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
    logger.info(f"RESUMO DOS RESULTADOS V1 - {SEARCH_APPROACHES[search_approach]['name'].upper()}")
    logger.info("="*100)
    logger.info(f"{'Rank':<6} {'Órgão':<40} {'Local':<30} {'Similaridade':<12} {'Valor (R$)':<17} {'Data Encerr.':<12}")
    logger.info("-"*100)
    
    for result in results:
        details = result.get("details", {})
        valor = format_currency(details.get("valor_total_estimado", 0)) if details else "N/A"
        data_encerramento = format_date(details.get("data_encerramento_proposta", "N/A")) if details else "N/A"
        
        unidade = details.get('unidade_orgao_nome_unidade', 'N/A')
        if len(unidade) > 40:
            unidade = unidade[:37] + "..."
        
        municipio = details.get('unidade_orgao_municipio_nome', 'N/A')
        uf = details.get('unidade_orgao_uf_sigla', '')
        local = f"{municipio}/{uf}" if uf else municipio
        if len(local) > 30:
            local = local[:27] + "..."
        
        logger.info(f"{result['rank']:<6} {unidade:<40} {local:<30} {result['similarity']:.4f}      {valor:<17} {str(data_encerramento):<12}")
    
    logger.info("="*100)

# ============================================================================
# FUNÇÃO PRINCIPAL DE BUSCA
# ============================================================================

def perform_search(args, logger):
    """Executa a busca conforme parâmetros fornecidos com progresso visual - V1."""
    start_time = time.time()
    
    # Configurar interface de progresso visual
    progress = None
    console = None
    if args.debug and RICH_AVAILABLE:
        console = Console()
        progress = create_progress_display(console)
        
        # Mostrar cabeçalho visual V1
        header = Panel.fit(
            f"🚀 [bold cyan]GovGo Search PNCP V1[/bold cyan]\n"
            f"📝 Query: [yellow]\"{args.prompt}\"[/yellow]\n"
            f"🔍 Tipo: [green]{SEARCH_TYPES[args.search]['name']}[/green] | "
            f"📊 Abordagem: [blue]{SEARCH_APPROACHES[args.approach]['name']}[/blue] | "
            f"🎯 Relevância: [magenta]Nível {args.relevance}[/magenta]",
            title="[bold]Sistema de Busca PNCP V1[/bold]",
            border_style="cyan"
        )
        console.print(header)
    
    # Log básico
    logger.info("="*100)
    logger.info("INICIANDO BUSCA GOVGO V1")
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
    logger.info("Processamento: GovGo Search Engine V1")
    
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
                task1 = progress.add_task("[bold cyan][1/6][/bold cyan] 🔧 Configuração inicial V1...", total=100)
                
                # Configurar filtro de relevância
                progress.update(task1, advance=30)
                try:
                    current_relevance_status = get_relevance_filter_status()
                    current_level = current_relevance_status.get('relevance_filter_level', 1)
                    
                    if args.relevance != current_level:
                        set_relevance_filter_level(args.relevance)
                        level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                        logger.info(f"Filtro de Relevância V1: {level_names.get(args.relevance, 'DESCONHECIDO')} (nível {args.relevance})")
                    else:
                        level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                        logger.info(f"Filtro de Relevância V1: {level_names.get(current_level, 'DESCONHECIDO')} (sem alterações)")
                except Exception as e:
                    logger.warning(f"❌ Erro ao configurar filtro de relevância: {e}")
                
                # Processamento inteligente V1
                progress.update(task1, advance=40)
                if DOCUMENT_PROCESSOR_AVAILABLE:
                    try:
                        processor = get_query_processor()
                        intelligent_info = processor.process_query(original_query)
                        processed_query = intelligent_info.get('search_terms', original_query)
                        logger.info(f"Query Processada V1: \"{processed_query}\"")
                        if intelligent_info.get('sql_conditions'):
                            logger.info(f"Condições SQL V1: {len(intelligent_info['sql_conditions'])}")
                    except Exception as e:
                        logger.warning(f"Erro no processamento inteligente V1: {e}")
                
                progress.update(task1, completed=100)
                
                # [2/6] BUSCA DE CATEGORIAS
                if args.approach in [2, 3]:
                    task2 = progress.add_task("[bold green][2/6][/bold green] 📂 Buscando categorias TOP V1...", total=100)
                    logger.info(f"\nBuscando TOP {args.top_cat} categorias V1...")
                    
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
                task3 = progress.add_task("[bold blue][3/6][/bold blue] 🔎 Executando busca principal V1...", total=100)
                
                if args.approach == 1:  # DIRETA
                    query_for_search = processed_query
                    logger.info(f"\nExecutando busca direta V1: \"{query_for_search}\"")
                    progress.update(task3, advance=50)
                    results, confidence = direct_search(query_for_search, args.search, args.max_results, args.filter_expired, args.negation_emb)
                
                elif args.approach == 2:  # CORRESPONDÊNCIA
                    logger.info(f"\nExecutando busca por correspondência V1: \"{original_query}\"")
                    progress.update(task3, advance=50)
                    results, confidence = correspondence_search(original_query, categories, args.max_results, args.filter_expired)
                
                elif args.approach == 3:  # FILTRO DE CATEGORIA
                    logger.info(f"\nExecutando busca com filtro categórico V1: \"{original_query}\"")
                    progress.update(task3, advance=50)
                    results, confidence = category_filtered_search(original_query, args.search, categories, args.max_results, args.filter_expired, args.negation_emb)
                
                else:
                    logger.error("Abordagem de busca inválida!")
                    return None, None, None, 0
                
                progress.update(task3, completed=100)
                
                if not results:
                    logger.warning("Nenhum resultado encontrado")
                    return [], categories, 0, time.time() - start_time
                
                # [4/6] FILTRO DE RELEVÂNCIA
                task4 = progress.add_task("[bold magenta][4/6][/bold magenta] 🎯 Filtro de relevância V1...", total=100)
                progress.update(task4, advance=50)
                logger.info(f"✅ Filtro de relevância V1 aplicado (nível {args.relevance})")
                progress.update(task4, completed=100)
                
                # [5/6] PROCESSAMENTO DOS RESULTADOS
                task5 = progress.add_task("[bold orange][5/6][/bold orange] 📊 Processando resultados V1...", total=100)
                
                # Aplicar ordenação
                progress.update(task5, advance=33)
                if args.order == 1:
                    logger.info("Ordenação V1: por similaridade (decrescente)")
                elif args.order == 2:
                    def parse_date_safe(val):
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
                    results.sort(key=lambda x: parse_date_safe(x.get("details", {}).get("data_encerramento_proposta", None)))
                    logger.info("Ordenação V1: por data de encerramento (ascendente)")
                elif args.order == 3:
                    results.sort(key=lambda x: float(x.get("details", {}).get("valor_total_estimado", 0) or 0), reverse=True)
                    logger.info("Ordenação V1: por valor estimado (decrescente)")
                
                # Atualizar ranks
                progress.update(task5, advance=33)
                for i, result in enumerate(results, 1):
                    result["rank"] = i
                
                progress.update(task5, completed=100)
                
                # [6/6] EXPORTAÇÃO E FINALIZAÇÃO
                task6 = progress.add_task("[bold red][6/6][/bold red] 💾 Finalizando V1...", total=100)
                
                progress.update(task6, advance=50)
                search_time = time.time() - start_time
                
                # Log das tabelas
                log_results_table(logger, results, args.approach)
                
                logger.info(f"\nTempo total de busca V1: {search_time:.4f} segundos")
                logger.info(f"Confiança V1: {confidence:.4f}")
                
                progress.update(task6, completed=100)
            
            # Mostrar resumo final visual
            console.print("\n" + "="*50)
            console.print(Panel.fit(
                f"✅ [bold green]Busca V1 Concluída![/bold green]\n"
                f"📊 Resultados: [cyan]{len(results)}[/cyan]\n"
                f"⏱️ Tempo: [yellow]{search_time:.2f}s[/yellow]\n"
                f"🎯 Confiança: [magenta]{confidence:.2f}[/magenta]\n"
                f"🚀 Engine: [blue]GovGo V1[/blue]",
                title="[bold]Resultado Final V1[/bold]",
                border_style="green"
            ))
        
        else:
            # Modo sem interface visual
            logger.info("Executando busca V1 sem interface visual")
            
            # Configuração inicial
            try:
                current_relevance_status = get_relevance_filter_status()
                current_level = current_relevance_status.get('relevance_filter_level', 1)
                
                if args.relevance != current_level:
                    set_relevance_filter_level(args.relevance)
                    level_names = {1: "SEM FILTRO", 2: "FLEXÍVEL", 3: "RESTRITIVO"}
                    logger.info(f"Filtro de Relevância V1: {level_names.get(args.relevance, 'DESCONHECIDO')}")
            except Exception as e:
                logger.warning(f"❌ Erro ao configurar filtro de relevância: {e}")
            
            # Processamento inteligente
            if DOCUMENT_PROCESSOR_AVAILABLE:
                try:
                    processor = get_query_processor()
                    intelligent_info = processor.process_query(original_query)
                    processed_query = intelligent_info.get('search_terms', original_query)
                    logger.info(f"Query Processada V1: \"{processed_query}\"")
                except Exception as e:
                    logger.warning(f"Erro no processamento inteligente V1: {e}")
            
            # Buscar categorias se necessário
            if args.approach in [2, 3]:
                logger.info(f"\nBuscando TOP {args.top_cat} categorias V1...")
                categories = get_top_categories_for_query(processed_query, args.top_cat, args.negation_emb, args.search)
                
                if not categories:
                    logger.error("Nenhuma categoria encontrada")
                    return None, None, None, 0
                
                log_top_categories_table(logger, categories)
            
            # Executar busca
            if args.approach == 1:
                results, confidence = direct_search(processed_query, args.search, args.max_results, args.filter_expired, args.negation_emb)
            elif args.approach == 2:
                results, confidence = correspondence_search(original_query, categories, args.max_results, args.filter_expired)
            elif args.approach == 3:
                results, confidence = category_filtered_search(original_query, args.search, categories, args.max_results, args.filter_expired, args.negation_emb)
            else:
                logger.error("Abordagem inválida!")
                return None, None, None, 0
            
            if not results:
                logger.warning("Nenhum resultado encontrado")
                return [], categories, 0, time.time() - start_time
            
            # Aplicar ordenação e processar
            if args.order == 2:
                def parse_date_safe(val):
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
            elif args.order == 3:
                results.sort(key=lambda x: float(x.get("details", {}).get("valortotalestimado", 0) or 0), reverse=True)
            
            # Atualizar ranks
            for i, result in enumerate(results, 1):
                result["rank"] = i
            
            search_time = time.time() - start_time
            log_results_table(logger, results, args.approach)
            logger.info(f"\nTempo total V1: {search_time:.4f} segundos")
            logger.info(f"Confiança V1: {confidence:.4f}")
        
        return results, categories, confidence, time.time() - start_time
        
    except Exception as e:
        logger.error(f"Erro durante a busca V1: {e}")
        if console:
            console.print(f"[bold red]❌ ERRO V1: {e}[/bold red]")
        return None, None, None, 0

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal do sistema V1."""
    parser = argparse.ArgumentParser(
        description='Sistema de Busca PNCP V1 via Linha de Comando',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Suporte para --h e --help
    if '--h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    # Argumentos obrigatórios
    parser.add_argument('--prompt', required=True, help='Query de busca (obrigatório)')
    
    # Argumentos opcionais V1
    parser.add_argument('--search', '--S', '--s', type=int, choices=[1, 2, 3], default=1,
                       help='Tipo de busca: 1=Semântica, 2=Palavras-chave, 3=Híbrida (padrão: 1)')
    parser.add_argument('--approach', '--A', '--a', type=int, choices=[1, 2, 3], default=3,
                       help='Abordagem: 1=Direta, 2=Correspondência, 3=Filtro (padrão: 3)')
    parser.add_argument('--relevance', '--R', '--r', type=int, choices=[1, 2, 3], default=1,
                       help='Nível de relevância: 1=sem filtro, 2=flexível, 3=restritivo (padrão: 1)')
    parser.add_argument('--order', '--O', '--o', type=int, choices=[1, 2, 3], default=3,
                       help='Ordenação: 1=Similaridade, 2=Data, 3=Valor (padrão: 3)')
    parser.add_argument('--intelligent', '--I', '--i', action='store_true', default=False,
                       help='Toggle do processamento inteligente V1')
    parser.add_argument('--max_results', type=int, default=30,
                       help='Número máximo de resultados (padrão: 30)')
    parser.add_argument('--top_cat', type=int, default=10,
                       help='Número de TOP categorias (padrão: 10)')
    parser.add_argument('--filter_expired', action='store_true', default=True,
                       help='Filtrar contratações encerradas (padrão: True)')
    parser.add_argument('--negation_emb', action='store_true', default=True,
                       help='Usar negation embeddings (padrão: True)')
    parser.add_argument('--debug', action='store_true', default=False,
                       help='Interface visual com progresso (padrão: False)')
    parser.add_argument('--output_dir', default=RESULTS_PATH,
                       help=f'Diretório de saída (padrão: {RESULTS_PATH})')
    
    args = parser.parse_args()
    
    # Verificar prompt
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
    
    # Processar toggle inteligente se solicitado
    if args.intelligent:
        try:
            current_status = get_intelligent_status()
            current_enabled = current_status.get('intelligent_processing_enabled', False)
            
            new_status = toggle_intelligent_processing()
            new_enabled = new_status.get('intelligent_processing_enabled', False)
            
            if new_enabled != current_enabled:
                status_text = "ATIVADO" if new_enabled else "DESATIVADO"
                print(f"✅ Processamento Inteligente V1 {status_text}")
                logger.info(f"Processamento Inteligente V1 {status_text}")
            else:
                print(f"⚠️ Status V1 mantido: {'ATIVADO' if new_enabled else 'DESATIVADO'}")
        except Exception as e:
            print(f"❌ Erro ao processar --intelligent V1: {e}")
            logger.error(f"Erro ao processar --intelligent V1: {e}")
    
    # Executar busca V1
    try:
        console = None
        
        if args.debug and RICH_AVAILABLE:
            console = Console()
            console.print("\n🚀 [bold cyan]Iniciando Sistema de Busca PNCP V1[/bold cyan]")
            console.print("📊 [yellow]Modo DEBUG ativado - Interface visual V1[/yellow]\n")
        elif args.debug and not RICH_AVAILABLE:
            print("\n🚀 Iniciando Sistema de Busca PNCP V1")
            print("⚠️ Rich não disponível - modo texto V1\n")
        
        results, categories, confidence, search_time = perform_search(args, logger)
        
        if results is None:
            error_msg = "ERRO V1: Falha na execução da busca"
            logger.error("Falha na execução da busca V1")
            if console:
                console.print(f"[bold red]{error_msg}[/bold red]")
            else:
                print(error_msg)
            sys.exit(1)
        
        if not results:
            warning_msg = "AVISO V1: Busca concluída sem resultados"
            logger.warning("Busca V1 sem resultados")
            if console:
                console.print(f"[bold yellow]{warning_msg}[/bold yellow]")
            else:
                print(warning_msg)
            return
        
        # Exportar JSON V1
        json_filename = export_results_to_json(
            results, args.prompt, args.search, args.approach, args.relevance, args.order, args.output_dir
        )
        
        if json_filename:
            logger.info(f"\nRESULTADOS V1 EXPORTADOS:")
            logger.info(f"JSON: {json_filename}")
            logger.info(f"LOG: {log_filename}")
            
            success_msg = f"SUCESSO V1: Busca concluída!\nResultados: {len(results)}\nJSON: {json_filename}\nLOG: {log_filename}"
            
            if console:
                console.print("\n" + "="*50)
                console.print(Panel.fit(
                    f"✅ [bold green]Busca V1 Finalizada![/bold green]\n"
                    f"📁 [cyan]JSON:[/cyan] [white]{Path(json_filename).name}[/white]\n"
                    f"📋 [cyan]LOG:[/cyan] [white]{Path(log_filename).name}[/white]\n"
                    f"📊 [cyan]Resultados:[/cyan] [yellow]{len(results)}[/yellow]\n"
                    f"⏱️ [cyan]Tempo:[/cyan] [magenta]{search_time:.2f}s[/magenta]\n"
                    f"🚀 [cyan]Engine:[/cyan] [blue]GovGo V1[/blue]",
                    title="[bold]Exportação V1 Concluída[/bold]",
                    border_style="green"
                ))
            else:
                print(success_msg)
        else:
            error_msg = "ERRO V1: Falha ao exportar resultados"
            logger.error("Falha ao exportar resultados V1")
            if console:
                console.print(f"[bold red]{error_msg}[/bold red]")
            else:
                print(error_msg)
            sys.exit(1)
    
    except Exception as e:
        error_msg = f"ERRO FATAL V1: {e}"
        logger.error(f"Erro fatal V1: {e}")
        console = Console() if args.debug and RICH_AVAILABLE else None
        if console:
            console.print(f"[bold red]{error_msg}[/bold red]")
        else:
            print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
