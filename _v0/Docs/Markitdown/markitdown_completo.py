"""
Sistema completo de testes MarkItDown - Versão Otimizada
Processa todos os tipos de arquivos usando funcionalidades nativas do MarkItDown
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import shutil

# Configuração
TEST_FILES_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\TESTE"
OUTPUT_DIR = "conversoes"
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
            print("✅ OpenAI configurado com sucesso - Descrições de imagens habilitadas")
            return client
        else:
            print("⚠️  Chave API OpenAI não encontrada no arquivo openai.env")
            print("   ➤ Imagens serão processadas apenas com OCR básico")
            return None
            
    except ImportError:
        print("⚠️  OpenAI não instalado. Para descrições de imagens instale: pip install openai")
        return None
    except Exception as e:
        print(f"⚠️  Erro ao configurar OpenAI: {e}")
        return None

def get_markitdown_instance(openai_client=None):
    """Cria instância MarkItDown otimizada"""
    from markitdown import MarkItDown
    
    if openai_client:
        print("🤖 MarkItDown configurado com IA para imagens (GPT-4o)")
        return MarkItDown(
            llm_client=openai_client, 
            llm_model="gpt-4o",
            enable_plugins=True
        )
    else:
        print("🔧 MarkItDown configurado com processamento básico")
        return MarkItDown(enable_plugins=True)

def create_output_directory():
    """Cria diretório de saída limpo"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    print(f"📁 Diretório de saída criado: {OUTPUT_DIR}")

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

def identify_file_type(filepath):
    """Identifica o tipo de arquivo baseado na extensão"""
    ext = Path(filepath).suffix.lower()
    
    file_types = {
        # Documentos Office
        '.pdf': '📄 PDF',
        '.docx': '📝 Word', 
        '.doc': '📝 Word Legacy',
        '.pptx': '🎨 PowerPoint',
        '.ppt': '🎨 PowerPoint Legacy',
        '.xlsx': '📊 Excel',
        '.xls': '📊 Excel Legacy',
        
        # Imagens
        '.jpg': '🖼️ Imagem JPEG',
        '.jpeg': '🖼️ Imagem JPEG', 
        '.png': '🖼️ Imagem PNG',
        '.gif': '🖼️ Imagem GIF',
        '.bmp': '🖼️ Imagem BMP',
        '.tiff': '🖼️ Imagem TIFF',
        '.webp': '🖼️ Imagem WebP',
        
        # Dados estruturados
        '.csv': '📋 CSV',
        '.json': '🔗 JSON',
        '.xml': '📰 XML',
        '.html': '🌐 HTML',
        '.htm': '🌐 HTML',
        
        # Arquivos compactados
        '.zip': '📦 ZIP',
        '.rar': '📦 RAR',
        '.7z': '📦 7-Zip',
        
        # Áudio/Vídeo
        '.mp3': '🎵 Áudio MP3',
        '.wav': '🎵 Áudio WAV',
        '.mp4': '🎬 Vídeo MP4',
        
        # Texto
        '.txt': '📄 Texto',
        '.md': '📝 Markdown',
        '.rtf': '📄 RTF',
        
        # E-books
        '.epub': '📚 E-book EPUB',
        '.mobi': '📚 E-book MOBI',
    }
    
    return file_types.get(ext, f'❓ Desconhecido ({ext})')

