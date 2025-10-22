"""
CSS utilitário e estilos para o GSB (Dash).

Este módulo concentra:
- O dicionário `styles` usado nos componentes (antes no GSB)
- CSS base para controles, tabelas, etc. (BASE_CSS)
- CSS específico para Markdown do resumo (MARKDOWN_CSS)
"""

# Cores base
_COLOR_PRIMARY = '#FF5722'  # Laranja GovGo
_COLOR_SECONDARY = '#003A70'  # Azul escuro GovGo
_COLOR_BACKGROUND = '#E0EAF9'  # Fundo claro GovGo
_COLOR_BACKGROUND_ALT = '#2E7D32'  # Fundo branco GovGo
_COLOR_GRAY = '#888888'  # Cinza neutro
_COLOR_ERROR = "#FF0000"  # Vermelho de erro


# Cores dos planos de assinatura
_COLOR_PLAN_FREE = '#6C757D'      
_COLOR_PLAN_PLUS = '#7B3FE4'      
_COLOR_PLAN_PRO = "#04c4ff"    
_COLOR_PLAN_CORP = '#089800'    


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
        'backgroundColor': _COLOR_BACKGROUND,
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
        'backgroundColor': _COLOR_BACKGROUND,
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
    'padding': '4px 2px 4px 8px', 'cursor': 'pointer',
    'border': '2px solid #D0D7E2', 'backgroundColor': 'white', 'color': _COLOR_SECONDARY,
    'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap',
    'fontSize': '12px', 'flex': '0 0 auto'
    },
    'tab_button_active': {
    'borderColor': _COLOR_SECONDARY,
    'backgroundColor': _COLOR_SECONDARY, 'color': 'white', 'fontWeight': '600'
    },
    'tab_button_query': {
    'borderColor': _COLOR_SECONDARY, 'color': _COLOR_SECONDARY, 'backgroundColor': "#E4E6F8"
    },
    'tab_button_pncp': {
    'borderColor': _COLOR_BACKGROUND_ALT, 'color': _COLOR_BACKGROUND_ALT, 'backgroundColor': "#DDF5DF"
    },
    'tab_close_btn': {
    'width': '20px', 'height': '20px', 'minWidth': '20px',
    'borderRadius': '50%', 'border': '2px solid #888888', 'backgroundColor': 'white',
    'color': _COLOR_GRAY, 'cursor': 'pointer',
    'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
    'lineHeight': '0', 'padding': '0px', 'fontSize': '12px',
    'boxSizing': 'border-box', 'marginRight': '2px', 'marginLeft': '6px',
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
        'backgroundColor': _COLOR_PRIMARY,
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'height': '36px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer'
    },
    # Variante específica para os botões de exportação (fonte menor)
    'export_button': {
        'backgroundColor': _COLOR_PRIMARY,
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'height': '25px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'cursor': 'pointer',
        'fontSize': '12px'
    },
    'input_container': {
        'padding': '10px',
        'backgroundColor': 'white',
        'borderRadius': '25px',
        'display': 'flex',
        'alignItems': 'center',
        'marginTop': '0px',
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
        'backgroundColor': _COLOR_PRIMARY,
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
        'color': _COLOR_PRIMARY,
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
    'fontSize': '24px', 'marginLeft': '15px', 'color': _COLOR_SECONDARY, 'fontWeight': 'bold', 'marginTop': '2px', 'marginBottom': '2px'
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
    # Botão "Mensagem" (inverso do laranja)
    'header_message_btn': {
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY, 'border': '1px solid #FF5722',
        'borderRadius': '16px', 'height': '32px', 'padding': '0 12px', 'marginRight': '10px',
        'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center', 'gap': '6px'
    },
    'header_user_badge': {
        'width': '32px', 'height': '32px', 'minWidth': '32px',
        'borderRadius': '50%', 'backgroundColor': _COLOR_PRIMARY,
        'color': 'white', 'fontWeight': 'bold', 'fontSize': '14px',
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'cursor': 'pointer'
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
        'backgroundColor': _COLOR_PRIMARY,
        'borderRadius': '999px',
        'transition': 'width 250ms ease'
    },
    'progress_label': {
        'marginTop': '6px', 'textAlign': 'center', 'color': _COLOR_PRIMARY, 'fontSize': '12px'
    },
    # Container do spinner central dentro do conteúdo da aba de consulta
    'center_spinner': {
        'display': 'none'
    },
    # --- History ---
    'history_item_button': {
        'backgroundColor': 'white',
        'color': _COLOR_SECONDARY,
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
    'history_prompt': {
        'fontWeight': 'bold', 'color': _COLOR_SECONDARY
    },
    'history_config': {
        'fontSize': '10px', 'color': _COLOR_SECONDARY, 'marginTop': '2px'
    },
    # Coluna vertical de ações (ex.: lixeira em cima e replay embaixo)
    'history_actions_col': {
        'display': 'flex', 'flexDirection': 'column', 'gap': '4px', 'alignItems': 'center'
    },
    'history_delete_btn': {
        'width': '28px', 'height': '28px', 'minWidth': '28px',
        'borderRadius': '50%', 'border': '1px solid #FF5722',
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
        'cursor': 'pointer'
    },
    # Botão de replay com o mesmo formato/dimensão da lixeira
    'history_replay_btn': {
        'width': '28px', 'height': '28px', 'minWidth': '28px',
        'borderRadius': '50%', 'border': '1px solid #FF5722',
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
        'cursor': 'pointer'
    },
    'history_email_btn': {
    'width': '28px', 'height': '28px', 'minWidth': '28px',
    'borderRadius': '50%', 'border': '1px solid #FF5722',
    'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
    'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
    'padding': '0'
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
        'color': _COLOR_SECONDARY,
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
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
        'cursor': 'pointer'
    },
    'fav_actions_col': {
        'display': 'flex', 'flexDirection': 'column', 'gap': '6px',
        'alignItems': 'center', 'justifyContent': 'flex-start',
        'minWidth': '28px'
    },
    'fav_email_btn': {
        'width': '28px', 'height': '28px', 'minWidth': '28px',
        'borderRadius': '50%', 'border': '1px solid #FF5722',
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
        'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'textDecoration': 'none'
    },
    'bookmark_btn': {
        'position': 'absolute', 'top': '10px', 'left': '40px',
        'width': '24px', 'height': '24px', 'minWidth': '24px',
        'border': 'none', 'backgroundColor': 'transparent', 'cursor': 'pointer',
        'color': _COLOR_PRIMARY
    },
    # --- Buttons (pills) for details right panel ---
    'btn_pill': {
        'backgroundColor': _COLOR_PRIMARY, 'color': 'white', 'border': 'none',
        'borderRadius': '16px', 'height': '28px', 'padding': '0 10px',
        'cursor': 'pointer', 'marginLeft': '6px'
    },
    'btn_pill_inverted': {
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY, 'border': '1px solid #FF5722',
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
    'marginTop': '35px', 'backgroundColor': '#FFFFFF', 'border': f'2px solid {_COLOR_PRIMARY}',
        'borderRadius': '25px', 'padding': '10px',
    'flex': '1 1 auto', 'position': 'relative', 'display': 'none'
    },
    # --- Export row ---
    'export_row': {
        'display': 'flex', 'flexWrap': 'wrap', 'marginTop': '8px'
    },
    # --- Generic rows/wrappers ---
    'row_header': {
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '8px'
    },
    # Clickable full-width header button for collapsible sections
    'section_header_button': {
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between',
        'width': '100%', 'backgroundColor': 'transparent', 'border': 'none', 'padding': '0',
        'cursor': 'pointer', 'textAlign': 'left', 'color': _COLOR_SECONDARY
    },
    'section_header_left': {
        'display': 'flex', 'alignItems': 'center', 'gap': '8px'
    },
    'section_icon': {
        'color': _COLOR_SECONDARY
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
        'backgroundColor': _COLOR_PRIMARY, 'color': 'white', 'border': 'none', 'borderRadius': '50%',
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
        'padding': '10px',
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
    'auth_title': { 'color': _COLOR_SECONDARY, 'fontWeight': 'bold', 'fontSize': '18px', 'marginTop': '4px' },
    'auth_subtitle': { 'color': _COLOR_SECONDARY, 'fontSize': '12px', 'marginTop': '6px' },
    'auth_input': { 'width': '100%', 'height': '36px', 'borderRadius': '16px', 'border': '1px solid #D0D7E2', 'padding': '6px 10px', 'fontSize': '12px' },
    'auth_input_group': { 'display': 'flex', 'alignItems': 'center', 'gap': '6px' },
    'auth_input_eye': { 'width': '100%', 'height': '36px', 'borderRadius': '16px', 'border': '1px solid #D0D7E2', 'padding': '6px 10px', 'fontSize': '12px', 'flex': '1' },
    'auth_eye_button': { 'backgroundColor': 'white', 'color': _COLOR_SECONDARY, 'border': '1px solid #D0D7E2', 'borderRadius': '16px', 'height': '32px', 'minWidth': '36px', 'padding': '0 10px', 'cursor': 'pointer' },
    'auth_btn_primary': { 'backgroundColor': _COLOR_PRIMARY, 'color': 'white', 'border': 'none', 'borderRadius': '16px', 'height': '32px', 'padding': '0 14px', 'cursor': 'pointer' },
    'auth_btn_secondary': { 'backgroundColor': 'white', 'color': _COLOR_PRIMARY, 'border': '1px solid #FF5722', 'borderRadius': '16px', 'height': '32px', 'padding': '0 14px', 'cursor': 'pointer' },
    'auth_actions': { 'display': 'flex', 'gap': '8px', 'marginTop': '16px' },
    'auth_actions_center': { 'display': 'flex', 'gap': '8px', 'marginTop': '16px', 'justifyContent': 'center' },
    'auth_row_between': { 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginTop': '6px' },
    'auth_link': { 'color': _COLOR_PRIMARY, 'textDecoration': 'underline', 'cursor': 'pointer', 'backgroundColor': 'transparent', 'border': 'none', 'padding': '0', 'height': 'auto', 'fontSize': '11px' },
    'auth_error': { 'color': _COLOR_ERROR, 'fontSize': '12px', 'marginTop': '6px' },
    # --- Planos (modal) ---
    'planos_card': {
        'backgroundColor': 'white', 'border': '1px solid #D0D7E2', 'borderRadius': '14px',
        'padding': '14px', 'flex': '1', 'minWidth': '0', 'display': 'flex', 'flexDirection': 'column', 'gap': '6px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.08)'
    },
    'planos_card_current': {
        'backgroundColor': '#F1F6FC', 'border': '2px solid #003A70', 'borderRadius': '14px',
        'padding': '14px', 'flex': '1', 'minWidth': '0', 'display': 'flex', 'flexDirection': 'column', 'gap': '6px',
        'boxShadow': '0 2px 6px rgba(0,58,112,0.15)'
    },
    'planos_table': {
        'width': '100%', 'fontSize': '12px', 'borderCollapse': 'collapse', 'marginTop': '12px'
    },
    'planos_table_th': {
        'textAlign': 'left', 'padding': '6px 8px', 'backgroundColor': _COLOR_SECONDARY, 'color': 'white', 'fontWeight': '600', 'fontSize': '11px'
    },
    'planos_table_td': {
        'textAlign': 'left', 'padding': '6px 8px', 'borderBottom': '1px solid #E0EAF9', 'fontSize': '11px'
    },
    'planos_limits_list': {
        'display': 'flex', 'flexDirection': 'column', 'gap': '4px', 'marginTop': '2px'
    },
    'planos_limit_item': {
        'fontSize': '13px', 'color': '#222', 'fontStyle': 'italic'
    },
    'planos_limit_row': {
        'display': 'flex', 'alignItems': 'center', 'gap': '6px'
    },
    'planos_limit_icon': {
        'width': '16px', 'height': '16px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'color': _COLOR_SECONDARY, 'fontSize': '13px'
    },
    'planos_desc': {
        'fontSize': '13px', 'fontWeight': '600', 'color': '#444', 'marginTop': '-2px'
    },
    'planos_price': {
        'fontSize': '14px', 'fontWeight': '600', 'color': _COLOR_PRIMARY, 'marginTop': '6px'
    },
    'planos_btn_current': {
        'backgroundColor': '#ECEFF3', 'color': _COLOR_SECONDARY, 'border': '1px solid #CAD4E0', 'borderRadius': '18px',
        'height': '32px', 'width': '100%', 'cursor': 'default', 'fontSize': '13px', 'fontWeight': '600'
    },
    'planos_btn_upgrade': {
        'backgroundColor': 'white', 'color': _COLOR_PRIMARY, 'border': '1px solid #FF5722', 'borderRadius': '18px',
        'height': '32px', 'width': '100%', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': '600'
    },
}

# --- User menu (avatar popover) ---
styles['user_menu'] = {
    'display': 'flex', 'flexDirection': 'column', 'gap': '4px',
    'minWidth': '220px', 'fontSize': '12px'
}
styles['user_menu_user'] = {
    'display': 'flex', 'flexDirection': 'column', 'gap': '2px',
    'color': _COLOR_SECONDARY
}
styles['user_menu_name'] = {
    'fontWeight': '700', 'fontSize': '14px', 'color': _COLOR_SECONDARY
}
styles['user_menu_email'] = {
    'fontStyle': 'italic', 'fontWeight': '700', 'fontSize': '12px', 'color': _COLOR_PRIMARY
}
styles['user_menu_sep'] = {
    'margin': '4px 0', 'border': 'none', 'borderTop': '1px solid #E0EAF9'
}
styles['user_menu_item'] = {
    'padding': '4px 8px', 'borderRadius': '10px', 'cursor': 'pointer',
    'color': _COLOR_SECONDARY, 'backgroundColor': 'transparent', 'display': 'flex', 'alignItems': 'center', 'gap': '8px',
    'fontSize': '14px'
}
styles['user_menu_icon'] = {
    'fontSize': '14px', 'color': _COLOR_SECONDARY, 'minWidth': '16px', 'textAlign': 'center'
}

# --- Mensagem (popover) ---
styles['message_menu'] = {
    'display': 'flex', 'flexDirection': 'column', 'gap': '8px',
    'minWidth': '260px'
}
# Wrapper para garantir padding lateral simétrico dentro do popover
styles['message_wrap'] = {
    # Apenas padding à direita no wrapper externo do textarea (sem padding esquerdo)
    'padding': '0 12px 0 0'
}
styles['message_textarea'] = {
    'width': '100%', 'minHeight': '120px', 'resize': 'vertical',
    'border': '1px solid #D0D7E2', 'borderRadius': '12px', 'padding': '8px 12px', 'boxSizing': 'border-box',
    'fontSize': '12px', 'fontFamily': "Segoe UI, Roboto, Arial, sans-serif"
}

# Botão enviar dentro do popover de mensagem (padding simétrico)
styles['message_send_btn'] = {
    'backgroundColor': _COLOR_PRIMARY, 'color': 'white', 'border': 'none',
    'borderRadius': '20px', 'padding': '8px 14px', 'cursor': 'pointer',
    'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px'
}
# Barra de ações com padding lateral simétrico
styles['message_actions'] = {
    'display': 'flex', 'justifyContent': 'flex-end', 'padding': '0 12px'
}

# === Bases comuns para botões de listas (Histórico/Favoritos/Boletins) ===
# Botão de item de lista (padrão compacto)
styles['btn_list_item'] = {
    'backgroundColor': 'white', 'color': _COLOR_SECONDARY, 'border': '1px solid #D0D7E2',
    'borderRadius': '16px', 'display': 'block', 'width': '100%', 'textAlign': 'left',
    'padding': '6px 10px', 'whiteSpace': 'normal', 'wordBreak': 'break-word',
    'lineHeight': '1.25', 'cursor': 'pointer', 'fontSize': '12px'
}
# Botão de ação pequeno (ícones: lixeira, replay, e-mail)
styles['btn_icon_sm'] = {
    'width': '24px', 'height': '24px', 'minWidth': '24px', 'borderRadius': '50%',
    'border': '1px solid #FF5722', 'backgroundColor': 'white', 'color': _COLOR_PRIMARY,
    'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
    'fontSize': '12px', 'lineHeight': '1'
}
# Linha compacta de itens de lista
styles['list_row_compact'] = {
    'display': 'flex', 'gap': '6px', 'alignItems': 'flex-start', 'marginBottom': '4px'
}
# Coluna de ações compacta
styles['list_actions_col'] = {
    'display': 'flex', 'flexDirection': 'column', 'gap': '4px', 'alignItems': 'center',
    'justifyContent': 'flex-start', 'minWidth': '24px'
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
    'backgroundColor': _COLOR_PRIMARY,
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
    'color': _COLOR_SECONDARY,
    'paddingRight': '8px',
    'paddingBottom': '8px',
}

# Badge de numeração compatível com e-mail (sem position/flex)
styles['result_number_email'] = {
    'display': 'inline-block',
    'width': '24px',
    'height': '24px',
    'lineHeight': '24px',
    'textAlign': 'center',
    'backgroundColor': _COLOR_PRIMARY,
    'color': 'white',
    'borderRadius': '50%',
    'fontSize': '12px',
    'fontWeight': 'bold',
    'marginBottom': '6px'
}

# === Billing / Planos ===
# Badges de plano (cores definidas no documento de billing)
styles['plan_badge_free'] = {
    'backgroundColor': _COLOR_PLAN_FREE, 'color': 'white', 'borderRadius': '16px',
    'padding': '2px 10px', 'fontSize': '12px', 'fontWeight': '600', 'display': 'inline-flex',
    'alignItems': 'center', 'justifyContent': 'center', 'height': '24px', 'lineHeight': '1'
}
styles['plan_badge_plus'] = {
    'backgroundColor': _COLOR_PLAN_PLUS, 'color': 'white', 'borderRadius': '16px',
    'padding': '2px 10px', 'fontSize': '12px', 'fontWeight': '600', 'display': 'inline-flex',
    'alignItems': 'center', 'justifyContent': 'center', 'height': '24px', 'lineHeight': '1'
}
styles['plan_badge_pro'] = {
    'backgroundColor': _COLOR_PLAN_PRO, 'color': 'white', 'borderRadius': '16px',
    'padding': '2px 10px', 'fontSize': '12px', 'fontWeight': '600', 'display': 'inline-flex',
    'alignItems': 'center', 'justifyContent': 'center', 'height': '24px', 'lineHeight': '1'
}
styles['plan_badge_corp'] = {
    'backgroundColor': _COLOR_PLAN_CORP, 'color': 'white', 'borderRadius': '16px',
    'padding': '2px 10px', 'fontSize': '12px', 'fontWeight': '600', 'display': 'inline-flex',
    'alignItems': 'center', 'justifyContent': 'center', 'height': '24px', 'lineHeight': '1'
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
    'backgroundColor': 'white', 'color': _COLOR_SECONDARY, 'border': '1px solid #D0D7E2',
    'borderRadius': '16px', 'display': 'block', 'width': '100%', 'textAlign': 'left',
    'padding': '8px 12px', 'whiteSpace': 'normal', 'wordBreak': 'break-word',
    'lineHeight': '1.25', 'cursor': 'default'
}
styles['boletim_delete_btn'] = {
    'width': '28px', 'height': '28px', 'minWidth': '28px', 'borderRadius': '50%',
    'border': '1px solid #FF5722', 'backgroundColor': 'white', 'color': _COLOR_PRIMARY, 'cursor': 'pointer'
}
styles['boletim_toggle_btn'] = {
    'backgroundColor': _COLOR_PRIMARY, 'color': 'white', 'border': 'none', 'borderRadius': '50%',
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
    'fontWeight': 'bold', 'color': _COLOR_SECONDARY
}
styles['boletim_config'] = {
    'fontStyle': 'italic', 'color': _COLOR_SECONDARY, 'marginTop': '2px'
}

# === Overrides focados apenas em botões e espaçamento vertical entre botões ===
# Histórico: reduzir apenas tamanho dos botões de ação e gap da coluna
styles['history_actions_col'] = { **styles['list_actions_col'], 'gap': '3px' }
styles['history_delete_btn'] = { **styles['btn_icon_sm'] }
styles['history_replay_btn'] = { **styles['btn_icon_sm'] }

# Favoritos: reduzir apenas tamanho dos botões de ação e gap da coluna
styles['fav_actions_col'] = { **styles['list_actions_col'] }
styles['fav_delete_btn'] = { **styles['btn_icon_sm'] }
styles['fav_email_btn'] = { **styles['btn_icon_sm'], 'textDecoration': 'none' }

# Boletins: reduzir apenas tamanho dos botões de ação
styles['boletim_delete_btn'] = { **styles['btn_icon_sm'] }

# === Notificações Toast ===
# Container fixo de notificações (canto inferior direito desktop; centro inferior mobile)
styles['toast_container'] = {
    'position': 'fixed',
    'bottom': '20px',
    'right': '20px',
    'zIndex': 9999,
    'display': 'flex',
    'flexDirection': 'column',
    'gap': '10px',
    'maxWidth': '350px',
    'pointerEvents': 'none',  # não bloquear cliques abaixo
}

# Toast individual
styles['toast_item'] = {
    'backgroundColor': '#f8f9fa',  # cinza claro
    'border': '3px solid',  # cor dinâmica por tipo
    'borderRadius': '12px',
    'padding': '12px 16px',
    'display': 'flex',
    'alignItems': 'center',
    'gap': '10px',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
    'pointerEvents': 'auto',
    'minWidth': '280px',
    'maxWidth': '350px',
    'animation': 'slideInRight 0.3s ease-out',
}

# Ícone da notificação
styles['toast_icon'] = {
    'fontSize': '20px',
    'minWidth': '20px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
}

# Texto da notificação
styles['toast_text'] = {
    'flex': '1',
    'fontSize': '13px',
    'color': '#222',
    'lineHeight': '1.4',
    'wordBreak': 'break-word',
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

/* Header title font-size enforcement (desktop and general) */
.gvg-header-title { font-size: 24px !important; }

/* Compact controls inside left panel config card */
.gvg-controls .Select-control { min-height: 32px; height: 32px; border-radius: 16px; font-size: 12px; border: 1px solid #D0D7E2; box-shadow: none; }
.gvg-controls .is-focused .Select-control, .gvg-controls .Select.is-focused > .Select-control { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); }
.gvg-controls .is-open .Select-control { border-color: #52ACFF; }
.gvg-controls .Select-value-label,
.gvg-controls .Select-option,
.gvg-controls .VirtualizedSelectOption,
.gvg-controls .Select-placeholder { font-size: 12px; }
.gvg-controls .Select-menu-outer { font-size: 12px; border-radius: 12px; }
.gvg-controls input[type="number"] { height: 32px; border-radius: 16px; font-size: 12px; padding: 6px 10px; border: 1px solid #D0D7E2; outline: none; box-shadow: none; box-sizing: border-box; background-color: white; }
.gvg-controls input[type="number"]:focus { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); outline: none; }
/* Text-like inputs should match number inputs exactly */
.gvg-controls input[type="text"],
.gvg-controls input[type="email"],
.gvg-controls input[type="password"],
.gvg-controls input[type="search"],
.gvg-controls textarea,
.gvg-controls .dash-input { height: 32px; border-radius: 16px; font-size: 12px; padding: 6px 10px; border: 1px solid #D0D7E2; outline: none; box-shadow: none; box-sizing: border-box; background-color: white; }
.gvg-controls input[type="text"]:focus,
.gvg-controls input[type="email"]:focus,
.gvg-controls input[type="password"]:focus,
.gvg-controls input[type="search"]:focus,
.gvg-controls textarea:focus,
.gvg-controls .dash-input:focus { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); outline: none; }
/* Date range now uses two text inputs side-by-side; nothing special to style beyond default inputs */


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

/* Favorites row hover: show action buttons (delete + email) */
.fav-item-row .delete-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.fav-item-row:hover .delete-btn { opacity: 1; }
.fav-item-row .delete-btn:hover { background-color: #FDEDEC; }
.fav-item-row .email-btn { opacity: 0; transition: opacity 0.15s ease-in-out; }
.fav-item-row:hover .email-btn { opacity: 1; }
.fav-item-row .email-btn:hover { background-color: #ECF2FF; }

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

/* Espaçamento padrão entre botões (ações) e a janela tripla */
.gvg-panel-wrapper { margin-top: 50px; }

/* MODO MOBILE (≤ 992px): slider horizontal com scroll-snap, zero-JS */
@media (max-width: 992px) {
    :root { --gvg-left-slide-width: 100vw; --gvg-right-slide-width: 100vw; }
    #gvg-main-panels { overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; }
    #gvg-main-panels > .gvg-slide { flex: 0 0 100vw; scroll-snap-align: start; }
    .gvg-header-title { display: none;}
    /* Detalhes acima, janelas (Itens/Docs/Resumo) abaixo */
    .gvg-details-row { flex-direction: column !important; gap: 8px !important; }
    .gvg-details-row > div { width: 100% !important; }
    /* Botões de ação no painel direito: alinhar ao topo à esquerda em mobile, sem margem extra */
    .gvg-details-row .gvg-right-actions { position: static !important; margin-bottom: 0; }

    /* Altura mínima das janelas (Itens/Docs/Resumo) quando abertas, para caber ~10 linhas */
    .gvg-panel-wrapper { min-height: 360px !important; }
}

/* ===== Email modal styles ===== */
#email-modal .modal-content { border-radius: 16px; }
#email-modal .modal-dialog { border-radius: 16px; }
#email-modal-input {
    height: 32px; border-radius: 16px; font-size: 12px; padding: 6px 10px;
    border: 1px solid #D0D7E2; outline: none; box-shadow: none; box-sizing: border-box; background-color: white;
}
#email-modal-input:focus { border-color: #52ACFF; box-shadow: 0 0 0 2px rgba(82,172,255,0.12); outline: none; }

/* ===== Planos modal responsive ===== */
.planos-cards-wrapper { width: 100%; }
@media (max-width: 768px) {
    .planos-cards-wrapper { flex-wrap: nowrap; flex-direction: column; gap: 16px !important; max-height: 70vh; overflow-y: auto; }
    .planos-cards-wrapper > div { width: 100% !important; }
}
/* Centraliza o modal e define largura de 90vw */
#planos-modal .modal-dialog {
    max-width: 90vw;
    width: 90vw;
    margin-left: auto;
    margin-right: auto;
}
@media (max-width: 576px) {
    #planos-modal .modal-dialog { max-width: 95vw !important; width: 95vw !important; }
}

/* ===== Notificações Toast ===== */
/* Animação de entrada (desliza da direita) */
@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(100%);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* Animação de saída (desvanece) */
@keyframes fadeOut {
    from {
        opacity: 1;
    }
    to {
        opacity: 0;
    }
}

/* Container de notificações: desktop (canto inferior direito) */
#toast-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 350px;
    pointer-events: none;
}

/* Mobile: centro inferior */
@media (max-width: 992px) {
    #toast-container {
        left: 50%;
        right: auto;
        transform: translateX(-50%);
        bottom: 60px;
        max-width: 90vw;
        align-items: center;
    }
}

/* Toast individual com animação de saída */
.toast-item-exiting {
    animation: fadeOut 0.3s ease-out forwards;
}

/* ===== Avatar Popover (user-menu-popover) ===== */
/* O elemento com id=user-menu-popover é o próprio .popover; use seletor direto e !important para vencer o Bootstrap */
#user-menu-popover,
#user-menu-popover.popover {
    border: 2px solid #FF5722 !important;
    border-radius: 25px !important;
    box-shadow: none !important;
}
#user-menu-popover .popover-arrow,
#user-menu-popover .arrow { display: none !important; }
#user-menu-popover .popover-body { padding: 10px; }

/* ===== Message Popover (message-popover) - Mesmo estilo do avatar ===== */
#message-popover,
#message-popover.popover {
    border: 2px solid #FF5722 !important;
    border-radius: 25px !important;
    box-shadow: none !important;
}
#message-popover .popover-arrow,
#message-popover .arrow { display: none !important; }
#message-popover .popover-body { padding: 10px; }
#message-popover textarea:focus {
    border-color: #003A70 !important; /* _COLOR_SECONDARY */
    box-shadow: none !important;
    outline: none !important;
}

/* ===== Query input focus highlight (igual ao textarea da mensagem) ===== */
#query-textarea-wrap:focus-within {
    border-color: #003A70 !important; /* _COLOR_SECONDARY */
    box-shadow: none !important;
    outline: none !important;
}
"""

# Classe aplicada em dcc.Markdown(children=..., className='markdown-summary')
MARKDOWN_CSS = (
    "/** Layout do resumo em Markdown **/\n"
    ".markdown-summary { padding: 10px 12px; }\n"
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
