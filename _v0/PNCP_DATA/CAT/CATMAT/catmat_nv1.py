import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATMAT.xlsx"
OUT_FILE = "CATMAT_nv1.json"

# 1) CARREGAR O ARQUIVO CATMAT.xlsx
df = pd.read_excel(PATH + IN_FILE)

# 2) RENOMEAR AS COLUNAS PARA UM PADRÃO CONSISTENTE
df.rename(columns={
    "Código do Grupo": "codGrupo",
    "Nome do Grupo": "Grupo",
    "Código da Classe": "codClasse",
    "Nome da Classe": "Classe",
    "Código do PDM": "codPDM",
    "Nome do PDM": "PDM"
}, inplace=True)

# 3) CONVERTER A COLUNA 'codGrupo' PARA INTEIRO
df["codGrupo"] = df["codGrupo"].astype(int)

# 4) ORDENAR O DATAFRAME PELA COLUNA codGrupo
df.sort_values(by=["codGrupo"], inplace=True)

# 5) SELECIONAR APENAS OS REGISTROS ÚNICOS DE GRUPO (NÍVEL 1)
df_nivel1 = df[["codGrupo", "Grupo"]].drop_duplicates()

# 6) CONVERTER O DATAFRAME PARA UMA LISTA DE DICIONÁRIOS
resultado = df_nivel1.to_dict(orient="records")

# 7) CONVERTER A ESTRUTURA PARA JSON COM INDENTAÇÃO
json_resultado = json.dumps(resultado, ensure_ascii=False, indent=4)

# 8) SALVAR O ARQUIVO JSON
with open(PATH + OUT_FILE, "w", encoding="utf-8") as f:
    f.write(json_resultado)

print("Arquivo CATMAT_nv1.json gerado com sucesso!")
