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
        'width': '30%',  ### 30%
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
        'width': '70%', ### 70%
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
    'header_logo': {
        'height': '40px'
    },
    'header_title': {
        'marginLeft': '15px', 'color': '#003A70', 'fontWeight': 'bold', 'marginTop': '4px'
    },
    # --- Header (top bar) ---
    'header': {
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'backgroundColor': 'white',
        'padding': '10px 20px',
        'borderBottom': '1px solid #ddd',
        'width': '100%',
        'position': 'fixed',
        'top': 0,
        'zIndex': 1000
    },
    'header_left': {
        'display': 'flex',
        'alignItems': 'center'
    },
    'header_right': {
        'display': 'flex',
        'alignItems': 'center'
    },
    'header_user_badge': {
        'width': '32px', 'height': '32px', 'minWidth': '32px',
        'borderRadius': '50%', 'backgroundColor': '#FF5722',
        'color': 'white', 'fontWeight': 'bold', 'fontSize': '14px',
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'cursor': 'default'
    },
    # --- Progress / Spinner ---
    'progress_bar_container': {
        'marginTop': '10px',
        'width': '260px',
        'height': '6px',
        'border': '1px solid #FF5722',
        'backgroundColor': 'rgba(255, 87, 34, 0.08)',
        'borderRadius': '999px',
        'overflow': 'hidden'
    },
    'progress_fill': {
        'height': '100%',
        'backgroundColor': '#FF5722',
        'borderRadius': '999px',
        'transition': 'width 250ms ease'
    },
    'progress_label': {
        'marginTop': '6px', 'textAlign': 'center', 'color': '#FF5722', 'fontSize': '12px'
    },
    'center_spinner': {
        'display': 'none'
    },
    # --- History ---
    'history_item_button': {
        'backgroundColor': 'white',
        'color': '#003A70',
        'border': '1px solid #D0D7E2',
        'borderRadius': '16px',
        'display': 'block',
        'width': '100%',
        'textAlign': 'left',
        'padding': '8px 12px',
        'whiteSpace': 'normal',
        'wordBreak': 'break-word',
        'lineHeight': '1.25',
        'cursor': 'pointer'
    },
    'history_delete_btn': {
        'width': '28px', 'height': '28px', 'minWidth': '28px',
        'borderRadius': '50%', 'border': '1px solid #FF5722',
        'backgroundColor': 'white', 'color': '#FF5722',
        'cursor': 'pointer'
    },
    'history_item_row': {
        'display': 'flex', 'gap': '8px', 'alignItems': 'flex-start', 'marginBottom': '6px'
    },
    # --- Favorites (bookmarks) ---
    'fav_item_row': {
        'display': 'flex', 'gap': '8px', 'alignItems': 'flex-start', 'marginBottom': '6px'
    },
    'fav_item_button': {
        'backgroundColor': 'white',
        'color': '#003A70',
        'border': '1px solid #D0D7E2',
        'borderRadius': '16px',
        'display': 'block',
        'width': '100%',
        'textAlign': 'left',
        'padding': '8px 12px',
        'whiteSpace': 'normal',
        'wordBreak': 'break-word',
        'lineHeight': '1.25',
        'cursor': 'pointer'
    },
    'fav_delete_btn': {
        'width': '28px', 'height': '28px', 'minWidth': '28px',
        'borderRadius': '50%', 'border': '1px solid #FF5722',
        'backgroundColor': 'white', 'color': '#FF5722',
        'cursor': 'pointer'
    },
    'bookmark_btn': {
        'position': 'absolute', 'top': '10px', 'left': '40px',
        'width': '24px', 'height': '24px', 'minWidth': '24px',
        'border': 'none', 'backgroundColor': 'transparent', 'cursor': 'pointer',
        'color': '#FF5722'
    },
    # --- Buttons (pills) for details right panel ---
    'btn_pill': {
        'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none',
        'borderRadius': '16px', 'height': '28px', 'padding': '0 10px',
        'cursor': 'pointer', 'marginLeft': '6px'
    },
    'btn_pill_inverted': {
        'backgroundColor': 'white', 'color': '#FF5722', 'border': '1px solid #FF5722',
        'borderRadius': '16px', 'height': '28px', 'padding': '0 10px',
        'cursor': 'pointer', 'marginLeft': '6px'
    },
    # --- Details layout ---
    'details_left_panel': {
        'width': '50%' ###60%
    },
    'details_right_panel': {
        'width': '50%', 'position': 'relative', 'display': 'flex', 'flexDirection': 'column'
    },
    'details_body': {
        'marginTop': '20px', 'paddingTop': '16px', 'paddingLeft': '20px', 'paddingRight': '20px'
    },
    'panel_wrapper': {
        'marginTop': '50px', 'backgroundColor': '#FFFFFF', 'border': '1px solid transparent',
        'borderRadius': '12px', 'padding': '10px',
        'flex': '1 1 auto', 'minHeight': '0', 'position': 'relative', 'display': 'none'
    },
    # --- Export row ---
    'export_row': {
        'display': 'flex', 'flexWrap': 'wrap', 'marginTop': '8px'
    },
    # --- Generic rows/wrappers ---
    'row_header': {
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '8px'
    },
    'row_wrap_gap': {
        'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap'
    },
    'column': {
        'display': 'flex', 'flexDirection': 'column'
    },
    # --- Generic inputs ---
    'input_fullflex': {
        'width': '100%', 'flex': '1'
    },
    # Small icon button variant
    'arrow_button_small': {
        'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'borderRadius': '50%',
        'width': '24px', 'height': '24px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'cursor': 'pointer'
    },
    # --- Right panel action bar (pills container) ---
    'right_panel_actions': {
        'position': 'absolute', 'top': '0px', 'right': '10px', 'display': 'flex'
    },
    # --- Hidden content area inside details panel (absolute fill) ---
    'details_content_base': {
        'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
        'display': 'none', 'overflowY': 'auto', 'boxSizing': 'border-box'
    },
    # Inner container inside each details window (content padding + font)
    'details_content_inner': {
        'padding': '4px',
        'fontFamily': "Segoe UI, Roboto, Arial, sans-serif",
        'fontSize': '12px'
    },
    # Centered spinner container for details inner content
    'details_spinner_center': {
        'height': '100%',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center'
    },
    # --- Text helpers ---
    'muted_text': {
        'color': '#555'
    },
    'summary_right': {
        'marginTop': '6px', 'textAlign': 'right'
    },
    'link_break_all': {
        'wordBreak': 'break-all'
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

/* Favorites row hover: show delete button */
.fav-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.fav-item-row:hover .delete-btn { opacity: 1; }
.fav-item-row .delete-btn:hover { background-color: #FDEDEC; }

/* Bigger sort arrows in DataTable header and orange color */
.dash-table-container .dash-spreadsheet-container th .column-header--sort { margin-left: 6px; }
.dash-table-container .dash-spreadsheet-container th .column-header--sort .column-header--sort-icon { font-size: 18px; color: #FF5722; }
.dash-table-container .dash-spreadsheet-container th .column-header--sort:after { font-size: 18px; color: #FF5722; }

#gvg-center-spinner { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 10; display: flex; flex-direction: column; align-items: center; width: 260px; }
"""

# Classe aplicada em dcc.Markdown(children=..., className='markdown-summary')
MARKDOWN_CSS = (
    "/** Títulos menores para o resumo em Markdown **/\n"
    ".markdown-summary h1 { font-size: 16px; line-height: 1.25; }\n"
    ".markdown-summary h2 { font-size: 14px; line-height: 1.25; }\n"
    ".markdown-summary h3 { font-size: 13px; line-height: 1.25; }\n"
    ".markdown-summary h4 { font-size: 12px; line-height: 1.25; }\n"
    ".markdown-summary h5 { font-size: 11px; line-height: 1.25; }\n"
    ".markdown-summary h6 { font-size: 10px; line-height: 1.25; }\n"
)

CSS_ALL = BASE_CSS + "\n" + MARKDOWN_CSS

__all__ = ["styles", "BASE_CSS", "MARKDOWN_CSS", "CSS_ALL"]
