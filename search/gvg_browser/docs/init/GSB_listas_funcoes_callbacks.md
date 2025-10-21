# GSB — Listas, Funções e Callbacks (consolidado)

Este documento unifica as referências:
- Lista extensiva de listas do GSB (UI, Stores, opções/constantes, dados externos, listas internas, heurísticas, entradas ALL)
- Lista completa de funções e callbacks (Rotas Flask, Callbacks Dash, Helpers)

Fonte: `GvG_Search_Browser.py` e módulos auxiliares em `search/gvg_browser/*`.

---

## Parte 1 — Listas do GSB

(Conteúdo a seguir replicado de `lista_funcoes_gsb.md`.)

# Lista extensiva de listas do GSB

Este documento consolida todas as “listas” do GovGo Search Browser (GSB) observadas no arquivo principal `GvG_Search_Browser.py` e módulos de apoio. Organizado por tipo: UI, Stores, opções/constantes, dados externos (BD/API), listas internas de callbacks e coleções de regras/heurísticas.

## 1) Listas de UI (componentes renderizados)
- Abas de resultados
  - Lista de abas em `tabs-bar` (tipos: query, history, boletim, pncp), cada uma com botão fechar.
- Categorias (Top categorias)
  - DataTable em `categories-table` com linhas de categorias ranqueadas.
- Resultados (resumo)
  - DataTable `results-dt` em `results-table-inner` com linhas por resultado (Rank, Órgão, Município, UF, Similaridade, Valor, Data Encerramento).
- Cards de detalhes
  - Lista de cards em `results-details`, um por resultado, cada um com:
    - Painel esquerdo: linhas de atributos (órgão, unidade, ID, local, valor, modalidade, modo, datas, link, descrição).
    - Painel direito: wrapper com três painéis sobrepostos (Itens/Documentos/Resumo).
- Itens (por PNCP)
  - DataTable dentro de `itens-card` (linhas: Nº, Descrição, Qtde, Unit, Total) + resumo de totalização.
- Documentos (por PNCP)
  - DataTable dentro de `docs-card` com links markdown (Nº, Documento).
- Resumo (por PNCP)
  - Markdown dentro de `resumo-card` (texto resumido, cacheado quando disponível).
- Histórico de consultas
  - Lista em `history-list`: para cada item, 3 linhas (prompt, configs, filtros) + ações (apagar, reabrir, e‑mail).
- Favoritos
  - Lista em `favorites-list`: botão principal por item (rótulo/local/órgão/data), mais ações (lixeira, e‑mail).
- Notificações (toasts)
  - Lista em `toast-container`, cada toast com ícone, cor e texto.

## 2) Stores que contêm listas (ou coleções list‑like)
- Resultados e categorias
  - `store-results`: lista de dicts de resultados.
  - `store-results-sorted`: lista ordenada para UI.
  - `store-categories`: lista de categorias.
- Sessões/abas
  - `store-result-sessions`: dict de sessões; cada sessão possui listas: `results` e `categories`.
- Histórico e favoritos
  - `store-history`: lista de strings (consultas recentes).
  - `store-favorites`: lista de objetos de favorito (campos exibidos no card/lista conforme regras do projeto).
- Caches por PNCP
  - `store-cache-itens`: dict { pncp -> lista de itens }.
  - `store-cache-docs`: dict { pncp -> lista de documentos }.
  - `store-cache-resumo`: dict { pncp -> { docs: lista, summary: str } }.
- Notificações
  - `store-notifications`: lista de notificações ativas (id, tipo, texto, timestamp).
- Planos/limites
  - `store-planos-data`: contém `plans` (lista de planos) e `usage` (estrutura de consumo).
- E-mail (fila)
  - `store-email-send-request`: quando ativo, inclui `recipients` (lista de e‑mails).

## 3) Listas de opções/constantes de UI
- Seletores/enums
  - `SEARCH_TYPES`, `SEARCH_APPROACHES`, `RELEVANCE_LEVELS`, `SORT_MODES` (coleções usadas como opções de UI).
- Combos de filtragem
  - `MODALIDADE_OPTIONS` (lista de modalidades).
  - `MODO_OPTIONS` (lista de modos de disputa).
  - Campo de data (encerramento/abertura/publicação) — conjunto de valores aceitos pelo componente.
