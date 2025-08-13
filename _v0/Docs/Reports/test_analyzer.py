#!/usr/bin/env python3
"""
Script de teste e exemplo para o Analisador Financeiro Automático
"""

import os
from financial_analyzer import FinancialAnalyzer

def test_analyzer():
    """Teste básico do analisador"""
    
    print("🧪 TESTE DO ANALISADOR FINANCEIRO")
    print("=" * 50)
    
    # Arquivo de exemplo (ajuste conforme necessário)
    test_file = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\RESULTADO_ANALITICO_-_MELHOR.xlsx"
    
    # Verificar se arquivo existe
    if not os.path.exists(test_file):
        print(f"❌ Arquivo de teste não encontrado: {test_file}")
        print("\n💡 Para testar, ajuste o caminho em test_analyzer.py")
        print("💡 Ou execute: python financial_analyzer.py seu_arquivo.xlsx")
        return
    
    try:
        # Criar analisador
        print("🔧 Inicializando analisador...")
        analyzer = FinancialAnalyzer()
        
        # Executar análise completa
        print("🚀 Iniciando análise...")
        md_file, analysis_file = analyzer.analyze_financial_report(test_file)
        
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print(f"📄 Markdown: {md_file}")
        print(f"📊 Análise: {analysis_file}")
        
        # Mostrar tamanho dos arquivos
        md_size = os.path.getsize(md_file) / 1024
        analysis_size = os.path.getsize(analysis_file) / 1024
        
        print(f"\n📏 Tamanhos:")
        print(f"  Markdown: {md_size:.1f} KB")
        print(f"  Análise: {analysis_size:.1f} KB")
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

def show_examples():
    """Mostra exemplos de uso"""
    print("📖 EXEMPLOS DE USO DO ANALISADOR FINANCEIRO")
    print("=" * 60)
    
    print("🔸 Análise básica:")
    print("  python financial_analyzer.py relatorio.xlsx")
    
    print("\n🔸 Com prompt personalizado:")
    print('  python financial_analyzer.py relatorio.xlsx --prompt "Foque no CMV e variações do INSS"')
    
    print("\n🔸 Não limpar arquivo do OpenAI:")
    print("  python financial_analyzer.py relatorio.xlsx --no-cleanup")
    
    print("\n🔸 Usar arquivo de configuração específico:")
    print("  python financial_analyzer.py relatorio.xlsx --env custom_openai.env")
    
    print("\n🔸 Ver ajuda completa:")
    print("  python financial_analyzer.py --help")
    
    print("\n📁 ARQUIVOS GERADOS:")
    print("  - ARQUIVO_dec4_YYYYMMDD_HHMMSS.md (Markdown do Excel)")
    print("  - ARQUIVO_ANALISE_YYYYMMDD_HHMMSS.md (Análise IA)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "examples":
        show_examples()
    else:
        test_analyzer()
