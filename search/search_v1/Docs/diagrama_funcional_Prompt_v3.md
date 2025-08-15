# 🚀 Diagrama Funcional - Prompt_v3 (Arquitetura Consolidada)

## 🎯 Visão Geral
Prompt_v3 consolida módulos (formatters + preprocessing, categorias + core, export centralizado) reduzindo acoplamento e eliminando arquivos utilitários redundantes (`gvg_formatters.py`, `gvg_categories.py`, `gvg_utils.py`). Mantém mesmas capacidades de busca, processamento inteligente, filtro de relevância, exportações e pipeline de documentos.

---
## 🏗️ Arquitetura Modular Atual
```mermaid
graph TB
    ST[GvG_Search_Terminal.py]
    FN[GvG_Search_Function.py]
    PR[GvG_Search_Prompt.py]

    subgraph Core
        SC[gvg_search_core.py]\n        AI[gvg_ai_utils.py]\n        PRE[gvg_preprocessing.py]\n        EXP[gvg_exporters.py]\n        DB[gvg_database.py]\n        DOC[gvg_documents.py]
    end

    ST --> SC
    ST --> DOC
    ST --> EXP
    ST --> AI
    ST --> PRE
    ST --> DB

    FN --> SC
    FN --> EXP
    FN --> PRE
    FN --> AI
    FN --> DB

    PR --> SC
    PR --> EXP
    PR --> PRE
    PR --> AI
    PR --> DB
    PR --> DOC

    SC --> AI
    SC --> PRE
    SC --> DB
    DOC --> AI
```

---
## 🔄 Fluxo de Busca Unificado
1. Entrada (Terminal / Prompt / Função) define params.
2. (Opcional) `SearchQueryProcessor` pré-processa query.
3. `gvg_search_core` executa busca (semantic / keyword / hybrid) e (opcional) filtro de relevância.
4. Resultados retornam com confidência e metadados de processamento.
5. Módulo de interface ordena e chama `gvg_exporters` para persistência.
6. Terminal pode iniciar pipeline de documentos (`gvg_documents`).

---
## 🔁 Reutilização de Funções (DRY)
- Categorias e filtros agora vivem em `gvg_search_core` eliminando arquivo separado.
- Formatters (moeda/data/decoders) vivem em `gvg_preprocessing` junto ao processamento inteligente.
- Nome de export + export JSON/XLSX/PDF centralizados em `gvg_exporters` e reutilizados por todas interfaces.

---
## 🧪 Filtro de Relevância
Mesma lógica do Prompt_v2, encapsulada em funções privadas + públicas em `gvg_search_core`.

---
## 📄 Documentos
Inalterado vs v2 exceto remoção de dependência de util façade.

---
## 🧩 Principais Mudanças vs Prompt_v2
| Área | Antes (v2) | Agora (v3) |
|------|------------|------------|
| Formatters | Arquivo dedicado | Integrado em preprocessing |
| Categorias | Arquivo dedicado | Integrado no search_core |
| Utils façade | Existia (reexports) | Removido |
| Export | Duplicado em Prompt/Function/Terminal | Centralizado em gvg_exporters |
| Funções de contagem | Espalhadas | Agrupadas por domínio |

---
## ✅ Benefícios
- Menos arquivos a manter.
- Redução de import chains e reexports.
- Ponto único para cada responsabilidade (embeddings, preprocessing, export, documentos, busca).
- Documentação alinhada com implementação real.

---
## 🔜 Próximos Passos Sugeridos
- Adicionar testes unitários leves (export filename, preprocessing fallback, relevance filter parsing).
- Extrair filtro de relevância para módulo próprio se crescer novamente.
- Parametrizar pesos híbridos via argumento.

---
Gerado para refletir estado pós-consolidação (Prompt_v3).
