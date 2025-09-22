#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline PNCP – Etapa 02: Geração de Embeddings (BDS1)
- Simples, estável e compatível com local/Render
- Sem Rich, sem numpy, sem pool complexo
"""

import os
import sys
import time
import json
import math
import argparse
import datetime as dt
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------
# Ambiente e logging
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

OPENAI_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
DEFAULT_BATCH = int(os.getenv("OPENAI_EMB_BATCH", "32"))

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
# Conexão DB e system_config
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


def get_last_embedding_date(conn) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'last_embedding_date'")
            row = cur.fetchone()
            return row[0] if row else "20200101"
    except Exception as e:
        log_line(f"Aviso ao ler last_embedding_date: {e}")
        return "20200101"


def get_last_processed_date(conn) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'last_processed_date'")
            row = cur.fetchone()
            return row[0] if row else dt.datetime.now().strftime("%Y%m%d")
    except Exception as e:
        log_line(f"Aviso ao ler last_processed_date: {e}")
        return dt.datetime.now().strftime("%Y%m%d")


def update_last_embedding_date(conn, date_str: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES ('last_embedding_date', %s, 'Última data processada (pipeline 02)', CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (date_str,),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_line(f"Erro ao salvar last_embedding_date: {e}")

# ---------------------------------------------------------------------
# Seleção de contratações (por data)
# ---------------------------------------------------------------------

def get_contratacoes_for_date(conn, date_str: str) -> List[Dict[str, Any]]:
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    query = """
        SELECT 
            c.numero_controle_pncp,
            c.objeto_compra,
            COALESCE(string_agg(COALESCE(i.descricao_item, ''), ' :: '), '') AS itens_concatenados
        FROM contratacao c
        LEFT JOIN item_contratacao i
          ON i.numero_controle_pncp = c.numero_controle_pncp
        WHERE c.data_publicacao_pncp IS NOT NULL
          AND DATE(c.data_publicacao_pncp) = %s::date
          AND NOT EXISTS (
              SELECT 1 FROM contratacao_emb e
               WHERE e.numero_controle_pncp = c.numero_controle_pncp
          )
        GROUP BY c.numero_controle_pncp, c.objeto_compra
        ORDER BY c.numero_controle_pncp
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (date_formatted,))
        rows = cur.fetchall()
    out = []
    for r in rows:
        desc_obj = r.get("objeto_compra") or ""
        desc_itens = r.get("itens_concatenados") or ""
        full = (desc_obj + " :: " + desc_itens).strip()
        if not full:
            full = "sem descrição"
        if len(full) > 8000:
            full = full[:8000]
        out.append({
            "numero_controle_pncp": r["numero_controle_pncp"],
            "descricao_completa": full,
        })
    return out

# ---------------------------------------------------------------------
# OpenAI Embeddings (batch)
# ---------------------------------------------------------------------
CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_embeddings_batch(texts: List[str], retries: int = 3) -> List[List[float]]:
    if not texts:
        return []
    # higienizar textos
    norm = []
    for t in texts:
        if not isinstance(t, str):
            t = str(t)
        t = t.strip() or "sem descrição"
        if len(t) > 8000:
            t = t[:8000]
        norm.append(t)

    for attempt in range(retries):
        try:
            resp = CLIENT.embeddings.create(model=OPENAI_MODEL, input=norm)
            return [item.embedding for item in resp.data]
        except Exception as e:
            if attempt < retries - 1:
                wait = (2 ** attempt) + 1
                log_line(f"OpenAI erro/limite: retry {attempt+1}/{retries} em {wait}s ({e})")
                time.sleep(wait)
            else:
                raise

# ---------------------------------------------------------------------
# Insert embeddings em contratacao_emb
# ---------------------------------------------------------------------

def insert_embeddings(conn, registros: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
    if not registros or not embeddings:
        return 0
    if len(registros) != len(embeddings):
        log_line("Mismatch entre registros e embeddings")
        return 0

    rows = []
    for r, emb in zip(registros, embeddings):
        metadata = json.dumps({"model": OPENAI_MODEL}, ensure_ascii=False)
        rows.append((r["numero_controle_pncp"], OPENAI_MODEL, metadata, emb))

    sql = (
        "INSERT INTO contratacao_emb (numero_controle_pncp, modelo_embedding, metadata, embeddings) "
        "VALUES %s ON CONFLICT (numero_controle_pncp) DO NOTHING RETURNING numero_controle_pncp"
    )
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template='(%s, %s, %s, %s::vector)', page_size=200)
        inserted_rows = cur.fetchall() or []
    conn.commit()
    return len(inserted_rows)

