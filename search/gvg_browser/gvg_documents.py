"""
gvg_documents.py
Processamento de documentos PNCP:
- Download, detecção e conversão para Markdown (Docling isolado em subprocesso)
- Extração de ZIP e RAR
- Resumo com OpenAI Assistants (ID via .env: GVG_SUMMARY_DOCUMENT_v1)

Observações:
- Mantemos Docling em subprocesso por estabilidade.
- Paths de trabalho vêm do .env (FILES_PATH, RESULTS_PATH, TEMP_PATH).
- Logs reduzidos via flag DOCUMENTS_DEBUG/DEBUG.
- Preparamos terreno para futuramente enviar o arquivo original ao Assistant sem Docling.
"""

import os
import re
import sys
import json
import subprocess
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
import re
import time
from dotenv import load_dotenv
from gvg_debug import debug_log as dbg
from gvg_ai_utils import ai_assistant_run_text, ai_assistant_run_with_files
from gvg_database import fetch_documentos  # centralizado

_OPENAI_AVAILABLE = True  # compat

warnings.filterwarnings("ignore", message=".*pin_memory.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*accelerator.*", category=UserWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*color because.*is an invalid float value", category=UserWarning)
warnings.filterwarnings("ignore", message="Cannot set gray.*", category=UserWarning)
warnings.filterwarnings("ignore", module="pdfminer.pdfinterp")
warnings.filterwarnings("ignore", module="pdfminer")
warnings.filterwarnings("ignore", category=UserWarning, module="pdfminer.*")

logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)

# ========= Configuração via .env =========
load_dotenv()  # garante variáveis carregadas

# Logs de depuração (menos ruído por padrão)
_DOC_DEBUG = (os.getenv('DOCUMENTS_DEBUG', os.getenv('DEBUG', 'false')) or 'false').strip().lower() in ('1', 'true', 'yes', 'on')

def _dbg(msg: str):
    """Compat: agora apenas chama dbg diretamente (sem try/except)."""
    dbg('DOCS', msg)

# Debug helper to print Assistant output when app runs with --debug
def _dbg_assistant_output(tag: str, text: str):
    """Imprime saída do Assistant usando categoria ASSISTANT (sem try/except)."""
    dbg('ASSISTANT', f"[RESUMO]{'['+tag+']' if tag else ''}:\n{text}\n")

