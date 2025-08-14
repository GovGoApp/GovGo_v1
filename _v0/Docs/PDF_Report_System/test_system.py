#!/usr/bin/env python3
"""
Script de teste para o processador de relatórios PDF
"""

from pdf_report_processor import PDFReportProcessor
import os

def test_pdf_processor():
    """
    Testa o processador com o PDF de exemplo do usuário
    """
    # PDF de exemplo fornecido pelo usuário
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    print("🧪 TESTE DO SISTEMA DE PROCESSAMENTO PDF")
    print("=" * 60)
    print(f"📄 Arquivo de teste: {pdf_path}")
    
    # Verificar se arquivo existe
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        print("💡 Verifique se o caminho está correto")
        return
    
    try:
        # Criar processador (irá solicitar Assistant ID)
        print("\n🔧 Inicializando processador...")
        processor = PDFReportProcessor()
        
        # Prompt de teste
        user_prompt = """
        Foque nos seguintes aspectos para o resumo executivo:
        1. Principais indicadores financeiros do mês
        2. Comparação com o mês anterior
        3. Destaques operacionais
        4. Pontos de atenção para gestão
        5. Tendências identificadas
        
        Mantenha linguagem executiva e seja específico com números.
        """
        
        print(f"\n📝 Prompt de teste configurado")
        print("🚀 Iniciando processamento...")
        
        # Processar relatório
        result_path = processor.process_monthly_report(pdf_path, user_prompt)
        
        print(f"\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print(f"📁 Arquivo original: {pdf_path}")
        print(f"📊 Arquivo gerado: {result_path}")
        print("\n💡 Abra o arquivo gerado para verificar o resumo inserido!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_processor()
