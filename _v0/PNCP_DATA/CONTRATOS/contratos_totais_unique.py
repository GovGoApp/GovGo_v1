import os
import pandas as pd
from tqdm import tqdm

# Parâmetros e caminhos
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_FILTRADOS_DADOS.xlsx"   # Arquivo que possui as abas 'CONTRATOS_1' e 'CONTRATOS_2'
FILE_OUT = "CONTRATOS_PNCP_FILTRADOS_UNIQUE_ANUAL.xlsx"         # Arquivo de saída com uma aba por ano

file_in_path = os.path.join(PATH, FILE_IN)
file_out_path = os.path.join(PATH, FILE_OUT)

# Lista das abas a serem lidas
sheets_to_load = ["CONTRATOS_1", "CONTRATOS_2"]

# Carrega as abas e concatena
df_list = []
print("Carregando abas:")
for sheet in tqdm(sheets_to_load, desc="Lendo abas", ncols=80):
    df = pd.read_excel(file_in_path, sheet_name=sheet)
    df_list.append(df)

print("Concatenando abas...")
df_all = pd.concat(df_list, ignore_index=True)
print(f"Total de linhas concatenadas: {len(df_all)}")

# Remove duplicatas (linhas inteiras idênticas)
print("Removendo duplicatas...")
df_unique = df_all.drop_duplicates()
print(f"Total de linhas após remoção de duplicatas: {len(df_unique)}")

# Cria uma nova coluna 'vigenciaAno' a partir de 'dataVigenciaInicio'
print("Extraindo o ano da coluna 'dataVigenciaInicio'...")
df_unique["vigenciaAno"] = pd.to_datetime(df_unique["dataVigenciaInicio"], errors="coerce").dt.year

# Verifica os anos encontrados e ordena
unique_years = sorted(df_unique["vigenciaAno"].dropna().unique())
print(f"Anos encontrados: {unique_years}")

# Salva os contratos separados por ano em abas diferentes
print(f"Salvando o arquivo com abas separadas por ano em: {file_out_path}")
with pd.ExcelWriter(file_out_path, engine="openpyxl") as writer:
    for year in tqdm(unique_years, desc="Salvando abas", ncols=80):
        # Seleciona os contratos cujo ano de vigência é o atual
        df_year = df_unique[df_unique["vigenciaAno"] == year]
        sheet_name = str(int(year))
        print(f" - Salvando {len(df_year)} linhas para o ano {year} na aba '{sheet_name}'")
        df_year.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Arquivo salvo com sucesso em: {file_out_path}")