- Toggles
  - `toggles` (lista contendo “filter_expired” quando ativo).
- Exportações
  - Tipos suportados: JSON, Excel, CSV, PDF, HTML (mapeados a botões e lógica de exportação).

## 4) Listas vindas de BD/API (dados externos)
- Favoritos do usuário
  - `fetch_bookmarks(limit)`: lista de favoritos (JOIN com contratacao).
- Histórico rico
  - `fetch_prompts_with_config(limit)`: lista de prompts com configurações/filtros.
- Resultados por prompt
  - `fetch_user_results_for_prompt_text(prompt, limit)`: lista de resultados salvos.
- Itens e documentos por PNCP
  - `fetch_itens_contratacao(pncp, limit)`: lista de itens do processo.
  - `fetch_documentos(pncp)`: lista de documentos do processo.
- Planos do sistema
  - `get_system_plans()`: lista de planos (com fallback local quando BD indisponível).
- Boletins (replay)
  - Consultas em `user_schedule`/`user_boletim` resultam em listas de resultados para a aba BOLETIM.

## 5) Listas internas usadas por callbacks
- PNCPs por renderização
  - `pncp_ids`: lista alinhada à ordem de resultados para sincronizar componentes (itens/docs/resumo/painéis/botões/ícones).
- Tabelas
  - `rows` (itens): linhas do DataTable de itens.
  - `rows` (documentos): linhas do DataTable de documentos (markdown com links).
- Histórico (UI)
  - `buttons`: lista de linhas/botões para `history-list`.
- Favoritos (UI)
  - `items`: lista de linhas para `favorites-list`.
- Notificações
  - `toasts`: lista transformada para renderização.
  - `updated_notifs`: acumulador de toasts durante as ações/callbacks.
- Ordenação do DataTable
  - `sort_by`: lista com o critério ativo de ordenação `[{column_id, direction}]`.
- E-mail
  - `recips`: lista de destinatários parseada do input.
- Abas
  - `out`: lista de elementos (componentes) da barra de abas.
  - Reordenação de `sessions` (dict preserva ordem de inserção) para mover aba ao fim no replay do histórico.
- Ações multi‑componentes
  - `n_clicks_list`: listas para detectar índices clicados (itens/docs/resumo/history/favorites/tabs/bookmark).

## 6) Listas/coleções de regras e heurísticas
- Documento principal (Resumo)
  - Lista de regex para priorização: edital; termo de referência/TR; projeto básico; anexo I; pregão/pe/concorrência/dispensa; fallback para primeiro PDF; senão primeiro documento.
- Cores/status de encerramento
  - Conjunto de estados (na, expired, lt3, lt7, lt15, lt30, gt30) usados em estilo condicional do DataTable.

## 7) Callbacks com padrão ALL (entradas/saídas em lista)
- Entradas com `ALL` (geram listas):
  - `{'type': 'itens-btn','pncp': ALL}.n_clicks`
  - `{'type': 'docs-btn','pncp': ALL}.n_clicks`
  - `{'type': 'resumo-btn','pncp': ALL}.n_clicks`
  - `{'type': 'favorite-item','index': ALL}.n_clicks`
  - `{'type': 'favorite-delete','index': ALL}.n_clicks`
  - `{'type': 'favorite-email','index': ALL}.n_clicks`
  - `{'type': 'history-item','index': ALL}.n_clicks`
  - `{'type': 'history-delete','index': ALL}.n_clicks`
  - `{'type': 'history-replay','index': ALL}.n_clicks`
  - `{'type': 'history-email','index': ALL}.n_clicks`
  - `{'type': 'boletim-replay','id': ALL}.n_clicks`
  - `{'type': 'boletim-email','id': ALL}.n_clicks`
  - `{'type': 'tab-activate','sid': ALL}.n_clicks`
  - `{'type': 'tab-close','sid': ALL}.n_clicks`
  - `{'type': 'bookmark-btn','pncp': ALL}.n_clicks` (e Outputs `children` como lista de ícones por PNCP).

---
Observação: onde aplicável, os formatos/colunas das listas podem ser conferidos diretamente no `GvG_Search_Browser.py` (montagem de linhas/objetos) e nos módulos auxiliares (`gvg_search_core.py`, `gvg_documents.py`, `gvg_user.py`, `gvg_exporters.py`).

