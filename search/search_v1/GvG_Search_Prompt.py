"""
GvG_Search_Prompt.py
Execução única (prompt) do Sistema de Busca PNCP v2 Otimizado.

Derivado de GvG_Search_Terminal.py removendo interface interativa e menus.
Mantém:
  • 3 tipos de busca (semântica / palavras‑chave / híbrida)
  • 3 abordagens (direta / correspondência / filtro)
  • Filtro de relevância (níveis 1–3)
  • Negation embeddings (positivos para categorias / completos para embedding)
  • Processamento inteligente (toggle opcional)
  • Exportação: JSON, XLSX, PDF (mesmo padrão de nomenclatura v9)
  • Barra de progresso (opcional via --debug)

Argumentos principais (com short forms):
  --prompt (obrigatório)
  --s / --search      (default 1)
  --a / --approach    (default 3)
  --r / --relevance   (default 2)
  --o / --order       (default 1)

Outros:
  --max_results (30 default)
  --top_cat (10 default)
  --negation_emb (ativa por default, usar --no-negation para desativar)
  --filter_expired (ativa por default, usar --no-filter-expired para desativar)
  --intelligent (faz toggle na flag persistida)
  --export (json|xlsx|pdf|all) pode repetir ou usar 'all' (default json)
  --output_dir (diretório destino para exportações)
  --debug (exibe progresso 6 etapas Rich)

Saídas:
  • LOG detalhado: Busca_{QUERY}_LOG_{timestamp}.log
  • Arquivos de exportação conforme formatos escolhidos

"""

import os
import sys
import re
import json
import time
import locale
import argparse
import logging
from datetime import datetime
from typing import List, Tuple

import pandas as pd

# Rich (opcional)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn, TimeRemainingColumn
    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False
    Console = None

# PDF (opcional)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

# Locale PT-BR
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# =====================================================================================
# IMPORTAÇÕES DOS MÓDULOS OTIMIZADOS
# =====================================================================================
from gvg_preprocessing import (
    format_currency,
    format_date,
    decode_poder,
    decode_esfera,
    SearchQueryProcessor
)
from gvg_ai_utils import (
    extract_pos_neg_terms,
    generate_keywords,  # mantida para potencial uso futuro
)
from gvg_search_core import (
    semantic_search,
    keyword_search,
    hybrid_search,
    toggle_intelligent_processing,
    toggle_intelligent_debug,
    get_intelligent_status,
    set_relevance_filter_level,
    get_relevance_filter_status,
)
from gvg_search_core import (
    get_top_categories_for_query,
    correspondence_search as categories_correspondence_search,
    category_filtered_search as categories_category_filtered_search
)
from gvg_exporters import (
    generate_export_filename,
    export_results_json,
    export_results_excel,
    export_results_pdf
)

# =====================================================================================
# CONSTANTES / CONFIGURAÇÃO
# =====================================================================================
SEMANTIC_WEIGHT = 0.75  # (usado internamente nos módulos de busca)
DEFAULT_MAX_RESULTS = 30
DEFAULT_TOP_CATEGORIES = 10

SEARCH_TYPES = {
    1: {"name": "Semântica"},
    2: {"name": "Palavras-chave"},
    3: {"name": "Híbrida"}
}
SEARCH_APPROACHES = {
    1: {"name": "Direta"},
    2: {"name": "Correspondência"},
    3: {"name": "Filtro"}
}
SORT_MODES = {
    1: {"name": "Similaridade"},
    2: {"name": "Data de Encerramento"},
    3: {"name": "Valor Estimado"}
}
RELEVANCE_LEVELS = {
    1: {"name": "Sem filtro"},
    2: {"name": "Flexível"},
    3: {"name": "Restritivo"}
}

# =====================================================================================
# LOGGING
# =====================================================================================
def setup_logging(output_dir: str, query: str) -> Tuple[logging.Logger, str]:
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    clean = re.sub(r'[^\w\s-]', '', query).strip().upper()
    clean = re.sub(r'\s+', '_', clean)[:30]
    logfile = os.path.join(output_dir, f"Busca_{clean}_LOG_{ts}.log")
    logger = logging.getLogger(f'GvG_Search_Prompt_{ts}')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(fh)
    return logger, logfile


# =====================================================================================
# BUSCA / ORQUESTRAÇÃO
# =====================================================================================
def sort_results(results: List[dict], order_mode: int):
    if not results:
        return results
    if order_mode == 1:
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
    elif order_mode == 2:
        # Data de encerramento (ascendente) replicando lógica robusta
        from datetime import datetime as _dt
        def parse_date(val):
            if not val:
                return _dt(9999,12,31)
            if isinstance(val, _dt):
                return val
            s = str(val)[:10]
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try: return _dt.strptime(s, fmt)
                except Exception: continue
            return _dt(9999,12,31)
        return sorted(results, key=lambda x: parse_date(x.get('details', {}).get('dataencerramentoproposta') or x.get('details', {}).get('dataEncerramentoProposta')))
    elif order_mode == 3:
        return sorted(results, key=lambda x: (x.get('details', {}).get('valortotalestimado') or x.get('details', {}).get('valorTotalEstimado') or 0), reverse=True)
    return results

