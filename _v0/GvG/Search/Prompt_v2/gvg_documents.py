"""
gvg_document_utils_v3.py (copiado para gvg_documents.py)
Processamento de documentos PNCP usando Docling v3 (EXATO conforme solicitado)
"""

import os
import sys
import requests
import tempfile
import warnings
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import unicodedata
import logging

# Import OpenAI opcional (não deve impedir carregamento do módulo)
try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

warnings.filterwarnings("ignore", message=".*pin_memory.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*accelerator.*", category=UserWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*color because.*is an invalid float value", category=UserWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*", category=UserWarning)
warnings.filterwarnings("ignore", module="pdfminer.pdfinterp")
warnings.filterwarnings("ignore", module="pdfminer")
warnings.filterwarnings("ignore", category=UserWarning, module="pdfminer.*")

logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\Terminal\\"
FILE_PATH = BASE_PATH + "Arquivos\\"
SUMMARY_PATH = BASE_PATH + "Resumos\\"
OPENAI_ENV_FILE = "openai.env"
MAX_TOKENS = 2000

def load_openai_config():
    config = {}
    if os.path.exists(OPENAI_ENV_FILE):
        with open(OPENAI_ENV_FILE, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

def setup_openai():
    if not _OPENAI_AVAILABLE:
        return None
    try:
        config = load_openai_config()
        api_key = config.get('api_key') or os.environ.get('OPENAI_API_KEY')
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
            try:
                client = OpenAI(api_key=api_key)
                return client
            except Exception:
                return None
        return None
    except Exception:
        return None

def create_files_directory():
    if not os.path.exists(FILE_PATH):
        os.makedirs(FILE_PATH)
    if not os.path.exists(SUMMARY_PATH):
        os.makedirs(SUMMARY_PATH)

def download_document(doc_url, timeout=30):
    try:
        if not doc_url or not doc_url.strip():
            return False, None, None, "URL não fornecida"
        if not doc_url.startswith(('http://', 'https://')):
            return False, None, None, "URL inválida"
        response = requests.get(doc_url, timeout=timeout, stream=True)
        response.raise_for_status()
        parsed_url = urlparse(doc_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            content_type = response.headers.get('content-type', '').lower()
            content_disposition = response.headers.get('content-disposition', '').lower()
            if 'filename=' in content_disposition:
                try:
                    cd_filename = content_disposition.split('filename=')[1].strip('"\'')
                    if '.' in cd_filename:
                        filename = cd_filename
                except:
                    pass
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
                    filename = "documento_temporario"
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"pncp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if filename == "documento_temporario":
            filename = detect_file_type_by_content_v3(temp_path)
            if filename != "documento_temporario":
                new_temp_path = os.path.join(temp_dir, f"pncp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
                os.rename(temp_path, new_temp_path)
                temp_path = new_temp_path
        return True, temp_path, filename, None
    except requests.exceptions.RequestException as e:
        return False, None, None, f"Erro de conexão: {str(e)}"
    except Exception as e:
        return False, None, None, f"Erro inesperado: {str(e)}"

def convert_document_to_markdown(file_path, original_filename):
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions, 
            TableStructureOptions,
            TableFormerMode
        )
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        print(f"🔄 Iniciando conversão SUPER OTIMIZADA do arquivo: {original_filename}")
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"📄 Tamanho do arquivo: {file_size_mb:.2f} MB")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_picture_classification = False
        pipeline_options.do_picture_description = False
        pipeline_options.do_code_enrichment = False
        pipeline_options.do_formula_enrichment = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options = TableStructureOptions()
        pipeline_options.table_structure_options.mode = TableFormerMode.FAST
        pipeline_options.table_structure_options.do_cell_matching = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False
        pipeline_options.images_scale = 1.0
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4,
            device=AcceleratorDevice.AUTO
        )
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, 
                    backend=PyPdfiumDocumentBackend
                )
            }
        )
        print("🚀 Convertendo com Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST)...")
        result = doc_converter.convert(file_path)
        doc = result.document
        print("✅ Conversão concluída, extraindo markdown...")
        markdown_content_raw = doc.export_to_markdown()
        table_count = 0
        if hasattr(doc, 'tables') and doc.tables:
            table_count = len(doc.tables)
        print(f"📊 Tabelas encontradas: {table_count}")
        file_info = os.stat(file_path)
        size_mb = file_info.st_size / (1024 * 1024)
        table_info = f"**Tabelas encontradas:** {table_count}  \n" if table_count > 0 else ""
        markdown_content = f"""# Documento PNCP: {original_filename}

**Arquivo original:** `{original_filename}`  
**Tamanho:** {size_mb:.2f} MB  
**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Ferramenta:** Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST) + OpenAI GPT-4o  
{table_info}

---

{markdown_content_raw}
"""
        print("✅ Markdown preparado com sucesso!")
        return True, markdown_content, None
    except ImportError:
        return False, None, "Docling não está instalado. Execute: pip install docling"
    except Exception as e:
        print(f"❌ Erro na conversão: {str(e)}")
        return False, None, f"Erro na conversão: {str(e)}"

