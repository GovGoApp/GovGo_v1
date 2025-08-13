#### GvG Embeddings Generator (GvG_EG) v1 ####
import os
import pandas as pd
import numpy as np
import pickle
import faiss
from openai import OpenAI
from datetime import datetime
import math
import re
import unidecode
import nltk
import traceback
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn
import shutil  # Adicionar esta importação para mover arquivos

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
NEW_PATH = BASE_PATH + "INPUT\\NEW\\"
OLD_PATH = BASE_PATH + "INPUT\\OLD\\"
GvG_FILE = BASE_PATH + "GvG_Contratações.xlsx"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\"
os.makedirs(EMBEDDINGS_PATH, exist_ok=True)

# Modelos de embedding disponíveis e suas dimensões
embedding_models = [
    {"modelo": "text-embedding-3-large", "dimensoes": 3072},
    {"modelo": "text-embedding-3-small", "dimensoes": 1536},
    {"modelo": "text-embedding-ada-002", "dimensoes": 1536}
]

# Modelo selecionado (configuração inicial)
EMBEDDING_MODEL = "text-embedding-3-large"

# Obter dimensão do modelo selecionado
def get_embedding_dimension(model_name):
    for model in embedding_models:
        if model["modelo"] == model_name:
            return model["dimensoes"]

# Dimensão do modelo de embedding selecionado
EMBEDDING_DIM = get_embedding_dimension(EMBEDDING_MODEL)

# Atualizar nome do arquivo de embeddings com o modelo selecionado
GvG_EMBEDDINGS_FILE = EMBEDDINGS_PATH + f"GvG_embeddings_{EMBEDDING_MODEL}.pkl"

# Constantes para processamento paralelo
MAX_WORKERS = 20
BATCH_SIZE = 200


# Inicializar NLTK
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Console para exibição formatada
console = Console()

# Cliente OpenAI
client = OpenAI(api_key="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")

# Lock para acessos concorrentes
embedding_lock = threading.Lock()

def selecionar_modelo():
    """Permite ao usuário selecionar o modelo de embedding a ser usado."""
    console.print("[bold magenta]SELEÇÃO DE MODELO DE EMBEDDING[/bold magenta]")
    console.print("\nModelos disponíveis:")
    
    for i, model in enumerate(embedding_models, 1):
        console.print(f"{i}. {model['modelo']} ({model['dimensoes']} dimensões)")
    
    default_index = next((i for i, m in enumerate(embedding_models) if m["modelo"] == EMBEDDING_MODEL), 0)
    choice = input(f"\nEscolha o modelo (1-{len(embedding_models)}) [padrão: {default_index+1}]: ")
    
    try:
        if choice.strip():
            idx = int(choice) - 1
            if 0 <= idx < len(embedding_models):
                return embedding_models[idx]["modelo"]
        # Se a escolha for inválida ou vazia, usar o modelo padrão
        return EMBEDDING_MODEL
    except ValueError:
        console.print("[yellow]Escolha inválida, usando o modelo padrão.[/yellow]")
        return EMBEDDING_MODEL

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

