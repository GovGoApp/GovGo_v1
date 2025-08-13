"""
Solução Híbrida: PDF Report Processor v4
Combina extração manual de imagens + MarkItDown + LLM
"""
import os
import fitz  # PyMuPDF
from markitdown import MarkItDown
from openai import OpenAI
from datetime import datetime
from pathlib import Path
import io
from PIL import Image

class HybridPDFProcessor:
    """Processador híbrido que extrai imagens de PDFs e usa LLM para descrever"""
    
    def __init__(self):
        self.setup_openai()
        self.setup_markitdown()
    
    def setup_openai(self):
        """Configura cliente OpenAI"""
        config = self.load_openai_config()
        if 'api_key' in config:
            self.client = OpenAI(api_key=config['api_key'])
            print("✅ OpenAI configurado")
        else:
            raise Exception("❌ Chave API OpenAI não encontrada!")
    
    def load_openai_config(self):
        """Carrega configuração OpenAI"""
        config = {}
        if os.path.exists("openai.env"):
            with open("openai.env", 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        return config
    
    def setup_markitdown(self):
        """Configura MarkItDown com LLM"""
        self.md_converter = MarkItDown(
            llm_client=self.client,
            llm_model="gpt-4o",
            enable_plugins=True
        )
        print("✅ MarkItDown configurado com LLM")
    
    def extract_text_from_pdf(self, pdf_path):
        """Extrai apenas texto do PDF (sem imagens)"""
        print("📝 Extraindo texto do PDF...")
        
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text_content += f"\n## Página {page_num + 1}\n\n"
                text_content += page.get_text()
                text_content += "\n"
            
            doc.close()
            print(f"✅ Texto extraído: {len(text_content)} caracteres")
            return text_content
            
        except Exception as e:
            print(f"❌ Erro ao extrair texto: {e}")
            return ""
    
    def extract_images_from_pdf(self, pdf_path):
        """Extrai todas as imagens do PDF"""
        print("🖼️ Extraindo imagens do PDF...")
        
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    # Obter dados da imagem
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        # Converter para PNG
                        img_data = pix.pil_tobytes(format="PNG")
                        
                        # Salvar temporariamente
                        temp_filename = f"temp_image_p{page_num+1}_{img_index+1}.png"
                        
                        with open(temp_filename, "wb") as f:
                            f.write(img_data)
                        
                        images.append({
                            'filename': temp_filename,
                            'page': page_num + 1,
                            'index': img_index + 1,
                            'data': img_data
                        })
                        
                        print(f"   📷 Imagem extraída: Página {page_num+1}, #{img_index+1}")
                    
                    pix = None
            
            doc.close()
            print(f"✅ Total de imagens extraídas: {len(images)}")
            return images
            
        except Exception as e:
            print(f"❌ Erro ao extrair imagens: {e}")
            return []
    
    def process_image_with_llm(self, image_info):
        """Processa uma imagem com LLM para obter descrição"""
        try:
            # Usar MarkItDown para processar a imagem
            result = self.md_converter.convert(image_info['filename'])
            
            # Adicionar contexto da localização
            description = f"### Imagem da Página {image_info['page']}\n\n"
            description += result.text_content
            description += "\n"
            
            return description
            
        except Exception as e:
            print(f"❌ Erro ao processar imagem: {e}")
            return f"### Imagem da Página {image_info['page']}\n\n*Erro ao processar imagem*\n\n"
    
    def process_tables_from_text(self, text_content):
        """Identifica e formata tabelas no texto extraído"""
        lines = text_content.split('\\n')
        formatted_text = ""
        
        for line in lines:
            # Detectar possíveis linhas de tabela (com múltiplos números/percentuais)
            if (',' in line and '%' in line) or ('$' in line and len(line.split()) > 3):
                # Tentar formatar como tabela markdown
                parts = line.split()
                if len(parts) > 2:
                    formatted_text += "| " + " | ".join(parts) + " |\\n"
                else:
                    formatted_text += line + "\\n"
            else:
                formatted_text += line + "\\n"
        
        return formatted_text
    
    def process_pdf_hybrid(self, pdf_path):
        """Processamento híbrido completo do PDF"""
        print("🚀 PROCESSAMENTO HÍBRIDO INICIADO")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Extrair texto
        text_content = self.extract_text_from_pdf(pdf_path)
        
        # 2. Extrair imagens
        images = self.extract_images_from_pdf(pdf_path)
        
        # 3. Processar cada imagem com LLM
        image_descriptions = ""
        if images:
            print("🤖 Processando imagens com LLM...")
            for i, img_info in enumerate(images, 1):
                print(f"   Processando imagem {i}/{len(images)}...")
                description = self.process_image_with_llm(img_info)
                image_descriptions += description
        
        # 4. Formatar tabelas no texto
        formatted_text = self.process_tables_from_text(text_content)
        
        # 5. Combinar tudo
        final_content = f"""# Relatório Processado (Versão Híbrida)
**Processado em:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Arquivo:** {os.path.basename(pdf_path)}  

## 📝 Conteúdo Textual

{formatted_text}

## 🖼️ Análise de Imagens/Gráficos

{image_descriptions if image_descriptions else "*Nenhuma imagem encontrada no PDF*"}

---
*Processado com PDF Processor Híbrido v4*
"""
        
        # 6. Salvar resultado
        output_filename = f"relatorio_hibrido_{timestamp}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(final_content)
        
        # 7. Limpar arquivos temporários
        for img_info in images:
            try:
                os.remove(img_info['filename'])
            except:
                pass
        
        print(f"✅ Processamento concluído!")
        print(f"📄 Resultado salvo em: {output_filename}")
        print(f"📊 Tamanho total: {len(final_content)} caracteres")
        print(f"🖼️ Imagens processadas: {len(images)}")
        
        return final_content, output_filename

def main():
    """Função principal de teste"""
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    try:
        processor = HybridPDFProcessor()
        content, output_file = processor.process_pdf_hybrid(pdf_path)
        
        print(f"\\n🎯 RESULTADO:")
        print(f"   - Arquivo gerado: {output_file}")
        print(f"   - Conteúdo: {len(content)} caracteres")
        print(f"\\n📋 Preview (primeiros 500 caracteres):")
        print("-" * 50)
        print(content[:500])
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
