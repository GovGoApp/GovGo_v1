### EMB_NV4_v2 - Versão com processamento de lotes em paralelo

import os
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.progress import TaskProgressColumn, MofNCompleteColumn
from rich.panel import Panel
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle
import time
import re
import unidecode
import nltk
import concurrent.futures
import queue

# Adicione esta função no início do arquivo, após as importações
from rich.table import Table
from rich import box

def create_batch_status_table(batch_statuses, completed, total):
    """Cria uma tabela estática de status para os lotes."""
    table = Table(
        title=f"Processamento de Lotes ({completed}/{total} concluídos)",
        box=box.SIMPLE,
        expand=False,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Última Atualização", style="yellow", no_wrap=True)
    table.add_column("Status", style="green")
    
    # Mostrar apenas os 12 últimos lotes por ordem de ID
    batch_ids = sorted(batch_statuses.keys())[-12:]
    
    for batch_id in batch_ids:
        status = batch_statuses.get(batch_id, {})
        
        # Determinar a cor do status
        status_msg = status.get("message", "Desconhecido")
        if "CONCLUÍDO" in status_msg:
            style = "green"
        elif "ERRO" in status_msg:
            style = "red"
        elif "Calculando" in status_msg:
            style = "blue"
        elif "Gerando" in status_msg:
            style = "yellow"
        else:
            style = "white"
            
        table.add_row(
            f"{batch_id}",
            status.get("time", ""),
            f"[{style}]{status_msg}[/{style}]"
        )
    
    return table

# Usar as mesmas configurações e imports do arquivo original...

# Criar instância do console
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
EXCEL_FILE = CLASS_PATH + "#CONTRATAÇÃO_ID_COMPRAS_ITENS.xlsx"  # Arquivo com 1M de linhas
SHEET = "ITENS"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = CLASS_PATH + f"GRANDES_VOLUMES_CATNV4_OPENAI_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_GRANDES_VOLUMES_{TIMESTAMP}.pkl"
BATCH_OUTPUT_DIR = os.path.join(CLASS_PATH, "BATCH_OUTPUT")

# Criar diretório para outputs em batch se não existir
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)

# BATCH e MAX_WORKERS
MAX_CONCURRENT_BATCHES = 12 # Máximo de lotes ativos simultaneamente
BATCH_SIZE = 5000  # Tamanho do batch para processamento e salvamento
SAVE_EVERY_N_BATCHES = 1  # Frequência de salvamento (a cada N batches)

# Constantes para controle de execução
MAX_WORKERS = os.cpu_count() * 2  # Número de threads para processamento paralelo

console.print(f"[bold cyan]CPU cores: {os.cpu_count()}[/bold cyan]")
console.print(f"[bold cyan]Workers configurados: {MAX_WORKERS}[/bold cyan]")

TOP_N = 10  # Número de categorias mais relevantes a serem retornadas

# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = BASE_PATH + "EMBEDDING\\"
CAT_EMBED_FILE = EMBEDDINGS_DIR + f"{NOVA_CAT_SHEET}_OPENAI_text_embedding_3_large.pkl"

