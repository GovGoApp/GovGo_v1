import requests
import pandas as pd
import os
import datetime
import calendar
import re
import gc
import concurrent.futures
import threading
from tqdm import tqdm

# Cria um lock para impressão thread-safe
print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

# Função para remover caracteres ilegais (intervalo \x00 a \x1F)
def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

# Limpa o DataFrame usando apply com map para cada coluna
def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

# Função para buscar dados de um período mensal com paginação
def fetch_month_data(data_inicial, data_final):
    base_url = "https://pncp.gov.br/api/consulta/v1/contratos"
    monthly_data = []
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "pagina": 1147, #1 default
        "tamanhoPagina": 100
    }
    safe_print(f"Iniciando a busca para o período {data_inicial} a {data_final} - Página 1")
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        safe_print(f"Erro na requisição: status code {response.status_code}")
        return monthly_data
    json_response = response.json()
    monthly_data.extend(json_response.get("data", []))
    total_paginas = json_response.get("totalPaginas", 1)
    safe_print(f"Página 1 de {total_paginas} concluída.")
    if total_paginas > 1:
        with tqdm(total=total_paginas - 1, desc="Progresso das páginas", ncols=100, leave=False) as pbar:
            for page in range(2, total_paginas + 1):
                params["pagina"] = page
                response = requests.get(base_url, params=params)
                if response.status_code != 200:
                    safe_print(f"Erro na requisição da página {page}: status code {response.status_code}")
                    break
                json_response = response.json()
                monthly_data.extend(json_response.get("data", []))
                pbar.update(1)
    return monthly_data

# Função para processar um único mês: buscar, salvar em arquivo e limpar memória
def process_month(year, month, path):
    data_inicio = datetime.date(year, month, 1)
    ultimo_dia = calendar.monthrange(year, month)[1]
    data_fim = datetime.date(year, month, ultimo_dia)
    
    data_inicial_str = data_inicio.strftime("%Y%m%d")
    data_final_str = data_fim.strftime("%Y%m%d")
    
    safe_print(f"\nProcessando mês: {year}-{month:02d} | Período: {data_inicial_str} a {data_final_str}")
    monthly_data = fetch_month_data(data_inicial_str, data_final_str)
    safe_print(f"Total de registros obtidos para {year}-{month:02d}: {len(monthly_data)}")
    
    if monthly_data:
        df = pd.json_normalize(monthly_data)
        df = clean_dataframe(df)
    else:
        df = pd.DataFrame()
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"contratos_pncp_{year}-{month:02d}_{timestamp}.xlsx"
    full_path = os.path.join(path, file_name)
    safe_print(f"Salvando planilha para {year}-{month:02d} em: {full_path}")
    
    with pd.ExcelWriter(full_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name=f"{year}-{month:02d}", index=False)
    
    safe_print(f"Planilha {file_name} salva com sucesso!")
    
    # Libera memória
    del df, monthly_data
    gc.collect()

def main():
    # Apenas os meses desejados
    meses = [(2025, 1)] # , (2025, 2)
    safe_print(f"Serão processados os meses: {meses}")
    
    # Caminho onde os arquivos serão salvos (diretório já existente)
    PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
    
    max_workers = 5  # Você pode ajustar conforme seus recursos; aqui usamos 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_month, year, month, PATH) for year, month in meses]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                safe_print(f"Erro no processamento: {e}")
    
    safe_print("Todos os meses foram processados com sucesso!")

if __name__ == "__main__":
    main()