---

## Parte 2 — Funções e Callbacks

(Conteúdo a seguir replicado de `lista_funcoes_callbacks.md`.)

# Lista completa de funções e callbacks do GSB

Escopo: `search/gvg_browser/GvG_Search_Browser.py`. Agrupado por: Rotas (Flask), Callbacks (Dash) e Helpers (internos). Para os callbacks centrais, incluí explicitamente os IDs de Outputs/Inputs/States conforme os decorators.

Observação: esta é uma documentação de referência rápida; para detalhes de lógica, consultar o próprio arquivo.

## 1) Rotas Flask (funções `def`)
- stripe_webhook — Webhook Stripe (linha 271) | Usa: gvg_billing.verify_webhook, gvg_billing.handle_webhook_event, gvg_debug.dbg
- webhook_health — Health check de billing (linha 309) | Usa: Flask jsonify
- debug_ping — Ping de debug (linha 316) | Usa: gvg_debug.dbg
- debug_info — Informações de debug (linha 326) | Usa: gvg_debug.dbg, os.getenv
- api_plan_status — Status do plano do usuário (linha 356) | Usa: gvg_billing.get_user_settings, gvg_billing.get_usage_snapshot, gvg_debug.dbg
- api_create_subscription — Criação de assinatura (linha 382) | Usa: gvg_billing.create_subscription_elements
- api_apply_subscription — Aplicar assinatura (linha 402) | Usa: gvg_billing.apply_scheduled_plan_changes
- api_create_checkout_embedded — Criar sessão do Embedded Checkout (linha 425) | Usa: gvg_billing.create_checkout_embedded_session

## 2) Callbacks Dash (funções `def`)
A seguir, os callbacks agrupados por domínio, com propósito. Na subseção 2.4 há um anexo com I/O detalhado (Outputs/Inputs/States) para os callbacks centrais.

### 2.1 Billing/Planos
- open_close_elements_modal — abrir/fechar modal do Embedded Checkout (linha 1337) | Usa: gvg_debug.dbg
- handle_embedded_result — processa resultado do checkout embutido (linha 1422) | Usa: gvg_debug.dbg
- reflect_header_badge — atualiza badge do plano no header (linha 1440) | Usa: gvg_user.get_user_initials (lógica inline para iniciais)
- toggle_planos_modal — abre/fecha modal Planos (linha 1470) | Usa: dash.callback_context
- load_planos_content — renderiza conteúdo do modal (planos/uso) (linha 1485) | Usa: gvg_styles.styles, _render_usage_bars, store-planos-data
- handle_plan_action — dispara upgrade/downgrade/cancel (linha 1601) | Usa: gvg_billing.create_checkout_embedded_session/get_system_plans/upgrade_plan, gvg_debug.dbg, gvg_limits.get_usage_status
- capture_payment_success — captura sucesso a partir da URL (linha 1788) | Usa: gvg_billing.get_user_settings/get_usage_snapshot, gvg_debug.dbg
- refresh_plan_after_payment — recarrega plano após pagamento (linha 1830) | Usa: gvg_styles.styles, atualiza stores; possui clientside callbacks auxiliares

### 2.2 Boletins
- enable_boletim_button — habilita botão de criação (linha 2226)
- sync_boletim_controls — sincroniza controles (frequência/config) (linha 2240)
- toggle_boletim_panel — abre/fecha painel de boletins (linha 2255)
- validate_boletim — valida entrada de boletim (linha 2269)
- refresh_boletim_save_visuals — atualiza ícones/estados de "salvar" (linha 2298)
- save_boletim — persiste/atualiza boletim (linha 2353) | Usa: gvg_boletim.{create_user_boletim,deactivate_user_boletim,fetch_user_boletins}, gvg_database.db_fetch_all, gvg_notifications.add_note
- load_boletins_on_auth — carrega boletins após login (linha 2455) | Usa: gvg_boletim.fetch_user_boletins
- delete_boletim — exclui boletim (linha 2486) | Usa: gvg_boletim.deactivate_user_boletim, gvg_notifications.add_note
- render_boletins_list — lista boletins com ações (linha 2535) | Usa: styles, helpers
- toggle_boletins_collapse — abre/fecha seção (linha 2734)
- update_boletins_icon — ícone up/down da seção (linha 2744)
- replay_from_boletim — reabre última execução do boletim em nova aba (linha 6757) | Usa: gvg_database.db_fetch_all, gvg_schema.get_contratacao_core_columns/normalize_contratacao_row/project_result_for_output, helpers {_augment_aliases}

