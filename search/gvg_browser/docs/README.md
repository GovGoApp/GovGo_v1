# GovGo Search Browser (GSB) — Arquitetura e Guia Rápido

Este documento resume e explica a arquitetura do módulo `gvg_browser` e, em especial, o app principal `GvG_Search_Browser.py` (Dash). Foquei no que existe no código e no que é necessário para rodar e manter.

## Visão geral

- Objetivo: Interface web (Dash) para buscar processos PNCP com 3 tipos de busca (Semântica, Palavras‑chave, Híbrida) e 3 abordagens (Direta, Correspondência de categoria, Filtro por categoria).
- Diferenciais:
  - “Processamento inteligente” da consulta (pré‑processamento com OpenAI Assistant) que separa termos e restrições SQL.
  - Filtro de relevância com 3 níveis (desligado, flexível, restritivo) via Assistant opcional.
  - Painéis de resultados com tabelas e cards de detalhes (ordenação, cores por proximidade da data de encerramento, botões de Itens/Documentos/Resumo).
  - Exportação: JSON, XLSX, CSV, PDF e HTML.
  - Integração de documentos PNCP com conversão para Markdown (Docling) e resumo (OpenAI), com cache mínimo local em pastas `files/` e `reports/`.
   - UX aprimorada para janelas de Itens/Documentos/Resumo: padding e fonte uniformes, spinner laranja centralizado no Resumo e toggle com ícones nos botões.

## Módulos e responsabilidades

- `GvG_Search_Browser.py` (principal)
  - Monta o app Dash (layout e callbacks) e orquestra: busca, progresso, ordenação, renderização das categorias e dos detalhes, abertura de painéis Itens/Docs/Resumo, exportações e histórico.
  - Importa funções de busca do `gvg_search_core` e utilitários (pré‑processamento, AI, exporters, documentos, estilos e usuário).

- `gvg_search_core.py`
  - Núcleo da busca (Semântica, Palavras‑chave, Híbrida) sobre as tabelas V1 (`contratacao`, `contratacao_emb`, `categoria`).
  - Usa `pgvector` (distância <=>) e/ou FTS do PostgreSQL; aplica filtros de data de encerramento e condições SQL retornadas pelo pré‑processador.
  - Suporte a categorias: top categorias via embedding, busca por correspondência e filtro por interseção de categorias.
  - Filtro de relevância opcional (3 níveis) com OpenAI Assistants.

- `gvg_schema.py`
  - “Fonte da verdade” de nomes de tabelas/colunas do V1 + builders de SELECTs para reduzir duplicação de SQL.
  - Fornece lista de colunas “core” para `contratacao` e builders para buscas semânticas e categorias.

- `gvg_database.py`
  - Conexões (psycopg2/SQLAlchemy) e utilidades leves de banco (lendo `.env`/`supabase_v1.env`).
  - `fetch_documentos(numero_controle)` tenta recuperar link do processo via DB; fallback para API oficial PNCP.

- `gvg_preprocessing.py`
  - Pré‑processa a consulta com OpenAI Assistant (separa `search_terms`, `negative_terms`, `sql_conditions`).
  - Utilitários de formatação: moeda, datas, decodificadores simples.

- `gvg_ai_utils.py`
  - Embeddings com OpenAI, incluindo estratégia de “negação” (embedding positivo – peso × embedding negativo) e geração de palavras‑chave.
  - `calculate_confidence` (média dos scores × 100).

- `gvg_documents.py`
  - Download/processamento de documentos PNCP: converte com Docling para Markdown e gera resumo com OpenAI. Salva artefatos em `files/` e `reports/`.
  - Contém sua própria `fetch_documentos` (mesma assinatura; o app importa de lá preferencialmente quando o pipeline de docs está habilitado).

- `gvg_exporters.py`
  - Exportação de resultados (JSON/XLSX/CSV/PDF/HTML) com nomes de arquivo padronizados.

- `gvg_email.py`
  - Envio de e-mails diretamente pela UI (Favoritos e Boletins) usando biblioteca padrão.
  - Modal compacto: Enter ou Click enviam e a janela fecha imediatamente; envio assíncrono (UI segue responsiva).
  - Renderização de conteúdo de e-mail consistente com a UI (cards e boletins).

