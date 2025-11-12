#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_cnpj_data_v3

Objetivo
- Evolução da v2: redução de 403 e maior transparência operacional.
- Recursos novos:
  * Barras fixas por worker + painel de métricas agregadas (200/404/403/429/outros).
  * Rate adapter (auto-tune): aumenta intervalo global se picos de 403/429; reduz levemente se estável.
  * Jitter por worker + jitter global.
  * Reprocessa CNPJs pendentes (não inseridos ou com api_json NULL) como na v2.
  * Upsert apenas em sucesso 200.

Env (.env em v1/scripts):
- SOURCE_VIEW=public.vw_fornecedores_pendentes  # já filtrada para evitar retrabalho
- BATCH_SIZE=100
- MAX_WORKERS=10
- GLOBAL_MIN_INTERVAL=0.04   # intervalo inicial mínimo global entre requisições
- GLOBAL_MIN_INTERVAL_MAX=0.25 # teto do intervalo global auto-ajustado
- GLOBAL_MIN_INTERVAL_MIN=0.025 # piso quando estável
- JITTER_MAX=0.05
- PER_THREAD_SLEEP=0.0       # delay opcional adicional por thread
- ADAPT_CHECK_INTERVAL=200   # a cada N requisições reavalia taxa de erro
- HIGH_ERROR_THRESHOLD=0.08  # proporção de (403+429)/total acima disto => aumenta intervalo
- LOW_ERROR_THRESHOLD=0.01   # proporção abaixo disto => tenta reduzir intervalo
- RETRIES_PER_CNPJ=3
- RETRY_429_SLEEP=1.5
- BATCH_LIMIT=0
- ONLY_PENDING=true

