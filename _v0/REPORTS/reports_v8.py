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
client = OpenAI(api_key="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")

# Criação da thread – o histórico é acumulado
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"  # Substitua pelo ID do seu assistente
model_id: str = "gpt-4o"

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

### FUNÇÕES GERAIS OPENAI

# OPENAI CHAT COMPLETION
def get_chat_completion(prompt: str, system_message: str, max_tokens: int = 50, temperature: float = 0) -> str:
    """
    Função genérica para obter respostas usando o modelo de chat do OpenAI.
    
    Args:
        prompt: O texto da consulta do usuário
        system_message: A mensagem de sistema que define o contexto/comportamento
        max_tokens: Número máximo de tokens na resposta
        temperature: Temperatura (criatividade) da resposta
        
    Returns:
        O texto da resposta gerada
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content.strip()

# OPENAI SEND USER MESSAGE
def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    formatted_content = [{"type": "text", "text": content}]
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=formatted_content
    )
    
# OPENAI POLL RUN
def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    return client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

# OPENAI GET LATEST ASSISTANT MESSAGE
def get_latest_assistant_message():
    """Retorna a mensagem do assistente na posição [0] da thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

# OPENAI GET ASSISTANT MESSAGE CONTENT
def get_assistant_response(user_query: str) -> str:
    """
    Função genérica para enviar uma consulta ao assistente e obter sua resposta.
    Retorna o conteúdo da resposta ou None em caso de erro.
    """
    send_user_message(user_query)
    run = poll_run()
    if run.status == 'completed':
        last_message = get_latest_assistant_message()
        if not last_message:
            console.print("[bold red]Nenhuma mensagem de assistente recebida.[/bold red]")
            return None
        return last_message
    else:
        console.print(f"[bold red]Run status: {run.status}[/bold red]")
        return None

### FUNÇÕES ESPECÍFICAS

# EXTRAI SQL DO ASSISTENTE
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

## GERA SQL A PARTIR DE CONSULTA EM LINGUAGEM NATURAL
def generate_sql_from_nl(nl_query: str) -> str:
    """
    Converte uma consulta em linguagem natural em um comando SQL.
    Utiliza a função genérica get_assistant_response e extrai o SQL.
    """
    assistant_message = get_assistant_response(nl_query)
    if assistant_message:
        return extract_sql_from_message(assistant_message)
    return None


# GERA NOME DO RELATÓRIO A PARTIR DO SQL
def generate_report_filename(sql: str) -> str:
    """
    Gera um nome de arquivo para o relatório Excel a partir do SQL recebido.
    O padrão de nome é: {TABELA}_{FUNCAO/AGG}_{OBJETO}_{REGIAO/ESTADO/MUNICIPIO/ENTIDADE/ORGAO}_{MES/ANO}.xlsx
    Exemplo:
        SQL: SELECT ct.* FROM contrato AS ct JOIN contratacao AS c ON ... ct.anoContrato = 2024;
        Nome: CONTRATOS_ALIMENTACAO_NORDESTE_2024
    """
    system_msg = (
    """
    Você é um assistente especialista em geração de nomes de arquivos para relatórios,
    seguindo o padrão: {QUAL}_{COMO}_{O QUÊ}_{ONDE}_{QUANDO}. 
    QUAL é a tabela principal, COMO é a função ou agregação (ex: CONTAGEM, SOMA, MÉDIA),
    O QUÊ é o objeto da compra ou contrato, ONDE é a região/estado/município/entidade/órgão, QUANDO é o período (mês/ano).
    A resposta deve conter somente o nome completo do arquivo em letra maiúscula.
    Use os dados do SQL fornecido para identificar a tabela principal, o objeto da compra ou contrato, 
    a região/estado/município/entidade/órgão e o período (mês/ano) se presentes. 
    """
    )
    
    user_prompt = f"SQL: {sql}\n\nGere o nome do relatório seguindo o padrão."
    file_name = get_chat_completion(user_prompt, system_msg, max_tokens=50, temperature=0)
    
    # Garantir que o nome esteja em maiúsculas e termine com .XLSX
    file_name = file_name.upper()
    if not file_name.endswith(".xlsx"):
        file_name += ".xlsx"
    
    return file_name


