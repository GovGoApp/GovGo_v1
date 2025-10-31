# Relatório de Testes PNCP – 02 (Embeddings), 03A (Embeddings de Categoria) e 03B (Categorização A..I)

Este relatório consolida como cada teste foi realizado, o que mede, o mapeamento de métodos A..I e os resultados coletados (tempos em JSON). Inclui também um ranking por "score vs A" (baseline) e explicações sobre o comportamento dos métodos com texto concatenado (objctx).

## Métodos e mapeamentos

- A: contrato embedding_3072_2 (vector 3072) × categoria cat_embeddings_3072 (vector); KNN por cosine; texto: objeto_contrato
- B: contrato embedding_1536 (vector 1536) × categoria cat_embeddings_1536 (vector); HNSW; texto: objeto_contrato
- C: contrato embedding_3072_hv (halfvec 3072) × categoria cat_embedding_3072_hv (halfvec); HNSW; texto: objeto_contrato
- D: contrato embedding_3072_hv_ivf (halfvec) × categoria cat_embedding_3072_hv_ivf (halfvec); IVFFLAT (lists=100); texto: objeto_contrato
- E: contrato embedding_objctx_1536 (vector 1536) × categoria cat_embeddings_1536 (vector); HNSW; texto: categoria_processo_nome :: objeto_contrato
- F: contrato embedding_objctx_3072_hv (halfvec 3072) × categoria cat_embedding_3072_hv (halfvec); HNSW; texto: categoria_processo_nome :: objeto_contrato
- G: contrato embedding_objctx_3072_hv (halfvec 3072) × categoria cat_embedding_3072_hv_ivf (halfvec); IVFFLAT (lists=100); texto: categoria_processo_nome :: objeto_contrato
- H: contrato embedding_objctx_3072_hv (halfvec 3072) × categoria cat_3072_hv_hnsw_h (halfvec); HNSW (m=32, ef_construction=64; ef_search=64); texto: categoria_processo_nome :: objeto_contrato
- I: contrato embedding_objctx_3072_hv (halfvec 3072) × categoria cat_3072_hv_ivf_i (halfvec); IVFFLAT (lists=300; probes=10); texto: categoria_processo_nome :: objeto_contrato

Parâmetros principais do 03B nesta rodada: top_k=5; batch_size=100; H com ef_search=64; I com probes=10.

---

## Teste 02 – Embeddings (contratos)

O que faz: gera embeddings de contratos por lote via OpenAI e grava nas colunas-alvo.

- A/B/C: texto base = objeto_contrato
- E/F (e G como alias de F): texto concat = categoria_processo_nome :: objeto_contrato

Resultados (JSON exatamente como coletado):

```
test_02	{"results": {"A": {"count": 1000, "secs": 67.52}, "B": {"count": 1000, "secs": 46.72}, "C": {"count": 1000, "secs": 57.78}}, "ts": "2025-10-30T15:01:54.201883"}
	{"results": {"E": {"count": 1000, "secs": 46.69}, "F": {"count": 1000, "secs": 59.38}, "G": {"count": 0, "secs": 0.0}}, "ts": "2025-10-30T22:30:22.957514"}
```

Observações:
- G não escreve pois compartilha a mesma coluna de F (embedding_objctx_3072_hv).

---

## Teste 03A – Embeddings de Categoria (test_categoria)

O que faz: preenche/atualiza embeddings de categorias. Nesta rodada, os índices dedicados (H/I) foram alimentados por cópia das colunas base correspondentes.

Resultados (JSON):

```
test_03A	{"results": {"A": {"count": 13082, "secs": 778.311, "rows_per_sec": 16.81}, "B": {"count": 13082, "secs": 774.436, "rows_per_sec": 16.89}, "C": {"count": 13082, "secs": 1265.97, "rows_per_sec": 10.33}}, "total": 39246, "ts": "2025-10-30T15:50:06.366138"}
```

---

## Teste 03B – Categorização (SQL no banco, KNN via pgvector)

