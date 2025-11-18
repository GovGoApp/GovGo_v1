r"""Sommelier v2 — Editais coloridos por similaridade (Folium.Icon)

Observação:
- Mantém a estrutura da versão anterior, com FeatureGroups e legenda interativa.
- Editais usam cores nomeadas do Folium conforme faixas de similaridade.
- Estilos importados e centralizados via gvg_styles.py.
"""
import os
import sys
import io
import argparse
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State

# Import robusto dos estilos para funcionar tanto como módulo quanto como script direto

import gvg_styles as _gvg_styles  # type: ignore
styles, CSS_ALL = _gvg_styles.styles, _gvg_styles.CSS_ALL
	

# --- Caminho para importar o motor v1_3 ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CNPJ_PATH = os.path.join(ROOT, 'scripts', 'cnpj_search')
if CNPJ_PATH not in sys.path:
	sys.path.insert(0, CNPJ_PATH)

try:
	from cnpj_search_v1_3 import (
		run_search,
		get_db_conn,
		load_municipios_coords,
		extract_hq_ibge,
		normalize_cnpj as engine_normalize_cnpj,
	)
except Exception:  # pragma: no cover
	run_search = None  # type: ignore
	get_db_conn = None  # type: ignore
	load_municipios_coords = None  # type: ignore
	extract_hq_ibge = None  # type: ignore
try:
	engine_normalize_cnpj
except NameError:
	engine_normalize_cnpj = None  # type: ignore


LOGO_PATH = "https://hemztmtbejcbhgfmsvfq.supabase.co/storage/v1/object/public/govgo/LOGO/LOGO_TEXTO_GOvGO_TRIM_v3.png"

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Sommelier v2"
MAP_VIEW_MODE = (os.environ.get('VIEW_MAP') or 'v2').lower()
CLUSTER_MODE = False