### 2.3 Autenticação/Inicialização
- on_auth_changed — prepara estado inicial após login (linha 2780) | Usa: gvg_user.set_current_user, gvg_styles, inicializa stores
- perform_initial_load — execução de carga inicial (linha 2847) | Usa: stores iniciais
- toggle_auth_overlay — mostra/esconde overlay (linha 2869)
- reflect_auth_view — controla a view (login/signup/otp/reset) (linha 2893)
- switch_auth_view — troca de telas (linha 2929)
- do_login — login (linha 2957) | Usa: gvg_auth.sign_in, gvg_user.set_access_token, gvg_notifications.add_note
- do_signup — cadastro (linha 3027) | Usa: gvg_auth.sign_up_with_metadata, gvg_notifications.add_note
- do_confirm — confirmação OTP (linha 3089) | Usa: gvg_auth.verify_otp, gvg_notifications.add_note
- do_forgot — iniciar reset de senha (linha 3135) | Usa: gvg_auth.reset_password, gvg_notifications.add_note
- do_resend_otp — reenviar OTP (linha 3156) | Usa: gvg_auth.resend_otp, gvg_notifications.add_note
- handle_stripe_return — tratar retorno Stripe (linha 3180) | Usa: URL parsing para post-pagamento
- detect_recovery_in_url — detectar hash de recuperação (linha 3240) | Usa: gvg_auth.recover_session_from_code
- confirm_password_reset — confirmar reset (linha 3318) | Usa: gvg_auth.update_user_password, gvg_notifications.add_note
- cancel_password_reset — cancelar reset (linha 3361)
- do_logout — logout (linha 3373) | Usa: gvg_auth.sign_out, gvg_notifications.add_note
- toggle_login_password_eye — alternar visibilidade senha (login) (linha 3404)
- toggle_signup_password_eye — alternar visibilidade senha (signup) (linha 3422)
- toggle_reset_password_eye1 — alternar visibilidade senha (reset-1) (linha 3440)
- toggle_reset_password_eye2 — alternar visibilidade senha (reset-2) (linha 3457)
- prefill_login_fields — preencher campos (remember-me) (linha 3474)

