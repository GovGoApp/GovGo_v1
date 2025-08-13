# create_categoria_table.py

import sqlite3
import pandas as pd

# ========== CONFIGURAÇÃO ==========




BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"

DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + 'pncp_v2.db'            # caminho para seu banco SQLite

EXCEL_PATH = BASE_PATH + "CAT\\NOVA\\"      # caminho para o arquivo Excel
EXCEL_FILE = EXCEL_PATH + "NOVA CAT.xlsx"   # caminho para o arquivo Excel
SHEET_NAME = 'CAT_NV4'                      # aba a ser lida
FORMAT_NAME = 'FORMATO'                     # aba de formatação

def criar_tabela_categoria(db_path: str, excel_path: str):
    """
    Cria a tabela 'categoria' no SQLite, com colunas definidas pela aba CAT_NV4.
    Usa a aba FORMATO apenas para referência de formatos/tamanhos (não aplica
    CHECKs, pois o SQLite não impõe comprimento em TEXT).
    """
    # 1) Lê as colunas da planilha CAT_NV4
    df = pd.read_excel(excel_path, sheet_name=SHEET_NAME, dtype=str)
    colunas = df.columns.tolist()

    # 2) (Opcional) Lê formatações de cada campo
    formatos = pd.read_excel(excel_path, sheet_name=FORMAT_NAME, usecols=['CAMPOS', 'Formato'], dtype=str)
    formato_map = formatos.set_index('CAMPOS')['Formato'].to_dict()
    # -> formato_map['CODCAT'] == '{M/S}{0000}{00000}{00000}', etc.

    # 3) Gera a DDL de criação: todas as colunas TEXT e PK em CODCAT
    defs = [f"{col} TEXT" for col in colunas]
    ddl = f"""CREATE TABLE IF NOT EXISTS categoria (
    {',\n    '.join(defs)},
    PRIMARY KEY (CODCAT)
);"""

    # 4) Executa no SQLite
    conn = sqlite3.connect(db_path)
    conn.execute(ddl)
    conn.commit()
    conn.close()
    print("✔ Tabela 'categoria' criada com sucesso.")

if __name__ == '__main__':
    criar_tabela_categoria(DB_FILE, EXCEL_FILE)
