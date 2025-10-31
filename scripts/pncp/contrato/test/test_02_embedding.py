#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 02 – Embeddings (Contrato) em test_contrato_emb
- A: vector(3072) -> coluna embedding_3072_2
- B: vector(1536) -> coluna embedding_1536 (modelo text-embedding-3-small)
- C: halfvec(3072) -> coluna embedding_3072_hv (cast ::halfvec)

Seleciona registros de test_contrato_emb faltantes por coluna alvo e busca o texto base em contrato.objeto_contrato.
Opcionalmente, com --text-mode=objctx, usa "categoria_processo_nome :: objeto_contrato".
Simplificação: só geramos dois embeddings concatenados — 1536 (E) e 3072 halfvec (F/G/H/I compartilham a mesma coluna do F).
Mede tempo por método. Usa batch com OpenAI, seguindo o 02 produtivo.
"""
import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ---- Config ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Carrega .env do nível scripts/pncp/.env (subindo dois níveis) e depois um .env local (se existir)
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


def sanitize_text(t: Any) -> str:
    s = (str(t or "").strip() or "sem descrição")
    return s[:8000]


def fetch_targets(conn, method: str, limit: int | None, text_mode: str) -> List[Dict[str, Any]]:
    """Seleciona id_contrato_emb e texto conforme a coluna alvo do método e modo de texto."""
    col_map = {
        "A": "embedding_3072_2",
        "B": "embedding_1536",
        "C": "embedding_3072_hv",
        # Novos métodos (objctx)
        "E": "embedding_objctx_1536",      # 1536 vector
        "F": "embedding_objctx_3072_hv",   # 3072 halfvec
        "G": "embedding_objctx_3072_hv",   # usa a MESMA coluna do F (sem coluna extra)
    }
    target_col = col_map[method]
    if text_mode == "objctx":
        text_expr = "(COALESCE(c.categoria_processo_nome,'') || ' :: ' || COALESCE(c.objeto_contrato,''))"
        text_filter = f"COALESCE(NULLIF(c.categoria_processo_nome, ''), NULL) IS NOT NULL OR COALESCE(NULLIF(c.objeto_contrato, ''), NULL) IS NOT NULL"
    else:
        text_expr = "c.objeto_contrato"
        text_filter = "COALESCE(NULLIF(c.objeto_contrato, ''), NULL) IS NOT NULL"

    sql = f"""
        SELECT t.id_contrato_emb, t.numero_controle_pncp, {text_expr} AS texto
          FROM public.test_contrato_emb t
          JOIN public.contrato c USING (numero_controle_pncp)
         WHERE ({text_filter})
           AND t.{target_col} IS NULL
         ORDER BY t.id_contrato_emb
         {f'LIMIT {int(limit)}' if limit else ''}
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall() or []
        for r in rows:
            r["texto"] = sanitize_text(r["texto"])
        return rows


def batch(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def create_client():
    if OpenAI is None:
        raise RuntimeError("Pacote openai não encontrado. pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente em scripts/pncp/.env")
    return OpenAI(api_key=api_key)


def embed_texts(client, model: str, texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def update_embeddings(conn, method: str, ids: List[int], vectors: List[List[float]]):
    if not ids:
        return 0
    col_cast = {
        "A": ("embedding_3072_2", "::vector"),
        "B": ("embedding_1536", "::vector"),
        "C": ("embedding_3072_hv", "::halfvec"),
        # Novos métodos (objctx)
        "E": ("embedding_objctx_1536", "::vector"),
        "F": ("embedding_objctx_3072_hv", "::halfvec"),
        "G": ("embedding_objctx_3072_hv", "::halfvec"),  # G escreve na mesma coluna do F
    }
    col, cast = col_cast[method]
    # Monta VALUES (id, '[v1,...,vn]')
    values = []
    for idv, vec in zip(ids, vectors):
        emb_str = "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"
        values.append((idv, emb_str))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            f"""
            UPDATE public.test_contrato_emb t
               SET {col} = v.emb {cast}
              FROM (VALUES %s) AS v(id, emb)
             WHERE t.id_contrato_emb = v.id
            """,
            values,
            template="(%s, %s)",
            page_size=1000,
        )
    return len(ids)


def run_method(conn, client, method: str, batch_size: int, limit: int | None, text_mode: str) -> Tuple[int, float]:
    start = time.perf_counter()
    targets = fetch_targets(conn, method, limit, text_mode)
    total = len(targets)
    done = 0
    if total == 0:
        return 0, 0.0

    with Progress(SpinnerColumn(), TextColumn(f"Método {method}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(), TimeRemainingColumn(), transient=False) as progress:
        task = progress.add_task("", total=total)
        for chunk in batch(targets, batch_size):
            texts = [c["texto"] for c in chunk]
            ids = [int(c["id_contrato_emb"]) for c in chunk]
            # Dimensão/modelo por método
            if method in ("B", "E"):
                model = MODEL_SMALL
            else:
                model = MODEL_LARGE
            vecs = embed_texts(client, model, texts)
            updated = update_embeddings(conn, method, ids, vecs)
            conn.commit()
            done += updated
            progress.update(task, advance=len(chunk))
    return done, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description="Test 02 – Embeddings em test_contrato_emb")
    parser.add_argument("--methods", default="A,B,C", help="Quais métodos rodar, ex: A,B,C,E,F,G")
    parser.add_argument("--batch", type=int, default=int(os.getenv("OPENAI_EMB_BATCH", "64")))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--text-mode", choices=["objeto", "objctx"], default="objeto", help="Texto base: objeto (padrão) ou objctx = categoria :: objeto")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    global TRACE
    TRACE = bool(args.trace)
    logging.basicConfig(level=(logging.INFO if TRACE else logging.WARNING), format="%(levelname)s %(message)s")

    methods = [m.strip().upper() for m in args.methods.split(",") if m.strip()]

    client = create_client()
    with get_conn() as conn:
        results = {}
        for m in methods:
            cnt, secs = run_method(conn, client, m, args.batch, args.limit, args.text_mode)
            results[m] = {"count": cnt, "secs": round(secs, 2)}
        print(json.dumps({"results": results, "ts": datetime.utcnow().isoformat()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