- `gvg_user.py`
  - Usuário atual (mock) e histórico: `user_prompts` / `user_results` no banco (se existirem). Permite salvar consultas, apagar e registrar resultados de uma busca.

- `gvg_styles.py` e `gvg_css.py`
  - Dicionário `styles` usado no layout e CSS adicional (inclui CSS para Markdown do resumo). OBS: `gvg_css.py` está vazio; o projeto usa `gvg_styles.py`.
  - Destaques recentes:
    - `details_content_base`: wrapper absoluto (posiciona/oculta as janelas).
    - `details_content_inner`: padding/fonte uniformes do conteúdo das janelas (padding 4px; fonte base 12px).
    - `details_spinner_center`: centraliza spinner (flex, alinhado no centro H/V).

## Fluxos principais

1) Consulta → pré‑processamento → categorias (opcional) → busca
- O botão “→” define `processing-state=True` e inicia `run_search`.
- `SearchQueryProcessor.process_query` tenta extrair termos/negativos/condições SQL.
- Se abordagem for 2/3, busca top categorias próximas à consulta via embedding (`get_top_categories_for_query`).
- Executa uma das buscas:
  - Direta: `semantic_search` (KNN com pgvector), `keyword_search` (FTS) ou `hybrid_search` (combinações)
  - Correspondência de categoria: filtra onde há interseção entre categorias do resultado e as top categorias da consulta
  - Filtro de categoria: busca base e filtra por interseção de categorias
- Ordena por similaridade / data / valor (configurável).
- (Opcional) Aplica Filtro de Relevância (níveis 2/3) com Assistant.
- Persiste histórico: salva prompt (com embedding do prompt) e resultados em `user_results` (se as tabelas existirem).

2) Renderização (UI)
- Status da busca (metadados) + tabela de categorias (se houver) + tabela de resultados (resumo) + cards detalhados.
- Cada card tem botões “Itens”, “Documentos” e “Resumo”. Abrir um painel dispara callbacks que:
  - Itens: lê itens do processo via `fetch_itens_contratacao` (em `gvg_search_core`, vindo do DB) e gera tabela (com bagulho de totalização).
  - Documentos: lista documentos do processo via `fetch_documentos` (DB ou API) e cria DataTable com links.
  - Resumo: escolhe “documento principal” (heurísticas por nome/URL) e chama `summarize_document`/`process_pncp_document` para baixar, converter e sumarizar. Resultado é exibido em Markdown.
  - Toggle entre janelas: o estado por PNCP é guardado em `store-panel-active`; somente a janela ativa fica com `display: 'block'` (as outras ficam `display: 'none'`). O wrapper (`panel-wrapper`) só aparece se houver uma janela ativa para aquele PNCP.
  - Ícones nos botões: os três botões exibem chevron para cima (ativo) ou para baixo (inativo), atualizados por callback conforme o toggle.
  - Spinner no Resumo: ao ativar “Resumo”, mostra um spinner laranja centralizado (usando `details_spinner_center`) enquanto o sumário é gerado; ao terminar, o spinner é substituído pelo texto.
  - Cache por PNCP: Resumo é processado apenas uma vez por sessão. O texto é salvo em `store-cache-resumo[pid]` e reapresentado instantaneamente nas próximas aberturas. Itens (`store-cache-itens`) e Documentos (`store-cache-docs`) também usam cache.
  - Envio de e‑mail pela UI: botões dedicados em Favoritos e Boletins abrem modal compacto; Enter/Click enviam e a janela fecha na hora.

3) Exportações
- Botões no painel “Exportar” geram arquivos em `reports/`: JSON, XLSX, CSV, PDF (se reportlab instalado) e HTML.

## Boletins (Agendamento de Consultas)

Funcionalidade recém‑adicionada para permitir que o usuário salve uma consulta parametrizada e a agende para execuções futuras (orquestração externa futura). Primeira etapa: criação, listagem e remoção.

