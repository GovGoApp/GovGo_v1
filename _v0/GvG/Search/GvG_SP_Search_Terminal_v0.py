import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import pickle
import locale
import time
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from openai import OpenAI
from dotenv import load_dotenv


DEFAULT_PREPROC_PARAMS = {
    "remove_special_chars": True,
    "keep_separators": True,
    "remove_accents": False,
    "case": "lower",
    "remove_stopwords": True,
    "lemmatize": True
}

SEMANTIC_WEIGHT = 0.8  # Peso padrão para busca semântica em busca híbrida

# Importar funções do módulo de pré-processamento
try:
    from gvg_pre_processing import (
        gvg_pre_processing,
        EMBEDDING_MODELS,
        EMBEDDING_MODELS_REVERSE
    )
except ImportError:
    print("ERRO: Não foi possível importar o módulo de pré-processamento.")
    sys.exit(1)

# Configure Rich console
console = Console()

# Configurar locale para formatação de valores em reais
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        console.print("[yellow]Aviso: Não foi possível configurar o locale para formatação monetária.[/yellow]")

# Load environment variables from .env
env_path = os.path.join(os.path.dirname(__file__), 'supabase_v0.env')
console.print(f"[blue]Buscando arquivo .env em: {env_path}")
load_dotenv(dotenv_path=env_path)

# Fetch connection variables
USER = os.getenv("user")
PASSWORD = os.getenv("password") 
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Cliente OpenAI para geração de embeddings
client = OpenAI(api_key="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")

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
RESULTS_PATH = BASE_PATH + "GvG\\SS\\RESULTADOS\\"

# Constantes para configuração de busca
EMBEDDING_MODEL = "text-embedding-3-large"
MIN_RESULTS = 5      # Número mínimo de resultados que serão retornados
MAX_RESULTS = 10     # Número máximo de resultados que serão retornados
TOP_TERMS = 7       # Número de termos principais para exibir na busca por palavras-chave

# Tipos de busca
SEARCH_TYPES = {
    1: {"name": "Semântica", "description": "Busca baseada no significado do texto"},
    2: {"name": "Palavras-chave", "description": "Busca exata de termos e expressões"},
    3: {"name": "Híbrida", "description": "Combinação de busca semântica e por palavras-chave"}
}

# Variáveis para armazenar estado global
last_results = None
last_query = None
current_search_type = 1  # Tipo de busca padrão: Semântica

def create_connection():
    """Cria uma conexão com o banco de dados Supabase"""
    try:
        connection = psycopg2.connect(
            user=USER, 
            password=PASSWORD, 
            host=HOST, 
            port=PORT, 
            dbname=DBNAME,
            connect_timeout=30
        )
        return connection
    except Exception as e:
        console.print(f"[bold red]Erro ao conectar ao banco de dados: {e}[/bold red]")
        return None

def get_embedding(text, model=EMBEDDING_MODEL):
    """Gera embedding para um texto usando a API da OpenAI"""
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

def semantic_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS):
    """Realiza busca semântica usando embeddings no Supabase"""
    connection = create_connection()
    if not connection:
        return [], 0.0
    
    cursor = connection.cursor()
    
    try:
        # Processar a consulta
        console.print(f"\n[cyan]Gerando embedding para consulta: \"{query_text}\"[/cyan]")
        query_embedding = get_embedding(query_text)
        
        # Converter para lista (formato compatível com PostgreSQL)
        query_embedding_list = query_embedding.tolist()
        
        # Consulta SQL usando o operador <=> (similaridade de cosseno)
        search_query = """
        SELECT 
            c.numeroControlePNCP,
            c.anoCompra,
            c.descricaoCompleta,
            c.valorTotalHomologado,
            c.dataAberturaProposta,
            c.dataEncerramentoProposta,
            c.unidadeOrgao_ufSigla,
            c.unidadeOrgao_municipioNome,
            c.unidadeOrgao_nomeUnidade,
            c.orgaoEntidade_razaosocial,
            1 - (e.embedding_vector <=> %s::vector) AS similarity
        FROM 
            contratacoes c
        JOIN 
            contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
        WHERE 
            e.embedding_vector IS NOT NULL 
         ORDER BY 
            similarity DESC
        LIMIT %s
        """

        cursor.execute(search_query, (
            query_embedding_list,
            limit
        ))

        results = cursor.fetchall()
        
        # Obter nomes das colunas
        column_names = [desc[0] for desc in cursor.description]
        
        # Converter para lista de dicionários
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": float(result_dict["similarity"]),
                "details": result_dict
            })
        
        # Calcular nível de confiança
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        
        return formatted_results, confidence
    
    except Exception as e:
        console.print(f"[bold red]Erro na busca semântica: {str(e)}[/bold red]")
        return [], 0.0
    
    finally:
        cursor.close()
        connection.close()

