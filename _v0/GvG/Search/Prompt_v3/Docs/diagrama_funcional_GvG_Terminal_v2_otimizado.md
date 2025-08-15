# 🚀 Diagrama Funcional Completo - GvG_Terminal_v2_Otimizado (Prompt_v2)

## 🎯 Visão Geral

A versão Prompt_v2 do terminal GvG implementa uma arquitetura enxuta: apenas funções realmente usadas foram mantidas e distribuídas em módulos especializados (formatters, AI/embeddings, busca core, banco, documentos, pré-processamento). Mantém as 3 modalidades de busca (semântica, palavras‑chave, híbrida), 3 abordagens (direta, correspondência simplificada, filtro simplificado), processamento inteligente opcional, exportações (Excel, PDF, JSON), processamento Docling v3 de documentos e geração de palavras‑chave.

---

## 🏗️ Arquitetura Modular

```mermaid
graph TB
    ST[GvG_Search_Terminal.py]
    subgraph Core
        SC[gvg_search_core.py]
        DB[gvg_database.py]
        AI[gvg_ai_utils.py]
        PRE[gvg_preprocessing.py]
        FM[gvg_formatters.py]
        DOC[gvg_documents.py]
    end

    ST --> SC
    ST --> DB
    ST --> AI
    ST --> PRE
    ST --> FM
    ST --> DOC

    SC --> DB
    SC --> AI
    SC --> PRE
    DOC --> AI
```

---

## 🔄 Fluxo Principal (Loop)

```mermaid
sequenceDiagram
    participant U as Usuário
    participant T as Terminal
    participant PRE as Preprocess
    participant SC as Search Core
    participant DB as Banco
    participant AI as Embeddings

    U->>T: Digita consulta ou opção
    T-->>U: Mostra menu/config
    alt Opção Config
        T->>T: Atualiza estado global
    else Consulta
        T->>PRE: (se IA ativa) process_query
        PRE-->>T: search_terms + sql_conditions
        T->>SC: semantic/keyword/hybrid()
        SC->>AI: get_embedding / get_negation_embedding
        SC->>DB: Executa SQL (contratacoes + embeddings)
        DB-->>SC: Registros
        SC->>T: Resultados + confiança
        T-->>U: Tabela + painéis detalhados
    end
```

---

## 🔍 Tipos e Abordagens de Busca

```mermaid
graph TD
    A[perform_search] --> B{Abordagem}
    B -->|Direta| D1[direct_search]
    B -->|Correspondência| D2[correspondence_search (simulada)]
    B -->|Filtro| D3[category_filtered_search (simulada)]

    D1 --> T1{Tipo}
    T1 -->|Semântica| S1[semantic_search]
    T1 -->|Keyword| S2[keyword_search]
    T1 -->|Híbrida| S3[hybrid_search]

    S1 --> E1[get_embedding / negation]
    S2 --> E2[Full-text ts_rank / fallback ILIKE]
    S3 --> E3[Embeddings + ts_rank combinados]
```

---

## 🤖 Processamento Inteligente de Query

```mermaid
graph TD
    Q[Consulta Original] --> C{IA Ativa?}
    C -->|Não| QO[Usar Query Original]
    C -->|Sim| PRE[SearchQueryProcessor.process_query]
    PRE --> OUT[search_terms + sql_conditions]
    QO --> OUT
```

Resultado incorporado em cada resultado: details.intelligent_processing

---

## 🧪 Filtro de Relevância Interno (Search Core)

Níveis (1=desligado / 2=flexível / 3=restritivo). Implementado em `gvg_search_core` com chamadas opcionais a Assistants OpenAI (thread reutilizável). Aplicado pós-ranking se ativo.

```mermaid
graph TD
    RIN[Resultados iniciais] --> L{Level > 1?}
    L -->|Não| ROUT[Sem filtro]
    L -->|Sim| PAY[_prepare_relevance_payload]
    PAY --> OAI[Assistant OpenAI]
    OAI --> RESP[_process_relevance_response]
    RESP --> ROUT[Resultados filtrados]
```

---

## 📄 Sistema de Documentos (Docling v3)

```mermaid
graph TD
    SEL[Selecionar Processo] --> FD[fetch_documentos]
    FD --> LIST{Doc(s) Encontrados?}
    LIST -->|Não| ND[Nenhum]
    LIST -->|Sim| MENU[Menu Nº/A/V/Q]
    MENU -->|Nº| ONE[process_single_document]
    MENU -->|A| ALL[process_all_documents]
    MENU -->|V| LINKS[show_document_links]

    ONE --> PP[process_pncp_document]
    ALL --> PP
    PP --> DL[download_document]
    DL --> CV[convert_document_to_markdown]
    CV --> SUMM[generate_document_summary (OpenAI opcional)]
    SUMM --> SAVE1[save_markdown_file]
    SUMM --> SAVE2[save_summary_file]
```

