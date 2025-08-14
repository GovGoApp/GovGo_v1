import os
import pandas as pd
from tqdm import tqdm

# Parâmetros
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_TOTAIS.xlsx"  # Arquivo original com várias abas
OUT_HDF5 = "CONTRATOS_HDF5_v1.h5"          # Arquivo de saída HDF5

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

file_in_path = os.path.join(PATH, FILE_IN)
hdf5_out_path = os.path.join(PATH, OUT_HDF5)

print("Abrindo o arquivo de entrada para ler as abas...")
excel_file = pd.ExcelFile(file_in_path)
sheet_names = excel_file.sheet_names
print(f"Total de abas encontradas: {len(sheet_names)}")

# Cria ou sobrescreve o arquivo HDF5
store = pd.HDFStore(hdf5_out_path, mode="w")

for sheet in tqdm(sheet_names, desc="Processando abas para HDF5", ncols=80):
    print(f"\nLendo aba: {sheet}")
    df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
    
    # Cria as colunas que faltam
    for col in desired_columns:
        if col not in df_sheet.columns:
            df_sheet[col] = None
    
    # Filtra e reordena as colunas desejadas
    df_sheet = df_sheet[desired_columns]
    
    # Define min_itemsize para todas as colunas do tipo string (para evitar erro de tamanho)
    min_itemsize = {col: 100 for col in df_sheet.select_dtypes(include="object").columns}
    
    print(f"Adicionando dados da aba '{sheet}' ao HDF5...")
    try:
        store.append("contratos", df_sheet, format="table", data_columns=True, index=False, min_itemsize=min_itemsize)
    except Exception as e:
        print(f"Erro ao adicionar a aba {sheet}: {e}")

store.close()
print(f"Arquivo HDF5 criado com sucesso em: {hdf5_out_path}")
