import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATSER.xlsx"
OUT_FILE = "CATSER_nv1.json"

# Carregar o arquivo Excel
df = pd.read_excel(PATH + IN_FILE)

# Renomear as colunas para manter um padrão de nomes (somente GRUPO)
df.rename(columns={
    'CodGrupo': 'codGrupo',
    'Grupo': 'Grupo'
}, inplace=True)

# Ordenar o DataFrame pelo codGrupo
df.sort_values(by=["codGrupo"], inplace=True)

# Selecionar somente as colunas de nível 1 e remover duplicatas
df_nivel1 = df[['codGrupo', 'Grupo']].drop_duplicates()

# Converter o DataFrame para uma lista de dicionários
resultado = df_nivel1.to_dict(orient='records')

# Converter a estrutura para JSON com indentação
json_resultado = json.dumps(resultado, ensure_ascii=False, indent=4)

# Salvar o arquivo JSON
with open(PATH + OUT_FILE, "w", encoding="utf-8") as f:
    f.write(json_resultado)

print("Arquivo CATSER_nivel1.json gerado com sucesso!")
