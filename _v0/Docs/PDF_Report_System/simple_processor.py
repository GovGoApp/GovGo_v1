#!/usr/bin/env python3
"""
Script simplificado usando o sistema existente que já funciona
"""

import os
import sys
from pathlib import Path

# Adicionar caminho do sistema existente
sys.path.append(r"C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\Docs\Reports")

try:

    from universal_converter import UniversalToMarkdownConverter
    from financial_analyzer import FinancialAnalyzer
    import fitz  # PyMuPDF
    from datetime import datetime
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("💡 Verifique se os arquivos estão no diretório Reports")
    sys.exit(1)

class SimplePDFProcessor:
    """Versão simplificada usando o sistema existente"""
    
    def __init__(self):
        # Usar o sistema financial_analyzer já testado
        self.analyzer = FinancialAnalyzer(env_file="openai.env")
        # Definir o Assistant ID fornecido
        self.analyzer.assistant_id = "asst_MuNzNFI5wiG481ogsVWQv52p"
        self.converter = UniversalToMarkdownConverter()
    
    def extract_pdf_with_docling(self, pdf_path: str) -> str:
        """Usa o sistema existente para extrair dados"""
        print("🔄 Extraindo dados do PDF com sistema existente...")
        
        try:
            # Usar o método do universal_converter
            data = self.converter._convert_with_docling(pdf_path)
            
            # Debug: verificar o que foi extraído
            print(f"🔍 Tipo de dados extraídos: {type(data)}")
            
            # Se retornou dicionário de DataFrames, converter para texto
            if isinstance(data, dict):
                content = "# RELATÓRIO FINANCEIRO MENSAL\n\n"
                for section_name, df in data.items():
                    if hasattr(df, 'to_markdown'):
                        content += f"## {section_name}\n\n"
                        content += df.to_markdown() + "\n\n"
                    else:
                        content += f"## {section_name}\n\n{str(df)}\n\n"
                
                # Debug: mostrar preview do conteúdo
                preview = content[:1000] + "..." if len(content) > 1000 else content
                print(f"📋 Preview do conteúdo extraído:\n{preview}\n")
                
                return content
            else:
                # Se retornou texto diretamente
                content = str(data)
                print(f"📋 Conteúdo extraído ({len(content)} chars): {content[:500]}...")
                return content
                
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            raise
    
    def identify_empty_area(self, pdf_path: str):
        """Identifica área vazia (mesmo código anterior)"""
        print("🔍 Identificando área vazia...")
        
        pdf_document = fitz.open(pdf_path)
        if pdf_document.page_count < 2:
            raise ValueError("PDF deve ter pelo menos 2 páginas")
        
        page = pdf_document[1]  # Segunda página
        page_rect = page.rect
        text_blocks = page.get_text("dict")
        
        # Área no último terço da página
        lower_third_y = page_rect.height * 2/3
        
        # Verificar blocos na área inferior
        lower_blocks = []
        for block in text_blocks.get('blocks', []):
            if 'lines' in block:
                bbox = block['bbox']
                if bbox[1] > lower_third_y:
                    lower_blocks.append(block)
        
        # Definir área disponível
        if len(lower_blocks) == 0:
            empty_area = {
                'x': 50, 'y': lower_third_y + 20,
                'width': page_rect.width - 100,
                'height': page_rect.height - lower_third_y - 70,
                'page_width': page_rect.width, 'page_height': page_rect.height
            }
        else:
            last_block_y = max([block['bbox'][3] for block in lower_blocks])
            empty_area = {
                'x': 50, 'y': last_block_y + 30,
                'width': page_rect.width - 100,
                'height': page_rect.height - last_block_y - 70,
                'page_width': page_rect.width, 'page_height': page_rect.height
            }
        
        pdf_document.close()
        print(f"✅ Área identificada: {empty_area['width']:.0f}x{empty_area['height']:.0f}")
        return empty_area
    
    def generate_summary(self, pdf_data: str, user_prompt: str) -> str:
        """Usa o sistema financial_analyzer para gerar resumo"""
        print("🤖 Gerando resumo com OpenAI Assistant...")
        
        # Criar arquivo temporário
        temp_file = Path.cwd() / "temp_pdf_data.md"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(pdf_data)
        
        try:
            # Upload para OpenAI
            file_id = self.analyzer.upload_file_to_openai(str(temp_file))
            
            # Prompt otimizado para o Assistant
            combined_prompt = f"""
DADOS DO RELATÓRIO MENSAL SUPERA - JUNHO 2025:
Analise o arquivo anexo com dados financeiros extraídos do relatório PDF.

INSTRUÇÕES DO USUÁRIO:
{user_prompt}

TAREFA:
Crie um resumo executivo de highlights para inserir no relatório PDF.

FORMATO EXATO:
- Máximo 80 palavras
- 2 parágrafos curtos
- Linguagem executiva direta
- Use números específicos encontrados no arquivo
- Título: "HIGHLIGHTS JUNHO 2025"
- Foque em: receitas, custos, margens, indicadores principais

EXEMPLO:
**HIGHLIGHTS JUNHO 2025**

Primeiro parágrafo com principais números e variações do mês.

Segundo parágrafo com destaques operacionais e perspectivas.
"""
            
            print(f"📤 Enviando prompt para Assistant {self.analyzer.assistant_id}")
            
            # Usar método do financial_analyzer mas com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    summary = self.analyzer.create_thread_and_run(file_id, combined_prompt)
                    print(f"✅ Resumo recebido na tentativa {attempt + 1}")
                    break
                except Exception as e:
                    print(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)[:100]}")
                    if attempt == max_retries - 1:
                        raise e
                    import time
                    time.sleep(5)  # Aguardar 5 segundos antes de tentar novamente
            
            # Cleanup
            self.analyzer.cleanup_openai_file(file_id)
            temp_file.unlink()
            
            print(f"📥 Resumo gerado: {len(summary)} caracteres")
            return summary
            
        except Exception as e:
            # Cleanup em caso de erro
            if temp_file.exists():
                temp_file.unlink()
            print(f"❌ Erro no Assistant: {e}")
            
            # Fallback: resumo básico se Assistant falhar
            fallback_summary = f"""**HIGHLIGHTS JUNHO 2025**

Relatório mensal apresenta indicadores financeiros e operacionais do período. Dados consolidados demonstram performance da empresa nas principais métricas.

Informações fornecem base para análise gerencial e decisões estratégicas. Números refletem desempenho operacional e financeiro de junho de 2025."""
            
            print("🚨 Usando resumo de fallback")
            return fallback_summary
    
    def insert_text_in_pdf(self, pdf_path: str, text: str, area: dict) -> str:
        """Insere texto no PDF com formatação melhorada"""
        print("✍️ Inserindo resumo no PDF...")
        
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[1]  # Segunda página
        
        # Configurar fonte Arial 8 com margens 0.5
        font_size = 8
        font_name = "helv"  # Helvetica (equivalente ao Arial)
        line_height = font_size + 3  # Espaçamento entre linhas
        paragraph_spacing = font_size + 6  # Espaçamento entre parágrafos
        
        # Margens laterais de 0.5 (aproximadamente 36 pontos = 0.5 polegada)
        margin_lateral = 36
        
        print(f"🖋️ Configuração: Arial {font_size}pt, margens 0.5\"")
        
        # Dividir texto em parágrafos
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            # Se não há quebras duplas, dividir por pontos finais
            paragraphs = [p.strip() + '.' for p in text.split('.') if p.strip()]
        
        print(f"📝 Texto dividido em {len(paragraphs)} parágrafos")
        
        # Calcular área útil com margens
        text_area = {
            'x': area['x'] + margin_lateral,
            'y': area['y'],
            'width': area['width'] - (2 * margin_lateral),
            'height': area['height']
        }
        
        # Quebrar cada parágrafo em linhas
        all_lines = []
        for i, paragraph in enumerate(paragraphs):
            words = paragraph.split()
            para_lines = []
            current_line = ""
            line_width = text_area['width'] - 10  # Margem interna adicional
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                text_width = fitz.get_text_length(test_line, fontname=font_name, fontsize=font_size)
                
                if text_width <= line_width:
                    current_line = test_line
                else:
                    if current_line:
                        para_lines.append(current_line)
                    current_line = word
            
            if current_line:
                para_lines.append(current_line)
            
            # Adicionar linhas do parágrafo
            all_lines.extend(para_lines)
            
            # Adicionar espaço entre parágrafos (exceto no último)
            if i < len(paragraphs) - 1:
                all_lines.append("")  # Linha vazia para espaçamento
        
        # Inserir texto linha por linha
        y_position = text_area['y']
        lines_inserted = 0
        
        for line in all_lines:
            # Verificar se ainda cabe na área
            next_y = y_position + (paragraph_spacing if line == "" else line_height)
            if next_y > text_area['y'] + text_area['height']:
                print(f"⚠️ Limite de área atingido - {lines_inserted} linhas inseridas")
                break
            
            if line == "":
                # Linha vazia - apenas adicionar espaçamento
                y_position += paragraph_spacing
            else:
                # Inserir linha de texto
                page.insert_text(
                    (text_area['x'], y_position),
                    line,
                    fontsize=font_size,
                    fontname=font_name,
                    color=(0, 0, 0)  # Preto
                )
                y_position += line_height
                lines_inserted += 1
        
        # Salvar com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = pdf_path.replace('.pdf', f'_com_resumo_{timestamp}.pdf')
        pdf_document.save(output_path)
        pdf_document.close()
        
        print(f"✅ {lines_inserted} linhas inseridas com Arial 8pt e margens 0.5\"")
        print(f"💾 PDF salvo: {output_path}")
        return output_path
    
    def process_report(self, pdf_path: str, user_prompt: str) -> str:
        """Processo completo"""
        print("🎯 PROCESSAMENTO SIMPLIFICADO COM SISTEMA EXISTENTE")
        print("=" * 60)
        
        try:
            # 1. Extrair dados
            pdf_data = self.extract_pdf_with_docling(pdf_path)
            
            # 2. Identificar área
            area = self.identify_empty_area(pdf_path)
            
            # 3. Gerar resumo
            summary = self.generate_summary(pdf_data, user_prompt)
            
            # 4. Inserir no PDF
            result = self.insert_text_in_pdf(pdf_path, summary, area)
            
            print("🎉 SUCESSO!")
            return result
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            raise

def main():
    """Teste com o arquivo do usuário"""
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    # Prompt do usuário
    user_prompt = input("Digite instruções para o resumo (Enter para padrão): ").strip()
    if not user_prompt:
        user_prompt = "Destaque os principais indicadores financeiros, variações significativas e pontos de atenção para gestão executiva."
    
    try:
        processor = SimplePDFProcessor()
        result = processor.process_report(pdf_path, user_prompt)
        print(f"\n🎊 Arquivo gerado: {result}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
