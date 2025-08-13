import pandas as pd
import numpy as np
import os
import re
import unidecode
from datetime import datetime
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import time
import threading

# Importação para OpenAI API
from openai import OpenAI

# Adicionando Rich para melhorar a visualização
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Inicializar o console Rich
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Modelo de embedding
EMBEDDING_MODEL = "text-embedding-3-large"

# Altere os caminhos conforme necessário
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

# Definindo os caminhos para os arquivos de entrada e saída
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\"
CAT_PATH = os.path.join(BASE_PATH, "PNCP\\CAT\\NOVA\\")
CNAE_PATH = os.path.join(BASE_PATH, "CNAE\\")
CAT_FILE = CAT_PATH + 'NOVA CAT.xlsx'
CNAE_FILE = CNAE_PATH + 'CNAE_NV_2.3.xlsx'

# Combinações a processar
CAT_SHEETS = ["CAT_NV3", "CAT_NV4"]
CNAE_SHEETS = ["CNAE_NV1", "CNAE_NV2", "CNAE_NV3", "CNAE_NV4", "CNAE_NV5"]

OUTPUT_PATH = os.path.join(CNAE_PATH, "OUTPUT\\")
EMBEDDINGS_PATH = os.path.join(CNAE_PATH, "EMBEDDINGS\\")

# Criar diretórios se não existirem
os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(EMBEDDINGS_PATH, exist_ok=True)

# Criar lock para acessos concorrentes
embedding_lock = threading.Lock()

# Baixe os recursos do NLTK se necessário
console.print(Panel.fit("[bold blue]Inicializando recursos NLTK...[/bold blue]"))
nltk.download('stopwords')
nltk.download('wordnet')

