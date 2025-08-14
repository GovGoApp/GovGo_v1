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

data_inicial = 20250101
data_final = 20250331
codigo_modalidade = 6 # pregão eletrônico
codigo_municipio_ibge = '' 
cnpj = ''  
codigo_unidade_administrativa = '' 
tamanho_pagina = 50

# URL para pesquisa de processos publicados - somente com os parâmetros obrigatórios:
# páginas 1 A[a] 10

base_url = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
tamanho_pagina = 50  # Defina o tamanho da página conforme necessário
urls = []

for pagina in range(1, 11):  
    for uf in ['ES','SP']: #['PE', 'PB', 'AL', 'SE', 'BA', 'RN', 'CE']:  
        url = f'{base_url}?dataInicial={data_inicial}&dataFinal={data_final}&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}&tamanhoPagina={tamanho_pagina}&pagina={pagina}'
        urls.append(url)


# requisitando e criando o DF com os dados
# Lista para armazenar todos os processos
processos = []

# Iterar sobre as URLs e realizar as requisições
for url in urls:
    response = requests.get(url)
    if response.status_code == 200:
        dados_dict = response.json()['data']  # Assumindo que 'data' contém os processos
        
        # Iterar sobre os processos retornados
        for processo in dados_dict:
            sequencial = processo['sequencialCompra']
            orgao = processo['orgaoEntidade']['razaoSocial']
            uf = processo['unidadeOrgao']['ufSigla']
            inclusao = processo['dataInclusao']
            amparo_legal = processo['amparoLegal']['descricao']
            abertura = processo['dataAberturaProposta']
            encerramento = processo['dataEncerramentoProposta']
            n_processo = processo['processo']
            objeto = processo['objetoCompra']
            link = processo['linkSistemaOrigem']
            valor_estimado = processo['valorTotalEstimado']
            valor_homologado = processo['valorTotalHomologado']
            disputa = processo['modoDisputaNome']
            plataforma = processo['usuarioNome']
            situacao = processo['situacaoCompraNome']
            srp = processo['srp']
            
            # Adicionar os dados formatados à lista de processos
            processos.append([
                sequencial, orgao, uf, inclusao, amparo_legal, abertura, encerramento, n_processo, objeto, link,
                valor_estimado, valor_homologado, disputa, plataforma, situacao, srp
            ])
    #else:
        print(f"Erro na requisição para {url}: {response.status_code} - {response.text}")

# Criar o DataFrame
df = pd.DataFrame(processos, columns=[
    'sequencial', 'orgao', 'uf', 'inclusao', 'amparo_legal', 'abertura', 'encerramento', 'n_processo', 'objeto', 'link',
    'valor_estimado', 'valor_homologado', 'disputa', 'plataforma', 'situacao', 'srp'
])

pd.set_option('display.max_rows', None)  

# organizando os dados

df['valor_estimado'] = pd.to_numeric(df['valor_estimado'], errors='coerce')

# data formatada

df['abertura'] = pd.to_datetime(df['abertura'], format='%Y-%m-%dT%H:%M:%S')
df['inclusao'] = pd.to_datetime(df['inclusao'], format='%Y-%m-%dT%H:%M:%S')
df['encerramento'] = pd.to_datetime(df['encerramento'], format='%Y-%m-%dT%H:%M:%S')

# filtrando pelas palavras de interesse 

palavras_chave = [
    'alimentício', 'alimento', 'alimentação', 'merenda', 'merenda escolar', 'gênero']

palavras_chave = [palavra.lower() for palavra in palavras_chave]

filtro = df['objeto'].str.lower().str.contains('|'.join(palavras_chave), na=False)

df_filtrado = df[filtro].reset_index()




def clean_illegal_chars(s):
    if isinstance(s, str):
        # Remove caracteres de controle (ASCII < 32)
        return re.sub(r'[\x00-\x1F]+', ' ', s)
    return s

# Aplicar a limpeza em todas as colunas do DataFrame
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].apply(clean_illegal_chars)
    df_filtrado[col] = df_filtrado[col].apply(clean_illegal_chars)


# salvar o arquivo no excel 

data_atual = datetime.now().strftime('%Y%m%d')

PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\PNCP\\"

nome_arquivo_excel = PATH + f'licitações_{data_atual}.xlsx'

with pd.ExcelWriter(nome_arquivo_excel) as writer:
    df.to_excel(writer, sheet_name='Todos', index=False)

    df_filtrado.to_excel(writer, sheet_name='Filtrados', index=False)

print(f'DataFrame salvo com sucesso em {nome_arquivo_excel}')