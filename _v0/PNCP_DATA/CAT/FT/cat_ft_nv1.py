
import json
import os
import time
import pandas as pd
from openai import OpenAI
from rich.progress import track, Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.console import Console

def main():
    """Função principal para preparar e executar o fine-tuning para classificação de CATMAT/CATSER."""
    
    # Criar uma instância de console para exibição formatada
    console = Console()
    
    # Configuração da OpenAI
    client = OpenAI(api_key="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")
    
    # Definir caminhos e arquivos
    BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
    CAT_PATH = BASE_PATH + "CAT\\"
    CATMAT_FILE = CAT_PATH + "catmat_datasets_nv1.xlsx"
    CATSER_FILE = CAT_PATH + "catser_datasets_nv1.xlsx"
    TRAINING_SHEET = "training"
    VALIDATION_SHEET = "validation"
    
    # Arquivos de saída para fine-tuning
    TRAINING_FILE = CAT_PATH + "cat_training_nv1.jsonl"
    VALIDATION_FILE = CAT_PATH + "cat_validation_nv1.jsonl"
    
    # Carregar os dados
    console.print("[bold magenta]Carregando dados do CATMAT nível 1...[/bold magenta]")
    try:
        catmat_training = pd.read_excel(CATMAT_FILE, sheet_name=TRAINING_SHEET)
        catmat_validation = pd.read_excel(CATMAT_FILE, sheet_name=VALIDATION_SHEET)
        console.print(f"[green]CATMAT carregado: {catmat_training.shape[0]} itens de treinamento, {catmat_validation.shape[0]} itens de validação[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar CATMAT: {str(e)}[/bold red]")
        return
    
    console.print("[bold magenta]Carregando dados do CATSER nível 1...[/bold magenta]")
    try:
        catser_training = pd.read_excel(CATSER_FILE, sheet_name=TRAINING_SHEET)
        catser_validation = pd.read_excel(CATSER_FILE, sheet_name=VALIDATION_SHEET)
        console.print(f"[green]CATSER carregado: {catser_training.shape[0]} itens de treinamento, {catser_validation.shape[0]} itens de validação[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar CATSER: {str(e)}[/bold red]")
        return
    
    # Juntar os DataFrames
    console.print("[bold magenta]Combinando dados de CATMAT e CATSER...[/bold magenta]")
    training_df = pd.concat([catmat_training, catser_training], ignore_index=True)
    validation_df = pd.concat([catmat_validation, catser_validation], ignore_index=True)
    
    # Estatísticas sobre os conjuntos combinados
    console.print(f"[green]Conjunto de treinamento combinado: {training_df.shape[0]} itens[/green]")
    console.print(f"[green]Conjunto de validação combinado: {validation_df.shape[0]} itens[/green]")
    
    # Verificar a distribuição dos tipos
    material_train = training_df['CATEGORIA'].str.startswith('MATERIAL;').sum()
    service_train = training_df['CATEGORIA'].str.startswith('SERVIÇO;').sum()
    material_valid = validation_df['CATEGORIA'].str.startswith('MATERIAL;').sum()
    service_valid = validation_df['CATEGORIA'].str.startswith('SERVIÇO;').sum()
    
    console.print(f"[green]Treinamento: {material_train} materiais e {service_train} serviços[/green]")
    console.print(f"[green]Validação: {material_valid} materiais e {service_valid} serviços[/green]")
    
    # Definir a mensagem do sistema
    system_message = """Classifique o ITEM na CATEGORIA apropriada. Materiais começam com 'MATERIAL;' e serviços com 'SERVIÇO;'. Responda apenas com a categoria."""
    
    def prepare_example_conversation(row):
        """Prepara um exemplo de conversa com base na linha do dataframe."""
        messages = []
        
        # Adiciona a mensagem do sistema
        messages.append({"role": "system", "content": system_message})
        
        # Adiciona a mensagem do usuário contendo apenas o ITEM
        user_message = f"Classifique este item: {row['ITEM']}"
        messages.append({"role": "user", "content": user_message})
        
        # Adiciona a resposta esperada (a CATEGORIA)
        assistant_message = f"{row['CATEGORIA']}"
        messages.append({"role": "assistant", "content": assistant_message})
    
        return {"messages": messages}
    
    # Aplicar a função a cada linha dos dataframes de treinamento e validação
    console.print("[bold magenta]Preparando conversas de treinamento...[/bold magenta]")
    training_conversations = [prepare_example_conversation(row) for row in track(training_df.to_dict('records'), description="Processando")]
    
    console.print("[bold magenta]Preparando conversas de validação...[/bold magenta]")
    validation_conversations = [prepare_example_conversation(row) for row in track(validation_df.to_dict('records'), description="Processando")]
    
    # Mostrar alguns exemplos de conversas preparadas
    console.print("\n[bold green]Exemplos de conversas de treinamento:[/bold green]")
    for i, conv in enumerate(training_conversations[:3]):
        console.print(f"[bold cyan]Exemplo {i+1}:[/bold cyan]")
        for msg in conv["messages"]:
            console.print(f"[bold]{msg['role']}:[/bold] {msg['content']}")
        console.print("")
    
    # Função para salvar dados em formato JSONL
    def write_jsonl(data_list, filename):
        """Salva a lista de dicionários em um arquivo .jsonl."""
        with open(filename, "w", encoding="utf-8") as out:
            for ddict in data_list:
                jout = json.dumps(ddict, ensure_ascii=False) + "\n"
                out.write(jout)
    
    # Salvar os conjuntos de treinamento e validação em .jsonl
    console.print("[bold magenta]Salvando arquivos JSONL...[/bold magenta]")
    write_jsonl(training_conversations, TRAINING_FILE)
    write_jsonl(validation_conversations, VALIDATION_FILE)
    
    console.print(f"[green]Arquivos salvos em:[/green]")
    console.print(f"- Treinamento: {TRAINING_FILE}")
    console.print(f"- Validação: {VALIDATION_FILE}")
    
    # Retornar os nomes de arquivos para uso posterior
    return TRAINING_FILE, VALIDATION_FILE, client


