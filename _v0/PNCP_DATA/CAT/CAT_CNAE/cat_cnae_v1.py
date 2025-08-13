import pandas as pd
import numpy as np
import os
import re
import unidecode
from datetime import datetime
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Adicionando Rich para melhorar a visualização
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

# Inicializar o console Rich
console = Console()

# Baixe os recursos do NLTK se necessário
console.print(Panel.fit("[bold blue]Inicializando recursos NLTK...[/bold blue]"))
nltk.download('stopwords')
nltk.download('wordnet')

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
# Passo 1: Carregar e pré-processar as planilhas
##########################################
console.print(Panel.fit("[bold green]PASSO 1: Carregando e pré-processando arquivos...[/bold green]"))

# Altere os caminhos conforme necessário
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
EMBEDDING_MODEL ='paraphrase-multilingual-mpnet-base-v2'

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\"
CAT_PATH = os.path.join(BASE_PATH, "PNCP\\CAT\\NOVA\\")
CNAE_PATH = os.path.join(BASE_PATH, "CNAE\\")
CAT_FILE = CAT_PATH + 'NOVA CAT.xlsx'
CAT_SHEET = "CAT_NV4"
CNAE_FILE = CNAE_PATH + 'CNAE_v2.xlsx'
CNAE_SHEET = "CNAE_NV4"

OUTPUT_PATH = os.path.join(CNAE_PATH, "OUTPUT\\")
OUTPUT_FILE = os.path.join(OUTPUT_PATH, f'{CAT_SHEET}_{CNAE_SHEET}_ST_{TIMESTAMP}.xlsx')
#CAT3_CNAE2_TOP10 significa CAT NV3 e CNAE NV2 

# Verificar arquivos de entrada
console.print(f"Verificando arquivos de entrada:", style="yellow")
console.print(f"  CAT: {os.path.exists(CAT_FILE)}", style="green" if os.path.exists(CAT_FILE) else "red")
console.print(f"  CNAE: {os.path.exists(CNAE_FILE)}", style="green" if os.path.exists(CNAE_FILE) else "red")

# Garantir que o diretório de saída exista
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Carregar planilhas
try:
    console.print("Carregando planilhas...", style="cyan")
    cat_df = pd.read_excel(CAT_FILE, sheet_name=CAT_SHEET)
    cnae_df = pd.read_excel(CNAE_FILE, sheet_name=CNAE_SHEET)
    console.print(f"✓ CAT carregado: {cat_df.shape[0]} registros", style="green")
    console.print(f"✓ CNAE carregado: {cnae_df.shape[0]} registros", style="green")
except Exception as e:
    console.print(f"[bold red]Erro ao carregar planilhas: {str(e)}[/bold red]")
    raise

# Pré-processamento dos textos - USANDO O MÉTODO ORIGINAL DO V0
console.print("Pré-processando textos...", style="cyan")
cat_df['descricao_proc'] = cat_df['NOMCAT'].astype(str).apply(preprocess_text)
cnae_df['divisao_proc'] = cnae_df['NOME'].astype(str).apply(preprocess_text)
console.print("✓ Pré-processamento concluído", style="green")

##########################################
# Passo 2: Gerar os embeddings com Sentence Transformer
##########################################
console.print(Panel.fit("[bold green]PASSO 2: Gerando embeddings com Sentence Transformer...[/bold green]"))

# Modelo multilingue (bom para português)
console.print("Carregando modelo de linguagem...", style="cyan")
model = SentenceTransformer(EMBEDDING_MODEL)
console.print("✓ Modelo carregado", style="green")

# Utilize encoding em lote para bases grandes
cat_texts = cat_df['descricao_proc'].tolist()
cnae_texts = cnae_df['divisao_proc'].tolist()

console.print("Gerando embeddings para CAT...", style="cyan")
cat_embeddings = model.encode(cat_texts, batch_size=64, show_progress_bar=True)
console.print("Gerando embeddings para CNAE...", style="cyan")
cnae_embeddings = model.encode(cnae_texts, batch_size=64, show_progress_bar=True)

# Armazenar os embeddings nos DataFrames
cat_df['embedding'] = list(cat_embeddings)
cnae_df['embedding'] = list(cnae_embeddings)
console.print("✓ Embeddings gerados com sucesso", style="green")

##########################################
# Passo 3: Calcular similaridade e gerar mapeamento top 10
##########################################
console.print(Panel.fit("[bold green]PASSO 3: Calculando similaridades e gerando mapeamento TOP 10...[/bold green]"))

def get_top10_cnaes(cat_embedding, cnae_embeddings):
    # Calcular similaridade via cosseno
    sims = cosine_similarity([cat_embedding], cnae_embeddings)[0]
    # Ordenar e pegar os índices dos top 10 com maiores scores
    top10_idx = np.argsort(sims)[::-1][:10]
    top10_scores = sims[top10_idx]
    return top10_idx, top10_scores

# Converter a lista de embeddings de CNAE para matriz
cnae_embeddings_matrix = np.vstack(cnae_df['embedding'].to_list())

# Criar um DataFrame para os resultados finais (uma linha por CAT)
result_data = []
# ...existing code...

# Iterar sobre cada linha (categoria) da planilha CAT com barra de progresso
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

# ...existing code...

# Converter a lista de resultados para DataFrame
console.print("Processando resultados...", style="cyan")
results_df = pd.DataFrame(result_data)

##########################################
# Passo 4: Visualizar e salvar os resultados
##########################################
console.print(Panel.fit("[bold green]PASSO 4: Visualizando e salvando resultados...[/bold green]"))

# Exibir informações sobre o resultado
console.print(f"Resultados gerados: {results_df.shape[0]} categorias CAT mapeadas", style="cyan")
console.print("Amostra dos resultados:", style="cyan")
console.print(results_df.iloc[:5, :5].to_string())  # Mostra apenas as primeiras 5 linhas e 5 colunas

# Garantir que o diretório de saída exista
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Salvar o resultado em Excel usando o caminho predefinido
console.print(f"Salvando resultados em: {OUTPUT_FILE}", style="yellow")
results_df.to_excel(OUTPUT_FILE, sheet_name='Mapeamento_TOP10', index=False)
console.print(f"✓ Arquivo salvo com sucesso!", style="green")
console.print(Panel.fit("[bold green]Processamento concluído![/bold green]"))