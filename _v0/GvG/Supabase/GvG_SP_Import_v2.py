import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import threading
import random
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Configure Rich console
console = Console()

# Load environment variables from .env
env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
console.print(f"[blue]Buscando arquivo .env em: {env_path}")
load_dotenv(dotenv_path=env_path)

# Fetch connection variables
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Log conexão (sem mostrar senha completa)
console.print(Panel("[bold yellow]DADOS DE CONEXÃO[/bold yellow]"))
console.print(f"[blue]USER: {USER}")
console.print(f"[blue]PASSWORD: {'*'*(len(PASSWORD)-4) + PASSWORD[-4:] if PASSWORD else 'Não definida'}")
console.print(f"[blue]HOST: {HOST}")
console.print(f"[blue]PORT: {PORT}")
console.print(f"[blue]DBNAME: {DBNAME}")

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
NEW_PATH = BASE_PATH + "INPUT\\NEW\\"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\USING\\"

# Configurações para processamento paralelo
MAX_WORKERS = 10     # Número de workers paralelos
BATCH_SIZE = 100     # Registros por lote (batch)
REAL_BATCH_SIZE = 20 # Sub-lotes para atualização de progresso

# Lock para controle de concorrência em estatísticas
stats_lock = threading.Lock()

# Estatísticas globais
global_stats = {
    'contratacoes_inseridas': 0,
    'embeddings_inseridos': 0,
    'contratacoes_duplicadas': 0,
    'embeddings_duplicados': 0,
    'erros': 0,
    'lotes_processados': 0
}

def create_connection():
    """Cria uma conexão individual com timeout configurado"""
    try:
        connection = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME,
            connect_timeout=30,
            options="-c statement_timeout=300000"  # 5 minutos para statements
        )
        connection.autocommit = False
        return connection
    except Exception as e:
        console.print(f"[bold red]Erro ao criar conexão: {e}[/bold red]")
        return None

def execute_with_retry(cursor, sql, params, max_retries=3, worker_id=None):
    """Executa SQL com retry e backoff exponencial"""
    for attempt in range(max_retries):
        try:
            cursor.execute(sql, params)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    if worker_id:
                        console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            if worker_id:
                console.print(f"[red]Worker {worker_id} - Erro definitivo: {e}[/red]")
            raise
    return False

def execute_batch_with_retry(cursor, sql, data_list, worker_id, max_retries=3):
    """Executa inserção em lote com retry"""
    for attempt in range(max_retries):
        try:
            # Usar batch_size igual ao tamanho da lista para inserção única
            execute_values(cursor, sql, data_list, template=None, page_size=len(data_list))
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "deadlock" in error_msg or "canceling statement" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    console.print(f"[yellow]Worker {worker_id} - Tentativa {attempt + 1} falhou, aguardando {wait_time:.2f}s[/yellow]")
                    time.sleep(wait_time)
                    continue
            console.print(f"[red]Worker {worker_id} - Erro definitivo em lote: {e}[/red]")
            raise
    return False

def load_existing_records(connection):
    """Carrega registros existentes para verificação de duplicatas"""
    cursor = connection.cursor()
    try:
        # Carregar IDs com commit read
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        
        # Carregar IDs de contratações existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes")
        existing_contracts = set(row[0] for row in cursor.fetchall())
        
        # Carregar IDs de embeddings existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes_embeddings")
        existing_embeddings = set(row[0] for row in cursor.fetchall())
        
        # Finalizar a transação de leitura
        connection.commit()
        
        console.print(f"[cyan]Contratações existentes: {len(existing_contracts)}[/cyan]")
        console.print(f"[cyan]Embeddings existentes: {len(existing_embeddings)}[/cyan]")
        
        return existing_contracts, existing_embeddings
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao carregar registros existentes: {e}[/bold red]")
        return set(), set()
    finally:
        cursor.close()

def load_embeddings(embeddings_file):
    """Carrega embeddings do arquivo pickle"""
    try:
        with open(embeddings_file, 'rb') as f:
            embeddings_dict = pickle.load(f)
        console.print(f"[green]Embeddings carregados: {len(embeddings_dict)} registros[/green]")
        return embeddings_dict
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar embeddings: {e}[/bold red]")
        return {}