def keyword_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS):
    """Realiza busca por palavras-chave usando full-text search do PostgreSQL"""
    connection = create_connection()
    if not connection:
        return [], 0.0
    
    cursor = connection.cursor()
    
    try:
        # Preparar a consulta para busca de texto completo
        # Converter a consulta para formato de busca tsquery
        tsquery = " & ".join(query_text.split())
        console.print(f"\n[cyan]tsquery\"{tsquery}\"[/cyan]")
        
        # Adicionar variantes com prefixo para melhorar resultados
        tsquery_prefix = ":* & ".join(query_text.split()) + ":*"
        console.print(f"\n[cyan]tsquery_prefix: \"{tsquery_prefix}\"[/cyan]")
        
        # Consulta SQL usando índice de texto completo e ranking ts_rank
        search_query = """
        SELECT 
            c.numeroControlePNCP,
            c.anoCompra,
            c.descricaoCompleta,
            c.valorTotalHomologado,
            c.dataAberturaProposta,
            c.dataEncerramentoProposta,
            c.unidadeOrgao_ufSigla,
            c.unidadeOrgao_municipioNome,
            c.unidadeOrgao_nomeUnidade,
            c.orgaoEntidade_razaosocial,
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank,
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank_prefix
        FROM 
            contratacoes c
        WHERE 
            to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)
            OR to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)
        ORDER BY 
            (ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.7 + 
            ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.3) DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, (
            tsquery, 
            tsquery_prefix, 
            tsquery, 
            tsquery_prefix, 
            tsquery,    # Parâmetro adicional para o ORDER BY
            tsquery_prefix,  # Parâmetro adicional para o ORDER BY
            limit
        ))
        results = cursor.fetchall()
        
        # Obter nomes das colunas
        column_names = [desc[0] for desc in cursor.description]
        
        # Converter para lista de dicionários
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            
            # Normalizar score para ficar entre 0 e 1, similar à similaridade
            score = float(result_dict["rank"]) * 0.7 + float(result_dict["rank_prefix"]) * 0.3
            max_possible_score = len(query_text.split()) * 0.1  # Estimativa simplificada
            normalized_score = min(score / max_possible_score, 1.0)
            
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": normalized_score,  # Score normalizado
                "details": result_dict
            })
        
        # Garantir número mínimo de resultados
        if len(formatted_results) < min_results:
            # Busca alternativa sem filtro de correspondência exata
            # Substituir a consulta alternativa na função keyword_search (por volta da linha 290)
            alternative_query = """
            SELECT 
                c.numeroControlePNCP,
                c.anoCompra,
                c.descricaoCompleta,
                c.valorTotalHomologado,
                c.dataAberturaProposta,
                c.dataEncerramentoProposta,
                c.unidadeOrgao_ufSigla,
                c.unidadeOrgao_municipioNome,
                c.unidadeOrgao_nomeUnidade,
                c.orgaoEntidade_razaosocial,
                ts_rank(to_tsvector('portuguese', c.descricaoCompleta), plainto_tsquery('portuguese', %s)) AS text_similarity
            FROM 
                contratacoes c
            WHERE 
                c.numeroControlePNCP NOT IN (
                    SELECT unnest(%s::text[]) AS numeroControlePNCP
                )
            ORDER BY 
                text_similarity DESC
            LIMIT %s
            """
            
            existing_ids = [r["id"] for r in formatted_results]
            cursor.execute(alternative_query, (
                query_text, 
                existing_ids, 
                max(min_results - len(formatted_results), 0)
            ))
            
            additional_results = cursor.fetchall()
            additional_column_names = [desc[0] for desc in cursor.description]
            
            for i, row in enumerate(additional_results):
                result_dict = dict(zip(additional_column_names, row))
                
                formatted_results.append({
                    "rank": len(formatted_results) + 1,
                    "id": result_dict["numerocontrolepncp"],
                    "similarity": float(result_dict["text_similarity"]),
                    "details": result_dict
                })
        
        # Calcular nível de confiança
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        
        return formatted_results, confidence
    
    except Exception as e:
        console.print(f"[bold red]Erro na busca por palavras-chave: {str(e)}[/bold red]")
        return [], 0.0
    
    finally:
        cursor.close()
        connection.close()

def hybrid_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, semantic_weight=SEMANTIC_WEIGHT):
    """Realiza busca híbrida combinando semântica e palavras-chave"""
    connection = create_connection()
    if not connection:
        return [], 0.0
    
    cursor = connection.cursor()
    
    try:
        # Gerar embedding para busca semântica
        console.print(f"[cyan]Gerando embedding para consulta híbrida: \"{query_text}\"[/cyan]")
        query_embedding = get_embedding(query_text)
        query_embedding_list = query_embedding.tolist()
        
        # Preparar a consulta para busca de texto
        tsquery = " & ".join(query_text.split())
        tsquery_prefix = ":* & ".join(query_text.split()) + ":*"
        
        # Consulta SQL híbrida que combina ambas as abordagens
        search_query = """
        SELECT 
            c.numeroControlePNCP,
            c.anoCompra,
            c.descricaoCompleta,
            c.valorTotalHomologado,
            c.dataAberturaProposta,
            c.dataEncerramentoProposta,
            c.unidadeOrgao_ufSigla,
            c.unidadeOrgao_municipioNome,
            c.unidadeOrgao_nomeUnidade,
            c.orgaoEntidade_razaosocial,
            (1 - (e.embedding_vector <=> %s::vector)) AS semantic_score,
            COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_score,
            COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_prefix_score,
            -- Calcular pontuação combinada normalizada diretamente no SQL
            (
                %s * (1 - (e.embedding_vector <=> %s::vector)) + 
                (1 - %s) * (
                    LEAST(
                        (0.7 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) + 
                         0.3 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0)) 
                         / (%s), 1.0
                    )
                )
            ) AS combined_score
        FROM 
            contratacoes c
        JOIN 
            contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
        WHERE 
            e.embedding_vector IS NOT NULL
        ORDER BY 
            combined_score DESC
        LIMIT %s
        """

        max_possible_keyword_score = len(query_text.split()) * 0.1  # Estimativa para normalização
        
        cursor.execute(search_query, (
            query_embedding_list,  # Para o SELECT (semantic_score)
            tsquery,               # Para o SELECT (keyword_score)
            tsquery_prefix,        # Para o SELECT (keyword_prefix_score)
            semantic_weight,       # Para o combined_score (peso semântico)
            query_embedding_list,  # Para o combined_score (embedding)
            semantic_weight,       # Para o combined_score (1 - peso semântico)
            tsquery,               # Para o combined_score (keyword score)
            tsquery_prefix,        # Para o combined_score (keyword_prefix score) 
            max_possible_keyword_score,  # Para normalização
            limit
        ))
        
        results = cursor.fetchall()
        
        # Obter nomes das colunas
        column_names = [desc[0] for desc in cursor.description]
        
        # Converter para lista de dicionários
        formatted_results = []
        for i, row in enumerate(results):
            result_dict = dict(zip(column_names, row))
            
            # Calcular pontuação combinada
            semantic_score = float(result_dict["semantic_score"])
            keyword_score = float(result_dict["keyword_score"]) if result_dict["keyword_score"] else 0
            keyword_prefix_score = float(result_dict["keyword_prefix_score"]) if result_dict["keyword_prefix_score"] else 0
            
            # Normalizar pontuação de palavra-chave
            max_possible_keyword_score = len(query_text.split()) * 0.1  # Estimativa simplificada
            normalized_keyword_score = min((0.7 * keyword_score + 0.3 * keyword_prefix_score) / max_possible_keyword_score, 1.0)
            
            # Calcular pontuação combinada ponderada
            combined_score = semantic_weight * semantic_score + (1 - semantic_weight) * normalized_keyword_score
            
            formatted_results.append({
                "rank": i + 1,
                "id": result_dict["numerocontrolepncp"],
                "similarity": float(result_dict["combined_score"]),  # Usar o score calculado pelo SQL
                "semantic_score": float(result_dict["semantic_score"]),
                "keyword_score": float(result_dict["keyword_score"]) if result_dict["keyword_score"] else 0,
                "details": result_dict
            })
        
        # Calcular nível de confiança
        confidence = calculate_confidence([r["similarity"] for r in formatted_results])
        
        return formatted_results, confidence
    
    except Exception as e:
        console.print(f"[bold red]Erro na busca híbrida: {str(e)}[/bold red]")
        return [], 0.0
    
    finally:
        cursor.close()
        connection.close()

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações."""
    import math
    
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

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

