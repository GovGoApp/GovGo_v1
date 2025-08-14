
import os
import time
import pandas as pd
from rich.console import Console
from rich.progress import Progress, BarColumn, SpinnerColumn, TextColumn
from openai import OpenAI, BadRequestError

# Configuração da API OpenAI (substitua pela sua chave)
client = OpenAI(api_key="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")

# Caminhos para a planilha
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
IN_FILE = os.path.join(REPORTS_PATH, "TESTE.xlsx")
OUT_FILE = os.path.join(REPORTS_PATH, "TESTE_OUT.xlsx")

# Cria uma nova thread
thread = client.beta.threads.create()

# Define o assistant específico e o modelo
assistant_id = "asst_Gxxpxxy951ai6CJoLkf6k6IJ"
model_id = "gpt-4o"

console = Console()

def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread."""
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=formatted_content
    )

def poll_run():
    """Tenta criar e aguardar uma run. Se já existir uma run ativa, aguarda e tenta novamente."""
    while True:
        try:
            return client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant_id
            )
        except BadRequestError as e:
            error_msg = str(e)
            if "already has an active run" in error_msg:
                console.print("[yellow]Thread com run ativo. Aguardando 1 segundo antes de tentar novamente...[/yellow]")
                time.sleep(1)
            else:
                raise e

def get_latest_assistant_message():
    """Retorna a última mensagem do assistente na thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

def get_assistant_response(query: str) -> str:
    """
    Envia uma consulta ao assistente e retorna a resposta como string.
    Espera-se que a resposta esteja no formato:
      "CATSER ; 166 - SERVIÇOS DE MANUTENÇÃO E INSTALAÇÃO DE EQUIPAMENTOS DE TIC"
    """
    send_user_message(query)
    run = poll_run()
    if run.status == "completed":
        message = get_latest_assistant_message()
        if message:
            content = message.content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if hasattr(item, 'text'):
                        if hasattr(item.text, 'value'):
                            parts.append(item.text.value)
                        else:
                            parts.append(str(item.text))
                    elif isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    else:
                        parts.append(str(item))
                full_text = " ".join(parts).strip()
            else:
                full_text = str(content).strip()
            return full_text
        else:
            console.print("[bold red]Nenhuma resposta recebida do assistente.[/bold red]")
            return ""
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return ""

def process_excel(file_path: str, output_path: str):
    """
    Lê uma planilha Excel, extrai a coluna 'objetoCompra',
    envia cada valor para o assistente, exibe o input e o output,
    processa a resposta (dividindo em CAT e GRUPO) e salva a planilha.
    Salva a cada 20 linhas processadas.
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        console.print(f"[bold red]Erro ao ler a planilha: {e}[/bold red]")
        return

    if "objetoCompra" not in df.columns:
        console.print("[bold red]A coluna 'objetoCompra' não foi encontrada na planilha.[/bold red]")
        return

    # Cria as colunas para os resultados
    df["CAT"] = ""
    df["GRUPO"] = ""

    total = len(df)
    console.print(f"[bold green]Processando {total} linhas...[/bold green]")

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processando linhas...", total=total)
        for idx, row in df.iterrows():
            objeto = row["objetoCompra"]
            if pd.isna(objeto):
                progress.update(task, advance=1, description=f"Linha {idx+1}: sem objetoCompra")
                continue

            # Exibe o input
            console.print(f"[bold cyan]Linha {idx+1} - Input:[/bold cyan] {objeto}")
            progress.update(task, description=f"Linha {idx+1} - Processando...")

            # Envia o conteúdo para o assistente e captura a resposta
            resposta = get_assistant_response(str(objeto))
            console.print(f"[bold magenta]Linha {idx+1} - Output:[/bold magenta] {resposta}")

            # Divide a resposta pelo separador ";" e atribui às colunas
            if ";" in resposta:
                partes = resposta.split(";", 1)
                df.at[idx, "CAT"] = partes[0].strip()
                df.at[idx, "GRUPO"] = partes[1].strip()
            else:
                df.at[idx, "CAT"] = resposta.strip()
                df.at[idx, "GRUPO"] = ""
            progress.update(task, advance=1, description=f"Linha {idx+1} concluída")

            # Salva a cada 20 linhas processadas
            if (idx + 1) % 20 == 0:
                try:
                    df.to_excel(output_path, index=False)
                    console.print(f"[bold green]Batch {(idx+1)//20} salvo com sucesso.[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Erro ao salvar o batch: {e}[/bold red]")

    # Salva a planilha final
    try:
        df.to_excel(output_path, index=False)
        console.print(f"[bold green]Planilha processada e salva em: {output_path}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar a planilha final: {e}[/bold red]")

if __name__ == '__main__':
    process_excel(IN_FILE, OUT_FILE)
