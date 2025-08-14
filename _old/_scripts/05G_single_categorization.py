# =======================================================================
# [05G] FUNÇÃO DE CATEGORIZAÇÃO INDIVIDUAL
# =======================================================================
# Função para categorizar um único numero_controle_pncp usando a mesma
# lógica do 05 original, mas de forma isolada e testável.
# =======================================================================

import os
import sys
import time
import json
import math
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rich.console import Console

# Configure Rich console
console = Console()

def log_message(message, log_type="info"):
    """Log padronizado"""
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'port': os.getenv('SUPABASE_PORT', 5432)
}

# Configurações
TOP_K = 5

def create_connection():
    """Cria conexão com o banco PostgreSQL/Supabase"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        log_message(f"Erro ao conectar ao banco: {e}", "error")
        return None

def calculate_confidence(similarities):
    """Calcula o nível de confiança baseado na diferença entre as similaridades"""
    if len(similarities) < 2:
        return 0.0
    
    top_score = similarities[0]
    
    if top_score == 0.0:
        return 0.0
    
    # Calcular gaps entre scores
    gaps = [top_score - score for score in similarities[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = (1 - math.exp(-10 * weighted_gap))
    
    return round(confidence, 4)

def categorize_single_contract(numero_controle_pncp):
    """
    FUNÇÃO 05G: Categoriza um único numero_controle_pncp
    
    Usa exatamente a mesma lógica do 05 original:
    1. Busca o embedding do contrato
    2. Faz busca pgvector nas categorias
    3. Calcula confidence
    4. Atualiza contratacao_emb
    
    Args:
        numero_controle_pncp (str): Número de controle a ser categorizado
        
    Returns:
        dict: Resultado da categorização com status, categorias encontradas, etc.
    """
    log_message(f"🎯 Categorizando contrato: {numero_controle_pncp}", "info")
    
    connection = create_connection()
    if not connection:
        return {
            'success': False,
            'error': 'Falha na conexão com banco de dados',
            'numero_controle_pncp': numero_controle_pncp
        }
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # PASSO 1: Buscar embedding do contrato
        log_message(f"📋 Buscando embedding para {numero_controle_pncp}...", "debug")
        
        embedding_query = """
        SELECT 
            id_contratacao_emb,
            numero_controle_pncp,
            embeddings
        FROM contratacao_emb 
        WHERE numero_controle_pncp = %s
        AND embeddings IS NOT NULL
        """
        
        cursor.execute(embedding_query, (numero_controle_pncp,))
        embedding_result = cursor.fetchone()
        
        if not embedding_result:
            cursor.close()
            connection.close()
            return {
                'success': False,
                'error': 'Embedding não encontrado para este contrato',
                'numero_controle_pncp': numero_controle_pncp
            }
        
        log_message(f"✅ Embedding encontrado (ID: {embedding_result['id_contratacao_emb']})", "debug")
        
        # PASSO 2: Buscar TOP K categorias usando pgvector (igual ao 05)
        log_message(f"🔍 Buscando categorias similares...", "debug")
        
        search_query = """
        SELECT 
            cod_cat,
            nom_cat,
            1 - (cat_embeddings <=> %s::vector) AS similarity
        FROM categoria
        WHERE cat_embeddings IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, (embedding_result['embeddings'], TOP_K))
        category_results = cursor.fetchall()
        
        if not category_results:
            cursor.close()
            connection.close()
            return {
                'success': False,
                'error': 'Nenhuma categoria encontrada',
                'numero_controle_pncp': numero_controle_pncp
            }
        
        log_message(f"✅ Encontradas {len(category_results)} categorias", "debug")
        
        # PASSO 3: Extrair códigos e similaridades
        top_categories = [row['cod_cat'] for row in category_results]
        top_similarities = [round(float(row['similarity']), 4) for row in category_results]
        
        # PASSO 4: Calcular confiança
        confidence = calculate_confidence(top_similarities)
        
        log_message(f"📊 Melhor categoria: {top_categories[0]} (similaridade: {top_similarities[0]}, confiança: {confidence})", "info")
        
        # PASSO 5: Atualizar contratacao_emb (igual ao 05)
        log_message(f"💾 Atualizando banco de dados...", "debug")
        
        update_embedding_query = """
            UPDATE contratacao_emb 
            SET 
                top_categories = %s,
                top_similarities = %s,
                confidence = %s
            WHERE id_contratacao_emb = %s
        """
        
        cursor.execute(update_embedding_query, (
            top_categories,
            top_similarities,
            confidence,
            embedding_result['id_contratacao_emb']
        ))
        
        # Commit das alterações
        connection.commit()
        cursor.close()
        connection.close()
        
        log_message(f"✅ Contrato {numero_controle_pncp} categorizado com sucesso!", "success")
        
        return {
            'success': True,
            'numero_controle_pncp': numero_controle_pncp,
            'id_contratacao_emb': embedding_result['id_contratacao_emb'],
            'top_categories': top_categories,
            'top_similarities': top_similarities,
            'confidence': confidence,
            'best_category': top_categories[0],
            'best_similarity': top_similarities[0]
        }
        
    except Exception as e:
        log_message(f"❌ Erro ao categorizar {numero_controle_pncp}: {e}", "error")
        connection.rollback()
        connection.close()
        return {
            'success': False,
            'error': str(e),
            'numero_controle_pncp': numero_controle_pncp
        }