Tabela: `public.user_boletins`
- Campos utilizados: `id`, `user_id`, `query_text`, `schedule_type`, `schedule_detail` (jsonb), `channels` (jsonb), `config_snapshot` (jsonb), `active`, `created_at`.
- Soft delete: `active = false` (não remove linha).

Frequências suportadas:
- MULTIDIARIO: `schedule_detail = { slots: [ 'manha'|'tarde'|'noite' ] }`
- DIARIO: implícito seg‑sex (armazenado como `{ days: ['seg','ter','qua','qui','sex'] }`)
- SEMANAL: `{ days: [...] }` com subset de seg..sex.

Canais: `email`, `whatsapp` (array JSONB em `channels`).

Snapshot de configuração salvo em `config_snapshot` (campos: search_type, search_approach, relevance_level, sort_mode, max_results, top_categories_count, filter_expired).

UI / Layout:
- Botão consulta (seta) e, logo abaixo dele (mesma coluna à direita do campo), o botão de boletim com ícone `fa-calendar-plus`.
- Botão Boletim: mesma geometria (32px, circular). Cor normal (laranja) quando fechado; invertida (fundo branco/borda laranja) quando o painel está aberto.
- Collapse “Configurar Boletim” com: Frequência, Horários/Dias, Canais e botão “Salvar Boletim”.

Comportamento de lista:
- Após salvar, o boletim aparece completo imediatamente na lista (sem recarregar a página).
- A coluna de ações usa estilo compacto, com botões menores e espaçamento reduzido.

Stores:
- `store-boletins`: lista de objetos `{ id, query_text, schedule_type, schedule_detail, channels }` (somente ativos, ordenados por criação desc).
- `store-boletim-open`: boolean (estado do collapse de configuração).

Callbacks principais:
- Habilitação do botão (depende de query não vazia) e inversão de estilo conforme aberto/fechado.
- Salvar: cria registro, insere otimisticamente na store (dedupe `_dedupe_boletins`).
- Carregar inicial: busca apenas ativos `active=true`.
- Remover: pattern‑matching com validação `n_clicks > 0` antes de `deactivate_user_boletim` (protege contra triggers fantasmas). Também aplica dedupe.

Deduplicação:
- Função `_dedupe_boletins` remove IDs repetidos e imprime log simples quando necessário.

Limitações atuais (backlog):
- Sem edição / reativação.
- Sem cálculo de `next_run_at` ou executor agendador interno (será implementado externamente).
- Sem página de histórico de execuções de boletim.

Logs:
- Apenas prints simples em exclusão e deduplicação (sem prefixos customizados, conforme política).

Impacto visual:
- Ajuste de layout do container da consulta mantendo alinhamento horizontal original do input + coluna de botões à direita.

## Banco de dados (V1)

- Tabelas chave:
  - `contratacao`: campos usados no core (ver `gvg_schema.CONTRATACAO_CORE_ORDER`). Datas são TEXT (convertidas com `to_date` no SQL quando necessário; ex. filtros por encerramento).
  - `contratacao_emb`: vetor de embeddings (`pgvector`) e listas `top_categories`/`top_similarities`.
  - `categoria`: embeddings de categorias e metadados por níveis.
  - (Opcional) `public.user_prompts` e `public.user_results` para histórico/salvamento de saídas da busca.

- Conexão: variáveis `SUPABASE_HOST/PORT/USER/PASSWORD/DBNAME` via `.env` (ou `supabase_v1.env`).

### Esquema do Banco (BDS1)

- Referência: `db/BDS1.txt` (apenas contexto, não executar diretamente).
- Tabelas relevantes e uso no app:
  - `public.contratacao`: fonte principal para UI e buscas (ex.: `orgao_entidade_razao_social`, `unidade_orgao_municipio_nome`, `unidade_orgao_uf_sigla`, `objeto_compra`, `data_encerramento_proposta`, `link_sistema_origem`).
  - `public.contratacao_emb`: embeddings, `top_categories`, `top_similarities` (pgvector) — usado nas buscas semânticas.
  - `public.item_contratacao`: itens por processo — usado no painel “Itens”.
  - `public.categoria`: taxonomia; suporte às buscas por/filtradas por categoria.
  - `public.user_prompts`, `public.user_results`: histórico do usuário.
  - `public.user_bookmarks`: favoritos (persiste apenas `user_id` e `numero_controle_pncp`).