Observação:
- Se usar muitos workers e a API continuar devolvendo 403, aumente GLOBAL_MIN_INTERVAL e/ou reduza MAX_WORKERS.
"""
import os
import re
import time
import random
import logging
import threading
from queue import Queue, Empty
from typing import List, Tuple, Optional, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import psycopg2
from psycopg2.extras import RealDictCursor, Json, execute_batch
from dotenv import load_dotenv

from rich.progress import (
    Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn
)
from rich.table import Table  # (não usado mais para painel dinâmico)

API_BASE = "https://api.opencnpj.org"

# Estado global de ritmo
RATE_LOCK = threading.Lock()
LAST_REQ_TS: float = 0.0
GLOBAL_MIN_INTERVAL: float = 0.04
GLOBAL_MIN_INTERVAL_MAX: float = 0.25
GLOBAL_MIN_INTERVAL_MIN: float = 0.025
JITTER_MAX: float = 0.05
ADAPT_CHECK_INTERVAL: int = 200
HIGH_ERROR_THRESHOLD: float = 0.08
LOW_ERROR_THRESHOLD: float = 0.01

# Métricas globais
METRICS_LOCK = threading.Lock()
METRICS: Dict[str, int] = {
    "req": 0,
    "200": 0,
    "404": 0,
    "403": 0,
    "429": 0,
    "5xx": 0,
    "other": 0,
}


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
    # A view já deve conter somente pendentes
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
            if cnpj and re.fullmatch(r"[0-9]{14}", cnpj):
                out.append((cnpj, r.get("razao_social"), int(r.get("contrato_count") or 0)))
        return out


def chunk_list(items: List[Tuple[str, Optional[str], int]], size: int) -> List[List[Tuple[str, Optional[str], int]]]:
    return [items[i : i + size] for i in range(len(items)) if i % size == 0]


def respect_global_rate():
    global LAST_REQ_TS, GLOBAL_MIN_INTERVAL
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
    j = random.uniform(0.0, JITTER_MAX) if JITTER_MAX > 0 else 0.0
    if j > 0:
        time.sleep(j)


def adapt_rate():
    """Avalia métricas e ajusta GLOBAL_MIN_INTERVAL.
    Critério: a cada ADAPT_CHECK_INTERVAL requisições totais.
    - Se (403+429)/req > HIGH_ERROR_THRESHOLD: aumenta interval (até o máximo)
    - Se (403+429)/req < LOW_ERROR_THRESHOLD: reduz interval (até o mínimo)
    """
    global GLOBAL_MIN_INTERVAL
    with METRICS_LOCK:
        total = METRICS["req"]
        if total == 0 or total % ADAPT_CHECK_INTERVAL != 0:
            return
        errors = METRICS["403"] + METRICS["429"]
        ratio = errors / total if total else 0.0
    # Ajuste simples multiplicativo
    if ratio > HIGH_ERROR_THRESHOLD and GLOBAL_MIN_INTERVAL < GLOBAL_MIN_INTERVAL_MAX:
        GLOBAL_MIN_INTERVAL = min(GLOBAL_MIN_INTERVAL * 1.25, GLOBAL_MIN_INTERVAL_MAX)
    elif ratio < LOW_ERROR_THRESHOLD and GLOBAL_MIN_INTERVAL > GLOBAL_MIN_INTERVAL_MIN:
        GLOBAL_MIN_INTERVAL = max(GLOBAL_MIN_INTERVAL * 0.9, GLOBAL_MIN_INTERVAL_MIN)


def record_status(code: int):
    with METRICS_LOCK:
        METRICS["req"] += 1
        if code == 200:
            METRICS["200"] += 1
        elif code == 404:
            METRICS["404"] += 1
        elif code == 403:
            METRICS["403"] += 1
        elif code == 429:
            METRICS["429"] += 1
        elif 500 <= code < 600:
            METRICS["5xx"] += 1
        else:
            METRICS["other"] += 1
    adapt_rate()


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

        code = resp.status_code
        record_status(code)

        if code == 200:
            try:
                return resp.json()
            except Exception:
                logging.error("Resposta 200 inválida (JSON) para %s", cnpj)
                return None
        elif code == 404:
            return None
        elif code == 429:
            if attempt == retries:
                return None
            time.sleep(sleep429 * attempt)
            continue
        elif code == 403:
            if attempt == retries:
                return None
            time.sleep(max(1.0, sleep429) * attempt)
            continue
        elif 500 <= code < 600:
            if attempt == retries:
                return None
            time.sleep(0.75 * attempt)
            continue
        else:
            # Outros códigos (ex: 400) -> não reprocessa
            return None
    return None


def build_metrics_line() -> str:
    with METRICS_LOCK:
        m = METRICS.copy()
    total = m["req"] or 0
    err_ratio = ((m["403"] + m["429"]) / total) if total else 0.0
    return (
        f"REQ:{total} 200:{m['200']} 404:{m['404']} 403:{m['403']} 429:{m['429']} 5xx:{m['5xx']} "
        f"O:{m['other']} Err%:{err_ratio*100:.2f}% Intv:{GLOBAL_MIN_INTERVAL:.3f}s"
    )


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

            progress.update(task_id, total=len(batch), completed=0,
                            description=f"W{worker_idx+1} batch {batch_idx+1}")

            rows_to_upsert: list[tuple] = []
            for (cnpj, razao, _cnt) in batch:
                data = fetch_cnpj(session, cnpj, retries=retries, sleep429=retry429)
                if data is not None:
                    rows_to_upsert.append((cnpj, razao, Json(data)))
                progress.update(task_id, advance=1)
                with total_lock:
                    progress.update(total_task, advance=1)
                # Per thread sleep + pequeno jitter por worker para diversificar
                if per_thread_sleep > 0:
                    time.sleep(per_thread_sleep + random.uniform(0, per_thread_sleep * 0.3))

            try:
                if rows_to_upsert:
                    execute_batch(cur, UPSERT_EMPRESA, rows_to_upsert, page_size=100)
                    conn.commit()
            except Exception as e:
                conn.rollback()
                progress.console.log(f"Erro no upsert do batch {batch_idx+1} W{worker_idx+1}: {e}")

            q.task_done()

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
    MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))
    global GLOBAL_MIN_INTERVAL, GLOBAL_MIN_INTERVAL_MAX, GLOBAL_MIN_INTERVAL_MIN, JITTER_MAX, ADAPT_CHECK_INTERVAL, HIGH_ERROR_THRESHOLD, LOW_ERROR_THRESHOLD
    GLOBAL_MIN_INTERVAL = float(os.environ.get("GLOBAL_MIN_INTERVAL", str(GLOBAL_MIN_INTERVAL)))
    GLOBAL_MIN_INTERVAL_MAX = float(os.environ.get("GLOBAL_MIN_INTERVAL_MAX", str(GLOBAL_MIN_INTERVAL_MAX)))
    GLOBAL_MIN_INTERVAL_MIN = float(os.environ.get("GLOBAL_MIN_INTERVAL_MIN", str(GLOBAL_MIN_INTERVAL_MIN)))
    JITTER_MAX = float(os.environ.get("JITTER_MAX", str(JITTER_MAX)))
    ADAPT_CHECK_INTERVAL = int(os.environ.get("ADAPT_CHECK_INTERVAL", str(ADAPT_CHECK_INTERVAL)))
    HIGH_ERROR_THRESHOLD = float(os.environ.get("HIGH_ERROR_THRESHOLD", str(HIGH_ERROR_THRESHOLD)))
    LOW_ERROR_THRESHOLD = float(os.environ.get("LOW_ERROR_THRESHOLD", str(LOW_ERROR_THRESHOLD)))

    PER_THREAD_SLEEP = float(os.environ.get("PER_THREAD_SLEEP", "0.0"))
    RETRIES_PER_CNPJ = int(os.environ.get("RETRIES_PER_CNPJ", "3"))
    RETRY_429_SLEEP = float(os.environ.get("RETRY_429_SLEEP", "1.5"))
    BATCH_LIMIT = int(os.environ.get("BATCH_LIMIT", "0"))
    # Removido ONLY_PENDING - a view já filtra pendentes

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
        metrics_task = progress.add_task(build_metrics_line(), total=1)
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

        # Loop de monitoramento para atualizar linha de métricas
        while any(t.is_alive() for t in threads):
            progress.update(metrics_task, description=build_metrics_line())
            time.sleep(5)

        for t in threads:
            t.join()

        progress.update(total_task, description=f"{total}/{total}")
        progress.update(metrics_task, description=build_metrics_line())

    logging.info("Concluído. Processados: %s", total)


if __name__ == "__main__":
    main()
