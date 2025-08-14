#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
comparative_unified_v2.py – Script para execução comparativa dos métodos de embeddings
utilizando uma nova tabela unificada de categorias (CAT).

Nesta versão a tabela CAT contém os campos CODCAT e NOMCAT e o embedding é calculado a partir da junção
destes campos (por exemplo, concatenando com um espaço). O fluxo de processamento dos itens, classificação,
merge com gabarito, pontuação e geração do comparativo permanece similar à versão original.
"""

import os
import pandas as pd
import numpy as np
import time
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Importa funções e constantes do módulo unificado de embeddings (versão adaptada)
from emb_nv2_unified_v3 import (
    load_data, prepare_catalog_entries, get_embeddings, 
    classify_items_batched, INPUT_FILE, INPUT_SHEET, GABARITO_FILE, GABARITO_SHEET, 
    save_embeddings, load_embeddings, EMBEDDING_PATH
)

console = Console()

# Define os modelos para cada provider (exemplo: utilizando apenas "ollama")
providers_models = {
    "openai": [
        {"name": "text-embedding-ada-002", "dim": 1536},
        {"name": "text-embedding-3-small", "dim": 1536},
        {"name": "text-embedding-3-large", "dim": 3072}
    ],
    "sentence_transformers": [
        {"name": "paraphrase-multilingual-MiniLM-L12-v2", "dim": 384},
        {"name": "paraphrase-multilingual-mpnet-base-v2", "dim": 768}
    ],
    "lm_studio": [
        {"name": "text-embedding-nomic-embed-text-v1.5", "dim": 768},
        {"name": "text-embedding-granite-embedding-278m-multilingual", "dim": 768},
        {"name": "text-embedding-granite-embedding-107m-multilingual", "dim": 512}
    ],
    "ollama": [
        {"name": "llama3.2", "dim": 4096},
        {"name": "bge-m3", "dim": 1024},
        {"name": "mxbai-embed-large", "dim": 1024}
    ],
    # Novos métodos:
    #"hugging_face": [{"name": "intfloat/multilingual-e5-large", "dim": 1024}],
    #"github": [{"name": "microsoft/mdeberta-v3-base", "dim": 768}],
    #"spacy": [{"name": "pt_core_news_md", "dim": 300}]
    #"cohere": [{"name": "embed-english-v2.0", "dim": 4096}],
    #langchain: [{"name": "text-embedding-ada-002", "dim": 1536}],

}

def comparing_progress(text, total):
    """Cria uma barra de progresso padrão."""
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]{text}..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )

results_dict = {}

# Carrega os dados de itens e o catálogo unificado
df_items, cat, _, _ = load_data()
cat_texts, cat_meta = prepare_catalog_entries(cat)

# Número total de combinações para a barra de progresso
total_combos = sum(len(models) for models in providers_models.values())

for provider, models in providers_models.items():
    for model_info in models:
        model_name = model_info["name"]
        model_dim = model_info["dim"]
        combo_name = f"{provider}_{model_name}"
        
        # Define o caminho para cache dos embeddings do catálogo unificado
        model_safe_name = model_name.replace("/", "_").replace("-", "_").replace(".", "_").lower()
        provider_safe_name = provider.lower()
        cat_embed_file = os.path.join(EMBEDDING_PATH, f"cat_{provider_safe_name}_{model_safe_name}.pkl")
        
        console.print(f"\n[bold green]Processando: {provider_safe_name}_{model_safe_name} (dim={model_dim})[/bold green]")
        
        try:
            # Tenta carregar os embeddings do catálogo do cache
            cat_embeds = load_embeddings(cat_embed_file)
            if cat_embeds is None or len(cat_embeds) != len(cat_texts):
                console.print(f"[yellow]Embeddings para {combo_name} não encontrados. Gerando novos...[/yellow]")
                cat_embeds = get_embeddings(
                    cat_texts, 
                    method=provider, 
                    model=model_name,
                    dim=model_dim,
                    show_progress=True
                )
                save_embeddings(cat_embeds, cat_embed_file)
            else:
                console.print(f"[green]Embeddings {combo_name} carregados do cache.[/green]")
            
            # Processa os itens utilizando os embeddings do catálogo unificado
            df_results = classify_items_batched(
                df_items, cat_embeds, cat_meta,
                lambda texts: get_embeddings(
                    texts, 
                    method=provider, 
                    model=model_name, 
                    dim=model_dim,
                    show_progress=True
                )
            )
            
            # Armazena a resposta (coluna "answer") para esta combinação provider_model
            results_dict[combo_name] = df_results["answer"]
            console.print(f"[bold green]{combo_name} concluído com {len(df_results)} respostas.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Erro em {combo_name}: {str(e)}[/bold red]")
            results_dict[combo_name] = pd.Series([""] * len(df_items))


# Recarrega a planilha original para anexar as respostas
console.print("[bold magenta]Gerando planilha comparativa...[/bold magenta]")
df_full = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)

# Adiciona, para cada combinação, uma coluna com a resposta gerada
for combo, series in results_dict.items():
    df_full[f"Resposta_{combo}"] = series

# Carrega o gabarito e faz merge com os dados
console.print(f"[bold cyan]Carregando gabarito de {GABARITO_FILE}...[/bold cyan]")
try:
    df_gabarito = pd.read_excel(GABARITO_FILE, sheet_name=GABARITO_SHEET)
    if "id_pncp" in df_gabarito.columns and "id_pncp" in df_full.columns:
        df_gabarito["id_pncp"] = df_gabarito["id_pncp"].astype(str)
        df_full["id_pncp"] = df_full["id_pncp"].astype(str)
        gabarito_cols = ["id_pncp", "tipoDetectado"]
        for i in range(1, 11):
            col = f"TOP_{i}"
            if col in df_gabarito.columns:
                gabarito_cols.append(col)
        df_full = pd.merge(
            df_full, 
            df_gabarito[gabarito_cols],
            on="id_pncp", 
            how="left"
        )
        matched_count = df_full["tipoDetectado"].notna().sum()
        console.print(f"[green]Gabarito mesclado com sucesso - {matched_count}/{len(df_full)} registros com correspondência.[/green]")
    else:
        console.print(f"[bold red]Coluna 'id_pncp' não encontrada no gabarito ou nos dados.[/bold red]")
        console.print("[yellow]Tentando usar 'id' como alternativa...[/yellow]")
        if "id" in df_gabarito.columns and "id" in df_full.columns:
            df_gabarito["id"] = df_gabarito["id"].astype(str)
            df_full["id"] = df_full["id"].astype(str)
            gabarito_cols = ["id", "tipoDetectado"] + [f"TOP_{i}" for i in range(1, 11) if f"TOP_{i}" in df_gabarito.columns]
            df_full = pd.merge(
                df_full, 
                df_gabarito[gabarito_cols],
                on="id", 
                how="left"
            )
            console.print(f"[green]Gabarito mesclado usando coluna 'id'.[/green]")
        else:
            console.print(f"[bold red]Nem 'id_pncp' nem 'id' encontrados. Não será possível usar o gabarito.[/bold red]")
except Exception as e:
    console.print(f"[bold red]Erro ao carregar gabarito: {str(e)}[/bold red]")
    console.print("[yellow]Continuando sem gabarito para pontuação. Os resultados podem não ser precisos.[/yellow]")

# =============================================================================
# FUNÇÕES DE PONTUAÇÃO (score_answer incorporado)
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
    expected_type = row.get("tipoDetectado", "")
    record_id = row.get("id_pncp", row.get("id", ""))
    ref_top_list = [str(row.get(col, "")) for col in top_cols if col in row.index and pd.notnull(row.get(col))]
    for method in method_cols:
        if method not in row.index:
            continue
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
    with comparing_progress("Pontuação de linhas", len(df)) as progress:
        task = progress.add_task("", total=len(df))
        for idx, row in df.iterrows():
            record_id = row["id_pncp"]
            row_final = {"id_pncp": record_id}
            row_intermediate = process_row_intermediate(row, method_cols, top_cols)
            for entry in row_intermediate:
                m = entry["method"]
                row_final[f"Score_{m}"] = entry["final_score"]
            final_scores_list.append(row_final)
            intermediate_list.extend(row_intermediate)
            progress.update(task, advance=1)
    df_final = pd.DataFrame(final_scores_list)
    df_intermediate = pd.DataFrame(intermediate_list)
    return df_final, df_intermediate

method_cols = [col for col in df_full.columns if col.startswith("Resposta_")]
top_cols = [f"TOP_{i}" for i in range(1, 11)]

console.print("[bold cyan]Processando pontuações...[/bold cyan]")
df_scores_final, df_scores_intermediate = process_all_rows(df_full, method_cols, top_cols)

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = os.path.join(os.path.dirname(INPUT_FILE), f"COMPARATIVO_METODOS_{TIMESTAMP}.xlsx")
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    df_full.to_excel(writer, sheet_name="Respostas", index=False)
    df_scores_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
    df_scores_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)

console.print(f"[bold green]Comparativo salvo em {OUTPUT_FILE}[/bold green]")
