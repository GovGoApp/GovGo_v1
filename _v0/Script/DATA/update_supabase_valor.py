# update_supabase_valor.py
import os
import sqlite3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress

console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))

# Configurações SQLite
DB_FILE = os.getenv("DB_FILE")

# Configurações Supabase
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

def main():
    console.print("[bold blue]Atualizando valorTotalEstimado no Supabase (apenas para registros existentes)[/bold blue]")
    
    try:
        # Conectar ao Supabase primeiro para obter os IDs existentes
        console.print("Conectando ao Supabase para obter IDs existentes...")
        pg_conn = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME
        )
        pg_cursor = pg_conn.cursor()
        
        # Verificar se a coluna valorTotalEstimado existe
        pg_cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'contratacoes' AND column_name = 'valortotalestimado'")
        column_exists = pg_cursor.fetchone()
        
        # Se a coluna não existir, criar
        if not column_exists:
            console.print("Criando nova coluna valorTotalEstimado...")
            pg_cursor.execute("ALTER TABLE contratacoes ADD COLUMN valorTotalEstimado DECIMAL")
            pg_conn.commit()
        
        # Obter todos os IDs do Supabase
        console.print("Obtendo IDs de contratações existentes no Supabase...")
        pg_cursor.execute("SELECT numerocontrolepncp FROM contratacoes")
        supabase_ids = [row[0] for row in pg_cursor.fetchall()]
        
        console.print(f"Encontrados {len(supabase_ids)} IDs no Supabase")
        
        # Conectar ao SQLite
        console.print("Conectando ao SQLite...")
        sqlite_conn = sqlite3.connect(DB_FILE)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Processar IDs em lotes para evitar consultas muito grandes
        batch_size = 1000
        all_data = []
        
        with Progress() as progress:
            task = progress.add_task("Obtendo dados do SQLite...", total=len(supabase_ids))
            
            for i in range(0, len(supabase_ids), batch_size):
                batch_ids = supabase_ids[i:i+batch_size]
                
                # Criar placeholders para a consulta
                placeholders = ','.join(['?'] * len(batch_ids))
                
                # Consultar SQLite para obter valorTotalEstimado para esses IDs
                query = f"""
                SELECT numeroControlePNCP, valorTotalEstimado 
                FROM contratacao 
                WHERE numeroControlePNCP IN ({placeholders})
                AND valorTotalEstimado IS NOT NULL
                """
                
                sqlite_cursor.execute(query, batch_ids)
                batch_data = sqlite_cursor.fetchall()
                all_data.extend(batch_data)
                
                progress.update(task, advance=len(batch_ids))
        
        sqlite_conn.close()
        
        console.print(f"Obtidos {len(all_data)} registros com valorTotalEstimado do SQLite")
        
        if not all_data:
            console.print("[yellow]Nenhum dado para atualizar[/yellow]")
            return
        
        # Atualizar registros no Supabase em lotes
        update_batch_size = 500
        total_updated = 0
        
        with Progress() as progress:
            task = progress.add_task("Atualizando registros no Supabase...", total=len(all_data))
            
            for i in range(0, len(all_data), update_batch_size):
                batch = all_data[i:i+update_batch_size]
                
                # Preparar dados para atualização
                tuples = [(valor, id) for id, valor in batch]
                
                # Executar atualização
                pg_cursor.executemany(
                    "UPDATE contratacoes SET valorTotalEstimado = %s WHERE numerocontrolepncp = %s",
                    tuples
                )
                
                total_updated += pg_cursor.rowcount
                progress.update(task, advance=len(batch))
                pg_conn.commit()
        
        console.print(f"[green]Atualização concluída! {total_updated} registros atualizados[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro: {e}[/bold red]")
    finally:
        if 'pg_conn' in locals() and pg_conn:
            pg_conn.close()
        if 'sqlite_conn' in locals() and sqlite_conn:
            sqlite_conn.close()

if __name__ == "__main__":
    main()