"""
Teste das otimizações do Docling v3 SUPER OTIMIZADO
Compara velocidade entre configuração otimizada e padrão
SALVA os arquivos Markdown em CONV_Docling
"""

import os
import sys
import time
from pathlib import Path

# Adicionar caminho dos módulos
sys.path.append(r"C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\GvG\Search")

try:
    from gvg_document_utils_v3 import (
        process_pncp_document, 
        convert_document_to_markdown, 
        is_zip_file, 
        extract_first_pdf_from_zip,
        extract_all_supported_files_from_zip
    )
    print("✅ Módulo v3 SUPER OTIMIZADO carregado com sucesso!")
except ImportError as e:
    print(f"❌ Erro ao importar v3: {e}")
    sys.exit(1)

def save_markdown_to_test_folder(markdown_content, original_filename, output_folder):
    """
    Salva o conteúdo Markdown na pasta de teste especificada
    
    Args:
        markdown_content (str): Conteúdo Markdown
        original_filename (str): Nome do arquivo original
        output_folder (str): Pasta de destino
        
    Returns:
        tuple: (sucesso, caminho_arquivo_salvo, erro)
    """
    try:
        # Criar pasta se não existir
        os.makedirs(output_folder, exist_ok=True)
        
        # Criar nome seguro para o arquivo baseado no nome original
        base_name = os.path.splitext(original_filename)[0]  # Remove extensão (.pdf, .zip, etc)
        safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name[:100]  # Limitar tamanho
        
        if not safe_name:
            safe_name = f"documento_{int(time.time())}"
        
        # Nome do arquivo Markdown
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        markdown_filename = f"DOCLING_{safe_name}_{timestamp}.md"
        markdown_path = os.path.join(output_folder, markdown_filename)
        
        # Se arquivo já existe, adicionar sufixo
        counter = 1
        while os.path.exists(markdown_path):
            base, ext = os.path.splitext(markdown_filename)
            markdown_filename = f"{base}_{counter:03d}{ext}"
            markdown_path = os.path.join(output_folder, markdown_filename)
            counter += 1
        
        # Salvar arquivo
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return True, markdown_path, None
        
    except Exception as e:
        return False, None, f"Erro ao salvar arquivo: {str(e)}"