def save_markdown_file(content, original_filename, doc_url, timestamp=None):
    try:
        create_files_directory()
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(original_filename)[0]
        safe_name = create_safe_filename(base_name)
        if not safe_name:
            safe_name = f"documento_{timestamp}"
        markdown_filename = f"DOCLING_{safe_name}_{timestamp}.md"
        markdown_path = os.path.join(FILE_PATH, markdown_filename)
        if os.path.exists(markdown_path):
            base, ext = os.path.splitext(markdown_filename)
            markdown_filename = f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
            markdown_path = os.path.join(FILE_PATH, markdown_filename)
        content_with_url = f"""<!-- URL Original: {doc_url} -->

{content}
"""
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(content_with_url)
        return True, markdown_path, None
    except Exception as e:
        return False, None, f"Erro ao salvar arquivo: {str(e)}"

def save_summary_file(summary_content, original_filename, doc_url, timestamp=None, pncp_data=None):
    try:
        create_files_directory()
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = Path(original_filename).stem
        safe_name = create_safe_filename(base_name)
        if not safe_name:
            safe_name = f"documento_{timestamp}"
        summary_filename = f"SUMMARY_{safe_name}_{timestamp}.md"
        summary_full_path = os.path.join(SUMMARY_PATH, summary_filename)
        timestamp_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pncp_header = ""
        if pncp_data:
            descricao_completa = pncp_data.get('descricao', 'Não informado')
            if " :: " in descricao_completa:
                descricao_resumida = descricao_completa.split(" :: ")[0].strip()
            else:
                descricao_resumida = descricao_completa[:200] + "..." if len(descricao_completa) > 200 else descricao_completa
            modalidade_id = pncp_data.get('modalidade_id', 'N/A')
            modalidade_nome = pncp_data.get('modalidade_nome', 'Não informado')
            disputa_id = pncp_data.get('disputa_id', 'N/A')
            disputa_nome = pncp_data.get('disputa_nome', 'Não informado')
            modalidade_texto = f"{modalidade_id} - {modalidade_nome}"
            disputa_texto = f"{disputa_id} - {disputa_nome}"
            pncp_header = f"""
## 🏛️ DADOS BÁSICOS DO PNCP
- **📍 Localização:** {pncp_data.get('municipio', 'Não informado')}/{pncp_data.get('uf', 'Não informado')}
- **🏢 Órgão:** {pncp_data.get('orgao', 'Não informado')}
- **🆔 ID do Processo:** {pncp_data.get('id', 'Não informado')}
- **🔗 Link PNCP:** {pncp_data.get('link', 'Não informado')}
- **📅 Inclusão:** {pncp_data.get('data_inclusao', 'Não informado')} | **Abertura:** {pncp_data.get('data_abertura', 'Não informado')} | **Encerramento:** {pncp_data.get('data_encerramento', 'Não informado')}
- **⚖️ Modalidade:** {modalidade_texto} | **Disputa:** {disputa_texto}
- **📋 Descrição:** {descricao_resumida}

"""
        summary_header = f"""# Resumo: {original_filename}

**Data de Processamento:** {timestamp_display}  
**URL Original:** {doc_url}  
**Ferramenta:** Docling  
**Arquivo Markdown:** DOCLING_{safe_name}_{timestamp}.md  
{pncp_header}---

"""
        full_summary_content = summary_header + summary_content
        with open(summary_full_path, 'w', encoding='utf-8') as f:
            f.write(full_summary_content)
        return True, summary_full_path, None
    except Exception as e:
        return False, None, str(e)

