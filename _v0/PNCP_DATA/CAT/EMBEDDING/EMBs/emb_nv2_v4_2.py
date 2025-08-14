### EMB_NV2_v4 (EMBEDDING NIVEL 2 V4) ###

# Este script é responsável por gerar embeddings para itens de compras e classificá-los em categorias unificadas.
# Modificação: Adaptado para usar NOVA CAT.xlsx em vez dos arquivos CATMAT e CATSER separados.

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

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
INPUT_PATH = CLASS_PATH + "INPUT\\"
OUTPUT_PATH = CLASS_PATH + "OUTPUT\\"
#EXCEL_FILE = TESTE_PATH + "TESTE_SIMPLES_ITENS.xlsx"
#SHEET = "OBJETOS"
INPUT_FILE = INPUT_PATH + "\\INPUT_001.xlsx"
SHEET = "Sheet1"

NOVA_CAT_FILE = NOVA_CAT_PATH + "NOVA CAT.xlsx"
NOVA_CAT_SHEET = "CAT_NV4"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = OUTPUT_PATH + f"OUTPUT_001_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = TESTE_PATH + f"CHECKPOINT_001_{TIMESTAMP}.pkl"

# BATCH e MAX_WORKERS
BATCH_SIZE = 1000  # Tamanho do batch para processamento e salvamento

# Constantes para controle de execução
MAX_WORKERS = 20 #os.cpu_count() * 4 # Número de threads para processamento paralelo
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
            #console.print(f"[green]Embeddings carregados de {filepath}[/green]")
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

def save_checkpoint(last_processed, output_file):
    """Salvar checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)

def load_data():
    """Carregar dados do Excel e catálogo unificado."""
    console.print("[bold magenta]Carregando dados e catálogo unificado...[/bold magenta]")
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint = load_checkpoint()
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        
        # Carregar apenas as linhas ainda não processadas
        try:
            # Primeiro, verificamos o tamanho total para calcular o offset
            total_rows = pd.read_excel(INPUT_FILE, sheet_name=SHEET, nrows=0).shape[0]
            
            # Depois carregamos apenas as linhas restantes
            skiprows = list(range(1, last_processed + 1))  # Pular cabeçalho + linhas já processadas
            df_items = pd.read_excel(INPUT_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel (a partir da linha {last_processed+1}).[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    else:
        # Carregar do início
        try:
            df_items = pd.read_excel(INPUT_FILE, sheet_name=SHEET)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    
    # Carregar catálogo unificado
    try:
        # Carrega o catálogo unificado a partir do arquivo Excel "NOVA CAT".xlsx
        catalog_file = NOVA_CAT_FILE
        cat_df = pd.read_excel(catalog_file, sheet_name=NOVA_CAT_SHEET)
        # Converte o DataFrame para uma lista de dicionários
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Carregadas {len(cat)} categorias do catálogo unificado.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar catálogo unificado: {str(e)}[/bold red]")
        raise
    
    # Se temos checkpoint, precisamos também carregar os resultados já processados
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Carregados {len(existing_results)} resultados anteriores.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
            existing_results = pd.DataFrame()
    else:
        existing_results = pd.DataFrame()
    
    return df_items, cat, existing_results, checkpoint

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
            #combined_text = f"{codcat} {nomcat}"
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("", total=total_batches)
            
            # Loop de processamento com progresso visível
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = process_batch(batch, model)
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
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

def classify_items_batched(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens
    e compara com os embeddings do catálogo unificado para classificação.
    """
    answers = []
    
    # Obtém os textos dos itens e aplica o pré-processamento
    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Calcula os embeddings dos textos dos itens
    item_embeds = embedding_function(item_texts)
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Para cada item, calcula a similaridade com todos os embeddings do catálogo
    with Progress(SpinnerColumn(), TextColumn("[bold blue]ITENS..."), 
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),transient=False) as progress:
        task = progress.add_task("", total=len(item_embeds))
        
        for item_embed in item_embeds:
            sims = [cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds]
            best_idx = np.argmax(sims) if sims else -1
            if best_idx >= 0:
                # cat_meta contém tuplas (CODCAT, NOMCAT)
                best_cat = cat_meta[best_idx]
                answer = best_cat[1]  # Retorna o NOMCAT como resposta
            else:
                answer = ""
            answers.append(answer)
            progress.update(task, advance=1)
    
    df_items = df_items.copy()
    df_items["answer"] = answers
    return df_items

def classify_items_batched(df_items, cat_embeds, cat_meta, embedding_function):
    """
    Processa os itens de df_items, calcula os embeddings dos textos dos itens
    e compara com os embeddings do catálogo unificado para classificação.
    """
    # Criar DataFrame de resultados
    result_df = df_items.copy()
    
    # Adicionar TOP_1 a TOP_10 e SCORE_1 a SCORE_10
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    # Obtém os textos dos itens e aplica o pré-processamento
    raw_texts = df_items["objetoCompra"].fillna("").tolist()
    item_texts = [preprocess_text(text) for text in raw_texts]
    
    # Calcula os embeddings dos textos dos itens
    item_embeds = embedding_function(item_texts)
    
    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)
    
    # Para cada item, calcula a similaridade com todos os embeddings do catálogo
    with Progress(SpinnerColumn(), TextColumn("[bold blue]ITENS..."), 
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),transient=False) as progress:
        task = progress.add_task("", total=len(item_embeds))
        
        for idx, item_embed in enumerate(item_embeds):
            if item_embed is None:
                progress.update(task, advance=1)
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
            
            progress.update(task, advance=1)
    
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
    return result_df[final_columns]

def main():
    start_time = time.time()
    
    try:
        # Carregar dados e verificar se existe checkpoint
        df_items, cat, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
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
        
        # Classificar items em batches com processamento paralelo
        console.print("[bold magenta]Iniciando classificação em batches com processamento paralelo...[/bold magenta]")
        results = classify_items_batched(
            df_items, 
            cat_embeddings, 
            cat_meta, 
            get_embeddings
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        console.print(f"[cyan]Os embeddings foram salvos em:")
        console.print(f"- Catálogo: {CAT_EMBED_FILE}")

        # Salvar resultados no arquivo Excel
        console.print(f"[bold magenta]Salvando resultados em {OUTPUT_FILE}...[/bold magenta]")
        results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[green]Resultados salvos com sucesso![/green]")
                
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

# Executar o código principal
if __name__ == "__main__":
    main()