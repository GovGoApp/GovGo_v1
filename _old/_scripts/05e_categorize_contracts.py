"""
05A CATEGORIZE CONTRACTS 
=================================

Versão otimizada com mudanças **localizadas** (estrutura geral preservada):

* **Pool de conexões**: `ThreadedConnectionPool` (psycopg2).
* **Parâmetros por ambiente**: MAX_WORKERS, BATCH_SIZE, TOP_K.
* **Commit por LOTE**: uma transação por batch, com SAVEPOINT por contrato.
  - Reduz drasticamente commits (I/O/WAL) no Supabase.
  - Erros por contrato dão ROLLBACK TO SAVEPOINT sem abortar o lote.
* **Query de data**: intervalo [data, data+1) e sem ORDER BY (desnecessário).
* **Fechamento do pool**: `db_pool.closeall()` ao final.

Variáveis de ambiente esperadas (.env):
  SUPABASE_HOST, SUPABASE_DBNAME, SUPABASE_USER, SUPABASE_PASSWORD, SUPABASE_PORT
  MAX_WORKERS (default 32), BATCH_SIZE (default 500), TOP_K (default 5)
"""

import os
import sys
import time
import math
import threading
from typing import Any
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

# ---------------------------------------------------------------------
# Configurações de ambiente e constantes
# ---------------------------------------------------------------------
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

# Parâmetros do processamento (parametrizáveis por ambiente)
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "32"))  # Número máximo de threads de trabalho
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))   # Número máximo de contratos por lote
TOP_K: int = int(os.getenv("TOP_K", "5"))               # Número de categorias retornadas

# Pool de conexões = nº de workers
MAX_POOL_CONNECTIONS: int = MAX_WORKERS

# Estatísticas globais protegidas por lock para thread-safety
lock = threading.Lock()
console = Console()
stats = {
    "processed": 0,
    "success": 0,
    "skipped": 0,
    "errors": 0,
    "start_time": None,
}

# Pool de conexões global (será inicializado no main)
db_pool: pg_pool.ThreadedConnectionPool | None = None


# ---------------------------------------------------------------------
# Utilitários de banco de dados
# ---------------------------------------------------------------------

def init_connection_pool() -> None:
    """Inicializa o pool de conexões global."""
    global db_pool
    if db_pool is None:
        try:
            # minconn > 1 para pré-aquecer algumas conexões sem exceder o teto
            minconn = min(4, MAX_POOL_CONNECTIONS) if MAX_POOL_CONNECTIONS > 1 else 1
            db_pool = pg_pool.ThreadedConnectionPool(
                minconn=minconn, maxconn=MAX_POOL_CONNECTIONS, **DB_CONFIG
            )
        except Exception as e:
            console.print(f"❌ Erro ao criar pool de conexões: {e}")
            sys.exit(1)


def get_system_dates() -> tuple[str | None, str | None]:
    """Recupera last_categorization_date (LCD) e last_embedding_date (LED) de system_config."""
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
    """Atualiza a chave `last_categorization_date` em `system_config`."""
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
    """Gera lista de datas (YYYY-MM-DD) entre duas datas inclusive a partir de YYYYMMDD."""
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


def calculate_confidence(similarities: list[float]) -> float:
    """Confiança baseada na diferença entre o melhor score e os demais."""
    if len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    return round(1 - math.exp(-10 * weighted_gap), 4)