# Criar os diretórios se não existirem
for directory in [EMBEDDINGS_DIR, BATCH_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Criar lock para acessos concorrentes
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
output_files_lock = threading.Lock() 

# Inicializar NLTK
try:
    # Configurar caminho para dados NLTK
    nltk_data_path = os.path.join(os.path.expanduser('~'), 'nltk_data')
    os.makedirs(nltk_data_path, exist_ok=True)
    nltk.data.path.append(nltk_data_path)
    
    # Baixar recursos necessários
    for resource in ['stopwords', 'wordnet']:
        try:
            nltk.download(resource, quiet=True)
        except Exception as e:
            console.print(f"[yellow]Aviso: Não foi possível baixar {resource}: {str(e)}[/yellow]")
    
    # Carregar stopwords antecipadamente
    from nltk.corpus import stopwords
    portuguese_stopwords = set(stopwords.words('portuguese'))
    
    # Inicializar lematizador
    from nltk.stem import WordNetLemmatizer
    lemmatizer = WordNetLemmatizer()
    
except Exception as e:
    console.print(f"[bold red]Erro na configuração do NLTK: {str(e)}[/bold red]")
    # Fallback - define stopwords e lemmatizer vazios
    portuguese_stopwords = set()
    
    class SimpleLemmatizer:
        def lemmatize(self, word):
            return word
    
    lemmatizer = SimpleLemmatizer()


def preprocess_text(text):
    """Aplica pré-processamento no texto."""
    try:
        # Remover acentuação e converter para string
        text = unidecode.unidecode(str(text))
        # Converter para minúsculas
        text = text.lower()
        # Remover caracteres não alfabéticos
        text = re.sub(r'[^a-z\s]', '', text)
        
        # Remover stopwords
        words = text.split()
        words = [word for word in words if word not in portuguese_stopwords]
        
        # Lematizar
        words = [lemmatizer.lemmatize(word) for word in words]
        
    except Exception as e:
        # Em caso de erro, aplicar um processamento mais simples
        console.print(f"[yellow]Aviso: Usando processamento simplificado para texto: {str(e)}[/yellow]")
        text = unidecode.unidecode(str(text)).lower()
        text = re.sub(r'[^a-z\s]', '', text)
        words = [word for word in text.split() if len(word) > 2]
    
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


def save_checkpoint(last_processed, output_file, batch_files=None):
    """Salva checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file,
            'batch_files': batch_files or []
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo: {last_processed} itens processados[/green]")


def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
            console.print(f"[yellow]Checkpoint encontrado - Último processado: {checkpoint['last_processed']}[/yellow]")
            return checkpoint
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar checkpoint: {str(e)}[/bold red]")
    return None


def load_data():
    """Carrega dados do Excel e catálogo unificado."""
    console.print(Panel.fit("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]"))
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint = load_checkpoint()
    last_processed = 0
    batch_files = []
    
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint.get('last_processed', 0)
        batch_files = checkpoint.get('batch_files', [])
        
        # Preparar para pular as linhas já processadas
        skiprows = list(range(1, last_processed + 1)) if last_processed > 0 else None
    else:
        skiprows = None
    
    # Carregar os dados do Excel
    try:
        if skiprows:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel (a partir da linha {last_processed+1}).[/green]")
        else:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
        raise
    
    # Carregar catálogo unificado
    try:
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Carregadas {len(cat)} categorias do catálogo unificado.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise
    
    return df_items, cat, last_processed, batch_files, checkpoint


def prepare_catalog_entries(cat):
    """Preparar entradas de catálogo unificado para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo unificado...[/bold magenta]")
    
    cat_texts = []
    cat_meta = []
    
    for entry in cat:
        # Utiliza as colunas CODCAT e NOMCAT do arquivo Excel
        codcat = entry.get('CODCAT', '')
        nomcat = entry.get('NOMCAT', '')
        # Forma o texto de embedding concatenando os dois campos com um espaço
        combined_text = preprocess_text(f"{codcat} {nomcat}")
        cat_texts.append(combined_text)
        cat_meta.append((codcat, nomcat))
    
    console.print(f"[magenta]Preparados {len(cat_texts)} textos de catálogo unificado.[/magenta]")
    return cat_texts, cat_meta


def process_batch(batch, model=EMBEDDING_MODEL):
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
                # Use console.print em vez de status para mensagens de erro
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI (lote de {len(batch)} textos): {str(e)}[/bold red]")
                raise

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=25, use_status=False):
    """Gera embeddings sem criar barras de progresso que causariam conflito."""
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Nunca usar barras de progresso aqui - apenas logs estáticos
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = process_batch(batch, model)
        embeddings.extend(batch_embeddings)
    
    return embeddings

