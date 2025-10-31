# Testes de Embedding (02) e Categorização (03) – Contrato

Pré‑requisitos
- Configurar `.env` em `scripts/pncp/.env` com SUPABASE_* e `OPENAI_API_KEY`.
- Tabelas de teste já criadas: `public.test_categoria` e `public.test_contrato_emb`.
- Índices de teste criados (pode ser sem CONCURRENTLY):
  - `test_categoria(cat_embeddings_1536 vector_cosine_ops)`, `test_categoria(cat_embedding_3072_hv halfvec_cosine_ops)`
  - `test_contrato_emb(embedding_1536 vector_cosine_ops)`, `test_contrato_emb(embedding_3072_hv halfvec_cosine_ops)`

Arquivos
- `test_02_embedding.py`: gera embeddings para contratos nas 3 metodologias (A/B/C) e mede tempo por método.
- `test_03a_categoria_embeddings.py`: gera embeddings para categorias nas 3 metodologias (A/B/C) e mede tempo.
- `test_03b_categorization.py`: executa categorização (top_k + confidence) para A/B/C/D e mede tempo por método.

Metodologias
- A: vector(3072)
- B: vector(1536) – text-embedding-3-small
- C: halfvec(3072) – text-embedding-3-large com cast ::halfvec
- D: halfvec(3072) com IVFFLAT em colunas dedicadas *_ivf (categoria: `cat_embedding_3072_hv_ivf`) 

Como rodar (PowerShell)
```powershell
# Embeddings dos contratos (limite opcional)
python .\scripts\pncp\contrato\test\test_02_embedding.py --limit 500 --batch 64 --trace

# Embeddings das categorias
python .\scripts\pncp\contrato\test\test_03a_categoria_embeddings.py --trace

# Categorização (A,B,C,D) com top-5
python .\scripts\pncp\contrato\test\test_03b_categorization.py --methods A,B,C,D --top-k 5 --batch-size 100 --trace
```

Notas
- Os scripts só preenchem colunas que estiverem NULL (use `--force` para recalcular).
- Se `halfvec` não estiver disponível, a metodologia C é ignorada automaticamente.
- Para reproduzir a janela de datas do 02/03 produtivos, adapte os filtros SQL ou adicione `--where` (melhoria futura).