def display_results(results, confidence, query, search_type_id):
    """Exibe os resultados da busca em formato detalhado"""
    if not results:
        console.print("\n[bold yellow]Nenhum resultado encontrado para esta consulta.[/bold yellow]")
        return
    
    search_type_name = SEARCH_TYPES[search_type_id]["name"]
    
    console.print(f"\n[bold green]Resultados para a consulta: [italic]\"{query}\"[/italic][/bold green]")
    console.print(f"[bold cyan]Tipo de busca: {search_type_name}[/bold cyan]")
    console.print(f"[bold cyan]Índice de confiança: {confidence:.2f}%[/bold cyan]\n")
    
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
        valor = format_currency(details.get("valortotalhomologado", 0)) if details else "N/A"
        
        # Formatar data
        data_encerramento = details.get("dataencerramentoproposta", "N/A") if details else "N/A"
        
        table.add_row(
            f"{result['rank']}", 
            f"{result['id']}", 
            f"{result['similarity']:.4f}",
            valor,
            str(data_encerramento)
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
            details.get("descricaocompleta", "N/A"),
            query.split()
        )
        
        # Criar painel com informações detalhadas
        panel_title = f"#{result['rank']} - {result['id']} (Similaridade: {result['similarity']:.4f})"
        
        # Adicionar scores específicos para busca híbrida
        if "semantic_score" in result and "keyword_score" in result:
            panel_title += f" [Semântico: {result['semantic_score']:.4f}, Palavra-chave: {result['keyword_score']:.4f}]"
        
        content = [
            f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoentidade_razaosocial', 'N/A')} [bold cyan]Unidade:[/bold cyan]   {details.get('unidadeorgao_nomeunidade', 'N/A')}",
            f"[bold cyan]Local:[/bold cyan] {details.get('unidadeorgao_municipionome', 'N/A')}/{details.get('unidadeorgao_ufsigla', 'N/A')}",
            #f"[bold cyan]Valor:[/bold cyan] {format_currency(details.get('valortotalhomologado', 0))}",
            f"[bold cyan]Datas:[/bold cyan] Abertura: {details.get('dataaberturaproposta', 'N/A')} | Encerramento: {details.get('dataencerramentoproposta', 'N/A')}",
            f"[bold cyan]Descrição:[/bold cyan] {descricao[:80]}..."
        ]
        
        panel = Panel(
            "\n".join(content),
            title=panel_title,
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print(panel)

def export_results_to_excel(results, query, search_type_id):
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
                result_data = {
                    "Rank": result["rank"],
                    "ID": result["id"],
                    "Similaridade": result["similarity"],
                    "Órgão": details.get("orgaoentidade_razaosocial", "N/A"),
                    "Unidade": details.get("unidadeorgao_nomeunidade", "N/A"),
                    "Município": details.get("unidadeorgao_municipionome", "N/A"),
                    "UF": details.get("unidadeorgao_ufsigla", "N/A"),
                    "Valor": details.get("valortotalhomologado", 0),
                    "Data Abertura": details.get("dataaberturaproposta", "N/A"),
                    "Data Encerramento": details.get("dataencerramentoproposta", "N/A"),
                    "Descrição": details.get("descricaocompleta", "N/A")
                }
                
                # Adicionar scores específicos para busca híbrida
                if "semantic_score" in result and "keyword_score" in result:
                    result_data["Score Semântico"] = result["semantic_score"]
                    result_data["Score Palavra-chave"] = result["keyword_score"]
                
                data.append(result_data)
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Gerar nome do arquivo baseado na data e hora
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_type_name = SEARCH_TYPES[search_type_id]["name"].lower()
        
        # Limitar o tamanho da consulta no nome do arquivo
        query_clean = "".join(c for c in query if c.isalnum() or c in " _").strip()
        query_clean = query_clean[:30].strip().replace(" ", "_")
        
        # Criar diretório para resultados se não existir
        os.makedirs(RESULTS_PATH, exist_ok=True)
        
        # Nome do arquivo
        filename = os.path.join(RESULTS_PATH, f"busca_{search_type_name}_{query_clean}_{timestamp}.xlsx")
        
        # Salvar para Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        console.print(f"[green]Resultados exportados para: {filename}[/green]")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao exportar resultados: {str(e)}[/bold red]")
        return False

def select_search_type():
    """Permite ao usuário selecionar o tipo de busca"""
    console.print("\n[bold magenta]Tipos de Busca Disponíveis[/bold magenta]")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Tipo", style="green")
    table.add_column("Descrição", style="magenta")
    
    for id, search_type in SEARCH_TYPES.items():
        table.add_row(
            str(id),
            search_type["name"],
            search_type["description"]
        )
    
    console.print(table)
    
    choice = Prompt.ask(
        "\nSelecione o tipo de busca",
        choices=["1", "2", "3"],
        default="1"
    )
    
    return int(choice)

def test_connection():
    """Testa a conexão com o banco de dados e verifica se as tabelas necessárias existem"""
    connection = create_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    try:
        # Verificar se as tabelas necessárias existem
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacoes', 'contratacoes_embeddings')
        """)
        count = cursor.fetchone()[0]
        
        if count != 2:
            console.print("[bold red]Erro: As tabelas 'contratacoes' e 'contratacoes_embeddings' não foram encontradas![/bold red]")
            return False
        
        # Verificar número de registros
        cursor.execute("SELECT COUNT(*) FROM contratacoes")
        contratacoes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contratacoes_embeddings")
        embeddings_count = cursor.fetchone()[0]
        
        console.print(f"[green]Conexão estabelecida com sucesso![/green]")
        console.print(f"[green]Registros encontrados: {contratacoes_count} contratações, {embeddings_count} embeddings[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Erro ao verificar tabelas: {e}[/bold red]")
        return False
    
    finally:
        cursor.close()
        connection.close()



def perform_search(query, search_type_id):
    """Realiza a busca de acordo com o tipo selecionado"""
    global last_results, last_query, current_search_type
    
    # Pré-processar a consulta antes da busca
    original_query = query  # Guardar consulta original
    processed_query = gvg_pre_processing(
        query, 
        remove_special_chars=DEFAULT_PREPROC_PARAMS["remove_special_chars"],
        keep_separators=DEFAULT_PREPROC_PARAMS["keep_separators"],
        remove_accents=DEFAULT_PREPROC_PARAMS["remove_accents"],
        case=DEFAULT_PREPROC_PARAMS["case"],
        remove_stopwords=DEFAULT_PREPROC_PARAMS["remove_stopwords"],
        lemmatize=DEFAULT_PREPROC_PARAMS["lemmatize"]
    )
    
    console.print(f"[bold blue]Realizando busca {SEARCH_TYPES[search_type_id]['name']} para: \"{original_query}\"[/bold blue]")
    console.print(f"[dim]Consulta pré-processada: \"{processed_query}\"[/dim]")
    
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Buscando resultados..."),
        BarColumn(),
        TaskProgressColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Processando", total=1)
        
        if search_type_id == 1:
            # Busca semântica
            results, confidence = semantic_search(processed_query)
        elif search_type_id == 2:
            # Busca por palavras-chave
            results, confidence = keyword_search(processed_query)
        elif search_type_id == 3:
            # Busca híbrida
            results, confidence = hybrid_search(processed_query)
        else:
            # Tipo inválido, usar semântica por padrão
            results, confidence = semantic_search(processed_query)
        
        progress.update(task, advance=1)
    
    end_time = time.time()
    search_time = end_time - start_time
    
    # Armazenar resultados para possível exportação
    last_results = results
    last_query = original_query  # Armazenar a consulta original para referência
    current_search_type = search_type_id
    
    # Exibir resultados
    display_results(results, confidence, original_query, search_type_id)
    console.print(f"[dim]Tempo de busca: {search_time:.4f} segundos[/dim]")

def display_menu():
    """Exibe o menu principal"""
    console.print("\n[bold magenta]" + "="*80 + "[/bold magenta]")
    console.print(f"[bold cyan]Tipo de busca atual: {SEARCH_TYPES[current_search_type]['name']}[/bold cyan]")
    console.print("[bold cyan]Digite sua consulta ou escolha uma opção:[/bold cyan]")
    console.print("[cyan]1[/cyan] - Alterar tipo de busca")
    console.print("[cyan]2[/cyan] - Exportar últimos resultados para Excel")
    console.print("[cyan]3[/cyan] - Encerrar o programa")
    console.print("\n[cyan]Digite qualquer outro texto para realizar uma nova busca[/cyan]")

def main():
    """Função principal do programa"""
    global current_search_type
    
    console.print(Panel(
        "[bold cyan]Conecta ao Supabase e realiza diferentes tipos de busca[/bold cyan]",
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE v1.0[/bold magenta]",
        subtitle="[bold cyan]Semântica, Palavras-chave e Híbrida[/bold cyan]",
        expand=False
    ))
    
    # Verificar conexão com o banco
    if not test_connection():
        console.print("[bold red]Não foi possível conectar ao banco de dados. Encerrando.[/bold red]")
        return
    
    # Selecionar tipo de busca inicial
    #current_search_type = select_search_type()
    
    # Loop principal
    while True:
        display_menu()
        
        # Solicitar entrada do usuário
        query = input("\n> ").strip()
        
        # Verificar opções especiais
        if query == "1":
            # Alterar tipo de busca
            current_search_type = select_search_type()
            continue
            
        elif query == "2":
            # Exportar resultados para Excel
            if last_results:
                export_results_to_excel(last_results, last_query, current_search_type)
            else:
                console.print("[yellow]Nenhum resultado disponível para exportação. Faça uma busca primeiro.[/yellow]")
            continue
            
        elif query == "3":
            # Sair do programa
            console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo![/bold green]")
            return
            
        elif not query:
            # Consulta vazia
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
            
        # Se chegou aqui, realizar busca normal
        perform_search(query, current_search_type)

if __name__ == "__main__":
    main()