import requests
import pandas as pd
import os
import time
from datetime import datetime
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

def main():
    # Consulta dos anos de 2021 a 2025
    years = list(range(2023, 2025)) 
    
    # Adiciona timestamp ao nome do arquivo para evitar substituições acidentais
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Caminho para salvar o arquivo
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
    FILE = f"contratos_pncp_{timestamp}.xlsx"
    
    # Garantir que o diretório existe
    os.makedirs(PATH, exist_ok=True)
    
    # Criar o ExcelWriter para salvar todas as abas no mesmo arquivo
    with pd.ExcelWriter(PATH + FILE, engine='openpyxl') as writer:
        # Coletar e salvar dados para cada ano em uma aba separada
        for year in years:
            print(f"\n{'='*50}")
            print(f"Processando o ano {year}")
            print(f"{'='*50}")
            
            # Buscar dados do ano
            contracts = get_all_contracts_for_year(year)
            
            if not contracts:
                print(f"Nenhum contrato encontrado para o ano {year}")
                continue
                
            print(f"Total de {len(contracts)} contratos encontrados para {year}")
            
            # Normalizar dados e criar DataFrame
            print(f"Normalizando dados de {year}...")
            normalized_contracts = normalize_data(contracts)
            year_df = pd.DataFrame(normalized_contracts)
            
            # Salvar checkpoint do ano
            checkpoint_path = os.path.join("checkpoints", f"contratos_pncp_{year}.pkl")
            os.makedirs("checkpoints", exist_ok=True)
            year_df.to_pickle(checkpoint_path)
            print(f"Checkpoint salvo para o ano {year}")
            
            # Salvar na aba do ano no Excel
            sheet_name = f'Contratos_{year}'
            year_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Dados de {year} salvos na aba {sheet_name}")
    
    print(f"\nProcessamento concluído.")
    print(f"Arquivo Excel salvo em: {PATH + FILE}")

if __name__ == "__main__":
    main()