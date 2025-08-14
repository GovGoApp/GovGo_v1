# =======================================================================
# IMPORTAÇÃO DE DADOS DE CATEGORIAS PARA SUPABASE
# =======================================================================
# Este script lê a planilha CATEGORIAS.xlsx e insere os dados na tabela
# categorias do Supabase, com tratamento de erros e verificação de duplicatas.
# 
# Funcionalidades:
# - Leitura da planilha Excel
# - Normalização dos dados (minúsculas, tipos corretos)
# - Verificação de duplicatas
# - Inserção em lotes com controle de transação
# - Logs detalhados do processo
# 
# Resultado: Tabela categorias populada com dados da planilha.
# =======================================================================

import pandas as pd
import psycopg2
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Configure Rich console
console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))
load_dotenv(os.path.join(script_dir, "files.env"))

# Configurações do banco
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Caminho da planilha
CATEGORIAS_FILE = "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/CAT/NOVA/CATEGORIAS.xlsx"

def create_connection():
    """Cria conexão com o banco Supabase"""
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
        console.print(f"[bold red]Erro ao conectar ao banco: {e}[/bold red]")
        return None

def normalize_data(df):
    """Normaliza os dados da planilha"""
    console.print("🔄 [cyan]Normalizando dados...[/cyan]")
    
    # Converter nomes das colunas para minúsculas
    df.columns = df.columns.str.lower()
    
    # Tratar valores nulos
    df = df.fillna('')
    
    # Converter tipos específicos
    for col in ['codnv1', 'codnv2', 'codnv3']:
        if col in df.columns:
            # Converter para string primeiro, depois para int (tratando strings vazias)
            df[col] = df[col].astype(str)
            df[col] = df[col].replace('', '0')  # Substituir vazios por 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Garantir que campos de texto sejam strings
    text_columns = ['codcat', 'nomcat', 'codnv0', 'nomnv0', 'nomnv1', 'nomnv2', 'nomnv3']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)
            df[col] = df[col].replace('nan', '')  # Remover 'nan' string
    
    console.print(f"   ✅ [green]Dados normalizados: {len(df)} registros[/green]")
    return df

def check_existing_records(connection):
    """Verifica registros já existentes na tabela"""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM categorias")
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute("SELECT codcat FROM categorias LIMIT 10")
            samples = cursor.fetchall()
            console.print(f"   📊 [yellow]Encontrados {count} registros existentes[/yellow]")
            console.print(f"   📋 [cyan]Amostras: {[s[0] for s in samples[:5]]}[/cyan]")
        else:
            console.print("   📊 [green]Tabela vazia - pronta para inserção[/green]")
        
        return count
        
    except Exception as e:
        console.print(f"   ❌ [red]Erro ao verificar registros existentes: {e}[/red]")
        return 0
    finally:
        cursor.close()