def get_embedding(text, model=EMBEDDING_MODEL):
    """Gera embedding para um único texto."""
    try:
        # Garantir que o texto não está vazio
        if not text or not text.strip():
            text = " "
        
        # Limitar tamanho se necessário
        if len(text) > 8000:
            text = text[:8000]
            
        response = client.embeddings.create(
            model=model,
            input=[text]
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embedding: {str(e)}[/bold red]")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)  # Retornar vetor zero com dimensão correta

def save_embeddings(embeddings_dict, filepath):
    """Salva dicionário de embeddings em arquivo pickle."""
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(embeddings_dict, f)
        console.print(f"[green]Embeddings salvos em {filepath} ({len(embeddings_dict)} registros)[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
        return False

def load_embeddings(filepath):
    """Carrega dicionário de embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings_dict = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath} ({len(embeddings_dict)} registros)[/green]")
            return embeddings_dict
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return {}

def partition_list(lst, n):
    """Divide uma lista em n partições aproximadamente iguais."""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i, m)] for i in range(n)]

def process_batch(batch, model):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro e validação de entrada."""
    max_retries = 5
    retry_delay = 5
    
    # Validar batch antes de enviar para API
    validated_batch = []
    for text in batch:
        # Garantir que é string e não está vazio
        if text is None:
            text = ""
        
        # Converter para string se não for
        if not isinstance(text, str):
            text = str(text)
            
        # Verificar se a string não está vazia após processamento
        if not text.strip():
            text = " "  # Espaço em branco para evitar erro de string vazia
            
        # Limitar tamanho se necessário (OpenAI tem limite de tokens)
        if len(text) > 8000:
            text = text[:8000]
            
        validated_batch.append(text)
    
    # Verificação final: batch não pode estar vazio
    if not validated_batch:
        validated_batch = [" "]
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=validated_batch
            )
            
            # Garantir que cada embedding tenha a dimensão correta
            results = []
            for item in response.data:
                emb = np.array(item.embedding, dtype=np.float32)
                # Verificar dimensão do embedding recebido
                if emb.shape != (EMBEDDING_DIM,):
                    console.print(f"[yellow]Aviso: Embedding recebido com formato {emb.shape} em vez de ({EMBEDDING_DIM},). Ajustando...[/yellow]")
                    if len(emb) > EMBEDDING_DIM:
                        # Truncar se maior
                        emb = emb[:EMBEDDING_DIM]
                    else:
                        # Preencher com zeros se menor
                        padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                        padded[:len(emb)] = emb
                        emb = padded
                results.append(emb)
            return results
            
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
                # Retornar embeddings vazios com a dimensão correta
                return [np.zeros(EMBEDDING_DIM, dtype=np.float32) for _ in range(len(validated_batch))]

def process_embedding_batch(batch_indices, texts, model, progress, task_id):
    """Processa um lote de textos para embeddings utilizando BATCH_SIZE."""
    batch_results = []
    
    # Agrupar índices em lotes do tamanho BATCH_SIZE
    for i in range(0, len(batch_indices), BATCH_SIZE):
        # Pegar os índices do lote atual
        current_batch_indices = batch_indices[i:i+BATCH_SIZE]
        
        # Obter os textos correspondentes aos índices
        current_batch_texts = [texts[idx] for idx in current_batch_indices]
        
        # Processar o lote de textos
        try:
            batch_embeddings = process_batch(current_batch_texts, model)
            
            # Associar cada embedding ao seu índice original
            for j, embedding in enumerate(batch_embeddings):
                original_idx = current_batch_indices[j]
                # Verificar se o embedding tem a forma correta
                if embedding is None or not isinstance(embedding, np.ndarray) or embedding.shape != (EMBEDDING_DIM,):
                    embedding = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                batch_results.append((original_idx, embedding))
                
            # Atualizar a barra de progresso uma vez por lote
            progress.update(task_id, advance=len(current_batch_indices))
            
        except Exception as e:
            console.print(f"[bold red]Erro processando lote {i//BATCH_SIZE + 1}: {str(e)}[/bold red]")
            # Criar embeddings vazios para índices com falha
            for idx in current_batch_indices:
                batch_results.append((idx, np.zeros(EMBEDDING_DIM, dtype=np.float32)))
            progress.update(task_id, advance=len(current_batch_indices))
    
    return batch_results

def get_embeddings_batch(texts, ids, model=EMBEDDING_MODEL, existing_progress=None, save_to_file=False):
    """Gera embeddings para uma lista de textos em lotes usando processamento paralelo.
    
    Args:
        texts (list): Lista de textos para processar
        ids (list): Lista de numeroControlePNCP correspondentes aos textos
        model (str): Modelo de embedding a usar
        existing_progress: Objeto de progresso existente (opcional)
        save_to_file (bool): Se deve salvar no arquivo
        
    Returns:
        dict: Dicionário com {numeroControlePNCP: embedding}
    """
    # Carregar embeddings existentes se disponíveis
    embeddings_dict = {}
    if os.path.exists(GvG_EMBEDDINGS_FILE):
        console.print("[cyan]Embeddings em cache encontrados. Tentando carregar...[/cyan]")
        cached_embeddings = load_embeddings(GvG_EMBEDDINGS_FILE)
        if cached_embeddings and isinstance(cached_embeddings, dict):
            embeddings_dict = cached_embeddings
            console.print(f"[green]Carregados {len(embeddings_dict)} embeddings existentes.[/green]")
            
            # Verificar quais IDs já possuem embeddings
            existing_ids = set(embeddings_dict.keys())
            ids_to_process = []
            texts_to_process = []
            
            for i, id_value in enumerate(ids):
                if id_value not in existing_ids:
                    ids_to_process.append(id_value)
                    texts_to_process.append(texts[i])
            
            if not ids_to_process:
                console.print("[green]Todos os embeddings já existem em cache. Nada para processar.[/green]")
                return embeddings_dict
            
            console.print(f"[yellow]Processando {len(ids_to_process)} novos embeddings...[/yellow]")
            texts = texts_to_process
            ids = ids_to_process
        else:
            console.print("[yellow]Cache de embeddings incompatível. Regenerando todos...[/yellow]")
    
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
        # Preparar embeddings para processamento paralelo
        result_embeddings = [None] * len(texts)
        all_indices = list(range(len(texts)))
        partitions = partition_list(all_indices, MAX_WORKERS)
        
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
                    task_id
                ))
            
            # Processar resultados
            for future in futures:
                for idx, embedding in future.result():
                    if embedding is not None:
                        result_embeddings[idx] = embedding
                    else:
                        # Usar embedding vazio para manter correspondência com os índices
                        result_embeddings[idx] = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    
    finally:
        if not use_external_progress:
            progress.stop()
    
    # Verificar consistência dos embeddings
    valid_count = 0
    invalid_count = 0
    
    # Criar mapeamento de ID para embedding
    new_embeddings_dict = {}
    for i, emb in enumerate(result_embeddings):
        if emb is None or not isinstance(emb, np.ndarray) or emb.shape != (EMBEDDING_DIM,):
            invalid_count += 1
            emb = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        else:
            valid_count += 1
        
        # Adicionar ao dicionário usando o ID como chave
        new_embeddings_dict[ids[i]] = emb
    
    if invalid_count > 0:
        console.print(f"[yellow]Encontrados {invalid_count} embeddings inválidos que foram corrigidos.[/yellow]")
    
    console.print(f"[green]Embeddings válidos: {valid_count}/{len(result_embeddings)} ({valid_count/len(result_embeddings)*100:.2f}%)[/green]")
    
    # Mesclar com os embeddings existentes
    embeddings_dict.update(new_embeddings_dict)
    
    # Salvar o dicionário completo
    if save_to_file:
        save_embeddings(embeddings_dict, GvG_EMBEDDINGS_FILE)
    
    return embeddings_dict