def process_file(filepath, md_converter, output_dir):
    """Processa um único arquivo com MarkItDown"""
    filename = os.path.basename(filepath)
    file_info = get_file_info(filepath)
    file_type = identify_file_type(filepath)
    
    print(f"\n{file_type} Processando: {filename}")
    print(f"   📏 Tamanho: {file_info['size_str']}")
    print(f"   📅 Modificado: {file_info['modified']}")
    
    try:
        # Conversão usando MarkItDown nativo
        print("   🔄 Convertendo com MarkItDown...")
        
        # Para ZIP, o MarkItDown processa automaticamente todos os arquivos internos
        if filename.lower().endswith('.zip'):
            print("   📦 Processando ZIP internamente (todos os arquivos serão incluídos)")
        
        result = md_converter.convert(filepath)
        
        # Nome do arquivo de saída
        base_name = Path(filename).stem
        output_filename = f"{base_name}.md"
        output_path = os.path.join(output_dir, output_filename)
        
        # Preparar conteúdo com metadados
        content_lines = [
            f"# {file_type}: {filename}",
            "",
            "## 📊 Metadados do Arquivo",
            "",
            f"- **Arquivo original:** `{filename}`",
            f"- **Tipo:** {file_type}",
            f"- **Tamanho:** {file_info['size_str']}",
            f"- **Modificado:** {file_info['modified']}",
            f"- **Convertido em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Adicionar informações específicas por tipo
        if filename.lower().endswith('.zip'):
            content_lines.extend([
                "## 📦 Informações do ZIP",
                "",
                "Este arquivo ZIP foi processado automaticamente pelo MarkItDown.",
                "Todos os arquivos internos foram analisados e convertidos.",
                ""
            ])
        elif any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            content_lines.extend([
                "## 🖼️ Processamento de Imagem",
                "",
                "Esta imagem foi processada com:",
                "- OCR para extração de texto",
                "- Análise de metadados EXIF",
            ])
            if "llm_client" in str(md_converter.__dict__):
                content_lines.append("- Descrição inteligente com IA (GPT-4o)")
            content_lines.append("")
        
        content_lines.extend([
            "---",
            "",
            "## 📄 Conteúdo Convertido",
            "",
            result.text_content
        ])
        
        # Salvar arquivo
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        # Estatísticas
        output_size = os.path.getsize(output_path)
        compression_ratio = (output_size / file_info['size']) * 100 if file_info['size'] > 0 else 0
        
        print(f"   ✅ Conversão concluída!")
        print(f"   📄 Arquivo gerado: {output_filename}")
        print(f"   📊 Tamanho MD: {output_size:,} bytes ({compression_ratio:.1f}% do original)")
        
        # Analisar conteúdo convertido
        lines_count = len(result.text_content.split('\n'))
        chars_count = len(result.text_content)
        words_count = len(result.text_content.split())
        
        print(f"   📝 Estatísticas: {lines_count} linhas, {words_count} palavras, {chars_count:,} caracteres")
        
        return {
            'status': 'success',
            'input_file': filename,
            'output_file': output_filename,
            'input_size': file_info['size'],
            'output_size': output_size,
            'compression_ratio': compression_ratio,
            'file_type': file_type,
            'lines': lines_count,
            'words': words_count,
            'chars': chars_count
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Erro na conversão: {error_msg}")
        
        # Salvar relatório de erro detalhado
        error_filename = f"{Path(filename).stem}_ERROR.md"
        error_path = os.path.join(output_dir, error_filename)
        
        error_content = [
            f"# ❌ ERRO: {filename}",
            "",
            "## 📊 Informações do Arquivo",
            "",
            f"- **Arquivo:** `{filename}`",
            f"- **Tipo:** {file_type}",
            f"- **Tamanho:** {file_info['size_str']}",
            f"- **Modificado:** {file_info['modified']}",
            f"- **Tentativa de conversão:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## ⚠️ Detalhes do Erro",
            "",
            f"```",
            f"{error_msg}",
            f"```",
            "",
            "## 🔧 Possíveis Soluções",
            "",
            "1. Verifique se o arquivo não está corrompido",
            "2. Confirme se o formato é suportado pelo MarkItDown",
            "3. Para imagens, verifique dependências de OCR",
            "4. Para Office, instale: `pip install 'markitdown[docx,xlsx,pptx]'`",
            ""
        ]
        
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(error_content))
        
        print(f"   📄 Relatório de erro salvo: {error_filename}")
        
        return {
            'status': 'error',
            'input_file': filename,
            'error': error_msg,
            'input_size': file_info['size'],
            'file_type': file_type
        }

def main():
    """Função principal do sistema"""
    print("🚀 SISTEMA OTIMIZADO DE CONVERSÃO MARKITDOWN")
    print("="*65)
    print(f"📂 Origem: {TEST_FILES_PATH}")
    print(f"📁 Destino: {OUTPUT_DIR}")
    print(f"🕒 Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*65)
    
    # Verificações iniciais
    if not os.path.exists(TEST_FILES_PATH):
        print(f"❌ Pasta de origem não encontrada: {TEST_FILES_PATH}")
        return
    
    # Configurar componentes
    print("\n🔧 Configurando sistema...")
    openai_client = setup_openai()
    md_converter = get_markitdown_instance(openai_client)
    create_output_directory()
    
    # Descobrir arquivos
    files_to_process = []
    for filename in os.listdir(TEST_FILES_PATH):
        filepath = os.path.join(TEST_FILES_PATH, filename)
        if os.path.isfile(filepath):
            files_to_process.append(filepath)
    
    print(f"\n📋 Arquivos descobertos: {len(files_to_process)}")
    
    # Mostrar preview dos arquivos
    print("\n📁 Arquivo encontrados:")
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        file_type = identify_file_type(filepath)
        file_info = get_file_info(filepath)
        print(f"   {file_type} {filename} ({file_info['size_str']})")
    
    # Processar todos os arquivos
    print(f"\n{'='*65}")
    print("🔄 INICIANDO PROCESSAMENTO")
    print("="*65)
    
    results = []
    for i, filepath in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}]", end=" ")
        result = process_file(filepath, md_converter, OUTPUT_DIR)
        results.append(result)
    
    # Gerar relatório final
    generate_comprehensive_report(results)

