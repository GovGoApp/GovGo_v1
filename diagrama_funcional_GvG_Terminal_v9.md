# 📊 Diagrama Funcional Completo - GvG_Terminal_v9

## 🎯 Visão Geral do Sistema

O **GvG_Terminal_v9** é um sistema avançado de busca para contratos públicos PNCP com três abordagens distintas de busca e processamento inteligente via IA.

---

## 🏗️ Arquitetura do Sistema

```mermaid
graph TB
    subgraph "MAIN MODULE"
        M[GvG_SP_Search_Terminal_v9.py]
    end
    
    subgraph "CORE MODULES"
        U3[gvg_search_utils_v3.py]
        U2[gvg_search_utils_v2.py - Fallback]
        PP[gvg_pre_processing_v3.py]
        D3[gvg_document_utils_v3_o.py]
        D2[gvg_document_utils_v2.py - Fallback]
    end
    
    subgraph "EXTERNAL APIS"
        OAI[OpenAI API]
        SUP[Supabase PostgreSQL + pgvector]
    end
    
    subgraph "EXTERNAL LIBS"
        RICH[Rich Console]
        PDF[ReportLab]
        PANDAS[Pandas]
        SQLALCHEMY[SQLAlchemy]
    end
    
    M --> U3
    M --> D3
    U3 --> U2
    U3 --> PP
    D3 --> D2
    U3 --> OAI
    U3 --> SUP
    M --> RICH
    M --> PDF
    M --> PANDAS
    M --> SQLALCHEMY
```

---

## 🔄 Fluxo Principal de Execução

### 1️⃣ **Inicialização do Sistema**

```mermaid
graph TD
    START([INÍCIO]) --> IMPORT[Importar Módulos]
    IMPORT --> CHECK_V3{gvg_search_utils_v3<br/>disponível?}
    CHECK_V3 -->|Sim| LOAD_V3[Carregar Sistema v3]
    CHECK_V3 -->|Não| EXIT[EXIT - Sistema v3 Obrigatório]
    LOAD_V3 --> DOC_CONFIG[Configurar Processador<br/>de Documentos]
    DOC_CONFIG --> DOC_V3{USE_DOCLING_V3?}
    DOC_V3 -->|Sim| LOAD_DOCLING[Carregar Docling v3]
    DOC_V3 -->|Não| LOAD_MARKITDOWN[Carregar MarkItDown v2]
    LOAD_DOCLING --> CONSOLE[Configurar Rich Console]
    LOAD_MARKITDOWN --> CONSOLE
    CONSOLE --> MAIN_LOOP[Entrar no Loop Principal]
```

### 2️⃣ **Loop Principal do Menu**

```mermaid
graph TD
    MENU[Exibir Menu Principal] --> INPUT[Aguardar Input Usuário]
    INPUT --> OPTION{Opção Escolhida}
    
    OPTION -->|1| SELECT_TYPE[Selecionar Tipo de Busca]
    OPTION -->|2| SELECT_APPROACH[Selecionar Abordagem]
    OPTION -->|3| SELECT_RELEVANCE[Selecionar Relevância]
    OPTION -->|4| SELECT_SORT[Selecionar Ordenação]
    OPTION -->|5| CONFIG_SYSTEM[Configurações do Sistema]
    OPTION -->|6| SHOW_DOCS[Ver Documentos - se há resultados]
    OPTION -->|7| GEN_KEYWORDS[Gerar Palavras-chave - se há resultados]
    OPTION -->|8| EXPORT[Exportar Resultados - se há resultados]
    OPTION -->|Texto| PERFORM_SEARCH[Executar Busca]
    OPTION -->|quit/exit/q| END([FIM])
    
    SELECT_TYPE --> MENU
    SELECT_APPROACH --> MENU
    SELECT_RELEVANCE --> MENU
    SELECT_SORT --> MENU
    CONFIG_SYSTEM --> MENU
    SHOW_DOCS --> MENU
    GEN_KEYWORDS --> MENU
    EXPORT --> MENU
    PERFORM_SEARCH --> MENU
```

---

## 🔍 Sistema de Busca - Três Abordagens

### **Fluxo Geral de Busca**

