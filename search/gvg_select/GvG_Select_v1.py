r"""Sommelier — Skeleton inicial (layout fiel ao Report)

Observação:
- Apenas estrutura e estilos (sem callbacks e sem lógica de dados).
- Estilos importados e centralizados via gvg_styles.py.
"""

import os
import sys
import io
import json
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State

# Import robusto dos estilos para funcionar tanto como módulo quanto como script direto
try:
	from ..gvg_browser.gvg_styles import styles, CSS_ALL  # type: ignore
except Exception:
	try:
		THIS_DIR = os.path.dirname(__file__)
		if THIS_DIR not in sys.path:
			sys.path.insert(0, THIS_DIR)
		import gvg_styles as _gvg_styles  # type: ignore
		styles, CSS_ALL = _gvg_styles.styles, _gvg_styles.CSS_ALL
	except Exception:
		# Último fallback (se 'search' estiver como pacote válido)
		from search.gvg_browser.gvg_styles import styles, CSS_ALL  # type: ignore

# --- Caminho para importar o motor v1_3 ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CNPJ_PATH = os.path.join(ROOT, 'scripts', 'cnpj_search')
if CNPJ_PATH not in sys.path:
	sys.path.insert(0, CNPJ_PATH)

try:
	from gvg_cnpj_search import (
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
app.title = "Sommelier"

# Injeta CSS global centralizado (gvg_styles.CSS_ALL) no index HTML
app.index_string = (
    """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>Sommelier</title>
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
	return html.Div([
		# Campo CNPJ + botão (placeholder visual)
		html.Div([
			html.Div([
				dcc.Input(id="input-cnpj", placeholder="CNPJ 00.000.000/0001-00", type="text", style={**styles['input_field']}, debounce=True),
				html.Button(html.I(className="fas fa-arrow-right"), id="btn-buscar", n_clicks=0, style=styles['arrow_button'])
			], style=styles['input_container'])
		], className="gvg-controls"),

		# Card Dados (dinâmico)
		html.Div([
			html.Div("Dados", style=styles['card_title']),
			html.Div("Nenhum dado para mostrar.", id="company-data")
		], style={**styles['result_card'], **styles['mt_same_card_gap']}),

		# Card Histórico
		#html.Div([
		#	html.Div("Histórico", style=styles['card_title']),
		#	html.Div([
		#		html.Div([
		#			html.Button("CNPJ 00.000.001/0001-00", style=styles['btn_list_item']),
		#			html.Button("→", style=styles['btn_icon_sm'])
		#		], style=styles['list_row_compact'], className="history-item-row"),
		#			html.Button("CNPJ 00.000.001/0001-00", style=styles['btn_list_item']),
		#			html.Button("→", style=styles['btn_icon_sm'])
		#		], style=styles['list_row_compact'], className="history-item-row")
		#	])
		#], style=styles['result_card'])
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
			html.Div("GvG Sommelier", style=styles['header_title'], className="gvg-header-title")
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
		dcc.Store(id='store-params', data={
			'top_k': 30,
			'top_candidates': 120,
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
		return dash.no_update, dash.no_update, dash.no_update, dash.no_update, 'Informe um CNPJ válido.', False
	if not run_search:
		return None, None, None, None, 'Dependência indisponível.', False
	cfg = dict(params or {})
	try:
		tk = int(cfg.get('top_k', 30))
		cfg['top_candidates'] = max(1, min(int(cfg.get('top_candidates', 120)), tk * 5))
	except Exception:
		cfg['top_candidates'] = 120
	company, stats, editais, _geo = run_search(cnpj14, cfg)
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
			'capital_social': (company or {}).get('capital_social'),
		}
		# Renderização lista neutra (sem cabeçalho azul) usando estilos centrais data_*.
		rows = [
			('Razão social', comp.get('razao_social') or '-'),
			('CNPJ', format_cnpj_display(comp.get('cnpj') or cnpj14)),
			('Município/UF', f"{comp.get('municipio') or '-'} / {comp.get('uf') or '-'}"),
			('Situação', comp.get('situacao_cadastral') or '-'),
			('Início atividade', format_date_br(comp.get('data_inicio_atividade')) if comp.get('data_inicio_atividade') else '-'),
			('Porte', comp.get('porte_empresa') or '-'),
			('CNAE principal', format_cnae_display(comp.get('cnae_principal')) if comp.get('cnae_principal') else '-'),
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
	return company, contratos, editais, stats, company_text, False


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
		out.append({
			'rank': i,
			'orgao': r.get('orgao_entidade_razao_social') or '-',
			'municipio': r.get('unidade_orgao_municipio_nome') or '-',
			'uf': r.get('unidade_orgao_uf_sigla') or '-',
			'similaridade': f"{(r.get('similarity') or 0.0):.3f}",
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
		html.Div(f"Local: {row.get('municipio','-')}/{row.get('uf','-')}"),
		html.Div(f"Valor: R$ {row.get('valor','-')}"),
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
		html.Div(f"Local: {row.get('municipio','-')}/{row.get('uf','-')}"),
		html.Div(f"Simil.: {row.get('similaridade','-')}") ,
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

	if not contratos and not editais:
		return html.Div('Sem dados para mapear.')

	def _get_ibge(row: Dict[str, Any]) -> Optional[str]:
		for k in ('ibge', 'unidade_orgao_codigo_ibge', 'codigo_ibge_municipio', 'municipio_codigo_ibge'):
			v = row.get(k)
			if v not in (None, '', '0'):
				return str(v)
		return None

	# Mapas auxiliares (para cores por similaridade dos editais)
	def _to_float(v) -> float:
		try:
			return float(v)
		except Exception:
			return 0.0

	def edital_color(sim: float) -> str:
		# Faixas de cor nomeadas do Folium.Icon (consistente com v2)
		if sim >= 0.90:
			return 'darkred'
		elif sim >= 0.80:
			return 'red'
		elif sim >= 0.70:
			return 'lightred'
		elif sim >= 0.60:
			return 'orange'
		else:
			return 'yellow'

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

	m = folium.Map(location=[-15.78, -47.93], zoom_start=4, control_scale=True)
	lat_list: List[float] = []
	lon_list: List[float] = []

	# Camadas por tipo de ponto (permite ligar/desligar via controle de camadas)
	contratos_group = folium.FeatureGroup(name='Contratos', show=True).add_to(m)
	editais_group = folium.FeatureGroup(name='Editais', show=True).add_to(m)
	hq_group = folium.FeatureGroup(name='Matriz', show=True).add_to(m)

	for r in (contratos or []):
		k = _get_ibge(r)
		latlon = coords_map.get(k) if k else None
		if not latlon:
			continue
		lat, lon = latlon
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
		# Ícone Font Awesome para contratos (verde, check)
		folium.Marker(
			[lat, lon],
			popup=popup_c,
			icon=folium.Icon(color='green', icon='check', prefix='fa', icon_color='white')
		).add_to(contratos_group)

	for r in (editais or []):
		k = _get_ibge(r)
		latlon = coords_map.get(k) if k else None
		if not latlon:
			continue
		lat, lon = latlon
		lat_list.append(lat)
		lon_list.append(lon)
		sim = _to_float(r.get('similarity') or r.get('similaridade') or 0.0)
		color = edital_color(sim)
		obj_e = r.get('objeto_compra') or r.get('objeto') or ''
		popup_html_e = (
			f"<b>Órgão:</b> {r.get('orgao_entidade_razao_social') or r.get('orgao','-')}<br>"
			f"<b>Local:</b> {r.get('unidade_orgao_municipio_nome') or r.get('municipio','-')}/{r.get('unidade_orgao_uf_sigla') or r.get('uf','-')}<br>"
			f"<b>Data Fim:</b> {format_date_br(r.get('data_encerramento_proposta') or r.get('data'))}<br>"
			f"<b>Objeto:</b> {obj_e}"
		)
		popup_e = folium.Popup(popup_html_e, max_width=340)
		# Ícone Font Awesome para editais (cor por similaridade)
		folium.Marker(
			[lat, lon],
			popup=popup_e,
			icon=folium.Icon(color=color, icon='info', prefix='fa', icon_color='white')
		).add_to(editais_group)

	hq_lat = stats.get('hq_lat') if isinstance(stats, dict) else None
	hq_lon = stats.get('hq_lon') if isinstance(stats, dict) else None
	if hq_lat is not None and hq_lon is not None:
		folium.Marker(
			[hq_lat, hq_lon],
			popup='<b>Matriz (HQ)</b>',
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
				popup='<b>Matriz (HQ)</b>',
				icon=folium.Icon(color='black', icon='home', prefix='fa', icon_color='white')
			).add_to(hq_group)

	# Legenda interativa (checkboxes que ligam/desligam camadas)
	legend_html = f"""
	<div style='position: fixed; top: 10px; left: 10px; z-index:9999; background: white; padding:8px 10px; border:1px solid #ccc; border-radius:6px; font-size:12px; line-height:16px;'>
	  <div style='font-weight:bold; margin-bottom:6px;'>Legenda</div>
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-contratos' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:green;border-radius:2px;'></span>
	    <span>Contratos</span>
	  </label>
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-editais' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:red;border-radius:2px;'></span>
	    <span>Editais</span>
	  </label>
	  <label style='display:flex; align-items:center; gap:6px; margin:2px 0;'>
	    <input type='checkbox' id='legend-toggle-hq' checked />
	    <span style='display:inline-block;width:12px;height:12px;background:black;border-radius:2px;'></span>
	    <span>Matriz</span>
	  </label>
	</div>
	<script>
	  (function(){{
	    function ready(){{
		try:
			from gvg_cnpj_search import (
	        var layerContratos = {contratos_group.get_name()};
	        var layerEditais = {editais_group.get_name()};
	        var layerHQ = {hq_group.get_name()};
	        function bindToggle(id, layer) {{
	          var cb = document.getElementById(id);
	          if (!cb) return;
	          function apply() {{
			logging.exception('Falha ao importar gvg_cnpj_search')
	              if (!mapRef.hasLayer(layer)) mapRef.addLayer(layer);
	            }} else {{
	              if (mapRef.hasLayer(layer)) mapRef.removeLayer(layer);
	            }}
	          }}
	          cb.addEventListener('change', apply);
	          // aplica estado inicial
	          apply();
	        }}
	        bindToggle('legend-toggle-contratos', layerContratos);
	        bindToggle('legend-toggle-editais', layerEditais);
	        bindToggle('legend-toggle-hq', layerHQ);
	      }} catch (e) {{
	        // se o mapa/camadas ainda não existem, tenta novamente
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

	# (Legenda antiga removida; agora usamos a versão interativa acima)

	html_buf = io.BytesIO()
	m.save(html_buf, close_file=False)
	html_str = html_buf.getvalue().decode('utf-8')
	return html.Iframe(srcDoc=html_str, style={'width': '100%', 'height': '100%', 'border': 'none'})


if __name__ == "__main__":
	app.run_server(host="127.0.0.1", port=int(os.environ.get("PORT", "8050")), debug=False)
