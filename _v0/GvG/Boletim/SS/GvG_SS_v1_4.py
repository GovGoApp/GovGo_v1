#### GvG Similarity Search (GvG_SS) v1.1 - Com detalhes completos da contratação
## Versão integrada com módulo GvG_PP_v0 ##

import os
import sys
import pandas as pd
import numpy as np
import pickle
import faiss
import sqlite3
import glob
from openai import OpenAI
import math
import time
import locale
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn

# Adicionar caminho para encontrar o módulo GvG_PP_v0
sys.path.append("C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\#GOvGO\\python\\GvG\\Boletim\\PP\\")

# Importar funções do módulo de pré-processamento
from GvG_PP_v0 import (
    gvg_pre_processing,
    gvg_parse_embedding_filename,
    EMBEDDING_MODELS,
    EMBEDDING_MODELS_REVERSE
)

# Configurar locale para formatação de valores em reais
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
EMBEDDINGS_PATH = BASE_PATH + "GvG\\EG\\EMBEDDINGS\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"

###### PARÂMETROS CONFIGURÁVEIS ######

# Número fixo de resultados para o método de corte fixo
TOP_N = 30

# Limites para todos os métodos de corte
MIN_RESULTS = 10      # Número mínimo de resultados que serão retornados
MAX_RESULTS = 30     # Número máximo de resultados que serão retornados


# Parâmetros do método do cotovelo
ELBOW_THRESHOLD = 1.5  # Multiplicador do desvio padrão para detectar um "cotovelo"
                        # Valores maiores: mais restritivo, menos resultados
                        # Valores menores: menos restritivo, mais resultados

# Parâmetros do método de limiar de similaridade
SIMILARITY_THRESHOLD = 0.85  # Percentual do melhor score para considerar relevante
                             # Valores maiores: mais restritivo
                             # Valores menores: menos restritivo

# Parâmetros do método de análise de gap
GAP_MULTIPLIER = 2.5   # Multiplicador para detectar gaps significativos
                       # Valores maiores: mais restritivo
                       # Valores menores: menos restritivo

NOISE_FACTOR = 1.05     # Multiplicador do nível de ruído para detectar proximidade
                       # Valores maiores: menos restritivo
                       # Valores menores: mais restritivo

# Adicionar após as constantes existentes

# Parâmetros do método de corte por confiança
CONFIDENCE_THRESHOLD = 90.0  # Limiar de confiança para corte (%)
CONFIDENCE_DROP_LIMIT = 5.0  # Queda máxima permitida na confiança (%)

#################################

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

def create_faiss_index(embeddings_dict, dimension, similarity_method=0):
    """
    Cria um índice FAISS para busca por similaridade.
    
    similarity_method:
    0 - Similaridade de Cosseno (produto interno com vetores normalizados)
    1 - Distância Euclidiana (L2)
    2 - Produto Interno (sem normalização)
    """
    console.print("[bold magenta]Criando índice FAISS para busca rápida...[/bold magenta]")
    
    # Extrair chaves e vetores
    keys = list(embeddings_dict.keys())
    vectors = list(embeddings_dict.values())
    
    # Converter para array NumPy
    vectors_array = np.array(vectors, dtype=np.float32)
    
    # Criar índice baseado no método selecionado
    if similarity_method == 1:
        # Distância Euclidiana (L2)
        index = faiss.IndexFlatL2(dimension)
        console.print("[cyan]Usando método: Distância Euclidiana (L2)[/cyan]")
        # Não normalizar os vetores para distância euclidiana
    elif similarity_method == 2:
        # Produto Interno sem normalização
        index = faiss.IndexFlatIP(dimension)
        console.print("[cyan]Usando método: Produto Interno (sem normalização)[/cyan]")
        # Não normalizar os vetores
    else:
        # Similaridade de Cosseno (produto interno com normalização)
        index = faiss.IndexFlatIP(dimension)
        console.print("[cyan]Usando método: Similaridade de Cosseno[/cyan]")
        # Normalizar vetores para garantir similaridade de cosseno
        faiss.normalize_L2(vectors_array)
    
    # Adicionar vetores ao índice
    index.add(vectors_array)
    
    console.print(f"[green]Índice FAISS criado com {index.ntotal} vetores.[/green]")
    return index, keys, similarity_method

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

