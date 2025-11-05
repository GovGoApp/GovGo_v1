#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline PNCP – Etapa 03 (CONTRATO): Categorização por similaridade (BDS1)
- Simples, idempotente e sem dependências extras (apenas psycopg2-binary, python-dotenv)
- Compatível com execução local e cron do Render
- Usa embeddings_hv existentes (contrato_emb.embeddings_hv) e calcula top_k categorias via pgvector (halfvec)
- Logs detalhados apenas com --trace; barra de progresso única por dia sempre visível
"""

import os
import sys
import time
import math
import argparse
import datetime as dt
from typing import List, Tuple, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, TaskProgressColumn, SpinnerColumn

# ---------------------------------------------------------------------
# Configuração de ambiente e logging
# ---------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V1_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))  # .../v1
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Carrega .env local da pasta do pipeline e, como fallback, o .env da raiz v1
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
load_dotenv(os.path.join(V1_ROOT, ".env"))

DB_CONFIG = {
    "host": os.getenv("SUPABASE_HOST", "localhost"),
    "port": os.getenv("SUPABASE_PORT", "6543"),
    "database": os.getenv("SUPABASE_DBNAME", "postgres"),
    "user": os.getenv("SUPABASE_USER", "postgres"),
    "password": os.getenv("SUPABASE_PASSWORD", ""),
}

PIPELINE_TIMESTAMP = os.getenv("PIPELINE_TIMESTAMP") or dt.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"log_{PIPELINE_TIMESTAMP}.log")

TRACE_ENABLED = False

def log_line(msg: str) -> None:
    """Loga apenas quando --trace estiver habilitado (não imprime barra/linhas no modo silencioso)."""
    if not TRACE_ENABLED:
        return
    try:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def table_has_column(conn, schema: str, table: str, column: str) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = %s AND table_name = %s AND column_name = %s
                """,
                (schema, table, column),
            )
            return cur.fetchone() is not None
    except Exception:
        return False

