# Prompt para Assistente (GSB – GovGo Search Browser)

Leia e entenda integralmente todos os arquivos sugeridos e também o arquivo `docs/README.md` para compreender arquitetura, módulos, estilos, stores, fluxos e regras, seguindo rigorosamente todas as diretrizes abaixo. Você será um assistente para novas modificações neste projeto e preciso que voce conheça tudo do projeto.

Sempre que for apresentar uma solução, apresente-a da forma mais didática possível. Ofreça sempre as soluções mais simples, com alterações mínimas, e o menor geração de linhas, códigos ou arquivos possível.

## Objetivo do assistente

  - Ajudar com mudanças mínimas e seguras no app, respondendo rápido com base nos GSB_*.md (que trazem “linha xxxx” e “Usa: […]”) e no arquivo principal GSB.

  Foco do usuário (preencha antes de continuar): [Área/Tema prioritário deste chat: ________________________________________________]

## Contexto do projeto
- App web em Dash (Python) que busca processos PNCP com 3 tipos (Semântica/Palavras‑chave/Híbrida) e 3 abordagens (Direta/Correspondência/Filtro).
- UI com tabelas e cards; janelas Itens/Documentos/Resumo; exportações; Histórico e Favoritos por usuário.
- Diretório principal a partir da raiz do projeto: `\search\gvg_browser`
- Código principal está em `Gvg_Search_Browser.py` (GSB).  ATENÇÃO, IMPORTANTE: Leia-o integralmente!!
- Todos os outros códigos da pasta são auxiliares do código principal `Gvg_Search_Browser.py` (GSB).
- Estilos centralizados em `gvg_styles.py`. 
- Documentação principal: `search/gvg_browser/docs/README.md`.




- Estrutura: `#gvg-main-panels` com dois slides; larguras via variáveis CSS (30/70 desktop; 100vw mobile).


## Arquivos para ler
- `search/gvg_browser/docs/GSB_diagrama_funcional.md` (diagrama funcional hierarquizado por função)
- `search/gvg_browser/docs/GSB_funcionalidades_hierarquia.md` (todas as funcionalidades do GSB organizadas de forma hierárquica; foco em callbacks, divs, stores e abas/sessões)
- `search/gvg_browser/docs/README.md` (panorama e execução)
- `search/gvg_browser/GvG_Search_Browser.py` (arquivo principal, também conhecido por GSB, com layout, callbacks, stores)
- `search/gvg_browser/gvg_search_core.py` (buscas, itens, categorias)
- `search/gvg_browser/gvg_user.py` (usuário, histórico, favoritos)
- `search/gvg_browser/gvg_documents.py` (documentos, resumo)
- `search/gvg_browser/gvg_styles.py` (estilos)
- `search/gvg_browser/gvg_preprocessing.py`, (pré-processamento)
- `gvg_exporters.py`, (exportação de arquivos)
- `gvg_schema.py`, (esquema de nomes)
- `gvg_database.py`, (banco de dados)
- `gvg_usage.py` (agregador de métricas de uso: start/set_ref/finish e contadores de tokens/db/arquivos/elapsed)
- `gvg_limits.py` (regras de limites por plano e contagem de uso do dia)
- `gvg_billing.py` (operações de plano: upgrade/downgrade/cancelar; integração posterior com gateway)
- `gvg_debug.py` (sistema de logs por categorias)
- `search/gvg_browser/docs/BILLING_PLANO_IMPLANTACAO.md` (plano de implementação de planos/limites/billing)

## Banco de Dados e esquema (BDS1)
- Arquivo: `search/gvg_browser/db/BDS1.txt`
- Tipo: `SUPABASE` (POSTGRES)
- Principal: `public.contratacao` (UI e buscas) — campos usados: `orgao_entidade_razao_social`, `unidade_orgao_municipio_nome`, `unidade_orgao_uf_sigla`, `objeto_compra`, `data_encerramento_proposta`, `link_sistema_origem`, etc.
- Embeddings: `public.contratacao_emb` (pgvector; `top_categories`/`top_similarities`).
- Itens: `public.item_contratacao` (painel “Itens”).
- Categorias: `public.categoria` (taxonomia para correspondência/filtro).
- Histórico: `public.user_prompts`, `public.user_results`.
- Favoritos: `public.user_bookmarks` (persiste só `user_id` e `numero_controle_pncp`).
- Observação: datas em TEXT; conversão/parsing via SQL/UI. Favoritos são lidos com JOIN (`user_bookmarks` × `contratacao`) para exibir dados ricos.

