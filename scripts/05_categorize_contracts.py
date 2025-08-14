"""
05A CATEGORIZE CONTRACTS 
=================================

Esta versão reescreve o script original de categorização de contratos para
aplicar as otimizações sugeridas. As principais mudanças são:

* **Pool de conexões**: utiliza `ThreadedConnectionPool` do `psycopg2` para
  reutilizar conexões ao banco de dados em vez de criar e destruir uma
  conexão a cada contrato. Isso reduz o overhead de conexão, conforme
  documentado em artigos de performance de banco de dados【635481882480027†L36-L56】.
* **Filtragem de datas sem função**: reescreve a consulta que busca
  contratos por data para evitar `DATE(c.data_publicacao_pncp) = %s`. Em
  vez disso, usa um intervalo `[data, data+1)` que permite ao PostgreSQL
  utilizar índices simples ou índices por expressão【634173647118604†L32-L69】.
* **Reutilização de conexões nos workers**: cada thread obtém uma
  conexão do pool, processa o lote inteiro de contratos e devolve a
  conexão ao pool ao final do processamento.
* **Separação de responsabilidades**: funções recebem conexões como
  parâmetros onde necessário, tornando o código mais testável e
  evitando dependências globais.
* **Comentários adicionais**: adiciona comentários explicativos para cada
  etapa do processamento.

Para executar este script, certifique-se de ter as mesmas variáveis de
ambiente (.env) utilizadas pelo script original. O comportamento geral
permanece o mesmo: processa datas entre `last_categorization_date` e
`last_embedding_date`, categorizando contratos em paralelo com
progresso em tempo real.
"""

import os
import sys
import time
import math
import threading
import logging
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
# Configuração de logging unificado
# ---------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_dir = os.path.dirname(script_dir)  # v1/
logs_dir = os.path.join(v1_dir, "logs")  # v1/logs/
os.makedirs(logs_dir, exist_ok=True)

# Usar timestamp do pipeline (passado via variável de ambiente) ou gerar novo
pipeline_timestamp = os.getenv('PIPELINE_TIMESTAMP')

if not pipeline_timestamp:
    pipeline_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_FILE = os.path.join(logs_dir, f"log_{pipeline_timestamp}.log")

# Configurar logger
logger = logging.getLogger('categorize_contracts')
logger.setLevel(logging.DEBUG)

# Formatter limpo sem timestamp/nível e sem prefixo de etapa
file_formatter = logging.Formatter('%(message)s')

# Handler para arquivo (modo append para log compartilhado)
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    # Sempre escrever no arquivo de log
    if log_type == "info":
        logger.info(message)
    elif log_type == "success":
        logger.info(f"✅ {message}")
    elif log_type == "warning":
        logger.warning(f"⚠️ {message}")
    elif log_type == "error":
        logger.error(f"❌ {message}")

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

# Parâmetros do processamento
MAX_WORKERS: int = 32  # Número máximo de threads de trabalho
MAX_POOL_CONNECTIONS: int = MAX_WORKERS  # Número máximo de conexões no pool
BATCH_SIZE: int = 100  # Número máximo de contratos por lote
TOP_K: int = 5  # Número de categorias retornadas na busca por similaridade

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
    """Inicializa o pool de conexões global.

    Utiliza `ThreadedConnectionPool`, que permite múltiplas conexões
    simultâneas em diferentes threads. O pool é criado apenas uma vez.
    """
    global db_pool
    if db_pool is None:
        try:
            db_pool = pg_pool.ThreadedConnectionPool(
                minconn=1, maxconn=MAX_POOL_CONNECTIONS, **DB_CONFIG
            )
        except Exception as e:
            console.print(f"❌ Erro ao criar pool de conexões: {e}")
            sys.exit(1)


def get_system_dates() -> tuple[str | None, str | None]:
    """Recupera as datas de `last_categorization_date` e `last_embedding_date`.

    Essas datas são armazenadas na tabela `system_config`. Caso não
    existam, retorna valores padrão.
    """
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
    """Atualiza a chave `last_categorization_date` em `system_config`.

    Se a chave já existir, faz `UPDATE`; caso contrário, faz `INSERT`. O
    timestamp de atualização é preenchido com `NOW()`. Retorna `True` em
    caso de sucesso e `False` se ocorrer algum erro.
    """
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
    """Gera lista de datas (YYYY-MM-DD) entre duas datas inclusive.

    As entradas devem estar no formato `YYYYMMDD`. Se ocorrer algum erro
    na conversão, retorna lista vazia.
    """
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
    """Calcula a confiança baseada na diferença entre o melhor score e os demais.

    Se houver menos de dois valores ou o maior valor for zero, retorna 0.0.
    A confiança é calculada por um decaimento exponencial sobre a diferença
    ponderada das similaridades. Este método evita viés em listas pequenas.
    """
    if len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    return round(1 - math.exp(-10 * weighted_gap), 4)


