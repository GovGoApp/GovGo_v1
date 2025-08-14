import os
import sqlite3
import pandas as pd
import datetime
from rich.console import Console
from rich.panel import Panel
import shutil

# Configuração de console rich para output formatado
console = Console()

# Obter a data atual para nomear os arquivos
today = datetime.date.today()
data_str = today.strftime("%Y%m%d")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Caminhos e nomes de arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_FILE = BASE_PATH + "DB\\pncp_v2.db"
OUT_DIR = BASE_PATH + "GvG\\EG\\INPUT\\NEW\\"
OUT_FILE = f"SQL_Results_{timestamp}.xlsx"

# Garantir que o diretório de saída existe
os.makedirs(OUT_DIR, exist_ok=True)

def connect_to_db():
    """Conecta ao banco de dados SQLite"""
    try:
        conn = sqlite3.connect(DB_FILE)
        console.print(f"[green]Conexão estabelecida com o banco de dados: {DB_FILE}[/green]")
        return conn
    except sqlite3.Error as e:
        console.print(f"[bold red]Erro ao conectar ao banco de dados: {e}[/bold red]")
        return None

def query_view_and_export():
    """Consulta a view vw_contratacoes e exporta para Excel"""
    # Conectar ao banco
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        # Consultar a view
        console.print("[blue]Executando consulta na view vw_contratacoes...[/blue]")
        
        # Verificar se a view existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='vw_contratacoes'")
        if not cursor.fetchone():
            console.print("[bold red]A view vw_contratacoes não existe no banco de dados![/bold red]")
            return False
        
        # Executar a consulta
        df = pd.read_sql_query("SELECT * FROM vw_contratacoes", conn)
        
        # Fechar conexão
        conn.close()
        
        # Verificar se temos dados
        if df.empty:
            console.print("[yellow]A consulta não retornou nenhum resultado.[/yellow]")
            return False
        
        console.print(f"[green]Consulta executada com sucesso. {len(df)} registros encontrados.[/green]")
        
        # Exportar para Excel
        output_path = os.path.join(OUT_DIR, OUT_FILE)
        df.to_excel(output_path, index=False)
        
        console.print(f"[green]Dados exportados para Excel: {output_path}[/green]")
        
        # Cria uma cópia de backup dos dados (opcional)
        backup_dir = BASE_PATH + "GvG\\EG\\INPUT\\BACKUP\\"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, OUT_FILE)
        shutil.copy2(output_path, backup_path)
        
        console.print(f"[blue]Backup salvo em: {backup_path}[/blue]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao consultar ou exportar dados: {e}[/bold red]")
        if conn:
            conn.close()
        return False

def main():
    console.print(Panel("[bold magenta]EXPORTAÇÃO DE DADOS - PNCP PARA EXCEL[/bold magenta]"))
    
    # Verifica se o banco de dados existe
    if not os.path.exists(DB_FILE):
        console.print(f"[bold red]Banco de dados não encontrado: {DB_FILE}[/bold red]")
        console.print("[yellow]Execute primeiro os scripts de coleta e carga de dados.[/yellow]")
        return
    
    # Executar a consulta e exportação
    success = query_view_and_export()
    
    if success:
        console.print(Panel("[bold green]EXPORTAÇÃO CONCLUÍDA COM SUCESSO![/bold green]"))
    else:
        console.print(Panel("[bold red]FALHA NA EXPORTAÇÃO DOS DADOS![/bold red]"))

if __name__ == "__main__":
    main()