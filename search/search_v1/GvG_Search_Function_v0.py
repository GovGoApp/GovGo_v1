"""
GvG_Search_Function.py

Versão funcional (programática) do mecanismo de busca PNCP v2 otimizado.
ABSOLUTAMENTE idêntica ao GvG_Search_Prompt em pipeline, ordenação, logs, formatação e heurísticas;
a única diferença é a interface: aqui é uma função (sem argparse / sem sys.exit).

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

Retorno (dict):
    {
        'results': [...], 'categories': [...], 'confidence': float, 'elapsed': float,
        'log_path': str, 'exports': {fmt: path, ...}, 'params': {...}
    }

Notas:
    • Export aceita 'json', 'xlsx', 'pdf', 'all' (todos) e 'none' (nenhum), igual ao Prompt.
    • Se debug=True e Rich instalado, mostra barra de progresso e tabelas igual ao Prompt.
    • Sem sys.exit; retorna estrutura mesmo sem resultados.
"""

from __future__ import annotations

import os
import re
import time
import logging
import locale
from types import SimpleNamespace
from typing import Iterable, Dict, Any

# Rich opcional (igual ao Prompt)
try:  # pragma: no cover
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False
    Console = None

# Locale (igual ao Prompt)
try:  # pragma: no cover
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:  # pragma: no cover
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# Reutiliza exatamente as mesmas funções do Prompt para garantir paridade total
from GvG_Search_Prompt import (
    setup_logging as _setup_logging_identico,
    perform_search as _perform_search_identico,
    _print_summary as _print_summary_identico,
)
from gvg_exporters import (
    export_results_json as _export_json,
    export_results_excel as _export_xlsx,
    export_results_pdf as _export_pdf,
)




# --------------------------------------------------------------------------------------------------
# Função Principal Programática (idêntica ao Prompt, sem argparse)
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
    """Executa a busca PNCP idêntica ao Prompt e retorna um dicionário com os dados."""
    assert isinstance(prompt, str) and len(prompt.strip()) >= 3, "prompt inválido"

    logger, log_path = _setup_logging_identico(output_dir, prompt)
    console = Console(width=120) if (debug and RICH_AVAILABLE and not return_raw) else None
    if console:
        console.print(Panel.fit("🚀 GvG Search Function", title="Inicialização", border_style="blue"))

    # Namespace idêntico ao argparse do Prompt
    params_ns = SimpleNamespace(
        prompt=prompt,
        search=search,
        approach=approach,
        relevance=relevance,
        order=order,
        max_results=max_results,
        top_cat=top_cat,
        negation_emb=negation_emb,
        filter_expired=filter_expired,
        intelligent=intelligent_toggle,
        debug=debug,
        export=list(export) if export else ['json'],
        output_dir=output_dir,
    )

    results, categories, confidence, elapsed = _perform_search_identico(params_ns, logger, console)

    # Exportação idêntica ao Prompt
    export_formats = set([str(f).lower() for f in (export or ("json",))])
    if 'all' in export_formats:
        export_formats = {'json','xlsx','pdf'}
    if 'none' in export_formats:
        export_formats = set()

    exported: Dict[str,str] = {}
    if 'json' in export_formats and results:
        try:
            exported['json'] = _export_json(results, prompt, params_ns, output_dir)
            logger.info(f"Export JSON: {exported['json']}")
        except Exception as e:
            logger.info(f"[ERRO] Export JSON: {e}")
    if 'xlsx' in export_formats and results:
        try:
            exported['xlsx'] = _export_xlsx(results, prompt, params_ns, output_dir)
            logger.info(f"Export XLSX: {exported['xlsx']}")
        except Exception as e:
            logger.info(f"[ERRO] Export XLSX: {e}")
    if 'pdf' in export_formats and results:
        try:
            pdf_path = _export_pdf(results, prompt, params_ns, output_dir)
            if pdf_path:
                exported['pdf'] = pdf_path
                logger.info(f"Export PDF: {pdf_path}")
            else:
                logger.info("PDF indisponível (ReportLab não instalado)")
        except Exception as e:
            logger.info(f"[ERRO] Export PDF: {e}")

    # Saída visual idêntica ao Prompt (se houver console e não for raw)
    if console and not return_raw:
        _print_summary_identico(console, results, categories, params_ns, confidence, elapsed, prompt)
        exports_list = '\n'.join([f"• {k.upper()}: {v}" for k,v in exported.items()]) or 'Nenhum'
        console.print(Panel.fit(f"LOG: {log_path}\n{exports_list}", title="Arquivos", border_style="green"))
    elif not return_raw:
        print(f"Resultados: {len(results)} | Confiança: {confidence:.4f} | Tempo: {elapsed:.2f}s")
        for k,v in exported.items():
            print(f"{k.upper()}: {v}")
        print(f"LOG: {log_path}")

    return {
        'results': results,
        'categories': categories,
        'confidence': confidence,
        'elapsed': elapsed,
        'log_path': log_path,
        'exports': exported if return_export_paths else {},
        'params': {
            'prompt': prompt,
            'search': search,
            'approach': approach,
            'relevance': relevance,
            'order': order,
            'max_results': max_results,
            'top_cat': top_cat,
            'negation_emb': negation_emb,
            'filter_expired': filter_expired,
            'intelligent': intelligent_toggle,
            'debug': debug,
            'output_dir': output_dir,
        }
    }


__all__ = ["gvg_search"]
