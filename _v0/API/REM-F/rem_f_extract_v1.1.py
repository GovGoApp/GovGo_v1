
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
    Procura por todos os elementos <p class="label"> que contenham o texto exato do indicador.
    Considera a estrutura complexa da página e busca o valor associado.
    """
    # Encontra todas as section-row que podem conter os dados
    section_rows = soup.find_all("div", class_="section-row")
    
    # Contador para rastrear ocorrências do label
    occurrence_count = 0
    
    for row in section_rows:
        # Procura pelo label dentro do container de labels
        label_elem = row.select_one("div.labels p.label")
        
        # Se o elemento existe e contém o texto que procuramos
        if label_elem and label_elem.get_text(strip=True) == label_text:
            occurrence_count += 1
            
            # Se é a ocorrência que procuramos
            if occurrence_count == occurrence:
                # Tenta encontrar o valor na estrutura values-container > div > p.rem
                values_container = row.find("div", class_="values-container")
                if values_container:
                    rem_elem = values_container.select_one("div p.rem")
                    if rem_elem:
                        return rem_elem.get_text(strip=True)
                    
                    # Se não encontrou rem, procura por outros containers com dados
                    value_div = values_container.find("div", attrs={"data-v-26eb1dc1": True})
                    if value_div:
                        label_div = value_div.find("div", class_="label")
                        if label_div:
                            return label_div.get_text(strip=True)
    
    # Tentar uma abordagem alternativa para REM, que aparece em um formato diferente
    if label_text == "REM":
        rem_elements = soup.find_all("p", class_="rem")
        rem_count = 0
        
        for rem in rem_elements:
            rem_count += 1
            if rem_count == occurrence:
                return rem.get_text(strip=True)
    
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

