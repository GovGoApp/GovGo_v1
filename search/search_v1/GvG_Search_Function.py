"""
GvG_Search_Function.py

Versão funcional (programática) do mecanismo de busca PNCP (v2 otimizado).
Baseada em GvG_Search_Prompt.py porém exposta como função reutilizável, sem argparse.

Função principal:
    gvg_search(
        prompt: str,
        search: int = 1,
        approach: int = 3,
        relevance: int = 2,
        order: int = 1,
        max_results: int = 30,
        top_cat: int = 10,
        negation_emb: bool = True,
        filter_expired: bool = True,
        intelligent_toggle: bool = False,
        export: tuple | list | None = ("json",),
        output_dir: str = "Resultados_Busca",
        debug: bool = False,
        return_export_paths: bool = True,
        return_raw: bool = False
    ) -> dict

Parâmetros seguem os mesmos padrões do script de prompt:
  search: 1=Semântica 2=Palavras-chave 3=Híbrida
  approach: 1=Direta 2=Correspondência 3=Filtro
  relevance: 1=Sem filtro 2=Flexível 3=Restritivo
  order: 1=Similaridade 2=DataEncerramento 3=ValorEstimado

Retorno (dict):
  {
    'results': [...],               # lista de resultados com ranks
    'categories': [...],            # categorias (se aplicável)
    'confidence': float,            # confiança média
    'elapsed': float,               # tempo (s)
    'log_path': str,                # caminho do log
    'exports': {fmt: path, ...},    # se exportação realizada
    'params': {...}                 # parâmetros efetivos
  }

Observações:
  • Se export incluir 'all' => json, xlsx, pdf
  • PDF depende de reportlab (silenciosamente ignorado se indisponível)
  • Se debug=True e Rich instalado, mostra barra de progresso
  • Não lança sys.exit; retorna estrutura vazia em caso de falha controlada
"""

from __future__ import annotations

import os
import re
import json
import time
import logging
import locale
from datetime import datetime
from typing import List, Tuple, Iterable, Dict, Any

import pandas as pd

# Rich opcional
try:  # pragma: no cover
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn, TimeRemainingColumn
    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False
    Console = None

# PDF opcional
try:  # pragma: no cover
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

# Locale
try:  # pragma: no cover
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:  # pragma: no cover
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# Imports de módulos internos (mesmos do prompt)
from gvg_preprocessing import (
    format_currency,
    format_date,
    decode_poder,
    decode_esfera,
    SearchQueryProcessor
)
from gvg_ai_utils import (
    extract_pos_neg_terms,
)
from gvg_search_core import (
    semantic_search,
    keyword_search,
    hybrid_search,
    toggle_intelligent_processing,
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
    generate_export_filename as _generate_export_filename,
    export_results_json as _export_json,
    export_results_excel as _export_xlsx,
    export_results_pdf as _export_pdf
)

# --------------------------------------------------------------------------------------------------
# Constantes / Metadados
# --------------------------------------------------------------------------------------------------
SEARCH_TYPES = {1: {"name": "Semântica"}, 2: {"name": "Palavras-chave"}, 3: {"name": "Híbrida"}}
SEARCH_APPROACHES = {1: {"name": "Direta"}, 2: {"name": "Correspondência"}, 3: {"name": "Filtro"}}
SORT_MODES = {1: {"name": "Similaridade"}, 2: {"name": "Data de Encerramento"}, 3: {"name": "Valor Estimado"}}
RELEVANCE_LEVELS = {1: {"name": "Sem filtro"}, 2: {"name": "Flexível"}, 3: {"name": "Restritivo"}}


# --------------------------------------------------------------------------------------------------
# Logging utilitário
# --------------------------------------------------------------------------------------------------
def _setup_logging(output_dir: str, query: str) -> tuple[logging.Logger, str]:
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    clean = re.sub(r'[^\w\s-]', '', query).strip().upper()
    clean = re.sub(r'\s+', '_', clean)[:30]
    logfile = os.path.join(output_dir, f"Busca_{clean}_LOG_{ts}.log")
    logger = logging.getLogger(f'GvG_Search_Function_{ts}')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(fh)
    return logger, logfile




# --------------------------------------------------------------------------------------------------
# Ordenação / Busca
# --------------------------------------------------------------------------------------------------
def _sort_results(results: List[dict], order_mode: int):
    if not results:
        return results
    if order_mode == 1:
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
    elif order_mode == 2:
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


def _direct_search(query: str, params: dict):
    st = params['search']
    if st == 1:
        return semantic_search(query, limit=params['max_results'], filter_expired=params['filter_expired'], use_negation=params['negation_emb'])
    if st == 2:
        return keyword_search(query, limit=params['max_results'], filter_expired=params['filter_expired'])
    if st == 3:
        return hybrid_search(query, limit=params['max_results'], filter_expired=params['filter_expired'], use_negation=params['negation_emb'])
    return [], 0.0