def perform_search(params, logger, console=None):
    start = time.time()
    intelligent_status = get_intelligent_status()
    intelligent_enabled = intelligent_status['intelligent_processing']
    relevance_status = get_relevance_filter_status()

    # Dados base
    original_query = params.prompt
    pos_terms, neg_terms = ("", "")
    if params.negation_emb and params.search in (1,3):
        try:
            pos_terms, neg_terms = extract_pos_neg_terms(original_query)
        except Exception:
            pos_terms = original_query
    else:
        pos_terms = original_query

    # Processamento inteligente para base de categorias
    base_category_terms = pos_terms
    processed_info = None
    try:
        processor = SearchQueryProcessor()
        processed_info = processor.process_query(original_query)
        processed_terms = processed_info.get('search_terms') or ''
        if processed_terms:
            cat_pos, _ = extract_pos_neg_terms(processed_terms) if (params.negation_emb and params.search in (1,3)) else (processed_terms, "")
            if cat_pos.strip():
                base_category_terms = cat_pos.strip()
    except Exception as e:
        logger.info(f"[WARN] Falha processamento inteligente: {e}")

    # Progress
    progress = None
    if params.debug and RICH_AVAILABLE and console:
        progress = Progress(
            SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn(), console=console
        )

    categories = []
    results = []
    confidence = 0.0

    def log_basic_header():
        logger.info("="*100)
        logger.info("INICIANDO BUSCA GOVGO (PROMPT MODE)")
        logger.info("="*100)
        logger.info(f"Query: \"{original_query}\"")
        logger.info(f"Tipo: {SEARCH_TYPES[params.search]['name']}")
        logger.info(f"Abordagem: {SEARCH_APPROACHES[params.approach]['name']}")
        logger.info(f"Relevância: {RELEVANCE_LEVELS[params.relevance]['name']} (nível {params.relevance})")
        logger.info(f"Ordenação: {SORT_MODES[params.order]['name']}")
        logger.info(f"Max Resultados: {params.max_results}")
        logger.info(f"TOP Categorias: {params.top_cat}")
        logger.info(f"Filtrar Encerradas: {params.filter_expired}")
        logger.info(f"Negation Embeddings: {params.negation_emb}")
        logger.info(f"Processamento Inteligente Ativo: {intelligent_enabled}")
        logger.info("="*100)

    log_basic_header()

    if progress:
        console.print(Panel.fit(
            f"🚀 GvG Search Prompt\nQuery: [yellow]{original_query}[/yellow]", title="Execução", border_style="cyan"
        ))
        progress.start()
        t1 = progress.add_task("[1/6] Configuração inicial", total=100)

    # [1/6] Configuração: ajustar filtro relevância se necessário
    if params.relevance != relevance_status['level']:
        try:
            set_relevance_filter_level(params.relevance)
        except Exception as e:
            logger.info(f"[WARN] Falha set_relevance_filter_level: {e}")
    # Toggle inteligente se flag passada
    if params.intelligent:
        try:
            toggle_intelligent_processing(not intelligent_enabled)
            intelligent_enabled = get_intelligent_status()['intelligent_processing']
            logger.info(f"Processamento Inteligente agora: {intelligent_enabled}")
        except Exception as e:
            logger.info(f"[WARN] Falha toggle inteligente: {e}")
    if progress:
        progress.update(t1, completed=100)

    # [2/6] Categorias (para abordagens 2/3)
    if progress:
        t2 = progress.add_task("[2/6] Buscando categorias", total=100)
    if params.approach in (2,3):
        logger.info(f"Buscando TOP {params.top_cat} categorias com termos-base: '{base_category_terms}'")
        try:
            categories = get_top_categories_for_query(
                query_text=base_category_terms or original_query,
                top_n=params.top_cat,
                use_negation=False,
                search_type=params.search,
                console=console if params.debug and RICH_AVAILABLE else None
            )
        except Exception as e:
            logger.info(f"[ERRO] Categorias: {e}")
        if not categories:
            logger.info("Nenhuma categoria encontrada")
        else:
            _log_categories_table(logger, categories)
    if progress:
        progress.update(t2, completed=100)

    # [3/6] Busca principal
    if progress:
        t3 = progress.add_task("[3/6] Busca principal", total=100)
    try:
        if params.approach == 1:
            results, confidence = _direct_search(original_query, params)
        elif params.approach == 2:
            results, confidence, _ = _correspondence_search(original_query, params, categories, console if params.debug and RICH_AVAILABLE else None)
        elif params.approach == 3:
            results, confidence, _ = _category_filtered_search(original_query, params, categories, console if params.debug and RICH_AVAILABLE else None)
    except Exception as e:
        logger.info(f"[ERRO] Falha na busca: {e}")
    if progress:
        progress.update(t3, completed=100)

    if not results:
        elapsed = time.time() - start
        msg = f"Nenhum resultado encontrado (tempo {elapsed:.2f}s)"
        logger.info(msg)
        if console:
            console.print(f"[red]{msg}[/red]")
        return [], categories, confidence, elapsed

    # [4/6] Filtro de relevância (já aplicado dentro do core)
    if progress:
        t4 = progress.add_task("[4/6] Filtro relevância", total=100)
        progress.update(t4, completed=100)

    # [5/6] Ordenação & pós processamento
    if progress:
        t5 = progress.add_task("[5/6] Ordenando resultados", total=100)
    results = sort_results(results, params.order)
    for i, r in enumerate(results, 1):
        r['rank'] = i
    if progress:
        progress.update(t5, completed=100)

    # [6/6] Exportação tratada fora desta função
    if progress:
        t6 = progress.add_task("[6/6] Finalizando", total=100)
        progress.update(t6, completed=100)
        progress.stop()

    elapsed = time.time() - start
    logger.info(f"Tempo total: {elapsed:.2f}s | Confiança: {confidence:.4f} | Resultados: {len(results)}")
    return results, categories, confidence, elapsed

