import os
import pandas as pd
import sqlite3
import json
from datetime import datetime
import time
from openai import OpenAI
import re
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.traceback import install

# Instalar o formatador de traceback do rich
install(show_locals=True)

# Console para saída formatada
console = Console()

# Variável de controle para debug
DEBUG = True

# Função auxiliar para logs de debug com rich
def debug_print(message, style="blue"):
    """Imprime mensagens de debug formatadas com rich."""
    if DEBUG:
        console.print(f"[bold blue][DEBUG][/bold blue] {message}", style=style)

def success_print(message):
    """Imprime mensagens de sucesso formatadas."""
    console.print(f"[bold green]✓[/bold green] {message}")

def error_print(message, exception=None):
    """Imprime mensagens de erro formatadas."""
    console.print(f"[bold red]✗[/bold red] {message}", style="red")
    if exception and DEBUG:
        console.print(Panel(traceback.format_exc(), title="Erro Detalhado", border_style="red"))

def info_print(message, style="bold cyan"):
    """Imprime mensagens informativas destacadas."""
    console.print(f"[info]{message}[/info]", style=style)

# Base paths e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
EXCEL_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CLASSY\\CLASSY_ITENS\\OUTPUT_ITENS\\ESTUDOS\\P176\\RESULTADOS_NV3\\RESULTADOS_OUTPUT_ITEM_176_H1_D9_5_5_5_0_1_1.xlsx"
VALIDATION_PATH = os.path.join(BASE_PATH, "CLASSY", "CLASSY_ITENS", "VALIDATION")
os.makedirs(VALIDATION_PATH, exist_ok=True)

# Criar arquivo de resultados de validação com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
VALIDATION_FILE = os.path.join(VALIDATION_PATH, f"p176_validation_{TIMESTAMP}.xlsx")

# OpenAI configuration
client = OpenAI(api_key="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")

# ID do assistente CLASSY_VALIDATOR
assistant_id = "asst_mnqJ7xzDWphZXH18aOazymct"

# Criar um novo thread para a conversa
thread = client.beta.threads.create()
debug_print(f"Thread criado: {thread.id}")

# ===== FUNÇÕES DO ASSISTENTE (adaptadas de gvg_CL_reports_v3) =====

def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    debug_print(f"Enviando mensagem para thread [bold yellow]{thread.id[:8]}...[/bold yellow]: '{content[:100]}...'")
    formatted_content = [{"type": "text", "text": content}]
    try:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=formatted_content
        )
        debug_print("Mensagem enviada com sucesso", style="green")
    except Exception as e:
        error_print(f"Erro ao enviar mensagem", e)
        raise

def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    debug_print(f"Iniciando run para thread [bold yellow]{thread.id[:8]}...[/bold yellow]")
    try:
        with console.status("[bold green]Aguardando resposta do assistente...", spinner="dots"):
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant_id,
            )
        debug_print(f"Run finalizado com status: [bold {'green' if run.status == 'completed' else 'red'}]{run.status}[/]")
        return run
    except Exception as e:
        error_print("Erro no poll_run", e)
        raise

