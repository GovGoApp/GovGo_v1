"""
Teste específico para verificar processamento de PDFs com imagens e tabelas
"""
import os
from markitdown import MarkItDown
from openai import OpenAI

def load_openai_config():
    """Carrega configuração OpenAI do arquivo .env"""
    config = {}
    if os.path.exists("openai.env"):
        with open("openai.env", 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

def test_pdf_with_llm():
    """Testa PDF com MarkItDown + LLM configurado corretamente"""
    print("=== TESTE PDF COM IMAGENS E TABELAS ===\n")
    
    # Configurar OpenAI
    config = load_openai_config()
    if 'api_key' not in config:
        print("❌ Chave API não encontrada no openai.env")
        return
    
    try:
        # Configurar cliente OpenAI
        client = OpenAI(api_key=config['api_key'])
        print("✅ Cliente OpenAI configurado")
        
        # Criar MarkItDown com LLM
        md = MarkItDown(
            llm_client=client,
            llm_model="gpt-4o",
            enable_plugins=True
        )
        print("✅ MarkItDown configurado com LLM e plugins")
        
        # Testar com PDF que sabemos que tem imagens/tabelas
        # Usar o mesmo PDF do sistema v3
        pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF não encontrado: {pdf_path}")
            return
        
        print(f"📄 Processando PDF: {os.path.basename(pdf_path)}")
        
        # Converter PDF
        result = md.convert(pdf_path)
        
        print(f"✅ Conversão concluída")
        print(f"📊 Tamanho do conteúdo: {len(result.text_content)} caracteres")
        
        # Salvar resultado para análise
        with open("test_pdf_output.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        # Analisar conteúdo
        content = result.text_content
        
        # Verificar se processou imagens
        image_indicators = [
            "![", "image", "figura", "gráfico", "chart", "graph", 
            "visual", "diagram", "tabela", "table"
        ]
        
        found_images = []
        for indicator in image_indicators:
            if indicator.lower() in content.lower():
                found_images.append(indicator)
        
        print(f"\n📊 Análise do conteúdo:")
        print(f"   - Caracteres totais: {len(content)}")
        print(f"   - Linhas: {len(content.splitlines())}")
        print(f"   - Indicadores de imagem/tabela encontrados: {found_images}")
        
        # Mostrar primeiros 1000 caracteres
        print(f"\n📋 Preview do conteúdo:")
        print("-" * 50)
        print(content[:1000])
        if len(content) > 1000:
            print("... (truncado)")
        print("-" * 50)
        
        # Verificar se há descrições de imagens geradas pelo LLM
        llm_descriptions = [
            "descrição", "description", "The image shows", "Esta imagem", 
            "gpt-4", "análise", "visualization"
        ]
        
        found_descriptions = []
        for desc in llm_descriptions:
            if desc.lower() in content.lower():
                found_descriptions.append(desc)
        
        print(f"\n🤖 Descrições LLM encontradas: {found_descriptions}")
        
        print(f"\n✅ Resultado salvo em: test_pdf_output.md")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

def test_basic_pdf():
    """Teste básico sem LLM para comparação"""
    print("\n=== TESTE PDF BÁSICO (SEM LLM) ===\n")
    
    try:
        # MarkItDown básico
        md = MarkItDown()
        print("✅ MarkItDown básico configurado")
        
        # Testar mesmo PDF
        pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF não encontrado: {pdf_path}")
            return
        
        result = md.convert(pdf_path)
        
        print(f"✅ Conversão básica concluída")
        print(f"📊 Tamanho do conteúdo: {len(result.text_content)} caracteres")
        
        # Salvar para comparação
        with open("test_pdf_basic_output.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print(f"✅ Resultado básico salvo em: test_pdf_basic_output.md")
        
    except Exception as e:
        print(f"❌ Erro no teste básico: {e}")

if __name__ == "__main__":
    test_pdf_with_llm()
    test_basic_pdf()
    
    print("\n🎯 COMPARAÇÃO:")
    print("   - test_pdf_output.md = MarkItDown + LLM")
    print("   - test_pdf_basic_output.md = MarkItDown básico")
    print("   Compare os dois arquivos para ver a diferença!")