```mermaid
graph TD
    START_SEARCH[perform_search] --> INTELLIGENT{Processamento<br/>Inteligente<br/>Ativo?}
    
    INTELLIGENT -->|Sim| PREPROCESS[Processamento Inteligente<br/>- Separar termos e condições SQL<br/>- via gvg_pre_processing_v3]
    INTELLIGENT -->|Não| USE_ORIGINAL[Usar Query Original]
    
    PREPROCESS --> PROCESSED_QUERY[Query Processada]
    USE_ORIGINAL --> ORIGINAL_QUERY[Query Original]
    
    PROCESSED_QUERY --> CHECK_APPROACH{Qual Abordagem?}
    ORIGINAL_QUERY --> CHECK_APPROACH
    
    CHECK_APPROACH -->|1| DIRECT_APPROACH[ABORDAGEM DIRETA]
    CHECK_APPROACH -->|2| CORRESPONDENCE_APPROACH[ABORDAGEM CORRESPONDÊNCIA]
    CHECK_APPROACH -->|3| FILTER_APPROACH[ABORDAGEM FILTRO]
    
    DIRECT_APPROACH --> APPLY_SORT[Aplicar Ordenação]
    CORRESPONDENCE_APPROACH --> APPLY_SORT
    FILTER_APPROACH --> APPLY_SORT
    
    APPLY_SORT --> DISPLAY_RESULTS[Exibir Resultados]
```

### **1️⃣ ABORDAGEM DIRETA**

```mermaid
graph TD
    DIRECT[direct_search] --> CHECK_TYPE{Tipo de Busca}
    
    CHECK_TYPE -->|1| SEMANTIC[semantic_search<br/>via gvg_search_utils_v3]
    CHECK_TYPE -->|2| KEYWORD[keyword_search<br/>via gvg_search_utils_v3]
    CHECK_TYPE -->|3| HYBRID[hybrid_search<br/>via gvg_search_utils_v3]
    
    SEMANTIC --> NEGATION{use_negation_<br/>embeddings?}
    HYBRID --> NEGATION
    
    NEGATION -->|Sim| NEG_EMBED[get_negation_embedding]
    NEGATION -->|Não| NORMAL_EMBED[get_embedding]
    
    NEG_EMBED --> DB_SEARCH[Busca no Banco<br/>via Supabase]
    NORMAL_EMBED --> DB_SEARCH
    KEYWORD --> DB_SEARCH
    
    DB_SEARCH --> RELEVANCE_FILTER{Filtro de<br/>Relevância<br/>Ativo?}
    
    RELEVANCE_FILTER -->|Sim| APPLY_AI_FILTER[Aplicar Filtro IA<br/>via OpenAI Assistant]
    RELEVANCE_FILTER -->|Não| RESULTS[Retornar Resultados]
    
    APPLY_AI_FILTER --> RESULTS
```

### **2️⃣ ABORDAGEM CORRESPONDÊNCIA**

```mermaid
graph TD
    CORRESP[correspondence_search] --> GET_CATS[get_top_categories_for_query<br/>Buscar TOP N Categorias]
    GET_CATS --> EMBED_QUERY[Embeddar Query<br/>para Categorias]
    
    EMBED_QUERY --> NEG_CHECK{use_negation_embeddings<br/>& busca semântica?}
    NEG_CHECK -->|Sim| NEG_EMBED[get_negation_embedding]
    NEG_CHECK -->|Não| NORMAL_EMBED[get_embedding]
    
    NEG_EMBED --> SIMILARITY_SEARCH[Busca por Similaridade<br/>na tabela 'categorias']
    NORMAL_EMBED --> SIMILARITY_SEARCH
    
    SIMILARITY_SEARCH --> TOP_CATS[Lista TOP N Categorias<br/>com Scores]
    TOP_CATS --> DISPLAY_CATS[display_top_categories_table]
    
    DISPLAY_CATS --> INTEL_PROC{Processamento<br/>Inteligente<br/>Ativo?}
    
    INTEL_PROC -->|Sim| EXTRACT_SQL[Extrair Condições SQL<br/>via gvg_pre_processing_v3]
    INTEL_PROC -->|Não| NO_SQL[Sem Condições SQL]
    
    EXTRACT_SQL --> CATEGORY_SEARCH[Busca por Categorias<br/>+ Condições SQL]
    NO_SQL --> CATEGORY_SEARCH
    
    CATEGORY_SEARCH --> CALC_CORRESP[calculate_correspondence_<br/>similarity_score<br/>Multiplicação de Similarities]
    
    CALC_CORRESP --> FIND_TOP_CAT[find_top_category_for_result<br/>Categoria mais importante]
    FIND_TOP_CAT --> SORT_RESULTS[Ordenar por Score<br/>de Correspondência]
    SORT_RESULTS --> RETURN_RESULTS[Retornar Resultados<br/>Formatados]
```

### **3️⃣ ABORDAGEM FILTRO**

