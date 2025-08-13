import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import time
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import register_adapter, AsIs
from dotenv import load_dotenv
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn
from rich.panel import Panel

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



#register_adapter(np.ndarray, adapt_numpy_array)

# Habilitar logs para depuração
def log_sql(sql, params=None):
    """Log da query SQL com parâmetros (truncados para legibilidade)"""
    if params:
        # Truncar arrays grandes para exibição
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

# Database connection function with better error handling
def connect_to_database(max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            console.print("[yellow]Tentando conectar ao banco de dados...[/yellow]")
            connection = psycopg2.connect(
                user=USER, password=PASSWORD, host=HOST, port=PORT, dbname=DBNAME
            )
            connection.autocommit = False  # Desligar autocommit para controlar transações
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

# Check if tables exist before importing
def check_tables_exist(connection):
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

# Load embeddings from pickle file
def load_embeddings(embeddings_file):
    try:
        with open(embeddings_file, 'rb') as f:
            embeddings_dict = pickle.load(f)
        console.print(f"[green]Embeddings carregados: {len(embeddings_dict)} registros[/green]")
        return embeddings_dict
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar embeddings: {e}[/bold red]")
        return {}

# Find the most recent embeddings file
def find_latest_embeddings():
    try:
        embedding_files = [f for f in os.listdir(EMBEDDINGS_PATH) if f.endswith('.pkl') and f.startswith("GvG_embeddings_")]
        
        if not embedding_files:
            console.print("[yellow]Nenhum arquivo de embeddings encontrado.[/yellow]")
            return None
        
        # Sort by modification time (newest first)
        embedding_files.sort(key=lambda f: os.path.getmtime(os.path.join(EMBEDDINGS_PATH, f)), reverse=True)
        latest_file = embedding_files[0]
        
        console.print(f"[green]Arquivo de embeddings mais recente: {latest_file}[/green]")
        return os.path.join(EMBEDDINGS_PATH, latest_file)
    
    except Exception as e:
        console.print(f"[bold red]Erro ao buscar arquivo de embeddings: {e}[/bold red]")
        return None


# REMOVA O ADAPTADOR ATUAL - ele está causando o problema
# register_adapter(np.ndarray, adapt_numpy_array)  # COMENTAR ESTA LINHA

# NOVA FUNÇÃO para preparar vetores
def prepare_vector_for_postgres(numpy_array):
    """
    Converte numpy array para lista Python para inserção no pgvector
    """
    return numpy_array.tolist()

# SUBSTITUA a seção de inserção de embedding por esta versão corrigida:
def process_excel_file(file_path, connection, embeddings_dict=None):
    try:
        df = pd.read_excel(file_path)
        console.print(f"[green]Arquivo Excel carregado: {len(df)} registros[/green]")
        
        cursor = connection.cursor()
        
        # Verificar amostra de embedding antes de prosseguir
        if embeddings_dict:
            sample_key = next(iter(embeddings_dict))
            sample_emb = embeddings_dict[sample_key]
            console.print(f"[blue]Exemplo de embedding para '{sample_key}':")
            console.print(f"[blue]Tipo: {type(sample_emb)}, Dimensões: {len(sample_emb)}")
            console.print(f"[blue]Primeiros 5 valores: {sample_emb[:5]}")
        
        # Track counts
        inserted_count = 0
        embedding_count = 0
        error_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[green]Importando registros...", total=len(df))
            
            for _, row in df.iterrows():
                try:
                    numero_controle = str(row['numeroControlePNCP'])
                    
                    # Check if record already exists
                    check_sql = "SELECT 1 FROM contratacoes WHERE numeroControlePNCP = %s"
                    cursor.execute(check_sql, (numero_controle,))
                    record_exists = cursor.fetchone() is not None
                    
                    if not record_exists:
                        # Insert contract data
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
                        inserted_count += 1
                    
                    # Handle embedding if available
                    if embeddings_dict and numero_controle in embeddings_dict:
                        try:
                            # Check if embedding already exists
                            cursor.execute(
                                "SELECT 1 FROM contratacoes_embeddings WHERE numeroControlePNCP = %s", 
                                (numero_controle,)
                            )
                            embedding_exists = cursor.fetchone() is not None
                            
                            if not embedding_exists:
                                embedding_vector = embeddings_dict[numero_controle]
                                
                                # MÉTODO CORRETO: Converter para lista Python
                                vector_list = prepare_vector_for_postgres(embedding_vector)
                                
                                metadata = {
                                    'dimensoes': len(embedding_vector),
                                    'data_geracao': datetime.now().strftime('%Y-%m-%d')
                                }
                                
                                # USAR CAST EXPLÍCITO para pgvector
                                emb_sql = """
                                    INSERT INTO contratacoes_embeddings (
                                        numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                                    ) VALUES (%s, %s::vector, %s, %s)
                                """
                                
                                if embedding_count < 2:
                                    console.print(f"[cyan]Inserindo embedding para {numero_controle}[/cyan]")
                                    console.print(f"[cyan]Vetor como lista: {vector_list[:3]}...{vector_list[-3:]}[/cyan]")
                                
                                cursor.execute(emb_sql, 
                                              (numero_controle, 
                                               vector_list,  # Lista Python, não string
                                               "text-embedding-3-large",
                                               json.dumps(metadata)))
                                embedding_count += 1
                            
                        except Exception as e:
                            console.print(f"[yellow]Erro ao inserir embedding para {numero_controle}: {e}[/yellow]")
                            error_count += 1
                    
                    # Commit a cada registro para evitar transações grandes
                    connection.commit()
                    
                except Exception as e:
                    connection.rollback()
                    console.print(f"[red]Erro no registro {numero_controle}: {e}[/red]")
                    error_count += 1
                
                progress.update(task, advance=1)
        
        console.print(f"[green]Importação concluída! {inserted_count} contratações e {embedding_count} embeddings importados.[/green]")
        console.print(f"[yellow]Total de erros: {error_count}[/yellow]")
        return inserted_count, embedding_count
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file_path)}: {e}[/bold red]")
        return 0, 0
      
