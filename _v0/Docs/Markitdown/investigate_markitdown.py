"""
Investigação detalhada do problema com MarkItDown + LLM para PDFs
"""
import os
from markitdown import MarkItDown
from openai import OpenAI
import fitz  # PyMuPDF

def load_openai_config():
    """Carrega configuração OpenAI"""
    config = {}
    if os.path.exists("openai.env"):
        with open("openai.env", 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

def investigate_pdf_content():
    """Investiga o conteúdo do PDF para ver se há imagens"""
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    print("=== INVESTIGAÇÃO DO CONTEÚDO DO PDF ===\n")
    
    try:
        doc = fitz.open(pdf_path)
        print(f"📄 PDF: {os.path.basename(pdf_path)}")
        print(f"📊 Páginas: {doc.page_count}")
        
        total_images = 0
        total_text_blocks = 0
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Verificar imagens
            image_list = page.get_images()
            text_blocks = page.get_text("dict")["blocks"]
            
            total_images += len(image_list)
            total_text_blocks += len(text_blocks)
            
            if image_list:
                print(f"   📃 Página {page_num + 1}: {len(image_list)} imagem(s), {len(text_blocks)} blocos de texto")
            
        print(f"\n🖼️ Total de imagens no PDF: {total_images}")
        print(f"📝 Total de blocos de texto: {total_text_blocks}")
        
        if total_images == 0:
            print("⚠️ PROBLEMA IDENTIFICADO: PDF não contém imagens embarcadas!")
            print("💡 As 'imagens' podem ser gráficos vetoriais ou tabelas formatadas")
            
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro ao analisar PDF: {e}")

def test_markitdown_with_different_configs():
    """Testa MarkItDown com diferentes configurações"""
    print("\n=== TESTE DE CONFIGURAÇÕES MARKITDOWN ===\n")
    
    config = load_openai_config()
    if 'api_key' not in config:
        print("❌ Chave API não encontrada")
        return
    
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    # Teste 1: MarkItDown simples
    print("1️⃣ Teste MarkItDown básico:")
    try:
        md1 = MarkItDown()
        result1 = md1.convert(pdf_path)
        print(f"   ✅ Sucesso - {len(result1.text_content)} caracteres")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 2: MarkItDown com plugins
    print("\n2️⃣ Teste MarkItDown com plugins:")
    try:
        md2 = MarkItDown(enable_plugins=True)
        result2 = md2.convert(pdf_path)
        print(f"   ✅ Sucesso - {len(result2.text_content)} caracteres")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 3: MarkItDown com OpenAI
    print("\n3️⃣ Teste MarkItDown com OpenAI:")
    try:
        client = OpenAI(api_key=config['api_key'])
        md3 = MarkItDown(llm_client=client, llm_model="gpt-4o")
        result3 = md3.convert(pdf_path)
        print(f"   ✅ Sucesso - {len(result3.text_content)} caracteres")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 4: MarkItDown com OpenAI + plugins
    print("\n4️⃣ Teste MarkItDown com OpenAI + plugins:")
    try:
        client = OpenAI(api_key=config['api_key'])
        md4 = MarkItDown(llm_client=client, llm_model="gpt-4o", enable_plugins=True)
        result4 = md4.convert(pdf_path)
        print(f"   ✅ Sucesso - {len(result4.text_content)} caracteres")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

def test_markitdown_with_image_file():
    """Testa MarkItDown com arquivo de imagem para verificar se LLM funciona"""
    print("\n=== TESTE COM ARQUIVO DE IMAGEM ===\n")
    
    config = load_openai_config()
    if 'api_key' not in config:
        print("❌ Chave API não encontrada")
        return
    
    # Criar uma imagem de teste simples
    from PIL import Image, ImageDraw, ImageFont
    
    # Criar imagem com texto e gráfico simples
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Desenhar um gráfico simples
    draw.rectangle([50, 50, 350, 200], outline='black', width=2)
    draw.rectangle([60, 60, 120, 190], fill='blue')
    draw.rectangle([140, 80, 200, 190], fill='red')
    draw.rectangle([220, 100, 280, 190], fill='green')
    
    # Adicionar texto
    draw.text((150, 220), "Vendas por Trimestre", fill='black')
    draw.text((50, 250), "Q1: 100  Q2: 150  Q3: 200", fill='black')
    
    img.save("test_chart.png")
    print("📊 Imagem de teste criada: test_chart.png")
    
    try:
        # Testar com LLM
        client = OpenAI(api_key=config['api_key'])
        md = MarkItDown(llm_client=client, llm_model="gpt-4o", enable_plugins=True)
        
        result = md.convert("test_chart.png")
        
        print(f"✅ Conversão de imagem concluída")
        print(f"📊 Tamanho do resultado: {len(result.text_content)} caracteres")
        
        # Salvar resultado
        with open("test_image_output.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print(f"📋 Resultado salvo em: test_image_output.md")
        print(f"📝 Preview:")
        print("-" * 50)
        print(result.text_content[:500])
        print("-" * 50)
        
        # Verificar se há descrição do LLM
        if any(word in result.text_content.lower() for word in ['chart', 'graph', 'sales', 'vendas', 'gráfico']):
            print("✅ LLM funcionou - encontrou descrição da imagem!")
        else:
            print("❌ LLM não funcionou - sem descrição inteligente")
            
    except Exception as e:
        print(f"❌ Erro no teste de imagem: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_pdf_content()
    test_markitdown_with_different_configs()
    test_markitdown_with_image_file()