def generate_comprehensive_report(results):
    """Gera relatório final abrangente"""
    print(f"\n{'='*65}")
    print("📊 RELATÓRIO FINAL COMPLETO")
    print("="*65)
    
    # Separar resultados
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    # Estatísticas básicas
    total_files = len(results)
    success_rate = (len(successful) / total_files * 100) if total_files > 0 else 0
    
    print(f"✅ Sucessos: {len(successful)}")
    print(f"❌ Erros: {len(failed)}")
    print(f"📊 Taxa de sucesso: {success_rate:.1f}%")
    
    if successful:
        # Estatísticas de tamanho
        total_input = sum(r['input_size'] for r in successful)
        total_output = sum(r['output_size'] for r in successful)
        total_words = sum(r['words'] for r in successful)
        total_chars = sum(r['chars'] for r in successful)
        
        print(f"📏 Total original: {total_input:,} bytes")
        print(f"📄 Total Markdown: {total_output:,} bytes")
        print(f"🗜️ Compressão média: {(total_output/total_input*100):.1f}%")
        print(f"📝 Total de palavras extraídas: {total_words:,}")
        print(f"📝 Total de caracteres: {total_chars:,}")
        
        # Análise por tipo de arquivo
        type_stats = {}
        for result in successful:
            file_type = result['file_type']
            if file_type not in type_stats:
                type_stats[file_type] = {'count': 0, 'size': 0, 'words': 0}
            type_stats[file_type]['count'] += 1
            type_stats[file_type]['size'] += result['input_size']
            type_stats[file_type]['words'] += result['words']
        
        print(f"\n📋 Arquivos processados por tipo:")
        for file_type, stats in type_stats.items():
            print(f"   {file_type}: {stats['count']} arquivo(s), {stats['words']:,} palavras")
    
    # Relatório detalhado em arquivo
    report_path = os.path.join(OUTPUT_DIR, "RELATORIO_COMPLETO.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 📊 Relatório Completo - Conversão MarkItDown\n\n")
        f.write(f"**🕒 Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**📂 Pasta origem:** `{TEST_FILES_PATH}`  \n")
        f.write(f"**📁 Pasta destino:** `{OUTPUT_DIR}`  \n\n")
        
        # Resumo executivo
        f.write("## 📈 Resumo Executivo\n\n")
        f.write(f"- **Total de arquivos:** {total_files}\n")
        f.write(f"- **✅ Sucessos:** {len(successful)}\n")
        f.write(f"- **❌ Erros:** {len(failed)}\n")
        f.write(f"- **📊 Taxa de sucesso:** {success_rate:.1f}%\n\n")
        
        if successful:
            f.write("## ✅ Conversões Bem-sucedidas\n\n")
            f.write("| Arquivo | Tipo | Tamanho Original | Markdown | Compressão | Palavras |\n")
            f.write("|---------|------|------------------|----------|------------|----------|\n")
            
            for result in successful:
                compression = f"{result['compression_ratio']:.1f}%"
                f.write(f"| `{result['input_file']}` | {result['file_type']} | {result['input_size']:,} B | {result['output_size']:,} B | {compression} | {result['words']:,} |\n")
            f.write("\n")
        
        if failed:
            f.write("## ❌ Erros de Conversão\n\n")
            f.write("| Arquivo | Tipo | Tamanho | Erro |\n")
            f.write("|---------|------|---------|------|\n")
            
            for result in failed:
                f.write(f"| `{result['input_file']}` | {result['file_type']} | {result['input_size']:,} B | {result['error'][:50]}... |\n")
            f.write("\n")
        
        # Lista de arquivos gerados
        f.write("## 📁 Arquivos Gerados\n\n")
        md_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.md')]
        f.write(f"Total de arquivos Markdown gerados: **{len(md_files)}**\n\n")
        
        for md_file in sorted(md_files):
            f.write(f"- [`{md_file}`](./{md_file})\n")
        
        f.write("\n---\n\n")
        f.write("*Relatório gerado automaticamente pelo Sistema MarkItDown*")
    
    print(f"\n📋 Relatório detalhado: {report_path}")
    print(f"📁 Arquivos gerados: {len(os.listdir(OUTPUT_DIR))}")
    print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
    print(f"📂 Acesse a pasta '{OUTPUT_DIR}' para ver todos os resultados.")

if __name__ == "__main__":
    try:
        from markitdown import MarkItDown
        main()
    except ImportError:
        print("❌ MarkItDown não está instalado!")
        print("💡 Instale com: pip install 'markitdown[all]'")
    except KeyboardInterrupt:
        print("\n⚠️ Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
