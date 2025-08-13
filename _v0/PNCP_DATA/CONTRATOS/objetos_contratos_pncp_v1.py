import pandas as pd
import os
from tqdm import tqdm

# Parâmetros e caminhos
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_FILTRADOS_UNIQUE_ANUAL.xlsx"  # Arquivo de entrada
FILE_OUT = "OBJETOS_CONTRATOS_PNCP_TOTAL.xlsx"          # Arquivo de saída

# Monta os caminhos completos
file_in_path = os.path.join(PATH, FILE_IN)
file_out_path = os.path.join(PATH, FILE_OUT)

print("Iniciando a leitura do arquivo Excel:", file_in_path)
xls = pd.ExcelFile(file_in_path)
df_final = None

print("Processando cada aba (ano) com tqdm:")
for sheet in tqdm(xls.sheet_names, desc="Anos"):
    print("Processando ano:", sheet)
    # Lê as colunas necessárias para a agregação, sem unidadeOrgao.ufSigla
    df_sheet = pd.read_excel(
        xls, 
        sheet_name=sheet, 
        usecols=[
            "objetoContrato", 
            "tipoContrato.id", 
            "tipoContrato.nome", 
            "categoriaProcesso.id", 
            "categoriaProcesso.nome", 
            "valorGlobal"
        ]
    )
    
    # Agrupa os dados pelos campos indicados e calcula:
    # - número de contratos (contando as linhas)
    # - soma de valorGlobal
    df_group = df_sheet.groupby(
        ["objetoContrato", "tipoContrato.id", "tipoContrato.nome", "categoriaProcesso.id", "categoriaProcesso.nome"],
        as_index=False
    ).agg(
        numero_contratos=("objetoContrato", "count"),
        soma_valorGlobal=("valorGlobal", "sum")
    )
    
    # Renomeia as colunas agregadas para incluir o ano (nome da aba)
    df_group = df_group.rename(columns={
        "numero_contratos": f"numero_contratos_{sheet}",
        "soma_valorGlobal": f"soma_valorGlobal_{sheet}"
    })
    
    # Faz o merge com o dataframe final (merge outer)
    if df_final is None:
        df_final = df_group
    else:
        df_final = pd.merge(
            df_final, df_group, 
            on=["objetoContrato", "tipoContrato.id", "tipoContrato.nome", "categoriaProcesso.id", "categoriaProcesso.nome"],
            how="outer"
        )
    
    print(f"Ano {sheet} processado. Grupos encontrados: {len(df_group)}")

# Preenche valores NaN resultantes dos merges com 0 nas colunas numéricas
numeric_cols = [col for col in df_final.columns if col.startswith("numero_contratos_") or col.startswith("soma_valorGlobal_")]
df_final[numeric_cols] = df_final[numeric_cols].fillna(0)

print("Calculando totais de contratos e valorGlobal (across all years)...")
# Soma os contratos e os valores de todas as colunas de cada ano para gerar o total
df_final["numero_contratos_total"] = df_final[[col for col in df_final.columns if col.startswith("numero_contratos_")]].sum(axis=1)
df_final["soma_valorGlobal_total"] = df_final[[col for col in df_final.columns if col.startswith("soma_valorGlobal_")]].sum(axis=1)

print("Salvando o dataframe final em:", file_out_path)
df_final.to_excel(file_out_path, index=False)
print("Arquivo salvo com sucesso em:", file_out_path)
