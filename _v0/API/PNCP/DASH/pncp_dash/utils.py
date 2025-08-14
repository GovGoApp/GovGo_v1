# utils.py
import pandas as pd
import requests
import re
import io
import locale
from datetime import datetime, date
from openai import OpenAI

# Flag global para controle de debug
DEBUG = True

def debug_print(*args, **kwargs):
    """Função auxiliar para prints condicionais de debug"""
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)

# Configuração da API da OpenAI - substitua pela sua chave real
client = OpenAI(
  #organization='org-2YkkE6qieHaCmPXsYoFecOsw',
  api_key = "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"  
)

# Configure locale para formatação de moeda
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # Fallback

# ===== Funções da API PNCP =====

def fetch_processos(data_inicial, data_final, codigo_modalidade, tamanho_pagina, ufs):
    """Busca processos da API do PNCP"""
    debug_print(f"Iniciando fetch_processos: data_inicial={data_inicial}, data_final={data_final}, modalidade={codigo_modalidade}, tamanho={tamanho_pagina}, ufs={ufs}")
    
    if not ufs:
        debug_print("ERRO: Nenhuma UF especificada")
        return [], "Nenhuma UF especificada para busca"
        
    base_url = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
    processos = []
    error_msg = None
    
    for uf in ufs:
        url_inicial = (f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
                       f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
                       f"&tamanhoPagina={tamanho_pagina}&pagina=1")
        
        debug_print(f"Consultando UF {uf}, URL: {url_inicial}")
        
        try:
            response_inicial = requests.get(url_inicial)
            response_inicial.raise_for_status()
            
            json_inicial = response_inicial.json()
            debug_print(f"Resposta inicial: {json_inicial.keys()}")
            
            # Processa a primeira página
            dados_inicial = json_inicial.get("data", [])
            processos.extend(dados_inicial)
            
            total_paginas = json_inicial.get("totalPaginas", 1)
            debug_print(f"UF {uf}: Total de páginas encontradas: {total_paginas}")
            
            # Processa páginas adicionais se houver
            for pagina in range(2, total_paginas + 1):
                url = (f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
                      f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
                      f"&tamanhoPagina={tamanho_pagina}&pagina={pagina}")
                
                debug_print(f"Buscando página {pagina}/{total_paginas} para UF {uf}")
                response = requests.get(url)
                response.raise_for_status()
                
                dados = response.json().get("data", [])
                debug_print(f"Página {pagina}: {len(dados)} processos encontrados")
                processos.extend(dados)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na consulta: {str(e)}"
            debug_print(f"ERRO ao consultar UF {uf}: {error_msg}")
    
    debug_print(f"Total de processos encontrados: {len(processos)}")
    return processos, error_msg

# Modificar a função fetch_documentos para adicionar mais logs detalhados

# Modificar a função fetch_documentos para adicionar mais logs detalhados

