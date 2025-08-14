import os
import pandas as pd
import numpy as np
import pickle
import json
import sys
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import register_adapter, AsIs
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn
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

console.print(Panel("[bold yellow]VERIFICAÇÃO DE VARIÁVEIS DE AMBIENTE[/bold yellow]"))
console.print(f"[blue]Arquivo .env procurado no diretório: {os.path.abspath('.')}")
console.print(f"[green]USER: {'encontrado' if USER else 'não encontrado'}")
console.print(f"[green]PASSWORD: {'encontrado' if PASSWORD else 'não encontrado (ou vazio)'}")
console.print(f"[green]HOST: {HOST}")
console.print(f"[green]PORT: {PORT}")
console.print(f"[green]DBNAME: {DBNAME}")
console.print()


# Base paths (use the same as in GvG_EG_v1_4.py)
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
NEW_PATH = BASE_PATH + "INPUT\\NEW\\"
OLD_PATH = BASE_PATH + "INPUT\\OLD\\"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\USING\\"

# Por esta:


# Register NumPy array adapter for PostgreSQL
def adapt_numpy_array(numpy_array):
    return AsIs(str(numpy_array.tolist()))

register_adapter(np.ndarray, adapt_numpy_array)

# Database connection function with retry
def connect_to_database(max_retries=3):
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            )
            console.print("[green]Conexão com o banco de dados estabelecida com sucesso![/green]")
            return connection
        except Exception as e:
            retry_count += 1
            console.print(f"[bold red]Tentativa {retry_count} falhou: {e}[/bold red]")
            if retry_count >= max_retries:
                console.print("[bold red]Não foi possível conectar ao banco após várias tentativas.[/bold red]")
                raise
            console.print("[yellow]Tentando novamente...[/yellow]")
    
    return None

# Create database tables
def create_tables(connection):
    cursor = connection.cursor()
    
    try:
        # Check if pgvector extension exists
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cursor.fetchone() is None:
            console.print("[yellow]Extensão pgvector não encontrada. Tentando criar...[/yellow]")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            console.print("[green]Extensão pgvector criada com sucesso![/green]")
        
        # Create contratacoes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contratacoes (
                numeroControlePNCP VARCHAR(255) PRIMARY KEY,
                anoCompra INTEGER,
                descricaoCompleta TEXT,
                valorTotalHomologado NUMERIC,
                dataAberturaProposta DATE,
                dataEncerramentoProposta DATE,
                unidadeOrgao_ufSigla VARCHAR(2),
                unidadeOrgao_municipioNome VARCHAR(255),
                unidadeOrgao_nomeUnidade VARCHAR(255),
                orgaoEntidade_razaosocial VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create embeddings table with vector support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contratacoes_embeddings (
                id SERIAL PRIMARY KEY,
                numeroControlePNCP VARCHAR(255) REFERENCES contratacoes(numeroControlePNCP),
                embedding_vector VECTOR(3072),
                modelo_embedding VARCHAR(100),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on numeroControlePNCP for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contratacoes_embeddings_numero_controle 
            ON contratacoes_embeddings(numeroControlePNCP)
        """)
        
        # Create vector similarity search index if it doesn't exist
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contratacoes_embeddings_vector_cosine
                ON contratacoes_embeddings 
                USING ivfflat (embedding_vector vector_cosine_ops)
                WITH (lists = 100)
            """)
        except Exception as e:
            console.print(f"[yellow]Aviso ao criar índice de similaridade: {e}[/yellow]")
            console.print("[yellow]O índice de similaridade será criado na próxima versão do pgvector.[/yellow]")
            
        connection.commit()
        console.print("[green]Tabelas e índices criados com sucesso![/green]")
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao criar tabelas: {e}[/bold red]")
        raise
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