- Observações:
  - Muitas datas estão como TEXT; conversões/parsing são feitos no SQL ou na UI quando necessário.
  - A leitura dos favoritos usa JOIN entre `user_bookmarks` e `contratacao` por `numero_controle_pncp` para exibir campos ricos na lista.

## OpenAI e Assistants

- `OPENAI_API_KEY` obrigatório para: embeddings, pré‑processamento da query, filtro de relevância, resumo de documentos.
- Assistants (IDs no `.env`):
  - `GVG_PREPROCESSING_QUERY_v1` (pré-processamento) — obrigatório para “inteligente”.
  - `GVG_RELEVANCE_FLEXIBLE` e `GVG_RELEVANCE_RESTRICTIVE` (níveis 2/3) — opcionais.
- Modelos: default `text-embedding-3-large`; chat para sumário/documentos configurado como `gpt-4o` no módulo de documentos.

### Arquivos de Assistants (prompts)

- Localização: `search/gvg_browser/assistant/*.md` (prompts versionados usados pelos Assistants).
- Principais arquivos e funções:
  - `GVG_PREPROCESSING_QUERY_v1.md` — Regras do pré-processamento da consulta (gera search_terms, negative_terms, sql_conditions, casting seguro de datas e defaults).
  - `GVG_PREPROCESSING_QUERY_v0.md` — Versão anterior/base do pré-processamento (fallback e histórico de evolução).
  - `GVG_RELEVANCE_FLEXIBLE.md` — Prompt para filtro de relevância nível Flexível (tolera ruído, mantém mais resultados).
  - `GVG_RELEVANCE_RESTRICTIVE.md` — Prompt para filtro de relevância nível Restritivo (mais rigoroso, reduz a lista).
  - `GVG_SUMMARY_DOCUMENT_v1.md` — Estrutura do resumo de documentos PNCP (formato e critérios).
- Configuração:
  - IDs dos Assistants e `OPENAI_API_KEY` devem estar no `.env` do app (não commitá-los).

## Documentos PNCP (Docling)

- Quando habilitado, o resumo baixa o arquivo (PDF/ZIP etc.), converte para Markdown com Docling e chama OpenAI para gerar um resumo padronizado.
- Saídas salvas em:
  - `files/DOCLING_*.md` — Markdown completo do(s) documento(s)
  - `reports/SUMMARY_*.md` — Resumo em Markdown
- Dependência opcional: `docling` (pesada). Se não instalada, o resumo retornará mensagem de erro; o app continua funcionando.
  - O resumo é reutilizado por usuário quando disponível (persistência opcional no banco) e também é cacheado por sessão por PNCP.
  - Quando o pipeline de documentos não está habilitado, a UI informa de forma clara e segue operando.

## Histórico do usuário

- Mock de usuário fixo em `gvg_user.py` (nome/email/uid). Integração futura com autenticação.
- Se `user_prompts` e `user_results` existirem no DB, o app salva consultas e resultados:
  - `add_prompt(...)` insere e retorna `prompt_id` (com embedding do prompt opcionalmente)
  - `save_user_results(prompt_id, results)` insere rank/similaridade/valor/data por resultado

Interação:
- Ao clicar em um item do histórico, a UI preenche as configurações e filtros correspondentes, mas não executa a busca automaticamente (o envio é manual).

## Favoritos do usuário

- O painel “Favoritos” lista marcações salvas por usuário. Cada item mostra 4 linhas:
  - Órgão (orgao_entidade_razao_social)
  - Local (Município/UF)
  - Descrição (objeto_compra) truncada em 100 caracteres
  - Data de Encerramento (DD/MM/YYYY) com cor conforme proximidade