def fetch_documentos(cnpj, ano, sequencial):
    """Busca documentos de um processo específico"""
    debug_print(f"Iniciando fetch_documentos: cnpj={cnpj}, ano={ano}, sequencial={sequencial}")
    
    if not (cnpj and ano and sequencial):
        debug_print("Dados insuficientes para buscar documentos")
        return []
        
    base_url = "https://pncp.gov.br/api/pncp/v1"
    url = f"{base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    
    debug_print(f"Consultando documentos na URL: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        documentos = response.json()
        debug_print(f"Documentos encontrados: {len(documentos)}")
        
        if DEBUG and documentos:
            # Mostra alguns detalhes dos documentos encontrados
            debug_print("Primeiros documentos:")
            for i, doc in enumerate(documentos[:3]):  # Mostra até 3 documentos
                debug_print(f"  Doc {i+1}: {doc.get('titulo', 'Sem título')} - URL: {doc.get('url', 'N/D')}")
            if len(documentos) > 3:
                debug_print(f"  ... e mais {len(documentos)-3} documento(s)")
        
        return documentos
    except requests.exceptions.RequestException as e:
        debug_print(f"ERRO ao buscar documentos: {str(e)}")
        return []

# ===== Funções da API OpenAI =====

def generate_keywords(text):
    """Gera palavras-chave a partir de um texto usando a API da OpenAI"""
    debug_print(f"Iniciando generate_keywords com texto de {len(text) if text else 0} caracteres")
    
    if not text:
        debug_print("Texto vazio, retornando mensagem padrão")
        return "Texto não disponível"
        
    prompt = f"""
    Resuma o conteúdo a seguir em 5 a 10 tópicos de palavras-chave separados por ponto e vírgula, sem numeração.
    Comece com o título, o tipo e o propósito, e depois destaque os principais tópicos abordados.
    Use apenas palavras-chave. Limite: 200 caracteres.
    Texto: {text}
    Exemplo: "Edital; Pregão Eletrônico; Aquisição de Equipamentos; Especificações Técnicas; Critérios de Avaliação"
    """
    
    debug_print("Enviando requisição para API OpenAI (generate_keywords)")
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que resume textos em palavras-chave."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )
        keywords = completion.choices[0].message.content.strip()
        debug_print(f"Palavras-chave geradas: {keywords}")
        return keywords
    except Exception as e:
        error_msg = f"Erro ao gerar palavras-chave: {str(e)}"
        debug_print(f"ERRO OpenAI: {error_msg}")
        return error_msg

def summarize_document(doc_url):
    """Sumariza um documento a partir de sua URL usando a API da OpenAI"""
    debug_print(f"Iniciando summarize_document com URL: {doc_url}")
    
    if not doc_url or doc_url == "#":
        debug_print("URL inválida, retornando mensagem de erro")
        return "URL do documento inválida"
        
    prompt = f"Por favor, leia o conteúdo do documento disponível no seguinte link: {doc_url}. Resuma o conteúdo detalhadamente em tópicos e parágrafos, destacando os principais pontos."
    
    debug_print("Enviando requisição para API OpenAI (summarize_document)")
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que sumariza documentos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = completion.choices[0].message.content.strip()
        debug_print(f"Sumário gerado com {len(summary)} caracteres")
        
        # Log apenas do início do sumário para não poluir muito o console
        if DEBUG:
            preview = summary[:100] + "..." if len(summary) > 100 else summary
            debug_print(f"Preview do sumário: {preview}")
            
        return summary
    except Exception as e:
        error_msg = f"Erro ao sumarizar: {str(e)}"
        debug_print(f"ERRO OpenAI: {error_msg}")
        return error_msg
    
#  Função summarize_documentSS

def summarize_documents(documentos):
    """
    Recebe uma lista de documentos (dicionários com chave 'url'), baixa seus conteúdos,
    extrai arquivos ZIP se necessário, agrega os textos e gera um sumário via OpenAI.
    """
    import requests, zipfile, io

    aggregated_text = ""
    
    for doc in documentos:
        url = doc.get("url", "#")
        if not url or url == "#":
            continue
        try:
            response = requests.get(url)
            response.raise_for_status()
            content = response.content
            # Se for um arquivo ZIP, extrai os arquivos de texto
            if url.lower().endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(('.txt', '.csv', '.json', '.md')):
                            with z.open(filename) as f:
                                try:
                                    aggregated_text += f.read().decode('utf-8') + "\n"
                                except Exception as e:
                                    aggregated_text += f"\n[Erro ao ler {filename}: {str(e)}]\n"
            else:
                # Arquivo não ZIP: assume conteúdo textual
                aggregated_text += response.text + "\n"
        except Exception as e:
            aggregated_text += f"\n[Erro ao baixar {url}: {str(e)}]\n"
    
    if not aggregated_text.strip():
        return "Nenhum conteúdo válido encontrado para sumarização."

    # Cria um arquivo em memória com o conteúdo agregado
    file_like = io.BytesIO(aggregated_text.encode('utf-8'))
    
    # Faz o upload do arquivo usando a API de arquivos da OpenAI
    try:
        upload_response = client.File.create(
            file=file_like,
            purpose="answers"  # Utilize o propósito adequado conforme sua aplicação
        )
        file_id = upload_response.get("id", "")
        debug_print(f"Arquivo enviado com sucesso. File ID: {file_id}")
    except Exception as e:
        debug_print(f"Erro no upload do arquivo: {str(e)}")
        # Se o upload falhar, podemos continuar com o conteúdo local
        file_id = ""
    
    # Cria o prompt para sumarização utilizando o conteúdo agregado
    prompt = f"Leia o conteúdo agregado dos documentos abaixo e gere um sumário detalhado destacando os principais pontos:\n\n{aggregated_text}"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que sumariza documentos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = completion.choices[0].message.content.strip()
        debug_print(f"Sumário gerado com {len(summary)} caracteres")
        return summary
    except Exception as e:
        error_msg = f"Erro ao sumarizar documentos: {str(e)}"
        debug_print(error_msg)
        return error_msg


# ===== Funções de Processamento de Dados =====

def clean_illegal_chars(s):
    """Remove caracteres ilegais de strings"""
    if isinstance(s, str):
        return re.sub(r'[\x00-\x1F]+', ' ', s)
    return s

def process_data(processos):
    """Processa os dados brutos da API do PNCP"""
    debug_print(f"Iniciando process_data com {len(processos) if processos else 0} processos")
    
    if not processos:
        debug_print("Nenhum processo para processar")
        return pd.DataFrame()
        
    df = pd.json_normalize(processos)
    debug_print(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
    
    # Renomeação e tratamento de colunas
    if 'objetoCompra' in df.columns:
        df.rename(columns={'objetoCompra': 'objeto'}, inplace=True)
        debug_print("Coluna 'objetoCompra' renomeada para 'objeto'")
        
    # Conversão de tipos
    if 'valorTotalEstimado' in df.columns:
        df['valorTotalEstimado'] = pd.to_numeric(df['valorTotalEstimado'], errors='coerce')
        debug_print("Coluna 'valorTotalEstimado' convertida para numérico")
        
    # Conversão de datas
    date_columns = ['dataAberturaProposta', 'dataInclusao', 'dataEncerramentoProposta']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
            debug_print(f"Coluna '{col}' convertida para datetime")
    
    # Limpeza de caracteres ilegais
    text_columns = df.select_dtypes(include='object').columns
    debug_print(f"Limpando caracteres ilegais em {len(text_columns)} colunas de texto")
    for col in text_columns:
        df[col] = df[col].apply(clean_illegal_chars)
    
    return df

def format_keywords(keywords_str):
    """Formata palavras-chave como chips HTML"""
    if not keywords_str:
        return []
    
    keywords = [kw.strip() for kw in keywords_str.split(";") if kw.strip()]
    debug_print(f"Formatadas {len(keywords)} palavras-chave a partir da string")
    return keywords

def to_excel(df_all, df_filtered=None):
    """Exporta dados para Excel"""
    debug_print(f"Iniciando exportação para Excel: {len(df_all)} registros totais, {len(df_filtered) if df_filtered is not None else 0} filtrados")
    
    if df_filtered is None:
        df_filtered = df_all
        
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_all.to_excel(writer, sheet_name='Todos', index=False)
            df_filtered.to_excel(writer, sheet_name='Filtrados', index=False)
        
        processed_data = output.getvalue()
        debug_print(f"Excel gerado com sucesso: {len(processed_data)} bytes")
        return processed_data
    except Exception as e:
        debug_print(f"ERRO ao gerar Excel: {str(e)}")
        raise

def get_excel_filename():
    """Gera nome de arquivo para exportação"""
    filename = f"licitacoes_{datetime.now().strftime('%Y%m%d')}.xlsx"
    debug_print(f"Nome de arquivo gerado: {filename}")
    return filename

# ===== Dados de Referência =====

def get_modalidades():
    """Retorna dicionário de modalidades de contratação"""
    return {
        "1 - Leilão - Eletrônico": 1,
        "2 - Diálogo Competitivo": 2,
        "3 - Concurso": 3,
        "4 - Concorrência - Eletrônica": 4,
        "5 - Concorrência - Presencial": 5,
        "6 - Pregão - Eletrônico": 6,
        "7 - Pregão - Presencial": 7,
        "8 - Dispensa de Licitação": 8,
        "9 - Inexigibilidade": 9,
        "10 - Manifestação de Interesse": 10,
        "11 - Pré-qualificação": 11,
        "12 - Credenciamento": 12,
        "13 - Leilão - Presencial": 13
    }

def get_ufs_brasil():
    """Retorna dicionário de UFs do Brasil"""
    return {
        "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", 
        "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", 
        "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", 
        "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", 
        "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", 
        "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", 
        "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", 
        "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"
    }