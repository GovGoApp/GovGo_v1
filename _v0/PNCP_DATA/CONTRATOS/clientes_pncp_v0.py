import pandas as pd
import os
from tqdm import tqdm

# Parâmetros e caminhos
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_FILTRADOS_UNIQUE_ANUAL.xlsx"         # Arquivo de entrada
FILE_OUT = "CONTRATOS_PNCP_CLIENTES.xlsx"                       # Arquivo de saída

# Monta os caminhos completos
file_in_path = os.path.join(PATH, FILE_IN)
file_out_path = os.path.join(PATH, FILE_OUT)

print("Iniciando a leitura do arquivo Excel:", file_in_path)
xls = pd.ExcelFile(file_in_path)
lista_dfs = []

print("Lendo as abas do arquivo com tqdm:")
for sheet in tqdm(xls.sheet_names, desc="Lendo abas"):
    print("  Lendo aba:", sheet)
    df_sheet = pd.read_excel(
        xls, 
        sheet_name=sheet, 
        usecols=[
            "orgaoEntidade.cnpj", 
            "orgaoEntidade.razaoSocial", 
            "orgaoEntidade.poderId", 
            "orgaoEntidade.esferaId", 
            "unidadeOrgao.ufNome", 
            "unidadeOrgao.codigoUnidade", 
            "unidadeOrgao.nomeUnidade", 
            "unidadeOrgao.ufSigla", 
            "unidadeOrgao.municipioNome", 
            "unidadeOrgao.codigoIbge", 
            "valorGlobal"
        ]
    )
    lista_dfs.append(df_sheet)

print("Concatenando os dataframes de todas as abas...")
df_total = pd.concat(lista_dfs, ignore_index=True)
print("Dataframes concatenados. Total de linhas:", len(df_total))

print("Agrupando os clientes e calculando número de contratos e soma de valorGlobal...")
df_resultado = df_total.groupby([
    "orgaoEntidade.cnpj", 
    "orgaoEntidade.razaoSocial", 
    "orgaoEntidade.poderId", 
    "orgaoEntidade.esferaId", 
    "unidadeOrgao.ufNome", 
    "unidadeOrgao.codigoUnidade", 
    "unidadeOrgao.nomeUnidade", 
    "unidadeOrgao.ufSigla", 
    "unidadeOrgao.municipioNome", 
    "unidadeOrgao.codigoIbge"
], as_index=False).agg(
    numero_contratos=("orgaoEntidade.cnpj", "count"),
    soma_valorGlobal=("valorGlobal", "sum")
)
print("Agrupamento concluído. Total de clientes agrupados:", len(df_resultado))

print("Ordenando os clientes por número de contratos (ordem decrescente)...")
df_resultado.sort_values(by="numero_contratos", ascending=False, inplace=True)
print("Ordenação concluída.")

print("Salvando o dataframe resultante em:", file_out_path)
df_resultado.to_excel(file_out_path, index=False)
print("Arquivo salvo com sucesso em:", file_out_path)
