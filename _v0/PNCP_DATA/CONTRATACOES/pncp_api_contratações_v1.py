import requests
import pandas as pd
import os
import datetime
import calendar
import re
import gc
import concurrent.futures

# Função para remover caracteres ilegais (intervalo \x00 a \x1F)
def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

# Função para limpar o DataFrame aplicando a remoção de caracteres ilegais
def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

# Função para buscar os dados de um código específico (codigoModalidadeContratacao)
# para um determinado período, utilizando paginação.
def fetch_by_code(data_inicial, data_final, codigo):
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50
    }
    print(f"[Código {codigo}] Iniciando busca para o período {data_inicial} a {data_final} - Página 1")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"[Código {codigo}] Erro na requisição da página 1: status code {response.status_code}")
        return all_data
    json_response = response.json()
    all_data.extend(json_response.get("data", []))
    total_paginas = json_response.get("totalPaginas", 1)
    if total_paginas > 1:
        for page in range(2, total_paginas + 1):
            params["pagina"] = page
            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                print(f"[Código {codigo}] Erro na requisição da página {page}: status code {response.status_code}")
                break
            json_response = response.json()
            all_data.extend(json_response.get("data", []))
    print(f"[Código {codigo}] Finalizado: {len(all_data)} registros obtidos.")
    return all_data

# Função para processar um mês: para o período do mês, lança threads para cada código (1 a 14),
# junta os dados e retorna um DataFrame limpo.
def process_month(year, month):
    data_inicio = datetime.date(year, month, 1)
    ultimo_dia = calendar.monthrange(year, month)[1]
    data_fim = datetime.date(year, month, ultimo_dia)
    
    data_inicial_str = data_inicio.strftime("%Y%m%d")
    data_final_str = data_fim.strftime("%Y%m%d")
    
    print(f"\n[Processando {year}-{month:02d}] Período: {data_inicial_str} a {data_final_str}")
    all_month_data = []
    
    # Lançar threads para cada código de modalidade (1 a 14)
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        future_to_codigo = {executor.submit(fetch_by_code, data_inicial_str, data_final_str, codigo): codigo for codigo in range(1, 15)}
        for future in concurrent.futures.as_completed(future_to_codigo):
            codigo = future_to_codigo[future]
            try:
                code_data = future.result()
                print(f"[{year}-{month:02d}] Código {codigo}: {len(code_data)} registros")
                all_month_data.extend(code_data)
            except Exception as e:
                print(f"[{year}-{month:02d}] Erro no código {codigo}: {e}")
    
    print(f"[{year}-{month:02d}] Total de registros: {len(all_month_data)}")
    if all_month_data:
        df = pd.json_normalize(all_month_data)
        df = clean_dataframe(df)
    else:
        df = pd.DataFrame()
    return df

# Função principal: processa os meses (para teste, apenas o ano de 2021) e salva os dados em abas mensais em uma única planilha.
def main():
    # Para teste, processaremos somente o ano de 2021
    start_year = 2021
    start_month = 1
    end_year = 2021
    end_month = 12
    
    # Caminho onde o arquivo Excel será salvo
    PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\CONTRATAÇÕES"
    
    # Gera a lista de meses a serem processados (no formato (ano, mês))
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
    
    monthly_dfs = {}  # dicionário para armazenar os DataFrames de cada mês, com chave "YYYY-MM"
    
    # Processa os meses de forma concorrente
    max_workers = 5  # ajustar conforme necessário
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_month = {executor.submit(process_month, year, month): (year, month) for year, month in meses}
        for future in concurrent.futures.as_completed(future_to_month):
            year, month = future_to_month[future]
            try:
                df = future.result()
                sheet_name = f"{year}-{month:02d}"
                monthly_dfs[sheet_name] = df
                print(f"[{sheet_name}] Processado com {len(df)} registros.")
            except Exception as e:
                print(f"Erro ao processar {year}-{month:02d}: {e}")
    
    # Cria um arquivo Excel com uma aba para cada mês
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(PATH, f"contratacoes_pncp_2021_{timestamp}.xlsx")
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for sheet, df in monthly_dfs.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"\nPlanilha consolidada salva em: {output_file}")

if __name__ == "__main__":
    main()