def generate_document_summary(markdown_content, max_tokens=None, pncp_data=None):
    try:
        openai_client = setup_openai()
        if not openai_client:
            return "OpenAI não configurado - não foi possível gerar resumo"
        max_content_chars = 100000
        if len(markdown_content) > max_content_chars:
            markdown_content = markdown_content[:max_content_chars] + "\n\n...(documento truncado devido ao limite de tokens)"
        pncp_header = ""
        if pncp_data:
            descricao_completa = pncp_data.get('descricao', 'Não informado')
            if " :: " in descricao_completa:
                descricao_resumida = descricao_completa.split(" :: ")[0].strip()
            else:
                descricao_resumida = descricao_completa[:200] + "..." if len(descricao_completa) > 200 else descricao_completa
            modalidade_id = pncp_data.get('modalidade_id', 'N/A')
            modalidade_nome = pncp_data.get('modalidade_nome', 'Não informado')
            disputa_id = pncp_data.get('disputa_id', 'N/A')
            disputa_nome = pncp_data.get('disputa_nome', 'Não informado')
            pncp_header = f"""

Os dados básicos do PNCP já estão no cabeçalho do arquivo. Use essas informações como contexto:
- ID do Processo: {pncp_data.get('id', 'Não informado')}
- Localização: {pncp_data.get('municipio', 'Não informado')}/{pncp_data.get('uf', 'Não informado')}
- Órgão: {pncp_data.get('orgao', 'Não informado')}
- Datas: Inclusão: {pncp_data.get('data_inclusao', 'Não informado')} | Abertura: {pncp_data.get('data_abertura', 'Não informado')} | Encerramento: {pncp_data.get('data_encerramento', 'Não informado')}
- Modalidade: {modalidade_id} - {modalidade_nome} | Disputa: {disputa_id} - {disputa_nome}
- Descrição: {descricao_resumida}

"""
        prompt = f"""
Analise o seguinte documento PNCP convertido para Markdown usando Docling e gere um resumo COMPLETO seguindo EXATAMENTE a estrutura padronizada abaixo.{pncp_header}

ESTRUTURA OBRIGATÓRIA DO RESUMO:

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
- Dê atenção especial a tabelas e dados estruturados extraídos pelo Docling

DOCUMENTO:
{markdown_content}

RESUMO:
"""
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um especialista em análise de documentos de licitações públicas e contratos governamentais. Gere resumos técnicos e precisos seguindo EXATAMENTE a estrutura fornecida. Dê atenção especial às tabelas extraídas pelo Docling."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"

def cleanup_temp_file(temp_path):
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except:
        pass

