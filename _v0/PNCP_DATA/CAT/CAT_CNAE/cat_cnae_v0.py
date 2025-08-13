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

# Baixe os recursos do NLTK se necessário (descomente as linhas abaixo)
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
# Altere os caminhos conforme necessário
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\"
CAT_PATH = os.path.join(BASE_PATH, "PNCP\\CAT\\NOVA\\")
CNAE_PATH = os.path.join(BASE_PATH, "CNAE\\")
CAT_FILE = CAT_PATH + 'NOVA CAT.xlsx'
CNAE_FILE = CNAE_PATH + 'CNAE_v2.xlsx'

OUTPUT_PATH = os.path.join(CNAE_PATH, "OUTPUT\\")
OUTPUT_FILE = os.path.join(OUTPUT_PATH, f'CAT_CNAE_TOP10_{TIMESTAMP}.xlsx')

# Carregar planilhas
cat_df = pd.read_excel(CAT_FILE, sheet_name='CAT')
cnae_df = pd.read_excel(CNAE_FILE, sheet_name='CNAE_NV2')

# Supondo:
# Na NOVA CAT, a coluna com a descrição é "descricao"
# Na CNAE, a coluna com a descrição da Divisão é "divisao_descricao"
cat_df['descricao_proc'] = cat_df['NOMCAT'].astype(str).apply(preprocess_text)
cnae_df['divisao_proc'] = cnae_df['NOME'].astype(str).apply(preprocess_text)

##########################################
# Passo 2: Gerar os embeddings com Sentence Transformer
##########################################
# Modelo multilingue (bom para português)
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# Utilize encoding em lote, especialmente para bases grandes
cat_texts = cat_df['descricao_proc'].tolist()
cnae_texts = cnae_df['divisao_proc'].tolist()

cat_embeddings = model.encode(cat_texts, batch_size=64, show_progress_bar=True)
cnae_embeddings = model.encode(cnae_texts, batch_size=64, show_progress_bar=True)

# Armazenar os embeddings nos DataFrames
cat_df['embedding'] = list(cat_embeddings)
cnae_df['embedding'] = list(cnae_embeddings)

##########################################
# Passo 3: Calcular similaridade e gerar mapeamento top 10
##########################################
def get_top10_cnaes(cat_embedding, cnae_embeddings):
    # Calcular similaridade via cosseno
    sims = cosine_similarity([cat_embedding], cnae_embeddings)[0]
    # Ordenar e pegar os índices dos top 10 com maiores scores
    top10_idx = np.argsort(sims)[::-1][:10]
    top10_scores = sims[top10_idx]
    return top10_idx, top10_scores

# Converter a lista de embeddings de CNAE para matriz
cnae_embeddings_matrix = np.vstack(cnae_df['embedding'].to_list())

# Estruturar os resultados: para cada item CAT, armazena os top 10 CNAEs mapeados com score
top10_results = []

# Iterar sobre cada linha (categoria) da planilha CAT
for index, row in cat_df.iterrows():
    cat_embed = row['embedding']
    top10_idx, top10_scores = get_top10_cnaes(cat_embed, cnae_embeddings_matrix)
    for idx, score in zip(top10_idx, top10_scores):
        result = {
            'cat_id': row.get('CODCAT', index),   # Utilize o identificador existente ou o índice
            'cat_descricao': row['NOMCAT'],
            'cnae_id': cnae_df.loc[idx, 'CODIGO'] if 'CODIGO' in cnae_df.columns else idx,
            'cnae_descricao': cnae_df.loc[idx, 'NOME'],
            'score': score
        }
        top10_results.append(result)

results_df = pd.DataFrame(top10_results)



##########################################
# Passo 4: Visualizar e salvar os resultados
##########################################
# Exibir as primeiras linhas dos resultados
print(results_df.head(20))

# Garantir que o diretório de saída exista
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Salvar o resultado em Excel usando o caminho predefinido
results_df.to_excel(OUTPUT_FILE, sheet_name='Mapeamento_Top10', index=False)
print(f"Arquivo salvo em: {OUTPUT_FILE}")

# Salvar versão filtrada com scores altos (≥ 0.60)
results_refined = results_df[results_df['score'] >= 0.60]
filtered_output = os.path.join(OUTPUT_PATH, f'CAT_CNAE_TOP10_FILTERED_{TIMESTAMP}.xlsx')
results_refined.to_excel(filtered_output, sheet_name='Mapeamento_Filtrado', index=False)
print(f"Arquivo filtrado salvo em: {filtered_output}")