# Strip unwanted citation markers like 【4:5†source】 or [..source..]
def strip_citations(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    # Remove fullwidth-bracket citations
    text = re.sub(r"【[^】]*】", "", text)
    # Remove square-bracket citations that contain the word 'source'
    text = re.sub(r"\[[^\]]*source[^\]]*\]", "", text, flags=re.IGNORECASE)
    # Collapse excessive whitespace created by removals
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# Diretórios de trabalho
_BASE_PATH = os.getenv('BASE_PATH') or str(Path(__file__).resolve().parents[2] / 'data')
FILE_PATH = os.getenv('FILES_PATH') or str(Path(_BASE_PATH) / 'files')
SUMMARY_PATH = os.getenv('RESULTS_PATH') or str(Path(_BASE_PATH) / 'reports')
TEMP_PATH = os.getenv('TEMP_PATH') or tempfile.gettempdir()

# Controle: gerar Markdown (Docling) antes do resumo ou enviar arquivo original ao Assistant
# Não vem do .env. Padrão: False (0). Será alterado pelo app (--markdown)
GVG_MARKDOWN = False

def set_markdown_enabled(enabled: bool):
    global GVG_MARKDOWN
    GVG_MARKDOWN = bool(enabled)

_ASSISTANT_SUMMARY_ID = os.getenv('GVG_SUMMARY_DOCUMENT_v1')

def create_files_directory():
    Path(FILE_PATH).mkdir(parents=True, exist_ok=True)
    Path(SUMMARY_PATH).mkdir(parents=True, exist_ok=True)

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
        temp_dir = TEMP_PATH or tempfile.gettempdir()
        try:
            # Garantir diretório temporário existente; se falhar, usar temp do sistema
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            _dbg(f"[GSB][RESUMO] TEMP_PATH inválido ('{temp_dir}'): {e}; usando temp padrão do sistema.")
            temp_dir = tempfile.gettempdir()
            os.makedirs(temp_dir, exist_ok=True)
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
    """Convert a PDF to Markdown using Docling in a subprocess (stable path)."""
    try:
        dbg('DOCS', f"Subprocesso Docling iniciado para '{original_filename}'")
        code = (
            "import json,sys; "
            "fp=sys.argv[1]; fn=sys.argv[2];\n"
            "from docling.document_converter import DocumentConverter, PdfFormatOption\n"
            "from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions, TableFormerMode\n"
            "from docling.datamodel.base_models import InputFormat\n"
            "from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions\n"
            "from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend\n"
            "ppo=PdfPipelineOptions(); ppo.do_ocr=False; ppo.do_picture_classification=False; ppo.do_picture_description=False; ppo.do_code_enrichment=False; ppo.do_formula_enrichment=False; ppo.do_table_structure=True;\n"
            "ppo.table_structure_options=TableStructureOptions(); ppo.table_structure_options.mode=TableFormerMode.FAST; ppo.table_structure_options.do_cell_matching=False;\n"
            "ppo.generate_page_images=False; ppo.generate_picture_images=False; ppo.images_scale=1.0; ppo.accelerator_options=AcceleratorOptions(num_threads=4, device=AcceleratorDevice.AUTO)\n"
            "dc=DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=ppo, backend=PyPdfiumDocumentBackend)});\n"
            "res=dc.convert(fp); md=res.document.export_to_markdown(); print(json.dumps({'ok':True,'markdown':md}))"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code, file_path, original_filename],
                capture_output=True, text=True, timeout=180
            )
        except Exception as e:
            return False, None, f"Falha ao executar subprocesso Docling: {e}"
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            dbg('DOCS', f"Subprocesso Docling falhou rc={proc.returncode}: {err[:300]}")
            return False, None, f"Docling falhou no subprocesso: {err}" if err else "Docling falhou no subprocesso"
        try:
            payload = json.loads(proc.stdout.strip())
            if payload.get('ok') and 'markdown' in payload:
                return True, payload['markdown'], None
        except Exception as e:
            return False, None, f"Saída inválida do subprocesso Docling: {e}"
        return False, None, "Saída inesperada do subprocesso Docling"
    except ImportError:
        dbg('DOCS', "ImportError em Docling - Docling não instalado")
        return False, None, "Docling não está instalado. Execute: pip install docling"
    except Exception as e:
        dbg('DOCS', f"Exceção em convert_document_to_markdown: {e}")
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

