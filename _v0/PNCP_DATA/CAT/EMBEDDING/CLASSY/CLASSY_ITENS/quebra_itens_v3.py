 # Create descrição: only  descricao (explicitly NOT using objetoCompra and NOT MS)
       

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
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"
OUTPUT_DIR = BASE_PATH + "CLASSY\\CLASSY_ITENS\\INPUT_ITENS_ALONE_ONLY\\"
CHUNK_SIZE = 20000  # Number of rows per output file

# Updated SQL query to include ID_ITEM_CONTRATACAO
QUERY = """
SELECT c.numeroControlePNCP, ic.ID_ITEM_CONTRATACAO, ic.numeroItem, c.objetoCompra, ic.descricao, ic.materialOuServico
FROM contratacao c, item_contratacao ic 
WHERE c.numeroControlePNCP = ic.numeroControlePNCP
"""

def extract_items():
    """Extract items from database and save in chunks with custom formatting"""
    
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
        
        # Process the data to create the formatted description field
        console.print("[bold blue]Processing data into required format...[/bold blue]")
        
        # Create descrição: combine materialOuServico, objetoCompra and descricao
        df['descrição'] = df.apply(
            lambda row: f"{row['descricao']}",
            axis=1
        )
        
        # Create a new DataFrame with the required columns (keeping IDs separate)
        df_final = df[['numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição']].copy()
        
        # Calculate number of chunks needed
        total_chunks = math.ceil(total_rows / CHUNK_SIZE)
        console.print(f"[bold cyan]Splitting into {total_chunks} files with {CHUNK_SIZE} rows each[/bold cyan]")
        
        # Process and save each chunk
        for chunk_idx in tqdm(range(total_chunks), desc="Saving files"):
            start_idx = chunk_idx * CHUNK_SIZE
            end_idx = min(start_idx + CHUNK_SIZE, total_rows)
            
            chunk_df = df_final.iloc[start_idx:end_idx].copy()
            
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