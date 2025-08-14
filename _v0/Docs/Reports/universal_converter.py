#!/usr/bin/env python3
"""
Conversor Universal para Markdown usando Docling
Converte múltiplos formatos (XLSX, CSV, HTML, PDF) para Markdown
Suporte a linha de comando e processamento em lote
"""

import pandas as pd
from docling.document_converter import DocumentConverter
from pathlib import Path
import json
import re
import sys
import argparse
import glob
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

class UniversalToMarkdownConverter:
    """Classe para conversão universal de múltiplos formatos para Markdown usando Docling"""
    
    def __init__(self, decimal_places: int = None):
        """
        Inicializa o conversor com configurações padrão
        
        Args:
            decimal_places: Número de casas decimais para números float (None = sem alteração)
        """
        self.converter = DocumentConverter()
        self.decimal_places = decimal_places
        self.supported_formats = {
            '.xlsx': self._convert_with_docling,
            '.xls': self._convert_with_docling,
            '.csv': self._convert_with_docling,
            '.html': self._convert_with_docling,
            '.htm': self._convert_with_docling,
            '.pdf': self._convert_with_docling,
            '.docx': self._convert_with_docling,
            '.pptx': self._convert_with_docling,
            '.txt': self._convert_with_docling
        }
    
    def detect_format(self, file_path: str) -> str:
        """
        Detecta o formato do arquivo baseado na extensão
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Extensão do arquivo em lowercase
        """
        return Path(file_path).suffix.lower()
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Verifica se o formato do arquivo é suportado
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se suportado, False caso contrário
        """
        format_ext = self.detect_format(file_path)
        return format_ext in self.supported_formats
    
    # === MÉTODO UNIVERSAL DOCLING ===
    def _convert_with_docling(self, file_path: str) -> Dict[str, Any]:
        """
        Converte qualquer arquivo suportado usando apenas Docling
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com dados extraídos
        """
        try:
            file_format = self.detect_format(file_path)
            print(f"� Processando {file_format.upper()} com Docling: {file_path}")
            
            # Usar Docling para processar o arquivo
            result = self.converter.convert(Path(file_path))
            document = result.document
            
            # Extrair texto completo
            text_content = document.export_to_text()
            
            # Extrair tabelas se disponível
            tables_data = self._extract_docling_tables(document, file_format)
            
            # Se não há tabelas estruturadas, usar o texto completo
            if not tables_data:
                filename = Path(file_path).stem
                # Criar DataFrame com o texto para manter compatibilidade
                df = pd.DataFrame({'Conteúdo': [text_content]})
                tables_data = {f'Conteúdo_{file_format[1:].upper()}': df}
            
            return tables_data
            
        except Exception as e:
            print(f"❌ Erro ao processar {file_format.upper()}: {e}")
            return {}
    
    def _extract_docling_tables(self, document, file_format: str) -> Dict[str, pd.DataFrame]:
        """
        Extrai tabelas do documento Docling
        
        Args:
            document: Documento Docling
            file_format: Formato do arquivo
            
        Returns:
            Dicionário com DataFrames das tabelas
        """
        tables_data = {}
        
        try:
            # Tentar extrair elementos estruturados
            if hasattr(document, 'body') and hasattr(document.body, 'elements'):
                elements = document.body.elements
            elif hasattr(document, 'elements'):
                elements = document.elements
            else:
                return {}
            
            table_count = 0
            
            for element in elements:
                # Verificar se é uma tabela
                if hasattr(element, 'element_type') and 'table' in str(element.element_type).lower():
                    table_count += 1
                    table_name = f"Tabela_{file_format[1:].upper()}_{table_count}"
                    
                    # Extrair dados da tabela
                    table_df = self._parse_docling_table(element)
                    if table_df is not None and not table_df.empty:
                        tables_data[table_name] = table_df
                        print(f"  ✅ {table_name}: {len(table_df)} linhas × {len(table_df.columns)} colunas")
            
            # Para XLSX/XLS, também tentar usar pandas como fallback
            if file_format in ['.xlsx', '.xls'] and not tables_data:
                pandas_data = self._fallback_pandas_xlsx(document._source if hasattr(document, '_source') else None)
                if pandas_data:
                    tables_data.update(pandas_data)
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair tabelas: {e}")
        
        return tables_data
    
    def _parse_docling_table(self, table_element) -> Optional[pd.DataFrame]:
        """
        Converte elemento de tabela Docling em DataFrame
        
        Args:
            table_element: Elemento de tabela do Docling
            
        Returns:
            DataFrame da tabela ou None
        """
        try:
            # Tentar extrair células da tabela
            if hasattr(table_element, 'table_cells') and table_element.table_cells:
                # Organizar células por posição
                cells_by_position = {}
                max_row, max_col = 0, 0
                
                for cell in table_element.table_cells:
                    if hasattr(cell, 'row_index') and hasattr(cell, 'col_index'):
                        row = getattr(cell, 'row_index', 0)
                        col = getattr(cell, 'col_index', 0)
                        text = getattr(cell, 'text', '')
                        
                        cells_by_position[(row, col)] = text
                        max_row = max(max_row, row)
                        max_col = max(max_col, col)
                
                # Construir DataFrame
                if cells_by_position:
                    data = []
                    headers = []
                    
                    # Extrair cabeçalhos (primeira linha)
                    for col in range(max_col + 1):
                        header = cells_by_position.get((0, col), f"Col_{col+1}")
                        headers.append(header if header else f"Col_{col+1}")
                    
                    # Extrair dados (demais linhas)
                    for row in range(1, max_row + 1):
                        row_data = []
                        for col in range(max_col + 1):
                            cell_value = cells_by_position.get((row, col), "")
                            row_data.append(cell_value)
                        data.append(row_data)
                    
                    if data:
                        return pd.DataFrame(data, columns=headers)
            
            # Fallback: usar texto simples da tabela
            if hasattr(table_element, 'text') and table_element.text:
                # Tentar interpretar texto como tabela
                lines = table_element.text.strip().split('\n')
                if len(lines) > 1:
                    # Assumir primeira linha como cabeçalho
                    headers = [h.strip() for h in lines[0].split('\t')]
                    if len(headers) == 1:  # Tentar separar por espaços múltiplos
                        headers = [h.strip() for h in re.split(r'\s{2,}', lines[0])]
                    
                    data = []
                    for line in lines[1:]:
                        row = [cell.strip() for cell in line.split('\t')]
                        if len(row) == 1:  # Tentar separar por espaços múltiplos
                            row = [cell.strip() for cell in re.split(r'\s{2,}', line)]
                        
                        # Ajustar número de colunas
                        while len(row) < len(headers):
                            row.append("")
                        data.append(row[:len(headers)])
                    
                    if data:
                        return pd.DataFrame(data, columns=headers)
            
        except Exception as e:
            print(f"⚠️ Erro ao parsear tabela: {e}")
        
        return None
    
    def _round_numeric_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Arredonda valores numéricos no DataFrame
        
        Args:
            df: DataFrame para processar
            
        Returns:
            DataFrame com valores arredondados
        """
        if self.decimal_places is None:
            return df
        
        try:
            df_copy = df.copy()
            
            # Processar cada coluna
            for col in df_copy.columns:
                # Verificar se a coluna contém números
                if df_copy[col].dtype in ['float64', 'float32']:
                    # Arredondar números float
                    df_copy[col] = df_copy[col].round(self.decimal_places)
                elif df_copy[col].dtype == 'object':
                    # Tentar converter strings que representam números
                    df_copy[col] = df_copy[col].apply(self._round_string_numbers)
            
            return df_copy
            
        except Exception as e:
            print(f"⚠️ Erro ao arredondar valores: {e}")
            return df
    
    def _round_string_numbers(self, value):
        """
        Arredonda números em formato string - versão melhorada
        
        Args:
            value: Valor a ser processado
            
        Returns:
            Valor processado (arredondado se for número)
        """
        if self.decimal_places is None:
            return value
        
        try:
            # Se já é um número, arredondar diretamente
            if isinstance(value, (int, float)):
                if pd.isna(value):
                    return value
                return round(float(value), self.decimal_places)
            
            # Se é string, tentar identificar e arredondar números
            if isinstance(value, str):
                # Primeiro, tentar converter string inteira para número
                try:
                    float_val = float(value.strip())
                    return f"{float_val:.{self.decimal_places}f}"
                except ValueError:
                    pass
                
                # Se não é um número puro, usar regex para encontrar números no texto
                import re
                
                def round_match(match):
                    try:
                        number_str = match.group()
                        number = float(number_str)
                        return f"{number:.{self.decimal_places}f}"
                    except (ValueError, OverflowError):
                        return match.group()
                
                # Padrão melhorado para números decimais
                # Captura números com ponto decimal obrigatório
                pattern = r'-?\d+\.\d+(?:[eE][+-]?\d+)?'
                
                # Substituir todos os números decimais encontrados
                result = re.sub(pattern, round_match, str(value))
                return result
            
            return value
            
        except (ValueError, TypeError):
            return value
        """
        Fallback para XLSX usando pandas quando Docling não extrai tabelas
        
        Args:
            file_path: Caminho do arquivo XLSX
            
        Returns:
            Dicionário com DataFrames das abas
        """
        if not file_path:
            return {}
        
        try:
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            
            print(f"📊 Fallback pandas - Encontradas {len(excel_file.sheet_names)} abas:")
            for sheet_name in excel_file.sheet_names:
                print(f"  - {sheet_name}")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets_data[sheet_name] = df
                
            return sheets_data
            
        except Exception as e:
            print(f"❌ Erro no fallback pandas: {e}")
            return {}
    
    # === MÉTODOS AUXILIARES (mantidos do original) ===
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
            
            print(f"📊 Encontradas {len(excel_file.sheet_names)} abas:")
            for sheet_name in excel_file.sheet_names:
                print(f"  - {sheet_name}")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets_data[sheet_name] = df
                
            return sheets_data
            
        except Exception as e:
            print(f"❌ Erro ao ler Excel com pandas: {e}")
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
            
            print("🔄 Convertendo arquivo com Docling...")
            result = self.converter.convert(file_path)
            
            return result.document
            
        except Exception as e:
            print(f"❌ Erro ao converter arquivo: {e}")
            return None
    
    def dataframe_to_markdown_table(self, df: pd.DataFrame, sheet_name: str) -> str:
        """
        Converte um DataFrame pandas para tabela Markdown
        
        Args:
            df: DataFrame para converter
            sheet_name: Nome da aba
            
        Returns:
            String da tabela em formato Markdown
        """
        if df.empty:
            return f"*Aba '{sheet_name}' está vazia*\n\n"
        
        markdown = f"## 📋 Aba: {sheet_name}\n\n"
        markdown += f"**Dimensões:** {len(df)} linhas × {len(df.columns)} colunas\n\n"
        
        try:
            # Aplicar arredondamento se especificado
            df_processed = self._round_numeric_values(df)
            
            # Converter para markdown usando pandas
            df_clean = df_processed.fillna("")  # Substituir NaN por string vazia
            
            # Limitar o número de linhas se muito grande
            max_rows = 1000
            if len(df_clean) > max_rows:
                markdown += f"*Mostrando apenas as primeiras {max_rows} linhas de {len(df_clean)} total*\n\n"
                df_display = df_clean.head(max_rows)
            else:
                df_display = df_clean
            
            # Adicionar informação sobre arredondamento se aplicado
            if self.decimal_places is not None:
                markdown += f"*Números arredondados para {self.decimal_places} casas decimais*\n\n"
            
            # Converter para markdown
            table_md = df_display.to_markdown(index=False, tablefmt="grid")
            markdown += table_md + "\n\n"
            
        except Exception as e:
            print(f"⚠️ Erro ao converter aba '{sheet_name}' para markdown: {e}")
            # Fallback: mostrar apenas informações básicas
            markdown += f"**Colunas:** {', '.join(df.columns.astype(str))}\n\n"
            markdown += f"*Erro na conversão da tabela: {e}*\n\n"
        
        return markdown
    
    def extract_docling_content(self, document) -> str:
        """
        Extrai conteúdo adicional do documento Docling
        
        Args:
            document: Documento Docling
            
        Returns:
            Conteúdo extraído em texto
        """
        if not document:
            return ""
        
        try:
            # Tentar extrair texto do documento
            docling_text = document.export_to_text()
            
            if docling_text and len(docling_text.strip()) > 0:
                return f"## 🔍 Conteúdo Adicional (Docling)\n\n{docling_text}\n\n"
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair conteúdo Docling: {e}")
        
        return ""
    
    def get_file_metadata(self, file_path: str, sheets_data: Dict[str, pd.DataFrame]) -> str:
        """
        Gera metadados do arquivo para incluir no Markdown
        
        Args:
            file_path: Caminho do arquivo
            sheets_data: Dados das abas
            
        Returns:
            String com metadados em Markdown
        """
        file_info = Path(file_path)
        file_size = file_info.stat().st_size / 1024 / 1024  # MB
        
        total_rows = sum(len(df) for df in sheets_data.values())
        total_cols = sum(len(df.columns) for df in sheets_data.values())
        
        metadata = f"""# 📊 Relatório da Planilha

**Arquivo:** {file_info.name}
**Caminho:** {file_path}
**Tamanho:** {file_size:.2f} MB
**Data de conversão:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 Resumo Estatístico

- **Total de abas:** {len(sheets_data)}
- **Total de linhas:** {total_rows:,}
- **Total de colunas:** {total_cols}

## 📋 Lista de Abas

"""
        
        for i, (sheet_name, df) in enumerate(sheets_data.items(), 1):
            metadata += f"{i}. **{sheet_name}** - {len(df)} linhas × {len(df.columns)} colunas\n"
        
        metadata += "\n---\n\n"
        
        return metadata
    
    def convert_file_to_markdown(self, input_file: str, output_file: str = None) -> str:
        """
        Converte qualquer arquivo suportado para Markdown
        
        Args:
            input_file: Caminho do arquivo de entrada
            output_file: Caminho do arquivo MD de saída (opcional)
            
        Returns:
            Caminho do arquivo MD gerado
        """
        
        print("="*80)
        print("🔄 CONVERSOR UNIVERSAL → MARKDOWN")
        print("="*80)
        print(f"📁 Arquivo de entrada: {input_file}")
        
        # Verificar se arquivo existe
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
        
        # Detectar formato
        file_format = self.detect_format(input_file)
        if not self.is_supported_format(input_file):
            raise ValueError(f"Formato não suportado: {file_format}")
        
        print(f"🔍 Formato detectado: {file_format.upper()}")
        
        # Definir arquivo de saída se não fornecido
        if not output_file:
            input_path = Path(input_file)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Adicionar informação sobre casas decimais no nome se aplicável
            decimal_info = f"_dec{self.decimal_places}" if self.decimal_places is not None else ""
            output_file = str(input_path.parent / f"{input_path.stem}{decimal_info}_{timestamp}.md")
        
        print(f"📄 Arquivo de saída: {output_file}")
        
        try:
            # Converter arquivo baseado no formato
            print(f"\n🔄 Processando arquivo {file_format.upper()}...")
            converter_method = self.supported_formats[file_format]
            data = converter_method(input_file)
            
            if not data:
                raise ValueError("Nenhum dado extraído do arquivo")
            
            # Gerar conteúdo Markdown
            print("\n📝 Gerando Markdown...")
            markdown_content = ""
            
            # Adicionar metadados
            markdown_content += self.get_file_metadata_universal(input_file, data, file_format)
            
            # Processar dados baseado no formato
            if file_format in ['.xlsx', '.xls']:
                # Para XLSX, usar método original
                for sheet_name, df in data.items():
                    print(f"  - Convertendo aba: {sheet_name}")
                    markdown_content += self.dataframe_to_markdown_table(df, sheet_name)
            else:
                # Para outros formatos, processar como tabelas
                for table_name, df in data.items():
                    print(f"  - Convertendo: {table_name}")
                    markdown_content += self.dataframe_to_markdown_table(df, table_name)
            
            # Salvar arquivo
            print(f"\n💾 Salvando em: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print("\n" + "="*80)
            print("✅ CONVERSÃO CONCLUÍDA!")
            print("="*80)
            print(f"📊 Seções processadas: {len(data)}")
            print(f"📄 Arquivo gerado: {output_file}")
            print(f"📏 Tamanho do MD: {len(markdown_content):,} caracteres")
            
            return output_file
            
        except Exception as e:
            print(f"\n❌ ERRO NA CONVERSÃO: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_file_metadata_universal(self, file_path: str, data: Dict[str, pd.DataFrame], file_format: str) -> str:
        """
        Gera metadados universais do arquivo para incluir no Markdown
        
        Args:
            file_path: Caminho do arquivo
            data: Dados extraídos
            file_format: Formato do arquivo
            
        Returns:
            String com metadados em Markdown
        """
        file_info = Path(file_path)
        file_size = file_info.stat().st_size / 1024 / 1024  # MB
        
        total_rows = sum(len(df) for df in data.values())
        total_cols = sum(len(df.columns) for df in data.values())
        
        metadata = f"""# 📊 Relatório de Conversão - {file_format.upper()}

**Arquivo:** {file_info.name}
**Caminho:** {file_path}
**Formato:** {file_format.upper()}
**Tamanho:** {file_size:.2f} MB
**Data de conversão:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 Resumo Estatístico

- **Total de seções/abas:** {len(data)}
- **Total de linhas:** {total_rows:,}
- **Total de colunas:** {total_cols}

## 📋 Lista de Seções

"""
        
        for i, (section_name, df) in enumerate(data.items(), 1):
            metadata += f"{i}. **{section_name}** - {len(df)} linhas × {len(df.columns)} colunas\n"
        
        metadata += "\n---\n\n"
        
        return metadata
    
    def convert_multiple_files(self, pattern: str, output_dir: str = None) -> List[str]:
        """
        Converte múltiplos arquivos usando padrão glob
        
        Args:
            pattern: Padrão glob para arquivos (ex: "*.xlsx", "/pasta/*.csv")
            output_dir: Diretório de saída (opcional)
            
        Returns:
            Lista de arquivos MD gerados
        """
        files = glob.glob(pattern)
        
        if not files:
            print(f"❌ Nenhum arquivo encontrado com o padrão: {pattern}")
            return []
        
        print(f"🔍 Encontrados {len(files)} arquivos para conversão:")
        for file in files:
            print(f"  - {file}")
        
        converted_files = []
        errors = []
        
        for file_path in files:
            try:
                print(f"\n{'='*60}")
                print(f"🔄 Processando: {Path(file_path).name}")
                print(f"{'='*60}")
                
                if output_dir:
                    # Gerar nome com timestamp para arquivos em lote
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    decimal_info = f"_dec{self.decimal_places}" if self.decimal_places is not None else ""
                    output_file = os.path.join(output_dir, f"{Path(file_path).stem}{decimal_info}_{timestamp}.md")
                else:
                    output_file = None
                
                result = self.convert_file_to_markdown(file_path, output_file)
                converted_files.append(result)
                
                print(f"✅ Concluído: {result}")
                
            except Exception as e:
                error_msg = f"❌ Erro em {file_path}: {e}"
                print(error_msg)
                errors.append(error_msg)
        
        # Relatório final
        print(f"\n{'='*80}")
        print("📊 RELATÓRIO FINAL DE CONVERSÃO EM LOTE")
        print(f"{'='*80}")
        print(f"✅ Arquivos convertidos: {len(converted_files)}")
        print(f"❌ Erros: {len(errors)}")
        
        if errors:
            print("\n❌ Arquivos com erro:")
            for error in errors:
                print(f"  {error}")
        
        return converted_files
        """
        Converte arquivo XLSX completo para Markdown
        
        Args:
            input_file: Caminho do arquivo XLSX
            output_file: Caminho do arquivo MD de saída (opcional)
            
        Returns:
            Caminho do arquivo MD gerado
        """
        
        print("="*80)
        print("🔄 CONVERSOR XLSX → MARKDOWN (Docling)")
        print("="*80)
        print(f"📁 Arquivo de entrada: {input_file}")
        
        # Verificar se arquivo existe
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
        
        # Definir arquivo de saída se não fornecido
        if not output_file:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}.md")
        
        print(f"📄 Arquivo de saída: {output_file}")
        
        try:
            # 1. Ler dados com pandas
            print("\n🔍 Lendo dados com pandas...")
            sheets_data = self.read_xlsx_with_pandas(input_file)
            
            if not sheets_data:
                raise ValueError("Nenhuma aba encontrada no arquivo")
            
            # 2. Converter com Docling
            print("\n🔄 Processando com Docling...")
            document = self.convert_xlsx_to_document(input_file)
            
            # 3. Gerar conteúdo Markdown
            print("\n📝 Gerando Markdown...")
            markdown_content = ""
            
            # Adicionar metadados
            markdown_content += self.get_file_metadata(input_file, sheets_data)
            
            # Adicionar conteúdo Docling se disponível
            docling_content = self.extract_docling_content(document)
            if docling_content:
                markdown_content += docling_content
            
            # Adicionar cada aba como seção
            for sheet_name, df in sheets_data.items():
                print(f"  - Convertendo aba: {sheet_name}")
                markdown_content += self.dataframe_to_markdown_table(df, sheet_name)
            
            # 4. Salvar arquivo
            print(f"\n💾 Salvando em: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print("\n" + "="*80)
            print("✅ CONVERSÃO CONCLUÍDA!")
            print("="*80)
            print(f"📊 Abas processadas: {len(sheets_data)}")
            print(f"📄 Arquivo gerado: {output_file}")
            print(f"📏 Tamanho do MD: {len(markdown_content):,} caracteres")
            
            return output_file
            
        except Exception as e:
            print(f"\n❌ ERRO NA CONVERSÃO: {e}")
            import traceback
            traceback.print_exc()
            raise

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Conversor Universal para Markdown - Suporta XLSX, CSV, HTML, PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Converter um arquivo específico
  python converter.py arquivo.xlsx
  python converter.py dados.csv
  python converter.py relatorio.pdf
  
  # Especificar arquivo de saída e casas decimais
  python converter.py arquivo.xlsx -o resultado.md --dec 2
  
  # Converter múltiplos arquivos com 4 casas decimais
  python converter.py "*.xlsx" --batch --dec 4
  python converter.py "/pasta/*.csv" --batch -d saida/
  
  # Listar formatos suportados
  python converter.py --formats

Formatos suportados: XLSX, XLS, CSV, HTML, HTM, PDF, DOCX, PPTX, TXT
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='Arquivo de entrada ou padrão glob (ex: *.xlsx)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Arquivo de saída (.md)'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Modo lote - processa múltiplos arquivos usando glob pattern'
    )
    
    parser.add_argument(
        '-d', '--output-dir',
        help='Diretório de saída para modo lote'
    )
    
    parser.add_argument(
        '--formats',
        action='store_true',
        help='Listar formatos suportados'
    )
    
    parser.add_argument(
        '--dec', '--decimals',
        type=int,
        metavar='N',
        help='Número de casas decimais para números (ex: --dec 2 para 2 casas)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Conversor Universal para Markdown v2.0'
    )
    
    return parser.parse_args()

def show_supported_formats():
    """Mostra formatos suportados"""
    print("="*60)
    print("📋 FORMATOS SUPORTADOS (via Docling)")
    print("="*60)
    print("📊 Planilhas:")
    print("  - .xlsx (Excel)")
    print("  - .xls  (Excel legado)")
    print("")
    print("📄 Dados estruturados:")
    print("  - .csv  (Comma Separated Values)")
    print("")
    print("🌐 Web:")
    print("  - .html (HyperText Markup Language)")
    print("  - .htm  (HyperText Markup Language)")
    print("")
    print("📑 Documentos:")
    print("  - .pdf  (Portable Document Format)")
    print("  - .docx (Microsoft Word)")
    print("  - .pptx (Microsoft PowerPoint)")
    print("  - .txt  (Texto simples)")
    print("")
    print("💡 Dica: Docling oferece extração inteligente de conteúdo!")

def main():
    """Função principal com suporte a argumentos de linha de comando"""
    
    args = parse_arguments()
    
    # Mostrar formatos suportados
    if args.formats:
        show_supported_formats()
        return
    
    # Verificar se foi fornecido arquivo de entrada
    if not args.input:
        print("❌ Erro: Arquivo de entrada não especificado")
        print("\n💡 Use --help para ver exemplos de uso")
        return
    
    try:
        # Criar instância do conversor
        converter = UniversalToMarkdownConverter(decimal_places=args.dec)
        
        if args.batch:
            # Modo lote
            print(f"🔄 Modo lote ativado - Padrão: {args.input}")
            
            # Criar diretório de saída se especificado
            if args.output_dir:
                os.makedirs(args.output_dir, exist_ok=True)
                print(f"📁 Diretório de saída: {args.output_dir}")
            
            # Converter múltiplos arquivos
            converted_files = converter.convert_multiple_files(args.input, args.output_dir)
            
            if converted_files:
                print(f"\n🎉 Conversão em lote concluída!")
                print(f"📊 {len(converted_files)} arquivos convertidos")
            else:
                print(f"\n❌ Nenhum arquivo foi convertido")
        
        else:
            # Modo arquivo único
            input_file = args.input
            
            # Verificar se arquivo existe
            if not os.path.exists(input_file):
                print(f"❌ Arquivo não encontrado: {input_file}")
                return
            
            # Verificar se formato é suportado
            if not converter.is_supported_format(input_file):
                format_ext = converter.detect_format(input_file)
                print(f"❌ Formato não suportado: {format_ext}")
                print("\n💡 Use --formats para ver formatos suportados")
                return
            
            # Converter arquivo
            output_file = converter.convert_file_to_markdown(input_file, args.output)
            
            print(f"\n🎉 Sucesso! Arquivo convertido para: {output_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Conversão interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante a conversão: {e}")
        import traceback
        traceback.print_exc()

# Manter compatibilidade com uso direto (sem argumentos)
def main_legacy():
    """Função principal legada (para compatibilidade)"""
    
    # Arquivo específico do usuário (exemplo)
    input_file = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\RESULTADO_ANALITICO_-_MELHOR.xlsx"
    
    # Verificar se arquivo existe
    if not os.path.exists(input_file):
        print(f"❌ Arquivo não encontrado: {input_file}")
        print("\n📝 Por favor, verifique o caminho do arquivo.")
        return
    
    try:
        # Criar instância do conversor
        converter = UniversalToMarkdownConverter(decimal_places=None)
        
        # Converter arquivo
        output_file = converter.convert_file_to_markdown(input_file)
        
        print(f"\n🎉 Sucesso! Arquivo convertido para: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Erro durante a conversão: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Se há argumentos de linha de comando, usar função principal
    if len(sys.argv) > 1:
        main()
    else:
        # Senão, usar função legada
        print("💡 Nenhum argumento fornecido, usando arquivo de exemplo...")
        print("💡 Use --help para ver opções de linha de comando")
        main_legacy()
