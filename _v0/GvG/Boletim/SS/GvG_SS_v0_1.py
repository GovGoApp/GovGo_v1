#### GvG Similarity Search (GvG_SS) v0.2
## Versão integrada com módulo GvG_PP_v0 ##

import os
import pandas as pd
import numpy as np
import pickle
import faiss
from openai import OpenAI
import math
import re
import sys
import glob
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn

# Adicionar caminho para encontrar o módulo GvG_PP_v0
sys.path.append("C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\#GOvGO\\python\\GvG\\Boletim\\PP\\")


# Importar funções do módulo de pré-processamento
from GvG_PP_v0 import (
    gvg_pre_processing,
    gvg_parse_embedding_filename
)



# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\"

# Constantes para busca
TOP_N = 10  # Número de resultados a serem retornados

# Console para exibição formatada
console = Console()

# Cliente OpenAI
client = OpenAI(api_key="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")

# Modelos de embedding disponíveis e suas dimensões
embedding_models = [
    {"modelo": "text-embedding-3-large", "dimensoes": 3072},
    {"modelo": "text-embedding-3-small", "dimensoes": 1536},
    {"modelo": "text-embedding-ada-002", "dimensoes": 1536}
]

def get_embedding_dimension(model_name):
    """Retorna a dimensão do modelo de embedding selecionado."""
    for model in embedding_models:
        if model["modelo"] == model_name:
            return model["dimensoes"]
    return 1536  # Dimensão padrão se o modelo não for encontrado

def list_available_embeddings():
    """Lista todos os arquivos de embeddings disponíveis no diretório."""
    embedding_files = glob.glob(os.path.join(EMBEDDINGS_PATH, "GvG_embeddings_*.pkl"))
    
    if not embedding_files:
        console.print("[yellow]Nenhum arquivo de embedding encontrado no diretório.[/yellow]")
        return []
    
    # Analisar cada arquivo e extrair informações
    available_embeddings = []
    
    for file_path in embedding_files:
        try:
            model_name, model_index, preproc_options = gvg_parse_embedding_filename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Tamanho em MB
            
            available_embeddings.append({
                "path": file_path,
                "model_name": model_name,
                "model_index": model_index,
                "preproc_options": preproc_options,
                "size_mb": file_size
            })
        except Exception as e:
            console.print(f"[yellow]Erro ao analisar arquivo {os.path.basename(file_path)}: {str(e)}[/yellow]")
    
    return available_embeddings

def display_available_embeddings(embeddings_list):
    """Exibe os embeddings disponíveis em uma tabela formatada."""
    if not embeddings_list:
        return
    
    console.print("\n[bold magenta]Arquivos de Embedding Disponíveis[/bold magenta]")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Modelo", style="green")
    table.add_column("Índice", style="cyan", width=6)
    table.add_column("Configuração de Pré-processamento", style="magenta")
    table.add_column("Tamanho", style="yellow", width=10)
    
    for i, emb in enumerate(embeddings_list, 1):
        # Criar descrição da configuração de pré-processamento
        pp_config = [
            "Remover acentos" if emb["preproc_options"]["remove_accents"] else "Manter acentos",
            "Remover caracteres especiais" if emb["preproc_options"]["remove_special_chars"] else "Manter caracteres especiais",
            "Manter separadores" if emb["preproc_options"]["keep_separators"] else "Remover separadores",
            f"Case: {emb['preproc_options']['case']}",
            "Remover stopwords" if emb["preproc_options"]["remove_stopwords"] else "Manter stopwords",
            "Aplicar lematização" if emb["preproc_options"]["lemmatize"] else "Sem lematização"
        ]
        
        pp_text = ", ".join([f"{item}" for item in pp_config])
        
        table.add_row(
            str(i),
            emb["model_name"],
            str(emb["model_index"]),
            pp_text,
            f"{emb['size_mb']:.2f} MB"
        )
    
    console.print(table)