def criar_indice_faiss(embeddings):
    """Cria um índice FAISS para busca por similaridade."""
    console.print("[bold magenta]Criando índice FAISS...[/bold magenta]")
    
    # Verificar e corrigir embeddings antes de criar o array
    valid_embeddings = []
    invalid_count = 0
    
    for i, emb in enumerate(embeddings):
        if emb is None or not isinstance(emb, np.ndarray) or emb.shape != (EMBEDDING_DIM,):
            valid_embeddings.append(np.zeros(EMBEDDING_DIM, dtype=np.float32))
            invalid_count += 1
            if invalid_count <= 10:  # Limitar mensagens para não sobrecarregar o console
                console.print(f"[yellow]Embedding inválido no índice {i}. Substituindo por vetor zero.[/yellow]")
            elif invalid_count == 11:
                console.print("[yellow]Ocultando mensagens adicionais de embeddings inválidos...[/yellow]")
        else:
            valid_embeddings.append(emb)
    
    if invalid_count > 0:
        console.print(f"[bold yellow]Total de {invalid_count} embeddings inválidos substituídos por zeros.[/bold yellow]")
    
    # Criar array NumPy a partir dos embeddings validados
    # Usar np.stack em vez de np.array para garantir consistência dimensional
    embeddings_array = np.stack(valid_embeddings).astype(np.float32)
    
    # Verificar forma final do array
    console.print(f"[cyan]Array de embeddings: {embeddings_array.shape}[/cyan]")
    
    # Criar índice de produto interno (similaridade de cosseno)
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    # Normalizar vetores para garantir similaridade de cosseno
    faiss.normalize_L2(embeddings_array)
    
    # Adicionar vetores ao índice
    index.add(embeddings_array)
    console.print(f"[green]Índice FAISS criado com {index.ntotal} vetores.[/green]")
    return index

