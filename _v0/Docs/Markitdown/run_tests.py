"""
Script principal para executar todos os testes do MarkItDown
"""

import os
import sys
from datetime import datetime

def print_header():
    """Imprime cabeçalho dos testes"""
    print("=" * 60)
    print("           TESTES MARKITDOWN")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Diretório: {os.getcwd()}")
    print("=" * 60)
    print()

def check_markitdown():
    """Verifica se MarkItDown está instalado"""
    try:
        import markitdown
        print("✅ MarkItDown está instalado")
        return True
    except ImportError:
        print("❌ MarkItDown não está instalado")
        print("Instale com: pip install 'markitdown[all]'")
        return False

def run_test_file(test_file, description):
    """Executa um arquivo de teste"""
    print(f"\n{'='*20} {description} {'='*20}")
    try:
        # Executar o arquivo de teste
        exec(open(test_file).read())
        print(f"✅ {description} concluído com sucesso")
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {test_file}")
    except Exception as e:
        print(f"❌ Erro em {description}: {e}")

def run_all_tests():
    """Executa todos os testes"""
    tests = [
        ("test_basic.py", "Testes Básicos"),
        ("test_images.py", "Testes de Imagens"),
        ("test_office.py", "Testes Office/URLs"),
        ("test_advanced.py", "Testes Avançados")
    ]
    
    results = []
    
    for test_file, description in tests:
        if os.path.exists(test_file):
            try:
                print(f"\n{'='*20} {description} {'='*20}")
                exec(open(test_file).read())
                results.append(f"✅ {description}")
            except Exception as e:
                results.append(f"❌ {description}: {str(e)[:50]}...")
        else:
            results.append(f"⚠️  {description}: Arquivo não encontrado")
    
    return results

def show_summary(results):
    """Mostra resumo dos testes"""
    print("\n" + "=" * 60)
    print("           RESUMO DOS TESTES")
    print("=" * 60)
    
    for result in results:
        print(result)
    
    success_count = sum(1 for r in results if r.startswith("✅"))
    total_count = len(results)
    
    print("-" * 60)
    print(f"Sucessos: {success_count}/{total_count}")
    print(f"Taxa de sucesso: {(success_count/total_count)*100:.1f}%")
    print("=" * 60)

def list_output_files():
    """Lista arquivos de saída gerados"""
    output_files = [f for f in os.listdir('.') if f.startswith('output_') and f.endswith('.md')]
    
    if output_files:
        print(f"\n📁 Arquivos de saída gerados ({len(output_files)}):")
        for file in sorted(output_files):
            size = os.path.getsize(file)
            print(f"  - {file} ({size} bytes)")
    else:
        print("\n📁 Nenhum arquivo de saída encontrado")

def interactive_menu():
    """Menu interativo para escolher testes"""
    while True:
        print("\n" + "=" * 40)
        print("    MENU DE TESTES MARKITDOWN")
        print("=" * 40)
        print("1. Executar todos os testes")
        print("2. Testes básicos (HTML, CSV, JSON)")
        print("3. Testes de imagens (OCR)")
        print("4. Testes Office/URLs (Excel, Word, URLs)")
        print("5. Testes avançados (ZIP, XML, Streaming)")
        print("6. Listar arquivos de saída")
        print("7. Limpar arquivos de saída")
        print("0. Sair")
        print("-" * 40)
        
        choice = input("Escolha uma opção: ").strip()
        
        if choice == "0":
            print("👋 Saindo...")
            break
        elif choice == "1":
            results = run_all_tests()
            show_summary(results)
            list_output_files()
        elif choice == "2":
            run_test_file("test_basic.py", "Testes Básicos")
        elif choice == "3":
            run_test_file("test_images.py", "Testes de Imagens")
        elif choice == "4":
            run_test_file("test_office.py", "Testes Office/URLs")
        elif choice == "5":
            run_test_file("test_advanced.py", "Testes Avançados")
        elif choice == "6":
            list_output_files()
        elif choice == "7":
            clean_output_files()
        else:
            print("❌ Opção inválida!")

def clean_output_files():
    """Limpa arquivos de saída"""
    output_files = [f for f in os.listdir('.') if f.startswith('output_') and f.endswith('.md')]
    
    if output_files:
        print(f"🧹 Limpando {len(output_files)} arquivos de saída...")
        for file in output_files:
            try:
                os.remove(file)
                print(f"  ✅ Removido: {file}")
            except Exception as e:
                print(f"  ❌ Erro ao remover {file}: {e}")
    else:
        print("🧹 Nenhum arquivo de saída para limpar")

if __name__ == "__main__":
    print_header()
    
    if not check_markitdown():
        sys.exit(1)
    
    # Verificar se deve executar no modo interativo
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Modo não-interativo: executar todos os testes
        results = run_all_tests()
        show_summary(results)
        list_output_files()
    else:
        # Modo interativo
        interactive_menu()
