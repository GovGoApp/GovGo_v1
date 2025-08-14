#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_model_comparative.py – Script para execução comparativa dos métodos de embeddings

Este código utiliza o módulo unificado (emb_nv2_unified_v0.py) para processar automaticamente
o arquivo TESTE_SIMPLES.xlsx utilizando, para cada provider, todos os modelos especificados. Em seguida,
usa (como modelo) as funções de pontuação do score_answer_v3 (incorporadas neste script)
para gerar uma planilha comparativa com as abas "Respostas", "NOTAS_METODOLOGIAS" e "INTERMEDIARIO".
"""

import os
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Importar rich para console padronizado
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Importa funções e constantes do módulo unificado
from emb_nv2_unified_v0 import (
    load_data, prepare_catalog_entries, get_embeddings, 
    classify_items_batched, INPUT_FILE, INPUT_SHEET, GABARITO_FILE, GABARITO_SHEET, BATCH_SIZE,
    save_embeddings, load_embeddings, EMBEDDING_PATH  # Adicione estas importações
)

# Inicializa o console para exibição padronizada
console = Console()


# Definição dos modelos por provider (conforme solicitado)
providers_models = {
    #"openai": ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
    #"sentence_transformers": ["paraphrase-multilingual-MiniLM-L12-v2", "paraphrase-multilingual-mpnet-base-v2"],
    #"lm_studio": ["text-embedding-nomic-embed-text-v1.5", "text-embedding-granite-embedding-278m-multilingual", "text-embedding-granite-embedding-107m-multilingual"],
    "ollama": [ "llama3.2"], #["mxbai-embed-large", "bge-m3"],
    # Para os novos métodos, mantemos modelo único (pode ser ampliado se necessário)
    #"hugging_face": ["intfloat/multilingual-e5-large"],
    #"github": ["microsoft/mdeberta-v3-base"],
    #"cohere": ["embed-english-v2.0", "embed-multilingual-v2.0"],
    #"text_sage_multilingual": ["text-sage-embedding-multilingual-1"],
    #"spacy": ["pt_core_news_md"]
}

def comparing_progress(text, total):
    """Cria uma barra de progresso padronizada para todos os providers.
    
    Args:
        provider_name: Nome do provider para exibição
        total: Número total de batches/itens para processar
        
    Returns:
        Objeto Progress configurado
    """
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]{text}..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )


# Dicionário para armazenar as respostas de cada combinação provider_model
results_dict = {}

# Carrega os dados e os catálogos (única vez)

df_items, catmat, catser, _, _ = load_data()
catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)


# Total de combinações para a barra de progresso
total_combos = sum(len(models) for models in providers_models.values())

# Itera sobre cada provider e cada modelo com barra de progresso padronizada
    
for provider, models in providers_models.items():
    for model in models:
        combo_name = f"{provider}_{model}"
        # Definir caminhos para cache de embeddings
        model_safe_name = model.replace("/", "_").replace("-", "_").replace(".", "_").lower()
        provider_safe_name = provider.lower()
        catmat_embed_file = os.path.join(EMBEDDING_PATH, f"catmat_{provider_safe_name}_{model_safe_name}.pkl")
        catser_embed_file = os.path.join(EMBEDDING_PATH, f"catser_{provider_safe_name}_{model_safe_name}.pkl")
        
        console.print(f"\n[bold green]Processando: {provider_safe_name}_{model_safe_name}[/bold green]")
        try:
            # Tentar carregar embeddings CATMAT do cache
            catmat_embeds = load_embeddings(catmat_embed_file)
            if catmat_embeds is None or len(catmat_embeds) != len(catmat_texts):
                console.print(f"[yellow]Embeddings CATMAT para {combo_name} não encontrados. Gerando novos...[/yellow]")
                with comparing_progress(f"CATMAT", len(catmat_texts)) as progress:
                    task = progress.add_task("", total=len(catmat_texts))
                    catmat_embeds = get_embeddings(catmat_texts, method=provider, model=model, show_progress=False)
                    progress.update(task, completed=len(catmat_texts))
                # Salvar para uso futuro
                save_embeddings(catmat_embeds, catmat_embed_file)
            else:
                console.print(f"[green]Embeddings CATMAT para {combo_name} carregados do cache.[/green]")
            
            # Tentar carregar embeddings CATSER do cache
            catser_embeds = load_embeddings(catser_embed_file)
            if catser_embeds is None or len(catser_embeds) != len(catser_texts):
                console.print(f"[yellow]Embeddings CATSER para {combo_name} não encontrados. Gerando novos...[/yellow]")
                with comparing_progress(f"CATSER", len(catser_texts)) as progress:
                    task = progress.add_task("", total=len(catser_texts))
                    catser_embeds = get_embeddings(catser_texts, method=provider, model=model, show_progress=False)
                    progress.update(task, completed=len(catser_texts))
                # Salvar para uso futuro
                save_embeddings(catser_embeds, catser_embed_file)
            else:
                console.print(f"[green]Embeddings CATSER para {combo_name} carregados do cache.[/green]")
                
            # O restante do código permanece igual
            with comparing_progress(f"ITENS", len(df_items)) as progress:
                task = progress.add_task("", total=len(df_items))
                df_results = classify_items_batched(df_items, catmat_embeds, catmat_meta, catser_embeds, catser_meta,
                                               lambda texts: get_embeddings(texts, method=provider, model=model, show_progress=False))
                progress.update(task, completed=len(df_items))

            # Armazena a coluna "answer" resultante
            results_dict[combo_name] = df_results["answer"]
            console.print(f"[bold green]{combo_name} concluído com {len(df_results)} respostas.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Erro em {combo_name}: {str(e)}[/bold red]")
            results_dict[combo_name] = pd.Series([""] * len(df_items))

# Adicionar após recarregar a planilha original

# Recarrega a planilha original completa
console.print("[bold magenta]Gerando planilha comparativa...[/bold magenta]")
df_full = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)

# Adiciona uma coluna para cada combinação com o nome "Resposta_<provider>_<modelo>"
for combo, series in results_dict.items():
    df_full[f"Resposta_{combo}"] = series

# Carregar o gabarito com as respostas esperadas
console.print(f"[bold cyan]Carregando gabarito de {GABARITO_FILE}...[/bold cyan]")
try:
    # Carregar o gabarito com a estrutura correta:
    # id_pncp, tipoDetectado, TOP_1 até TOP_10
    df_gabarito = pd.read_excel(GABARITO_FILE, sheet_name=GABARITO_SHEET)
    
    # Converter id_pncp para string em ambos os dataframes para garantir correspondência
    if "id_pncp" in df_gabarito.columns and "id_pncp" in df_full.columns:
        df_gabarito["id_pncp"] = df_gabarito["id_pncp"].astype(str)
        df_full["id_pncp"] = df_full["id_pncp"].astype(str)
        
        # Lista explícita das colunas do gabarito
        gabarito_cols = ["id_pncp", "tipoDetectado"]
        # Adicionar todas as colunas TOP_1 a TOP_10
        for i in range(1, 11):
            col = f"TOP_{i}"
            if col in df_gabarito.columns:
                gabarito_cols.append(col)
        
        # Mesclar com o gabarito usando id_pncp
        df_full = pd.merge(
            df_full, 
            df_gabarito[gabarito_cols],
            on="id_pncp", 
            how="left"
        )
        
        # Verificar se a mesclagem foi bem-sucedida
        matched_count = df_full["tipoDetectado"].notna().sum()
        console.print(f"[green]Gabarito mesclado com sucesso - {matched_count}/{len(df_full)} registros com correspondência.[/green]")
    else:
        console.print(f"[bold red]Coluna 'id_pncp' não encontrada no gabarito ou nos dados.[/bold red]")
        console.print("[yellow]Tentando usar 'id' como alternativa...[/yellow]")
        
        # Tentativa alternativa com a coluna 'id'
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
    
    # Verificar se a coluna existe e usar valor padrão caso não exista
    expected_type = row.get("tipoDetectado", "")  # Valor padrão vazio se não existir
    
    # Verificar se id_pncp existe ou usar id alternativo
    record_id = row.get("id_pncp", row.get("id", ""))
    
    # Pegar a lista de referência apenas se as colunas existirem
    ref_top_list = [str(row.get(col, "")) for col in top_cols if col in row.index and pd.notnull(row.get(col))]
    
    for method in method_cols:
        if method not in row.index:
            continue  # Pular se o método não existir
        
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
    
    # Usar barra de progresso padronizada para processamento de linhas
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

# Definição dos nomes de colunas para pontuação
# Aqui, os métodos são as colunas de resposta que foram adicionadas
method_cols = [col for col in df_full.columns if col.startswith("Resposta_")]
# As colunas de referência (TOP_1 a TOP_10) serão as que estão na planilha original (supondo que já existam)
top_cols = [f"TOP_{i}" for i in range(1, 11)]

console.print("[bold cyan]Processando pontuações...[/bold cyan]")
# Processa a pontuação para todas as linhas
df_scores_final, df_scores_intermediate = process_all_rows(df_full, method_cols, top_cols)

# Gera o output comparativo
# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

OUTPUT_FILE = os.path.join(os.path.dirname(INPUT_FILE), f"COMPARATIVO_METODOS_{TIMESTAMP}.xlsx")
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    df_full.to_excel(writer, sheet_name="Respostas", index=False)
    df_scores_final.to_excel(writer, sheet_name="NOTAS_METODOLOGIAS", index=False)
    df_scores_intermediate.to_excel(writer, sheet_name="INTERMEDIARIO", index=False)

console.print(f"[bold green]Comparativo salvo em {OUTPUT_FILE}[/bold green]")