```mermaid
graph TD
    FILTER[category_filtered_search] --> GET_CATS_F[get_top_categories_for_query<br/>Buscar TOP N Categorias]
    
    GET_CATS_F --> TRADICIONAL[Executar Busca Tradicional<br/>limit * 3 resultados]
    
    TRADICIONAL --> TYPE_CHECK{Tipo de Busca}
    
    TYPE_CHECK -->|1| SEM_TRAD[semantic_search tradicional]
    TYPE_CHECK -->|2| KEY_TRAD[keyword_search tradicional]
    TYPE_CHECK -->|3| HYB_TRAD[hybrid_search tradicional]
    
    SEM_TRAD --> ALL_RESULTS[Todos os Resultados<br/>da Busca Tradicional]
    KEY_TRAD --> ALL_RESULTS
    HYB_TRAD --> ALL_RESULTS
    
    ALL_RESULTS --> GET_CATEGORIES[Buscar Categorias<br/>dos Resultados<br/>tabela 'contratacoes_embeddings']
    
    GET_CATEGORIES --> FILTER_BY_CATS[Filtrar Resultados<br/>que tenham pelo menos<br/>1 categoria relevante]
    
    FILTER_BY_CATS --> UPDATE_RANKS[Atualizar Ranks<br/>após Filtragem]
    
    UPDATE_RANKS --> ADD_METADATA[Adicionar Metadados<br/>matched_categories<br/>filtered_universe_size]
    
    ADD_METADATA --> RETURN_FILTERED[Retornar Resultados<br/>Filtrados]
```

---

## 🤖 Sistema de Processamento Inteligente

### **Preprocessamento de Queries**

```mermaid
graph TD
    QUERY[Query do Usuário] --> INTEL_CHECK{Processamento<br/>Inteligente<br/>Ativo?}
    
    INTEL_CHECK -->|Sim| IMPORT_PREP[Importar<br/>gvg_pre_processing_v3]
    INTEL_CHECK -->|Não| SKIP_PREP[Usar Query Original]
    
    IMPORT_PREP --> CREATE_PROCESSOR[SearchQueryProcessor()]
    CREATE_PROCESSOR --> PROCESS_QUERY[process_query]
    
    PROCESS_QUERY --> OPENAI_CALL[Chamada para<br/>OpenAI Assistant]
    
    OPENAI_CALL --> SEPARATE[Separar:<br/>- search_terms<br/>- sql_conditions<br/>- explanation]
    
    SEPARATE --> PROCESSED[Query Processada]
    
    SKIP_PREP --> ORIGINAL[Query Original]
    
    PROCESSED --> RETURN_PROCESSED[Retornar Termos<br/>Processados]
    ORIGINAL --> RETURN_PROCESSED
```

### **Sistema de Filtro de Relevância**

```mermaid
graph TD
    RESULTS[Resultados da Busca] --> REL_CHECK{Filtro de<br/>Relevância<br/>Ativo?}
    
    REL_CHECK -->|Não| NO_FILTER[Retornar Resultados<br/>Sem Filtro]
    REL_CHECK -->|Sim| CHECK_LEVEL{Nível do Filtro}
    
    CHECK_LEVEL -->|1| NO_FILTER
    CHECK_LEVEL -->|2| FLEXIBLE[Filtro Flexível<br/>Assistant ID:<br/>asst_tfD5oQxSgoGhtqdKQHK9UwRi]
    CHECK_LEVEL -->|3| RESTRICTIVE[Filtro Restritivo<br/>Assistant ID:<br/>asst_XmsefQEKbuVWu51uNST7kpYT]
    
    FLEXIBLE --> THREAD_FLEX[Criar/Usar Thread<br/>para Filtro Flexível]
    RESTRICTIVE --> THREAD_REST[Criar/Usar Thread<br/>para Filtro Restritivo]
    
    THREAD_FLEX --> SEND_MSG_FLEX[Enviar Mensagem:<br/>Query + Descrições]
    THREAD_REST --> SEND_MSG_REST[Enviar Mensagem:<br/>Query + Descrições]
    
    SEND_MSG_FLEX --> AI_ANALYSIS[Análise IA:<br/>Relevância dos Contratos]
    SEND_MSG_REST --> AI_ANALYSIS
    
    AI_ANALYSIS --> FILTER_RESULTS[Filtrar Resultados<br/>baseado na Resposta IA]
    
    FILTER_RESULTS --> FILTERED[Resultados Filtrados<br/>por IA]
```

---

## 📄 Sistema de Documentos

### **Visualização e Processamento de Documentos**

