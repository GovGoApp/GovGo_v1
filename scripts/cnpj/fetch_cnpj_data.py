#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_cnpj_data

Objetivo
- Ler fornecedores com >3 contratos (view pendentes) e enriquecer via API OpenCNPJ
- Salvar em public.empresa: (id, cnpj, razao_social, api_json)
- Segue padrões de .env e bibliotecas já usadas em 01_processing.py

Config (.env em v1/scripts):
- SUPABASE_HOST, SUPABASE_PORT, SUPABASE_DBNAME, SUPABASE_USER, SUPABASE_PASSWORD
- SOURCE_VIEW=public.vw_fornecedores_3plus_pendentes
- BATCH_LIMIT=10000 (fallback: BATCH_SIZE)
- SLEEP_BETWEEN=0.03
- RETRIES_PER_CNPJ=3
- RETRY_429_SLEEP=1.5
"""
import os
import re
import time
import logging
import argparse
from typing import List, Tuple, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import psycopg2
from psycopg2.extras import RealDictCursor, Json, execute_batch
from dotenv import load_dotenv

from rich.progress import (
    Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn
)

API_BASE = "https://api.opencnpj.org"


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"accept": "application/json", "user-agent": "GovGo-CNPJ/1.0"})
    return s


def load_env():
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)


def get_db_conn():
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )


DDL_EMPRESA = """
create table if not exists public.empresa (
  id_empresa bigserial primary key,
  cnpj text not null unique,
  razao_social text,
  api_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
"""

UPSERT_EMPRESA = """
insert into public.empresa (cnpj, razao_social, api_json)
values (%s, %s, %s)
on conflict (cnpj) do update
set razao_social = excluded.razao_social,
    api_json = excluded.api_json,
    updated_at = now();
"""


def ensure_table():
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(DDL_EMPRESA)
        conn.commit()


def load_suppliers(view_name: str, limit: Optional[int]) -> List[Tuple[str, Optional[str], int]]:
    base_sql = f"""
        select cnpj, razao_social, contrato_count
        from {view_name}
        order by contrato_count desc
    """
    params: Tuple = tuple()
    if limit is not None and int(limit) > 0:
        sql = base_sql + "\n        limit %s"
        params = (int(limit),)
    else:
        sql = base_sql

    with get_db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        out = []
        for r in rows:
            cnpj = r["cnpj"]
            # proteção extra: garantir 14 dígitos
            if cnpj and re.fullmatch(r"[0-9]{14}", cnpj):
                out.append((cnpj, r.get("razao_social"), int(r.get("contrato_count") or 0)))
        return out


def fetch_cnpj(session: requests.Session, cnpj: str, retries: int, sleep429: float) -> Optional[dict]:
    url = f"{API_BASE}/{cnpj}"
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
        except requests.RequestException as e:
            if attempt == retries:
                logging.error("Falha de rede para %s (%s): %s", cnpj, attempt, e)
                return None
            time.sleep(0.5 * attempt)
            continue

        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                logging.error("Resposta 200 inválida (JSON) para %s", cnpj)
                return None
        elif resp.status_code == 404:
            logging.warning("CNPJ não encontrado: %s", cnpj)
            return None
        elif resp.status_code == 429:
            if attempt == retries:
                logging.warning("Rate limit 429 persistente para %s", cnpj)
                return None
            time.sleep(sleep429 * attempt)
            continue
        elif 500 <= resp.status_code < 600:
            if attempt == retries:
                logging.error("Erro %s na API para %s", resp.status_code, cnpj)
                return None
            time.sleep(0.75 * attempt)
            continue
        else:
            logging.error("Status inesperado %s para %s", resp.status_code, cnpj)
            return None
    return None


def upsert_empresa(cnpj: str, razao_social: Optional[str], api_data: Optional[dict]):
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(UPSERT_EMPRESA, (cnpj, razao_social, Json(api_data) if api_data else None))
        conn.commit()


def upsert_empresa_batch(conn, rows: List[Tuple[str, Optional[str], Optional[Json]]]):
    """Executa upsert em lote usando conexão aberta.

    rows: lista de tuplas (cnpj, razao_social, api_json_adapted)
    """
    if not rows:
        return
    with conn.cursor() as cur:
        execute_batch(cur, UPSERT_EMPRESA, rows, page_size=len(rows))
    conn.commit()


def main():
    load_env()
    # Logs simples (sem prefixo custom)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # CLI args
    parser = argparse.ArgumentParser(description="Enriquecimento OpenCNPJ - v1 (sequencial)")
    parser.add_argument("--limit", type=int, default=None, help="Número de CNPJs a processar (0=todos; default: usa env BATCH_LIMIT ou todos)")
    parser.add_argument("--batch-size", type=int, default=100, help="Tamanho do lote para commit/upsert (<=1 = sem batching)")
    args = parser.parse_args()

    # Passa a usar a view já filtrada de pendentes para evitar retrabalho
    SOURCE_VIEW = os.environ.get("SOURCE_VIEW", "public.vw_fornecedores_pendentes")
    # Fallback para env apenas se --limit não for fornecido
    env_limit_str = (os.environ.get("BATCH_LIMIT") or os.environ.get("BATCH_SIZE") or "0")
    try:
        env_limit = int(env_limit_str)
    except ValueError:
        env_limit = 0
    effective_limit = args.limit if args.limit is not None else env_limit

    SLEEP_BETWEEN = float(os.environ.get("SLEEP_BETWEEN", "0.03"))
    RETRIES_PER_CNPJ = int(os.environ.get("RETRIES_PER_CNPJ", "3"))
    RETRY_429_SLEEP = float(os.environ.get("RETRY_429_SLEEP", "1.5"))
    batch_size = int(args.batch_size or 100)

    logging.info("Garantindo tabela public.empresa...")
    ensure_table()

    logging.info("Carregando fornecedores de %s (limit=%s, batch_size=%s)...", SOURCE_VIEW, (effective_limit if effective_limit and effective_limit > 0 else "todos"), batch_size)
    suppliers = load_suppliers(SOURCE_VIEW, effective_limit if (effective_limit is not None) else None)
    total = len(suppliers)
    logging.info("Total de CNPJs a processar: %s", total)
    if total == 0:
        return

    session = build_session()
    conn = get_db_conn()
    buffer_rows: List[Tuple[str, Optional[str], Optional[Json]]] = []

    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn("[bold]CNPJs[/] {task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task(f"0/{total}", total=total)
        processed = 0

        try:
            for (cnpj, razao, cnt) in suppliers:
                data = fetch_cnpj(session, cnpj, retries=RETRIES_PER_CNPJ, sleep429=RETRY_429_SLEEP)
                # mantém comportamento: upsert mesmo quando data=None (api_json NULL)
                buffer_rows.append((cnpj, razao, Json(data) if data else None))

                # flush por lote
                if batch_size is not None and batch_size > 1 and len(buffer_rows) >= batch_size:
                    upsert_empresa_batch(conn, buffer_rows)
                    buffer_rows.clear()

                # sem batching (commit por CNPJ)
                if batch_size <= 1:
                    upsert_empresa_batch(conn, buffer_rows)
                    buffer_rows.clear()

                processed += 1
                progress.update(task, advance=1, description=f"{processed}/{total}")
                # leve rate-limit para manter margem
                time.sleep(SLEEP_BETWEEN)
        finally:
            # flush final
            if buffer_rows:
                upsert_empresa_batch(conn, buffer_rows)
                buffer_rows.clear()
            conn.close()

    logging.info("Concluído. Processados: %s", total)


if __name__ == "__main__":
    main()