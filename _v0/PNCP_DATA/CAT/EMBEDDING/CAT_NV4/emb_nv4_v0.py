### EMB_NV4_v0 


import os
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.progress import TaskProgressColumn, MofNCompleteColumn
from rich.panel import Panel
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import re
import unidecode
import nltk
import concurrent.futures

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
BATCH_SIZE = 10000  # Tamanho do batch para processamento e salvamento
SAVE_EVERY_N_BATCHES = 1  # Frequência de salvamento (a cada N batches)

# Constantes para controle de execução
MAX_WORKERS = max(os.cpu_count() * 2, 4)  # Número de threads para processamento paralelo
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
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise


def get_embeddings(texts, model=EMBEDDING_MODEL, batch_size=25):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI."""
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    with console.status("[bold green]Gerando embeddings...") as status:
        for i in range(0, len(texts), batch_size):
            status.update(f"[bold green]Gerando embeddings... Batch {i//batch_size + 1}/{total_batches}")
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


def process_item_batch(batch_df, cat_embeds, cat_meta, batch_id, progress, text_task, embed_task, sim_task):
    """Processa um lote de itens gerando embeddings e determinando as categorias similares."""
    # Criar DataFrame de resultados para este lote
    result_df = batch_df.copy()
    
    # Adicionar TOP_1 a TOP_10 e SCORE_1 a SCORE_10
    for i in range(1, TOP_N + 1):
        result_df[f"TOP_{i}"] = ""
        result_df[f"SCORE_{i}"] = 0.0
    
    # Extrair e combinar textos
    raw_texts = []
    for _, row in batch_df.iterrows():
        obj_compra = str(row.get("objetoCompra", ""))
        itens = str(row.get("itens", ""))
        combined_text = f"{obj_compra} {itens}".strip()
        raw_texts.append(combined_text)
        progress.update(text_task, advance=1)
    
    # Pré-processar textos
    console.print(f"[cyan]Batch {batch_id}: Pré-processando {len(raw_texts)} textos[/cyan]")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        chunk_size = max(1, len(raw_texts) // MAX_WORKERS)
        chunks = [raw_texts[i:i+chunk_size] for i in range(0, len(raw_texts), chunk_size)]
        processed_chunks = list(executor.map(process_text_batch, chunks))
    
    processed_texts = []
    for chunk in processed_chunks:
        processed_texts.extend(chunk)
    
    # Gerar embeddings
    console.print(f"[cyan]Batch {batch_id}: Gerando embeddings para {len(processed_texts)} textos[/cyan]")
    item_embeds = get_embeddings(processed_texts)
    progress.update(embed_task, advance=1)
    
    # Calcular similaridades
    console.print(f"[cyan]Batch {batch_id}: Calculando similaridades[/cyan]")
    
    for idx, item_embed in enumerate(item_embeds):
        # Calcular similaridade com todos os itens do catálogo
        sims = np.array([cosine_similarity(item_embed, cat_embed) for cat_embed in cat_embeds])
        
        # Obter TOP_N categorias com maior similaridade
        top_indices = np.argsort(sims)[-TOP_N:][::-1] if len(sims) > 0 else []
        
        # Armazenar TOP_N categorias e scores
        for i, cat_idx in enumerate(top_indices):
            if i < TOP_N:  # Garantir que só usamos TOP_N categorias
                _, nom = cat_meta[cat_idx]
                result_df.iloc[idx, result_df.columns.get_loc(f"TOP_{i+1}")] = nom
                result_df.iloc[idx, result_df.columns.get_loc(f"SCORE_{i+1}")] = float(sims[cat_idx])
        
        # Atualizar progresso a cada 100 itens para não sobrecarregar
        if idx % 100 == 0 or idx == len(item_embeds) - 1:
            progress.update(sim_task, advance=min(100, len(item_embeds) - idx))
    
    # Corrigir nomes de colunas se necessário
    if "id" in result_df.columns and "id_pncp" not in result_df.columns:
        result_df = result_df.rename(columns={"id": "id_pncp"})
    
    # Preparar colunas finais
    desired_columns = ['id_pncp', 'objetoCompra', 'itens']
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"TOP_{i}")
    for i in range(1, TOP_N + 1):
        desired_columns.append(f"SCORE_{i}")
    
    # Filtrar apenas as colunas existentes
    final_columns = [col for col in desired_columns if col in result_df.columns]
    
    return result_df[final_columns]


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
    """Função principal do script."""
    console.print(Panel.fit("[bold yellow]EMB_NV2_v4_3 - Sistema de classificação com embeddings para grandes volumes[/bold yellow]"))
    start_time = time.time()
    
    try:
        # 1. Carregar dados e verificar se existe checkpoint
        df_items, cat, last_processed, batch_files, checkpoint = load_data()
        
        # 2. Preparar textos de catálogo para embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # 3. Verificar se há embeddings de catálogo pré-existentes
        console.print(Panel.fit("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]"))
        
        cat_embeddings = load_embeddings(CAT_EMBED_FILE)
        if cat_embeddings is None or len(cat_embeddings) != len(cat_texts):
            console.print("[yellow]Embeddings de catálogo não encontrados ou desatualizados. Gerando novos...[/yellow]")
            cat_embeddings = get_embeddings(cat_texts)
            save_embeddings(cat_embeddings, CAT_EMBED_FILE)
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # 4. Dividir todos os itens em lotes para processamento
        batches = []
        for i in range(0, len(df_items), BATCH_SIZE):
            batch_df = df_items.iloc[i:i+BATCH_SIZE].copy()
            batch_df = batch_df.reset_index(drop=True)
            batches.append(batch_df)
        
        # Pular lotes já processados
        batches_to_process = batches[len(batch_files):]
        total_batches = len(batches_to_process)
        total_items = sum(len(batch) for batch in batches_to_process)
        
        if total_batches == 0:
            console.print("[bold green]Todos os lotes já foram processados.[/bold green]")
            if batch_files:
                merge_batch_files(batch_files, OUTPUT_FILE)
            return
        
        console.print(f"[bold cyan]Processando {total_batches} lotes com total de {total_items} itens[/bold cyan]")
        
        # 5. Inicializar contadores e listas
        processed_items = 0
        batch_number = len(batch_files) + 1  # Começar do próximo número após os já processados
        current_batch_files = batch_files.copy()
        
        # 6. Processar lotes com progresso único e múltiplas tarefas
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            # Criar tarefas para cada etapa do processamento
            batch_task = progress.add_task("[cyan]Lotes", total=total_batches)
            text_task = progress.add_task("[yellow]Extração de textos", total=total_items, visible=True)
            embed_task = progress.add_task("[green]Embeddings", total=total_batches, visible=True)
            sim_task = progress.add_task("[magenta]Similaridades", total=total_items, visible=True)
            
            # 7. Processar cada lote sequencialmente para evitar conflitos
            for batch_idx, batch_df in enumerate(batches_to_process):
                try:
                    # Atualizar descrição da tarefa do lote
                    progress.update(batch_task, 
                                    description=f"[cyan]Lote {batch_number}/{batch_number+total_batches-1}")
                    
                    # Processar o lote atual
                    console.print(f"[bold blue]Processando lote {batch_number}...[/bold blue]")
                    result_df = process_item_batch(
                        batch_df, 
                        cat_embeddings, 
                        cat_meta, 
                        batch_number,
                        progress,
                        text_task,
                        embed_task,
                        sim_task
                    )
                    
                    # Atualizar contadores
                    start_idx = last_processed + 1
                    last_processed += len(batch_df)
                    processed_items += len(batch_df)
                    
                    # Salvar resultados deste lote
                    batch_file = save_batch_results(
                        result_df, 
                        batch_number, 
                        start_idx, 
                        last_processed
                    )
                    
                    # Adicionar à lista de arquivos de lote
                    current_batch_files.append(batch_file)
                    
                    # Atualizar checkpoints periodicamente
                    if batch_number % SAVE_EVERY_N_BATCHES == 0:
                        save_checkpoint(last_processed, OUTPUT_FILE, current_batch_files)
                    
                    # Atualizar contadores e progresso
                    batch_number += 1
                    progress.update(batch_task, advance=1)
                    
                except Exception as e:
                    console.print(f"[bold red]Erro no lote {batch_idx}: {str(e)}[/bold red]")
                    import traceback
                    console.print(traceback.format_exc())
        
        # 8. Quando todos os lotes estiverem processados, mesclar em um arquivo final
        if current_batch_files:
            # Salvar checkpoint final
            save_checkpoint(last_processed, OUTPUT_FILE, current_batch_files)
            
            # Mesclar todos os arquivos de lote
            merge_batch_files(current_batch_files, OUTPUT_FILE)
        
        # 9. Exibir estatísticas de tempo
        end_time = time.time()
        total_time = end_time - start_time
        total_minutes = total_time / 60
        
        console.print(Panel.fit(f"[bold green]Processamento concluído![/bold green]"))
        console.print(f"[bold cyan]Tempo total: {total_minutes:.2f} minutos ({total_time:.2f} segundos)[/bold cyan]")
        
        if processed_items > 0:
            console.print(f"[bold cyan]Média por item: {total_time/processed_items:.4f} segundos[/bold cyan]")
        
        console.print(f"[bold cyan]Itens processados: {processed_items}[/bold cyan]")
                
    except Exception as e:
        console.print(Panel.fit(f"[bold red]Erro durante processamento: {str(e)}[/bold red]"))
        import traceback
        console.print(traceback.format_exc())


# Executar o código principal
if __name__ == "__main__":
    main()