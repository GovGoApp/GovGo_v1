import os
import pandas as pd
import numpy as np
import pickle
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import nltk
import re
import unidecode
import traceback
from openai import OpenAI
from datetime import datetime
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn

# Configurações
EMBEDDING_MODEL = "text-embedding-3-large"
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
GvG_FILE = BASE_PATH + "GvG_Contratações.xlsx"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\"
GvG_EMBEDDINGS_FILE = EMBEDDINGS_PATH + "GvG_embeddings.pkl"

# Constantes para processamento paralelo
MAX_WORKERS = 20
BATCH_SIZE = 50

# Inicializar NLTK
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Console para exibição formatada
console = Console()

# Cliente OpenAI
client = OpenAI(api_key="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")

# Lock para acessos concorrentes
embedding_lock = threading.Lock()

def preprocess_text(text):
    """Normaliza e limpa o texto para processamento."""
    text = unidecode.unidecode(str(text))
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

def process_batch(batch, model):
    """Processa um lote de textos para embeddings com tratamento de erro."""
    max_retries = 5
    retry_delay = 5
    
    # Validar batch
    validated_batch = []
    for text in batch:
        # Garantir que o texto é string e não está vazio
        if text is None:
            text = " "
        
        if not isinstance(text, str):
            text = str(text)
            
        if not text.strip():
            text = " "
            
        # Limitar tamanho
        if len(text) > 8000:
            text = text[:8000]
            
        validated_batch.append(text)
    
    # Verificação final
    if not validated_batch:
        validated_batch = [" "]
    
    # Tentar com retries
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=validated_batch
            )
            return [np.array(item.embedding, dtype=np.float32) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                console.print(f"[bold yellow]Detalhes do batch: {len(validated_batch)} itens[/bold yellow]")
                if validated_batch:
                    console.print(f"[bold yellow]Primeiro item: {validated_batch[0][:100]}...[/bold yellow]")
                # Retornar Nones para indicar falha
                return [None] * len(validated_batch)

def partition_list(lst, n):
    """Divide uma lista em n partições aproximadamente iguais."""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n)]