def get_conn(max_attempts: int = 3, retry_delay: int = 5):
    attempt = 1
    while attempt <= max_attempts:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.set_session(autocommit=False)
            return conn
        except psycopg2.Error as e:
            log_line(f"Erro ao conectar ao banco (tentativa {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(retry_delay)
                attempt += 1
            else:
                raise


def get_system_dates(conn) -> Tuple[str, str, str]:
    """Lê LCD, LED e LPD de system_config (contrato). Defaults seguros se ausentes.
    - LCD: last_categorization_date_contrato
    - LED: last_embedded_date_contrato
    - LPD: last_processed_date_contrato
    """
    lcd = "20200101"
    today = dt.datetime.now().strftime("%Y%m%d")
    led = today
    lpd = today
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'last_categorization_date_contrato'")
            row = cur.fetchone()
            if row and row[0]:
                lcd = row[0]
            cur.execute("SELECT value FROM system_config WHERE key = 'last_embedded_date_contrato'")
            row = cur.fetchone()
            if row and row[0]:
                led = row[0]
            cur.execute("SELECT value FROM system_config WHERE key = 'last_processed_date_contrato'")
            row = cur.fetchone()
            if row and row[0]:
                lpd = row[0]
    except Exception as e:
        log_line(f"Aviso ao ler datas do sistema: {e}")
    return lcd, led, lpd


def update_last_categorization_date(conn, date_str: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES ('last_categorization_date_contrato', %s, 'Última data categorizada (pipeline 03 contrato)', CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (date_str,),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_line(f"Erro ao atualizar last_categorization_date_contrato: {e}")


def build_dates(start: str, end: str) -> List[str]:
    dates: List[str] = []
    try:
        cur = dt.datetime.strptime(start, "%Y%m%d")
        end_dt = dt.datetime.strptime(end, "%Y%m%d")
        while cur <= end_dt:
            dates.append(cur.strftime("%Y%m%d"))
            cur += dt.timedelta(days=1)
    except Exception as e:
        log_line(f"Erro ao gerar datas: {e}")
    return dates


def yyyymmdd_to_date_str(d: str) -> str:
    """Converte YYYYMMDD -> YYYY-MM-DD."""
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def day_bounds_iso(d: str) -> Tuple[str, str]:
    """Retorna limites ISO para comparação textual [day_start, next_day_start)."""
    day = yyyymmdd_to_date_str(d)
    d0 = f"{day}T00:00:00"
    d1_dt = dt.datetime.strptime(d, "%Y%m%d") + dt.timedelta(days=1)
    day1 = d1_dt.strftime("%Y-%m-%d")
    d1 = f"{day1}T00:00:00"
    return d0, d1


def calculate_confidence(similarities: List[float]) -> float:
    # Não usada diretamente (cálculo é feito em SQL), mantida por simetria
    if not similarities or len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - s for s in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / max(1e-9, top_score)
    return round(1 - math.exp(-10 * weighted_gap), 4)

# ---------------------------------------------------------------------
# Seleção dos contratos pendentes e categorização
# ---------------------------------------------------------------------

def get_pending_ids_for_date(conn, date_yyyymmdd: str) -> List[int]:
    """Retorna apenas IDs (id_contrato_emb) pendentes para a data.
    Junta contrato_emb com contrato por id_contrato e filtra por janela diária
    usando a DATA (YYYY-MM-DD) derivada de contrato.data_atualizacao_global (TEXT).
    Observação: como o campo é TEXT e pode ter 'T' ou espaço entre data e hora,
    evitamos comparação lexical de timestamps e comparamos apenas a parte da data (LEFT(...,10)).
    Evita trafegar embeddings para o cliente.
    """
    day = yyyymmdd_to_date_str(date_yyyymmdd)
    log_line(f"[seleção] Dia {date_yyyymmdd}: filtro por data = {day}")

    # Descobre colunas disponíveis em contrato_emb para decidir JOIN
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'contrato_emb'
                   AND column_name IN ('id_contrato','numero_controle_pncp')
                """
            )
            cols = {r[0] for r in (cur.fetchall() or [])}
    except Exception as e:
        log_line(f"Aviso ao inspecionar colunas de contrato_emb: {e}")
        cols = set()

    join_mode = 'none'
    if 'id_contrato' in cols:
        join_mode = 'id_contrato'
    elif 'numero_controle_pncp' in cols:
        join_mode = 'numero_controle_pncp'

    try:
        with conn.cursor() as cur:
            if join_mode == 'id_contrato':
                # Preferido: data pela tabela contrato; fallback para created_at do emb quando data estiver vazia
                cur.execute(
                    """
                    SELECT ce.id_contrato_emb
                      FROM contrato_emb ce
                      JOIN contrato c ON c.id_contrato = ce.id_contrato
                     WHERE ce.embeddings_hv IS NOT NULL
                       AND ce.top_categories IS NULL
                       AND (
                            LEFT(COALESCE(NULLIF(c.data_atualizacao_global,''),'') , 10) = %s
                         OR (c.data_atualizacao_global IS NULL OR c.data_atualizacao_global = '')
                            AND LEFT(ce.created_at::text, 10) = %s
                       )
                    """,
                    (day, day),
                )
            elif join_mode == 'numero_controle_pncp':
                cur.execute(
                    """
                    SELECT ce.id_contrato_emb
                      FROM contrato_emb ce
                      JOIN contrato c ON c.numero_controle_pncp = ce.numero_controle_pncp
                                                WHERE ce.embeddings_hv IS NOT NULL
                       AND ce.top_categories IS NULL
                       AND (
                            LEFT(COALESCE(NULLIF(c.data_atualizacao_global,''),'') , 10) = %s
                         OR (c.data_atualizacao_global IS NULL OR c.data_atualizacao_global = '')
                            AND LEFT(ce.created_at::text, 10) = %s
                       )
                    """,
                    (day, day),
                )
            else:
                # Sem JOIN possível: usa apenas created_at do emb (cobre bases antigas/atípicas)
                                cur.execute(
                    """
                    SELECT ce.id_contrato_emb
                      FROM contrato_emb ce
                                                WHERE ce.embeddings_hv IS NOT NULL
                       AND ce.top_categories IS NULL
                       AND LEFT(ce.created_at::text, 10) = %s
                    """,
                    (day,),
                )

            ids = [r[0] for r in (cur.fetchall() or [])]
            log_line(f"[seleção] Dia {date_yyyymmdd}: join={join_mode} pendentes={len(ids)}")
            return ids
    except Exception as e:
        log_line(f"Erro ao buscar IDs pendentes {date_yyyymmdd}: {e}")
        return []


def update_batch_categories_sql(conn, ids: List[int], top_k: int) -> int:
    """Calcula top_k categorias totalmente no banco e atualiza contrato_emb em lote.
    Retorna quantidade de linhas atualizadas (sucesso). Não faz commit.
    """
    if not ids:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH pending AS (
                                        SELECT ce.id_contrato_emb,
                                                     ce.embeddings_hv AS emb_hv
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
                                                     ROUND((1 - (c.cat_embeddings_hv <=> p.emb_hv))::numeric, 4)::double precision AS sim
                       FROM categoria c
                      WHERE c.cat_embeddings_hv IS NOT NULL
                                            ORDER BY c.cat_embeddings_hv <=> p.emb_hv
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


def process_date(conn, date_yyyymmdd: str, top_k: int, batch_size: int, progress: Progress | None = None) -> Dict[str, int]:
    log_line("")
    log_line(f"Categorizando contratos {date_yyyymmdd}...")

    pending_ids = get_pending_ids_for_date(conn, date_yyyymmdd)
    total = len(pending_ids)

    # Cria uma barra única por data (sempre visível). Para total=0, mostramos completa imediatamente.
    task_id = None
    if progress is not None:
        desc = f"{date_yyyymmdd}"
        if total == 0:
            task_id = progress.add_task(desc, total=1)
            progress.update(task_id, completed=1)
        else:
            task_id = progress.add_task(desc, total=total)

    if total == 0:
        log_line("Sem pendências para a data.")
        return {"success": 0, "skipped": 0, "errors": 0}

    success = 0
    skipped = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch_ids = pending_ids[i:i + batch_size]
        attempted = len(batch_ids)
        try:
            updated = update_batch_categories_sql(conn, batch_ids, top_k)
            success += updated
            skipped += max(0, attempted - updated)
            conn.commit()
        except Exception as e:
            conn.rollback()
            errors += attempted
            log_line(f"Erro no lote ({i}-{i+attempted-1}): {e}")
        finally:
            if progress is not None and task_id is not None and total > 0:
                progress.update(task_id, advance=attempted)

    log_line(f"Data {date_yyyymmdd}: {success} categorizados, {skipped} pulados, {errors} erros")
    return {"success": success, "skipped": skipped, "errors": errors}

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    global TRACE_ENABLED

    parser = argparse.ArgumentParser(description="Pipeline PNCP 03 – Categorização (CONTRATO)")
    parser.add_argument("--tipo", choices=["diario", "periodo"], help="Modo de execução: diario ou periodo")
    parser.add_argument("--diario", action="store_true", help="Atalho para --tipo diario")
    parser.add_argument("--from", dest="from_date", help="Data inicial YYYYMMDD")
    parser.add_argument("--to", dest="to_date", help="Data final YYYYMMDD")
    parser.add_argument("--trace", action="store_true", help="Exibe logs detalhados")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("PNCP_CAT_BATCH", "100")))
    parser.add_argument("--top-k", type=int, default=int(os.getenv("PNCP_CAT_TOPK", "5")))
    parser.add_argument("--h-ef-search", dest="h_ef_search", type=int, default=int(os.getenv("PNCP_H_EF_SEARCH", "0")), help="Define hnsw.ef_search para consultas HNSW (0 = não ajustar)")
    args = parser.parse_args()

    TRACE_ENABLED = bool(args.trace)

    log_line("[3/3] CATEGORIZAÇÃO DE CONTRATOS (LCD_CONTRATO)")

    conn = get_conn()
    try:
        # Pré-checagem: exigir colunas HV necessárias
        if not table_has_column(conn, 'public', 'contrato_emb', 'embeddings_hv'):
            log_line("Erro: public.contrato_emb.embeddings_hv não encontrada. Crie/popule embeddings_hv antes da categorização.")
            return
        if not table_has_column(conn, 'public', 'categoria', 'cat_embeddings_hv'):
            log_line("Erro: public.categoria.cat_embeddings_hv não encontrada. Gere cat_embeddings_hv antes da categorização.")
            return
        # Ajuste opcional de sessão para performance
        try:
            work_mem = os.getenv("PNCP_CAT_WORK_MEM")
            if work_mem:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL work_mem TO %s", (work_mem,))
        except Exception as e:
            log_line(f"Aviso ao ajustar work_mem: {e}")

        # Ajuste opcional de hnsw.ef_search (sessão)
        try:
            if args.h_ef_search and args.h_ef_search > 0:
                with conn.cursor() as cur:
                    cur.execute("SET hnsw.ef_search TO %s", (args.h_ef_search,))
        except Exception as e:
            log_line(f"Aviso ao ajustar hnsw.ef_search: {e}")

        # Determinação do intervalo de datas
        today = dt.datetime.now().strftime("%Y%m%d")
        lcd, led, lpd = get_system_dates(conn)
        log_line(f"Datas do sistema: LCD={lcd} | LED={led} | LPD={lpd} | TODAY={today}")

        # Se --tipo/--diario/--from/--to não informados, usar janela padrão:
        # start = (LCD == hoje ? LCD : LCD + 1)
        # end = min(LED, LPD, hoje)
        start = None
        end = None

        if args.from_date or args.to_date or args.tipo == "periodo":
            # Execução por período explícito
            start = args.from_date or lcd
            end = args.to_date or min(led, lpd, today)
        elif args.tipo == "diario" or args.diario or (args.tipo is None and not args.from_date and not args.to_date):
            # Execução diária padrão com base nas datas do sistema
            try:
                if lcd == today:
                    start = lcd
                else:
                    start_dt = dt.datetime.strptime(lcd, "%Y%m%d") + dt.timedelta(days=1)
                    start = start_dt.strftime("%Y%m%d")
            except Exception:
                start = today
            end = min(led, lpd, today)
        else:
            # Fallback conservador
            start = lcd
            end = min(led, lpd, today)

        # Regra de segurança: clamp end
        end = min(end, led, lpd, today)
        log_line(f"Janela base (após clamp): start={start} end={end}")

        # LCD<=LED<=LPD<=CURRENT_DAY: por que é assim?
        # - LCD (last_categorization_date_contrato) é o ponto de recomeço; avançamos a partir dele sem reprocessar.
        # - LED (last_embedded_date_contrato) limita o que já tem embeddings; não categorizamos além de LED.
        # - LPD (last_processed_date_contrato) limita o que foi ingerido; embeddings não devem superar a ingestão.
        # - CURRENT_DAY é teto natural; nunca planejar futuro.

        if start is None or end is None or start > end:
            log_line("Nenhuma data para processar.")
            return

        dates = build_dates(start, end)
        if dates:
            log_line(f"Intervalo de datas 03 (LCD→min(LED,LPD)): {dates[0]} .. {dates[-1]} ({len(dates)})")
        else:
            log_line("Nenhuma data para processar.")
            return

        total_success = total_skipped = total_errors = 0
        last_processed = None

        # Barra Rich persistente por data
        with Progress(
            SpinnerColumn(style="bright_yellow"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=False,
        ) as progress:
            for d in dates:
                stats = process_date(conn, d, top_k=args.top_k, batch_size=args.batch_size, progress=progress)
                total_success += stats["success"]
                total_skipped += stats["skipped"]
                total_errors += stats["errors"]
                update_last_categorization_date(conn, d)
                last_processed = d
                log_line(f"LCD_CONTRATO atualizado: {d}")

        log_line("CATEGORIZAÇÃO (CONTRATO) FINALIZADA")
        log_line(f"Datas: {len(dates)} | Sucesso: {total_success} | Pulados: {total_skipped} | Erros: {total_errors}")
        if last_processed:
            log_line(f"LCD_CONTRATO atualizado: {last_processed}")
        if TRACE_ENABLED:
            log_line(f"Log: {os.path.basename(LOG_FILE)}")

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
