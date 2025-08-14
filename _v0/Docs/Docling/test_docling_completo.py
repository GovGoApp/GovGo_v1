"""
Sistema Completo de Testes Docling
Processa todos os tipos de arquivos suportados com foco especial em tabelas de PDFs
"""

import os
import sys
import json
import zipfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Suprimir warnings específicos do PyTorch/Docling
warnings.filterwarnings("ignore", message=".*pin_memory.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*accelerator.*", category=UserWarning)

# Configuração
TEST_FILES_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\TESTE"
OUTPUT_DIR = TEST_FILES_PATH + r"\CONV_Docling"

def ensure_output_directory():
    """Garante que o diretório de saída existe"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Diretório de saída: {OUTPUT_DIR}")

def get_file_info(filepath: str) -> Dict[str, Any]:
    """Obtém informações detalhadas do arquivo"""
    stat = os.stat(filepath)
    size = stat.st_size
    
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        size_str = f"{size/(1024*1024):.1f} MB"
    else:
        size_str = f"{size/(1024*1024*1024):.1f} GB"
    
    modified = datetime.fromtimestamp(stat.st_mtime)
    
    return {
        'size': size,
        'size_str': size_str,
        'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
        'extension': Path(filepath).suffix.lower()
    }

def analyze_table_quality(doc) -> Dict[str, Any]:
    """Analisa a qualidade das tabelas extraídas"""
    stats = {
        'total_tables': 0,
        'tables_with_structure': 0,
        'total_cells': 0,
        'tables_data': []
    }
    
    if not doc or not hasattr(doc, 'tables'):
        return stats
    
    try:
        stats['total_tables'] = len(doc.tables)
        
        for i, table in enumerate(doc.tables):
            table_info = {
                'table_index': i,
                'has_structure': False,
                'cell_count': 0,
                'bbox': None,
                'text_preview': ""
            }
            
            # Verificar estrutura da tabela
            if hasattr(table, 'data') and table.data:
                table_info['has_structure'] = True
                stats['tables_with_structure'] += 1
                
                # Contar células
                if hasattr(table.data, 'table_cells') and table.data.table_cells:
                    table_info['cell_count'] = len(table.data.table_cells)
                    stats['total_cells'] += table_info['cell_count']
            
            # Obter bbox se disponível
            if hasattr(table, 'bbox') and table.bbox:
                table_info['bbox'] = {
                    'x': table.bbox.l,
                    'y': table.bbox.t, 
                    'width': table.bbox.w,
                    'height': table.bbox.h
                }
            
            # Preview do texto
            if hasattr(table, 'text') and table.text:
                table_info['text_preview'] = table.text[:200] + "..." if len(table.text) > 200 else table.text
            
            stats['tables_data'].append(table_info)
    
    except Exception as e:
        print(f"⚠️ Erro ao analisar tabelas: {e}")
    
    return stats

def extract_tables_to_markdown(doc) -> str:
    """Extrai tabelas e converte para formato Markdown"""
    tables_md = ""
    
    if not doc or not hasattr(doc, 'tables') or not doc.tables:
        return "❌ Nenhuma tabela encontrada no documento."
    
    try:
        for i, table in enumerate(doc.tables):
            tables_md += f"\n## Tabela {i+1}\n\n"
            
            # Tentar extrair estrutura da tabela
            if hasattr(table, 'data') and table.data and hasattr(table.data, 'table_cells'):
                # Organizar células por linha e coluna
                cells_by_position = {}
                max_row = 0
                max_col = 0
                
                for cell in table.data.table_cells:
                    if hasattr(cell, 'row_index') and hasattr(cell, 'col_index'):
                        row = cell.row_index
                        col = cell.col_index
                        text = getattr(cell, 'text', '').strip()
                        
                        if (row, col) not in cells_by_position:
                            cells_by_position[(row, col)] = text
                        
                        max_row = max(max_row, row)
                        max_col = max(max_col, col)
                
                # Construir tabela Markdown
                if cells_by_position:
                    # Cabeçalho
                    header_row = []
                    for col in range(max_col + 1):
                        cell_text = cells_by_position.get((0, col), "")
                        header_row.append(cell_text if cell_text else f"Col {col+1}")
                    
                    tables_md += "| " + " | ".join(header_row) + " |\n"
                    tables_md += "| " + " | ".join(["---"] * len(header_row)) + " |\n"
                    
                    # Linhas de dados
                    for row in range(1, max_row + 1):
                        data_row = []
                        for col in range(max_col + 1):
                            cell_text = cells_by_position.get((row, col), "")
                            data_row.append(cell_text if cell_text else "")
                        tables_md += "| " + " | ".join(data_row) + " |\n"
                else:
                    tables_md += "⚠️ Estrutura de célula não encontrada\n"
            else:
                # Fallback: usar texto simples da tabela
                if hasattr(table, 'text') and table.text:
                    tables_md += f"```\n{table.text}\n```\n"
                else:
                    tables_md += "⚠️ Nenhum conteúdo de tabela disponível\n"
            
            tables_md += "\n"
    
    except Exception as e:
        tables_md += f"\n❌ Erro ao extrair tabelas: {str(e)}\n"
    
    return tables_md

def process_zip_file(zip_path: str) -> List[Dict[str, Any]]:
    """Processa arquivos dentro de um ZIP (similar ao MarkItDown)"""
    results = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extrair para pasta temporária
            temp_extract_dir = os.path.join(OUTPUT_DIR, f"temp_zip_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            zip_ref.extractall(temp_extract_dir)
            
            # Processar cada arquivo extraído
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, temp_extract_dir)
                    
                    print(f"  📄 Processando arquivo do ZIP: {relative_path}")
                    
                    result = process_single_file(file_path, f"ZIP:{relative_path}")
                    if result:
                        results.append(result)
            
            # Limpar arquivos temporários
            import shutil
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
    
    except Exception as e:
        print(f"❌ Erro ao processar ZIP: {e}")
        results.append({
            'status': 'error',
            'file_name': os.path.basename(zip_path),
            'error': f"Erro ZIP: {str(e)}"
        })
    
    return results

def process_single_file(filepath: str, display_name: str = None) -> Dict[str, Any]:
    """Processa um único arquivo com Docling"""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return {
            'status': 'error',
            'file_name': os.path.basename(filepath),
            'error': "Docling não instalado. Execute: pip install docling"
        }
    
    filename = display_name or os.path.basename(filepath)
    file_info = get_file_info(filepath)
    
    print(f"\n📄 Processando: {filename}")
    print(f"   📏 Tamanho: {file_info['size_str']}")
    print(f"   📅 Modificado: {file_info['modified']}")
    print(f"   🔧 Extensão: {file_info['extension']}")
    
    try:
        # Configurar Docling converter
        converter = DocumentConverter()
        
        # Conversão
        print("   🔄 Convertendo com Docling...")
        result = converter.convert(filepath)
        doc = result.document
        
        # Análise de tabelas
        table_stats = analyze_table_quality(doc)
        
        # Extrair conteúdo
        markdown_content = doc.export_to_markdown()
        html_content = doc.export_to_html()
        json_content = doc.model_dump(exclude_none=True)
        
        # Extrair tabelas em formato Markdown
        tables_markdown = extract_tables_to_markdown(doc)
        
        # Nome base para arquivos de saída
        safe_name = "".join(c for c in Path(filename).stem if c.isalnum() or c in (' ', '-', '_')).strip()[:100]
        if not safe_name:
            safe_name = f"documento_{datetime.now().strftime('%H%M%S')}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Salvar resultados
        outputs = {}
        
        # 1. Markdown completo
        md_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Conversão Docling: {filename}\n\n")
            f.write(f"**Arquivo original:** `{filename}`  \n")
            f.write(f"**Tamanho:** {file_info['size_str']}  \n")
            f.write(f"**Modificado:** {file_info['modified']}  \n")
            f.write(f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Ferramenta:** Docling v2.x  \n\n")
            f.write(f"## 📊 Estatísticas de Tabelas\n\n")
            f.write(f"- **Total de tabelas:** {table_stats['total_tables']}\n")
            f.write(f"- **Tabelas com estrutura:** {table_stats['tables_with_structure']}\n")
            f.write(f"- **Total de células:** {table_stats['total_cells']}\n\n")
            f.write("---\n\n")
            f.write(markdown_content)
        outputs['markdown'] = md_file
        
        # 2. Tabelas específicas
        if table_stats['total_tables'] > 0:
            tables_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}_TABLES.md")
            with open(tables_file, 'w', encoding='utf-8') as f:
                f.write(f"# Tabelas Extraídas: {filename}\n\n")
                f.write(f"**Documento:** {filename}  \n")
                f.write(f"**Tabelas encontradas:** {table_stats['total_tables']}  \n")
                f.write(f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
                f.write("---\n\n")
                f.write(tables_markdown)
            outputs['tables'] = tables_file
        
        # 3. HTML
        html_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        outputs['html'] = html_file
        
        # 4. JSON estruturado
        json_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2, ensure_ascii=False)
        outputs['json'] = json_file
        
        # 5. Estatísticas de tabelas
        if table_stats['total_tables'] > 0:
            stats_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}_TABLE_STATS.json")
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(table_stats, f, indent=2, ensure_ascii=False)
            outputs['table_stats'] = stats_file
        
        # Calcular estatísticas
        total_output_size = sum(os.path.getsize(f) for f in outputs.values())
        
        print(f"   ✅ Sucesso! Arquivos gerados:")
        for format_type, file_path in outputs.items():
            size = os.path.getsize(file_path)
            print(f"      📝 {format_type.upper()}: {os.path.basename(file_path)} ({size:,} bytes)")
        
        return {
            'status': 'success',
            'file_name': filename,
            'input_size': file_info['size'],
            'outputs': outputs,
            'total_output_size': total_output_size,
            'table_stats': table_stats,
            'processing_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Erro: {error_msg}")
        
        # Salvar erro
        error_file = os.path.join(OUTPUT_DIR, f"ERROR_{Path(filename).stem}_{datetime.now().strftime('%H%M%S')}.md")
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"# ERRO na conversão Docling: {filename}\n\n")
            f.write(f"**Arquivo:** `{filename}`  \n")
            f.write(f"**Erro:** {error_msg}  \n")
            f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("## Detalhes do arquivo\n\n")
            f.write(f"- Tamanho: {file_info['size_str']}\n")
            f.write(f"- Extensão: {file_info['extension']}\n")
            f.write(f"- Modificado: {file_info['modified']}\n")
        
        return {
            'status': 'error',
            'file_name': filename,
            'error': error_msg,
            'input_size': file_info['size']
        }

def generate_final_report(all_results: List[Dict[str, Any]]):
    """Gera relatório final detalhado"""
    print(f"\n{'='*60}")
    print("📊 RELATÓRIO FINAL - DOCLING")
    print("="*60)
    
    successful = [r for r in all_results if r['status'] == 'success']
    failed = [r for r in all_results if r['status'] == 'error']
    
    # Estatísticas gerais
    print(f"✅ Sucessos: {len(successful)}")
    print(f"❌ Erros: {len(failed)}")
    print(f"📊 Taxa de sucesso: {(len(successful)/len(all_results)*100):.1f}%")
    
    # Estatísticas de tabelas
    total_tables = sum(r.get('table_stats', {}).get('total_tables', 0) for r in successful)
    tables_with_structure = sum(r.get('table_stats', {}).get('tables_with_structure', 0) for r in successful)
    total_cells = sum(r.get('table_stats', {}).get('total_cells', 0) for r in successful)
    
    print(f"\n📋 ESTATÍSTICAS DE TABELAS:")
    print(f"   📊 Total de tabelas encontradas: {total_tables}")
    print(f"   🏗️  Tabelas com estrutura: {tables_with_structure}")
    print(f"   📝 Total de células: {total_cells}")
    if total_tables > 0:
        print(f"   ✅ Taxa de estruturação: {(tables_with_structure/total_tables*100):.1f}%")
    
    # Tamanhos
    if successful:
        total_input = sum(r['input_size'] for r in successful)
        total_output = sum(r['total_output_size'] for r in successful)
        print(f"\n📏 Tamanho original: {total_input:,} bytes")
        print(f"📄 Tamanho de saída total: {total_output:,} bytes")
        print(f"📈 Expansão média: {(total_output/total_input*100):.1f}%")
    
    # Relatório em arquivo
    report_file = os.path.join(OUTPUT_DIR, "RELATORIO_FINAL_DOCLING.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Relatório Final - Testes Docling\n\n")
        f.write(f"**Data/Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Diretório de saída:** `{OUTPUT_DIR}`  \n")
        f.write(f"**Total de arquivos:** {len(all_results)}  \n")
        f.write(f"**Sucessos:** {len(successful)}  \n")
        f.write(f"**Erros:** {len(failed)}  \n")
        f.write(f"**Taxa de sucesso:** {(len(successful)/len(all_results)*100):.1f}%  \n\n")
        
        f.write("## 📊 Estatísticas de Tabelas\n\n")
        f.write(f"- **Total de tabelas:** {total_tables}\n")
        f.write(f"- **Tabelas estruturadas:** {tables_with_structure}\n")
        f.write(f"- **Total de células:** {total_cells}\n")
        f.write(f"- **Taxa de estruturação:** {(tables_with_structure/total_tables*100):.1f}%\n\n" if total_tables > 0 else "")
        
        if successful:
            f.write("## ✅ Arquivos processados com sucesso\n\n")
            f.write("| Arquivo | Tamanho | Tabelas | Células | Arquivos Gerados |\n")
            f.write("|---------|---------|---------|---------|------------------|\n")
            
            for result in successful:
                tables = result.get('table_stats', {}).get('total_tables', 0)
                cells = result.get('table_stats', {}).get('total_cells', 0)
                output_count = len(result.get('outputs', {}))
                f.write(f"| `{result['file_name']}` | {result['input_size']:,} B | {tables} | {cells} | {output_count} |\n")
            f.write("\n")
        
        if failed:
            f.write("## ❌ Arquivos com erro\n\n")
            f.write("| Arquivo | Erro | Tamanho |\n")
            f.write("|---------|------|----------|\n")
            
            for result in failed:
                f.write(f"| `{result['file_name']}` | {result['error']} | {result['input_size']:,} B |\n")
            f.write("\n")
        
        f.write("## 📁 Tipos de arquivo gerados\n\n")
        f.write("Para cada documento processado com sucesso, os seguintes arquivos são gerados:\n\n")
        f.write("- **`.md`** - Markdown completo com metadados\n")
        f.write("- **`_TABLES.md`** - Tabelas extraídas em formato Markdown\n")
        f.write("- **`.html`** - Versão HTML do documento\n")
        f.write("- **`.json`** - Estrutura completa do DoclingDocument\n")
        f.write("- **`_TABLE_STATS.json`** - Estatísticas detalhadas das tabelas\n")
    
    print(f"\n📋 Relatório detalhado salvo em: {report_file}")
    print(f"📁 Total de arquivos gerados: {len(os.listdir(OUTPUT_DIR))}")
    print(f"\n🎉 Teste Docling concluído!")
    print(f"📂 Verifique a pasta '{OUTPUT_DIR}' para ver todos os resultados.")

def main():
    """Função principal"""
    print("🚀 SISTEMA COMPLETO DE TESTES DOCLING")
    print("="*60)
    print(f"📂 Pasta de origem: {TEST_FILES_PATH}")
    print(f"📁 Pasta de destino: {OUTPUT_DIR}")
    print(f"🕒 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verificar argumentos da linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file" and len(sys.argv) > 2:
            # Processar arquivo específico
            file_path = sys.argv[2]
            if os.path.exists(file_path):
                ensure_output_directory()
                result = process_single_file(file_path)
                if result:
                    print("\n📊 RESULTADO:")
                    print(f"Status: {result['status']}")
                    if result['status'] == 'success':
                        print(f"Tabelas: {result.get('table_stats', {}).get('total_tables', 0)}")
                        print(f"Arquivos gerados: {len(result.get('outputs', {}))}")
                return
            else:
                print(f"❌ Arquivo não encontrado: {file_path}")
                return
    
    # Verificar se Docling está instalado
    try:
        from docling.document_converter import DocumentConverter
        print("✅ Docling encontrado e configurado")
    except ImportError:
        print("❌ Docling não está instalado!")
        print("Instale com: pip install docling")
        return
    
    # Verificar pasta de origem
    if not os.path.exists(TEST_FILES_PATH):
        print(f"❌ Pasta de origem não encontrada: {TEST_FILES_PATH}")
        print(f"💡 Use: python {sys.argv[0]} --file caminho_arquivo  (para arquivo específico)")
        return
    
    # Criar diretório de saída
    ensure_output_directory()
    
    # Listar arquivos para processar
    files_to_process = []
    try:
        for filename in os.listdir(TEST_FILES_PATH):
            filepath = os.path.join(TEST_FILES_PATH, filename)
            if os.path.isfile(filepath):
                files_to_process.append(filepath)
    except PermissionError:
        print(f"❌ Sem permissão para acessar: {TEST_FILES_PATH}")
        print(f"💡 Use: python {sys.argv[0]} --file caminho_arquivo  (para arquivo específico)")
        return
    
    print(f"\n📋 Arquivos encontrados: {len(files_to_process)}")
    
    # Processar arquivos
    all_results = []
    
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        
        # Verificar se é ZIP (processar conteúdo)
        if filename.lower().endswith('.zip'):
            print(f"\n📦 Processando arquivo ZIP: {filename}")
            zip_results = process_zip_file(filepath)
            all_results.extend(zip_results)
        else:
            # Processar arquivo individual
            result = process_single_file(filepath)
            if result:
                all_results.append(result)
    
    # Gerar relatório final
    if all_results:
        generate_final_report(all_results)
    else:
        print("\n❌ Nenhum arquivo foi processado.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
