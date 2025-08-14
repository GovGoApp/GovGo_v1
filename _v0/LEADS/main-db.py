import requests
import pandas as pd
import zipfile
import os
import sqlite3
import datetime
from urllib.request import urlretrieve
from urllib.error import HTTPError
import time
import csv
import shutil

def obter_cnpjs_pncp(quantidade, data_inicial, data_final):
    """
    Obtém CNPJs do PNCP dentro do período especificado
    
    Args:
        quantidade (int): Quantidade máxima de CNPJs a retornar
        data_inicial (str): Data inicial no formato 'YYYY-MM-DD'
        data_final (str): Data final no formato 'YYYY-MM-DD'
        
    Returns:
        list: Lista de CNPJs únicos
    """
    url_base = "https://pncp.gov.br/api/consulta/v1/contratos"
    tamanho_pagina = 100
    pagina = 0
    cnpjs = set()
    
    while len(cnpjs) < quantidade:
        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
            "dataInicial": data_inicial,
            "dataFinal": data_final
        }
        
        try:
            print(f"Consultando página {pagina} da API PNCP...")
            response = requests.get(url_base, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
            
            # Extrair CNPJs do campo niFornecedor
            for contrato in data:
                if 'niFornecedor' in contrato and contrato['niFornecedor']:
                    cnpjs.add(contrato['niFornecedor'])
                    if len(cnpjs) >= quantidade:
                        break
            
            if len(data) < tamanho_pagina or len(cnpjs) >= quantidade:
                break
                
            pagina += 1
            time.sleep(0.5)  # Evitar sobrecarregar a API
            
        except Exception as e:
            print(f"Erro ao consultar a API do PNCP: {e}")
            break
    
    return list(cnpjs)[:quantidade]

def criar_db():
    """
    Baixa arquivos de dados abertos de CNPJ, extrai e cria uma database SQLite
    """
    # Criar pastas para os arquivos
    data_dir = "dados_cnpj"
    extract_dir = "dados_cnpj_extraidos"
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(extract_dir, exist_ok=True)
    
    # Obter mês atual e anterior
    hoje = datetime.datetime.now()
    mes_atual = hoje.strftime("%Y-%m")
    mes_anterior = (hoje.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    
    # Tenta o mês atual primeiro, depois o mês anterior
    for mes in [mes_atual, mes_anterior]:
        base_url = f"https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/{mes}/"
        arquivos_baixados = False
        
        # Baixar arquivos de Estabelecimentos
        index = 0
        estabelecimentos_baixados = False
        while True:
            arquivo = f"Estabelecimentos{index}.zip"
            url = base_url + arquivo
            destino = os.path.join(data_dir, arquivo)
            
            try:
                if not os.path.exists(destino):
                    print(f"Baixando {url}...")
                    urlretrieve(url, destino)
                    estabelecimentos_baixados = True
                else:
                    estabelecimentos_baixados = True
                    print(f"Arquivo {destino} já existe.")
                
                index += 1
                
            except HTTPError as e:
                if e.code == 404:
                    print(f"Arquivo {url} não encontrado, passando para o próximo.")
                    break
                else:
                    print(f"Erro ao baixar {url}: {e}")
                    break
        
        # Baixar arquivos de Socios
        index = 0
        socios_baixados = False
        while True:
            arquivo = f"Socios{index}.zip"
            url = base_url + arquivo
            destino = os.path.join(data_dir, arquivo)
            
            try:
                if not os.path.exists(destino):
                    print(f"Baixando {url}...")
                    urlretrieve(url, destino)
                    socios_baixados = True
                else:
                    socios_baixados = True
                    print(f"Arquivo {destino} já existe.")
                
                index += 1
                
            except HTTPError as e:
                if e.code == 404:
                    print(f"Arquivo {url} não encontrado, passando para o próximo.")
                    break
                else:
                    print(f"Erro ao baixar {url}: {e}")
                    break
        
        # Se conseguimos baixar ambos os tipos de arquivos, saímos do loop
        if estabelecimentos_baixados and socios_baixados:
            arquivos_baixados = True
            break
    
    if not arquivos_baixados:
        print("Não foi possível baixar os arquivos necessários.")
        return False
    
    # Extrair arquivos
    print("Extraindo arquivos...")
    for arquivo in os.listdir(data_dir):
        if arquivo.startswith("Estabelecimentos") or arquivo.startswith("Socios"):
            caminho_zip = os.path.join(data_dir, arquivo)
            try:
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                print(f"Erro ao extrair {caminho_zip}: {e}")
                continue
    
    # Criar banco de dados SQLite
    print("Criando banco de dados...")
    conn = sqlite3.connect('cnpj.db')
    cursor = conn.cursor()
    
    # Criar tabelas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS estabelecimentos (
        cnpj TEXT PRIMARY KEY,
        nome_fantasia TEXT,
        situacao_cadastral INTEGER,
        data_situacao_cadastral TEXT,
        motivo_situacao_cadastral INTEGER,
        nome_cidade_exterior TEXT,
        pais INTEGER,
        data_inicio_atividade TEXT,
        cnae_fiscal_principal INTEGER,
        cnae_fiscal_secundaria TEXT,
        tipo_logradouro TEXT,
        logradouro TEXT,
        numero TEXT,
        complemento TEXT,
        bairro TEXT,
        cep TEXT,
        uf TEXT,
        municipio INTEGER,
        ddd_1 TEXT,
        telefone_1 TEXT,
        ddd_2 TEXT,
        telefone_2 TEXT,
        ddd_fax TEXT,
        fax TEXT,
        correio_eletronico TEXT,
        situacao_especial TEXT,
        data_situacao_especial TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS socios (
        cnpj_basico TEXT,
        identificador_socio INTEGER,
        nome_socio TEXT,
        cnpj_cpf_socio TEXT,
        qualificacao_socio INTEGER,
        data_entrada_sociedade TEXT,
        pais INTEGER,
        representante_legal TEXT,
        nome_representante TEXT,
        qualificacao_representante INTEGER,
        faixa_etaria INTEGER,
        PRIMARY KEY (cnpj_basico, cnpj_cpf_socio)
    )
    ''')
    
    # Importar dados dos arquivos CSV para o SQLite
    print("Importando dados para o banco de dados...")
    
    for arquivo in os.listdir(extract_dir):
        if "ESTABELE" in arquivo.upper():  # Arquivo de Estabelecimentos
            print(f"Processando {arquivo}...")
            caminho_csv = os.path.join(extract_dir, arquivo)
            
            # Ler o arquivo CSV em chunks para não sobrecarregar a memória
            for chunk in pd.read_csv(caminho_csv, sep=';', header=None, chunksize=10000, 
                                     encoding='latin1', low_memory=False, dtype=str):
                # Colunas do arquivo de estabelecimentos
                chunk.columns = ['cnpj_basico', 'cnpj_ordem', 'cnpj_dv', 'matriz_filial',
                                'nome_fantasia', 'situacao_cadastral', 'data_situacao_cadastral',
                                'motivo_situacao_cadastral', 'nome_cidade_exterior', 'pais',
                                'data_inicio_atividade', 'cnae_fiscal_principal', 'cnae_fiscal_secundaria',
                                'tipo_logradouro', 'logradouro', 'numero', 'complemento', 'bairro',
                                'cep', 'uf', 'municipio', 'ddd_1', 'telefone_1', 'ddd_2',
                                'telefone_2', 'ddd_fax', 'fax', 'correio_eletronico',
                                'situacao_especial', 'data_situacao_especial']
                
                # Criar CNPJ completo
                chunk['cnpj'] = chunk['cnpj_basico'] + chunk['cnpj_ordem'] + chunk['cnpj_dv']
                
                # Inserir dados na tabela
                for _, row in chunk.iterrows():
                    try:
                        cursor.execute('''
                        INSERT OR REPLACE INTO estabelecimentos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row['cnpj'], row['nome_fantasia'], row['situacao_cadastral'],
                            row['data_situacao_cadastral'], row['motivo_situacao_cadastral'],
                            row['nome_cidade_exterior'], row['pais'], row['data_inicio_atividade'],
                            row['cnae_fiscal_principal'], row['cnae_fiscal_secundaria'],
                            row['tipo_logradouro'], row['logradouro'], row['numero'],
                            row['complemento'], row['bairro'], row['cep'], row['uf'],
                            row['municipio'], row['ddd_1'], row['telefone_1'],
                            row['ddd_2'], row['telefone_2'], row['ddd_fax'],
                            row['fax'], row['correio_eletronico'], 
                            row['situacao_especial'], row['data_situacao_especial']
                        ))
                    except Exception as e:
                        print(f"Erro ao inserir dados de estabelecimento: {e}")
                
                conn.commit()
        
        elif "SOCIO" in arquivo.upper():  # Arquivo de Sócios
            print(f"Processando {arquivo}...")
            caminho_csv = os.path.join(extract_dir, arquivo)
            
            # Ler o arquivo CSV em chunks
            for chunk in pd.read_csv(caminho_csv, sep=';', header=None, chunksize=10000, 
                                    encoding='latin1', low_memory=False, dtype=str):
                # Colunas do arquivo de sócios
                chunk.columns = ['cnpj_basico', 'identificador_socio', 'nome_socio',
                                'cnpj_cpf_socio', 'qualificacao_socio', 'data_entrada_sociedade',
                                'pais', 'representante_legal', 'nome_representante',
                                'qualificacao_representante', 'faixa_etaria']
                
                # Inserir dados na tabela
                for _, row in chunk.iterrows():
                    try:
                        cursor.execute('''
                        INSERT OR REPLACE INTO socios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row['cnpj_basico'], row['identificador_socio'], row['nome_socio'],
                            row['cnpj_cpf_socio'], row['qualificacao_socio'],
                            row['data_entrada_sociedade'], row['pais'],
                            row['representante_legal'], row['nome_representante'],
                            row['qualificacao_representante'], row['faixa_etaria']
                        ))
                    except Exception as e:
                        print(f"Erro ao inserir dados de sócio: {e}")
                
                conn.commit()
    
    # Criar índices para melhorar performance
    print("Criando índices...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cnpj ON estabelecimentos(cnpj)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cnpj_basico ON socios(cnpj_basico)')
    
    conn.commit()
    conn.close()
    
    print("Banco de dados criado com sucesso!")
    return True

def obter_contatos(lista_cnpjs):
    """
    Obtém dados de contato dos CNPJs fornecidos
    
    Args:
        lista_cnpjs (list): Lista de CNPJs para buscar contatos
        
    Returns:
        list: Lista de dicionários com dados de contato
    """
    if not lista_cnpjs:
        return []
    
    contatos = []
    
    try:
        conn = sqlite3.connect('cnpj.db')
        cursor = conn.cursor()
        
        for cnpj in lista_cnpjs:
            # Buscar dados do estabelecimento
            cnpj_basico = cnpj[:8]  # Os 8 primeiros dígitos correspondem ao CNPJ básico
            
            cursor.execute("""
            SELECT 
                e.cnpj, 
                e.nome_fantasia, 
                e.correio_eletronico, 
                e.ddd_1, 
                e.telefone_1, 
                e.ddd_2, 
                e.telefone_2,
                e.logradouro,
                e.numero,
                e.complemento,
                e.bairro,
                e.cep,
                e.uf,
                e.municipio
            FROM estabelecimentos e
            WHERE e.cnpj = ?
            """, (cnpj,))
            
            estabelecimento = cursor.fetchone()
            
            if not estabelecimento:
                print(f"Estabelecimento não encontrado para o CNPJ {cnpj}")
                continue
            
            info_estabelecimento = {
                'cnpj': estabelecimento[0],
                'nome_fantasia': estabelecimento[1],
                'email': estabelecimento[2],
                'telefone1': f"{estabelecimento[3]} {estabelecimento[4]}".strip(),
                'telefone2': f"{estabelecimento[5]} {estabelecimento[6]}".strip(),
                'endereco': f"{estabelecimento[7]}, {estabelecimento[8]} {estabelecimento[9]}, {estabelecimento[10]}, {estabelecimento[11]}, {estabelecimento[12]}-{estabelecimento[13]}".strip().replace('  ', ' '),
            }
            
            # Buscar dados dos sócios
            cursor.execute("""
            SELECT 
                s.nome_socio, 
                s.cnpj_cpf_socio
            FROM socios s
            WHERE s.cnpj_basico = ?
            """, (cnpj_basico,))
            
            socios = cursor.fetchall()
            
            if socios:
                info_estabelecimento['socios'] = [{'nome': socio[0], 'cpf_cnpj': socio[1]} for socio in socios]
            else:
                info_estabelecimento['socios'] = []
            
            contatos.append(info_estabelecimento)
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao obter contatos: {e}")
    
    return contatos

def exportar_contatos(contatos, arquivo_saida="contatos_cnpj.csv"):
    """
    Exporta a lista de contatos para um arquivo CSV
    
    Args:
        contatos (list): Lista de dicionários com dados de contato
        arquivo_saida (str): Nome do arquivo CSV de saída
    """
    if not contatos:
        print("Não há contatos para exportar.")
        return
    
    try:
        with open(arquivo_saida, 'w', newline='', encoding='utf-8') as file:
            # Definir cabeçalhos base
            headers = ['cnpj', 'nome_fantasia', 'email', 'telefone1', 'telefone2', 'endereco']
            
            # Adicionar cabeçalhos para sócios - verificar quantos sócios tem no máximo
            max_socios = 0
            for contato in contatos:
                if 'socios' in contato:
                    max_socios = max(max_socios, len(contato['socios']))
            
            for i in range(max_socios):
                headers.extend([f'socio_{i+1}_nome', f'socio_{i+1}_cpf_cnpj'])
            
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            
            for contato in contatos:
                # Preparar linha base
                linha = {
                    'cnpj': contato.get('cnpj', ''),
                    'nome_fantasia': contato.get('nome_fantasia', ''),
                    'email': contato.get('email', ''),
                    'telefone1': contato.get('telefone1', ''),
                    'telefone2': contato.get('telefone2', ''),
                    'endereco': contato.get('endereco', '')
                }
                
                # Adicionar sócios
                if 'socios' in contato:
                    for i, socio in enumerate(contato['socios']):
                        if i < max_socios:
                            linha[f'socio_{i+1}_nome'] = socio.get('nome', '')
                            linha[f'socio_{i+1}_cpf_cnpj'] = socio.get('cpf_cnpj', '')
                
                writer.writerow(linha)
        
        print(f"Contatos exportados com sucesso para {arquivo_saida}")
        
    except Exception as e:
        print(f"Erro ao exportar contatos: {e}")

def main():
    """
    Função principal que coordena a execução das demais funções
    """
    print("Iniciando processo de coleta de dados de contato...")
    
    # 1. Criar banco de dados
    print("\n1. Criando banco de dados...")
    criar_db()
    
    # 2. Obter CNPJs da API do PNCP
    print("\n2. Obtendo CNPJs da API do PNCP...")
    quantidade_cnpjs = 50  # Quantidade de CNPJs a coletar
    data_final = datetime.now()
    data_inicial = datetime(data_final.year - 1, data_final.month, data_final.day)
    
    # Formata as datas no padrão YYYYMMDD
    data_final_str = data_final.strftime("%Y%m%d")
    data_inicial_str = data_inicial.strftime("%Y%m%d")
    
    cnpjs = obter_cnpjs_pncp(quantidade_cnpjs, data_inicial_str, data_final_str)
    print(f"Foram obtidos {len(cnpjs)} CNPJs únicos.")
    
    # 3. Obter contatos
    print("\n3. Obtendo dados de contato para os CNPJs...")
    contatos = obter_contatos(cnpjs)
    print(f"Foram obtidos dados de contato para {len(contatos)} CNPJs.")
    
    # 4. Exportar contatos
    print("\n4. Exportando dados de contato para CSV...")
    exportar_contatos(contatos)
    
    print("\nProcesso concluído com sucesso!")

if __name__ == "__main__":
    main()