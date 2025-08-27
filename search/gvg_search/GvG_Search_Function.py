"""
GvG_Search_Function.py
Execução programática (função) do Sistema de Busca PNCP v2 Otimizado.

	• 3 tipos de busca (--s, --search) (semântica: 1 / palavras‑chave: 2 / híbrida: 3)
	• 3 abordagens (--a, --approach) (direta: 1 / correspondência: 2 / filtro: 3)
	• Filtro de relevância (níveis 1–3: 1=Sem filtro, 2=Flexível, 3=Restritivo)
	• Ordenação: 1=Similaridade (desc), 2=Data de assinatura (desc), 3=Valor final (desc)
	• Negation embeddings (positivos para categorias / completos para embedding)
	• Processamento inteligente (toggle opcional)
	• Exportação: JSON, XLSX, PDF (mesmo padrão de nomenclatura v9); também aceita 'all' e 'none'
	• Paridade com o Prompt/Terminal: mesmo pipeline de busca e ordenação
	• Heurística de segurança: desativa IA nesta execução se detectar condições inseguras do assistente (p.ex. '%s' literal ou OR sem parênteses)
	• Barra de progresso (opcional via debug=True)

Assinatura principal (substitui argparse do Prompt):

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
		output_dir: str = "resultados",
		debug: bool = False,
		return_export_paths: bool = True,
		return_raw: bool = False,
) -> dict
"""

import os
import sys
import re
import json
import time
import locale
import logging
from types import SimpleNamespace
from datetime import datetime
from typing import List, Tuple, Iterable, Dict, Any

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
# IMPORTAÇÕES DOS MÓDULOS OTIMIZADOS (iguais ao Prompt)
# =====================================================================================
from gvg_preprocessing import (
	format_currency,
	format_date,
	decode_poder,
	decode_esfera,
	SearchQueryProcessor
)
from gvg_ai_utils import (
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
	export_results_csv,
	export_results_pdf,
	export_results_html
)




from gvg_preprocessing import (
	format_currency,
	format_date,
)

# =====================================================================================
# CONSTANTES / CONFIGURAÇÃO (iguais ao Prompt)
# =====================================================================================
SEMANTIC_WEIGHT = 0.75
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
	2: {"name": "Data (Assinatura)"},
	3: {"name": "Valor (Final)"}
}
RELEVANCE_LEVELS = {
	1: {"name": "Sem filtro"},
	2: {"name": "Flexível"},
	3: {"name": "Restritivo"}
}

# =====================================================================================
# LOGGING (igual ao Prompt)
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
# BUSCA / ORQUESTRAÇÃO (igual ao Prompt)
# =====================================================================================
def sort_results(results: List[dict], order_mode: int):
	if not results:
		return results
	if order_mode == 1:
		return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
	elif order_mode == 2:
		def _key_date(r):
			d = r.get('details', {})
			val = d.get('dataassinatura') or d.get('dataAssinatura') or ''
			return str(val)
		return sorted(results, key=_key_date, reverse=True)
	elif order_mode == 3:
		def _key_val(r):
			d = r.get('details', {})
			return d.get('valorfinal') or d.get('valorFinal') or 0
		return sorted(results, key=_key_val, reverse=True)
	return results

