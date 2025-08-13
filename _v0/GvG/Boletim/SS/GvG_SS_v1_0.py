#### GvG Similarity Search (GvG_SS) v1 - Com detalhes completos da contratação

import os
import pandas as pd
import numpy as np
import pickle
import faiss
import sqlite3
from openai import OpenAI
import math
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
import time
import locale

# Configurar locale para formatação de valores em reais
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
EMBEDDINGS_PATH = BASE_PATH + "GvG\\EG\\EMBEDDINGS\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"

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
    {"modelo": "text-embedding-ada-002", "dimensoes": 1536},
    {"modelo": "text-similarity-ada-001", "dimensoes": 1024},
    {"modelo": "text-similarity-babbage-001", "dimensoes": 2048},
    {"modelo": "text-similarity-curie-001", "dimensoes": 4096},
]

# Inicializar NLTK
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

def get_embedding_dimension(model_name):
    """Retorna a dimensão do modelo de embedding selecionado."""
    for model in embedding_models:
        if model["modelo"] == model_name:
            return model["dimensoes"]
    return 1536  # Dimensão padrão se o modelo não for encontrado

def selecionar_modelo():
    """Permite ao usuário selecionar o modelo de embedding a ser usado."""
    console.print("[bold magenta]SELEÇÃO DE MODELO DE EMBEDDING[/bold magenta]")
    console.print("\nModelos disponíveis:")
    
    for i, model in enumerate(embedding_models, 1):
        console.print(f"{i}. {model['modelo']} ({model['dimensoes']} dimensões)")
    
    default_index = 0  # text-embedding-3-large como padrão
    choice = input(f"\nEscolha o modelo (1-{len(embedding_models)}) [padrão: 1]: ")
    
    try:
        if choice.strip():
            idx = int(choice) - 1
            if 0 <= idx < len(embedding_models):
                return embedding_models[idx]["modelo"]
        # Se a escolha for inválida ou vazia, usar o modelo padrão
        return embedding_models[default_index]["modelo"]
    except ValueError:
        console.print("[yellow]Escolha inválida, usando o modelo padrão.[/yellow]")
        return embedding_models[default_index]["modelo"]

def preprocess_text(text):
    """Normaliza e limpa o texto para processamento."""
    text = unidecode.unidecode(str(text))
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

def get_embedding(text, model):
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
                model=model,
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

def load_embeddings(modelo):
    """Carrega os embeddings do modelo especificado."""
    filepath = EMBEDDINGS_PATH + f"GvG_embeddings_{modelo}.pkl"
    console.print(f"[bold cyan]Carregando embeddings do modelo {modelo}...[/bold cyan]")
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings_dict = pickle.load(f)
            console.print(f"[green]Carregados {len(embeddings_dict)} embeddings.[/green]")
            return embeddings_dict
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
            return None
    else:
        console.print(f"[bold red]Arquivo de embeddings não encontrado: {filepath}[/bold red]")
        return None

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

