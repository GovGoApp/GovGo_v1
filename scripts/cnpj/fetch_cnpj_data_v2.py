#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_cnpj_data_v2

Objetivo
- Processar fornecedores com >3 contratos em paralelo usando ThreadPool
- 10 workers simultâneos (configurável), cada um processa batches de 100 itens (configurável)
- Barra de progresso Rich fixa por worker (uma linha por worker), reset por batch
- Salvar em public.empresa: (id, cnpj, razao_social, api_json)

Padrões do projeto:
- Lê .env de v1/scripts/.env (SUPABASE_HOST, SUPABASE_PORT, SUPABASE_DBNAME, SUPABASE_USER, SUPABASE_PASSWORD)
- Usa requests + Retry, psycopg2, dotenv, rich
- Sem prefixos customizados em logs

Env suportadas (opcionais):
- SOURCE_VIEW=public.vw_fornecedores_pendentes (default já filtrada)
- BATCH_SIZE=100
- MAX_WORKERS=10
- PER_THREAD_SLEEP=0.25
- RETRIES_PER_CNPJ=3
- RETRY_429_SLEEP=1.5
- BATCH_LIMIT=0 (0 ou vazio = sem limite)
 - ONLY_PENDING=true (se true, filtra CNPJs já existentes em public.empresa; também considera api_json NULL como pendente)
"""
import os
import re
import time
import logging
import threading
from queue import Queue, Empty
import random
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


def load_suppliers(view_name: str, limit: int | None) -> List[Tuple[str, Optional[str], int]]:
    # A view já deve retornar apenas pendentes (não presentes ou api_json NULL)
    sql = f"""
        SELECT cnpj, razao_social, contrato_count
        FROM {view_name}
        ORDER BY contrato_count DESC
        {"LIMIT %s" if limit and limit > 0 else ""}
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        if limit and limit > 0:
            cur.execute(sql, (limit,))
        else:
            cur.execute(sql)
        rows = cur.fetchall()
        out = []
        for r in rows:
            cnpj = r["cnpj"]
            # Garantir 14 dígitos
            if cnpj and re.fullmatch(r"[0-9]{14}", cnpj):
                out.append((cnpj, r.get("razao_social"), int(r.get("contrato_count") or 0)))
        return out


def chunk_list(items: List[Tuple[str, Optional[str], int]], size: int) -> List[List[Tuple[str, Optional[str], int]]]:
    return [items[i : i + size] for i in range(len(items)) if i % size == 0]


# Controle global de taxa (token bucket simples)
RATE_LOCK = threading.Lock()
LAST_REQ_TS: float = 0.0
GLOBAL_MIN_INTERVAL: float = 0.04  # atualizado via env em main
JITTER_MAX: float = 0.05           # atualizado via env em main

def respect_global_rate():
    global LAST_REQ_TS
    now = time.time()
    with RATE_LOCK:
        next_ts = LAST_REQ_TS + GLOBAL_MIN_INTERVAL
        if now < next_ts:
            sleep_for = next_ts - now
            LAST_REQ_TS = next_ts
        else:
            sleep_for = 0.0
            LAST_REQ_TS = now
    if sleep_for > 0:
        time.sleep(sleep_for)
    # pequeno jitter para quebrar padrão
    j = random.uniform(0.0, JITTER_MAX) if JITTER_MAX > 0 else 0.0
    if j > 0:
        time.sleep(j)


def fetch_cnpj(session: requests.Session, cnpj: str, retries: int, sleep429: float) -> Optional[dict]:
    url = f"{API_BASE}/{cnpj}"
    for attempt in range(1, retries + 1):
        try:
            respect_global_rate()
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
        elif resp.status_code == 403:
            # Tratado como proteção/limite (Cloudflare/WAF). Tentar novamente com backoff.
            if attempt == retries:
                logging.warning("403 persistente (possível proteção) para %s", cnpj)
                return None
            time.sleep(max(1.0, sleep429) * attempt)
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