# Process and import Excel data
def process_excel_file(file_path, connection, embeddings_dict=None):
    try:
        df = pd.read_excel(file_path)
        console.print(f"[green]Arquivo Excel carregado: {len(df)} registros[/green]")
        
        # Verify required columns
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
        
        # Process data types
        df['anoCompra'] = pd.to_numeric(df['anoCompra'], errors='coerce').fillna(0).astype(int)
        
        # Format values - replace comma with dot and convert to float
        if isinstance(df['valorTotalHomologado'].iloc[0], str):
            df['valorTotalHomologado'] = df['valorTotalHomologado'].str.replace(',', '.').astype(float)
        
        # Convert dates
        date_columns = ['dataAberturaProposta', 'dataEncerramentoProposta']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        cursor = connection.cursor()
        
        # Track counts
        inserted_count = 0
        embedding_count = 0
        
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
                    numero_controle = row['numeroControlePNCP']
                    
                    # Check if record already exists
                    cursor.execute(
                        "SELECT 1 FROM contratacoes WHERE numeroControlePNCP = %s", 
                        (numero_controle,)
                    )
                    record_exists = cursor.fetchone() is not None
                    
                    if not record_exists:
                        # Insert contract data
                        cursor.execute("""
                            INSERT INTO contratacoes (
                                numeroControlePNCP, anoCompra, descricaoCompleta,
                                valorTotalHomologado, dataAberturaProposta, dataEncerramentoProposta,
                                unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                                unidadeOrgao_nomeUnidade, orgaoEntidade_razaosocial
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
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
                        inserted_count += 1
                    
                    # Handle embedding if available and embeddings_dict is provided
                    if embeddings_dict and numero_controle in embeddings_dict:
                        # Check if embedding already exists
                        cursor.execute(
                            "SELECT 1 FROM contratacoes_embeddings WHERE numeroControlePNCP = %s", 
                            (numero_controle,)
                        )
                        if cursor.fetchone() is None:
                            embedding_vector = embeddings_dict[numero_controle]
                            
                            metadata = {
                                'dimensoes': len(embedding_vector),
                                'data_geracao': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            cursor.execute("""
                                INSERT INTO contratacoes_embeddings (
                                    numeroControlePNCP, embedding_vector, modelo_embedding, metadata
                                ) VALUES (%s, %s, %s, %s)
                            """, (
                                numero_controle,
                                embedding_vector,
                                "text-embedding-3-large",  # Hard-coded for now, can be made dynamic
                                json.dumps(metadata)
                            ))
                            embedding_count += 1
                    
                    # Commit every 100 records to avoid large transactions
                    if (inserted_count + embedding_count) % 100 == 0:
                        connection.commit()
                    
                except Exception as e:
                    console.print(f"[red]Erro no registro {numero_controle}: {e}[/red]")
                
                progress.update(task, advance=1)
        
        # Final commit
        connection.commit()
        console.print(f"[green]Importação concluída! {inserted_count} contratações e {embedding_count} embeddings importados.[/green]")
        return inserted_count, embedding_count
    
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file_path)}: {e}[/bold red]")
        return 0, 0

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

# Create a function for vector similarity search
def create_similarity_search_function(connection):
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
        CREATE OR REPLACE FUNCTION search_similar_contratacoes(
            query_embedding VECTOR(3072),
            similarity_threshold FLOAT DEFAULT 0.7,
            max_results INT DEFAULT 10
        )
        RETURNS TABLE (
            "numeroControlePNCP" VARCHAR,
            "descricaoCompleta" TEXT,
            "valorTotalHomologado" NUMERIC,
            "dataEncerramentoProposta" DATE,
            "unidadeOrgao_municipioNome" VARCHAR,
            "orgaoEntidade_razaosocial" VARCHAR,
            "similarity" FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                c."numeroControlePNCP",
                c."descricaoCompleta",
                c."valorTotalHomologado",
                c."dataEncerramentoProposta",
                c."unidadeOrgao_municipioNome",
                c."orgaoEntidade_razaosocial",
                1 - (e.embedding_vector <=> query_embedding) as similarity
            FROM
                contratacoes c
            JOIN
                contratacoes_embeddings e ON c."numeroControlePNCP" = e."numeroControlePNCP"
            WHERE 
                1 - (e.embedding_vector <=> query_embedding) > similarity_threshold
            ORDER BY
                similarity DESC
            LIMIT max_results;
        END;
        $$;
        """)
        
        connection.commit()
        console.print("[green]Função de busca por similaridade criada com sucesso![/green]")
    except Exception as e:
        connection.rollback()
        console.print(f"[bold red]Erro ao criar função de busca: {e}[/bold red]")
    finally:
        cursor.close()

# Main function
def main():
    console.print(Panel("[bold magenta]IMPORTAÇÃO DE DADOS PARA SUPABASE[/bold magenta]"))
    
    try:
        # Connect to database
        connection = connect_to_database()
        
        # Create tables
        create_tables(connection)
        
        # Create search function
        create_similarity_search_function(connection)
        
        # Find embeddings file
        embeddings_file = find_latest_embeddings()
        embeddings_dict = {}
        
        if embeddings_file:
            embeddings_dict = load_embeddings(embeddings_file)
        
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