def _direct_search(query: str, params):
    if params.search == 1:
        return semantic_search(query, limit=params.max_results, filter_expired=params.filter_expired, use_negation=params.negation_emb)
    if params.search == 2:
        return keyword_search(query, limit=params.max_results, filter_expired=params.filter_expired)
    if params.search == 3:
        return hybrid_search(query, limit=params.max_results, filter_expired=params.filter_expired, use_negation=params.negation_emb)
    return [], 0.0

def _correspondence_search(query: str, params, categories, console=None):
    if not categories:
        return [], 0.0, {}
    return categories_correspondence_search(
        query_text=query,
        top_categories=categories,
        limit=params.max_results,
        filter_expired=params.filter_expired,
        console=console
    )

def _category_filtered_search(query: str, params, categories, console=None):
    if not categories:
        return [], 0.0, {}
    return categories_category_filtered_search(
        query_text=query,
        search_type=params.search,
        top_categories=categories,
        limit=params.max_results,
        filter_expired=params.filter_expired,
        use_negation=params.negation_emb,
        console=console
    )

def _log_categories_table(logger, categories: List[dict]):
    if not categories:
        return
    logger.info("TOP CATEGORIAS")
    logger.info(f"{'Rank':<6}{'Código':<12}{'Similaridade':<14}Descrição")
    for c in categories:
        logger.info(f"{c.get('rank',0):<6}{c.get('codigo',''):<12}{c.get('similarity_score',0):<14.4f}{c.get('descricao','')[:70]}")

def _print_summary(console, results: List[dict], categories: List[dict], params, confidence: float, elapsed: float, query: str):  # pragma: no cover (visual)
    console.print(Panel.fit(
        f"✅ Busca concluída\nResultados: {len(results)} | Tempo: {elapsed:.2f}s | Confiança: {confidence:.2f}",
        title="Resumo", border_style="green"))
    # Prompt negativo
    if params.negation_emb and params.search in (1,3):
        try:
            pos, neg = extract_pos_neg_terms(query)
            if neg.strip():
                console.print(f"[cyan]🎯 Negativo: [green]{pos}[/green]  --  [red]{neg}[/red][/cyan]")
        except Exception:
            pass
    if params.approach in (2,3) and categories:
        table = Table(title="TOP Categorias", show_header=True, header_style="bold magenta")
        table.add_column("Rank", width=5)
        table.add_column("Código", width=10)
        table.add_column("Similaridade", width=12)
        table.add_column("Descrição", width=60)
        for c in categories:
            table.add_row(str(c.get('rank')), c.get('codigo',''), f"{c.get('similarity_score',0):.4f}", c.get('descricao','')[:58])
        console.print(table)
    # Resultados
    res_table = Table(title="Resultados", show_header=True, header_style="bold blue")
    res_table.add_column("Rank", width=5)
    res_table.add_column("Órgão", width=38)
    res_table.add_column("Local", width=28)
    res_table.add_column("Similarity", width=10)
    res_table.add_column("Valor", width=14)
    res_table.add_column("Encerramento", width=12)
    for r in results:
        d = r.get('details', {})
        unidade = d.get('unidadeorgao_nomeunidade') or d.get('unidadeOrgao_nomeUnidade') or d.get('orgaoentidade_razaosocial') or 'N/A'
        municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or 'N/A'
        uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or 0)
        data_enc = format_date(d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or 'N/A')
        res_table.add_row(str(r.get('rank')), unidade[:38], local[:28], f"{r.get('similarity',0):.4f}", valor, str(data_enc))
    console.print(res_table)

