"""
gvg_document_utils_v2.py
Módulo para processamento de documentos PNCP usando MarkItDown
- Download de documentos do PNCP
- Conversão para Markdown usando MarkItDown
- Integração com OpenAI para processamento de imagens
- Sumarização automática dos documentos convertidos
- Organização e persistência dos arquivos processados
"""

import os
import sys
import requests
import tempfile
import warnings
import unicodedata
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from openai import OpenAI

# Suprimir warnings específicos do PyDub/FFmpeg e pdfminer
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv.*", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*color because.*is an invalid float value", category=UserWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*", category=UserWarning)
warnings.filterwarnings("ignore", module="pdfminer.pdfinterp")
warnings.filterwarnings("ignore", module="pdfminer")
warnings.filterwarnings("ignore", category=UserWarning, module="pdfminer.*")

# Suprimir logs do pdfminer também
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)

# Configurações
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\Terminal\\"
FILE_PATH = BASE_PATH + "Arquivos\\"
SUMMARY_PATH = BASE_PATH + "Resumos\\"
OPENAI_ENV_FILE = "openai.env"
MAX_TOKENS = 2000 # Número máximo de tokens para o resumo

def load_openai_config():
    """Carrega configuração OpenAI do arquivo .env"""
    config = {}
    if os.path.exists(OPENAI_ENV_FILE):
        with open(OPENAI_ENV_FILE, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

def setup_openai():
    """Configura cliente OpenAI se disponível"""
    try:
        config = load_openai_config()
        
        if 'api_key' in config:
            os.environ['OPENAI_API_KEY'] = config['api_key']
            client = OpenAI(api_key=config['api_key'])
            return client
        else:
            return None
            
    except ImportError:
        return None
    except Exception as e:
        return None

def get_markitdown_instance():
    """Cria instância MarkItDown com ou sem OpenAI"""
    try:
        from markitdown import MarkItDown
        
        openai_client = setup_openai()
        
        if openai_client:
            return MarkItDown(
                llm_client=openai_client, 
                llm_model="gpt-4o",
                enable_plugins=True
            )
        else:
            return MarkItDown(enable_plugins=True)
    except ImportError:
        raise ImportError("MarkItDown não está instalado. Instale com: pip install 'markitdown[all]'")

def create_files_directory():
    """Cria diretórios de arquivos e resumos se não existirem"""
    if not os.path.exists(FILE_PATH):
        os.makedirs(FILE_PATH)
    if not os.path.exists(SUMMARY_PATH):
        os.makedirs(SUMMARY_PATH)

def download_document(doc_url, timeout=30):
    """
    Baixa um documento da URL fornecida
    
    Args:
        doc_url (str): URL do documento
        timeout (int): Timeout para download
        
    Returns:
        tuple: (sucesso, caminho_arquivo_temporario, nome_arquivo, erro)
    """
    try:
        if not doc_url or not doc_url.strip():
            return False, None, None, "URL não fornecida"
        
        if not doc_url.startswith(('http://', 'https://')):
            return False, None, None, "URL inválida"
        
        # Fazer requisição
        response = requests.get(doc_url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Extrair nome do arquivo da URL
        parsed_url = urlparse(doc_url)
        filename = os.path.basename(parsed_url.path)
        
        # Se não conseguir extrair nome, usar um padrão baseado no content-type
        if not filename or '.' not in filename:
            content_type = response.headers.get('content-type', '').lower()
            content_disposition = response.headers.get('content-disposition', '').lower()
            
            # Tentar extrair extensão do content-disposition
            if 'filename=' in content_disposition:
                try:
                    cd_filename = content_disposition.split('filename=')[1].strip('"\'')
                    if '.' in cd_filename:
                        filename = cd_filename
                except:
                    pass
            
            # Se ainda não temos nome, usar content-type
            if not filename or '.' not in filename:
                if 'pdf' in content_type:
                    filename = "documento.pdf"
                elif 'zip' in content_type or 'compressed' in content_type:
                    filename = "documento.zip"
                elif 'word' in content_type or 'msword' in content_type:
                    filename = "documento.docx"
                elif 'excel' in content_type or 'spreadsheet' in content_type:
                    filename = "documento.xlsx"
                elif 'text' in content_type:
                    filename = "documento.txt"
                elif 'xml' in content_type:
                    filename = "documento.xml"
                elif 'json' in content_type:
                    filename = "documento.json"
                else:
                    # Usar extensão temporária que será detectada depois
                    filename = "documento_temporario"
        
        # Criar arquivo temporário
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"pncp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        
        # Salvar arquivo
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Se o arquivo não tinha extensão, tentar detectar pelo conteúdo
        if filename == "documento_temporario":
            filename = detect_file_type_by_content_v2(temp_path)
            if filename != "documento_temporario":
                # Renomear arquivo com extensão correta
                new_temp_path = os.path.join(temp_dir, f"pncp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
                os.rename(temp_path, new_temp_path)
                temp_path = new_temp_path
        
        return True, temp_path, filename, None
        
    except requests.exceptions.RequestException as e:
        return False, None, None, f"Erro de conexão: {str(e)}"
    except Exception as e:
        return False, None, None, f"Erro inesperado: {str(e)}"

def convert_document_to_markdown(file_path, original_filename):
    """
    Converte um documento para Markdown usando MarkItDown
    
    Args:
        file_path (str): Caminho do arquivo
        original_filename (str): Nome original do arquivo
        
    Returns:
        tuple: (sucesso, conteudo_markdown, erro)
    """
    try:
        md_converter = get_markitdown_instance()
        
        # Conversão
        result = md_converter.convert(file_path)
        
        # Preparar conteúdo com metadados
        file_info = os.stat(file_path)
        size_mb = file_info.st_size / (1024 * 1024)
        
        markdown_content = f"""# Documento PNCP: {original_filename}

**Arquivo original:** `{original_filename}`  
**Tamanho:** {size_mb:.2f} MB  
**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Ferramenta:** MarkItDown + OpenAI GPT-4o  

---

{result.text_content}
"""
        
        return True, markdown_content, None
        
    except Exception as e:
        return False, None, f"Erro na conversão: {str(e)}"

def save_markdown_file(content, original_filename, doc_url, timestamp=None):
    """
    Salva o conteúdo Markdown em arquivo
    
    Args:
        content (str): Conteúdo Markdown
        original_filename (str): Nome do arquivo original
        doc_url (str): URL original do documento
        timestamp (str): Timestamp para nome único (opcional)
        
    Returns:
        tuple: (sucesso, caminho_arquivo_salvo, erro)
    """
    try:
        create_files_directory()
        
        # Usar timestamp fornecido ou gerar novo
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Criar nome seguro para o arquivo baseado no nome original
        base_name = os.path.splitext(original_filename)[0]  # Remove extensão (.pdf, .zip, etc)
        safe_name = create_safe_filename(base_name)
        
        if not safe_name:
            safe_name = f"documento_{timestamp}"
        
        markdown_filename = f"MARKITDOWN_{safe_name}_{timestamp}.md"
        markdown_path = os.path.join(FILE_PATH, markdown_filename)
        
        # Se arquivo já existe, adicionar timestamp
        if os.path.exists(markdown_path):
            base, ext = os.path.splitext(markdown_filename)
            markdown_filename = f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
            markdown_path = os.path.join(FILE_PATH, markdown_filename)
        
        # Adicionar URL original no início do conteúdo
        content_with_url = f"""<!-- URL Original: {doc_url} -->

{content}
"""
        
        # Salvar arquivo
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(content_with_url)
        
        return True, markdown_path, None
        
    except Exception as e:
        return False, None, f"Erro ao salvar arquivo: {str(e)}"

def cleanup_temp_file(temp_path):
    """Remove arquivo temporário"""
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except:
        pass

def detect_file_type_by_content_v2(filepath: str) -> str:
    """
    Detecta o tipo de arquivo analisando os primeiros bytes (magic numbers)
    
    Args:
        filepath (str): Caminho do arquivo
        
    Returns:
        str: Nome do arquivo com extensão apropriada
    """
    try:
        with open(filepath, 'rb') as f:
            # Ler os primeiros 512 bytes para identificação
            header = f.read(512)
        
        # Magic numbers para diferentes tipos de arquivo
        if header.startswith(b'%PDF'):
            return "documento.pdf"
        elif header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06') or header.startswith(b'PK\x07\x08'):
            # ZIP/DOCX/XLSX (todos usam formato ZIP)
            # Verificar se é MS Office
            if b'word/' in header or b'xl/' in header or b'ppt/' in header:
                if b'word/' in header:
                    return "documento.docx"
                elif b'xl/' in header:
                    return "documento.xlsx"
                elif b'ppt/' in header:
                    return "documento.pptx"
            return "documento.zip"
        elif header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            # Formato antigo do MS Office (OLE)
            return "documento.doc"
        elif header.startswith(b'<?xml'):
            return "documento.xml"
        elif header.startswith(b'{') or header.startswith(b'['):
            # Provavelmente JSON
            return "documento.json"
        elif header.startswith(b'\xff\xd8\xff'):
            return "documento.jpg"
        elif header.startswith(b'\x89PNG'):
            return "documento.png"
        elif header.startswith(b'GIF8'):
            return "documento.gif"
        elif header.startswith(b'RIFF') and b'WEBP' in header:
            return "documento.webp"
        elif header.startswith(b'\x00\x00\x00\x20ftyp'):
            return "documento.mp4"
        elif header.startswith(b'Rar!'):
            return "documento.rar"
        elif header.startswith(b'\x1f\x8b'):
            return "documento.gz"
        elif header.startswith(b'BZh'):
            return "documento.bz2"
        elif header.startswith(b'\x37\x7a\xbc\xaf\x27\x1c'):
            return "documento.7z"
        else:
            # Verificar se é texto simples
            try:
                header.decode('utf-8')
                return "documento.txt"
            except UnicodeDecodeError:
                try:
                    header.decode('latin-1')
                    return "documento.txt"
                except UnicodeDecodeError:
                    # Se não conseguir identificar, usar extensão padrão sem .bin
                    return "documento.dat"
    
    except Exception as e:
        print(f"⚠️ Erro ao detectar tipo de arquivo: {e}")
        return "documento.dat"

def save_summary_file(summary_content, original_filename, doc_url, timestamp=None):
    """
    Salva o resumo em arquivo no diretório SUMMARY_PATH
    
    Args:
        summary_content (str): Conteúdo do resumo
        original_filename (str): Nome do arquivo original
        doc_url (str): URL do documento original
        timestamp (str): Timestamp para nome único (opcional)
        
    Returns:
        tuple: (sucesso, caminho_salvo, erro)
    """
    try:
        # Criar diretório se não existir
        create_files_directory()
        
        # Usar timestamp fornecido ou gerar novo
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Criar nome seguro baseado no nome original do arquivo
        base_name = Path(original_filename).stem  # Remove extensão (.pdf, .zip, etc)
        safe_name = create_safe_filename(base_name)
        
        if not safe_name:
            safe_name = f"documento_{timestamp}"
        
        # Criar nome do arquivo de resumo
        summary_filename = f"SUMMARY_{safe_name}_{timestamp}.md"
        summary_full_path = os.path.join(SUMMARY_PATH, summary_filename)
        
        # Preparar conteúdo completo do resumo
        timestamp_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        summary_header = f"""# Resumo: {original_filename}

**Data de Processamento:** {timestamp_display}  
**URL Original:** {doc_url}  
**Arquivo Markdown:** MARKITDOWN_{safe_name}_{timestamp}.md  

---

"""
        
        full_summary_content = summary_header + summary_content
        
        # Salvar arquivo de resumo
        with open(summary_full_path, 'w', encoding='utf-8') as f:
            f.write(full_summary_content)
        
        return True, summary_full_path, None
        
    except Exception as e:
        return False, None, str(e)

def generate_document_summary(markdown_content, max_tokens=None, pncp_data=None):
    """
    Gera resumo estruturado do documento a partir do conteúdo Markdown
    
    Args:
        markdown_content (str): Conteúdo Markdown do documento
        max_tokens (int): Parâmetro mantido para compatibilidade (não usado)
        pncp_data (dict): Dados básicos do PNCP (ID, link, datas, localização)
        
    Returns:
        str: Resumo estruturado do documento ou mensagem de erro
    """
    try:
        openai_client = setup_openai()
        
        if not openai_client:
            return "OpenAI não configurado - não foi possível gerar resumo"
        
        # Limite hard de 128k tokens do GPT-4o
        # Aproximadamente 512k caracteres = 128k tokens (deixando margem para o prompt)
        max_content_chars = 100000  # ~100k tokens para o conteúdo + prompt
        
        if len(markdown_content) > max_content_chars:
            markdown_content = markdown_content[:max_content_chars] + "\n\n...(documento truncado devido ao limite de tokens)"
        
        # Construir cabeçalho com dados do PNCP se disponível
        pncp_header = ""
        if pncp_data:
            pncp_header = f"""
## 🏛️ DADOS BÁSICOS DO PNCP
- **ID do Processo:** {pncp_data.get('id', 'Não informado')}
- **Link PNCP:** {pncp_data.get('link', 'Não informado')}
- **Data de Inclusão:** {pncp_data.get('data_inclusao', 'Não informado')}
- **Data de Abertura:** {pncp_data.get('data_abertura', 'Não informado')}
- **Data de Encerramento:** {pncp_data.get('data_encerramento', 'Não informado')}
- **Localização:** {pncp_data.get('municipio', 'Não informado')}/{pncp_data.get('uf', 'Não informado')}
- **Órgão:** {pncp_data.get('orgao', 'Não informado')}

"""

        prompt = f"""
Analise o seguinte documento PNCP convertido para Markdown e gere um resumo COMPLETO seguindo EXATAMENTE a estrutura padronizada abaixo.

ESTRUTURA OBRIGATÓRIA DO RESUMO:
{pncp_header}
## 📄 IDENTIFICAÇÃO DO DOCUMENTO
- **Tipo:** [Edital/Ata/Contrato/Termo de Referência/etc]
- **Modalidade:** [Pregão Eletrônico/Concorrência/Dispensa/etc]
- **Número:** [Número do processo/edital]
- **Órgão:** [Secretaria/Prefeitura/etc]
- **Data:** [Data de publicação/assinatura]

## 🎯 OBJETO PRINCIPAL
- **Descrição:** [O que está sendo contratado/licitado]
- **Finalidade:** [Para que será usado]

## 💰 INFORMAÇÕES FINANCEIRAS
- **Valor Estimado/Contratado:** [Valores principais]
- **Fonte de Recursos:** [Se mencionado]
- **Forma de Pagamento:** [Condições de pagamento]

## ⏰ PRAZOS E CRONOGRAMA
- **Prazo de Entrega/Execução:** [Tempo para conclusão]
- **Vigência do Contrato:** [Período de validade]
- **Prazos Importantes:** [Datas críticas]

## 📋 ESPECIFICAÇÕES TÉCNICAS
- **Requisitos Principais:** [Especificações obrigatórias]
- **Quantidades:** [Volumes/quantitativos]
- **Padrões/Normas:** [Certificações exigidas]

## 📑 DOCUMENTOS EXIGIDOS
### 📊 Documentos de Habilitação Jurídica
- **Societários:** [CNPJ, contrato social, etc.]
- **Regularidade Jurídica:** [Certidões, declarações]

### 💼 Documentos de Qualificação Técnica
- **Atestados Técnicos:** [Comprovação de capacidade]
- **Certidões Técnicas:** [Registros profissionais]
- **Equipe Técnica:** [Qualificação dos profissionais]

### 💰 Documentos de Qualificação Econômico-Financeira
- **Balanços Patrimoniais:** [Demonstrações contábeis]
- **Certidões Negativas:** [Débitos fiscais/trabalhistas]
- **Garantias:** [Seguros, fianças]

### 📋 Documentos Complementares
- **Declarações:** [Idoneidade, menor, etc.]
- **Propostas:** [Técnica e comercial]
- **Amostras:** [Se exigidas]

## 📊 DADOS ESTRUTURADOS (TABELAS)
- **Resumo de Tabelas:** [Principais informações tabulares]
- **Itens/Produtos:** [Lista dos principais itens se houver]
- **Valores Relevantes:** [Dados quantitativos importantes]

## ⚖️ CONDIÇÕES E EXIGÊNCIAS
- **Habilitação:** [Requisitos para participar]
- **Critérios de Julgamento:** [Como será avaliado]
- **Penalidades:** [Multas e sanções]

## 📍 INFORMAÇÕES COMPLEMENTARES
- **Endereço de Entrega:** [Local de execução]
- **Contatos:** [Responsáveis/telefones]
- **Observações:** [Informações adicionais relevantes]

INSTRUÇÕES IMPORTANTES:
- Siga EXATAMENTE a estrutura acima
- Mantenha todos os emojis e formatação
- Se alguma informação não estiver disponível, escreva "Não informado" ou "Não especificado"
- Use linguagem técnica apropriada para licitações públicas
- Extraia TODAS as informações relevantes do documento
- Dê atenção especial a tabelas e dados estruturados

DOCUMENTO:
{markdown_content}

RESUMO:
"""
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um especialista em análise de documentos de licitações públicas e contratos governamentais. Gere resumos técnicos e precisos seguindo EXATAMENTE a estrutura fornecida."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"

def process_pncp_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    """
    Função principal para processar documentos PNCP
    
    Args:
        doc_url (str): URL do documento PNCP
        max_tokens (int): Número máximo de tokens para o resumo
        document_name (str): Nome personalizado do documento (opcional)
        pncp_data (dict): Dados básicos do PNCP (ID, link, datas, localização)
        
    Returns:
        str: Resumo do documento processado ou mensagem de erro
    """
    temp_path = None
    
    try:
        # Gerar timestamp único para este processamento
        processing_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Download do documento
        success, temp_path, filename, error = download_document(doc_url)
        if not success:
            return f"Erro no download: {error}"
        
        # Usar nome personalizado se fornecido, senão usar nome do arquivo baixado
        final_filename = document_name if document_name else filename
        
        # 2. Conversão para Markdown
        success, markdown_content, error = convert_document_to_markdown(temp_path, final_filename)
        if not success:
            return f"Erro na conversão: {error}"
        
        # 3. Salvar arquivo Markdown com timestamp específico
        success, saved_path, error = save_markdown_file(markdown_content, final_filename, doc_url, processing_timestamp)
        if not success:
            return f"Erro ao salvar: {error}"
        
        # 4. Gerar resumo
        summary = generate_document_summary(markdown_content, max_tokens, pncp_data)
        
        # 5. Salvar arquivo de resumo com o MESMO timestamp
        summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp)
        if not summary_success:
            print(f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
        
        # 6. Adicionar informações do arquivo salvo
        final_summary = f"""📄 **DOCUMENTO PROCESSADO**

**Arquivo:** {final_filename}  
**Markdown:** `{os.path.basename(saved_path)}`  
**Resumo:** `{os.path.basename(summary_path) if summary_success else 'Erro ao salvar'}`  
**Pasta Arquivos:** `{FILE_PATH}`  
**Pasta Resumos:** `{SUMMARY_PATH}`  

---

## 📋 RESUMO

{summary}

---

💡 *Documento completo disponível em Markdown e resumo salvos nas respectivas pastas.*
"""
        
        return final_summary
        
    except Exception as e:
        return f"Erro inesperado no processamento: {str(e)}"
    
    finally:
        # Limpar arquivo temporário
        cleanup_temp_file(temp_path)

# Função para manter compatibilidade com código existente
def summarize_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    """
    Função de compatibilidade que substitui a função original
    Esta função baixa, converte e sumariza documentos PNCP
    
    Args:
        doc_url (str): URL do documento
        max_tokens (int): Número máximo de tokens para o resumo
        document_name (str): Nome personalizado do documento (opcional)
        pncp_data (dict): Dados básicos do PNCP (ID, link, datas, localização)
        
    Returns:
        str: Resumo do documento processado
    """
    return process_pncp_document(doc_url, max_tokens, document_name, pncp_data)

def create_safe_filename(filename, max_length=100):
    """
    Cria nome de arquivo seguro preservando caracteres especiais importantes
    
    Args:
        filename (str): Nome original do arquivo
        max_length (int): Comprimento máximo do nome
        
    Returns:
        str: Nome seguro para arquivo
    """
    # Caracteres que devem ser substituídos por segurança no sistema de arquivos
    unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    safe_filename = filename
    
    # Substituir caracteres perigosos
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, '_')
    
    # Preservar caracteres acentuados mas remover caracteres de controle
    safe_filename = ''.join(c for c in safe_filename if unicodedata.category(c) != 'Cc')
    
    # Limitar tamanho
    if len(safe_filename) > max_length:
        safe_filename = safe_filename[:max_length]
    
    # Remover espaços nas extremidades
    safe_filename = safe_filename.strip()
    
    return safe_filename if safe_filename else "documento"
