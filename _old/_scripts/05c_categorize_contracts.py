"""
05I_UNIFIED_CATEGORIZER (Otimizacao incremental)
=============================================

Este script deriva do 05a_categorize_contracts.py e tem como objetivo
reduzir o tempo de categorização mantendo a mesma estrutura de
paralelismo e barra de progresso. As melhorias implementadas visam
diminuiro número de interações com o banco de dados por contrato e
aproveitar mais o banco para calcular as categorias similares.

Principais diferenças em relação ao 05a:

* **Função SQL de confiança**: cria uma função PL/pgSQL
  `public.calculate_confidence` que calcula a confiança a partir de um
  array de similaridades. Isso permite que a confiança seja calculada
  diretamente no banco, evitando chamadas a Python para esse cálculo.
* **Categorização em uma única query**: cada contrato é atualizado
  utilizando um único `UPDATE ... FROM LATERAL`, que obtém as
  `TOP_K` categorias mais próximas via índice `pgvector` e calcula
  `top_categories`, `top_similarities` e `confidence` em uma única
  chamada. Dessa forma, eliminamos as três consultas separadas (SELECT
  embedding, SELECT categorias e UPDATE) usadas no 05a, reduzindo
  consideravelmente o overhead de ida e volta ao banco.
* **Busca de contratos por id**: a função `get_contracts_by_date`
  retorna os IDs da tabela `contratacao_emb` em vez do
  `numero_controle_pncp`. Esse identificador é suficiente para realizar
  a atualização direta.

O restante da lógica (datas, barras de progresso, paralelismo e
tratamento de erros) permanece praticamente idêntico ao 05a, para
preservar a compatibilidade e o comportamento geral do script.
"""

import os
import sys
import time
import threading
import math
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    Progress,
    TaskID,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configuração do banco a partir das variáveis de ambiente
DB_CONFIG = {
    "host": os.getenv("SUPABASE_HOST"),
    "database": os.getenv("SUPABASE_DBNAME", "postgres"),
    "user": os.getenv("SUPABASE_USER"),
    "password": os.getenv("SUPABASE_PASSWORD"),
    "port": int(os.getenv("SUPABASE_PORT", 5432)),
}

# Parâmetros de processamento
MAX_WORKERS: int = 32
MAX_POOL_CONNECTIONS: int = MAX_WORKERS
BATCH_SIZE: int = 400
MIN_CONTRACTS_FOR_FULL_WORKERS: int = 1000
TOP_K: int = 5

lock = threading.Lock()
console = Console()
stats = {
    "processed": 0,
    "success": 0,
    "skipped": 0,
    "errors": 0,
    "start_time": None,
}

# Pool de conexões global
db_pool: pg_pool.ThreadedConnectionPool | None = None


def init_connection_pool() -> None:
    """Inicializa o pool de conexões global caso ainda não exista."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = pg_pool.ThreadedConnectionPool(
                minconn=1, maxconn=MAX_POOL_CONNECTIONS, **DB_CONFIG
            )
        except Exception as e:
            console.print(f"❌ Erro ao criar pool de conexões: {e}")
            sys.exit(1)


def create_confidence_function(conn) -> None:
    """Cria a função SQL calculate_confidence se ela não existir.

    A função aceita um array de valores numeric (similaridades) e
    retorna a confiança calculada de forma equivalente à função
    calculate_confidence do Python. É usada nas queries de atualização.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION public.calculate_confidence(similarities numeric[])
            RETURNS numeric AS $$
            DECLARE
              top_score numeric;
              weighted_sum numeric := 0;
            BEGIN
              IF similarities IS NULL OR array_length(similarities,1) < 2 THEN
                RETURN 0;
              END IF;
              top_score := similarities[1];
              IF top_score = 0 THEN
                RETURN 0;
              END IF;
              -- Calcula a soma ponderada das diferenças entre top_score e demais scores
              FOR i IN 2..array_length(similarities,1) LOOP
                 weighted_sum := weighted_sum + (top_score - similarities[i]) / (i - 1);
              END LOOP;
              weighted_sum := weighted_sum / top_score;
              RETURN round(1 - exp(-10 * weighted_sum), 4);
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        conn.commit()


