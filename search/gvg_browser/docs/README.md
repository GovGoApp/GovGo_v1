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

3) Exportações
- Botões no painel “Exportar” geram arquivos em `reports/`: JSON, XLSX, CSV, PDF (se reportlab instalado) e HTML.

## Banco de dados (V1)

- Tabelas chave:
  - `contratacao`: campos usados no core (ver `gvg_schema.CONTRATACAO_CORE_ORDER`). Datas são TEXT (convertidas com `to_date` no SQL quando necessário; ex. filtros por encerramento).
  - `contratacao_emb`: vetor de embeddings (`pgvector`) e listas `top_categories`/`top_similarities`.
  - `categoria`: embeddings de categorias e metadados por níveis.
  - (Opcional) `public.user_prompts` e `public.user_results` para histórico/salvamento de saídas da busca.

- Conexão: variáveis `SUPABASE_HOST/PORT/USER/PASSWORD/DBNAME` via `.env` (ou `supabase_v1.env`).

## OpenAI e Assistants

- `OPENAI_API_KEY` obrigatório para: embeddings, pré‑processamento da query, filtro de relevância, resumo de documentos.
- Assistants (IDs no `.env`):
  - `GVG_PREPROCESSING_QUERY_v1` (pré-processamento) — obrigatório para “inteligente”.
  - `GVG_RELEVANCE_FLEXIBLE` e `GVG_RELEVANCE_RESTRICTIVE` (níveis 2/3) — opcionais.
- Modelos: default `text-embedding-3-large`; chat para sumário/documentos configurado como `gpt-4o` no módulo de documentos.

## Documentos PNCP (Docling)

- Quando habilitado, o resumo baixa o arquivo (PDF/ZIP etc.), converte para Markdown com Docling e chama OpenAI para gerar um resumo padronizado.
- Saídas salvas em:
  - `files/DOCLING_*.md` — Markdown completo do(s) documento(s)
  - `reports/SUMMARY_*.md` — Resumo em Markdown
- Dependência opcional: `docling` (pesada). Se não instalada, o resumo retornará mensagem de erro; o app continua funcionando.

## Histórico do usuário

- Mock de usuário fixo em `gvg_user.py` (nome/email/uid). Integração futura com autenticação.
- Se `user_prompts` e `user_results` existirem no DB, o app salva consultas e resultados:
  - `add_prompt(...)` insere e retorna `prompt_id` (com embedding do prompt opcionalmente)
  - `save_user_results(prompt_id, results)` insere rank/similaridade/valor/data por resultado

## Estilos e UX

- Estilo e cores (cards, botões, tabelas) vêm de `gvg_styles.styles`.
- Ícones via FontAwesome (por meio do Bootstrap theme referenciado).
- Cores da Data Encerramento variam por proximidade (roxo para vencidos; verde para > 30 dias).

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

## Depuração

- Ative `--debug` para imprimir SQL de busca e etapas do pipeline no console.
- Em `gvg_search_core.set_sql_debug(True)` também ativa prints internos.
- Progresso de busca é refletido no spinner central e numa barra de progresso (percent/label).

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

---

Última atualização: auto‑gerado a partir do código em 2025‑09‑02.
