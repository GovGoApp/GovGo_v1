# GSB — Funcionalidades (Hierarquia completa, v2)

Documento hierárquico e explicativo por função, alinhado ao consolidado. Inclui referências de linha do `GvG_Search_Browser.py` ("linha xxxx") e os módulos usados pelos callbacks principais.

## 1) Layout e Divs principais
- Header/topo: título, botões utilitários, overlay de autenticação (fora do escopo desse trecho).
- Painel de configuração e entrada:
  - query-input (textarea), submit-button (seta), config-collapse + config-toggle-btn, history-collapse + history-toggle-btn.
  - status-bar, categories-table, export-panel, results-table (DataTable), results-details (cards).
  - tabs-bar (barra de abas com rolagem horizontal).
- Painéis por cartão de resultado:
  - panel-wrapper (por PNCP), com 3 janelas sobrepostas: itens-card, docs-card, resumo-card.
  - Botões por cartão: itens-btn, docs-btn, resumo-btn, bookmark-btn.

## 2) Stores (estado)
- processing-state: bool do processamento ativo.
- progress-interval/progress-store: clock e dados da barra de progresso.
- store-result-sessions/store-active-session/store-session-event/store-current-query-token: controle de abas/sessões e token de rodada.
- store-results/store-results-sorted/store-meta/store-categories/store-last-query: stores “legadas” espelhadas da sessão ativa.
- store-sort: estado da ordenação atual.
- store-panel-active: mapa pncp -> 'itens'|'docs'|'resumo'.
- store-cache-itens/store-cache-docs/store-cache-resumo: caches por PNCP.
- store-history: lista de prompts.
- store-favorites: array de favoritos (com os campos exibidos no card/lista).
- store-config-open/store-history-open/store-favorites-open: collapses.

## 3) Entrada/Processamento/Progresso
- set_processing_state (linha 4937) — Inputs: submit-button.n_clicks; States: query-input.value, processing-state.data, store-search-filters. Outputs: processing-state, store-session-event(pending), store-current-query-token. Usa: helpers {_has_any_filter}.
- run_search (linha 3978) — Input: processing-state=true; States: query/config/sort/limites/toggles/token/filters/notifications. Output: store-session-event(completed), processing-state=false, notifications. Usa: gvg_search_core, gvg_preprocessing.SearchQueryProcessor, gvg_user.{add_prompt,save_user_results,get_current_user,get_prompt_preproc_output}, gvg_limits.ensure_capacity, gvg_usage.{usage_event_*}, gvg_notifications.add_note, helpers {progress_*, _build_sql_conditions_from_ui_filters, _sanitize_limit, _sort_results, _make_query_signature}.
- Progresso — progress-interval/update_progress_store (linha 4849) / reflect_progress_bar (linha 4870): barra + spinner; ativos enquanto processing-state=true.
- clear_results_content_on_start (linha 4901) / hide_result_panels_during_processing (linha 4918): limpa/oculta conteúdo durante execução.

## 4) Sessões, Abas e Sincronização
- create_or_update_session (linha 4383) — Input: store-session-event. Outputs: store-result-sessions, store-active-session. Dedup por assinatura; suporta 'query'/'pncp'/'history'; limite 100 abas.
- render_tabs_bar (linha 4474): desenha cada aba; PNCP usa cor pela data de encerramento via _enc_status_and_color.
- on_tab_click (linha 4629): ativa/fecha abas; mantém ativo consistente.
- toggle_tabs_bar_style (linha 4613): oculta barra se não houver sessões.
- sync_active_session (linha 4679): espelha sessão ativa nas stores legadas (results/results-sorted/meta/categories/last_query).

## 5) Renderização de resultados
- render_status_and_categories (linha 5437): usa helpers de formatação e estilos.
- compute_sorted_results (linha 5834) / init_sort_from_meta (linha 5847) / on_header_sort (linha 5867): estado de ordenação para DataTable (sort_action='custom').
- render_results_table (linha 5595): DataTable “results-dt” com destaque de coluna ordenada e cores por status.
- render_details (linha 5674): cards com painel direito (Itens/Documentos/Resumo) e favorito.
- toggle_results_visibility (linha 6558): mostra/esconde cards conforme tipo de sessão ativa (query/pncp/history).

## 6) Painéis por PNCP (Itens/Docs/Resumo)
- set_active_panel (linha 6454): toggle por PNCP; limpa seleção quando clica novamente.
- update_button_icons (linha 6501): chevron up/down conforme ativo.
- toggle_panel_wrapper (linha 6525): exibe contêiner quando há painel ativo.
- load_itens_for_cards (linha 5903): busca itens (fetch_itens_contratacao), monta DataTable e resumo; cache em store-cache-itens. Usa: gvg_search_core, helpers {_format_money,_format_qty}.
- load_docs_for_cards (linha 6012): carrega documentos (fetch_documentos), DataTable com links; cache em store-cache-docs. Usa: gvg_database.
- show_resumo_spinner_when_active (linha 6401): mostra spinner imediato; exibe markdown do cache quando existir.
- load_resumo_for_cards (linha 6107): escolhe doc principal (heurística), processa (summarize_document/process_pncp_document), persiste cache e BD por usuário. Usa: gvg_documents, gvg_database, gvg_limits/gvg_usage, gvg_notifications.

## 7) Histórico
- init_history (linha 5218) / load_history: popula store-history.
- render_history_list (linha 5228): mostra prompt e configurações gravadas.
- update_history_on_search (linha 6595): adiciona consulta ao topo com dedupe e persistência (save_history).
- run_from_history (linha 6621): preenche o campo de consulta (não dispara automaticamente).
- delete_history_item (linha 6653): remove do array e do BD; notifica (gvg_notifications).
- replay_from_history (linha 6699): emite evento de sessão 'history' com resultados persistidos (fetch_user_results_for_prompt_text).

## 8) Favoritos
- init_favorites (linha 7136) / load_favorites_on_results (linha 7201): carrega do BD (JOIN com contratacao) e ordena por data de encerramento.
- render_favorites_list (linha 7256): aplica filtro de expirados (opcional) e formata cada item; lixeira clicável.
- toggle_bookmark (linha 7650): alterna favorito a partir do card; atualização otimista com os mesmos campos exibidos no card; persiste no BD apenas (user_id, numero_controle_pncp).
- sync_bookmark_icons (linha 7824): sincroniza ícones dos cards ao mudar a store-favorites.
- delete_favorite (linha 7896): remove pela lixeira da lista; atualiza store-favorites.
- open_pncp_tab_from_favorite (linha 4706): abre aba PNCP para o item clicado; reusa sessão se a assinatura existir.

## 9) Exportações
- export_files: gera JSON/XLSX/CSV/PDF/HTML em `Resultados_Busca`; baixa o arquivo com dcc.send_file.

## 10) Regras e comportamentos relevantes
- Ordenação: meta.order → store-sort (similaridade desc | data asc | valor desc); DataTable controla sort custom.
- Sessões: assinatura evita duplicidade; histórico reordena abas ao reabrir; PNCP mostra apenas painel de detalhes.
- Datas: TEXT no BD; formatação e status de encerramento via helpers (_format_br_date, _enc_status_and_color, _enc_status_text).
- Estilos: usar `gvg_styles.py` para classes/cores/botões; evitar CSS inline custom além de pequenos ajustes contextuais.
- Desempenho: caches por PNCP; spinner imediato no Resumo; highlight de descrição desativado por performance.
