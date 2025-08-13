import os
from bs4 import BeautifulSoup

# Mapeamento dos campos a serem extraídos:
fields = {
    # Dados Gerais (supondo que os labels sejam exatamente esses)
    "Municipio": {"label": "Município", "occurrence": 1},
    "UF": {"label": "UF", "occurrence": 1},
    "Populacao": {"label": "População", "occurrence": 1},
    "Area": {"label": "Área (km²)", "occurrence": 1},
    # Educação
    "Educacao_REM": {"label": "REM", "occurrence": 1},
    "Criancas_4_5": {"label": "Crianças de 4 e 5 anos na escola", "occurrence": 1},
    "Criancas_0_3": {"label": "Crianças de 0 a 3 anos na creche", "occurrence": 1},
    # Saúde
    "Saude_REM": {"label": "REM", "occurrence": 2},
    "Atencao_basica": {"label": "Domicílios cobertos por atenção básica", "occurrence": 1},
    "Medicos_por_1000": {"label": "Médicos por 1.000 habitantes", "occurrence": 1},
    # Saneamento
    "Saneamento_REM": {"label": "REM", "occurrence": 3},
    "Atendimento_agua": {"label": "Atendimento de água", "occurrence": 1},
    "Cobertura_esgoto": {"label": "Cobertura de esgoto", "occurrence": 1},
    "Coleta_lixo": {"label": "Coleta de lixo", "occurrence": 1},
    # Receita
    "Receita_REM": {"label": "REM", "occurrence": 4},
    "Receita_per_capita": {"label": "Receita per capita", "occurrence": 1},
    "Receita_total": {"label": "Receita", "occurrence": 1},
    "PIB": {"label": "PIB", "occurrence": 1},
    "Receita_transferencias": {"label": "Receita de transferências", "occurrence": 1},
    "Despesas_educacao": {"label": "Despesas com educação", "occurrence": 1},
    "Despesas_saude": {"label": "Despesas com saúde", "occurrence": 1},
    "Despesas_legislativo": {"label": "Despesas com o Legislativo", "occurrence": 1},
    "Servidores_publicos": {"label": "Servidores públicos", "occurrence": 1},
    "Variacao_servidores": {"label": "Variação de servidores públicos entre 2015 e 2021", "occurrence": 1},
}

def get_indicator_value(soup, label_text, occurrence=1):
    """
    Procura por todos os elementos <p class="label" data-v-c1a430e0=""> que contenham o texto exato do indicador.
    A partir do elemento encontrado, tenta extrair o valor:
      - Primeiro, procura um <p class="rem"> imediatamente após o label.
      - Se não encontrar, busca o próximo elemento <div> com atributo data-v-26eb1dc1
        e extrai o valor do <div class="label" data-v-26eb1dc1>.
    Retorna o valor extraído ou None se não encontrado.
    """
    labels = soup.find_all("p", class_="label", attrs={"data-v-c1a430e0": True})
    matching = [tag for tag in labels if tag.get_text(strip=True) == label_text]
    if len(matching) >= occurrence:
        target_label = matching[occurrence - 1]
        # Tenta extrair valor em <p class="rem">
        next_rem = target_label.find_next_sibling("p", class_="rem")
        if next_rem:
            return next_rem.get_text(strip=True)
        # Se não encontrou, tenta extrair valor em container com data-v-26eb1dc1
        next_div = target_label.find_next_sibling("div", attrs={"data-v-26eb1dc1": True})
        if next_div:
            inner_label = next_div.find("div", class_="label", attrs={"data-v-26eb1dc1": True})
            if inner_label:
                return inner_label.get_text(strip=True)
    return None

def extract_local_page_data(file_path):
    """
    Lê o arquivo HTML local e extrai os dados conforme os campos definidos.
    Retorna um dicionário com os dados extraídos.
    """
    data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
        # Itera sobre cada campo e extrai o valor usando o label e a ocorrência definida
        for key, info in fields.items():
            label = info["label"]
            occurrence = info.get("occurrence", 1)
            value = get_indicator_value(soup, label, occurrence)
            data[key] = value
    except Exception as e:
        print(f"Erro ao processar o arquivo {file_path}: {e}")
    return data

if __name__ == "__main__":
    # Defina o caminho completo para a página local
    file_path = r"C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#XERXES\API\REM-F\Botucatu (SP) é 1ª cidade mais eficiente em ranking Folha.html"
    
    # Extrai os dados da página local
    extracted_data = extract_local_page_data(file_path)
    
    # Exibe os dados extraídos
    for key, value in extracted_data.items():
        print(f"{key}: {value}")
