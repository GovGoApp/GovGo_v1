#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 03a – Embeddings de Categoria em test_categoria (A/B/C/D/H/I)
- A: vector(3072) -> cat_embeddings_3072 (já copiado de categoria; só recalcula se --force)
- B: vector(1536) -> cat_embeddings_1536 (modelo text-embedding-3-small)
- C: halfvec(3072) -> cat_embedding_3072_hv (modelo large com cast ::halfvec)
- D: halfvec(3072) -> cat_embedding_3072_hv_ivf (cópia de C, sem recomputar)
- H: halfvec(3072) -> cat_3072_hv_hnsw_h (cópia de C, sem recomputar)
- I: halfvec(3072) -> cat_3072_hv_ivf_i (cópia de D, sem recomputar)
"""
import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Carrega .env de scripts/pncp/.env (subindo dois níveis) e depois um .env local (se existir)
ENV_PATH_PNCP = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".env"))
ENV_PATH_LOCAL = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".env"))
load_dotenv(ENV_PATH_PNCP)
load_dotenv(ENV_PATH_LOCAL)

TRACE = False
MODEL_LARGE = os.getenv("OPENAI_MODEL_EMBEDDINGS") or os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-large"
MODEL_SMALL = "text-embedding-3-small"

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


def create_client():
    if OpenAI is None:
        raise RuntimeError("Pacote openai não encontrado. pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente em scripts/pncp/.env")
    return OpenAI(api_key=api_key)


def fetch_targets(conn, method: str, force: bool) -> List[Dict[str, Any]]:
    col_map = {
        "A": "cat_embeddings_3072",
        "B": "cat_embeddings_1536",
        "C": "cat_embedding_3072_hv",
        # Métodos de cópia
        "D": "cat_embedding_3072_hv_ivf",
        "H": "cat_3072_hv_hnsw_h",
        "I": "cat_3072_hv_ivf_i",
    }
    target_col = col_map[method]
    # nom_cat é a coluna de texto
    # Para D/H/I, apenas retornamos linhas onde destino está NULL (ou todas se force) para realizar cópia
    if method in ("D", "H", "I"):
        if force:
            sql = f"""
                SELECT id_categoria, nom_cat AS texto
                  FROM public.test_categoria
                 ORDER BY id_categoria
            """
        else:
            sql = f"""
                SELECT id_categoria, nom_cat AS texto
                  FROM public.test_categoria
                 WHERE ({target_col}) IS NULL
                 ORDER BY id_categoria
            """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall() or []
            for r in rows:
                t = (r["texto"] or "").strip() or "sem categoria"
                r["texto"] = t[:8000]
            return rows

    if force:
        # Recalcular tudo: não filtrar por NULL
        sql = f"""
            SELECT id_categoria, nom_cat AS texto
              FROM public.test_categoria
             ORDER BY id_categoria
        """
    else:
        sql = f"""
            SELECT id_categoria, nom_cat AS texto
              FROM public.test_categoria
             WHERE ({target_col}) IS NULL
             ORDER BY id_categoria
        """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall() or []
        # Sanitiza
        for r in rows:
            t = (r["texto"] or "").strip() or "sem categoria"
            r["texto"] = t[:8000]
        return rows


def embed_texts(client, model: str, texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def update_embeddings(conn, method: str, ids: List[int], vectors: List[List[float]]):
    if not ids:
        return 0
    col_cast = {
        "A": ("cat_embeddings_3072", "::vector"),
        "B": ("cat_embeddings_1536", "::vector"),
        "C": ("cat_embedding_3072_hv", "::halfvec"),
    }
    col, cast = col_cast[method]
    values = []
    for idv, vec in zip(ids, vectors):
        emb_str = "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"
        values.append((idv, emb_str))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            f"""
            UPDATE public.test_categoria t
               SET {col} = v.emb {cast}
              FROM (VALUES %s) AS v(id, emb)
             WHERE t.id_categoria = v.id
            """,
            values,
            template="(%s, %s)",
            page_size=1000,
        )
    return len(ids)


def copy_column(conn, src_col: str, dst_col: str, force: bool) -> int:
    """Copia embeddings de src_col para dst_col (mesma dimensão/tipo), evitando overwrite se não --force."""
    with conn.cursor() as cur:
        if force:
            cur.execute(
                f"""
                UPDATE public.test_categoria t
                   SET {dst_col} = {src_col}
                """
            )
        else:
            cur.execute(
                f"""
                UPDATE public.test_categoria t
                   SET {dst_col} = {src_col}
                 WHERE {dst_col} IS NULL
                """
            )
        return cur.rowcount or 0


def run_method(conn, client, method: str, batch_size: int, force: bool) -> int:
    # Métodos de cópia não chamam OpenAI
    if method == "D":
        return copy_column(conn, "cat_embedding_3072_hv", "cat_embedding_3072_hv_ivf", force)
    if method == "H":
        return copy_column(conn, "cat_embedding_3072_hv", "cat_3072_hv_hnsw_h", force)
    if method == "I":
        # I copia de D (ivf base) para coluna dedicada de I
        return copy_column(conn, "cat_embedding_3072_hv_ivf", "cat_3072_hv_ivf_i", force)

    targets = fetch_targets(conn, method, force)
    total = len(targets)
    if total == 0:
        return 0
    done = 0
    with Progress(SpinnerColumn(), TextColumn(f"Categorias {method}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(), TimeRemainingColumn(), transient=False) as progress:
        task = progress.add_task("", total=total)
        for i in range(0, total, batch_size):
            chunk = targets[i : i + batch_size]
            texts = [c["texto"] for c in chunk]
            ids = [int(c["id_categoria"]) for c in chunk]
            model = MODEL_SMALL if method == "B" else MODEL_LARGE
            vecs = embed_texts(client, model, texts)
            updated = update_embeddings(conn, method, ids, vecs)
            conn.commit()
            done += updated
            progress.update(task, advance=len(chunk))
    return done


def main():
    parser = argparse.ArgumentParser(description="Test 03a – Embeddings de Categoria (A/B/C/D/H/I)")
    parser.add_argument("--methods", default="B,C,D,H,I", help="Quais métodos rodar (A,B,C,D,H,I). D/H/I apenas copiam de colunas base.")
    parser.add_argument("--batch", type=int, default=int(os.getenv("OPENAI_EMB_BATCH", "64")))
    parser.add_argument("--force", action="store_true", help="Recalcula mesmo se já houver valor")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    global TRACE
    TRACE = bool(args.trace)
    logging.basicConfig(level=(logging.INFO if TRACE else logging.WARNING), format="%(levelname)s %(message)s")

    methods = [m.strip().upper() for m in args.methods.split(",") if m.strip()]
    client = create_client()
    with get_conn() as conn:
        results: Dict[str, Any] = {}
        total = 0
        for m in methods:
            t0 = time.perf_counter()
            cnt = run_method(conn, client, m, args.batch, args.force)
            secs = time.perf_counter() - t0
            rps = (cnt / secs) if secs > 0 else None
            results[m] = {"count": cnt, "secs": round(secs, 3), "rows_per_sec": (round(rps, 2) if rps is not None else None)}
            total += cnt
        summary = {"results": results, "total": total, "ts": datetime.utcnow().isoformat()}
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
