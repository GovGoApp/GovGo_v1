import os
import sqlite3
import pandas as pd
import json
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

console = Console()

# Definindo os caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"
OUTPUT_PATH = BASE_PATH + "CLASSY\\CLASSY_ITENS\\OUTPUT_ITENS\\OUTPUT\\"
PROCESSED_FILES_LOG = DB_PATH + "processed_files_log.json"

# Adicionar esta função para normalizar caminhos
def normalize_path(path):
    """Normaliza o caminho para evitar inconsistências entre diferentes formatos de caminho"""
    return os.path.normpath(path)

# Modificar a função load_processed_files para normalizar caminhos
def load_processed_files():
    """Carrega a lista de arquivos já processados"""
    if not os.path.exists(PROCESSED_FILES_LOG):
        return []
    
    try:
        with open(PROCESSED_FILES_LOG, 'r') as f:
            file_list = json.load(f)
            # Normalizar todos os caminhos
            return [normalize_path(path) for path in file_list]
    except Exception as e:
        console.log(f"[yellow]Aviso: Erro ao carregar registro de arquivos processados: {str(e)}[/yellow]")
        return []

# Modificar a função add_processed_file para normalizar caminhos
def add_processed_file(filepath):
    """Adiciona um arquivo à lista de processados"""
    processed_files = load_processed_files()
    
    # Normalizar o caminho antes de comparar
    normalized_path = normalize_path(filepath)
    
    if normalized_path not in processed_files:
        processed_files.append(normalized_path)
        
        try:
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(PROCESSED_FILES_LOG), exist_ok=True)
            
            with open(PROCESSED_FILES_LOG, 'w') as f:
                json.dump(processed_files, f, indent=2)
        except Exception as e:
            console.log(f"[red]Erro ao salvar registro de arquivos processados: {str(e)}[/red]")

# Modificar a função import_output_files para normalizar caminhos e adicionar verificação de dados existentes
def import_output_files():
    """Importar dados dos arquivos de saída para o banco de dados."""
    console.log(f"Importando dados dos arquivos em: {OUTPUT_PATH}")
    
    # Verificar arquivos já processados (caminhos já normalizados)
    processed_files = load_processed_files()
    console.log(f"Encontrados {len(processed_files)} arquivos já processados anteriormente.")
    
    conn = sqlite3.connect(DB_FILE)
    
    # Verificar se a tabela existe
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_classificacao'")
    if not cursor.fetchone():
        console.log("[bold red]Tabela 'item_classificacao' não existe. Execute primeiro o script de criação da tabela.[/bold red]")
        return
    
    # Obter lista de todos os arquivos de saída (normalizando os caminhos)
    output_files = []
    for file in os.listdir(OUTPUT_PATH):
        if file.endswith('.xlsx'):
            full_path = normalize_path(os.path.join(OUTPUT_PATH, file))
            if full_path not in processed_files:
                output_files.append(full_path)
    
    if not output_files:
        console.log("[bold green]Todos os arquivos já foram processados. Nada para fazer.[/bold green]")
        return
        
    console.log(f"Encontrados {len(output_files)} arquivos novos para processar.")
    
    # Processar cada arquivo com barra de progresso
    total_records = 0
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("Processando arquivos...", total=len(output_files))
        
        for file in output_files:
            try:
                df = pd.read_excel(file)
                file_name = os.path.basename(file)
                
                # Verificar colunas necessárias
                required_columns = [
                    'numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 
                    'item_type', 'TOP_1', 'TOP_2', 'TOP_3', 'TOP_4', 'TOP_5',
                    'SCORE_1', 'SCORE_2', 'SCORE_3', 'SCORE_4', 'SCORE_5', 'CONFIDENCE'
                ]
                
                # Verificar se todas as colunas necessárias estão no DataFrame
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    console.log(f"[yellow]Aviso: Colunas ausentes em {file_name}: {missing_cols}. Pulando arquivo.[/yellow]")
                    progress.update(task, advance=1)
                    continue
                
                # Selecionar apenas as colunas necessárias
                df_filtered = df[required_columns]
                
                # Preencher valores NaN apropriadamente
                df_filtered = df_filtered.fillna({
                    'numeroControlePNCP': '', 
                    'numeroItem': '', 
                    'ID_ITEM_CONTRATACAO': '', 
                    'descrição': '',
                    'item_type': '',
                    'TOP_1': '', 'TOP_2': '', 'TOP_3': '', 'TOP_4': '', 'TOP_5': '',
                    'SCORE_1': 0.0, 'SCORE_2': 0.0, 'SCORE_3': 0.0, 'SCORE_4': 0.0, 'SCORE_5': 0.0,
                    'CONFIDENCE': 0.0
                })
                
                # Verificar existência de registros duplicados
                total_processar = len(df_filtered)
                console.log(f"Arquivo {file_name}: Processando {total_processar} registros...")
                
                # Inserir dados no banco de dados - uso de uma única transação para melhor desempenho
                cursor = conn.cursor()
                registros_inseridos = 0
                
                # Iniciar transação
                conn.execute("BEGIN TRANSACTION")
                
                for _, row in df_filtered.iterrows():
                    try:
                        # Inserir novo registro
                        cursor.execute('''
                        INSERT INTO item_classificacao 
                        (numeroControlePNCP, numeroItem, ID_ITEM_CONTRATACAO, descrição, item_type,
                         TOP_1, TOP_2, TOP_3, TOP_4, TOP_5, 
                         SCORE_1, SCORE_2, SCORE_3, SCORE_4, SCORE_5, CONFIDENCE)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row['numeroControlePNCP'], row['numeroItem'], row['ID_ITEM_CONTRATACAO'], 
                            row['descrição'], row['item_type'],
                            row['TOP_1'], row['TOP_2'], row['TOP_3'], row['TOP_4'], row['TOP_5'],
                            row['SCORE_1'], row['SCORE_2'], row['SCORE_3'], row['SCORE_4'], row['SCORE_5'],
                            row['CONFIDENCE']
                        ))
                        registros_inseridos += 1
                    except Exception as e:
                        console.log(f"[yellow]Erro ao inserir registro: {str(e)}[/yellow]")
                
                # Finalizar transação
                conn.commit()
                
                total_records += registros_inseridos
                
                # Registrar arquivo como processado após sucesso
                add_processed_file(file)
                
                console.log(f"Processado {file_name}: {registros_inseridos} registros inseridos.")
                
            except Exception as e:
                console.log(f"[bold red]Erro ao processar {os.path.basename(file)}: {str(e)}[/bold red]")
                
            progress.update(task, advance=1)
    
    conn.close()
    console.log(f"[bold green]Importação concluída. Total de registros importados: {total_records}[/bold green]")

def create_table_if_not_exists():
    """Cria a tabela item_classificacao se não existir"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_classificacao (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        numeroControlePNCP TEXT,
        numeroItem TEXT,
        ID_ITEM_CONTRATACAO TEXT,
        descrição TEXT,
        item_type TEXT,
        TOP_1 TEXT,
        TOP_2 TEXT,
        TOP_3 TEXT,
        TOP_4 TEXT,
        TOP_5 TEXT,
        SCORE_1 REAL,
        SCORE_2 REAL,
        SCORE_3 REAL,
        SCORE_4 REAL,
        SCORE_5 REAL,
        CONFIDENCE REAL
    );
    """)
    
    conn.commit()
    conn.close()
    console.log("[green]Tabela 'item_classificacao' verificada/criada com sucesso![/green]")

if __name__ == "__main__":
    # Criar a tabela se não existir
    create_table_if_not_exists()
    
    # Importar os dados
    import_output_files()