import pandas as pd
import numpy as np
import os
import random
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Configurações
console = Console()
SAMPLE_SIZE = 5  # Número N de casos a selecionar de cada célula da tabela
PAGE_BEGIN = 176
PAGE_END = 176
SEED = 42  # Para reprodutibilidade

# Paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CLASSY_PATH = BASE_PATH + "CLASSY\\"
ITENS_PATH = CLASSY_PATH + "CLASSY_ITENS\\"
OUTPUT_ITENS_PATH = ITENS_PATH + "OUTPUT_ITENS\\"
SAMPLES_PATH = OUTPUT_ITENS_PATH + "SAMPLES\\"

# Garantir que a pasta de amostras existe
os.makedirs(SAMPLES_PATH, exist_ok=True)

def read_output_file():
    """Lê o arquivo OUTPUT correspondente ao PAGE_BEGIN especificado"""
    input_num_str = f"{PAGE_BEGIN:03d}"
    output_file = OUTPUT_ITENS_PATH + f"OUTPUT_ITEM_{input_num_str}.xlsx"
    
    console.print(f"[bold blue]Lendo arquivo: {output_file}[/bold blue]")
    
    if not os.path.exists(output_file):
        console.print(f"[bold red]Arquivo não encontrado: {output_file}[/bold red]")
        return None
    
    try:
        df = pd.read_excel(output_file)
        console.print(f"[bold green]Arquivo lido com sucesso: {len(df)} linhas[/bold green]")
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao ler arquivo: {str(e)}[/bold red]")
        return None

def categorize_by_score_confidence(df):
    """Categoriza os itens de acordo com faixas de SCORE_1 e CONFIDENCE"""
    
    # Definir as faixas - corrigido para o problema do número de labels
    score_bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    score_labels = ['0.0', '0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9']
    
    confidence_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    confidence_labels = ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90']
    
    # Adicionar as categorias ao DataFrame
    df['SCORE_CAT'] = pd.cut(df['SCORE_1'], bins=score_bins, labels=score_labels, right=False)
    df['CONFIDENCE_CAT'] = pd.cut(df['CONFIDENCE'], bins=confidence_bins, labels=confidence_labels, right=False)
    
    return df

def sample_from_each_cell(df, sample_size=SAMPLE_SIZE):
    """Seleciona N amostras aleatórias de cada célula da tabela SCORE_1 vs CONFIDENCE"""
    
    # Para reprodutibilidade
    random.seed(SEED)
    np.random.seed(SEED)
    
    # Criar uma lista para armazenar todas as amostras
    samples = []
    
    # Faixas específicas solicitadas
    score_cats = ['0.4', '0.5', '0.6', '0.7', '0.8', '0.9']  # Score entre 0.4 e 0.9
    conf_cats = ['10', '20', '30', '40', '50', '60', '70', '80', '90']  # Confidence de 10 a 90
    
    # Criar uma tabela de contagem para log (apenas com as categorias desejadas)
    count_matrix = pd.DataFrame(index=score_cats, columns=conf_cats)
    count_matrix = count_matrix.fillna(0).astype(int)
    
    sample_matrix = pd.DataFrame(index=score_cats, columns=conf_cats)
    sample_matrix = sample_matrix.fillna(0).astype(int)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        
        task = progress.add_task("[cyan]Amostrando cada célula da tabela...", total=len(score_cats)*len(conf_cats))
        
        # Iterar apenas pelas combinações solicitadas
        for score_cat in score_cats:
            for conf_cat in conf_cats:
                
                # Filtrar o DataFrame para essa célula específica
                cell_df = df[(df['SCORE_CAT'] == score_cat) & (df['CONFIDENCE_CAT'] == conf_cat)]
                
                # Contar e registrar o número de itens nessa célula
                cell_count = len(cell_df)
                count_matrix.at[score_cat, conf_cat] = cell_count
                
                # Selecionar amostras aleatórias (ou todas, se houver menos que N)
                if cell_count > 0:
                    if cell_count <= sample_size:
                        cell_samples = cell_df
                    else:
                        cell_samples = cell_df.sample(sample_size)
                    
                    samples.append(cell_samples)
                    sample_matrix.at[score_cat, conf_cat] = len(cell_samples)
                
                progress.update(task, advance=1, description=f"Processando SCORE={score_cat}, CONF={conf_cat}: {cell_count} itens")
    
    # Verificar se temos alguma amostra
    if not samples:
        console.print("[bold red]Nenhuma amostra selecionada![/bold red]")
        return None, count_matrix, sample_matrix
    
    # Combinar todas as amostras em um único DataFrame
    sampled_df = pd.concat(samples, ignore_index=True)
    
    return sampled_df, count_matrix, sample_matrix

def main():
    console.print("[bold magenta]Iniciando amostragem estratificada por SCORE_1 e CONFIDENCE...[/bold magenta]")
    
    # Ler o arquivo OUTPUT
    df = read_output_file()
    if df is None:
        return
    
    # Verificar se as colunas necessárias existem
    required_cols = ['numeroControlePNCP', 'numeroItem', 'ID_ITEM_CONTRATACAO', 'descrição', 
                    'item_type', 'TOP_1', 'TOP_2', 'TOP_3', 'TOP_4', 'TOP_5',
                    'SCORE_1', 'SCORE_2', 'SCORE_3', 'SCORE_4', 'SCORE_5', 'CONFIDENCE']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        console.print(f"[bold red]Colunas ausentes: {missing_cols}[/bold red]")
        return
    
    # Categorizar por faixas de SCORE_1 e CONFIDENCE
    df = categorize_by_score_confidence(df)
    
    # Realizar amostragem estratificada
    sampled_df, count_matrix, sample_matrix = sample_from_each_cell(df, SAMPLE_SIZE)
    
    if sampled_df is None:
        return
    
    # Mostrar estatísticas
    console.print("[bold yellow]Contagem de itens em cada célula da tabela:[/bold yellow]")
    console.print(count_matrix)
    
    console.print("[bold yellow]Número de amostras coletadas de cada célula:[/bold yellow]")
    console.print(sample_matrix)
    
    console.print(f"[bold green]Total de amostras coletadas: {len(sampled_df)}[/bold green]")
    
    # Salvar o resultado
    output_file = SAMPLES_PATH + f"SAMPLE_STRAT_N{SAMPLE_SIZE}_P{PAGE_BEGIN}.xlsx"
    sampled_df.to_excel(output_file, index=False)
    
    # Salvar também as matrizes de contagem para referência
    count_file = SAMPLES_PATH + f"COUNT_MATRIX_P{PAGE_BEGIN}.xlsx"
    count_matrix.to_excel(count_file)
    
    console.print(f"[bold green]Amostras salvas em: {output_file}[/bold green]")
    console.print(f"[bold green]Matriz de contagem salva em: {count_file}[/bold green]")

if __name__ == "__main__":
    main()