### 2.4 Busca/Sessões/Resultados
- run_search — executa busca, persiste histórico/uso e emite evento de sessão (linha 3978) | Usa: gvg_search_core.{semantic_search,keyword_search,hybrid_search,correspondence_search,category_filtered_search,get_top_categories_for_query}; gvg_ai_utils.{get_embedding}; gvg_search_core.get_negation_embedding; gvg_user.{add_prompt,save_user_results,get_current_user,get_prompt_preproc_output}; gvg_preprocessing.SearchQueryProcessor; gvg_limits.ensure_capacity; gvg_usage.{usage_event_start,usage_event_finish,usage_event_set_ref,record_usage}; gvg_notifications.add_note; gvg_schema.{project_result_for_output}; helpers {_build_sql_conditions_from_ui_filters,_sanitize_limit,_sort_results,_make_query_signature,progress_*}
- create_or_update_session — cria/atualiza sessão/aba por evento (linha 4383) | Usa: time, dict ops (sem módulos externos)
- render_tabs_bar — renderiza barra de abas (linha 4474) | Usa: gvg_styles.styles, helpers {_enc_status_and_color}
- toggle_tabs_bar_style — oculta barra quando vazio (linha 4613) | Usa: gvg_styles.styles
- on_tab_click — ativa/fecha abas (linha 4629) | Usa: dash.callback_context
- sync_active_session — reflete sessão ativa em stores legadas (linha 4679) | Usa: projeção simples de stores (sem módulos externos)
- open_pncp_tab_from_favorite — abre aba PNCP a partir de favorito (linha 4706) | Usa: cria sessão tipo 'pncp' a partir do favorito (sem módulos externos)
- update_submit_button — spinner/habilitação do botão enviar (linha 4806) | Usa: validações locais
- toggle_center_spinner — spinner central no painel direito (linha 4827)
- toggle_progress_interval — liga/desliga Interval de progresso (linha 4838)
- update_progress_store — atualiza `progress-store` (linha 4849)
- reflect_progress_bar — aplica estilo da barra/label (linha 4870)
- clear_results_content_on_start — limpa resultados ao iniciar processamento (linha 4901)
- hide_result_panels_during_processing — oculta cartões/tabelas durante processamento (linha 4918)
- set_processing_state — define `processing-state` e evento pendente (linha 4937) | Usa: helpers {_has_any_filter}
- toggle_config — abre/fecha Configurações (linha 4979)
- reflect_collapse — reflete colapso de Configurações (linha 4989)
- update_config_icon — ícone de Configurações (linha 4997)
- toggle_filters — abre/fecha Filtros Avançados (linha 5015)
- update_filters_icon — ícone de Filtros Avançados (linha 5025)
- sync_filters_store — consolida filtros da UI → store (linha 5051) | Usa: parsing de datas; sem módulos externos
- ensure_end_after_start — garante fim >= início (visual) (linha 5123)
- init_history — inicializa store de histórico (disco) (linha 5218) | Usa: load_history
- render_history_list — renderiza lista de histórico (linha 5228)
- render_status_and_categories — status da busca + DataTable de categorias (linha 5437) | Usa: helpers de formatação e estilos
- render_results_table — DataTable de resultados (linha 5595) | Usa: dash_table, formatação, styles
- render_details — cards com detalhes (linha 5674) | Usa: helpers {_build_pncp_data,_format_*,_highlight_terms}; gvg_styles.styles
- compute_sorted_results — mantém `store-results-sorted` (linha 5834) | Usa: _sorted_for_ui
- init_sort_from_meta — ordenação default pós-busca (linha 5847)
- on_header_sort — ordenação a partir do header do DataTable (linha 5867)
- load_itens_for_cards — carrega (e cacheia) Itens (linha 5903) | Usa: gvg_search_core.fetch_itens_contratacao; gvg_styles.styles; helpers {_format_money,_format_qty}
- load_docs_for_cards — carrega (e cacheia) Documentos (linha 6012) | Usa: gvg_database.fetch_documentos; helpers de markdown/link
- load_resumo_for_cards — gera/mostra (e cacheia) Resumo (linha 6107) | Usa: gvg_documents.{summarize_document,process_pncp_document}; gvg_database.{get_user_resumo,upsert_user_resumo}; gvg_limits.get_usage_status; gvg_usage.record_usage; gvg_notifications.add_note
- show_resumo_spinner_when_active — exibe spinner imediato ao ativar painel (linha 6401)
- set_active_panel — alterna painel ativo (itens/docs/resumo) (linha 6454)
- update_button_icons — ícones up/down nos botões de painel (linha 6501)
- toggle_panel_wrapper — mostra/esconde wrapper do painel direito (linha 6525)
- toggle_results_visibility — controla visibilidade (especial PNCP/history) (linha 6558)

