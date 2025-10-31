# Pipelines PNCP (v1) – Organização por Domínio/Estágio

Estrutura:
- 01 Processing (LPD): coleta/normalização e upsert idempotente
- 02 Embeddings (LED): geração de embeddings (OpenAI/pgvector)
- 03 Categorization (LCD): classificação por similaridade

Pastas:
- contrato/01_processing.py
- ata/01_processing.py
- pca/01_processing.py
- contratacao/01_processing.py (ponte para pipeline legado)

Convenções:
- Datas em TEXT
- Paginação até 500
- Retries/backoff (HTTP)
- Upsert ON CONFLICT usando chaves naturais
- Estado via system_config (ex.: contrato_last_processed_date, ata_last_processed_date, pca_last_processed_date)
- Métricas em pipeline_run_stats (pode exigir migração para colunas extras)

Como rodar (exemplos):
- Contratos (publicação do dia)
  - `python contrato/01_processing.py --mode publicacao`
- Contratos (atualização D-1..D)
  - `python contrato/01_processing.py --mode atualizacao`
- Atas (backfill vigência 2025)
  - `python ata/01_processing.py --mode vigencia --from 20250101 --to 20251231`
- Atas (atualização D-1..D)
  - `python ata/01_processing.py --mode atualizacao`
- PCA (atualização D-1..D)
  - `python pca/01_processing.py`

Observações:
- Execute as migrações em `db/migrations/20251025_create_ata_pca.sql` e `20251025_create_embeddings_tables.sql` antes de rodar os scripts 01.
- A tabela pipeline_run_stats usada aqui grava métricas detalhadas (started_at, finished_at, etc.). Caso seu schema atual seja diferente, ajuste a função `insert_pipeline_run_stats` nos scripts ou migre a tabela.
