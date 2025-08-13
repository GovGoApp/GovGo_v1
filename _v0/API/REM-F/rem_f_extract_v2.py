import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from tqdm import tqdm
import random

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

def extract_data_from_html(html_content):
    """
    Extrai os dados do conteúdo HTML.
    Retorna um dicionário com os dados extraídos.
    """
    data = {}
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
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
        print(f"Erro ao processar o HTML: {e}")
    
    return data

def fetch_municipality_data(rank):
    """
    Busca os dados do município com o ranking especificado.
    Retorna um dicionário com os dados extraídos ou None em caso de erro.
    """
    url = f"https://www1.folha.uol.com.br/remf/municipio/{rank}/"
    
    try:
        # Configura cabeçalhos para simular um navegador
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www1.folha.uol.com.br/remf/"
        }
        
        # Faz a requisição HTTP
        response = requests.get(url, headers=headers, timeout=30)
        
        # Se a requisição foi bem-sucedida, extrai os dados
        if response.status_code == 200:
            data = extract_data_from_html(response.content)
            # Adiciona o ranking original
            data["Original_Rank"] = rank
            return data
        else:
            print(f"Erro ao acessar município de ranking {rank}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro ao acessar município de ranking {rank}: {e}")
        return None

def save_to_excel(df, path):
    """
    Salva o DataFrame em um arquivo Excel.
    """
    try:
        df.to_excel(path, index=False, engine='openpyxl')
        print(f"Dados salvos em {path}")
    except Exception as e:
        print(f"Erro ao salvar arquivo Excel: {e}")

def main():
    """
    Função principal que coordena a extração de dados de todos os municípios.
    """
    # Caminho para salvar o arquivo Excel
    output_path = r"C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#XERXES\API\REM-F\remf_municipios.xlsx"
    
    # Cria um DataFrame vazio para armazenar os dados
    all_data = pd.DataFrame()
    
    # Define o intervalo de rankings a serem processados
    start_rank = 1
    end_rank = 5276
    
    # Contador para saber quando salvar o arquivo (a cada 100 páginas)
    save_counter = 0
    
    # Configuração da barra de progresso
    pbar = tqdm(range(start_rank, end_rank + 1), desc="Extraindo dados", unit="município")
    
    try:
        for rank in pbar:
            # Atualiza a barra de progresso com o município atual
            pbar.set_description(f"Processando município {rank}/{end_rank}")
            
            # Busca os dados do município
            municipality_data = fetch_municipality_data(rank)
            
            # Se os dados foram extraídos com sucesso
            if municipality_data:
                # Adiciona os dados ao DataFrame
                new_row = pd.DataFrame([municipality_data])
                all_data = pd.concat([all_data, new_row], ignore_index=True)
                
                # Incrementa o contador de salvamento
                save_counter += 1
                
                # Salva o arquivo a cada 100 municípios processados
                if save_counter % 100 == 0:
                    save_to_excel(all_data, output_path)
                    print(f"Progresso: {save_counter}/{end_rank} municípios processados.")
            
            # Adiciona um atraso aleatório entre as requisições para evitar sobrecarga no servidor
            time.sleep(random.uniform(0.5, 2.0))
        
        # Salva o arquivo final
        save_to_excel(all_data, output_path)
        print(f"Extração concluída! Total de {len(all_data)} municípios processados.")
        
    except KeyboardInterrupt:
        # Se o usuário interromper o processo, salva os dados coletados até o momento
        print("Processo interrompido pelo usuário.")
        if not all_data.empty:
            save_to_excel(all_data, output_path)
            print(f"Dados parciais salvos em {output_path}")
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        if not all_data.empty:
            save_to_excel(all_data, output_path)
            print(f"Dados parciais salvos em {output_path}")

if __name__ == "__main__":
    main()