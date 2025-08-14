import requests
import pandas as pd
import os
import datetime
import concurrent.futures
import re
import json
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn


# Lista de campos dos itens conforme o exemplo de itens.json (fixa)
ITEM_FIELDS = [
    "numeroItem",
    "descricao",
    "materialOuServico",
    "materialOuServicoNome",
    "valorUnitarioEstimado",
    "valorTotal",
    "quantidade",
    "unidadeMedida",
    "orcamentoSigiloso",
    "itemCategoriaId",
    "itemCategoriaNome",
    "patrimonio",
    "codigoRegistroImobiliario",
    "criterioJulgamentoId",
    "criterioJulgamentoNome",
    "situacaoCompraItem",
    "situacaoCompraItemNome",
    "tipoBeneficio",
    "tipoBeneficioNome",
    "incentivoProdutivoBasico",
    "dataInclusao",
    "dataAtualizacao",
    "temResultado",
    "imagem",
    "aplicabilidadeMargemPreferenciaNormal",
    "aplicabilidadeMargemPreferenciaAdicional",
    "percentualMargemPreferenciaNormal",
    "percentualMargemPreferenciaAdicional",
    "ncmNbsCodigo",
    "ncmNbsDescricao",
    "catalogo",
    "categoriaItemCatalogo",
    "catalogoCodigoItem",
    "informacaoComplementar"
]

# Função para remover caracteres ilegais
def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

# Função que processa uma contratação (linha do input)
def process_row(row):
    # Tenta extrair os campos necessários; converte para string e faz strip
    cnpj = str(row.get("orgaoEntidade.cnpj", "")).strip()
    anoCompra = str(row.get("anoCompra", "")).strip()
    sequencialCompra = str(row.get("sequencialCompra", "")).strip()
    numeroControlePNCP = str(row.get("numeroControlePNCP", "")).strip()
    # Se faltar algum dado essencial, registra um log e retorna uma lista vazia
    if not (cnpj and anoCompra and sequencialCompra):
        return []
    # Monta a URL para recuperar os itens
    url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/itens"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return []
        itens = response.json()  # espera-se que seja uma lista
        resultados = []
        for item in itens:
            registro = {
                "numeroControlePNCP": numeroControlePNCP,
                "orgaoEntidade.cnpj": cnpj,
                "anoCompra": anoCompra,
                "sequencialCompra": sequencialCompra
            }
            for campo in ITEM_FIELDS:
                registro[campo] = item.get(campo)
            resultados.append(registro)
        return resultados
    except Exception:
        return []

# Função que processa uma aba (sheet) do IN_FILE
def process_sheet(sheet_name, df, progress):
    # Remover linhas totalmente vazias
    df = df.dropna(how="all")
    progress.console.log(f"Sheet '{sheet_name}' lida com {len(df)} linhas.")
    
    resultados = []
    total_rows = len(df)
    # Cria uma task para processar as contratações desta aba (indentado e em amarelo)
    task_id = progress.add_task(f"[bold yellow]  {sheet_name} (contratações)", total=total_rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_index = {executor.submit(process_row, row): idx for idx, row in df.iterrows()}
        for future in concurrent.futures.as_completed(future_to_index):
            try:
                linhas = future.result()
                if linhas:
                    resultados.extend(linhas)
            except Exception:
                pass
            progress.update(task_id, advance=1)
    progress.remove_task(task_id)
    # Ordem de saída: 4 campos fixos + os ITEM_FIELDS
    colunas_saida = ["numeroControlePNCP", "orgaoEntidade.cnpj", "anoCompra", "sequencialCompra"] + ITEM_FIELDS
    if resultados:
        sheet_df = pd.DataFrame(resultados)
        sheet_df = clean_dataframe(sheet_df)
        sheet_df = sheet_df.reindex(columns=colunas_saida)
    else:
        sheet_df = pd.DataFrame(columns=colunas_saida)
    return sheet_df

def main():
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATAÇÕES\\"
    OUT_PATH = PATH + "ITENS\\"
    IN_FILE = "CONTRATAÇÕES_PNCP_2023.xlsx"
    OUT_FILE = "ITENS_CONTRATAÇÕES_PNCP_2023.xlsx"
    
    # Lê o arquivo Excel com todas as abas
    xls = pd.ExcelFile(PATH + IN_FILE)
    sheets = xls.sheet_names  # lista de abas
    
    resultados_sheets = {}  # dicionário para armazenar os DataFrames processados por aba
    
    # Cria uma instância global de Progress (Rich)
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        
    )
    
    with progress:
        # Task externa: Processamento das abas (batch de abas)
        outer_task = progress.add_task("[bold green]Batch de abas", total=len(sheets))
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_sheet = {}
            for sheet in sheets:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                future = executor.submit(process_sheet, sheet, df_sheet, progress)
                future_to_sheet[future] = sheet
            for future in concurrent.futures.as_completed(future_to_sheet):
                sheet = future_to_sheet[future]
                try:
                    resultados_sheets[sheet] = future.result()
                except Exception:
                    resultados_sheets[sheet] = pd.DataFrame()
                progress.update(outer_task, advance=1)
        progress.remove_task(outer_task)
    
    # As abas de saída serão na mesma ordem do IN_FILE
    ordered_sheets = sheets
    
    # Salva cada aba de resultados em um único arquivo Excel
    with pd.ExcelWriter(OUT_PATH + OUT_FILE, engine="openpyxl") as writer:
        for sheet in ordered_sheets:
            resultados_sheets[sheet].to_excel(writer, sheet_name=sheet, index=False)
    print("\nPlanilha de itens consolidada salva em:", OUT_FILE)

if __name__ == "__main__":
    main()
