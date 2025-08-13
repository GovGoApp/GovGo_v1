import pandas as pd
import os
import requests
import time

# Diretório dos arquivos CSV
TABELAS_DIR = os.path.dirname(os.path.abspath(__file__))

# Lista dos arquivos a juntar
anos = [2021, 2022, 2023, 2024, 2025]
arquivos = [os.path.join(TABELAS_DIR, f"pca_{ano}.csv") for ano in anos]

# Juntar todos os CSVs
dfs = []
for arq in arquivos:
    if os.path.exists(arq):
        try:
            df = pd.read_csv(arq, dtype=str)
            if not df.empty and len(df.columns) > 0:
                dfs.append(df)
            else:
                print(f"Arquivo ignorado (vazio ou sem colunas): {arq}")
        except Exception as e:
            print(f"Erro ao ler {arq}: {e}")

df_geral = pd.concat(dfs, ignore_index=True)
df_geral.to_csv(os.path.join(TABELAS_DIR, "pca_todos_anos.csv"), index=False, encoding="utf-8")
print(f"CSV único salvo como pca_todos_anos.csv com {len(df_geral)} linhas.")

# Puxar dados completos de cada PCA
# O endpoint é: https://pncp.gov.br/api/pncp/v1/pca/{id}
# Salvar resultados em pca_completo_todos_anos.jsonl

saida_jsonl = os.path.join(TABELAS_DIR, "pca_completo_todos_anos.jsonl")

with open(saida_jsonl, "w", encoding="utf-8") as fout:
    for idx, row in df_geral.iterrows():
        pca_id = row.get("id")
        if pd.isna(pca_id):
            continue
        url = f"https://pncp.gov.br/api/pncp/v1/pca/{pca_id}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                fout.write(resp.text.strip() + "\n")
            else:
                fout.write(f"{{\"id\": \"{pca_id}\", \"erro\": {resp.status_code}}}\n")
        except Exception as e:
            fout.write(f"{{\"id\": \"{pca_id}\", \"erro\": \"{str(e)}\"}}\n")
        if idx % 100 == 0:
            print(f"{idx} PCAs processados...")
        time.sleep(0.1)  # Pequeno delay para não sobrecarregar o endpoint

print(f"Dados completos salvos em {saida_jsonl}")
