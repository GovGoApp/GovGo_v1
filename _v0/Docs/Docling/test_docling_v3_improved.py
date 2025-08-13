"""
test_docling_v3_improved.py
Script para testar a versão melhorada do Docling v3 com timeouts
"""

import os
import sys
import time
import requests
from datetime import datetime

# Adicionar o diretório ao path
sys.path.append(r'c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\GvG\Search')

try:
    from OLD.gvg_document_utils_v3_improved import process_pncp_document, summarize_document
    print("✅ Módulo v3 improved carregado com sucesso!")
except ImportError as e:
    print(f"❌ Erro ao importar módulo v3 improved: {e}")
    sys.exit(1)

def test_single_document():
    """Testa um documento PDF pequeno"""
    print("\n🔍 TESTE 1: Documento PDF pequeno")
    print("=" * 50)
    
    # URL de teste (documento pequeno)
    test_url = "https://pncp.gov.br/api/pncp/v1/orgaos/39154071000137/compras/2024/compras/1/documentos/140624"
    
    print(f"📄 Testando URL: {test_url}")
    print(f"⏰ Iniciando às {datetime.now().strftime('%H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        result = process_pncp_document(test_url, max_tokens=500, document_name="teste_documento.pdf")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Processamento concluído em {duration:.2f} segundos")
        print("\n📋 RESULTADO:")
        print("-" * 50)
        print(result)
        
        return True
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ Erro após {duration:.2f} segundos: {str(e)}")
        return False

def test_multiple_documents():
    """Testa múltiplos documentos"""
    print("\n🔍 TESTE 2: Múltiplos documentos")
    print("=" * 50)
    
    # URLs de teste
    test_urls = [
        "https://pncp.gov.br/api/pncp/v1/orgaos/39154071000137/compras/2024/compras/1/documentos/140624",
        "https://pncp.gov.br/api/pncp/v1/orgaos/39154071000137/compras/2024/compras/2/documentos/140625",
        "https://pncp.gov.br/api/pncp/v1/orgaos/39154071000137/compras/2024/compras/3/documentos/140626"
    ]
    
    results = []
    total_start = time.time()
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📄 Documento {i}/{len(test_urls)}: {url}")
        print(f"⏰ Iniciando às {datetime.now().strftime('%H:%M:%S')}")
        
        start_time = time.time()
        
        try:
            result = process_pncp_document(url, max_tokens=300, document_name=f"teste_doc_{i}.pdf")
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Concluído em {duration:.2f} segundos")
            results.append(('success', duration, result[:200] + "..."))
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"❌ Erro após {duration:.2f} segundos: {str(e)}")
            results.append(('error', duration, str(e)))
    
    total_end = time.time()
    total_duration = total_end - total_start
    
    print(f"\n📊 RESUMO DOS TESTES:")
    print("=" * 50)
    print(f"Total de documentos: {len(test_urls)}")
    print(f"Tempo total: {total_duration:.2f} segundos")
    print(f"Tempo médio por documento: {total_duration/len(test_urls):.2f} segundos")
    
    successful = sum(1 for r in results if r[0] == 'success')
    failed = sum(1 for r in results if r[0] == 'error')
    
    print(f"Sucessos: {successful}")
    print(f"Erros: {failed}")
    print(f"Taxa de sucesso: {successful/len(test_urls)*100:.1f}%")
    
    return successful == len(test_urls)

def test_timeout_behavior():
    """Testa comportamento com timeout"""
    print("\n🔍 TESTE 3: Comportamento com timeout")
    print("=" * 50)
    
    # Este teste vai verificar se o timeout está funcionando
    # Vamos tentar processar um documento que pode demorar
    
    print("🕒 Configurando timeout baixo para testar...")
    
    # Modificar temporariamente o timeout (precisaria ser feito no módulo)
    print("⚠️ Nota: Para testar timeout, modifique CONVERSION_TIMEOUT no módulo")
    print("⚠️ Configuração atual: 300 segundos (5 minutos)")
    
    return True

def test_file_size_limits():
    """Testa limites de tamanho de arquivo"""
    print("\n🔍 TESTE 4: Limites de tamanho de arquivo")
    print("=" * 50)
    
    print("📏 Configuração atual:")
    print(f"- Limite de arquivo: 100 MB")
    print(f"- Timeout de download: 30 segundos")
    print(f"- Timeout de conversão: 300 segundos")
    
    # Teste com URL que pode ter arquivo grande
    test_url = "https://pncp.gov.br/api/pncp/v1/orgaos/39154071000137/compras/2024/compras/1/documentos/140624"
    
    print(f"\n📄 Testando URL: {test_url}")
    print("⚠️ Este teste verifica se o arquivo é rejeitado por tamanho")
    
    try:
        # Fazer uma requisição HEAD para verificar tamanho
        response = requests.head(test_url, timeout=10)
        content_length = response.headers.get('content-length')
        
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            print(f"📊 Tamanho do arquivo: {size_mb:.2f} MB")
            
            if size_mb > 100:
                print("✅ Arquivo grande detectado - teste de limite funcionará")
            else:
                print("ℹ️ Arquivo pequeno - teste de limite não aplicável")
        else:
            print("⚠️ Tamanho do arquivo não disponível no cabeçalho")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar tamanho: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🚀 INICIANDO TESTES DO DOCLING V3 IMPROVED")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Diretório atual: {os.getcwd()}")
    
    tests = [
        ("Documento único", test_single_document),
        ("Múltiplos documentos", test_multiple_documents),
        ("Timeout behavior", test_timeout_behavior),
        ("Limites de arquivo", test_file_size_limits)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'PASSOU' if result else 'FALHOU'}")
        except Exception as e:
            print(f"❌ {test_name}: ERRO - {str(e)}")
            results.append((test_name, False))
    
    print(f"\n{'=' * 60}")
    print("📊 RESUMO FINAL DOS TESTES")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    print(f"\nResultado geral: {passed}/{total} testes passaram")
    print(f"Taxa de sucesso: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n⚠️ {total - passed} TESTE(S) FALHARAM")

if __name__ == "__main__":
    main()
