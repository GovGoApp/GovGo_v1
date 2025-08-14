#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MultiModelEvaluation.py
-------------------------
Este script lê o arquivo de teste (TESTE_SIMPLES.xlsx) e executa a classificação para
cada um dos métodos de embedding definidos. Em seguida, utiliza uma função de “score”
(similar ao score_answer_v3) para comparar a resposta do método com os valores de referência
(assumindo que as colunas TOP_1 a TOP_10 estejam presentes) e grava os resultados na aba
"NOTAS_METODOLOGIAS" do arquivo de saída.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Importa as funções de classificação do módulo unificado
from UnifiedEmbeddingClassifier import classify_items, load_items

console = Console()

# Configurações de caminhos e arquivos
BASE_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\\"
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO")
INPUT_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
OUTPUT_FILE = os.path.join(CLASS_PATH, f"MULTI_EVALUATION_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
SHEET_INPUT = "OBJETOS"  # folha com os dados de teste

# Definição dos métodos e os novos nomes para as colunas de resposta
METODOS = {
    "openai": "Embedding_OpenAI_Large",
    "sentence_transformers": "Embedding_SentenceTransformers",
    "lm_studio": "Embedding_LMStudio",
    "ollama": "Embedding_Ollama",
    "hf_transformers": "Embedding_HFTransformers",
    "spacy": "Embedding_spaCy"
}

def simplified_score_answer(method_answer: str, expected_type: str, ref_top_list: list) -> int:
    """
    Calcula uma pontuação simplificada (0 a 5) para a resposta do método.
    Critérios:
      - Se o tipo (primeira parte antes de ";") coincidir com expected_type: +1
      - Se o número de partes (separadas por ";") for igual ao da referência: +1
      - Se a resposta estiver entre os TOP_1 a TOP_10: +1
      - Se estiver entre TOP_1 a TOP_5: +1 extra
      - Se for exatamente TOP_1: +1 extra
    """
    score = 0
    parts = [p.strip() for p in method_answer.split(";") if p.strip()]
    if not parts:
        return 0
    # Tipo
    if parts[0].upper() == expected_type.upper():
        score += 1
    # Formato: compara número de partes com TOP_1 (se disponível)
    if ref_top_list and ref_top_list[0]:
        ref_parts = [p.strip() for p in ref_top_list[0].split(";") if p.strip()]
        if len(parts) == len(ref_parts):
            score += 1
    # Ranking: busca correspondência exata nos TOP_1 a TOP_10
    ranking = None
    for i, ref in enumerate(ref_top_list):
        if method_answer.strip().upper() == ref.strip().upper():
            ranking = i + 1
            break
    if ranking is not None:
        score += 1
        if ranking <= 5:
            score += 1
        if ranking == 1:
            score += 1
    return min(score, 5)

def process_evaluation(df: pd.DataFrame, metodo: str, nova_coluna: str) -> pd.DataFrame:
    """
    Executa a classificação usando o método especificado e adiciona a coluna com a resposta.
    """
    console.print(f"[bold cyan]Processando método: {metodo}[/bold cyan]")
    respostas = classify_items(df, method=metodo)
    df[nova_coluna] = respostas
    return df

def apply_scoring(df: pd.DataFrame, metodo_col: str, score_col: str) -> pd.DataFrame:
    """
    Para cada linha, compara a resposta do método com as referências (colunas TOP_1 a TOP_10)
    e calcula a pontuação, adicionando uma nova coluna de score.
    """
    scores = []
    for idx, row in df.iterrows():
        expected_type = str(row["tipoDetectado"]).strip()
        method_answer = str(row[metodo_col]) if pd.notnull(row[metodo_col]) else ""
        # Obtém as referências dos TOP_1 a TOP_10
        ref_top = [str(row.get(f"TOP_{i}")).strip() for i in range(1, 11) if pd.notnull(row.get(f"TOP_{i}"))]
        score = simplified_score_answer(method_answer, expected_type, ref_top)
        scores.append(score)
    df[score_col] = scores
    return df

def main():
    try:
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_INPUT)
        console.print(f"[green]Planilha carregada com {len(df)} registros.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar a planilha: {str(e)}[/bold red]")
        return

    # Para cada método, processa a classificação e calcula a pontuação
    for metodo, nome_col in METODOS.items():
        df = process_evaluation(df, metodo, nome_col)
        df = apply_scoring(df, nome_col, f"Score_{nome_col}")

    # Salva os resultados na aba "NOTAS_METODOLOGIAS"
    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
        console.print(f"[green]Resultados salvos em {OUTPUT_FILE}[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar o arquivo Excel: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()