def cosine_similarity(a, b):
    """Calcula similaridade de cosseno entre dois vetores."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

def process_text_batch(texts):
    """Processa um lote de textos aplicando pré-processamento paralelo."""
    return [preprocess_text(text) for text in texts]

def process_complete_batch(batch_df, cat_embeds, cat_meta, batch_id, start_idx, log_queue):
    """Processa um lote completo com logs estáticos em vez de barras de progresso."""
    batch_start_time = time.time()
    
    try:
        # Enviar início de processamento para o log centralizado
        log_queue.put((batch_id, f"Lote {batch_id} iniciado - {len(batch_df)} itens"))
        
        # Criar DataFrame de resultados
        result_df = batch_df.copy()
        
        # Adicionar TOP_N colunas
        for i in range(1, TOP_N + 1):
            result_df[f"TOP_{i}"] = ""
            result_df[f"SCORE_{i}"] = 0.0
        
        # 1. Extrair textos (sem barra de progresso)
        raw_texts = []
        for _, row in batch_df.iterrows():
            obj_compra = str(row.get("objetoCompra", ""))
            itens = str(row.get("itens", ""))
            combined_text = f"{obj_compra} {itens}".strip()
            raw_texts.append(combined_text)
        
        log_queue.put((batch_id, f"Lote {batch_id} - Extração de textos concluída"))
        
        # 2. Pré-processar textos (sem barra de progresso)
        with ThreadPoolExecutor(max_workers=max(2, MAX_WORKERS // 4)) as executor:
            chunk_size = max(1, len(raw_texts) // (MAX_WORKERS // 4))
            chunks = [raw_texts[i:i+chunk_size] for i in range(0, len(raw_texts), chunk_size)]
            processed_chunks = list(executor.map(process_text_batch, chunks))
        
        processed_texts = []
        for chunk in processed_chunks:
            processed_texts.extend(chunk)
        
        log_queue.put((batch_id, f"Lote {batch_id} - Pré-processamento concluído"))
        
        # 3. Gerar embeddings (sem barra de progresso)
        item_embeds = get_embeddings(processed_texts)
        log_queue.put((batch_id, f"Lote {batch_id} - Geração de embeddings concluída"))
        
        # 4. Calcular similaridades (sem barra de progresso)
        for idx, item_embed in enumerate(item_embeds):
            # Calcular similaridade com todas as categorias
            sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
            
            # Obter TOP_N categorias com maior similaridade
            top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
            
            # Armazenar TOP_N categorias e scores
            for i, cat_idx in enumerate(top_indices):
                if i < TOP_N:
                    _, nom = cat_meta[cat_idx]
                    result_df.iloc[idx, result_df.columns.get_loc(f"TOP_{i+1}")] = nom
                    result_df.iloc[idx, result_df.columns.get_loc(f"SCORE_{i+1}")] = float(sims[cat_idx])
            
            # Reportar progresso em intervalos mais largos para reduzir a quantidade de mensagens
            if idx % 1000 == 0 or idx == len(item_embeds) - 1:
                perc = int(100 * (idx + 1) / len(item_embeds))
                log_queue.put((batch_id, f"Lote {batch_id} - Calculando similaridades: {perc}%"))
        
        # Processar colunas finais
        if "id" in result_df.columns and "id_pncp" not in result_df.columns:
            result_df = result_df.rename(columns={"id": "id_pncp"})
        
        desired_columns = ['id_pncp', 'objetoCompra', 'itens']
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"TOP_{i}")
        for i in range(1, TOP_N + 1):
            desired_columns.append(f"SCORE_{i}")
        
        final_columns = [col for col in desired_columns if col in result_df.columns]
        result_df = result_df[final_columns]
        
        # Salvar resultados
        last_processed = start_idx + len(batch_df) - 1
        batch_filename = os.path.join(
            BATCH_OUTPUT_DIR, 
            f"batch_{batch_id:04d}_{start_idx}_{last_processed}.xlsx"
        )
        
        result_df.to_excel(batch_filename, index=False)
        
        # Calcular estatísticas e tempo
        batch_time = time.time() - batch_start_time
        items_per_second = len(batch_df) / batch_time
        
        log_queue.put((
            batch_id, 
            f"Lote {batch_id} CONCLUÍDO - {len(batch_df)} itens em {batch_time:.1f}s ({items_per_second:.1f} itens/s)"
        ))
        
        return {
            'batch_id': batch_id,
            'start_idx': start_idx,
            'last_processed': last_processed,
            'batch_file': batch_filename,
            'items_processed': len(batch_df),
            'processing_time': batch_time
        }
    
    except Exception as e:
        error_msg = f"Erro ao processar lote {batch_id}: {str(e)}"
        log_queue.put((batch_id, f"[ERRO] {error_msg}"))
        console.print(f"[bold red]{error_msg}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return None

def save_batch_results(batch_df, batch_number, start_idx, last_processed):
    """Salva um lote de resultados em um arquivo Excel separado."""
    # Criar nome do arquivo com informações do lote
    batch_filename = os.path.join(
        BATCH_OUTPUT_DIR, 
        f"batch_{batch_number:04d}_{start_idx}_{last_processed}.xlsx"
    )
    
    # Salvar o DataFrame no arquivo Excel
    batch_df.to_excel(batch_filename, index=False)
    console.print(f"[green]Lote {batch_number} salvo em {batch_filename}[/green]")
    
    return batch_filename

# Add this function to better track processed batches
def get_processed_batch_ids(batch_files):
    """Extract batch IDs from batch filenames to recognize already processed batches."""
    processed_ids = set()
    if not batch_files:
        return processed_ids
        
    for file_path in batch_files:
        try:
            # Extract batch ID from filename (format: batch_0001_start_end.xlsx)
            filename = os.path.basename(file_path)
            batch_id = int(filename.split('_')[1])
            processed_ids.add(batch_id)
        except (IndexError, ValueError):
            console.print(f"[yellow]Warning: Could not extract batch ID from {file_path}[/yellow]")
    
    return processed_ids

def save_checkpoint(last_processed, output_file, batch_files=None):
    """Salva checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        # Extract batch IDs from filenames
        batch_ids = list(get_processed_batch_ids(batch_files or []))
        
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file,
            'batch_files': batch_files or [],
            'processed_batch_ids': batch_ids  # Add this to track batch IDs
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo: {last_processed} itens processados, {len(batch_ids)} lotes concluídos[/green]")
        
