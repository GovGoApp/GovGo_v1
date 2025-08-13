"""
Sistema de Processamento de Relatórios PDF com OpenAI Assistant
Adaptado do sistema financialanalyzer existente
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import io
import tempfile

# Imports do sistema existente
from docling.document_converter import DocumentConverter
from openai import OpenAI
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class PDFReportProcessor:
    """
    Processador de relatórios PDF que:
    1. Usa Docling para extrair dados do PDF
    2. Identifica área vazia na segunda página
    3. Gera resumo via OpenAI Assistant
    4. Insere o resumo no PDF e salva
    """
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key não encontrada. Configure OPENAI_API_KEY no arquivo .env")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.converter = DocumentConverter()
        
        # ID do Assistant OpenAI (criar se necessário)
        self.assistant_id = "asst_G8pkl29kFjPbAhYlS2kAclsU"  # Usar o existente ou criar novo
        
    def extract_pdf_data_with_docling(self, pdf_path: str) -> str:
        """
        Extrai dados do PDF usando Docling (mesmo método do sistema existente)
        """
        print(f"Extraindo dados do PDF com Docling: {pdf_path}")
        
        try:
            # Usar Docling para conversão
            result = self.converter.convert(pdf_path)
            
            # Extrair conteúdo em markdown
            markdown_content = result.document.export_to_markdown()
            
            print(f"Dados extraídos com sucesso ({len(markdown_content)} caracteres)")
            return markdown_content
            
        except Exception as e:
            print(f"Erro ao extrair dados com Docling: {e}")
            return ""
    
    def identify_empty_area(self, pdf_path: str) -> Dict[str, Any]:
        """
        Identifica a área vazia na segunda página do PDF
        """
        print("Identificando área vazia na segunda página...")
        
        pdf_document = fitz.open(pdf_path)
        
        if pdf_document.page_count < 2:
            raise ValueError("PDF deve ter pelo menos 2 páginas")
        
        # Analisar segunda página (índice 1)
        page = pdf_document[1]
        page_rect = page.rect
        
        # Obter blocos de texto
        text_blocks = page.get_text("dict")
        
        # Procurar área vazia na parte inferior (último terço da página)
        lower_third_y = page_rect.height * 2/3
        
        # Verificar se há blocos na área inferior
        lower_blocks = []
        for block in text_blocks.get('blocks', []):
            if 'lines' in block:
                bbox = block['bbox']
                if bbox[1] > lower_third_y:
                    lower_blocks.append(block)
        
        # Definir área disponível para o resumo
        if len(lower_blocks) == 0:
            # Área completamente vazia
            empty_area = {
                'x': 50,  # Margem esquerda
                'y': lower_third_y + 20,  # Um pouco abaixo do último terço
                'width': page_rect.width - 100,  # Margens laterais
                'height': page_rect.height - lower_third_y - 50,  # Margem inferior
                'page_width': page_rect.width,
                'page_height': page_rect.height
            }
        else:
            # Área parcialmente ocupada - posicionar após último bloco
            last_block_y = max([block['bbox'][3] for block in lower_blocks])
            empty_area = {
                'x': 50,
                'y': last_block_y + 20,
                'width': page_rect.width - 100,
                'height': page_rect.height - last_block_y - 50,
                'page_width': page_rect.width,
                'page_height': page_rect.height
            }
        
        pdf_document.close()
        
        print(f"Área identificada: x={empty_area['x']}, y={empty_area['y']}, "
              f"width={empty_area['width']}, height={empty_area['height']}")
        
        return empty_area
    
    def generate_summary_with_openai(self, pdf_data: str, user_prompt: str) -> str:
        """
        Gera resumo usando OpenAI Assistant (mesmo método do sistema existente)
        """
        print("Gerando resumo com OpenAI Assistant...")
        
        try:
            # Criar thread
            thread = self.client.beta.threads.create()
            
            # Prompt combinado
            combined_prompt = f"""
DADOS DO RELATÓRIO:
{pdf_data}

INSTRUÇÕES ADICIONAIS DO USUÁRIO:
{user_prompt}

Crie um resumo conciso para a área de highlights do relatório mensal, focando nos pontos mais importantes e dados relevantes.
O resumo deve ter no máximo 150 palavras e ser adequado para executives.
"""
            
            # Enviar mensagem
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=combined_prompt
            )
            
            # Executar Assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Aguardar conclusão
            while run.status in ['queued', 'in_progress']:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Obter resposta
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                assistant_message = None
                for msg in messages:
                    if msg.role == 'assistant':
                        assistant_message = msg
                        break
                
                if assistant_message and assistant_message.content:
                    summary = assistant_message.content[0].text.value
                    print(f"Resumo gerado com sucesso ({len(summary)} caracteres)")
                    return summary
                else:
                    return "Erro: Não foi possível obter resposta do Assistant"
            else:
                return f"Erro na execução do Assistant: {run.status}"
                
        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            return f"Erro ao gerar resumo: {e}"
    
    def insert_text_in_pdf(self, pdf_path: str, text: str, area: Dict[str, Any]) -> str:
        """
        Insere o texto na área especificada do PDF e salva uma nova versão
        """
        print("Inserindo texto no PDF...")
        
        # Abrir PDF original
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[1]  # Segunda página
        
        # Configurar fonte
        font_size = 10
        font_name = "helv"  # Helvetica (similar ao Arial)
        
        # Calcular quebras de linha para o texto
        words = text.split()
        lines = []
        current_line = ""
        line_width = area['width'] - 20  # Margem interna
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            text_width = fitz.get_text_length(test_line, fontname=font_name, fontsize=font_size)
            
            if text_width <= line_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Inserir texto linha por linha
        y_position = area['y']
        line_height = font_size + 2
        
        for line in lines:
            if y_position + line_height > area['y'] + area['height']:
                break  # Não exceder a área disponível
            
            # Inserir texto
            page.insert_text(
                (area['x'], y_position),
                line,
                fontsize=font_size,
                fontname=font_name,
                color=(0, 0, 0)  # Preto
            )
            
            y_position += line_height
        
        # Salvar novo PDF
        output_path = pdf_path.replace('.pdf', '_com_resumo.pdf')
        pdf_document.save(output_path)
        pdf_document.close()
        
        print(f"PDF salvo com resumo: {output_path}")
        return output_path
    
    def process_monthly_report(self, pdf_path: str, user_prompt: str) -> str:
        """
        Método principal que processa o relatório mensal completo
        """
        print(f"Iniciando processamento do relatório: {pdf_path}")
        
        try:
            # 1. Extrair dados do PDF com Docling
            pdf_data = self.extract_pdf_data_with_docling(pdf_path)
            if not pdf_data:
                raise Exception("Falha ao extrair dados do PDF")
            
            # 2. Identificar área vazia
            empty_area = self.identify_empty_area(pdf_path)
            
            # 3. Gerar resumo com OpenAI
            summary = self.generate_summary_with_openai(pdf_data, user_prompt)
            
            # 4. Inserir texto no PDF
            output_path = self.insert_text_in_pdf(pdf_path, summary, empty_area)
            
            print(f"Processamento concluído com sucesso!")
            print(f"Arquivo gerado: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"Erro no processamento: {e}")
            raise e

def main():
    """
    Função principal para teste
    """
    # Exemplo de uso
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    user_prompt = "Destaque os principais indicadores financeiros e variações significativas em relação ao mês anterior"
    
    processor = PDFReportProcessor()
    result = processor.process_monthly_report(pdf_path, user_prompt)
    print(f"Resultado: {result}")

if __name__ == "__main__":
    main()
