import pandas as pd
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PipelineOptions
from pathlib import Path
import json
import re
from typing import Dict, List, Any, Optional

class DoclingXLSXParser:
    """Classe para parsing de arquivos XLSX usando Docling"""
    
    def __init__(self):
        """Inicializa o parser com configurações padrão"""
        self.converter = DocumentConverter()
    
    def read_xlsx_with_pandas(self, file_path: str) -> Dict[str, pd.DataFrame]:
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
            print(f"Erro ao ler Excel com pandas: {e}")
            return {}
    
    def convert_xlsx_to_document(self, file_path: str) -> Any:
        """
        Converte arquivo XLSX para documento Docling
        
        Args:
            file_path: Caminho para o arquivo XLSX
            
        Returns:
            Documento convertido
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            if file_path.suffix.lower() not in ['.xlsx', '.xls']:
                raise ValueError("Arquivo deve ser um Excel (.xlsx ou .xls)")
            
            # Converter documento com configurações padrão
            result = self.converter.convert(file_path)
            
            return result.document
            
        except Exception as e:
            print(f"Erro ao converter arquivo: {e}")
            return None
    
    def clean_text_content(self, text: str) -> str:
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
    
    def extract_text_content(self, document) -> str:
        """
        Extrai todo o conteúdo de texto do documento
        
        Args:
            document: Documento Docling
            
        Returns:
            Texto extraído e limpo
        """
        if not document:
            return ""
        
        try:
            raw_text = document.export_to_text()
            return self.clean_text_content(raw_text)
        except Exception as e:
            print(f"Erro ao extrair texto: {e}")
            return ""
    
    def extract_structured_tables(self, sheets_data: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
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
    
    def extract_tables(self, document) -> List[Dict]:
        """
        Extrai tabelas do documento Docling (mantido para compatibilidade)
        
        Args:
            document: Documento Docling
            
        Returns:
            Lista de tabelas extraídas
        """
        tables = []
        
        if not document:
            return tables
        
        try:
            # Tentar diferentes formas de acessar elementos
            elements = []
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                elements = document.body.elements
            elif hasattr(document, 'elements'):
                elements = document.elements
            
            for element in elements:
                # Verificar se é uma tabela
                if (hasattr(element, 'label') and 'table' in str(element.label).lower()) or \
                   (hasattr(element, 'element_type') and 'table' in str(element.element_type).lower()):
                    
                    table_data = {
                        'bbox': getattr(element, 'bbox', None),
                        'text': getattr(element, 'text', ""),
                        'label': str(getattr(element, 'label', '')),
                        'element_type': str(getattr(element, 'element_type', '')),
                        'table_cells': []
                    }
                    
                    # Extrair células da tabela se disponível
                    if hasattr(element, 'table_cells') and element.table_cells:
                        for cell in element.table_cells:
                            cell_data = {
                                'text': getattr(cell, 'text', ""),
                                'bbox': getattr(cell, 'bbox', None),
                                'row': getattr(cell, 'row_index', None),
                                'col': getattr(cell, 'col_index', None)
                            }
                            table_data['table_cells'].append(cell_data)
                    
                    tables.append(table_data)
                    
        except Exception as e:
            print(f"Erro ao extrair tabelas: {e}")
        
        return tables
    
    def extract_metadata(self, document, sheets_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Extrai metadados do documento e das abas
        
        Args:
            document: Documento Docling
            sheets_data: Dados das abas do Excel
            
        Returns:
            Dicionário com metadados
        """
        metadata = {}
        
        try:
            # Metadados do Docling
            if document and hasattr(document, 'metadata'):
                metadata.update(document.metadata)
            
            # Informações das abas
            sheets_info = {}
            for sheet_name, df in sheets_data.items():
                sheets_info[sheet_name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist(),
                    'has_data': not df.empty
                }
            
            metadata.update({
                'num_sheets': len(sheets_data),
                'sheet_names': list(sheets_data.keys()),
                'sheets_info': sheets_info
            })
            
            # Informações do documento Docling
            if document:
                if hasattr(document, 'pages'):
                    metadata['num_pages'] = len(document.pages)
                
                if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                    metadata['num_elements'] = len(document.body.elements)
                elif hasattr(document, 'elements'):
                    metadata['num_elements'] = len(document.elements)
            
        except Exception as e:
            print(f"Erro ao extrair metadados: {e}")
        
        return metadata
    
    def parse_xlsx_file(self, file_path: str) -> Dict[str, Any]:
        """
        Função principal para parsing completo de arquivo XLSX
        
        Args:
            file_path: Caminho para o arquivo XLSX
            
        Returns:
            Dicionário com todos os dados extraídos
        """
        print(f"Iniciando parsing do arquivo: {file_path}")
        
        # Ler com pandas para obter estrutura das abas
        sheets_data = self.read_xlsx_with_pandas(file_path)
        
        if not sheets_data:
            return {"error": "Falha ao ler arquivo Excel"}
        
        # Converter com Docling
        document = self.convert_xlsx_to_document(file_path)
        
        # Extrair dados estruturados por aba
        structured_tables = self.extract_structured_tables(sheets_data)
        
        # Extrair dados
        result = {
            "file_path": str(file_path),
            "text_content": self.extract_text_content(document) if document else "",
            "sheets_data": structured_tables,
            "docling_tables": self.extract_tables(document) if document else [],
            "metadata": self.extract_metadata(document, sheets_data),
            "raw_document": document  # Manter referência ao documento original
        }
        
        total_tables = sum(len(tables) for tables in structured_tables.values())
        print(f"Parsing concluído. Encontradas {len(sheets_data)} abas com {total_tables} tabelas.")
        
        return result
    
    def save_results_to_json(self, results: Dict[str, Any], output_path: str):
        """
        Salva resultados em arquivo JSON
        
        Args:
            results: Resultados do parsing
            output_path: Caminho para salvar o arquivo JSON
        """
        try:
            # Remover documento raw antes de salvar (não é serializável)
            results_copy = results.copy()
            if 'raw_document' in results_copy:
                del results_copy['raw_document']
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_copy, f, indent=2, ensure_ascii=False)
            
            print(f"Resultados salvos em: {output_path}")
            
        except Exception as e:
            print(f"Erro ao salvar resultados: {e}")

