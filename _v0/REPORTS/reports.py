import os
import sqlite3
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Configuração dos caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")

if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

console = Console()

def read_multiline_input():
    """
    Permite colar sua consulta SQL (em múltiplas linhas) no prompt.
    Para finalizar, basta pressionar ENTER em uma linha vazia.
    """
    console.print("[bold green]Cole sua consulta SQL abaixo.[/bold green]")
    console.print("Para finalizar, pressione ENTER em uma linha vazia.\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines)

def execute_query(query, db_file=DB_FILE):
    """
    Conecta à base SQLite, executa a query e retorna um DataFrame.
    """
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row  # para retornar linhas como dicionário
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao executar a query:[/bold red] {e}")
        return None

def save_df_to_excel(df, output_filename):
    """
    Salva o DataFrame em um arquivo Excel no diretório REPORTS.
    """
    file_path = os.path.join(REPORTS_PATH, output_filename)
    try:
        df.to_excel(file_path, index=False)
        return file_path
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar o arquivo Excel:[/bold red] {e}")
        return None

def vacuum_db(db_file=DB_FILE):
    """
    Executa o comando VACUUM para recompactar o banco de dados.
    """
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("VACUUM;")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        console.print(f"[bold red]Erro ao executar VACUUM:[/bold red] {e}")
        return False

if __name__ == '__main__':
    # Lê a consulta SQL (entrada multilinhas sem precisar digitar "FIM")
    sql_query = read_multiline_input()
    if not sql_query.strip():
        console.print("[bold red]Consulta SQL vazia. Encerrando.[/bold red]")
        exit(1)

    # Usamos um objeto Progress com spinner para acompanhar as três etapas:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        # Etapa 1: Executar a query
        task_query = progress.add_task("Executando query...", total=1)
        df_result = execute_query(sql_query)
        progress.advance(task_query, 1)

        if df_result is None:
            console.print("[bold red]Nenhum dado foi retornado ou ocorreu um erro na query.[/bold red]")
            exit(1)

        # Etapa 2: Salvar o resultado em Excel
        task_save = progress.add_task("Salvando arquivo...", total=1)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"report_{timestamp}.xlsx"
        file_path = save_df_to_excel(df_result, output_filename)
        progress.advance(task_save, 1)
        if file_path:
            console.print(f"[bold green]Relatório salvo em:[/bold green] {file_path}")
        else:
            console.print("[bold red]Erro ao salvar o relatório.[/bold red]")
        
        # Etapa 3: Executar VACUUM
        #task_vac = progress.add_task("Executando VACUUM...", total=1)
        #if vacuum_db():
        #    progress.advance(task_vac, 1)
        #    console.print("[bold green]VACUUM executado com sucesso![/bold green]")
        #else:
        #    console.print("[bold red]Erro ao executar VACUUM.[/bold red]")
