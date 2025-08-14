import os
import pandas as pd

# Parâmetros
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CONTRATOS\\"
IN_FILE = "contratos_pncp_2025-02_20250325_132442.xlsx"
OUT_FILE = "contratos_pncp_2025-02_20250325_123616.xlsx"
NEW_SHEET_NAME = "INFILE_REORDERED"

# 1. Ler o OUT_FILE para capturar a ordem das colunas (usamos a 1ª aba)
out_path = os.path.join(PATH, OUT_FILE)
with pd.ExcelFile(out_path) as xls:
    # Lê somente o cabeçalho (nrows=0) da primeira aba para obter a ordem desejada
    out_df_header = pd.read_excel(xls, sheet_name=xls.sheet_names[0], nrows=0)
desired_columns = list(out_df_header.columns)
print("Ordem de colunas desejada (OUT_FILE):")
print(desired_columns)

# 2. Ler o IN_FILE (que tem as mesmas nomenclaturas, mas em ordem diferente)
in_path = os.path.join(PATH, IN_FILE)
in_df = pd.read_excel(in_path)
print("Colunas originais de IN_FILE:")
print(list(in_df.columns))

# 3. Reordenar as colunas de IN_FILE para que fiquem na mesma ordem de OUT_FILE
# Se alguma coluna do OUT_FILE não existir no IN_FILE, ela será criada com None
for col in desired_columns:
    if col not in in_df.columns:
        in_df[col] = None
# Se IN_FILE tiver colunas extras que não estão em desired_columns, elas serão descartadas
in_df_reordered = in_df[desired_columns]
print("Nova ordem de colunas aplicada em IN_FILE.")

# 4. Salvar o DataFrame reordenado como uma nova aba no OUT_FILE
with pd.ExcelWriter(out_path, engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
    in_df_reordered.to_excel(writer, sheet_name=NEW_SHEET_NAME, index=False)

print(f"A nova aba '{NEW_SHEET_NAME}' foi criada em '{OUT_FILE}' com as colunas reordenadas!")
