import requests
import pandas as pd
import os
import datetime
import calendar
import re
import gc
import concurrent.futures
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# Lista com a ordem esperada das colunas (baseada no exemplo da API)
expected_columns = [
    "modoDisputaId",
    "amparoLegal.codigo",
    "amparoLegal.descricao",
    "amparoLegal.nome",
    "dataAberturaProposta",
    "dataEncerramentoProposta",
    "srp",
    "orgaoEntidade.cnpj",
    "orgaoEntidade.razaoSocial",
    "orgaoEntidade.poderId",
    "orgaoEntidade.esferaId",
    "anoCompra",
    "sequencialCompra",
    "informacaoComplementar",
    "processo",
    "objetoCompra",
    "linkSistemaOrigem",
    "justificativaPresencial",
    "unidadeSubRogada",
    "orgaoSubRogado",
    "valorTotalHomologado",
    "dataInclusao",
    "dataPublicacaoPncp",
    "dataAtualizacao",
    "numeroCompra",
    "unidadeOrgao.ufNome",
    "unidadeOrgao.ufSigla",
    "unidadeOrgao.municipioNome",
    "unidadeOrgao.codigoUnidade",
    "unidadeOrgao.nomeUnidade",
    "unidadeOrgao.codigoIbge",
    "modalidadeId",
    "linkProcessoEletronico",
    "dataAtualizacaoGlobal",
    "numeroControlePNCP",
    "tipoInstrumentoConvocatorioNome",
    "tipoInstrumentoConvocatorioCodigo",
    "valorTotalEstimado",
    "modalidadeNome",
    "modoDisputaNome",
    "situacaoCompraId",
    "situacaoCompraNome",
    "usuarioNome"
]

def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

def fetch_by_code(data_inicial, data_final, codigo, progress):
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50
    }
    # Primeira requisição (página 1)
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return all_data
    json_response = response.json()
    all_data.extend(json_response.get("data", []))
    total_paginas = json_response.get("totalPaginas", 1)
    if total_paginas > 1:
        # Usa o prefixo do mês para garantir que a task seja única, por exemplo "202301"
        month_str = data_inicial[:6]
        task_id = progress.add_task(f"        {month_str} - Código {codigo}", total=total_paginas - 1)
        for page in range(2, total_paginas + 1):
            params["pagina"] = page
            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                break
            json_response = response.json()
            all_data.extend(json_response.get("data", []))
            progress.update(task_id, advance=1)
        progress.remove_task(task_id)
    return all_data

def process_month(year, month, progress):
    # Define o período do mês
    data_inicio = datetime.date(year, month, 1)
    ultimo_dia = calendar.monthrange(year, month)[1]
    data_fim = datetime.date(year, month, ultimo_dia)
    data_inicial_str = data_inicio.strftime("%Y%m%d")
    data_final_str = data_fim.strftime("%Y%m%d")
    
    all_month_data = []
    # Cria task para o mês (indentação de 4 espaços, texto em amarelo)
    month_task_id = progress.add_task(f"[bold yellow]    {year}-{month:02d} (códigos)", total=14)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        futures = {
            executor.submit(fetch_by_code, data_inicial_str, data_final_str, codigo, progress): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                code_data = future.result()
                all_month_data.extend(code_data)
            except Exception:
                pass
            progress.update(month_task_id, advance=1)
    
    progress.remove_task(month_task_id)
    
    if all_month_data:
        df = pd.json_normalize(all_month_data)
        df = clean_dataframe(df)
        # Ordena os dados por "modalidadeId" e "numeroControlePNCP"
        df.sort_values(by=["modalidadeId", "numeroControlePNCP"], inplace=True)
        df = df.reindex(columns=expected_columns)
    else:
        df = pd.DataFrame(columns=expected_columns)
    return df

def main():
    # Para teste, processa o ano de 2023 (ajuste conforme necessário)
    start_year = 2025
    start_month = 3
    end_year = 2025
    end_month = 5
    
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\DB\\CONTRATAÇÕES"
    OUT_FILE = f"CONTRATAÇÕES_PNCP_{start_year}_{start_month}.xlsx"
    
    # Gera a lista de meses a serem processados
    meses = []
    current_year = start_year
    current_month = start_month
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        meses.append((current_year, current_month))
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1
    
    monthly_dfs = {}
    
    # Cria uma instância global de Progress customizada com Rich
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),

    )
    
    with progress:
        # Task externa: Batch de meses (sem indentação, texto branco)
        outer_task_id = progress.add_task("[bold white]Batch de meses", total=len(meses))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_month = {
                executor.submit(process_month, year, month, progress): (year, month) 
                for year, month in meses
            }
            for future in concurrent.futures.as_completed(future_to_month):
                year, month = future_to_month[future]
                try:
                    df = future.result()
                    sheet_name = f"{year}-{month:02d}"
                    monthly_dfs[sheet_name] = df
                except Exception:
                    pass
                progress.update(outer_task_id, advance=1)
        
        progress.remove_task(outer_task_id)
    
    ordered_sheets = sorted(monthly_dfs.keys())
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(PATH, OUT_FILE)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for sheet in ordered_sheets:
            monthly_dfs[sheet].to_excel(writer, sheet_name=sheet, index=False)
    print("\nPlanilha consolidada salva em:", output_file)

if __name__ == "__main__":
    main()
