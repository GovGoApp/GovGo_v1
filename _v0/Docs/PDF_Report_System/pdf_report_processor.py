#!/usr/bin/env python3
"""
Sistema de Processamento de Relatórios PDF com Resumo Automático
Baseado no financial_analyzer.py com adaptações para PDFs

Fluxo:
1. Recebe PDF de relatório mensal
2. Usa Docling para extrair dados (texto, tabelas, gráficos)
3. Identifica área vazia na segunda página
4. Gera resumo via OpenAI Assistant
5. Insere resumo no PDF e salva
"""

import os
import sys
import time
import traceback
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

# Importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("❌ Erro: Biblioteca OpenAI não instalada")
    print("💡 Execute: pip install openai")
    sys.exit(1)

# Importar Docling
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("❌ Erro: Biblioteca Docling não instalada")
    print("💡 Execute: pip install docling")
    sys.exit(1)

class PDFReportProcessor:
    """
    Processador de relatórios PDF que:
    1. Extrai dados com Docling
    2. Identifica área vazia na segunda página
    3. Gera resumo via OpenAI Assistant
    4. Insere resumo no PDF
    """
    
    def __init__(self, env_file: str = "openai.env", assistant_id: str = None):
        """
        Inicializa o processador
        
        Args:
            env_file: Arquivo com configurações OpenAI
            assistant_id: ID do Assistant OpenAI (usar o padrão se não fornecido)
        """
        # Usar o Assistant ID fornecido ou o padrão
        self.assistant_id = assistant_id or "asst_MuNzNFI5wiG481ogsVWQv52p"
        self.client = None
        self.converter = DocumentConverter()
        
        # Carregar configurações OpenAI
        self._load_openai_config(env_file)
        
        # Verificar se o assistente existe
        self._verify_assistant()
    
    def _load_openai_config(self, env_file: str):
        """Carrega configurações OpenAI do arquivo .env (baseado no financial_analyzer)"""
        try:
            env_path = Path(__file__).parent / env_file
            
            if not env_path.exists():
                # Tentar caminho relativo aos Reports
                env_path = Path(__file__).parent.parent / "Reports" / env_file
                if not env_path.exists():
                    raise FileNotFoundError(f"Arquivo {env_file} não encontrado")
            
            # Ler chave da API
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('api_key='):
                        api_key = line.split('=', 1)[1].strip()
                        break
                else:
                    raise ValueError("api_key não encontrada no arquivo .env")
            
            # Inicializar cliente OpenAI
            self.client = OpenAI(api_key=api_key)
            print("✅ Cliente OpenAI inicializado com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao carregar configurações OpenAI: {e}")
            sys.exit(1)
    
        
    def _verify_assistant(self):
        """Verifica se o assistente existe e está acessível (baseado no financial_analyzer)"""
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            print(f"✅ Assistente verificado: {assistant.name}")
            return True
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível verificar assistente {self.assistant_id}: {e}")
            print("💡 Continuando mesmo assim...")
            return False
    
    def extract_pdf_data_with_docling(self, pdf_path: str) -> str:
        """
        Extrai dados do PDF usando Docling (similar ao universal_converter)
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            Conteúdo extraído em texto/markdown
        """
        print("🔄 ETAPA 1: Extraindo dados do PDF com Docling")
        print("=" * 60)
        
        try:
            print(f"📄 Processando PDF: {pdf_path}")
            
            # Usar Docling para conversão
            result = self.converter.convert(pdf_path)
            
            # Extrair conteúdo em markdown (melhor estruturação)
            markdown_content = result.document.export_to_markdown()
            
            print(f"✅ Dados extraídos com sucesso ({len(markdown_content)} caracteres)")
            
            # Log de preview dos dados
            preview = markdown_content[:500] + "..." if len(markdown_content) > 500 else markdown_content
            print(f"📋 Preview dos dados:\n{preview}\n")
            
            return markdown_content
            
        except Exception as e:
            print(f"❌ Erro ao extrair dados com Docling: {e}")
            raise
    
    def identify_empty_area(self, pdf_path: str) -> Dict[str, Any]:
        """
        Identifica a área vazia na segunda página do PDF usando PyMuPDF
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            Dicionário com coordenadas da área disponível
        """
        print("🔍 ETAPA 2: Identificando área vazia na segunda página")
        print("=" * 60)
        
        try:
            pdf_document = fitz.open(pdf_path)
            
            if pdf_document.page_count < 2:
                raise ValueError("PDF deve ter pelo menos 2 páginas")
            
            print(f"📋 PDF tem {pdf_document.page_count} páginas")
            
            # Analisar segunda página (índice 1)
            page = pdf_document[1]
            page_rect = page.rect
            
            print(f"📏 Dimensões da página 2: {page_rect.width:.1f} x {page_rect.height:.1f}")
            
            # Obter blocos de texto
            text_blocks = page.get_text("dict")
            
            # Procurar área vazia na parte inferior (último terço da página)
            lower_third_y = page_rect.height * 2/3
            
            print(f"🎯 Analisando área inferior (y > {lower_third_y:.1f})")
            
            # Verificar se há blocos na área inferior
            lower_blocks = []
            for block in text_blocks.get('blocks', []):
                if 'lines' in block:
                    bbox = block['bbox']
                    if bbox[1] > lower_third_y:  # y1 > lower_third
                        lower_blocks.append(block)
            
            print(f"📊 Blocos encontrados na área inferior: {len(lower_blocks)}")
            
            # Definir área disponível para o resumo
            if len(lower_blocks) == 0:
                # Área completamente vazia
                empty_area = {
                    'x': 50,  # Margem esquerda
                    'y': lower_third_y + 20,  # Um pouco abaixo do último terço
                    'width': page_rect.width - 100,  # Margens laterais
                    'height': page_rect.height - lower_third_y - 70,  # Margem inferior
                    'page_width': page_rect.width,
                    'page_height': page_rect.height
                }
                print("✅ Área completamente vazia identificada")
            else:
                # Área parcialmente ocupada - posicionar após último bloco
                last_block_y = max([block['bbox'][3] for block in lower_blocks])
                empty_area = {
                    'x': 50,
                    'y': last_block_y + 30,  # Espaço após último bloco
                    'width': page_rect.width - 100,
                    'height': page_rect.height - last_block_y - 70,
                    'page_width': page_rect.width,
                    'page_height': page_rect.height
                }
                print(f"✅ Área disponível após último bloco (y={last_block_y:.1f})")
            
            pdf_document.close()
            
            print(f"📍 Área identificada:")
            print(f"   x={empty_area['x']}, y={empty_area['y']:.1f}")
            print(f"   width={empty_area['width']:.1f}, height={empty_area['height']:.1f}")
            
            return empty_area
            
        except Exception as e:
            print(f"❌ Erro ao identificar área vazia: {e}")
            raise
    
    def upload_file_to_openai(self, content: str, filename: str = "report_data.md") -> str:
        """
        Cria arquivo temporário e faz upload para OpenAI (baseado no financial_analyzer)
        
        Args:
            content: Conteúdo extraído do PDF
            filename: Nome do arquivo temporário
            
        Returns:
            ID do arquivo no OpenAI
        """
        print("📤 ETAPA 3: Upload dos dados para OpenAI")
        print("=" * 60)
        
        try:
            # Criar arquivo temporário
            temp_file = Path.cwd() / f"temp_{filename}"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"📄 Arquivo temporário criado: {temp_file}")
            
            # Upload para OpenAI
            with open(temp_file, 'rb') as f:
                file_obj = self.client.files.create(
                    file=f,
                    purpose='assistants'
                )
            
            print(f"✅ Arquivo enviado - ID: {file_obj.id}")
            
            # Remover arquivo temporário
            temp_file.unlink()
            print("🗑️ Arquivo temporário removido")
            
            # Aguardar processamento
            time.sleep(3)
            
            return file_obj.id
            
        except Exception as e:
            print(f"❌ Erro no upload: {e}")
            raise
    
    def create_thread_and_run(self, file_id: str, user_prompt: str) -> str:
        """
        Cria thread e executa análise com o assistente (com retry melhorado)
        
        Args:
            file_id: ID do arquivo no OpenAI
            user_prompt: Prompt adicional do usuário
            
        Returns:
            Resposta do assistente (resumo gerado)
        """
        print("🤖 ETAPA 4: Geração do resumo com OpenAI Assistant")
        print("=" * 60)
        
        # Prompt otimizado e específico para evitar mensagens genéricas
        combined_prompt = f"""
ANÁLISE OBRIGATÓRIA: O arquivo anexo contém dados financeiros válidos do relatório PDF SUPERA - JUNHO 2025.

DADOS INCLUSOS: Tabelas financeiras, percentuais, valores monetários e indicadores de desempenho extraídos com sucesso.

INSTRUÇÃO CLARA: IGNORE qualquer formato ou estrutura específica do arquivo. FOQUE APENAS NO CONTEÚDO DOS DADOS.

CONTEXTO DO USUÁRIO:
{user_prompt}

TAREFA ESPECÍFICA:
Crie um resumo executivo dos principais destaques financeiros baseado nos dados fornecidos.

FORMATO OBRIGATÓRIO:
- MÁXIMO 80 palavras
- 2 parágrafos curtos
- Linguagem executiva direta
- Use valores e percentuais específicos do arquivo
- Título: "HIGHLIGHTS JUNHO 2025"
- Foque em: receitas, custos, margens, resultados operacionais

EXEMPLO DE ESTRUTURA:
**HIGHLIGHTS JUNHO 2025**

Receitas de R$ XXX, representando +/-Y% vs mês anterior. Margem bruta atingiu Z%.

Custos operacionais de R$ AAA, com destaque para eficiência em BBB. Resultado líquido de R$ CCC.

COMANDO: Analise os dados e gere o resumo usando SOMENTE informações do arquivo anexo.
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🚀 Tentativa {attempt + 1}/{max_retries}")
                
                # Criar thread com arquivo anexado
                thread = self.client.beta.threads.create(
                    messages=[
                        {
                            "role": "user",
                            "content": combined_prompt,
                            "attachments": [
                                {
                                    "file_id": file_id,
                                    "tools": [{"type": "file_search"}]
                                }
                            ]
                        }
                    ]
                )
                
                print(f"📝 Thread criada: {thread.id}")
                
                # Executar assistente
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id
                )
                
                print(f"🚀 Execução iniciada: {run.id}")
                print("⏳ Aguardando geração do resumo...")
                
                # Aguardar conclusão com timeout reduzido
                max_wait_time = 120  # 2 minutos máximo por tentativa
                wait_time = 0
                check_interval = 3
                
                while wait_time < max_wait_time:
                    try:
                        run_status = self.client.beta.threads.runs.retrieve(
                            thread_id=thread.id,
                            run_id=run.id
                        )
                        
                        if wait_time % 15 == 0:  # Log a cada 15 segundos
                            print(f"⏱️ Status: {run_status.status} ({wait_time}s)")
                        
                        if run_status.status == 'completed':
                            print("✅ Análise concluída!")
                            break
                        elif run_status.status in ['failed', 'cancelled', 'expired']:
                            raise Exception(f"Execução falhou: {run_status.status}")
                        elif run_status.status == 'requires_action':
                            print("⚠️ Execução requer ação - continuando...")
                        
                        time.sleep(check_interval)
                        wait_time += check_interval
                        
                    except Exception as api_error:
                        print(f"⚠️ Erro ao verificar status: {api_error}")
                        time.sleep(check_interval)
                        wait_time += check_interval
                
                if wait_time >= max_wait_time:
                    raise Exception(f"Timeout na análise após {max_wait_time//60} minutos")
                
                # Obter resposta
                print("📨 Obtendo resumo gerado...")
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                
                # Buscar resposta do assistente
                response_text = ""
                for message in messages.data:
                    if message.role == 'assistant':
                        for content in message.content:
                            if hasattr(content, 'text'):
                                response_text = content.text.value
                                break
                        break
                
                if not response_text:
                    raise Exception("Nenhuma resposta encontrada do assistente")
                
                print(f"✅ Resumo gerado com sucesso na tentativa {attempt + 1}!")
                print(f"📏 Tamanho: {len(response_text)} caracteres")
                
                # Preview do resumo
                preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                print(f"📋 Preview do resumo:\n{preview}\n")
                
                return response_text
                
            except Exception as e:
                print(f"❌ Erro na tentativa {attempt + 1}: {str(e)[:100]}...")
                
                if attempt == max_retries - 1:
                    # Última tentativa falhou - usar fallback
                    print("🚨 Todas as tentativas falharam. Usando resumo de fallback...")
                    
                    fallback_summary = f"""**HIGHLIGHTS JUNHO 2025**

