"""
GvG_SP_Search_Terminal_v2.py
Versão 2.0 - Sistema de busca terminal com funcionalidades avançadas
- Todas as funcionalidades do v1 mantidas
- Busca e listagem de documentos PNCP por processo
- Geração de palavras-chave via OpenAI GPT
- Sumarização automática de documentos
- Menu contextual (opções aparecem só quando há resultados)
- Links clicáveis para documentos no terminal
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
        get_embedding,
        parse_numero_controle_pncp,
        fetch_documentos,
        generate_keywords,
        summarize_document
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

def show_process_documents(process_number):
    """Mostra documentos de um processo específico"""
    if not last_results or process_number < 1 or process_number > len(last_results):
        console.print("[red]Número de processo inválido![/red]")
        return
    
    result = last_results[process_number - 1]
    details = result.get("details", {})
    
    # Tentar diferentes campos possíveis para o número de controle PNCP
    numero_controle = None
    possible_fields = [
        'numero_controle_pncp',
        'numerocontrolepncp', 
        'id',
        'numero_processo',
        'numeroprocesso'
    ]
    
    for field in possible_fields:
        if field in details and details[field]:
            numero_controle = details[field]
            break
    
    # Debug: mostrar todos os campos disponíveis se não encontrar
    if not numero_controle:
        console.print("[yellow]Debug - Campos disponíveis no resultado:[/yellow]")
        console.print(f"[dim]Details keys: {list(details.keys())}[/dim]")
        console.print(f"[dim]Result keys: {list(result.keys())}[/dim]")
        
        # Tentar usar o ID do resultado principal
        if 'id' in result and result['id']:
            numero_controle = result['id']
        else:
            console.print("[red]Número de controle PNCP não encontrado para este processo.[/red]")
            return
    
    console.print(f"\n[bold cyan]Processo Selecionado: #{process_number} - {numero_controle}[/bold cyan]")
    console.print(f"\n[bold green]Buscando documentos para: {numero_controle}[/bold green]")
    
    try:
        with console.status("[bold green]Carregando documentos..."):
            documentos = fetch_documentos(numero_controle)
        
        if not documentos:
            console.print("[yellow]Nenhum documento encontrado para este processo.[/yellow]")
            return
        
        console.print(f"\n[bold green]Links diretos para os documentos:[/bold green]")
        for i, doc in enumerate(documentos, 1):
            titulo = doc.get('titulo', 'Documento sem título')
            url = doc.get('url', 'N/A')
            
            # Criar hyperlink clicável (funciona na maioria dos terminais modernos)
            hyperlink = f"[link={url}]{url}[/link]"
            console.print(f"[bold cyan]{i}.[/bold cyan] {titulo}")
            console.print(f"   {hyperlink}")
            console.print()
        
        # Opções para sumarização
        while True:
            console.print("\n[bold yellow]Opções:[/bold yellow]")
            console.print("Digite o número do documento para sumarizar (1-{})".format(len(documentos)))
            console.print("Digite 0 para voltar")
            
            choice = input("> ").strip()
            
            if choice == "0":
                break
            
            try:
                doc_num = int(choice)
                if 1 <= doc_num <= len(documentos):
                    doc = documentos[doc_num - 1]
                    doc_url = doc.get('url')
                    doc_title = doc.get('titulo', 'Documento')
                    
                    if doc_url:
                        console.print(f"\n[bold green]Sumarizando: {doc_title}[/bold green]")
                        console.print(f"[dim]URL: {doc_url}[/dim]")
                        
                        with console.status("[bold green]Gerando resumo..."):
                            summary = summarize_document(doc_url)
                        
                        # Exibir resumo em painel
                        panel = Panel(
                            summary,
                            title=f"Resumo: {doc_title}",
                            border_style="green"
                        )
                        console.print(panel)
                    else:
                        console.print("[red]URL do documento não disponível.[/red]")
                else:
                    console.print("[red]Número inválido![/red]")
            except ValueError:
                console.print("[red]Digite apenas números![/red]")
    
    except Exception as e:
        console.print(f"[red]Erro ao buscar documentos: {str(e)}[/red]")

def generate_process_keywords(process_number):
    """Gera palavras-chave da descrição de um processo específico"""
    if not last_results or process_number < 1 or process_number > len(last_results):
        console.print("[red]Número de processo inválido![/red]")
        return
    
    result = last_results[process_number - 1]
    details = result.get("details", {})
    
    # Tentar diferentes campos possíveis para o número de controle PNCP
    numero_controle = None
    possible_fields = [
        'numero_controle_pncp',
        'numerocontrolepncp', 
        'id',
        'numero_processo',
        'numeroprocesso'
    ]
    
    for field in possible_fields:
        if field in details and details[field]:
            numero_controle = details[field]
            break
    
    # Se não encontrou nos details, tentar no result principal
    if not numero_controle and 'id' in result and result['id']:
        numero_controle = result['id']
    
    if not numero_controle:
        numero_controle = 'N/A'
    
    descricao = details.get('descricaocompleta', '')
    
    if not descricao or descricao.strip() == '':
        console.print("[yellow]Descrição não disponível para gerar palavras-chave.[/yellow]")
        return
    
    console.print(f"\n[bold green]Gerando palavras-chave para: {numero_controle}[/bold green]")
    
    try:
        with console.status("[bold green]Gerando palavras-chave..."):
            keywords = generate_keywords(descricao)
        
        # Exibir palavras-chave em painel
        panel_content = f"""