def get_contracts_by_date(target_date: str) -> list[str]:
    """Recupera contratos não categorizados e com embeddings para uma data (sem ORDER BY)."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ce.numero_controle_pncp
                FROM contratacao_emb ce
                JOIN contratacao c
                  ON ce.numero_controle_pncp = c.numero_controle_pncp
                WHERE c.data_publicacao_pncp IS NOT NULL
                  AND DATE(c.data_publicacao_pncp) >= %s::date
                  AND DATE(c.data_publicacao_pncp) < (%s::date + INTERVAL '1 day')
                  AND ce.embeddings IS NOT NULL
                  AND ce.top_categories IS NULL
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
    """Determina o número de workers baseado na quantidade de BATCHES."""
    if total_contracts == 0:
        return 1
    total_batches = math.ceil(total_contracts / (BATCH_SIZE))
    if total_batches == 1:
        return 1
    elif total_batches <= 4:
        return min(total_batches, 4)
    elif total_batches <= 8:
        return min(total_batches, 8)
    elif total_batches <= 16:
        return min(total_batches, 16)
    else:
        # Nota: Se o DB estiver gargalando, reduza MAX_WORKERS via .env (ex: 16 ou 8)
        return MAX_WORKERS


def categorize_single_contract(
    numero_controle_pncp: str,
    conn,
    commit: bool = True
) -> dict[str, Any]:
    """
    Categoriza um único contrato usando a conexão fornecida.

    Quando commit=True (padrão): comportamento original (commit/rollback por contrato).
    Quando commit=False: NÃO faz commit/rollback aqui (o batch controla via SAVEPOINT).
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Buscar embedding
            cursor.execute(
                """
                SELECT id_contratacao_emb, embeddings
                FROM contratacao_emb
                WHERE numero_controle_pncp = %s AND embeddings IS NOT NULL
                """,
                (numero_controle_pncp,),
            )
            embedding_row = cursor.fetchone()
            if not embedding_row:
                return {"success": False, "error": "No embedding"}

            # Busca categorias similares usando pgvector (<=> menor distância)
            cursor.execute(
                """
                SELECT cod_cat,
                       1 - (cat_embeddings <=> %s::vector) AS similarity
                FROM categoria
                WHERE cat_embeddings IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (embedding_row["embeddings"], TOP_K),
            )
            category_rows = cursor.fetchall()
            if not category_rows:
                return {"success": False, "error": "No categories"}

            # Extrair listas de categorias e similaridades
            top_categories = [row["cod_cat"] for row in category_rows]
            top_similarities = [round(float(row["similarity"]), 4) for row in category_rows]
            confidence = calculate_confidence(top_similarities)

            # Atualização com proteção anti-duplicação
            cursor.execute(
                """
                UPDATE contratacao_emb
                   SET top_categories = %s,
                       top_similarities = %s,
                       confidence = %s
                 WHERE id_contratacao_emb = %s
                   AND top_categories IS NULL
                """,
                (
                    top_categories,
                    top_similarities,
                    confidence,
                    embedding_row["id_contratacao_emb"],
                ),
            )
            updated_rows = cursor.rowcount

            if commit:
                conn.commit()

            if updated_rows == 0:
                # Já havia sido categorizado por outra execução
                return {"success": True, "skipped": True}
            return {
                "success": True,
                "skipped": False,
                "best_category": top_categories[0],
                "best_similarity": top_similarities[0],
                "confidence": confidence,
            }
    except Exception as exc:
        if commit:
            conn.rollback()
        # Quando commit=False, o controle de rollback é do SAVEPOINT do batch
        return {"success": False, "error": str(exc)}


def process_contract_batch(
    contract_ids: list[str],
    worker_id: int,
    date_str: str,
    progress: Progress,
    task_id: TaskID,
    date_stats_shared: dict[str, int],
) -> dict[str, int]:
    """
    Processa um lote de contratos dentro de uma thread.

    - Transação única por lote (commit no fim).
    - SAVEPOINT por contrato para isolar falhas sem abortar a transação do lote.
    """
    batch_stats = {"success": 0, "skipped": 0, "errors": 0}
    conn = db_pool.getconn()
    try:
        # Garantir transação explícita (default já é False, reforçamos por clareza)
        conn.autocommit = False

        with conn.cursor() as sp_cur:
            for contract_id in contract_ids:
                # SAVEPOINT antes de cada contrato
                sp_cur.execute("SAVEPOINT sp_categ")

                result = categorize_single_contract(
                    contract_id,
                    conn,
                    commit=False  # commit/rollback controlados aqui
                )

                if result.get("success"):
                    # Libera o savepoint (mantém alterações deste contrato)
                    sp_cur.execute("RELEASE SAVEPOINT sp_categ")
                    with lock:
                        stats["processed"] += 1
                        if result.get("skipped"):
                            batch_stats["skipped"] += 1
                            date_stats_shared["skipped"] += 1
                            stats["skipped"] += 1
                        else:
                            batch_stats["success"] += 1
                            date_stats_shared["success"] += 1
                            stats["success"] += 1
                else:
                    # Reverte apenas este contrato e segue
                    sp_cur.execute("ROLLBACK TO SAVEPOINT sp_categ")
                    with lock:
                        stats["processed"] += 1
                        batch_stats["errors"] += 1
                        date_stats_shared["errors"] += 1
                        stats["errors"] += 1

                # Atualizar Rich progress
                progress.update(
                    task_id,
                    advance=1,
                    description=(
                        f"🚀 {date_str} | ✅ {date_stats_shared['success']} | "
                        f"⏭️ {date_stats_shared['skipped']} | ❌ {date_stats_shared['errors']}"
                    ),
                )

        # Commit único do lote (tudo que não foi revertido por savepoint)
        conn.commit()
        return batch_stats
    except Exception as exc:
        # Falha inesperada no lote -> rollback total do lote
        try:
            conn.rollback()
        except Exception:
            pass
        console.print(f"    ❌ Erro no batch {worker_id}: {exc}")
        return batch_stats
    finally:
        # Devolver a conexão ao pool, independentemente de sucesso/erro
        db_pool.putconn(conn)


def process_date(target_date: str) -> dict[str, int]:
    """Processa todos os contratos de uma data específica com paralelismo por batches."""
    console.print(f"\n📅 Processando data: {target_date}")
    contract_ids = get_contracts_by_date(target_date)
    total_contracts = len(contract_ids)
    if total_contracts == 0:
        console.print(f"    ✅ Todos os contratos já categorizados para {target_date}")
        return {"success": 0, "skipped": 0, "errors": 0}

    workers = calculate_optimal_workers(total_contracts)

    # Dividir em lotes
    batches: list[list[str]] = []
    for i in range(0, total_contracts, BATCH_SIZE):
        batches.append(contract_ids[i: i + BATCH_SIZE])

    console.print(f"    📋 {total_contracts:,} contratos precisam categorização")
    console.print(f"    📦 Dividindo em {len(batches)} lotes de até {BATCH_SIZE} contratos")
    console.print(f"    ⚡ Usando {workers} workers (otimizado para {len(batches)} batches)")

    # Estatísticas compartilhadas entre workers
    date_stats = {"success": 0, "skipped": 0, "errors": 0}

    # Progresso com Rich
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

        # Executor para threads
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(
                    process_contract_batch,
                    batch,
                    batch_idx,
                    target_date,
                    progress,
                    task_id,
                    date_stats,
                )
                futures.append(future)
            # Aguardar conclusão das threads
            for future in as_completed(futures):
                try:
                    future.result()
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
    """Pipeline principal: verifica datas, processa e atualiza LCD, com resumo final."""
    console.print("=" * 80)
    console.print("🚀 05_CATEGORIZE - CATEGORIZAÇÃO UNIFICADA BATCH PARALLEL (Otimizado)")
    console.print("=" * 80)

    # Inicializar o pool de conexões uma única vez
    init_connection_pool()

    # FASE 1: Datas do sistema
    console.print("\n📊 FASE 1: Verificando datas do sistema...")
    lcd, led = get_system_dates()
    if not lcd or not led:
        console.print("❌ Erro ao obter datas do sistema")
        sys.exit(1)
    console.print(f"📅 Last Categorization Date (LCD): {lcd}")
    console.print(f"📅 Last Embedded Date (LED): {led}")

    # Verificar se há trabalho a fazer
    lcd_date = datetime.strptime(lcd, "%Y%m%d")
    led_date = datetime.strptime(led, "%Y%m%d")
    if lcd_date >= led_date:
        console.print("\n✅ Todas as datas já foram categorizadas!")
        console.print(f"   LCD ({lcd}) >= LED ({led})")
        # Fechar pool antes de sair
        if db_pool is not None:
            try:
                db_pool.closeall()
            except Exception:
                pass
        return

    # Próxima data a processar
    next_date = lcd_date + timedelta(days=1)
    next_date_str = next_date.strftime("%Y%m%d")
    console.print(f"🎯 Próxima data a processar: {next_date_str}")

    # FASE 2: Geração de lista de datas
    console.print(
        f"\n📋 FASE 2: Gerando lista de datas entre {next_date_str} e {led}..."
    )
    dates_to_process = generate_date_range(next_date_str, led)
    total_dates = len(dates_to_process)
    if total_dates == 0:
        console.print("❌ Nenhuma data para processar")
        if db_pool is not None:
            try:
                db_pool.closeall()
            except Exception:
                pass
        return
    console.print(f"📈 Total de datas para processar: {total_dates}")

    # FASE 3: Processar datas
    stats["start_time"] = time.time()
    overall_start = time.time()
    total_stats = {"success": 0, "skipped": 0, "errors": 0}
    last_processed_date = lcd
    idx = 0
    try:
        for idx, date_str in enumerate(dates_to_process, start=1):
            console.print(f"\n🔄 [{idx}/{total_dates}] {date_str}")
            result = process_date(date_str)
            total_stats["success"] += result["success"]
            total_stats["skipped"] += result["skipped"]
            total_stats["errors"] += result["errors"]
            # Atualizar LCD
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
        if stats["processed"] > 0 and total_time > 0:
            avg_rate = stats["processed"] / total_time
            console.print(f"🏃 Taxa média: {avg_rate:.1f} contratos/segundo")
        console.print(f"📅 LCD final: {last_processed_date}")
        console.print("=" * 80)

        # Fechar pool de conexões com elegância
        if db_pool is not None:
            try:
                db_pool.closeall()
            except Exception:
                pass


if __name__ == "__main__":
    main()
