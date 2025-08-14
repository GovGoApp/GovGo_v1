"""
gvg_document_utils.py
Módulo para processamento avançado de documentos PNCP usando Docling
- Identificação automática de tipos de documentos (PDF, DOCX, XLSX, CSV, TXT, etc.)
- Parsing especializado por tipo de arquivo com Docling
- Extração e processamento de arquivos compactados (ZIP, RAR)
- Detecção e extração de tabelas, texto, imagens e gráficos
- Sumarização de conteúdo com OpenAI GPT
- Estrutura extensível para adicionar novos tipos de documentos
"""

import os
import re
import json
import hashlib
import requests
import tempfile
import shutil
import zipfile
import rarfile
import mimetypes
import pandas as pd
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse, unquote
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configurar Docling
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat, Document
    from docling.datamodel.pipeline_options import PipelineOptions
    #from docling.document_processor import DocumentProcessor
    DOCLING_AVAILABLE = True
except ImportError:
    print("AVISO: Biblioteca Docling não encontrada. Algumas funcionalidades estarão indisponíveis.")
    DOCLING_AVAILABLE = False

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gvg_document_utils')

# Carregar variáveis de ambiente
load_dotenv()

# Cliente OpenAI
#client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
client = OpenAI(api_key="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")

# Constantes
TEMP_DIR = os.path.join(tempfile.gettempdir(), "gvg_documents")
CACHE_DIR = os.path.join(TEMP_DIR, "cache")
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 11 MB
TIMEOUT = 60  # 60 segundos para download
DEFAULT_PARSE_TIMEOUT = 300  # 5 minutos para parsing

# Mime types e extensões suportados
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.ms-excel': '.xls',
    'text/csv': '.csv',
    'text/plain': '.txt',
    'text/markdown': '.md',
    'application/json': '.json',
    'application/xml': '.xml',
    'text/html': '.html',
    'application/zip': '.zip',
    'application/x-rar-compressed': '.rar',
    'application/vnd.rar': '.rar',
    'application/octet-stream': '.bin'  # Genérico
}

# Extensões suportadas
SUPPORTED_EXTENSIONS = {
    '.pdf': 'PDF',
    '.docx': 'DOCX',
    '.xlsx': 'XLSX',
    '.xls': 'XLS',
    '.csv': 'CSV',
    '.txt': 'TXT',
    '.md': 'Markdown',
    '.json': 'JSON',
    '.xml': 'XML',
    '.html': 'HTML',
    '.zip': 'ZIP',
    '.rar': 'RAR'
}

# Criar diretórios temporários
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

#####################################
# Classes Base para Processamento
#####################################