```mermaid
graph TD
    SELECT_PROC[Selecionar Processo] --> EXTRACT_PNCP[extract_pncp_data<br/>Extrair dados básicos]
    
    EXTRACT_PNCP --> FETCH_DOCS[fetch_documentos<br/>via gvg_search_utils_v3]
    
    FETCH_DOCS --> DOCS_FOUND{Documentos<br/>Encontrados?}
    
    DOCS_FOUND -->|Não| NO_DOCS[Nenhum documento<br/>encontrado]
    DOCS_FOUND -->|Sim| SHOW_LIST[Mostrar Lista<br/>de Documentos]
    
    SHOW_LIST --> USER_CHOICE{Escolha do Usuário}
    
    USER_CHOICE -->|V| VIEW_LINKS[Apenas Ver Links]
    USER_CHOICE -->|A| PROCESS_ALL[Processar TODOS]
    USER_CHOICE -->|Número| PROCESS_ONE[Processar UM]
    USER_CHOICE -->|Q| QUIT_DOCS[Voltar ao Menu]
    
    PROCESS_ALL --> LOOP_DOCS[Loop por Todos<br/>os Documentos]
    PROCESS_ONE --> SINGLE_DOC[Documento<br/>Selecionado]
    
    LOOP_DOCS --> DOC_PROCESSOR[Processador de<br/>Documentos]
    SINGLE_DOC --> DOC_PROCESSOR
    
    DOC_PROCESSOR --> DOC_VERSION{Versão do<br/>Processador}
    
    DOC_VERSION -->|v3| DOCLING[summarize_document<br/>via gvg_document_utils_v3_o<br/>Docling + Extração Tabelas]
    DOC_VERSION -->|v2| MARKITDOWN[summarize_document<br/>via gvg_document_utils_v2<br/>MarkItDown + OpenAI]
    
    DOCLING --> SUMMARY[Resumo/Análise<br/>do Documento]
    MARKITDOWN --> SUMMARY
    
    SUMMARY --> DISPLAY_SUMMARY[Exibir Resumo]
```

### **Geração de Palavras-chave**

```mermaid
graph TD
    SELECT_PROC_KW[Selecionar Processo] --> GET_DESC[Obter Descrição<br/>do Processo]
    
    GET_DESC --> DESC_FOUND{Descrição<br/>Disponível?}
    
    DESC_FOUND -->|Não| NO_DESC[Descrição não<br/>disponível]
    DESC_FOUND -->|Sim| GEN_KW[generate_keywords<br/>via gvg_search_utils_v3]
    
    GEN_KW --> OPENAI_KW[Chamada OpenAI<br/>para Gerar<br/>Palavras-chave]
    
    OPENAI_KW --> KEYWORDS[Lista de<br/>Palavras-chave<br/>Inteligentes]
    
    KEYWORDS --> DISPLAY_KW[Exibir<br/>Palavras-chave]
```

---

## 📊 Sistema de Exportação

### **Fluxo de Exportação**

```mermaid
graph TD
    EXPORT_START[export_results] --> HAS_RESULTS{Há Resultados<br/>para Exportar?}
    
    HAS_RESULTS -->|Não| NO_EXPORT[Nenhum resultado<br/>para exportar]
    HAS_RESULTS -->|Sim| CHOOSE_FORMAT[Escolher Formato<br/>1-Excel, 2-PDF, 3-JSON]
    
    CHOOSE_FORMAT -->|1| EXCEL[export_results_to_excel]
    CHOOSE_FORMAT -->|2| PDF[export_results_to_pdf]
    CHOOSE_FORMAT -->|3| JSON[export_results_to_json]
    
    EXCEL --> GEN_FILENAME_XL[generate_export_filename<br/>Busca_{QUERY}_S{type}_A{approach}_R{relevance}_O{sort}_I{intelligent}_{timestamp}.xlsx]
    PDF --> GEN_FILENAME_PDF[generate_export_filename<br/>Busca_{QUERY}_S{type}_A{approach}_R{relevance}_O{sort}_I{intelligent}_{timestamp}.pdf]
    JSON --> GEN_FILENAME_JSON[generate_export_filename<br/>Busca_{QUERY}_S{type}_A{approach}_R{relevance}_O{sort}_I{intelligent}_{timestamp}.json]
    
    GEN_FILENAME_XL --> PANDAS_DF[Criar DataFrame<br/>com Pandas]
    GEN_FILENAME_PDF --> REPORTLAB[Usar ReportLab<br/>para PDF]
    GEN_FILENAME_JSON --> JSON_FORMAT[Formatação JSON<br/>com Metadados]
    
    PANDAS_DF --> SAVE_EXCEL[Salvar .xlsx<br/>via openpyxl]
    REPORTLAB --> SAVE_PDF[Salvar .pdf<br/>com Tabelas e<br/>Detalhes Formatados]
    JSON_FORMAT --> SAVE_JSON[Salvar .json<br/>com encoding UTF-8]
    
    SAVE_EXCEL --> SUCCESS[Exportação<br/>Concluída]
    SAVE_PDF --> SUCCESS
    SAVE_JSON --> SUCCESS
```