def search_similar_items(query_text, model_name, preproc_options, embeddings_dict, faiss_index, keys, 
                        similarity_method=0, cutoff_method=0, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """Busca itens similares à consulta usando métodos configuráveis de similaridade e corte."""
    # Processar texto da consulta
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
    
    # Converter para float32 e aplicar normalização conforme o método
    query_embedding_np = np.array([query_embedding], dtype=np.float32)
    
    # Normalizar apenas para similaridade de cosseno
    if similarity_method == 0:
        faiss.normalize_L2(query_embedding_np)
    
    # Buscar inicialmente um número maior de resultados para aplicar o corte dinâmico
    initial_n = min(MAX_RESULTS, len(keys)) # Limitar pelo número de itens disponíveis
    
    # Realizar busca inicial
    distances, indices = faiss_index.search(query_embedding_np, initial_n)
    
    # Converter scores conforme o método de similaridade
    if similarity_method == 1:
        # Para distância euclidiana, menores valores são melhores (converter para similaridade)
        similarities = [1 / (1 + float(dist)) for dist in distances[0]]
        scores = similarities  # Para cálculo de confiança
    else:
        # Para produto interno e cosseno, maiores valores são melhores
        similarities = [float(dist) for dist in distances[0]]
        scores = similarities
    
    # Determinar o número de resultados usando o método de corte selecionado
    cutoff = determine_dynamic_cutoff(scores, cutoff_method, min_results, max_results)
    console.print(f"[dim]Método de corte aplicado: resultados limitados a {cutoff} itens[/dim]")
    
    # Processar resultados até o ponto de corte
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Buscando detalhes das contratações..."),
        BarColumn(),
        TaskProgressColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Processando", total=cutoff)
        
        for i in range(cutoff):
            if i >= len(indices[0]):
                break
                
            idx = indices[0][i]
            key = keys[idx]
            similarity = similarities[i]
            
            # Buscar detalhes completos no banco de dados
            details = get_contratacao_details(key)
            
            results.append({
                "rank": i+1,
                "id": key,
                "similarity": similarity,
                "details": details
            })
            
            progress.update(task, advance=1)
    
    # Calcular confiança geral na classificação usando apenas os scores até o ponto de corte
    confidence = calculate_confidence(scores[:cutoff])
    
    # Retornar os resultados e a confiança
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

def display_results(results, confidence, query, preproc_options):
    """Exibe os resultados da busca em formato detalhado com informações completas."""
    if not results:
        console.print("\n[bold yellow]Nenhum resultado encontrado para esta consulta.[/bold yellow]")
        return
        
    console.print(f"\n[bold green]Resultados para a consulta: [italic]\"{query}\"[/italic][/bold green]")
    console.print(f"[bold cyan]Índice de confiança: {confidence:.2f}%[/bold cyan]\n")
    
    # Processar a consulta com as mesmas opções para encontrar termos relevantes
    processed_query = gvg_pre_processing(
        query,
        remove_special_chars=preproc_options["remove_special_chars"],
        keep_separators=preproc_options["keep_separators"],
        remove_accents=preproc_options["remove_accents"],
        case=preproc_options["case"],
        remove_stopwords=preproc_options["remove_stopwords"],
        lemmatize=preproc_options["lemmatize"]
    )
    query_terms = set(processed_query.split())
    
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

# Adicionar esta nova função para exportar resultados para Excel
def export_results_to_excel(results, query, preproc_options):
    """Exporta os resultados da busca para um arquivo Excel."""
    if not results:
        console.print("[yellow]Nenhum resultado para exportar.[/yellow]")
        return False
    
    try:
        # Criar um dataframe com os resultados
        data = []
        for result in results:
            details = result.get("details", {})
            if details:
                data.append({
                    "Rank": result["rank"],
                    "ID": result["id"],
                    "Similaridade": result["similarity"],
                    "Órgão": details.get("orgaoEntidade_razaosocial", "N/A"),
                    "Unidade": details.get("unidadeOrgao_nomeUnidade", "N/A"),
                    "Município": details.get("unidadeOrgao_municipioNome", "N/A"),
                    "UF": details.get("unidadeOrgao_ufSigla", "N/A"),
                    "Valor": details.get("valorTotalHomologado", 0),
                    "Data Abertura": details.get("dataAberturaProposta", "N/A"),
                    "Data Encerramento": details.get("dataEncerramentoProposta", "N/A"),
                    "Descrição": details.get("descricaoCompleta", "N/A")
                })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Gerar nome do arquivo baseado na data e hora
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:30].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        results_dir = os.path.join(BASE_PATH, "GvG", "SS", "RESULTADOS")
        os.makedirs(results_dir, exist_ok=True)
        
        # Nome do arquivo
        filename = os.path.join(results_dir, f"busca_{query_clean}_{timestamp}.xlsx")
        
        # Salvar para Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        console.print(f"[green]Resultados exportados para: {filename}[/green]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados: {str(e)}[/bold red]")
        return False
    
