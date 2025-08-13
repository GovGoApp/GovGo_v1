import pandas as pd
from openpyxl import load_workbook
from rich.progress import track
from rich.console import Console

console = Console()

# Carregar a planilha Excel original
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\TESTE\\"
FILE = 'TESTE_2022_mini.xlsx'

# Carregar abas específicas em dataframes
df_resumo = pd.read_excel(PATH + FILE, sheet_name='RESUMO_2022')
df_itens = pd.read_excel(PATH + FILE, sheet_name='ITENS_2022')

# Definir campos necessários para serem adicionados ao resumo
campos = ['numeroItem', 'descricao', 'valorUnitarioEstimado', 'valorTotal', 'quantidade', 'unidadeMedida']

# Adicionar colunas somente se não existirem
for campo in campos:
    if campo not in df_resumo.columns:
        df_resumo[campo] = ''

# Preencher as informações no resumo
for idx, row in track(df_resumo.iterrows(), description="Processando itens", total=len(df_resumo)):
    num_pncp = row['numeroControlePNCP']
    # Filtrar itens correspondentes ao numeroControlePNCP
    itens_filtrados = df_itens[df_itens['numeroControlePNCP'] == num_pncp]

    # Ordenar por numeroItem
    itens_filtrados = itens_filtrados.sort_values(by='numeroItem')

    # Criar listas formatadas para cada coluna desejada
    for campo in campos:
        lista_valores = itens_filtrados[campo].astype(str).tolist()
        texto_formatado = '{' + ';'.join(lista_valores) + '}'
        df_resumo.at[idx, campo] = texto_formatado

# Carregar a planilha original para atualizar apenas a aba RESUMO_2022
workbook = load_workbook(PATH + FILE)

# Atualizar a aba RESUMO_2022
with pd.ExcelWriter(PATH + FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    df_resumo.to_excel(writer, sheet_name='RESUMO_2022', index=False)


console.print('[bold green]Planilha original atualizada com sucesso.[/bold green]')