O que faz: para cada contrato pendente por método, roda um LATERAL KNN contra a tabela de categorias com o índice adequado, calcula top_k categorias, similaridades e uma confiança (gap ponderado), e atualiza test_contrato_emb.

Resultados (JSON):

```
test_03B	{"results": {"A": {"count": 1000, "total": 1000, "secs": 214.399, "rows_per_sec": 4.66}, "B": {"count": 1000, "total": 1000, "secs": 10.166, "rows_per_sec": 98.37}, "C": {"count": 1000, "total": 1000, "secs": 10.887, "rows_per_sec": 91.86}, "D": {"count": 1000, "total": 1000, "secs": 6.171, "rows_per_sec": 162.05}}, "ts": "2025-10-30T16:27:37.706765"}
	{"results": {"E": {"count": 1000, "total": 1000, "secs": 10.424, "rows_per_sec": 95.93}, "F": {"count": 1000, "total": 1000, "secs": 10.899, "rows_per_sec": 91.75}, "G": {"count": 1000, "total": 1000, "secs": 11.358, "rows_per_sec": 88.04}, "H": {"count": 1000, "total": 1000, "secs": 14.363, "rows_per_sec": 69.62}, "I": {"count": 1000, "total": 1000, "secs": 11.933, "rows_per_sec": 83.8}}, "ts": "2025-10-30T22:40:06.244411"}
```

Leituras rápidas de performance:
- D (IVFFLAT base) foi o mais rápido nesta amostra.
- B e C (HNSW base) rápidos e estáveis; E/F (objctx) próximos aos seus equivalentes.
- H ficou mais lento pelo ef_search=64; I ficou próximo de G, com probes=10 e lists=300.

---

## Ranking de qualidade (score X vs A)

Métrica: para cada item no top‑5 de A na posição i, se o mesmo cod_cat aparece em X na posição j, soma-se weightA(i)×factor(|i−j|), com weightA=[10,5,3,2,1] e factor=[1.0,0.5,0.3,0.2,0.1]. Máximo por método: 21 por contrato.

Somas totais informadas:

- score_b_vs_a = 46.562
- score_c_vs_a = 155.766
- score_d_vs_a = 94.687
- score_e_vs_a = 40.730
- score_f_vs_a = 102.328
- score_g_vs_a = 66.908
- score_h_vs_a = 114.369
- score_i_vs_a = 105.961

Ordem (maior→menor): C > H > I > F > D > G > B > E.

Interpretação:
- C lidera em alinhamento com A (baseline). Entre os concat, H e I foram os melhores.

---

## Por que os métodos com concat (objctx) tendem a pontuar menos vs A?

- A é o baseline com texto somente do objeto_contrato. O score mede concordância com A (mesmos cod_cat e posições). 
- Nos métodos concat, o embedding do contrato incorpora categoria_processo_nome como prefixo. Esse contexto extra muda a vizinhança semântica do vetor do contrato, deslocando o top‑k em relação ao obtido usando só o objeto.
- Assim, mesmo que o concat possa melhorar a qualidade absoluta para certos casos, a métrica de score vs A penaliza qualquer divergência do top‑5 de A. Logo, os somatórios tendem a ser menores por definição da métrica.
- Detalhe prático: o prefixo da categoria pode dominar parte do embedding (especialmente em textos curtos), reduzindo a sobreposição com o top‑5 de A.

---

## Notas finais e próximos passos

- Já simplificamos para apenas dois embeddings "concat" no lado dos contratos: 1536 (E) e 3072 halfvec (F/G/H/I). 
- Diferenças entre F/G/H/I ficam no lado das categorias (colunas/índices e tuning: HNSW vs IVFFLAT, ef_search, probes, lists).
- Próximos ajustes sugeridos: avaliar probes (I) 15–20 e ef_search (H) 96–128 em amostras menores; revisar score também contra um rótulo de referência (se disponível) para avaliar qualidade absoluta.
