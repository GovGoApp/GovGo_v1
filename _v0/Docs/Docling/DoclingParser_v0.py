import pandas as pd
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PipelineOptions
from pathlib import Path
import json
from typing import Dict, List, Any, Optional

class DoclingXLSXParser:
    """Classe para parsing de arquivos XLSX usando Docling"""
    
    def __init__(self):
        """Inicializa o parser com configurações padrão"""
        self.converter = DocumentConverter()
    
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
    
    def extract_text_content(self, document) -> str:
        """
        Extrai todo o conteúdo de texto do documento
        
        Args:
            document: Documento Docling
            
        Returns:
            Texto extraído
        """
        if not document:
            return ""
        
        try:
            return document.export_to_text()
        except Exception as e:
            print(f"Erro ao extrair texto: {e}")
            return ""
    
    def extract_tables(self, document) -> List[Dict]:
        """
        Extrai tabelas do documento
        
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
    
    def extract_metadata(self, document) -> Dict:
        """
        Extrai metadados do documento
        
        Args:
            document: Documento Docling
            
        Returns:
            Dicionário com metadados
        """
        metadata = {}
        
        if not document:
            return metadata
        
        try:
            # Extrair metadados disponíveis
            if hasattr(document, 'metadata'):
                metadata.update(document.metadata)
            
            # Adicionar informações básicas
            info = {}
            if hasattr(document, 'pages'):
                info['num_pages'] = len(document.pages)
            
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                info['num_elements'] = len(document.body.elements)
            elif hasattr(document, 'elements'):
                info['num_elements'] = len(document.elements)
            
            metadata.update(info)
            
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
        
        # Converter documento
        document = self.convert_xlsx_to_document(file_path)
        
        if not document:
            return {"error": "Falha na conversão do documento"}
        
        # Extrair dados
        result = {
            "file_path": str(file_path),
            "text_content": self.extract_text_content(document),
            "tables": self.extract_tables(document),
            "metadata": self.extract_metadata(document),
            "raw_document": document  # Manter referência ao documento original
        }
        
        print(f"Parsing concluído. Encontradas {len(result['tables'])} tabelas.")
        
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

# Funções auxiliares
def process_multiple_xlsx_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Processa múltiplos arquivos XLSX
    
    Args:
        file_paths: Lista de caminhos para arquivos XLSX
        
    Returns:
        Dicionário com resultados de todos os arquivos
    """
    parser = DoclingXLSXParser()
    results = {}
    
    for file_path in file_paths:
        print(f"\nProcessando: {file_path}")
        file_result = parser.parse_xlsx_file(file_path)
        results[file_path] = file_result
    
    return results

def compare_xlsx_documents(file_path1: str, file_path2: str) -> Dict[str, Any]:
    """
    Compara dois documentos XLSX
    
    Args:
        file_path1: Primeiro arquivo
        file_path2: Segundo arquivo
        
    Returns:
        Comparação entre os documentos
    """
    parser = DoclingXLSXParser()
    
    doc1 = parser.parse_xlsx_file(file_path1)
    doc2 = parser.parse_xlsx_file(file_path2)
    
    comparison = {
        "file1": file_path1,
        "file2": file_path2,
        "tables_count_diff": len(doc1.get('tables', [])) - len(doc2.get('tables', [])),
        "text_length_diff": len(doc1.get('text_content', '')) - len(doc2.get('text_content', '')),
        "metadata_comparison": {
            "doc1_pages": doc1.get('metadata', {}).get('num_pages', 0),
            "doc2_pages": doc2.get('metadata', {}).get('num_pages', 0)
        }
    }
    
    return comparison

# Exemplo de uso
if __name__ == "__main__":
    # Criar instância do parser
    parser = DoclingXLSXParser()
    
    # Definir arquivo manualmente - SUBSTITUA PELO SEU ARQUIVO
    file_path = "C:\\Users\\Haroldo Duraes\\Desktop\\Firmesa\\Comparativo ERP.xlsx"
    
    print(f"Processando arquivo: {file_path}")
    
    try:
        # Fazer parsing do arquivo
        results = parser.parse_xlsx_file(file_path)
        
        # Verificar se houve erro
        if "error" in results:
            print(f"Erro: {results['error']}")
            exit()
        
        # Exibir resultados
        print(f"\nTexto extraído:")
        text_content = results.get('text_content', '')
        if text_content:
            print(text_content[:1000])  # Primeiros 1000 caracteres
        else:
            print("Nenhum texto extraído")
        
        print(f"\nNúmero de tabelas encontradas: {len(results.get('tables', []))}")
        
        # Mostrar detalhes das tabelas
        for i, table in enumerate(results.get('tables', []), 1):
            print(f"\nTabela {i}:")
            print(f"  Tipo: {table.get('element_type', 'N/A')}")
            print(f"  Label: {table.get('label', 'N/A')}")
            print(f"  Células: {len(table.get('table_cells', []))}")
            if table.get('text'):
                print(f"  Texto: {table['text'][:200]}...")
        
        print(f"\nMetadados:")
        for key, value in results.get('metadata', {}).items():
            print(f"  {key}: {value}")
        
        # Salvar resultados
        parser.save_results_to_json(results, "resultados_parsing.json")
        
    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        import traceback
        traceback.print_exc()