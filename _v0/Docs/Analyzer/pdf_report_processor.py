"""
Sistema de Geração Automática de Resumos para Relatórios PDF
Lê PDF, extrai dados, usa OpenAI Assistant para gerar resumo e insere no PDF
"""
import os
import fitz  # PyMuPDF
from openai import OpenAI
from datetime import datetime
import json
import re

class PDFReportProcessor:
    def __init__(self, openai_api_key, assistant_id):
        """
        Inicializa o processador de relatórios PDF
        
        Args:
            openai_api_key: Chave da API OpenAI
            assistant_id: ID do Assistant OpenAI configurado
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.assistant_id = assistant_id
        
    def extract_pdf_data(self, pdf_path):
        """
        Extrai dados do relatório PDF
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            dict: Dados extraídos do PDF
        """
        print(f"Extraindo dados do PDF: {pdf_path}")
        
        pdf_document = fitz.open(pdf_path)
        extracted_data = {
            "total_pages": pdf_document.page_count,
            "pages_content": [],
            "financial_data": {},
            "metadata": {}
        }
        
        # Extrair texto de todas as páginas
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text = page.get_text()
            extracted_data["pages_content"].append({
                "page": page_num + 1,
                "text": text,
                "length": len(text)
            })
            
            # Procurar por dados financeiros específicos
            if page_num == 0:  # Primeira página
                self._extract_financial_indicators(text, extracted_data["financial_data"])
        
        pdf_document.close()
        return extracted_data
    
    def _extract_financial_indicators(self, text, financial_data):
        """
        Extrai indicadores financeiros do texto
        """
        # Padrões para identificar valores financeiros
        patterns = {
            "receita": r"receita.*?R\$\s*([\d.,]+)",
            "lucro": r"lucro.*?R\$\s*([\d.,]+)",
            "ebitda": r"ebitda.*?R\$\s*([\d.,]+)",
            "margem": r"margem.*?([\d,]+)%"
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                financial_data[key] = matches
    
    def find_summary_area(self, pdf_path):
        """
        Identifica a área destinada ao resumo na segunda página
        
        Returns:
            tuple: Coordenadas da área vazia (x1, y1, x2, y2)
        """
        print("Identificando área para inserção do resumo...")
        
        pdf_document = fitz.open(pdf_path)
        
        if pdf_document.page_count < 2:
            raise ValueError("PDF deve ter pelo menos 2 páginas")
        
        page = pdf_document[1]  # Segunda página
        page_rect = page.rect
        
        # Obter blocos de texto existentes
        text_blocks = page.get_text("dict")
        
        # Definir área inferior da página (último terço)
        lower_third_y = page_rect.height * 2/3
        
        # Verificar se há texto na área inferior
        lower_blocks = []
        for block in text_blocks.get('blocks', []):
            if 'lines' in block:
                bbox = block['bbox']
                if bbox[1] > lower_third_y:
                    lower_blocks.append(block)
        
        # Se não há blocos na área inferior, essa é nossa área de inserção
        if len(lower_blocks) == 0:
            # Margem de 50 pontos nas laterais
            summary_area = (50, lower_third_y + 20, page_rect.width - 50, page_rect.height - 50)
        else:
            # Encontrar espaço disponível entre blocos
            # Por simplicidade, usar área padrão
            summary_area = (50, page_rect.height - 150, page_rect.width - 50, page_rect.height - 50)
        
        pdf_document.close()
        return summary_area
    
    def generate_summary_with_openai(self, pdf_data, user_prompt):
        """
        Gera resumo usando OpenAI Assistant
        
        Args:
            pdf_data: Dados extraídos do PDF
            user_prompt: Prompt adicional fornecido pelo usuário
            
        Returns:
            str: Resumo gerado
        """
        print("Gerando resumo com OpenAI Assistant...")
        
        # Preparar dados para o Assistant
        report_content = ""
        for page in pdf_data["pages_content"]:
            report_content += f"=== PÁGINA {page['page']} ===\n{page['text']}\n\n"
        
        # Criar mensagem para o Assistant
        message_content = f"""