def get_last_categorization_date():
    """Obtém a última data de categorização do system_config"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT value FROM system_config 
            WHERE key = 'last_categorization_date'
        """)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return result[0]
        else:
            return "20250101"
            
    except Exception as e:
        log_message(f"Erro ao obter última data de categorização: {e}", "error")
        connection.close()
        return "20250101"

def get_first_contract_after_date(date_str):
    """
    Busca o primeiro contrato da data posterior à last_categorization_date
    para teste da função 05G
    """
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Converter data de YYYYMMDD para YYYY-MM-DD e adicionar 1 dia
        from datetime import datetime, timedelta
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        next_date_obj = date_obj + timedelta(days=1)
        next_date_formatted = next_date_obj.strftime('%Y-%m-%d')
        
        log_message(f"🔍 Buscando primeiro contrato da data {next_date_obj.strftime('%d/%m/%Y')}...", "info")
        
        # Buscar primeiro contrato da próxima data
        query = """
        SELECT numero_controle_pncp 
        FROM contratacao 
        WHERE data_publicacao_pncp IS NOT NULL
        AND DATE(data_publicacao_pncp) = %s::date
        LIMIT 1
        """
        
        cursor.execute(query, (next_date_formatted,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            numero_controle = result[0]
            log_message(f"✅ Primeiro contrato encontrado: {numero_controle}", "success")
            return numero_controle
        else:
            log_message(f"⚠️  Nenhum contrato encontrado na data {next_date_obj.strftime('%d/%m/%Y')}", "warning")
            return None
            
    except Exception as e:
        log_message(f"❌ Erro ao buscar primeiro contrato: {e}", "error")
        connection.close()
        return None

if __name__ == "__main__":
    """Teste da função 05G"""
    
    console.print("\n[bold blue]═══════════════════════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]             🧪 TESTE DA FUNÇÃO 05G - CATEGORIZAÇÃO INDIVIDUAL      [/bold blue]") 
    console.print("[bold blue]═══════════════════════════════════════════════════════════════════[/bold blue]\n")
    
    # PASSO 1: Obter última data de categorização
    log_message("📅 Obtendo última data de categorização...", "info")
    last_date = get_last_categorization_date()
    log_message(f"Última data de categorização: {last_date}", "info")
    
    # PASSO 2: Buscar primeiro contrato da próxima data
    first_contract = get_first_contract_after_date(last_date)
    
    if not first_contract:
        log_message("❌ Não foi possível encontrar um contrato para testar", "error")
        sys.exit(1)
    
    # PASSO 3: Testar a função 05G
    console.print(f"\n[bold yellow]🎯 TESTANDO CATEGORIZAÇÃO DO CONTRATO: {first_contract}[/bold yellow]\n")
    
    start_time = time.time()
    result = categorize_single_contract(first_contract)
    end_time = time.time()
    
    # PASSO 4: Exibir resultado
    console.print(f"\n[bold cyan]📊 RESULTADO DA CATEGORIZAÇÃO:[/bold cyan]")
    console.print("-" * 60)
    
    if result['success']:
        console.print(f"[green]✅ STATUS: SUCESSO[/green]")
        console.print(f"[white]📄 Contrato: {result['numero_controle_pncp']}[/white]")
        console.print(f"[white]🔢 ID Embedding: {result['id_contratacao_emb']}[/white]")
        console.print(f"[white]🏆 Melhor Categoria: {result['best_category']}[/white]")
        console.print(f"[white]📈 Similaridade: {result['best_similarity']:.4f}[/white]")
        console.print(f"[white]🎯 Confiança: {result['confidence']:.4f}[/white]")
        console.print(f"[white]⏱️  Tempo: {end_time - start_time:.2f}s[/white]")
        
        console.print(f"\n[cyan]🔝 TOP {len(result['top_categories'])} CATEGORIAS:[/cyan]")
        for i, (cat, sim) in enumerate(zip(result['top_categories'], result['top_similarities'])):
            console.print(f"[white]  {i+1}. {cat} - {sim:.4f}[/white]")
            
    else:
        console.print(f"[red]❌ STATUS: ERRO[/red]")
        console.print(f"[red]📄 Contrato: {result['numero_controle_pncp']}[/red]")
        console.print(f"[red]⚠️  Erro: {result['error']}[/red]")
    
    console.print("\n[bold blue]═══════════════════════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]                         🏁 TESTE CONCLUÍDO                        [/bold blue]")
    console.print("[bold blue]═══════════════════════════════════════════════════════════════════[/bold blue]\n")