def get_latest_assistant_message():
    """Retorna a mensagem do assistente na posição [0] da thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

def get_assistant_response(user_query: str, max_retries=3):
    """
    Função genérica para enviar uma consulta ao assistente e obter sua resposta.
    Retorna o conteúdo da resposta ou None em caso de erro.
    """
    debug_print(f"Solicitando resposta para query: '{user_query[:100]}...'")
    
    for attempt in range(max_retries):
        try:
            send_user_message(user_query)
            run = poll_run()
            if run.status == 'completed':
                last_message = get_latest_assistant_message()
                if not last_message:
                    debug_print("Nenhuma mensagem de assistente recebida.", style="yellow")
                    return None
                debug_print("Resposta do assistente recebida com sucesso", style="green")
                return last_message
            else:
                debug_print(f"Run status não é 'completed': [bold red]{run.status}[/]", style="yellow")
                if attempt < max_retries - 1:
                    retry_msg = f"Tentando novamente ({attempt+2}/{max_retries})..."
                    debug_print(retry_msg, style="yellow")
                    time.sleep(2)  # Pequeno atraso antes de tentar novamente
                else:
                    return None
        except Exception as e:
            error_print(f"Erro ao obter resposta do assistente", e)
            if attempt < max_retries - 1:
                retry_msg = f"Tentando novamente ({attempt+2}/{max_retries})..."
                debug_print(retry_msg, style="yellow")
                time.sleep(2)  # Pequeno atraso antes de tentar novamente
            else:
                return None

def extract_content_from_message(message):
    """Extrai o texto completo da resposta da mensagem do assistente."""
    try:
        if message is None:
            return ""
            
        content = message.content
        if not content:
            return ""
            
        text_parts = []
        for part in content:
            if hasattr(part, 'text') and hasattr(part.text, 'value'):
                text_parts.append(part.text.value)
            elif isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
        
        return ''.join(text_parts)
    except Exception as e:
        error_print(f"Erro ao extrair conteúdo da mensagem", e)
        return ""

def extract_choices_from_response(response_text):
    """Extrai a lista de índices da resposta do assistente."""
    debug_print(f"Extraindo escolhas da resposta: {response_text}")
    try:
        # Procurar por um padrão de lista no formato [n, n, ...]
        match = re.search(r'\[[\d,\s]*\]', response_text)
        if match:
            # Extrair a parte que corresponde à lista
            choices_str = match.group(0)
            # Converter para lista de inteiros usando json.loads
            choices = json.loads(choices_str)
            debug_print(f"Escolhas extraídas: [bold green]{choices}[/]", style="green")
            return choices
        else:
            debug_print("Nenhuma lista de escolhas encontrada na resposta", style="yellow")
            return []
    except Exception as e:
        error_print(f"Erro ao extrair escolhas", e)
        return []

# ===== FUNÇÕES DE CARREGAMENTO E SALVAMENTO DE DADOS =====

def load_data(limit=None):
    """Carrega dados da planilha Excel"""
    info_print(f"Carregando dados da planilha: {EXCEL_PATH}")
    
    try:
        with console.status("[bold green]Carregando dados da planilha...", spinner="dots"):
            # Carregar a planilha Excel
            df = pd.read_excel(EXCEL_PATH, sheet_name='Sheet1')
            
            # Verificar se os campos necessários estão presentes
            required_fields = ['descrição', 'TOP_1', 'TOP_2', 'TOP_3', 'TOP_4', 'TOP_5', 
                              'SCORE_1', 'SCORE_2', 'SCORE_3', 'SCORE_4', 'SCORE_5', 'CONFIDENCE']
            
            # Verificar campos obrigatórios
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                error_print(f"Campos obrigatórios ausentes na planilha: {missing_fields}")
                return pd.DataFrame()
            
            # Adicionar campos que podem estar faltando com valores padrão
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            
            if 'numeroControlePNCP' not in df.columns:
                df['numeroControlePNCP'] = 'N/A'
                
            if 'numeroItem' not in df.columns:
                df['numeroItem'] = 'N/A'
                
            if 'ID_ITEM_CONTRATACAO' not in df.columns:
                df['ID_ITEM_CONTRATACAO'] = range(10001, 10001 + len(df))
                
            if 'item_type' not in df.columns:
                df['item_type'] = 'item'
            
            # Limitar o número de linhas se especificado
            if limit:
                df = df.head(limit)
        
        # Mostrar informações sobre os dados carregados
        success_print(f"Dados carregados: {len(df)} itens da planilha")
        
        # Exibir amostra dos dados
        if DEBUG and len(df) > 0:
            sample_table = Table(title="Amostra de Dados da Planilha", show_header=True, header_style="bold")
            sample_table.add_column("ID_ITEM", style="cyan")
            sample_table.add_column("Descrição", style="green", max_width=40)
            sample_table.add_column("TOP_1", style="magenta", max_width=30)
            
            for _, row in df.head(3).iterrows():
                sample_table.add_row(
                    str(row['ID_ITEM_CONTRATACAO']), 
                    row['descrição'][:40] + ('...' if len(row['descrição']) > 40 else ''), 
                    row['TOP_1'][:30] + ('...' if len(row['TOP_1']) > 30 else '')
                )
            console.print(sample_table)
            
        return df
        
    except Exception as e:
        error_print(f"Erro ao carregar dados da planilha", e)
        return pd.DataFrame()  # Retorna DataFrame vazio em caso de erro

def save_validation_results(validation_results, partial=False):
    """Salva os resultados da validação em um arquivo Excel"""
    if not validation_results:
        error_print("Nenhum resultado para salvar.")
        return False
    
    # Determinar nome do arquivo (parcial ou final)
    file_path = VALIDATION_FILE
    if partial:
        file_path = VALIDATION_FILE.replace('.xlsx', f'_partial_{len(validation_results)}.xlsx')
    
    try:
        with console.status(f"[bold green]Salvando {len(validation_results)} resultados...", spinner="dots"):
            # Salvar em Excel
            results_df = pd.DataFrame(validation_results)
            results_df.to_excel(file_path, index=False)
            
            # Também salvar como JSON para backup
            json_file = file_path.replace('.xlsx', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False)
        
        success_print(f"Resultados salvos em: {file_path}")
        debug_print(f"Backup JSON salvo em: {json_file}")
        
        return True
    except Exception as e:
        error_print(f"Erro ao salvar resultados", e)
        return False

# ===== FUNÇÃO PARA CONSTRUIR O PROMPT =====

def build_prompt(item_data):
    """Constrói o prompt para o assistente no formato especificado"""
    prompt = f"""
