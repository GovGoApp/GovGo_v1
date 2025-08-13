import os
import time
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from openai import OpenAI, BadRequestError

# Configuração da API OpenAI (substitua pela sua chave)
client = OpenAI(api_key="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")

# Caminhos para a planilha
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
IN_FILE = os.path.join(REPORTS_PATH, "TESTE.xlsx")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_FILE = os.path.join(REPORTS_PATH, f"TESTE_OUT_{timestamp}.xlsx")

# Assistant específico e modelo
assistant_id = "asst_Gxxpxxy951ai6CJoLkf6k6IJ" # usando gpt3.5-turbo
#model_id = "gpt-4o"

console = Console()
# Lock para atualizar o dataframe e salvar
update_lock = threading.Lock()
# Lock para atualizar progresso individual das tasks
task_lock = threading.Lock()

def process_row(idx, objeto, progress, task_id):
    """
    Processa uma linha da planilha: cria uma thread local no OpenAI, envia o conteúdo
    e retorna o índice da linha, e os valores extraídos (CAT e GRUPO) da resposta.
    """
    # Atualiza o status da tarefa individual
    with task_lock:
        progress.update(task_id, description=f"[blue]    ⚙ Processando linha {idx+1}[/blue]", completed=10)
    
    # Cria uma thread local no OpenAI para evitar conflitos de run ativo
    local_thread = client.beta.threads.create()

    def send_user_message_local(content: str, thread_id: str):
        formatted_content = [{"type": "text", "text": content}]
        with task_lock:
            progress.update(task_id, description=f"[cyan]    ⚡ Enviando linha {idx+1}[/cyan]", completed=30)
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=formatted_content
        )

    def poll_run_local(thread_id: str):
        with task_lock:
            progress.update(task_id, description=f"[yellow]    ⏳ Aguardando resposta para linha {idx+1}[/yellow]", completed=50)
        while True:
            try:
                return client.beta.threads.runs.create_and_poll(
                    thread_id=thread_id,
                    assistant_id=assistant_id
                )
            except BadRequestError as e:
                if "already has an active run" in str(e):
                    time.sleep(1)
                else:
                    raise e

    def get_latest_message_local(thread_id: str):
        with task_lock:
            progress.update(task_id, description=f"[green]    ✓ Obtendo resposta para linha {idx+1}[/green]", completed=80)
        messages = list(client.beta.threads.messages.list(thread_id=thread_id))
        assistant_msgs = [msg for msg in messages if msg.role == "assistant"]
        return assistant_msgs[0] if assistant_msgs else None

    query = str(objeto)
    send_user_message_local(query, local_thread.id)
    run = poll_run_local(local_thread.id)
    if run.status == "completed":
        message = get_latest_message_local(local_thread.id)
        if message:
            content = message.content
            # Se o conteúdo for uma lista, concatena os textos
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
        else:
            full_text = ""
    else:
        full_text = ""

    # Marca a tarefa como concluída
    with task_lock:
        progress.update(task_id, description=f"[bright_green]    ✅ Linha {idx+1} concluída[/bright_green]", completed=100)

    # Divide a resposta pelo separador ";" para extrair CAT e GRUPO
    if ";" in full_text:
        partes = full_text.split(";", 1)
        cat = partes[0].strip()
        grupo = partes[1].strip()
    else:
        cat = full_text.strip()
        grupo = ""
    return idx, cat, grupo

def process_excel(file_path: str, output_path: str):
    """
    Lê a planilha, processa a coluna 'objetoCompra' utilizando 30 threads concorrentes,
    atualiza as colunas "CAT" e "GRUPO" com os valores extraídos e salva a planilha a cada
    batch de 20 linhas.
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        console.print(f"[bold red]Erro ao ler a planilha: {e}[/bold red]")
        return

    if "objetoCompra" not in df.columns:
        console.print("[bold red]A coluna 'objetoCompra' não foi encontrada na planilha.[/bold red]")
        return

    # Cria as colunas de resultado
    df["CAT"] = ""
    df["GRUPO"] = ""

    total = len(df)
    console.print(f"[bold green]Processando {total} linhas...[/bold green]")

    processed_count = 0
    futures = []
    task_ids = {}  # Dicionário para armazenar IDs de tarefas individuais
    
    # Cria um executor com 30 threads
    with ThreadPoolExecutor(max_workers=30) as executor, Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        TextColumn("{task.description}"),
        console=console,
    ) as progress:
        # Tarefa principal
        main_task = progress.add_task("[white]Processando linhas...", total=total)
        
        # Envia as tarefas para as linhas que possuem valor em 'objetoCompra'
        for idx, row in df.iterrows():
            objeto = row["objetoCompra"]
            if pd.isna(objeto):
                with update_lock:
                    df.at[idx, "CAT"] = ""
                    df.at[idx, "GRUPO"] = ""
                progress.update(main_task, advance=1, description=f"[white]Processando linhas: {processed_count+1}/{total}")
                processed_count += 1
            else:
                # Cria uma tarefa individual para esta linha
                task_id = progress.add_task(f"[blue]    ⚙ Preparando linha {idx+1}[/blue]", total=100, completed=0)
                task_ids[idx] = task_id
                futures.append(executor.submit(process_row, idx, objeto, progress, task_id))

        # Conforme as tarefas vão sendo completadas, atualiza o dataframe e salva a cada 20 linhas
        for future in as_completed(futures):
            idx, cat, grupo = future.result()
            with update_lock:
                df.at[idx, "CAT"] = cat
                df.at[idx, "GRUPO"] = grupo
            processed_count += 1
            progress.update(main_task, advance=1, description=f"[white]Processando linhas: {processed_count}/{total}")
            
            if processed_count % 20 == 0:
                with update_lock:
                    try:
                        df.to_excel(output_path, index=False)
                        console.print(f"[bold green]Batch de {processed_count} linhas salvo com sucesso.[/bold green]")
                    except Exception as e:
                        console.print(f"[bold red]Erro ao salvar o batch: {e}[/bold red]")

    # Salva o dataframe final
    with update_lock:
        try:
            df.to_excel(output_path, index=False)
            console.print(f"[bold green]Planilha final processada e salva em: {output_path}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar a planilha final: {e}[/bold red]")

if __name__ == '__main__':
    process_excel(IN_FILE, OUT_FILE)