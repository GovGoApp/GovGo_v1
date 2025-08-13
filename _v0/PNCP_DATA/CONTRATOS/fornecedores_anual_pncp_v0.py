import pandas as pd
import os
from tqdm import tqdm

# Parâmetros e caminhos
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_FILTRADOS_UNIQUE_ANUAL.xlsx"  # Arquivo de entrada
FILE_OUT = "FORNECEDORES_PNCP_ANUAL.xlsx"               # Arquivo de saída

# Monta os caminhos completos
file_in_path = os.path.join(PATH, FILE_IN)
file_out_path = os.path.join(PATH, FILE_OUT)

print("Iniciando a leitura do arquivo Excel:", file_in_path)
xls = pd.ExcelFile(file_in_path)
df_final = None

print("Processando cada aba (ano) com tqdm:")
for sheet in tqdm(xls.sheet_names, desc="Anos"):
    print("Processando ano:", sheet)
    # Lê somente as colunas dos fornecedores e a coluna 'valorGlobal'
    df_sheet = pd.read_excel(xls, sheet_name=sheet, usecols=["niFornecedor", "tipoPessoa", "nomeRazaoSocialFornecedor", "valorGlobal"])
    
    # Agrupa por fornecedor: calcula a contagem de contratos e a soma dos valores
    df_group = df_sheet.groupby(["niFornecedor", "tipoPessoa", "nomeRazaoSocialFornecedor"], as_index=False).agg(
        numero_contratos=("niFornecedor", "count"),
        soma_valorGlobal=("valorGlobal", "sum")
    )
    
    # Renomeia as colunas agregadas para incluir o ano (nome da aba)
    df_group = df_group.rename(columns={
        "numero_contratos": f"contratos_{sheet}",
        "soma_valorGlobal": f"global_{sheet}"
    })
    
    # Faz o merge com o dataframe final
    if df_final is None:
        df_final = df_group
    else:
        df_final = pd.merge(df_final, df_group, on=["niFornecedor", "tipoPessoa", "nomeRazaoSocialFornecedor"], how="outer")
    
    print(f"Ano {sheet} processado. Fornecedores encontrados neste ano: {len(df_group)}")

# Preenche os NaNs resultantes dos merges com 0 para as colunas numéricas
numeric_cols = [col for col in df_final.columns if col.startswith("numero_contratos_") or col.startswith("soma_valorGlobal_")]
df_final[numeric_cols] = df_final[numeric_cols].fillna(0)

print("Salvando o dataframe final em:", file_out_path)
df_final.to_excel(file_out_path, index=False)
print("Arquivo salvo com sucesso em:", file_out_path)
