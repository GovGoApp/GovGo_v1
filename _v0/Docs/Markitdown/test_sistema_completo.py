"""
Sistema completo de testes MarkItDown
Processa todos os tipos de arquivos suportados incluindo integração com OpenAI
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import shutil

# Configuração
TEST_FILES_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\TESTE"
OUTPUT_DIR = os.path.join(TEST_FILES_PATH, "conversoes")
OPENAI_ENV_FILE = "openai.env"

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
        from openai import OpenAI
        config = load_openai_config()
        
        if 'api_key' in config:
            os.environ['OPENAI_API_KEY'] = config['api_key']
            client = OpenAI(api_key=config['api_key'])
            print("✅ OpenAI configurado com sucesso")
            return client
        else:
            print("⚠️  Chave API OpenAI não encontrada no arquivo openai.env")
            return None
            
    except ImportError:
        print("⚠️  OpenAI não instalado. Instale com: pip install openai")
        return None
    except Exception as e:
        print(f"⚠️  Erro ao configurar OpenAI: {e}")
        return None

def get_markitdown_instance(openai_client=None):
    """Cria instância MarkItDown com ou sem OpenAI"""
    from markitdown import MarkItDown
    
    if openai_client:
        return MarkItDown(
            llm_client=openai_client, 
            llm_model="gpt-4o",
            enable_plugins=True
        )
    else:
        return MarkItDown(enable_plugins=True)

def create_output_directory():
    """Cria diretório de saída se não existir"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Diretório de saída criado: {OUTPUT_DIR}")
    else:
        print(f"📁 Usando diretório de saída existente: {OUTPUT_DIR}")

def get_file_info(filepath):
    """Obtém informações detalhadas do arquivo"""
    stat = os.stat(filepath)
    size = stat.st_size
    
    # Converter tamanho para formato legível
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

def is_already_converted(file_path, output_dir):
    """Verifica se um arquivo já foi convertido baseado na existência do arquivo markdown correspondente"""
    try:
        # Obter nome base do arquivo sem extensão
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Criar nome do arquivo markdown esperado
        markdown_file = os.path.join(output_dir, f"{base_name}.md")
        
        # Verificar se o arquivo markdown existe e se é mais recente que o arquivo original
        if os.path.exists(markdown_file):
            original_mtime = os.path.getmtime(file_path)
            markdown_mtime = os.path.getmtime(markdown_file)
            return markdown_mtime >= original_mtime
        
        return False
    except Exception as e:
        print(f"Erro ao verificar se arquivo foi convertido: {e}")
        return False

