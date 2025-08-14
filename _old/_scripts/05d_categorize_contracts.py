"""
05I_UNIFIED_CATEGORIZER (Versão Python-Vector)
=============================================

Esta versão visa otimizar o tempo de categorização eliminando a
dependência de consultas de similaridade ao banco de dados para cada
contrato. Em vez disso, carregamos todos os embeddings das categorias
uma única vez em memória e calculamos as similaridades em Python
utilizando NumPy (quando disponível) ou algoritmos nativos. A seguir,
realizamos apenas atualizações no banco para gravar os resultados.

Principais características:

* **Pré-carregamento de categorias**: todas as categorias com
  `cat_embeddings` são carregadas em um array no início da execução.
* **Cálculo de similaridade em memória**: para cada contrato, o
  algoritmo calcula as distâncias Euclidianas entre o embedding do
  contrato e todas as categorias, selecionando as `TOP_K` mais próximas.
  A similaridade é definida como `1 - distância`, de forma compatível
  com a abordagem original.
* **Cálculo de confiança em Python**: a confiança é calculada com a
  mesma fórmula usada nas versões anteriores, evitando estouros de
  `numeric` no banco.
* **Atualizações individuais**: cada contrato atualizado realiza uma
  única query `UPDATE` para gravar `top_categories`, `top_similarities`
  e `confidence`. Ainda assim, o overhead total é reduzido porque não
  há mais consultas para buscar categorias.

Requisitos: este script utiliza NumPy se disponível. Caso a importação
falhe, ele recorre a uma implementação em Python puro, que é menos
eficiente.
"""

import os
import sys
import time
import math
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import psycopg2
from psycopg2 import pool as pg_pool
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

# Configurações de banco
DB_CONFIG = {
    "host": os.getenv("SUPABASE_HOST"),
    "database": os.getenv("SUPABASE_DBNAME", "postgres"),
    "user": os.getenv("SUPABASE_USER"),
    "password": os.getenv("SUPABASE_PASSWORD"),
    "port": int(os.getenv("SUPABASE_PORT", 5432)),
}

# Constantes
MAX_WORKERS = 32
MAX_POOL_CONNECTIONS = MAX_WORKERS
BATCH_SIZE = 400
MIN_CONTRACTS_FOR_FULL_WORKERS = 1000
TOP_K = 5

# Variáveis globais
lock = threading.Lock()
console = Console()
stats = {
    "processed": 0,
    "success": 0,
    "skipped": 0,
    "errors": 0,
    "start_time": None,
}

db_pool: pg_pool.ThreadedConnectionPool | None = None

# Estruturas para categorias carregadas
categories_codes: list[str] = []
categories_matrix: "np.ndarray | None" = None
categories_loaded = False