**Descrição do Item:**
"{item_data['descrição']}"

**Categorias Sugeridas (com seus índices originais de 0 a 4):**
0: "{item_data['TOP_1']}" (Score: {item_data['SCORE_1']:.4f})
1: "{item_data['TOP_2']}" (Score: {item_data['SCORE_2']:.4f})
2: "{item_data['TOP_3']}" (Score: {item_data['SCORE_3']:.4f})
3: "{item_data['TOP_4']}" (Score: {item_data['SCORE_4']:.4f})
4: "{item_data['TOP_5']}" (Score: {item_data['SCORE_5']:.4f})

**Confiança Geral das Sugestões:** {item_data['CONFIDENCE']:.2f}%
"""
    return prompt

# ===== FUNÇÃO PARA PROCESSAR ITENS =====

def process_items(df, batch_size=None):
    """Processa e valida um lote de itens"""
    validation_results = []
    total_items = len(df) if batch_size is None else min(batch_size, len(df))
    
    info_print(f"Iniciando processamento de {total_items} itens...")
    
    # Configuração da barra de progresso
    progress_columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ]
    
    with Progress(*progress_columns) as progress:
        task = progress.add_task("[cyan]Processando itens...", total=total_items)
        
        for i, (_, item) in enumerate(df.head(total_items).iterrows()):
            item_id = item['ID_ITEM_CONTRATACAO']
            progress.update(task, description=f"[cyan]Processando item {i+1}/{total_items}: {item_id}")
            
            item_data = item.to_dict()
            
            # Exibir detalhes do item atual
            if DEBUG:
                item_panel = Panel(
                    f"[bold]ID:[/] {item_id}\n[bold]Descrição:[/] {item_data['descrição'][:100]}...\n[bold]Confiança:[/] {item_data['CONFIDENCE']:.2f}%",
                    title=f"Item {i+1}/{total_items}",
                    border_style="cyan"
                )
                console.print(item_panel)
            
            # Construir o prompt para o assistente
            prompt = build_prompt(item_data)
            
            # Obter a validação do assistente
            assistant_message = get_assistant_response(prompt)
            
            if assistant_message:
                # Extrair o texto da resposta
                response_text = extract_content_from_message(assistant_message)
                
                # Mostrar resposta truncada em debug
                if DEBUG:
                    response_preview = response_text.strip()[:100] + ('...' if len(response_text) > 100 else '')
                    debug_print(f"Resposta: {response_preview}", style="dim")
                
                # Extrair as escolhas da resposta
                validated_choices_indices = extract_choices_from_response(response_text)
                
                # Mostrar as escolhas de forma visual
                if validated_choices_indices:
                    choices_text = Text()
                    choices_text.append(f"Validação: ")
                    for idx in validated_choices_indices:
                        if 0 <= idx <= 4:
                            category = item_data[f'TOP_{idx+1}']
                            score = item_data[f'SCORE_{idx+1}']
                            choices_text.append(f"[{idx}] ", style=f"bold {'green' if score > 0.7 else 'yellow' if score > 0.4 else 'red'}")
                            choices_text.append(f"{category[:40]}... ", style="dim")
                    console.print(choices_text)
                else:
                    console.print("[yellow]Nenhuma categoria selecionada[/]")
            else:
                error_print("Falha ao obter resposta do assistente")
                validated_choices_indices = []
            
            # Extrair as categorias validadas na ordem correta
            validated_categories = []
            for idx in validated_choices_indices:
                if 0 <= idx <= 4:  # Verificar se o índice é válido
                    category_key = f'TOP_{idx+1}'
                    validated_categories.append(item_data[category_key])
            
            # Montar o registro de validação no mesmo formato que cv_v3.py
            validation_item = {
                'ID': item_data['ID'],
                'numeroControlePNCP': item_data['numeroControlePNCP'],
                'numeroItem': item_data['numeroItem'],
                'ID_ITEM_CONTRATACAO': item_data['ID_ITEM_CONTRATACAO'],
                'descrição': item_data['descrição'],
                'item_type': item_data['item_type'],
                'original_top_1': item_data['TOP_1'],
                'original_top_2': item_data['TOP_2'],
                'original_top_3': item_data['TOP_3'],
                'original_top_4': item_data['TOP_4'],
                'original_top_5': item_data['TOP_5'],
                'original_score_1': item_data['SCORE_1'],
                'original_score_2': item_data['SCORE_2'],
                'original_score_3': item_data['SCORE_3'],
                'original_score_4': item_data['SCORE_4'],
                'original_score_5': item_data['SCORE_5'],
                'original_confidence': item_data['CONFIDENCE'],
                'validated_choices_indices': validated_choices_indices,
                'validated_top_1': validated_categories[0] if len(validated_categories) > 0 else None,
                'validated_top_2': validated_categories[1] if len(validated_categories) > 1 else None,
                'validated_top_3': validated_categories[2] if len(validated_categories) > 2 else None,
                'validated_top_4': validated_categories[3] if len(validated_categories) > 3 else None,
                'validated_top_5': validated_categories[4] if len(validated_categories) > 4 else None,
                'validation_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'validation_method': 'auto_ai'  # Marcar que foi validação automática
            }
            
            validation_results.append(validation_item)
            
            # Salvar resultados parciais a cada 10 itens
            if (i+1) % 10 == 0:
                save_validation_results(validation_results, partial=True)
            
            # Atualizar a barra de progresso
            progress.update(task, advance=1)
    
    return validation_results

# ===== FUNÇÃO PRINCIPAL =====

def main():
    console.print(Panel.fit(
        "[bold cyan]Auto-Validador P176 com CLASSY_VALIDATOR[/]", 
        border_style="blue",
        padding=(1, 10)
    ))
    
    # Carregar dados da planilha
    items_df = load_data()
    
    if len(items_df) == 0:
        error_print("Nenhum item encontrado na planilha!")
        return
    
    # Processar os itens
    validation_results = process_items(items_df)
    
    # Salvar resultados finais
    success = save_validation_results(validation_results)
    
    if success:
        # Mostrar estatísticas finais
        stats_table = Table(title="Estatísticas de Validação", show_header=True, header_style="bold")
        stats_table.add_column("Estatística", style="cyan")
        stats_table.add_column("Valor", style="green")
        
        stats_table.add_row("Total de itens processados", str(len(validation_results)))
        
        # Contar quantos itens têm pelo menos uma categoria validada
        with_validation = len([item for item in validation_results if item.get('validated_top_1') is not None])
        stats_table.add_row("Itens com categorias validadas", f"{with_validation} ({with_validation/len(validation_results)*100:.1f}%)")
        
        # Número médio de categorias selecionadas
        avg_categories = sum(len(item.get('validated_choices_indices', [])) for item in validation_results) / len(validation_results)
        stats_table.add_row("Média de categorias por item", f"{avg_categories:.2f}")
        
        console.print(stats_table)
        
        success_print(f"\nProcessamento concluído. {len(validation_results)} itens validados.")
        info_print(f"Resultados salvos em: {VALIDATION_FILE}")
    else:
        error_print("\nErro ao salvar os resultados!")

if __name__ == "__main__":
    main()