def detect_file_type_by_content_v3(filepath: str) -> str:
    try:
        with open(filepath, 'rb') as f:
            header = f.read(512)
        if header.startswith(b'%PDF'):
            return "documento.pdf"
        elif header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06') or header.startswith(b'PK\x07\x08'):
            if b'word/' in header or b'xl/' in header or b'ppt/' in header:
                if b'word/' in header:
                    return "documento.docx"
                elif b'xl/' in header:
                    return "documento.xlsx"
                elif b'ppt/' in header:
                    return "documento.pptx"
            return "documento.zip"
        elif header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return "documento.doc"
        elif header.startswith(b'<?xml'):
            return "documento.xml"
        elif header.startswith(b'{') or header.startswith(b'['):
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
            try:
                header.decode('utf-8')
                return "documento.txt"
            except UnicodeDecodeError:
                try:
                    header.decode('latin-1')
                    return "documento.txt"
                except UnicodeDecodeError:
                    return "documento.dat"
    except Exception as e:
        print(f"⚠️ Erro ao detectar tipo de arquivo: {e}")
        return "documento.dat"

def is_zip_file(file_path):
    try:
        if file_path.lower().endswith('.zip'):
            return True
        with open(file_path, 'rb') as f:
            magic = f.read(2)
            if magic == b'PK':
                return True
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            return True
    except (OSError, zipfile.BadZipFile, Exception):
        return False
    return False