def get_system_dates() -> tuple[str | None, str | None]:
    """Recupera as datas de 'last_categorization_date' e 'last_embedding_date'."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM system_config WHERE key = 'last_categorization_date'"
            )
            lcd_row = cursor.fetchone()
            lcd = lcd_row[0] if lcd_row else "20250101"

            cursor.execute(
                "SELECT value FROM system_config WHERE key = 'last_embedding_date'"
            )
            led_row = cursor.fetchone()
            led = led_row[0] if led_row else "20250101"
        return lcd, led
    except Exception as exc:
        console.print(f"❌ Erro ao buscar datas do sistema: {exc}")
        return None, None
    finally:
        db_pool.putconn(conn)


def update_last_categorization_date(new_date: str) -> bool:
    """Atualiza ou insere a chave 'last_categorization_date' com o novo valor."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO system_config (key, value, updated_at)
                VALUES ('last_categorization_date', %s, NOW())
                ON CONFLICT (key) DO UPDATE
                  SET value = EXCLUDED.value,
                      updated_at = EXCLUDED.updated_at
                """,
                (new_date,),
            )
            conn.commit()
        return True
    except Exception as exc:
        console.print(f"❌ Erro ao atualizar last_categorization_date: {exc}")
        conn.rollback()
        return False
    finally:
        db_pool.putconn(conn)


def generate_date_range(start_date_str: str, end_date_str: str) -> list[str]:
    """Gera lista de datas (YYYY-MM-DD) entre duas datas inclusive."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        end_date = datetime.strptime(end_date_str, "%Y%m%d")
        dates: list[str] = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        return dates
    except Exception as exc:
        console.print(f"❌ Erro ao gerar range de datas: {exc}")
        return []


def calculate_confidence_py(similarities: list[float]) -> float:
    """Calcula a confiança em Python (referência)."""
    if len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    return round(1 - math.exp(-10 * weighted_gap), 4)


def get_contracts_by_date(target_date: str) -> list[int]:
    """Recupera IDs de contratacao_emb para contratos sem top_categories na data."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ce.id_contratacao_emb
                FROM contratacao_emb ce
                JOIN contratacao c
                  ON ce.numero_controle_pncp = c.numero_controle_pncp
                WHERE c.data_publicacao_pncp IS NOT NULL
                  AND DATE(c.data_publicacao_pncp) >= %s::date
                  AND DATE(c.data_publicacao_pncp) < (%s::date + INTERVAL '1 day')
                  AND ce.embeddings IS NOT NULL
                  AND ce.top_categories IS NULL
                ORDER BY ce.id_contratacao_emb
                """,
                (target_date, target_date),
            )
            rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as exc:
        console.print(f"❌ Erro ao buscar contratos da data {target_date}: {exc}")
        return []
    finally:
        db_pool.putconn(conn)