ZIP: extração múltipla (todos arquivos suportados) com log detalhado.

---

## 🧠 Geração de Palavras‑chave

```mermaid
graph TD
    PICK[Selecionar Processo] --> DESC[Extrair descrição]
    DESC --> AIKW[generate_keywords (chat.completions)]
    AIKW --> KWLIST[Lista de palavras]
    KWLIST --> DISPLAY[Exibir formato v9]
```

---

## 💾 Exportações

```mermaid
graph TD
    EXP[export_results] --> F{Formato}
    F -->|1| XL[export_results_to_excel]
    F -->|2| PDF[export_results_to_pdf]
    F -->|3| JS[export_results_to_json]

    XL --> PANDAS[DataFrame + to_excel]
    PDF --> RPT[ReportLab: tabela + cards]
    JS --> META[Gerar metadata + results]
```

Nome padrão: `Busca_{QUERY_SAN}_S{tipo}_A{abord}_R{relev}_O{ord}_{I/N}_{timestamp}.{ext}`

---

## 🧩 Principais Estruturas de Dados

Resultado de busca (por item):
- id / numero_controle
- similarity (float 0..1)
- rank
- details (dict campos contratação + intelligent_processing)

Intelligent Processing (`details.intelligent_processing`):
- original_query
- processed_terms
- applied_conditions
- explanation

Document Summary Output: string markdown formatado + arquivos persistidos (Markdown e SUMMARY).

---

## 🔌 Integrações Externas

| Área | Tecnologia | Uso |
|------|------------|-----|
| Embeddings | OpenAI text-embedding-3-large | semantic / hybrid / negation |
| Chat / Keywords | OpenAI gpt-3.5-turbo | generate_keywords |
| Summaries Doc | OpenAI gpt-4o | generate_document_summary |
| Banco | PostgreSQL + pgvector | consultas SQL vetoriais e full-text |
| Doc Conversion | Docling (PyPdfium + TableFormer FAST) | PDF/ZIP parsing |
| UI | Rich | Tabelas, painéis, progresso |
| PDF | ReportLab | Exportação relatório |
| Excel | pandas + openpyxl | Export planilha |

Fallbacks: keyword_search → ILIKE se full‑text indisponível; hybrid_search → fusão Python se SQL combinado falhar; documentos → API PNCP se DB vazio.

---

## 🌐 Estados Globais (Terminal)
- current_search_type / current_search_approach / current_sort_mode
- max_results / num_top_categories
- filter_expired / use_negation_embeddings
- intelligent_processing (proxy via get_intelligent_status)
- relevance_filter_level (local simplificado)
- last_results / last_query / last_query_categories

---

## ⚙️ Ciclo de Vida de uma Consulta
1. Usuário digita query
2. (Opcional) Pré-processamento → termos + condições SQL
3. Seleção de função conforme tipo (semantic/keyword/hybrid)
4. Execução SQL (embedding + ts_rank ou combinação)
5. Aplicação de filtro de relevância (se nível >1 e OpenAI disponível)
6. Ordenação adicional conforme sort mode
7. Exibição: tabela resumo + painéis detalhados
8. Ações opcionais: documentos / keywords / exportar

---

## ✅ Principais Diferenças vs v9
- Importações seletivas (sem wildcard * )
- Módulos separados (AI, DB, formatters, core, docs, preprocessing)
- Correspondência e Filtro simplificados (mock de categorias)
- Filtro de relevância implementado diretamente em `gvg_search_core`
- Documentos: sempre Docling v3 (sem alternância MarkItDown)
- Export JSON inclui metadados simplificados

---

## 🔐 Considerações de Segurança
- Chaves OpenAI lidas de variáveis ambiente / .env
- Sanitização de nome de arquivos de exportação e documentos
- Fallbacks evitam falhas críticas (rede / ausência de feature)

---

## 📈 Pontos de Otimização
- Redução de namespace: apenas funções usadas
- Menos overhead de importação dinâmica
- Filtros e processamento incremental (apenas quando necessário)
- Reuso de threads OpenAI (pré-processamento / relevância)

---

## 📝 Conclusão
A arquitetura Prompt_v2 entrega o mesmo conjunto funcional essencial do terminal anterior com menor acoplamento, clareza modular e pipelines de documentos e busca otimizados, preservando a experiência visual e fluxos operacionais herdados da versão v9.