[bold cyan]Processo:[/bold cyan] {numero_controle}

[bold yellow]Descrição Original:[/bold yellow]
{descricao[:300]}{'...' if len(descricao) > 300 else ''}

[bold green]Palavras-chave Geradas:[/bold green]
{keywords}
        """
        
        panel = Panel(
            panel_content,
            title="Palavras-chave do Processo",
            border_style="green"
        )
        console.print(panel)
    
    except Exception as e:
        console.print(f"[red]Erro ao gerar palavras-chave: {str(e)}[/red]")

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
    
    # Só mostrar opções dependentes de resultados SE houver resultados
    if last_results:
        console.print("[cyan]2[/cyan] - Exportar últimos resultados para Excel")
        console.print("[cyan]3[/cyan] - Ver documentos de um processo específico")
        console.print("[cyan]4[/cyan] - Gerar palavras-chave de um processo específico")
        console.print("[cyan]5[/cyan] - Encerrar o programa")
        console.print(f"\n[dim]Última busca: \"{last_query}\" - {len(last_results)} resultados encontrados[/dim]")
    else:
        console.print("[cyan]2[/cyan] - Encerrar o programa")
        console.print("\n[dim]Nenhuma busca realizada ainda[/dim]")
    
    console.print("\n[cyan]Digite qualquer outro texto para realizar uma nova busca[/cyan]")


def main():
    """Função principal do programa"""
    global current_search_type
    
    console.print(Panel(
        "[bold cyan]Conecta ao Supabase e realiza diferentes tipos de busca[/bold cyan]",
        title="[bold magenta]SISTEMA DE BUSCA GOVGO SUPABASE v2.0[/bold magenta]",
        subtitle="[bold cyan]Semântica, Palavras-chave e Híbrida[/bold cyan]",
        expand=False,
        width=80
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
        
        # Se há resultados, usar numeração completa
        elif last_results:
            if query == "2":
                # Exportar resultados para Excel
                export_results_to_excel(last_results, last_query, current_search_type)
                continue
            
            elif query == "3":
                # Ver documentos de um processo específico
                console.print(f"\n[yellow]Processos disponíveis: 1 a {len(last_results)}[/yellow]")
                process_choice = input("Digite o número do processo: ").strip()
                try:
                    process_num = int(process_choice)
                    show_process_documents(process_num)
                except ValueError:
                    console.print("[red]Digite apenas números![/red]")
                continue
                
            elif query == "4":
                # Gerar palavras-chave de um processo específico
                console.print(f"\n[yellow]Processos disponíveis: 1 a {len(last_results)}[/yellow]")
                process_choice = input("Digite o número do processo: ").strip()
                try:
                    process_num = int(process_choice)
                    generate_process_keywords(process_num)
                except ValueError:
                    console.print("[red]Digite apenas números![/red]")
                continue
                
            elif query == "5":
                # Sair do programa
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo![/bold green]")
                return
        
        # Se NÃO há resultados, usar numeração simplificada
        else:
            if query == "2":
                # Sair do programa
                console.print("\n[bold green]Obrigado por usar o sistema de busca GovGo![/bold green]")
                return
            
        # Verificar consulta vazia
        if not query:
            console.print("[yellow]Consulta vazia. Tente novamente.[/yellow]")
            continue
            
        # Se chegou aqui, realizar busca normal
        perform_search(query, current_search_type)
        
if __name__ == "__main__":
    main()
    