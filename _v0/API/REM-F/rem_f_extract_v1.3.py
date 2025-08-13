import os
from bs4 import BeautifulSoup

# Mapeamento dos campos a serem extraídos com suas estratégias específicas
fields = {
    # Dados Gerais
    "Municipio": {"type": "title"},
    "UF": {"type": "state-label"},
    "Populacao": {"type": "info-value", "label": "População"},
    "Area": {"type": "info-value", "label": "Área"},
    "Ranking_Geral": {"type": "ranking-label"},
    "Eficiencia": {"type": "efficiency-label"},
    "Valor_Ranking": {"type": "rem-label-lg"},
    
    # Educação
    "Educacao_REM": {"type": "section-value", "label": "REM", "section": "Educação"},
    "Criancas_4_5": {"type": "section-value", "label": "Crianças de 4 e 5 anos na escola"},
    "Criancas_0_3": {"type": "section-value", "label": "Crianças de 0 a 3 anos na creche"},
    
    # Saúde
    "Saude_REM": {"type": "section-value", "label": "REM", "section": "Saúde"},
    "Atencao_basica": {"type": "section-value", "label": "Domicílios cobertos por atenção básica"},
    "Medicos_por_1000": {"type": "text-value", "label": "Médicos por 1.000 habitantes"},
    
    # Saneamento
    "Saneamento_REM": {"type": "section-value", "label": "REM", "section": "Saneamento"},
    "Atendimento_agua": {"type": "section-value", "label": "Atendimento de água"},
    "Cobertura_esgoto": {"type": "section-value", "label": "Cobertura de esgoto"},
    "Coleta_lixo": {"type": "section-value", "label": "Coleta de lixo"},
    
    # Receita
    "Receita_REM": {"type": "section-value", "label": "REM", "section": "Receita"},
    "Receita_per_capita": {"type": "text-value", "label": "Receita per capita"},
    "Receita_total": {"type": "text-value", "label": "Receita"},
    "PIB": {"type": "text-value", "label": "PIB"},
    "Receita_transferencias": {"type": "section-value", "label": "Receita de transferências"},
    "Despesas_educacao": {"type": "section-value", "label": "Despesas com educação"},
    "Despesas_saude": {"type": "section-value", "label": "Despesas com saúde"},
    "Despesas_legislativo": {"type": "section-value", "label": "Despesas com o Legislativo"},
    "Servidores_publicos": {"type": "text-value", "label": "Servidores públicos"},
    "Variacao_servidores": {"type": "section-value", "label": "Variação de servidores públicos entre 2015 e 2021"},
}

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
        
        # Itera sobre cada campo e extrai o valor usando a estratégia apropriada
        for key, info in fields.items():
            extraction_type = info["type"]
            
            if extraction_type == "title":
                # Extrai o nome do município do título
                title_elem = soup.find("h1", class_="title")
                if title_elem:
                    data[key] = title_elem.get_text(strip=True)
            
            elif extraction_type == "state-label":
                # Extrai o UF do rótulo de estado
                state_elem = soup.find("p", class_="state-label")
                if state_elem:
                    data[key] = state_elem.get_text(strip=True)
            
            elif extraction_type == "info-value":
                # Extrai valores do raio-x da cidade
                label_text = info["label"]
                for item in soup.find_all("div", class_="city-info-item"):
                    label_elem = item.find("p", class_="info-label")
                    if label_elem and label_text in label_elem.get_text(strip=True):
                        value_elem = item.find("p", class_="info-value")
                        if value_elem:
                            data[key] = value_elem.get_text(strip=True)
                            break
            
            elif extraction_type == "ranking-label":
                # Extrai o ranking geral
                ranking_elem = soup.find("p", class_="ranking-label")
                if ranking_elem:
                    # Remove o º e obtém apenas o número
                    ranking_text = ranking_elem.get_text(strip=True)
                    data[key] = ranking_text.replace("º", "")
            
            elif extraction_type == "efficiency-label":
                # Extrai a eficiência
                efficiency_elem = soup.find("p", class_="efficiency-label")
                if efficiency_elem:
                    data[key] = efficiency_elem.get_text(strip=True)
            
            elif extraction_type == "rem-label-lg":
                # Extrai o valor do ranking do atributo aria-label
                rem_elem = soup.find("p", class_="rem-label-lg")
                if rem_elem and rem_elem.get("aria-label"):
                    aria_label = rem_elem.get("aria-label")
                    # Extrai o número da string "Valor do ranking: X.XXX"
                    if "Valor do ranking:" in aria_label:
                        value = aria_label.split("Valor do ranking:")[1].strip()
                        data[key] = value
            
            elif extraction_type == "text-value":
                # Extrai valores de texto de indicadores específicos
                label_text = info["label"]
                for row in soup.find_all("div", class_="section-row"):
                    label_elem = row.select_one("div.labels p.label")
                    if label_elem and label_elem.get_text(strip=True) == label_text:
                        text_elem = row.find("p", class_="text-value")
                        if text_elem:
                            data[key] = text_elem.get_text(strip=True)
                            break
            
            elif extraction_type == "section-value":
                # Extrai valores de seções específicas
                label_text = info["label"]
                section_name = info.get("section", None)  # Opcional para REM que aparece em várias seções
                
                # Tratamento especial para Variacao_servidores
                if key == "Variacao_servidores":
                    for row in soup.find_all("div", class_="section-row"):
                        label_elem = row.select_one("div.labels p.label")
                        if label_elem and "Variação de servidores públicos" in label_elem.get_text(strip=True):
                            container_div = row.select_one("div.values-container div.value-item div.container")
                            if container_div:
                                label_div = container_div.find("div", class_="label")
                                if label_div:
                                    data[key] = label_div.get_text(strip=True)
                                    break
                    continue
                
                # Para todos os outros campos section-value
                for row in soup.find_all("div", class_="section-row"):
                    label_elem = row.select_one("div.labels p.label")
                    if label_elem and label_elem.get_text(strip=True) == label_text:
                        # Se especificamos uma seção, verificamos se estamos na seção correta
                        if section_name and label_text == "REM":
                            # Encontra a seção atual
                            section_header = row.find_previous("header", class_="section-header")
                            if section_header:
                                section_title = section_header.find("h2", class_="title")
                                if section_title and section_title.get_text(strip=True) == section_name:
                                    pass
                                else:
                                    continue  # Pula esta row se não está na seção desejada
                            else:
                                continue  # Pula se não conseguir determinar a seção
                        
                        # Verifica vários tipos possíveis de valores
                        values_container = row.find("div", class_="values-container")
                        if values_container:
                            # Tenta encontrar valor em p.rem
                            rem_elem = values_container.select_one("div p.rem")
                            if rem_elem:
                                data[key] = rem_elem.get_text(strip=True)
                                continue
                            
                            # Tenta encontrar valor em div.label
                            value_div = values_container.find("div", attrs={"data-v-26eb1dc1": True})
                            if value_div:
                                label_div = value_div.find("div", class_="label")
                                if label_div:
                                    data[key] = label_div.get_text(strip=True)
                                    continue
                            
                            # Tenta encontrar valor em text-value
                            text_elem = values_container.find("p", class_="text-value")
                            if text_elem:
                                data[key] = text_elem.get_text(strip=True)
                                continue
                
    except Exception as e:
        print(f"Erro ao processar o arquivo {file_path}: {e}")
    
    return data

if __name__ == "__main__":
    # Defina o caminho completo para a página local
    path = "C:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\#XERXES\\API\\REM-F\\"
    file = "Santa Cruz da Vitória (BA) é 123ª cidade mais eficiente em ranking Folha.html"
    # Extrai os dados da página local
    extracted_data = extract_local_page_data(path + file)
    
    # Exibe os dados extraídos
    for key, value in extracted_data.items():
        print(f"{key}: {value}")