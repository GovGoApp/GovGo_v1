# =======================================================================
# LEITOR DE PLANILHA CATEGORIAS - ANÁLISE DE ESTRUTURA
# =======================================================================
# Este script lê a planilha CATEGORIAS.xlsx e analisa sua estrutura
# para gerar automaticamente o script de criação da tabela no Supabase.
# 
# Funcionalidades:
# - Leitura completa da planilha Excel
# - Análise dos tipos de dados de cada coluna
# - Detecção de valores únicos e padrões
# - Geração de relatório da estrutura dos dados
# - Preparação para criação da tabela no banco
# 
# Resultado: Relatório completo da estrutura para criação da tabela.
# =======================================================================

import pandas as pd
import numpy as np
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
import re

# Configure Rich console
console = Console()

def analyze_column_data(series, column_name):
    """Analisa uma coluna e retorna informações sobre seu tipo e características"""
    
    analysis = {
        'column_name': column_name,
        'total_rows': len(series),
        'non_null_count': series.notna().sum(),
        'null_count': series.isna().sum(),
        'unique_count': series.nunique(),
        'data_type': str(series.dtype),
        'sample_values': [],
        'max_length': 0,
        'suggested_sql_type': 'TEXT',
        'has_numbers': False,
        'has_dates': False,
        'is_boolean': False
    }
    
    # Obter valores não nulos para análise
    non_null_values = series.dropna()
    
    if len(non_null_values) > 0:
        # Amostras de valores (primeiros 5 únicos)
        analysis['sample_values'] = non_null_values.unique()[:5].tolist()
        
        # Analisar comprimento máximo para strings
        if series.dtype == 'object':
            str_lengths = non_null_values.astype(str).str.len()
            analysis['max_length'] = str_lengths.max()
            
            # Verificar se contém números
            analysis['has_numbers'] = any(re.search(r'\d', str(val)) for val in non_null_values[:100])
            
            # Verificar se são valores booleanos
            unique_vals = set(str(val).lower() for val in non_null_values.unique())
            boolean_vals = {'true', 'false', 'sim', 'não', 'yes', 'no', '1', '0'}
            analysis['is_boolean'] = unique_vals.issubset(boolean_vals) and len(unique_vals) <= 2
            
            # Tentar detectar datas
            try:
                pd.to_datetime(non_null_values.head(10))
                analysis['has_dates'] = True
            except:
                analysis['has_dates'] = False
        
        # Sugerir tipo SQL baseado na análise
        if analysis['is_boolean']:
            analysis['suggested_sql_type'] = 'BOOLEAN'
        elif series.dtype in ['int64', 'int32']:
            analysis['suggested_sql_type'] = 'INTEGER'
        elif series.dtype in ['float64', 'float32']:
            analysis['suggested_sql_type'] = 'DECIMAL'
        elif analysis['has_dates']:
            analysis['suggested_sql_type'] = 'TIMESTAMP'
        elif analysis['max_length'] <= 50:
            analysis['suggested_sql_type'] = 'VARCHAR(100)'
        elif analysis['max_length'] <= 255:
            analysis['suggested_sql_type'] = 'VARCHAR(500)'
        else:
            analysis['suggested_sql_type'] = 'TEXT'
    
    return analysis

