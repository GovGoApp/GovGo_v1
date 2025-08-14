import os
import pandas as pd

# Parâmetros de caminho e arquivos
PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\CONTRATOS\\"
IN_FILE = "CONTRATOS_2021_2022_v2.xlsx"
OUT_FILE = "CONTRATOS_2023_2025.xlsx"
NEW_SHEET_NAME = "2021_2022_ALIGNED"

# Mapeamento De -> Para (colunas 2021–2022 -> colunas 2023–2025)
rename_dict = {
    "numeroControlePncpCompra": "numeroControlePncpCompra",
    "codigoPaisFornecedor": "codigoPaisFornecedor",
    "anoContrato": "anoContrato",
    "tipoContrato_id": "tipoContrato.id",
    "tipoContrato_nome": "tipoContrato.nome",
    "numeroContratoEmpenho": "numeroContratoEmpenho",
    "dataAssinatura": "dataAssinatura",
    "dataVigenciaInicio": "dataVigenciaInicio",
    "dataVigenciaFim": "dataVigenciaFim",
    "niFornecedor": "niFornecedor",
    "tipoPessoa": "tipoPessoa",
    "orgaoEntidade_cnpj": "orgaoEntidade.cnpj",
    "orgaoEntidade_razaoSocial": "orgaoEntidade.razaoSocial",
    "orgaoEntidade_poderId": "orgaoEntidade.poderId",
    "orgaoEntidade_esferaId": "orgaoEntidade.esferaId",
    "categoriaProcesso_id": "categoriaProcesso.id",
    "categoriaProcesso_nome": "categoriaProcesso.nome",
    "dataPublicacaoPncp": "dataPublicacaoPncp",
    "dataAtualizacao": "dataAtualizacao",
    "sequencialContrato": "sequencialContrato",
    "unidadeOrgao_ufNome": "unidadeOrgao.ufNome",
    "unidadeOrgao_codigoUnidade": "unidadeOrgao.codigoUnidade",
    "unidadeOrgao_nomeUnidade": "unidadeOrgao.nomeUnidade",
    "unidadeOrgao_ufSigla": "unidadeOrgao.ufSigla",
    "unidadeOrgao_municipioNome": "unidadeOrgao.municipioNome",
    "unidadeOrgao_codigoIbge": "unidadeOrgao.codigoIbge",
    "informacaoComplementar": "informacaoComplementar",
    "processo": "processo",
    "unidadeSubRogada_ufNome": "unidadeSubRogada.ufNome",
    "unidadeSubRogada_codigoUnidade": "unidadeSubRogada.codigoUnidade",
    "unidadeSubRogada_nomeUnidade": "unidadeSubRogada.nomeUnidade",
    "unidadeSubRogada_ufSigla": "unidadeSubRogada.ufSigla",
    "unidadeSubRogada_municipioNome": "unidadeSubRogada.municipioNome",
    "unidadeSubRogada_codigoIbge": "unidadeSubRogada.codigoIbge",
    "orgaoSubRogado_cnpj": "orgaoSubRogado.cnpj",
    "orgaoSubRogado_razaoSocial": "orgaoSubRogado.razaoSocial",
    "orgaoSubRogado_poderId": "orgaoSubRogado.poderId",
    "orgaoSubRogado_esferaId": "orgaoSubRogado.esferaId",
    "nomeRazaoSocialFornecedor": "nomeRazaoSocialFornecedor",
    "niFornecedorSubContratado": "niFornecedorSubContratado",
    "nomeFornecedorSubContratado": "nomeFornecedorSubContratado",
    "receita": "receita",
    "numeroParcelas": "numeroParcelas",
    "numeroRetificacao": "numeroRetificacao",
    "tipoPessoaSubContratada": "tipoPessoaSubContratada",
    "objetoContrato": "objetoContrato",
    "valorInicial": "valorInicial",
    "valorParcela": "valorParcela",
    "valorGlobal": "valorGlobal",
    "valorAcumulado": "valorAcumulado",
    "dataAtualizacaoGlobal": "dataAtualizacaoGlobal",
    "identificadorCipi": "identificadorCipi",
    "urlCipi": "urlCipi",
    "numeroControlePNCP": "numeroControlePNCP",
    "usuarioNome": "usuarioNome"
}

# 1) Lê o OUT_FILE apenas para capturar a ORDEM das colunas (assumindo que a 1ª aba tem o layout correto)
out_file_path = os.path.join(PATH, OUT_FILE)
with pd.ExcelFile(out_file_path) as xls:
    out_file_sheets = xls.sheet_names
    # Aqui usamos a primeira aba; ajuste caso queira outra
    out_df_header = pd.read_excel(xls, sheet_name=out_file_sheets[0], nrows=0)

# A ordem das colunas desejadas:
desired_columns = list(out_df_header.columns)

# 2) Lê o IN_FILE (2021–2022)
in_file_path = os.path.join(PATH, IN_FILE)
in_df = pd.read_excel(in_file_path)

# 3) Renomeia colunas conforme o dicionário De->Para
in_df_renamed = in_df.rename(columns=rename_dict)

# 4) Garante que todas as colunas do OUT_FILE existam no DataFrame
for col in desired_columns:
    if col not in in_df_renamed.columns:
        in_df_renamed[col] = None

# 5) Reordena as colunas de acordo com a mesma ordem do OUT_FILE
in_df_renamed = in_df_renamed[desired_columns]

# 6) Salva o resultado em uma nova aba do IN_FILE
with pd.ExcelWriter(in_file_path, engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
    in_df_renamed.to_excel(writer, sheet_name=NEW_SHEET_NAME, index=False)

print(f"A nova aba '{NEW_SHEET_NAME}' foi criada em '{IN_FILE}' com as colunas no mesmo formato do OUT_FILE.")
