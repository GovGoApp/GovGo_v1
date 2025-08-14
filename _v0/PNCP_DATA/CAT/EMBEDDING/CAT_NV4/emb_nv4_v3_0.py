### EMB_NV2_v4_3 (EMBEDDING NIVEL 2 V4.3) ###

# Este script é responsável por gerar embeddings para itens de compras e classificá-los em categorias unificadas.
# Modificação: Adaptado para processar arquivos grandes (1 milhão de linhas) em batches paralelos.

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle
import time
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from tqdm.auto import tqdm

# Baixar recursos NLTK necessários
nltk.download('stopwords')
nltk.download('wordnet')

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")  # Novo caminho para o catálogo unificado
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
TESTE_PATH = CLASS_PATH + "TESTE\\"
EXCEL_FILE = TESTE_PATH + "TESTE_SIMPLES_ITENS.xlsx" # CLASS_PATH + "#CONTRATAÇÃO_ID_COMPRAS_ITENS.xlsx" # 
SHEET = "OBJETOS" #"ITENS"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_DIR = TESTE_PATH + f"RESULTADOS_{TIMESTAMP}\\"
CHECKPOINT_FILE = TESTE_PATH + f"CHECKPOINT_TESTE_SIMPLES_ITENS_{TIMESTAMP}.pkl"

# Criar diretório de saída se não existir
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BATCH e MAX_WORKERS
BATCH_SIZE = 20  # Tamanho do batch para processamento e salvamento (AJUSTADO PARA 1000)

# Constantes para controle de execução
MAX_WORKERS = 15 #30  # Número de threads para processamento paralelo
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
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def save_checkpoint(last_processed):
    """Salvar checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[yellow]Checkpoint salvo: processadas {last_processed} linhas[/yellow]")

def get_total_rows():
    """Obtém o número total de linhas no arquivo Excel."""
    try:
        # Abordagem mais robusta usando pandas para contar linhas
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
        total_rows = len(df)
        return total_rows
    except Exception as e:
        console.print(f"[bold red]Erro ao verificar total de linhas: {str(e)}[/bold red]")
        raise

def load_batch(start_row, batch_size):
    """Carrega um batch específico do arquivo Excel."""
    try:
        # Calcular linhas a pular (header + linhas anteriores)
        skiprows = list(range(1, start_row + 1))  # Pular cabeçalho + linhas anteriores
        
        # Carregar apenas o batch atual
        df_batch = pd.read_excel(
            EXCEL_FILE, 
            sheet_name=SHEET, 
            skiprows=skiprows,
            nrows=batch_size
        )
        
        return df_batch
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar batch {start_row}-{start_row+batch_size}: {str(e)}[/bold red]")
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

def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=100, show_progress=True):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI."""
    embeddings = []
    
    # Processar em lotes para evitar limites de token ou requisição
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Determinar como processar - com ou sem barra de progresso
    if show_progress:
        # Usar tqdm para mostrar progresso
        for i in tqdm(range(0, len(texts), batch_size), 
                     total=total_batches, 
                     desc="Gerando embeddings", 
                     position=1):
            batch = texts[i:i+batch_size]
            batch_embeddings = process_batch(batch, model)
            embeddings.extend(batch_embeddings)
    else:
        # Loop de processamento sem progresso visível
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = process_batch(batch, model)
            embeddings.extend(batch_embeddings)
    
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

def classify_items_batched_tqdm(df_items, cat_embeds, cat_meta, embedding_function, batch_id=None):
    """
    Versão da função classify_items_batched que usa tqdm para mostrar progresso.
    """
    # Criar DataFrame de resultados
    result_df = df_items.copy()
    
    # Adicionar TOP_1 a TOP_10 e SCORE_1 a SCORE_10
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    # Obtém os textos dos itens concatenando "objetoCompra" e "itens" e aplica o pré-processamento
    batch_prefix = f"Batch {batch_id}" if batch_id is not None else "Batch"
    print(f"Processando {batch_prefix} - Preparando textos...")
    
    # Substituindo valores nulos com strings vazias para evitar problemas de concatenação
    objeto_compra = df_items["objetoCompra"].fillna("").astype(str)
    #itens = df_items["itens"].fillna("").astype(str)
    

    # Concatenar os dois campos
    #raw_texts = [f"{obj} {item}" for obj, item in zip(objeto_compra, itens)]
    raw_texts = objeto_compra
    # Pré-processar os textos concatenados com barra de progresso
    print(f"Pré-processando textos do {batch_prefix}...")
    item_texts = []
    for text in tqdm(raw_texts, desc=f"{batch_prefix} - Pré-processamento", position=0):
        item_texts.append(preprocess_text(text))
    
    # Calcula os embeddings dos textos dos itens
    print(f"Gerando embeddings para {len(item_texts)} itens do {batch_prefix}...")
    item_embeds = embedding_function(item_texts, show_progress=False)
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Para cada item, calcula a similaridade com todos os embeddings do catálogo
    print(f"Calculando similaridades para o {batch_prefix}...")
    
    # Usar tqdm para mostrar progresso por item dentro do batch
    for idx, item_embed in tqdm(enumerate(item_embeds), 
                                total=len(item_embeds),
                                desc=f"{batch_prefix} - Similaridade",
                                position=0):
        if item_embed is None:
            continue
            
        # Calcular similaridade com todos os itens do catálogo
        sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
        
        # Obter TOP_N categorias com maior similaridade
        top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
        
        # Armazenar TOP_N categorias e scores
        for i, cat_idx in enumerate(top_indices):
            if i < TOP_N:  # Garantir que só usamos TOP_N categorias
                _, nom = cat_meta[cat_idx]
                result_df.loc[idx, f"TOP_{i+1}"] = nom
                result_df.loc[idx, f"SCORE_{i+1}"] = float(sims[cat_idx])
    
    # Renomear coluna id para id_pncp se necessário
    if "id" in result_df.columns and "id_pncp" not in result_df.columns:
        result_df = result_df.rename(columns={"id": "id_pncp"})
    
    # Manter apenas as colunas desejadas na ordem especificada
    desired_columns = ['id_pncp', 'objetoCompra']
    
    # Adicionar TOP_1 a TOP_10
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"TOP_{i}")
    
    # Adicionar SCORE_1 a SCORE_10
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"SCORE_{i}")
    
    # Filtrar apenas as colunas existentes no DataFrame
    final_columns = [col for col in desired_columns if col in result_df.columns]
    
    # Retornar DataFrame com apenas as colunas desejadas
    print(f"{batch_prefix} - Classificação concluída!")
    return result_df[final_columns]

