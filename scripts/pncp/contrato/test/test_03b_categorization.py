#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 03b – Categorização (A/B/C/D/E/F/G/H/I) em test_contrato_emb usando test_categoria
- A: embedding_3072_2           <=> cat_embeddings_3072          (vector)
- B: embedding_1536             <=> cat_embeddings_1536          (vector)
- C: embedding_3072_hv          <=> cat_embedding_3072_hv        (halfvec)
- D: embedding_3072_hv_ivf      <=> cat_embedding_3072_hv_ivf    (halfvec, IVFFLAT lists=100)
- E: embedding_objctx_1536      <=> cat_embeddings_1536          (vector)
- F: embedding_objctx_3072_hv   <=> cat_embedding_3072_hv        (halfvec)
+- G: embedding_objctx_3072_hv   <=> cat_embedding_3072_hv_ivf    (halfvec, IVFFLAT lists=100)
+- H: embedding_objctx_3072_hv   <=> cat_3072_hv_hnsw_h           (halfvec, HNSW m=32, ef_search ajustável)
+- I: embedding_objctx_3072_hv   <=> cat_3072_hv_ivf_i            (halfvec, IVFFLAT lists=400, probes ajustável)

Atualiza colunas:
- A: top_categories_a, top_similarities_a, confidence_a
- B: top_categories_b, top_similarities_b, confidence_b
- C: top_categories_c, top_similarities_c, confidence_c
- D: top_categories_d, top_similarities_d, confidence_d
- E: top_categories_e, top_similarities_e, confidence_e
- F: top_categories_f, top_similarities_f, confidence_f
- G: top_categories_g, top_similarities_g, confidence_g
- H: top_categories_h, top_similarities_h, confidence_h
- I: top_categories_i, top_similarities_i, confidence_i
"""
import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any

import psycopg2
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Carrega .env de scripts/pncp/.env (subindo dois níveis) e depois um .env local (se existir)
ENV_PATH_PNCP = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".env"))
ENV_PATH_LOCAL = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".env"))
load_dotenv(ENV_PATH_PNCP)
load_dotenv(ENV_PATH_LOCAL)

TRACE = False

DB_CFG = dict(
    host=os.getenv("SUPABASE_HOST"),
    port=int(os.getenv("SUPABASE_PORT", "6543")),
    dbname=os.getenv("SUPABASE_DBNAME"),
    user=os.getenv("SUPABASE_USER"),
    password=os.getenv("SUPABASE_PASSWORD"),
)


def get_conn():
    return psycopg2.connect(**DB_CFG)


def log(msg: str):
    if TRACE:
        print(msg, flush=True)
        logging.info(msg)


METHOD_SPECS = {
    "A": {
        "emb_col": "embedding_3072_2",
        "cat_col": "cat_embeddings_3072",
        "top_cat_col": "top_categories_a",
        "top_sim_col": "top_similarities_a",
        "conf_col": "confidence_a",
        "cast": "::vector",
    },
    "B": {
        "emb_col": "embedding_1536",
        "cat_col": "cat_embeddings_1536",
        "top_cat_col": "top_categories_b",
        "top_sim_col": "top_similarities_b",
        "conf_col": "confidence_b",
        "cast": "::vector",
    },
    "C": {
        "emb_col": "embedding_3072_hv",
        "cat_col": "cat_embedding_3072_hv",
        "top_cat_col": "top_categories_c",
        "top_sim_col": "top_similarities_c",
        "conf_col": "confidence_c",
        "cast": "::halfvec",
    },
    "D": {
        # Método D: IVFFLAT em halfvec(3072) usando colunas dedicadas *_ivf
        "emb_col": "embedding_3072_hv_ivf",
        "cat_col": "cat_embedding_3072_hv_ivf",
        "top_cat_col": "top_categories_d",
        "top_sim_col": "top_similarities_d",
        "conf_col": "confidence_d",
        "cast": "::halfvec",
    },
    # Novos métodos com texto objctx e índices dedicados
    "E": {
        "emb_col": "embedding_objctx_1536",
        "cat_col": "cat_embeddings_1536",
        "top_cat_col": "top_categories_e",
        "top_sim_col": "top_similarities_e",
        "conf_col": "confidence_e",
        "cast": "::vector",
    },
    "F": {
        "emb_col": "embedding_objctx_3072_hv",
        "cat_col": "cat_embedding_3072_hv",
        "top_cat_col": "top_categories_f",
        "top_sim_col": "top_similarities_f",
        "conf_col": "confidence_f",
        "cast": "::halfvec",
    },
    "G": {
        "emb_col": "embedding_objctx_3072_hv",
        "cat_col": "cat_embedding_3072_hv_ivf",
        "top_cat_col": "top_categories_g",
        "top_sim_col": "top_similarities_g",
        "conf_col": "confidence_g",
        "cast": "::halfvec",
    },
    "H": {
        "emb_col": "embedding_objctx_3072_hv",
        "cat_col": "cat_3072_hv_hnsw_h",
        "top_cat_col": "top_categories_h",
        "top_sim_col": "top_similarities_h",
        "conf_col": "confidence_h",
        "cast": "::halfvec",
        "session": {"hnsw_ef_search": int(os.getenv("H_EF_SEARCH", "64"))},
    },
    "I": {
        "emb_col": "embedding_objctx_3072_hv",
        "cat_col": "cat_3072_hv_ivf_i",
        "top_cat_col": "top_categories_i",
        "top_sim_col": "top_similarities_i",
        "conf_col": "confidence_i",
        "cast": "::halfvec",
        "session": {"ivf_probes": int(os.getenv("I_PROBES", "10"))},
    },
}


def fetch_pending_ids(conn, method: str, limit: int | None) -> List[int]:
    spec = METHOD_SPECS[method]
    sql = f"""
        SELECT id_contrato_emb
          FROM public.test_contrato_emb
         WHERE {spec['emb_col']} IS NOT NULL
           AND {spec['top_cat_col']} IS NULL
         ORDER BY id_contrato_emb
         {f'LIMIT {int(limit)}' if limit else ''}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall() or []
        return [int(r[0]) for r in rows]


