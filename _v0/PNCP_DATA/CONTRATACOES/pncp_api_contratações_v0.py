import pandas as pd
import requests
import re
from time import sleep

# Parâmetros de caminho e nomes de arquivo
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATAÇÕES\\"
IN_FILE = "CONTRATOS_MODELO_v2.xlsx"
OUT_FILE = "CONTRATOS_MODELO_v2_CONTRATAÇÕES.xlsx"

# Lê a planilha com os dados de contratos
df = pd.read_excel(PATH + IN_FILE)

# Nome da coluna que contém o número de controle do PNCP
contract_column = "numeroControlePncpCompra"

# Expressão regular para extrair CNPJ, sequencial e ano do número de controle
pattern = r"(?P<cnpj>\d{14})-\d+-(?P<seq>\d+)/(?P<ano>\d{4})"

def fetch_api_data(contract_str):
    match = re.match(pattern, contract_str)
    if match:
        cnpj = match.group("cnpj")
        seq = match.group("seq")
        ano = match.group("ano")
        # Converte o sequencial para inteiro para remover zeros à esquerda
        seq_int = int(seq)
        # Monta a URL do endpoint: /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}
        url = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq_int}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Erro ao acessar {url}: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Exception ao acessar {url}: {e}")
            return {}
    else:
        print(f"Formato inválido para contrato: {contract_str}")
        return {}

# Consulta a API para cada contrato e armazena os resultados
api_results = []
for idx, row in df.iterrows():
    contrato = row[contract_column]
    dados_api = fetch_api_data(contrato)
    api_results.append(dados_api)
    sleep(0.1)  # pausa breve para não sobrecarregar o servidor da API

# Achata os dados da API (incluindo os dicionários aninhados) em colunas
df_api = pd.json_normalize(api_results)

# Identifica e remove colunas redundantes (por exemplo, "numeroControlePNCP" já existe na planilha como "numeroControlePncpCompra")
existing_cols_lower = [c.lower() for c in df.columns]
redundant_cols = [col for col in df_api.columns if col.lower() in existing_cols_lower]
if redundant_cols:
    df_api.drop(columns=redundant_cols, inplace=True)

# Concatena os dados originais com os dados retornados pela API, sem duplicar colunas
df_atualizado = pd.concat([df, df_api], axis=1)

# Salva o DataFrame atualizado em um novo arquivo Excel
df_atualizado.to_excel(PATH + OUT_FILE, index=False)

print("Processamento concluído. Planilha atualizada salva em:", OUT_FILE)
