"""
Teste Docling Simples - Apenas Markdown
Gera apenas arquivos .md com foco em tabelas de PDFs
"""

import os
import sys
import warnings
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Suprimir warnings do PyTorch/Docling
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
    """Obtém informações básicas do arquivo"""
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
    
    return {
        'size': size,
        'size_str': size_str,
        'extension': Path(filepath).suffix.lower()
    }

def count_tables_in_doc(doc) -> int:
    """Conta o número de tabelas no documento"""
    if not doc or not hasattr(doc, 'tables'):
        return 0
    return len(doc.tables)

def process_single_file(filepath: str, display_name: str = None) -> Dict[str, Any]:
    """Processa um único arquivo com Docling e gera apenas MD"""
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
    print(f"   🔧 Extensão: {file_info['extension']}")
    
    try:
        # Converter documento
        converter = DocumentConverter()
        print("   🔄 Convertendo com Docling...")
        result = converter.convert(filepath)
        doc = result.document
        
        # Contar tabelas
        table_count = count_tables_in_doc(doc)
        
        # Extrair conteúdo markdown
        markdown_content = doc.export_to_markdown()
        
        # Nome do arquivo de saída
        safe_name = "".join(c for c in Path(filename).stem if c.isalnum() or c in (' ', '-', '_')).strip()[:100]
        if not safe_name:
            safe_name = f"documento_{datetime.now().strftime('%H%M%S')}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Salvar arquivo Markdown
        md_file = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Conversão Docling: {filename}\n\n")
            f.write(f"**Arquivo original:** `{filename}`  \n")
            f.write(f"**Tamanho:** {file_info['size_str']}  \n")
            f.write(f"**Extensão:** {file_info['extension']}  \n")
            f.write(f"**Tabelas encontradas:** {table_count}  \n")
            f.write(f"**Processado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Ferramenta:** Docling  \n\n")
            f.write("---\n\n")
            f.write(markdown_content)
        
        file_size = os.path.getsize(md_file)
        print(f"   ✅ Sucesso! Arquivo gerado:")
        print(f"      📝 {os.path.basename(md_file)} ({file_size:,} bytes)")
        print(f"      📊 Tabelas: {table_count}")
        
        return {
            'status': 'success',
            'file_name': filename,
            'input_size': file_info['size'],
            'output_file': md_file,
            'output_size': file_size,
            'table_count': table_count
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Erro: {error_msg}")
        
        # Salvar arquivo de erro
        error_file = os.path.join(OUTPUT_DIR, f"ERROR_{Path(filename).stem}_{datetime.now().strftime('%H%M%S')}.md")
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"# ERRO na conversão Docling: {filename}\n\n")
            f.write(f"**Arquivo:** `{filename}`  \n")
            f.write(f"**Erro:** {error_msg}  \n")
            f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("## Detalhes do arquivo\n\n")
            f.write(f"- Tamanho: {file_info['size_str']}\n")
            f.write(f"- Extensão: {file_info['extension']}\n")
        
        return {
            'status': 'error',
            'file_name': filename,
            'error': error_msg,
            'input_size': file_info['size']
        }

def process_zip_file(zip_path: str) -> List[Dict[str, Any]]:
    """Processa arquivos dentro de um ZIP e gera apenas MDs"""
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
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
    
    except Exception as e:
        print(f"❌ Erro ao processar ZIP: {e}")
        results.append({
            'status': 'error',
            'file_name': os.path.basename(zip_path),
            'error': f"Erro ZIP: {str(e)}"
        })
    
    return results

