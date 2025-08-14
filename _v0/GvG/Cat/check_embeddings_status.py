# =======================================================================
# VERIFICAÇÃO E COMPLETAR EMBEDDINGS FALTANTES
# =======================================================================
# Script para verificar quantas categorias ainda não têm embeddings
# e processar apenas as faltantes.
# =======================================================================

import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Configure Rich console
console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))

# Fetch connection variables
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

def create_connection():
    """Cria conexão com o banco"""
    try:
        connection = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME,
            connect_timeout=30
        )
        return connection
    except Exception as e:
        console.print(f"[bold red]Erro ao conectar: {e}[/bold red]")
        return None

def check_embedding_status():
    """Verifica o status dos embeddings na tabela categorias"""
    connection = create_connection()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    try:
        # Total de categorias
        cursor.execute("SELECT COUNT(*) FROM categorias")
        total_categories = cursor.fetchone()[0]
        
        # Categorias com embeddings
        cursor.execute("SELECT COUNT(*) FROM categorias WHERE cat_embeddings IS NOT NULL")
        with_embeddings = cursor.fetchone()[0]
        
        # Categorias sem embeddings
        cursor.execute("SELECT COUNT(*) FROM categorias WHERE cat_embeddings IS NULL")
        without_embeddings = cursor.fetchone()[0]
        
        console.print(Panel("[bold cyan]STATUS DOS EMBEDDINGS DE CATEGORIAS[/bold cyan]"))
        
        # Criar tabela de status
        status_table = Table(show_header=True, header_style="bold cyan")
        status_table.add_column("Métrica", style="blue")
        status_table.add_column("Quantidade", justify="right", style="green")
        status_table.add_column("Percentual", justify="right", style="yellow")
        
        status_table.add_row("Total de Categorias", f"{total_categories:,}", "100.0%")
        status_table.add_row("Com Embeddings", f"{with_embeddings:,}", f"{(with_embeddings/total_categories*100):.1f}%")
        status_table.add_row("Sem Embeddings", f"{without_embeddings:,}", f"{(without_embeddings/total_categories*100):.1f}%")
        
        console.print(status_table)
        
        if without_embeddings > 0:
            console.print(f"\n[yellow]⚠️ Ainda restam {without_embeddings:,} categorias sem embeddings![/yellow]")
            console.print("[cyan]Execute o script generate_category_embeddings.py para processar as faltantes.[/cyan]")
            
            # Mostrar algumas categorias sem embeddings
            cursor.execute("""
                SELECT codcat, nomcat 
                FROM categorias 
                WHERE cat_embeddings IS NULL 
                ORDER BY codcat 
                LIMIT 10
            """)
            missing_samples = cursor.fetchall()
            
            if missing_samples:
                console.print("\n[bold blue]Exemplos de categorias sem embeddings:[/bold blue]")
                for codcat, nomcat in missing_samples:
                    console.print(f"  • {codcat}: {nomcat[:80]}{'...' if len(nomcat) > 80 else ''}")
                
                if without_embeddings > 10:
                    console.print(f"  ... e mais {without_embeddings - 10} categorias")
        else:
            console.print("\n[bold green]✅ Todas as categorias já possuem embeddings![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro ao verificar status: {e}[/bold red]")
    
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    check_embedding_status()