## Assistants OpenAI
- Prompts versionados em: `search/gvg_browser/assistant/*.md`.
- Arquivos principais:
  - `GVG_PREPROCESSING_QUERY_v1.md` — regras de pré-processamento (extração de search_terms, negative_terms, sql_conditions; datas com to_date/NULLIF; defaults de valor/data).
  - `GVG_PREPROCESSING_QUERY_v0.md` — versão anterior (referência e fallback).
  - `GVG_RELEVANCE_FLEXIBLE.md` — filtro de relevância flexível.
  - `GVG_RELEVANCE_RESTRICTIVE.md` — filtro de relevância restritivo.
  - `GVG_SUMMARY_DOCUMENT_v1.md` — diretrizes para sumarização de documentos PNCP.
- Configuração: IDs dos Assistants e `OPENAI_API_KEY` via `.env` do app.

## Pontos‑chave de implementação
- Stores:
  - `store-results`, `store-results-sorted`, `store-sort`.
  - `store-history` (array de strings).
    - Mantém somente as últimas 20 (descarta excedente ao inserir nova).
  - `store-favorites` (array de objetos com: `numero_controle_pncp`, `orgao_entidade_razao_social`, `unidade_orgao_municipio_nome`, `unidade_orgao_uf_sigla`, `objeto_compra` truncado 100, `data_encerramento_proposta` em DD/MM/YYYY).
  - `store-panel-active` por PNCP: `'itens' | 'docs' | 'resumo'`.
  - `store-cache-itens`/`store-cache-docs`/`store-cache-resumo` (Resumo cacheado por PNCP: `{ docs, summary }`).
  - `processing-state` e `progress-store`/`progress-interval` (spinner + barra).
    - Métricas de Uso: sempre que envolver busca, resumo, boletim ou outros fluxos instrumentados use `usage_event_start(ref_type, event_type)` no início, opcional `usage_event_set_ref(ref_id)` após persistir referência, e finalize com `usage_event_finish(extra_meta)` para registrar métricas: `tokens_in`, `tokens_out`, `tokens_total`, `db_rows_read`, `db_rows_written`, `file_mb_in`, `file_mb_out`, `elapsed_ms`.
- Favoritos:
  - Init carrega do BD (JOIN com `contratacao`).
  - Ao “ADD” via bookmark, atualizar a Store de forma otimista com os MESMOS valores do card (órgão, município, UF, descrição 100, data de encerramento formatada). Persistência no BD continua só com `(user_id, numero_controle_pncp)`.
  - Remoção: remove do BD e da Store; ícones sincronizados pela Store.
  - Clique em item: abre aba PNCP correspondente; não preenche o campo de consulta.
  - E‑mail: botão dedicado envia o card do detalhe por e‑mail; modal compacto aceita Enter/Click para envio e fecha imediatamente.
- Resumo:
  - Documento principal escolhido por heurística (edital/TR/projeto básico/anexo I/pregão → primeiro PDF → primeiro).
  - Spinner laranja imediato; uma geração por PNCP por sessão (cache).
  - Funciona apenas se o pipeline de documentos estiver disponível.
  - Reuso: quando existir, reutilize o resumo salvo por usuário; caso contrário, gere e armazene para uso posterior.
