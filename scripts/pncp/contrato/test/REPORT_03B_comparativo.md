# Comparativo de metodologias de categorização (03B)

## Metodologias avaliadas
- Método A — baseline
  - Embeddings: vector(3072)
  - Índices: sem KNN (baseline “sem índice”)
  - Uso: referência para o sistema de pontuação
- Método B — 1536 + HNSW
  - Embeddings: vector(1536) (text-embedding-3-small)
  - Índices: HNSW em `test_categoria(cat_embeddings_1536 vector_cosine_ops)`
- Método C — 3072 + HNSW
  - Embeddings: halfvec(3072) (cast do 3072), text-embedding-3-large
  - Índices: HNSW em `test_categoria(cat_embedding_3072_hv halfvec_cosine_ops)`
- Método D — 3072 + IVFFLAT
  - Embeddings: halfvec(3072)
  - Índices: IVFFLAT em `test_categoria(cat_embedding_3072_hv_ivf halfvec_cosine_ops, lists=100)`

Observação: nos três casos com índice (B/C/D), o KNN é aplicado no lado das categorias (subconsulta LATERAL com `ORDER BY <=> LIMIT k`).

## Sistema de pontuação (A como baseline)
- Para cada contrato, comparamos o top‑5 de A contra o top‑5 de X (X ∈ {B,C,D}).
- Peso por posição em A: [10, 5, 3, 2, 1] para posições [1..5].
- Penalização por distância de posição entre A e X:
  - fator(|i−j|): 0→1.0, 1→0.5, 2→0.3, 3→0.2, 4→0.1
- Fórmula do score (por item do top‑5 de A): `score += weightA(i) × factor(|i−j|)`
- Score máximo por contrato e por método: 21 (quando todos os itens aparecem nas mesmas posições).

Exemplos:
- X igual a A (mesmas categorias nas mesmas posições) → 21.
- X contém as mesmas categorias de A, porém invertidas → score bem menor (ordem penaliza).

## Resultados de desempenho (1000 contratos)
- A: 214.399 s (4.66 rows/s)
- B: 10.166 s (98.37 rows/s)
- C: 10.887 s (91.86 rows/s)
- D: 6.171 s (162.05 rows/s)

Leituras:
- B/C/D são muito mais rápidos que A (índice KNN faz toda a diferença).
- D (IVFFLAT 3072) foi o mais rápido; C (HNSW 3072) próximo; B rápido porém 1536 dims.

## Resultados de qualidade (scores agregados)
- score_b_vs_a: 46.562
- score_c_vs_a: 155.766
- score_d_vs_a: 94.687

Interpretação:
- C obteve o maior alinhamento com A (maior score).
- D vem em segundo; B em terceiro.
- O ganho de C/D frente a B deve‑se, em parte, aos 3072 dims (maior capacidade representacional) e aos índices adequados.

## Ranking final
1) Método C — melhor qualidade (maior score), velocidade alta
2) Método D — melhor velocidade, qualidade intermediária entre C e B
3) Método B — boa velocidade, menor score (1536 dims)

## Recomendações
- Qualidade consistente: adotar C (3072 + HNSW) como padrão.
- Máxima velocidade com boa qualidade: considerar D (3072 + IVFFLAT), ajustando:
  - `lists` na criação (p.ex. 50–200) e `probes` em runtime (p.ex. 5–20) para recall/latência.
- B útil como baseline barato, mas perde em qualidade frente a 3072.

## Tuning
- HNSW: aumentar `hnsw.ef_search` melhora recall (custo moderado).
- IVFFLAT: aumentar `ivfflat.probes` aumenta recall (custo). Ajustar `lists` no índice para equilibrar partição e seletividade.
- Sempre `ANALYZE` após criar índices para planos otimizados.

## Próximos passos
- Amostra com inspeção humana (objeto_contrato × nom_cat) para validar top‑1/top‑k de C e D.
- Se C for o escolhido:
  - Consolidar halfvec(3072) no pipeline 02 (cast ::halfvec na escrita).
  - Manter índice HNSW nas categorias 3072 e monitorar tempos.
- Manter D disponível via flag como fallback de velocidade, com parâmetros (`lists`/`probes`) configuráveis por sessão.
