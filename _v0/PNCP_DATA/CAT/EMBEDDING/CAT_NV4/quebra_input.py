import os
import pandas as pd
import math
from tqdm.auto import tqdm

# Definir caminhos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
INPUT_FILE = CLASS_PATH + "#CONTRATAÇÃO_ID_COMPRAS_ITENS.xlsx"
SHEET = "ITENS"
OUTPUT_DIR = CLASS_PATH + "INPUT\\"

# Criar diretório de saída se não existir
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Definir tamanho de cada arquivo de saída
CHUNK_SIZE = 20000

def process_large_file():
    print(f"Processando o arquivo grande {INPUT_FILE}")
    
    try:
        # Carregar o arquivo inteiro de uma vez
        print("Carregando o arquivo completo...")
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET)
        
        print(f"Arquivo carregado com {len(df)} linhas")
        
        # Processar as colunas - substituir valores nulos e converter para string
        print("Processando colunas...")
        df['objetoCompra'] = df['objetoCompra'].fillna('').astype(str)
        df['itens'] = df['itens'].fillna('').astype(str)
        
        # Remover as chaves dos itens
        df['itens'] = df['itens'].str.replace('{', '').str.replace('}', '')
        
        # Combinar as colunas objetoCompra e itens no formato solicitado
        print("Concatenando colunas...")
        df['objetoCompra_nova'] = df.apply(
            lambda row: f"{row['objetoCompra']}: {row['itens']}", axis=1
        )
        
        # Criar DataFrame final com apenas as colunas necessárias
        df_final = pd.DataFrame({
            'id_pncp': df['id_pncp'],
            'objetoCompra': df['objetoCompra_nova']
        })
        
        # Calcular o número total de chunks para salvar
        total_chunks = math.ceil(len(df_final) / CHUNK_SIZE)
        print(f"Dividindo em {total_chunks} arquivos de {CHUNK_SIZE} linhas cada")
        
        # Dividir e salvar em arquivos menores
        for chunk_idx in tqdm(range(total_chunks), desc="Salvando arquivos"):
            start_idx = chunk_idx * CHUNK_SIZE
            end_idx = min(start_idx + CHUNK_SIZE, len(df_final))
            
            chunk_df = df_final.iloc[start_idx:end_idx].copy()
            
            # Salvar o chunk em um arquivo separado
            output_file = f"{OUTPUT_DIR}INPUT_{chunk_idx+1:03d}.xlsx"
            chunk_df.to_excel(output_file, index=False)
        
        print(f"Processamento concluído! {total_chunks} arquivos gerados em {OUTPUT_DIR}")
    
    except Exception as e:
        print(f"Erro durante o processamento: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    process_large_file()