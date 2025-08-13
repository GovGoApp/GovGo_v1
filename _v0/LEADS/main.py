import requests
from bs4 import BeautifulSoup
import csv
import time
from datetime import datetime
import re
import random
import os
import concurrent.futures


def clean_text(text):
    """
    Remove excess spaces and linebreaks from a string.

    Args:
        text (str): The input string to clean

    Returns:
        str: Cleaned string with no excess whitespace
    """
    if not text:
        return text

    # Replace multiple spaces with a single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with a single newline
    text = re.sub(r"\n+", "", text)

    # Remove leading and trailing whitespace
    text = text.strip()

    return text


def obter_cnpjs_pncp(quantidade, data_inicial, data_final):
    """
    Obtém uma lista de CNPJs a partir da API do PNCP.

    Args:
        quantidade (int): Quantidade máxima de CNPJs a retornar (0 para buscar todos disponíveis)
        data_inicial (str): Data inicial no formato 'YYYYMMDD'
        data_final (str): Data final no formato 'YYYYMMDD'

    Returns:
        list: Lista de CNPJs
    """
    url = "https://pncp.gov.br/api/consulta/v1/contratos"
    cnpjs = []
    pagina = 1
    tamanho_pagina = 100  # Máximo permitido pela API
    sem_limite = quantidade <= 0  # Flag para buscar todos os disponíveis

    while sem_limite or len(cnpjs) < quantidade:
        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
        }

        try:
            print(f"Consultando página {pagina}...")
            response = requests.get(url, params=params)
            response.raise_for_status()

            response_json = response.json()
            data = response_json.get("data")

            if not data or len(data) == 0:
                print("Não há mais resultados disponíveis.")
                break

            # Extrair CNPJs (niFornecedor) dos contratos
            for contrato in data:
                if "niFornecedor" in contrato and contrato["niFornecedor"] not in cnpjs:
                    cnpjs.append(contrato["niFornecedor"])
                    if not sem_limite and len(cnpjs) >= quantidade:
                        break

            print(f"Encontrados {len(cnpjs)} CNPJs até o momento.")
            pagina += 1
            time.sleep(0.5)  # Pausa para não sobrecarregar a API

        except Exception as e:
            print(f"Erro ao obter dados da API PNCP: {e}")
            break

    return cnpjs if sem_limite else cnpjs[:quantidade]


def obter_contatos_transp(cnpjs, max_workers=7):
    """
    Obtém dados de contato para cada CNPJ da lista através de scraping do site portaldatransparencia.gov.br
    usando processamento paralelo para maior velocidade.

    Args:
        cnpjs (list): Lista de CNPJs

    Returns:
        list: Lista de dicionários com dados de contato
    """
    total = len(cnpjs)

    # Função para processar um único CNPJ
    def processar_cnpj(idx_cnpj):
        i, cnpj = idx_cnpj
        print(f"Obtendo dados para CNPJ {i}/{total}: {cnpj}")
        url = f"https://portaldatransparencia.gov.br/pessoa-juridica/{cnpj}"

        try:
            # Adicionar user-agent para evitar bloqueios
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Inicializar dicionário para armazenar os dados
            contato = {"cnpj": cnpj}

            # Mapeamento dos textos nos elementos strong para as chaves no dicionário contato
            mapeamento_campos = {
                "Nome empresarial": "nome_emp",
                "Nome de fantasia": "nome_fan",
                "CNAE": "cnae",
                "Telefone": "telefone",
                "Endereço eletrônico": "email",
            }

            # Extrair dados simples
            for elemento in soup.select("strong"):
                for texto_chave, nome_campo in mapeamento_campos.items():
                    if texto_chave in elemento.text:
                        next_el = elemento.find_next_sibling()
                        if next_el:
                            contato[nome_campo] = next_el.text.strip()
                            break

            # Extrair endereço
            for elemento in soup.select("strong"):
                if "Logradouro" in elemento.text:
                    logradouro = elemento.find_next_sibling().text.strip()
                elif "Número" in elemento.text:
                    numero = elemento.find_next_sibling().text.strip()
                elif "Complemento" in elemento.text:
                    complemento = elemento.find_next_sibling().text.strip()
                elif "CEP" in elemento.text:
                    cep = elemento.find_next_sibling().text.strip()
                elif "Bairro/Distrito" in elemento.text:
                    bairro_distrito = elemento.find_next_sibling().text.strip()
                elif "Município" in elemento.text:
                    municipio = elemento.find_next_sibling().text.strip()
                elif "UF" in elemento.text:
                    uf = elemento.find_next_sibling().text.strip()

            # Montar o endereço completo
            contato["endereco"] = clean_text(
                f"{logradouro}, {numero} {complemento}, {bairro_distrito}, {cep} {municipio}/{uf}"
            )

            # Extrair sócios
            for elemento in soup.select("caption"):
                if "Quadro Societário" in elemento.text:
                    tbody = elemento.find_next_sibling("tbody")
                    if tbody:
                        contato["socios"] = clean_text(tbody.text)
                        break

            return contato

        except Exception as e:
            print(f"Erro ao obter dados para o CNPJ {cnpj}: {e}")
            return {"cnpj": cnpj, "erro": str(e)}

    # Usar ThreadPoolExecutor para processar CNPJs em paralelo
    contatos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers) as executor:
        # Criar lista de tuplas (índice, cnpj) para manter a numeração correta
        indexed_cnpjs = list(enumerate(cnpjs, 1))
        # Processar em paralelo
        resultados = list(executor.map(processar_cnpj, indexed_cnpjs))

    # Adicionar resultados à lista de contatos
    contatos = [r for r in resultados if r]

    return contatos


