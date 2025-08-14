# =======================================================================
# [5/7] EXPORTAÇÃO DE VIEWS PARA EXCEL
# =======================================================================
# Este script gera relatórios em Excel a partir dos dados do banco SQLite,
# criando planilhas organizadas para análise.
# 
# Funcionalidades:
# - Executa consultas SQL para obter dados relevantes
# - Formata e organiza os dados em planilhas Excel
# - Cria visualizações agregadas e detalhadas dos dados
# 
# Arquivo de saída: Planilhas Excel com dados formatados.
# =======================================================================

import os
import sqlite3
import pandas as pd
import datetime
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Configuração de console rich para output formatado
console = Console()

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    # Não incluir timestamp, apenas a mensagem com ícone
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))

# Obter a data atual para nomear os arquivos
today = datetime.date.today()
data_str = today.strftime("%Y%m%d")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Usar caminhos do arquivo de configuração
DB_FILE = os.getenv("DB_FILE")
OUT_DIR = os.getenv("NEW_PATH")
OUT_FILE = f"SQL_Results_{timestamp}.xlsx"

# Garantir que o diretório de saída existe
os.makedirs(OUT_DIR, exist_ok=True)

def connect_to_db():
    """Conecta ao banco de dados SQLite"""
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        log_message(f"Erro na conexão: {e}", "error")
        return None

def query_view_and_export():
    """Consulta a view vw_contratacoes e exporta para Excel"""
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        # Verificar se a view existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='vw_contratacoes'")
        if not cursor.fetchone():
            log_message("View vw_contratacoes não encontrada", "error")
            return False
        
        # Executar a consulta
        log_message("Executando consulta na view...")
        df = pd.read_sql_query("SELECT * FROM vw_contratacoes", conn)
        conn.close()
        
        # Verificar se temos dados
        if df.empty:
            log_message("Consulta sem resultados", "warning")
            console.print(Panel("[bold yellow]⚠️ SEM DADOS PARA EXPORTAR[/bold yellow]"))
            return False
        
        # Exportar para Excel
        output_path = os.path.join(OUT_DIR, OUT_FILE)
        df.to_excel(output_path, index=False)
        
        log_message(f"Dados exportados: {len(df):,} registros", "success")
        return True
    
    except Exception as e:
        log_message(f"Erro na exportação: {e}", "error")
        if conn:
            conn.close()
        return False

def check_new_records():
    """Verifica se houve inserção de novos registros nos scripts anteriores"""
    try:
        # Caminho do arquivo de log
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGS")
        log_file = os.path.join(log_dir, "processamento.log")
        
        # Se o arquivo não existir, não continuar
        if not os.path.exists(log_file):
            return False
            
        # Obter a data atual para filtrar apenas registros de hoje
        data_atual = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Ler o arquivo de log
        with open(log_file, "r") as f:
            lines = f.readlines()
            
        # Filtrar apenas as linhas de hoje
        todays_lines = [line for line in lines if line.startswith(data_atual)]
        
        if not todays_lines:
            return False
            
        # Verificar se algum script adicionou registros
        for line in todays_lines:
            if "SCRIPT03:" in line or "SCRIPT04:" in line:
                # Extrair o número de registros adicionados
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        count = int(parts[1].split()[0])
                        if count > 0:
                            # Se encontrou pelo menos um registro adicionado, continuar
                            return True
                    except ValueError:
                        # Se não conseguir converter para int, ignorar esta linha
                        pass
                        
        # Se chegou aqui, nenhum script adicionou registros
        return False
        
    except Exception as e:
        print(f"Erro ao verificar registros no log: {e}")
        return False  # Em caso de erro, não continuar

def main():
    console.print(Panel("[bold blue][5/7] EXPORTAÇÃO PARA EXCEL[/bold blue]"))

    # Verifica se o banco de dados existe
    if not os.path.exists(DB_FILE):
        log_message(f"Banco não encontrado: {DB_FILE}", "error")
        console.print(Panel("[bold red]❌ BANCO NÃO ENCONTRADO[/bold red]"))
        return
    
    # Verifica se houve novos registros a serem processados
    if not check_new_records():
        log_message("Nenhum novo registro encontrado para processamento", "success")
        return
    
    # Executar a consulta e exportação
    success = query_view_and_export()
    
    if success:
        log_message("Exportação concluída", "success")
        console.print(Panel("[bold green]✅ EXPORTAÇÃO CONCLUÍDA[/bold green]"))
    else:
        log_message("Falha na exportação", "error")
        console.print(Panel("[bold red]❌ FALHA NA EXPORTAÇÃO[/bold red]"))

if __name__ == "__main__":
    main()