# Exemplo de uso
if __name__ == "__main__":
    # Criar instância do parser
    parser = DoclingXLSXParser()
    
    # Definir arquivo manualmente - SUBSTITUA PELO SEU ARQUIVO
    file_path = r"C:\Users\Haroldo Duraes\Desktop\Firmesa\Comparativo ERP.xlsx"
    
    print(f"Processando arquivo: {file_path}")
    
    try:
        # Fazer parsing do arquivo
        results = parser.parse_xlsx_file(file_path)
        
        # Verificar se houve erro
        if "error" in results:
            print(f"Erro: {results['error']}")
            exit()
        
        # Exibir informações das abas
        print(f"\nArquivo possui {results['metadata']['num_sheets']} aba(s):")
        for sheet_name in results['metadata']['sheet_names']:
            sheet_info = results['metadata']['sheets_info'][sheet_name]
            print(f"  - {sheet_name}: {sheet_info['rows']} linhas, {sheet_info['columns']} colunas")
        
        # Exibir dados de cada aba
        for sheet_name, tables in results['sheets_data'].items():
            print(f"\n=== ABA: {sheet_name} ===")
            for table in tables:
                print(f"Tabela com {table['rows']} linhas e {table['columns']} colunas")
                print(f"Colunas: {', '.join(table['column_names'])}")
                
                # Mostrar primeiras 3 linhas de dados
                for i, row_data in enumerate(table['data'][:3]):
                    print(f"  Linha {i+1}: {row_data}")
                
                if len(table['data']) > 3:
                    print(f"  ... e mais {len(table['data']) - 3} linhas")
        
        # Exibir texto limpo (se houver)
        if results.get('text_content'):
            print(f"\nTexto extraído (primeiros 500 caracteres):")
            print(results['text_content'][:500])
        
        # Salvar resultados
        parser.save_results_to_json(results, "resultados_parsing_melhorado.json")
        
    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        import traceback
        traceback.print_exc()