import os
import pandas as pd
import glob
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
import time

console = Console()

# Constantes
MAX_ROWS_PER_SHEET = 1000000  # Limite do Excel é 1.048.576 linhas, usando 1M para margem de segurança
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CLASSY_PATH = BASE_PATH + "CLASSY\\"
ITENS_PATH = CLASSY_PATH + "CLASSY_ITENS\\"
OUTPUT_ITENS_PATH = ITENS_PATH + "OUTPUT_ITENS\\"
UNIFIED_OUTPUT = OUTPUT_ITENS_PATH + "UNIFIED_OUTPUT.xlsx"

# Definir colunas desejadas para o arquivo final
DESIRED_COLUMNS = [
    'numeroControlePNCP',
    'numeroItem',
    'ID_ITEM_CONTRATACAO',
    'descrição',
    'item_type',
    'TOP_1',
    'TOP_2',
    'TOP_3',
    'TOP_4',
    'TOP_5',
    'SCORE_1',
    'SCORE_2',
    'SCORE_3',
    'SCORE_4',
    'SCORE_5',
    'CONFIDENCE'
]

def unify_output_files():
    start_time = time.time()
    console.print("[bold magenta]Iniciando unificação de arquivos OUTPUT...[/bold magenta]")
    
    # Encontrar todos os arquivos OUTPUT_ITEM
    output_files = glob.glob(os.path.join(OUTPUT_ITENS_PATH, "OUTPUT_ITEM_*.xlsx"))
    
    if not output_files:
        console.print("[bold red]Nenhum arquivo OUTPUT_ITEM encontrado![/bold red]")
        return False
    
    console.print(f"[green]Encontrados {len(output_files)} arquivos OUTPUT_ITEM para unificar.[/green]")
    
    # Ler e unificar todos os arquivos
    all_data = []
    total_rows = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        read_task = progress.add_task("Lendo arquivos...", total=len(output_files))
        
        for file_path in output_files:
            try:
                df = pd.read_excel(file_path)
                all_data.append(df)
                total_rows += len(df)
                file_name = os.path.basename(file_path)
                progress.update(read_task, advance=1, description=f"Lendo {file_name} ({len(df)} linhas)")
            except Exception as e:
                console.print(f"[bold red]Erro ao ler o arquivo {file_path}: {str(e)}[/bold red]")
    
    if not all_data:
        console.print("[bold red]Não foi possível ler nenhum arquivo.[/bold red]")
        return False
    
    console.print(f"[green]Total de linhas lidas: {total_rows}[/green]")
    
    # Unificar todos os DataFrames
    console.print("[bold cyan]Unificando dados...[/bold cyan]")
    unified_df = pd.concat(all_data, ignore_index=True)
    console.print(f"[green]DataFrame unificado original: {len(unified_df)} linhas, {len(unified_df.columns)} colunas[/green]")
    
    # Filtrar apenas as colunas desejadas
    available_columns = [col for col in DESIRED_COLUMNS if col in unified_df.columns]
    missing_columns = [col for col in DESIRED_COLUMNS if col not in unified_df.columns]
    
    if missing_columns:
        console.print(f"[yellow]Aviso: As seguintes colunas não foram encontradas: {', '.join(missing_columns)}[/yellow]")
    
    unified_df = unified_df[available_columns]
    console.print(f"[green]DataFrame após filtragem: {len(unified_df)} linhas, {len(unified_df.columns)} colunas[/green]")
    
    # Salvar o arquivo unificado
    num_sheets = (len(unified_df) // MAX_ROWS_PER_SHEET) + (1 if len(unified_df) % MAX_ROWS_PER_SHEET > 0 else 0)
    
    console.print(f"[bold cyan]Salvando dados em {num_sheets} aba(s)...[/bold cyan]")
    
    writer = pd.ExcelWriter(UNIFIED_OUTPUT, engine='xlsxwriter')
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        save_task = progress.add_task("Salvando...", total=num_sheets)
        
        for i in range(num_sheets):
            start_idx = i * MAX_ROWS_PER_SHEET
            end_idx = min((i + 1) * MAX_ROWS_PER_SHEET, len(unified_df))
            sheet_name = f"Sheet_{i+1}"
            
            sheet_df = unified_df.iloc[start_idx:end_idx]
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            progress.update(save_task, advance=1, 
                            description=f"Salvando aba {i+1}/{num_sheets} ({end_idx-start_idx} linhas)")
    
    # Finalizar o arquivo Excel
    try:
        writer.close()
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[bold green]{'='*80}[/bold green]")
        console.print(f"[bold green]UNIFICAÇÃO CONCLUÍDA COM SUCESSO![/bold green]")
        console.print(f"[bold green]Arquivo salvo: {UNIFIED_OUTPUT}[/bold green]")
        console.print(f"[bold green]Total de arquivos: {len(output_files)}[/bold green]")
        console.print(f"[bold green]Total de linhas: {len(unified_df)}[/bold green]")
        console.print(f"[bold green]Total de colunas: {len(available_columns)}[/bold green]")
        console.print(f"[bold green]Total de abas: {num_sheets}[/bold green]")
        console.print(f"[bold green]Tempo total: {total_time/60:.2f} minutos[/bold green]")
        console.print(f"[bold green]{'='*80}[/bold green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar arquivo unificado: {str(e)}[/bold red]")
        return False

# Se executado como script principal
if __name__ == "__main__":
    try:
        unify_output_files()
    except Exception as e:
        console.print(f"[bold red]Erro na unificação: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())