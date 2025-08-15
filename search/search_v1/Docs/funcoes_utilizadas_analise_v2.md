# 📊 Análise das Funções Realmente Utilizadas - GvG_Terminal_v2_Otimizado (Prompt_v2)

## 🎯 Resumo Executivo
Esta análise lista EXATAMENTE as funções, classes e utilidades efetivamente utilizadas pelo terminal otimizado (`GvG_Search_Terminal.py`) na pasta Prompt_v2. Código redundante ou legado foi removido na refatoração; ainda assim, alguns módulos expõem funções não chamadas diretamente pelo terminal.

---

## 📁 GvG_Search_Terminal.py - Funções / Objetos Utilizados

### 🔗 Importações de `gvg_search_core`
```python
semantic_search()
keyword_search()
hybrid_search()
get_intelligent_status()
toggle_intelligent_processing()
toggle_intelligent_debug()
```

### 🔗 Importações de `gvg_ai_utils`
```python
get_embedding()              # (indireto via search_core)
get_negation_embedding()     # (indireto via search_core e uso_negation flag)
extract_pos_neg_terms()      # Para exibir prompt negativo / export filename
generate_keywords()          # Submenu geração de palavras-chave
calculate_confidence()       # (indireto via search_core retorno de confiança)
```

### 🔗 Importações de `gvg_database`
```python
create_connection()          # Indireto (search_core)
create_engine_connection()   # (Não usado no terminal atual)
fetch_documentos()           # Menu de documentos
```

### 🔗 Importações de `gvg_preprocessing`
```python
SearchQueryProcessor         # (Indireto; usado dentro de search_core via _get_processed)
process_search_query         # (Não chamado diretamente pelo terminal)
```

### 🔗 Importações de `gvg_formatters`
```python
format_currency()
format_date()
decode_poder()
decode_esfera()
```

### 🔗 Importações de `gvg_documents`
```python
summarize_document()         # (Alias para process_pncp_document; não chamado diretamente)
process_pncp_document()      # Usado em processamento de documentos
```

### 🖥️ Funções Definidas Localmente no Terminal
```python
display_header()
display_menu()
select_search_type()
select_search_approach()
select_relevance_level()     # Wrapper interno simplificado
select_sort_mode()
configure_system()
perform_search()
direct_search()
correspondence_search()      # Versão simplificada (mock categorias)
category_filtered_search()   # Versão simplificada (filtro mock)
apply_sort_mode()
display_results()
display_result_details()
highlight_key_terms()
show_process_documents()
process_documents_for_result()
show_document_links()
process_single_document()
process_all_documents()
display_document_summary()
generate_process_keywords()
_generate_keywords_for_process()
export_results()
export_results_to_excel()
export_results_to_pdf()
export_results_to_json()
generate_export_filename()
main()
```

---

## 📁 gvg_search_core.py - Funções Utilizadas pelo Terminal

### ✅ Realmente chamadas (direto ou indireto)
```python
semantic_search()
keyword_search()
hybrid_search()
get_intelligent_status()
toggle_intelligent_processing()
toggle_intelligent_debug()
calculate_confidence()   # (via import de gvg_ai_utils)
```

### ⚙️ Funções Internas de Suporte (utilizadas apenas dentro do módulo)
```python
apply_relevance_filter()
_process_relevance_response()
_prepare_relevance_payload()
_get_processed()
_get_relevance_thread() / _call_relevance_assistant() / _poll_run()
_extract_json_block()
set_relevance_filter_level()        # (Não chamado pelo terminal direto)
get_relevance_filter_status()       # (Terminal usa sua própria versão simplificada)
toggle_relevance_filter()           # (Não utilizado)
toggle_relevance_filter_debug()     # (Não utilizado)
```

### ❌ Não utilizadas externamente no Prompt_v2
- toggle_relevance_filter()
- toggle_relevance_filter_debug()
- set_relevance_filter_level() (duplicado no terminal com lógica simplificada)

