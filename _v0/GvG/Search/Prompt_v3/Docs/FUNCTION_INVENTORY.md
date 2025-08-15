# GvG Prompt_v2 Function Inventory

Gerado automaticamente.

## Convenção
- `gvg_*.py`: módulos núcleo utilitários/engine (lowercase) – funções atômicas ou de baixo nível.
- `GvG_*.py`: camadas de orquestração / interface (Prompt, Function, Terminal) – combinam e coordenam módulos núcleo.

---
## 1. Módulos núcleo (`gvg_*.py`)

### gvg_ai_utils.py
Funções relacionadas a embeddings, negação e geração de palavras‑chave.
- get_embedding(text): Retorna embedding vetorial usando provedor configurado.
- _has_negation_markers(text): Detecta presença de marcadores de negação simples (heurística).
- extract_pos_neg_terms(query): Separa termos positivos e negativos da consulta (prompt negativo) via LLM + fallback.
- get_negation_embedding(pos_terms, neg_terms): Calcula embedding resultante subtraindo vetor médio negativo do positivo.
- has_negation(text): Interface pública para checar se há negação (wrapper de heurística/LLM).
- generate_keywords(text, max_keywords=15): Extrai conjunto de keywords relevantes com LLM; fallback simplista se falhar.
- calculate_confidence(results): Calcula confiança média percentual baseada em similaridades dos resultados.

### gvg_categories.py (REMOVIDO NA v3 - lógica integrada em gvg_search_core)
Funções para categorização, correspondência e filtragem baseada em categorias (agora incorporadas diretamente no `gvg_search_core.py` via: `get_top_categories_for_query`, `correspondence_search`, `category_filtered_search`).
- get_top_categories_for_query(query_text, top_n, use_negation, search_type, console=None): Retorna lista ranqueada de categorias mais similares ao texto.
- _calculate_correspondence_similarity_score(result, category): Score combinado entre resultado e categoria para priorização.
- _find_top_category_for_result(result, categories): Localiza melhor categoria para um resultado individual.
- correspondence_search(query_text, top_categories, limit, filter_expired, console=None): Busca baseada em pivot de categorias (expande por categorias e depois mapeia resultados).
- category_filtered_search(query_text, search_type, top_categories, limit, filter_expired, use_negation, console=None): Busca universo + filtragem por categorias identificadas relevantes.

### gvg_database.py
Conectividade e acesso a dados de processos/documentos PNCP.
- create_connection(): Cria conexão psycopg2 (modo simples) para leitura.
- create_engine_connection(): Cria engine SQLAlchemy (lazy) para operações mais avançadas.
- _parse_numero_controle_pncp(raw): Normaliza número de controle para formato consistente.
- fetch_documentos(numero_controle): Recupera metadados de documentos (DB ou fallback API/local) para um processo.

### gvg_documents.py
Pipeline de download, extração e sumarização de documentos.
- load_openai_config(): Carrega/valida credenciais OpenAI do ambiente.
- setup_openai(): Inicializa cliente / configs de OpenAI.
- create_files_directory(base_path): Garante diretório base para arquivos baixados.
- download_document(url, document_name): Faz download binário do documento e retorna caminho temporário.
- convert_document_to_markdown(path): Usa mecanismo (Docling/convert) para converter para texto/markdown unificado.
- save_markdown_file(markdown_text, base_filename, output_dir): Persiste markdown extraído.
- save_summary_file(summary_text, base_filename, output_dir): Persiste resumo em arquivo .summary.txt.
- generate_document_summary(markdown_text, metadata): Usa LLM para gerar resumo estruturado.
- cleanup_temp_file(path): Remove arquivo temporário com segurança.
- detect_file_type_by_content_v3(binary_head): Detecta tipo de arquivo por assinatura (fallback ao nome).
- is_zip_file(path): Verifica se arquivo é ZIP válido.
- extract_all_supported_files_from_zip(zip_path, work_dir): Extrai todos os arquivos suportados de um ZIP.
- extract_first_pdf_from_zip(zip_path, work_dir): Extrai primeiro PDF para processamento rápido.
- process_pncp_document(url, document_name, pncp_data=None): Pipeline completo (download -> extração -> resumo) retornando texto resumido.
- summarize_document(text): Função de alto nível para gerar resumo isolado.
- create_safe_filename(name): Sanitiza nome para uso em disco.

