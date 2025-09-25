# GSB — Diagrama Funcional (v1)

Este documento descreve o fluxo funcional do GovGo Search Browser (GSB) com ênfase em callbacks, Stores e componentes UI. O diagrama e as seções abaixo estão hierarquizados e explicados por função.

## Visão geral (Mermaid)

```mermaid
flowchart TB
  subgraph UI[UI / Dash]
    Q[query-input]
    BTN[submit-button]
    CFG[config-collapse]
    HIST[history-list]
    TABS[tabs-bar]
    TABLE[results-dt]
    DETAILS[results-details]
    STATUS[status-bar]
    CATS[categories-table]
    EXP[export-panel]
  end

  subgraph Stores
    PS[processing-state]
    PINT[progress-interval]
    PSTORE[progress-store]
    SESS[store-result-sessions]
    ACTIVE[store-active-session]
    EVENT[store-session-event]
    CURT[store-current-query-token]
    RES[store-results]
    RESS[store-results-sorted]
    META[store-meta]
    CATS_S[store-categories]
    LQ[store-last-query]
    SORT[store-sort]
    PAN[store-panel-active]
    CITEMS[store-cache-itens]
    CDOCS[store-cache-docs]
    CSUM[store-cache-resumo]
    HIST_S[store-history]
    FAV_S[store-favorites]
  end

  Q -->|Enter/Click| BTN
  BTN -->|set_processing_state| PS
  PS -->|clear panels / hide| UI
  PS -->|toggle interval| PINT
  PINT --> PSTORE --> UI
  PS -->|run_search| EVENT
  EVENT -->|create_or_update_session| SESS --> ACTIVE -->|sync_active_session| RES & RESS & META & CATS_S & LQ
  ACTIVE --> TABS

  RES & SORT -->|compute_sorted_results| RESS --> TABLE
  META & CATS_S & LQ --> STATUS & CATS

  RESS --> DETAILS
  PAN -->|toggle icons/wrappers| DETAILS
  DETAILS -->|itens-btn/docs-btn/resumo-btn| PAN
  PAN -->|load_itens/load_docs/load_resumo| CITEMS & CDOCS & CSUM

  META -->|update_history_on_search| HIST_S --> HIST
  HIST -->|history-item| Q
  HIST -->|history-replay| EVENT
  HIST -->|history-delete| HIST_S

  DETAILS -->|bookmark-btn| FAV_S
  FAV_S -->|sync icons| DETAILS
  FAV_S --> favorites-list
  favorites-list -->|favorite-item| EVENT
  favorites-list -->|favorite-delete| FAV_S

  RES -->|export-buttons| EXP
```

## Estágios e callbacks principais

- Entrada e processamento
  - set_processing_state: cria token, emite EVENT pendente, marca PS=true.
  - run_search: consome PS, pré-processa consulta (Assistant), busca (direta/corresp/filtro), ordena, persiste histórico/resultados, emite EVENT concluído, limpa PS.
  - Progresso: progress-interval/update_progress_store/reflect_progress_bar controlam barra e spinner central.
- Sessões e Abas
  - create_or_update_session: dedup por assinatura; cria/atualiza sessões (query, pncp, history).
  - render_tabs_bar/on_tab_click: renderiza/ativa/fecha abas; estilo dinâmico para PNCP.
  - sync_active_session: reflete sessão ativa nas Stores legadas (RES, RESS, META, CATS_S, LQ).
- Renderização de resultados
  - clear_results_content_on_start/hide_result_panels_during_processing: limpam/ocultam painéis durante processamento.
  - render_status_and_categories: mostra status e tabela de categorias.
  - compute_sorted_results/init_sort_from_meta/on_header_sort/render_results_table: ordenação custom e tabela resumo.
  - render_details: cards com informações e painel direito (Itens/Documentos/Resumo).
  - toggle_results_visibility: mostra/esconde cards conforme tipo de aba (query/pncp/history).
- Painéis Itens/Docs/Resumo
  - set_active_panel/update_button_icons/toggle_panel_wrapper: toggle por PNCP.
  - load_itens_for_cards/load_docs_for_cards: busca e cache local por PNCP.
  - show_resumo_spinner_when_active/load_resumo_for_cards: spinner imediato; geração e cache de resumo (com persistência por usuário quando disponível).
- Histórico
  - init_history/render_history_list: carrega e exibe histórico (com configs gravadas).
  - run_from_history/delete_history_item/replay_from_history/update_history_on_search.
- Favoritos
  - init_favorites/load_favorites_on_results/render_favorites_list.
  - toggle_bookmark/sync_bookmark_icons/delete_favorite/open_pncp_tab_from_favorite.
- Exportações
  - export_files: JSON/XLSX/CSV/PDF/HTML para `Resultados_Busca`.

## Notas
- Estilos centralizados em `gvg_styles.py` (sem inline custom além do necessário).
- Favoritos: Store otimista reflete os mesmos campos dos cards; persistência no BD somente `(user_id, numero_controle_pncp, rotulo opcional)`.
- Resumo: uma geração por PNCP por sessão; cache em `store-cache-resumo`.
