import requests
import pandas as pd
import os
import datetime
import calendar
import re
from tqdm import tqdm

# Função para remover caracteres ilegais (intervalo \x00 a \x1F)
def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

# Aplica a limpeza em todas as células do DataFrame usando apply com map
def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

# Função para buscar dados de um período mensal com paginação
def fetch_month_data(data_inicial, data_final):
    base_url = "https://pncp.gov.br/api/consulta/v1/contratos"
    monthly_data = []
    
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "pagina": 1,
        "tamanhoPagina": 100
    }
    
    print(f"Iniciando a busca para o período {data_inicial} a {data_final} - Página 1")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"Erro na requisição: status code {response.status_code}")
        return monthly_data
    
    json_response = response.json()
    monthly_data.extend(json_response.get("data", []))
    total_paginas = json_response.get("totalPaginas", 1)
    print(f"Página 1 de {total_paginas} concluída.")
    
    if total_paginas > 1:
        with tqdm(total=total_paginas - 1, desc="Progresso das páginas", ncols=100, leave=False) as pbar:
            for page in range(2, total_paginas + 1):
                params["pagina"] = page
                response = requests.get(base_url, params=params)
                if response.status_code != 200:
                    print(f"Erro na requisição da página {page}: status code {response.status_code}")
                    break
                json_response = response.json()
                monthly_data.extend(json_response.get("data", []))
                pbar.update(1)
    return monthly_data

def main():
    # Caminho onde a planilha será salva (este diretório já existe)
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    FILE = f"contratos_pncp_{timestamp}.xlsx"
    full_path = os.path.join(PATH, FILE)
    
    print(f"\nO arquivo Excel será criado em: {full_path}")
    
    # Indicador para a primeira aba (criação do arquivo)
    first_sheet = True
    
    # Define o intervalo de anos
    ano_inicial = 2023
    ano_final = 2025
    
    # Loop pelos anos e meses
    for year in range(ano_inicial, ano_final + 1):
        for month in range(1, 13):
            data_inicio = datetime.date(year, month, 1)
            ultimo_dia = calendar.monthrange(year, month)[1]
            data_fim = datetime.date(year, month, ultimo_dia)
            
            data_inicial_str = data_inicio.strftime("%Y%m%d")
            data_final_str = data_fim.strftime("%Y%m%d")
            
            print(f"\nProcessando mês: {year}-{month:02d} | Período: {data_inicial_str} a {data_final_str}")
            monthly_data = fetch_month_data(data_inicial_str, data_final_str)
            print(f"Total de registros obtidos para {year}-{month:02d}: {len(monthly_data)}")
            
            if monthly_data:
                df = pd.json_normalize(monthly_data)
                df = clean_dataframe(df)
            else:
                df = pd.DataFrame()  # DataFrame vazio
            
            sheet_name = f"{year}-{month:02d}"
            print(f"Salvando aba: {sheet_name} com {len(df)} registros")
            
            if first_sheet:
                # Cria o arquivo pela primeira vez (modo 'w' sem if_sheet_exists)
                with pd.ExcelWriter(full_path, engine="openpyxl", mode="w") as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                first_sheet = False
            else:
                # Acrescenta nova aba no arquivo existente (modo 'a' com if_sheet_exists="new")
                with pd.ExcelWriter(full_path, engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"Aba {sheet_name} salva na planilha.")
    
    print("\nProcesso concluído com sucesso!")
    print(f"Planilha final salva em: {full_path}")

if __name__ == "__main__":
    main()
