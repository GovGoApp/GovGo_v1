#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_model_comparative.py – Script para execução comparativa dos métodos de embeddings

Este código utiliza o módulo unificado (emb_nv2_unified_v0.py) para processar automaticamente
o arquivo TESTE_SIMPLES.xlsx utilizando, para cada provider, todos os modelos especificados. Em seguida,
usa (como modelo) as funções de pontuação do score_answer_v3 (incorporadas neste script)
para gerar uma planilha comparativa com as abas “Respostas”, “NOTAS_METODOLOGIAS” e “INTERMEDIARIO”.
"""

import os
import pandas as pd
import numpy as np
import time
import logging

# Importa funções e constantes do módulo unificado
from emb_nv2_unified_v0 import load_data, prepare_catalog_entries, get_embeddings, classify_items_batched, EXCEL_FILE, SHEET, BATCH_SIZE

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Definição dos modelos por provider (conforme solicitado)
providers_models = {
    "openai": ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
    "sentence_transformers": ["paraphrase-multilingual-MiniLM-L12-v2", "paraphrase-multilingual-mpnet-base-v2"],
    "lm_studio": ["text-embedding-nomic-embed-text-v1.5", "text-embedding-granite-embedding-278m-multilingual", "text-embedding-granite-embedding-107m-multilingual"],
    "ollama": ["mxbai-embed-large", "bge-m3"],
    # Para os novos métodos, mantemos modelo único (pode ser ampliado se necessário)
    #"hugging_face": ["sentence-transformers/paraphrase-mpnet-base-v2"],
    #"github": ["sentence-transformers/all-MiniLM-L6-v2"],
    #"spacy": ["pt_core_news_md"]
}

# Dicionário para armazenar as respostas de cada combinação provider_model
results_dict = {}

# Carrega os dados e os catálogos (única vez)
df_items, catmat, catser, _, _ = load_data()
catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)

# Itera sobre cada provider e cada modelo
for provider, models in providers_models.items():
    for model in models:
        combo_name = f"{provider}_{model}"
        logger.info(f"Processando: {combo_name}")
        try:
            # Gera os embeddings dos catálogos com o método/modelo atual
            catmat_embeds = get_embeddings(catmat_texts, method=provider, model=model)
            catser_embeds = get_embeddings(catser_texts, method=provider, model=model)
            # Executa a classificação dos itens – a função classify_items_batched utiliza uma função lambda para obter embeddings dos itens
            df_results = classify_items_batched(df_items, catmat_embeds, catmat_meta, catser_embeds, catser_meta,
                                                lambda texts: get_embeddings(texts, method=provider, model=model))
            # Armazena a coluna "answer" resultante
            results_dict[combo_name] = df_results["answer"]
            logger.info(f"{combo_name} concluído com {len(df_results)} respostas.")
        except Exception as e:
            logger.error(f"Erro em {combo_name}: {e}")
            results_dict[combo_name] = pd.Series([""] * len(df_items))

# Recarrega a planilha original completa
df_full = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
# Adiciona uma coluna para cada combinação com o nome "Resposta_<provider>_<modelo>"
for combo, series in results_dict.items():
    df_full[f"Resposta_{combo}"] = series

# =============================================================================
# FUNÇÕES DE PONTUAÇÃO (modelo score_answer_v3 incorporado)
# =============================================================================
def simplified_score_answer(method_answer: str, expected_type: str, ref_top_list: list) -> int:
    score = 0
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if not parts:
        return 0
    method_type = parts[0].upper()
    expected = expected_type.upper()
    if method_type == expected:
        score += 1
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        if len(parts) == len(ref_parts):
            score += 1
    ranking_position = None
    for i, ref_ans in enumerate(ref_top_list):
        if method_answer.strip().upper() == ref_ans.strip().upper():
            ranking_position = i + 1
            break
    if ranking_position is not None:
        score += 1
        if ranking_position <= 5:
            score += 1
        if ranking_position == 1:
            score += 1
    return min(score, 5)

def process_row_intermediate(row: pd.Series, method_cols: list, top_cols: list) -> list:
    intermediate_results = []
    expected_type = row["tipoDetectado"]
    ref_top_list = [str(row[col]) for col in top_cols if pd.notnull(row[col])]
    record_id = row["id_pncp"]
    for method in method_cols:
        method_answer = str(row[method]) if pd.notnull(row[method]) else ""
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
    final_scores_list = []
    intermediate_list = []
    for idx, row in df.iterrows():
        record_id = row["id_pncp"]
        row_final = {"id_pncp": record_id}
        row_intermediate = process_row_intermediate(row, method_cols, top_cols)
        for entry in row_intermediate:
            m = entry["method"]
            row_final[f"Score_{m}"] = entry["final_score"]
        final_scores_list.append(row_final)
        intermediate_list.extend(row_intermediate)
    df_final = pd.DataFrame(final_scores_list)
    df_intermediate = pd.DataFrame(intermediate_list)
    return df_final, df_intermediate

# Definição dos nomes de colunas para pontuação
# Aqui, os métodos são as colunas de resposta que foram adicionadas
method_cols = [col for col in df_full.columns if col.startswith("Resposta_")]
# As colunas de referência (TOP_1 a TOP_10) serão as que estão na planilha original (supondo que já existam)
top_cols = [f"TOP_{i}" for i in range(1, 11)]

# Processa a pontuação para todas as linhas
df_scores_final, df_scores_intermediate = process_all_rows(df_full, method_cols, top_cols)

# Gera o output comparativo
output_comparativo = os.path.join(os.path.dirname(EXCEL_FILE), "COMPARATIVO_METODOS_v6_output.xlsx")
with pd.ExcelWriter(output_comparativo, engine="openpyxl") as writer:
    df_full.to_excel(writer, sheet_name="Respostas", index=False)
    df_scores_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
    df_scores_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)

logger.info(f"Comparativo salvo em {output_comparativo}")
