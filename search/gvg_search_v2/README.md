# gvg_search (função programática)

Pasta com a função de busca programática (`gvg_search`) e todos os módulos internos para uso standalone.

Conteúdo:
- GvG_Search_Function.py — função principal que retorna dict com results, log path e exports opcionais.
- gvg_search_core.py — lógica central (semântica/keyword/híbrida + categorias + filtro de relevância + toggles de IA).
- gvg_preprocessing.py — pré-processamento da consulta com Assistant da OpenAI e formatadores.
- gvg_ai_utils.py — embeddings OpenAI, negation embedding e helper de confiança.
- gvg_database.py — conexões Postgres via variáveis de ambiente.
- gvg_schema.py — metadados do schema e builders de SELECT.
- gvg_exporters.py — exportação JSON/XLSX/PDF e geração de nomes padronizados.
- gvg_documents.py — utilidades opcionais de documentos PNCP (não obrigatórias para busca).
- requirements.txt — dependências mínimas para executar a função.

## Variáveis de ambiente
Crie um `.env` com uma das opções de conexão:

Opção A (URL completa):
- DATABASE_URL ou SUPABASE_DB_URL (ou POSTGRES_URL)

Opção B (parâmetros separados):
- DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT (padrão 5432)

Opção C (padrão Supabase separados):
- SUPABASE_DB_HOST, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, SUPABASE_DB_PORT (padrão 5432)

Outros:
- OPENAI_API_KEY
- GVG_PREPROCESSING_QUERY_v1 (Assistant ID do pré-processamento; opcional)
- GVG_RELEVANCE_FLEXIBLE e GVG_RELEVANCE_RESTRICTIVE (opcionais)
- NEGATION_EMB_WEIGHT (padrão 1.0)
- GVG_SQL_DEBUG=1 para imprimir SQL

## Instalação (Windows PowerShell)
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install --upgrade pip; pip install -r .\search\search_v1\gvg_search\requirements.txt
```

## Uso rápido (Python)
```python
from gvg_search import gvg_search

result = gvg_search(
    prompt="Alimentação escolar no Nordeste",
    search=1, approach=3, relevance=2, order=1,
    max_results=20, top_cat=10,
    negation_emb=True, filter_expired=True,
    intelligent_toggle=False,
    export=("json",),
    output_dir="Resultados_Busca",
    debug=True
)
print(result["log_path"])  # caminho do log
```

Saídas são gravadas em `output_dir`, com a mesma nomenclatura do Prompt/Terminal.