def worker_loop(worker_idx: int, q: Queue, progress: Progress, task_id: int,
                 per_thread_sleep: float, retries: int, retry429: float,
                 total_task: int, total_lock: threading.Lock):
    session = build_session()
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        while True:
            try:
                batch_idx, batch = q.get_nowait()
            except Empty:
                break

            # Reset barra do worker para o novo batch
            progress.update(task_id, total=len(batch), completed=0,
                            description=f"W{worker_idx+1} batch {batch_idx+1}")

            rows_to_upsert: list[tuple] = []
            processed_in_batch = 0

            for (cnpj, razao, _cnt) in batch:
                data = fetch_cnpj(session, cnpj, retries=retries, sleep429=retry429)
                # Só upsert se obteve JSON válido (evita marcar como processado na tabela e perder na view pendente)
                if data is not None:
                    rows_to_upsert.append((cnpj, razao, Json(data)))
                processed_in_batch += 1
                progress.update(task_id, advance=1)
                with total_lock:
                    progress.update(total_task, advance=1)
                time.sleep(per_thread_sleep)

            # Upsert do batch em uma transação
            try:
                if rows_to_upsert:
                    execute_batch(cur, UPSERT_EMPRESA, rows_to_upsert, page_size=100)
                    conn.commit()
            except Exception as e:
                conn.rollback()
                # Log acima das barras sem quebrar layout
                progress.console.log(f"Erro no upsert do batch {batch_idx+1} pelo worker {worker_idx+1}: {e}")

            q.task_done()

        # Finalização do worker
        progress.update(task_id, description=f"W{worker_idx+1} concluído")

    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def main():
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    SOURCE_VIEW = os.environ.get("SOURCE_VIEW", "public.vw_fornecedores_pendentes")
    BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))
    MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "1"))
    PER_THREAD_SLEEP = float(os.environ.get("PER_THREAD_SLEEP", "0.5"))
    RETRIES_PER_CNPJ = int(os.environ.get("RETRIES_PER_CNPJ", "3"))
    RETRY_429_SLEEP = float(os.environ.get("RETRY_429_SLEEP", "1.5"))
    BATCH_LIMIT = int(os.environ.get("BATCH_LIMIT", "0"))
    global GLOBAL_MIN_INTERVAL, JITTER_MAX
    GLOBAL_MIN_INTERVAL = float(os.environ.get("GLOBAL_MIN_INTERVAL", "0.04"))
    JITTER_MAX = float(os.environ.get("JITTER_MAX", "0.05"))

    logging.info("Garantindo tabela public.empresa...")
    ensure_table()

    logging.info("Carregando fornecedores de %s ...", SOURCE_VIEW)
    suppliers = load_suppliers(SOURCE_VIEW, BATCH_LIMIT if BATCH_LIMIT > 0 else None)
    total = len(suppliers)
    logging.info("Total de CNPJs a processar: %s", total)
    if total == 0:
        return

    batches = chunk_list(suppliers, BATCH_SIZE)
    num_batches = len(batches)
    logging.info("Total de batches: %s (tamanho=%s)", num_batches, BATCH_SIZE)

    q: Queue = Queue()
    for idx, batch in enumerate(batches):
        q.put((idx, batch))

    total_lock = threading.Lock()

    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn("[bold]CNPJs[/] {task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
        refresh_per_second=10,
    ) as progress:
        total_task = progress.add_task(f"0/{total}", total=total)
        # Cria uma task fixa por worker
        worker_tasks: list[int] = []
        for w in range(MAX_WORKERS):
            tid = progress.add_task(f"W{w+1} aguardando...", total=1)
            worker_tasks.append(tid)

        threads: list[threading.Thread] = []
        for w in range(MAX_WORKERS):
            t = threading.Thread(
                target=worker_loop,
                args=(w, q, progress, worker_tasks[w], PER_THREAD_SLEEP, RETRIES_PER_CNPJ, RETRY_429_SLEEP, total_task, total_lock),
                daemon=True,
            )
            threads.append(t)
            t.start()

        # Aguarda término
        for t in threads:
            t.join()

        # Finaliza barra total
        progress.update(total_task, description=f"{total}/{total}")

    logging.info("Concluído. Processados: %s", total)


if __name__ == "__main__":
    main()