def perform_search(params, logger, console=None):
	start = time.time()
	intelligent_status = get_intelligent_status()
	intelligent_enabled = intelligent_status['intelligent_processing']
	relevance_status = get_relevance_filter_status()

	original_query = params.prompt
	base_category_terms = original_query
	unsafe_intelligent = False
	try:
		processor = SearchQueryProcessor()
		processed_info = processor.process_query(original_query)
		processed_terms = (processed_info.get('search_terms') or '').strip()
		if processed_terms:
			base_category_terms = processed_terms
		sql_conds = processed_info.get('sql_conditions') or []
		for cond in sql_conds:
			if not isinstance(cond, str):
				continue
			if '%s' in cond:
				unsafe_intelligent = True
				break
			if ' OR ' in cond.upper():
				stripped = cond.strip()
				has_outer_parens = stripped.startswith('(') and stripped.endswith(')')
				if not has_outer_parens:
					unsafe_intelligent = True
					break
	except Exception as e:
		logger.info(f"[WARN] Falha processamento inteligente: {e}")

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
		if console:
			console.print(Panel.fit(
				f"🚀 GvG Search Function\nQuery: [yellow]{original_query}[/yellow]", title="Execução", border_style="cyan"
			))
		progress.start()
		t1 = progress.add_task("[1/6] Configuração inicial", total=100)

	if params.relevance != relevance_status['level']:
		try:
			set_relevance_filter_level(params.relevance)
		except Exception as e:
			logger.info(f"[WARN] Falha set_relevance_filter_level: {e}")
	if params.intelligent:
		try:
			toggle_intelligent_processing(not intelligent_enabled)
			intelligent_enabled = get_intelligent_status()['intelligent_processing']
			logger.info(f"Processamento Inteligente agora: {intelligent_enabled}")
		except Exception as e:
			logger.info(f"[WARN] Falha toggle inteligente: {e}")
	if progress:
		progress.update(t1, completed=100)

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

	if progress:
		t3 = progress.add_task("[3/6] Busca principal", total=100)
	restore_intelligent = None
	if unsafe_intelligent:
		try:
			restore_intelligent = get_intelligent_status()['intelligent_processing']
			if restore_intelligent:
				toggle_intelligent_processing(False)
				if console:
					console.print("[yellow]IA desativada nesta execução devido a padrões '%X' nas condições do assistente[/yellow]")
				logger.info("[WARN] IA desativada nesta execução por padrão '%%X' nas condições")
		except Exception as e:
			logger.info(f"[WARN] Toggle IA temporária falhou: {e}")

	try:
		if params.approach == 1:
			results, confidence = _direct_search(original_query, params)
		elif params.approach == 2:
			results, confidence, _ = _correspondence_search(original_query, params, categories, console if params.debug and RICH_AVAILABLE else None)
		elif params.approach == 3:
			results, confidence, _ = _category_filtered_search(original_query, params, categories, console if params.debug and RICH_AVAILABLE else None)
	except Exception as e:
		logger.info(f"[ERRO] Falha na busca: {e}")
	finally:
		if restore_intelligent is not None:
			try:
				toggle_intelligent_processing(restore_intelligent)
			except Exception:
				pass
	if progress:
		progress.update(t3, completed=100)

	if not results:
		elapsed = time.time() - start
		msg = f"Nenhum resultado encontrado (tempo {elapsed:.2f}s)"
		logger.info(msg)
		if console:
			console.print(f"[red]{msg}[/red]")
		return [], categories, confidence, elapsed

	if progress:
		t4 = progress.add_task("[4/6] Filtro relevância", total=100)
		progress.update(t4, completed=100)

	if progress:
		t5 = progress.add_task("[5/6] Ordenando resultados", total=100)
	results = sort_results(results, params.order)
	for i, r in enumerate(results, 1):
		r['rank'] = i
	if progress:
		progress.update(t5, completed=100)

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
	if params.approach in (2,3) and categories:
		table = Table(title="TOP Categorias", show_header=True, header_style="bold magenta")
		table.add_column("Rank", width=5)
		table.add_column("Código", width=10)
		table.add_column("Similaridade", width=12)
		table.add_column("Descrição", width=60)
		for c in categories:
			table.add_row(str(c.get('rank')), c.get('codigo',''), f"{c.get('similarity_score',0):.4f}", c.get('descricao','')[:58])
		console.print(table)
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
# Função programática equivalente ao Prompt (substitui argparse/main)
# =====================================================================================
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
	assert prompt and isinstance(prompt, str) and len(prompt.strip()) >= 3, "prompt inválido"

	logger, log_path = setup_logging(output_dir, prompt)
	console = Console(width=120) if (debug and RICH_AVAILABLE) else None
	if console:
		console.print(Panel.fit("🚀 GvG Search Function", title="Inicialização", border_style="blue"))

	params = SimpleNamespace(
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

	results, categories, confidence, elapsed = perform_search(params, logger, console)

	export_formats = set([str(f).lower() for f in (export or ['json'])])
	if 'all' in export_formats:
		export_formats = {'json','xlsx','csv','pdf','html'}
	if 'none' in export_formats:
		export_formats = set()
	exported = {}
	if 'json' in export_formats:
		try:
			exported['json'] = export_results_json(results, prompt, params, output_dir)
			logger.info(f"Export JSON: {exported['json']}")
		except Exception as e:
			logger.info(f"[ERRO] Export JSON: {e}")
	if 'xlsx' in export_formats:
		try:
			exported['xlsx'] = export_results_excel(results, prompt, params, output_dir)
			logger.info(f"Export XLSX: {exported['xlsx']}")
		except Exception as e:
			logger.info(f"[ERRO] Export XLSX: {e}")
	if 'csv' in export_formats:
		try:
			exported['csv'] = export_results_csv(results, prompt, params, output_dir)
			logger.info(f"Export CSV: {exported['csv']}")
		except Exception as e:
			logger.info(f"[ERRO] Export CSV: {e}")
	if 'pdf' in export_formats:
		try:
			pdf_path = export_results_pdf(results, prompt, params, output_dir)
			if pdf_path:
				exported['pdf'] = pdf_path
				logger.info(f"Export PDF: {pdf_path}")
			else:
				logger.info("PDF indisponível (ReportLab não instalado)")
		except Exception as e:
			logger.info(f"[ERRO] Export PDF: {e}")
	if 'html' in export_formats:
		try:
			exported['html'] = export_results_html(results, prompt, params, output_dir)
			logger.info(f"Export HTML: {exported['html']}")
		except Exception as e:
			logger.info(f"[ERRO] Export HTML: {e}")

	if console and not return_raw:
		_print_summary(console, results, categories, params, confidence, elapsed, prompt)
		exports_list = '\n'.join([f"• {k.upper()}: {v}" for k,v in exported.items()]) or 'Nenhum'
		console.print(Panel.fit(
			f"LOG: {log_path}\n{exports_list}", title="Arquivos", border_style="green"
		))
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