---

## 🎛️ Sistema de Configuração

### **Configurações do Sistema**

```mermaid
graph TD
    CONFIG[configure_system] --> CONFIG_MENU[Menu de Configurações]
    
    CONFIG_MENU --> OPTION_CONFIG{Opção Escolhida}
    
    OPTION_CONFIG -->|1| MAX_RESULTS[Alterar Número Máximo<br/>de Resultados]
    OPTION_CONFIG -->|2| TOP_CATS[Alterar Número<br/>TOP Categorias]
    OPTION_CONFIG -->|3| DOC_PROCESSOR[toggle_document_processor<br/>Alternar v3↔v2]
    OPTION_CONFIG -->|4| FILTER_EXPIRED[toggle_filter<br/>Alternar Filtro Expirados]
    OPTION_CONFIG -->|5| NEGATION[toggle_negation_embeddings<br/>Alternar Prompt Negativo]
    OPTION_CONFIG -->|6| INTELLIGENT[toggle_intelligent_processing<br/>Alternar Processamento IA]
    OPTION_CONFIG -->|7| DEBUG[toggle_intelligent_debug<br/>Alternar Debug IA]
    OPTION_CONFIG -->|8| BACK[Voltar ao Menu]
    
    DOC_PROCESSOR --> RELOAD_MODULES[Recarregar Módulos<br/>de Documentos]
    
    RELOAD_MODULES --> DOC_V3_CHECK{USE_DOCLING_V3}
    
    DOC_V3_CHECK -->|True| LOAD_V3[Carregar<br/>gvg_document_utils_v3_o]
    DOC_V3_CHECK -->|False| LOAD_V2[Carregar<br/>gvg_document_utils_v2]
    
    LOAD_V3 --> DOCLING_ACTIVE[Docling v3 Ativo]
    LOAD_V2 --> MARKITDOWN_ACTIVE[MarkItDown v2 Ativo]
    
    INTELLIGENT --> TOGGLE_INTEL[toggle_intelligent_processing<br/>via gvg_search_utils_v3]
    
    TOGGLE_INTEL --> UPDATE_GLOBAL[Atualizar Flag Global<br/>ENABLE_INTELLIGENT_PROCESSING]
```

### **Seleção de Configurações de Busca**

```mermaid
graph TD
    SEARCH_CONFIG[Configurações de Busca] --> TYPE_SELECT[select_search_type<br/>1-Semântica, 2-Palavras-chave, 3-Híbrida]
    
    SEARCH_CONFIG --> APPROACH_SELECT[select_search_approach<br/>1-Direta, 2-Correspondência, 3-Filtro]
    
    SEARCH_CONFIG --> RELEVANCE_SELECT[select_relevance_level<br/>1-Sem filtro, 2-Flexível, 3-Restritivo]
    
    SEARCH_CONFIG --> SORT_SELECT[select_sort_mode<br/>1-Similaridade, 2-Data, 3-Valor]
    
    TYPE_SELECT --> UPDATE_GLOBAL_TYPE[Atualizar<br/>current_search_type]
    APPROACH_SELECT --> UPDATE_GLOBAL_APPROACH[Atualizar<br/>current_search_approach]
    RELEVANCE_SELECT --> UPDATE_RELEVANCE[set_relevance_filter_level<br/>via gvg_search_utils_v3]
    SORT_SELECT --> UPDATE_GLOBAL_SORT[Atualizar<br/>current_sort_mode]
```

---

## 💾 Sistema de Banco de Dados

### **Conexões e Engines**

```mermaid
graph TD
    DB_CONNECTION[Conexão com Banco] --> TWO_ENGINES[Dois Tipos de Engine]
    
    TWO_ENGINES --> PSYCOPG[create_connection<br/>via gvg_search_utils_v3<br/>psycopg2 direto]
    
    TWO_ENGINES --> SQLALCHEMY[create_engine_connection<br/>SQLAlchemy Engine<br/>para Pandas]
    
    PSYCOPG --> ENV_FILE[Carregar supabase_v0.env]
    SQLALCHEMY --> ENV_FILE
    
    ENV_FILE --> CREDENTIALS[host, dbname, user, password, port]
    
    CREDENTIALS --> SUPABASE[Supabase PostgreSQL<br/>+ pgvector Extension]
    
    SUPABASE --> TABLES[Tabelas Principais]
    
    TABLES --> CONTRATACOES[contratacoes<br/>Dados dos Contratos]
    TABLES --> EMBEDDINGS[contratacoes_embeddings<br/>Embeddings + Categorias]
    TABLES --> CATEGORIAS[categorias<br/>Sistema de Categorização]
```