def categorize_batch(conn, method: str, ids: List[int], top_k: int) -> int:
    if not ids:
        return 0
    s = METHOD_SPECS[method]
    # SQL inspirado no 03 produtivo, adaptado para colunas de teste
    sql = f"""
        WITH pending AS (
            SELECT t.id_contrato_emb, t.{s['emb_col']} AS emb
              FROM public.test_contrato_emb t
             WHERE t.id_contrato_emb = ANY(%s::int[])
               AND t.{s['top_cat_col']} IS NULL
               AND t.{s['emb_col']} IS NOT NULL
        ),
        best AS (
            SELECT p.id_contrato_emb,
                   array_agg(c.cod_cat ORDER BY (1 - (c.{s['cat_col']} <=> p.emb)) DESC) AS top_categories,
                   array_agg(ROUND((1 - (c.{s['cat_col']} <=> p.emb))::numeric, 4)::double precision ORDER BY (1 - (c.{s['cat_col']} <=> p.emb)) DESC) AS top_similarities
              FROM pending p
              JOIN LATERAL (
                   SELECT cod_cat, {s['cat_col']}
                     FROM public.test_categoria
                    WHERE {s['cat_col']} IS NOT NULL
                    ORDER BY {s['cat_col']} <=> p.emb
                    LIMIT %s
              ) c ON TRUE
             GROUP BY p.id_contrato_emb
        ),
        scored AS (
            SELECT b.id_contrato_emb,
                   b.top_categories,
                   b.top_similarities,
                   CASE
                     WHEN array_length(b.top_similarities,1) IS NULL
                       OR array_length(b.top_similarities,1) < 2
                       OR b.top_similarities[1] = 0
                       THEN 0.0
                     ELSE ROUND(
                        (1 - EXP(
                          -10 * (
                            COALESCE((
                              SELECT SUM((b.top_similarities[1] - s) * (1.0/(i)))
                                FROM unnest(b.top_similarities[2:]) WITH ORDINALITY AS t(s,i)
                            ), 0) / b.top_similarities[1]
                          )
                        ))::numeric,
                        4
                     )::double precision
                   END AS confidence
              FROM best b
        )
        UPDATE public.test_contrato_emb t
           SET {s['top_cat_col']} = s.top_categories,
               {s['top_sim_col']} = s.top_similarities,
               {s['conf_col']}    = s.confidence
          FROM scored s
         WHERE t.id_contrato_emb = s.id_contrato_emb
           AND t.{s['top_cat_col']} IS NULL
        RETURNING t.id_contrato_emb
    """
    with conn.cursor() as cur:
        cur.execute(sql, (ids, top_k))
        rows = cur.fetchall() or []
        return len(rows)