def salvar_dados(df, embeddings, index, timestamp):
    """Salva a base de dados, embeddings e índice FAISS."""
    try:
        # Criar nome de arquivo com timestamp
        filename_base = f"contratacoes_{timestamp}"
        
        # Salvar DataFrame
        df_path = f"{BASE_PATH}{filename_base}.xlsx"
        df.to_excel(df_path, index=False)
        console.print(f"[green]DataFrame salvo em {df_path}[/green]")
        
        # Salvar embeddings
        embedding_file = f"{EMBEDDINGS_PATH}{filename_base}_embeddings.pkl"
        with open(embedding_file, 'wb') as f:
            pickle.dump(embeddings, f)
        console.print(f"[green]Embeddings salvos em {embedding_file}[/green]")
        
        # Salvar índice FAISS
        index_file = f"{EMBEDDINGS_PATH}{filename_base}_faiss.index"
        faiss.write_index(index, index_file)
        console.print(f"[green]Índice FAISS salvo em {index_file}[/green]")
        
        # Salvar metadados
        metadata = {
            'df_path': df_path,
            'embeddings_path': embedding_file,
            'index_path': index_file,
            'timestamp': timestamp,
            'num_records': len(df),
            'embedding_model': EMBEDDING_MODEL
        }
        
        metadata_path = f"{EMBEDDINGS_PATH}{filename_base}_metadata.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        console.print(f"[green]Metadados salvos em {metadata_path}[/green]")
        
        return metadata_path
        
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar dados: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return None