def _correspondence_search(query: str, params: dict, categories, console=None):
    if not categories:
        return [], 0.0, {}
    return categories_correspondence_search(
        query_text=query,
        top_categories=categories,
        limit=params['max_results'],
        filter_expired=params['filter_expired'],
        console=console
    )


def _category_filtered_search(query: str, params: dict, categories, console=None):
    if not categories:
        return [], 0.0, {}
    return categories_category_filtered_search(
        query_text=query,
        search_type=params['search'],
        top_categories=categories,
        limit=params['max_results'],
        filter_expired=params['filter_expired'],
        use_negation=params['negation_emb'],
        console=console
    )


# --------------------------------------------------------------------------------------------------
# Função Principal Programática
# --------------------------------------------------------------------------------------------------
def gvg_search(
    prompt: str,
    search: int = 1,
    approach: int = 3,
    relevance: int = 2,
    order: int = 1,
    max_results: int = 30,
    top_cat: int = 10,
    negation_emb: bool = True,
    filter_expired: bool = True,
    intelligent_toggle: bool = False,
    export: Iterable[str] | None = ("json",),
    output_dir: str = "Resultados_Busca",
    debug: bool = False,
    return_export_paths: bool = True,
    return_raw: bool = False,
) -> Dict[str, Any]:
    """Executa a busca PNCP e retorna resultados estruturados.

    Args descrevidos no cabeçalho do módulo.
    return_raw: se True, não imprime nada (silencioso) mesmo em debug (apenas gera arquivos/retorno)
    """
    assert prompt and isinstance(prompt, str) and len(prompt.strip()) >= 3, "prompt inválido"
    params = {
        'prompt': prompt,
        'search': search,
        'approach': approach,
        'relevance': relevance,
        'order': order,
        'max_results': max_results,
        'top_cat': top_cat,
        'negation_emb': negation_emb,
        'filter_expired': filter_expired,
    }

    logger, log_path = _setup_logging(output_dir, prompt)
    console = None
    if debug and RICH_AVAILABLE and not return_raw:
        console = Console(width=120)
        console.print(Panel.fit("🚀 GvG Search Function", title="Inicialização", border_style="blue"))

    start = time.time()
    intelligent_status = get_intelligent_status()
    current_intelligent = intelligent_status['intelligent_processing']
    relevance_status = get_relevance_filter_status()

    # Ajustar nível de relevância
    if relevance != relevance_status['level']:
        try:
            set_relevance_filter_level(relevance)
        except Exception as e:
            logger.info(f"[WARN] Falha set_relevance: {e}")

    # Toggle inteligente se solicitado
    if intelligent_toggle:
        try:
            toggle_intelligent_processing(not current_intelligent)
            current_intelligent = get_intelligent_status()['intelligent_processing']
        except Exception as e:
            logger.info(f"[WARN] Falha toggle inteligente: {e}")

    # Pos/neg extraction e processamento inteligente para categorias
    try:
        pos_terms, neg_terms = extract_pos_neg_terms(prompt) if negation_emb and search in (1,3) else (prompt, "")
    except Exception:
        pos_terms, neg_terms = prompt, ""
    base_category_terms = pos_terms
    try:
        processor = SearchQueryProcessor()
        processed = processor.process_query(prompt)
        processed_terms = processed.get('search_terms') or ''
        if processed_terms:
            cat_pos, _ = extract_pos_neg_terms(processed_terms) if negation_emb and search in (1,3) else (processed_terms, "")
            if cat_pos.strip():
                base_category_terms = cat_pos.strip()
    except Exception as e:
        logger.info(f"[WARN] Inteligente categorias: {e}")

    # Progress (6 etapas)
    progress = None
    if debug and RICH_AVAILABLE and console:
        progress = Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn(), console=console)
        progress.start()
        t1 = progress.add_task("[1/6] Configuração", total=100)
        progress.update(t1, completed=100)

    # Categorias
    categories = []
    if debug and console and progress:
        t2 = progress.add_task("[2/6] Categorias", total=100)
    if approach in (2,3):
        try:
            categories = get_top_categories_for_query(
                query_text=base_category_terms or prompt,
                top_n=top_cat,
                use_negation=False,
                search_type=search,
                console=console if debug and RICH_AVAILABLE and not return_raw else None
            )
        except Exception as e:
            logger.info(f"[ERRO] categorias: {e}")
    if debug and console and progress:
        progress.update(t2, completed=100)

    # Busca principal
    if debug and console and progress:
        t3 = progress.add_task("[3/6] Busca", total=100)
    results = []
    confidence = 0.0
    try:
        if approach == 1:
            results, confidence = _direct_search(prompt, params)
        elif approach == 2:
            results, confidence, _ = _correspondence_search(prompt, params, categories, console if debug and RICH_AVAILABLE and not return_raw else None)
        elif approach == 3:
            results, confidence, _ = _category_filtered_search(prompt, params, categories, console if debug and RICH_AVAILABLE and not return_raw else None)
    except Exception as e:
        logger.info(f"[ERRO] busca: {e}")
    if debug and console and progress:
        progress.update(t3, completed=100)

    # Filtro relevância (já interno) etapa 4
    if debug and console and progress:
        t4 = progress.add_task("[4/6] Relevância", total=100)
        progress.update(t4, completed=100)

    # Ordenação etapa 5
    if debug and console and progress:
        t5 = progress.add_task("[5/6] Ordenação", total=100)
    results = _sort_results(results, order)
    for i, r in enumerate(results, 1):
        r['rank'] = i
    if debug and console and progress:
        progress.update(t5, completed=100)

    # Final etapa 6
    if debug and console and progress:
        t6 = progress.add_task("[6/6] Final", total=100)
        progress.update(t6, completed=100)
        progress.stop()

    elapsed = time.time() - start
    logger.info(f"Tempo: {elapsed:.2f}s | Confiança: {confidence:.4f} | Resultados: {len(results)}")

    # Exportações
    export_map: Dict[str,str] = {}
    if export:
        fmt_set = {f.lower() for f in export}
        if 'all' in fmt_set:
            fmt_set = {'json','xlsx','pdf'}
        # Executar exportações
        if results:
            if 'json' in fmt_set:
                try:
                    export_map['json'] = _export_json(results, prompt, params, output_dir)
                except Exception as e:
                    logger.info(f"[ERRO] export json: {e}")
            if 'xlsx' in fmt_set:
                try:
                    export_map['xlsx'] = _export_xlsx(results, prompt, params, output_dir)
                except Exception as e:
                    logger.info(f"[ERRO] export xlsx: {e}")
            if 'pdf' in fmt_set:
                try:
                    pdf_path = _export_pdf(results, prompt, params, output_dir)
                    if pdf_path:
                        export_map['pdf'] = pdf_path
                except Exception as e:
                    logger.info(f"[ERRO] export pdf: {e}")

    # Exibição resumida se debug e não raw
    if debug and console and not return_raw:
        _print_summary(console, results, categories, params, confidence, elapsed, prompt, export_map, log_path)

    return {
        'results': results,
        'categories': categories,
        'confidence': confidence,
        'elapsed': elapsed,
        'log_path': log_path,
        'exports': export_map if return_export_paths else {},
        'params': params
    }