### 2.5 Histórico/Favoritos/Export/E-mail/Toasts
- update_history_on_search — adiciona consulta ao histórico (linha 6595) | Usa: save_history
- run_from_history — reabre prompt no campo (linha 6621) | Usa: save_history
- delete_history_item — remove item do histórico (linha 6653) | Usa: gvg_user.delete_prompt, save_history, gvg_notifications.add_note
- replay_from_history — reabre resultados do histórico (linha 6699) | Usa: gvg_user.fetch_user_results_for_prompt_text, gvg_notifications.add_note
- init_favorites — inicializa favoritos (linha 7136) | Usa: gvg_user.fetch_bookmarks
- load_planos_data_on_init — carrega planos/uso (linha 7151) | Usa: gvg_billing.get_system_plans, gvg_billing.get_user_settings, gvg_limits.get_usage_status
- load_favorites_on_results — recarrega favoritos após busca (linha 7201) | Usa: gvg_user.fetch_bookmarks, gvg_debug.dbg
- toggle_favorites — abre/fecha favoritos (linha 7222)
- reflect_favorites_collapse — colapso favoritos (linha 7232)
- update_favorites_icon — ícone favoritos (linha 7240)
- render_favorites_list — lista favoritos com ações (linha 7256) | Usa: helpers {_format_br_date,_enc_status_*}, gvg_styles.styles
- open_email_modal — abre modal de e‑mail (boletim/favorito/histórico) (linha 7347) | Usa: gvg_usage.record_usage, gvg_debug.dbg
- reflect_email_modal — reflete título/abertura do modal (linha 7396)
- queue_email_send — enfileira envio (parse recipients) (linha 7444) | Usa: _parse_recipients
- process_email_send — envia e‑mails e notifica (linha 7468) | Usa: gvg_database.db_fetch_all, gvg_email.{render_*_email_html,send_html_email}, gvg_notifications.add_note
- toggle_bookmark — alterna favorito no card (persistência mínima + otimista) (linha 7650) | Usa: gvg_user.{add_bookmark,remove_bookmark}, gvg_notifications.add_note
- sync_bookmark_icons — sincroniza ícones com store de favoritos (linha 7824)
- select_favorite — clique no favorito não altera query (linha 7867)
- delete_favorite — remove favorito (BD + UI) (linha 7896) | Usa: gvg_user.remove_bookmark, gvg_notifications.add_note
- export_files — exporta (JSON/XLSX/CSV/PDF/HTML) + download (linha 7961) | Usa: gvg_exporters.{export_results_json,export_results_excel,export_results_csv,export_results_pdf,export_results_html}
- render_notifications — renderiza toasts (linha 8032)
- auto_remove_notifications — auto-remove toasts (>3s) (linha 8065)

## 3) Helpers/Utils (funções `def` internas, não-callback)
- progress_set(percent, label) (linha 557)
- progress_reset() (linha 566)
- b64_image(image_path) (linha 570)
- _get_user_plan_code(user) (linha 585)
- _render_usage_bars(usage) (linha 1222)
- _build_sql_conditions_from_ui_filters(f) (linha 2012) | Usa: validações/SQL do projeto; sem chamadas externas
- _has_any_filter(f) (linha 2097)
- _sql_only_search(sql_conditions, limit, filter_expired) (linha 2110) | Usa: gvg_database.db_fetch_all, gvg_schema.{normalize_contratacao_row,project_result_for_output}
- _restrict_results_by_sql(sql_conditions, current_results, limit, filter_expired) (linha 2169) | Usa: gvg_database.db_fetch_all, gvg_schema
- _dedupe_boletins(items) (linha 2435)
- _to_float(value) (linha 3489)
- _sort_results(results, order_mode) (linha 3518)
- _extract_text(d, keys) (linha 3583)
- _sorted_for_ui(results, sort_state) (linha 3591)
- _highlight_terms(text, query) (linha 3662)
- _parse_date_generic(date_value) (linha 3741)
- _enc_status_and_color(date_value) (linha 3772)
- _enc_status_text(status, dt_value) (linha 3796)
- _build_pncp_data(details) (linha 3825)
- _format_br_date(date_value) (linha 3843)
- _format_qty(value) (linha 3857)
- _format_money(value) (linha 3867)
- _extract_pncp_id_from_result(r) (linha 3878)
- _make_query_signature(query, meta, results, max_ids) (linha 3887)
- _sanitize_limit(value, default, min_v, max_v) (linha 3920)
- load_history(max_items) (linha 3937)
- save_history(history, max_items) (linha 3947)
- _parse_recipients(raw) (linha 7409)

---

## Anexo A — I/O de callbacks centrais (Outputs/Inputs/States)

Abaixo, Inputs/Outputs/States mais relevantes (nomes exatos dos IDs conforme decorators):

- run_search
  - Outputs: `store-results` (no_update), `store-categories` (no_update), `store-meta` (no_update), `store-last-query` (no_update), `store-session-event` (evento), `processing-state` (False), `store-notifications`
  - Inputs: `processing-state`, `query-input`, `search-type`, `search-approach`, `relevance-level`, `sort-mode`, `max-results`, `top-categories`, `toggles`, `store-current-query-token`, `store-search-filters`, `store-notifications`
  - Observação: grava histórico/resultados, emite sessão, controla progresso e limites

