WITH base AS (
  SELECT
    t.numero_controle_pncp,
    c.objeto_contrato,
    t.top_categories_a, t.top_similarities_a, t.confidence_a,
    t.top_categories_b, t.top_similarities_b, t.confidence_b,
    t.top_categories_c, t.top_similarities_c, t.confidence_c,
    t.top_categories_d, t.top_similarities_d, t.confidence_d
  FROM public.test_contrato_emb t
  JOIN public.contrato c USING (numero_controle_pncp)
  -- WHERE t.numero_controle_pncp = 'SEU_NUMERO_PNCP'   -- opcional
),

-- Arrays de nomes (nom_cat) na ordem do top-k
nomes AS (
  SELECT
    b.numero_controle_pncp,

    (SELECT array_agg(COALESCE(tc.nom_cat, u.cod_cat) ORDER BY u.rn)
       FROM unnest(b.top_categories_a) WITH ORDINALITY AS u(cod_cat, rn)
       LEFT JOIN public.test_categoria tc ON tc.cod_cat = u.cod_cat) AS top_nom_a,

    (SELECT array_agg(COALESCE(tc.nom_cat, u.cod_cat) ORDER BY u.rn)
       FROM unnest(b.top_categories_b) WITH ORDINALITY AS u(cod_cat, rn)
       LEFT JOIN public.test_categoria tc ON tc.cod_cat = u.cod_cat) AS top_nom_b,

    (SELECT array_agg(COALESCE(tc.nom_cat, u.cod_cat) ORDER BY u.rn)
       FROM unnest(b.top_categories_c) WITH ORDINALITY AS u(cod_cat, rn)
       LEFT JOIN public.test_categoria tc ON tc.cod_cat = u.cod_cat) AS top_nom_c,

    (SELECT array_agg(COALESCE(tc.nom_cat, u.cod_cat) ORDER BY u.rn)
       FROM unnest(b.top_categories_d) WITH ORDINALITY AS u(cod_cat, rn)
       LEFT JOIN public.test_categoria tc ON tc.cod_cat = u.cod_cat) AS top_nom_d

  FROM base b
),

-- Listas com posição (1..5) para A, B, C, D
ua AS (
  SELECT b.numero_controle_pncp, u.cod_cat AS a_cat, u.rn::int AS i
  FROM base b
  JOIN LATERAL unnest(COALESCE(b.top_categories_a, ARRAY[]::text[])) WITH ORDINALITY AS u(cod_cat, rn) ON TRUE
  WHERE u.rn <= 5
),
ub AS (
  SELECT b.numero_controle_pncp, u.cod_cat AS x_cat, u.rn::int AS j
  FROM base b
  JOIN LATERAL unnest(COALESCE(b.top_categories_b, ARRAY[]::text[])) WITH ORDINALITY AS u(cod_cat, rn) ON TRUE
  WHERE u.rn <= 5
),
uc AS (
  SELECT b.numero_controle_pncp, u.cod_cat AS x_cat, u.rn::int AS j
  FROM base b
  JOIN LATERAL unnest(COALESCE(b.top_categories_c, ARRAY[]::text[])) WITH ORDINALITY AS u(cod_cat, rn) ON TRUE
  WHERE u.rn <= 5
),
ud AS (
  SELECT b.numero_controle_pncp, u.cod_cat AS x_cat, u.rn::int AS j
  FROM base b
  JOIN LATERAL unnest(COALESCE(b.top_categories_d, ARRAY[]::text[])) WITH ORDINALITY AS u(cod_cat, rn) ON TRUE
  WHERE u.rn <= 5
),

-- Funções de peso (A) e fator por distância (|i-j|) embutidas via CASE
scores AS (
  SELECT
    a.numero_controle_pncp,

    SUM(  -- B vs A
      CASE
        WHEN b.j IS NULL THEN 0
        ELSE
          (CASE a.i WHEN 1 THEN 10 WHEN 2 THEN 5 WHEN 3 THEN 3 WHEN 4 THEN 2 WHEN 5 THEN 1 ELSE 0 END) *
          (CASE ABS(a.i - b.j)
               WHEN 0 THEN 1.0
               WHEN 1 THEN 0.5
               WHEN 2 THEN 0.3
               WHEN 3 THEN 0.2
               WHEN 4 THEN 0.1
               ELSE 0.0 END)
      END
    ) AS score_b_vs_a,

    SUM(  -- C vs A
      CASE
        WHEN c.j IS NULL THEN 0
        ELSE
          (CASE a.i WHEN 1 THEN 10 WHEN 2 THEN 5 WHEN 3 THEN 3 WHEN 4 THEN 2 WHEN 5 THEN 1 ELSE 0 END) *
          (CASE ABS(a.i - c.j)
               WHEN 0 THEN 1.0
               WHEN 1 THEN 0.5
               WHEN 2 THEN 0.3
               WHEN 3 THEN 0.2
               WHEN 4 THEN 0.1
               ELSE 0.0 END)
      END
    ) AS score_c_vs_a,

    SUM(  -- D vs A
      CASE
        WHEN d.j IS NULL THEN 0
        ELSE
          (CASE a.i WHEN 1 THEN 10 WHEN 2 THEN 5 WHEN 3 THEN 3 WHEN 4 THEN 2 WHEN 5 THEN 1 ELSE 0 END) *
          (CASE ABS(a.i - d.j)
               WHEN 0 THEN 1.0
               WHEN 1 THEN 0.5
               WHEN 2 THEN 0.3
               WHEN 3 THEN 0.2
               WHEN 4 THEN 0.1
               ELSE 0.0 END)
      END
    ) AS score_d_vs_a

  FROM ua a
  LEFT JOIN ub b ON b.numero_controle_pncp = a.numero_controle_pncp AND b.x_cat = a.a_cat
  LEFT JOIN uc c ON c.numero_controle_pncp = a.numero_controle_pncp AND c.x_cat = a.a_cat
  LEFT JOIN ud d ON d.numero_controle_pncp = a.numero_controle_pncp AND d.x_cat = a.a_cat
  GROUP BY a.numero_controle_pncp
)

SELECT
  b.numero_controle_pncp,
  b.objeto_contrato,

  -- Método A
  b.top_categories_a   AS top5_cod_a,
  n.top_nom_a          AS top5_nom_a,
  b.top_similarities_a AS top5_sim_a,
  b.confidence_a,

  -- Método B
  b.top_categories_b   AS top5_cod_b,
  n.top_nom_b          AS top5_nom_b,
  b.top_similarities_b AS top5_sim_b,
  b.confidence_b,
  s.score_b_vs_a,

  -- Método C
  b.top_categories_c   AS top5_cod_c,
  n.top_nom_c          AS top5_nom_c,
  b.top_similarities_c AS top5_sim_c,
  b.confidence_c,
  s.score_c_vs_a,

  -- Método D
  b.top_categories_d   AS top5_cod_d,
  n.top_nom_d          AS top5_nom_d,
  b.top_similarities_d AS top5_sim_d,
  b.confidence_d,
  s.score_d_vs_a,

  -- Ranking total (para ordenar)
  (COALESCE(s.score_b_vs_a,0) + COALESCE(s.score_c_vs_a,0) + COALESCE(s.score_d_vs_a,0)) AS score_total

FROM base b
LEFT JOIN nomes  n ON n.numero_controle_pncp = b.numero_controle_pncp
LEFT JOIN scores s ON s.numero_controle_pncp = b.numero_controle_pncp
ORDER BY score_total DESC, b.numero_controle_pncp