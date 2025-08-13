import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATSER.xlsx"
OUT_FILE = "CATSER_nv2.json"

# Carregar o arquivo Excel
df = pd.read_excel(PATH + IN_FILE)

# Renomear as colunas para manter um padrão de nomes
df.rename(columns={
    'CodGrupo': 'codGrupo',
    'Grupo': 'Grupo',
    'CodClasse': 'codClasse',
    'Classe': 'Classe',
    'CodigoServico': 'codServico',
    'Serviço': 'Servico'
}, inplace=True)

# Ordenar o DataFrame pelas colunas desejadas
df.sort_values(by=["codGrupo", "codClasse"], inplace=True)

# Construir a estrutura JSON em 2 níveis: GRUPO e CLASSE
resultado = []
# Agrupar pelo nível de GRUPO
for (codGrupoVal, grupoVal), grupo_df in df.groupby(["codGrupo", "Grupo"], sort=False):
    classes_list = []
    
    # Agrupar pelo nível de CLASSE dentro de cada GRUPO
    for (codClasseVal, classeVal), _ in grupo_df.groupby(["codClasse", "Classe"], sort=False):
        classes_list.append({
            "codClasse": codClasseVal,
            "Classe": classeVal
        })
    
    resultado.append({
        "codGrupo": codGrupoVal,
        "Grupo": grupoVal,
        "Classes": classes_list
    })

# Converter a estrutura para JSON com indentação
json_resultado = json.dumps(resultado, ensure_ascii=False, indent=4)

# Salvar o arquivo JSON
with open(PATH + OUT_FILE, "w", encoding="utf-8") as f:
    f.write(json_resultado)

print("Arquivo CATSER_nested_2levels.json gerado com sucesso!")
