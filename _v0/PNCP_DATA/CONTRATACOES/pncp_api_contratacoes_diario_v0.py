import requests
import pandas as pd
import os
import datetime
import re
import concurrent.futures
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

today = datetime.date.today()
data_str = today.strftime("%Y%m%d")
#data_str = '20250522'

# Diretório de saída
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\DB\\CONTRATAÇÕES\\NEW\\"
# Nome do arquivo com a data de hoje
OUT_FILE = f"CONTRATAÇÕES_PNCP_{data_str}.xlsx"

# Lista com a ordem esperada das colunas
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

def fetch_by_code(data_str, codigo, progress):
    """Busca dados para um único dia e código de modalidade específico"""
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    params = {
        "dataInicial": data_str,
        "dataFinal": data_str,  # Mesmo dia para início e fim
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
        task_id = progress.add_task(f"        Código {codigo}", total=total_paginas - 1)
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

def process_today(progress, data_str):
    """Processa os dados apenas para o dia atual"""
    
    all_data = []
    day_task_id = progress.add_task(f"[bold yellow]    Processando {data_str} (códigos)", total=14)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        futures = {
            executor.submit(fetch_by_code, data_str, codigo, progress): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                code_data = future.result()
                all_data.extend(code_data)
            except Exception as e:
                print(f"Erro ao processar código: {e}")
            progress.update(day_task_id, advance=1)
    
    progress.remove_task(day_task_id)
    
    if all_data:
        df = pd.json_normalize(all_data)
        df = clean_dataframe(df)
        # Ordena os dados por "modalidadeId" e "numeroControlePNCP"
        df.sort_values(by=["modalidadeId", "numeroControlePNCP"], inplace=True)
        df = df.reindex(columns=expected_columns)
    else:
        df = pd.DataFrame(columns=expected_columns)
    return df

def main():

    
    # Cria uma instância global de Progress customizada com Rich
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )
    
    with progress:
        # Task principal
        main_task_id = progress.add_task("[bold white]Download de contratações do dia", total=1)
        
        # Processa o dia de hoje
        try:
            df = process_today(progress, data_str)
            progress.update(main_task_id, advance=1)
        except Exception as e:
            print(f"Erro ao processar dados: {e}")
            return
    
    # Salva o resultado
    output_file = PATH + OUT_FILE
    df.to_excel(output_file, sheet_name=data_str, index=False)
    print(f"\nDados do dia {data_str} salvos em:", output_file)

if __name__ == "__main__":
    main()