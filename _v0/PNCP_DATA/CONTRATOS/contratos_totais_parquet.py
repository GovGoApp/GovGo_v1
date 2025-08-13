import os
import pandas as pd
from tqdm import tqdm

# Parâmetros
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_TOTAIS.xlsx"  # Arquivo original com várias abas
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

file_in_path = os.path.join(PATH, FILE_IN)
parquet_out_path = os.path.join(PATH, OUT_PARQUET)

df_list = []

print("Abrindo o arquivo de entrada para leitura de abas...")
with pd.ExcelFile(file_in_path) as xls:
    sheet_names = xls.sheet_names
    print(f"Total de abas encontradas: {len(sheet_names)}")
    
    for sheet in tqdm(sheet_names, desc="Processando abas para Parquet", ncols=80):
        df_sheet = pd.read_excel(xls, sheet_name=sheet)
        # Cria as colunas desejadas que faltarem
        for col in desired_columns:
            if col not in df_sheet.columns:
                df_sheet[col] = None
        # Filtra e reordena as colunas desejadas
        df_sheet = df_sheet[desired_columns]
        df_list.append(df_sheet)
        
print("Concatenando todas as abas em um único DataFrame...")
df_final = pd.concat(df_list, ignore_index=True)
print(f"Total de linhas concatenadas: {len(df_final)}")

print(f"Salvando o DataFrame final em Parquet em: {parquet_out_path}")
df_final.to_parquet(parquet_out_path, engine="pyarrow")
print(f"Arquivo Parquet criado com sucesso em: {parquet_out_path}")