def process_embedding_batch(batch_indices, texts, model, progress, task_id, dimension=1536):
    """Processa um lote de textos para embeddings utilizando BATCH_SIZE."""
    batch_results = []
    
    # Agrupar índices em lotes do tamanho BATCH_SIZE
    for i in range(0, len(batch_indices), BATCH_SIZE):
        current_batch_indices = batch_indices[i:i+BATCH_SIZE]
        current_batch_texts = [texts[idx] for idx in current_batch_indices]
        
        try:
            # Processar o lote
            batch_embeddings = process_batch(current_batch_texts, model)
            
            # Verificar cada embedding e garantir formato consistente
            for j, embedding in enumerate(batch_embeddings):
                idx = current_batch_indices[j]
                
                # Verificar se o embedding é válido, caso contrário, criar um vetor vazio
                if embedding is None or not isinstance(embedding, np.ndarray) or embedding.shape != (dimension,):
                    console.print(f"[yellow]Embedding inválido para índice {idx}. Substituindo por vetor zero.[/yellow]")
                    embedding = np.zeros(dimension, dtype=np.float32)
                
                batch_results.append((idx, embedding))
                
            # Atualizar progresso
            progress.update(task_id, advance=len(current_batch_indices))
            
        except Exception as e:
            console.print(f"[bold red]Erro processando lote {i//BATCH_SIZE + 1}: {str(e)}[/bold red]")
            # Criar embeddings vazios para índices com falha
            for idx in current_batch_indices:
                batch_results.append((idx, np.zeros(dimension, dtype=np.float32)))
            progress.update(task_id, advance=len(current_batch_indices))
    
    return batch_results

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(embeddings, f)
        console.print(f"[green]Embeddings salvos em {filepath}[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return False

def load_embeddings(filepath):
    """Carrega embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def get_embeddings_batch(texts, model=EMBEDDING_MODEL, dimension=1536, existing_progress=None):
    """Gera embeddings para uma lista de textos em lotes usando processamento paralelo."""
    # Verificar cache
    if os.path.exists(GvG_EMBEDDINGS_FILE) and len(texts) > 0:
        console.print("[cyan]Embeddings em cache encontrados. Tentando carregar...[/cyan]")
        cached_embeddings = load_embeddings(GvG_EMBEDDINGS_FILE)
        if cached_embeddings and len(cached_embeddings) == len(texts):
            console.print(f"[green]Embeddings em cache carregados com sucesso para {len(cached_embeddings)} itens.[/green]")
            return cached_embeddings
        else:
            console.print("[yellow]Embeddings em cache incompatíveis ou corrompidos. Gerando novos...[/yellow]")
    
    # Preparar para processamento paralelo
    result_embeddings = [np.zeros(dimension, dtype=np.float32)] * len(texts)
    all_indices = list(range(len(texts)))
    partitions = partition_list(all_indices, MAX_WORKERS)
    
    # Configurar barra de progresso
    use_external_progress = existing_progress is not None
    progress = existing_progress if use_external_progress else Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    )
    
    if not use_external_progress:
        progress.start()
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            task_ids = []
            
            # Criar tarefas para cada worker
            for worker_id, partition in enumerate(partitions, 1):
                task_id = progress.add_task(f"Worker {worker_id} embeddings", total=len(partition))
                task_ids.append(task_id)
                futures.append(executor.submit(
                    process_embedding_batch, 
                    partition, 
                    texts, 
                    model, 
                    progress, 
                    task_id,
                    dimension
                ))
            
            # Processar resultados
            for future in futures:
                for idx, embedding in future.result():
                    result_embeddings[idx] = embedding
    
    finally:
        if not use_external_progress:
            progress.stop()
    
    # Verificar qualidade dos embeddings
    valid_count = sum(1 for emb in result_embeddings if np.any(emb))
    total_count = len(result_embeddings)
    console.print(f"[bold blue]Embeddings válidos: {valid_count}/{total_count} ({valid_count/total_count*100:.2f}%)[/bold blue]")
    
    # Salvar os embeddings em cache
    save_embeddings(result_embeddings, GvG_EMBEDDINGS_FILE)
    
    return result_embeddings

def carregar_dados(excel_path):
    """Carrega os dados do Excel de contratações."""
    try:
        df = pd.read_excel(excel_path)
        console.print(f"[green]Carregados {len(df)} registros do Excel.[/green]")
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return None

def processar_descricoes(df):
    """Pré-processa as descrições de contratações."""
    console.print("[bold magenta]Processando descrições...[/bold magenta]")
    df['descricao_processada'] = df['descricaoCompleta'].apply(preprocess_text)
    console.print("[green]Descrições processadas com sucesso.[/green]")
    return df

def main():
    """Função principal simplificada apenas para geração de embeddings."""
    console.print("[bold magenta]SISTEMA DE GERAÇÃO DE EMBEDDINGS PARA CONTRATAÇÕES[/bold magenta]")
    console.print("[bold cyan]Baseado em OpenAI Embeddings[/bold cyan]\n")
    
    # Verificar diretório de embeddings
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    # Carregar dados
    console.print("[bold blue]Carregando dados do Excel...[/bold blue]")
    df = carregar_dados(GvG_FILE)
    if df is None:
        console.print("[bold red]Falha ao carregar dados. Encerrando.[/bold red]")
        return
    
    # Processar descrições
    df = processar_descricoes(df)
    
    # Gerar embeddings
    console.print("[bold blue]Iniciando geração de embeddings...[/bold blue]")
    textos = df['descricao_processada'].tolist()
    
    # Medir tempo de execução
    inicio = time.time()
    
    # Gerar embeddings com processamento em lotes e paralelismo
    embeddings = get_embeddings_batch(textos)
    
    # Calcular tempo decorrido
    fim = time.time()
    tempo_total = fim - inicio
    
    console.print(f"[bold green]Embeddings gerados com sucesso: {len(embeddings)}[/bold green]")
    console.print(f"[bold green]Tempo total: {tempo_total:.2f} segundos[/bold green]")
    console.print(f"[bold green]Média por item: {tempo_total/len(embeddings):.4f} segundos[/bold green]")
    
    # Arquivo de registro
    log_file = EMBEDDINGS_PATH + "embedding_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Arquivo: {GvG_FILE}\n")
        f.write(f"Modelo: {EMBEDDING_MODEL}\n")
        f.write(f"Registros processados: {len(embeddings)}\n")
        f.write(f"Tempo total: {tempo_total:.2f} segundos\n")
        f.write(f"Média por item: {tempo_total/len(embeddings):.4f} segundos\n")
        f.write(f"Arquivo de embeddings: {GvG_EMBEDDINGS_FILE}\n")
        f.write("-" * 50 + "\n\n")
    
    console.print(f"[bold green]Log salvo em {log_file}[/bold green]")
    console.print("[bold green]Processamento concluído com sucesso![/bold green]")

if __name__ == "__main__":
    main()