def save_summary_file(summary_content, original_filename, doc_url, timestamp=None, pncp_data=None, method_label: str = "Docling + Assistant", markdown_filename: str | None = None):
    """Save ONLY the assistant's output to the summary file (no headers or extras)."""
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
        content = summary_content or ""
        with open(summary_full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, summary_full_path, None
    except Exception as e:
        return False, None, str(e)

def generate_document_summary(markdown_content, max_tokens=None, pncp_data=None):
    """Resumo via OpenAI Assistants (ID do .env: GVG_SUMMARY_DOCUMENT_v1) usando wrappers centrais."""
    try:
        _dbg("[GSB][RESUMO] generate_document_summary() via Assistants...")
        if not _ASSISTANT_SUMMARY_ID:
            return "OpenAI/Assistant não configurado (verifique GVG_SUMMARY_DOCUMENT_v1 no .env)."
        # Truncagem conservadora
        content = markdown_content or ""
        if len(content) > 100_000:
            content = content[:100_000] + "\n\n...(documento truncado)"
        # Contexto compacto
        ctx_lines = []
        if isinstance(pncp_data, dict) and pncp_data:
            try:
                ctx_lines.append(f"ID: {pncp_data.get('id')}")
                ctx_lines.append(f"Órgão: {pncp_data.get('orgao')} | Local: {pncp_data.get('municipio')}/{pncp_data.get('uf')}")
                ctx_lines.append(f"Datas: Inc {pncp_data.get('data_inclusao')} | Ab {pncp_data.get('data_abertura')} | Enc {pncp_data.get('data_encerramento')}")
                ctx_lines.append(f"Modal/Disp: {pncp_data.get('modalidade_id')} - {pncp_data.get('modalidade_nome')} | {pncp_data.get('disputa_id')} - {pncp_data.get('disputa_nome')}")
            except Exception:
                pass
        ctx_block = ("\n".join([l for l in ctx_lines if l])) if ctx_lines else ""
        anti_citation = (
            "INSTRUÇÕES ADICIONAIS IMPORTANTES:\n"
            "- NUNCA inclua citações, referências ou marcas de fonte.\n"
            "- Remova padrões como 【4:5†source】, [1], [1:2], [qualquer-coisa†source] ou links.\n"
            "- Gere apenas o resumo no formato especificado, sem referências.\n\n"
        )
        user_message = (
            (("Contexto PNCP:\n" + ctx_block + "\n\n") if ctx_block else "")
            + anti_citation
            + "Documento (Markdown):\n\n" + content
        )
        out = ai_assistant_run_text(_ASSISTANT_SUMMARY_ID, user_message, context_key='doc_summary', timeout=180)
        out = strip_citations(out or "")

    except Exception as e:
        return f"Erro ao gerar resumo (Assistants): {str(e)}"

def generate_document_summary_from_files(file_paths: list[str], max_tokens=None, pncp_data=None):
    """Generate a summary by uploading original files to the Assistant (skip Docling) via wrappers."""
    try:
        if not _ASSISTANT_SUMMARY_ID:
            return "OpenAI/Assistant não configurado (verifique GVG_SUMMARY_DOCUMENT_v1 no .env)."
        # Context block (compact)
        ctx_lines = []
        if isinstance(pncp_data, dict) and pncp_data:
            try:
                ctx_lines.append(f"ID: {pncp_data.get('id')}")
                ctx_lines.append(f"Órgão: {pncp_data.get('orgao')} | Local: {pncp_data.get('municipio')}/{pncp_data.get('uf')}")
                ctx_lines.append(f"Datas: Inc {pncp_data.get('data_inclusao')} | Ab {pncp_data.get('data_abertura')} | Enc {pncp_data.get('data_encerramento')}")
                ctx_lines.append(f"Modal/Disp: {pncp_data.get('modalidade_id')} - {pncp_data.get('modalidade_nome')} | {pncp_data.get('disputa_id')} - {pncp_data.get('disputa_nome')}")
            except Exception:
                pass
        ctx_block = ("\n".join([l for l in ctx_lines if l])) if ctx_lines else ""
        anti_citation = (
            "INSTRUÇÕES ADICIONAIS IMPORTANTES:\n"
            "- NUNCA inclua citações, referências ou marcas de fonte.\n"
            "- Remova padrões como 【4:5†source】, [1], [1:2], [qualquer-coisa†source] ou links.\n"
            "- Gere apenas o resumo no formato especificado, sem referências.\n\n"
        )
        user_message = (
            (("Contexto PNCP:\n" + ctx_block + "\n\n") if ctx_block else "")
            + anti_citation
            + "Documentos anexados. Gerar um resumo executivo com itens de atenção."
        )
        out = ai_assistant_run_with_files(_ASSISTANT_SUMMARY_ID, list(file_paths or []), user_message, timeout=180)
        out = strip_citations(out or "")

    except Exception as e:
        return f"Erro ao gerar resumo (Assistants arquivos): {str(e)}"

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
        
        dbg('DOCS', f"⚠️ Erro ao detectar tipo de arquivo: {e}")
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

def is_rar_file(file_path: str) -> bool:
    try:
        p = file_path.lower()
        if p.endswith('.rar'):
            return True
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header == b'Rar!':
                return True
    except Exception:
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
            
            dbg('DOCS', f"   📦 Arquivos no ZIP: {len(file_list)}")
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
                            dbg('DOCS', f"   📄 Extraído: {os.path.basename(file_name)} ({file_size:.2f} MB)")
                            extracted_files.append((extracted_path, os.path.basename(file_name)))
                    except Exception as e:
                        dbg('DOCS', f"   ⚠️ Erro ao extrair {file_name}: {str(e)}")
                        continue
            if not extracted_files:
                return False, [], "Nenhum arquivo suportado encontrado no ZIP"
            dbg('DOCS', f"   ✅ Total extraído: {len(extracted_files)} arquivo(s)")
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

def _discover_7z_exe():
    candidates = [
        r"C:\\Program Files\\7-Zip\\7z.exe",
        r"C:\\Program Files (x86)\\7-Zip\\7z.exe",
        "7z",
    ]
    for c in candidates:
        try:
            if os.path.sep in c:
                if os.path.exists(c):
                    return c
            else:
                return c
        except Exception:
            continue
    return None

def extract_all_supported_files_from_rar(rar_path: str):
    try:
        supported_extensions = ['.pdf', '.docx', '.doc', '.pptx', '.xlsx', '.xls', '.csv', '.txt', '.md']
        extract_dir = os.path.join(tempfile.gettempdir(), f"rar_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_files = []
        # Tentar rarfile
        used_rarfile = False
        try:
            import rarfile  # type: ignore
            rf = rarfile.RarFile(rar_path)
            names = rf.namelist()
            _dbg(f"   📦 Arquivos no RAR: {len(names)}")
            for nm in names:
                if nm.endswith('/') or nm.startswith('__MACOSX/'):
                    continue
                ext = os.path.splitext(nm)[1].lower()
                if ext in supported_extensions:
                    try:
                        rf.extract(nm, extract_dir)
                        outp = os.path.join(extract_dir, nm)
                        if os.path.exists(outp):
                            extracted_files.append((outp, os.path.basename(nm)))
                            _dbg(f"   📄 Extraído: {os.path.basename(nm)}")
                    except Exception as e:
                        _dbg(f"   ⚠️ Erro ao extrair {nm}: {e}")
                        continue
            used_rarfile = True
        except Exception as e:
            _dbg(f"[RAR] rarfile indisponível/erro: {e}")
        # Fallback 7z
        if not extracted_files:
            seven = _discover_7z_exe()
            if not seven:
                return False, [], "RAR: 'rarfile' indisponível e 7-Zip não encontrado."
            try:
                proc = subprocess.run([seven, 'x', '-y', f"-o{extract_dir}", rar_path], capture_output=True, text=True, timeout=120)
                if proc.returncode != 0:
                    err = proc.stderr.strip() or proc.stdout.strip()
                    return False, [], f"Erro 7-Zip ao extrair RAR: {err[:200]}"
                for root, _, files in os.walk(extract_dir):
                    for fn in files:
                        ext = os.path.splitext(fn)[1].lower()
                        if ext in supported_extensions:
                            path = os.path.join(root, fn)
                            extracted_files.append((path, fn))
                            _dbg(f"   📄 Extraído: {fn}")
            except Exception as e:
                return False, [], f"Falha ao usar 7-Zip para RAR: {e}"
        if not extracted_files:
            return False, [], "Nenhum arquivo suportado encontrado no RAR"
        return True, extracted_files, None
    except Exception as e:
        return False, [], f"Erro ao extrair RAR: {str(e)}"

def process_pncp_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    temp_path = None
    try:
        processing_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dbg('DOCS', f"process_pncp_document() inicio url='{str(doc_url)[:80]}{'...' if doc_url and len(str(doc_url))>80 else ''}' nome='{document_name}'")
        success, temp_path, filename, error = download_document(doc_url)
        dbg('DOCS', f"download_document -> success={success} temp='{temp_path}' file='{filename}' err='{error}'")

        if not success:
            return f"Erro no download: {error}"
        final_filename = document_name if document_name else filename
        if is_zip_file(temp_path):
            dbg('DOCS', "📦 Arquivo ZIP detectado. Extraindo TODOS os arquivos suportados...")
            success, extracted_files_list, error = extract_all_supported_files_from_zip(temp_path)
            if not success:
                return f"Erro ao extrair arquivos do ZIP: {error}"
            if not extracted_files_list:
                return "Erro: Nenhum arquivo suportado encontrado no ZIP"
            if GVG_MARKDOWN:
                # Docling -> Markdown -> Assistant
                all_markdown_content = f"# Documento PNCP: {final_filename} (ZIP com múltiplos arquivos)\n\n"
                all_markdown_content += f"**Arquivo original:** `{final_filename}`  \n"
                all_markdown_content += f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
                all_markdown_content += f"**Ferramenta:** Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST) + OpenAI GPT-4o  \n"
                all_markdown_content += f"**Arquivos extraídos:** {len(extracted_files_list)}  \n\n"
                all_markdown_content += "---\n\n"
                processed_files = []
                for extracted_path, original_name in extracted_files_list:
                    dbg('DOCS', f"📄 Processando arquivo extraído: {original_name}")
                    if os.path.exists(extracted_path):
                        file_size_extracted = os.path.getsize(extracted_path) / (1024 * 1024)
                        dbg('DOCS', f"📏 Tamanho: {file_size_extracted:.2f} MB")
                        file_success, file_markdown, file_error = convert_document_to_markdown(extracted_path, original_name)
                        if file_success:
                            all_markdown_content += f"## 📄 Arquivo: {original_name}\n\n"
                            all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                            all_markdown_content += f"**Status:** ✅ Processado com sucesso  \n\n"
                            all_markdown_content += "### Conteúdo:\n\n"
                            all_markdown_content += file_markdown
                            all_markdown_content += "\n\n---\n\n"
                            processed_files.append({'name': original_name, 'success': True})
                            dbg('DOCS', f"✅ {original_name} processado com sucesso")
                        else:
                            all_markdown_content += f"## ❌ Arquivo: {original_name}\n\n"
                            all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                            all_markdown_content += f"**Status:** ❌ Erro no processamento  \n"
                            all_markdown_content += f"**Erro:** {file_error}  \n\n"
                            all_markdown_content += "---\n\n"
                            processed_files.append({'name': original_name, 'success': False})
                            dbg('DOCS', f"❌ Erro em {original_name}: {file_error}")
                    else:
                        dbg('DOCS', f"❌ Arquivo extraído não encontrado: {original_name}")
                # Cleanup
                try:
                    if extracted_files_list:
                        extract_dir = os.path.dirname(extracted_files_list[0][0])
                        if os.path.exists(extract_dir):
                            shutil.rmtree(extract_dir)
                except Exception as cleanup_error:
                    dbg('DOCS', f"⚠️ Aviso: Erro na limpeza: {cleanup_error}")
                successful_files = [f for f in processed_files if f['success']]
                if successful_files:
                    success = True
                    markdown_content = all_markdown_content
                    error = None
                    final_filename = f"{final_filename} ({len(successful_files)}-{len(processed_files)} arquivos)"
                    dbg('DOCS', f"✅ ZIP processado: {len(successful_files)}/{len(processed_files)} arquivos com sucesso")
                else:
                    return "Erro: Nenhum arquivo do ZIP foi processado com sucesso"
            else:
                # Assistant direto com arquivos originais
                try:
                    files_to_send = [p for (p, _n) in extracted_files_list if os.path.exists(p)]
                    summary = generate_document_summary_from_files(files_to_send, max_tokens, pncp_data)
                    method_label = "Assistant (arquivos originais)"
                    summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data, method_label=method_label, markdown_filename=None)
                    if not summary_success:
                        dbg('DOCS', f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
                    # Cleanup extract dir
                    try:
                        if extracted_files_list:
                            extract_dir = os.path.dirname(extracted_files_list[0][0])
                            if os.path.exists(extract_dir):
                                shutil.rmtree(extract_dir)
                    except Exception as cleanup_error:
                        dbg('DOCS', f"⚠️ Aviso: Erro na limpeza: {cleanup_error}")
                    # Return only assistant output so the UI shows the exact text
                    return summary
                finally:
                    # Ensure temp is removed
                    pass
        elif is_rar_file(temp_path):
            dbg('DOCS', "📦 Arquivo RAR detectado. Extraindo TODOS os arquivos suportados...")
            success, extracted_files_list, error = extract_all_supported_files_from_rar(temp_path)
            if not success:
                return f"Erro ao extrair arquivos do RAR: {error}"
            if not extracted_files_list:
                return "Erro: Nenhum arquivo suportado encontrado no RAR"
            if GVG_MARKDOWN:
                # Docling -> Markdown -> Assistant
                all_markdown_content = f"# Documento PNCP: {final_filename} (RAR com múltiplos arquivos)\n\n"
                all_markdown_content += f"**Arquivo original:** `{final_filename}`  \n"
                all_markdown_content += f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
                all_markdown_content += f"**Ferramenta:** Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST) + OpenAI GPT-4o  \n"
                all_markdown_content += f"**Arquivos extraídos:** {len(extracted_files_list)}  \n\n"
                all_markdown_content += "---\n\n"
                processed_files = []
                for extracted_path, original_name in extracted_files_list:
                    dbg('DOCS', f"📄 Processando arquivo extraído: {original_name}")
                    if os.path.exists(extracted_path):
                        file_size_extracted = os.path.getsize(extracted_path) / (1024 * 1024)
                        dbg('DOCS', f"📏 Tamanho: {file_size_extracted:.2f} MB")
                        file_success, file_markdown, file_error = convert_document_to_markdown(extracted_path, original_name)
                        if file_success:
                            all_markdown_content += f"## 📄 Arquivo: {original_name}\n\n"
                            all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                            all_markdown_content += f"**Status:** ✅ Processado com sucesso  \n\n"
                            all_markdown_content += "### Conteúdo:\n\n"
                            all_markdown_content += file_markdown
                            all_markdown_content += "\n\n---\n\n"
                            processed_files.append({'name': original_name, 'success': True})
                            dbg('DOCS', f"✅ {original_name} processado com sucesso")
                        else:
                            all_markdown_content += f"## ❌ Arquivo: {original_name}\n\n"
                            all_markdown_content += f"**Tamanho:** {file_size_extracted:.2f} MB  \n"
                            all_markdown_content += f"**Status:** ❌ Erro no processamento  \n"
                            all_markdown_content += f"**Erro:** {file_error}  \n\n"
                            all_markdown_content += "---\n\n"
                            processed_files.append({'name': original_name, 'success': False})
                            dbg('DOCS', f"❌ Erro em {original_name}: {file_error}")
                    else:
                        dbg('DOCS', f"❌ Arquivo extraído não encontrado: {original_name}")
                try:
                    if extracted_files_list:
                        extract_dir = os.path.dirname(extracted_files_list[0][0])
                        if os.path.exists(extract_dir):
                            shutil.rmtree(extract_dir)
                except Exception as cleanup_error:
                    dbg('DOCS', f"⚠️ Aviso: Erro na limpeza: {cleanup_error}")
                successful_files = [f for f in processed_files if f['success']]
                if successful_files:
                    success = True
                    markdown_content = all_markdown_content
                    error = None
                    final_filename = f"{final_filename} ({len(successful_files)}-{len(processed_files)} arquivos)"
                    dbg('DOCS', f"✅ RAR processado: {len(successful_files)}/{len(processed_files)} arquivos com sucesso")
                else:
                    return "Erro: Nenhum arquivo do RAR foi processado com sucesso"
            else:
                # Assistant direto com arquivos originais
                try:
                    files_to_send = [p for (p, _n) in extracted_files_list if os.path.exists(p)]
                    summary = generate_document_summary_from_files(files_to_send, max_tokens, pncp_data)
                    method_label = "Assistant (arquivos originais)"
                    summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data, method_label=method_label, markdown_filename=None)
                    if not summary_success:
                        dbg('DOCS', f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
                    try:
                        if extracted_files_list:
                            extract_dir = os.path.dirname(extracted_files_list[0][0])
                            if os.path.exists(extract_dir):
                                shutil.rmtree(extract_dir)
                    except Exception as cleanup_error:
                        print(f"⚠️ Aviso: Erro na limpeza: {cleanup_error}")
                    return summary
                finally:
                    pass
        else:
            dbg('DOCS', f"📄 Processando arquivo diretamente: {final_filename}")
            file_to_process = temp_path
            dbg('DOCS', f"Converter -> path='{file_to_process}' nome='{final_filename}'")

            if GVG_MARKDOWN:
                success, markdown_content, error = convert_document_to_markdown(file_to_process, final_filename)
                if not success:
                    return f"Erro na conversão: {error}"
                
                dbg('DOCS', "Salvando Markdown...")
                save_success, saved_path, save_error = save_markdown_file(markdown_content, final_filename, doc_url, processing_timestamp)
                if not save_success:
                    dbg('DOCS', f"Falha ao salvar Markdown: {save_error}")
                    return f"Erro ao salvar: {save_error}"
                summary = generate_document_summary(markdown_content, max_tokens, pncp_data)
                
                dbg('DOCS', f"Resumo gerado (len={len(summary) if isinstance(summary,str) else 'N/A'})")
                summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data, method_label="Docling + Assistant", markdown_filename=os.path.basename(saved_path) if save_success else None)
                if not summary_success:
                    dbg('DOCS', f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
                return summary
            else:
                # Assistant direto com arquivo original
                summary = generate_document_summary_from_files([file_to_process], max_tokens, pncp_data)
                method_label = "Assistant (arquivo original)"
                summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data, method_label=method_label, markdown_filename=None)
                if not summary_success:
                    dbg('DOCS', f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
                return summary
        # Common path (GVG_MARKDOWN True) continues below to save markdown + summary (already returned in direct paths)
        dbg('DOCS', "Salvando Markdown...")
        save_success, saved_path, save_error = save_markdown_file(markdown_content, final_filename, doc_url, processing_timestamp)
        if not save_success:
            dbg('DOCS', f"Falha ao salvar Markdown: {save_error}")
            return f"Erro ao salvar: {save_error}"
        summary = generate_document_summary(markdown_content, max_tokens, pncp_data)
        dbg('DOCS', f"Resumo gerado (len={len(summary) if isinstance(summary,str) else 'N/A'})")
        summary_success, summary_path, summary_error = save_summary_file(summary, final_filename, doc_url, processing_timestamp, pncp_data, method_label="Docling + Assistant", markdown_filename=os.path.basename(saved_path) if save_success else None)
        if not summary_success:
            dbg('DOCS', f"⚠️ Aviso: Erro ao salvar resumo: {summary_error}")
        return summary
    except Exception as e:
        return f"Erro inesperado no processamento: {str(e)}"
    finally:
        cleanup_temp_file(temp_path)

def summarize_document(doc_url, max_tokens=500, document_name=None, pncp_data=None):
    dbg('DOCS', f"summarize_document() url='{str(doc_url)[:80]}{'...' if doc_url and len(str(doc_url))>80 else ''}' nome='{document_name}' tokens={max_tokens}")
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
    'generate_document_summary',
    'generate_document_summary_from_files',
    'set_markdown_enabled',
    'fetch_documentos'
]


## Listagem de documentos centralizada em gvg_database.fetch_documentos