##########################################
# Funções para salvar/carregar embeddings
##########################################
def save_embeddings(embeddings, sheet_name):
    """Salva embeddings em arquivo pickle com nome baseado na sheet."""
    with embedding_lock:
        try:
            filepath = os.path.join(EMBEDDINGS_PATH, f'{sheet_name}_OPENAI_{EMBEDDING_MODEL.replace("-", "_")}.pkl')
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings de {sheet_name} salvos com sucesso[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings de {sheet_name}: {str(e)}[/bold red]")
            return False

def load_embeddings(sheet_name):
    """Carrega embeddings de arquivo pickle se existir."""
    filepath = os.path.join(EMBEDDINGS_PATH, f'{sheet_name}_OPENAI_{EMBEDDING_MODEL.replace("-", "_")}.pkl')
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings de {sheet_name} carregados com sucesso[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings de {sheet_name}: {str(e)}[/bold red]")
    return None

##########################################
# Funções para embeddings OpenAI
##########################################
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
                console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

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

##########################################
# Função de pré-processamento de texto
##########################################
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

##########################################
# Funções para processar uma combinação
##########################################
def load_data(cat_sheet, cnae_sheet):
    """Carrega os dados dos arquivos Excel."""
    console.print(f"[bold cyan]Carregando CAT ({cat_sheet}) e CNAE ({cnae_sheet})...[/bold cyan]")
    
    try:
        cat_df = pd.read_excel(CAT_FILE, sheet_name=cat_sheet)
        cnae_df = pd.read_excel(CNAE_FILE, sheet_name=cnae_sheet)
        console.print(f"✓ CAT carregado: {cat_df.shape[0]} registros", style="green")
        console.print(f"✓ CNAE carregado: {cnae_df.shape[0]} registros", style="green")
        return cat_df, cnae_df
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar planilhas: {str(e)}[/bold red]")
        raise

def preprocess_dataframes(cat_df, cnae_df):
    """Aplica pré-processamento aos DataFrames."""
    console.print("Pré-processando textos...", style="cyan")
    
    # Copiar os dataframes para não modificar os originais
    cat_df = cat_df.copy()
    cnae_df = cnae_df.copy()
    
    cat_df['descricao_proc'] = cat_df['NOMCAT'].astype(str).apply(preprocess_text)
    cnae_df['divisao_proc'] = cnae_df['NOME'].astype(str).apply(preprocess_text)
    
    console.print("✓ Pré-processamento concluído", style="green")
    return cat_df, cnae_df

def generate_or_load_embeddings(df, sheet_name, field_name):
    """Gera ou carrega embeddings para um DataFrame específico."""
    # Tentar carregar embeddings existentes
    embeddings = load_embeddings(sheet_name)
    
    if embeddings is None or len(embeddings) != len(df):
        console.print(f"[yellow]Gerando embeddings para {sheet_name}...[/yellow]")
        texts = df[field_name].tolist()
        embeddings = get_embeddings(texts, show_progress=True)
        save_embeddings(embeddings, sheet_name)
    
    # Adicionar embeddings ao DataFrame
    df['embedding'] = list(embeddings)
    return df

def get_top10_cnaes(cat_embedding, cnae_embeddings):
    """Calcula a similaridade e retorna os top 10 CNAEs mais similares."""
    # Calcular similaridade via cosseno
    sims = cosine_similarity([cat_embedding], cnae_embeddings)[0]
    # Ordenar e pegar os índices dos top 10 com maiores scores
    top10_idx = np.argsort(sims)[::-1][:10]
    top10_scores = sims[top10_idx]
    return top10_idx, top10_scores

def process_combination(cat_sheet, cnae_sheet):
    """Processa uma combinação específica de CAT e CNAE."""
    console.print(Panel.fit(f"[bold green]Processando combinação: {cat_sheet} × {cnae_sheet}[/bold green]"))
    
    # 1. Carregar os dados
    cat_df, cnae_df = load_data(cat_sheet, cnae_sheet)
    
    # 2. Pré-processar os dados
    cat_df, cnae_df = preprocess_dataframes(cat_df, cnae_df)
    
    # 3. Gerar ou carregar embeddings
    cat_df = generate_or_load_embeddings(cat_df, cat_sheet, 'descricao_proc')
    cnae_df = generate_or_load_embeddings(cnae_df, cnae_sheet, 'divisao_proc')
    
    # 4. Converter embeddings de CNAE para matriz
    cnae_embeddings_matrix = np.vstack(cnae_df['embedding'].to_list())
    
    # 5. Calcular similaridades e mapear top 10
    console.print(Panel.fit("[bold green]Calculando similaridades e gerando mapeamento TOP 10...[/bold green]"))
    
    result_data = []
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn()
    ) as progress:
        sim_task = progress.add_task("[cyan]Calculando similaridades...", total=cat_df.shape[0])
        
        for index, row in cat_df.iterrows():
            cat_id = row['CODCAT']
            cat_desc = row['NOMCAT']
            cat_embed = row['embedding']
            
            # Obter os top 10 CNAEs mais similares
            top10_idx, top10_scores = get_top10_cnaes(cat_embed, cnae_embeddings_matrix)
            
            # Criar um registro para esta CAT
            cat_record = {
                'cat_id': cat_id,
                'cat_descricao': cat_desc
            }
            
            # Primeiro adicionar todos os TOPs no formato "CODIGO - NOME"
            for i, idx in enumerate(top10_idx, 1):
                cnae_id = cnae_df.iloc[idx]['CODIGO'] if 'CODIGO' in cnae_df.columns else idx
                cnae_desc = cnae_df.iloc[idx]['NOME']
                
                # Combinar código e nome no formato solicitado
                cat_record[f'top_{i}'] = f"{cnae_id} - {cnae_desc}"
            
            # Depois adicionar todos os SCOREs
            for i, score in enumerate(top10_scores, 1):
                cat_record[f'score_{i}'] = score
            
            # Adicionar à lista de resultados
            result_data.append(cat_record)
            
            # Atualizar a barra de progresso
            progress.update(sim_task, advance=1)
    
    # 6. Converter resultados para DataFrame
    console.print("Processando resultados...", style="cyan")
    results_df = pd.DataFrame(result_data)
    
    # 7. Salvar resultados
    output_file = os.path.join(OUTPUT_PATH, f'{cat_sheet}_{cnae_sheet}_OPENAI_{TIMESTAMP}.xlsx')
    console.print(f"Salvando resultados em: {output_file}", style="yellow")
    results_df.to_excel(output_file, sheet_name='Mapeamento_TOP10', index=False)
    console.print(f"✓ Arquivo salvo com sucesso!", style="green")
    
    return output_file

##########################################
# Função principal
##########################################
def main():
    console.print(Panel.fit("[bold yellow]CAT-CNAE Mapeamento v3 - Múltiplas Combinações[/bold yellow]"))
    
    # Verificar arquivos de entrada
    console.print(f"Verificando arquivos de entrada:", style="yellow")
    console.print(f"  CAT: {os.path.exists(CAT_FILE)}", style="green" if os.path.exists(CAT_FILE) else "red")
    console.print(f"  CNAE: {os.path.exists(CNAE_FILE)}", style="green" if os.path.exists(CNAE_FILE) else "red")
    
    if not os.path.exists(CAT_FILE) or not os.path.exists(CNAE_FILE):
        console.print("[bold red]Arquivos de entrada não encontrados. Encerrando.[/bold red]")
        return
    
    # Criar tabela para mostrar combinações que serão processadas
    table = Table(title="Combinações a Processar")
    table.add_column("CAT", style="cyan")
    table.add_column("CNAE", style="green")
    table.add_column("Status", style="yellow")
    
    for cat_sheet in CAT_SHEETS:
        for cnae_sheet in CNAE_SHEETS:
            table.add_row(cat_sheet, cnae_sheet, "Pendente")
    
    console.print(table)
    
    # Processar todas as combinações
    processed_files = []
    
    start_time = time.time()
    
    for cat_sheet in CAT_SHEETS:
        for cnae_sheet in CNAE_SHEETS:
            try:
                output_file = process_combination(cat_sheet, cnae_sheet)
                processed_files.append((cat_sheet, cnae_sheet, output_file))
            except Exception as e:
                console.print(f"[bold red]Erro ao processar {cat_sheet} × {cnae_sheet}: {str(e)}[/bold red]")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Mostrar resumo
    console.print(Panel.fit("[bold green]Processamento concluído![/bold green]"))
    
    summary_table = Table(title="Resumo de Processamento")
    summary_table.add_column("CAT", style="cyan")
    summary_table.add_column("CNAE", style="green")
    summary_table.add_column("Arquivo de Saída", style="yellow")
    
    for cat_sheet, cnae_sheet, output_file in processed_files:
        summary_table.add_row(cat_sheet, cnae_sheet, os.path.basename(output_file))
    
    console.print(summary_table)
    console.print(f"[bold cyan]Tempo total de processamento: {total_time/60:.2f} minutos[/bold cyan]")

if __name__ == "__main__":
    main()