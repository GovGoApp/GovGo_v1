import os
import csv
import json
import time
import requests
import pandas as pd
import sqlite3
import zipfile
import shutil
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta


class ReceitaFederalDados:
    def __init__(self):
        self.base_url = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/"
        self.data_dir = "dados_cnpj"
        self.db_path = os.path.join(self.data_dir, "cnpj.db")
        self.downloaded_files = []
        self.current_data_folder = None
        self.create_data_dir()

    def create_data_dir(self):
        """Cria o diretório de dados se não existir"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def verificar_arquivos_disponíveis(self):
        """Verifica quais arquivos estão disponíveis para download"""
        print("Verificando arquivos disponíveis na Receita Federal...")
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
            
            # Atualiza a lista de arquivos necessários com os nomes mais recentes
            # Isso é necessário porque os nomes dos arquivos mudam conforme são atualizados
            arquivos = []
            # Aqui usaríamos um parser HTML para extrair os links, mas para simplificar
            # vamos manter os nomes fixos (o usuário pode atualizar manualmente)
            
            if arquivos:
                self.arquivos_necessarios = arquivos
                
            return True
        except Exception as e:
            print(f"Erro ao verificar arquivos disponíveis: {e}")
            return False

    def encontrar_pasta_dados_atual(self):
        """Encontra a pasta mais recente de dados no site da Receita Federal"""
        print("Procurando pasta de dados mais recente...")
        
        # Obter a data atual
        hoje = datetime.now()
        
        # Tentar o mês atual e depois o anterior, até três meses atrás
        for i in range(4):  # Tenta o mês atual e 3 meses anteriores
            # Calcula o mês a ser verificado (mês atual - i)
            data_teste = hoje.replace(day=1) - timedelta(days=i*30)
            pasta = data_teste.strftime("%Y-%m")  # Formato YYYY-MM
            
            url_pasta = f"{self.base_url}{pasta}/"
            print(f"Verificando se existe a pasta: {url_pasta}")
            
            try:
                response = requests.head(url_pasta)
                if response.status_code == 200:
                    print(f"Pasta encontrada: {pasta}")
                    self.current_data_folder = pasta
                    return True
            except Exception as e:
                print(f"Erro ao verificar pasta {pasta}: {e}")
        
        print("Não foi possível encontrar uma pasta de dados válida dos últimos 4 meses.")
        return False

    def baixar_arquivo(self, arquivo):
        """Baixa um arquivo da Receita Federal"""
        url = f"{self.base_url}{arquivo}"
        filepath = os.path.join(self.data_dir, arquivo)
        
        if os.path.exists(filepath):
            print(f"Arquivo {arquivo} já existe localmente.")
            return True
        
        try:
            print(f"Baixando {arquivo}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024  # 1 Kibibyte
            
            with open(filepath, 'wb') as file, tqdm(
                desc=arquivo,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(block_size):
                    file.write(data)
                    bar.update(len(data))
                    
            print(f"Download de {arquivo} concluído!")
            return True
        except Exception as e:
            print(f"Erro ao baixar {arquivo}: {e}")
            return False

    def baixar_arquivos_incrementais(self, tipo_arquivo):
        """Baixa arquivos incrementalmente (0, 1, 2...) até não haver mais"""
        if not self.current_data_folder:
            if not self.encontrar_pasta_dados_atual():
                return False
                
        index = 0
        arquivos_baixados = 0
        
        while True:
            arquivo = f"{tipo_arquivo}{index}.zip"
            url = f"{self.base_url}{self.current_data_folder}/{arquivo}"
            filepath = os.path.join(self.data_dir, arquivo)
            
            print(f"Tentando baixar: {url}")
            
            try:
                response = requests.head(url)
                if response.status_code != 200:
                    print(f"Arquivo {arquivo} não encontrado. Finalizando download de {tipo_arquivo}.")
                    break
                    
                if os.path.exists(filepath):
                    print(f"Arquivo {arquivo} já existe localmente.")
                    self.downloaded_files.append(arquivo)
                    index += 1
                    arquivos_baixados += 1
                    continue
                
                print(f"Baixando {arquivo}...")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                block_size = 1024  # 1 Kibibyte
                
                with open(filepath, 'wb') as file, tqdm(
                    desc=arquivo,
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        bar.update(len(data))
                        
                print(f"Download de {arquivo} concluído!")
                self.downloaded_files.append(arquivo)
                self.extrair_arquivo(arquivo)
                
                index += 1
                arquivos_baixados += 1
                
            except requests.exceptions.RequestException as e:
                if arquivos_baixados == 0:
                    print(f"Erro ao baixar o primeiro arquivo de {tipo_arquivo}: {str(e)}")
                    return False
                else:
                    print(f"Não há mais arquivos do tipo {tipo_arquivo} para baixar.")
                    break
                    
        print(f"Total de {arquivos_baixados} arquivos de {tipo_arquivo} baixados.")
        return arquivos_baixados > 0

    def extrair_arquivo(self, arquivo):
        """Extrai um arquivo ZIP baixado"""
        zip_path = os.path.join(self.data_dir, arquivo)
        extract_dir = os.path.join(self.data_dir, arquivo.replace(".zip", ""))
        
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
            
        try:
            print(f"Extraindo {arquivo}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"Extração de {arquivo} concluída!")
            return True
        except Exception as e:
            print(f"Erro ao extrair {arquivo}: {e}")
            return False

    def preparar_banco_dados(self):
        """Cria ou conecta ao banco de dados SQLite"""
        if os.path.exists(self.db_path):
            print("Banco de dados já existe.")
            return True
            
        try:
            print("Criando banco de dados...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Criar tabela de estabelecimentos
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS estabelecimentos (
                cnpj_basico TEXT,
                cnpj_ordem TEXT,
                cnpj_dv TEXT,
                identificador_matriz_filial TEXT,
                nome_fantasia TEXT,
                situacao_cadastral TEXT,
                data_situacao_cadastral TEXT,
                motivo_situacao_cadastral TEXT,
                nome_cidade_exterior TEXT,
                pais TEXT,
                data_inicio_atividade TEXT,
                cnae_fiscal_principal TEXT,
                cnae_fiscal_secundaria TEXT,
                tipo_logradouro TEXT,
                logradouro TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cep TEXT,
                uf TEXT,
                municipio TEXT,
                ddd_1 TEXT,
                telefone_1 TEXT,
                ddd_2 TEXT,
                telefone_2 TEXT,
                ddd_fax TEXT,
                fax TEXT,
                email TEXT,
                situacao_especial TEXT,
                data_situacao_especial TEXT
            )
            ''')
            
            # Criar tabela de sócios
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS socios (
                cnpj_basico TEXT,
                identificador_socio TEXT,
                nome_socio TEXT,
                cpf_cnpj_socio TEXT,
                qualificacao_socio TEXT,
                data_entrada_sociedade TEXT,
                pais TEXT,
                representante_legal TEXT,
                nome_representante TEXT,
                qualificacao_representante TEXT,
                faixa_etaria TEXT
            )
            ''')
            
            # Criar índices para otimizar as consultas
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnpj_basico ON estabelecimentos (cnpj_basico)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_socios_cnpj_basico ON socios (cnpj_basico)')
            
            conn.commit()
            conn.close()
            
            print("Banco de dados criado com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao preparar banco de dados: {e}")
            return False

    def importar_dados_socios(self):
        """Importa dados de sócios para o banco"""
        # Procurar os diretórios extraídos dos arquivos Socios*.zip
        socios_dirs = [d for d in os.listdir(self.data_dir) 
                      if os.path.isdir(os.path.join(self.data_dir, d)) 
                      and d.startswith("Socios")]
        
        if not socios_dirs:
            print("Diretório de sócios não encontrado!")
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for dir_name in socios_dirs:
                dir_path = os.path.join(self.data_dir, dir_name)
                
                # Listar arquivos CSV no diretório
                csv_files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    file_path = os.path.join(dir_path, csv_file)
                    print(f"Importando sócios de {csv_file}...")
                    
                    # Para não carregar tudo na memória, vamos ler e inserir em blocos
                    chunk_size = 10000
                    count = 0
                    
                    # Criando um DataFrame vazio apenas para obter os nomes das colunas
                    with open(file_path, 'r', encoding='latin1') as f:
                        # Lê apenas uma linha para obter cabeçalho
                        header = next(csv.reader(f, delimiter=';'))
                    
                    for chunk in pd.read_csv(file_path, sep=';', encoding='latin1', 
                                           chunksize=chunk_size, header=None,
                                           names=header, low_memory=True):
                        chunk.fillna('', inplace=True)
                        chunk.to_sql('socios', conn, if_exists='append', index=False)
                        count += len(chunk)
                        print(f"Inseridos {count} sócios...")
            
            conn.commit()
            conn.close()
            print("Importação de sócios concluída!")
            return True
        except Exception as e:
            print(f"Erro ao importar sócios: {e}")
            return False

    def importar_dados_estabelecimentos(self):
        """Importa dados de estabelecimentos para o banco"""
        # Procurar os diretórios extraídos dos arquivos Estabelecimentos*.zip
        estabelecimentos_dirs = [d for d in os.listdir(self.data_dir) 
                                if os.path.isdir(os.path.join(self.data_dir, d)) 
                                and d.startswith("Estabelecimentos")]
        
        if not estabelecimentos_dirs:
            print("Diretório de estabelecimentos não encontrado!")
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for dir_name in estabelecimentos_dirs:
                dir_path = os.path.join(self.data_dir, dir_name)
                
                # Listar arquivos CSV no diretório
                csv_files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    file_path = os.path.join(dir_path, csv_file)
                    print(f"Importando estabelecimentos de {csv_file}...")
                    
                    # Para não carregar tudo na memória, vamos ler e inserir em blocos
                    chunk_size = 10000
                    count = 0
                    
                    # Criando um DataFrame vazio apenas para obter os nomes das colunas
                    with open(file_path, 'r', encoding='latin1') as f:
                        # Lê apenas uma linha para obter cabeçalho
                        header = next(csv.reader(f, delimiter=';'))
                    
                    for chunk in pd.read_csv(file_path, sep=';', encoding='latin1', 
                                           chunksize=chunk_size, header=None, 
                                           names=header, low_memory=True):
                        chunk.fillna('', inplace=True)
                        chunk.to_sql('estabelecimentos', conn, if_exists='append', index=False)
                        count += len(chunk)
                        print(f"Inseridos {count} estabelecimentos...")
            
            conn.commit()
            conn.close()
            print("Importação de estabelecimentos concluída!")
            return True
        except Exception as e:
            print(f"Erro ao importar estabelecimentos: {e}")
            return False

    def preparar_base_dados(self):
        """Prepara toda a base de dados"""
        if os.path.exists(self.db_path):
            print("Base de dados já existe e está pronta para uso!")
            return True
            
        # Definir os tipos de arquivos necessários
        tipos_arquivos = ["Estabelecimentos", "Socios"]
        
        # Encontrar a pasta de dados atual
        if not self.encontrar_pasta_dados_atual():
            print("Não foi possível encontrar uma pasta de dados válida.")
            return False
        
        # Baixa e extrai os arquivos necessários
        for tipo in tipos_arquivos:
            print(f"Baixando arquivos de {tipo}...")
            self.baixar_arquivos_incrementais(tipo)
        
        # Prepara o banco de dados
        if not self.preparar_banco_dados():
            return False
            
        # Importa os dados
        if not self.importar_dados_estabelecimentos():
            return False
            
        if not self.importar_dados_socios():
            return False
            
        print("Base de dados preparada com sucesso!")
        return True


class CNPJConsultor:
    def __init__(self):
        self.output_dir = "resultados"
        self.create_output_dir()
        self.dados_rf = ReceitaFederalDados()
        
    def create_output_dir(self):
        """Cria o diretório de resultados se não existir"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def consultar_cnpj(self, cnpj):
        """Consulta os dados de um CNPJ usando os dados da Receita Federal"""
        # Remove caracteres não numéricos do CNPJ
        cnpj = ''.join(filter(str.isdigit, cnpj))
        
        # Verifica se o CNPJ tem 14 dígitos
        if len(cnpj) != 14:
            return {"error": f"CNPJ inválido: {cnpj}"}
        
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.dados_rf.db_path)
            conn.row_factory = sqlite3.Row  # Para facilitar o acesso aos campos pelo nome
            cursor = conn.cursor()
            
            # Extrai o CNPJ básico (8 primeiros dígitos)
            cnpj_basico = cnpj[:8]
            cnpj_ordem = cnpj[8:12]
            cnpj_dv = cnpj[12:14]
            
            # Primeiro, tenta uma busca específica para o CNPJ completo
            cursor.execute('''
            SELECT * FROM estabelecimentos 
            WHERE cnpj_basico = ? AND cnpj_ordem = ? AND cnpj_dv = ?
            ''', (cnpj_basico, cnpj_ordem, cnpj_dv))
            
            estabelecimento = cursor.fetchone()
            
            # Se não encontrar, tenta apenas pelo CNPJ básico
            if not estabelecimento:
                cursor.execute('''
                SELECT * FROM estabelecimentos WHERE cnpj_basico = ?
                ''', (cnpj_basico,))
                
                estabelecimento = cursor.fetchone()
                
            # Se ainda não encontrar, retorna erro
            if not estabelecimento:
                # Verifica se a tabela está vazia (o que indica problemas na importação)
                cursor.execute("SELECT COUNT(*) FROM estabelecimentos")
                count = cursor.fetchone()[0]
                if count == 0:
                    return {"error": f"A base de dados não possui registros de estabelecimentos. Execute a opção 4 para atualizar a base de dados."}
                return {"error": f"CNPJ {cnpj} não encontrado na base de dados"}
                
            # Converte para dicionário usando os nomes das colunas
            estabelecimento_dict = dict(estabelecimento)
            
            # Busca os sócios
            cursor.execute('''
            SELECT * FROM socios WHERE cnpj_basico = ?
            ''', (cnpj_basico,))
            
            socios = cursor.fetchall()
            socios_list = []
            
            if socios:
                for socio in socios:
                    socio_dict = dict(socio)
                    socios_list.append(socio_dict)
            
            # Monta o resultado final
            resultado = {
                "cnpj": cnpj,
                "cnpj_basico": cnpj_basico,
                "razao_social": "",  # Estabelecimentos não tem razão social diretamente
                "nome_fantasia": estabelecimento_dict.get("nome_fantasia", ""),
                "logradouro": estabelecimento_dict.get("logradouro", ""),
                "numero": estabelecimento_dict.get("numero", ""),
                "complemento": estabelecimento_dict.get("complemento", ""),
                "bairro": estabelecimento_dict.get("bairro", ""),
                "cep": estabelecimento_dict.get("cep", ""),
                "municipio": estabelecimento_dict.get("municipio", ""),
                "uf": estabelecimento_dict.get("uf", ""),
                "telefone": f"{estabelecimento_dict.get('ddd_1', '')}{estabelecimento_dict.get('telefone_1', '')}",
                "email": estabelecimento_dict.get("email", ""),
                "qsa": []
            }
            
            # Adiciona os sócios no formato adequado
            for socio in socios_list:
                resultado["qsa"].append({
                    "nome_socio": socio.get("nome_socio", ""),
                    "qualificacao_socio": socio.get("qualificacao_socio", ""),
                    "cpf_cnpj_socio": socio.get("cpf_cnpj_socio", "")
                })
                
            conn.close()
            return resultado
        except Exception as e:
            return {"error": f"Erro ao consultar CNPJ {cnpj}: {str(e)}"}
    
    def extrair_dados_socios(self, dados_cnpj):
        """Extrai dados de contato dos sócios a partir dos dados do CNPJ"""
        if "error" in dados_cnpj:
            return [{"cnpj": "erro", "razao_social": dados_cnpj["error"], "erro": dados_cnpj["error"]}]
        
        empresa = {
            "cnpj": dados_cnpj.get("cnpj", ""),
            "razao_social": dados_cnpj.get("razao_social", ""),
            "nome_fantasia": dados_cnpj.get("nome_fantasia", ""),
            "telefone": dados_cnpj.get("telefone", ""),
            "email": dados_cnpj.get("email", ""),
            "cep": dados_cnpj.get("cep", ""),
            "logradouro": dados_cnpj.get("logradouro", ""),
            "numero": dados_cnpj.get("numero", ""),
            "municipio": dados_cnpj.get("municipio", ""),
            "uf": dados_cnpj.get("uf", "")
        }
        
        resultado = []
        socios = dados_cnpj.get("qsa", [])
        
        if not socios:
            # Se não houver sócios, retorna apenas os dados da empresa
            empresa["tipo_socio"] = "N/A"
            empresa["nome_socio"] = "N/A"
            resultado.append(empresa)
            return resultado
            
        # Para cada sócio, cria um registro com dados da empresa + dados do sócio
        for socio in socios:
            socio_data = empresa.copy()
            socio_data["tipo_socio"] = socio.get("qualificacao_socio", "")
            socio_data["nome_socio"] = socio.get("nome_socio", "")
            resultado.append(socio_data)
            
        return resultado
    
    def processar_lista_cnpjs(self, cnpjs, max_workers=5):
        """Processa uma lista de CNPJs e retorna dados dos sócios"""
        todos_socios = []
        erros = []
        
        # Verifica se a base de dados está pronta
        if not os.path.exists(self.dados_rf.db_path):
            print("Base de dados não encontrada. Iniciando preparação...")
            if not self.dados_rf.preparar_base_dados():
                return [], ["Erro ao preparar base de dados"]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            resultados = list(executor.map(self.consultar_cnpj, cnpjs))
            
        for resultado in resultados:
            if "error" in resultado:
                erros.append(resultado["error"])
                continue
                
            dados_socios = self.extrair_dados_socios(resultado)
            todos_socios.extend(dados_socios)
            
        return todos_socios, erros
    
    def obter_cnpjs_pncp(self, quantidade):
        """Obtém CNPJs de fornecedores da API de contratos do PNCP"""
        url = "https://pncp.gov.br/api/consulta/v1/contratos"
        cnpjs = []
        pagina = 1
        tamanho_pagina = 100  # Obter mais registros por página para reduzir chamadas
        
        # Calcula o período de um ano
        data_final = datetime.now()
        data_inicial = datetime(data_final.year - 1, data_final.month, data_final.day)
        
        # Formata as datas no padrão YYYYMMDD
        data_final_str = data_final.strftime("%Y%m%d")
        data_inicial_str = data_inicial.strftime("%Y%m%d")
        
        print("Conectando à API do PNCP...")
        print(f"Período de consulta: {data_inicial_str} a {data_final_str}")
        
        try:
            while len(cnpjs) < quantidade:
                params = {
                    "pagina": pagina,
                    "tamanhoPagina": tamanho_pagina,
                    "dataInicial": data_inicial_str,
                    "dataFinal": data_final_str
                }
                
                print(f"Consultando página {pagina}...")
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extrai os contratos da resposta
                contratos = data.get("data", [])
                
                if not contratos:
                    print(f"Não foram encontrados mais contratos após {len(cnpjs)} CNPJs.")
                    break
                    
                for contrato in contratos:
                    # Extrai o CNPJ do fornecedor
                    cnpj_fornecedor = contrato.get("niFornecedor")
                    if cnpj_fornecedor and cnpj_fornecedor not in cnpjs:
                        cnpjs.append(cnpj_fornecedor)
                        
                    if len(cnpjs) >= quantidade:
                        break
                        
                pagina += 1
                time.sleep(0.5)  # Pausa para não sobrecarregar a API
                
        except Exception as e:
            print(f"Erro ao consultar a API do PNCP: {str(e)}")
            
        print(f"Foram obtidos {len(cnpjs)} CNPJs da API do PNCP.")
        return cnpjs
    
    def ler_cnpjs_arquivo(self, arquivo):
        """Lê CNPJs de um arquivo (txt, csv)"""
        cnpjs = []
        try:
            with open(arquivo, 'r') as f:
                for linha in f:
                    cnpj = linha.strip()
                    if cnpj:  # Verifica se não está vazio
                        cnpjs.append(cnpj)
            return cnpjs
        except Exception as e:
            print(f"Erro ao ler o arquivo: {str(e)}")
            return []
    
    def salvar_resultados(self, dados, formato="csv"):
        """Salva os resultados em um arquivo CSV ou Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not dados:
            print("Nenhum dado para salvar.")
            return None
            
        df = pd.DataFrame(dados)
        
        if formato.lower() == "csv":
            filename = f"{self.output_dir}/contatos_socios_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')  # Encoding para caracteres especiais
        elif formato.lower() == "excel":
            filename = f"{self.output_dir}/contatos_socios_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
        else:
            raise ValueError("Formato não suportado. Use 'csv' ou 'excel'.")
            
        print(f"Resultados salvos em: {filename}")
        return filename


def menu():
    consultor = CNPJConsultor()
    
    # Verificar se a base de dados já existe
    if not os.path.exists(consultor.dados_rf.db_path):
        print("\nPreparo inicial da base de dados")
        print("Este processo irá baixar e processar os arquivos da Receita Federal.")
        print("Atenção: Estes arquivos são grandes e podem levar bastante tempo para baixar e processar.")
        resposta = input("Deseja continuar? (s/n): ")
        
        if resposta.lower() == 's':
            consultor.dados_rf.preparar_base_dados()
        else:
            print("Não é possível prosseguir sem preparar a base de dados.")
            return
    
    while True:
        print("\n========== CONSULTA DE CNPJs E CONTATOS DE SÓCIOS ==========")
        print("1. Consultar CNPJs de um arquivo")
        print("2. Digitar CNPJs manualmente")
        print("3. Obter CNPJs da API do PNCP")
        print("4. Atualizar base de dados da Receita Federal")
        print("5. Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            arquivo = input("Digite o caminho do arquivo com os CNPJs (um por linha): ")
            if not os.path.exists(arquivo):
                print("Arquivo não encontrado!")
                continue
                
            cnpjs = consultor.ler_cnpjs_arquivo(arquivo)
            if not cnpjs:
                print("Nenhum CNPJ encontrado no arquivo!")
                continue
                
            print(f"Foram encontrados {len(cnpjs)} CNPJs no arquivo.")
            
            formato = input("Formato de saída (csv ou excel) [padrão: csv]: ").lower() or "csv"
            if formato not in ["csv", "excel"]:
                print("Formato inválido! Usando CSV como padrão.")
                formato = "csv"
                
            print("\nConsultando CNPJs... Isso pode demorar um pouco.")
            resultados, erros = consultor.processar_lista_cnpjs(cnpjs)
            
            if erros:
                print(f"\nForam encontrados {len(erros)} erros:")
                for erro in erros[:5]:  # Mostra apenas os 5 primeiros erros
                    print(f"- {erro}")
                if len(erros) > 5:
                    print(f"... e mais {len(erros) - 5} erros.")
                    
            consultor.salvar_resultados(resultados, formato)
            
        elif opcao == "2":
            cnpjs = []
            print("Digite os CNPJs (um por linha). Deixe em branco para finalizar:")
            
            while True:
                cnpj = input("> ")
                if not cnpj:
                    break
                cnpjs.append(cnpj)
                
            if not cnpjs:
                print("Nenhum CNPJ informado!")
                continue
                
            formato = input("Formato de saída (csv ou excel) [padrão: csv]: ").lower() or "csv"
            if formato not in ["csv", "excel"]:
                print("Formato inválido! Usando CSV como padrão.")
                formato = "csv"
                
            print("\nConsultando CNPJs... Isso pode demorar um pouco.")
            resultados, erros = consultor.processar_lista_cnpjs(cnpjs)
            
            if erros:
                print(f"\nForam encontrados {len(erros)} erros:")
                for erro in erros:
                    print(f"- {erro}")
                    
            consultor.salvar_resultados(resultados, formato)
            
        elif opcao == "3":
            try:
                quantidade = int(input("Quantos CNPJs deseja obter da API do PNCP? "))
                if quantidade <= 0:
                    print("A quantidade deve ser maior que zero!")
                    continue
                    
                print(f"Consultando API do PNCP para obter {quantidade} CNPJs de fornecedores...")
                cnpjs = consultor.obter_cnpjs_pncp(quantidade)
                
                if not cnpjs:
                    print("Não foi possível obter CNPJs da API do PNCP.")
                    continue
                    
                print(f"Foram obtidos {len(cnpjs)} CNPJs da API do PNCP.")
                
                formato = input("Formato de saída (csv ou excel) [padrão: csv]: ").lower() or "csv"
                if formato not in ["csv", "excel"]:
                    print("Formato inválido! Usando CSV como padrão.")
                    formato = "csv"
                    
                print("\nConsultando dados dos CNPJs... Isso pode demorar um pouco.")
                resultados, erros = consultor.processar_lista_cnpjs(cnpjs)
                
                if erros:
                    print(f"\nForam encontrados {len(erros)} erros:")
                    for erro in erros[:5]:
                        print(f"- {erro}")
                    if len(erros) > 5:
                        print(f"... e mais {len(erros) - 5} erros.")
                        
                consultor.salvar_resultados(resultados, formato)
            except ValueError:
                print("Por favor, digite um número válido.")
            
        elif opcao == "4":
            print("\nAtualização da base de dados")
            print("Este processo irá baixar e processar novamente os arquivos da Receita Federal.")
            print("Atenção: Estes arquivos são grandes e podem levar bastante tempo para baixar e processar.")
            resposta = input("Deseja continuar? (s/n): ")
            
            if resposta.lower() == 's':
                # Remove a base de dados existente
                if os.path.exists(consultor.dados_rf.db_path):
                    os.remove(consultor.dados_rf.db_path)
                    print("Base de dados removida.")
                    
                # Remove os diretórios extraídos (mantém os ZIPs)
                tipos_arquivos = ["Estabelecimentos", "Socios"]
                for tipo in tipos_arquivos:
                    # Encontra diretórios que começam com o tipo de arquivo
                    for item in os.listdir(consultor.dados_rf.data_dir):
                        item_path = os.path.join(consultor.dados_rf.data_dir, item)
                        if os.path.isdir(item_path) and item.startswith(tipo):
                            print(f"Removendo diretório: {item}")
                            shutil.rmtree(item_path)
                
                # Prepara a base novamente
                print("Iniciando preparação da nova base de dados...")
                consultor.dados_rf.preparar_base_dados()
            
        elif opcao == "5":
            print("Encerrando o programa...")
            break
            
        else:
            print("Opção inválida!")


if __name__ == "__main__":
    menu()