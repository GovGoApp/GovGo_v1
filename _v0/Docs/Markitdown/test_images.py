"""
Teste de conversão de imagens com MarkItDown
Demonstra OCR e extração de metadados EXIF
"""

from markitdown import MarkItDown
from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """Cria uma imagem de teste com texto"""
    # Criar uma imagem simples com texto
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Adicionar texto
    try:
        # Tentar usar uma fonte padrão
        font = ImageFont.load_default()
    except:
        font = None
    
    text = "Teste de OCR\nMarkItDown\n2025"
    draw.text((50, 50), text, fill='black', font=font)
    
    # Salvar imagem
    img.save("test_image.png")
    print("✅ Imagem de teste criada: test_image.png")

def test_image_conversion():
    """Teste de conversão de imagem"""
    md = MarkItDown()
    
    print("=== Teste Conversão de Imagem ===\n")
    
    # Criar imagem de teste
    create_test_image()
    
    try:
        # Converter imagem
        result = md.convert("test_image.png")
        print("Conversão Imagem -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("output_image.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão de imagem salva em: output_image.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão de imagem: {e}")
        print("Nota: OCR pode requerer dependências adicionais\n")
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists("test_image.png"):
            os.remove("test_image.png")

def test_image_with_llm():
    """Teste de conversão de imagem com LLM (se disponível)"""
    print("=== Teste Imagem com LLM ===\n")
    
    # Criar imagem de teste
    create_test_image()
    
    try:
        # Tentar importar OpenAI
        from openai import OpenAI
        
        # Configurar cliente OpenAI (precisa de API key)
        # Este teste só funcionará se você tiver uma chave API configurada
        try:
            client = OpenAI()  # Precisa de OPENAI_API_KEY nas variáveis de ambiente
            md = MarkItDown(llm_client=client, llm_model="gpt-4o")
            
            result = md.convert("test_image.png")
            print("Conversão Imagem com LLM -> Markdown:")
            print("-" * 40)
            print(result.text_content)
            print("-" * 40)
            
            with open("output_image_llm.md", "w", encoding="utf-8") as f:
                f.write(result.text_content)
            
            print("✅ Conversão com LLM salva em: output_image_llm.md\n")
            
        except Exception as e:
            print(f"⚠️  LLM não disponível: {e}")
            print("Para usar LLM, configure OPENAI_API_KEY nas variáveis de ambiente\n")
            
    except ImportError:
        print("⚠️  OpenAI não instalado. Para usar LLM, instale: pip install openai\n")
    
    finally:
        if os.path.exists("test_image.png"):
            os.remove("test_image.png")

if __name__ == "__main__":
    test_image_conversion()
    test_image_with_llm()
    print("=== Testes de Imagem Concluídos ===")