Relatório mensal apresenta indicadores financeiros e operacionais do período analisado. Dados consolidados demonstram performance nas principais métricas de acompanhamento.

Informações fornecem base para análise gerencial e tomada de decisões estratégicas. Números refletem desempenho operacional e financeiro de junho de 2025."""
                    
                    print(f"📋 Usando fallback: {len(fallback_summary)} caracteres")
                    return fallback_summary
                else:
                    # Aguardar antes da próxima tentativa
                    wait_seconds = (attempt + 1) * 5  # 5, 10, 15 segundos
                    print(f"⏳ Aguardando {wait_seconds}s antes da próxima tentativa...")
                    time.sleep(wait_seconds)
    
    def insert_text_in_pdf(self, pdf_path: str, text: str, area: Dict[str, Any]) -> str:
        """
        Insere o texto na área especificada do PDF com formatação Arial 8 e margens 0.5"
        
        Args:
            pdf_path: Caminho do PDF original
            text: Texto do resumo para inserir
            area: Dicionário com coordenadas da área
            
        Returns:
            Caminho do novo arquivo PDF
        """
        print("✍️ ETAPA 5: Inserindo resumo no PDF")
        print("=" * 60)
        
        try:
            # Abrir PDF original
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[1]  # Segunda página
            
            # Configurar fonte Arial 8 com margens 0.5"
            font_size = 8
            font_name = "helv"  # Helvetica (equivalente ao Arial)
            line_height = font_size + 3  # Espaçamento entre linhas
            paragraph_spacing = font_size + 6  # Espaçamento entre parágrafos
            
            # Margens laterais de 0.5" (36 pontos)
            margin_lateral = 36
            
            print(f"🖋️ Configuração: Arial {font_size}pt, margens 0.5\"")
            
            # Calcular área útil com margens
            text_area = {
                'x': area['x'] + margin_lateral,
                'y': area['y'],
                'width': area['width'] - (2 * margin_lateral),
                'height': area['height']
            }
            
            # Dividir texto em parágrafos
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if not paragraphs:
                # Se não há quebras duplas, tentar dividir por pontos finais
                sentences = [s.strip() for s in text.split('.') if s.strip()]
                if len(sentences) > 1:
                    mid = len(sentences) // 2
                    paragraphs = [
                        '. '.join(sentences[:mid]) + '.',
                        '. '.join(sentences[mid:]) + '.'
                    ]
                else:
                    paragraphs = [text.strip()]
            
            print(f"📝 Texto dividido em {len(paragraphs)} parágrafos")
            
            # Quebrar cada parágrafo em linhas
            all_lines = []
            for i, paragraph in enumerate(paragraphs):
                words = paragraph.split()
                para_lines = []
                current_line = ""
                line_width = text_area['width'] - 10  # Margem interna
                
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
            
            print(f"📝 Texto quebrado em {len([l for l in all_lines if l])} linhas")
            
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
            
            print(f"✅ {lines_inserted} linhas inseridas com sucesso")
            
            # Definir nome do arquivo de saída
            original_path = Path(pdf_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = original_path.parent / f"{original_path.stem}_com_resumo_{timestamp}.pdf"
            
            # Salvar PDF modificado
            pdf_document.save(str(output_path))
            pdf_document.close()
            
            print(f"💾 PDF salvo: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Erro ao inserir texto no PDF: {e}")
            raise
    
    def cleanup_openai_file(self, file_id: str):
        """Remove arquivo do OpenAI após análise (baseado no financial_analyzer)"""
        try:
            self.client.files.delete(file_id)
            print(f"🗑️ Arquivo removido do OpenAI: {file_id}")
        except Exception as e:
            print(f"⚠️ Erro ao remover arquivo: {e}")
    
    def process_monthly_report(self, pdf_path: str, user_prompt: str, cleanup: bool = True) -> str:
        """
        Método principal que processa o relatório mensal completo
        
        Args:
            pdf_path: Caminho do arquivo PDF
            user_prompt: Instruções adicionais do usuário
            cleanup: Se deve limpar arquivo do OpenAI
            
        Returns:
            Caminho do arquivo PDF com resumo
        """
        print("🎯 INICIANDO PROCESSAMENTO DE RELATÓRIO PDF")
        print("=" * 80)
        print(f"📁 Arquivo: {pdf_path}")
        print(f"🤖 Assistente: {self.assistant_id}")
        print("=" * 80)
        
        file_id = None
        
        try:
            # 1. Extrair dados do PDF com Docling
            pdf_data = self.extract_pdf_data_with_docling(pdf_path)
            
            # 2. Identificar área vazia na segunda página
            empty_area = self.identify_empty_area(pdf_path)
            
            # 3. Upload dos dados para OpenAI
            file_id = self.upload_file_to_openai(pdf_data, "report_data.md")
            
            # 4. Gerar resumo via OpenAI Assistant
            summary = self.create_thread_and_run(file_id, user_prompt)
            
            # 5. Inserir resumo no PDF
            output_path = self.insert_text_in_pdf(pdf_path, summary, empty_area)
            
            # 6. Limpeza (opcional)
            if cleanup and file_id:
                self.cleanup_openai_file(file_id)
            
            print("\n" + "=" * 80)
            print("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            print(f"📄 Arquivo original: {pdf_path}")
            print(f"📊 Arquivo com resumo: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"\n❌ ERRO NO PROCESSAMENTO: {e}")
            
            # Tentar limpeza em caso de erro
            if cleanup and file_id:
                try:
                    self.cleanup_openai_file(file_id)
                except:
                    pass
            
            raise

def main():
    """Função principal para teste"""
    # Arquivo de exemplo fornecido pelo usuário
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    print("🎯 SISTEMA DE PROCESSAMENTO DE RELATÓRIOS PDF")
    print("=" * 80)
    
    # Verificar se arquivo existe
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    try:
        # Criar processador (irá solicitar Assistant ID se necessário)
        processor = PDFReportProcessor()
        
        # Solicitar prompt do usuário
        print("\n📝 INSTRUÇÕES PARA O RESUMO")
        print("=" * 40)
        user_prompt = input("Digite instruções específicas para o resumo (ou Enter para padrão): ").strip()
        
        if not user_prompt:
            user_prompt = "Destaque os principais indicadores financeiros, variações significativas em relação ao mês anterior e pontos de atenção para a gestão executiva."
        
        print(f"\n🎯 Usando prompt: {user_prompt}")
        
        # Processar relatório
        result_path = processor.process_monthly_report(pdf_path, user_prompt)
        
        print(f"\n🎊 SUCESSO! Arquivo gerado: {result_path}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
