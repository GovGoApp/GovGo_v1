import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from openai import OpenAI

# Configuração da chave da API OpenAI (substitua pela sua)
client = OpenAI(api_key="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")

# Criação do thread
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"

# Caminhos da base e diretórios para relatórios
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

console = Console()

def send_user_message(content):
    """
    Envia uma mensagem para a thread formatando o conteúdo como uma lista de blocos.
    """
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=formatted_content
    )

def poll_run(instructions: str = None):
    """
    Cria um run e aguarda o resultado.
    """
    return client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions=instructions
    )

def extract_sql_from_message(message) -> str:
    """
    Extrai e limpa o SQL do conteúdo da mensagem do assistente.
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
    """
    Retorna a última mensagem enviada pelo assistente.
    """
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[-1] if assistant_messages else None

def generate_sql_from_nl(nl_query: str) -> str:
    """
    Converte uma consulta em linguagem natural para um comando SQL.
    """
    send_user_message(nl_query)
    run = poll_run()
    if run.status == 'completed':
        last_message = get_latest_assistant_message()
        if not last_message:
            console.print("[bold red]Nenhuma mensagem de assistente recebida.[/bold red]")
            return None
        return extract_sql_from_message(last_message)
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return None

def execute_report(sql: str):
    """
    Executa o SQL na base de dados e salva o resultado em um arquivo Excel.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(REPORTS_PATH, f"report_{timestamp}.xlsx")
        df.to_excel(output_file, index=False)
        console.print(f"[bold green]Relatório salvo com sucesso em:[/bold green] {output_file}")
    except Exception as e:
        console.print(f"[bold red]Erro ao executar a query:[/bold red] {e}")

def confirm_sql_execution(sql: str) -> str:
    """
    Exibe o SQL gerado e recebe feedback do usuário para confirmação ou refinamento.
    """
    console.print("\n[bold green]SQL Gerado:[/bold green]\n")
    console.print(sql)
    console.print("\n[bold yellow]Pressione Enter para confirmar a execução do SQL, ou digite comentários adicionais para refinar a query:[/bold yellow]")
    return input()

def refine_sql(feedback: str) -> str:
    """
    Envia o feedback para atualizar o comando SQL e retorna o SQL refinado utilizando a mesma thread.
    """
    send_user_message(feedback)
    run = poll_run(instructions="Atualize o comando SQL com base na mensagem adicional.")
    if run.status == 'completed':
        latest_message = get_latest_assistant_message()
        if latest_message:
            return extract_sql_from_message(latest_message)
        else:
            console.print("[bold red]Nenhuma mensagem de assistente retornada após o feedback.[/bold red]")
            sys.exit(1)
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        sys.exit(1)

def main():
    console.print("[bold green]Bem-vindo ao assistente PNCP_AI![/bold green]")
    console.print("Digite sua consulta em linguagem natural (em uma única linha) e pressione Enter:")
    
    nl_query = input("Consulta: ")
    if not nl_query.strip():
        console.print("[bold red]Nenhuma consulta fornecida![/bold red]")
        sys.exit(1)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Gerando SQL...", total=1)
        sql_query = generate_sql_from_nl(nl_query)
        progress.advance(task)
    
    if sql_query is None:
        console.print("[bold red]Falha ao gerar SQL. Tente novamente.[/bold red]")
        sys.exit(1)
    
    feedback = confirm_sql_execution(sql_query)
    if not feedback.strip():
        execute_report(sql_query)
    else:
        updated_sql = refine_sql(feedback)
        console.print("\n[bold green]SQL Atualizado:[/bold green]")
        console.print(updated_sql)
        console.print("\n[bold yellow]Pressione Enter para confirmar e executar o SQL atualizado.[/bold yellow]")
        input()
        execute_report(updated_sql)

if __name__ == '__main__':
    main()