def selecionar_metodo_similaridade():
    """Permite ao usuário selecionar o método de similaridade a ser utilizado."""
    console.print("\n[bold magenta]Métodos de Similaridade Disponíveis[/bold magenta]")
    
    # Criar tabela comparativa dos métodos
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Método", style="green")
    table.add_column("Descrição", style="magenta")
    table.add_column("Melhor para", style="cyan")
    table.add_column("Características", style="yellow")
    
    methods = [
        {"nome": "Similaridade de Cosseno", 
         "descricao": "Mede o ângulo entre vetores, ignorando magnitude",
         "melhor_para": "Embeddings de texto, onde direção representa significado",
         "caracteristicas": "Ignora magnitude, foca na direção"},
        
        {"nome": "Distância Euclidiana", 
         "descricao": "Mede a distância 'em linha reta' entre vetores",
         "melhor_para": "Dados onde a magnitude importa (ex: imagens)",
         "caracteristicas": "Considera tanto direção quanto magnitude, sensível a outliers"},
        
        {"nome": "Produto Interno", 
         "descricao": "Produto escalar entre vetores sem normalização",
         "melhor_para": "Quando a 'força' do sinal é relevante",
         "caracteristicas": "Considera direção e magnitude, favorece vetores maiores"}
    ]
    
    for i, method in enumerate(methods, 1):
        table.add_row(
            str(i),
            method["nome"],
            method["descricao"],
            method["melhor_para"],
            method["caracteristicas"]
        )
    
    console.print(table)
    
    choice = input(f"\nSelecione o método de similaridade a utilizar (1-{len(methods)}): ")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(methods):
            return idx, methods[idx]["nome"]
        else:
            console.print("[yellow]Escolha inválida. Selecionando similaridade de cosseno (padrão).[/yellow]")
            return 0, methods[0]["nome"]
    except ValueError:
        console.print("[yellow]Entrada inválida. Selecionando similaridade de cosseno (padrão).[/yellow]")
        return 0, methods[0]["nome"]
    
  
def determine_cutoff_fixed(scores, top_n=TOP_N):
    """Método de corte fixo - retorna sempre TOP_N resultados."""
    return min(top_n, len(scores))