class DocumentInfo:
    """Classe para armazenar informações sobre um documento"""
    
    def __init__(self, url: str = "", file_path: str = "", 
                 title: str = "", doc_type: str = "", 
                 mime_type: str = "", extension: str = "",
                 size: int = 0, metadata: Dict = None):
        """
        Inicializa as informações do documento
        
        Args:
            url: URL do documento (se online)
            file_path: Caminho local do arquivo
            title: Título ou nome do documento
            doc_type: Tipo do documento (PDF, DOCX, etc.)
            mime_type: MIME type do documento
            extension: Extensão do arquivo
            size: Tamanho em bytes
            metadata: Metadados adicionais
        """
        self.url = url
        self.file_path = file_path
        self.title = title or os.path.basename(file_path or url or "Documento sem título")
        self.doc_type = doc_type
        self.mime_type = mime_type
        self.extension = extension
        self.size = size
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.success = False
        self.error = None
        self.content_info = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte as informações para dicionário"""
        return {
            "url": self.url,
            "file_path": self.file_path,
            "title": self.title,
            "doc_type": self.doc_type,
            "mime_type": self.mime_type,
            "extension": self.extension,
            "size": self.size,
            "size_formatted": self.get_size_formatted(),
            "timestamp": self.timestamp,
            "success": self.success,
            "error": str(self.error) if self.error else None,
            "metadata": self.metadata,
            "content_info": self.content_info
        }
    
    def get_size_formatted(self) -> str:
        """Retorna o tamanho formatado (KB, MB, etc.)"""
        if not self.size:
            return "Desconhecido"
        
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.2f} {unit}"
            size /= 1024

class DocumentContent:
    """Classe para armazenar o conteúdo extraído de um documento"""
    
    def __init__(self, doc_info: DocumentInfo):
        """
        Inicializa o conteúdo do documento
        
        Args:
            doc_info: Informações do documento
        """
        self.doc_info = doc_info
        self.text = ""
        self.tables = []
        self.images = []
        self.paragraphs = []
        self.headings = []
        self.metadata = {}
        self.raw_content = None
        self.processed_elements = []
        self.summary = ""
        self.keywords = ""
    
    def to_dict(self, include_raw=False) -> Dict[str, Any]:
        """
        Converte o conteúdo para dicionário
        
        Args:
            include_raw: Se True, inclui o conteúdo raw (pode ser grande)
        
        Returns:
            Dicionário com o conteúdo
        """
        result = {
            "doc_info": self.doc_info.to_dict(),
            "text_length": len(self.text),
            "text_preview": self.text[:500] + "..." if len(self.text) > 500 else self.text,
            "tables_count": len(self.tables),
            "images_count": len(self.images),
            "paragraphs_count": len(self.paragraphs),
            "headings_count": len(self.headings),
            "metadata": self.metadata,
            "summary": self.summary,
            "keywords": self.keywords,
            "processed_elements_count": len(self.processed_elements),
        }
        
        if include_raw and self.raw_content is not None:
            if isinstance(self.raw_content, (dict, list)):
                result["raw_content"] = self.raw_content
            else:
                result["raw_content"] = str(self.raw_content)
        
        return result

class BaseDocumentParser:
    """Classe base para parsers de documentos"""
    
    def __init__(self):
        """Inicializa o parser com configurações padrão"""
        self.doc_converter = DocumentConverter() if DOCLING_AVAILABLE else None
        self.supports_docling = DOCLING_AVAILABLE
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """
        Verifica se o parser pode processar este documento
        
        Args:
            doc_info: Informações do documento
            
        Returns:
            True se o parser pode processar, False caso contrário
        """
        return False
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """
        Processa o documento e extrai conteúdo
        
        Args:
            doc_info: Informações do documento
            
        Returns:
            DocumentContent com o conteúdo extraído
        """
        content = DocumentContent(doc_info)
        content.text = "Método de parsing não implementado para este tipo de documento"
        return content
    
    def extract_text(self, document: Any) -> str:
        """
        Extrai texto do documento Docling
        
        Args:
            document: Documento Docling
            
        Returns:
            Texto extraído
        """
        if not document:
            return ""
        
        try:
            if hasattr(document, 'export_to_text'):
                raw_text = document.export_to_text()
                return self._clean_text(raw_text)
            return ""
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Limpa e formata o texto extraído
        
        Args:
            text: Texto bruto extraído
            
        Returns:
            Texto limpo e formatado
        """
        if not text:
            return ""
        
        # Remover caracteres markdown desnecessários
        text = re.sub(r'\|\n\|---+.*?\n', '\n', text)
        text = re.sub(r'^\|---+.*?\n', '', text, flags=re.MULTILINE)
        
        # Limpar linhas vazias excessivas
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remover pipes desnecessários no início e fim das linhas
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('|') and line.endswith('|'):
                # Converter linha de tabela markdown em texto limpo
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if cells and any(cell for cell in cells):  # Se há conteúdo nas células
                    cleaned_lines.append(' | '.join(cells))
            elif line and not line.startswith('|---'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_metadata(self, document: Any) -> Dict:
        """
        Extrai metadados do documento
        
        Args:
            document: Documento Docling
            
        Returns:
            Dicionário com metadados
        """
        metadata = {}
        
        try:
            if document and hasattr(document, 'metadata'):
                metadata.update(document.metadata)
                
            # Informações do documento Docling
            if document:
                if hasattr(document, 'pages'):
                    metadata['num_pages'] = len(document.pages)
                
                if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                    metadata['num_elements'] = len(document.body.elements)
                elif hasattr(document, 'elements'):
                    metadata['num_elements'] = len(document.elements)
                    
        except Exception as e:
            logger.error(f"Erro ao extrair metadados: {e}")
            
        return metadata

#####################################
# Parsers Específicos por Tipo
#####################################

class PDFDocumentParser(BaseDocumentParser):
    """Parser específico para documentos PDF"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um PDF"""
        return doc_info.extension.lower() == '.pdf' or doc_info.mime_type == 'application/pdf'
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa documento PDF"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo PDF não encontrado"
            return content
        
        try:
            if not self.supports_docling:
                content.doc_info.error = "Biblioteca Docling não disponível para processar PDF"
                return content
            
            # Usar Docling para processar o PDF
            file_path = Path(doc_info.file_path)
            pipeline_options = PipelineOptions(
                input_format=InputFormat.PDF,
                extract_tables=True,
                extract_charts=True,
                extract_images=True,
                extract_text=True,
                extract_formulas=True,
                parse_rich_text=True,
                extract_metadata=True
            )
            
            document = self.doc_converter.convert(file_path, pipeline_options=pipeline_options)
            docling_doc = document.document
            
            # Extrair texto
            content.text = self.extract_text(docling_doc)
            
            # Extrair metadados
            content.metadata = self.extract_metadata(docling_doc)
            
            # Extrair elementos como tabelas, imagens, etc.
            content = self._extract_elements(docling_doc, content)
            
            # Armazenar documento processado
            content.raw_content = docling_doc
            content.doc_info.success = True
            content.doc_info.content_info = {
                "pages": content.metadata.get("num_pages", 0),
                "tables": len(content.tables),
                "images": len(content.images),
                "paragraphs": len(content.paragraphs),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar PDF: {e}")
            content.doc_info.error = f"Erro ao processar PDF: {str(e)}"
            return content
    
    def _extract_elements(self, document: Any, content: DocumentContent) -> DocumentContent:
        """
        Extrai elementos específicos do PDF (tabelas, imagens, etc.)
        
        Args:
            document: Documento Docling
            content: DocumentContent para preencher
            
        Returns:
            DocumentContent atualizado
        """
        if not document:
            return content
        
        try:
            # Extrair tabelas
            tables = []
            elements = []
            
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                elements = document.body.elements
            elif hasattr(document, 'elements'):
                elements = document.elements
            
            for element in elements:
                # Identificar tipo de elemento
                element_type = getattr(element, 'element_type', '')
                label = getattr(element, 'label', '')
                text = getattr(element, 'text', '')
                
                # Processar elemento baseado no tipo
                if 'table' in str(element_type).lower() or 'table' in str(label).lower():
                    # Processar tabela
                    table_data = self._process_table(element)
                    if table_data:
                        tables.append(table_data)
                        content.tables.append(table_data)
                
                elif 'image' in str(element_type).lower() or 'figure' in str(label).lower():
                    # Processar imagem
                    image_data = self._process_image(element)
                    if image_data:
                        content.images.append(image_data)
                
                elif 'paragraph' in str(element_type).lower():
                    # Processar parágrafo
                    if text:
                        content.paragraphs.append({
                            'text': text,
                            'bbox': getattr(element, 'bbox', None)
                        })
                
                elif 'heading' in str(element_type).lower() or 'title' in str(label).lower():
                    # Processar título/cabeçalho
                    if text:
                        content.headings.append({
                            'text': text,
                            'level': getattr(element, 'level', 1),
                            'bbox': getattr(element, 'bbox', None)
                        })
                
                # Armazenar todos os elementos processados
                content.processed_elements.append({
                    'type': str(element_type),
                    'label': str(label),
                    'text': text[:100] + '...' if len(text) > 100 else text
                })
            
        except Exception as e:
            logger.error(f"Erro ao extrair elementos do PDF: {e}")
            
        return content
    
    def _process_table(self, table_element: Any) -> Dict:
        """
        Processa elemento de tabela
        
        Args:
            table_element: Elemento de tabela do Docling
            
        Returns:
            Dicionário com dados da tabela
        """
        table_data = {
            'bbox': getattr(table_element, 'bbox', None),
            'text': getattr(table_element, 'text', ''),
            'element_type': str(getattr(table_element, 'element_type', '')),
            'cells': []
        }
        
        # Extrair células da tabela se disponível
        if hasattr(table_element, 'table_cells') and table_element.table_cells:
            rows = set()
            cols = set()
            
            # Primeiro passo: identificar número de linhas e colunas
            for cell in table_element.table_cells:
                row_idx = getattr(cell, 'row_index', None)
                col_idx = getattr(cell, 'col_index', None)
                
                if row_idx is not None:
                    rows.add(row_idx)
                if col_idx is not None:
                    cols.add(col_idx)
            
            # Criar matriz vazia
            matrix = [[None for _ in range(len(cols))] for _ in range(len(rows))]
            
            # Preencher matriz com células
            for cell in table_element.table_cells:
                row_idx = getattr(cell, 'row_index', None)
                col_idx = getattr(cell, 'col_index', None)
                text = getattr(cell, 'text', '')
                
                if row_idx is not None and col_idx is not None:
                    # Converter para índices 0-based
                    row_idx_norm = sorted(list(rows)).index(row_idx)
                    col_idx_norm = sorted(list(cols)).index(col_idx)
                    
                    matrix[row_idx_norm][col_idx_norm] = text
                    
                    cell_data = {
                        'text': text,
                        'bbox': getattr(cell, 'bbox', None),
                        'row': row_idx,
                        'col': col_idx,
                        'row_span': getattr(cell, 'row_span', 1),
                        'col_span': getattr(cell, 'col_span', 1)
                    }
                    table_data['cells'].append(cell_data)
            
            # Adicionar matriz de dados
            table_data['matrix'] = matrix
            table_data['num_rows'] = len(rows)
            table_data['num_cols'] = len(cols)
        
        return table_data
    
    def _process_image(self, image_element: Any) -> Dict:
        """
        Processa elemento de imagem
        
        Args:
            image_element: Elemento de imagem do Docling
            
        Returns:
            Dicionário com dados da imagem
        """
        image_data = {
            'bbox': getattr(image_element, 'bbox', None),
            'text': getattr(image_element, 'text', ''),  # Possível texto alt ou caption
            'element_type': str(getattr(image_element, 'element_type', '')),
            'width': getattr(image_element, 'width', None),
            'height': getattr(image_element, 'height', None)
        }
        
        # Tentar extrair dados da imagem se disponível
        if hasattr(image_element, 'image_data') and image_element.image_data:
            image_data['format'] = getattr(image_element.image_data, 'format', None)
            image_data['has_data'] = True
        else:
            image_data['has_data'] = False
        
        return image_data

class ExcelDocumentParser(BaseDocumentParser):
    """Parser específico para documentos Excel (XLSX, XLS)"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um Excel"""
        return doc_info.extension.lower() in ['.xlsx', '.xls'] or doc_info.mime_type in [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ]
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa documento Excel"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo Excel não encontrado"
            return content
        
        try:
            # Primeiro, ler com pandas para obter estrutura das abas
            sheets_data = self._read_excel_with_pandas(doc_info.file_path)
            
            if not sheets_data:
                content.doc_info.error = "Falha ao ler arquivo Excel com pandas"
                return content
            
            # Tentar com Docling se disponível
            if self.supports_docling:
                # Usar Docling para processamento adicional
                file_path = Path(doc_info.file_path)
                document = self.doc_converter.convert(file_path)
                docling_doc = document.document
                
                # Extrair texto
                content.text = self.extract_text(docling_doc)
                
                # Extrair metadados
                content.metadata = self.extract_metadata(docling_doc)
                
                # Armazenar documento processado
                content.raw_content = docling_doc
            
            # Extrair tabelas estruturadas (sempre com pandas, mesmo sem Docling)
            structured_tables = self._extract_structured_tables(sheets_data)
            
            # Adicionar tabelas estruturadas ao conteúdo
            for sheet_name, tables in structured_tables.items():
                for table in tables:
                    content.tables.append(table)
            
            # Criar texto a partir das tabelas se não tiver texto
            if not content.text:
                content.text = self._create_text_from_tables(structured_tables)
            
            # Adicionar metadados das abas
            sheet_info = {}
            for sheet_name, df in sheets_data.items():
                sheet_info[sheet_name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist(),
                    'has_data': not df.empty
                }
            
            # Adicionar metadados se não foram extraídos pelo Docling
            if not content.metadata:
                content.metadata = {
                    'num_sheets': len(sheets_data),
                    'sheet_names': list(sheets_data.keys()),
                    'sheets_info': sheet_info
                }
            else:
                content.metadata.update({
                    'num_sheets': len(sheets_data),
                    'sheet_names': list(sheets_data.keys()),
                    'sheets_info': sheet_info
                })
            
            content.doc_info.success = True
            content.doc_info.content_info = {
                "sheets": len(sheets_data),
                "tables": len(content.tables),
                "total_rows": sum(len(df) for df in sheets_data.values()),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar Excel: {e}")
            content.doc_info.error = f"Erro ao processar Excel: {str(e)}"
            return content
    
    def _read_excel_with_pandas(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """
        Lê arquivo Excel com pandas para obter estrutura das abas
        
        Args:
            file_path: Caminho para o arquivo XLSX
            
        Returns:
            Dicionário com DataFrames de cada aba
        """
        try:
            # Ler todas as abas do Excel
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets_data[sheet_name] = df
                
            return sheets_data
            
        except Exception as e:
            logger.error(f"Erro ao ler Excel com pandas: {e}")
            return {}
    
    def _extract_structured_tables(self, sheets_data: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
        """
        Extrai tabelas estruturadas de cada aba usando pandas
        
        Args:
            sheets_data: Dados das abas do Excel
            
        Returns:
            Dicionário com tabelas estruturadas por aba
        """
        structured_tables = {}
        
        for sheet_name, df in sheets_data.items():
            tables = []
            
            if not df.empty:
                # Converter DataFrame para formato estruturado
                table_data = {
                    'sheet_name': sheet_name,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist(),
                    'data': []
                }
                
                # Adicionar dados linha por linha
                for index, row in df.iterrows():
                    row_data = {}
                    for col in df.columns:
                        value = row[col]
                        # Tratar valores NaN
                        if pd.isna(value):
                            row_data[str(col)] = ""
                        else:
                            row_data[str(col)] = str(value)
                    table_data['data'].append(row_data)
                
                tables.append(table_data)
            
            structured_tables[sheet_name] = tables
        
        return structured_tables
    
    def _create_text_from_tables(self, structured_tables: Dict[str, List[Dict]]) -> str:
        """
        Cria texto a partir das tabelas estruturadas
        
        Args:
            structured_tables: Tabelas estruturadas por aba
            
        Returns:
            Texto gerado
        """
        text_parts = []
        
        for sheet_name, tables in structured_tables.items():
            text_parts.append(f"== Aba: {sheet_name} ==\n")
            
            for table in tables:
                # Adicionar cabeçalho
                text_parts.append(f"Tabela com {table['rows']} linhas e {table['columns']} colunas")
                text_parts.append(f"Colunas: {', '.join(table['column_names'])}\n")
                
                # Adicionar dados (limitar a 50 linhas para não ficar muito grande)
                max_rows = min(50, len(table['data']))
                for i, row_data in enumerate(table['data'][:max_rows]):
                    row_text = " | ".join(f"{k}: {v}" for k, v in row_data.items())
                    text_parts.append(f"Linha {i+1}: {row_text}")
                
                if len(table['data']) > max_rows:
                    text_parts.append(f"... e mais {len(table['data']) - max_rows} linhas\n")
                
                text_parts.append("")  # Linha em branco entre tabelas
        
        return "\n".join(text_parts)

class DocxDocumentParser(BaseDocumentParser):
    """Parser específico para documentos DOCX"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um DOCX"""
        return doc_info.extension.lower() == '.docx' or doc_info.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa documento DOCX"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo DOCX não encontrado"
            return content
        
        try:
            if not self.supports_docling:
                content.doc_info.error = "Biblioteca Docling não disponível para processar DOCX"
                return content
            
            # Usar Docling para processar o DOCX
            file_path = Path(doc_info.file_path)
            pipeline_options = PipelineOptions(
                input_format=InputFormat.DOCX,
                extract_tables=True,
                extract_images=True,
                extract_text=True,
                parse_rich_text=True,
                extract_metadata=True
            )
            
            document = self.doc_converter.convert(file_path, pipeline_options=pipeline_options)
            docling_doc = document.document
            
            # Extrair texto
            content.text = self.extract_text(docling_doc)
            
            # Extrair metadados
            content.metadata = self.extract_metadata(docling_doc)
            
            # Extrair elementos como tabelas, imagens, etc.
            content = self._extract_elements(docling_doc, content)
            
            # Armazenar documento processado
            content.raw_content = docling_doc
            content.doc_info.success = True
            content.doc_info.content_info = {
                "paragraphs": len(content.paragraphs),
                "tables": len(content.tables),
                "images": len(content.images),
                "headings": len(content.headings),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar DOCX: {e}")
            content.doc_info.error = f"Erro ao processar DOCX: {str(e)}"
            return content
    
    def _extract_elements(self, document: Any, content: DocumentContent) -> DocumentContent:
        """
        Extrai elementos específicos do DOCX (tabelas, imagens, etc.)
        
        Args:
            document: Documento Docling
            content: DocumentContent para preencher
            
        Returns:
            DocumentContent atualizado
        """
        if not document:
            return content
        
        try:
            # Extrair tabelas e outros elementos
            elements = []
            
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                elements = document.body.elements
            elif hasattr(document, 'elements'):
                elements = document.elements
            
            for element in elements:
                # Identificar tipo de elemento
                element_type = getattr(element, 'element_type', '')
                label = getattr(element, 'label', '')
                text = getattr(element, 'text', '')
                
                # Processar elemento baseado no tipo
                if 'table' in str(element_type).lower() or 'table' in str(label).lower():
                    # Processar tabela
                    table_data = self._process_table(element)
                    if table_data:
                        content.tables.append(table_data)
                
                elif 'image' in str(element_type).lower() or 'figure' in str(label).lower():
                    # Processar imagem
                    image_data = self._process_image(element)
                    if image_data:
                        content.images.append(image_data)
                
                elif 'paragraph' in str(element_type).lower():
                    # Processar parágrafo
                    if text:
                        content.paragraphs.append({
                            'text': text,
                            'style': getattr(element, 'style', None)
                        })
                
                elif 'heading' in str(element_type).lower() or 'title' in str(label).lower():
                    # Processar título/cabeçalho
                    if text:
                        content.headings.append({
                            'text': text,
                            'level': getattr(element, 'level', 1)
                        })
                
                # Armazenar todos os elementos processados
                content.processed_elements.append({
                    'type': str(element_type),
                    'label': str(label),
                    'text': text[:100] + '...' if len(text) > 100 else text
                })
            
        except Exception as e:
            logger.error(f"Erro ao extrair elementos do DOCX: {e}")
            
        return content
    
    def _process_table(self, table_element: Any) -> Dict:
        """
        Processa elemento de tabela
        
        Args:
            table_element: Elemento de tabela do Docling
            
        Returns:
            Dicionário com dados da tabela
        """
        table_data = {
            'text': getattr(table_element, 'text', ''),
            'element_type': str(getattr(table_element, 'element_type', '')),
            'cells': []
        }
        
        # Extrair células da tabela se disponível
        if hasattr(table_element, 'table_cells') and table_element.table_cells:
            rows = set()
            cols = set()
            
            # Primeiro passo: identificar número de linhas e colunas
            for cell in table_element.table_cells:
                row_idx = getattr(cell, 'row_index', None)
                col_idx = getattr(cell, 'col_index', None)
                
                if row_idx is not None:
                    rows.add(row_idx)
                if col_idx is not None:
                    cols.add(col_idx)
            
            # Criar matriz vazia
            num_rows = len(rows) if rows else 0
            num_cols = len(cols) if cols else 0
            matrix = [[None for _ in range(num_cols)] for _ in range(num_rows)]
            
            # Preencher matriz com células
            for cell in table_element.table_cells:
                row_idx = getattr(cell, 'row_index', None)
                col_idx = getattr(cell, 'col_index', None)
                text = getattr(cell, 'text', '')
                
                if row_idx is not None and col_idx is not None and rows and cols:
                    # Converter para índices 0-based
                    row_idx_norm = sorted(list(rows)).index(row_idx) if row_idx in rows else None
                    col_idx_norm = sorted(list(cols)).index(col_idx) if col_idx in cols else None
                    
                    if row_idx_norm is not None and col_idx_norm is not None:
                        matrix[row_idx_norm][col_idx_norm] = text
                    
                    cell_data = {
                        'text': text,
                        'row': row_idx,
                        'col': col_idx,
                        'row_span': getattr(cell, 'row_span', 1),
                        'col_span': getattr(cell, 'col_span', 1)
                    }
                    table_data['cells'].append(cell_data)
            
            # Adicionar matriz de dados
            table_data['matrix'] = matrix
            table_data['num_rows'] = num_rows
            table_data['num_cols'] = num_cols
        
        return table_data
    
    def _process_image(self, image_element: Any) -> Dict:
        """
        Processa elemento de imagem
        
        Args:
            image_element: Elemento de imagem do Docling
            
        Returns:
            Dicionário com dados da imagem
        """
        image_data = {
            'text': getattr(image_element, 'text', ''),  # Possível texto alt ou caption
            'element_type': str(getattr(image_element, 'element_type', '')),
            'width': getattr(image_element, 'width', None),
            'height': getattr(image_element, 'height', None)
        }
        
        # Tentar extrair dados da imagem se disponível
        if hasattr(image_element, 'image_data') and image_element.image_data:
            image_data['format'] = getattr(image_element.image_data, 'format', None)
            image_data['has_data'] = True
        else:
            image_data['has_data'] = False
        
        return image_data

class TextDocumentParser(BaseDocumentParser):
    """Parser para documentos de texto simples (TXT, CSV, etc.)"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um documento de texto"""
        return doc_info.extension.lower() in ['.txt', '.csv', '.md'] or doc_info.mime_type in [
            'text/plain', 'text/csv', 'text/markdown'
        ]
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa documento de texto"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo de texto não encontrado"
            return content
        
        try:
            # Verificar se é CSV (caso especial)
            if doc_info.extension.lower() == '.csv' or doc_info.mime_type == 'text/csv':
                return self._parse_csv(doc_info)
            
            # Para outros arquivos de texto, ler diretamente
            with open(doc_info.file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            
            content.text = text
            
            # Extrair parágrafos (linhas não vazias)
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            for p in paragraphs:
                content.paragraphs.append({'text': p})
            
            # Para markdown, tentar identificar cabeçalhos
            if doc_info.extension.lower() == '.md' or doc_info.mime_type == 'text/markdown':
                for line in text.split('\n'):
                    if re.match(r'^#{1,6}\s+', line):
                        level = len(line) - len(line.lstrip('#'))
                        text = line.lstrip('#').strip()
                        content.headings.append({
                            'text': text,
                            'level': level
                        })
            
            # Metadados básicos
            content.metadata = {
                'size': len(text),
                'lines': text.count('\n') + 1,
                'paragraphs': len(content.paragraphs),
                'format': doc_info.extension.lower().lstrip('.')
            }
            
            content.doc_info.success = True
            content.doc_info.content_info = {
                "paragraphs": len(content.paragraphs),
                "headings": len(content.headings),
                "lines": content.metadata.get("lines", 0),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar texto: {e}")
            content.doc_info.error = f"Erro ao processar texto: {str(e)}"
            return content
    
    def _parse_csv(self, doc_info: DocumentInfo) -> DocumentContent:
        """
        Processa arquivo CSV
        
        Args:
            doc_info: Informações do documento
            
        Returns:
            DocumentContent com conteúdo do CSV
        """
        content = DocumentContent(doc_info)
        
        try:
            # Tentar diferentes delimitadores
            delimiters = [',', ';', '\t', '|']
            df = None
            
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(doc_info.file_path, delimiter=delimiter, encoding='utf-8')
                    if len(df.columns) > 1:
                        break
                except:
                    continue
            
            if df is None:
                # Última tentativa com detecção automática
                df = pd.read_csv(doc_info.file_path, encoding='utf-8')
            
            # Converter DataFrame para texto
            text_parts = []
            text_parts.append(f"CSV com {len(df)} linhas e {len(df.columns)} colunas")
            text_parts.append(f"Colunas: {', '.join(df.columns.tolist())}\n")
            
            # Adicionar primeiras 50 linhas como texto
            max_rows = min(50, len(df))
            for i, row in df.head(max_rows).iterrows():
                row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
                text_parts.append(f"Linha {i+1}: {row_text}")
            
            if len(df) > max_rows:
                text_parts.append(f"... e mais {len(df) - max_rows} linhas\n")
            
            content.text = "\n".join(text_parts)
            
            # Criar tabela estruturada
            table_data = {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist(),
                'data': []
            }
            
            # Adicionar dados linha por linha
            for i, row in df.iterrows():
                row_data = {}
                for col in df.columns:
                    value = row[col]
                    # Tratar valores NaN
                    if pd.isna(value):
                        row_data[str(col)] = ""
                    else:
                        row_data[str(col)] = str(value)
                table_data['data'].append(row_data)
            
            content.tables.append(table_data)
            
            # Metadados
            content.metadata = {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist(),
                'delimiter_detected': delimiter if 'delimiter' in locals() else 'auto'
            }
            
            content.doc_info.success = True
            content.doc_info.content_info = {
                "rows": len(df),
                "columns": len(df.columns),
                "tables": 1,
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {e}")
            content.doc_info.error = f"Erro ao processar CSV: {str(e)}"
            return content

class ArchiveDocumentParser(BaseDocumentParser):
    """Parser para arquivos compactados (ZIP, RAR)"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um arquivo compactado"""
        return doc_info.extension.lower() in ['.zip', '.rar'] or doc_info.mime_type in [
            'application/zip', 'application/x-rar-compressed', 'application/vnd.rar'
        ]
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa arquivo compactado"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo compactado não encontrado"
            return content
        
        try:
            # Criar diretório temporário para extrair
            extract_dir = os.path.join(TEMP_DIR, 'extracted', os.path.basename(doc_info.file_path).replace('.', '_'))
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extrair arquivos
            if doc_info.extension.lower() == '.zip':
                self._extract_zip(doc_info.file_path, extract_dir)
            elif doc_info.extension.lower() == '.rar':
                self._extract_rar(doc_info.file_path, extract_dir)
            else:
                content.doc_info.error = f"Formato de arquivo compactado não suportado: {doc_info.extension}"
                return content
            
            # Listar arquivos extraídos
            extracted_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, extract_dir)
                    file_size = os.path.getsize(file_path)
                    
                    extracted_files.append({
                        'name': file,
                        'path': file_path,
                        'relative_path': rel_path,
                        'size': file_size,
                        'extension': os.path.splitext(file)[1].lower()
                    })
            
            # Processar cada arquivo extraído
            document_processor = DocumentProcessor()
            processed_files = []
            all_text = []
            
            for file_info in extracted_files:
                # Criar DocumentInfo para o arquivo
                file_doc_info = DocumentInfo(
                    file_path=file_info['path'],
                    title=file_info['name'],
                    extension=file_info['extension'],
                    size=file_info['size']
                )
                
                # Identificar tipo e MIME type
                file_doc_info.mime_type, _ = mimetypes.guess_type(file_info['path'])
                file_doc_info.doc_type = SUPPORTED_EXTENSIONS.get(file_info['extension'], 'Desconhecido')
                
                # Processar o arquivo
                file_content = document_processor.process_document(file_doc_info)
                
                # Adicionar ao resultado
                if file_content and file_content.doc_info.success:
                    processed_files.append({
                        'file_info': file_info,
                        'content': file_content.to_dict(include_raw=False),
                        'success': True
                    })
                    
                    # Acumular texto
                    if file_content.text:
                        all_text.append(f"=== {file_info['name']} ===")
                        all_text.append(file_content.text[:1000] + "..." if len(file_content.text) > 1000 else file_content.text)
                        all_text.append("")
                    
                    # Acumular tabelas
                    for table in file_content.tables:
                        content.tables.append(table)
                else:
                    processed_files.append({
                        'file_info': file_info,
                        'error': file_content.doc_info.error if file_content else "Falha no processamento",
                        'success': False
                    })
            
            # Consolidar resultados
            content.text = "\n".join(all_text)
            content.metadata = {
                'archive_type': doc_info.extension.lower().lstrip('.'),
                'total_files': len(extracted_files),
                'processed_files': len([f for f in processed_files if f['success']]),
                'files': [
                    {
                        'name': f['file_info']['name'],
                        'relative_path': f['file_info']['relative_path'],
                        'size': f['file_info']['size'],
                        'extension': f['file_info']['extension'],
                        'success': f['success']
                    } for f in processed_files
                ]
            }
            
            # Armazenar resultados completos
            content.raw_content = {
                'extract_dir': extract_dir,
                'processed_files': processed_files
            }
            
            content.doc_info.success = True
            content.doc_info.content_info = {
                "total_files": len(extracted_files),
                "processed_files": len([f for f in processed_files if f['success']]),
                "tables": len(content.tables),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo compactado: {e}")
            content.doc_info.error = f"Erro ao processar arquivo compactado: {str(e)}"
            return content
        
    def _extract_zip(self, zip_path: str, extract_dir: str) -> bool:
        """
        Extrai arquivo ZIP
        
        Args:
            zip_path: Caminho para o arquivo ZIP
            extract_dir: Diretório para extração
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            return True
        except Exception as e:
            logger.error(f"Erro ao extrair ZIP: {e}")
            return False
    
    def _extract_rar(self, rar_path: str, extract_dir: str) -> bool:
        """
        Extrai arquivo RAR
        
        Args:
            rar_path: Caminho para o arquivo RAR
            extract_dir: Diretório para extração
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            with rarfile.RarFile(rar_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)
            return True
        except Exception as e:
            logger.error(f"Erro ao extrair RAR: {e}")
            return False

class HTMLDocumentParser(BaseDocumentParser):
    """Parser para documentos HTML"""
    
    def can_parse(self, doc_info: DocumentInfo) -> bool:
        """Verifica se é um HTML"""
        return doc_info.extension.lower() == '.html' or doc_info.mime_type == 'text/html'
    
    def parse(self, doc_info: DocumentInfo) -> DocumentContent:
        """Processa documento HTML"""
        content = DocumentContent(doc_info)
        
        if not os.path.exists(doc_info.file_path):
            content.doc_info.error = "Arquivo HTML não encontrado"
            return content
        
        try:
            # Tentar usar Docling se disponível
            if self.supports_docling:
                file_path = Path(doc_info.file_path)
                pipeline_options = PipelineOptions(
                    input_format=InputFormat.HTML,
                    extract_tables=True,
                    extract_images=True,
                    extract_text=True,
                    parse_rich_text=True,
                    extract_metadata=True
                )
                
                document = self.doc_converter.convert(file_path, pipeline_options=pipeline_options)
                docling_doc = document.document
                
                # Extrair texto
                content.text = self.extract_text(docling_doc)
                
                # Extrair metadados
                content.metadata = self.extract_metadata(docling_doc)
                
                # Extrair elementos como tabelas, imagens, etc.
                content = self._extract_elements(docling_doc, content)
                
                # Armazenar documento processado
                content.raw_content = docling_doc
            else:
                # Alternativa: usar BeautifulSoup para extrair texto
                try:
                    from bs4 import BeautifulSoup
                    
                    with open(doc_info.file_path, 'r', encoding='utf-8', errors='replace') as f:
                        html = f.read()
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extrair metadados
                    content.metadata = {
                        'title': soup.title.string if soup.title else None,
                        'meta': {}
                    }
                    
                    for meta in soup.find_all('meta'):
                        if meta.get('name') and meta.get('content'):
                            content.metadata['meta'][meta['name']] = meta['content']
                    
                    # Extrair texto
                    text_parts = []
                    
                    # Cabeçalhos
                    for i in range(1, 7):
                        for heading in soup.find_all(f'h{i}'):
                            text = heading.get_text().strip()
                            if text:
                                content.headings.append({
                                    'text': text,
                                    'level': i
                                })
                                text_parts.append(f"{'#' * i} {text}")
                    
                    # Parágrafos
                    for p in soup.find_all('p'):
                        text = p.get_text().strip()
                        if text:
                            content.paragraphs.append({'text': text})
                            text_parts.append(text)
                    
                    # Tabelas
                    for table in soup.find_all('table'):
                        table_data = {
                            'rows': len(table.find_all('tr')),
                            'columns': 0,
                            'cells': []
                        }
                        
                        rows = []
                        for i, tr in enumerate(table.find_all('tr')):
                            row = []
                            for j, cell in enumerate(tr.find_all(['td', 'th'])):
                                text = cell.get_text().strip()
                                row.append(text)
                                
                                table_data['cells'].append({
                                    'row': i,
                                    'col': j,
                                    'text': text,
                                    'is_header': cell.name == 'th'
                                })
                            
                            if row:
                                rows.append(row)
                                table_data['columns'] = max(table_data['columns'], len(row))
                        
                        if rows:
                            table_data['matrix'] = rows
                            content.tables.append(table_data)
                            
                            # Adicionar tabela ao texto
                            text_parts.append("\nTabela:")
                            for row in rows:
                                text_parts.append(" | ".join(row))
                    
                    content.text = "\n\n".join(text_parts)
                except ImportError:
                    # Fallback: apenas ler o arquivo
                    with open(doc_info.file_path, 'r', encoding='utf-8', errors='replace') as f:
                        html = f.read()
                    
                    # Remover tags HTML (simplificado)
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = re.sub(r'\s+', ' ', text)
                    content.text = text.strip()
            
            content.doc_info.success = True
            content.doc_info.content_info = {
                "paragraphs": len(content.paragraphs),
                "tables": len(content.tables),
                "images": len(content.images),
                "headings": len(content.headings),
                "text_length": len(content.text)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao processar HTML: {e}")
            content.doc_info.error = f"Erro ao processar HTML: {str(e)}"
            return content
    
    def _extract_elements(self, document: Any, content: DocumentContent) -> DocumentContent:
        """
        Extrai elementos específicos do HTML (tabelas, imagens, etc.)
        
        Args:
            document: Documento Docling
            content: DocumentContent para preencher
            
        Returns:
            DocumentContent atualizado
        """
        if not document:
            return content
        
        try:
            # Extrair tabelas e outros elementos
            elements = []
            
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                elements = document.body.elements
            elif hasattr(document, 'elements'):
                elements = document.elements
            
            for element in elements:
                # Identificar tipo de elemento
                element_type = getattr(element, 'element_type', '')
                label = getattr(element, 'label', '')
                text = getattr(element, 'text', '')
                
                # Processar elemento baseado no tipo
                if 'table' in str(element_type).lower() or 'table' in str(label).lower():
                    # Processar tabela (simplificado)
                    table_data = {
                        'text': text,
                        'element_type': str(element_type)
                    }
                    content.tables.append(table_data)
                
                elif 'image' in str(element_type).lower() or 'figure' in str(label).lower():
                    # Processar imagem (simplificado)
                    image_data = {
                        'text': text,
                        'element_type': str(element_type),
                        'alt': getattr(element, 'alt_text', '')
                    }
                    content.images.append(image_data)
                
                elif 'paragraph' in str(element_type).lower():
                    # Processar parágrafo
                    if text:
                        content.paragraphs.append({'text': text})
                
                elif 'heading' in str(element_type).lower() or 'title' in str(label).lower():
                    # Processar título/cabeçalho
                    if text:
                        content.headings.append({
                            'text': text,
                            'level': getattr(element, 'level', 1)
                        })
            
        except Exception as e:
            logger.error(f"Erro ao extrair elementos do HTML: {e}")
            
        return content

#####################################
# Processador de Documentos
#####################################

class DocumentProcessor:
    """Classe principal para processar documentos de diferentes tipos"""
    
    def __init__(self):
        """Inicializa o processador com todos os parsers disponíveis"""
        self.parsers = [
            PDFDocumentParser(),
            ExcelDocumentParser(),
            DocxDocumentParser(),
            TextDocumentParser(),
            ArchiveDocumentParser(),
            HTMLDocumentParser()
        ]
    
    def detect_document_type(self, file_path: str) -> Tuple[str, str]:
        """
        Detecta o tipo e MIME type de um arquivo
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Tupla (tipo de documento, MIME type)
        """
        if not os.path.exists(file_path):
            return "Desconhecido", ""
        
        # Obter extensão
        extension = os.path.splitext(file_path)[1].lower()
        
        # Verificar MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Determinar tipo de documento
        doc_type = SUPPORTED_EXTENSIONS.get(extension, "Desconhecido")
        
        return doc_type, mime_type
    
    def get_parser_for_document(self, doc_info: DocumentInfo) -> Optional[BaseDocumentParser]:
        """
        Encontra o parser adequado para o documento
        
        Args:
            doc_info: Informações do documento
            
        Returns:
            Parser adequado ou None se não encontrado
        """
        for parser in self.parsers:
            if parser.can_parse(doc_info):
                return parser
        return None
    
    def process_document(self, doc_info: DocumentInfo) -> Optional[DocumentContent]:
        """
        Processa um documento baseado em suas informações
        
        Args:
            doc_info: Informações do documento
            
        Returns:
            DocumentContent com o conteúdo extraído ou None se erro
        """
        if not doc_info.doc_type and not doc_info.mime_type and doc_info.file_path:
            # Detectar tipo se não foi fornecido
            doc_type, mime_type = self.detect_document_type(doc_info.file_path)
            doc_info.doc_type = doc_type
            doc_info.mime_type = mime_type
            
            if not doc_info.extension and doc_info.file_path:
                doc_info.extension = os.path.splitext(doc_info.file_path)[1].lower()
        
        # Encontrar parser adequado
        parser = self.get_parser_for_document(doc_info)
        
        if not parser:
            content = DocumentContent(doc_info)
            content.doc_info.error = f"Não foi possível encontrar um parser para este tipo de documento: {doc_info.doc_type} ({doc_info.mime_type})"
            return content
        
        # Processar documento
        try:
            content = parser.parse(doc_info)
            return content
        except Exception as e:
            logger.error(f"Erro ao processar documento: {e}")
            content = DocumentContent(doc_info)
            content.doc_info.error = f"Erro ao processar documento: {str(e)}"
            return content
    
    def process_url(self, url: str, timeout: int = TIMEOUT, max_size: int = MAX_DOWNLOAD_SIZE) -> Optional[DocumentContent]:
        """
        Baixa e processa um documento a partir de uma URL
        
        Args:
            url: URL do documento
            timeout: Timeout para download (segundos)
            max_size: Tamanho máximo para download (bytes)
            
        Returns:
            DocumentContent com o conteúdo extraído ou None se erro
        """
        doc_info = DocumentInfo(url=url)
        
        try:
            # Baixar documento
            file_path, download_info = download_document(url, timeout=timeout, max_size=max_size)
            
            if not file_path:
                doc_info.error = download_info.get('error', 'Erro desconhecido no download')
                return DocumentContent(doc_info)
            
            # Atualizar informações do documento
            doc_info.file_path = file_path
            doc_info.title = download_info.get('title', os.path.basename(file_path))
            doc_info.mime_type = download_info.get('mime_type', '')
            doc_info.extension = download_info.get('extension', '')
            doc_info.size = download_info.get('size', 0)
            
            # Detectar tipo se não foi identificado
            if not doc_info.doc_type:
                doc_type, _ = self.detect_document_type(file_path)
                doc_info.doc_type = doc_type
            
            # Processar documento
            return self.process_document(doc_info)
            
        except Exception as e:
            logger.error(f"Erro ao processar URL {url}: {e}")
            doc_info.error = f"Erro ao processar URL: {str(e)}"
            return DocumentContent(doc_info)

#####################################
# Funções para Download de Documentos
#####################################

def download_document(url: str, timeout: int = TIMEOUT, max_size: int = MAX_DOWNLOAD_SIZE) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Baixa um documento a partir de uma URL
    
    Args:
        url: URL do documento
        timeout: Timeout para download (segundos)
        max_size: Tamanho máximo para download (bytes)
        
    Returns:
        Tupla (caminho do arquivo baixado ou None, informações do download)
    """
    info = {
        'url': url,
        'success': False,
        'error': None,
        'size': 0,
        'mime_type': '',
        'extension': '',
        'title': '',
        'download_time': 0
    }
    
    # Criar hash da URL para cache
    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    # Verificar cache
    cache_dir = os.path.join(CACHE_DIR, url_hash[:2], url_hash[2:4])
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_info_path = os.path.join(cache_dir, 'info.json')
    cache_file_path = None
    
    # Verificar se já temos este arquivo em cache
    if os.path.exists(cache_info_path):
        try:
            with open(cache_info_path, 'r') as f:
                cached_info = json.load(f)
                
            if cached_info.get('url') == url and cached_info.get('success'):
                cache_file_path = cached_info.get('file_path')
                
                if cache_file_path and os.path.exists(cache_file_path):
                    logger.info(f"Usando documento em cache: {url}")
                    return cache_file_path, cached_info
        except:
            pass
    
    # Se não está em cache ou cache inválido, baixar
    try:
        start_time = time.time()
        
        # Fazer requisição HEAD para obter informações
        head_response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        # Obter informações do cabeçalho
        content_type = head_response.headers.get('Content-Type', '')
        content_length = head_response.headers.get('Content-Length')
        content_disposition = head_response.headers.get('Content-Disposition', '')
        
        if content_length and int(content_length) > max_size:
            info['error'] = f"Arquivo muito grande: {int(content_length) // (1024*1024)}MB (máximo: {max_size // (1024*1024)}MB)"
            return None, info
        
        # Determinar extensão pelo Content-Type
        extension = SUPPORTED_MIME_TYPES.get(content_type.split(';')[0].strip(), '')
        
        # Se não encontrou extensão pelo Content-Type, tentar pela URL
        if not extension:
            url_path = urlparse(url).path
            _, ext = os.path.splitext(unquote(url_path))
            if ext:
                extension = ext.lower()
        
        # Tentar extrair nome do arquivo do Content-Disposition
        filename = None
        if content_disposition:
            # Extrair nome do arquivo do cabeçalho Content-Disposition
            match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if match:
                filename = match.group(1)
        
        # Se não encontrou nome, usar última parte da URL
        if not filename:
            url_path = urlparse(url).path
            filename = os.path.basename(unquote(url_path))
        
        if not filename:
            filename = f"documento_{url_hash}{extension}"
        
        # Baixar o arquivo
        response = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
        response.raise_for_status()
        
        # Determinar caminho de destino
        file_path = os.path.join(cache_dir, filename)
        
        # Garantir que a extensão está correta
        if extension and not file_path.lower().endswith(extension.lower()):
            file_path = f"{file_path}{extension}"
        
        # Baixar em chunks para evitar consumo excessivo de memória
        total_size = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size > max_size:
                        f.close()
                        os.remove(file_path)
                        info['error'] = f"Arquivo muito grande: {total_size // (1024*1024)}MB (máximo: {max_size // (1024*1024)}MB)"
                        return None, info
                    f.write(chunk)
        
        # Atualizar informações
        download_time = time.time() - start_time
        
        info.update({
            'success': True,
            'file_path': file_path,
            'size': total_size,
            'mime_type': content_type,
            'extension': extension,
            'title': filename,
            'download_time': download_time
        })
        
        # Salvar informações de cache
        with open(cache_info_path, 'w') as f:
            json.dump(info, f)
        
        logger.info(f"Download concluído: {url} ({total_size // 1024}KB em {download_time:.1f}s)")
        return file_path, info
        
    except Exception as e:
        logger.error(f"Erro ao baixar documento {url}: {e}")
        info['error'] = str(e)
        return None, info

#####################################
# Funções de processamento semântico
#####################################

def summarize_document_content(content: DocumentContent, max_tokens: int = 4000) -> str:
    """
    Gera um resumo do conteúdo de um documento usando OpenAI GPT
    
    Args:
        content: Conteúdo do documento
        max_tokens: Limite de tokens para o resumo
        
    Returns:
        Resumo gerado
    """
    if not content or not content.text:
        return "Documento sem conteúdo para resumir."
    
    # Se já tem resumo, retornar
    if content.summary:
        return content.summary
    
    try:
        text = content.text
        
        # Truncar texto se muito grande
        if len(text) > 15000:
            text = text[:15000] + "...\n[Texto truncado devido ao tamanho]"
        
        # Preparar prompt para GPT
        prompt = f"""Por favor, analise o seguinte documento e crie um resumo estruturado. 
O documento é do tipo {content.doc_info.doc_type}, intitulado "{content.doc_info.title}".

DOCUMENTO:
{text}

INSTRUÇÕES PARA O RESUMO:
1. Comece com um parágrafo introdutório sobre o que é o documento.
2. Identifique os principais tópicos e pontos-chave.
3. Se houver tabelas, resuma as informações mais importantes delas.
4. Estruture o resumo em seções com subtítulos.
5. Termine com uma conclusão sobre a relevância do documento.
6. Use formato Markdown para a estruturação.
7. Limite o resumo a aproximadamente 300 palavras.

RESUMO:"""

        # Chamar API da OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Você é um assistente especializado em análise de documentos, focado em extrair as informações mais importantes e resumir de forma clara e estruturada."},
                     {"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.5
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Armazenar resumo no conteúdo
        content.summary = summary
        
        return summary
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {e}")
        return f"Erro ao gerar resumo: {str(e)}"

def generate_document_keywords(content: DocumentContent, max_keywords: int = 10) -> str:
    """
    Gera palavras-chave para um documento usando OpenAI GPT
    
    Args:
        content: Conteúdo do documento
        max_keywords: Número máximo de palavras-chave
        
    Returns:
        String com palavras-chave separadas por ;
    """
    if not content or not content.text:
        return ""
    
    # Se já tem keywords, retornar
    if content.keywords:
        return content.keywords
    
    try:
        text = content.text
        
        # Truncar texto se muito grande
        if len(text) > 10000:
            text = text[:10000] + "...\n[Texto truncado devido ao tamanho]"
        
        # Preparar prompt para GPT
        prompt = f"""Analise o seguinte documento e extraia até {max_keywords} palavras-chave ou termos relevantes.
O documento é do tipo {content.doc_info.doc_type}, intitulado "{content.doc_info.title}".

DOCUMENTO:
{text}

INSTRUÇÕES:
1. Identifique os termos mais importantes e relevantes do documento.
2. Inclua termos técnicos específicos do domínio do documento.
3. Não inclua palavras muito genéricas.
4. Retorne apenas a lista de palavras-chave separadas por ponto e vírgula (;).
5. Não numere as palavras-chave nem adicione texto extra.
6. Exemplo de formato: palavra1; palavra2; expressão composta; termo técnico

PALAVRAS-CHAVE:"""

        # Chamar API da OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Você é um assistente especializado em extrair palavras-chave relevantes de documentos."},
                     {"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.3
        )
        
        keywords = response.choices[0].message.content.strip()
        
        # Limpar possíveis linhas extras ou numerações
        keywords = re.sub(r'^\d+\.\s*', '', keywords, flags=re.MULTILINE)
        keywords = re.sub(r'[\r\n]+', '; ', keywords)
        
        # Garantir formato correto (separado por ;)
        keywords = keywords.replace(',', ';')
        keywords = re.sub(r';\s*;', ';', keywords)
        keywords = re.sub(r'\s*;\s*', '; ', keywords)
        
        # Armazenar keywords no conteúdo
        content.keywords = keywords
        
        return keywords
        
    except Exception as e:
        logger.error(f"Erro ao gerar palavras-chave: {e}")
        return ""

#####################################
# Funções públicas para integração
#####################################

def fetch_documentos(numero_controle: str) -> List[Dict[str, Any]]:
    """
    Busca documentos do PNCP e processa-os
    
    Args:
        numero_controle: Número de controle PNCP no formato CNPJ-1-SEQUENCIAL/ANO
        
    Returns:
        Lista de documentos processados
    """
    try:
        # Parsear número de controle
        cnpj, sequencial, ano = parse_numero_controle_pncp(numero_controle)
        
        # URL da API PNCP
        base_url = "https://pncp.gov.br/pncp-api/v1"
        url = f"{base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
        
        # Fazer requisição à API
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Erro na consulta de documentos para {numero_controle}: {response.status_code}")
            return []
        
        # Processar resposta
        documentos_raw = response.json()
        
        # Inicializar processador de documentos
        processor = DocumentProcessor()
        
        # Processar cada documento
        documentos_processados = []
        
        for doc in documentos_raw:
            arquivo_id = doc.get('id', '')
            titulo = doc.get('titulo', 'Documento sem título')
            
            # Construir URL do documento
            doc_url = f"{base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/{arquivo_id}"
            
            # Verificar se o documento já foi processado anteriormente
            cache_key = f"{cnpj}_{ano}_{sequencial}_{arquivo_id}"
            cache_path = os.path.join(CACHE_DIR, 'processed', cache_key.replace('/', '_'))
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            document_info = {
                'id': arquivo_id,
                'titulo': titulo,
                'url': doc_url,
                'processado': False,
                'texto_disponivel': False,
                'tipo_documento': 'Desconhecido',
                'tamanho': 0,
                'conteudo_resumido': '',
                'palavras_chave': '',
                'original_data': doc
            }
            
            # Tentar baixar e processar o documento
            try:
                # Baixar apenas metadados primeiro
                doc_content = processor.process_url(doc_url, timeout=10, max_size=MAX_DOWNLOAD_SIZE)
                
                if doc_content and doc_content.doc_info.success:
                    document_info.update({
                        'processado': True,
                        'texto_disponivel': len(doc_content.text) > 0,
                        'tipo_documento': doc_content.doc_info.doc_type,
                        'tamanho': doc_content.doc_info.size,
                        'tamanho_formatado': doc_content.doc_info.get_size_formatted(),
                        'conteudo_info': doc_content.doc_info.content_info
                    })
                    
                    # Gerar resumo e palavras-chave apenas se tiver texto
                    if len(doc_content.text) > 100:
                        document_info['conteudo_resumido'] = summarize_document_content(doc_content)
                        document_info['palavras_chave'] = generate_document_keywords(doc_content)
            except Exception as e:
                logger.error(f"Erro ao processar documento {doc_url}: {e}")
            
            documentos_processados.append(document_info)
        
        return documentos_processados
        
    except Exception as e:
        logger.error(f"Erro ao buscar documentos para {numero_controle}: {e}")
        return []

def parse_numero_controle_pncp(numero_controle: str) -> Tuple[str, str, str]:
    """
    Parseia o número de controle PNCP para seus componentes
    
    Args:
        numero_controle: Número de controle no formato CNPJ-1-SEQUENCIAL/ANO
        
    Returns:
        Tupla (cnpj, sequencial, ano)
        
    Raises:
        ValueError: Se o formato for inválido
    """
    # Padrão regex: {cnpj}-1-{sequencial}/{ano}
    pattern = r'^(\d{14})-1-(\d+)/(\d{4})$'
    match = re.match(pattern, numero_controle.strip())
    
    if not match:
        raise ValueError(f"Formato inválido do numeroControlePNCP: {numero_controle}. Formato esperado: CNPJ-1-SEQUENCIAL/ANO")
    
    cnpj = match.group(1)
    sequencial = match.group(2)
    ano = match.group(3)
    
    return cnpj, sequencial, ano

def summarize_document(url: str) -> str:
    """
    Baixa e sumariza o conteúdo de um documento a partir da URL
    
    Args:
        url: URL do documento
        
    Returns:
        Resumo do documento
    """
    try:
        # Inicializar processador de documentos
        processor = DocumentProcessor()
        
        # Processar URL
        doc_content = processor.process_url(url)
        
        if not doc_content or not doc_content.doc_info.success:
            error_msg = doc_content.doc_info.error if doc_content else "Erro desconhecido"
            return f"Não foi possível processar o documento: {error_msg}"
        
        # Verificar se há texto para sumarizar
        if not doc_content.text or len(doc_content.text) < 100:
            return "Documento não contém texto suficiente para gerar um resumo."
        
        # Gerar resumo
        summary = summarize_document_content(doc_content)
        return summary
        
    except Exception as e:
        logger.error(f"Erro ao sumarizar documento {url}: {e}")
        return f"Erro ao sumarizar documento: {str(e)}"

def generate_keywords(texto: str) -> str:
    """
    Gera palavras-chave a partir de um texto
    
    Args:
        texto: Texto para gerar palavras-chave
        
    Returns:
        String com palavras-chave separadas por ;
    """
    if not texto or len(texto) < 50:
        return ""
    
    try:
        # Criar DocumentInfo e DocumentContent temporários
        doc_info = DocumentInfo(title="Texto temporário")
        content = DocumentContent(doc_info)
        content.text = texto
        
        # Gerar palavras-chave
        return generate_document_keywords(content)
        
    except Exception as e:
        logger.error(f"Erro ao gerar palavras-chave: {e}")
        return ""

# Inicialização do módulo
if __name__ == "__main__":
    # Exemplo de uso
    print("Teste de processamento de documento:")
    
    # Exemplo: Baixar e processar um documento
    url = "https://pncp.gov.br/pncp-api/v1/orgaos/46732442000123/compras/2025/21/arquivos/1"
    print(f"Processando {url}...")
    
    summary = summarize_document(url)
    print("\nResumo do documento:")
    print(summary)