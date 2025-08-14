import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
import os
import time

# Configurações
CSV_PATH = 'pca_todos_anos.csv'
OUTPUT_PATH = 'pca_completo_detalhado.csv'
API_BASE = 'https://www.pncp.gov.br/api/pncp/v1/orgaos'
MAX_WORKERS = 20
HEADERS = {'accept': 'application/json'}

# Carrega o CSV
print('Lendo CSV...')
df = pd.read_csv(CSV_PATH, dtype=str)
df = df.drop_duplicates(subset=['cnpj', 'anoPca'])
orgaos_anos = df[['cnpj', 'anoPca']].drop_duplicates().to_dict('records')

# Função para buscar todos sequenciais de um órgão/ano
def get_sequenciais(cnpj, ano):
    url = f"{API_BASE}/{cnpj}/pca/{ano}/consolidado"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return [item['sequencialPca'] for item in data if 'sequencialPca' in item]
        else:
            return []
    except Exception:
        return []

# Função para buscar o PCA completo
def get_pca_completo(cnpj, ano, sequencial):
    url = f"{API_BASE}/{cnpj}/pca/{ano}/{sequencial}/consolidado"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception:
        return None

# Coleta todos os sequenciais
print('Buscando sequenciais de todos os órgãos/anos...')
sequenciais = []
with Progress(TextColumn("[bold blue]{task.description}", justify="right"), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%", TimeElapsedColumn(), TimeRemainingColumn()) as progress:
    task = progress.add_task("Órgãos/anos", total=len(orgaos_anos))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_org = {executor.submit(get_sequenciais, org['cnpj'], org['anoPca']): org for org in orgaos_anos}
        for future in as_completed(future_to_org):
            org = future_to_org[future]
            result = future.result()
            for seq in result:
                sequenciais.append((org['cnpj'], org['anoPca'], seq))
            progress.advance(task)

# Busca os PCAs completos
print(f'Buscando dados completos de {len(sequenciais)} PCAs...')
pca_completos = []
with Progress(TextColumn("[bold green]{task.description}", justify="right"), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%", TimeElapsedColumn(), TimeRemainingColumn()) as progress:
    task = progress.add_task("PCAs completos", total=len(sequenciais))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_pca = {executor.submit(get_pca_completo, cnpj, ano, seq): (cnpj, ano, seq) for cnpj, ano, seq in sequenciais}
        for future in as_completed(future_to_pca):
            data = future.result()
            if data:
                pca_completos.append(data)
            progress.advance(task)

# Salva tudo em CSV
if pca_completos:
    df_pca = pd.json_normalize(pca_completos)
    df_pca.to_csv(OUTPUT_PATH, index=False)
    print(f'Finalizado! Dados completos salvos em {OUTPUT_PATH}')
else:
    print('Nenhum dado completo de PCA foi obtido.')
