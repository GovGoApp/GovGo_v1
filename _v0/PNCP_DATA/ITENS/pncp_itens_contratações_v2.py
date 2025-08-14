import requests
import pandas as pd
import os
import datetime
import concurrent.futures
import re
import json
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# Lista de campos dos itens conforme o exemplo do arquivo itens.json
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

# Processa uma linha (contratação) usando apenas o campo numeroControlePNCP.
def process_row(row):
    numeroControle = str(row.get("numeroControlePNCP", "")).strip()
    if not numeroControle:
        return []
    try:
        # Formato esperado: "00394452000103-1-000675/2021"
        parts = numeroControle.split("-")
        if len(parts) != 3:
            return []
        cnpj = parts[0]
        # Ignora o prefixo (parts[1])
        seq_and_year = parts[2].split("/")
        if len(seq_and_year) != 2:
            return []
        seq = seq_and_year[0]
        anoCompra = seq_and_year[1]
        # Remove zeros à esquerda do sequencial
        sequencialCompra = str(int(seq))
        # Monta a URL:
        url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/itens"
        response = requests.get(url)
        if response.status_code != 200:
            return []
        itens = response.json()  # Espera-se que seja uma lista
        resultados = []
        for item in itens:
            registro = {"numeroControlePNCP": numeroControle}
            for campo in ITEM_FIELDS:
                registro[campo] = item.get(campo)
            resultados.append(registro)
        return resultados
    except Exception:
        return []

# Processa uma aba (sheet) do IN_FILE.
def process_sheet(sheet_name, df, progress):
    # Remove linhas totalmente vazias
    df = df.dropna(how="all")
    progress.console.log(f"Sheet '{sheet_name}' lida com {len(df)} linhas.")
    
    resultados = []
    total_rows = len(df)
    # Cria uma task para processar as contratações desta aba (indentado, em amarelo)
    task_id = progress.add_task(f"[bold yellow]  {sheet_name}", total=total_rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
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
    
    # Define a ordem de saída: a primeira coluna é numeroControlePNCP, depois os campos dos itens conforme ITEM_FIELDS
    colunas_saida = ["numeroControlePNCP"] + ITEM_FIELDS
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
    IN_FILE = "CONTRATAÇÕES_PNCP_2025.xlsx"
    OUT_FILE = "ITENS_CONTRATAÇÕES_PNCP_2025.xlsx"
    
    # Lê o arquivo Excel com todas as abas
    xls = pd.ExcelFile(PATH + IN_FILE)
    sheets = xls.sheet_names  # lista de abas
    
    resultados_sheets = {}
    
    # Cria uma instância global de Progress (Rich) com colunas customizadas (incluindo tempo e taxa, se disponível)
    progress = Progress(
        TextColumn("[bold yellow]{task.description}"),
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
    
    # Preserva a ordem das abas conforme no IN_FILE
    ordered_sheets = sheets
    
    # Salva os resultados em OUT_FILE (cada aba com o mesmo nome do IN_FILE)
    with pd.ExcelWriter(OUT_PATH + OUT_FILE, engine="openpyxl") as writer:
        for sheet in ordered_sheets:
            resultados_sheets[sheet].to_excel(writer, sheet_name=sheet, index=False)
    print("\nPlanilha de itens consolidada salva em:", OUT_FILE)

if __name__ == "__main__":
    main()