def carregar_base(metadata_path):
    """Carrega a base de dados a partir do arquivo de metadados."""
    try:
        # Carregar metadados
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        console.print(f"[bold magenta]Carregando base de {metadata['timestamp']}...[/bold magenta]")
        
        # Carregar DataFrame
        df = pd.read_excel(metadata['df_path'])
        console.print(f"[green]DataFrame carregado com {len(df)} registros.[/green]")
        
        # Carregar embeddings
        embeddings = None
        if metadata['embeddings_path'] and os.path.exists(metadata['embeddings_path']):
            with open(metadata['embeddings_path'], 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados: {len(embeddings)}[/green]")
        
        # Carregar índice FAISS
        index = None
        if metadata['index_path'] and os.path.exists(metadata['index_path']):
            index = faiss.read_index(metadata['index_path'])
            console.print(f"[green]Índice FAISS carregado com {index.ntotal} vetores.[/green]")
        
        return df, embeddings, index, metadata['timestamp']
        
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar base: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return None, None, None, None

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações."""
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

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

def processar_pipeline_completo():
    """Executa o pipeline completo de processamento."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # Carregar dados
        df = carregar_dados(GvG_FILE)
        if df is None:
            return None
        
        # Verificar se o arquivo tem a coluna necessária
        if 'numeroControlePNCP' not in df.columns:
            console.print("[bold red]Erro: O arquivo não possui a coluna 'numeroControlePNCP'[/bold red]")
            return None
            
        # Processar descrições
        df = processar_descricoes(df)
        
        # Gerar embeddings
        console.print("[bold magenta]Gerando embeddings para as descrições...[/bold magenta]")
        textos = df['descricao_processada'].tolist()
        ids = df['numeroControlePNCP'].tolist()
        
        embeddings_dict = get_embeddings_batch(textos, ids, model=EMBEDDING_MODEL, save_to_file=True)
        console.print(f"[green]Embeddings gerados e salvos: {len(embeddings_dict)}[/green]")
        
        # Log de processamento
        log_file = EMBEDDINGS_PATH + "embedding_log.txt"
        with open(log_file, 'a') as f:
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Arquivo: {GvG_FILE}\n")
            f.write(f"Modelo: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dimensões)\n")
            f.write(f"Registros processados: {len(df)}\n")
            f.write(f"Total de embeddings: {len(embeddings_dict)}\n")
            f.write(f"Arquivo de embeddings: {GvG_EMBEDDINGS_FILE}\n")
            f.write("-" * 50 + "\n\n")
        
        console.print(f"[bold green]Log salvo em {log_file}[/bold green]")
        console.print("[bold green]Processamento concluído com sucesso![/bold green]")
        
        return df, embeddings_dict, None, GvG_EMBEDDINGS_FILE
                
    except Exception as e:
        console.print(f"[bold red]Erro no pipeline de processamento: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return None

def main_embedding_only():
    """Função principal simplificada apenas para processamento de embeddings."""
    console.print("[bold magenta]SISTEMA DE GERAÇÃO DE EMBEDDINGS PARA CONTRATAÇÕES[/bold magenta]")
    console.print("[bold cyan]Baseado em OpenAI Embeddings[/bold cyan]\n")
    
    # Garantir que o diretório de embeddings existe
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    # Selecionar modelo de embedding
    global EMBEDDING_MODEL, EMBEDDING_DIM, GvG_EMBEDDINGS_FILE
    selected_model = selecionar_modelo()
    
    if selected_model != EMBEDDING_MODEL:
        EMBEDDING_MODEL = selected_model
        EMBEDDING_DIM = get_embedding_dimension(EMBEDDING_MODEL)
        GvG_EMBEDDINGS_FILE = EMBEDDINGS_PATH + f"GvG_embeddings_{EMBEDDING_MODEL}.pkl"
    
    console.print(f"[bold cyan]Modelo selecionado: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dimensões)[/bold cyan]\n")
    
    # Iniciar processamento
    inicio = time.time()
    result = processar_pipeline_completo()
    fim = time.time()
    
    if result:
        tempo_total = fim - inicio
        df, embeddings, _, _ = result
        console.print(f"[bold green]Processamento completo em {tempo_total:.2f} segundos[/bold green]")
        console.print(f"[bold green]Média por item: {tempo_total/len(df):.4f} segundos[/bold green]")
    else:
        console.print("[bold red]Processamento falhou.[/bold red]")

if __name__ == "__main__":
    main_embedding_only()

def processar_diretorio_new():
    """Processa todos os arquivos Excel no diretório NEW_PATH e move para OLD_PATH após processamento."""
    console.print("[bold magenta]PROCESSAMENTO DE ARQUIVOS[/bold magenta]")
    
    # Verificar se os diretórios existem
    os.makedirs(NEW_PATH, exist_ok=True)
    os.makedirs(OLD_PATH, exist_ok=True)
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    
    # Buscar todos os arquivos Excel no diretório NEW_PATH
    excel_files = [f for f in os.listdir(NEW_PATH) if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        console.print("[yellow]Nenhum arquivo Excel encontrado em {}[/yellow]".format(NEW_PATH))
        return
    
    console.print(f"[green]Encontrados {len(excel_files)} arquivos para processamento.[/green]")
    
    # Estatísticas globais
    total_novos = 0
    total_atualizados = 0
    total_processados = 0
    
    inicio_total = time.time()
    
    # Processar cada arquivo
    for i, excel_file in enumerate(excel_files, 1):
        excel_path = os.path.join(NEW_PATH, excel_file)
        console.print(f"[bold blue][{i}/{len(excel_files)}] Processando: {excel_file}[/bold blue]")
        
        # Processar o arquivo
        novos, atualizados, total = processar_arquivo(excel_path)
        
        # Atualizar estatísticas
        total_novos += novos
        total_atualizados += atualizados
        total_processados += 1
        
        # Mover arquivo para OLD_PATH
        if novos > 0 or atualizados > 0:
            # Criar nome de destino com timestamp para evitar colisões
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Preservar a extensão original
            nome, extensao = os.path.splitext(excel_file)
            destino = os.path.join(OLD_PATH, f"{nome}_{timestamp}{extensao}")
            
            try:
                shutil.move(excel_path, destino)
                console.print(f"[green]Arquivo movido para: {destino}[/green]")
            except Exception as e:
                console.print(f"[bold red]Erro ao mover arquivo: {str(e)}[/bold red]")
                # Se não conseguir mover, renomear in-place para indicar processamento
                novo_nome = os.path.join(NEW_PATH, f"{nome}_processado_{timestamp}{extensao}")
                try:
                    os.rename(excel_path, novo_nome)
                    console.print(f"[yellow]Arquivo renomeado para: {novo_nome}[/yellow]")
                except Exception as e2:
                    console.print(f"[bold red]Também não foi possível renomear o arquivo: {str(e2)}[/bold red]")
        else:
            console.print(f"[yellow]Nenhum registro adicionado ou atualizado para o arquivo {excel_file}.[/yellow]")
            # Mesmo sem processamentos, movemos o arquivo para evitar reprocessamento
            destino = os.path.join(OLD_PATH, excel_file)
            try:
                shutil.move(excel_path, destino)
                console.print(f"[yellow]Arquivo movido para: {destino} (sem alterações)[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Erro ao mover arquivo: {str(e)}[/bold red]")
    
    # Calcular tempo total
    fim_total = time.time()
    tempo_total = fim_total - inicio_total
    
    # Relatório final
    console.print("\n[bold green]" + "="*50 + "[/bold green]")
    console.print("[bold green]RELATÓRIO DE PROCESSAMENTO[/bold green]")
    console.print(f"[green]Arquivos processados: {total_processados}[/green]")
    console.print(f"[green]Novos registros: {total_novos}[/green]")
    console.print(f"[green]Registros atualizados: {total_atualizados}[/green]")
    console.print(f"[green]Tempo total: {tempo_total:.2f} segundos[/green]")
    console.print("[bold green]" + "="*50 + "[/bold green]")

def processar_arquivo(excel_path):
    """Processa um arquivo Excel e atualiza a base de embeddings."""
    console.print(f"[bold magenta]Processando arquivo: {os.path.basename(excel_path)}[/bold magenta]")
    
    # Carregar dados do arquivo
    df = carregar_dados(excel_path)
    if df is None:
        return 0, 0, 0
    
    # Verificar se o arquivo tem a coluna necessária
    if 'numeroControlePNCP' not in df.columns:
        console.print("[bold red]Erro: O arquivo não possui a coluna 'numeroControlePNCP'[/bold red]")
        return 0, 0, 0
    
    # Processar descrições
    df = processar_descricoes(df)
    
    # Carregar embeddings existentes
    embeddings_dict = load_embeddings(GvG_EMBEDDINGS_FILE) if os.path.exists(GvG_EMBEDDINGS_FILE) else {}
    existing_ids = set(embeddings_dict.keys())
    
    # Identificar registros novos e existentes
    df['is_new'] = ~df['numeroControlePNCP'].isin(existing_ids)
    new_records = df[df['is_new']].copy()
    existing_records = df[~df['is_new']].copy()
    
    console.print(f"[cyan]Registros no arquivo: {len(df)}[/cyan]")
    console.print(f"[cyan]Novos registros: {len(new_records)}[/cyan]")
    console.print(f"[cyan]Registros existentes para atualizar: {len(existing_records)}[/cyan]")
    
    # Processar novos registros
    if len(new_records) > 0:
        console.print("[bold magenta]Processando novos registros...[/bold magenta]")
        textos = new_records['descricao_processada'].tolist()
        ids = new_records['numeroControlePNCP'].tolist()
        
        # Gerar embeddings para novos registros
        embeddings_dict = get_embeddings_batch(textos, ids, model=EMBEDDING_MODEL, save_to_file=False)
    
    # Processar registros existentes (atualização)
    if len(existing_records) > 0:
        console.print("[bold magenta]Processando registros existentes...[/bold magenta]")
        textos = existing_records['descricao_processada'].tolist()
        ids = existing_records['numeroControlePNCP'].tolist()
        
        # Gerar embeddings para registros atualizados
        embeddings_dict = get_embeddings_batch(textos, ids, model=EMBEDDING_MODEL, save_to_file=False)
    
    # Salvar resultado final apenas se houve alterações
    if len(new_records) > 0 or len(existing_records) > 0:
        save_embeddings(embeddings_dict, GvG_EMBEDDINGS_FILE)
    
    # Log de processamento
    log_file = EMBEDDINGS_PATH + "embedding_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Arquivo processado: {excel_path}\n")
        f.write(f"Modelo: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dimensões)\n")
        f.write(f"Novos registros: {len(new_records)}\n")
        f.write(f"Registros atualizados: {len(existing_records)}\n")
        f.write(f"Total de embeddings na base: {len(embeddings_dict)}\n")
        f.write("-" * 50 + "\n\n")
    
    console.print(f"[bold green]Processamento concluído para {os.path.basename(excel_path)}.[/bold green]")
    console.print(f"[bold green]Total de embeddings na base: {len(embeddings_dict)}[/bold green]")
    
    return len(new_records), len(existing_records), len(embeddings_dict)

def main():
    """Função principal que processa todos os arquivos em NEW_PATH."""
    console.print("[bold magenta]SISTEMA DE GERAÇÃO DE EMBEDDINGS PARA CONTRATAÇÕES[/bold magenta]")
    console.print("[bold cyan]Baseado em OpenAI Embeddings[/bold cyan]\n")
    
    # Selecionar modelo de embedding
    global EMBEDDING_MODEL, EMBEDDING_DIM, GvG_EMBEDDINGS_FILE
    selected_model = selecionar_modelo()
    
    if selected_model != EMBEDDING_MODEL:
        EMBEDDING_MODEL = selected_model
        EMBEDDING_DIM = get_embedding_dimension(EMBEDDING_MODEL)
        GvG_EMBEDDINGS_FILE = EMBEDDINGS_PATH + f"GvG_embeddings_{EMBEDDING_MODEL}.pkl"
    
    console.print(f"[bold cyan]Modelo selecionado: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dimensões)[/bold cyan]\n")
    
    # Processar todos os arquivos em NEW_PATH
    processar_diretorio_new()

if __name__ == "__main__":
    main()