- Fluxo principal:
  - Inicialização: na primeira renderização, a Store de favoritos é preenchida a partir do banco via `fetch_bookmarks(limit=200)`.
  - Adicionar/remover via botão bookmark no card de detalhes:
    - Ao adicionar, o app insere na Store (UI) um item com os mesmos valores que estão no card (órgão, município, UF, descrição truncada, data de encerramento formatada) — atualização otimista, sem aguardar o BD.
    - Em paralelo, persiste no BD apenas `(user_id, numero_controle_pncp)` com `add_bookmark(...)` (sem campos extras).
    - Ao remover, chama `remove_bookmark(...)` e filtra a Store pelo PNCP.
  - Ícones dos cartões são atualizados imediatamente com base na Store e sincronizados quando a Store muda.
  - Clicar num favorito abre uma aba PNCP com o processo; não altera o campo de consulta.
  - Após cada busca concluída, a lista de favoritos pode ser recarregada do BD.

Formato do item em `store-favorites` (UI):

- numero_controle_pncp: string
- orgao_entidade_razao_social: string
- unidade_orgao_municipio_nome: string
- unidade_orgao_uf_sigla: string
- objeto_compra: string (máx. 100 chars)
- data_encerramento_proposta: string (DD/MM/YYYY)

Observação de UX:
- A lixeira do item deve permanecer clicável; o botão do item não ocupa 100% da largura (usa flex) para não sobrepor o botão de exclusão.

## Estilos e UX

- Estilo e cores (cards, botões, tabelas) vêm de `gvg_styles.styles`.
- Ícones via FontAwesome (por meio do Bootstrap theme referenciado).
- Cores da Data Encerramento variam por proximidade (roxo para vencidos; verde para > 30 dias).

Botões e colunas de ação (listas):
- Botões de ação em Histórico, Favoritos e Boletins foram padronizados e estão mais compactos.
- As colunas de ações têm espaçamento vertical reduzido para melhor aproveitamento do espaço.
- Os itens de lista permanecem com o estilo original; somente os botões e o espaçamento entre eles foram reduzidos.

### Barra de abas (Sessões)

- Abas com rolagem horizontal (sem encolher). Quando uma nova aba é criada, o scroll é movido automaticamente para o final, mantendo a aba recém‑criada visível.
- Ícones: busca para abas de consulta e bookmark sólido para abas PNCP. Títulos truncados para caber com reticências.

### Layout dos detalhes e janelas laterais

- Largura dos painéis no card de detalhes: esquerda (detalhes do processo) 50% e direita (janelas Itens/Documentos/Resumo) 50%.
- Cada janela é composta por:
  - `details_content_base` (wrapper absoluto, controla visibilidade e scroll)
  - `details_content_inner` (container interno com padding de 4px e fonte base 12px)
- O spinner do Resumo é centralizado horizontal e verticalmente aplicando `details_spinner_center` dentro de um `details_content_inner` com `height: 100%`.

### Política de Estilos (obrigatória)

- Toda adição/alteração de estilos deve ser centralizada no arquivo `gvg_styles.py`.
- O app principal (`GvG_Search_Browser.py`) deve apenas referenciar chaves do dicionário `styles` e não inserir estilos inline, salvo raras exceções utilitárias já padronizadas em `gvg_styles`.
- Se precisar de um novo estilo, crie uma chave em `styles` (ou reutilize uma existente) e aplique-a nos componentes. Evite duplicação de dicionários de estilo dentro do layout/callbacks.
- Benefícios: consistência visual, manutenção mais simples, e possibilidade de ajustes globais sem varrer o código.

### Stores e estado da UI

Principais Stores e seus formatos:

- `store-results`: lista de resultados “brutos” (cada item possui `details` com os campos do processo).
- `store-results-sorted`: lista ordenada para UI; o campo `rank` é recalculado após ordenação.
- `store-sort`: objeto `{ field: 'orgao'|'municipio'|'uf'|'similaridade'|'valor'|'data', direction: 'asc'|'desc' }` refletindo a ordenação ativa.
- `store-history`: array de strings (consultas anteriores do usuário).
- `store-favorites`: array de objetos (formato descrito na seção Favoritos).
- `store-panel-active`: mapeia `{ [pncp]: 'itens'|'docs'|'resumo' }` para controlar a janela ativa por cartão.
- `store-cache-itens` / `store-cache-docs` / `store-cache-resumo`: caches por PNCP; para Resumo, o valor é `{ docs: [...], summary: '...' }`.
- `processing-state` + `progress-store`/`progress-interval`: controle do spinner central e da barra de progresso (percent/label) durante a busca.
- `store-boletins`: boletins ativos do usuário.
- `store-boletim-open`: estado (True/False) painel de configuração de boletim.