def _print_summary(console, results, categories, params, confidence, elapsed, prompt, export_map, log_path):  # pragma: no cover (visual)
    console.print(Panel.fit(
        f"✅ Busca concluída\nResultados: {len(results)} | Tempo: {elapsed:.2f}s | Confiança: {confidence:.2f}", title="Resumo", border_style="green"))
    if params['negation_emb'] and params['search'] in (1,3):
        try:
            pos, neg = extract_pos_neg_terms(prompt)
            if neg.strip():
                console.print(f"[cyan]🎯 Negativo: [green]{pos}[/green]  --  [red]{neg}[/red][/cyan]")
        except Exception:
            pass
    if params['approach'] in (2,3) and categories:
        table = Table(title="TOP Categorias", show_header=True, header_style="bold magenta")
        table.add_column("Rank", width=5)
        table.add_column("Código", width=10)
        table.add_column("Similarity", width=12)
        table.add_column("Descrição", width=60)
        for c in categories:
            table.add_row(str(c.get('rank')), c.get('codigo',''), f"{c.get('similarity_score',0):.4f}", c.get('descricao','')[:58])
        console.print(table)
    rtable = Table(title="Resultados", show_header=True, header_style="bold blue")
    rtable.add_column("Rank", width=5)
    rtable.add_column("Órgão", width=38)
    rtable.add_column("Local", width=28)
    rtable.add_column("Similarity", width=10)
    rtable.add_column("Valor", width=14)
    rtable.add_column("Encerramento", width=12)
    for r in results[:100]:  # limitar visual
        d = r.get('details', {})
        unidade = d.get('unidadeorgao_nomeunidade') or d.get('unidadeOrgao_nomeUnidade') or d.get('orgaoentidade_razaosocial') or 'N/A'
        municipio = d.get('unidadeorgao_municipionome') or d.get('unidadeOrgao_municipioNome') or 'N/A'
        uf = d.get('unidadeorgao_ufsigla') or d.get('unidadeOrgao_ufSigla') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        valor = format_currency(d.get('valortotalestimado') or d.get('valorTotalEstimado') or 0)
        data_enc = format_date(d.get('dataencerramentoproposta') or d.get('dataEncerramentoProposta') or 'N/A')
        rtable.add_row(str(r.get('rank')), unidade[:38], local[:28], f"{r.get('similarity',0):.4f}", valor, str(data_enc))
    console.print(rtable)
    if export_map:
        lines = "\n".join(f"• {k.upper()}: {v}" for k,v in export_map.items())
    else:
        lines = "Nenhum arquivo exportado"
    console.print(Panel.fit(f"LOG: {log_path}\n{lines}", title="Arquivos", border_style="cyan"))


__all__ = ["gvg_search"]