def apply_session_tuning(conn, method: str):
    """Aplica parâmetros de sessão específicos por método (H/I)."""
    spec = METHOD_SPECS.get(method, {})
    sess = spec.get("session") if spec else None
    if not sess:
        return
    with conn.cursor() as cur:
        if "hnsw_ef_search" in sess:
            try:
                cur.execute("SET LOCAL hnsw.ef_search TO %s", (int(sess["hnsw_ef_search"]),))
            except Exception:
                pass
        if "ivf_probes" in sess:
            try:
                cur.execute("SET LOCAL ivfflat.probes TO %s", (int(sess["ivf_probes"]),))
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Test 03b – Categorização A..I em test_contrato_emb")
    parser.add_argument("--methods", default="A,B,C,D,E,F,G,H,I")
    parser.add_argument("--top-k", type=int, default=int(os.getenv("PNCP_CAT_TOPK", "5")))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("PNCP_CAT_BATCH", "100")))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--h-ef-search", type=int, default=int(os.getenv("H_EF_SEARCH", "64")), help="ef_search para HNSW (método H)")
    parser.add_argument("--i-probes", type=int, default=int(os.getenv("I_PROBES", "10")), help="probes para IVFFLAT (método I)")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    global TRACE
    TRACE = bool(args.trace)
    logging.basicConfig(level=(logging.INFO if TRACE else logging.WARNING), format="%(levelname)s %(message)s")

    methods = [m.strip().upper() for m in args.methods.split(",") if m.strip()]

    with get_conn() as conn:
        results: Dict[str, Any] = {}
        for m in methods:
            ids = fetch_pending_ids(conn, m, args.limit)
            total = len(ids)
            done = 0
            if total == 0:
                results[m] = {"count": 0, "total": 0, "secs": 0.0, "rows_per_sec": None}
                continue
            t0 = time.perf_counter()
            with Progress(SpinnerColumn(), TextColumn(f"Cat {m}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(), TimeRemainingColumn(), transient=False) as progress:
                task = progress.add_task("", total=total)
                for i in range(0, total, args.batch_size):
                    batch_ids = ids[i : i + args.batch_size]
                    # Ajuste de sessão por método, se aplicável
                    if m == "H":
                        METHOD_SPECS["H"]["session"] = {"hnsw_ef_search": int(args.h_ef_search)}
                        apply_session_tuning(conn, "H")
                    elif m == "I":
                        METHOD_SPECS["I"]["session"] = {"ivf_probes": int(args.i_probes)}
                        apply_session_tuning(conn, "I")
                    updated = categorize_batch(conn, m, batch_ids, args.top_k)
                    conn.commit()
                    done += updated
                    progress.update(task, advance=len(batch_ids))
            secs = time.perf_counter() - t0
            rps = (done / secs) if secs > 0 else None
            results[m] = {"count": done, "total": total, "secs": round(secs, 3), "rows_per_sec": (round(rps, 2) if rps is not None else None)}
        summary = {"results": results, "ts": datetime.utcnow().isoformat()}
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