# =====================================================================================
# ARGPARSE / MAIN
# =====================================================================================
def parse_args():
    p = argparse.ArgumentParser(description='GvG Search Prompt v2 (execução única)')
    p.add_argument('--prompt', required=True, help='Texto da busca')
    p.add_argument('--search','--s', type=int, choices=[1,2,3], default=1, help='Tipo: 1=Semântica 2=Palavras-chave 3=Híbrida (default 1)')
    p.add_argument('--approach','--a', type=int, choices=[1,2,3], default=3, help='Abordagem: 1=Direta 2=Correspondência 3=Filtro (default 3)')
    p.add_argument('--relevance','--r', type=int, choices=[1,2,3], default=2, help='Relevância: 1=Sem filtro 2=Flexível 3=Restritivo (default 2)')
    p.add_argument('--order','--o', type=int, choices=[1,2,3], default=1, help='Ordenação: 1=Similaridade 2=Data 3=Valor (default 1)')
    p.add_argument('--max_results', type=int, default=DEFAULT_MAX_RESULTS, help='Máximo de resultados (default 30)')
    p.add_argument('--top_cat', type=int, default=DEFAULT_TOP_CATEGORIES, help='TOP categorias (default 10)')
    # Negation / filtro expirados com disable
    p.add_argument('--negation_emb', dest='negation_emb', action='store_true', default=True, help='Ativar negation embeddings (default True)')
    p.add_argument('--no-negation', dest='negation_emb', action='store_false', help='Desativar negation embeddings')
    p.add_argument('--filter_expired', dest='filter_expired', action='store_true', default=True, help='Filtrar encerradas (default True)')
    p.add_argument('--no-filter-expired', dest='filter_expired', action='store_false', help='Não filtrar encerradas')
    p.add_argument('--intelligent', action='store_true', help='Toggle processamento inteligente antes da execução')
    p.add_argument('--debug', action='store_true', help='Mostrar barra de progresso Rich (6 etapas)')
    p.add_argument('--export', nargs='*', default=['json'], help='Formatos: json xlsx pdf all (default json)')
    p.add_argument('--output_dir', default=os.path.join(os.getcwd(), 'Resultados_Busca'), help='Diretório de saída')
    return p.parse_args()

def main():  # pragma: no cover (exec path)
    params = parse_args()
    logger, log_path = setup_logging(params.output_dir, params.prompt)
    console = Console(width=120) if (params.debug and RICH_AVAILABLE) else None
    if console:
        console.print(Panel.fit("🚀 GvG Search Prompt v2", title="Inicialização", border_style="blue"))

    results, categories, confidence, elapsed = perform_search(params, logger, console)
    if not results:
        print(f"Nenhum resultado. LOG: {log_path}")
        sys.exit(0)

    # Exportação
    export_formats = set([f.lower() for f in params.export])
    if 'all' in export_formats:
        export_formats = {'json','xlsx','pdf'}
    exported = {}
    if 'json' in export_formats:
        try:
            exported['json'] = export_results_json(results, params.prompt, params, params.output_dir)
            logger.info(f"Export JSON: {exported['json']}")
        except Exception as e:
            logger.info(f"[ERRO] Export JSON: {e}")
    if 'xlsx' in export_formats:
        try:
            exported['xlsx'] = export_results_excel(results, params.prompt, params, params.output_dir)
            logger.info(f"Export XLSX: {exported['xlsx']}")
        except Exception as e:
            logger.info(f"[ERRO] Export XLSX: {e}")
    if 'pdf' in export_formats:
        try:
            pdf_path = export_results_pdf(results, params.prompt, params, params.output_dir)
            if pdf_path:
                exported['pdf'] = pdf_path
                logger.info(f"Export PDF: {pdf_path}")
            else:
                logger.info("PDF indisponível (ReportLab não instalado)")
        except Exception as e:
            logger.info(f"[ERRO] Export PDF: {e}")

    # Resumo console
    if console:
        _print_summary(console, results, categories, params, confidence, elapsed, params.prompt)
        exports_list = '\n'.join([f"• {k.upper()}: {v}" for k,v in exported.items()]) or 'Nenhum'
        console.print(Panel.fit(
            f"LOG: {log_path}\n{exports_list}", title="Arquivos", border_style="green"
        ))
    else:
        print(f"Resultados: {len(results)} | Confiança: {confidence:.4f} | Tempo: {elapsed:.2f}s")
        for k,v in exported.items():
            print(f"{k.upper()}: {v}")
        print(f"LOG: {log_path}")

if __name__ == '__main__':
    main()
