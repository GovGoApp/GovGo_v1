import os
import pandas as pd
import numpy as np
import logging

# Configura o logging para exibir informações durante a execução
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Nome do arquivo de entrada – ajuste o caminho se necessário
# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
REPORTS_PATH = BASE_PATH + "REPORTS\\"

INPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v0.xlsx"
OUTPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v0.xlsx"
 # iremos sobrescrever adicionando uma nova aba

# Lista dos nomes das colunas com as respostas dos métodos
METHOD_COLS = [
    "Fine Tuning", 
    "Assistente", 
    "Embedding -ADA_002", 
    "Embedding - Paraphrase 384", 
    "Embedding - Paraphrase 768", 
    "Embedding - OpenAI - large - 1536"
]

# Colunas com as respostas de referência (TOP_1 a TOP_10)
TOP_COLS = [f"TOP_{i}" for i in range(1, 11)]
# (Os SCORES_1 a SCORE_10 já estão na planilha mas aqui a referência é a lista TOP, que usaremos para encontrar em que posição o método acerta)

def score_answer(method_answer: str, expected_type: str, ref_top_list: list) -> int:
    """
    Calcula a pontuação da resposta de um método para uma linha, usando os critérios:
      1) Tipo correto (3 pontos)
      2) Formato (mesmo número de partes separadas por ";" que a resposta de referência TOP_1) (2 pontos)
      3) Ranking: se a resposta for exatamente igual a um dos TOPs, pontua de 5 (TOP_1) a 1 (TOP_5); caso contrário 0.
    Retorna um inteiro entre 0 e 10.
    """
    total_score = 0

    # 1) Tipo correto
    # Dividindo a resposta pelo separador ";"
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if len(parts) < 1:
        # Se não há resposta, retorna 0
        return 0
    method_type = parts[0].upper()
    expected = expected_type.upper()
    if method_type == expected:
        total_score += 3
    else:
        logger.debug(f"Tipo incorreto: esperado '{expected}', obtido '{method_type}'.")

    # 2) Formato – comparar com a resposta de referência TOP_1
    # Se o TOP_1 existir, usamos-o como referência para quantos níveis (partes) são esperados.
    ref = ref_top_list[0] if ref_top_list and ref_top_list[0] else ""
    ref_parts = [p.strip() for p in ref.split(";") if p.strip()]
    if ref_parts and (len(parts) == len(ref_parts)):
        total_score += 2
    else:
        logger.debug(f"Formato diferente: esperado {len(ref_parts)} partes, obtido {len(parts)}.")

    # 3) Verifica se a resposta aparece entre os TOP_1 a TOP_10 e em qual posição
    rank = None
    for i, ref_ans in enumerate(ref_top_list):
        # Comparação case-insensitive e ignorando espaços extras
        if method_answer.strip().upper() == ref_ans.strip().upper():
            rank = i + 1  # posição 1-indexada
            break
    if rank is not None:
        # Pontua de acordo com a posição
        if rank == 1:
            total_score += 5
        elif rank == 2:
            total_score += 4
        elif rank == 3:
            total_score += 3
        elif rank == 4:
            total_score += 2
        elif rank == 5:
            total_score += 1
        else:
            total_score += 0
    else:
        logger.debug("Resposta não encontrada entre os TOP_1 a TOP_10.")

    return total_score

def process_row(row: pd.Series, method_cols: list, top_cols: list) -> dict:
    """
    Para uma linha (registro) da planilha, calcula a pontuação para cada método.
    Retorna um dicionário com o id e as pontuações.
    """
    result = {"id_pncp": row["id_pncp"]}
    expected_type = row["tipoDetectado"]  # exemplo: "Material" ou "Serviço"
    
    # Cria a lista de TOPs para esta linha (valores dos TOP_1 ... TOP_10)
    ref_top_list = [str(row[col]) for col in top_cols if pd.notnull(row[col])]

    for method in method_cols:
        # Recupera a resposta do método; se for nulo, usa string vazia
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
        score = score_answer(method_answer, expected_type, ref_top_list)
        result[f"Score_{method}"] = score
    return result

def main():
    # Lê a planilha
    logger.info(f"Lendo planilha: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)
    logger.info(f"Planilha lida com {len(df)} registros.")

    # Para cada linha, computa a pontuação para cada método
    scores_list = []
    for idx, row in df.iterrows():
        row_scores = process_row(row, METHOD_COLS, TOP_COLS)
        scores_list.append(row_scores)
    df_scores = pd.DataFrame(scores_list)
    logger.info("Pontuação calculada para todos os registros.")

    # Opcional: calcular também a média ou soma total por método
    summary = {}
    for method in METHOD_COLS:
        col = f"Score_{method}"
        summary[col] = df_scores[col].mean()
    logger.info("Médias por método:")
    logger.info(summary)

    # Agora, escrevemos os resultados em uma nova aba da mesma planilha.
    # Usamos ExcelWriter com openpyxl e o modo 'a' para anexar uma nova sheet.
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_scores.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
    logger.info(f"Resultados gravados na aba 'NOTAS_METODOLOGIAS' da planilha {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
