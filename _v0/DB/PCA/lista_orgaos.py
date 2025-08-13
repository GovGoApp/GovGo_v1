import requests
import pandas as pd

# Endpoint público para listar órgãos do PNCP
ep = "https://treina.pncp.gov.br/api/pncp/v1/orgaos"
resp = requests.get(ep)
resp.raise_for_status()
orgaos = resp.json()

# Extrai CNPJ, nome, esfera, poder, etc.
df = pd.DataFrame(orgaos)

# Salva em CSV
csv_path = "lista_orgaos.csv"
df.to_csv(csv_path, index=False, encoding="utf-8")

print(f"Salvo em {csv_path} com {len(df)} órgãos.")