## Como executar

Pré‑requisitos:
- Python 3.12+ (recomendado pelo cache `__pycache__` visto) e acesso ao banco V1.
- Variáveis de ambiente configuradas no `gvg_browser/.env` (NÃO commitar chaves reais). Rotacione chaves se `.env` com segredos ficou público.

Instalação (Windows/PowerShell):
1. Crie um ambiente virtual (opcional) e instale dependências deste pacote:
   - `pip install -r search/gvg_browser/requirements.txt`
   - Dependências de UI (faltavam no arquivo e foram adicionadas): `dash` e `dash-bootstrap-components`.
   - Opcional para resumo de documentos: `pip install docling`
2. Verifique conectividade ao banco (Supabase Postgres) e se as tabelas V1 existem.

Execução:
- No diretório `search/gvg_browser`:
  - `python .\GvG_Search_Browser.py --debug` (ativa logs SQL)  
  - `python .\GvG_Search_Browser.py --markdown` (habilita CSS de markdown nos resumos)

Atenção:
- Se falhar ao importar `dash`/`dash_bootstrap_components`, instale-os (ver seção Instalação).
- Se o filtro de relevância ou pré‑processamento falhar por falta dos Assistants, a busca segue sem essas etapas.
- Se o resumo falhar por ausência do `docling` ou `OPENAI_API_KEY`, a funcionalidade “Resumo” apenas mostra o erro; o resto do app segue ok.

## Deploy no Render (essencial)

- Serviço Web (env: Python) com raiz do projeto em `search/gvg_browser` (rootDirectory).
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn GvG_Search_Browser:server -w 2 -k gthread --threads 4 --timeout 180 -b 0.0.0.0:$PORT --access-logfile /dev/null`
- Site (produção): https://www.govgo.com.br (Render)
- Variáveis no painel (não commitar .env):
  - Banco: `SUPABASE_HOST`, `SUPABASE_USER`, `SUPABASE_PASSWORD`, `SUPABASE_PORT=6543`, `SUPABASE_DBNAME`.
  - OpenAI/Assistants: `OPENAI_API_KEY`, `GVG_PREPROCESSING_QUERY_v1`, `GVG_RELEVANCE_FLEXIBLE`, `GVG_RELEVANCE_RESTRICTIVE`, `GVG_SUMMARY_DOCUMENT_v1`.
  - Recomendadas (filesystem efêmero): `BASE_PATH=/tmp`, `FILES_PATH=/tmp/files`, `RESULTS_PATH=/tmp/reports`, `TEMP_PATH=/tmp`, `DEBUG=false`.
  - Opcionais (e‑mail): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS` (1/0), `SMTP_FROM`, `SMTP_FROM_NAME`.
- DNS (www.govgo.com.br): criar CNAME `www` apontando para o domínio do serviço no Render e remover A de `www`; apex opcional conforme instruções do Render.

## Depuração

- Sistema de logs centralizado (`gvg_debug.py`) com categorias e Rich:
  - Importação: `from gvg_debug import debug_log as dbg, debug_sql as dbg_sql`.
  - Uso: chame diretamente `dbg('AREA', 'mensagem')` — sem try/except nem guards; o `dbg` já verifica as flags.
  - Prefixo automático: toda mensagem sai como `[AREA] ...`; `dbg_sql` imprime `[SQL] ...` (inclui cabeçalho, SQL e parâmetros).
  - Flags de ambiente (booleanos: 1/true/yes/on):
    - `DEBUG`: master. Se `false`, nada loga. Se `true`, apenas áreas com `GVG_<AREA>_DEBUG=true` logam.
    - `GVG_<AREA>_DEBUG`: por categoria, ex.: `GVG_SQL_DEBUG`, `GVG_AUTH_DEBUG`, `GVG_SEARCH_DEBUG`, `GVG_DOCS_DEBUG`, `GVG_ASSISTANT_DEBUG`, `GVG_UI_DEBUG`, `GVG_BROWSER_DEBUG`, `GVG_BOLETIM_DEBUG`, `GVG_BMK_DEBUG`, `GVG_FAV_DEBUG`, `GVG_PREPROC_DEBUG`, `GVG_RESUMO_DEBUG`.
  - Exemplos: `dbg('AUTH', 'Login ok')` → `[AUTH] Login ok`; `dbg_sql('fetch', sql, params)` → linhas com `[SQL]`.

