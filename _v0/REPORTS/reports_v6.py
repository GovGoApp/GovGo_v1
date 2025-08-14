import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from openai import OpenAI

# Configuração da chave da API OpenAI (substitua pela sua)
client = OpenAI( api_key="")
    
# Criação da thread – a mesma thread mantém o histórico de conversa
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"

# Caminhos para o banco e diretórios para relatórios
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

console = Console()

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
    # Remove quebras de linha e espaços extras
    return " ".join(sql_query.replace("\n", " ").split())

def get_latest_assistant_message():
    """Retorna a última mensagem enviada pelo assistente na thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[-1] if assistant_messages else None

def generate_sql_from_nl(nl_query: str) -> str:
    """
    Converte uma consulta em linguagem natural em um comando SQL.
    A mensagem do usuário é adicionada à thread e um run é criado.
    """
    console.print(f"[bold blue]QUERY : {nl_query}\n\n[/bold blue]")
    
    send_user_message(nl_query)
    # Instrução padrão para transformar a consulta em SQL
    run = poll_run()
    if run.status == 'completed':
        last_message = get_latest_assistant_message()
        console.print(f"[bold blue]Last Message: {last_message.content}[/bold blue]")
        console.print(f"[bold blue]Run status: {run.status}[/bold blue]")
        if not last_message:
            console.print("[bold red]Nenhuma mensagem de assistente recebida.[/bold red]")
            return None
        return extract_sql_from_message(last_message)
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return None

def execute_report(sql: str):
    """
    Executa o comando SQL na base de dados e salva o resultado em um arquivo Excel.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(REPORTS_PATH, f"report_{timestamp}.xlsx")
        df.to_excel(output_file, index=False)
        console.print(f"[bold green]Relatório salvo em:[/bold green] {output_file}")
    except Exception as e:
        console.print(f"[bold red]Erro ao executar a query:[/bold red] {e}")

def conversation_loop():
    """
    Loop de conversa que continua até que o usuário digite 'ESC'.
    A cada nova consulta, o assistente gera um comando SQL, que é exibido.
    O usuário pode optar por executar a query ou não.
    """
    console.print("[bold green]Bem-vindo ao assistente PNCP_AI![/bold green]")
    console.print("[bold green]Digite sua consulta em linguagem natural e pressione Enter.[/bold green]\n")
    
    while True:
        nl_query = input("Consulta: ")
        if nl_query.strip().upper() == "ESC":
            console.print("[bold green]Encerrando o assistente. Até logo![/bold green]")
            break
        if not nl_query.strip():
            continue


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
        
        # A conversa é contínua; o usuário pode inserir uma nova consulta e o contexto é mantido na thread.

def main():
    conversation_loop()

if __name__ == '__main__':
    main()
