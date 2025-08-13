import os
import pandas as pd
from tqdm import tqdm

# Parâmetros
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
FILE_IN = "CONTRATOS_PNCP_TOTAIS.xlsx"  # arquivo original com várias abas
FILE_OUT = "CONTRATOS_PNCP_FILTRADOS.xlsx"  # arquivo de saída
# Máximo de linhas de dados por aba (excluindo o cabeçalho)
MAX_ROWS_PER_SHEET = 1_048_575

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
file_out_path = os.path.join(PATH, FILE_OUT)

# Lê todas as abas do arquivo de entrada e filtra/reordena as colunas desejadas
df_list = []
print("Lendo abas do arquivo de entrada...")
with pd.ExcelFile(file_in_path) as xls:
    for sheet in tqdm(xls.sheet_names, desc="Processando abas", ncols=80):
        df = pd.read_excel(xls, sheet_name=sheet)
        # Cria as colunas desejadas que não existirem
        for col in desired_columns:
            if col not in df.columns:
                df[col] = None
        # Filtra e reordena as colunas
        df = df[desired_columns]
        df_list.append(df)

print("Concatenando todas as abas em um único DataFrame...")
df_final = pd.concat(df_list, ignore_index=True)
print("Total de linhas após concatenação:", len(df_final))

# Grava o DataFrame final em um novo arquivo Excel com múltiplas abas se necessário
print("Salvando arquivo de saída...")
with pd.ExcelWriter(file_out_path, engine="openpyxl") as writer:
    total_rows = len(df_final)
    start_idx = 0
    sheet_count = 1
    # Processa em chunks para não exceder o limite de linhas
    while start_idx < total_rows:
        end_idx = min(start_idx + MAX_ROWS_PER_SHEET, total_rows)
        sheet_name = f"CONTRATOS_{sheet_count}"
        df_final.iloc[start_idx:end_idx].to_excel(writer, sheet_name=sheet_name, index=False)
        print(f" - Salvando linhas {start_idx+1} até {end_idx} na aba '{sheet_name}'")
        sheet_count += 1
        start_idx = end_idx

print("Arquivo salvo com sucesso!")