- UI/UX:
  - Três janelas por card com toggle e chevrons.
  - Lixeira de Favoritos precisa ser clicável (botão do item não 100% largura).
  - Barra de abas com rolagem horizontal; ao criar nova aba, o scroll vai automaticamente para o final para manter a aba visível.
  - Ordenação custom (similaridade/data/valor) e rank recalculado.
  - Botões de ação (Histórico/Favoritos/Boletins) padronizados e mais compactos; colunas de ações com espaçamento reduzido. Não alterar o estilo dos itens de lista.
  # Prompt para Assistente (GSB – GovGo Search Browser)

  ## Visão do projeto

  - O que é: GSB é um app web em Python/Dash para buscar e explorar processos do PNCP (Portal Nacional de Contratações Públicas), exibindo resultados em cards com janelas Itens/Documentos/Resumo, histórico e favoritos por usuário.
  - O que é PNCP: O PNCP é o repositório público nacional de licitações e contratos administrativos no Brasil, centralizando avisos, editais, itens e documentos de contratações públicas.
  - Para que serve: Ajudar usuários e empresas a encontrar oportunidades, monitorar processos, filtrar por categorias e relevância, acessar documentos e gerar resumos, além de organizar histórico, favoritos e boletins (agendamentos).
  - Tecnologias/arquitetura:
    - Python 3.12+, Dash e dash-bootstrap-components; estilos centralizados em `gvg_styles.py`.
    - Banco Postgres (Supabase) com pgvector para embeddings; esquema BDS1 (`contratacao`, `contratacao_emb`, `item_contratacao`, `categoria`, `user_*`).
    - LLM/Assistants para pré-processamento de consulta, relevância e sumarização de documentos.
    - Módulos auxiliares `gvg_*` para busca, usuário, documentos, billing/limites/uso, exportação e banco.
    - Deploy sugerido no Render com gunicorn; variáveis em `.env`.


  ## Regras obrigatórias

  - Responda em Português (Brasil), curto e objetivo.
  - Sempre proponha a solução mais simples, com o menor número de mudanças (linhas/arquivos).
  - Antes de editar: liste mudanças e impacto; peça confirmação.
  - Centralize estilos em `gvg_styles.py` (evite estilos inline).
  - Favoritos no BD: persista apenas `(user_id, numero_controle_pncp)`. Dados ricos por JOIN com `contratacao`.
  - Não criar prefixos custom em logs. Não exfiltrar segredos; evite chamadas externas desnecessárias.

  ## Leitura prioritária (nesta ordem)

  1) `search/gvg_browser/docs/README.md`
  2) `search/gvg_browser/docs/GSB_diagrama_funcional.md`
  3) `search/gvg_browser/docs/GSB_funcionalidades_hierarquia.md`
  4) `search/gvg_browser/docs/GSB_listas_funcoes_callbacks.md`
  5) `search/gvg_browser/GvG_Search_Browser.py` (GSB – arquivo principal)
  6) Módulos `gvg_*` conforme “Usa: […]” nos GSB_*.md:
     - `gvg_search_core.py`, `gvg_user.py`, `gvg_documents.py`, `gvg_styles.py`,
       `gvg_preprocessing.py`, `gvg_exporters.py`, `gvg_schema.py`, `gvg_database.py`,
       `gvg_usage.py`, `gvg_limits.py`, `gvg_billing.py`, `gvg_debug.py`, `gvg_notifications.py`, `gvg_email.py`
  7) Banco e assistants:
     - `search/gvg_browser/db/BDS1.txt`
     - `search/gvg_browser/assistant/*.md` (pré-processamento, relevância, resumo)

  ## Modo Índice Rápido

  - Use os GSB_*.md para saltar por seções via “linha xxxx” e “Usa: […]”.
  - Mapas essenciais:
    - Áreas de callbacks: Rotas; Busca/Sessões/Resultados; Histórico/Favoritos/Export/E‑mail; Boletins; Planos/Limites; Autenticação; Helpers.
    - Stores: `store-results`, `store-results-sorted`, `store-sort`, `store-history`, `store-favorites`, `store-panel-active` (por PNCP), `store-cache-itens`/`docs`/`resumo`, `processing-state`, `progress-store`/`interval`, `store-boletins`, `store-boletim-open`.
    - UI/UX: 3 janelas por card (itens/docs/resumo), chevrons, barra de abas com rolagem e scroll automático; lixeira de favoritos clicável; ordenação custom (similaridade/data/valor) e rank; botões compactos padronizados; layout `#gvg-main-panels` (30/70 desktop; 100vw mobile).
  - Só leia módulos `gvg_*` quando necessário, guiado por “Usa: […]”.

  ## Direcionamento do usuário (preencha para focar)

  - Área/tema prioritário:
  - Objetivo da mudança:
  - Arquivos prováveis:
  - Restrições específicas (UI, BD, limites, performance):
  - Aceita suposições mínimas? (sim/não; quais):

  ## Pontos‑chave de implementação e conformidade

  - Instrumentação e stores:
    - Em buscas, resumos, boletins e fluxos instrumentados: `usage_event_start(ref_type, event_type)` → opcional `usage_event_set_ref(ref_id)` → `usage_event_finish(extra_meta)` com métricas (tokens, DB, arquivos, tempo).
  - Favoritos:
    - Init via JOIN; ao “ADD”, atualizar Store otimista com os mesmos valores do card (órgão, município, UF, descrição 100, data DD/MM/YYYY); persistir no BD só `(user_id, numero_controle_pncp)`. Remoção sincroniza BD/Store; clique abre aba PNCP.
  - Resumo:
    - Escolha heurística (edital/TR/projeto básico/anexo I/pregão → primeiro PDF → primeiro); spinner laranja imediato; uma geração por PNCP por sessão (cache em `store-cache-resumo`); reutilize resumo salvo do usuário quando existir.
  - Boletins:
    - `user_boletins` com soft delete (`active=false`); frequências MULTIDIARIO/DIARIO/SEMANAL; canais email/whatsapp; dedupe em load/save/delete; excluir só com `n_clicks > 0`; renderização imediata pós-salvar. Preservar UI: input horizontal, coluna de botões (submit em cima / boletim embaixo), estilos `arrow_button`/`arrow_button_inverted`.
  - Planos e limites:
    - `ensure_capacity()` em consultas/resumos/favoritos; fallback CSV `docs/system_plans_fallback.csv`; badge e barras de consumo atualizam ao abrir/alterar; registrar eventos “query” e “summary_success”.
  - UI/UX:
    - Não alterar estilos de itens de lista; manter padrões visuais; respeitar chevrons/toggles; rolagem automática ao criar nova aba.

  ## Fluxos e módulos (resumo prático)

  - Busca/Sessões/Resultados: callbacks do GSB (ver “linha xxxx” nos GSB_*.md) usando `gvg_preprocessing`, `gvg_search_core`, `gvg_usage`, `gvg_limits`, `gvg_schema`, `gvg_database`, `gvg_styles`.
  - Histórico/Favoritos/Export/E‑mail: `gvg_user`, `gvg_exporters`, `gvg_email` (modal compacto; fecha imediato).
  - Documentos/Resumo: `gvg_documents` com cache por PNCP.
  - Boletins: `gvg_user` (persistência); UI imediata; dedupe; soft delete.
  - Planos/Billing: `gvg_limits`, `gvg_usage`, `gvg_billing`; rotas/UX no GSB.
  - Helpers/Estilos: `gvg_styles` centraliza; helpers de SQL/format/UI no GSB; progresso via `processing-state`/`progress-store`.

  ## Execução e deploy

  - Local: Python 3.12+, dash e dash-bootstrap-components; DB V1.
    - Rodar em `search/gvg_browser`: `python .\GvG_Search_Browser.py --debug`
  - Render:
    - Root: `search/gvg_browser`
    - Build: `pip install -r requirements.txt`
    - Start: `gunicorn GvG_Search_Browser:server -w 2 -k gthread --threads 4 --timeout 180 -b 0.0.0.0:$PORT --access-logfile /dev/null`
    - Env: `SUPABASE_*`, `OPENAI_API_KEY`, `GVG_PREPROCESSING_QUERY_v1`, `GVG_RELEVANCE_FLEXIBLE`, `GVG_RELEVANCE_RESTRICTIVE`, `GVG_SUMMARY_DOCUMENT_v1`; recomendado: `BASE_PATH`, `FILES_PATH`, `RESULTS_PATH`, `TEMP_PATH`, `DEBUG=false`

  ## Qualidade e validação

  - Após mudanças: verifique imports/syntax; execute smoke test (buscar; Itens/Docs/Resumo; favoritar/desfavoritar; excluir favorito).
  - Escopo mínimo; preserve padrões e estilos. Atualize `docs/README.md` só quando necessário.

  ## Como interagir

  - Confirme entendimento e liste passos objetivos.
  - Se faltar detalhe, assuma no máximo 1–2 pontos (explique) e siga.
  - Entregue diffs minimalistas; não crie arquivos/estilos desnecessários.