def upload_files(training_file, validation_file, client):
    """Função para fazer upload dos arquivos para a OpenAI."""
    console = Console()
    
    # Função para realizar upload com feedback visual
    def upload_file_with_progress(filepath, purpose):
        file_size = os.path.getsize(filepath)
        file_name = os.path.basename(filepath)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[bold yellow]{task.fields[status]}"),
            TimeElapsedColumn()
        ) as progress:
            # Criar a tarefa de upload
            task = progress.add_task(f"Enviando {file_name}", total=3, status="Inicializando...")
            
            # Etapa 1: Preparando arquivo
            progress.update(task, advance=1, status="Preparando arquivo...")
            time.sleep(0.5)  # Pequena pausa para visualização
            
            # Etapa 2: Enviando arquivo
            progress.update(task, advance=1, status=f"Enviando {file_size/1024/1024:.2f} MB...")
            
            # Realizar o upload de fato
            try:
                response = client.files.create(file=open(filepath, "rb"), purpose=purpose)
                
                # Etapa 3: Concluído
                progress.update(task, advance=1, status="Concluído!")
                return response
            except Exception as e:
                progress.update(task, status=f"Erro: {str(e)}")
                raise e
    
    # Fazer upload dos arquivos para a OpenAI
    console.print("[bold magenta]Enviando arquivos para a OpenAI...[/bold magenta]")
    
    try:
        console.print("\n[bold]Arquivo de treinamento:[/bold]")
        training_response = upload_file_with_progress(training_file, "fine-tune")
        
        console.print("\n[bold]Arquivo de validação:[/bold]")
        validation_response = upload_file_with_progress(validation_file, "fine-tune")
        
        console.print(f"\n[green]Upload concluído com sucesso![/green]")
        console.print(f"- ID do arquivo de treinamento: {training_response.id}")
        console.print(f"- ID do arquivo de validação: {validation_response.id}")
        
        # Retornar os IDs para uso posterior
        return training_response.id, validation_response.id
        
    except Exception as e:
        console.print(f"\n[bold red]Erro ao fazer upload: {str(e)}[/bold red]")
        return None, None


def start_fine_tuning(training_file_id, validation_file_id, client):
    """Função para iniciar o job de fine-tuning."""
    console = Console()
    
    # Iniciando o job de fine-tuning
    console.print("[bold magenta]Iniciando o job de fine-tuning...[/bold magenta]")
    
    try:
        ft_job = client.fine_tuning.jobs.create(
            training_file=training_file_id,
            validation_file=validation_file_id,
            model="gpt-3.5-turbo",
            suffix="cat_grupo_classificador"
        )
        
        console.print(f"[green]Job de fine-tuning iniciado com sucesso![/green]")
        console.print(f"- ID do job: {ft_job.id}")
        console.print(f"- Status: {ft_job.status}")
        console.print("[bold]Você pode monitorar o progresso do fine-tuning através da API ou do dashboard da OpenAI.[/bold]")
        
        return ft_job.id
        
    except Exception as e:
        console.print(f"\n[bold red]Erro ao iniciar fine-tuning: {str(e)}[/bold red]")
        return None


if __name__ == "__main__":
    # Executar a preparação dos dados
    training_file, validation_file, client = main()
    
    # Perguntar se deseja fazer upload agora
    console = Console()
    if input("\nDeseja fazer upload dos arquivos agora? (s/n): ").lower() == 's':
        # Executar o upload dos arquivos
        training_id, validation_id = upload_files(training_file, validation_file, client)
        
        # Perguntar se deseja iniciar o fine-tuning
        if training_id and validation_id and input("\nDeseja iniciar o fine-tuning agora? (s/n): ").lower() == 's':
            # Iniciar o fine-tuning
            job_id = start_fine_tuning(training_id, validation_id, client)
            
            if job_id:
                console.print(f"\n[bold green]Todo o processo foi concluído com sucesso![/bold green]")
                console.print(f"[bold]Job ID: {job_id}[/bold]")
            else:
                console.print("\n[bold yellow]O processo foi interrompido na etapa de fine-tuning.[/bold yellow]")
        else:
            console.print("\n[bold yellow]O upload foi concluído, mas o fine-tuning não foi iniciado.[/bold yellow]")
    else:
        console.print("\n[bold yellow]Arquivos preparados, mas o upload não foi realizado.[/bold yellow]")