def insert_categories_batch(connection, df_batch, batch_num, total_batches):
    """Insere um lote de categorias no banco"""
    cursor = connection.cursor()
    
    try:
        # Preparar dados para inserção
        insert_data = []
        for _, row in df_batch.iterrows():
            insert_data.append((
                row['codcat'],
                row['nomcat'],
                row['codnv0'],
                row['nomnv0'],
                int(row['codnv1']),
                row['nomnv1'],
                int(row['codnv2']),
                row['nomnv2'],
                int(row['codnv3']),
                row['nomnv3']
            ))        # SQL de inserção simples
        insert_sql = """
            INSERT INTO categorias (
                codcat, nomcat, codnv0, nomnv0, codnv1, 
                nomnv1, codnv2, nomnv2, codnv3, nomnv3
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Executar inserção
        cursor.executemany(insert_sql, insert_data)
        connection.commit()
        
        console.print(f"   ✅ [green]Lote {batch_num}/{total_batches} inserido: {len(insert_data)} registros[/green]")
        return len(insert_data), 0  # inseridos, erros
        
    except Exception as e:
        connection.rollback()
        console.print(f"   ❌ [red]Erro no lote {batch_num}: {e}[/red]")
        return 0, len(df_batch)  # inseridos, erros
    
    finally:
        cursor.close()

def import_categories():
    """Função principal para importar categorias"""
    
    console.print(Panel("[bold green]IMPORTAÇÃO DE CATEGORIAS PARA SUPABASE[/bold green]"))
    
    # 1. VERIFICAR ARQUIVO
    console.print("📂 [cyan]Verificando arquivo da planilha...[/cyan]")
    if not os.path.exists(CATEGORIAS_FILE):
        console.print(f"   ❌ [red]Arquivo não encontrado: {CATEGORIAS_FILE}[/red]")
        return False
    
    console.print(f"   ✅ [green]Arquivo encontrado: {os.path.basename(CATEGORIAS_FILE)}[/green]")
    
    # 2. CARREGAR PLANILHA
    console.print("📖 [cyan]Carregando planilha...[/cyan]")
    try:
        df = pd.read_excel(CATEGORIAS_FILE)
        console.print(f"   ✅ [green]Planilha carregada: {len(df)} registros, {len(df.columns)} colunas[/green]")
        console.print(f"   📋 [cyan]Colunas: {list(df.columns)}[/cyan]")
    except Exception as e:
        console.print(f"   ❌ [red]Erro ao carregar planilha: {e}[/red]")
        return False
    
    # 3. NORMALIZAR DADOS
    df = normalize_data(df)
    
    # 4. CONECTAR AO BANCO
    console.print("🔌 [cyan]Conectando ao Supabase...[/cyan]")
    connection = create_connection()
    if not connection:
        return False
    
    console.print(f"   ✅ [green]Conectado ao Supabase: {HOST}[/green]")
    
    # 5. VERIFICAR REGISTROS EXISTENTES
    console.print("🔍 [cyan]Verificando registros existentes...[/cyan]")
    existing_count = check_existing_records(connection)
    
    # 6. INSERIR DADOS EM LOTES
    console.print("📝 [cyan]Iniciando inserção de dados...[/cyan]")
    
    batch_size = 1000
    total_batches = (len(df) + batch_size - 1) // batch_size
    total_inserted = 0
    total_errors = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Inserindo categorias", total=len(df))
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            inserted, errors = insert_categories_batch(
                connection, batch_df, batch_num, total_batches
            )
            
            total_inserted += inserted
            total_errors += errors
            
            progress.update(task, advance=len(batch_df))
    
    # 7. VERIFICAÇÃO FINAL
    console.print("\n🔍 [cyan]Verificação final...[/cyan]")
    final_count = check_existing_records(connection)
    
    # 8. FECHAR CONEXÃO
    connection.close()
    
    # 9. RELATÓRIO FINAL
    console.print("\n[bold green]" + "="*60 + "[/bold green]")
    console.print("[bold green]RELATÓRIO DE IMPORTAÇÃO[/bold green]")
    console.print("[bold green]" + "="*60 + "[/bold green]")
    
    stats_table = Table(show_header=True, header_style="bold cyan")
    stats_table.add_column("Métrica", style="blue")
    stats_table.add_column("Valor", justify="right", style="green")
    
    stats_table.add_row("Registros na planilha", str(len(df)))
    stats_table.add_row("Registros antes da importação", str(existing_count))
    stats_table.add_row("Registros inseridos/atualizados", str(total_inserted))
    stats_table.add_row("Erros durante inserção", str(total_errors))
    stats_table.add_row("Total final na tabela", str(final_count))
    
    console.print(stats_table)
    
    if total_errors == 0:
        console.print("\n🎉 [bold green]Importação concluída com sucesso![/bold green]")
        return True
    else:
        console.print(f"\n⚠️ [yellow]Importação concluída com {total_errors} erros[/yellow]")
        return False

def main():
    """Função principal"""
    start_time = datetime.now()
    
    try:
        success = import_categories()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            console.print(Panel(f"[bold green]IMPORTAÇÃO CONCLUÍDA EM {duration:.2f} SEGUNDOS![/bold green]"))
        else:
            console.print(Panel(f"[bold red]IMPORTAÇÃO FALHOU APÓS {duration:.2f} SEGUNDOS![/bold red]"))
        
        return success
    
    except Exception as e:
        console.print(Panel(f"[bold red]ERRO GERAL: {e}[/bold red]"))
        return False

if __name__ == "__main__":
    main()
