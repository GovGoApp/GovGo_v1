import os
import sqlite3
import pandas as pd
import math
from tqdm.auto import tqdm
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize console for rich output
console = Console()

# Define paths and constants
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp_v2.db")  # New database file
OUTPUT_DIR = os.path.join(BASE_PATH, "CLASSY", "INPUT_ITENS")
CHUNK_SIZE = 20000  # Number of rows per output file

# SQL query to execute
QUERY = """
SELECT c.numeroControlePNCP, ic.numeroItem, c.objetoCompra, ic.descricao, ic.materialOuServico, ic.itemCategoriaNome
FROM contratacao c, item_contratacao ic 
WHERE c.numeroControlePNCP = ic.numeroControlePNCP
"""

def extract_items():
    """Extract items from database and save in chunks"""
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    console.print(f"[bold blue]Connecting to database: {DB_FILE}[/bold blue]")
    
    try:
        # Connect to database and execute query
        with Progress(SpinnerColumn(), TextColumn("[bold white]{task.description}[/bold white]")) as progress:
            task = progress.add_task("Executing SQL query...", total=1)
            
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query(QUERY, conn)
            conn.close()
            
            progress.update(task, completed=1)
        
        # Report total rows found
        total_rows = len(df)
        console.print(f"[bold green]Successfully retrieved {total_rows:,} rows from database[/bold green]")
        
        # Calculate number of chunks needed
        total_chunks = math.ceil(total_rows / CHUNK_SIZE)
        console.print(f"[bold cyan]Splitting into {total_chunks} files with {CHUNK_SIZE} rows each[/bold cyan]")
        
        # Process and save each chunk
        for chunk_idx in tqdm(range(total_chunks), desc="Saving files"):
            start_idx = chunk_idx * CHUNK_SIZE
            end_idx = min(start_idx + CHUNK_SIZE, total_rows)
            
            chunk_df = df.iloc[start_idx:end_idx].copy()
            
            # Create output filename
            output_file = os.path.join(OUTPUT_DIR, f"INPUT_ITEM_{chunk_idx+1:03d}.xlsx")
            
            # Save to Excel file
            chunk_df.to_excel(output_file, index=False)
        
        console.print(f"[bold green]Processing complete! {total_chunks} files generated in:[/bold green]")
        console.print(f"[bold cyan]{OUTPUT_DIR}[/bold cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Error during processing: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return False

if __name__ == "__main__":
    extract_items()