def selecionar_embedding_arquivo():
    """Permite ao usuário selecionar um arquivo de embedding disponível."""
    embeddings_list = list_available_embeddings()
    
    if not embeddings_list:
        console.print("[bold red]Nenhum arquivo de embedding encontrado. Encerrando.[/bold red]")
        return None
    
    display_available_embeddings(embeddings_list)
    
    choice = input(f"\nSelecione o número do embedding a utilizar (1-{len(embeddings_list)}): ")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(embeddings_list):
            return embeddings_list[idx]
        else:
            console.print("[yellow]Escolha inválida. Selecionando o primeiro embedding.[/yellow]")
            return embeddings_list[0]
    except ValueError:
        console.print("[yellow]Entrada inválida. Selecionando o primeiro embedding.[/yellow]")
        return embeddings_list[0]

def load_embeddings(embedding_file_path):
    """Carrega os embeddings do arquivo especificado."""
    console.print(f"[bold cyan]Carregando embeddings de {os.path.basename(embedding_file_path)}...[/bold cyan]")
    
    if os.path.exists(embedding_file_path):
        try:
            with open(embedding_file_path, 'rb') as f:
                embeddings_dict = pickle.load(f)
            console.print(f"[green]Carregados {len(embeddings_dict)} embeddings.[/green]")
            return embeddings_dict
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
            return None
    else:
        console.print(f"[bold red]Arquivo de embeddings não encontrado: {embedding_file_path}[/bold red]")
        return None

def get_embedding(text, model_name):
    """Gera embedding para um único texto."""
    max_retries = 3
    retry_delay = 2
    
    # Garantir que o texto não está vazio
    if not text or not text.strip():
        text = " "
    
    # Limitar tamanho se necessário
    if len(text) > 8000:
        text = text[:8000]
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model_name,
                input=[text]
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            if attempt < max_retries - 1:
                console.print(f"[yellow]Erro ao gerar embedding: {str(e)}. Tentativa {attempt+1}/{max_retries}.[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro ao gerar embedding: {str(e)}[/bold red]")
                raise

