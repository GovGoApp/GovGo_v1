import requests
import pandas as pd
import time

# Carrega a lista de órgãos
orgaos = pd.read_csv("lista_orgaos.csv")

resultados = []

for cnpj in orgaos["cnpj"]:
    url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/pca/2025/consolidado"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            dados["cnpj"] = cnpj
            resultados.append(dados)
        else:
            print(f"CNPJ {cnpj}: {resp.status_code}")
    except Exception as e:
        print(f"Erro no CNPJ {cnpj}: {e}")
    time.sleep(0.1)  # Evita sobrecarga no servidor

# Salva resultados
pd.DataFrame(resultados).to_csv("pca_2025.csv", index=False, encoding="utf-8")
print(f"Salvo em pca_2025.csv com {len(resultados)} PCAs.")
