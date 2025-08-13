import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATMAT.xlsx"
OUT_FILE = "CATMAT_nv3.json"

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

# 3) CONVERTER COLUNAS NUMÉRICAS PARA INTEIRO (se aplicável)
df["codGrupo"] = df["codGrupo"].astype(int)
df["codClasse"] = df["codClasse"].astype(int)
df["codPDM"] = df["codPDM"].astype(int)

# 4) ORDENAR O DATAFRAME POR codGrupo, codClasse e codPDM
df.sort_values(by=["codGrupo", "codClasse", "codPDM"], inplace=True)

# 5) CONSTRUIR A ESTRUTURA JSON HIERÁRQUICA:
# Nível 1: Grupo (codGrupo e Grupo)
# Nível 2: Classe (codClasse e Classe)
# Nível 3: PDM (codPDM e PDM)
resultado = []
for (codGrupoVal, grupoVal), group_df in df.groupby(["codGrupo", "Grupo"], sort=False):
    classes_list = []
    for (codClasseVal, classeVal), class_df in group_df.groupby(["codClasse", "Classe"], sort=False):
        pdm_list = []
        for _, row in class_df.iterrows():
            pdm_list.append({
                "codPDM": int(row["codPDM"]),
                "PDM": row["PDM"]
            })
        classes_list.append({
            "codClasse": int(codClasseVal),
            "Classe": classeVal,
            "PDMs": pdm_list
        })
    resultado.append({
        "codGrupo": int(codGrupoVal),
        "Grupo": grupoVal,
        "Classes": classes_list
    })

# 6) CONVERTER A ESTRUTURA PARA JSON COM INDENTAÇÃO
json_resultado = json.dumps(resultado, ensure_ascii=False, indent=4)

# 7) SALVAR O ARQUIVO JSON
with open(PATH + OUT_FILE, "w", encoding="utf-8") as f:
    f.write(json_resultado)

print("Arquivo CATMAT_nv3.json gerado com sucesso!")