def calculate_optimal_workers(total_contracts: int) -> int:
    """Determina número ideal de threads conforme quantidade de contratos."""
    if total_contracts == 0:
        return 1
    if total_contracts < 100:
        return min(4, total_contracts)
    if total_contracts < 500:
        return min(8, max(1, total_contracts // 10))
    if total_contracts < MIN_CONTRACTS_FOR_FULL_WORKERS:
        return min(16, max(1, total_contracts // 50))
    return MAX_WORKERS


def categorize_single_contract(contract_id: int, conn) -> dict[str, any]:
    """Categorização de um único contrato usando query set-based.

    Esta função utiliza um `UPDATE ... FROM LATERAL` para buscar as
    categorias mais próximas do embedding já armazenado em
    `contratacao_emb.embeddings`, calculando as arrays de categorias,
    similaridades e a confiança com a função SQL. O update é feito
    apenas se `top_categories` estiver nulo.
    """
    try:
        with conn.cursor() as cursor:
            # Utiliza um UPDATE com subconsulta que calcula as categorias e similaridades
            # para o contrato alvo. A subconsulta referencia uma nova alias da tabela
            # contratacao_emb (ce2) para permitir o uso de LATERAL com ce2.embeddings
            cursor.execute(
                """
                UPDATE contratacao_emb ce
                   SET top_categories   = sub.top_categories,
                       top_similarities = sub.top_similarities,
                       confidence       = sub.confidence
                FROM (
                    SELECT ce2.id_contratacao_emb,
                           array_agg(k.cod_cat) AS top_categories,
                           -- converte cada similaridade numérica para float8 e agrega
                           array_agg(k.similarity_num::float8) AS top_similarities,
                           -- calcula a confiança a partir dos valores numéricos com precisão limitada
                           calculate_confidence(array_agg(k.similarity_num)) AS confidence
                    FROM contratacao_emb ce2
                    JOIN LATERAL (
                        SELECT
                            cat.cod_cat,
                            -- similaridade original como double precision
                            1 - (cat.cat_embeddings <-> ce2.embeddings) AS similarity,
                            -- similaridade convertida para numeric(15,4) para evitar overflow
                            (1 - (cat.cat_embeddings <-> ce2.embeddings))::numeric(15,4) AS similarity_num
                        FROM categoria cat
                        WHERE cat.cat_embeddings IS NOT NULL
                        ORDER BY cat.cat_embeddings <-> ce2.embeddings
                        LIMIT %s
                    ) AS k ON true
                    WHERE ce2.id_contratacao_emb = %s
                      AND ce2.top_categories IS NULL
                    GROUP BY ce2.id_contratacao_emb
                ) AS sub
                WHERE ce.id_contratacao_emb = sub.id_contratacao_emb;
                """,
                (TOP_K, contract_id),
            )
            updated_rows = cursor.rowcount
            conn.commit()
            if updated_rows == 0:
                return {"success": True, "skipped": True}
            return {"success": True, "skipped": False}
    except Exception as exc:
        # Em caso de erro, desfazemos a transação e registramos o erro.  
        conn.rollback()
        # Loga o erro no console para facilitar depuração.
        try:
            console.print(
                f"❌ Erro ao categorizar contrato {contract_id}: {exc}"
            )
        except Exception:
            # Evita que problemas de logging causem falha adicional
            pass
        return {"success": False, "error": str(exc)}


def process_contract_batch(
    contract_ids: list[int],
    worker_id: int,
    date_str: str,
    progress: Progress,
    task_id: TaskID,
    date_stats_shared: dict[str, int],
) -> dict[str, int]:
    """Processa um lote de IDs de contratos em uma thread."""
    batch_stats = {"success": 0, "skipped": 0, "errors": 0}
    conn = db_pool.getconn()
    try:
        for cid in contract_ids:
            result = categorize_single_contract(cid, conn)
            with lock:
                stats["processed"] += 1
                if result.get("success"):
                    if result.get("skipped"):
                        batch_stats["skipped"] += 1
                        date_stats_shared["skipped"] += 1
                        stats["skipped"] += 1
                    else:
                        batch_stats["success"] += 1
                        date_stats_shared["success"] += 1
                        stats["success"] += 1
                else:
                    batch_stats["errors"] += 1
                    date_stats_shared["errors"] += 1
                    stats["errors"] += 1
                # Atualiza progresso
                progress.update(
                    task_id,
                    advance=1,
                    description=(
                        f"🚀 {date_str} | ✅ {date_stats_shared['success']} | "
                        f"⏭️ {date_stats_shared['skipped']} | ❌ {date_stats_shared['errors']}"
                    ),
                )
        return batch_stats
    finally:
        db_pool.putconn(conn)


def process_date(target_date: str) -> dict[str, int]:
    """Processa todos os contratos de uma data específica."""
    console.print(f"\n📅 Processando data: {target_date}")
    contract_ids = get_contracts_by_date(target_date)
    total_contracts = len(contract_ids)
    if total_contracts == 0:
        console.print(f"    ✅ Todos os contratos já categorizados para {target_date}")
        return {"success": 0, "skipped": 0, "errors": 0}

    workers = calculate_optimal_workers(total_contracts)
    console.print(f"    📋 {total_contracts:,} contratos precisam categorização")
    console.print(
        f"    ⚡ Usando {workers} workers (otimizado para {total_contracts} contratos)"
    )

    # Dividir em lotes
    batches: list[list[int]] = []
    for i in range(0, total_contracts, BATCH_SIZE):
        batches.append(contract_ids[i : i + BATCH_SIZE])

    console.print(
        f"    📦 Dividindo em {len(batches)} lotes de até {BATCH_SIZE} contratos"
    )

    date_stats = {"success": 0, "skipped": 0, "errors": 0}

    # Barra de progresso
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("/"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task(f"🚀 {target_date}", total=total_contracts)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for idx, batch in enumerate(batches):
                fut = executor.submit(
                    process_contract_batch,
                    batch,
                    idx,
                    target_date,
                    progress,
                    task_id,
                    date_stats,
                )
                futures.append(fut)
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as exc:
                    console.print(f"    ❌ Erro em batch: {exc}")
                    with lock:
                        stats["errors"] += 1
                        date_stats["errors"] += 1

    console.print(
        f"    ✅ Concluído: {date_stats['success']} categorizados | "
        f"{date_stats['skipped']} pulados | {date_stats['errors']} erros"
    )
    return date_stats


def main() -> None:
    """Rotina principal."""
    console.print("=" * 80)
    console.print("🚀 05_CATEGORIZE - CATEGORIZAÇÃO UNIFICADA BATCH PARALLEL (Otimiz.)")
    console.print("=" * 80)

    init_connection_pool()

    # Cria a função SQL de confiança no banco
    conn_tmp = db_pool.getconn()
    try:
        create_confidence_function(conn_tmp)
    finally:
        db_pool.putconn(conn_tmp)

    console.print("\n📊 FASE 1: Verificando datas do sistema...")
    lcd, led = get_system_dates()
    if not lcd or not led:
        console.print("❌ Erro ao obter datas do sistema")
        sys.exit(1)
    console.print(f"📅 Last Categorization Date (LCD): {lcd}")
    console.print(f"📅 Last Embedded Date (LED): {led}")

    lcd_date = datetime.strptime(lcd, "%Y%m%d")
    led_date = datetime.strptime(led, "%Y%m%d")
    if lcd_date >= led_date:
        console.print("\n✅ Todas as datas já foram categorizadas!")
        console.print(f"   LCD ({lcd}) >= LED ({led})")
        return

    next_date = lcd_date + timedelta(days=1)
    next_date_str = next_date.strftime("%Y%m%d")
    console.print(f"🎯 Próxima data a processar: {next_date_str}")

    console.print(
        f"\n📋 FASE 2: Gerando lista de datas entre {next_date_str} e {led}..."
    )
    dates_to_process = generate_date_range(next_date_str, led)
    total_dates = len(dates_to_process)
    if total_dates == 0:
        console.print("❌ Nenhuma data para processar")
        return
    console.print(f"📈 Total de datas para processar: {total_dates}")

    stats["start_time"] = time.time()
    overall_start = time.time()
    total_stats = {"success": 0, "skipped": 0, "errors": 0}
    last_processed_date = lcd
    try:
        for idx, date_str in enumerate(dates_to_process, start=1):
            console.print(f"\n🔄 [{idx}/{total_dates}] {date_str}")
            result = process_date(date_str)
            total_stats["success"] += result["success"]
            total_stats["skipped"] += result["skipped"]
            total_stats["errors"] += result["errors"]
            formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime(
                "%Y%m%d"
            )
            if update_last_categorization_date(formatted_date):
                last_processed_date = formatted_date
                console.print(f"    ✅ LCD atualizada para: {formatted_date}")
            else:
                console.print(f"    ⚠️  Falha ao atualizar LCD para: {formatted_date}")
    except KeyboardInterrupt:
        console.print("\n⚠️  Processo interrompido pelo usuário")
        console.print(f"📅 Última data processada: {last_processed_date}")
    except Exception as exc:
        console.print(f"\n❌ Erro durante processamento: {exc}")
        console.print(f"📅 Última data processada: {last_processed_date}")
    finally:
        overall_end = time.time()
        total_time = overall_end - overall_start
        console.print("\n" + "=" * 80)
        console.print("📊 RESULTADOS FINAIS")
        console.print("=" * 80)
        console.print(
            f"⏱️  Tempo total: {total_time/3600:.1f}h ({total_time:.0f}s)"
        )
        console.print(f"📅 Datas processadas: {idx}/{total_dates}")
        console.print("📋 Total de contratos:")
        console.print(f"   ✅ Categorizados: {total_stats['success']:,}")
        console.print(f"   ⏭️  Pulados: {total_stats['skipped']:,}")
        console.print(f"   ❌ Erros: {total_stats['errors']:,}")
        console.print(f"   📊 Total: {stats['processed']:,}")
        if stats["processed"] > 0:
            avg_rate = stats["processed"] / total_time
            console.print(f"🏃 Taxa média: {avg_rate:.1f} contratos/segundo")
        console.print(f"📅 LCD final: {last_processed_date}")
        console.print("=" * 80)


if __name__ == "__main__":
    main()