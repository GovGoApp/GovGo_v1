import os
import pandas as pd
import numpy as np
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Nome do arquivo de entrada – ajuste o caminho se necessário
# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
REPORTS_PATH = BASE_PATH + "REPORTS\\"

INPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v1.xlsx"
OUTPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v1.xlsx"
 # iremos sobrescrever adicionando uma nova aba

# Colunas dos métodos (respostas dos diferentes métodos)
METHOD_COLS = [
    "Fine Tuning", 
    "Assistente", 
    "Embedding -ADA_002", 
    "Embedding - Paraphrase 384", 
    "Embedding - Paraphrase 768", 
    "Embedding - OpenAI - large - 1536"
]

# Colunas de referência dos TOPs e dos SCORES (do embedding referência)
TOP_COLS = [f"TOP_{i}" for i in range(1, 11)]
SCORE_COLS = [f"SCORE_{i}" for i in range(1, 11)]

def score_answer(method_answer: str, expected_type: str, ref_top_list: list, ref_score_list: list) -> int:
    """
    Calcula a pontuação da resposta de um método para um registro, considerando:
      - Tipo: 3 pontos se o tipo (primeira parte) confere.
      - Formato: 2 pontos se o número de partes (separadas por ';') for igual ao da referência (TOP_1).
      - Ranking: Se a resposta for encontrada entre os TOP_1 a TOP_10, atribui pontos decrescentes
        onde TOP_1 vale 10, TOP_2 vale 9, ..., TOP_10 vale 1, multiplicados pelo fator (SCORE_i / 0.7).
        Se não encontrada, 0 pontos.
    Retorna um inteiro entre 0 e aproximadamente 15.
    """
    total_score = 0

    # 1) Tipo
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if len(parts) < 1:
        return 0
    method_type = parts[0].upper()
    expected = expected_type.upper()
    if method_type == expected:
        total_score += 3
    else:
        logger.debug(f"Tipo incorreto: esperado '{expected}', obtido '{method_type}'.")

    # 2) Formato: verifica se o número de partes é igual à do TOP_1 (referência)
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        if len(parts) == len(ref_parts):
            total_score += 2
        else:
            logger.debug(f"Formato diferente: esperado {len(ref_parts)} partes, obtido {len(parts)}.")
    else:
        logger.debug("Não há referência TOP_1 para verificar formato.")

    # 3) Ranking: busca a resposta entre os TOP_1 a TOP_10
    rank = None
    for i, ref_ans in enumerate(ref_top_list):
        # Comparação sem case sensitive e com strip
        if method_answer.strip().upper() == ref_ans.strip().upper():
            rank = i + 1  # posição 1-indexada
            break

    if rank is not None:
        # Pontuação decrescente: TOP_1 = 10, TOP_2 = 9, ..., TOP_10 = 1
        base_points = 11 - rank
        # Ajusta pelo score da posição; assume que 0.7 é um score alto (normaliza)
        # Se SCORE_i é menor, a pontuação é reduzida
        try:
            sim_score = float(ref_score_list[rank - 1])
        except Exception as e:
            logger.error(f"Erro ao converter SCORE para rank {rank}: {e}")
            sim_score = 0
        ranking_points = int(round(base_points * (sim_score / 0.7)))
        total_score += ranking_points
    else:
        logger.debug("Resposta não encontrada entre os TOP_1 a TOP_10; ranking = 0.")

    return total_score

def process_row(row: pd.Series, method_cols: list, top_cols: list, score_cols: list) -> dict:
    """
    Processa uma linha da planilha e calcula a pontuação para cada método.
    Retorna um dicionário com o id e as pontuações.
    """
    result = {"id_pncp": row["id_pncp"]}
    expected_type = row["tipoDetectado"]  # ex.: "Material" ou "Serviço"
    
    # Cria a lista de respostas de referência TOP_1 ... TOP_10
    ref_top_list = [str(row[col]) for col in top_cols if pd.notnull(row[col])]
    # Cria a lista de scores correspondentes (SCORE_1 ... SCORE_10)
    ref_score_list = [row[col] for col in score_cols if pd.notnull(row[col])]

    for method in method_cols:
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
        score = score_answer(method_answer, expected_type, ref_top_list, ref_score_list)
        result[f"Score_{method}"] = score
    return result

def main():
    logger.info(f"Lendo planilha: {INPUT_FILE}")
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        logger.error(f"Erro ao ler a planilha: {e}")
        return
    logger.info(f"Planilha lida com {len(df)} registros.")

    scores_list = []
    for idx, row in df.iterrows():
        row_scores = process_row(row, METHOD_COLS, TOP_COLS, SCORE_COLS)
        scores_list.append(row_scores)
    df_scores = pd.DataFrame(scores_list)
    logger.info("Pontuação calculada para todos os registros.")

    # Cálculo opcional: média dos scores por método
    summary = {}
    for method in METHOD_COLS:
        col = f"Score_{method}"
        summary[col] = df_scores[col].mean()
    logger.info("Médias dos scores por método:")
    logger.info(summary)

    # Grava os resultados em uma nova aba na mesma planilha
    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_scores.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
        logger.info(f"Resultados gravados na aba 'NOTAS_METODOLOGIAS' da planilha {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Erro ao gravar a nova aba: {e}")

if __name__ == '__main__':
    main()