### **Operações de Busca no Banco**

```mermaid
graph TD
    SEARCH_DB[Busca no Banco] --> VECTOR_SEARCH[Busca Vetorial<br/>pgvector]
    
    VECTOR_SEARCH --> COSINE_SIM[Similaridade Coseno<br/><=> operator]
    
    COSINE_SIM --> EMBEDDING_TYPES[Tipos de Embedding]
    
    EMBEDDING_TYPES --> NORMAL[get_embedding<br/>OpenAI text-embedding-3-small]
    EMBEDDING_TYPES --> NEGATION[get_negation_embedding<br/>Processamento de<br/>Termos Positivos/Negativos]
    
    NORMAL --> SIMILARITY_CALC[1 - (embedding <=> query_embedding)<br/>AS similarity]
    NEGATION --> SIMILARITY_CALC
    
    SIMILARITY_CALC --> ORDER_RESULTS[ORDER BY similarity DESC]
    
    ORDER_RESULTS --> LIMIT_RESULTS[LIMIT por configuração]
```

---

## 🔧 Funções Auxiliares e Utilitárias

### **Formatação e Apresentação**

```mermaid
graph TD
    DISPLAY[display_results] --> RICH_CONSOLE[Rich Console<br/>Formatação Avançada]
    
    RICH_CONSOLE --> TABLE[Rich Table<br/>Resumo dos Resultados]
    RICH_CONSOLE --> PANELS[Rich Panels<br/>Detalhes por Resultado]
    
    TABLE --> FORMAT_CURRENCY[format_currency<br/>via gvg_search_utils_v3]
    TABLE --> FORMAT_DATE[format_date<br/>via gvg_search_utils_v3]
    
    PANELS --> HIGHLIGHT[highlight_key_terms<br/>Destacar termos da query]
    PANELS --> DECODE_PODER[decode_poder<br/>via gvg_search_utils_v3]
    PANELS --> DECODE_ESFERA[decode_esfera<br/>via gvg_search_utils_v3]
    
    HIGHLIGHT --> REGEX_REPLACE[Regex para destacar<br/>termos em [bold yellow]]
```

### **Cálculos de Similaridade**

```mermaid
graph TD
    SIMILARITY[Cálculos de Similaridade] --> CONFIDENCE[calculate_confidence<br/>via gvg_search_utils_v3<br/>Média das Similarities]
    
    SIMILARITY --> CORRESPONDENCE[calculate_correspondence_<br/>similarity_score<br/>Multiplicação:<br/>query_sim × result_sim]
    
    SIMILARITY --> TOP_CATEGORY[find_top_category_for_result<br/>Categoria com maior<br/>score de correspondência]
    
    CONFIDENCE --> MEAN_CALC[numpy.mean(similarities)]
    
    CORRESPONDENCE --> MAX_SCORE[Encontrar score máximo<br/>entre todas as categorias]
    
    TOP_CATEGORY --> BEST_MATCH[Retornar melhor match<br/>com metadados da categoria]
```

---

## 🌐 Integrações Externas

### **OpenAI API**

```mermaid
graph TD
    OPENAI[OpenAI Integration] --> CLIENT[OpenAI Client<br/>via API Key]
    
    CLIENT --> EMBEDDINGS_API[Embeddings API<br/>text-embedding-3-small]
    CLIENT --> ASSISTANTS_API[Assistants API<br/>Múltiplos Assistants]
    
    ASSISTANTS_API --> PREPROCESSING[Preprocessing Assistant<br/>Separação de Queries]
    ASSISTANTS_API --> RELEVANCE_FLEX[Relevance Flexible<br/>asst_tfD5oQxSgoGhtqdKQHK9UwRi]
    ASSISTANTS_API --> RELEVANCE_REST[Relevance Restrictive<br/>asst_XmsefQEKbuVWu51uNST7kpYT]
    ASSISTANTS_API --> KEYWORDS[Keywords Generation<br/>via generate_keywords]
    ASSISTANTS_API --> DOCUMENTS[Document Summarization<br/>via summarize_document]
    
    EMBEDDINGS_API --> VECTOR_DB[Armazenar em<br/>PostgreSQL pgvector]
    
    PREPROCESSING --> SMART_QUERIES[Queries Inteligentes<br/>Termos + Condições SQL]
    RELEVANCE_FLEX --> FILTERED_RESULTS[Resultados Filtrados<br/>Nível Flexível]
    RELEVANCE_REST --> FILTERED_RESULTS_REST[Resultados Filtrados<br/>Nível Restritivo]
```

