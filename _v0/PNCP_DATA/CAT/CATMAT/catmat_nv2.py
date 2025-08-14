import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATMAT.xlsx"
OUT_FILE = "CATMAT_nv2.json"

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

# 4) ORDENAR O DATAFRAME POR codGrupo e codClasse
df.sort_values(by=["codGrupo", "codClasse"], inplace=True)

# 5) CONSTRUIR A ESTRUTURA JSON HIERÁRQUICA EM 2 NÍVEIS:
# Nível 1: Grupo (codGrupo e Grupo)
# Nível 2: Classe (codClasse e Classe)
resultado = []
for (codGrupoVal, grupoVal), group_df in df.groupby(["codGrupo", "Grupo"], sort=False):
    classes_list = []
    for (codClasseVal, classeVal), _ in group_df.groupby(["codClasse", "Classe"], sort=False):
        classes_list.append({
            "codClasse": int(codClasseVal),
            "Classe": classeVal
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

print("Arquivo CATMAT_nv2.json gerado com sucesso!")
