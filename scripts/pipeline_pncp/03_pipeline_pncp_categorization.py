#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline PNCP – Etapa 03: Categorização por similaridade (BDS1)
- Simples, idempotente e sem dependências extras (apenas psycopg2-binary, python-dotenv)
- Compatível com execução local e cron do Render
- Usa embeddings existentes (contratacao_emb) e calcula top_k categorias via pgvector
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

# ---------------------------------------------------------------------
# Configuração de ambiente e logging
# ---------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V1_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # .../v1
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

def log_line(msg: str) -> None:
    try:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

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


def get_system_dates(conn) -> Tuple[str, str]:
    """Lê LCD e LED do system_config. Defaults seguros se ausentes."""
    lcd = "20200101"
    led = dt.datetime.now().strftime("%Y%m%d")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'last_categorization_date'")
            row = cur.fetchone()
            if row and row[0]:
                lcd = row[0]
            cur.execute("SELECT value FROM system_config WHERE key = 'last_embedding_date'")
            row = cur.fetchone()
            if row and row[0]:
                led = row[0]
    except Exception as e:
        log_line(f"Aviso ao ler datas do sistema: {e}")
    return lcd, led


def update_last_categorization_date(conn, date_str: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES ('last_categorization_date', %s, 'Última data categorizada (pipeline 03)', CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (date_str,),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_line(f"Erro ao atualizar last_categorization_date: {e}")


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


def calculate_confidence(similarities: List[float]) -> float:
    if not similarities or len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - s for s in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / max(1e-9, top_score)
    # decaimento exponencial
    return round(1 - math.exp(-10 * weighted_gap), 4)


# ---------------------------------------------------------------------
# Seleção dos contratos pendentes e categorização
# ---------------------------------------------------------------------

def get_pending_contracts_for_date(conn, date_yyyymmdd: str) -> List[Dict[str, Any]]:
    target = yyyymmdd_to_date_str(date_yyyymmdd)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT ce.id_contratacao_emb, ce.numero_controle_pncp, ce.embeddings
                FROM contratacao_emb ce
                JOIN contratacao c ON c.numero_controle_pncp = ce.numero_controle_pncp
                WHERE c.data_publicacao_pncp IS NOT NULL
                  AND DATE(c.data_publicacao_pncp) >= %s::date
                  AND DATE(c.data_publicacao_pncp) < (%s::date + INTERVAL '1 day')
                  AND ce.embeddings IS NOT NULL
                  AND ce.top_categories IS NULL
                ORDER BY ce.numero_controle_pncp
                """,
                (target, target),
            )
            rows = cur.fetchall() or []
            return rows
    except Exception as e:
        log_line(f"Erro ao buscar pendentes {date_yyyymmdd}: {e}")
        return []


def compute_top_categories(conn, embedding_vector, top_k: int) -> Tuple[List[str], List[float]] | None:
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT cod_cat, 1 - (cat_embeddings <=> %s::vector) AS similarity
                FROM categoria
                WHERE cat_embeddings IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (embedding_vector, top_k),
            )
            rows = cur.fetchall() or []
            if not rows:
                return None
            cats = [r["cod_cat"] for r in rows]
            sims = [round(float(r["similarity"]), 4) for r in rows]
            return cats, sims
    except Exception as e:
        log_line(f"Erro ao calcular categorias: {e}")
        return None


def update_contract_category(conn, id_contratacao_emb: int, cats: List[str], sims: List[float], conf: float) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contratacao_emb
                   SET top_categories = %s,
                       top_similarities = %s,
                       confidence = %s
                 WHERE id_contratacao_emb = %s
                   AND top_categories IS NULL
                """,
                (cats, sims, conf, id_contratacao_emb),
            )
            updated = cur.rowcount
        return updated > 0
    except Exception as e:
        log_line(f"Erro ao atualizar categoria id={id_contratacao_emb}: {e}")
        return False


def process_date(conn, date_yyyymmdd: str, top_k: int, batch_size: int) -> Dict[str, int]:
    log_line(f"Processando categorização {date_yyyymmdd}...")
    rows = get_pending_contracts_for_date(conn, date_yyyymmdd)
    total = len(rows)
    if total == 0:
        log_line("Sem pendências para a data.")
        return {"success": 0, "skipped": 0, "errors": 0}

    success = 0
    skipped = 0
    errors = 0

    total_batches = math.ceil(total / max(1, batch_size))
    batch_idx = 0
    last_pct = -1
    for i in range(0, total, batch_size):
        batch_idx += 1
        batch = rows[i:i + batch_size]
        try:
            for r in batch:
                comp = compute_top_categories(conn, r["embeddings"], top_k)
                if not comp:
                    skipped += 1
                    continue
                cats, sims = comp
                conf = calculate_confidence(sims)
                if update_contract_category(conn, r["id_contratacao_emb"], cats, sims, conf):
                    success += 1
                else:
                    # já categorizado por outra execução
                    skipped += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            errors += len(batch)
            log_line(f"Erro no lote ({i}-{i+len(batch)-1}): {e}")
        finally:
            done = min(i + batch_size, total)
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Categorização: {pct}% [{bar}] ({done}/{total}) ✓{success} ↷{skipped} ✗{errors}")
                last_pct = pct

    log_line(f"Data {date_yyyymmdd}: {success} categorizados, {skipped} pulados, {errors} erros")
    return {"success": success, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline PNCP 03 – Categorização")
    parser.add_argument("--test", help="Rodar apenas uma data YYYYMMDD")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("PNCP_CAT_BATCH", "200")))
    parser.add_argument("--top-k", type=int, default=int(os.getenv("PNCP_CAT_TOPK", "5")))
    args = parser.parse_args()

    log_line("[3/3] CATEGORIZAÇÃO DE CONTRATOS INICIADA (LCD)")

    conn = get_conn()
    try:
        if args.test:
            dates = [args.test]
            log_line(f"Modo teste: {args.test}")
        else:
            lcd, led = get_system_dates(conn)
            log_line(f"LCD atual: {lcd} | LED atual: {led}")
            # Definir início = LCD+1 até LED
            try:
                start_dt = dt.datetime.strptime(lcd, "%Y%m%d") + dt.timedelta(days=1)
            except Exception:
                start_dt = dt.datetime.now()
            start = start_dt.strftime("%Y%m%d")
            end = led
            dates = build_dates(start, end)

        if dates:
            log_line(f"Intervalo de datas para 03 (LCD→LED): {dates[0]} .. {dates[-1]} ({len(dates)})")
        if not dates:
            log_line("Nenhuma data para processar.")
            return

        total_success = total_skipped = total_errors = 0
        last_processed = None
        for d in dates:
            stats = process_date(conn, d, top_k=args.top_k, batch_size=args.batch_size)
            total_success += stats["success"]
            total_skipped += stats["skipped"]
            total_errors += stats["errors"]
            update_last_categorization_date(conn, d)
            last_processed = d
            log_line(f"LCD atualizado: {d}")

        log_line("CATEGORIZAÇÃO FINALIZADA")
        log_line(f"Datas: {len(dates)} | Sucesso: {total_success} | Pulados: {total_skipped} | Erros: {total_errors}")
        if last_processed:
            log_line(f"LCD atualizado: {last_processed}")
        log_line(f"Log: {os.path.basename(LOG_FILE)}")

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
