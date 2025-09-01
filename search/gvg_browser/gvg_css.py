"""
CSS utilitário e estilos para o GSB (Dash).

Este módulo concentra:
- O dicionário `styles` usado nos componentes (antes no GSB)
- CSS base para controles, tabelas, etc. (BASE_CSS)
- CSS específico para Markdown do resumo (MARKDOWN_CSS)
"""

# Estilos de componentes (antes definidos em GSB)
styles = {
    'container': {
        'display': 'flex',
        'height': 'calc(100vh - 60px)',
        'width': '100%',
        'marginTop': '60px',
        'padding': '5px',
    },
    'left_panel': {
        'width': '35%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
        'display': 'flex',
        'flexDirection': 'column',
        'height': 'calc(100vh - 100px)'
    },
    'right_panel': {
        'width': '65%',
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
    'height': 'calc(100vh - 100px)',
    'position': 'relative'
    },
    'controls_group': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'display': 'flex',
        'flexDirection': 'column',
        'gap': '8px',
        'marginTop': '8px',
    },
    'submit_button': {
        'backgroundColor': '#FF5722',
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'height': '36px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer'
    },
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'alignItems': 'center',
        'marginTop': '10px',
         'border': '2px solid #FF5722',
    },
    'input_field': {
        'flex': '1',
        'border': 'none',
        'outline': 'none',
        'padding': '8px',
        'backgroundColor': 'transparent'
    },
    'arrow_button': {
        'backgroundColor': '#FF5722',
        'color': 'white',
        'border': 'none',
        'borderRadius': '50%',
        'width': '32px',
        'height': '32px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer'
    },
    'result_card': {
        'backgroundColor': 'white',
        'borderRadius': '15px',
        'padding': '15px',
        'marginBottom': '12px',
        'outline': '#E0EAF9 solid 1px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
        'position': 'relative'
    },
    'logo': {
        'marginBottom': '20px',
        'maxWidth': '100px'
    },
}

styles['result_number'] = {
    'position': 'absolute',
    'top': '10px',
    'left': '10px',
    'backgroundColor': '#FF5722',
    'color': 'white',
    'borderRadius': '50%',
    'width': '24px',
    'height': '24px',
    'display': 'flex',
    'padding': '5px',
    'alignItems': 'center',
    'justifyContent': 'center',
    'fontSize': '12px',
    'fontWeight': 'bold',
}

styles['card_title'] = {
    'fontWeight': 'bold',
    'color': '#003A70',
    'paddingRight': '8px',
    'paddingBottom': '8px',
}


# CSS base (antes inline no app.index_string do GSB)
BASE_CSS = """
/* Compact controls inside left panel config card */
.gvg-controls .Select-control { min-height: 32px; height: 32px; border-radius: 16px; font-size: 12px; border: 1px solid #D0D7E2; box-shadow: none; }
.gvg-controls .is-focused .Select-control, .gvg-controls .Select.is-focused > .Select-control { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); }
.gvg-controls .is-open .Select-control { border-color: #52ACFF; }
.gvg-controls .Select-value-label,
.gvg-controls .Select-option,
.gvg-controls .VirtualizedSelectOption,
.gvg-controls .Select-placeholder { font-size: 12px; }
.gvg-controls .Select-menu-outer { font-size: 12px; border-radius: 12px; }
.gvg-controls input[type="number"] { height: 32px; border-radius: 16px; font-size: 12px; padding: 6px 10px; border: 1px solid #D0D7E2; outline: none; }
.gvg-controls input[type="number"]:focus { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); outline: none; }
/* Reduce label spacing slightly */
.gvg-controls label { font-size: 12px; margin-bottom: 4px; }
/* Remove default input spinners for consistent look (optional) */
.gvg-controls input[type=number]::-webkit-outer-spin-button,
.gvg-controls input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.gvg-controls input[type=number] { -moz-appearance: textfield; }
/* Horizontal form rows */
.gvg-controls .gvg-form-row { display: flex; align-items: center; gap: 5px; margin-bottom: 4px; }
.gvg-controls .gvg-form-label { width: 130px; min-width: 130px; font-size: 12px; color: #003A70; margin: 0; font-weight: 600; }
.gvg-controls .gvg-form-row > *:last-child { flex: 1; }

/* History row hover: show delete button */
.history-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.history-item-row:hover .delete-btn { opacity: 1; }
.history-item-row .delete-btn:hover { background-color: #FDEDEC; }

/* Bigger sort arrows in DataTable header and orange color */
.dash-table-container .dash-spreadsheet-container th .column-header--sort { margin-left: 6px; }
.dash-table-container .dash-spreadsheet-container th .column-header--sort .column-header--sort-icon { font-size: 18px; color: #FF5722; }
.dash-table-container .dash-spreadsheet-container th .column-header--sort:after { font-size: 18px; color: #FF5722; }

#gvg-center-spinner { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 10; display: flex; flex-direction: column; align-items: center; width: 260px; }
"""

# Classe aplicada em dcc.Markdown(children=..., className='markdown-summary')
MARKDOWN_CSS = (
    "/** Títulos menores para o resumo em Markdown **/\n"
    ".markdown-summary h1 { font-size: 18px; line-height: 1.25; }\n"
    ".markdown-summary h2 { font-size: 16px; line-height: 1.25; }\n"
    ".markdown-summary h3 { font-size: 14px; line-height: 1.25; }\n"
    ".markdown-summary h4 { font-size: 13px; line-height: 1.25; }\n"
    ".markdown-summary h5 { font-size: 12px; line-height: 1.25; }\n"
    ".markdown-summary h6 { font-size: 11px; line-height: 1.25; }\n"
)

CSS_ALL = BASE_CSS + "\n" + MARKDOWN_CSS

__all__ = ["styles", "BASE_CSS", "MARKDOWN_CSS", "CSS_ALL"]