- create_or_update_session
  - Outputs: `store-result-sessions`, `store-active-session`
  - Inputs: `store-session-event`
  - States: `store-result-sessions`, `store-active-session`

- sync_active_session
  - Outputs: `store-results`, `store-results-sorted`, `store-categories`, `store-meta`, `store-last-query`
  - Inputs: `store-active-session`
  - States: `store-result-sessions`

- render_tabs_bar
  - Outputs: `tabs-bar.children`
  - Inputs: `store-result-sessions`, `store-active-session`

- on_tab_click
  - Outputs: `store-active-session`, `store-result-sessions`
  - Inputs: `{type: 'tab-activate', sid: ALL}.n_clicks`, `{type: 'tab-close', sid: ALL}.n_clicks`
  - States: `store-active-session`, `store-result-sessions`

- set_processing_state
  - Outputs: `processing-state`, `store-session-event`, `store-current-query-token`
  - Inputs: `submit-button.n_clicks`
  - States: `query-input`, `processing-state`, `store-search-filters`

- clear_results_content_on_start
  - Outputs: `results-table-inner.children`, `results-details.children`, `status-bar.children`, `categories-table.children`, `store-panel-active.data`, `store-cache-itens.data`, `store-cache-docs.data`, `store-cache-resumo.data`
  - Inputs: `processing-state`

- hide_result_panels_during_processing
  - Outputs: `status-bar.style`, `categories-table.style`, `export-panel.style`, `results-table.style`, `results-details.style`
  - Inputs: `processing-state`

- render_status_and_categories
  - Outputs: `status-bar.children`, `categories-table.children`
  - Inputs: `store-meta`, `store-categories`
  - States: `store-last-query`, `store-search-filters`

- render_results_table
  - Outputs: `results-table-inner.children`
  - Inputs: `store-results-sorted`, `store-sort`

- render_details
  - Outputs: `results-details.children`
  - Inputs: `store-results-sorted`, `store-last-query`

- compute_sorted_results
  - Outputs: `store-results-sorted`
  - Inputs: `store-results`, `store-sort`

- init_sort_from_meta
  - Outputs: `store-sort`
  - Inputs: `store-meta`

- on_header_sort
  - Outputs: `store-sort`
  - Inputs: `results-dt.sort_by`
  - States: `store-sort`

- load_itens_for_cards
  - Outputs: `{type:'itens-card',pncp:ALL}.children`, `{type:'itens-card',pncp:ALL}.style`, `{type:'itens-btn',pncp:ALL}.style`, `store-cache-itens`
  - Inputs: `{type:'itens-btn',pncp:ALL}.n_clicks`, `store-panel-active`
  - States: `store-results-sorted`, `store-cache-itens`

- load_docs_for_cards
  - Outputs: `{type:'docs-card',pncp:ALL}.children`, `{type:'docs-card',pncp:ALL}.style`, `{type:'docs-btn',pncp:ALL}.style`, `store-cache-docs`
  - Inputs: `{type:'docs-btn',pncp:ALL}.n_clicks`, `store-panel-active`
  - States: `store-results-sorted`, `store-cache-docs`

- load_resumo_for_cards
  - Outputs: `{type:'resumo-card',pncp:ALL}.children`, `{type:'resumo-card',pncp:ALL}.style`, `{type:'resumo-btn',pncp:ALL}.style`, `store-cache-resumo`, `store-notifications`
  - Inputs: `{type:'resumo-btn',pncp:ALL}.n_clicks`, `store-panel-active`
  - States: `store-results-sorted`, `store-cache-resumo`, `store-notifications`

- show_resumo_spinner_when_active
  - Outputs: `{type:'resumo-card',pncp:ALL}.children`, `{type:'resumo-card',pncp:ALL}.style`, `{type:'resumo-btn',pncp:ALL}.style`
  - Inputs: `store-panel-active`
  - States: `store-results-sorted`, `store-cache-resumo`

- set_active_panel
  - Outputs: `store-panel-active`
  - Inputs: `{type:'itens-btn',pncp:ALL}.n_clicks`, `{type:'docs-btn',pncp:ALL}.n_clicks`, `{type:'resumo-btn',pncp:ALL}.n_clicks`
  - States: `store-results-sorted`, `store-panel-active`