def read_and_analyze_excel():
    """Lê e analisa a planilha CATEGORIAS.xlsx"""
    
    console.print(Panel("[bold green]ANÁLISE DA PLANILHA CATEGORIAS[/bold green]"))
    
    # Caminho do arquivo Excel
    excel_path = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\CAT\NOVA\CATEGORIAS.xlsx"
    
    console.print(f"📂 [cyan]Lendo arquivo: {excel_path}[/cyan]")
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(excel_path):
            console.print(f"[red]❌ Arquivo não encontrado: {excel_path}[/red]")
            return None
        
        # Ler todas as abas da planilha
        excel_file = pd.ExcelFile(excel_path)
        console.print(f"📊 [green]Abas encontradas: {excel_file.sheet_names}[/green]")
        
        # Ler a primeira aba (ou a única aba)
        df = pd.read_excel(excel_path, sheet_name=0)
        
        console.print(f"📈 [yellow]Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas[/yellow]")
        
        # Mostrar primeiras linhas
        console.print("\n📋 [bold blue]PRIMEIRAS 5 LINHAS:[/bold blue]")
        table = Table()
        
        # Adicionar colunas à tabela
        for col in df.columns:
            table.add_column(str(col), style="cyan", no_wrap=True)
        
        # Adicionar primeiras 5 linhas
        for idx in range(min(5, len(df))):
            row_data = []
            for col in df.columns:
                value = df.iloc[idx][col]
                if pd.isna(value):
                    row_data.append("[red]NULL[/red]")
                else:
                    # Truncar valores muito longos
                    str_val = str(value)
                    if len(str_val) > 30:
                        str_val = str_val[:27] + "..."
                    row_data.append(str_val)
            table.add_row(*row_data)
        
        console.print(table)
        
        # Análise detalhada de cada coluna
        console.print("\n🔍 [bold magenta]ANÁLISE DETALHADA DAS COLUNAS:[/bold magenta]")
        
        column_analyses = []
        
        with Progress() as progress:
            task = progress.add_task("Analisando colunas...", total=len(df.columns))
            
            for col in df.columns:
                analysis = analyze_column_data(df[col], col)
                column_analyses.append(analysis)
                progress.update(task, advance=1)
        
        # Criar tabela de análise
        analysis_table = Table()
        analysis_table.add_column("Campo", style="green", width=20)
        analysis_table.add_column("Tipo Atual", style="yellow", width=12)
        analysis_table.add_column("Não Nulos", style="cyan", width=10)
        analysis_table.add_column("Únicos", style="blue", width=8)
        analysis_table.add_column("Tam. Máx", style="magenta", width=10)
        analysis_table.add_column("SQL Sugerido", style="red", width=15)
        analysis_table.add_column("Amostras", style="white", width=30)
        
        for analysis in column_analyses:
            # Preparar amostras para exibição
            samples_str = ", ".join(str(val) for val in analysis['sample_values'])
            if len(samples_str) > 25:
                samples_str = samples_str[:22] + "..."
            
            analysis_table.add_row(
                analysis['column_name'],
                analysis['data_type'],
                f"{analysis['non_null_count']}/{analysis['total_rows']}",
                str(analysis['unique_count']),
                str(analysis['max_length']),
                analysis['suggested_sql_type'],
                samples_str
            )
        
        console.print(analysis_table)
        
        # Gerar script SQL de criação da tabela
        console.print("\n🏗️ [bold green]SCRIPT SQL SUGERIDO:[/bold green]")
        
        sql_script = generate_create_table_sql(column_analyses)
        console.print(Panel(sql_script, title="CREATE TABLE categorias", expand=False))
        
        # Salvar análise em arquivo
        save_analysis_to_file(column_analyses, df, sql_script)
        
        return column_analyses, df
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao ler planilha: {e}[/red]")
        return None

def generate_create_table_sql(column_analyses):
    """Gera o script SQL CREATE TABLE baseado na análise"""
    
    sql_lines = ["CREATE TABLE IF NOT EXISTS categorias ("]
    sql_lines.append("    id SERIAL PRIMARY KEY,")
    
    for analysis in column_analyses:
        # Converter nome da coluna para minúsculas e remover espaços
        col_name = analysis['column_name'].lower().replace(' ', '_').replace('-', '_')
        col_name = re.sub(r'[^a-z0-9_]', '', col_name)  # Remover caracteres especiais
        
        # Determinar se é NOT NULL baseado na presença de valores
        null_clause = "NOT NULL" if analysis['null_count'] == 0 else ""
        
        sql_lines.append(f"    {col_name} {analysis['suggested_sql_type']} {null_clause},")
    
    # Adicionar campo de embeddings
    sql_lines.append("    cat_embeddings VECTOR(3072),")  # Mesmo tamanho de contratacoes_embeddings
    sql_lines.append("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    sql_lines.append(");")
    
    # Adicionar índices sugeridos
    sql_lines.append("")
    sql_lines.append("-- Índices sugeridos:")
    sql_lines.append("CREATE INDEX IF NOT EXISTS idx_categorias_embeddings ON categorias USING ivfflat (cat_embeddings vector_cosine_ops);")
    
    return "\n".join(sql_lines)

def save_analysis_to_file(column_analyses, df, sql_script):
    """Salva a análise em um arquivo de texto"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f"categorias_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ANÁLISE DA PLANILHA CATEGORIAS.xlsx\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"DIMENSÕES: {df.shape[0]} linhas x {df.shape[1]} colunas\n\n")
        
        f.write("ANÁLISE DAS COLUNAS:\n")
        f.write("-" * 50 + "\n")
        
        for analysis in column_analyses:
            f.write(f"Campo: {analysis['column_name']}\n")
            f.write(f"  Tipo atual: {analysis['data_type']}\n")
            f.write(f"  Total de linhas: {analysis['total_rows']}\n")
            f.write(f"  Valores não nulos: {analysis['non_null_count']}\n")
            f.write(f"  Valores únicos: {analysis['unique_count']}\n")
            f.write(f"  Comprimento máximo: {analysis['max_length']}\n")
            f.write(f"  Tipo SQL sugerido: {analysis['suggested_sql_type']}\n")
            f.write(f"  Amostras: {analysis['sample_values']}\n")
            f.write("-" * 30 + "\n")
        
        f.write("\nSCRIPT SQL GERADO:\n")
        f.write("=" * 50 + "\n")
        f.write(sql_script)
        f.write("\n")
    
    console.print(f"📄 [green]Análise salva em: {output_file}[/green]")

def main():
    """Função principal"""
    start_time = datetime.now()
    
    try:
        result = read_and_analyze_excel()
        
        if result:
            console.print("\n✅ [bold green]Análise concluída com sucesso![/bold green]")
        else:
            console.print("\n❌ [bold red]Falha na análise![/bold red]")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        console.print(f"⏱️ [yellow]Tempo total: {duration:.2f} segundos[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Erro geral: {e}[/red]")

if __name__ == "__main__":
    main()
