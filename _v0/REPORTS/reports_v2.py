import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.panel import Panel
#from rich.layout import Group
from openai import OpenAI

# Configuração da chave da API OpenAI (substitua pela sua)
client = OpenAI(api_key = "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"  )

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

def generate_sql_from_nl(nl_query: str) -> str:
    """
    Envia a consulta em linguagem natural para a thread e cria um run para
    converter essa consulta em um comando SQL. O retorno será limpo, contendo
    somente o SQL em uma única linha.
    """
    # Envia a consulta do usuário como mensagem formatada
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=[{"type": "text", "text": nl_query}]
    )
    
    # Cria o run com as instruções para transformar a pergunta em SQL
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
        #instructions="Leia a pergunta e transforme-a em um comando SQL."
    )
    
    if run.status == 'completed':
        messages = list(client.beta.threads.messages.list(thread_id=thread.id))
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if not assistant_messages:
            console.print("[bold red]Nenhuma mensagem de assistente recebida.[/bold red]")
            return None
        last_message = assistant_messages[-1]
        # Se o conteúdo for uma lista de blocos, extraímos o valor de cada bloco
        blocks = last_message.content if isinstance(last_message.content, list) else [last_message.content]
        sql_parts = []
        for block in blocks:
            # Se for um dicionário com a chave "text", usamos seu valor
            if isinstance(block, dict) and "text" in block:
                sql_parts.append(block["text"])
            # Se o bloco possuir o atributo 'text' com subatributo 'value', extraímos-o
            elif hasattr(block, "text") and hasattr(block.text, "value"):
                sql_parts.append(block.text.value)
            else:
                sql_parts.append(str(block))
        sql_query = " ".join(sql_parts)
        # Remove quebras de linha e espaços extras
        return " ".join(sql_query.replace("\n", " ").split())
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return None



def execute_report(sql: str):
    """
    Executa o SQL na base pncp.db e salva o resultado em um arquivo Excel
    no diretório REPORTS.
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

def main():
    console.print("[bold green]Bem-vindo ao assistente PNCP_AI![/bold green]")
    console.print("Digite sua consulta em linguagem natural (em uma única linha) e pressione Enter:")
    
    nl_query = input("Consulta: ")
    if not nl_query.strip():
        console.print("[bold red]Nenhuma consulta fornecida![/bold red]")
        sys.exit(1)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task_gen = progress.add_task("Gerando SQL...", total=1)
        sql_query = generate_sql_from_nl(nl_query)
        progress.advance(task_gen, 1)
    
    if sql_query is None:
        console.print("[bold red]Falha ao gerar SQL. Tente novamente.[/bold red]")
        sys.exit(1)
    
    console.print("\n[bold green]SQL Gerado:[/bold green]\n")
    console.print(sql_query)
    
    console.print("\n[bold yellow]Pressione Enter para confirmar a execução do SQL, ou digite comentários adicionais para refinar a query:[/bold yellow]")
    user_feedback = input()
    
    if user_feedback.strip() == "":
        execute_report(sql_query)
    else:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_feedback
        )
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
            instructions="Atualize o comando SQL com base na mensagem adicional."
        )
        if run.status == 'completed':
            messages = list(client.beta.threads.messages.list(thread_id=thread.id))
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]
            if assistant_messages:
                last_message = assistant_messages[-1]
                if isinstance(last_message.content, list):
                    updated_sql = " ".join(
                        item if isinstance(item, str) else (item.value if hasattr(item, "value") else str(item))
                        for item in last_message.content
                    )
                else:
                    updated_sql = str(last_message.content)
                console.print("\n[bold green]SQL Atualizado:[/bold green]")
                console.print(updated_sql.strip())
                console.print("\n[bold yellow]Pressione Enter para confirmar e executar o SQL atualizado.[/bold yellow]")
                input()
                execute_report(updated_sql.strip())
            else:
                console.print("[bold red]Nenhuma mensagem de assistente retornada após o feedback.[/bold red]")
                sys.exit(1)
        else:
            console.print(f"[bold red]Run status: {run.status}[/bold red]")
            sys.exit(1)

if __name__ == '__main__':
    main()
