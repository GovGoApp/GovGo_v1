# GSB — Funcionalidades (Hierarquia completa)

Documento hierárquico e explicativo por função. Foco em callbacks, funcionalidades e divs. Campos/estilos refletem o código atual do GSB.

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
- set_processing_state (Inputs: submit-button.n_clicks; State: query-input.value, processing-state.data) → Outputs: processing-state, store-session-event(pending), store-current-query-token.
  - Cria token, emite evento pendente para abrir aba "CONSULTA: Processando".
- run_search (Input: processing-state=true; States: query/config/sort/limites/toggles/token) → Output: store-session-event(completed) e limpeza do processing-state.
  - Pré-processa (SearchQueryProcessor), busca (semantic/keyword/hybrid + correspondência/filtro por categoria), ordena, persiste histórico/resultados, monta assinatura e evento de sessão.
- progress-interval/update_progress_store/reflect_progress_bar: barra + spinner central; habilitados enquanto processing-state=true.
- clear_results_content_on_start/hide_result_panels_during_processing: limpa e oculta conteúdo durante a execução.

## 4) Sessões, Abas e Sincronização
- create_or_update_session (Input: store-session-event) → Outputs: store-result-sessions, store-active-session.
  - Dedup por assinatura; suporta tipos 'query', 'pncp', 'history'; limite 100 abas; placeholders pendentes.
- render_tabs_bar: desenha cada aba com ícone e estilo; PNCP usa cor pela data de encerramento.
- on_tab_click: ativa ou fecha abas; mantém ativo coerente.
- toggle_tabs_bar_style: oculta barra se não houver sessões.
- sync_active_session: espelha sessão ativa nas Stores legadas (results/results-sorted/meta/categories/last_query).

## 5) Renderização de resultados
- render_status_and_categories: a partir de store-meta e store-categories.
- compute_sorted_results/init_sort_from_meta/on_header_sort: estado de ordenação e DataTable custom (sort_action='custom').
- render_results_table: DataTable “results-dt” com destaques de coluna ordenada e cores por status de encerramento.
- render_details: cards detalhados com painel direito (Itens/Documentos/Resumo) e botão de favorito.
- toggle_results_visibility: mostra/esconde cards conforme tipo de sessão ativa (query/pncp/history).

## 6) Painéis por PNCP (Itens/Docs/Resumo)
- set_active_panel: toggle por PNCP; limpa seleção quando clica novamente.
- update_button_icons: chevron up/down conforme ativo.
- toggle_panel_wrapper: exibe contêiner quando há painel ativo.
- load_itens_for_cards: busca itens (fetch_itens_contratacao), monta DataTable e resumo total; cache em store-cache-itens.
- load_docs_for_cards: carrega documentos (fetch_documentos), DataTable com links; cache em store-cache-docs.
- show_resumo_spinner_when_active: mostra spinner imediato; se houver resumo em cache, exibe já o markdown.
- load_resumo_for_cards: escolhe documento principal (heurística), processa via summarize_document/process_pncp_document, persiste em cache e no BD por usuário (quando aplicável).

## 7) Histórico
- init_history/load_history: popula store-history na inicialização.
- render_history_list: mostra prompt e configurações gravadas (tipo/abordagem/relevância/ordem/limites/filtro); botões apagar e reabrir.
- update_history_on_search: adiciona consulta ao topo com dedupe local e persistência.
- run_from_history: preenche o campo de consulta (não dispara busca automática).
- delete_history_item: remove do array e do BD; persiste novo estado.
- replay_from_history: emite evento de sessão 'history' com resultados persistidos, abrindo aba HISTÓRICO.

## 8) Favoritos
- init_favorites/load_favorites_on_results: carrega do BD (JOIN com contratacao) e ordena por data de encerramento.
- render_favorites_list: aplica filtro de expirados (opcional) e formata cada item; lixeira clicável.
- toggle_bookmark: alterna favorito a partir do card; atualização otimista mantendo os mesmos campos exibidos no card; persiste no BD apenas (user_id, numero_controle_pncp[, rotulo]).
- sync_bookmark_icons: sincroniza ícones dos cards ao mudar a store-favorites.
- delete_favorite: remove pela lixeira da lista; atualiza store-favorites.
- open_pncp_tab_from_favorite: abre aba PNCP para o item clicado; reusa sessão se a assinatura existir.

## 9) Exportações
- export_files: gera JSON/XLSX/CSV/PDF/HTML em `Resultados_Busca`; baixa o arquivo com dcc.send_file.

## 10) Regras e comportamentos relevantes
- Ordenação: meta.order → store-sort (similaridade desc | data asc | valor desc); DataTable controla sort custom.
- Sessões: assinatura evita duplicidade; histórico reordena abas ao reabrir; PNCP mostra apenas painel de detalhes.
- Datas: TEXT no BD; formatação e status de encerramento via helpers (_format_br_date, _enc_status_and_color, _enc_status_text).
- Estilos: usar `gvg_styles.py` para classes/cores/botões; evitar CSS inline custom além de pequenos ajustes contextuais.
- Desempenho: caches por PNCP; spinner imediato no Resumo; highlight de descrição desativado por performance.
