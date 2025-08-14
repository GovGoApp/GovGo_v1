import json
from openai import OpenAI
import pandas as pd
import os
import time
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from rich.console import Console
from datetime import datetime

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")
ft_model = "ft:gpt-4o-mini-2024-07-18:hiperhyped:cat-nv1:BIHDGpKQ"

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
REPORTS_PATH = BASE_PATH + "REPORTS\\"
REPORT_FILE = REPORTS_PATH + "CONTRATACAO_ID_ITENS_TESTE.xlsx"
SHEET = "CONTRATAÇÕES"
OUTPUT_FILE = REPORTS_PATH + f"CONTRATACAO_CLASSIFICADA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

# Mensagem do sistema (a mesma utilizada no fine-tuning)
system_message = """
Classifique o ITEM na CATEGORIA apropriada. 
Responda no formato: MATERIAL/SERVIÇO; Grupo CATMAT/CATSER.
"""

# --- 1. Carregar a planilha e selecionar 200 linhas ---
console.print("[bold magenta]Carregando a planilha de compras governamentais...[/bold magenta]")
df = pd.read_excel(REPORT_FILE, sheet_name=SHEET)

if "objetoCompra" not in df.columns:
    console.print("[bold red]A coluna 'objetoCompra' não foi encontrada na planilha.[/bold red]")
    raise ValueError("Coluna 'objetoCompra' inexistente.")

# Selecionar as 200 primeiras linhas para teste
df_test = df.head(200).copy()

# --- 2. Função para processar cada linha de forma síncrona ---
def process_line(objeto):
    user_message = "Classifique este item: " + objeto
    response = client.chat.completions.create(
        model=ft_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        max_tokens=100  # ajuste conforme o tamanho esperado da resposta
    )
    answer = response.choices[0].message.content.strip()
    return answer

# --- 3. Processar as 200 linhas e coletar os resultados ---
start_time = time.time()

# Preparar a coluna de resultados
df_test['Classificação'] = None

# Configurar barra de progresso rica
with Progress(
    SpinnerColumn(),
    TextColumn("[bold cyan]{task.description}"),
    BarColumn(bar_width=50),
    TaskProgressColumn(),
    TextColumn("[bold yellow]{task.fields[status]}"),
    TimeElapsedColumn()
) as progress:
    
    # Criar a tarefa principal
    task = progress.add_task("[cyan]Processando itens...", total=len(df_test), status="Iniciando...")
    
    # Processar cada linha
    for idx, row in df_test.iterrows():
        objeto = row["objetoCompra"]
        if pd.isna(objeto) or not objeto:
            df_test.at[idx, 'Classificação'] = "Sem descrição"
        else:
            try:
                # Atualizar status na barra de progresso
                progress.update(task, status=f"Item {idx+1}/{len(df_test)}")
                
                # Processar o item
                classification = process_line(str(objeto))
                
                # Armazenar o resultado diretamente no DataFrame
                df_test.at[idx, 'Classificação'] = classification
                
            except Exception as e:
                df_test.at[idx, 'Classificação'] = f"Erro: {str(e)}"
        
        # Avançar a barra de progresso
        progress.update(task, advance=1)

# Calcular tempo total
end_time = time.time()
total_time = end_time - start_time
avg_time = total_time / len(df_test)

# Reordenar as colunas para colocar a classificação logo após a descrição
cols = list(df_test.columns)
obj_index = cols.index("objetoCompra")
class_index = cols.index("Classificação")
cols.insert(obj_index + 1, cols.pop(class_index))
df_test = df_test[cols]

# Salvar o resultado em Excel
df_test.to_excel(OUTPUT_FILE, index=False)

# Mostrar estatísticas de tempo
console.print(f"\n[green]Processamento concluído![/green]")
console.print(f"[yellow]Tempo total: {total_time:.2f} segundos")