import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import threading
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import register_adapter, AsIs
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
MAX_WORKERS = 10  # Reduzido para evitar sobrecarga no banco
BATCH_SIZE = 100  # Tamanho do lote para inserção

# Lock para controle de concorrência
db_lock = threading.Lock()
stats_lock = threading.Lock()

# Estatísticas globais
global_stats = {
    'contratacoes_inseridas': 0,
    'embeddings_inseridos': 0,
    'contratacoes_duplicadas': 0,
    'embeddings_duplicados': 0,
    'erros': 0
}

def log_sql(sql, params=None):
    """Log da query SQL com parâmetros (truncados para legibilidade)"""
    if params:
        param_display = []
        for p in params:
            if isinstance(p, np.ndarray) or (isinstance(p, list) and len(p) > 10):
                param_display.append(f"[Array com {len(p)} elementos]")
            elif isinstance(p, str) and len(p) > 100:
                param_display.append(f"{p[:50]}...{p[-50:]}")
            else:
                param_display.append(p)
        console.print(f"[cyan]SQL: {sql}[/cyan]")
        console.print(f"[cyan]Parâmetros: {param_display}[/cyan]")
    else:
        console.print(f"[cyan]SQL: {sql}[/cyan]")

def create_connection_pool():
    """Cria pool de conexões para threads"""
    connections = []
    for i in range(MAX_WORKERS):
        try:
            connection = psycopg2.connect(
                user=USER, password=PASSWORD, host=HOST, port=PORT, dbname=DBNAME
            )
            connection.autocommit = False
            connections.append(connection)
        except Exception as e:
            console.print(f"[bold red]Erro ao criar conexão {i+1}: {e}[/bold red]")
    
    console.print(f"[green]Pool de {len(connections)} conexões criado com sucesso![/green]")
    return connections

def connect_to_database(max_retries=3):
    """Conecta ao banco de dados principal"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            console.print("[yellow]Tentando conectar ao banco de dados...[/yellow]")
            connection = psycopg2.connect(
                user=USER, password=PASSWORD, host=HOST, port=PORT, dbname=DBNAME
            )
            connection.autocommit = False
            console.print("[green]Conexão com o banco de dados estabelecida com sucesso![/green]")
            
            # Testar a conexão
            cursor = connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            console.print(f"[green]Versão PostgreSQL: {version[0]}[/green]")
            cursor.close()
            
            return connection
        except Exception as e:
            retry_count += 1
            console.print(f"[bold red]Tentativa {retry_count} falhou: {e}[/bold red]")
            if retry_count >= max_retries:
                raise
            console.print("[yellow]Tentando novamente em 2 segundos...[/yellow]")
            time.sleep(2)
    return None

def check_tables_exist(connection):
    """Verifica se as tabelas existem"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        count = cursor.fetchone()[0]
        return count == 2
    finally:
        cursor.close()

def load_existing_records(connection):
    """Carrega registros existentes para verificação de duplicatas"""
    cursor = connection.cursor()
    try:
        # Carregar IDs de contratações existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes")
        existing_contracts = set(row[0] for row in cursor.fetchall())
        
        # Carregar IDs de embeddings existentes
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes_embeddings")
        existing_embeddings = set(row[0] for row in cursor.fetchall())
        
        console.print(f"[cyan]Contratações existentes: {len(existing_contracts)}[/cyan]")
        console.print(f"[cyan]Embeddings existentes: {len(existing_embeddings)}[/cyan]")
        
        return existing_contracts, existing_embeddings
    
    except Exception as e:
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
            console.print("[yellow]Nenhum arquivo de embeddings encontrado.[/yellow]")
            return None
        
        # Ordenar por tempo de modificação (mais recente primeiro)
        embedding_files.sort(key=lambda f: os.path.getmtime(os.path.join(EMBEDDINGS_PATH, f)), reverse=True)
        latest_file = embedding_files[0]
        
        console.print(f"[green]Arquivo de embeddings mais recente: {latest_file}[/green]")
        return os.path.join(EMBEDDINGS_PATH, latest_file)
    
    except Exception as e:
        console.print(f"[bold red]Erro ao buscar arquivo de embeddings: {e}[/bold red]")
        return None