def generate_simple_report(all_results: List[Dict[str, Any]]):
    """Gera relatório simples"""
    print(f"\n{'='*50}")
    print("📊 RELATÓRIO FINAL - DOCLING MD")
    print("="*50)
    
    successful = [r for r in all_results if r['status'] == 'success']
    failed = [r for r in all_results if r['status'] == 'error']
    
    print(f"✅ Sucessos: {len(successful)}")
    print(f"❌ Erros: {len(failed)}")
    print(f"📊 Taxa de sucesso: {(len(successful)/len(all_results)*100):.1f}%")
    
    if successful:
        total_tables = sum(r.get('table_count', 0) for r in successful)
        total_input = sum(r['input_size'] for r in successful)
        total_output = sum(r['output_size'] for r in successful)
        
        print(f"\n📋 ESTATÍSTICAS:")
        print(f"   📊 Total de tabelas: {total_tables}")
        print(f"   📏 Tamanho original: {total_input:,} bytes")
        print(f"   📄 Tamanho MD gerado: {total_output:,} bytes")
        print(f"   📈 Expansão: {(total_output/total_input*100):.1f}%")
    
    # Relatório em arquivo
    report_file = os.path.join(OUTPUT_DIR, "RELATORIO_DOCLING_MD.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Relatório - Conversão Docling para MD\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Diretório:** `{OUTPUT_DIR}`  \n")
        f.write(f"**Arquivos processados:** {len(all_results)}  \n")
        f.write(f"**Sucessos:** {len(successful)}  \n")
        f.write(f"**Erros:** {len(failed)}  \n\n")
        
        if successful:
            f.write("## ✅ Arquivos convertidos\n\n")
            f.write("| Arquivo | Tamanho | Tabelas | Arquivo MD |\n")
            f.write("|---------|---------|---------|------------|\n")
            
            for result in successful:
                tables = result.get('table_count', 0)
                md_name = os.path.basename(result['output_file'])
                f.write(f"| `{result['file_name']}` | {result['input_size']:,} B | {tables} | `{md_name}` |\n")
            f.write("\n")
        
        if failed:
            f.write("## ❌ Arquivos com erro\n\n")
            f.write("| Arquivo | Erro |\n")
            f.write("|---------|------|\n")
            
            for result in failed:
                f.write(f"| `{result['file_name']}` | {result['error']} |\n")
            f.write("\n")
    
    print(f"\n📋 Relatório salvo em: {os.path.basename(report_file)}")
    print(f"📁 Arquivos gerados: {len(os.listdir(OUTPUT_DIR))}")
    print(f"📂 Pasta: {OUTPUT_DIR}")

def main():
    """Função principal"""
    print("🚀 DOCLING - CONVERSÃO SIMPLES PARA MD")
    print("="*50)
    print(f"📂 Origem: {TEST_FILES_PATH}")
    print(f"📁 Destino: {OUTPUT_DIR}")
    print("="*50)
    
    # Processar arquivo específico se fornecido
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            ensure_output_directory()
            result = process_single_file(file_path)
            if result:
                print(f"\n📊 RESULTADO:")
                print(f"Status: {result['status']}")
                if result['status'] == 'success':
                    print(f"Tabelas: {result.get('table_count', 0)}")
                    print(f"Arquivo: {os.path.basename(result['output_file'])}")
            return
        else:
            print(f"❌ Arquivo não encontrado: {file_path}")
            return
    
    # Verificar Docling
    try:
        from docling.document_converter import DocumentConverter
        print("✅ Docling OK")
    except ImportError:
        print("❌ Docling não instalado! Use: pip install docling")
        return
    
    # Verificar pasta de origem
    if not os.path.exists(TEST_FILES_PATH):
        print(f"❌ Pasta não encontrada: {TEST_FILES_PATH}")
        print(f"💡 Use: python {sys.argv[0]} caminho_arquivo")
        return
    
    # Criar diretório de saída
    ensure_output_directory()
    
    # Listar arquivos
    files_to_process = []
    try:
        for filename in os.listdir(TEST_FILES_PATH):
            filepath = os.path.join(TEST_FILES_PATH, filename)
            if os.path.isfile(filepath) and not filename.startswith('.'):
                files_to_process.append(filepath)
    except PermissionError:
        print(f"❌ Sem permissão para acessar: {TEST_FILES_PATH}")
        return
    
    if not files_to_process:
        print("❌ Nenhum arquivo encontrado para processar")
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
    
    # Gerar relatório
    if all_results:
        generate_simple_report(all_results)
    else:
        print("\n❌ Nenhum arquivo foi processado.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