def exportar_contatos(contatos, nome_arquivo=None):
    """
    Exporta a lista de contatos para um arquivo CSV.

    Args:
        contatos (list): Lista de dicionários com dados de contato
        nome_arquivo (str, optional): Nome do arquivo CSV

    Returns:
        str: Caminho do arquivo criado
    """
    if not contatos:
        print("Nenhum contato para exportar.")
        return None

    # Gerar nome de arquivo com timestamp se não foi especificado
    if nome_arquivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"contatos_cnpj_{timestamp}.csv"

    # Criar pasta export se não existir
    export_folder = "export"
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)
        print(f"Pasta '{export_folder}' criada com sucesso.")

    # Caminho completo do arquivo
    caminho_arquivo = os.path.join(export_folder, nome_arquivo)

    # Determinar a ordem das colunas de forma dinâmica
    colunas = []
    for contato in contatos:
        for chave in contato:
            if chave not in colunas:
                colunas.append(chave)

    try:
        with open(caminho_arquivo, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(contatos)

        print(f"Contatos exportados com sucesso para {caminho_arquivo}")
        return caminho_arquivo

    except Exception as e:
        print(f"Erro ao exportar contatos para CSV: {e}")
        return None


def main():
    """
    Função principal que coordena o fluxo do programa.
    """
    print("=== Extrator de Contatos PNCP e CNPJ.biz ===")

    # Solicitar parâmetros de entrada
    try:
        quantidade_input = input("Digite a quantidade máxima de CNPJs a obter (0 para buscar todos disponíveis): ")
        quantidade = int(quantidade_input)
    except ValueError:
        print("Entrada inválida. Usando valor padrão 0 (todos disponíveis).")
        quantidade = 0
    
    data_inicial = input("Digite a data inicial (YYYYMMDD): ")
    data_final = input("Digite a data final (YYYYMMDD): ")

    # 1. Obter CNPJs do PNCP
    if quantidade > 0:
        print(f"\nObtendo até {quantidade} CNPJs do PNCP...")
    else:
        print("\nObtendo todos os CNPJs disponíveis do PNCP...")
        
    cnpjs = obter_cnpjs_pncp(quantidade, data_inicial, data_final)
    print(f"Foram obtidos {len(cnpjs)} CNPJs.")

    # 2. Obter dados de contato para os CNPJs
    print("\nObtendo dados de contato para os CNPJs...")
    contatos = obter_contatos_transp(cnpjs)
    print(f"Foram obtidos dados para {len(contatos)} CNPJs.")

    # 3. Exportar para CSV
    print("\nExportando contatos para CSV...")
    exportar_contatos(contatos)

    print("\nProcesso concluído!")


if __name__ == "__main__":
    main()