### **Supabase PostgreSQL**

```mermaid
graph TD
    SUPABASE[Supabase PostgreSQL] --> PGVECTOR[pgvector Extension<br/>Vector Operations]
    
    PGVECTOR --> COSINE[Cosine Similarity<br/><=> operator]
    PGVECTOR --> STORAGE[Vector Storage<br/>1536 dimensions]
    
    SUPABASE --> MAIN_TABLES[Tabelas Principais]
    
    MAIN_TABLES --> CONTRACTS[contratacoes<br/>Dados PNCP completos]
    MAIN_TABLES --> EMBED_TABLE[contratacoes_embeddings<br/>Vectors + TOP categories]
    MAIN_TABLES --> CAT_TABLE[categorias<br/>Sistema categorização]
    
    CONTRACTS --> FULL_FIELDS[43+ campos PNCP<br/>incluindo novos campos v7+]
    EMBED_TABLE --> TOP_CATEGORIES[Arrays: top_categories,<br/>top_similarities]
    CAT_TABLE --> HIERARCHY[Hierarquia multi-nível<br/>codnv0, codnv1, codnv2, codnv3]
```

---

## 📈 Métricas e Monitoramento

### **Sistema de Debug e Logging**

```mermaid
graph TD
    DEBUG[Sistema de Debug] --> FLAGS[Debug Flags]
    
    FLAGS --> INTEL_DEBUG[DEBUG_INTELLIGENT_QUERIES<br/>Debug processamento IA]
    FLAGS --> RELEVANCE_DEBUG[DEBUG_RELEVANCE_FILTER<br/>Debug filtro relevância]
    FLAGS --> TEMP_DEBUG[Debug Temporário<br/>Status sistema v3]
    
    INTEL_DEBUG --> QUERY_INFO[Informações Query<br/>Original vs Processada]
    INTEL_DEBUG --> SQL_CONDITIONS[Condições SQL<br/>Extraídas]
    INTEL_DEBUG --> AI_EXPLANATION[Explicação IA<br/>do Processamento]
    
    RELEVANCE_DEBUG --> FILTER_STATUS[Status do Filtro<br/>Nível ativo]
    RELEVANCE_DEBUG --> AI_RESPONSES[Respostas IA<br/>Filtro relevância]
    
    TEMP_DEBUG --> SYSTEM_STATUS[Status Sistema<br/>v3 vs v2 fallback]
    TEMP_DEBUG --> MODULE_VERSIONS[Versões Módulos<br/>Carregados]
```

### **Medição de Performance**

```mermaid
graph TD
    PERFORMANCE[Medição Performance] --> SEARCH_TIME[Tempo de Busca<br/>start_time → end_time]
    
    SEARCH_TIME --> PHASES[Fases Medidas]
    
    PHASES --> PREPROCESSING_TIME[Tempo Preprocessamento<br/>IA]
    PHASES --> CATEGORY_TIME[Tempo Busca<br/>Categorias]
    PHASES --> SEARCH_EXEC_TIME[Tempo Execução<br/>Busca Principal]
    PHASES --> FILTER_TIME[Tempo Aplicação<br/>Filtros]
    PHASES --> SORT_TIME[Tempo Ordenação]
    
    SEARCH_TIME --> DISPLAY_TIME[Exibir Tempo Total<br/>na Interface]
```

---

## 🔄 Estados e Variáveis Globais

### **Estado Global do Sistema**

```mermaid
graph TD
    GLOBAL_STATE[Estado Global] --> SEARCH_CONFIG[Configurações Busca]
    GLOBAL_STATE --> SYSTEM_FLAGS[Flags Sistema]
    GLOBAL_STATE --> LAST_RESULTS[Últimos Resultados]
    
    SEARCH_CONFIG --> CURRENT_TYPE[current_search_type<br/>1-Semântica, 2-Palavras-chave, 3-Híbrida]
    SEARCH_CONFIG --> CURRENT_APPROACH[current_search_approach<br/>1-Direta, 2-Correspondência, 3-Filtro]
    SEARCH_CONFIG --> CURRENT_SORT[current_sort_mode<br/>1-Similaridade, 2-Data, 3-Valor]
    
    SYSTEM_FLAGS --> FILTER_EXPIRED[filter_expired<br/>Filtrar encerradas]
    SYSTEM_FLAGS --> USE_NEGATION[use_negation_embeddings<br/>Prompt negativo]
    SYSTEM_FLAGS --> USE_DOCLING[USE_DOCLING_V3<br/>Processador docs]
    SYSTEM_FLAGS --> NUM_CATEGORIES[num_top_categories<br/>TOP N categorias]
    
    LAST_RESULTS --> RESULTS_LIST[last_results<br/>Lista resultados]
    LAST_RESULTS --> LAST_QUERY[last_query<br/>Query anterior]
    LAST_RESULTS --> LAST_CATEGORIES[last_query_categories<br/>Categorias query anterior]
```

