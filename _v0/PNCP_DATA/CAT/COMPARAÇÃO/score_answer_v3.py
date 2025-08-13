import os
import pandas as pd
import numpy as np
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Definição dos caminhos e arquivos (ajuste conforme necessário)
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
REPORTS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\COMPARATIVOS\\"

INPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v6.xlsx"
OUTPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v6.xlsx"  # iremos sobrescrever adicionando novas abas

# Lista dos nomes das colunas com as respostas dos métodos
METHOD_COLS = [
    "Fine Tuning", 
    "Assistente", 
    "Embedding - ADA_002", 
    "Embedding - Paraphrase 384", 
    "Embedding - Paraphrase 768", 
    "Embedding - Nomic",
    "Embedding - Granite107",
    "Embedding - Granite278",
    "Embedding - Mxbai",
    "Embedding - OpenAI - large - 1536"
]

# Colunas de referência (TOP_1 a TOP_10) – SCORE_COLS não serão utilizados aqui
TOP_COLS = [f"TOP_{i}" for i in range(1, 11)]
SCORE_COLS = [f"SCORE_{i}" for i in range(1, 11)]

def simplified_score_answer(method_answer: str, expected_type: str, ref_top_list: list) -> int:
    """
    Calcula a pontuação simplificada para uma resposta com base nos seguintes critérios:
      1) Tipo correto: +1 ponto (comparando a primeira parte, antes do ";")
      2) Formato correto: +1 ponto se o número de partes da resposta for igual ao número de partes da referência (TOP_1)
      3) Ranking:
         - Se a resposta estiver entre os TOP_1 a TOP_10: +1 ponto
         - Se a resposta estiver entre os TOP_1 a TOP_5: +1 ponto extra
         - Se a resposta estiver exatamente no TOP_1: +1 ponto extra
         
    Retorna um inteiro entre 0 e 5.
    """
    score = 0

    # Dividir a resposta do método em partes (usando ";" como separador)
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    # Se não houver partes, retorna 0
    if not parts:
        return 0

    # 1) Tipo: comparar a primeira parte com o expected_type (case-insensitive)
    method_type = parts[0].upper()
    expected = expected_type.upper()
    if method_type == expected:
        score += 1

    # 2) Formato: usar o TOP_1 como referência (se existir)
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        if len(parts) == len(ref_parts):
            score += 1

    # 3) Ranking: verificar se a resposta aparece entre os TOP_1 a TOP_10
    ranking_position = None
    for i, ref_ans in enumerate(ref_top_list):
        if method_answer.strip().upper() == ref_ans.strip().upper():
            ranking_position = i + 1  # posição 1-indexada
            break
    if ranking_position is not None:
        score += 1  # +1 se estiver entre TOP_1 e TOP_10
        if ranking_position <= 5:
            score += 1  # +1 extra se estiver entre TOP_1 e TOP_5
        if ranking_position == 1:
            score += 1  # +1 extra se estiver exatamente no TOP_1

    # Garantir que o score máximo seja 5
    return min(score, 5)

def process_row_intermediate(row: pd.Series, method_cols: list, top_cols: list) -> list:
    """
    Para uma linha da planilha, calcula a pontuação simplificada para cada método.
    Retorna uma lista de dicionários com os detalhes:
       id_pncp, método, resposta do método, expected_type, ranking_position, final_score.
    """
    intermediate_results = []
    expected_type = row["tipoDetectado"]  # Ex: "Material" ou "Serviço"
    ref_top_list = [str(row[col]) for col in top_cols if pd.notnull(row[col])]
    record_id = row["id_pncp"]
    
    for method in method_cols:
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
        # Obter o ranking se a resposta estiver na lista (1-indexado) ou None
        ranking_position = None
        for i, ref_ans in enumerate(ref_top_list):
            if method_answer.strip().upper() == ref_ans.strip().upper():
                ranking_position = i + 1
                break
        final_score = simplified_score_answer(method_answer, expected_type, ref_top_list)
        entry = {
            "id_pncp": record_id,
            "method": method,
            "method_answer": method_answer,
            "expected_type": expected_type,
            "ranking_position": ranking_position,
            "final_score": final_score
        }
        intermediate_results.append(entry)
    return intermediate_results

def process_all_rows(df: pd.DataFrame, method_cols: list, top_cols: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa todos os registros:
     - Cria um DataFrame final (wide) com a pontuação final de cada método por registro.
     - Cria um DataFrame intermediário (long) com os detalhes de cada cálculo.
    """
    final_scores_list = []
    intermediate_list = []
    for idx, row in df.iterrows():
        record_id = row["id_pncp"]
        row_final = {"id_pncp": record_id}
        row_intermediate = process_row_intermediate(row, method_cols, top_cols)
        for entry in row_intermediate:
            method = entry["method"]
            row_final[f"Score_{method}"] = entry["final_score"]
        final_scores_list.append(row_final)
        intermediate_list.extend(row_intermediate)
    df_final = pd.DataFrame(final_scores_list)
    df_intermediate = pd.DataFrame(intermediate_list)
    return df_final, df_intermediate

def main():
    logging.info(f"Lendo planilha: {INPUT_FILE}")
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        logging.error(f"Erro ao ler a planilha: {e}")
        return
    logging.info(f"Planilha lida com {len(df)} registros.")

    # Processa todos os registros para obter o resumo final e os detalhes intermediários
    df_final, df_intermediate = process_all_rows(df, METHOD_COLS, TOP_COLS)
    logging.info("Pontuação simplificada calculada para todos os registros.")

    # Estatísticas (médias) para cada método (opcional)
    summary = {}
    for method in METHOD_COLS:
        col = f"Score_{method}"
        summary[col] = df_final[col].mean()
    logging.info("Médias dos scores por método:")
    logging.info(summary)

    # Grava os resultados em duas novas abas na mesma planilha:
    # "NOTAS_METODOLOGIAS" para o resumo final e "INTERMEDIARIO" para os detalhes do cálculo.
    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
            df_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)
        logging.info(f"Resultados gravados nas abas 'NOTAS_METODOLOGIAS' e 'INTERMEDIARIO' da planilha {OUTPUT_FILE}")
    except Exception as e:
        logging.error(f"Erro ao gravar as novas abas: {e}")

if __name__ == '__main__':
    main()