def main():
    console.print(Panel("[bold magenta]IMPORTAÇÃO DE DADOS PARA SUPABASE[/bold magenta]"))
    
    try:
        # Connect to database
        connection = connect_to_database()
        
        # Check if tables exist
        if not check_tables_exist(connection):
            console.print("[bold red]As tabelas necessárias não existem no banco de dados![/bold red]")
            console.print("[yellow]Execute primeiro o script GvG_SP_Tables.py para criar as tabelas.[/yellow]")
            return
        
        # Find embeddings file
        embeddings_file = find_latest_embeddings()
        embeddings_dict = {}
        
        if embeddings_file:
            embeddings_dict = load_embeddings(embeddings_file)
        else:
            console.print("[yellow]Nenhum arquivo de embeddings encontrado. Apenas dados de contratações serão importados.[/yellow]")
        
        # Process Excel files in NEW_PATH
        excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            console.print("[yellow]Nenhum arquivo Excel encontrado em {}[/yellow]".format(NEW_PATH))
            return
        
        console.print(f"[green]Encontrados {len(excel_files)} arquivos para processamento.[/green]")
        
        # Process each file
        total_contratacoes = 0
        total_embeddings = 0
        
        for i, excel_file in enumerate(excel_files, 1):
            excel_path = os.path.join(NEW_PATH, excel_file)
            console.print(f"[bold blue][{i}/{len(excel_files)}] Processando: {excel_file}[/bold blue]")
            
            contratacoes, embeddings = process_excel_file(excel_path, connection, embeddings_dict)
            total_contratacoes += contratacoes
            total_embeddings += embeddings
        
        # Final report
        console.print("\n[bold green]" + "="*50 + "[/bold green]")
        console.print("[bold green]RELATÓRIO DE IMPORTAÇÃO[/bold green]")
        console.print(f"[green]Arquivos processados: {len(excel_files)}[/green]")
        console.print(f"[green]Contratações importadas: {total_contratacoes}[/green]")
        console.print(f"[green]Embeddings importados: {total_embeddings}[/green]")
        console.print("[bold green]" + "="*50 + "[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro durante a importação: {e}[/bold red]")
    finally:
        if connection:
            connection.close()
            console.print("[blue]Conexão com o banco encerrada.[/blue]")

if __name__ == "__main__":
    main()