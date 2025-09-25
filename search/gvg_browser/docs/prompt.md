# Prompt para Assistente (GSB – GovGo Search Browser)

Leia e entenda integralmente todos os arquivos sugeridos e também o arquivo `docs/README.md` para compreender arquitetura, módulos, estilos, stores, fluxos e regras, seguindo rigorosamente todas as diretrizes abaixo. Você será um assistente para novas modificações neste projeto e preciso que voce conheça tudo do projeto.

## Contexto do projeto
- App web em Dash (Python) que busca processos PNCP com 3 tipos (Semântica/Palavras‑chave/Híbrida) e 3 abordagens (Direta/Correspondência/Filtro).
- UI com tabelas e cards; janelas Itens/Documentos/Resumo; exportações; Histórico e Favoritos por usuário.
- Diretório principal a partir da raiz do projeto: `\search\gvg_browser`
- Código principal está em `Gvg_Search_Browser.py` (GSB). Todos os outros códigos da pasta são auxiliares desse código. Leia-o integralmente, e não somente algumas linhas.
- Estilos centralizados em `gvg_styles.py`. Documentação principal: `search/gvg_browser/docs/README.md`.


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
  - `store-favorites` (array de objetos com: `numero_controle_pncp`, `orgao_entidade_razao_social`, `unidade_orgao_municipio_nome`, `unidade_orgao_uf_sigla`, `objeto_compra` truncado 100, `data_encerramento_proposta` em DD/MM/YYYY).
  - `store-panel-active` por PNCP: `'itens' | 'docs' | 'resumo'`.
  - `store-cache-itens`/`store-cache-docs`/`store-cache-resumo` (Resumo cacheado por PNCP: `{ docs, summary }`).
  - `processing-state` e `progress-store`/`progress-interval` (spinner + barra).
- Favoritos:
  - Init carrega do BD (JOIN com `contratacao`).
  - Ao “ADD” via bookmark, atualizar a Store de forma otimista com os MESMOS valores do card (órgão, município, UF, descrição 100, data de encerramento formatada). Persistência no BD continua só com `(user_id, numero_controle_pncp)`.
  - Remoção: remove do BD e da Store; ícones sincronizados pela Store.
  - Clique em item: abre aba PNCP correspondente; não preenche o campo de consulta.
- Resumo:
  - Documento principal escolhido por heurística (edital/TR/projeto básico/anexo I/pregão → primeiro PDF → primeiro).
  - Spinner laranja imediato; uma geração por PNCP por sessão (cache).
  - Funciona apenas se o pipeline de documentos estiver disponível.
- UI/UX:
  - Três janelas por card com toggle e chevrons.
  - Lixeira de Favoritos precisa ser clicável (botão do item não 100% largura).
  - Barra de abas com rolagem horizontal; ao criar nova aba, o scroll vai automaticamente para o final para manter a aba visível.
  - Ordenação custom (similaridade/data/valor) e rank recalculado.
  - Boletins (agendamento):
    - Tabela `public.user_boletins` (soft delete via `active=false`).
    - Frequências: MULTIDIARIO (slots), DIARIO (seg-sex implícito), SEMANAL (dias).
    - Canais: email / whatsapp.
    - Snapshot de config salvo (search_type, approach, relevance, sort_mode, max_results, top_categories_count, filter_expired).
    - Stores: `store-boletins`, `store-boletim-open`.
    - Botão Boletim (ícone calendário) reposicionado: abaixo do submit, mesma largura/estilo circular; alterna estilo invertido ao abrir collapse.
    - Deduplicação `_dedupe_boletins` aplicada em load/save/delete.
    - Exclusão: valida `n_clicks > 0` antes de soft delete.
    - Limitações: sem editar/reativar/scheduler interno ainda.

## Execução local
- Requisitos: Python 3.12+, `dash` e `dash-bootstrap-components`; DB V1 configurado.
- Rodar em `search/gvg_browser`: `python .\GvG_Search_Browser.py --debug`
- `docling` é opcional (apenas Resumo). Variáveis em `.env` (inclui `OPENAI_API_KEY` e IDs dos Assistants).

## Deploy no Render (essencial)
- Root Directory: `search/gvg_browser`
- Build: `pip install -r requirements.txt`
- Start: `gunicorn GvG_Search_Browser:server -w 2 -k gthread --threads 4 --timeout 180 -b 0.0.0.0:$PORT`
- Env (no painel): `SUPABASE_*`, `OPENAI_API_KEY`, `GVG_PREPROCESSING_QUERY_v1`, `GVG_RELEVANCE_FLEXIBLE`, `GVG_RELEVANCE_RESTRICTIVE`, `GVG_SUMMARY_DOCUMENT_v1` e, recomendado: `BASE_PATH=/tmp`, `FILES_PATH=/tmp/files`, `RESULTS_PATH=/tmp/reports`, `TEMP_PATH=/tmp`, `DEBUG=false`.
- DNS (www): CNAME `www` → domínio do serviço no Render; remover A de `www`. Apex opcional conforme instruções do Render.

## Qualidade e validação
- Antes de editar: liste mudanças e impacto. Peça confirmação.
- Depois: verifique imports/syntax, execute e faça smoke test (buscar, Itens/Docs/Resumo, favoritar/desfavoritar, excluir favorito).
- Escopo mínimo; preserve padrões e estilos.

## Como interagir
- Confirme entendimento do pedido e liste passos objetivos.
- Se faltar detalhe, faça no máximo 1–2 suposições razoáveis e siga, apontando-as.
- Entregue diffs minimalistas; atualize `docs/README.md` quando necessário.
- Ao modificar UI de Boletins, preservar: input horizontal, coluna de botões (submit em cima / boletim embaixo) e uso de estilos centralizados (`arrow_button` / `arrow_button_inverted`).

