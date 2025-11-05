#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_embeddings (Contrato)

Objetivo
- Gerar embeddings (OpenAI) para contratos e gravar em public.contrato_emb.embeddings_hv (halfvec)
- Selecionar contratos NOVOS (sem linha em contrato_emb) e BACKFILL (linha existe, embeddings_hv NULL)
- LED: system_config.last_embedded_date_contrato (AAAAMMDD)
- Data de seleção: contrato.data_atualizacao_global (TEXT ISO: YYYY-MM-DDTHH:MM:SS)

CLI (espelha 01):
--mode {publicacao,atualizacao}  (compatibilidade)
--tipo {periodo,diario}
--from AAAAMMDD
--to   AAAAMMDD

Escolhas alinhadas ao 02 de contratacao (HV-first):
- Modelo: text-embedding-3-large
- Batch default: 32 (configurável por OPENAI_EMB_BATCH)
- Texto: objeto_contrato (higienizado e truncado até 8000 chars)
- Persistência APENAS em embeddings_hv::halfvec(3072) (campos vector serão descontinuados)
- Logs simples com percentuais por data (com barra Rich)
"""
import os
import sys
import json
import logging
import argparse
import time
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

STAGE_NAME = "contrato.02"
CFG_LED = "last_embedded_date_contrato"
# Para limitar janelas do 02 ao que já foi processado no 01
CFG_LPD = "last_processed_date_contrato"
# Serão definidos após load_dotenv() no main
EMBED_MODEL = None  # type: ignore
EMBED_DIM = 3072
BATCH_SIZE = 32
TRACE = False
CLIENT = None  # OpenAI client global, inicializado no main


def get_db_conn():
    """Conecta usando SUPABASE_* do scripts/pncp/.env."""
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )


def get_system_config(cur, key: str) -> Optional[str]:
    cur.execute("SELECT value FROM system_config WHERE key=%s", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_system_config(cur, key: str, value: str):
    cur.execute(
        """
        INSERT INTO system_config (key, value, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
        """,
        (key, value, f"Atualizado por {STAGE_NAME}"),
    )


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


def get_contratos_for_date(conn, day_str: str) -> List[Dict[str, Any]]:
    """Seleciona contratos pendentes de embedding HV (NOVOS + BACKFILL) no dia (AAAAMMDD)."""
    date_from_iso = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:8]}T00:00:00"
    date_to_iso = (
        datetime.strptime(day_str, "%Y%m%d") + timedelta(days=1)
    ).strftime("%Y-%m-%dT00:00:00")
    # Seleciona contratos cujo texto existe e:
    #  - não têm linha em contrato_emb OU
    #  - têm linha, mas embeddings_hv está NULL (backfill)
    query = (
        "SELECT c.numero_controle_pncp, c.objeto_contrato, e.embeddings_hv IS NOT NULL AS has_hv "
        "FROM public.contrato c "
        "LEFT JOIN public.contrato_emb e ON e.numero_controle_pncp = c.numero_controle_pncp "
        "WHERE c.data_atualizacao_global >= %s "
        "  AND c.data_atualizacao_global < %s "
        "  AND COALESCE(NULLIF(c.objeto_contrato, ''), NULL) IS NOT NULL "
        "  AND (e.numero_controle_pncp IS NULL OR e.embeddings_hv IS NULL) "
        "ORDER BY c.numero_controle_pncp"
    )
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, (date_from_iso, date_to_iso))
        rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        desc = (r.get("objeto_contrato") or "").strip() or "sem descrição"
        if len(desc) > 8000:
            desc = desc[:8000]
        out.append({
            "numero_controle_pncp": r.get("numero_controle_pncp"),
            "descricao": desc,
        })
    return out


def log_line(msg: str) -> None:
    """Logs só aparecem quando --trace. A barra Rich aparece sempre."""
    if not TRACE:
        return
    try:
        print(msg, flush=True)
        logging.info(msg)
    except Exception:
        pass


def chunk_list(lst: List[Any], n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def generate_embeddings_batch(texts: List[str], retries: int = 3) -> List[List[float]]:
    if OpenAI is None:
        raise RuntimeError("Biblioteca OpenAI não encontrada. Instale 'openai'.")
    # Higienizar textos
    norm: List[str] = []
    for t in texts:
        if not isinstance(t, str):
            t = str(t)
        t = (t.strip() or "sem descrição")
        if len(t) > 8000:
            t = t[:8000]
        norm.append(t)

    for attempt in range(retries):
        try:
            resp = CLIENT.embeddings.create(model=EMBED_MODEL, input=norm)
            return [item.embedding for item in resp.data]
        except Exception as e:
            if attempt < retries - 1:
                wait = (2 ** attempt) + 1
                log_line(f"OpenAI erro/limite: retry {attempt+1}/{retries} em {wait}s ({e})")
                time.sleep(wait)
            else:
                raise


def insert_embeddings(cur, registros: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
    if not registros or not embeddings:
        return 0
    if len(registros) != len(embeddings):
        log_line("Mismatch entre registros e embeddings")
        return 0

    rows = []
    for r, emb in zip(registros, embeddings):
        metadata = json.dumps({"model": EMBED_MODEL}, ensure_ascii=False)
        emb_str = "[" + ",".join(f"{float(x):.8f}" for x in emb) + "]"
        rows.append((r["numero_controle_pncp"], EMBED_MODEL, metadata, emb_str))

    # Upsert apenas HV; backfill quando já existir a linha
    sql = (
        "INSERT INTO public.contrato_emb (numero_controle_pncp, modelo_embedding, metadata, embeddings_hv) "
        "VALUES %s "
        "ON CONFLICT (numero_controle_pncp) DO UPDATE SET "
        "  modelo_embedding = EXCLUDED.modelo_embedding, "
        "  metadata = EXCLUDED.metadata, "
        "  embeddings_hv = COALESCE(public.contrato_emb.embeddings_hv, EXCLUDED.embeddings_hv) "
        "RETURNING numero_controle_pncp"
    )
    psycopg2.extras.execute_values(
        cur,
        sql,
        [(ncp, model, meta, emb) for (ncp, model, meta, emb) in rows],
        template='(%s, %s, %s, %s::halfvec(3072))',
        page_size=1000,
    )
    inserted = cur.fetchall() or []
    return len(inserted)


def process_day(conn, day_str: str, progress: Progress):
    """Processa um dia (AAAAMMDD) com uma barra Rich única, total baseado em pendentes do dia."""
    log_line("")
    log_line(f"[2/3] Embeddings (contrato): processando {day_str} (LED)")
    regs = get_contratos_for_date(conn, day_str)
    n = len(regs)
    # Criar sempre uma barra por dia, mesmo sem pendentes
    task = progress.add_task(f"Dia {day_str[:4]}-{day_str[4:6]}-{day_str[6:8]}: [Contrato Emb]", total=(n if n > 0 else 1))
    if n == 0:
        progress.update(task, advance=1)
        with conn.cursor() as cur:
            set_system_config(cur, CFG_LED, day_str)
            cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LED,))
            v = (cur.fetchone() or [None])[0]
            if v != day_str:
                raise RuntimeError(f"Divergência LED: gravado {day_str}, lido {v}")
            conn.commit()
        return 0
    total_inserted = 0
    for i in range(0, n, BATCH_SIZE):
        chunk = regs[i : i + BATCH_SIZE]
        texts = [r["descricao"] for r in chunk]
        if TRACE:
            log_line(f"Lote OpenAI: {len(texts)} registros")
        embs = generate_embeddings_batch(texts)
        with conn.cursor() as cur:
            inserted = insert_embeddings(cur, chunk, embs)
        conn.commit()
        total_inserted += inserted
        progress.update(task, advance=len(chunk))

    with conn.cursor() as cur:
        set_system_config(cur, CFG_LED, day_str)
        cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LED,))
        v = (cur.fetchone() or [None])[0]
        if v != day_str:
            raise RuntimeError(f"Divergência LED: gravado {day_str}, lido {v}")
        conn.commit()
    # Não remover a task: manter uma barra persistente por dia
    log_line(f"Concluído {day_str}: {total_inserted} embeddings novos")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description="Pipeline 02 - Contratos (embeddings)")
    parser.add_argument("--mode", choices=["publicacao", "atualizacao"], default="publicacao")
    parser.add_argument("--tipo", choices=["periodo", "diario"], default="periodo")
    parser.add_argument("--from", dest="date_from", required=False, help="AAAAMMDD")
    parser.add_argument("--to", dest="date_to", required=False, help="AAAAMMDD")
    parser.add_argument("--trace", action="store_true", help="Exibe logs detalhados de progresso")
    args = parser.parse_args()

    # Setup env e logging
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    # Nível de log: INFO se --trace, senão WARNING (erros ainda aparecem)
    logging.basicConfig(level=(logging.INFO if args.trace else logging.WARNING), format="%(levelname)s %(message)s")
    global TRACE, EMBED_MODEL, BATCH_SIZE
    TRACE = bool(args.trace)
    EMBED_MODEL = os.environ.get("OPENAI_MODEL_EMBEDDINGS") or os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-large"
    try:
        BATCH_SIZE = int(os.environ.get("OPENAI_EMB_BATCH", "64"))
    except Exception:
        BATCH_SIZE = 64

    # Suprimir verbosidade de bibliotecas externas quando não for trace
    for name in [
        "openai",
        "httpx",
        "httpcore",
        "httpcore.http11",
        "httpcore.connection",
    ]:
        ext_logger = logging.getLogger(name)
        if not TRACE:
            ext_logger.setLevel(logging.ERROR)
            ext_logger.propagate = False

    if not os.getenv("OPENAI_API_KEY"):
        logging.error("OPENAI_API_KEY não encontrada no .env de scripts/pncp")
        sys.exit(2)
    # Inicializa OpenAI client global uma única vez
    global CLIENT
    CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Determinar janela default via LED
    with get_db_conn() as conn:
        # Pré-checagem: exigir coluna embeddings_hv em contrato_emb
        if not table_has_column(conn, 'public', 'contrato_emb', 'embeddings_hv'):
            logging.error("Coluna public.contrato_emb.embeddings_hv não encontrada. Crie a coluna (halfvec) antes de rodar o 02.")
            sys.exit(2)
        with conn.cursor() as cur:
            led = get_system_config(cur, CFG_LED)
            lpd = get_system_config(cur, CFG_LPD) or today

    # Regras de janela (alinhadas ao 02 de contratacao):
    # - Sem --from: usar LED (última data embutida)
    # - Sem --to: usar LPD (última data processada pelo 01)
    # - Se --to > LPD: clamp em LPD
    date_from = args.date_from or (led or today)
    tmp_to = args.date_to or lpd
    # clamp
    date_to = tmp_to if tmp_to <= lpd else lpd

    # Validar datas
    try:
        dt_from = datetime.strptime(date_from, "%Y%m%d")
        dt_to = datetime.strptime(date_to, "%Y%m%d")
    except Exception:
        logging.error("Formato de data inválido. Use AAAAMMDD.")
        sys.exit(2)
    if dt_from > dt_to:
        logging.error("Data inicial maior que a final.")
        sys.exit(2)

    # Caso nenhum dos dois tenha sido informado e LED == LPD, não processa
    if not args.date_from and not args.date_to and (date_from == date_to):
        logging.info("Embeddings: LED (%s) já está alinhado ao LPD (%s). Nada a fazer.", date_from, date_to)
        return

    with get_db_conn() as conn:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=False,
        ) as progress:
            if args.tipo == "periodo":
                cur_dt = dt_from
                while cur_dt <= dt_to:
                    day_str = cur_dt.strftime("%Y%m%d")
                    process_day(conn, day_str, progress)
                    cur_dt += timedelta(days=1)
            else:
                # diario: mesmo laço dia-a-dia
                cur_dt = dt_from
                while cur_dt <= dt_to:
                    day_str = cur_dt.strftime("%Y%m%d")
                    process_day(conn, day_str, progress)
                    cur_dt += timedelta(days=1)


if __name__ == "__main__":
    main()
