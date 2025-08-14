import requests
import pandas as pd
import os
from datetime import datetime
import time
from tqdm import tqdm

def fetch_pncp_data(data_inicial, data_final, pagina=1, tamanho_pagina=100):
    """Função para buscar dados da API do PNCP"""
    url = "https://pncp.gov.br/api/consulta/v1/contratos"
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "pagina": pagina,
        "tamanhoPagina": tamanho_pagina
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None

def get_all_contracts_for_year(year):
    """Função para obter todos os contratos de um ano específico"""
    data_inicial = f"{year}0101"
    data_final = f"{year}1231"
    
    print(f"Buscando dados para o ano {year}...")
    first_page = fetch_pncp_data(data_inicial, data_final)
    
    if not first_page or first_page.get("empty", True):
        print(f"Nenhum dado encontrado para o ano {year}")
        return []
    
    total_paginas = first_page.get("totalPaginas", 0)
    total_registros = first_page.get("totalRegistros", 0)
    print(f"Total de {total_registros} registros em {total_paginas} páginas")
    
    all_data = first_page.get("data", [])
    
    if total_paginas > 1:
        for pagina in tqdm(range(2, total_paginas + 1), desc=f"Páginas do ano {year}"):
            response_data = fetch_pncp_data(data_inicial, data_final, pagina)
            if response_data and not response_data.get("empty", True):
                all_data.extend(response_data.get("data", []))
            time.sleep(0.5)
    
    return all_data

def normalize_data(contratos):
    """Função para normalizar os dados aninhados para formato plano"""
    normalized_data = []
    
    for contrato in contratos:
        flat_contrato = {}
        
        # Copia dos campos simples
        for key, value in contrato.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                flat_contrato[key] = value
        
        # Processa os campos aninhados
        nested_fields = ["tipoContrato", "orgaoEntidade", "categoriaProcesso",
                         "unidadeOrgao", "unidadeSubRogada", "orgaoSubRogado"]
        
        for field in nested_fields:
            if field in contrato and contrato[field]:
                for subkey, subvalue in contrato[field].items():
                    flat_contrato[f"{field}_{subkey}"] = subvalue
        
        normalized_data.append(flat_contrato)
    
    return normalized_data

def save_excel_in_batches(df, PATH, FILE, batch_size=1000):
    """Salva o DataFrame em batches em um arquivo Excel"""
    os.makedirs(os.path.dirname(PATH + FILE), exist_ok=True)
    
    # Cria um ExcelWriter
    with pd.ExcelWriter(PATH + FILE, engine='openpyxl') as writer:
        # Calcula o número de batches
        total_rows = len(df)
        num_batches = (total_rows + batch_size - 1) // batch_size
        
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]
            
            # Cria uma aba para cada batch
            sheet_name = f'Contratos_Pagina_{i+1}'
            batch_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Salvando {sheet_name}: linhas {start_idx+1} a {end_idx}")

def main():
    # Consulta dos anos de 2021 a 2025
    years = list(range(2021, 2026))
    
    all_contracts = []
    
    for year in years:
        contracts = get_all_contracts_for_year(year)
        all_contracts.extend(contracts)
        print(f"Total acumulado: {len(all_contracts)} contratos")
    
    if not all_contracts:
        print("Nenhum contrato encontrado")
        return
    
    print("Normalizando dados...")
    normalized_contracts = normalize_data(all_contracts)
    df = pd.DataFrame(normalized_contracts)
    
    # Caminho para salvar o arquivo
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
    FILE = "contratos_pncp.xlsx"
    
    # Salva o DataFrame em batches de 1000 linhas (10 páginas)
    save_excel_in_batches(df, PATH , FILE, batch_size=1000)
    
    print(f"Processamento concluído. Total de {len(df)} contratos exportados.")

if __name__ == "__main__":
    main()