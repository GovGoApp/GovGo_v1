#!/usr/bin/env python3
"""Pipeline 02 - Embeddings para CNAE (nom_nv4).

Gera embeddings OpenAI (text-embedding-3-large) para cada descrição `nom_nv4`
na tabela `public.cnae`, armazenando o vetor em `cnae_emb halfvec(3072)` e
criando um índice IVFFLAT dedicado.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

EMBED_DIM = 3072
DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_BATCH = 64
DEFAULT_LISTS = 200
LOGGER = logging.getLogger("cnae_embeddings")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera embeddings para tabela public.cnae (nom_nv4)")
    parser.add_argument("--env", default=str(Path(__file__).resolve().parent / ".env"), help="Caminho para .env")
    parser.add_argument("--limit", type=int, default=None, help="Limita quantidade de CNAEs processados")
    parser.add_argument("--from-code", dest="from_code", default=None, help="Começa a partir de um cod_nv4 específico")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH, help="Tamanho dos lotes de embeddings")
    parser.add_argument("--lists", type=int, default=DEFAULT_LISTS, help="Parâmetro lists do índice IVFFLAT")
    parser.add_argument("--recompute-all", action="store_true", help="Recalcula mesmo quem já possui embedding")
    parser.add_argument("--dry-run", action="store_true", help="Não persiste alterações, apenas mostra contagem")
    parser.add_argument("--trace", action="store_true", help="Logs detalhados")
    return parser.parse_args()


def configure_logging(trace: bool) -> None:
    logging.basicConfig(level=(logging.DEBUG if trace else logging.INFO), format="%(levelname)s %(message)s")


def load_env(env_path: str) -> None:
    if not Path(env_path).exists():
        raise FileNotFoundError(f".env não encontrado em {env_path}")
    load_dotenv(env_path)


def get_db_conn():
    required = ["SUPABASE_HOST", "SUPABASE_PORT", "SUPABASE_DBNAME", "SUPABASE_USER", "SUPABASE_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis ausentes no .env: {missing}")
    return psycopg2.connect(
        host=os.environ["SUPABASE_HOST"],
        port=int(os.environ["SUPABASE_PORT"]),
        dbname=os.environ["SUPABASE_DBNAME"],
        user=os.environ["SUPABASE_USER"],
        password=os.environ["SUPABASE_PASSWORD"],
    )


def ensure_column(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name   = 'cnae'
               AND column_name  = 'cnae_emb'
            """
        )
        if cur.fetchone() is None:
            LOGGER.info("Adicionando coluna cnae_emb halfvec(3072)...")
            cur.execute(f"ALTER TABLE public.cnae ADD COLUMN cnae_emb halfvec({EMBED_DIM})")
    conn.commit()


def ensure_index(conn, lists: int) -> None:
    lists = max(10, int(lists))
    with conn.cursor() as cur:
        LOGGER.info("Garantindo índice IVFFLAT (cnae_emb_ivfflat)...")
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS cnae_emb_ivfflat
                ON public.cnae USING ivfflat (cnae_emb halfvec_cosine_ops)
                WITH (lists = {lists})
            """
        )
    conn.commit()


def fetch_targets(cur, limit: int | None, from_code: str | None, recompute_all: bool) -> List[Tuple[str, str]]:
    clauses = ["COALESCE(NULLIF(nom_nv4, ''), NULL) IS NOT NULL", "COALESCE(NULLIF(cod_nv4, ''), NULL) IS NOT NULL"]
    params: List[object] = []
    if not recompute_all:
        clauses.append("cnae_emb IS NULL")
    if from_code:
        clauses.append("cod_nv4 >= %s")
        params.append(from_code)
    where_sql = " AND ".join(clauses)
    sql = f"SELECT cod_nv4, nom_nv4 FROM public.cnae WHERE {where_sql} ORDER BY cod_nv4"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall() or []
    return [(r[0], r[1]) for r in rows]


def chunk(seq: Sequence, size: int) -> Iterable[Sequence]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def sanitize(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "Descrição CNAE não informada"
    if len(text) > 8000:
        return text[:8000]
    return text


def embedding_to_halfvec_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vector) + "]"


def generate_embeddings(client, model: str, texts: List[str], retries: int = 3) -> List[List[float]]:
    if OpenAI is None:
        raise RuntimeError("Biblioteca openai não instalada. pip install openai")
    norm = [sanitize(t) for t in texts]
    for attempt in range(retries):
        try:
            resp = client.embeddings.create(model=model, input=norm)
            return [item.embedding for item in resp.data]
        except Exception as exc:  # pragma: no cover - depende de API externa
            wait = (2 ** attempt) + 1
            LOGGER.warning("OpenAI erro (%s). Tentando novamente em %ss...", exc, wait)
            if attempt == retries - 1:
                raise
            time.sleep(wait)
    return []  # unreachable


def persist_embeddings(conn, batch: List[Tuple[str, str]]) -> None:
    if not batch:
        return
    sql = (
        "WITH data (cod_nv4, cnae_emb) AS (VALUES %s) "
        "UPDATE public.cnae AS c SET cnae_emb = data.cnae_emb "
        "FROM data WHERE c.cod_nv4 = data.cod_nv4"
    )
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            sql,
            batch,
            template="(%s, %s::halfvec(3072))",
            page_size=len(batch),
        )
    conn.commit()


def main():
    args = parse_args()
    configure_logging(args.trace)
    load_env(args.env)

    if not os.getenv("OPENAI_API_KEY"):
        LOGGER.error("OPENAI_API_KEY não encontrada no .env")
        sys.exit(2)

    model = os.getenv("OPENAI_MODEL_EMBEDDINGS", DEFAULT_MODEL)
    batch_size = max(1, args.batch_size)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with get_db_conn() as conn:
        ensure_column(conn)
        ensure_index(conn, args.lists)
        with conn.cursor() as cur:
            targets = fetch_targets(cur, args.limit, args.from_code, args.recompute_all)
        LOGGER.info("Total de CNAEs alvo: %s", len(targets))
        if args.dry_run or not targets:
            return
        processed = 0
        for chunk_rows in chunk(targets, batch_size):
            texts = [sanitize(desc) for _, desc in chunk_rows]
            embeddings = generate_embeddings(client, model, texts)
            data = [
                (code, embedding_to_halfvec_literal(vec))
                for (code, _), vec in zip(chunk_rows, embeddings)
            ]
            persist_embeddings(conn, data)
            processed += len(chunk_rows)
            LOGGER.info("Processados: %s/%s", processed, len(targets))

if __name__ == "__main__":
    main()