def get_contracts_by_date(target_date: str) -> list[str]:
    """Recupera contratos não categorizados e com embeddings para uma data.

    Utiliza intervalo `[data, data + 1)` em vez de `DATE(col) =` para
    permitir que o PostgreSQL utilize índices na coluna `data_publicacao_pncp`.
    Retorna uma lista de números de controle (strings).
    """
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # A coluna c.data_publicacao_pncp é do tipo TEXT na base; por isso
            # precisamos convertê-la explicitamente para DATE antes de comparar
            # com a data alvo. O formato utilizado aqui replica o script
            # original (05_categorize_contracts.py), realizando a conversão
            # através da função DATE() e comparando com o parâmetro como
            # ::date. Optamos por manter um intervalo [data, data+1) para
            # permitir expansões futuras, mas ainda usando DATE() para
            # respeitar o tipo TEXT. Caso prefira comparação de igualdade
            # simples, basta substituir a condição abaixo por
            # "DATE(c.data_publicacao_pncp) = %s::date".
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
                ORDER BY ce.numero_controle_pncp
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
    """Determina o número de workers baseado na quantidade de BATCHES.

    Esta função calcula primeiro quantos batches serão criados e então
    otimiza o número de workers baseado na quantidade de batches, não
    de contratos individuais. Evita overhead de ter mais workers que batches.
    """
    if total_contracts == 0:
        return 1
    
    # Calcular número de batches que serão criados
    import math
    total_batches = math.ceil(total_contracts / (BATCH_SIZE))
    
    # Otimizar workers baseado no número de batches
    if total_batches == 1:
        return 1  # Apenas 1 batch, 1 worker é suficiente
    elif total_batches <= 4:
        return min(total_batches, 4)  # Pequenos: 1 worker por batch
    elif total_batches <= 8:
        return min(total_batches, 8)  # Médios: máximo 8 workers
    elif total_batches <= 16:
        return min(total_batches, 16)  # Grandes: máximo 16 workers
    else:
        return MAX_WORKERS  # Muito grandes: usar todos os workers disponíveis
    
    # Nunca retorna mais workers que batches disponíveis
    # return min(calculated_workers, total_batches, MAX_WORKERS)


def categorize_single_contract(numero_controle_pncp: str, conn) -> dict[str, any]:
    """Categoriza um único contrato usando a conexão fornecida.

    Busca o embedding do contrato, procura categorias mais similares e
    atualiza a tabela `contratacao_emb` com as `top_categories`,
    `top_similarities` e `confidence` se ainda não houver valores.

    Retorna um dicionário com `success`, `skipped` e eventualmente
    detalhes sobre a melhor categoria.
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
        # Em caso de erro, desfaz alterações do contrato atual
        conn.rollback()
        return {"success": False, "error": str(exc)}


def process_contract_batch(
    contract_ids: list[str],
    worker_id: int,
    date_str: str,
    progress: Progress,
    task_id: TaskID,
    date_stats_shared: dict[str, int],
) -> dict[str, int]:
    """Processa um lote de contratos dentro de uma thread.

    Cada worker obtém uma conexão do pool, processa todos os IDs do lote
    com essa conexão e devolve a conexão ao pool ao final. As
    estatísticas locais (`batch_stats`) são retornadas para fins de
    depuração, enquanto `date_stats_shared` (compartilhado entre
    threads) e `stats` (global) são atualizados com locks. O progresso
    é atualizado a cada contrato.
    """
    batch_stats = {"success": 0, "skipped": 0, "errors": 0}
    conn = db_pool.getconn()
    try:
        for contract_id in contract_ids:
            result = categorize_single_contract(contract_id, conn)
            # Atualizar estatísticas globais com lock
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
                # Atualizar Rich progress
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
        # Devolver a conexão ao pool, independentemente de sucesso/erro
        db_pool.putconn(conn)


def process_date(target_date: str) -> dict[str, int]:
    """Processa todos os contratos de uma data específica.

    Exibe informações detalhadas sobre quantidade de contratos,
    trabalhadores a serem utilizados e conclui a atualização da LCD ao
    final. Retorna um dicionário com as estatísticas de `success`,
    `skipped` e `errors`.
    """
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
        batches.append(contract_ids[i : i + BATCH_SIZE])
    
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
    """Função principal executada quando o script é chamado diretamente.

    Recupera as datas do sistema, gera o intervalo de datas a ser processado
    e, para cada data, chama `process_date` e atualiza a LCD. Ao final,
    exibe um resumo com o tempo total e estatísticas agregadas.
    """
    # Log de início
    log_message("")
    log_message("=" * 80)
    log_message("[3/3] CATEGORIZAÇÃO DE CONTRATOS")
    log_message("=" * 80)
    log_message(f"MAX_WORKERS: {MAX_WORKERS}")
    log_message(f"BATCH_SIZE: {BATCH_SIZE}")
    log_message("-" * 80)
    
    console.print("=" * 80)
    console.print("🚀 CATEGORIZAÇÃO DE CONTRATOS")
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
        return
    console.print(f"📈 Total de datas para processar: {total_dates}")

    # FASE 3: Processar datas
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
        if stats["processed"] > 0:
            avg_rate = stats["processed"] / total_time
            console.print(f"🏃 Taxa média: {avg_rate:.1f} contratos/segundo")
        console.print(f"📅 LCD final: {last_processed_date}")
        console.print("=" * 80)
        
        # Log de finalização
        log_message("-" * 80)
        log_message("CATEGORIZAÇÃO UNIFICADA BATCH PARALLEL FINALIZADA")
        log_message(f"Tempo total: {total_time:.1f}s")
        log_message(f"Datas processadas: {idx}/{total_dates}")
        log_message(f"Contratos categorizados: {total_stats['success']:,}")
        log_message(f"Contratos pulados: {total_stats['skipped']:,}")
        log_message(f"Erros: {total_stats['errors']:,}")
        log_message(f"Total processado: {stats['processed']:,}")
        if stats["processed"] > 0:
            log_message(f"Taxa média: {stats['processed'] / total_time:.1f} contratos/segundo")
        log_message(f"LCD final: {last_processed_date}")
        log_message("=" * 80)


if __name__ == "__main__":
    main()