### gvg_formatters.py (REMOVIDO NA v3 - formatters migrados para gvg_preprocessing)
Formatação de campos e decodificação de códigos.
- format_currency(value): Formata número em moeda brasileira (com fallbacks) como string.
- format_date(value): Normaliza várias representações de data para dd/mm/yyyy ou retorna original/N/A.
- decode_poder(poder_id): Decodifica id de poder (Executivo, Legislativo, etc.).
- decode_esfera(esfera_id): Decodifica id de esfera administrativa.

### gvg_preprocessing.py
Processamento inteligente de query (decomposição, limpeza, extração de termos base) via assistente.
- get_preprocessing_thread(): Obtém ou cria thread de processamento (estado persistido em LLM).
- class SearchQueryProcessor: Encapsula lógica de processamento assistido.
  - process_query(query): Retorna dict com termos de busca normalizados e metadados.
  - _wait_for_response(run_id, thread_id, timeout): Polling até conclusão do assistente.
  - _parse_response(text): Extrai estrutura JSON da resposta textual do assistente.
- process_search_query(query): Função procedural simplificada que instância SearchQueryProcessor.

### gvg_search_core.py
Engine de busca e filtros de relevância + toggles inteligentes.
Relevância / Assistente:
- _get_current_assistant_id(): Recupera ID do assistente de relevância configurado.
- _get_relevance_thread(): Garante thread de relevância (cache).
- _poll_run(client, thread_id, run_id, timeout): Polling de execução de run.
- _call_relevance_assistant(payload, debug): Executa assistente de relevância e retorna resposta bruta.
- _extract_json_block(text): Extrai bloco JSON válido de texto multi-formato.
- _prepare_relevance_payload(results, level): Monta payload de entrada para filtragem de relevância.
- _process_relevance_response(results, response_json): Aplica marcas/filtragem aos resultados originais.
Funções públicas de relevância:
- apply_relevance_filter(results, level, debug): Aplica filtro (níveis) retornando subset anotado.
- set_relevance_filter_level(level): Ajusta nível global (1-3).
- toggle_relevance_filter(enable: bool): Liga/desliga filtro mantendo nível.
- get_relevance_filter_status(): Retorna dict com ativo/nivel/debug.
- toggle_relevance_filter_debug(enable: bool): Liga debug interno do filtro.
Busca / Query processing:
- _safe_close(conn): Fecha conexão sem exceção.
- _get_processed(query): Retorna (talvez cache) de processamento inteligente para query.
- _ensure_vector_cast(sql): Ajusta SQL para casting pgvector adequado.
- semantic_search(query, limit, filter_expired, use_negation): Busca vetorial com embeddings (negation opcional).
- keyword_search(query, limit, filter_expired): Busca texto bruto (ILIKE / TS query).
- hybrid_search(query, limit, filter_expired, use_negation): Combina semantic + keyword com pesos.
Intelligent toggles:
- toggle_intelligent_processing(enable: bool): Ativa/desativa modo de processamento inteligente global.
- toggle_intelligent_debug(enable: bool): Ativa debug do pipeline inteligente.
- get_intelligent_status(): Retorna dict {intelligent_processing, debug_mode}.

### gvg_utils.py (REMOVIDO NA v3 - funções consolidadas em gvg_search_core, gvg_preprocessing, gvg_ai_utils, gvg_exporters)
Aglutina funções utilitárias e wrappers de configuração.
- set_relevance_filter_level(level): Reexport do core.
- get_relevance_filter_status(): Reexport status do filtro relevância.
- get_module_info(): Retorna metadados (quantidade de funções, versão, etc.) para diagnósticos.

---
## 2. Módulos de orquestração (`GvG_*.py`)

### GvG_Search_Prompt.py
Execução única via linha de comando (batch). Coordena fluxo 6 etapas, logging e exportações.
- setup_logging(output_dir, query): Configura logger e arquivo de log.
- generate_export_filename(query, search_type, approach, relevance, order, intelligent_enabled, output_dir, extension): Nome padronizado de export.
- export_results_json(results, query, params, output_dir): Serializa resultados em JSON + metadados.
- export_results_excel(results, query, params, output_dir): Gera planilha Excel com colunas principais.
- export_results_pdf(results, query, params, output_dir): (Opcional) Relatório PDF resumido.
- sort_results(results, order_mode): Ordena resultados por similaridade, data ou valor.
- perform_search(params, logger, console=None): Pipeline principal (config -> categorias -> busca -> ordenação).
- _direct_search(query, params): Chama função de busca base conforme tipo.
- _correspondence_search(query, params, categories, console=None): Orquestra busca por correspondência categórica.
- _category_filtered_search(query, params, categories, console=None): Orquestra busca filtrada por categorias.
- _log_categories_table(logger, categories): Log formatado das TOP categorias.
- _print_summary(console, results, categories, params, confidence, elapsed, query): Impressão rica (tabelas) resumo.
- parse_args(): Define argumentos CLI (com short forms).
- main(): Ponto de entrada CLI.

