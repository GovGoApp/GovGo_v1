import os
import psycopg2
from dotenv import load_dotenv
from rich.console import Console
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
console.print(f"[blue]Arquivo .env procurado em: {env_path}")
console.print(f"[green]USER: {'encontrado' if USER else 'não encontrado'}")
console.print(f"[green]PASSWORD: {'encontrado' if PASSWORD else 'não encontrado (ou vazio)'}")
console.print(f"[green]HOST: {HOST}")
console.print(f"[green]PORT: {PORT}")
console.print(f"[green]DBNAME: {DBNAME}")
console.print()

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

# Create search function for vector similarity
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

# Function to verify if tables exist and show their structure
def verify_tables(connection):
    cursor = connection.cursor()
    
    try:
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if 'contratacoes' in existing_tables and 'contratacoes_embeddings' in existing_tables:
            console.print("[green]✓ Ambas as tabelas existem![/green]")
        else:
            missing = []
            if 'contratacoes' not in existing_tables:
                missing.append('contratacoes')
            if 'contratacoes_embeddings' not in existing_tables:
                missing.append('contratacoes_embeddings')
            console.print(f"[bold red]✗ Tabelas ausentes: {', '.join(missing)}[/bold red]")
            return False
        
        # Check for pgvector extension
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cursor.fetchone() is None:
            console.print("[bold red]✗ Extensão pgvector não está instalada![/bold red]")
            return False
        else:
            console.print("[green]✓ Extensão pgvector está instalada[/green]")
        
        # Check for search function
        cursor.execute("SELECT proname FROM pg_proc WHERE proname = 'search_similar_contratacoes'")
        if cursor.fetchone() is None:
            console.print("[bold red]✗ Função search_similar_contratacoes não existe[/bold red]")
        else:
            console.print("[green]✓ Função search_similar_contratacoes existe[/green]")
        
        # Show table structures
        for table in ['contratacoes', 'contratacoes_embeddings']:
            cursor.execute(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            
            columns = cursor.fetchall()
            
            table_display = Table(title=f"Estrutura da Tabela: {table}")
            table_display.add_column("Coluna", style="cyan")
            table_display.add_column("Tipo", style="green")
            table_display.add_column("Tamanho", style="yellow")
            
            for col in columns:
                name, dtype, length = col
                length_str = str(length) if length else "-"
                table_display.add_row(name, dtype, length_str)
            
            console.print(table_display)
        
        # Count records
        for table in ['contratacoes', 'contratacoes_embeddings']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            console.print(f"[blue]Registros na tabela {table}: {count}[/blue]")
            
        return True
        
    except Exception as e:
        console.print(f"[bold red]Erro ao verificar tabelas: {e}[/bold red]")
        return False
    finally:
        cursor.close()

def main():
    console.print(Panel("[bold magenta]CRIAÇÃO E VERIFICAÇÃO DE TABELAS NO SUPABASE[/bold magenta]"))
    
    try:
        # Connect to database
        connection = connect_to_database()
        
        # Check if tables exist
        tables_verified = verify_tables(connection)
        
        if not tables_verified:
            console.print(Panel("[yellow]Criando tabelas necessárias...[/yellow]"))
            # Create tables
            create_tables(connection)
            
            # Create search function
            create_similarity_search_function(connection)
            
            # Verify again after creation
            console.print(Panel("[yellow]Verificando tabelas após criação...[/yellow]"))
            verify_tables(connection)
        else:
            console.print("[green]Todas as tabelas e estruturas necessárias já existem.[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro durante a operação: {e}[/bold red]")
    finally:
        if connection:
            connection.close()
            console.print("[blue]Conexão com o banco encerrada.[/blue]")

if __name__ == "__main__":
    main()