### **Configurações e Constantes**

```mermaid
graph TD
    CONSTANTS[Constantes Sistema] --> SEARCH_LIMITS[Limites Busca]
    CONSTANTS --> PATHS[Caminhos Arquivos]
    CONSTANTS --> DICTS[Dicionários Config]
    
    SEARCH_LIMITS --> MIN_RESULTS[MIN_RESULTS = 5]
    SEARCH_LIMITS --> MAX_RESULTS[MAX_RESULTS = 30]
    SEARCH_LIMITS --> MAX_TOKENS[MAX_TOKENS = 2000]
    SEARCH_LIMITS --> SEMANTIC_WEIGHT[SEMANTIC_WEIGHT = 0.75]
    
    PATHS --> BASE_PATH[BASE_PATH]
    PATHS --> RESULTS_PATH[RESULTS_PATH]
    PATHS --> FILES_PATH[FILES_PATH]
    
    DICTS --> SEARCH_TYPES[SEARCH_TYPES dict<br/>1,2,3 → nomes/descrições]
    DICTS --> SEARCH_APPROACHES[SEARCH_APPROACHES dict<br/>1,2,3 → nomes/descrições]
    DICTS --> SORT_MODES[SORT_MODES dict<br/>1,2,3 → nomes/descrições]
    DICTS --> RELEVANCE_LEVELS[RELEVANCE_LEVELS dict<br/>1,2,3 → nomes/descrições]
```

---

## 🎯 Pontos de Integração Críticos

### **1. Fallback System v3 → v2**
- O sistema **REQUER** gvg_search_utils_v3
- Se v3 não disponível → **EXIT** (não há fallback para v2)
- Para documentos: v3 ↔ v2 fallback automático

### **2. Processamento Inteligente**
- **Opcional**: Sistema funciona com/sem IA
- Se ativo: separação termos/condições SQL automática
- Se inativo: usa query original tradicional

### **3. Filtro de Relevância**
- **3 Níveis**: Sem filtro / Flexível / Restritivo
- Usa OpenAI Assistants específicos por nível
- Aplicado **APÓS** busca principal

### **4. Negation Embeddings**
- **Opcional**: Para prompts negativos
- Formato: "termo positivo -- termo negativo"  
- Apenas para busca Semântica e Híbrida

### **5. Sistema de Categorias**
- **Abordagens 2 e 3** dependem de categorização
- Busca TOP N categorias similares à query
- Multiplicação de similarities para correspondência

---

## 📋 Resumo das Principais Funcionalidades

### ✅ **Funcionalidades Principais**

1. **🔍 Três Tipos de Busca**
   - Semântica (embedding-based)
   - Palavras-chave (text matching)  
   - Híbrida (combinação ponderada)

2. **📊 Três Abordagens de Busca**
   - Direta (tradicional)
   - Correspondência (categorical matching)
   - Filtro (category-restricted universe)

3. **🎯 Sistema de Relevância IA (3 níveis)**
   - Sem filtro / Flexível / Restritivo
   - OpenAI Assistants especializados

4. **🤖 Processamento Inteligente**
   - Separação automática query → termos + SQL
   - Condições geográficas, valores, datas

5. **📄 Processamento de Documentos**
   - Docling v3 (tabelas avançadas) 
   - MarkItDown v2 (compatibilidade)

6. **📊 Exportação Multi-formato**
   - Excel (análise)
   - PDF (relatórios)
   - JSON (integração)

7. **⚙️ Interface Rica e Configurável**
   - Rich Console (tabelas, painéis, cores)
   - Menu adaptativo baseado em estado
   - Configurações persistentes por sessão

### 🔧 **Integrações Externas**
- **OpenAI API**: Embeddings + Assistants
- **Supabase**: PostgreSQL + pgvector  
- **Rich**: Interface terminal avançada
- **ReportLab**: Geração PDF profissional
- **Pandas**: Manipulação e exportação dados

---

*Este diagrama representa a arquitetura completa do sistema GvG_Terminal_v9, mostrando todos os caminhos de execução, dependências e integrações identificadas no código.*