app.index_string = (
    """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>Sommelier v2</title>
    {%favicon%}
    {%css%}
    <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css\" />
    <style>""" + CSS_ALL + """</style>
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""
)


def left_panel():
	# Inputs para parâmetros (labels explicativos)
	param_card = html.Div([
		# Cabeçalho com botão de expandir/colapsar (padrão GSB)
		html.Div([
			html.Button([
				html.Div([
					html.I(className='fas fa-sliders-h', style=styles['section_icon']),
					html.Div('Parâmetros', style=styles['card_title'])
				], style=styles['section_header_left']),
				html.I(className='fas fa-chevron-down')
			], id='params-toggle-btn', title='Mostrar/ocultar parâmetros', style=styles['section_header_button'])
		], style=styles['row_header']),
		dbc.Collapse(
			html.Div([
			# Cada linha segue padrão gvg-form-row + gvg-form-label para herdar CSS global
			html.Div([
				html.Label('Máx. resultados', className='gvg-form-label', title='Limite de editais/contratos exibidos no ranking final.'),
				dcc.Input(id='param-top-k', type='number', min=1, value=30)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Candidatos iniciais', className='gvg-form-label', title='Quantidade de candidatos antes dos filtros; mantenha maior que o Máx. resultados.'),
				dcc.Input(id='param-top-candidates', type='number', min=1, value=120)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Amostragem contratos', className='gvg-form-label', title='Quantidade de contratos históricos usada como amostra para métricas.'),
				dcc.Input(id='param-sample-contratos', type='number', min=1, value=50)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Peso geográfico', className='gvg-form-label', title='Peso (0-1) aplicado ao critério de proximidade geográfica na nota final.'),
				dcc.Input(id='param-geo-weight', type='number', min=0, max=1, step=0.01, value=0.25)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Escala geográfica (km)', className='gvg-form-label', title='Tau em quilômetros usado no decaimento exponencial da distância.'),
				dcc.Input(id='param-geo-tau', type='number', min=0, value=300)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Tau HQ (km)', className='gvg-form-label', title='Tau em quilômetros para o fator adaptativo entre sede e mediana geográfica.'),
				dcc.Input(id='param-tau-hq', type='number', min=0, value=400)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Tau dispersão (km)', className='gvg-form-label', title='Tau em quilômetros usado no fator adaptativo para dispersão dos contratos.'),
				dcc.Input(id='param-tau-disp', type='number', min=0, value=800)
			], className='gvg-form-row'),
			html.Div([
				html.Label('Usar fator geográfico', className='gvg-form-label', title='Ativa ou desativa o componente geográfico na ordenação.'),
				dcc.Checklist(id='param-use-geo', options=[{'label': 'Ativo', 'value': 'yes'}], value=['yes'], style={'fontSize': '12px'})
			], className='gvg-form-row'),
			html.Div([
				html.Label('Adaptação geográfica', className='gvg-form-label', title='Ajusta automaticamente o peso geográfico conforme a densidade dos resultados.'),
				dcc.Checklist(id='param-geo-adapt', options=[{'label': 'Ativo', 'value': 'yes'}], value=['yes'], style={'fontSize': '12px'})
			], className='gvg-form-row'),
			html.Div([
				html.Label('Filtrar encerrados', className='gvg-form-label', title='Remove editais e contratos cujo encerramento já passou.'),
				dcc.Checklist(id='param-filter-expired', options=[{'label': 'Ativo', 'value': 'yes'}], value=['yes'], style={'fontSize': '12px'})
			], className='gvg-form-row'),
		], className='gvg-controls params-card', style=styles['controls_group']),
			id='params-collapse', is_open=True
		)
	], style={**styles['result_card_compact'], **styles['mt_same_card_gap']})

	return html.Div([
		# Campo CNPJ + botão
		html.Div([
			html.Div([
				dcc.Input(id="input-cnpj", placeholder="CNPJ 00.000.000/0001-00", type="text", style={**styles['input_field']}, debounce=True),
				html.Button(html.I(className="fas fa-arrow-right"), id="btn-buscar", n_clicks=0, style=styles['arrow_button'])
			], style=styles['input_container'])
		], className="gvg-controls"),
		param_card,
		# Card Dados
		html.Div([
			html.Div("Dados", style=styles['card_title']),
			html.Div("Nenhum dado para mostrar.", id="company-data")
		], style={**styles['result_card_compact'], **styles['mt_same_card_gap']}),
	], style=styles['left_panel'])


def tab_contratos():
	return html.Div([
		html.Div([
			html.Div(
				dash_table.DataTable(
				id="table-contratos",
				columns=[
					{"name": "Nº", "id": "rank"},
					{"name": "Órgão", "id": "orgao"},
					{"name": "Município", "id": "municipio"},
					{"name": "UF", "id": "uf"},
					{"name": "Similaridade", "id": "similaridade"},
					{"name": "Valor (R$)", "id": "valor"},
					{"name": "Data de Encerramento", "id": "data"},
				],
				data=[],
				page_size=10,
				style_table={"overflowX": "auto"},
				style_cell={"fontSize": "12px", "padding": "6px"},
				style_header={"backgroundColor": "#f1f3f4", "fontWeight": "bold"},
				),
				id="contratos-table-wrap",
				style={"display": "none"}
			),
			html.Div("Nenhum contrato para mostrar.", id="contratos-empty")
		], style=styles['result_card']),
		html.Div([
			html.Div("Detalhe", style=styles['card_title']),
			html.Div("Selecione uma linha para ver os detalhes.", id="contrato-detalhe")
		], id="contratos-detail-wrap", style={'display': 'none'})
	])


def tab_editais():
	return html.Div([
		html.Div([
			html.Div(
				dash_table.DataTable(
				id="table-editais",
				columns=[
					{"name": "#", "id": "rank"},
					{"name": "Órgão", "id": "orgao"},
					{"name": "Município", "id": "municipio"},
					{"name": "UF", "id": "uf"},
					{"name": "Similaridade", "id": "similaridade"},
					{"name": "Score final", "id": "score_final"},
					{"name": "Valor (R$)", "id": "valor"},
					{"name": "Data de Encerramento", "id": "data"},
				],
				data=[],
				page_size=10,
				style_table={"overflowX": "auto"},
				style_cell={"fontSize": "12px", "padding": "6px"},
				style_header={"backgroundColor": "#f1f3f4", "fontWeight": "bold"},
				)
				,
				id="editais-table-wrap",
				style={"display": "none"}
			),
			html.Div("Nenhum edital para mostrar.", id="editais-empty")
		], style=styles['result_card']),
		html.Div([
			html.Div("Detalhe", style=styles['card_title']),
			html.Div("Selecione uma linha para ver os detalhes.", id="edital-detalhe")
		], id="editais-detail-wrap", style={'display': 'none'})
	])


def tab_mapas():
	return html.Div([
		html.Div([
			html.Div([
				html.Div(id="map-container", style={"height": "600px"})
			], id="map-wrap", style={"display": "none"}),
			html.Div("Nenhum mapa para mostrar.", id="map-empty")
		], style=styles['result_card'])
	])


def right_panel():
	return html.Div([
		dcc.Tabs(
			id="tabs",
			value="tab-contratos",
			className="gvg-tabs",
			colors={
				'border': '#D0D7E2',
				'primary': '#FF5722',
				'background': 'white'
			},
			children=[
				dcc.Tab(
					label="Contratos",
					value="tab-contratos",
					className="gvg-tab",
					selected_className="gvg-tab-selected",
					children=[html.Div(tab_contratos(), style=styles['tabs_content'])]
				),
				dcc.Tab(
					label="Editais",
					value="tab-editais",
					className="gvg-tab",
					selected_className="gvg-tab-selected",
					children=[html.Div(tab_editais(), style=styles['tabs_content'])]
				),
				dcc.Tab(
					label="Mapas",
					value="tab-mapas",
					className="gvg-tab",
					selected_className="gvg-tab-selected",
					children=[html.Div(tab_mapas(), style=styles['tabs_content'])]
				),
			]
		)
	], style=styles['right_panel'])


app.layout = html.Div([
	# Header (Navbar) fiel ao Report
	html.Div([
		html.Div([
			html.Img(src=LOGO_PATH, style=styles['header_logo']),
			html.Div("GvG Sommelier v2", style=styles['header_title'], className="gvg-header-title")
		], style=styles['header_left']),
		html.Div([], style=styles['header_right'])
	], style=styles['header']),

	# Painéis principais (30/70 via CSS vars)
	html.Div([
		# Stores (dados em memória)
		dcc.Store(id='store-company'),
		dcc.Store(id='store-contratos'),
		dcc.Store(id='store-editais'),
		dcc.Store(id='store-stats'),
		dcc.Store(id='store-geo-stats'),
		dcc.Store(id='store-params', data={
			'top_k': 30,
			'top_candidates': 300,
			'timeout_ms': 120000,
			'fallback_sample_pct': 2.0,
			'rows': 15,
			'sample_contratos': 50,
			'width': 96,
			'geo_weight': 0.25,
			'geo_tau': 300.0,
			'use_geo': True,
			'geo_adapt': True,
			'tau_hq': 400.0,
			'tau_disp': 800.0,
			'filter_expired': True,
		}),

		dcc.Store(id='processing-state', data=False),
		dcc.Store(id='search-trigger'),
		html.Div(left_panel(), className="gvg-slide"),
		html.Div(right_panel(), className="gvg-slide"),
	], id="gvg-main-panels", style=styles['container'])
])


# -------------------- Util --------------------

def _only_digits(s: str) -> str:
	return ''.join(ch for ch in s if ch.isdigit())


def normalize_cnpj(cnpj: Optional[str]) -> Optional[str]:
	"""Normaliza CNPJ como no motor v1_3: aceita formatado (12.345...) ou 14 dígitos."""
	if cnpj is None:
		return None
	# Preferir implementação do motor para garantir paridade
	if engine_normalize_cnpj:
		try:
			return engine_normalize_cnpj(str(cnpj))  # type: ignore
		except Exception:
			pass
	# Fallback local
	d = _only_digits(str(cnpj))
	return d if len(d) == 14 else None


def format_currency(v) -> str:
	try:
		if v is None:
			return "-"
		return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
	except Exception:
		return "-"


def format_date_br(txt: Optional[str]) -> str:
	if not txt:
		return "-"
	# suporta YYYY-MM-DD ou ISO
	try:
		y = txt[:10]
		yyyy, mm, dd = y.split("-")
		return f"{dd}/{mm}/{yyyy}"
	except Exception:
		return txt


def format_cnpj_display(v: Optional[str]) -> str:
	"""Formata CNPJ em 99.999.999/9999-99 (mantém original se não for 14 dígitos)."""
	if not v:
		return "-"
	d = _only_digits(str(v))
	if len(d) != 14:
		return str(v)
	return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def format_cnae_display(v: Optional[str]) -> str:
	"""Formata CNAE em 99.99-9-99 a partir dos dígitos (ex.: 6201501 -> 62.01-5-01)."""
	if not v:
		return "-"
	d = _only_digits(str(v))
	if len(d) == 7:
		return f"{d[0:2]}.{d[2:4]}-{d[4]}-{d[5:7]}"
	return str(v)


def normalize_cnae_code(raw: Optional[Any]) -> Optional[str]:
	"""Remove pontuação e retorna o CNAE com 7 dígitos (zero-fill se necessário)."""
	if raw is None:
		return None
	d = _only_digits(str(raw))
	if not d:
		return None
	if len(d) < 7:
		d = d.zfill(7)
	return d[:7]


def extract_cnae_codes(principal: Any, secundarios: Any) -> Tuple[Optional[str], List[str]]:
	principal_code = normalize_cnae_code(principal)
	sec_codes: List[str] = []
	if isinstance(secundarios, (list, tuple)):
		for item in secundarios:
			code = None
			if isinstance(item, dict):
				code = normalize_cnae_code(item.get('code') or item.get('codigo') or item.get('cod'))
			else:
				code = normalize_cnae_code(item)
			if code and code not in sec_codes:
				sec_codes.append(code)
	elif isinstance(secundarios, str) and secundarios:
		for part in secundarios.split(','):
			code = normalize_cnae_code(part)
			if code and code not in sec_codes:
				sec_codes.append(code)
	return principal_code, sec_codes


def fetch_cnae_descriptions(codes: List[str]) -> Dict[str, str]:
	if not codes or not get_db_conn:
		return {}
	codes_unique = list(dict.fromkeys(codes))
	query = "SELECT cod_nv4, nom_nv4 FROM public.cnae WHERE cod_nv4 = ANY(%s)"
	conn = get_db_conn()
	try:
		with conn:
			with conn.cursor() as cur:
				cur.execute(query, (codes_unique,))
				rows = cur.fetchall() or []
		return {str(code): desc for code, desc in rows if code}
	finally:
		try:
			conn.close()
		except Exception:
			pass


def format_cnae_with_desc(code: Optional[str], desc_map: Dict[str, str]) -> Optional[str]:
	if not code:
		return None
	desc = desc_map.get(code) or 'Descrição indisponível'
	return f"{code} - {desc}"


def fetch_contratos_fornecedor(cnpj14: str) -> List[Dict[str, Any]]:
	if not get_db_conn:
		return []
	sql = """
		SELECT
			numero_controle_pncp,
			orgao_entidade_razaosocial AS orgao_entidade_razao_social,
			unidade_orgao_municipio_nome,
			unidade_orgao_uf_sigla,
			unidade_orgao_codigo_ibge,
			objeto_contrato,
				valor_global AS valor_total_homologado,
				data_vigencia_fim AS data_encerramento_proposta,
				NULL::text AS link_sistema_origem
		FROM public.contrato
		WHERE ni_fornecedor = %s
			ORDER BY COALESCE(data_vigencia_fim,'9999-12-31') DESC
		LIMIT 300
	"""
	conn = get_db_conn()
	try:
		with conn:
			with conn.cursor() as cur:
				cur.execute(sql, (cnpj14,))
				cols = [c[0] for c in cur.description]
				rows = cur.fetchall()
				return [dict(zip(cols, r)) for r in rows]
	finally:
		try:
			conn.close()
		except Exception:
			pass


# -------------------- Callbacks --------------------

# Callback 1: inicia processamento (ativa spinner e armazena CNPJ)
@app.callback(
	Output('processing-state', 'data'),
	Output('search-trigger', 'data'),
	Input('btn-buscar', 'n_clicks'),
	Input('input-cnpj', 'n_submit'),
	State('input-cnpj', 'value'),
	prevent_initial_call=True
)

def start_search(n_clicks, n_submit, cnpj_input):
	cnpj14 = normalize_cnpj(cnpj_input)
	if not cnpj14:
		return False, None
	# Ativa processamento e passa cnpj válido
	return True, {'cnpj': cnpj14, 'ts': (n_clicks or 0) + (n_submit or 0)}


# Callback 2: executa busca quando processing-state=True e search-trigger atualizado
@app.callback(
	Output('store-company', 'data'),
	Output('store-contratos', 'data'),
	Output('store-editais', 'data'),
	Output('store-stats', 'data'),
	Output('store-geo-stats', 'data'),
	Output('company-data', 'children'),
	Output('processing-state', 'data', allow_duplicate=True),
	Input('search-trigger', 'data'),
	State('processing-state', 'data'),
	State('store-params', 'data'),
	prevent_initial_call=True
)

def perform_search(trigger, processing, params):
	if not trigger or not processing:
		raise dash.exceptions.PreventUpdate
	cnpj14 = trigger.get('cnpj')
	if not cnpj14:
		return (dash.no_update, dash.no_update, dash.no_update,
			dash.no_update, dash.no_update, 'Informe um CNPJ válido.', False)
	if not run_search:
		return None, None, None, None, None, 'Dependência indisponível.', False
	cfg = dict(params or {})
	try:
		cfg['top_k'] = max(1, int(cfg.get('top_k', 30)))
	except Exception:
		cfg['top_k'] = 30
	try:
		cfg['top_candidates'] = max(1, int(cfg.get('top_candidates', 300)))
	except Exception:
		cfg['top_candidates'] = 300
	company, stats, editais, geo_stats = run_search(cnpj14, cfg)
	top_limit = int(cfg.get('top_k', 30))
	editais = (editais or [])[:top_limit]
	contratos = fetch_contratos_fornecedor(cnpj14)
	try:
		comp = {
			'razao_social': (company or {}).get('razao_social') or '-',
			'cnpj': (company or {}).get('cnpj') or cnpj14,
			'municipio': (company or {}).get('municipio') or '-',
			'uf': (company or {}).get('uf') or '-',
			'situacao_cadastral': (company or {}).get('situacao_cadastral'),
			'data_inicio_atividade': (company or {}).get('data_inicio_atividade'),
			'porte_empresa': (company or {}).get('porte_empresa'),
			'cnae_principal': (company or {}).get('cnae_principal'),
			'cnaes_secundarios': (company or {}).get('cnaes_secundarios') or [],
			'capital_social': (company or {}).get('capital_social'),
		}
		principal_code, secondary_codes = extract_cnae_codes(comp.get('cnae_principal'), comp.get('cnaes_secundarios'))
		lookup_codes = [code for code in ([principal_code] + secondary_codes) if code]
		desc_map = fetch_cnae_descriptions(lookup_codes)
		principal_display = format_cnae_with_desc(principal_code, desc_map)
		secondary_display_list = [format_cnae_with_desc(code, desc_map) for code in secondary_codes]
		secondary_display = '; '.join([item for item in secondary_display_list if item])
		# Renderização lista neutra (sem cabeçalho azul) usando estilos centrais data_*.
		rows = [
			('Razão social', comp.get('razao_social') or '-'),
			('CNPJ', format_cnpj_display(comp.get('cnpj') or cnpj14)),
			('Município/UF', f"{comp.get('municipio') or '-'} / {comp.get('uf') or '-'}"),
			('Situação', comp.get('situacao_cadastral') or '-'),
			('Início atividade', format_date_br(comp.get('data_inicio_atividade')) if comp.get('data_inicio_atividade') else '-'),
			('Porte', comp.get('porte_empresa') or '-'),
			('CNAE principal', principal_display or '-'),
			('CNAEs secundários', secondary_display or '-'),
			('Capital social', f"R$ {format_currency(comp.get('capital_social'))}" if comp.get('capital_social') else '-'),
		]
		company_text = html.Div([
			html.Div([
				html.Div([
					html.Span(label, style=styles['data_label']),
					html.Span(str(value), style=styles['data_value'])
				], style=styles['data_row'])
				for (label, value) in rows
			])
		], style=styles['data_table'])
	except Exception:
		company_text = '—'
	return company, contratos, editais, stats, geo_stats, company_text, False


# Callback 3: atualiza botão (spinner / seta)
@app.callback(
	Output('btn-buscar', 'children'),
	Output('btn-buscar', 'disabled'),
	Output('btn-buscar', 'style'),
	Input('processing-state', 'data')
)

def update_button(is_processing):
	if is_processing:
		return html.I(className="fas fa-spinner fa-spin", style={'color': 'white'}), True, {**styles['arrow_button'], 'opacity': '1'}
	else:
		return html.I(className="fas fa-arrow-right"), False, styles['arrow_button']

# Toggle do card de Parâmetros (expandir/colapsar)
@app.callback(
	Output('params-collapse', 'is_open'),
	Input('params-toggle-btn', 'n_clicks'),
	State('params-collapse', 'is_open'),
	prevent_initial_call=True
)
def toggle_params(n, is_open):
	if not n:
		raise dash.exceptions.PreventUpdate
	return not bool(is_open)

# Callback parâmetros: atualizar store-params quando qualquer input mudar
@app.callback(
	Output('store-params', 'data'),
	Input('param-top-k', 'value'),
	Input('param-top-candidates', 'value'),
	Input('param-sample-contratos', 'value'),
	Input('param-geo-weight', 'value'),
	Input('param-geo-tau', 'value'),
	Input('param-tau-hq', 'value'),
	Input('param-tau-disp', 'value'),
	Input('param-use-geo', 'value'),
	Input('param-geo-adapt', 'value'),
	Input('param-filter-expired', 'value'),
	State('store-params', 'data'),
	prevent_initial_call=False
)
def update_params(top_k, top_candidates, sample_contratos, geo_weight, geo_tau, tau_hq, tau_disp, use_geo_list, geo_adapt_list, filter_exp_list, current):
	try:
		cfg = dict(current or {})
		# Sanitizações
		if top_k is not None:
			cfg['top_k'] = max(1, int(top_k))
		if top_candidates is not None:
			cfg['top_candidates'] = max(1, int(top_candidates))
		if sample_contratos is not None:
			cfg['sample_contratos'] = max(1, int(sample_contratos))
		if geo_weight is not None:
			try:
				gw = float(geo_weight)
				cfg['geo_weight'] = max(0.0, min(1.0, gw))
			except Exception:
				pass
		if geo_tau is not None:
			cfg['geo_tau'] = max(0.0, float(geo_tau))
		if tau_hq is not None:
			cfg['tau_hq'] = max(0.0, float(tau_hq))
		if tau_disp is not None:
			cfg['tau_disp'] = max(0.0, float(tau_disp))
		cfg['use_geo'] = 'yes' in (use_geo_list or [])
		cfg['geo_adapt'] = 'yes' in (geo_adapt_list or [])
		cfg['filter_expired'] = 'yes' in (filter_exp_list or [])
		return cfg
	except Exception:
		return current


@app.callback(
	Output('table-contratos', 'data'),
	Input('store-contratos', 'data')
)

def render_contratos(contratos):
	if not contratos:
		return []
	out = []
	for i, r in enumerate(contratos, 1):
		out.append({
			'rank': i,
			'orgao': r.get('orgao_entidade_razao_social') or '-',
			'municipio': r.get('unidade_orgao_municipio_nome') or '-',
			'uf': r.get('unidade_orgao_uf_sigla') or '-',
			'similaridade': '',
			'valor': format_currency(r.get('valor_total_homologado')),
			'data': format_date_br(r.get('data_encerramento_proposta')),
			'numero_controle_pncp': r.get('numero_controle_pncp'),
			'ibge': r.get('unidade_orgao_codigo_ibge'),
			'link': r.get('link_sistema_origem'),
			'objeto': r.get('objeto_contrato') or '',
		})
	return out


@app.callback(
	Output('table-editais', 'data'),
	Input('store-editais', 'data')
)

def render_editais(editais):
	if not editais:
		return []
	out = []
	for i, r in enumerate(editais, 1):
		sim_val = float(r.get('similarity') or 0.0)
		score_val = float(r.get('final_score') or r.get('similarity') or 0.0)
		out.append({
			'rank': i,
			'orgao': r.get('orgao_entidade_razao_social') or '-',
			'municipio': r.get('unidade_orgao_municipio_nome') or '-',
			'uf': r.get('unidade_orgao_uf_sigla') or '-',
			'similaridade': f"{sim_val:.3f}",
			'score_final': f"{score_val:.3f}",
			'valor': format_currency(r.get('valor_total_homologado')),
			'data': format_date_br(r.get('data_encerramento_proposta')),
			'numero_controle_pncp': r.get('numero_controle_pncp'),
			'ibge': r.get('unidade_orgao_codigo_ibge'),
			'link': r.get('link_sistema_origem'),
			'objeto': r.get('objeto_compra') or r.get('objeto') or '',
		})
	return out


# Mostrar/ocultar tabelas vs. placeholders
@app.callback(
	Output('contratos-table-wrap', 'style'),
	Output('contratos-empty', 'style'),
	Output('contratos-detail-wrap', 'style'),
	Input('store-contratos', 'data')
)

def toggle_contratos_block(contratos):
	has_data = bool(contratos)
	table_style = {} if has_data else {'display': 'none'}
	empty_style = {'display': 'none'} if has_data else {}
	detail_style = styles['result_card'] if has_data else {'display': 'none'}
	return table_style, empty_style, detail_style


@app.callback(
	Output('editais-table-wrap', 'style'),
	Output('editais-empty', 'style'),
	Output('editais-detail-wrap', 'style'),
	Input('store-editais', 'data')
)

def toggle_editais_block(editais):
	has_data = bool(editais)
	table_style = {} if has_data else {'display': 'none'}
	empty_style = {'display': 'none'} if has_data else {}
	detail_style = styles['result_card'] if has_data else {'display': 'none'}
	return table_style, empty_style, detail_style


@app.callback(
	Output('map-wrap', 'style'),
	Output('map-empty', 'style'),
	Input('store-contratos', 'data'),
	Input('store-editais', 'data')
)

def toggle_map_block(contratos, editais):
	has_any = bool(contratos) or bool(editais)
	map_style = {} if has_any else {'display': 'none'}
	empty_style = {'display': 'none'} if has_any else {}
	return map_style, empty_style


@app.callback(
	Output('contrato-detalhe', 'children'),
	Input('table-contratos', 'active_cell'),
	State('table-contratos', 'data')
)

def show_contrato_detail(active_cell, data):
	if not active_cell or not data:
		return "Selecione uma linha para ver os detalhes."
	i = active_cell.get('row')
	try:
		row = data[i]
	except Exception:
		return "Selecione uma linha para ver os detalhes."
	return html.Div([
		html.Div(f"Órgão: {row.get('orgao','-')}", style={'fontWeight': 'bold'}),
		html.Div(f"Local: {row.get('municipio','-')}/{row.get('uf','-')}") ,
		html.Div(f"Valor: R$ {row.get('valor','-')}") ,
		html.Div(f"Data de Encerramento: {row.get('data','-')}") ,
		html.Div(f"Objeto: {row.get('objeto','-')}")
	])


@app.callback(
	Output('edital-detalhe', 'children'),
	Input('table-editais', 'active_cell'),
	State('table-editais', 'data')
)

def show_edital_detail(active_cell, data):
	if not active_cell or not data:
		return "Selecione uma linha para ver os detalhes."
	i = active_cell.get('row')
	try:
		row = data[i]
	except Exception:
		return "Selecione uma linha para ver os detalhes."
	return html.Div([
		html.Div(f"Órgão: {row.get('orgao','-')}", style={'fontWeight': 'bold'}),
		html.Div(f"Local: {row.get('municipio','-')}/{row.get('uf','-')}") ,
		html.Div(f"Simil.: {row.get('similaridade','-')}") ,
		html.Div(f"Score final: {row.get('score_final','-')}") ,
		html.Div(f"Objeto: {row.get('objeto','-')}")
	])


@app.callback(
	Output('map-container', 'children'),
	Input('store-contratos', 'data'),
	Input('store-editais', 'data'),
	Input('store-company', 'data'),
	Input('store-stats', 'data')
)

def render_map(contratos, editais, company, stats):
	try:
		import folium  # type: ignore
	except Exception:
		return html.Div('Folium não instalado.')

	# Plugins para clustering e subgrupos
	try:
		from folium.plugins import MarkerCluster, FeatureGroupSubGroup  # type: ignore
	except Exception:
		MarkerCluster = None  # type: ignore
		FeatureGroupSubGroup = None  # type: ignore

	if not contratos and not editais:
		return html.Div('Sem dados para mapear.')

	def _get_ibge(row: Dict[str, Any]) -> Optional[str]:
		for k in ('ibge', 'unidade_orgao_codigo_ibge', 'codigo_ibge_municipio', 'municipio_codigo_ibge'):
			v = row.get(k)
			if v not in (None, '', '0'):
				return str(v)
		return None

	# Mapas auxiliares
	def _to_float(v) -> float:
		try:
			return float(v)
		except Exception:
			return 0.0

	def edital_color(sim: float) -> str:
		# Faixas de cor nomeadas do Folium.Icon (opção B)
		if sim >= 0.90:
			return 'darkred'
		elif sim >= 0.80:
			return 'red'
		elif sim >= 0.70:
			return 'lightred'
		elif sim >= 0.60:
			return 'orange'
		else:
			return 'beige'

	ibges: List[str] = []
	for lst in (contratos or []):
		v = _get_ibge(lst)
		if v:
			ibges.append(v)
	for lst in (editais or []):
		v = _get_ibge(lst)
		if v:
			ibges.append(v)

	coords_map: Dict[str, Tuple[float, float]] = {}
	if load_municipios_coords and ibges:
		conn = get_db_conn()
		try:
			with conn:
				coords_map = load_municipios_coords(conn, ibges)
		finally:
			try:
				conn.close()
			except Exception:
				pass

	m = folium.Map(location=[-15.78, -47.93], zoom_start=4, control_scale=False, zoom_control=False)
	# Garante inicialização para evitar UnboundLocalError em falhas durante construção
	legend_html: str = ""
	lat_list: List[float] = []
	lon_list: List[float] = []

	# Cluster raiz + subgrupos (mantém toggles independentes)
	use_cluster = bool(CLUSTER_MODE and MarkerCluster and FeatureGroupSubGroup)
	if use_cluster:
		cluster_root = MarkerCluster(name='Clusters').add_to(m)
		contratos_group = FeatureGroupSubGroup(cluster_root, 'Contratos'); m.add_child(contratos_group)
		editais_group = FeatureGroupSubGroup(cluster_root, 'Editais'); m.add_child(editais_group)
		hq_group = FeatureGroupSubGroup(cluster_root, 'Matriz'); m.add_child(hq_group)
	else:
		# Fallback sem clustering se plugins indisponíveis
		contratos_group = folium.FeatureGroup(name='Contratos', show=True).add_to(m)
		editais_group = folium.FeatureGroup(name='Editais', show=True).add_to(m)
		hq_group = folium.FeatureGroup(name='Matriz', show=True).add_to(m)

	# Jitter (500m–1km) apenas quando sem cluster para reduzir sobreposição
	apply_jitter = not use_cluster
	def _jitter_latlon(lat: float, lon: float) -> Tuple[float, float]:
		try:
			r_m = random.uniform(500.0, 1000.0)
			theta = random.uniform(0.0, 2 * math.pi)
			dlat = (r_m * math.cos(theta)) / 111320.0
			denom = 111320.0 * max(0.00001, math.cos(math.radians(lat)))
			dlon = (r_m * math.sin(theta)) / denom
			return lat + dlat, lon + dlon
		except Exception:
			return lat, lon

	# Contratos: popup largo + objeto
	for r in (contratos or []):
		k = _get_ibge(r)
		latlon = coords_map.get(k) if k else None
		if not latlon:
			continue
		lat, lon = latlon
		if apply_jitter:
			lat, lon = _jitter_latlon(lat, lon)
		lat_list.append(lat)
		lon_list.append(lon)
		obj_c = r.get('objeto_contrato') or r.get('objeto') or ''
		popup_html_c = (
			f"<b>Órgão:</b> {r.get('orgao_entidade_razao_social') or r.get('orgao','-')}<br>"
			f"<b>Local:</b> {r.get('unidade_orgao_municipio_nome') or r.get('municipio','-')}/{r.get('unidade_orgao_uf_sigla') or r.get('uf','-')}<br>"
			f"<b>Data Fim:</b> {format_date_br(r.get('data_encerramento_proposta') or r.get('data'))}<br>"
			f"<b>Valor:</b> R$ {format_currency(r.get('valor_total_homologado') or r.get('valor'))}<br>"
			f"<b>Objeto:</b> {obj_c}"
		)
		popup_c = folium.Popup(popup_html_c, max_width=340)
		folium.Marker(
			[lat, lon],
			popup=popup_c,
			icon=folium.Icon(color='green', icon='check', prefix='fa', icon_color='white')
		).add_to(contratos_group)

	# Editais: cor por similaridade (v2) ou cor fixa (v1) + popup largo sem similaridade
	for r in (editais or []):
		k = _get_ibge(r)
		latlon = coords_map.get(k) if k else None
		if not latlon:
			continue
		lat, lon = latlon
		if apply_jitter:
			lat, lon = _jitter_latlon(lat, lon)
		lat_list.append(lat)
		lon_list.append(lon)
		sim = _to_float(r.get('similarity') or r.get('similaridade') or 0.0)
		score = _to_float(r.get('final_score') or r.get('similarity') or 0.0)
		color = 'red' if (MAP_VIEW_MODE == 'v1') else edital_color(score)
		obj_e = r.get('objeto_compra') or r.get('objeto') or ''
		popup_html_e = (
			f"<b>Órgão:</b> {r.get('orgao_entidade_razao_social') or r.get('orgao','-')}<br>"
			f"<b>Local:</b> {r.get('unidade_orgao_municipio_nome') or r.get('municipio','-')}/{r.get('unidade_orgao_uf_sigla') or r.get('uf','-')}<br>"
			f"<b>Data Fim:</b> {format_date_br(r.get('data_encerramento_proposta') or r.get('data'))}<br>"
			f"<b>Similaridade:</b> {sim:.3f}<br>"
			f"<b>Score final:</b> {score:.3f}<br>"
			f"<b>Objeto:</b> {obj_e}"
		)
		popup_e = folium.Popup(popup_html_e, max_width=340)
		folium.Marker(
			[lat, lon],
			popup=popup_e,
			icon=folium.Icon(color=color, icon='info', prefix='fa', icon_color='white')
		).add_to(editais_group)

	# Popup da Matriz com dados do card da empresa
	comp = company if isinstance(company, dict) else {}
	rs = comp.get('razao_social') or '-'
	cnpj_disp = format_cnpj_display(comp.get('cnpj')) if comp.get('cnpj') else '-'
	mun = comp.get('municipio') or '-'
	uf = comp.get('uf') or '-'
	sit = comp.get('situacao_cadastral') or '-'
	inicio = format_date_br(comp.get('data_inicio_atividade')) if comp.get('data_inicio_atividade') else '-'
	porte = comp.get('porte_empresa') or '-'
	cnae = format_cnae_display(comp.get('cnae_principal')) if comp.get('cnae_principal') else '-'
	cap = f"R$ {format_currency(comp.get('capital_social'))}" if comp.get('capital_social') else '-'
	popup_html_hq = (
		"<b>Matriz (HQ)</b><br>"
		f"<b>Razão Social:</b> {rs}<br>"
		f"<b>CNPJ:</b> {cnpj_disp}<br>"
		f"<b>Município/UF:</b> {mun}/{uf}<br>"
		f"<b>Situação:</b> {sit}<br>"
		f"<b>Início atividade:</b> {inicio}<br>"
		f"<b>Porte:</b> {porte}<br>"
		f"<b>CNAE principal:</b> {cnae}<br>"
		f"<b>Capital social:</b> {cap}"
	)
	popup_hq = folium.Popup(popup_html_hq, max_width=340)

	hq_lat = stats.get('hq_lat') if isinstance(stats, dict) else None
	hq_lon = stats.get('hq_lon') if isinstance(stats, dict) else None
	if hq_lat is not None and hq_lon is not None:
		folium.Marker(
			[hq_lat, hq_lon],
			popup=popup_hq,
			icon=folium.Icon(color='black', icon='home', prefix='fa', icon_color='white')
		).add_to(hq_group)
	else:
		matriz_ibge = None
		if company and isinstance(company, dict) and extract_hq_ibge:
			matriz_ibge = extract_hq_ibge(company)
		if matriz_ibge and matriz_ibge in coords_map:
			lat_matriz, lon_matriz = coords_map[matriz_ibge]
			folium.Marker(
				[lat_matriz, lon_matriz],
				popup=popup_hq,
				icon=folium.Icon(color='black', icon='home', prefix='fa', icon_color='white')
			).add_to(hq_group)

	# Legenda interativa: muda conforme o modo
	if MAP_VIEW_MODE == 'v1':
		legend_editais_block = """
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-editais' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:red;border-radius:2px;'></span>
	    <span>Editais</span>
	  </label>
		"""
	else:
		legend_editais_block = """
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-editais' checked />
		    <span> Editais (score final) </span>
	  </label>
	  <div style='margin:4px 0 6px 20px; display:flex; flex-direction:column; gap:2px;'>
	    <div><span style='display:inline-block;width:12px;height:12px;background:#7f0000; border-radius:2px; margin-right:6px;'></span>≥ 0.90</div>
	    <div><span style='display:inline-block;width:12px;height:12px;background:#d32f2f; border-radius:2px; margin-right:6px;'></span>0.80–0.90</div>
	    <div><span style='display:inline-block;width:12px;height:12px;background:#ef5350; border-radius:2px; margin-right:6px;'></span>0.70–0.80</div>
	    <div><span style='display:inline-block;width:12px;height:12px;background:#fb8c00; border-radius:2px; margin-right:6px;'></span>0.60–0.70</div>
	    <div><span style='display:inline-block;width:12px;height:12px;background:#f5e5c9; border-radius:2px; margin-right:6px;'></span>< 0.60</div>
	  </div>
		"""

	legend_html = f"""
	<div style='position: fixed; top: 10px; left: 10px; z-index:9999; background: white; padding:8px 10px; border:1px solid #ccc; border-radius:6px; font-size:12px; line-height:16px;'>
	  <div style='font-weight:bold; margin-bottom:6px;'>Legenda</div>
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-contratos' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:green;border-radius:2px;'></span>
	    <span>Contratos</span>
	  </label>
	  {legend_editais_block}
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-hq' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:black;border-radius:2px;'></span>
	    <span>Matriz</span>
	  </label>
	</div>
	<script>
	  (function(){{
	    function ready(){{
	      try {{
	        var mapRef = {m.get_name()};
	        var layerContratos = {contratos_group.get_name()};
	        var layerEditais = {editais_group.get_name()};
	        var layerHQ = {hq_group.get_name()};
	        function bindToggle(id, layer) {{
	          var cb = document.getElementById(id);
	          if (!cb) return;
	          function apply() {{
	            if (cb.checked) {{
	              if (!mapRef.hasLayer(layer)) mapRef.addLayer(layer);
	            }} else {{
	              if (mapRef.hasLayer(layer)) mapRef.removeLayer(layer);
	            }}
	          }}
	          cb.addEventListener('change', apply);
	          apply();
	        }}
	        bindToggle('legend-toggle-contratos', layerContratos);
	        bindToggle('legend-toggle-editais', layerEditais);
	        bindToggle('legend-toggle-hq', layerHQ);
	        // Reposiciona controles de zoom (desativados no Map inicial)
	        if (!mapRef._zoomControl) {{
	          L.control.zoom({{position:'topright'}}).addTo(mapRef);
	        }}
	      }} catch (e) {{
	        return setTimeout(ready, 60);
	      }}
	    }}
	    if (document.readyState === 'complete') {{
	      setTimeout(ready, 0);
	    }} else {{
	      window.addEventListener('load', ready);
	    }}
	  }})();
	</script>
	"""
	from folium import Element  # type: ignore
	m.get_root().html.add_child(Element(legend_html))

	html_buf = io.BytesIO()
	m.save(html_buf, close_file=False)
	html_str = html_buf.getvalue().decode('utf-8')
	return html.Iframe(srcDoc=html_str, style={'width': '100%', 'height': '100%', 'border': 'none'})


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="GvG Sommelier v2")
	parser.add_argument("--view_map", choices=["v1", "v2"], default=os.environ.get("VIEW_MAP", MAP_VIEW_MODE))
	parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8051")))
	parser.add_argument("--cluster", action="store_true", help="Habilita clusters no mapa")
	args = parser.parse_args()
	# Atualiza modo global
	MAP_VIEW_MODE = (args.view_map or "v2").lower()
	CLUSTER_MODE = bool(args.cluster)
	app.run_server(host="127.0.0.1", port=args.port, debug=False)