def execute_report(sql: str):
    """
    Executa o comando SQL na base de dados e obtém o resultado.
    Exibe um preview dos dados (10 primeiras linhas/7 primeiras colunas) e o total de linhas, 
    além de mostrar o SQL gerado. Em seguida, pergunta se deseja salvar o relatório.
    Se o resultado tiver mais que 1.048.576 linhas, divide os dados em múltiplas abas.
    """
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("[bold white]Executando Query...[/bold white]", total=1)
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            progress.advance(task)
        total_rows = len(df)
        # Exibir preview: 10 primeiras linhas e 7 primeiras colunas
        preview_df = df.iloc[:10, :7]
        table = Table(show_header=True, header_style="bold magenta")
        for col in preview_df.columns:
            table.add_column(str(col))
        for _, row in preview_df.iterrows():
            table.add_row(*[str(value) for value in row])
        console.print("\n[bold blue]Preview dos dados:[/bold blue]")
        console.print(table)
        console.print(f"\n[bold blue]Total de linhas retornadas: {total_rows}[/bold blue]")
        console.print(f"\n[bold blue]SQL Gerado: [/bold blue]{sql}")
        
        choice = input("\nDeseja salvar o relatório? (S/N): ")
        if choice.strip().upper() == "S":
            file_name = generate_report_filename(sql)
            output_file = os.path.join(REPORTS_PATH, file_name)
            
            # Verifica se o resultado excede o limite de linhas do Excel (1.048.576)
            if total_rows > 1048576:
                console.print(f"\n[bold yellow]Atenção: O resultado possui {total_rows} linhas, excedendo o limite de 1.048.576 linhas por planilha do Excel.[/bold yellow]")
                console.print("[bold yellow]Os dados serão divididos em múltiplas abas.[/bold yellow]")
                
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    task = progress.add_task("[bold white]Salvando Relatório...[/bold white]", total=1)
                    
                    # Cria um ExcelWriter para salvar os dados em múltiplas abas
                    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                        # Calcula quantas abas serão necessárias
                        max_rows_per_sheet = 1048575  # -1 para cabeçalho
                        num_sheets = (total_rows + max_rows_per_sheet - 1) // max_rows_per_sheet
                        
                        for i in range(num_sheets):
                            start_row = i * max_rows_per_sheet
                            end_row = min((i + 1) * max_rows_per_sheet, total_rows)
                            sheet_name = f"Dados_{i+1}"
                            
                            # Salva o subconjunto do DataFrame na aba atual
                            df.iloc[start_row:end_row].to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    progress.advance(task)
                    
                console.print(f"[bold green]Relatório dividido em {num_sheets} abas e salvo com sucesso em:[/bold green] {output_file}")
            else:
                # Caso normal: salva em uma única aba
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    task = progress.add_task("[bold white]Salvando Relatório...[/bold white]", total=1)
                    df.to_excel(output_file, index=False)
                    progress.advance(task)
                    
                console.print(f"[bold green]Relatório salvo com sucesso em:[/bold green] {output_file}")
        else:
            console.print("[bold yellow]Relatório não salvo. Continuando a conversa...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Erro ao executar a query:[/bold red] {e}")


def conversation_loop():
    """
    Loop de conversa que continua até que o usuário digite 'ESC'.
    A cada nova consulta, o assistente gera um comando SQL que é executado automaticamente.
    É exibido um preview dos dados, o total de linhas e o SQL gerado.
    Depois, pergunta se deseja salvar o relatório (S/N).
    O histórico da thread é mantido.
    """
    console.print("[bold green]Bem-vindo ao assistente PNCP_AI![/bold green]")
    console.print("[bold green]Digite sua consulta em linguagem natural e pressione Enter[/bold green]\n")
    
    while True:
        console.print("[bold green]Consulta:[/bold green]")
        nl_query = input()
        if not nl_query.strip():
            continue
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("[bold white]Gerando SQL...[/bold white]", total=1)
            sql_query = generate_sql_from_nl(nl_query)
            progress.advance(task)
        if sql_query is None:
            console.print("[bold red]Falha ao gerar SQL. Tente novamente.[/bold red]")
            continue
        
        execute_report(sql_query)
        console.print("\n")

    
def main():
    conversation_loop()

if __name__ == '__main__':
    main()