def create_faiss_index(embeddings_dict, dimension):
    """Cria um índice FAISS para busca por similaridade."""
    console.print("[bold magenta]Criando índice FAISS para busca rápida...[/bold magenta]")
    
    # Extrair chaves e vetores
    keys = list(embeddings_dict.keys())
    vectors = list(embeddings_dict.values())
    
    # Converter para array NumPy
    vectors_array = np.array(vectors, dtype=np.float32)
    
    # Criar índice
    index = faiss.IndexFlatIP(dimension)  # Produto interno (similaridade de cosseno)
    
    # Normalizar vetores para garantir similaridade de cosseno
    faiss.normalize_L2(vectors_array)
    
    # Adicionar vetores ao índice
    index.add(vectors_array)
    
    console.print(f"[green]Índice FAISS criado com {index.ntotal} vetores.[/green]")
    return index, keys

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações."""
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

def search_similar_items(query_text, model_name, preproc_options, embeddings_dict, faiss_index, keys, top_n=TOP_N):
    """Busca itens similares à consulta usando FAISS com os mesmos parâmetros de pré-processamento do arquivo de embeddings."""
    # Processar texto da consulta com as mesmas opções que foram usadas no arquivo de embeddings
    processed_query = gvg_pre_processing(
        query_text,
        remove_special_chars=preproc_options["remove_special_chars"],
        keep_separators=preproc_options["keep_separators"],
        remove_accents=preproc_options["remove_accents"],
        case=preproc_options["case"],
        remove_stopwords=preproc_options["remove_stopwords"],
        lemmatize=preproc_options["lemmatize"]
    )
    
    console.print(f"[cyan]Texto processado: {processed_query}[/cyan]")
    
    # Gerar embedding da consulta
    try:
        query_embedding = get_embedding(processed_query, model_name)
    except Exception as e:
        console.print(f"[bold red]Falha ao gerar embedding da consulta: {str(e)}[/bold red]")
        return [], 0.0
    
    # Converter para float32 e normalizar
    query_embedding = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_embedding)
    
    # Realizar busca
    distances, indices = faiss_index.search(query_embedding, top_n)
    
    # Processar resultados
    results = []
    scores = distances[0].tolist()  # Extrair scores para cálculo de confiança
    
    for i, (score, idx) in enumerate(zip(distances[0], indices[0])):
        # Obter a chave correspondente
        key = keys[idx]
        
        # Calcular similaridade a partir da distância
        similarity = float(score)  # A distância já é o produto interno normalizado (similaridade de cosseno)
        
        results.append({
            "rank": i+1,
            "id": key,
            "similarity": similarity,
        })
    
    # Calcular confiança geral na classificação
    confidence = calculate_confidence(scores)
    
    return results, confidence

def display_results(results, confidence, query):
    """Exibe os resultados da busca em formato tabular."""
    console.print(f"\n[bold green]Resultados para a consulta: [italic]\"{query}\"[/italic][/bold green]")
    console.print(f"[bold cyan]Índice de confiança: {confidence:.2f}%[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6)
    table.add_column("ID", style="cyan")
    table.add_column("Similaridade", justify="right", width=12)
    
    for result in results:
        table.add_row(
            f"{result['rank']}", 
            f"{result['id']}", 
            f"{result['similarity']:.4f}"
        )
    
    console.print(table)

def display_embedding_info(embedding_info):
    """Exibe informações detalhadas sobre o embedding selecionado."""
    console.print(Panel(
        f"[bold cyan]Modelo:[/bold cyan] {embedding_info['model_name']} (índice: {embedding_info['model_index']})\n"
        f"[bold cyan]Arquivo:[/bold cyan] {os.path.basename(embedding_info['path'])}\n"
        f"[bold cyan]Tamanho:[/bold cyan] {embedding_info['size_mb']:.2f} MB\n"
        f"[bold cyan]Configuração de pré-processamento:[/bold cyan]\n"
        f"  • Remover acentos: {embedding_info['preproc_options']['remove_accents']}\n"
        f"  • Remover caracteres especiais: {embedding_info['preproc_options']['remove_special_chars']}\n"
        f"  • Manter separadores: {embedding_info['preproc_options']['keep_separators']}\n"
        f"  • Case: {embedding_info['preproc_options']['case']}\n"
        f"  • Remover stopwords: {embedding_info['preproc_options']['remove_stopwords']}\n"
        f"  • Aplicar lematização: {embedding_info['preproc_options']['lemmatize']}",
        title="[bold magenta]Informações do Embedding[/bold magenta]",
        expand=False
    ))

def main():
    console.print(Panel(
        "[bold cyan]Baseado em OpenAI Embeddings com processamento adaptado[/bold cyan]",
        title="[bold magenta]SISTEMA DE BUSCA POR SIMILARIDADE DE CONTRATAÇÕES v0.2[/bold magenta]",
        expand=False
    ))
    
    # Selecionar arquivo de embedding
    embedding_info = selecionar_embedding_arquivo()
    if not embedding_info:
        return
    
    # Exibir informações detalhadas do embedding selecionado
    display_embedding_info(embedding_info)
    
    # Obter modelo e parâmetros de pré-processamento
    model_name = embedding_info["model_name"]
    model_index = embedding_info["model_index"]
    preproc_options = embedding_info["preproc_options"]
    dimension = get_embedding_dimension(model_name)
    
    # Carregar embeddings
    embeddings_dict = load_embeddings(embedding_info["path"])
    if not embeddings_dict:
        console.print("[bold red]Não foi possível carregar os embeddings. Encerrando.[/bold red]")
        return
    
    # Criar índice FAISS
    faiss_index, keys = create_faiss_index(embeddings_dict, dimension)
    
    # Loop de consulta
    while True:
        console.print("\n[bold magenta]" + "="*80 + "[/bold magenta]")
        query = input("\nDigite sua consulta (ou 'sair' para encerrar): ")
        
        if query.lower() in ['sair', 'exit', 'quit', 'q']:
            break
        
        if not query.strip():
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
        
        console.print(f"\n[bold magenta]Processando consulta: \"{query}\"[/bold magenta]")
        
        # Buscar itens similares usando os mesmos parâmetros de pré-processamento do arquivo de embeddings
        try:
            start_time = time.time()
            results, confidence = search_similar_items(
                query, 
                model_name, 
                preproc_options,
                embeddings_dict, 
                faiss_index, 
                keys
            )
            end_time = time.time()
            
            # Exibir resultados
            display_results(results, confidence, query)
            console.print(f"[dim]Tempo de busca: {(end_time - start_time):.4f} segundos[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]Erro durante a busca: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
    
    console.print("\n[bold green]Obrigado por usar o sistema de busca![/bold green]")

if __name__ == "__main__":
    main()