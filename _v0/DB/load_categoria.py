# load_categoria_data.py

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

def carregar_dados_categoria(db_path: str, excel_path: str):
    """
    Lê a aba CAT_NV4 e insere (ou atualiza) todas as linhas na tabela 'categoria'.
    Usa INSERT OR REPLACE para evitar duplicatas de CODCAT.
    """
    # 1) Lê dados, garantindo strings e sem NaN
    df = pd.read_excel(excel_path, sheet_name=SHEET_NAME, dtype=str).fillna('')

    # 2) Prepara SQL de inserção
    cols = df.columns.tolist()
    placeholders = ','.join('?' for _ in cols)
    sql = f"INSERT OR REPLACE INTO categoria ({', '.join(cols)}) VALUES ({placeholders});"

    # 3) Executa em lote
    conn = sqlite3.connect(db_path)
    conn.executemany(sql, df.values.tolist())
    conn.commit()
    conn.close()
    print(f"✔ {len(df)} registros inseridos em 'categoria'.")

if __name__ == '__main__':
    carregar_dados_categoria(DB_FILE, EXCEL_FILE)