def determine_cutoff_elbow(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """Método do cotovelo - identifica quedas significativas nos scores."""
    if len(scores) <= min_results:
        return len(scores)
    
    # Calcular diferenças entre scores consecutivos
    diffs = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
    
    # Calcular média e desvio padrão das diferenças
    mean_diff = sum(diffs) / len(diffs)
    std_diff = (sum((d - mean_diff)**2 for d in diffs) / len(diffs))**0.5
    
    # Encontrar o primeiro ponto onde a diferença é maior que média + 1.5*std
    cutoff = max_results  # Valor padrão se não encontrar um cotovelo
    for i in range(min_results-1, min(len(diffs), max_results-1)):
        if diffs[i] > mean_diff + ELBOW_THRESHOLD * std_diff:
            cutoff = i + 1  # +1 porque queremos incluir este resultado
            break
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_threshold(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """Limiar de similaridade - mantém resultados acima de um percentual do melhor score."""
    if len(scores) <= min_results:
        return len(scores)
    
    # Obter o melhor score
    top_score = scores[0]
    
    # Encontrar quantos resultados estão acima do limiar
    cutoff = 0
    for score in scores:
        if score >= top_score * SIMILARITY_THRESHOLD:
            cutoff += 1
        else:
            break
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_gap(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """Análise de Gap - detecta saltos significativos entre scores consecutivos."""
    if len(scores) <= min_results:
        return len(scores)
    
    # Estabelecer um "nível de ruído" baseado nos scores mais baixos
    noise_level = np.mean(scores[-10:]) if len(scores) >= 10 else scores[-1]
    
    # Analisar diferenças entre scores consecutivos
    cutoff = max_results  # Valor padrão se não encontrar um gap significativo
    
    for i in range(min_results, min(len(scores)-1, max_results-1)):
        current_gap = scores[i] - scores[i+1]
        
        # Calcular o gap médio dos últimos resultados
        if i >= min_results + 2:
            avg_gap = sum(scores[j] - scores[j+1] for j in range(i-min_results, i)) / min_results
            
            # Se encontramos um gap significativo e o próximo score está próximo do ruído
            if (current_gap > GAP_MULTIPLIER * avg_gap) and (scores[i+1] < noise_level * NOISE_FACTOR):
                cutoff = i + 1
                break
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_combined(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """Método Combinado - aplica diferentes métodos e usa o mais restritivo."""
    if len(scores) <= min_results:
        return len(scores)
    
    # Aplicar método do cotovelo
    cutoff_elbow = determine_cutoff_elbow(scores, min_results, max_results)
    
    # Aplicar limiar de similaridade
    cutoff_threshold = determine_cutoff_threshold(scores, min_results, max_results)
    
    # Aplicar análise de gap
    cutoff_gap = determine_cutoff_gap(scores, min_results, max_results)
    
    # Usar o mais restritivo dos três métodos
    cutoff = min(cutoff_elbow, cutoff_threshold, cutoff_gap)
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_auto_inflection(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Método de pontos de inflexão - detecta automaticamente mudanças na curvatura dos scores
    sem depender de constantes predefinidas.
    """
    if len(scores) <= min_results:
        return len(scores)
    
    # Calcular diferenças de primeira ordem (primeira derivada)
    first_derivative = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
    
    # Precisamos de pelo menos 3 pontos para calcular a segunda derivada
    if len(first_derivative) < 2:
        return min(len(scores), max_results)
    
    # Calcular diferenças de segunda ordem (segunda derivada)
    second_derivative = [first_derivative[i] - first_derivative[i+1] for i in range(len(first_derivative)-1)]
    
    # Encontrar o ponto com maior mudança na segunda derivada após os primeiros resultados
    # Isso indica um ponto de inflexão na curva de scores
    max_inflection = 0
    cutoff = max_results
    
    for i in range(min_results-2, min(len(second_derivative), max_results-2)):
        if abs(second_derivative[i]) > max_inflection:
            max_inflection = abs(second_derivative[i])
            cutoff = i + 2  # +2 porque estamos trabalhando com a segunda derivada
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_natural_gap(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Método de gap natural - usa estatísticas internas dos próprios dados para 
    determinar gaps significativos sem usar constantes predefinidas.
    """
    if len(scores) <= min_results:
        return len(scores)
    
    # Calcular todos os gaps entre scores consecutivos
    gaps = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
    
    # Não temos gaps suficientes para análise
    if len(gaps) < min_results:
        return len(scores)
    
    # Calcular a média e desvio padrão dos gaps
    mean_gap = sum(gaps) / len(gaps)
    
    # Normalizar os gaps em relação à média (quanto maior o valor, mais significativo é o gap)
    normalized_gaps = [gap / mean_gap if mean_gap > 0 else 0 for gap in gaps]
    
    # Encontrar o primeiro gap significativamente maior que os outros
    # Sem usar uma constante fixa, usamos a própria distribuição dos dados
    cutoff = max_results
    
    for i in range(min_results-1, min(len(normalized_gaps), max_results-1)):
        # Verificar se este gap é um outlier em relação aos gaps anteriores
        previous_gaps = normalized_gaps[:i]
        if previous_gaps:
            prev_mean = sum(previous_gaps) / len(previous_gaps)
            prev_std = (sum((g - prev_mean)**2 for g in previous_gaps) / len(previous_gaps))**0.5
            
            # Um gap é considerado significativo se for maior que todos os anteriores
            # ou se for um outlier estatístico (adaptativo aos dados)
            if normalized_gaps[i] > max(previous_gaps) or (prev_std > 0 and normalized_gaps[i] > prev_mean + 2 * prev_std):
                cutoff = i + 1
                break
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_kmeans(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Método de clustering - usa K-means para agrupar automaticamente os scores em
    relevantes e irrelevantes, sem depender de constantes predefinidas.
    """
    if len(scores) <= min_results:
        return len(scores)
    
    # Limitar o número de scores para análise
    analysis_scores = scores[:min(len(scores), max_results)]
    
    # Precisamos de pelo menos alguns pontos para clustering
    if len(analysis_scores) < min_results + 2:
        return len(analysis_scores)
    
    try:
        # Reshape para formato esperado pelo KMeans
        X = np.array(analysis_scores).reshape(-1, 1)
        
        # Aplicar K-means com 2 clusters (relevante e irrelevante)
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=2, random_state=0, n_init=10).fit(X)
        
        # Obter os centros dos clusters
        centers = kmeans.cluster_centers_.flatten()
        labels = kmeans.labels_
        
        # Determinar qual cluster tem valor médio mais alto (mais relevante)
        relevant_cluster = 0 if centers[0] > centers[1] else 1
        
        # Encontrar o primeiro ponto que pertence ao cluster irrelevante
        for i in range(len(labels)):
            if labels[i] != relevant_cluster:
                return max(min_results, i)
        
        # Se todos pertencem ao mesmo cluster
        return len(analysis_scores)
    except:
        # Se ocorrer algum erro (ex: sklearn não disponível), use o método de inflexão
        return determine_cutoff_auto_inflection(scores, min_results, max_results)

def determine_cutoff_confidence_based(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Método baseado na confiança - analisa como o índice de confiança varia à medida que
    mais resultados são adicionados, sem depender de constantes fixas.
    """
    if len(scores) <= min_results:
        return len(scores)
    
    # Calcular confiança para diferentes números de resultados
    confidences = []
    for i in range(min_results, min(len(scores) + 1, max_results + 1)):
        current_scores = scores[:i]
        confidence = calculate_confidence(current_scores)
        confidences.append(confidence)
    
    # Se não tivermos confidences suficientes para análise
    if len(confidences) < 2:
        return min(len(scores), max_results)
    
    # Calcular a variação da confiança
    confidence_changes = [confidences[i-1] - confidences[i] for i in range(1, len(confidences))]
    
    # Encontrar onde a confiança começa a cair significativamente
    if len(confidence_changes) < 2:
        return min(len(scores), max_results)
    
    # Calcular a média e desvio padrão das mudanças
    mean_change = sum(confidence_changes) / len(confidence_changes)
    std_change = (sum((c - mean_change)**2 for c in confidence_changes) / len(confidence_changes))**0.5
    
    # Encontrar o primeiro ponto onde a queda é significativa em relação à própria distribuição
    cutoff = min_results
    for i, change in enumerate(confidence_changes, min_results):
        # Verificar se a queda é um outlier em relação às quedas anteriores
        if std_change > 0 and change > mean_change + std_change:
            cutoff = i
            break
        # Ou se a confiança cai continuamente por alguns pontos
        elif i >= min_results + 2 and all(c > 0 for c in confidence_changes[i-min_results:i]):
            cutoff = i
            break
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))

def determine_cutoff_distribution_based(scores, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Método baseado na distribuição - usa a própria distribuição dos scores para
    encontrar um ponto de corte natural, sem depender de constantes predefinidas.
    """
    if len(scores) <= min_results:
        return len(scores)
    
    # Limitar o número de scores para análise
    analysis_scores = scores[:min(len(scores), max_results)]
    
    # Calcular a soma total dos scores
    total_score = sum(analysis_scores)
    if total_score == 0:
        return min_results
    
    # Calcular a porcentagem acumulada
    cumulative_percent = []
    cumulative_sum = 0
    for score in analysis_scores:
        cumulative_sum += score
        cumulative_percent.append(cumulative_sum / total_score)
    
    # Encontrar o "ponto do cotovelo" na curva de porcentagem acumulada
    # usando a distância máxima até a linha diagonal
    max_distance = 0
    cutoff = min_results
    
    for i in range(len(cumulative_percent)):
        # Distância até a linha diagonal (y = x)
        # Para cada ponto (i/n, cum_percent[i]), calculamos a distância até a linha y = x
        x = (i + 1) / len(cumulative_percent)
        y = cumulative_percent[i]
        
        # Distância de um ponto (x,y) à linha y = x é |y - x| / sqrt(2)
        distance = abs(y - x) / 1.414
        
        if distance > max_distance:
            max_distance = distance
            cutoff = i + 1
    
    # Garantir os limites mínimo e máximo
    return max(min_results, min(cutoff, max_results))


def determine_dynamic_cutoff(scores, cutoff_method=0, min_results=MIN_RESULTS, max_results=MAX_RESULTS):
    """
    Determina o número de resultados a retornar baseado no método de corte selecionado.
    
    cutoff_method:
    0 - Corte Fixo (TOP N)
    1 - Método do Cotovelo
    2 - Limiar de Similaridade
    3 - Análise de Gap
    4 - Método Combinado
    5 - Pontos de Inflexão Auto-Adaptativo
    6 - Gap Natural
    7 - Clustering K-means
    8 - Baseado em Confiança Adaptativa
    9 - Baseado em Distribuição
    """
    if cutoff_method == 1:
        return determine_cutoff_elbow(scores, min_results, max_results)
    elif cutoff_method == 2:
        return determine_cutoff_threshold(scores, min_results, max_results)
    elif cutoff_method == 3:
        return determine_cutoff_gap(scores, min_results, max_results)
    elif cutoff_method == 4:
        return determine_cutoff_combined(scores, min_results, max_results)
    elif cutoff_method == 5:
        return determine_cutoff_auto_inflection(scores, min_results, max_results)
    elif cutoff_method == 6:
        return determine_cutoff_natural_gap(scores, min_results, max_results)
    elif cutoff_method == 7:
        return determine_cutoff_kmeans(scores, min_results, max_results)
    elif cutoff_method == 8:
        return determine_cutoff_confidence_based(scores, min_results, max_results)
    elif cutoff_method == 9:
        return determine_cutoff_distribution_based(scores, min_results, max_results)
    else:
        # Método 0 ou qualquer outro - usar corte fixo
        return determine_cutoff_fixed(scores, TOP_N)
    
def selecionar_metodo_corte():
    """Permite ao usuário selecionar o método de corte a ser utilizado para limitar resultados."""
    console.print("\n[bold magenta]Métodos de Corte Disponíveis[/bold magenta]")
    
    # Criar tabela comparativa dos métodos
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Método", style="green")
    table.add_column("Descrição", style="magenta")
    table.add_column("Vantagens", style="cyan")
    table.add_column("Funcionamento", style="yellow")
    
    methods = [
        {"nome": "Corte Fixo (TOP N)", 
         "descricao": "Retorna sempre um número fixo de resultados",
         "vantagens": "Simples e previsível",
         "funcionamento": f"Retorna sempre os {TOP_N} melhores resultados"},
        
        {"nome": "Método do Cotovelo", 
         "descricao": "Identifica quedas significativas nos scores de similaridade",
         "vantagens": "Adapta-se à distribuição dos resultados",
         "funcionamento": "Detecta onde há uma 'quebra' na curva de similaridade"},
        
        {"nome": "Limiar de Similaridade", 
         "descricao": "Mantém apenas resultados acima de um percentual do melhor score",
         "vantagens": "Foco na qualidade relativa dos resultados",
         "funcionamento": f"Corta resultados abaixo de {SIMILARITY_THRESHOLD*100}% do melhor score"},
        
        {"nome": "Análise de Gap", 
         "descricao": "Detecta saltos significativos entre scores consecutivos",
         "vantagens": "Sensível a descontinuidades na relevância",
         "funcionamento": "Identifica onde há um gap maior que o esperado"},
        
        {"nome": "Método Combinado", 
         "descricao": "Combina cotovelo, limiar e análise de gap",
         "vantagens": "Mais robusto, combina múltiplas heurísticas",
         "funcionamento": "Aplica diferentes métodos e usa o mais restritivo"},
         
        {"nome": "Pontos de Inflexão Auto-Adaptativo", 
         "descricao": "Detecta automaticamente pontos de inflexão na curva de scores",
         "vantagens": "Totalmente adaptativo, sem constantes fixas",
         "funcionamento": "Analisa mudanças na segunda derivada dos scores"},
         
        {"nome": "Gap Natural", 
         "descricao": "Usa estatísticas dos próprios gaps para determinar cortes",
         "vantagens": "Auto-calibrante, independente de parâmetros",
         "funcionamento": "Detecta outliers nos próprios gaps entre scores"},
         
        {"nome": "Clustering K-means", 
         "descricao": "Agrupa automaticamente scores em relevantes e irrelevantes",
         "vantagens": "Abordagem de machine learning totalmente adaptativa",
         "funcionamento": "Usa algoritmo K-means para classificar os resultados"},
         
        {"nome": "Baseado em Confiança Adaptativa", 
         "descricao": "Analisa como a confiança varia à medida que resultados são adicionados",
         "vantagens": "Foco na qualidade do conjunto de resultados",
         "funcionamento": "Detecta quando adicionar resultados reduz significativamente a confiança"},
         
        {"nome": "Baseado em Distribuição", 
         "descricao": "Usa a distribuição cumulativa dos scores para encontrar o ponto ideal",
         "vantagens": "Baseia-se em propriedades estatísticas da distribuição",
         "funcionamento": "Encontra o ponto que maximiza a distância à linha diagonal"}
    ]
    
    for i, method in enumerate(methods, 1):
        table.add_row(
            str(i),
            method["nome"],
            method["descricao"],
            method["vantagens"],
            method["funcionamento"]
        )
    
    console.print(table)
    
    choice = input(f"\nSelecione o método de corte a utilizar (1-{len(methods)}): ")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(methods):
            return idx, methods[idx]["nome"]
        else:
            console.print("[yellow]Escolha inválida. Selecionando corte fixo (padrão).[/yellow]")
            return 0, methods[0]["nome"]
    except ValueError:
        console.print("[yellow]Entrada inválida. Selecionando corte fixo (padrão).[/yellow]")
        return 0, methods[0]["nome"]
    
  

# Modificar a função main para incluir múltipla escolha
# Modificar a função main para implementar a nova lógica
def main():
    console.print(Panel(
        "[bold cyan]Baseado em OpenAI Embeddings com detalhes completos[/bold cyan]",
        title="[bold magenta]SISTEMA DE BUSCA POR SIMILARIDADE DE CONTRATAÇÕES v1.4[/bold magenta]",
        subtitle="[bold cyan]Métodos de similaridade e corte configuráveis[/bold cyan]",
        expand=False
    ))
    
    # Variáveis para armazenar os resultados da última consulta
    last_results = None
    last_query = None
    last_preproc_options = None
    
    # Selecionar arquivo de embedding inicialmente
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
    
    # Definir método de similaridade padrão
    similarity_method_idx = 0
    similarity_method_name = "Similaridade de Cosseno"
    
    # Definir método de corte padrão
    cutoff_method_idx = 0
    cutoff_method_name = "Corte Fixo (TOP N)"
    
    # Criar índice FAISS com método padrão
    faiss_index, keys, similarity_method_idx = create_faiss_index(embeddings_dict, dimension, similarity_method_idx)
    
    # Loop principal com menu expandido
    while True:
        console.print("\n[bold magenta]" + "="*80 + "[/bold magenta]")
        console.print("[bold cyan]Digite sua consulta ou escolha uma opção:[/bold cyan]")
        console.print(f"[cyan]1[/cyan] - Selecionar outro embedding (atual: {embedding_info['model_name']})")
        console.print(f"[cyan]2[/cyan] - Alterar método de similaridade (atual: {similarity_method_name})")
        console.print(f"[cyan]3[/cyan] - Alterar método de corte (atual: {cutoff_method_name})")
        console.print("[cyan]4[/cyan] - Exportar últimos resultados para Excel")
        console.print("[cyan]5[/cyan] - Encerrar o programa")
        
        # Solicitar entrada do usuário
        query = input("\n> ").strip()
        
        # Verificar se é um comando especial
        if query == "1":
            # Selecionar novo embedding
            embedding_info = selecionar_embedding_arquivo()
            if not embedding_info:
                continue
            
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
                console.print("[bold red]Não foi possível carregar os embeddings.[/bold red]")
                continue
            
            # Recriar índice FAISS com o mesmo método de similaridade
            faiss_index, keys, similarity_method_idx = create_faiss_index(embeddings_dict, dimension, similarity_method_idx)
            continue
            
        elif query == "2":
            # Selecionar método de similaridade
            similarity_method_idx, similarity_method_name = selecionar_metodo_similaridade()
            
            # Recriar índice FAISS com o novo método
            faiss_index, keys, similarity_method_idx = create_faiss_index(embeddings_dict, dimension, similarity_method_idx)
            continue
            
        elif query == "3":
            # Selecionar método de corte
            cutoff_method_idx, cutoff_method_name = selecionar_metodo_corte()
            continue
            
        elif query == "4":
            # Exportar resultados para Excel
            if last_results:
                export_results_to_excel(last_results, last_query, last_preproc_options)
            else:
                console.print("[yellow]Nenhum resultado disponível para exportação. Faça uma consulta primeiro.[/yellow]")
            continue
            
        elif query == "5":
            # Sair do programa
            console.print("\n[bold green]Obrigado por usar o sistema de busca![/bold green]")
            return
            
        elif not query:
            # Consulta vazia
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
            
        # Se chegou aqui, é uma consulta normal
        console.print(f"\n[bold magenta]Processando consulta: \"{query}\"[/bold magenta]")
        
        # Buscar itens similares
        try:
            start_time = time.time()
            results, confidence = search_similar_items(
                query, 
                model_name, 
                preproc_options,
                embeddings_dict, 
                faiss_index, 
                keys,
                similarity_method_idx,
                cutoff_method_idx
            )
            end_time = time.time()
            
            # Armazenar resultados para possível exportação
            last_results = results
            last_query = query
            last_preproc_options = preproc_options
            
            # Exibir resultados
            display_results(results, confidence, query, preproc_options)
            console.print(f"[dim]Tempo de busca: {(end_time - start_time):.4f} segundos[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]Erro durante a busca: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())

if __name__ == "__main__":
    main()