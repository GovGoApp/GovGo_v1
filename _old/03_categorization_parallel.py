#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline PNCP – Etapa 03 (CONTRATO) – Versão Paralela
- Divide os IDs pendentes do dia em N workers e executa categorização (pgvector) em paralelo
- Cada worker abre sua própria conexão e roda UPDATE em lotes (100% SQL) para seu subconjunto
- Logs só com --trace; barra Rich única por dia (percentual + número/total)

Pré-requisitos recomendados de BD (para desempenho):
- Índice pgvector em categoria(cat_embeddings) com opclass de cosine (ex.: ivfflat)
- Índice/UNIQUE em contrato(numero_controle_pncp) para JOIN rápido
- (Opcional) Índice B-tree em contrato(data_atualizacao_global) se for o campo de recorte
"""

import os
import sys
import math
import time
import argparse
import datetime as dt
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED

import psycopg2
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V1_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))  # .../v1
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Carrega .env local do pipeline e como fallback o da raiz v1
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
load_dotenv(os.path.join(V1_ROOT, ".env"))

DB_CONFIG = {
    "host": os.getenv("SUPABASE_HOST", "localhost"),
    "port": int(os.getenv("SUPABASE_PORT", "6543")),
    "dbname": os.getenv("SUPABASE_DBNAME", "postgres"),
    "user": os.getenv("SUPABASE_USER", "postgres"),
    "password": os.getenv("SUPABASE_PASSWORD", ""),
}

TRACE = False

# Keys no system_config
CFG_LCD = "last_categorization_date_contrato"
CFG_LED = "last_embedded_date_contrato"
CFG_LPD = "last_processed_date_contrato"

# Parâmetros padrão
# Converte defaults para int (argparse não converte default automaticamente)
DEFAULT_TOPK = int(os.getenv("PNCP_CAT_TOPK", "5"))
DEFAULT_WORKERS = int(os.getenv("PNCP_CAT_WORKERS", "8"))
DEFAULT_WORKER_BATCH = int(os.getenv("PNCP_CAT_WORKER_BATCH", "800"))

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def log_line(msg: str) -> None:
    if not TRACE:
        return
    try:
        print(msg, flush=True)
    except Exception:
        pass


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_system_dates(conn) -> Tuple[str, str, str]:
    lcd = "20200101"
    today = dt.datetime.now().strftime("%Y%m%d")
    led = today
    lpd = today
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LCD,))
            row = cur.fetchone()
            if row and row[0]:
                lcd = row[0]
            cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LED,))
            row = cur.fetchone()
            if row and row[0]:
                led = row[0]
            cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LPD,))
            row = cur.fetchone()
            if row and row[0]:
                lpd = row[0]
    except Exception as e:
        log_line(f"Aviso ao ler datas do sistema: {e}")
    return lcd, led, lpd


def update_lcd(conn, date_str: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES (%s, %s, 'Última data categorizada (pipeline 03 contrato paralelo)', CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (CFG_LCD, date_str),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_line(f"Erro ao atualizar {CFG_LCD}: {e}")


def yyyymmdd_to_date_str(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def day_bounds_iso(d: str) -> Tuple[str, str]:
    day = yyyymmdd_to_date_str(d)
    d0 = f"{day}T00:00:00"
    d1_dt = dt.datetime.strptime(d, "%Y%m%d") + dt.timedelta(days=1)
    day1 = d1_dt.strftime("%Y-%m-%d")
    d1 = f"{day1}T00:00:00"
    return d0, d1


# ---------------------------------------------------------------------
# Seleção e Atualização (SQL)
# ---------------------------------------------------------------------

def get_pending_ids_for_date(conn, yyyymmdd: str) -> List[int]:
    """Retorna IDs (id_contrato_emb) pendentes para a data recortada por data_atualizacao_global.
    Alinhado ao 02 (contrato), evita cast DATE pesado e usa comparação textual ISO.
    """
    d0, d1 = day_bounds_iso(yyyymmdd)
    log_line(f"[seleção] Dia {yyyymmdd}: bounds {d0} .. {d1}")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ce.id_contrato_emb
                  FROM contrato_emb ce
                  JOIN contrato c ON c.numero_controle_pncp = ce.numero_controle_pncp
                 WHERE ce.embeddings IS NOT NULL
                   AND ce.top_categories IS NULL
                   AND c.data_atualizacao_global >= %s
                   AND c.data_atualizacao_global < %s
                """,
                (d0, d1),
            )
            rows = cur.fetchall() or []
            ids = [r[0] for r in rows]
            log_line(f"[seleção] Dia {yyyymmdd}: pendentes={len(ids)}")
            return ids
    except Exception as e:
        log_line(f"Erro ao buscar pendentes {yyyymmdd}: {e}")
        return []


