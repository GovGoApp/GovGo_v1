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
REPORTS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\COMPARATIVOS\\"

INPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v3.xlsx"
OUTPUT_FILE = REPORTS_PATH + "COMPARATIVO_METODOS_v3.xlsx"
 # iremos sobrescrever adicionando uma nova aba


# Lista dos nomes das colunas com as respostas dos métodos
METHOD_COLS = [
    "Fine Tuning", 
    "Assistente", 
    "Embedding -ADA_002", 
    "Embedding - Paraphrase 384", 
    "Embedding - Paraphrase 768", 
    "Embedding - Nomic",
    "Embedding - Granite",
    "Embedding - OpenAI - large - 1536"
]

# Colunas de referência de TOP e SCORE (do embedding de referência)
TOP_COLS = [f"TOP_{i}" for i in range(1, 11)]
SCORE_COLS = [f"SCORE_{i}" for i in range(1, 11)]

def breakdown_score_answer(method_answer: str, expected_type: str, ref_top_list: list, ref_score_list: list) -> dict:
    """
    Calcula e detalha a pontuação da resposta de um método para um registro.
    Critérios:
      1) Tipo: 3 pontos se a primeira parte (antes do ";") confere com expected_type.
      2) Formato: 2 pontos se o número de partes (split por ";") for igual ao número de partes da referência TOP_1.
      3) Ranking: Se a resposta for encontrada entre os TOP_1 a TOP_10, atribui uma pontuação decrescente:
         - TOP_1 vale 10, TOP_2 vale 9, ..., TOP_10 vale 1,
         multiplicado pelo fator (SCORE_i / 0.7) e arredondado para inteiro.
         Se não encontrada, 0 pontos.
    Retorna um dicionário com os seguintes campos:
      - tipo_score, formato_score, ranking_position, base_points, sim_score, ranking_score, final_score.
    """
    details = {}
    
    # 1) Tipo
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if len(parts) < 1:
        details["tipo_score"] = 0
        details["method_type"] = ""
    else:
        method_type = parts[0].upper()
        details["method_type"] = method_type
        expected = expected_type.upper()
        details["expected_type"] = expected
        details["tipo_score"] = 3 if method_type == expected else 0
    
    # 2) Formato
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        details["expected_num_parts"] = len(ref_parts)
        details["method_num_parts"] = len(parts)
        details["formato_score"] = 2 if len(parts) == len(ref_parts) else 0
    else:
        details["expected_num_parts"] = None
        details["method_num_parts"] = len(parts)
        details["formato_score"] = 0

    # 3) Ranking: Procura a resposta entre os TOP_1 a TOP_10
    ranking_position = None
    for i, ref_ans in enumerate(ref_top_list):
        if method_answer.strip().upper() == ref_ans.strip().upper():
            ranking_position = i + 1  # posição 1-indexada
            break
    details["ranking_position"] = ranking_position
    if ranking_position is not None:
        base_points = 11 - ranking_position  # TOP_1:10, TOP_2:9, ..., TOP_10:1
        details["base_points"] = base_points
        try:
            sim_score = float(ref_score_list[ranking_position - 1])
        except Exception as e:
            logger.error(f"Erro ao converter SCORE para posição {ranking_position}: {e}")
            sim_score = 0
        details["sim_score"] = sim_score
        ranking_score = int(round(base_points * (sim_score / 0.7)))
        details["ranking_score"] = ranking_score
    else:
        details["base_points"] = 0
        details["sim_score"] = 0
        details["ranking_score"] = 0

    # Soma final
    details["final_score"] = details["tipo_score"] + details["formato_score"] + details["ranking_score"]
    return details

def process_row_intermediate(row: pd.Series, method_cols: list, top_cols: list, score_cols: list) -> list:
    """
    Para uma linha (registro) da planilha, calcula a pontuação e os detalhes para cada método.
    Retorna uma lista de dicionários, cada um correspondendo a um método, contendo:
       id_pncp, método, resposta do método, expected_type,
       tipo_score, method_num_parts, expected_num_parts, formato_score,
       ranking_position, base_points, sim_score, ranking_score, final_score.
    """
    intermediate_results = []
    expected_type = row["tipoDetectado"]  # "Material" ou "Serviço"
    ref_top_list = [str(row[col]) for col in top_cols if pd.notnull(row[col])]
    ref_score_list = [row[col] for col in score_cols if pd.notnull(row[col])]
    record_id = row["id_pncp"]
    
    for method in method_cols:
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
        details = breakdown_score_answer(method_answer, expected_type, ref_top_list, ref_score_list)
        # Monta o dicionário com o passo-a-passo
        entry = {
            "id_pncp": record_id,
            "method": method,
            "method_answer": method_answer,
            "expected_type": expected_type,
            "method_type": details.get("method_type", ""),
            "tipo_score": details.get("tipo_score", 0),
            "method_num_parts": details.get("method_num_parts", 0),
            "expected_num_parts": details.get("expected_num_parts", np.nan),
            "formato_score": details.get("formato_score", 0),
            "ranking_position": details.get("ranking_position"),
            "base_points": details.get("base_points", 0),
            "sim_score": details.get("sim_score", 0),
            "ranking_score": details.get("ranking_score", 0),
            "final_score": details.get("final_score", 0)
        }
        intermediate_results.append(entry)
    return intermediate_results

def process_all_rows(df: pd.DataFrame, method_cols: list, top_cols: list, score_cols: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa todos os registros:
     - Cria um DataFrame final com as pontuações por registro (uma linha por registro, com uma coluna para cada método).
     - Cria um DataFrame intermediário (formato long) com o passo-a-passo das contas para cada método por registro.
    """
    final_scores_list = []
    intermediate_list = []
    for idx, row in df.iterrows():
        record_id = row["id_pncp"]
        row_final = {"id_pncp": record_id}
        row_intermediate = process_row_intermediate(row, method_cols, top_cols, score_cols)
        for entry in row_intermediate:
            method = entry["method"]
            row_final[f"Score_{method}"] = entry["final_score"]
        final_scores_list.append(row_final)
        intermediate_list.extend(row_intermediate)
    df_final = pd.DataFrame(final_scores_list)
    df_intermediate = pd.DataFrame(intermediate_list)
    return df_final, df_intermediate

def main():
    logger.info(f"Lendo planilha: {INPUT_FILE}")
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        logger.error(f"Erro ao ler a planilha: {e}")
        return
    logger.info(f"Planilha lida com {len(df)} registros.")

    # Processa todos os registros para obter o resumo final e os detalhes intermediários
    df_final, df_intermediate = process_all_rows(df, METHOD_COLS, TOP_COLS, SCORE_COLS)
    logger.info("Pontuação calculada para todos os registros.")

    # Calcula também estatísticas simples (médias) para cada método – opcional
    summary = {}
    for method in METHOD_COLS:
        col = f"Score_{method}"
        summary[col] = df_final[col].mean()
    logger.info("Médias dos scores por método:")
    logger.info(summary)

    # Grava os resultados em duas novas abas na mesma planilha:
    # "NOTAS_METODOLOGIAS" para o resumo final e "INTERMEDIARIO" para o detalhamento passo-a-passo.
    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
            df_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)
        logger.info(f"Resultados gravados nas abas 'NOTAS_METODOLOGIAS' e 'INTERMEDIARIO' da planilha {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Erro ao gravar as novas abas: {e}")

if __name__ == '__main__':
    main()