def test_optimized_conversion():
    """Testa a conversão otimizada com TODOS os arquivos da pasta E SALVA em CONV_Docling"""
    
    # Pasta de teste (origem)
    test_folder = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\TESTE"
    
    # Pasta de saída para arquivos Markdown convertidos
    output_folder = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\TESTE\CONV_Docling"
    
    if not os.path.exists(test_folder):
        print(f"❌ Pasta de teste não encontrada: {test_folder}")
        return
    
    print(f"📂 Pasta de origem: {test_folder}")
    print(f"📂 Pasta de saída: {output_folder}")
    
    # Criar pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)
    print(f"✅ Pasta de saída criada/verificada: {output_folder}")
    
    # Buscar todos os arquivos suportados
    supported_extensions = ['.pdf', '.docx', '.doc', '.pptx', '.txt', '.md', '.zip', '.xlsx', '.xls', '.csv']
    test_files = []
    
    print(f"🔍 Buscando arquivos em: {test_folder}")
    
    for filename in os.listdir(test_folder):
        file_path = os.path.join(test_folder, filename)
        if os.path.isfile(file_path):
            file_ext = Path(filename).suffix.lower()
            if file_ext in supported_extensions:
                test_files.append(file_path)
    
    if not test_files:
        print("❌ Nenhum arquivo suportado encontrado na pasta")
        print(f"Extensões suportadas: {', '.join(supported_extensions)}")
        return
    
    print(f"📁 Encontrados {len(test_files)} arquivo(s) para teste:")
    for i, file in enumerate(test_files, 1):
        size = os.path.getsize(file) / (1024 * 1024)
        print(f"  {i}. {Path(file).name} ({size:.2f} MB)")
    
    # Executar teste em todos os arquivos
    print("\n" + "="*80)
    print("🚀 INICIANDO TESTE EM LOTE - DOCLING V3 SUPER OTIMIZADO")
    print("="*80)
    
    total_files = len(test_files)
    successful_conversions = 0
    total_time = 0
    total_size = 0
    results = []
    
    for i, test_file in enumerate(test_files, 1):
        filename = Path(test_file).name
        file_size = os.path.getsize(test_file) / (1024 * 1024)
        total_size += file_size
        
        print(f"\n📄 [{i}/{total_files}] Processando: {filename}")
        print(f"   📏 Tamanho: {file_size:.2f} MB")
        
        start_time = time.time()
        
        try:
            # Detectar tipo de arquivo e processar adequadamente
            file_extension = Path(test_file).suffix.lower()
            
            # Verificar se é arquivo comprimido (ZIP, RAR, etc.)
            if file_extension in ['.zip', '.rar', '.7z'] or (file_extension == '' and is_zip_file(test_file)):
                print(f"   📦 Arquivo comprimido detectado ({file_extension})...")
                
                if file_extension == '.zip' or is_zip_file(test_file):
                    # Extrair TODOS os arquivos suportados do ZIP
                    extract_success, extracted_files_list, extract_error = extract_all_supported_files_from_zip(test_file)
                    
                    if extract_success and extracted_files_list:
                        # Processar cada arquivo extraído
                        zip_results = []
                        total_markdown_content = f"# Arquivos extraídos de {filename}\n\n"
                        
                        for extracted_path, original_name in extracted_files_list:
                            print(f"   📄 Processando arquivo extraído: {original_name}")
                            
                            # Verificar se o arquivo extraído existe
                            if os.path.exists(extracted_path):
                                file_size_extracted = os.path.getsize(extracted_path) / (1024 * 1024)
                                print(f"   📏 Tamanho: {file_size_extracted:.2f} MB")
                                
                                # Processar o arquivo extraído
                                file_success, file_markdown, file_error = convert_document_to_markdown(
                                    extracted_path, 
                                    original_name
                                )
                                
                                if file_success:
                                    total_markdown_content += f"\n\n---\n\n## Arquivo: {original_name}\n\n{file_markdown}\n\n"
                                    zip_results.append({
                                        'name': original_name,
                                        'success': True,
                                        'size': file_size_extracted,
                                        'chars': len(file_markdown)
                                    })
                                    print(f"   ✅ {original_name} processado com sucesso")
                                else:
                                    zip_results.append({
                                        'name': original_name,
                                        'success': False,
                                        'error': file_error
                                    })
                                    print(f"   ❌ Erro em {original_name}: {file_error}")
                            else:
                                print(f"   ❌ Arquivo extraído não encontrado: {original_name}")
                        
                        # Limpar arquivos temporários
                        try:
                            import shutil
                            extract_dir = os.path.dirname(extracted_files_list[0][0])
                            if os.path.exists(extract_dir):
                                shutil.rmtree(extract_dir)
                        except Exception as cleanup_error:
                            print(f"   ⚠️ Aviso: Erro na limpeza: {cleanup_error}")
                        
                        # Consolidar resultado
                        successful_files = [r for r in zip_results if r['success']]
                        if successful_files:
                            success = True
                            markdown_content = total_markdown_content
                            error = None
                            print(f"   ✅ ZIP processado: {len(successful_files)}/{len(zip_results)} arquivos")
                        else:
                            success = False
                            error = "Nenhum arquivo do ZIP foi processado com sucesso"
                            markdown_content = None
                            
                    else:
                        success = False
                        error = f"Erro ao extrair ZIP: {extract_error}"
                        markdown_content = None
                        
                else:
                    # Outros formatos comprimidos (RAR, 7Z) não suportados ainda
                    success = False
                    error = f"Formato comprimido {file_extension} não suportado ainda"
                    markdown_content = None
                    
            else:
                # Processar arquivo diretamente (PDF, DOCX, PPTX, XLSX, CSV, etc.)
                print(f"   📄 Processando {file_extension.upper()} diretamente...")
                success, markdown_content, error = convert_document_to_markdown(
                    test_file, 
                    filename
                )
            
            end_time = time.time()
            elapsed = end_time - start_time
            total_time += elapsed
            
            if success:
                successful_conversions += 1
                
                # SALVAR arquivo Markdown convertido
                save_success, saved_path, save_error = save_markdown_to_test_folder(
                    markdown_content, 
                    filename, 
                    output_folder
                )
                
                if save_success:
                    saved_filename = os.path.basename(saved_path)
                    print(f"   💾 Salvo como: {saved_filename}")
                else:
                    print(f"   ⚠️ Erro ao salvar: {save_error}")
                
                # Análise do conteúdo
                lines = markdown_content.split('\n')
                table_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
                
                mb_per_second = file_size / elapsed if elapsed > 0 else 0
                
                result = {
                    'filename': filename,
                    'success': True,
                    'size_mb': file_size,
                    'time_seconds': elapsed,
                    'speed_mb_s': mb_per_second,
                    'markdown_chars': len(markdown_content),
                    'total_lines': len(lines),
                    'table_lines': len(table_lines),
                    'saved_file': saved_filename if save_success else 'ERRO'
                }
                
                print(f"   ✅ SUCESSO em {elapsed:.2f}s ({mb_per_second:.2f} MB/s)")
                print(f"   � Markdown: {len(markdown_content):,} chars, {len(lines):,} linhas, {len(table_lines):,} tabelas")
                
            else:
                result = {
                    'filename': filename,
                    'success': False,
                    'size_mb': file_size,
                    'time_seconds': elapsed,
                    'error': error
                }
                print(f"   ❌ ERRO em {elapsed:.2f}s: {error}")
            
            results.append(result)
                
        except Exception as e:
            end_time = time.time()
            elapsed = end_time - start_time
            total_time += elapsed
            
            result = {
                'filename': filename,
                'success': False,
                'size_mb': file_size,
                'time_seconds': elapsed,
                'error': f"Exception: {str(e)}"
            }
            
            print(f"   ❌ EXCEPTION em {elapsed:.2f}s: {str(e)}")
            results.append(result)
    
    # Relatório final
    print("\n" + "="*80)
    print("� RELATÓRIO FINAL - DOCLING V3 SUPER OTIMIZADO")
    print("="*80)
    
    success_rate = (successful_conversions / total_files) * 100
    avg_speed = total_size / total_time if total_time > 0 else 0
    
    print(f"📈 Taxa de sucesso: {successful_conversions}/{total_files} ({success_rate:.1f}%)")
    print(f"⏱️  Tempo total: {total_time:.2f} segundos")
    print(f"📊 Tamanho total processado: {total_size:.2f} MB")
    print(f"🏃 Velocidade média: {avg_speed:.2f} MB/s")
    
    if successful_conversions > 0:
        successful_results = [r for r in results if r['success']]
        fastest = min(successful_results, key=lambda x: x['speed_mb_s'])
        slowest = max(successful_results, key=lambda x: x['speed_mb_s'])
        
        print(f"\n🏆 Arquivo mais rápido: {fastest['filename']} ({fastest['speed_mb_s']:.2f} MB/s)")
        print(f"🐌 Arquivo mais lento: {slowest['filename']} ({slowest['speed_mb_s']:.2f} MB/s)")
    
    # Detalhes por arquivo
    print(f"\n📋 DETALHES POR ARQUIVO:")
    print("-" * 80)
    for result in results:
        status = "✅" if result['success'] else "❌"
        if result['success']:
            print(f"{status} {result['filename']:30} | {result['size_mb']:6.2f}MB | {result['time_seconds']:6.2f}s | {result['speed_mb_s']:6.2f}MB/s")
        else:
            print(f"{status} {result['filename']:30} | {result['size_mb']:6.2f}MB | {result['time_seconds']:6.2f}s | ERRO: {result['error'][:30]}")
    
    print("\n🎉 TESTE COMPLETO!")

if __name__ == "__main__":
    print("🔬 TESTE DOCLING V3 SUPER OTIMIZADO")
    print("Otimizações aplicadas:")
    print("  ✅ Backend PyPdfium2 (mais rápido)")
    print("  ✅ TableFormer FAST mode")
    print("  ✅ Cell matching desabilitado")
    print("  ✅ OCR desabilitado")
    print("  ✅ Enriquecimentos desabilitados")
    print("  ✅ AcceleratorOptions (4 threads, AUTO device)")
    
    test_optimized_conversion()