def extract_all_supported_files_from_zip(zip_path):
    try:
        supported_extensions = ['.pdf', '.docx', '.doc', '.pptx', '.xlsx', '.xls', '.csv', '.txt', '.md']
        extract_dir = os.path.join(tempfile.gettempdir(), f"zip_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(f"   📦 Arquivos no ZIP: {len(file_list)}")
            for file_name in file_list:
                if file_name.startswith('__MACOSX/') or file_name.endswith('/'):
                    continue
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext in supported_extensions:
                    try:
                        zip_ref.extract(file_name, extract_dir)
                        extracted_path = os.path.join(extract_dir, file_name)
                        if os.path.exists(extracted_path):
                            file_size = os.path.getsize(extracted_path) / (1024 * 1024)
                            print(f"   📄 Extraído: {os.path.basename(file_name)} ({file_size:.2f} MB)")
                            extracted_files.append((extracted_path, os.path.basename(file_name)))
                    except Exception as e:
                        print(f"   ⚠️ Erro ao extrair {file_name}: {str(e)}")
                        continue
            if not extracted_files:
                return False, [], "Nenhum arquivo suportado encontrado no ZIP"
            print(f"   ✅ Total extraído: {len(extracted_files)} arquivo(s)")
            return True, extracted_files, None
    except Exception as e:
        return False, [], f"Erro ao extrair ZIP: {str(e)}"

def extract_first_pdf_from_zip(zip_path):
    try:
        success, extracted_files, error = extract_all_supported_files_from_zip(zip_path)
        if not success:
            return False, None, None, error
        for file_path, file_name in extracted_files:
            if file_name.lower().endswith('.pdf'):
                return True, file_path, file_name, None
        if extracted_files:
            file_path, file_name = extracted_files[0]
            return True, file_path, file_name, None
        return False, None, None, "Nenhum arquivo encontrado no ZIP"
    except Exception as e:
        return False, None, None, f"Erro ao extrair ZIP: {str(e)}"

def process_pncp_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    temp_path = None
    try:
        processing_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        success, temp_path, filename, error = download_document(doc_url)
        if not success:
            return f"Erro no download: {error}"
        final_filename = document_name if document_name else filename
        if is_zip_file(temp_path):
            print("📦 Arquivo ZIP detectado. Extraindo TODOS os arquivos suportados...")
            success, extracted_files_list, error = extract_all_supported_files_from_zip(temp_path)
            if not success:
                return f"Erro ao extrair arquivos do ZIP: {error}"
            if not extracted_files_list:
                return "Erro: Nenhum arquivo suportado encontrado no ZIP"
            all_markdown_content = f"# Documento PNCP: {final_filename} (ZIP com múltiplos arquivos)\n\n"
            all_markdown_content += f"**Arquivo original:** `{final_filename}`  \n"
            all_markdown_content += f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
            all_markdown_content += f"**Ferramenta:** Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST) + OpenAI GPT-4o  \n"
            all_markdown_content += f"**Arquivos extraídos:** {len(extracted_files_list)}  \n\n"
            all_markdown_content += "---\n\n"
            processed_files = []
            total_size = 0
            for extracted_path, original_name in extracted_files_list:
                print(f"📄 Processando arquivo extraído: {original_name}")
                if os.path.exists(extracted_path):
                    file_size_extracted = os.path.getsize(extracted_path) / (1024 * 1024)
                    total_size += file_size_extracted
                    print(f"📏 Tamanho: {file_size_extracted:.2f} MB")
                    file_success, file_markdown, file_error = convert_document_to_markdown(
                        extracted_path, 
                        original_name
                    )
                    if file_success:
                        all_markdown_content += f"## 📄 Arquivo: {original_name}\n\n"
                        all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                        all_markdown_content += f"**Status:** ✅ Processado com sucesso  \n\n"
                        all_markdown_content += "### Conteúdo:\n\n"
                        all_markdown_content += file_markdown
                        all_markdown_content += "\n\n---\n\n"
                        processed_files.append({
                            'name': original_name,
                            'success': True,
                            'size': file_size_extracted,
                            'chars': len(file_markdown)
                        })
                        print(f"✅ {original_name} processado com sucesso")
                    else:
                        all_markdown_content += f"## ❌ Arquivo: {original_name}\n\n"
                        all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                        all_markdown_content += f"**Status:** ❌ Erro no processamento  \n"
                        all_markdown_content += f"**Erro:** {file_error}  \n\n"
                        all_markdown_content += "---\n\n"
                        processed_files.append({
                            'name': original_name,
                            'success': False,
                            'error': file_error
                        })
                        print(f"❌ Erro em {original_name}: {file_error}")
                else:
                    print(f"❌ Arquivo extraído não encontrado: {original_name}")
            try:
                if extracted_files_list:
                    extract_dir = os.path.dirname(extracted_files_list[0][0])
                    if os.path.exists(extract_dir):
                        shutil.rmtree(extract_dir)
            except Exception as cleanup_error:
                print(f"⚠️ Aviso: Erro na limpeza: {cleanup_error}")
            successful_files = [f for f in processed_files if f['success']]
            if successful_files:
                success = True
                markdown_content = all_markdown_content
                error = None
                final_filename = f"{final_filename} ({len(successful_files)}-{len(processed_files)} arquivos)"
                print(f"✅ ZIP processado: {len(successful_files)}/{len(processed_files)} arquivos com sucesso")
            else:
                return "Erro: Nenhum arquivo do ZIP foi processado com sucesso"
        else:
            print(f"📄 Processando arquivo diretamente: {final_filename}")
            file_to_process = temp_path
            success, markdown_content, error = convert_document_to_markdown(file_to_process, final_filename)
            if not success:
                return f"Erro na conversão: {error}"
        save_success, saved_path, save_error = save_markdown_file(markdown_content, final_filename, doc_url, processing_timestamp)
        if not save_success:
            return f"Erro ao salvar: {save_error}"
        summary = generate_document_summary(markdown_content, max_tokens, pncp_data)
        summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data)
        if not summary_success:
            print(f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
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
        cleanup_temp_file(temp_path)

def summarize_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    return process_pncp_document(doc_url, max_tokens, document_name, pncp_data)

def create_safe_filename(filename, max_length=100):
    unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    safe_filename = filename
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, '_')
    safe_filename = ''.join(c for c in safe_filename if unicodedata.category(c) != 'Cc')
    if len(safe_filename) > max_length:
        safe_filename = safe_filename[:max_length]
    safe_filename = safe_filename.strip()
    return safe_filename if safe_filename else "documento"

__all__ = [
    'summarize_document',
    'process_pncp_document',
    'download_document',
    'convert_document_to_markdown',
    'save_markdown_file',
    'save_summary_file',
    'generate_document_summary'
]
