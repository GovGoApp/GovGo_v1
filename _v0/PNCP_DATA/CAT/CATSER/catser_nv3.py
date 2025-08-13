import pandas as pd
import json

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CAT\\"
IN_FILE = "CATSER.xlsx"
OUT_FILE = "CATSER_nv3.json"

# 1) CARREGAR O ARQUIVO EXCEL
# Ajuste o caminho conforme a localização real do seu arquivo:
df = pd.read_excel(PATH + IN_FILE)

# 2) RENOMEAR AS COLUNAS (se necessário) para manter um padrão de nomes
df.rename(columns={
    'CodGrupo': 'codGrupo',
    'Grupo': 'Grupo',
    'CodClasse': 'codClasse',
    'Classe': 'Classe',
    'CodigoServico': 'codServico',
    'Serviço': 'Servico'
}, inplace=True)

# 3) ORDENAR O DATAFRAME PELAS COLUNAS DESEJADAS
df.sort_values(by=["codGrupo", "codClasse", "codServico"], inplace=True)

# 4) CONSTRUIR A ESTRUTURA JSON ANINHADA
resultado = []
# Agrupamento de 1º nível: (codGrupo, Grupo)
for (codGrupoVal, grupoVal), grupo_df in df.groupby(["codGrupo", "Grupo"], sort=False):
    classes_list = []
    
    # Agrupamento de 2º nível: (codClasse, Classe)
    for (codClasseVal, classeVal), classe_df in grupo_df.groupby(["codClasse", "Classe"], sort=False):
        servicos_list = []
        
        # Nível final (Serviços)
        for _, row in classe_df.iterrows():
            servicos_list.append({
                "codServico": row["codServico"],
                "Servico": row["Servico"]
            })
        
        classes_list.append({
            "codClasse": codClasseVal,
            "Classe": classeVal,
            "Servicos": servicos_list
        })
    
    resultado.append({
        "codGrupo": codGrupoVal,
        "Grupo": grupoVal,
        "Classes": classes_list
    })

# 5) GERAR O JSON (aninhado) COM INDENTAÇÃO
json_aninhado = json.dumps(resultado, ensure_ascii=False, indent=4)

# 6) SALVAR O ARQUIVO JSON
with open(PATH + OUT_FILE, "w", encoding="utf-8") as f:
    f.write(json_aninhado)

print("Arquivo CATSER_nested.json gerado com sucesso!")