def process_batch_job(batch_id, start_row, batch_size, cat_embeddings, cat_meta):
    """Função para processar um batch completo como um job separado usando tqdm."""
    try:
        console.print(f"[bold blue]Iniciando processamento do batch {batch_id} (linhas {start_row+1}-{start_row+batch_size})...[/bold blue]")
        
        # Carregar batch
        df_batch = load_batch(start_row, batch_size)
        
        # Processar batch com tqdm para visualizar progresso
        results_batch = classify_items_batched_tqdm(
            df_batch, 
            cat_embeddings, 
            cat_meta, 
            get_embeddings,
            batch_id
        )
        
        # Salvar resultados do batch
        output_file = f"{OUTPUT_DIR}batch_{batch_id:06d}.xlsx"
        results_batch.to_excel(output_file, index=False)
        console.print(f"[green]Batch {batch_id} salvo em {output_file}[/green]")
        
        return batch_id, results_batch, start_row, batch_size
    except Exception as e:
        console.print(f"[bold red]Erro no batch {batch_id}: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return batch_id, None, start_row, batch_size

def merge_results(batch_results, output_file):
    """Mescla os resultados de todos os batches em um único arquivo."""
    console.print("[bold magenta]Mesclando resultados de todos os batches...[/bold magenta]")
    
    all_results = pd.concat(batch_results, ignore_index=True)
    all_results.to_excel(output_file, index=False)
    console.print(f"[green]Resultados mesclados salvos em {output_file}[/green]")
    return all_results

def main():
    start_time = time.time()
    
    try:
        # Verificar checkpoint existente
        checkpoint = load_checkpoint()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Obter número total de linhas
        total_rows = get_total_rows()
        console.print(f"[bold blue]Arquivo com {total_rows} linhas a processar[/bold blue]")
        
        # Carregar catálogo unificado
        cat = load_catalog()
        
        # Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Calcular batches a processar
        remaining_rows = total_rows - last_processed
        console.print(f"[bold blue]Processando {remaining_rows} linhas restantes em batches de {BATCH_SIZE}...[/bold blue]")
        
        # Criar lista de batches para processar
        batch_jobs = []
        for batch_id, start_row in enumerate(range(last_processed, total_rows, BATCH_SIZE), start=1):
            end_row = min(start_row + BATCH_SIZE, total_rows)
            batch_size = end_row - start_row
            batch_jobs.append((batch_id, start_row, batch_size))
        
        total_batches = len(batch_jobs)
        console.print(f"[bold blue]Total de {total_batches} batches a processar[/bold blue]")
        
        # Processar batches em paralelo com ThreadPoolExecutor
        completed_batches = []
        successful_results = []
        
        console.print(f"[bold blue]Total de {len(batch_jobs)} batches a processar[/bold blue]")
        
        # Criar um tqdm global para todos os batches
        global_progress = tqdm(total=len(batch_jobs), desc="Progresso geral", position=2)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submeter jobs para o executor
            future_to_batch = {
                executor.submit(
                    process_batch_job, 
                    batch_id, 
                    start_row, 
                    batch_size, 
                    cat_embeddings, 
                    cat_meta
                ): (batch_id, start_row, batch_size) 
                for batch_id, start_row, batch_size in batch_jobs
            }
            
            # Processar resultados à medida que são concluídos
            for future in as_completed(future_to_batch):
                batch_id, results, start_row, batch_size = future.result()
                completed_batches.append(batch_id)
                
                if results is not None:
                    successful_results.append(results)
                
                # Atualizar checkpoint após cada batch
                with checkpoint_lock:
                    last_row_processed = start_row + batch_size
                    save_checkpoint(last_row_processed)
                
                # Atualizar o progresso global
                global_progress.update(1)
        
        # Fechar a barra de progresso global
        global_progress.close()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Processamento concluído em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total)[/green]")
        
        # Opcionalmente, mesclar resultados em um único arquivo
        if successful_results:
            merged_output = TESTE_PATH + f"TESTE_SIMPLES_ITENS_CATNV4_OPENAI_COMPLETO_{TIMESTAMP}.xlsx"
            merge_results(successful_results, merged_output)
        
        console.print(f"[cyan]Os embeddings do catálogo foram salvos em:")
        console.print(f"- {CAT_EMBED_FILE}")
        console.print(f"[cyan]Os resultados em batches foram salvos em:")
        console.print(f"- {OUTPUT_DIR}")
                
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

# Executar o código principal
if __name__ == "__main__":
    main()