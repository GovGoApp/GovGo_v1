"""
GvG_SP_Search_Terminal_v1.py
Versão 1.0 - Sistema de busca terminal usando Rich
- Busca semântica, por palavras-chave e híbrida no Supabase
- Interface de terminal com formatação Rich e progress bars
- Exportação para Excel com timestamp
- Pré-processamento configurável de texto
- Usa funções centralizadas de gvg_search_utils
"""

import os
import sys
import pandas as pd
import time
import locale
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm

# Configurações padrão
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

# Importar funções de busca (agora de gvg_search_utils)
try:
    from gvg_search_utils import (
        create_connection,
        semantic_search,
        keyword_search,
        hybrid_search,
        calculate_confidence,
        format_currency,
        test_connection,
        get_embedding
    )
except ImportError:
    print("ERRO: Não foi possível importar as funções de busca de gvg_search_utils.")
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

# Configurações de busca
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
RESULTS_PATH = BASE_PATH + "GvG\\SS\\RESULTADOS\\"

# Constantes para configuração de busca
MIN_RESULTS = 5      # Número mínimo de resultados que serão retornados
MAX_RESULTS = 10     # Número máximo de resultados que serão retornados

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
        
        # Formatar valor usando função de gvg_search_utils
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
            f"[bold cyan]Órgão:[/bold cyan] {details.get('orgaoentidade_razaosocial', 'N/A')}",
            f"[bold cyan]Unidade:[/bold cyan] {details.get('unidadeorgao_nomeunidade', 'N/A')}",
            f"[bold cyan]Local:[/bold cyan] {details.get('unidadeorgao_municipionome', 'N/A')}/{details.get('unidadeorgao_ufsigla', 'N/A')}",
            f"[bold cyan]Valor:[/bold cyan] {format_currency(details.get('valortotalhomologado', 0))}",
            f"[bold cyan]Datas:[/bold cyan] Abertura: {details.get('dataaberturaproposta', 'N/A')} | Encerramento: {details.get('dataencerramentoproposta', 'N/A')}",
            f"[bold cyan]Descrição:[/bold cyan] {descricao[:100]}..."
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

def perform_search(query, search_type_id):
    """Realiza a busca de acordo com o tipo selecionado usando funções de gvg_search_utils"""
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
        
        try:
            # Usar funções importadas de gvg_search_utils
            if search_type_id == 1:
                # Busca semântica
                results, confidence = semantic_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS)
            elif search_type_id == 2:
                # Busca por palavras-chave
                results, confidence = keyword_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS)
            elif search_type_id == 3:
                # Busca híbrida
                results, confidence = hybrid_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS, semantic_weight=SEMANTIC_WEIGHT)
            else:
                # Tipo inválido, usar semântica por padrão
                results, confidence = semantic_search(processed_query, limit=MAX_RESULTS, min_results=MIN_RESULTS)
            
            progress.update(task, advance=1)
            
        except Exception as e:
            console.print(f"[bold red]Erro durante a busca: {str(e)}[/bold red]")
            results, confidence = [], 0.0
    
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
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE v1.0 (Refatorado)[/bold magenta]",
        subtitle="[bold cyan]Semântica, Palavras-chave e Híbrida - Usando gvg_search_utils[/bold cyan]",
        expand=False
    ))
    
    # Verificar conexão com o banco usando função de gvg_search_utils
    console.print("[blue]Testando conexão com o banco de dados...[/blue]")
    if not test_connection():
        console.print("[bold red]Não foi possível conectar ao banco de dados. Verifique:")
        console.print("1. Se o arquivo 'supabase_v0.env' está presente")
        console.print("2. Se as credenciais estão corretas")
        console.print("3. Se as tabelas 'contratacoes' e 'contratacoes_embeddings' existem")
        console.print("Encerrando.[/bold red]")
        return
    
    console.print("[green]✓ Conexão com banco de dados estabelecida com sucesso![/green]")
    
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