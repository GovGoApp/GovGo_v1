import os
import sqlite3
import pandas as pd
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from datetime import datetime

console = Console()

# Definindo os caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"
ALL_ITENS_PATH = BASE_PATH + "CLASSY\\CLASSY_ITENS\\ALL_ITENS\\"

def export_high_confidence_items():
    """Exporta itens com alta confiança (CONFIDENCE > 80 e SCORE_1 > 0.8) para Excel"""
    console.log(f"[bold cyan]Exportando itens de alta confiança para {ALL_ITENS_PATH}[/bold cyan]")
    
    # Garantir que o diretório de destino existe
    os.makedirs(ALL_ITENS_PATH, exist_ok=True)
    
    # Conectar ao banco de dados
    conn = sqlite3.connect(DB_FILE)
    
    try:
        # Verificar se a tabela existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_classificacao'")
        if not cursor.fetchone():
            console.log("[bold red]Tabela 'item_classificacao' não existe no banco de dados![/bold red]")
            return
        
        # Consultar quantidade de registros que atendem aos critérios
        cursor.execute("""
            SELECT COUNT(*) FROM item_classificacao 
            WHERE CONFIDENCE > 80 AND SCORE_1 > 0.8
        """)
        total_registros = cursor.fetchone()[0]
        console.log(f"[cyan]Encontrados {total_registros} registros com CONFIDENCE > 80 e SCORE_1 > 0.8[/cyan]")
        
        if total_registros == 0:
            console.log("[yellow]Nenhum registro encontrado com os critérios especificados.[/yellow]")
            return
            
        # Definir nome do arquivo de saída com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_excel = os.path.join(ALL_ITENS_PATH, f"ITEMS_Sg80_Cg70_{timestamp}.xlsx")
        
        # Fazer a consulta SQL
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("Exportando dados...", total=2) # 2 etapas: consulta e salvamento
            
            # Consultar dados
            query = """
                SELECT * FROM item_classificacao 
                WHERE CONFIDENCE > 80 AND SCORE_1 > 0.7
                ORDER BY CONFIDENCE DESC, SCORE_1 DESC
            """
            console.log("[cyan]Executando consulta SQL...[/cyan]")
            df = pd.read_sql_query(query, conn)
            progress.update(task, advance=1)
            
            # Salvar para Excel
            console.log(f"[cyan]Salvando {len(df)} registros para Excel...[/cyan]")
            df.to_excel(output_excel, index=False)
            
            progress.update(task, advance=1)
        
        console.log(f"[bold green]Exportação concluída![/bold green]")
        console.log(f"[green]Arquivo Excel: {output_excel}[/green]")
        
        # Mostrar resumo dos dados
        console.log(f"[bold cyan]Resumo dos dados exportados:[/bold cyan]")
        console.log(f"Total de registros: {len(df)}")
        console.log(f"Média de CONFIDENCE: {df['CONFIDENCE'].mean():.2f}")
        console.log(f"Média de SCORE_1: {df['SCORE_1'].mean():.4f}")
        
        # Distribuição por tipo de item
        if 'item_type' in df.columns:
            item_type_counts = df['item_type'].value_counts()
            console.log("[cyan]Distribuição por tipo de item:[/cyan]")
            for item_type, count in item_type_counts.items():
                console.log(f"  {item_type}: {count} registros")
            
    except Exception as e:
        console.log(f"[bold red]Erro durante a exportação: {str(e)}[/bold red]")
        import traceback
        console.log(traceback.format_exc())
    finally:
        conn.close()

if __name__ == "__main__":
    export_high_confidence_items()