def init_connection_pool() -> None:
    """Inicializa o pool de conexões global."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = pg_pool.ThreadedConnectionPool(
                minconn=1, maxconn=MAX_POOL_CONNECTIONS, **DB_CONFIG
            )
        except Exception as exc:
            console.print(f"❌ Erro ao criar pool de conexões: {exc}")
            sys.exit(1)


def load_categories(conn=None) -> None:
    """
    Carrega todas as categorias e seus embeddings do arquivo cat.csv.
    O arquivo deve estar em v1/scripts/cat/cat.csv e usar separador ';'.
    """
    import csv
    import ast

    global categories_codes, categories_matrix, categories_loaded
    
    # Evita recarregar caso já tenham sido carregadas
    if categories_loaded:
        return
    
    # Caminho fixo para o arquivo cat.csv
    script_dir_local = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir_local, "cat", "cat.csv")
    
    console.print(f"🔍 Procurando arquivo: {csv_path}")
    
    if not os.path.exists(csv_path):
        raise RuntimeError(f"Arquivo cat.csv não encontrado em: {csv_path}")
    
    try:
        categories_codes = []
        vectors: list[list[float]] = []
        
        with open(csv_path, "r", encoding="utf-8") as f:
            # Usar separador ; conforme especificado
            reader = csv.DictReader(f, delimiter=';')
            
            console.print(f"📋 Colunas encontradas: {reader.fieldnames}")
            
            # Verifica se as colunas mínimas existem
            if "cod_cat" not in reader.fieldnames or "cat_embeddings" not in reader.fieldnames:
                raise ValueError(
                    f"CSV deve conter colunas 'cod_cat' e 'cat_embeddings'. Encontradas: {reader.fieldnames}"
                )
            
            for row_num, row in enumerate(reader, 1):
                code = row.get("cod_cat", "").strip()
                emb_str = row.get("cat_embeddings", "").strip()
                
                if not code or not emb_str:
                    console.print(f"⚠️  Linha {row_num}: dados vazios, pulando...")
                    continue
                
                # Parse do embedding - tenta múltiplas estratégias
                try:
                    vec = None
                    
                    # Estratégia 1: Tenta interpretar como lista Python completa
                    if emb_str.startswith('[') and emb_str.endswith(']'):
                        try:
                            parsed = ast.literal_eval(emb_str)
                            if isinstance(parsed, (list, tuple)):
                                vec = [float(x) for x in parsed]
                        except:
                            pass
                    
                    # Estratégia 2: Se truncado, tenta parsear manualmente
                    if vec is None:
                        # Remove colchetes e espaços
                        clean_str = emb_str.strip('[]() ')
                        if clean_str:
                            # Split por vírgula e converte para float
                            parts = [x.strip() for x in clean_str.split(',') if x.strip()]
                            vec = []
                            for part in parts:
                                try:
                                    vec.append(float(part))
                                except ValueError:
                                    # Se não conseguir converter, para aqui
                                    break
                    
                    # Verifica se conseguiu extrair pelo menos alguns valores
                    if not vec or len(vec) < 100:  # Embeddings muito pequenos são suspeitos
                        console.print(f"⚠️  Linha {row_num}: embedding muito pequeno ({len(vec) if vec else 0} dimensões), pulando...")
                        continue
                    
                except Exception as e:
                    console.print(f"❌ Linha {row_num}: erro ao parsear embedding '{emb_str[:50]}...': {e}")
                    continue
                
                categories_codes.append(code)
                vectors.append(vec)
                
                # Log de progresso a cada 1000 categorias
                if row_num % 1000 == 0:
                    console.print(f"📈 Processadas {row_num} linhas...")
        
        if not categories_codes:
            raise RuntimeError("Nenhuma categoria válida foi carregada do CSV")
        
        # Verifica consistência das dimensões
        if vectors:
            expected_dim = len(vectors[0])
            inconsistent = []
            for i, vec in enumerate(vectors[1:], 1):
                if len(vec) != expected_dim:
                    inconsistent.append(f"Categoria {categories_codes[i]}: {len(vec)} vs {expected_dim}")
            
            if inconsistent:
                console.print(f"⚠️  Encontradas {len(inconsistent)} categorias com dimensões inconsistentes:")
                for msg in inconsistent[:10]:  # Mostra apenas as primeiras 10
                    console.print(f"   {msg}")
                if len(inconsistent) > 10:
                    console.print(f"   ... e mais {len(inconsistent) - 10}")
                
                # Remove categorias inconsistentes
                valid_categories = []
                valid_vectors = []
                for code, vec in zip(categories_codes, vectors):
                    if len(vec) == expected_dim:
                        valid_categories.append(code)
                        valid_vectors.append(vec)
                
                categories_codes = valid_categories
                vectors = valid_vectors
                console.print(f"✅ Mantidas {len(categories_codes)} categorias com dimensão consistente ({expected_dim})")
        
        # Após ler o CSV, monta a matriz
        categories_matrix = np.array(vectors, dtype=float)
        
        categories_loaded = True
        console.print(f"✅ {len(categories_codes)} categorias carregadas com sucesso!")
        console.print(f"📊 Dimensão dos embeddings: {len(vectors[0])} se houver categorias")
        
    except Exception as exc:
        raise RuntimeError(f"Erro ao carregar categorias de '{csv_path}': {exc}")


def get_system_dates() -> tuple[str | None, str | None]:
    """Obtém as datas LCD e LED do system_config."""
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
    """Atualiza ou insere a LCD."""
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
        conn.rollback()
        console.print(f"❌ Erro ao atualizar LCD: {exc}")
        return False
    finally:
        db_pool.putconn(conn)


def generate_date_range(start_date_str: str, end_date_str: str) -> list[str]:
    """Gera intervalo de datas (YYYY-MM-DD) inclusive."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        end_date = datetime.strptime(end_date_str, "%Y%m%d")
        dates: list[str] = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return dates
    except Exception as exc:
        console.print(f"❌ Erro ao gerar datas: {exc}")
        return []


