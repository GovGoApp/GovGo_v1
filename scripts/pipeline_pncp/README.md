# Pipeline PNCP (simplificado)

Esta pasta contém a nova versão simplificada do pipeline diário (recomendado).

Etapas:
- 01_pipeline_pncp_download.py (LPD)
  - Download de contratações e itens da API PNCP
  - Mapeamento inline para BDS1; inserções idempotentes
- 02_pipeline_pncp_embeddings.py (LED)
  - Gera embeddings para contratações pendentes
  - Lotes sequenciais e estáveis; idempotente
- 03_pipeline_pncp_categorization.py (LCD)
  - Classifica contratações por similaridade (pgvector)
  - Atualiza top_categories/top_similarities/confidence

Pré-requisitos
- Python 3.12+
- pacotes: requests, psycopg2-binary, python-dotenv, openai (somente etapa 02)
- .env em v1/ com SUPABASE_* e (para 02) OPENAI_API_KEY

Execução manual
```bash
# 01 – Download (usa e atualiza LPD)
python 01_pipeline_pncp_download.py
python 01_pipeline_pncp_download.py --test 20250901

# 02 – Embeddings (usa LED/LPD e atualiza LED)
python 02_pipeline_pncp_embeddings.py
python 02_pipeline_pncp_embeddings.py --test 20250901 --batch 32

# 03 – Categorização (usa LCD/LED e atualiza LCD)
python 03_pipeline_pncp_categorization.py
python 03_pipeline_pncp_categorization.py --test 20250901 --batch-size 300 --top-k 5
```

Logs
- Todos os scripts usam `logs/log_<PIPELINE_TIMESTAMP>.log` compartilhado
- Mensagens concisas com LPD/LED/LCD e totais por data

Agendamento
- Use o `00_run_pipeline_pncp.bat` (Windows) ou `00_pipeline.py` (cron) nesta pasta para executar 01→02→03 em sequência