DADOS DO RELATÓRIO:
{report_content}

DADOS FINANCEIROS IDENTIFICADOS:
{json.dumps(pdf_data['financial_data'], indent=2, ensure_ascii=False)}

CONTEXTO ADICIONAL DO USUÁRIO:
{user_prompt}

Por favor, gere um resumo executivo focado nos highlights e pontos importantes do relatório, 
considerando as informações adicionais fornecidas pelo usuário. 
O resumo deve ser conciso e adequado para inserção em um espaço limitado no PDF.
"""
        
        try:
            # Criar thread
            thread = self.client.beta.threads.create()
            
            # Adicionar mensagem
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message_content
            )
            
            # Executar Assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Aguardar conclusão
            while run.status in ['queued', 'in_progress']:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Obter resposta
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                summary = messages.data[0].content[0].text.value
                return summary
            else:
                raise Exception(f"Erro na execução: {run.status}")
                
        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            return f"Erro ao gerar resumo: {str(e)}"
    
    def insert_summary_into_pdf(self, pdf_path, summary_text, summary_area):
        """
        Insere o resumo no PDF na área especificada
        
        Args:
            pdf_path: Caminho do PDF original
            summary_text: Texto do resumo a ser inserido
            summary_area: Coordenadas da área (x1, y1, x2, y2)
        """
        print("Inserindo resumo no PDF...")
        
        # Abrir PDF
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[1]  # Segunda página
        
        # Definir área de inserção
        text_rect = fitz.Rect(summary_area)
        
        # Configurar fonte e tamanho
        font_size = 10
        font_name = "helv"  # Arial/Helvetica
        
        # Inserir texto
        page.insert_textbox(
            text_rect,
            summary_text,
            fontsize=font_size,
            fontname=font_name,
            color=(0, 0, 0),  # Preto
            align=0  # Alinhamento à esquerda
        )
        
        # Salvar PDF modificado
        output_path = pdf_path.replace('.pdf', '_com_resumo.pdf')
        pdf_document.save(output_path)
        pdf_document.close()
        
        print(f"PDF salvo com resumo: {output_path}")
        return output_path
    
    def process_report(self, pdf_path, user_prompt):
        """
        Processa o relatório completo: extração -> geração -> inserção
        
        Args:
            pdf_path: Caminho do PDF
            user_prompt: Contexto adicional do usuário
            
        Returns:
            str: Caminho do PDF final
        """
        try:
            # Etapa 1: Extrair dados do PDF
            pdf_data = self.extract_pdf_data(pdf_path)
            
            # Etapa 2: Identificar área de inserção
            summary_area = self.find_summary_area(pdf_path)
            
            # Etapa 3: Gerar resumo com OpenAI
            summary = self.generate_summary_with_openai(pdf_data, user_prompt)
            
            # Etapa 4: Inserir resumo no PDF
            final_pdf = self.insert_summary_into_pdf(pdf_path, summary, summary_area)
            
            return final_pdf
            
        except Exception as e:
            print(f"Erro no processamento: {e}")
            raise

def main():
    """
    Função principal para teste
    """
    # Configurações
    OPENAI_API_KEY = "sua_chave_aqui"  # Substituir pela chave real
    ASSISTANT_ID = "seu_assistant_id"  # Substituir pelo ID do Assistant
    
    # Arquivo de teste
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    # Contexto adicional do usuário
    user_prompt = """
    Este é o relatório mensal de junho de 2025 da empresa Supera.
    Destacar: crescimento em vendas, novos projetos iniciados, 
    desafios enfrentados no trimestre, e perspectivas para o próximo mês.
    """
    
    # Processar relatório
    processor = PDFReportProcessor(OPENAI_API_KEY, ASSISTANT_ID)
    result = processor.process_report(pdf_path, user_prompt)
    
    print(f"Processamento concluído: {result}")

if __name__ == "__main__":
    main()