- update_button_icons
  - Outputs: `{type:'itens-btn',pncp:ALL}.children`, `{type:'docs-btn',pncp:ALL}.children`, `{type:'resumo-btn',pncp:ALL}.children`
  - Inputs: `store-panel-active`
  - States: `store-results-sorted`

- toggle_panel_wrapper
  - Outputs: `{type:'panel-wrapper',pncp:ALL}.style`
  - Inputs: `store-panel-active`
  - States: `store-results-sorted`

- toggle_results_visibility
  - Outputs: `status-bar.style`, `categories-table.style`, `export-panel.style`, `results-table.style`, `results-details.style`
  - Inputs: `store-meta`, `store-results`, `store-categories`
  - States: `store-active-session`, `store-result-sessions`

- update_history_on_search
  - Outputs: `store-history`
  - Inputs: `store-meta`
  - States: `store-last-query`, `store-history`

- run_from_history
  - Outputs: `query-input.value`, `processing-state`, `store-history`
  - Inputs: `{type:'history-item',index:ALL}.n_clicks`
  - States: `store-history`

- delete_history_item
  - Outputs: `store-history`, `store-notifications`
  - Inputs: `{type:'history-delete',index:ALL}.n_clicks`
  - States: `store-history`, `store-notifications`

- replay_from_history
  - Outputs: `store-session-event`, `store-notifications`
  - Inputs: `{type:'history-replay',index:ALL}.n_clicks`
  - States: `store-history`, `store-notifications`

- init_favorites
  - Outputs: `store-favorites`
  - Inputs: `store-favorites`

- load_favorites_on_results
  - Outputs: `store-favorites`
  - Inputs: `store-meta`

- toggle_favorites / reflect_favorites_collapse / update_favorites_icon
  - Outputs: `store-favorites-open` / `favorites-collapse.is_open` / `favorites-toggle-btn.children`
  - Inputs: `favorites-toggle-btn.n_clicks` / `store-favorites-open` / `store-favorites-open`

- render_favorites_list
  - Outputs: `favorites-list.children`
  - Inputs: `store-favorites`, `toggles`

- open_email_modal / reflect_email_modal / queue_email_send / process_email_send
  - Outputs:
    - `store-email-modal-context`
    - `email-modal.is_open`, `email-modal-title.children`
    - `store-email-send-request`, `store-email-modal-context`, `email-modal-error.children`, `email-modal-error.style`
    - `store-email-send-request` (limpeza), `store-notifications`
  - Inputs:
    - `{type:'boletim-email',id:ALL}.n_clicks`, `{type:'favorite-email',index:ALL}.n_clicks`, `{type:'history-email',index:ALL}.n_clicks`
    - `store-email-modal-context`
    - `email-modal-send.n_clicks`, `email-modal-input.n_submit`
    - `store-email-send-request`
  - States: `store-favorites`, `store-history`, `store-email-modal-context`, `email-modal-input`, `email-modal-self`, `store-auth`, `store-notifications`

- toggle_bookmark / sync_bookmark_icons / select_favorite / delete_favorite
  - Outputs:
    - `{type:'bookmark-btn',pncp:ALL}.children`, `store-favorites`, `store-notifications`
    - `{type:'bookmark-btn',pncp:ALL}.children`
    - `query-input.value`
    - `store-favorites`, `store-notifications`
  - Inputs: `{type:'bookmark-btn',pncp:ALL}.n_clicks` / `store-favorites` / `{type:'favorite-item',index:ALL}.n_clicks` / `{type:'favorite-delete',index:ALL}.n_clicks`
  - States: `store-results-sorted`, `store-favorites`, `store-notifications`, `{type:'bookmark-btn',pncp:ALL}.n_clicks`

- export_files
  - Outputs: `download-out.data`, `store-notifications`
  - Inputs: `export-json.n_clicks`, `export-xlsx.n_clicks`, `export-csv.n_clicks`, `export-pdf.n_clicks`, `export-html.n_clicks`
  - States: `store-results`, `store-last-query`, `store-meta`, `store-notifications`

- render_notifications / auto_remove_notifications
  - Outputs: `toast-container.children` / `store-notifications`
  - Inputs: `store-notifications` / `notifications-interval.n_intervals`
  - States: `store-notifications`

---