def calculate_confidence_py(similarities: list[float]) -> float:
    """Calcula a confiança em Python (igual ao 05a)."""
    if len(similarities) < 2 or similarities[0] == 0.0:
        return 0.0
    top_score = similarities[0]
    gaps = [top_score - s for s in similarities[1:]]
    weights = [1 / (i + 1) for i in range(len(gaps))]
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    return round(1 - math.exp(-10 * weighted_gap), 4)


def fetch_contract_embeddings(target_date: str) -> list[tuple[int, list[float]]]:
    """Busca todos os embeddings de contratos de uma data sem top_categories."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ce.id_contratacao_emb, ce.embeddings
                FROM contratacao_emb ce
                JOIN contratacao c ON ce.numero_controle_pncp = c.numero_controle_pncp
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
        result: list[tuple[int, list[float]]] = []
        for row in rows:
            cid = row[0]
            emb = row[1]
            if isinstance(emb, list):
                vec = [float(x) for x in emb]
            else:
                emb_str = str(emb).strip("[]()")
                vec = [float(x) for x in emb_str.split(",") if x.strip()]
            result.append((cid, vec))
        # Exibe quantidade de embeddings carregados para a data
        console.print(f"🗂️  {len(result)} embeddings carregados para a data {target_date}")
        return result
    except Exception as exc:
        console.print(f"❌ Erro ao buscar embeddings de {target_date}: {exc}")
        return []
    finally:
        db_pool.putconn(conn)


def compute_top_k_categories(embedding: list[float]) -> tuple[list[str], list[float], float]:
    """Computa top K categorias para um embedding em memória."""
    if not categories_loaded:
        raise RuntimeError("Categorias não carregadas")
    
    vec = np.array(embedding, dtype=float)
    # calcula distâncias euclidianas: ||cat - vec||
    diffs = categories_matrix - vec  # shape (n_categories, d)
    dists = np.sqrt((diffs**2).sum(axis=1))
    # Seleciona índices dos menores
    top_indices = np.argsort(dists)[:TOP_K]
    top_cats = [categories_codes[i] for i in top_indices]
    # Similaridade como 1 - distância
    # similaridade como 1 - distância; aplica limite para evitar estouros numéricos
    top_sims = []
    for i in top_indices:
        sim = 1 - float(dists[i])
        # limita o valor absoluto a 1e11 (escala compatível com numeric(15,4))
        if sim > 1e11:
            sim = 1e11
        elif sim < -1e11:
            sim = -1e11
        top_sims.append(sim)
    
    conf = calculate_confidence_py(top_sims)
    return top_cats, top_sims, conf


def update_contract(conn, contract_id: int, cats: list[str], sims: list[float], conf: float) -> bool:
    """Atualiza um contrato com categorias, similaridades e confiança."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE contratacao_emb
                   SET top_categories = %s,
                       top_similarities = %s,
                       confidence = %s
                 WHERE id_contratacao_emb = %s
                   AND top_categories IS NULL
                """,
                (cats, sims, conf, contract_id),
            )
            return cursor.rowcount > 0
    except Exception as exc:
        console.print(
            f"❌ Erro ao atualizar contrato {contract_id} no DB: {exc}"
        )
        return False


def process_contract_batch(
    contracts: list[tuple[int, list[float]]],
    worker_id: int,
    date_str: str,
    progress: Progress,
    task_id: TaskID,
    date_stats: dict[str, int],
) -> dict[str, int]:
    """Processa um lote de contratos em uma thread."""
    batch_stats = {"success": 0, "skipped": 0, "errors": 0}
    conn = db_pool.getconn()
    try:
        # Log apenas no início do lote, não para cada contrato
        if len(contracts) > 0:
            console.print(f"🧵 Worker {worker_id}: processando {len(contracts)} contratos")
        
        for cid, emb in contracts:
            # calcula top K em memória
            try:
                cats, sims, conf = compute_top_k_categories(emb)
            except Exception as exc:
                with lock:
                    batch_stats["errors"] += 1
                    date_stats["errors"] += 1
                    stats["errors"] += 1
                console.print(f"❌ Erro ao calcular topK p/ contrato {cid}: {exc}")
                # Continua com próximo
                progress.update(
                    task_id,
                    advance=1,
                    description=(
                        f"🚀 {date_str} | ✅ {date_stats['success']} | "
                        f"⏭️ {date_stats['skipped']} | ❌ {date_stats['errors']}"
                    ),
                )
                continue
            
            # atualiza DB
            ok = update_contract(conn, cid, cats, sims, conf)
            
            with lock:
                stats["processed"] += 1
                if ok:
                    batch_stats["success"] += 1
                    date_stats["success"] += 1
                    stats["success"] += 1
                else:
                    batch_stats["skipped"] += 1
                    date_stats["skipped"] += 1
                    stats["skipped"] += 1
                progress.update(
                    task_id,
                    advance=1,
                    description=(
                        f"🚀 {date_str} | ✅ {date_stats['success']} | "
                        f"⏭️ {date_stats['skipped']} | ❌ {date_stats['errors']}"
                    ),
                )
        conn.commit()
        return batch_stats
    finally:
        db_pool.putconn(conn)


def process_date(date_str: str) -> dict[str, int]:
    """Processa todos os contratos de uma data específica."""
    console.print(f"\n📅 Processando data: {date_str}")
    contracts = fetch_contract_embeddings(date_str)
    total = len(contracts)
    if total == 0:
        console.print(f"    ✅ Todos os contratos já categorizados para {date_str}")
        return {"success": 0, "skipped": 0, "errors": 0}
    
    # Dividir em lotes de BATCH_SIZE contratos PRIMEIRO
    batches: list[list[tuple[int, list[float]]]] = []
    for i in range(0, total, BATCH_SIZE):
        batches.append(contracts[i : i + BATCH_SIZE])
    
    # Calcular workers otimizado para batches
    workers = calculate_optimal_workers(total)
    
    console.print(f"    📋 {total:,} contratos precisam categorização")
    console.print(f"    📦 Dividindo em {len(batches)} lotes de até {BATCH_SIZE} contratos")
    console.print(f"    ⚡ Usando {workers} workers (otimizado para {len(batches)} batches)")
    date_stats = {"success": 0, "skipped": 0, "errors": 0}
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
        task_id = progress.add_task(f"🚀 {date_str}", total=total)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for idx, batch in enumerate(batches):
                fut = executor.submit(
                    process_contract_batch,
                    batch,
                    idx,
                    date_str,
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
                        date_stats["errors"] += 1
                        stats["errors"] += 1
    console.print(
        f"    ✅ Concluído: {date_stats['success']} categorizados | "
        f"{date_stats['skipped']} pulados | {date_stats['errors']} erros"
    )
    return date_stats


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
    total_batches = math.ceil(total_contracts / BATCH_SIZE)
    
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


def main() -> None:
    console.print("=" * 80)
    console.print(
        "🚀 05_CATEGORIZE - CATEGORIZAÇÃO UNIFICADA BATCH PARALLEL (Python-Vector)"
    )
    console.print("=" * 80)
    init_connection_pool()
    # Carrega categorias apenas uma vez
    # Carrega categorias a partir de arquivo CSV. Não utiliza conexão.
    # Se o arquivo não existir ou houver erro de leitura, a função lançará RuntimeError.
    try:
        load_categories()
    except Exception as exc:
        console.print(f"❌ Erro ao carregar categorias: {exc}")
        return
    # Verifica datas
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