def process_single_file(filepath, md_converter, output_dir):
    """Processa um único arquivo"""
    filename = os.path.basename(filepath)
    file_info = get_file_info(filepath)
    
    print(f"\n📄 Processando: {filename}")
    print(f"   📏 Tamanho: {file_info['size_str']}")
    print(f"   📅 Modificado: {file_info['modified']}")
    print(f"   🔧 Extensão: {file_info['extension']}")
    
    # Verificar se já foi convertido
    if is_already_converted(filepath, output_dir):
        print(f"   ⏭️  Arquivo já convertido - pulando...")
        base_name = Path(filename).stem
        output_filename = f"{base_name}.md"
        output_path = os.path.join(output_dir, output_filename)
        output_size = os.path.getsize(output_path)
        
        return {
            'status': 'success',
            'input_file': filename,
            'output_file': output_filename,
            'input_size': file_info['size'],
            'output_size': output_size,
            'skipped': True
        }
    
    try:
        # Conversão
        print("   🔄 Convertendo...")
        result = md_converter.convert(filepath)
        
        # Nome do arquivo de saída
        base_name = Path(filename).stem
        output_filename = f"{base_name}.md"
        output_path = os.path.join(output_dir, output_filename)
        
        # Salvar resultado
        with open(output_path, 'w', encoding='utf-8') as f:
            # Cabeçalho com metadados
            f.write(f"# Conversão: {filename}\n\n")
            f.write(f"**Arquivo original:** `{filename}`  \n")
            f.write(f"**Tamanho:** {file_info['size_str']}  \n")
            f.write(f"**Modificado:** {file_info['modified']}  \n")
            f.write(f"**Tipo:** {file_info['extension']}  \n")
            f.write(f"**Convertido em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("---\n\n")
            f.write(result.text_content)
        
        # Estatísticas
        output_size = os.path.getsize(output_path)
        compression_ratio = (output_size / file_info['size']) * 100 if file_info['size'] > 0 else 0
        
        print(f"   ✅ Sucesso! Salvo em: {output_filename}")
        print(f"   📊 Markdown: {output_size} bytes ({compression_ratio:.1f}% do original)")
        
        return {
            'status': 'success',
            'input_file': filename,
            'output_file': output_filename,
            'input_size': file_info['size'],
            'output_size': output_size,
            'compression_ratio': compression_ratio,
            'skipped': False
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Erro: {error_msg}")
        
        # Salvar erro em arquivo
        error_filename = f"{Path(filename).stem}_ERROR.md"
        error_path = os.path.join(output_dir, error_filename)
        
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f"# ERRO na conversão: {filename}\n\n")
            f.write(f"**Arquivo:** `{filename}`  \n")
            f.write(f"**Erro:** {error_msg}  \n")
            f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("## Detalhes do arquivo\n\n")
            f.write(f"- Tamanho: {file_info['size_str']}\n")
            f.write(f"- Extensão: {file_info['extension']}\n")
            f.write(f"- Modificado: {file_info['modified']}\n")
        
        return {
            'status': 'error',
            'input_file': filename,
            'error': error_msg,
            'input_size': file_info['size']
        }

def main():
    """Função principal"""
    print("🚀 SISTEMA COMPLETO DE TESTES MARKITDOWN")
    print("="*60)
    print(f"📂 Pasta de origem: {TEST_FILES_PATH}")
    print(f"📁 Pasta de destino: {OUTPUT_DIR}")
    print(f"🕒 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verificar se pasta de origem existe
    if not os.path.exists(TEST_FILES_PATH):
        print(f"❌ Pasta de origem não encontrada: {TEST_FILES_PATH}")
        return
    
    # Configurar OpenAI
    openai_client = setup_openai()
    
    # Criar instância MarkItDown
    md_converter = get_markitdown_instance(openai_client)
    print(f"🔧 MarkItDown configurado (OpenAI: {'Sim' if openai_client else 'Não'})")
    
    # Criar diretório de saída
    create_output_directory()
    
    # Listar arquivos para processar
    files_to_process = []
    for filename in os.listdir(TEST_FILES_PATH):
        filepath = os.path.join(TEST_FILES_PATH, filename)
        if os.path.isfile(filepath):
            files_to_process.append(filepath)
    
    print(f"\n📋 Arquivos encontrados: {len(files_to_process)}")
    
    # Processar arquivos
    all_results = []
    
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        
        # Processar todos os arquivos da mesma forma
        # MarkItDown já processa ZIP nativamente
        result = process_single_file(filepath, md_converter, OUTPUT_DIR)
        all_results.append(result)
    
    # Gerar relatório final
    generate_final_report(all_results)

def generate_final_report(results):
    """Gera relatório final"""
    print(f"\n{'='*60}")
    print("📊 RELATÓRIO FINAL")
    print("="*60)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    skipped = [r for r in successful if r.get('skipped', False)]
    processed = [r for r in successful if not r.get('skipped', False)]
    
    # Estatísticas console
    print(f"✅ Sucessos: {len(successful)}")
    print(f"   🔄 Processados: {len(processed)}")
    print(f"   ⏭️  Pulados (já convertidos): {len(skipped)}")
    print(f"❌ Erros: {len(failed)}")
    print(f"📊 Taxa de sucesso: {(len(successful)/len(results)*100):.1f}%")
    
    if successful:
        total_input = sum(r['input_size'] for r in successful)
        total_output = sum(r['output_size'] for r in successful)
        print(f"📏 Tamanho original: {total_input:,} bytes")
        print(f"📄 Tamanho Markdown: {total_output:,} bytes")
        if total_input > 0:
            print(f"🗜️  Compressão média: {(total_output/total_input*100):.1f}%")
    
    # Relatório detalhado em arquivo
    report_path = os.path.join(OUTPUT_DIR, "RELATORIO_FINAL.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Relatório Final - Conversão MarkItDown\n\n")
        f.write(f"**Data/Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Total de arquivos:** {len(results)}  \n")
        f.write(f"**Sucessos:** {len(successful)}  \n")
        f.write(f"  - **Processados:** {len(processed)}  \n")
        f.write(f"  - **Pulados (já convertidos):** {len(skipped)}  \n")
        f.write(f"**Erros:** {len(failed)}  \n")
        f.write(f"**Taxa de sucesso:** {(len(successful)/len(results)*100):.1f}%  \n\n")
        
        if processed:
            f.write("## 🔄 Arquivos processados\n\n")
            f.write("| Arquivo Original | Arquivo Markdown | Tamanho Original | Tamanho MD | Compressão |\n")
            f.write("|------------------|------------------|------------------|------------|------------|\n")
            
            for result in processed:
                compression = f"{result.get('compression_ratio', 0):.1f}%"
                f.write(f"| `{result['input_file']}` | `{result['output_file']}` | {result['input_size']:,} B | {result['output_size']:,} B | {compression} |\n")
            f.write("\n")
        
        if skipped:
            f.write("## ⏭️ Arquivos pulados (já convertidos)\n\n")
            f.write("| Arquivo Original | Arquivo Markdown | Tamanho Original | Tamanho MD |\n")
            f.write("|------------------|------------------|------------------|------------|\n")
            
            for result in skipped:
                f.write(f"| `{result['input_file']}` | `{result['output_file']}` | {result['input_size']:,} B | {result['output_size']:,} B |\n")
            f.write("\n")
        
        if failed:
            f.write("## ❌ Arquivos com erro\n\n")
            f.write("| Arquivo | Erro | Tamanho |\n")
            f.write("|---------|------|----------|\n")
            
            for result in failed:
                f.write(f"| `{result['input_file']}` | {result['error']} | {result['input_size']:,} B |\n")
            f.write("\n")
        
        f.write("## 📁 Arquivos gerados\n\n")
        md_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.md')]
        for md_file in sorted(md_files):
            f.write(f"- `{md_file}`\n")
    
    print(f"\n📋 Relatório detalhado salvo em: {report_path}")
    print(f"📁 Total de arquivos gerados: {len(os.listdir(OUTPUT_DIR))}")
    print(f"\n🎉 Processamento concluído!")
    print(f"📂 Verifique a pasta '{OUTPUT_DIR}' para ver todos os resultados.")

if __name__ == "__main__":
    try:
        from markitdown import MarkItDown
        main()
    except ImportError:
        print("❌ MarkItDown não está instalado!")
        print("Instale com: pip install 'markitdown[all]'")
    except KeyboardInterrupt:
        print("\n⚠️  Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
