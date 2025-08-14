# importando os módulos 
import pandas as pd
import requests
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import seaborn as sns
import re
from datetime import datetime

# parâmetros - pesquisa por data de publicação 
data_inicial = 20250301
data_final = 20250331
codigo_modalidade = 6  # pregão eletrônico
codigo_municipio_ibge = '' 
cnpj = ''  
codigo_unidade_administrativa = '' 
tamanho_pagina = 50

base_url = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
ufs = ['ES', 'SP']

# Lista para armazenar todos os processos (dicionários completos)
processos = []

for uf in ufs:
    # Requisição inicial para obter o total de páginas para o UF atual
    url_inicial = f'{base_url}?dataInicial={data_inicial}&dataFinal={data_final}&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}&tamanhoPagina={tamanho_pagina}&pagina=1'
    response_inicial = requests.get(url_inicial)
    if response_inicial.status_code == 200:
        json_inicial = response_inicial.json()
        total_paginas = json_inicial.get("totalPaginas", 1)
        # Iterar por todas as páginas conforme total_paginas
        for pagina in range(1, total_paginas + 1):
            url = f'{base_url}?dataInicial={data_inicial}&dataFinal={data_final}&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}&tamanhoPagina={tamanho_pagina}&pagina={pagina}'
            response = requests.get(url)
            if response.status_code == 200:
                dados = response.json().get('data', [])
                # Adiciona o dicionário completo de cada processo
                processos.extend(dados)
            else:
                print(f"Erro na requisição para {url}: {response.status_code} - {response.text}")
    else:
        print(f"Erro na requisição para {url_inicial}: {response_inicial.status_code} - {response_inicial.text}")

# Criar o DataFrame utilizando pd.json_normalize para capturar todos os campos dos processos
df = pd.json_normalize(processos)

# Renomear 'objetoCompra' para 'objeto' para manter a consistência com o restante do código
if 'objetoCompra' in df.columns:
    df.rename(columns={'objetoCompra': 'objeto'}, inplace=True)

pd.set_option('display.max_rows', None)  

# Organizando os dados: conversões numéricas e de datas, se os campos existirem
if 'valorTotalEstimado' in df.columns:
    df['valorTotalEstimado'] = pd.to_numeric(df['valorTotalEstimado'], errors='coerce')
if 'dataAberturaProposta' in df.columns:
    df['dataAberturaProposta'] = pd.to_datetime(df['dataAberturaProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
if 'dataInclusao' in df.columns:
    df['dataInclusao'] = pd.to_datetime(df['dataInclusao'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
if 'dataEncerramentoProposta' in df.columns:
    df['dataEncerramentoProposta'] = pd.to_datetime(df['dataEncerramentoProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')

# Filtrando pelas palavras de interesse utilizando a coluna 'objeto'
palavras_chave = ['alimentício', 'alimento', 'alimentação', 'merenda', 'merenda escolar', 'gênero']
palavras_chave = [palavra.lower() for palavra in palavras_chave]

filtro = df['objeto'].str.lower().str.contains('|'.join(palavras_chave), na=False)
df_filtrado = df[filtro].reset_index(drop=True)

def clean_illegal_chars(s):
    if isinstance(s, str):
        # Remove caracteres de controle (ASCII < 32)
        return re.sub(r'[\x00-\x1F]+', ' ', s)
    return s

# Aplicar a limpeza em todas as colunas de tipo objeto do DataFrame principal e do filtrado
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].apply(clean_illegal_chars)
for col in df_filtrado.select_dtypes(include='object').columns:
    df_filtrado[col] = df_filtrado[col].apply(clean_illegal_chars)

# Salvar o arquivo em Excel
data_atual = datetime.now().strftime('%Y%m%d')
PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\PNCP\\"
nome_arquivo_excel = PATH + f'licitações_{data_atual}.xlsx'

with pd.ExcelWriter(nome_arquivo_excel) as writer:
    df.to_excel(writer, sheet_name='Todos', index=False)
    df_filtrado.to_excel(writer, sheet_name='Filtrados', index=False)

print(f'DataFrame salvo com sucesso em {nome_arquivo_excel}')
