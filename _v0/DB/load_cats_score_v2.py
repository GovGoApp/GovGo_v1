# load_cats_score_top.py

import sqlite3
import pandas as pd
import time
import os
from tqdm import tqdm

# ========== CONFIGURAÇÃO ==========
BASE_PATH   = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_FILE     = BASE_PATH + "DB\\pncp_v2.db"  
EXCEL_FILE  = BASE_PATH + "CLASSY\\OUTPUT\\NEW_ORDER\\UNIFIED_OUTPUT_TOP.xlsx"
SHEET_NAME  = 'OUTPUT'   # nome da aba (ou use índice 0 para a primeira)

# ======= EXECUÇÃO =======
def main():
    start_time = time.time()
    print(f"Iniciando processamento de {os.path.basename(EXCEL_FILE)}")
    
    # Conexão otimizada com SQLite
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Otimizações SQLite avançadas
    cur.execute("PRAGMA journal_mode = OFF;")
    cur.execute("PRAGMA synchronous = 0;")  # 0 é ainda mais rápido que OFF
    cur.execute("PRAGMA cache_size = 100000;")  # Aumentado 10x
    cur.execute("PRAGMA temp_store = MEMORY;")
    cur.execute("PRAGMA locking_mode = EXCLUSIVE;")
    cur.execute("PRAGMA busy_timeout = 60000;")  # 60 segundos
    conn.commit()
    
    print("Carregando arquivo Excel (pode levar alguns minutos)...")
    
    try:
        # Carregamento do Excel
        df = pd.read_excel(
            EXCEL_FILE, 
            sheet_name=SHEET_NAME,
            usecols=['id_pncp', 'TOP_1', 'SCORE_1'],
            dtype={'id_pncp': str, 'TOP_1': str}
        )
        
        print(f"Excel carregado: {len(df)} linhas encontradas")
        
        # Filtrar registros com id_pncp válido
        df = df.dropna(subset=['id_pncp'])
        print(f"Após filtrar registros vazios: {len(df)} linhas")
        
        # Preparar DataFrame otimizado
        df['TOP_1'] = df['TOP_1'].where(pd.notna(df['TOP_1']), None)
        df['SCORE_1'] = df['SCORE_1'].apply(lambda x: float(x) if pd.notna(x) else None)
        
        # OTIMIZAÇÃO PRINCIPAL: Usar tabela temporária e UPDATE via JOIN
        print("Criando índice para aceleração...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_numeroControlePNCP ON contratacao(numeroControlePNCP);")
        conn.commit()
        
        print("Criando tabela temporária...")
        cur.execute("DROP TABLE IF EXISTS temp_updates;")
        cur.execute("""
        CREATE TEMPORARY TABLE temp_updates (
            id_pncp TEXT,
            codcat TEXT,
            score REAL
        );
        """)
        
        # Inserir em lotes na tabela temporária
        print("Carregando dados na tabela temporária...")
        batch_size = 50000
        
        # Converter para lista de tuplas para inserção mais rápida
        update_data = list(zip(df['id_pncp'], df['TOP_1'], df['SCORE_1']))
        
        # Inserir dados na tabela temporária em lotes
        with tqdm(total=len(update_data), desc="Carregando dados temp", unit="lin") as pbar:
            for i in range(0, len(update_data), batch_size):
                batch = update_data[i:i+batch_size]
                cur.executemany(
                    "INSERT INTO temp_updates (id_pncp, codcat, score) VALUES (?, ?, ?)",
                    batch
                )
                pbar.update(len(batch))
        
        conn.commit()
        
        # Criar índice na tabela temporária
        print("Criando índice na tabela temporária...")
        cur.execute("CREATE INDEX idx_temp_id_pncp ON temp_updates(id_pncp);")
        conn.commit()
        
        # Executar atualização única via JOIN (muito mais rápido)
        print("Executando atualização em massa via JOIN...")
        cur.execute("""
        UPDATE contratacao
        SET CODCAT = (SELECT codcat FROM temp_updates WHERE temp_updates.id_pncp = contratacao.numeroControlePNCP),
            SCORE = (SELECT score FROM temp_updates WHERE temp_updates.id_pncp = contratacao.numeroControlePNCP)
        WHERE EXISTS (SELECT 1 FROM temp_updates WHERE temp_updates.id_pncp = contratacao.numeroControlePNCP)
        """)
        
        # Limpar tabela temporária e índices
        cur.execute("DROP TABLE IF EXISTS temp_updates;")
        conn.commit()
        
        elapsed_time = time.time() - start_time
        rows_updated = cur.rowcount
        update_speed = rows_updated / elapsed_time if elapsed_time > 0 else 0
        
        print(f"✅ Atualização concluída em {elapsed_time:.2f}s")
        print(f"✅ {rows_updated} linhas atualizadas ({update_speed:.2f} linhas/s)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro durante processamento: {str(e)}")
        conn.close()
        raise

if __name__ == '__main__':
    main()