### GvG_Search_Function.py
Interface programática (função gvg_search) para uso embutido em outros scripts/serviços.
- _setup_logging(output_dir, query): Similar ao prompt.
- _generate_export_filename(...): Igual, para função.
- _export_json(results, query, params, output_dir): Exportação JSON.
- _export_xlsx(results, query, params, output_dir): Exportação XLSX.
- _export_pdf(results, query, params, output_dir): Exportação PDF (se disponível).
- _sort_results(results, order_mode): Ordenação.
- _direct_search(query, params): Busca direta.
- _correspondence_search(query, params, categories, console=None): Correspondência.
- _category_filtered_search(query, params, categories, console=None): Filtro categórico.
- gvg_search(...): Função pública principal retornando dict estruturado.
- _print_summary(...): Impressão rica opcional (debug) com tabelas e caminhos export.

### GvG_Search_Terminal.py
Interface interativa (loop menus) para exploração iterativa e processamento de documentos.
Principais grupos de funções:
Interface / Menu:
- display_header(), display_menu(), select_search_type(), select_search_approach(), select_relevance_level(), select_sort_mode(), configure_system()
Busca e Categorias:
- perform_search(query), direct_search(query), correspondence_search(query, categories), category_filtered_search(query, categories), _display_top_categories_table(categories), apply_sort_mode(results)
Exibição:
- display_results(results, query), display_result_details(result, position, query), highlight_key_terms(text, query_terms, max_length)
Documentos:
- show_process_documents(), process_documents_for_result(result), process_single_document(documento, pncp_data=None), process_all_documents(documentos, pncp_data=None), display_document_summary(result,...), _build_pncp_data(details), show_document_links(documentos)
Palavras‑chave:
- generate_process_keywords(), _generate_keywords_for_process(process_number)
Exportação:
- export_results(), export_results_to_excel(), export_results_to_pdf(), export_results_to_json(), generate_export_filename(extension)
Loop principal:
- main()

---
## 3. Relações e Fluxo
1. Orquestração chama search_core (semantic/keyword/hybrid) e opcionalmente categorias (correspondence / filtered).
2. search_core pode acionar processamento inteligente (preprocessing) e filtro de relevância (assistente LLM).
3. Negation embeddings aplicados em semantic/hybrid via ai_utils.
4. Export layers usam formatters para moeda/data e seguem padrão de nomenclatura compartilhado.
5. Terminal adiciona camada de persistência de contexto (última busca) + processamento de documentos (documents.py).

---
## 4. Notas de Manutenção
- Ao adicionar novo tipo de busca, manter sincronia em: SEARCH_TYPES (Prompt/Function/Terminal) + dispatcher (_direct_search / hybrid etc.).
- Extensões de export precisam atualizar ambos Prompt e Function (e Terminal se desejado) garantindo pattern nominal.
- Filtro de relevância centralizado em gvg_search_core: evite duplicar estado em camadas superiores.
- Preprocessing: caso mude formato de retorno do assistente, ajustar _parse_response em gvg_preprocessing e acessos em orquestração.
- Documentos: pipeline Docling modular; cuidado com formatos adicionais (ZIP com múltiplos PDFs) – atualizar funções de extração.

---
## 5. Resumo Rápido (Cheat Sheet)
Search Types: 1=Semântica 2=Palavras-chave 3=Híbrida
Approaches: 1=Direta 2=Correspondência (categoria pivot) 3=Filtro (universo + filtra por categoria)
Relevância: 1=Sem filtro 2=Flexível 3=Restritivo (assistente LLM pós-busca)
Negation Embeddings: Extrai termos negativos e ajusta vetor semântico (subtração de centróide negativo).
Intelligent Processing: Decompõe query em termos base e condições SQL para expandir recall com controle.

---
Gerado em tempo de execução.