def prepare_vector_for_postgres(numpy_array):
    """Converte numpy array para lista Python para inserção no pgvector"""
    return numpy_array.tolist()

def partition_dataframe(df, n_partitions):
    """Divide um DataFrame em n partições aproximadamente iguais"""
    k, m = divmod(len(df), n_partitions)
    return [df.iloc[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n_partitions)]

def update_global_stats(contract_inserted=0, embedding_inserted=0, contract_duplicate=0, embedding_duplicate=0, errors=0):
    """Atualiza estatísticas globais de forma thread-safe"""
    with stats_lock:
        global_stats['contratacoes_inseridas'] += contract_inserted
        global_stats['embeddings_inseridos'] += embedding_inserted
        global_stats['contratacoes_duplicadas'] += contract_duplicate
        global_stats['embeddings_duplicados'] += embedding_duplicate
        global_stats['erros'] += errors

def process_batch_records(batch_df, connection, embeddings_dict, existing_contracts, existing_embeddings, progress, task_id, worker_id):
    """Processa um lote de registros em uma thread específica"""
    cursor = connection.cursor()
    
    local_stats = {
        'contratacoes_inseridas': 0,
        'embeddings_inseridos': 0,
        'contratacoes_duplicadas': 0,
        'embeddings_duplicados': 0,
        'erros': 0
    }
    
    try:
        for _, row in batch_df.iterrows():
            try:
                numero_controle = str(row['numeroControlePNCP'])
                
                # Inserir contratação se não existir
                if numero_controle not in existing_contracts:
                    insert_sql = """
                        INSERT INTO contratacoes (
                            numeroControlePNCP, anoCompra, descricaoCompleta,
                            valorTotalHomologado, dataAberturaProposta, dataEncerramentoProposta,
                            unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                            unidadeOrgao_nomeUnidade, orgaoEntidade_razaosocial
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    insert_params = (
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
                    )
                    
                    cursor.execute(insert_sql, insert_params)
                    existing_contracts.add(numero_controle)  # Adicionar ao conjunto local
                    local_stats['contratacoes_inseridas'] += 1
                else:
                    local_stats['contratacoes_duplicadas'] += 1
                
                # Inserir embedding se disponível e não existir
                if (embeddings_dict and numero_controle in embeddings_dict and 
                    numero_controle not in existing_embeddings):
                    
                    embedding_vector = embeddings_dict[numero_controle]
                    vector_list = prepare_vector_for_postgres(embedding_vector)
                    
                    metadata = {
                        'dimensoes': len(embedding_vector),
                        'data_geracao': datetime.now().strftime('%Y-%m-%d')
                    }
                    
                    emb_sql = """
                        INSERT INTO contratacoes_embeddings (
                            numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                        ) VALUES (%s, %s::vector, %s, %s)
                    """
                    
                    cursor.execute(emb_sql, (
                        numero_controle,
                        vector_list,
                        "text-embedding-3-large",
                        json.dumps(metadata)
                    ))
                    existing_embeddings.add(numero_controle)  # Adicionar ao conjunto local
                    local_stats['embeddings_inseridos'] += 1
                
                elif embeddings_dict and numero_controle in embeddings_dict:
                    local_stats['embeddings_duplicados'] += 1
                
                # Commit a cada 50 registros para evitar transações muito grandes
                if (local_stats['contratacoes_inseridas'] + local_stats['embeddings_inseridos']) % 50 == 0:
                    connection.commit()
                
            except Exception as e:
                connection.rollback()
                local_stats['erros'] += 1
                console.print(f"[red]Worker {worker_id} - Erro no registro {numero_controle}: {e}[/red]")
            
            # Atualizar progresso
            progress.update(task_id, advance=1)
        
        # Commit final
        connection.commit()
        
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Worker {worker_id} - Erro no lote: {e}[/bold red]")
        local_stats['erros'] += len(batch_df)
    
    finally:
        cursor.close()
    
    # Atualizar estatísticas globais
    update_global_stats(
        contract_inserted=local_stats['contratacoes_inseridas'],
        embedding_inserted=local_stats['embeddings_inseridos'],
        contract_duplicate=local_stats['contratacoes_duplicadas'],
        embedding_duplicate=local_stats['embeddings_duplicados'],
        errors=local_stats['erros']
    )
    
    return local_stats

def process_excel_file_parallel(file_path, connection_pool, embeddings_dict, existing_contracts, existing_embeddings):
    """Processa arquivo Excel usando ThreadPool"""
    try:
        df = pd.read_excel(file_path)
        console.print(f"[green]Arquivo Excel carregado: {len(df)} registros[/green]")
        
        # Verificar colunas necessárias
        required_columns = [
            'numeroControlePNCP', 'anoCompra', 'descricaoCompleta', 
            'valorTotalHomologado', 'dataAberturaProposta', 'dataEncerramentoProposta', 
            'unidadeOrgao_ufSigla', 'unidadeOrgao_municipioNome', 
            'unidadeOrgao_nomeUnidade', 'orgaoEntidade_razaosocial'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            console.print(f"[bold red]Colunas faltando no arquivo: {', '.join(missing_columns)}[/bold red]")
            return 0, 0
        
        # Processar tipos de dados
        df['anoCompra'] = pd.to_numeric(df['anoCompra'], errors='coerce').fillna(0).astype(int)
        
        # Formatar valores monetários
        if isinstance(df['valorTotalHomologado'].iloc[0], str):
            df['valorTotalHomologado'] = df['valorTotalHomologado'].str.replace(',', '.').astype(float)
        
        # Converter datas
        date_columns = ['dataAberturaProposta', 'dataEncerramentoProposta']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Dividir DataFrame em partições para processamento paralelo
        partitions = partition_dataframe(df, len(connection_pool))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Usar ThreadPoolExecutor para processamento paralelo
            with ThreadPoolExecutor(max_workers=len(connection_pool)) as executor:
                futures = []
                task_ids = []
                
                for worker_id, (partition, connection) in enumerate(zip(partitions, connection_pool), 1):
                    if len(partition) > 0:
                        task_id = progress.add_task(
                            f"Worker {worker_id} - {os.path.basename(file_path)}", 
                            total=len(partition)
                        )
                        task_ids.append(task_id)
                        
                        # Submeter tarefa para o executor
                        future = executor.submit(
                            process_batch_records,
                            partition,
                            connection,
                            embeddings_dict,
                            existing_contracts.copy(),  # Cópia do conjunto para evitar conflitos
                            existing_embeddings.copy(),  # Cópia do conjunto para evitar conflitos
                            progress,
                            task_id,
                            worker_id
                        )
                        futures.append(future)
                
                # Aguardar conclusão de todas as tarefas
                batch_results = []
                for future in futures:
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        console.print(f"[bold red]Erro em thread: {e}[/bold red]")
        
        # Somar resultados de todos os workers
        total_inserted_contracts = sum(r['contratacoes_inseridas'] for r in batch_results)
        total_inserted_embeddings = sum(r['embeddings_inseridos'] for r in batch_results)
        
        console.print(f"[green]Arquivo processado! {total_inserted_contracts} contratações e {total_inserted_embeddings} embeddings inseridos.[/green]")
        return total_inserted_contracts, total_inserted_embeddings
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file_path)}: {e}[/bold red]")
        return 0, 0

def clear_tables(connection):
    """Limpa todas as tabelas para começar do zero"""
    cursor = connection.cursor()
    try:
        console.print("[yellow]Limpando tabelas existentes...[/yellow]")
        
        # Deletar em ordem segura
        cursor.execute("DELETE FROM contratacoes_embeddings")
        cursor.execute("DELETE FROM contratacoes")
        
        # Resetar sequence
        cursor.execute("ALTER SEQUENCE contratacoes_embeddings_id_seq RESTART WITH 1")
        
        connection.commit()
        console.print("[green]Tabelas limpas com sucesso![/green]")
        
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao limpar tabelas: {e}[/bold red]")
        raise
    finally:
        cursor.close()

def main():
    console.print(Panel("[bold magenta]IMPORTAÇÃO PARALELA DE DADOS PARA SUPABASE[/bold magenta]"))
    
    try:
        # Conectar ao banco principal
        main_connection = connect_to_database()
        
        # Verificar se as tabelas existem
        if not check_tables_exist(main_connection):
            console.print("[bold red]As tabelas necessárias não existem no banco de dados![/bold red]")
            console.print("[yellow]Execute primeiro o script GvG_SP_Tables.py para criar as tabelas.[/yellow]")
            return
        
        # Perguntar se deseja limpar as tabelas
        while True:
            resposta = input("\nDeseja limpar as tabelas antes de importar? (s/n): ").strip().lower()
            if resposta in ['s', 'sim', 'n', 'não', 'nao']:
                break
            console.print("[yellow]Por favor, responda 's' para sim ou 'n' para não.[/yellow]")
        
        if resposta in ['s', 'sim']:
            clear_tables(main_connection)
        
        # Carregar registros existentes para verificação de duplicatas
        existing_contracts, existing_embeddings = load_existing_records(main_connection)
        
        # Criar pool de conexões para threads
        connection_pool = create_connection_pool()
        
        if not connection_pool:
            console.print("[bold red]Não foi possível criar o pool de conexões![/bold red]")
            return
        
        # Encontrar arquivo de embeddings
        embeddings_file = find_latest_embeddings()
        embeddings_dict = {}
        
        if embeddings_file:
            embeddings_dict = load_embeddings(embeddings_file)
        else:
            console.print("[yellow]Nenhum arquivo de embeddings encontrado. Apenas dados de contratações serão importados.[/yellow]")
        
        # Processar arquivos Excel
        excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            console.print("[yellow]Nenhum arquivo Excel encontrado em {}[/yellow]".format(NEW_PATH))
            return
        
        console.print(f"[green]Encontrados {len(excel_files)} arquivos para processamento.[/green]")
        console.print(f"[cyan]Usando {len(connection_pool)} workers para processamento paralelo.[/cyan]")
        
        # Resetar estatísticas globais
        global_stats.update({
            'contratacoes_inseridas': 0,
            'embeddings_inseridos': 0,
            'contratacoes_duplicadas': 0,
            'embeddings_duplicados': 0,
            'erros': 0
        })
        
        inicio_total = time.time()
        
        # Processar cada arquivo
        for i, excel_file in enumerate(excel_files, 1):
            excel_path = os.path.join(NEW_PATH, excel_file)
            console.print(f"[bold blue][{i}/{len(excel_files)}] Processando: {excel_file}[/bold blue]")
            
            contratacoes, embeddings = process_excel_file_parallel(
                excel_path, connection_pool, embeddings_dict, existing_contracts, existing_embeddings
            )
        
        # Calcular tempo total
        fim_total = time.time()
        tempo_total = fim_total - inicio_total
        
        # Relatório final com estatísticas detalhadas
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
        console.print(f"[green]Tempo total: {tempo_total:.2f} segundos[/green]")
        console.print(f"[green]Workers utilizados: {len(connection_pool)}[/green]")
        console.print("[bold green]" + "="*60 + "[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro durante a importação: {e}[/bold red]")
    finally:
        # Fechar todas as conexões
        if 'main_connection' in locals():
            main_connection.close()
        if 'connection_pool' in locals():
            for conn in connection_pool:
                conn.close()
        console.print("[blue]Todas as conexões foram encerradas.[/blue]")

if __name__ == "__main__":
    main()