def update_batch_categories_sql(conn, ids: List[int], top_k: int) -> int:
    if not ids:
        return 0
    try:
        log_line(f"[lote] Atualizando {len(ids)} ids (top_k={top_k})")
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH pending AS (
                    SELECT ce.id_contrato_emb, ce.embeddings
                      FROM contrato_emb ce
                     WHERE ce.id_contrato_emb = ANY(%s::int[])
                       AND ce.top_categories IS NULL
                ),
                best AS (
                    SELECT p.id_contrato_emb,
                           array_agg(s.cod_cat ORDER BY s.sim DESC) AS top_categories,
                           array_agg(s.sim ORDER BY s.sim DESC) AS top_similarities
                      FROM pending p
                  JOIN LATERAL (
                     SELECT c.cod_cat,
                           ROUND((1 - (c.cat_embeddings <=> p.embeddings))::numeric, 4)::double precision AS sim
                       FROM categoria c
                      WHERE c.cat_embeddings IS NOT NULL
                      ORDER BY c.cat_embeddings <=> p.embeddings
                      LIMIT %s
                  ) s ON TRUE
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
                UPDATE contrato_emb ce
                   SET top_categories   = s.top_categories,
                       top_similarities = s.top_similarities,
                       confidence       = s.confidence
                  FROM scored s
                 WHERE ce.id_contrato_emb = s.id_contrato_emb
                   AND ce.top_categories IS NULL
                RETURNING ce.id_contrato_emb
                """,
                (ids, top_k),
            )
            updated_rows = cur.fetchall() or []
            return len(updated_rows)
    except Exception as e:
        log_line(f"Erro na atualização em lote (ids~{len(ids)}): {e}")
        raise


# ---------------------------------------------------------------------
# Paralelismo
# ---------------------------------------------------------------------

def chunk_evenly(items: List[int], parts: int) -> List[List[int]]:
    n = len(items)
    if parts <= 1 or n == 0:
        return [items]
    size = (n + parts - 1) // parts
    return [items[i:i+size] for i in range(0, n, size)]


def worker_batch_job(ids_batch: List[int], top_k: int, work_mem: Optional[str], trace_flag: bool, log_tag: str) -> Tuple[int, int, int]:
    """Executa a atualização para um único sublote de IDs.
    Retorna (attempted, updated, errors) deste sublote.
    """
    attempted = len(ids_batch)
    updated = 0
    errors = 0
    conn = get_conn()
    try:
        if trace_flag:
            try:
                print(f"[worker-start] {log_tag}: ids={attempted} top_k={top_k} work_mem={work_mem}", flush=True)
            except Exception:
                pass
        if work_mem:
            try:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL work_mem TO %s", (work_mem,))
            except Exception:
                pass
        try:
            t0 = time.time()
            if trace_flag:
                try:
                    print(f"[worker-sql] {log_tag}: start", flush=True)
                except Exception:
                    pass
            u = update_batch_categories_sql(conn, ids_batch, top_k)
            updated += u
            dt_ms = int((time.time() - t0) * 1000)
            if trace_flag:
                try:
                    print(f"[worker-sql] {log_tag}: end time={dt_ms}ms updated={u}", flush=True)
                except Exception:
                    pass
            conn.commit()
            if trace_flag:
                try:
                    print(f"[worker-commit] {log_tag}: ok", flush=True)
                except Exception:
                    pass
        except Exception:
            conn.rollback()
            errors += attempted
            if trace_flag:
                try:
                    print(f"[worker-rollback] {log_tag}: erro no sublote (ids={attempted})", flush=True)
                except Exception:
                    pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return attempted, updated, errors


# ---------------------------------------------------------------------
# Orquestração por dia
# ---------------------------------------------------------------------

def process_day_parallel(yyyymmdd: str, top_k: int, workers: int, worker_batch: int) -> Tuple[int, int, int]:
    """Processa um dia com N workers em paralelo, exibindo uma barra por worker.
    Retorna (attempted, updated, errors) do dia.
    """
    log_line(f"Iniciando {yyyymmdd} (workers={workers}, wb={worker_batch})")
    with get_conn() as conn:
        pending = get_pending_ids_for_date(conn, yyyymmdd)
    total = len(pending)
    d0, d1 = day_bounds_iso(yyyymmdd)
    log_line(f"[dia] {yyyymmdd}: total pendentes={total} | bounds={d0}->{d1}")
    if total == 0:
        return 0, 0, 0

    chunks = chunk_evenly(pending, max(1, workers))
    sizes = [len(p) for p in chunks]
    log_line(f"[split] {yyyymmdd}: tamanhos por worker={sizes}")
    attempted = 0
    updated = 0
    errors = 0

    work_mem = os.getenv("PNCP_CAT_WORK_MEM")
    if work_mem:
        log_line(f"[sessão] work_mem={work_mem}")
    log_line(f"[params] top_k={top_k} | workers={workers} | worker_batch={worker_batch}")

    # Barra Rich: uma task por worker
    with Progress(
        SpinnerColumn(style="bright_yellow"),
        TextColumn(f"Dia {yyyymmdd} – Worker [progress.description]{'{task.fields[worker]}'}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:
        # Cria uma task por worker com total = tamanho do chunk
        worker_tasks: List[Optional[int]] = []
        for idx, part in enumerate(chunks):
            total_part = len(part)
            if total_part == 0:
                # Ainda cria task vazia (1/1) para persistência visual
                task_id = progress.add_task("processando", total=1, worker=f"#{idx+1}")
                progress.update(task_id, advance=1)
                worker_tasks.append(task_id)
            else:
                task_id = progress.add_task("processando", total=total_part, worker=f"#{idx+1}")
                worker_tasks.append(task_id)

        # Submete sublotes (por worker) como futures separados
        with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
            futures: set[Any] = set()
            # Mapa: future -> (chunk_idx, att_expected, t0, sub_idx, n_sub)
            future_meta: Dict[Any, Tuple[int, int, float, int, int]] = {}

            # Pré-computa sublotes por chunk
            batches_by_chunk: List[List[List[int]]] = []
            max_batches = 0
            for idx, part in enumerate(chunks):
                part_batches: List[List[int]] = []
                for i in range(0, len(part), worker_batch):
                    part_batches.append(part[i:i+worker_batch])
                batches_by_chunk.append(part_batches)
                if len(part_batches) > max_batches:
                    max_batches = len(part_batches)

            max_inflight = int(os.getenv("PNCP_CAT_MAX_INFLIGHT", str(max(1, workers) * 2)))
            log_line(f"[throttle] max_inflight={max_inflight}")

            def submit_one(idx: int, sub_idx: int):
                ids_batch = batches_by_chunk[idx][sub_idx]
                if not ids_batch:
                    return
                t0 = time.time()
                batch_size = len(ids_batch)
                n_sub = len(batches_by_chunk[idx])
                log_line(f"[submit] {yyyymmdd} worker#{idx+1} sublote {sub_idx+1}/{n_sub} tam={batch_size}")
                log_tag = f"D{yyyymmdd}-W{idx+1}-S{sub_idx+1}/{n_sub}-N{batch_size}"
                fut = ex.submit(worker_batch_job, ids_batch, top_k, work_mem, bool(TRACE), log_tag)
                futures.add(fut)
                future_meta[fut] = (idx, batch_size, t0, sub_idx+1, n_sub)

            def drain_completed(wait_one: bool = False):
                nonlocal attempted, updated, errors
                if not futures:
                    return
                if wait_one:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                else:
                    done, _ = wait(futures, timeout=0)
                for fut in list(done):
                    idx, att_expected, t0, sub_idx, n_sub = future_meta.pop(fut, (None, 0, time.time(), 0, 0))
                    futures.discard(fut)
                    try:
                        att, upd, err = fut.result()
                    except Exception as ex_err:
                        att, upd, err = att_expected, 0, att_expected
                        log_line(f"[erro] {yyyymmdd} worker#{(idx or 0)+1} sublote {sub_idx}/{n_sub}: {ex_err}")
                    dt_ms = int((time.time() - t0) * 1000)
                    attempted += att
                    updated += upd
                    errors += err
                    if idx is not None:
                        log_line(f"[done] {yyyymmdd} worker#{idx+1} sublote {sub_idx}/{n_sub}: time={dt_ms}ms attempted={att} updated={upd} errors={err}")
                        task_id = worker_tasks[idx]
                        if task_id is not None and len(chunks[idx]) > 0:
                            progress.update(task_id, advance=att)

            # Round-robin: intercalar sublotes entre chunks para progresso equilibrado
            for sub_idx in range(max_batches):
                for idx in range(len(chunks)):
                    if sub_idx < len(batches_by_chunk[idx]) and len(batches_by_chunk[idx][sub_idx]) > 0:
                        submit_one(idx, sub_idx)
                        if len(futures) >= max_inflight:
                            drain_completed(wait_one=True)

            # Drena o restante
            while futures:
                drain_completed(wait_one=True)

    return attempted, updated, errors


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    global TRACE
    parser = argparse.ArgumentParser(description="Pipeline 03 (Contrato) – Paralelo")
    parser.add_argument("--tipo", choices=["diario", "periodo"], default="diario")
    parser.add_argument("--diario", action="store_true", help="Atalho para --tipo diario")
    parser.add_argument("--from", dest="from_date", help="YYYYMMDD")
    parser.add_argument("--to", dest="to_date", help="YYYYMMDD")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOPK)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--worker-batch-size", type=int, default=DEFAULT_WORKER_BATCH)
    args = parser.parse_args()

    TRACE = bool(args.trace)

    today = dt.datetime.now().strftime("%Y%m%d")

    with get_conn() as conn:
        lcd, led, lpd = get_system_dates(conn)
        if TRACE:
            log_line(f"[datas] LCD={lcd} LED={led} LPD={lpd} TODAY={today}")

        # Janela padrão
        if args.from_date or args.to_date or args.tipo == "periodo":
            start = args.from_date or lcd
            end = args.to_date or min(led, lpd, today)
        else:
            # diario
            try:
                start = lcd if lcd == today else (dt.datetime.strptime(lcd, "%Y%m%d") + dt.timedelta(days=1)).strftime("%Y%m%d")
            except Exception:
                start = today
            end = min(led, lpd, today)

        end = min(end, led, lpd, today)
        if not start or not end or start > end:
            log_line("Nenhuma data para processar.")
            return

        # Monta lista de dias
        cur = dt.datetime.strptime(start, "%Y%m%d")
        end_dt = dt.datetime.strptime(end, "%Y%m%d")
        days: List[str] = []
        while cur <= end_dt:
            days.append(cur.strftime("%Y%m%d"))
            cur += dt.timedelta(days=1)
        if TRACE:
            log_line(f"[janela] start={start} end={end} dias={len(days)} -> {days[:3]}{'...' if len(days)>3 else ''}")

    total_attempted = total_updated = total_errors = 0

    for d in days:
        att, upd, err = process_day_parallel(d, top_k=args.top_k, workers=args.workers, worker_batch=args.worker_batch_size)
        total_attempted += att
        total_updated += upd
        total_errors += err
        with get_conn() as conn:
            update_lcd(conn, d)
        log_line(f"[resumo-dia] {d}: attempted={att} updated={upd} errors={err}")

    log_line(f"[resumo-geral] attempted={total_attempted} updated={total_updated} errors={total_errors}")


if __name__ == "__main__":
    main()
