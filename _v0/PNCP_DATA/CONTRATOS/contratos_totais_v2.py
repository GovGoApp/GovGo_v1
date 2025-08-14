import os
import pandas as pd
from tqdm import tqdm

# Parâmetros
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_TOTAIS.xlsx"     # nome do arquivo original com várias abas
OUT_HDF5 = "CONTRATOS_HDF5.h5"             # Arquivo de saída HDF5
OUT_PARQUET = "CONTRATOS_PARQUET.parquet"  # Arquivo de saída Parquet

# Lista de colunas desejadas, na ordem exata
desired_columns = [
    "numeroControlePncpCompra",
    "anoContrato",
    "numeroContratoEmpenho",
    "dataAssinatura",
    "dataVigenciaInicio",
    "dataVigenciaFim",
    "niFornecedor",
    "tipoPessoa",
    "sequencialContrato",
    "informacaoComplementar",
    "processo",
    "nomeRazaoSocialFornecedor",
    "numeroControlePNCP",
    "numeroParcelas",
    "numeroRetificacao",
    "objetoContrato",
    "valorInicial",
    "valorParcela",
    "valorGlobal",
    "dataAtualizacaoGlobal",
    "usuarioNome",
    "tipoContrato.id",
    "tipoContrato.nome",
    "orgaoEntidade.cnpj",
    "orgaoEntidade.razaoSocial",
    "orgaoEntidade.poderId",
    "orgaoEntidade.esferaId",
    "categoriaProcesso.id",
    "categoriaProcesso.nome",
    "unidadeOrgao.ufNome",
    "unidadeOrgao.codigoUnidade",
    "unidadeOrgao.nomeUnidade",
    "unidadeOrgao.ufSigla",
    "unidadeOrgao.municipioNome",
    "unidadeOrgao.codigoIbge",
]

# Monta os caminhos completos
file_in_path = os.path.join(PATH, FILE_IN)
hdf5_out_path = os.path.join(PATH, OUT_HDF5)
parquet_out_path = os.path.join(PATH, OUT_PARQUET)

# Abre o arquivo Excel com várias abas
print("Abrindo o arquivo de entrada para ler as abas...")
excel_file = pd.ExcelFile(file_in_path)
sheet_names = excel_file.sheet_names
print(f"Total de abas encontradas: {len(sheet_names)}")

# ---------------------------------------------------
# Parte 1: Salvar em HDF5 (append de cada aba)
# ---------------------------------------------------
print("\nSalvando os dados em HDF5...")
# Cria ou sobrescreve o arquivo HDF5
store = pd.HDFStore(hdf5_out_path, mode="w")

# Itera sobre cada aba com tqdm
for sheet in tqdm(sheet_names, desc="Processando abas para HDF5", ncols=80):
    print(f"\nLendo aba: {sheet}")
    df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
    
    # Cria as colunas que faltam
    for col in desired_columns:
        if col not in df_sheet.columns:
            df_sheet[col] = None
    # Filtra e reordena as colunas desejadas
    df_sheet = df_sheet[desired_columns]
    
    # Append no HDF5; usamos formato "table" para permitir consultas
    store.append("contratos", df_sheet, format="table", data_columns=True, index=False)
    
store.close()
print(f"Arquivo HDF5 criado com sucesso em: {hdf5_out_path}")

# ---------------------------------------------------
# Parte 2: Salvar em Parquet (concatenando todas as abas)
# ---------------------------------------------------
print("\nConcatenando abas para salvar em Parquet...")
df_list = []
for sheet in tqdm(sheet_names, desc="Processando abas para Parquet", ncols=80):
    df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
    for col in desired_columns:
        if col not in df_sheet.columns:
            df_sheet[col] = None
    df_sheet = df_sheet[desired_columns]
    df_list.append(df_sheet)
    
# Concatena todas as abas
df_final = pd.concat(df_list, ignore_index=True)
print(f"Total de linhas concatenadas: {len(df_final)}")

# Salva o DataFrame final em formato Parquet
df_final.to_parquet(parquet_out_path, engine="pyarrow")
print(f"Arquivo Parquet criado com sucesso em: {parquet_out_path}")