Outros:
- `--debug` (CLI) e/ou `DEBUG=1` (env) habilitam logs gerais; ligue as áreas específicas que deseja ver.
- `set_sql_debug(True)` segue existindo, porém prefira controlar por `DEBUG` + `GVG_SQL_DEBUG`.
- Progresso de busca é refletido no spinner central e numa barra (percent/label).
- Para diagnosticar UI (favoritos, histórico, Itens/Docs/Resumo), ative `GVG_UI_DEBUG`/`GVG_DOCS_DEBUG` etc.

## Estrutura de pastas (dentro de `gvg_browser`)

- `GvG_Search_Browser.py` — app Dash
- `gvg_search_core.py` — buscas, categorias, relevância
- `gvg_schema.py` — schema central V1 e builders de SELECT
- `gvg_database.py` — conexões DB e fetch de links/documentos
- `gvg_preprocessing.py` — Assistant de pré‑processamento + formatters
- `gvg_ai_utils.py` — embeddings/keywords/confidence
- `gvg_documents.py` — pipeline Docling + sumário OpenAI
- `gvg_exporters.py` — exportação (JSON/XLSX/CSV/PDF/HTML)
- `gvg_user.py` — usuário/histórico/armazenamento de resultados
- `gvg_styles.py` — estilos e CSS utilitário
- `docs/` — documentação (este arquivo)
- `files/`, `reports/`, `temp/` — saídas e temporários

## Requisitos e compatibilidade

- Banco: PostgreSQL com extensão `pgvector` instalada na instância Supabase.
- Python libs (principais): `openai`, `psycopg2-binary`, `sqlalchemy`, `pandas`, `numpy`, `requests`, `pgvector`, `openpyxl`, `reportlab` (PDF), `dash`, `dash-bootstrap-components`. Opcional: `docling`.

## Resumo executivo

- O GSB entrega uma busca moderna sobre PNCP com UX de painel, combinando embeddings (pgvector) e FTS.
- O código está modularizado: schema centralizado, SQL builders, e UI separada dos serviços de busca/IA.
- Funcionalidades premium (relevância, sumários) degradam graciosamente quando não configuradas.
- Para rodar sem atritos: configure `.env`, garanta `dash`/`dash-bootstrap-components`/`openai`/DB e, se quiser resumo de documentos, instale `docling`.
- Nova funcionalidade de Boletins adiciona camada de agendamento (primeira etapa: CRUD básico e UI). Próximas etapas incluem executor e reativação.

---


## Atualizações recentes (2025-09-10)
- Logging unificado por categorias (`gvg_debug`):
  - `dbg` auto‑gaitado por `DEBUG` + `GVG_<AREA>_DEBUG` (sem `isdbg` nem try/except ao redor de logs).
  - Prefixo `[AREA]` em todas as mensagens; `dbg_sql` imprime `[SQL]` em todas as linhas (header, SQL e params).
  - Novas flags por área adicionadas ao `.env` do browser.
- `GVG_BROWSER_DEV` separa DEV/PROD de `DEBUG` (host/porta independentes do nível de log).

## Atualizações recentes (2025-09-09)
- Mobile (≤ 992px): swipe zero‑JS entre “Controles” e “Resultados” via CSS scroll‑snap; desktop preservado (30/70).
- Estrutura: painéis envolvidos em `#gvg-main-panels > .gvg-slide`; larguras controladas por variáveis CSS (desktop 30/70; mobile 100vw por slide).
- Estilos centralizados em `gvg_styles.py`; nenhuma nova dependência.
- Header: título “GvG Search” oculto no mobile.

Última atualização: 2025-09-10.