# ---------------------------------------------------------------------
# Processamento de uma data
# ---------------------------------------------------------------------

def process_date(conn, date_str: str, batch_size: int) -> int:
    log_line(f"[2/3] Embeddings: processando {date_str} (LED/LPD)")
    regs = get_contratacoes_for_date(conn, date_str)
    if not regs:
        log_line("Sem contratações pendentes para essa data.")
        return 0

    total = 0
    n = len(regs)
    total_batches = math.ceil(n / max(1, batch_size))
    batch_idx = 0
    last_pct = -1
    for i in range(0, len(regs), batch_size):
        batch_idx += 1
        chunk = regs[i:i + batch_size]
        texts = [r["descricao_completa"] for r in chunk]
        embs = generate_embeddings_batch(texts)
        inserted = insert_embeddings(conn, chunk, embs)
        total += inserted
        done = min(i + batch_size, n)
        pct = int((done * 100) / max(1, n))
        if pct == 100 or pct - last_pct >= 5:
            fill = int(round(pct * 20 / 100))
            bar = "█" * fill + "░" * (20 - fill)
            log_line(f"Embeddings: {pct}% [{bar}] ({done}/{n}) Δ+{inserted} Σ{total} (tentados {len(chunk)})")
            last_pct = pct
    log_line(f"Concluído {date_str}: {total} embeddings novos")
    return total

# ---------------------------------------------------------------------
# Datas utilitárias
# ---------------------------------------------------------------------

def build_dates_for_embeddings(conn, start: str | None, end: str | None, test: str | None) -> List[str]:
    if test:
        return [test]
    last_emb = get_last_embedding_date(conn)
    last_proc = get_last_processed_date(conn)

    s = dt.datetime.strptime(last_emb, "%Y%m%d") + dt.timedelta(days=1)
    e = dt.datetime.strptime(last_proc, "%Y%m%d")

    if start:
        s = dt.datetime.strptime(start, "%Y%m%d")
    if end:
        e = dt.datetime.strptime(end, "%Y%m%d")

    if s > e:
        return []

    dates: List[str] = []
    cur = s
    while cur <= e:
        dates.append(cur.strftime("%Y%m%d"))
        cur += dt.timedelta(days=1)
    return dates

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline PNCP 02 – Embeddings")
    parser.add_argument("--start", help="Data inicial YYYYMMDD")
    parser.add_argument("--end", help="Data final YYYYMMDD")
    parser.add_argument("--test", help="Rodar apenas uma data YYYYMMDD")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Tamanho do batch para OpenAI")
    args = parser.parse_args()

    log_line("[2/3] GERAÇÃO DE EMBEDDINGS INICIADA (LED)")

    if not os.getenv("OPENAI_API_KEY"):
        log_line("OPENAI_API_KEY não configurada no .env")
        return

    conn = get_conn()
    try:
        # LED/LPD atuais
        led_cur = get_last_embedding_date(conn)
        lpd_cur = get_last_processed_date(conn)
        log_line(f"LED atual: {led_cur} | LPD atual: {lpd_cur}")

        dates = build_dates_for_embeddings(conn, args.start, args.end, args.test)
        if dates:
            log_line(f"Intervalo de datas para 02 (LED→LPD): {dates[0]} .. {dates[-1]} ({len(dates)})")
        if not dates:
            log_line("Nenhuma data para processar.")
            return

        total = 0
        for d in dates:
            try:
                inserted = process_date(conn, d, max(1, args.batch))
                total += inserted
                if not args.test:
                    update_last_embedding_date(conn, d)
                    log_line(f"LED atualizado: {d}")
            except Exception as e:
                log_line(f"Erro na data {d}: {e}")

        log_line("EMBEDDINGS FINALIZADOS")
        log_line(f"Datas: {len(dates)} | Embeddings novos: {total}")
        log_line(f"Log: {os.path.basename(LOG_FILE)}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
