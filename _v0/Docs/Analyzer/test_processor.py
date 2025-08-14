"""
Script de teste para o processador de relatórios PDF
"""
from monthly_report_processor import PDFReportProcessor

def test_processor():
    """
    Testa o processador com o PDF de exemplo
    """
    # Caminho do PDF de exemplo
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    # Prompt do usuário
    user_prompt = input("Digite as instruções para o resumo (ou pressione Enter para usar padrão): ").strip()
    
    if not user_prompt:
        user_prompt = "Destaque os principais indicadores financeiros, variações significativas em relação ao mês anterior e pontos de atenção para a gestão."
    
    print(f"\nUsando prompt: {user_prompt}\n")
    
    try:
        # Criar processador
        processor = PDFReportProcessor()
        
        # Processar relatório
        result_path = processor.process_monthly_report(pdf_path, user_prompt)
        
        print(f"\n✅ SUCESSO!")
        print(f"📄 Arquivo original: {pdf_path}")
        print(f"📄 Arquivo com resumo: {result_path}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    test_processor()
