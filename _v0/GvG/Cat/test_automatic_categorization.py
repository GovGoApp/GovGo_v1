#!/usr/bin/env python3
"""
Script para testar categorização automática usando embeddings já existentes.

Este script:
1. Seleciona descrições aleatórias de contratações da base (tabela contratacoes_embeddings)
2. Usa os embeddings já existentes dessas descrições
3. Calcula a similaridade com os embeddings das categorias (tabela categorias)
4. Retorna as Top 10 categorias mais similares para cada descrição

Autor: Sistema
Data: 26/06/2025
"""

import psycopg2
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import json
import pickle
from datetime import datetime
import random
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# Carrega as variáveis de ambiente do arquivo supabase_v0.env
load_dotenv('supabase_v0.env')

# Configurações do banco de dados usando credenciais do Supabase
DB_CONFIG = {
    'host': os.getenv('host'),
    'database': os.getenv('dbname'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'port': os.getenv('port')
}

# Cria connection string para SQLAlchemy
CONNECTION_STRING = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Inicializa console do Rich
console = Console()

def connect_to_db():
    """Conecta ao banco de dados PostgreSQL usando credenciais do Supabase."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """Cria engine SQLAlchemy para pandas."""
    try:
        engine = create_engine(CONNECTION_STRING)
        return engine
    except Exception as e:
        print(f"Erro ao criar engine: {e}")
        return None

def load_random_contracts(engine, num_samples=10):
    """
    Carrega uma amostra aleatória de contratações que possuem embeddings.
    
    Args:
        engine: SQLAlchemy engine
        num_samples: Número de amostras a carregar
    
    Returns:
        DataFrame com id, descricaocompleta e embedding_vector das contratações
    """
    query = """
    SELECT ce.id, c.descricaocompleta, ce.embedding_vector 
    FROM contratacoes_embeddings ce
    JOIN contratacoes c ON ce.numerocontrolepncp = c.numerocontrolepncp
    WHERE ce.embedding_vector IS NOT NULL 
    ORDER BY RANDOM() 
    LIMIT %(num_samples)s
    """
    
    try:
        df = pd.read_sql_query(query, engine, params={'num_samples': num_samples})
        return df
    except Exception as e:
        console.print(f"[red]Erro ao carregar contratações: {e}[/red]")
        return None

def semantic_categorization_search(contract_embedding, engine, top_k=10):
    """
    Realiza busca semântica de categorias usando embedding da contratação.
    Similar à função semantic_search do gvg_search_utils.
    
    Args:
        contract_embedding: Embedding da contratação (array numpy)
        engine: SQLAlchemy engine
        top_k: Número de categorias top a retornar
        
    Returns:
        Lista de dicionários com as top categorias e suas similaridades
    """
    try:
        # Converte embedding para lista para usar na query
        contract_embedding_list = contract_embedding.tolist()
        
        # Query SQL usando operador de similaridade coseno do pgvector
        query = """
        SELECT 
            id,
            codcat,
            nomcat,
            codnv0,
            nomnv0,
            codnv1,
            nomnv1,
            codnv2,
            nomnv2,
            codnv3,
            nomnv3,
            1 - (cat_embeddings <=> %(embedding)s::vector) AS similarity
        FROM 
            categorias
        WHERE 
            cat_embeddings IS NOT NULL
        ORDER BY 
            similarity DESC
        LIMIT %(limit)s
        """
        
        # Executa a query
        df = pd.read_sql_query(
            query, 
            engine, 
            params={
                'embedding': contract_embedding_list,
                'limit': top_k
            }
        )
        
        # Formata os resultados
        results = []
        for idx, row in df.iterrows():
            results.append({
                'rank': idx + 1,
                'categoria_id': row['id'],
                'codigo': row['codcat'],
                'descricao': row['nomcat'],
                'nivel0_cod': row['codnv0'],
                'nivel0_nome': row['nomnv0'],
                'nivel1_cod': row['codnv1'],
                'nivel1_nome': row['nomnv1'],
                'nivel2_cod': row['codnv2'],
                'nivel2_nome': row['nomnv2'],
                'nivel3_cod': row['codnv3'],
                'nivel3_nome': row['nomnv3'],
                'similarity_score': float(row['similarity'])
            })
        
        return results
        
    except Exception as e:
        console.print(f"[red]Erro ao realizar busca semântica de categorias: {e}[/red]")
        return []

def parse_embedding(embedding_str):
    """
    Converte string de embedding para array numpy.
    
    Args:
        embedding_str: String do embedding (pode ser JSON ou array)
    
    Returns:
        Array numpy do embedding
    """
    try:
        if isinstance(embedding_str, str):
            # Tenta fazer parse como JSON
            embedding = json.loads(embedding_str)
        else:
            embedding = embedding_str
        
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        console.print(f"[red]Erro ao converter embedding: {e}[/red]")
        return None

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações"""
    import math
    
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score if top_score > 0 else 0
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

def display_contract_details(contract, index, total):
    """Exibe detalhes de uma contratação usando Rich"""
    
    # Criar painel com informações da contratação
    title = f"CONTRATAÇÃO {index}/{total}"
    
    # Preparar texto da descrição (limitado para visualização)
    descricao = contract['descricaocompleta']
    if len(descricao) > 500:
        descricao_display = descricao[:500] + "..."
    else:
        descricao_display = descricao
    
    content = f"""
[bold blue]ID:[/bold blue] {contract['id']}

[bold green]Descrição Completa:[/bold green]
{descricao_display}
"""
    
    panel = Panel(
        content,
        title=title,
        border_style="cyan",
        expand=False
    )
    
    console.print(panel)

def display_categories_table(categories, confidence):
    """Exibe tabela de categorias usando Rich"""
    
    table = Table(
        title=f"🎯 TOP {len(categories)} CATEGORIAS MAIS SIMILARES (Confiança: {confidence:.1f}%)",
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    table.add_column("Rank", style="bold yellow", justify="center", width=6)
    table.add_column("Código", style="cyan", width=15)
    table.add_column("Categoria", style="white", min_width=30)
    table.add_column("Similaridade", style="bold green", justify="center", width=12)
    table.add_column("Nível 1", style="dim", width=20)
    table.add_column("Nível 2", style="dim", width=20)
    
    for cat in categories:
        similarity_color = "bright_green" if cat['similarity_score'] > 0.8 else "green" if cat['similarity_score'] > 0.6 else "yellow"
        
        table.add_row(
            str(cat['rank']),
            cat['codigo'],
            cat['descricao'],
            f"[{similarity_color}]{cat['similarity_score']:.4f}[/{similarity_color}]",
            cat['nivel1_nome'][:20] + "..." if len(cat['nivel1_nome']) > 20 else cat['nivel1_nome'],
            cat['nivel2_nome'][:20] + "..." if len(cat['nivel2_nome']) > 20 else cat['nivel2_nome']
        )
    
    console.print(table)
    console.print()  # Linha em branco

def test_categorization(num_samples=5, top_k=10):
    """
    Função principal para testar a categorização automática.
    
    Args:
        num_samples: Número de contratações para testar
        top_k: Número de categorias top a retornar para cada contratação
    """
    # Header com Rich
    console.print("\n" + "="*80)
    console.print(Panel.fit(
        "[bold cyan]TESTE DE CATEGORIZAÇÃO AUTOMÁTICA[/bold cyan]",
        border_style="bright_blue"
    ))
    console.print("="*80)
    
    # Informações do teste
    info_text = f"""
[bold green]Data/Hora:[/bold green] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
[bold green]Amostras:[/bold green] {num_samples}
[bold green]Top categorias:[/bold green] {top_k}
"""
    console.print(Panel(info_text, title="ℹ️ Informações do Teste", border_style="green"))
    
    # Conecta ao banco
    with console.status("[bold green]Conectando ao banco de dados...") as status:
        engine = create_engine_connection()
        if not engine:
            console.print("[bold red]❌ Falha na conexão com o banco de dados![/bold red]")
            return
    
    try:
        # Carrega dados
        with console.status("[bold blue]Carregando contratações aleatórias...") as status:
            contracts_df = load_random_contracts(engine, num_samples)
            if contracts_df is None or len(contracts_df) == 0:
                console.print("[bold red]❌ Nenhuma contratação encontrada com embeddings![/bold red]")
                return
        
        console.print(f"[bold green]✅ Carregadas {len(contracts_df)} contratações com embeddings[/bold green]")
        
        # Processa cada contratação
        for idx, contract in contracts_df.iterrows():
            console.print("\n" + "-"*80)
            
            # Exibe detalhes da contratação
            display_contract_details(contract, idx + 1, len(contracts_df))
            
            # Converte embedding da contratação
            with console.status("[bold yellow]Processando embedding da contratação..."):
                contract_embedding = parse_embedding(contract['embedding_vector'])
                if contract_embedding is None:
                    console.print("[bold red]❌ Erro ao processar embedding da contratação![/bold red]")
                    continue
            
            # Realiza busca semântica de categorias
            with console.status("[bold blue]Buscando categorias similares..."):
                top_categories = semantic_categorization_search(
                    contract_embedding,
                    engine,
                    top_k
                )
            
            if not top_categories:
                console.print("[bold red]❌ Erro ao calcular similaridades![/bold red]")
                continue
            
            # Calcula confiança
            scores = [cat['similarity_score'] for cat in top_categories]
            confidence = calculate_confidence(scores)
            
            # Exibe resultados em tabela
            display_categories_table(top_categories, confidence)
    
    except Exception as e:
        console.print(f"[bold red]❌ Erro durante o teste: {e}[/bold red]")
    
    finally:
        # Finalização
        console.print("\n" + "="*80)
        console.print(Panel.fit(
            "[bold green]✅ TESTE CONCLUÍDO[/bold green]",
            border_style="bright_green"
        ))
        console.print("="*80)

def main():
    """Função principal."""
    console.print(Panel.fit(
        "[bold cyan]🔍 Script de Teste de Categorização Automática[/bold cyan]",
        border_style="bright_cyan"
    ))
    
    try:
        # Solicita parâmetros do usuário
        console.print("\n[bold yellow]⚙️ Configuração dos Parâmetros[/bold yellow]")
        
        num_samples_input = console.input("[green]Número de contratações para testar (padrão: 5): [/green]").strip()
        if not num_samples_input:
            num_samples = 5
        else:
            num_samples = int(num_samples_input)
        
        top_k_input = console.input("[green]Número de categorias top para retornar (padrão: 10): [/green]").strip()
        if not top_k_input:
            top_k = 10
        else:
            top_k = int(top_k_input)
        
        # Confirmação dos parâmetros
        params_text = f"""
[bold blue]Contratações:[/bold blue] {num_samples}
[bold blue]Top categorias:[/bold blue] {top_k}
"""
        console.print(Panel(params_text, title="📋 Parâmetros Confirmados", border_style="blue"))
        
        # Executa teste
        test_categorization(num_samples, top_k)
        
    except KeyboardInterrupt:
        console.print("\n[bold red]⚠️ Teste interrompido pelo usuário.[/bold red]")
    except ValueError as e:
        console.print(f"\n[bold red]❌ Erro nos parâmetros: {e}[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro inesperado: {e}[/bold red]")

if __name__ == "__main__":
    main()