---

## 📁 gvg_ai_utils.py - Funções Utilizadas
```python
get_embedding()               # Via search_core
get_negation_embedding()      # Via search_core (quando '--' na query e flag ativa)
extract_pos_neg_terms()       # Exibição + filenames exportação
generate_keywords()           # Submenu de palavras‑chave
calculate_confidence()        # Retorno consolidado de buscas
```
Nenhuma função excedente: módulo já mínimo.

---

## 📁 gvg_database.py - Funções Utilizadas
```python
create_connection()           # Chamado por search_core
fetch_documentos()            # Chamado pelo terminal
```
Funções não usadas:
```python
create_engine_connection()    # Mantida para futura expansão (exportações avançadas)
```

---

## 📁 gvg_preprocessing.py - Utilização
```python
SearchQueryProcessor.process_query()  # Indireto via search_core._get_processed()
process_search_query()                # Não usado diretamente
```
Outras funções internas (`_wait_for_response`, `_parse_response`) são encapsuladas pela classe.

---

## 📁 gvg_documents.py - Funções Utilizadas
```python
process_pncp_document()       # Chamada para cada documento (Nº/A)
create_safe_filename()        # Usada internamente (save_* helpers)
download_document()
convert_document_to_markdown()
save_markdown_file()
save_summary_file()
generate_document_summary()
```
`summarize_document()` é apenas alias para `process_pncp_document` (não chamado diretamente).

---

## 📁 gvg_formatters.py - Funções Utilizadas
```python
format_currency()
format_date()
decode_poder()
decode_esfera()
```

---

## 📊 Estatísticas de Utilização (Prompt_v2)
| Categoria | Funções Usadas | Observações |
|-----------|---------------|-------------|
| Busca Core | 3 públicas principais | Semântica / Keyword / Híbrida |
| Inteligência (flags) | 3 | Status + toggles |
| Pré-processamento | 1 classe principal | Sempre indireto |
| Formatação | 4 | Alta frequência em exibições/export |
| Documentos | 7 núcleo | Pipeline Docling completo |
| Palavras‑chave | 1 | OpenAI gpt-3.5-turbo |
| Exportações | 3 | Excel/PDF/JSON |

Total funções expostas relevantes: ~21 (excluindo helpers internos encapsulados)

---

## 🔍 Principais Chamadas por Fluxo
1. Busca: perform_search → direct_search → semantic/keyword/hybrid → (pré-processamento + embeddings + SQL) → display_results
2. Documentos: show_process_documents → process_documents_for_result → process_pncp_document → Docling + summary
3. Keywords: generate_process_keywords → generate_keywords
4. Export: export_results → export_results_to_{excel|pdf|json}

---

## ⚡ Reduções vs v9
| Área | v9 | Prompt_v2 |
|------|----|-----------|
| Import style | wildcard * | seletivo explícito |
| Filtro Relevância | Arquivo monolítico v3 | Embutido no search_core simplificado |
| Categorias | Cálculo real | Mock/placeholders (pode ser reintroduzido) |
| Document Processor | v2/v3 alternáveis | Só Docling v3 completo |
| Funções não usadas | Muitas (50%+) | Mínimas (quase todas usadas) |

---

## 🚩 Oportunidades Futuras
- Reintroduzir categorização real (se necessário) em módulo dedicado.
- Isolar filtro de relevância em `relevance_filter.py` para clareza.
- Adicionar testes unitários básicos para: highlight_key_terms, generate_export_filename, _get_processed.
- Parametrizar caminhos de saída de documentos (hoje hardcoded em `gvg_documents`).

---

## 📝 Conclusão
A versão otimizada elimina o inchaço estrutural: cada módulo contém apenas o essencial para a experiência completa (busca + inteligência + documentos + export). O mapa acima reflete 100% das dependências reais do terminal no estado atual do Prompt_v2.