def merge_batch_files(batch_files, output_file):
    """Mescla todos os arquivos de lotes em um único arquivo final."""
    console.print(Panel.fit(f"[bold green]Mesclando {len(batch_files)} arquivos de lote em arquivo final...[/bold green]"))
    
    all_dfs = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Mesclando lotes..."),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn()
    ) as progress:
        merge_task = progress.add_task("", total=len(batch_files))
        
        for batch_file in batch_files:
            try:
                df = pd.read_excel(batch_file)
                all_dfs.append(df)
                progress.update(merge_task, advance=1)
            except Exception as e:
                console.print(f"[bold red]Erro ao ler o arquivo {batch_file}: {str(e)}[/bold red]")
    
    if all_dfs:
        # Combinar todos os DataFrames
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # Salvar no arquivo final
        final_df.to_excel(output_file, index=False)
        console.print(f"[bold green]Arquivo final salvo com sucesso: {output_file}[/bold green]")
        console.print(f"[bold green]Total de {len(final_df)} registros processados[/bold green]")
    else:
        console.print("[bold red]Nenhum arquivo de lote pôde ser lido para mesclagem![/bold red]")

def main():
    """Função principal com processamento de lotes em paralelo e visualização estática."""
    console.print(Panel.fit("[bold yellow]EMB_NV4_v2 - Sistema de classificação com embeddings para grandes volumes[/bold yellow]"))
    console.print("[bold green]Versão otimizada com processamento em lotes paralelos e visualização estática[/bold green]")
    start_time = time.time()
    
    try:
        # 1. Carregar dados e checkpoint
        df_items, cat, last_processed, batch_files, checkpoint = load_data()
        
        # 2. Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # 3. Verificar embeddings de catálogo
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        else:
            console.print("[green]Embeddings de catálogo carregados com sucesso.[/green]")
        
        # 4. Dividir em lotes
        batches = []
        for i in range(0, len(df_items), BATCH_SIZE):
            batch_df = df_items.iloc[i:i+BATCH_SIZE].copy()
            batch_df = batch_df.reset_index(drop=True)
            batches.append(batch_df)
        
        # 5. Verificar quais lotes já foram processados
        processed_batch_ids = get_processed_batch_ids(batch_files)
        console.print(f"[yellow]Encontrados {len(processed_batch_ids)} lotes já processados[/yellow]")
        
        # Preparar lotes a serem processados com informações adicionais
        batches_with_info = []
        next_start_idx = last_processed + 1
        
        for idx, batch_df in enumerate(batches):
            batch_id = idx + 1
            
            # Verificar se este lote já foi processado
            if batch_id in processed_batch_ids:
                console.print(f"[yellow]Pulando lote {batch_id} (já processado)[/yellow]")
                next_start_idx += len(batch_df)
                continue
                
            # Adicionar à lista para processamento
            batches_with_info.append({
                'batch_id': batch_id,
                'start_idx': next_start_idx,
                'batch_df': batch_df
            })
            next_start_idx += len(batch_df)
        
        # Verificar se há lotes para processar
        total_batches = len(batches_with_info)
        total_items = sum(len(info['batch_df']) for info in batches_with_info)
        
        if total_batches == 0:
            console.print("[bold green]Todos os lotes já foram processados.[/bold green]")
            if batch_files:
                merge_batch_files(batch_files, OUTPUT_FILE)
            return
        
        console.print(f"[bold cyan]Processando {total_batches} lotes com total de {total_items} itens[/bold cyan]")
        console.print(f"[bold cyan]Usando {MAX_CONCURRENT_BATCHES} workers para processamento paralelo[/bold cyan]")
        
        # 6. Inicializar variáveis para acompanhamento
        current_batch_files = batch_files.copy() if batch_files else []
        completed_count = 0
        
        # Criar uma tabela para mostrar o status dos lotes
        from rich.table import Table
        from rich.live import Live
        
        # Criamos uma fila thread-safe para logs de status dos lotes
        from queue import Queue
        log_queue = Queue()
        
        # Dicionário para manter status por lote
        batch_status = {}
        
        # Função para gerar a tabela de status
        def generate_status_table():
            table = Table(title=f"Processamento de Lotes - {completed_count}/{total_batches} concluídos")
            table.add_column("Lote", justify="right", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Progresso", justify="right", style="blue")
            
            # Adicionar somente os últimos 10 lotes ativos
            active_batches = sorted(batch_status.keys())[-10:] if batch_status else []
            for batch_id in active_batches:
                table.add_row(
                    f"{batch_id}", 
                    batch_status[batch_id]["message"],
                    batch_status[batch_id]["time"]
                )
            
            return table
        
        # 7. Executar processamento com Live Table para status
        with Live(generate_status_table(), refresh_per_second=1) as live:
            # 8. Processar lotes em paralelo
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
                # Submeter todos os lotes para processamento
                future_to_batch = {}
                
                # Iniciar lotes de forma progressiva
                active_futures = set()
                pending_batches = list(batches_with_info)
                
                # Thread de processamento de logs
                def process_logs():
                    while True:
                        try:
                            # Obter uma mensagem da fila (timeout para permitir saída da thread)
                            batch_id, message = log_queue.get(timeout=0.5)
                            
                            # Atualizar o status deste lote
                            if batch_id not in batch_status:
                                batch_status[batch_id] = {
                                    "message": "",
                                    "time": datetime.now().strftime("%H:%M:%S")
                                }
                            
                            batch_status[batch_id]["message"] = message
                            batch_status[batch_id]["time"] = datetime.now().strftime("%H:%M:%S")
                            
                            # Atualizar a tabela
                            live.update(generate_status_table())
                            
                            # Marcar como processado
                            log_queue.task_done()
                        except queue.Empty:
                            # Verificar se devemos encerrar a thread
                            if not pending_batches and not active_futures:
                                break
                
                # Iniciar thread de processamento de logs
                import threading
                log_thread = threading.Thread(target=process_logs, daemon=True)
                log_thread.start()

                while pending_batches or active_futures:
                    # Submeter mais lotes se estiver abaixo do limite
                    while pending_batches and len(active_futures) < MAX_CONCURRENT_BATCHES:
                        batch_info = pending_batches.pop(0)
                        future = executor.submit(
                            process_complete_batch,
                            batch_info['batch_df'],
                            cat_embeddings,
                            cat_meta,
                            batch_info['batch_id'],
                            batch_info['start_idx'],
                            log_queue  # Passa a fila de logs para o processador de batch
                        )
                        future_to_batch[future] = batch_info
                        active_futures.add(future)
                        
                        # Inicializar status para este lote
                        batch_id = batch_info['batch_id']
                        batch_status[batch_id] = {
                            "message": "Aguardando...",
                            "time": datetime.now().strftime("%H:%M:%S")
                        }
                        live.update(generate_status_table())
                    
                    # Esperar pelo menos um lote ser concluído
                    done, active_futures = concurrent.futures.wait(
                        active_futures, 
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    
                    # Processar lotes concluídos
                    for future in done:
                        batch_info = future_to_batch[future]
                        batch_id = batch_info['batch_id']
                        
                        try:
                            # Obter resultado 
                            result = future.result()
                            
                            if result:
                                # Adicionar à lista de arquivos processados 
                                with output_files_lock:
                                    current_batch_files.append(result['batch_file'])
                                    completed_count += 1
                                
                                # Atualizar status na tabela
                                batch_status[batch_id]["message"] = f"CONCLUÍDO ({result['processing_time']:.1f}s)"
                                batch_status[batch_id]["time"] = datetime.now().strftime("%H:%M:%S")
                                live.update(generate_status_table())
                                
                                # Salvar checkpoint a cada N lotes
                                if completed_count % SAVE_EVERY_N_BATCHES == 0:
                                    # Ordenar arquivos por ID do lote
                                    sorted_files = sorted(
                                        current_batch_files, 
                                        key=lambda x: int(os.path.basename(x).split('_')[1])
                                    )
                                    save_checkpoint(result['last_processed'], OUTPUT_FILE, sorted_files)
                            
                        except Exception as e:
                            error_msg = f"Erro ao processar lote {batch_id}: {str(e)}"
                            console.print(f"[bold red]{error_msg}[/bold red]")
                            
                            # Atualizar status na tabela
                            batch_status[batch_id]["message"] = f"ERRO: {str(e)}"
                            batch_status[batch_id]["time"] = datetime.now().strftime("%H:%M:%S")
                            live.update(generate_status_table())
            
            # Esperar a thread de logs terminar
            log_thread.join(timeout=1.0)
        
        # 9. Salvar checkpoint final e mesclar arquivos
        if current_batch_files:
            # Ordenar arquivos por ID do lote
            sorted_batch_files = sorted(
                current_batch_files, 
                key=lambda x: int(os.path.basename(x).split('_')[1])
            )
            
            # Salvar checkpoint final
            save_checkpoint(next_start_idx - 1, OUTPUT_FILE, sorted_batch_files)
            
            # Mesclar todos os arquivos em um único arquivo final
            merge_batch_files(sorted_batch_files, OUTPUT_FILE)
        
        # 10. Exibir estatísticas totais
        end_time = time.time()
        total_time = end_time - start_time
        total_minutes = total_time / 60
        
        console.print(Panel.fit(f"[bold green]Processamento concluído![/bold green]"))
        console.print(f"[bold cyan]Tempo total: {total_minutes:.2f} minutos ({total_time:.2f} segundos)[/bold cyan]")
        
        if total_items > 0:
            console.print(f"[bold cyan]Média por item: {total_time/total_items:.4f} segundos[/bold cyan]")
            console.print(f"[bold cyan]Taxa de processamento: {total_items/total_time:.2f} itens/segundo[/bold cyan]")
        
        console.print(f"[bold cyan]Total de itens processados: {total_items}[/bold cyan]")
                
    except Exception as e:
        console.print(Panel.fit(f"[bold red]Erro durante processamento: {str(e)}[/bold red]"))
        import traceback
        console.print(traceback.format_exc())

# Executar o código principal se este arquivo for executado diretamente
if __name__ == "__main__":
    main()