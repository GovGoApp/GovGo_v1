### EMB_NV4_v3_2 (EMBEDDING NIVEL 4 V3.2) ###

# Este script é responsável por gerar embeddings para itens de compras e classificá-los em categorias unificadas.
# Modificação: Visualização melhorada com rich.Progress para todas as etapas
import os
import re
import sys
import json
import threading
import pickle
import time
import numpy as np
import pandas as pd
import nltk
import unidecode
import traceback
import glob
import math
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import (
    Progress, 
    TextColumn, 
    BarColumn, 
    SpinnerColumn, 
    TimeElapsedColumn, 
    TimeRemainingColumn, 
    TaskProgressColumn, 
    MofNCompleteColumn
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

# Baixar recursos NLTK necessários
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")  # Novo caminho para o catálogo unificado
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
INPUT_DIR = CLASS_PATH + "INPUT\\"  # Diretório com os arquivos divididos
NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_PATH = CLASS_PATH + f"RESULTS_{TIMESTAMP}\\"  # Diretório de saída para resultados
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_ARQUIVOS_{TIMESTAMP}.pkl"

# Criar diretório de saída se não existir
os.makedirs(OUTPUT_PATH, exist_ok=True)

# BATCH e MAX_WORKERS
BATCH_SIZE = 20  # Tamanho do batch para processamento dentro de cada arquivo

# Constantes para controle de execução
MAX_WORKERS = 15  # Número de threads para processamento paralelo
console.print("CPU: " + str(os.cpu_count()))
console.print("WORKERS = " + str(MAX_WORKERS))

TOP_N = 10 # Número de categorias mais relevantes a serem retornadas

# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = BASE_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"

# Criar lock para acessos concorrentes
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
progress_lock = threading.Lock()

def preprocess_text(text):
    # Remover acentuação e converter para string
    text = unidecode.unidecode(str(text))
    # Converter para minúsculas
    text = text.lower()
    # Remover caracteres não alfabéticos
    text = re.sub(r'[^a-z\s]', '', text)
    # Remover stopwords
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    # Lematizar (opcional - ajuste conforme necessário)
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings salvos em {filepath}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
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

def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar checkpoint: {str(e)}[/bold red]")
    return None

def save_checkpoint(processed_files):
    """Salvar checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'processed_files': processed_files
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[yellow]Checkpoint salvo: processados {len(processed_files)} arquivos[/yellow]")

def load_input_file(filepath):
    """Carrega um arquivo de entrada específico."""
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo {filepath}: {str(e)}[/bold red]")
        raise

def load_catalog():
    """Carrega apenas o catálogo unificado."""
    console.print("[bold magenta]Carregando catálogo unificado...[/bold magenta]")
    
    # Carregar catálogo unificado
    try:
        # Carrega o catálogo unificado a partir do arquivo Excel "NOVA CAT".xlsx
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        # Converte o DataFrame para uma lista de dicionários
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Carregadas {len(cat)} categorias do catálogo unificado.[/green]")
        return cat
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise

def prepare_catalog_entries(cat):
    """Preparar entradas de catálogo unificado para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    
    cat_texts = []
    cat_meta = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando catálogo unificado..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(cat))
        
        for entry in cat:
            # Utiliza as colunas CODCAT e NOMCAT do arquivo Excel
            codcat = entry.get('CODCAT', '')
            nomcat = entry.get('NOMCAT', '')
            # Forma o texto de embedding concatenando os dois campos com um espaço
            combined_text = preprocess_text(f"{codcat} {nomcat}")
            cat_texts.append(combined_text)
            cat_meta.append((codcat, nomcat))
            progress.update(task, advance=1)
    
    console.print(f"[magenta]Preparados {len(cat_texts)} textos de catálogo unificado.[/magenta]")
    return cat_texts, cat_meta

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=100, progress=None, task_id=None, worker_id=None):
    """
    Gerar embeddings para uma lista de textos usando a API da OpenAI.
    Atualiza o progresso usando o objeto Progress e task_id fornecidos.
    """
    embeddings = []
    
    # Processar em lotes para evitar limites de token ou requisição
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Se não foi fornecido um task_id, crie um novo Progress temporário
    if progress is None or task_id is None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Gerando embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn()
        ) as temp_progress:
            temp_task = temp_progress.add_task("Embeddings", total=total_batches)
            
            # Loop de processamento com progresso
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = process_batch(batch, model)
                embeddings.extend(batch_embeddings)
                temp_progress.update(temp_task, advance=1)
    else:
        # Garantir thread-safety para atualizações do progresso
        # Loop de processamento usando o Progress fornecido
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = process_batch(batch, model)
            embeddings.extend(batch_embeddings)
            
            # Atualizar o progresso de forma thread-safe
            with progress_lock:
                progress.update(task_id, advance=1)
    
    return embeddings

