"""
Analisador de PDF para identificar estrutura e áreas de texto
"""
import fitz  # PyMuPDF

def analyze_pdf_structure(pdf_path):
    """
    Analisa a estrutura do PDF para identificar o layout e áreas de texto
    """
    print(f"Analisando PDF: {pdf_path}")
    
    # Abrir PDF com PyMuPDF para análise detalhada
    pdf_document = fitz.open(pdf_path)
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        print(f"\n=== PÁGINA {page_num + 1} ===")
        
        # Obter texto da página
        text = page.get_text()
        print(f"Texto encontrado ({len(text)} caracteres):")
        print(text[:500] + "..." if len(text) > 500 else text)
        
        # Obter blocos de texto com coordenadas
        text_blocks = page.get_text("dict")
        print(f"\nBlocos de texto encontrados: {len(text_blocks.get('blocks', []))}")
        
        for i, block in enumerate(text_blocks.get('blocks', [])):
            if 'lines' in block:
                bbox = block['bbox']
                print(f"Bloco {i}: ({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})")
        
        # Identificar áreas vazias na página 2
        if page_num == 1:  # Segunda página (índice 1)
            print("\n=== ANÁLISE DA SEGUNDA PÁGINA ===")
            page_rect = page.rect
            print(f"Dimensões da página: {page_rect.width} x {page_rect.height}")
            
            # Procurar por áreas vazias na parte inferior
            lower_third_y = page_rect.height * 2/3
            print(f"Analisando área inferior (y > {lower_third_y:.1f})")
            
            # Verificar se há blocos de texto na parte inferior
            lower_blocks = []
            for block in text_blocks.get('blocks', []):
                if 'lines' in block:
                    bbox = block['bbox']
                    if bbox[1] > lower_third_y:  # y1 > lower_third
                        lower_blocks.append(block)
            
            print(f"Blocos na área inferior: {len(lower_blocks)}")
            
            if len(lower_blocks) == 0:
                print("ÁREA VAZIA IDENTIFICADA na parte inferior da página 2!")
                empty_area = (0, lower_third_y, page_rect.width, page_rect.height)
                print(f"Coordenadas da área vazia: {empty_area}")
    
    pdf_document.close()

if __name__ == "__main__":
    # Exemplo de uso
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    analyze_pdf_structure(pdf_path)
