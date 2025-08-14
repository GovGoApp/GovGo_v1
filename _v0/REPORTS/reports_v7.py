#### REPORTS v7: Versão com Preview de Dados

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from openai import OpenAI
from rich.table import Table

# Configuração da chave da API OpenAI (substitua pela sua)
client = OpenAI(api_key="")

# Criação da thread – o histórico é acumulado
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"  # Substitua pelo ID do seu assistente

# Caminhos para o banco e diretórios para relatórios
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

console = Console()

def debug_thread_messages():
    """Exibe todo o histórico de mensagens da thread para debug."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    console.print("[bold magenta]Histórico da Thread:[/bold magenta]")
    for idx, msg in enumerate(messages):
        console.print(f"[{idx}] {msg.role}: {msg.content}")
    console.print("[bold magenta]Fim do histórico[/bold magenta]\n")

def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=formatted_content
    )
    

def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    # Se desejar, você pode forçar o assistente a ignorar parte do contexto adicionando
    # uma instrução como "Considere somente a última mensagem." ou similar.
    return client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
        
    )

def extract_sql_from_message(message) -> str:
    """
    Extrai e limpa o SQL do conteúdo da mensagem do assistente.
    Retorna apenas o texto (sem quebras de linha extras).
    """
    blocks = message.content if isinstance(message.content, list) else [message.content]
    sql_parts = []
    for block in blocks:
        if isinstance(block, dict) and "text" in block:
            sql_parts.append(block["text"])
        elif hasattr(block, "text") and hasattr(block.text, "value"):
            sql_parts.append(block.text.value)
        else:
            sql_parts.append(str(block))
    sql_query = " ".join(sql_parts)
    return " ".join(sql_query.replace("\n", " ").split())

def get_latest_assistant_message():
    """Retorna a mensagem do assistente na posição [0] da thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

def generate_sql_from_nl(nl_query: str) -> str:
    """
    Converte uma consulta em linguagem natural em um comando SQL.
    A mensagem do usuário é adicionada à thread e um run é criado.
    """
    send_user_message(nl_query)
    # Opcional: para forçar que o assistente foque apenas na nova consulta, você pode passar
    # uma instrução extra, ex.:
  
    run = poll_run()

    #debug_thread_messages()
    if run.status == 'completed':
        last_message = get_latest_assistant_message()
        if not last_message:
            console.print("[bold red]Nenhuma mensagem de assistente recebida.[/bold red]")
            return None
        extracted_sql = extract_sql_from_message(last_message)
        return extracted_sql
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return None

from rich.table import Table

def execute_report(sql: str):
    """
    Executa o comando SQL na base de dados e salva o resultado em um arquivo Excel,
    exibindo um progresso durante a execução e mostrando uma visualização do resultado.
    """
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Executando Query...", total=1)
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(REPORTS_PATH, f"report_{timestamp}.xlsx")
            df.to_excel(output_file, index=False)
            progress.advance(task)
        console.print(f"[bold green]Relatório salvo com sucesso em:[/bold green] {output_file}")

        # Exibir preview do resultado: 10 primeiras linhas e 7 primeiras colunas
        preview_df = df.iloc[:10, :7] # Ajuste o número de linhas e colunas conforme necessário
        table = Table(show_header=True, header_style="bold magenta")
        # Adiciona as colunas ao table
        for col in preview_df.columns:
            table.add_column(str(col))
        # Adiciona as linhas do dataframe
        for _, row in preview_df.iterrows():
            table.add_row(*[str(value) for value in row])
        console.print("\n[bold blue]Preview dos dados:[/bold blue]")
        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Erro ao executar a query:[/bold red] {e}")

def conversation_loop():
    """
    Loop de conversa que continua até que o usuário digite 'ESC'.
    A cada nova consulta, o assistente gera um comando SQL, que é exibido.
    O usuário pode optar por executar a query ou não.
    O histórico da thread é mantido.
    """
    console.print("[bold green]Bem-vindo ao assistente PNCP_AI![/bold green]")
    console.print("Digite sua consulta em linguagem natural e pressione Enter.\n\n")
    
    while True:
        console.print("[bold green]Consulta:[/bold green]")
        nl_query = input() #("Consulta: ") 
        if not nl_query.strip():
            continue
        
        # Gera o SQL com base na consulta, mantendo o contexto
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Gerando SQL...", total=1)
            sql_query = generate_sql_from_nl(nl_query)
            progress.advance(task)
        
        if sql_query is None:
            console.print("[bold red]Falha ao gerar SQL. Tente novamente.[/bold red]")
            continue
        
        console.print("\n[bold green]SQL Gerado:[/bold green]")
        console.print(sql_query)
        
        choice = input("\nDeseja executar a query? (S/N): ")
        if choice.strip().upper() == "S":
            execute_report(sql_query)
        else:
            console.print("[bold yellow]Query não executada. Continuando a conversa...[/bold yellow]\n")
        
        # Debug: exibe o histórico atual da thread
        #debug_thread_messages()

def main():
    conversation_loop()

if __name__ == '__main__':
    main()