def process_batch(batch, model):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=batch
            )
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                if attempt == max_retries - 1:
                    console.print(f"[bold red]Erro após {max_retries} tentativas: {str(e)}[/bold red]")
                else:
                    console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

def process_chunk(chunk_df, cat_embeds, cat_meta, worker_id, progress, task_ids):
    """
    Processa um chunk específico do DataFrame utilizando o objeto Progress fornecido.
    
    Args:
        chunk_df: DataFrame contendo os dados a serem processados
        cat_embeds: Embeddings das categorias
        cat_meta: Metadados das categorias
        worker_id: ID do worker para identificação nas barras de progresso
        progress: Objeto Progress compartilhado
        task_ids: Dicionário contendo os IDs das tarefas de progresso para este worker:
                 {'preproc': task_id1, 'embed': task_id2, 'sim': task_id3}
    """
    # Criar DataFrame de resultados para este chunk
    result_df = chunk_df.copy()
    
    # Adicionar TOP_1 a TOP_10 e SCORE_1 a SCORE_10
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    # Obter textos dos itens para processamento
    raw_texts = chunk_df["objetoCompra"].fillna("").astype(str).tolist()
    
    # Pré-processar os textos atualizando o progresso
    item_texts = []
    total_items = len(raw_texts)
    
    # Pré-processamento com atualização de progresso
    for i, text in enumerate(raw_texts):
        item_texts.append(preprocess_text(text))
        # Atualizar progresso de pré-processamento de forma thread-safe
        with progress_lock:
            progress.update(task_ids['preproc'], advance=1)
    
    # Obter embeddings com atualização de progresso
    # O get_embeddings já cuida da atualização de progresso internamente
    item_embeds = get_embeddings(
        item_texts, 
        batch_size=100,
        progress=progress, 
        task_id=task_ids['embed'],
        worker_id=worker_id
    )
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Calcular similaridades e atualizar progresso
    for idx, item_embed in enumerate(item_embeds):
        if item_embed is None:
            # Atualizar progresso mesmo para itens pulados
            with progress_lock:
                progress.update(task_ids['sim'], advance=1)
            continue
            
        # Calcular similaridade com todos os itens do catálogo
        sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
        
        # Obter TOP_N categorias com maior similaridade
        top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
        
        # Armazenar TOP_N categorias e scores
        for i, cat_idx in enumerate(top_indices):
            if i < TOP_N:  # Garantir que só usamos TOP_N categorias
                cod, nom = cat_meta[cat_idx]
                result_df.loc[idx, f"TOP_{i+1}"] = nom
                result_df.loc[idx, f"SCORE_{i+1}"] = float(sims[cat_idx])
        
        # Atualizar progresso de similaridade de forma thread-safe
        with progress_lock:
            progress.update(task_ids['sim'], advance=1)
    
    # Renomear coluna id para id_pncp se necessário
    if "id" in result_df.columns and "id_pncp" not in result_df.columns:
        result_df = result_df.rename(columns={"id": "id_pncp"})
    
    return result_df