def find_latest_embeddings():
    """Encontra o arquivo de embeddings mais recente"""
    try:
        embedding_files = [f for f in os.listdir(EMBEDDINGS_PATH) if f.endswith('.pkl') and f.startswith("GvG_embeddings_")]
        
        if not embedding_files:
            return None
        
        embedding_files.sort(key=lambda f: os.path.getmtime(os.path.join(EMBEDDINGS_PATH, f)), reverse=True)
        latest_file = embedding_files[0]
        
        console.print(f"[green]Arquivo de embeddings: {latest_file}[/green]")
        return os.path.join(EMBEDDINGS_PATH, latest_file)
    
    except Exception as e:
        console.print(f"[bold red]Erro ao buscar embeddings: {e}[/bold red]")
        return None

def prepare_vector_for_postgres(numpy_array):
    """Converte numpy array para lista Python"""
    return numpy_array.tolist()

def partition_dataframe(df, n_partitions):
    """Divide DataFrame em partições equilibradas"""
    k, m = divmod(len(df), n_partitions)
    return [df.iloc[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n_partitions)]

def update_global_stats(contract_inserted=0, embedding_inserted=0, contract_duplicate=0, embedding_duplicate=0, errors=0, batches=0):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        global_stats['contratacoes_inseridas'] += contract_inserted
        global_stats['embeddings_inseridos'] += embedding_inserted
        global_stats['contratacoes_duplicadas'] += contract_duplicate
        global_stats['embeddings_duplicados'] += embedding_duplicate
        global_stats['erros'] += errors
        global_stats['lotes_processados'] += batches

