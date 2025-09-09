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
    'width': '100%',  ### controle de largura via wrapper/CSS var
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
    'width': '100%', ### controle de largura via wrapper/CSS var
        'backgroundColor': '#E0EAF9',
        'padding': '10px',
        'margin': '5px',
        'borderRadius': '15px',
        'overflowY': 'auto',
    'height': 'calc(100vh - 100px)',
    'position': 'relative'
    },
    # --- Tabs (abas) ---
    'tabs_bar': {
    'display': 'flex', 'gap': '6px', 'alignItems': 'center', 'padding': '4px',
        'backgroundColor': 'white', 'borderRadius': '16px', 'marginBottom': '8px',
    'overflowX': 'auto', 'whiteSpace': 'nowrap', 'flexWrap': 'nowrap'
    },
    'tab_button_base': {
    'display': 'inline-flex', 'alignItems': 'center', 'gap': '6px',
    'borderRadius': '16px', 'borderTopRightRadius': '18px', 'borderBottomRightRadius': '18px',
    'padding': '2px 2px 2px 8px', 'cursor': 'pointer',
    'border': '2px solid #D0D7E2', 'backgroundColor': 'white', 'color': '#003A70',
    'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap',
    'fontSize': '11px', 'flex': '0 0 auto'
    },
    'tab_button_active': {
    'borderColor': '#003A70',
    'backgroundColor': '#003A70', 'color': 'white', 'fontWeight': '600'
    },
    'tab_button_query': {
    'borderColor': '#003A70', 'color': '#003A70', 'backgroundColor': "#E4E6F8"
    },
    'tab_button_pncp': {
    'borderColor': '#2E7D32', 'color': '#2E7D32', 'backgroundColor': "#DDF5DF"
    },
    'tab_close_btn': {
    'width': '14px', 'height': '14px', 'minWidth': '14px',
    'borderRadius': '50%', 'border': '1px solid #888888', 'backgroundColor': 'white',
    'color': '#888888', 'cursor': 'pointer',
    'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
    'lineHeight': '0', 'padding': '2px', 'fontSize': '10px',
    'boxSizing': 'border-box', 'marginRight': '0px', 'marginLeft': '4px',
    'transform': 'translateY(0.5px)'
    },
    'tabs_content': {
        'backgroundColor': 'transparent'
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
    'arrow_button_inverted': {
        'backgroundColor': 'white',
        'color': '#FF5722',
        'border': '2px solid #FF5722',
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
    # Container do spinner central dentro do conteúdo da aba de consulta
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
    # --- Auth overlay ---
    'auth_overlay': {
        'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
        'backgroundColor': 'rgba(224,234,249,0.95)', 'zIndex': 2000,
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'padding': '20px'
    },
    'auth_card': {
        'backgroundColor': 'white', 'borderRadius': '18px', 'padding': '20px',
        'width': '100%', 'maxWidth': '470px', 'boxShadow': '0 4px 16px rgba(0,0,0,0.12)'
    },
    'auth_logo': { 'height': '48px', 'marginBottom': '10px' },
    'auth_title': { 'color': '#003A70', 'fontWeight': 'bold', 'fontSize': '18px', 'marginTop': '4px' },
    'auth_subtitle': { 'color': '#003A70', 'fontSize': '12px', 'marginTop': '6px' },
    'auth_input': { 'width': '100%', 'height': '36px', 'borderRadius': '16px', 'border': '1px solid #D0D7E2', 'padding': '6px 10px', 'fontSize': '12px' },
    'auth_input_group': { 'display': 'flex', 'alignItems': 'center', 'gap': '6px' },
    'auth_input_eye': { 'width': '100%', 'height': '36px', 'borderRadius': '16px', 'border': '1px solid #D0D7E2', 'padding': '6px 10px', 'fontSize': '12px', 'flex': '1' },
    'auth_eye_button': { 'backgroundColor': 'white', 'color': '#003A70', 'border': '1px solid #D0D7E2', 'borderRadius': '16px', 'height': '32px', 'minWidth': '36px', 'padding': '0 10px', 'cursor': 'pointer' },
    'auth_btn_primary': { 'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'borderRadius': '16px', 'height': '32px', 'padding': '0 14px', 'cursor': 'pointer' },
    'auth_btn_secondary': { 'backgroundColor': 'white', 'color': '#FF5722', 'border': '1px solid #FF5722', 'borderRadius': '16px', 'height': '32px', 'padding': '0 14px', 'cursor': 'pointer' },
    'auth_actions': { 'display': 'flex', 'gap': '8px', 'marginTop': '16px' },
    'auth_actions_center': { 'display': 'flex', 'gap': '8px', 'marginTop': '16px', 'justifyContent': 'center' },
    'auth_row_between': { 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '6px' },
    'auth_link': { 'color': '#FF5722', 'textDecoration': 'underline', 'cursor': 'pointer', 'backgroundColor': 'transparent', 'border': 'none', 'padding': '0', 'height': 'auto', 'fontSize': '11px' },
    'auth_error': { 'color': '#D32F2F', 'fontSize': '12px', 'marginTop': '6px' },
}

# Tag de status de data de encerramento
styles['date_status_tag'] = {
    'display': 'inline-block', 'padding': '2px 6px', 'borderRadius': '12px',
    'fontSize': '10px', 'fontWeight': '600', 'color': 'white', 'lineHeight': '1',
    'marginLeft': '6px', 'textTransform': 'none'
}

# Estilos específicos para favoritos (rótulo em negrito, local em itálico)
styles['fav_label'] = {
    'fontWeight': 'bold'
}
styles['fav_local'] = {
    'fontStyle': 'italic'
}
styles['fav_orgao'] = {
    'fontSize': '11px'
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

# --- Boletins ---
styles['boletim_panel'] = {
    'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '15px',
    'display': 'flex', 'flexDirection': 'column', 'gap': '8px'
}
styles['boletim_item_row'] = {
    'display': 'flex', 'gap': '8px', 'alignItems': 'flex-start', 'marginBottom': '6px'
}
styles['boletim_item_button'] = {
    'backgroundColor': 'white', 'color': '#003A70', 'border': '1px solid #D0D7E2',
    'borderRadius': '16px', 'display': 'block', 'width': '100%', 'textAlign': 'left',
    'padding': '8px 12px', 'whiteSpace': 'normal', 'wordBreak': 'break-word',
    'lineHeight': '1.25', 'cursor': 'default'
}
styles['boletim_delete_btn'] = {
    'width': '28px', 'height': '28px', 'minWidth': '28px', 'borderRadius': '50%',
    'border': '1px solid #FF5722', 'backgroundColor': 'white', 'color': '#FF5722', 'cursor': 'pointer'
}
styles['boletim_toggle_btn'] = {
    'backgroundColor': '#FF5722', 'color': 'white', 'border': 'none', 'borderRadius': '50%',
    'width': '32px', 'height': '32px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'cursor': 'pointer'
}
styles['boletim_config_panel'] = {
    'paddingTop': '10px', 'paddingBottom': '10px', 'paddingLeft': '0px', 'paddingRight': '0px',
    'backgroundColor': 'white', 'borderRadius': '15px', 'marginTop': '8px', 'width': '100%'
}
styles['boletim_section_header'] = {
    'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '8px'
}
styles['boletim_inline_group'] = {
    'display': 'flex', 'gap': '6px', 'flexWrap': 'wrap', 'alignItems': 'center'
}

# Utilitário: esconder elemento mantendo no DOM
styles['hidden'] = {
    'display': 'none'
}

# Linha do input do query + coluna de botões
styles['input_row'] = {
    'display': 'flex', 'alignItems': 'center', 'width': '100%'
}

# Tabela do input de consulta: célula de texto flexível e coluna de botões mínima
styles['query_table'] = {
    'width': '100%'
}
styles['query_text_cell'] = {
    'width': '100%', 'verticalAlign': 'top', 'paddingRight': '6px'
}
styles['query_buttons_cell'] = {
    'width': '36px', 'minWidth': '36px', 'verticalAlign': 'top', 'paddingLeft': '4px', 'textAlign': 'center', 'whiteSpace': 'nowrap'
}
styles['query_textbox'] = {
    'width': '100%', 'border': '1px solid #D0D7E2', 'borderRadius': '16px', 'padding': '4px', 'boxSizing': 'border-box', 'backgroundColor': 'white'
}

# Texto da query (negrito) e bloco de configurações (itálico) nos itens de boletim
styles['boletim_query'] = {
    'fontWeight': 'bold', 'color': '#003A70'
}
styles['boletim_config'] = {
    'fontStyle': 'italic', 'color': '#003A70', 'marginTop': '2px'
}


# CSS base (antes inline no app.index_string do GSB)
BASE_CSS = """
/* Larguras padrão (desktop) controladas por variáveis CSS */
:root { --gvg-left-slide-width: 30%; --gvg-right-slide-width: 70%; }

/* Wrappers dos painéis (desktop: respeita 30/70; mobile: vira slider) */
#gvg-main-panels > .gvg-slide { display: flex; }
#gvg-main-panels > .gvg-slide:first-child { width: var(--gvg-left-slide-width); }
#gvg-main-panels > .gvg-slide:last-child { width: var(--gvg-right-slide-width); }
#gvg-main-panels > .gvg-slide > div { width: 100%; }

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
.gvg-controls .gvg-form-label { width: 110px; min-width: 110px; font-size: 12px; color: #003A70; margin: 0; font-weight: 600; }
.gvg-controls .gvg-form-row > *:last-child { flex: 1; }

/* History row hover: show delete button */
.history-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.history-item-row:hover .delete-btn { opacity: 1; }
.history-item-row .delete-btn:hover { background-color: #FDEDEC; }

/* Favorites row hover: show delete button */
.fav-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.fav-item-row:hover .delete-btn { opacity: 1; }
.fav-item-row .delete-btn:hover { background-color: #FDEDEC; }

/* Boletins row hover: show action buttons (trash + edit) */
.boletim-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.boletim-item-row:hover .delete-btn { opacity: 1; }
.boletim-item-row .delete-btn:hover { background-color: #FDEDEC; }
.boletim-item-row .edit-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.boletim-item-row:hover .edit-btn { opacity: 1; }
.boletim-item-row .edit-btn:hover { background-color: #FDEDEC; }

/* DataTable sort icons to the RIGHT of the header label, with spacing */
.dash-table-container .dash-spreadsheet-container th { position: relative; padding-right: 22px; }
.dash-table-container .dash-spreadsheet-container th .column-header--sort {
    position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
    margin-left: 0; /* no left margin when absolutely positioned */
}
.dash-table-container .dash-spreadsheet-container th .column-header--sort .column-header--sort-icon {
    font-size: 22px; color: #FF5722;
}
.dash-table-container .dash-spreadsheet-container th .column-header--sort:after {
    font-size: 22px; color: #FF5722;
}

#gvg-center-spinner { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 10; display: flex; flex-direction: column; align-items: center; width: 260px; }

/* MODO MOBILE (≤ 992px): slider horizontal com scroll-snap, zero-JS */
@media (max-width: 992px) {
    :root { --gvg-left-slide-width: 100vw; --gvg-right-slide-width: 100vw; }
    #gvg-main-panels { overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; }
    #gvg-main-panels > .gvg-slide { flex: 0 0 100vw; scroll-snap-align: start; }
}
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