def process_file_parallel(input_file, cat_embeddings, cat_meta, file_idx):
    """
    Processa um arquivo usando paralelismo interno - divide o arquivo em chunks
    e processa cada chunk em uma thread separada, com visualização melhorada usando rich.
    """
    try:
        filename = os.path.basename(input_file)
        console.print(f"[bold blue]Processando arquivo {file_idx}: {filename}[/bold blue]")
        
        # Carregar arquivo de entrada
        df_input = load_input_file(input_file)
        total_rows = len(df_input)
        
        # Calcular tamanho de cada chunk para processamento paralelo
        chunk_size = max(1, min(1000, math.ceil(total_rows / MAX_WORKERS)))
        total_chunks = math.ceil(total_rows / chunk_size)
        
        console.print(f"[cyan]Arquivo tem {total_rows} linhas. Dividindo em {total_chunks} chunks de ~{chunk_size} linhas cada[/cyan]")
        
        # Limpar a tela antes de iniciar
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Inicializar a lista para armazenar resultados dos chunks
        chunks_results = []
        
        # Criar um objeto Progress compartilhado para todos os workers
        progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn()
        ]
        
        # Iniciar o processamento com barras de progresso dedicadas para cada worker e fase
        with Progress(*progress_columns) as progress:
            # Dicionário para armazenar os task_ids para cada worker e fase
            all_tasks = {}
            
            # Criar tarefas para cada worker e cada fase do processamento
            for chunk_idx in range(min(total_chunks, MAX_WORKERS)):
                worker_id = chunk_idx + 1
                worker_prefix = f"Worker {worker_id:02d}"
                
                # Calcular o número de itens deste chunk
                start_idx = chunk_idx * chunk_size
                end_idx = min(start_idx + chunk_size, total_rows)
                items_in_chunk = end_idx - start_idx
                
                # Criar tarefas para cada fase deste worker
                preproc_task = progress.add_task(
                    f"{worker_prefix} - Pré-processamento", 
                    total=items_in_chunk
                )
                
                # Para embeddings, calcular o número de batches
                embed_batches = math.ceil(items_in_chunk / 100)  # batch_size=100 no get_embeddings
                embed_task = progress.add_task(
                    f"{worker_prefix} - Embeddings", 
                    total=embed_batches
                )
                
                sim_task = progress.add_task(
                    f"{worker_prefix} - Similaridade", 
                    total=items_in_chunk
                )
                
                # Armazenar os task_ids para este worker
                all_tasks[worker_id] = {
                    'preproc': preproc_task,
                    'embed': embed_task,
                    'sim': sim_task
                }
            
            # Adicionar uma tarefa para o progresso geral
            master_task = progress.add_task(
                f"[yellow]Progresso geral dos chunks", 
                total=total_chunks
            )
            
            # Criar chunks do DataFrame e processá-los em paralelo
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                # Submeter cada chunk para processamento em paralelo
                for chunk_idx in range(min(total_chunks, MAX_WORKERS)):
                    start_idx = chunk_idx * chunk_size
                    end_idx = min(start_idx + chunk_size, total_rows)
                    
                    # Obter chunk do DataFrame
                    chunk_df = df_input.iloc[start_idx:end_idx].copy().reset_index(drop=True)
                    
                    # ID do worker (1-based)
                    worker_id = chunk_idx + 1
                    
                    # Submeter tarefa com referências às barras de progresso
                    future = executor.submit(
                        process_chunk, 
                        chunk_df, 
                        cat_embeddings, 
                        cat_meta, 
                        worker_id,
                        progress,
                        all_tasks[worker_id]
                    )
                    futures.append((future, chunk_idx))
                
                # Coletar resultados à medida que ficam prontos
                for future, chunk_idx in as_completed(futures):
                    try:
                        result = future.result()
                        chunks_results.append(result)
                        # Atualizar o progresso geral
                        progress.update(master_task, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro no chunk {chunk_idx}: {str(e)}[/bold red]")
                        console.print(traceback.format_exc())
                
                # Processar chunks restantes sequencialmente
                # Reutilizamos os mesmos task_ids dos workers já concluídos
                for chunk_idx in range(MAX_WORKERS, total_chunks):
                    worker_id = (chunk_idx % MAX_WORKERS) + 1  # Reutilizar IDs de 1 a MAX_WORKERS
                    
                    # Resetar os progressos das tarefas para este worker
                    task_ids = all_tasks[worker_id]
                    for task_id in task_ids.values():
                        progress.reset(task_id)
                    
                    start_idx = chunk_idx * chunk_size
                    end_idx = min(start_idx + chunk_size, total_rows)
                    items_in_chunk = end_idx - start_idx
                    
                    # Atualizar os totais para o novo chunk
                    embed_batches = math.ceil(items_in_chunk / 100)
                    progress.update(task_ids['preproc'], total=items_in_chunk, completed=0)
                    progress.update(task_ids['embed'], total=embed_batches, completed=0)
                    progress.update(task_ids['sim'], total=items_in_chunk, completed=0)
                    
                    # Processar o chunk
                    chunk_df = df_input.iloc[start_idx:end_idx].copy().reset_index(drop=True)
                    try:
                        result = process_chunk(
                            chunk_df, 
                            cat_embeddings, 
                            cat_meta, 
                            worker_id,
                            progress,
                            task_ids
                        )
                        chunks_results.append(result)
                        # Atualizar o progresso geral
                        progress.update(master_task, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro no chunk {chunk_idx}: {str(e)}[/bold red]")
                        console.print(traceback.format_exc())
        
        # Combinar todos os chunks em um único DataFrame de resultado
        console.print("[cyan]Combinando resultados dos chunks...[/cyan]")
        if chunks_results:
            combined_results = pd.concat(chunks_results, ignore_index=True)
            
            # Manter apenas as colunas desejadas na ordem especificada
            desired_columns = ['id_pncp', 'objetoCompra']
            
            # Adicionar TOP_1 a TOP_10
            for i in range(1, TOP_N + 1):
                desired_columns.append(f"TOP_{i}")
            
            # Adicionar SCORE_1 a SCORE_10
            for i in range(1, TOP_N + 1):
                desired_columns.append(f"SCORE_{i}")
            
            # Filtrar apenas as colunas existentes no DataFrame
            final_columns = [col for col in desired_columns if col in combined_results.columns]
            combined_results = combined_results[final_columns]
            
            # Gerar nome do arquivo de saída baseado no nome do arquivo de entrada
            output_file = os.path.join(OUTPUT_PATH, f"RESULT_{os.path.basename(input_file)}")
            
            # Salvar resultados combinados
            combined_results.to_excel(output_file, index=False)
            console.print(f"[green]Resultado do arquivo {file_idx} salvo em {output_file}[/green]")
            
            return input_file, True
        else:
            console.print(f"[bold red]Nenhum resultado gerado para o arquivo {filename}[/bold red]")
            return input_file, False
            
    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo {file_idx}: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return input_file, False

def main():
    start_time = time.time()
    
    try:
        # Verificar checkpoint existente
        checkpoint = load_checkpoint()
        processed_files = checkpoint['processed_files'] if checkpoint else []
        
        # Obter lista de arquivos de entrada na ordem correta
        input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "INPUT_*.xlsx")))
        console.print(f"[bold blue]Encontrados {len(input_files)} arquivos de entrada[/bold blue]")
        
        # Filtrar apenas arquivos não processados
        remaining_files = [f for f in input_files if f not in processed_files]
        console.print(f"[bold blue]Processando {len(remaining_files)} arquivos restantes[/bold blue]")
        
        if not remaining_files:
            console.print("[yellow]Todos os arquivos já foram processados.[/yellow]")
            return
        
        # Carregar catálogo unificado
        cat = load_catalog()
        
        # Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if (cat_embeddings is None or len(cat_embeddings) != len(cat_texts)):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Criar um único objeto Progress para o processamento de arquivos
        file_progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold cyan]Progresso de arquivos:"),
            BarColumn(bar_width=50),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn()
        ]
        
        # Processar arquivos SEQUENCIALMENTE, um de cada vez
        with Progress(*file_progress_columns) as file_progress:
            file_task = file_progress.add_task(
                "Processando arquivos", 
                total=len(remaining_files)
            )
            
            for idx, input_file in enumerate(remaining_files, 1):
                # Processar um arquivo por vez, com paralelismo INTERNO
                file_path, success = process_file_parallel(
                    input_file, 
                    cat_embeddings, 
                    cat_meta,
                    idx
                )
                
                if success:
                    processed_files.append(file_path)
                    save_checkpoint(processed_files)
                
                file_progress.update(file_task, advance=1)
                
                # Pausa visual entre arquivos
                time.sleep(1)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Processamento concluído em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total)[/green]")
        console.print(f"[cyan]Os resultados foram salvos em: {OUTPUT_PATH}[/cyan]")
                
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        console.print(traceback.format_exc())

# Executar o código principal
if __name__ == "__main__":
    main()