def get_contratacao_details(numero_controle_pncp):
    """Busca os detalhes completos de uma contratação pelo seu número de controle."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = f"SELECT * FROM vw_contratacoes WHERE numeroControlePNCP = ?"
        df = pd.read_sql_query(query, conn, params=(numero_controle_pncp,))
        conn.close()
        
        if not df.empty:
            return df.iloc[0].to_dict()
        else:
            console.print(f"[yellow]Contratação não encontrada: {numero_controle_pncp}[/yellow]")
            return None
    except Exception as e:
        console.print(f"[bold red]Erro ao buscar detalhes da contratação: {str(e)}[/bold red]")
        return None

def search_similar_items(query_text, embedding_model, embeddings_dict, faiss_index, keys, top_n=TOP_N):
    """Busca itens similares à consulta usando FAISS e recupera detalhes do banco de dados."""
    # Processar texto da consulta
    processed_query = preprocess_text(query_text)
    console.print(f"[cyan]Texto processado: {processed_query}[/cyan]")
    
    # Gerar embedding da consulta
    try:
        query_embedding = get_embedding(processed_query, embedding_model)
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
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Buscando detalhes das contratações..."),
        BarColumn(),
        TaskProgressColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Processando", total=len(indices[0]))
        
        for i, (score, idx) in enumerate(zip(distances[0], indices[0])):
            # Obter a chave correspondente
            key = keys[idx]
            
            # Calcular similaridade a partir da distância
            similarity = float(score)  # A distância já é o produto interno normalizado (similaridade de cosseno)
            
            # Buscar detalhes completos no banco de dados
            details = get_contratacao_details(key)
            
            results.append({
                "rank": i+1,
                "id": key,
                "similarity": similarity,
                "details": details
            })
            
            progress.update(task, advance=1)
    
    # Calcular confiança geral na classificação
    confidence = calculate_confidence(scores)
    
    return results, confidence

def format_currency(value):
    """Formata um valor como moeda brasileira."""
    try:
        if pd.isna(value):
            return "N/A"
        return locale.currency(float(value), grouping=True, symbol=True)
    except:
        return str(value)

def highlight_key_terms(text, query_terms, max_length=500):
    """Destaca termos da consulta no texto e limita o comprimento."""
    if not text:
        return "N/A"
        
    # Limitar comprimento se for muito longo
    if len(text) > max_length:
        text = text[:max_length] + "..."
        
    # Substituir :: por quebras de linha para melhorar legibilidade
    text = text.replace(" :: ", "\n• ")
    if not text.startswith("•"):
        text = "• " + text
        
    return text

def display_results(results, confidence, query):
    """Exibe os resultados da busca em formato detalhado com informações completas."""
    if not results:
        console.print("\n[bold yellow]Nenhum resultado encontrado para esta consulta.[/bold yellow]")
        return
        
    console.print(f"\n[bold green]Resultados para a consulta: [italic]\"{query}\"[/italic][/bold green]")
    console.print(f"[bold cyan]Índice de confiança: {confidence:.2f}%[/bold cyan]\n")
    
    query_terms = set(preprocess_text(query).split())
    
    # Primeiro, mostrar uma tabela resumida
    table = Table(title="Resumo dos Resultados", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=6, justify="center")
    table.add_column("ID da Contratação", style="cyan")
    table.add_column("Similaridade", justify="right", width=12)
    table.add_column("Valor (R$)", justify="right", width=16)
    table.add_column("Data Encerramento", width=12)
    
    for result in results:
        details = result.get("details", {})
        
        # Formatar valor
        valor = format_currency(details.get("valorTotalHomologado", 0)) if details else "N/A"
        
        # Formatar data
        data_encerramento = details.get("dataEncerramentoProposta", "N/A") if details else "N/A"
        
        table.add_row(
            f"{result['rank']}", 
            f"{result['id']}", 
            f"{result['similarity']:.4f}",
            valor,
            data_encerramento
        )
    
    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    
    # Depois, mostrar detalhes de cada resultado
    for result in results:
        details = result.get("details", {})
        
        if not details:
            continue
            
        # Preparar o texto da descrição com destaque
        descricao = highlight_key_terms(
            details.get("descricaoCompleta", "N/A"),
            query_terms
        )
        
        # Criar painel com informações detalhadas
        panel_title = f"#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})"
        
        content = [
            f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoEntidade_razaosocial', 'N/A')}",
            f"[bold cyan]Unidade:[/bold cyan] {details.get('unidadeOrgao_nomeUnidade', 'N/A')}",
            f"[bold cyan]Local:[/bold cyan] {details.get('unidadeOrgao_municipioNome', 'N/A')}/{details.get('unidadeOrgao_ufSigla', 'N/A')}",
            f"[bold cyan]Valor:[/bold cyan] {format_currency(details.get('valorTotalHomologado', 0))}",
            f"[bold cyan]Datas:[/bold cyan] Abertura: {details.get('dataAberturaProposta', 'N/A')} | Encerramento: {details.get('dataEncerramentoProposta', 'N/A')}",
            f"[bold cyan]Descrição:[/bold cyan]\n{descricao}"
        ]
        
        panel = Panel(
            "\n".join(content),
            title=panel_title,
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print(panel)

def main():
    console.print("[bold magenta]SISTEMA DE BUSCA POR SIMILARIDADE DE CONTRATAÇÕES[/bold magenta]")
    console.print("[bold cyan]Baseado em OpenAI Embeddings com detalhes completos[/bold cyan]\n")
    
    # Selecionar modelo
    embedding_model = selecionar_modelo()
    dimension = get_embedding_dimension(embedding_model)
    
    # Carregar embeddings
    embeddings_dict = load_embeddings(embedding_model)
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
        
        # Buscar itens similares
        try:
            start_time = time.time()
            results, confidence = search_similar_items(
                query, 
                embedding_model, 
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