def process_batch(worker_id, batch_df, embeddings_dict, existing_contracts, existing_embeddings, progress, task_id):
    """Processa um lote de registros com atualizações de progresso por sublote"""
    
    # Criar conexão dedicada para este worker
    connection = create_connection()
    if not connection:
        console.print(f"[bold red]Worker {worker_id} não conseguiu criar conexão![/bold red]")
        return {
            'contratacoes_inseridas': 0,
            'embeddings_inseridos': 0,
            'contratacoes_duplicadas': 0,
            'embeddings_duplicados': 0,
            'erros': len(batch_df)
        }
    
    cursor = connection.cursor()
    
    # Estatísticas locais para este worker
    local_stats = {
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'erros': 0
    }
    
    # Criar sub-lotes para atualização do progresso
    sublotes = []
    batch_size = REAL_BATCH_SIZE
    for i in range(0, len(batch_df), batch_size):
        sublotes.append(batch_df.iloc[i:i+batch_size])
    
    console.print(f"[blue]Worker {worker_id} - Processando {len(batch_df)} registros em {len(sublotes)} sublotes[/blue]")
    
    try:
        # Processar cada sublote (permite atualização visual do progresso)
        for sublote_idx, sublote in enumerate(sublotes):
            contract_data = []
            embedding_data = []
            
            # Preparar dados para inserção do sublote
            for _, row in sublote.iterrows():
                try:
                    numero_controle = str(row['numeroControlePNCP'])
                    
                    # Preparar contratação se não existir
                    if numero_controle not in existing_contracts:
                        try:
                            contract_data.append((
                                numero_controle,
                                int(row['anoCompra']),
                                row['descricaoCompleta'],
                                float(row['valorTotalHomologado']),
                                row['dataAberturaProposta'],
                                row['dataEncerramentoProposta'],
                                row['unidadeOrgao_ufSigla'],
                                row['unidadeOrgao_municipioNome'],
                                row['unidadeOrgao_nomeUnidade'],
                                row['orgaoEntidade_razaosocial']
                            ))
                            existing_contracts.add(numero_controle)
                            local_stats['contratacoes_inseridas'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar contratação {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    else:
                        local_stats['contratacoes_duplicadas'] += 1
                    
                    # Preparar embedding se disponível
                    if (embeddings_dict and numero_controle in embeddings_dict and 
                        numero_controle not in existing_embeddings):
                        try:
                            embedding_vector = embeddings_dict[numero_controle]
                            vector_list = prepare_vector_for_postgres(embedding_vector)
                            
                            metadata = {
                                'dimensoes': len(embedding_vector),
                                'data_geracao': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            embedding_data.append((
                                numero_controle,
                                vector_list,
                                "text-embedding-3-large",
                                json.dumps(metadata)
                            ))
                            existing_embeddings.add(numero_controle)
                            local_stats['embeddings_inseridos'] += 1
                        except Exception as e:
                            console.print(f"[red]Worker {worker_id} - Erro ao preparar embedding {numero_controle}: {e}[/red]")
                            local_stats['erros'] += 1
                    elif embeddings_dict and numero_controle in embeddings_dict:
                        local_stats['embeddings_duplicados'] += 1
                
                except Exception as e:
                    local_stats['erros'] += 1
                    console.print(f"[red]Worker {worker_id} - Erro geral em {numero_controle}: {e}[/red]")
            
            # INSERÇÕES EM TRANSAÇÃO ÚNICA
            try:
                # Iniciar transação para este sublote
                #connection.begin()
                
                # Inserir contratações em lote
                if contract_data:
                    contract_sql = """
                        INSERT INTO contratacoes (
                            numeroControlePNCP, anoCompra, descricaoCompleta,
                            valorTotalHomologado, dataAberturaProposta, dataEncerramentoProposta,
                            unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                            unidadeOrgao_nomeUnidade, orgaoEntidade_razaosocial
                        ) VALUES %s
                    """
                    
                    execute_batch_with_retry(cursor, contract_sql, contract_data, worker_id)
                
                # Inserir embeddings individualmente (devido ao pgvector)
                if embedding_data:
                    for emb_data in embedding_data:
                        single_emb_sql = """
                            INSERT INTO contratacoes_embeddings (
                                numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                            ) VALUES (%s, %s::vector, %s, %s)
                        """
                        execute_with_retry(cursor, single_emb_sql, emb_data, worker_id=worker_id)
                
                # Commit da transação completa do sublote
                connection.commit()
                
                # Atualizar progresso para este sublote
                update_global_stats(batches=1)
                progress.update(task_id, advance=len(sublote))
                
                # Breve pausa para reduzir contenção no banco
                time.sleep(0.05)
                
            except Exception as e:
                # Rollback em caso de erro
                connection.rollback()
                console.print(f"[bold red]Worker {worker_id} - Erro no sublote {sublote_idx+1}: {e}[/bold red]")
                local_stats['erros'] += len(sublote)
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Worker {worker_id} - Erro geral no processamento: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
    
    finally:
        # Fechar conexão
        cursor.close()
        connection.close()
    
    # Atualizar estatísticas globais com os resultados deste worker
    update_global_stats(
        contract_inserted=local_stats['contratacoes_inseridas'],
        embedding_inserted=local_stats['embeddings_inseridos'],
        contract_duplicate=local_stats['contratacoes_duplicadas'],
        embedding_duplicate=local_stats['embeddings_duplicados'],
        errors=local_stats['erros']
    )
    
    return local_stats

def process_excel_file(file_path, embeddings_dict, existing_contracts, existing_embeddings):
    """Processa um arquivo Excel usando ThreadPool com workers independentes"""
    try:
        df = pd.read_excel(file_path)
        console.print(f"[green]Arquivo carregado: {len(df)} registros[/green]")
        
        # Verificar colunas necessárias
        required_columns = [
            'numeroControlePNCP', 'anoCompra', 'descricaoCompleta', 
            'valorTotalHomologado', 'dataAberturaProposta', 'dataEncerramentoProposta', 
            'unidadeOrgao_ufSigla', 'unidadeOrgao_municipioNome', 
            'unidadeOrgao_nomeUnidade', 'orgaoEntidade_razaosocial'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            console.print(f"[bold red]Colunas faltando: {', '.join(missing_columns)}[/bold red]")
            return 0, 0
        
        # Processar tipos de dados
        df['anoCompra'] = pd.to_numeric(df['anoCompra'], errors='coerce').fillna(0).astype(int)
        
        if len(df) > 0 and isinstance(df['valorTotalHomologado'].iloc[0], str):
            df['valorTotalHomologado'] = df['valorTotalHomologado'].str.replace(',', '.').astype(float)
        
        date_columns = ['dataAberturaProposta', 'dataEncerramentoProposta']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Dividir em partições equilibradas entre os workers
        partitions = partition_dataframe(df, MAX_WORKERS)
        
        # Remover partições vazias
        partitions = [p for p in partitions if len(p) > 0]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Criar um task por worker para acompanhamento visual
            tasks = []
            for worker_id in range(len(partitions)):
                task = progress.add_task(
                    f"Worker {worker_id+1}/{len(partitions)} - {os.path.basename(file_path)}", 
                    total=len(partitions[worker_id])
                )
                tasks.append(task)
            
            # Usar ThreadPoolExecutor com cada thread tendo sua própria conexão
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for worker_id, partition in enumerate(partitions):
                    # Submeter tarefa para processamento paralelo
                    future = executor.submit(
                        process_batch,
                        worker_id + 1,               # ID do worker (1-based)
                        partition,                   # Dados a processar
                        embeddings_dict,             # Embeddings
                        existing_contracts.copy(),   # Cópia para evitar conflitos
                        existing_embeddings.copy(),  # Cópia para evitar conflitos
                        progress,                    # Objeto de progresso
                        tasks[worker_id]             # ID da tarefa visual
                    )
                    futures.append(future)
                
                # Aguardar conclusão de todos os workers
                results = []
                for future in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        console.print(f"[bold red]Erro em worker: {e}[/bold red]")
        
        # Contabilizar resultados
        if results:
            total_inserted_contracts = sum(r['contratacoes_inseridas'] for r in results)
            total_inserted_embeddings = sum(r['embeddings_inseridos'] for r in results)
            total_duplicated_contracts = sum(r['contratacoes_duplicadas'] for r in results)
            total_duplicated_embeddings = sum(r['embeddings_duplicados'] for r in results)
            total_errors = sum(r['erros'] for r in results)
            
            # Exibir relatório do arquivo
            console.print(f"[green]Arquivo processado![/green]")
            console.print(f"[green]Contratações: {total_inserted_contracts} inseridas, {total_duplicated_contracts} duplicadas[/green]")
            console.print(f"[green]Embeddings: {total_inserted_embeddings} inseridos, {total_duplicated_embeddings} duplicados[/green]")
            console.print(f"[yellow]Erros: {total_errors}[/yellow]")
            
            return total_inserted_contracts, total_inserted_embeddings
        
        return 0, 0
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar {os.path.basename(file_path)}: {e}[/bold red]")
        return 0, 0

def clear_tables():
    """Limpa todas as tabelas para começar do zero"""
    connection = create_connection()
    if not connection:
        console.print("[bold red]Não foi possível conectar para limpar tabelas![/bold red]")
        return False
    
    cursor = connection.cursor()
    try:
        console.print("[yellow]Limpando tabelas...[/yellow]")
        
        # Usar TRUNCATE com CASCADE para eficiência
        cursor.execute("TRUNCATE TABLE contratacoes CASCADE")
        
        # Resetar sequências
        cursor.execute("ALTER SEQUENCE contratacoes_embeddings_id_seq RESTART WITH 1")
        
        connection.commit()
        console.print("[green]Tabelas limpas com sucesso![/green]")
        return True
        
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao limpar tabelas: {e}[/bold red]")
        return False
    
    finally:
        cursor.close()
        connection.close()

def check_tables_exist():
    """Verifica se as tabelas necessárias existem"""
    connection = create_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        count = cursor.fetchone()[0]
        connection.commit()
        return count == 2
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao verificar tabelas: {e}[/bold red]")
        return False
    
    finally:
        cursor.close()
        connection.close()

def main():
    console.print(Panel("[bold magenta]IMPORTAÇÃO PARALELA OTIMIZADA - VERSÃO 3.0[/bold magenta]"))
    console.print(f"[cyan]Configuração: {MAX_WORKERS} Workers | Batch Size: {BATCH_SIZE} | Real Batch: {REAL_BATCH_SIZE}[/cyan]")
    
    # Verificar se as tabelas existem
    if not check_tables_exist():
        console.print("[bold red]As tabelas necessárias não existem no banco de dados![/bold red]")
        console.print("[yellow]Execute o script de criação de tabelas primeiro.[/yellow]")
        return
    
    # Perguntar se deve limpar as tabelas
    resposta = input("\nLimpar tabelas antes de importar? (s/n): ").strip().lower()
    if resposta in ['s', 'sim']:
        if not clear_tables():
            return
    
    # Criar conexão temporária para consultar registros existentes
    connection = create_connection()
    if not connection:
        console.print("[bold red]Não foi possível conectar ao banco![/bold red]")
        return
    
    # Carregar registros existentes para verificação de duplicatas
    existing_contracts, existing_embeddings = load_existing_records(connection)
    connection.close()
    
    # Carregar embeddings
    embeddings_file = find_latest_embeddings()
    embeddings_dict = {}
    if embeddings_file:
        embeddings_dict = load_embeddings(embeddings_file)
    else:
        console.print("[yellow]Nenhum arquivo de embeddings encontrado. Apenas contratações serão importadas.[/yellow]")
    
    # Processar arquivos Excel
    excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
    if not excel_files:
        console.print("[yellow]Nenhum arquivo Excel encontrado em {}[/yellow]".format(NEW_PATH))
        return
    
    console.print(f"[green]Encontrados {len(excel_files)} arquivos para processamento.[/green]")
    
    # Resetar estatísticas globais
    global_stats.update({
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'erros': 0,
        'lotes_processados': 0
    })
    
    # Iniciar cronômetro
    inicio = time.time()
    
    # Processar cada arquivo Excel
    for i, excel_file in enumerate(excel_files, 1):
        excel_path = os.path.join(NEW_PATH, excel_file)
        console.print(f"\n[bold blue][{i}/{len(excel_files)}] Processando: {excel_file}[/bold blue]")
        
        # Processar arquivo com ThreadPool
        process_excel_file(
            excel_path, 
            embeddings_dict, 
            existing_contracts,
            existing_embeddings
        )
    
    # Calcular tempo total
    tempo_total = time.time() - inicio
    
    # Calcular métricas de desempenho
    registros_totais = global_stats['contratacoes_inseridas'] + global_stats['embeddings_inseridos']
    registros_por_segundo = registros_totais / tempo_total if tempo_total > 0 else 0
    
    # Exibir relatório final
    console.print("\n[bold green]" + "="*60 + "[/bold green]")
    console.print("[bold green]RELATÓRIO FINAL DE IMPORTAÇÃO[/bold green]")
    console.print("[bold green]" + "="*60 + "[/bold green]")
    
    # Criar tabela de estatísticas
    stats_table = Table(show_header=True, header_style="bold cyan")
    stats_table.add_column("Métrica", style="blue")
    stats_table.add_column("Contratações", justify="right", style="green")
    stats_table.add_column("Embeddings", justify="right", style="yellow")
    
    stats_table.add_row("Inseridos", str(global_stats['contratacoes_inseridas']), str(global_stats['embeddings_inseridos']))
    stats_table.add_row("Duplicados", str(global_stats['contratacoes_duplicadas']), str(global_stats['embeddings_duplicados']))
    stats_table.add_row("Erros", str(global_stats['erros']), "-")
    
    console.print(stats_table)
    
    console.print(f"\n[green]Arquivos processados: {len(excel_files)}[/green]")
    console.print(f"[green]Lotes processados: {global_stats['lotes_processados']}[/green]")
    console.print(f"[green]Tempo total: {tempo_total:.2f} segundos[/green]")
    console.print(f"[green]Performance: {registros_por_segundo:.2f} registros/segundo[/green]")
    console.print("[bold green]" + "="*60 + "[/bold green]")

if __name__ == "__main__":
    main()