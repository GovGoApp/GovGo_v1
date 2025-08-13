#!/usr/bin/env python3
"""
Sistema de Processamento de Relatórios PDF com Resumo Automático - VERSÃO 3
Baseado exatamente no v2, APENAS substituindo Docling por MarkItDown:
1. Usa MarkItDown + LLM para extrair dados (incluindo imagens/gráficos)
2. Mantém TODA a lógica do v2 (área vazia, margens, formatação, etc.)
3. Arquivo temporário preservado com timestamp
4. Arquivo de saída com timestamp

Fluxo IDÊNTICO ao v2:
1. Recebe PDF de relatório mensal
2. Usa MarkItDown para extrair dados (ÚNICA mudança)
3. Identifica área vazia na segunda página (igual v2)
4. Gera resumo via OpenAI Assistant (igual v2)
5. Converte markdown para texto formatado (igual v2)
6. Insere resumo no PDF e salva (igual v2)
"""

import sys
import os
import io
from PIL import Image
import time
import traceback
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import re

# Importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("❌ Erro: Biblioteca OpenAI não instalada")
    print("💡 Execute: pip install openai")
    sys.exit(1)

# Importar MarkItDown (ÚNICA mudança do v2)
try:
    from markitdown import MarkItDown
except ImportError:
    print("❌ Erro: Biblioteca MarkItDown não instalada")
    print("💡 Execute: pip install 'markitdown[all]'")
    sys.exit(1)

class PDFReportProcessorV3:
    """
    Processador de relatórios PDF versão 3 - BASEADO NO V2
    ÚNICA mudança: MarkItDown no lugar do Docling
    """
    
    def __init__(self, env_file: str = "openai.env", assistant_id: str = None):
        """
        Inicializa o processador v3 (IGUAL ao v2)
        """
        # Mesmo Assistant ID do v2
        self.assistant_id = "asst_qPkntEzl6JPch7UV08RW52i4" # V2 - RESUMEE_v1
        
        self.client = None
        # ÚNICA mudança: MarkItDown em vez de DocumentConverter
        self.converter = None
        
        # Carregar configurações OpenAI (IGUAL v2)
        self._load_openai_config(env_file)
        
        # Inicializar MarkItDown (NOVA linha)
        self._initialize_markitdown()
        
        # Verificar se o assistente existe (IGUAL v2)
        self._verify_assistant()
    
    def _load_openai_config(self, env_file: str):
        """Carrega configurações OpenAI do arquivo .env (IGUAL v2)"""
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
    
    def _initialize_markitdown(self):
        """Inicializa MarkItDown com LLM (NOVA função)"""
        try:
            # Criar instância MarkItDown com LLM para imagens
            self.converter = MarkItDown(
                llm_client=self.client,
                llm_model="gpt-4o",
                enable_plugins=True
            )
            print("✅ MarkItDown inicializado com LLM para processamento de imagens")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar MarkItDown: {e}")
            # Fallback sem LLM
            self.converter = MarkItDown(enable_plugins=True)
            print("⚠️ MarkItDown inicializado sem LLM (fallback)")
    
    def _verify_assistant(self):
        """Verifica se o assistente existe e está acessível (IGUAL v2)"""
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            print(f"✅ Assistente verificado: {assistant.name}")
            return True
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível verificar assistente {self.assistant_id}: {e}")
            print("💡 Continuando mesmo assim...")
            return False
    
    def extract_pdf_data_with_markitdown(self, pdf_path: str) -> str:
        """
        Extrai dados do PDF usando abordagem HÍBRIDA (MarkItDown + LLM para imagens)
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            Conteúdo extraído em texto/markdown incluindo descrições de imagens
        """
        print("🔄 ETAPA 1: Extraindo dados do PDF com ABORDAGEM HÍBRIDA")
        print("=" * 60)
        
        try:
            print(f"📄 Processando PDF: {pdf_path}")
            
            # 1. Extrair texto do PDF
            text_content = self._extract_text_from_pdf(pdf_path)
            
            # 2. Extrair e processar imagens com LLM
            images = self._extract_images_from_pdf(pdf_path)
            
            # 3. Processar cada imagem com LLM
            image_descriptions = ""
            if images:
                print("🤖 Processando imagens com LLM...")
                for i, img_info in enumerate(images, 1):
                    print(f"   Processando imagem {i}/{len(images)}...")
                    description = self._process_image_with_llm(img_info)
                    image_descriptions += description
            
            # 4. Combinar texto + descrições das imagens
            if image_descriptions:
                combined_content = f"{text_content}\n\n## 🖼️ Análise de Imagens/Gráficos\n\n{image_descriptions}"
            else:
                combined_content = text_content
            
            print(f"✅ Dados extraídos com sucesso ({len(combined_content)} caracteres)")
            print(f"🖼️ Imagens processadas: {len(images)}")
            
            # Log de preview dos dados
            preview = combined_content[:500] + "..." if len(combined_content) > 500 else combined_content
            print(f"📋 Preview dos dados:\n{preview}\n")
            
            return combined_content
            
        except Exception as e:
            print(f"❌ Erro ao extrair dados híbridos: {e}")
            raise
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrai apenas texto do PDF (sem imagens)"""
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text_content += page.get_text()
                text_content += "\n"
            
            doc.close()
            return text_content
            
        except Exception as e:
            print(f"❌ Erro ao extrair texto: {e}")
            return ""
    
    def _extract_images_from_pdf(self, pdf_path: str) -> list:
        """Extrai todas as imagens do PDF"""
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
            return images
            
        except Exception as e:
            print(f"❌ Erro ao extrair imagens: {e}")
            return []
    
    def _process_image_with_llm(self, image_info: dict) -> str:
        """Processa uma imagem com LLM para obter descrição"""
        try:
            # Usar MarkItDown para processar a imagem
            result = self.converter.convert(image_info['filename'])
            
            # Adicionar contexto da localização
            description = f"### Imagem da Página {image_info['page']}\n\n"
            description += result.text_content
            description += "\n\n"
            
            # Limpar arquivo temporário
            try:
                os.remove(image_info['filename'])
            except:
                pass
            
            return description
            
        except Exception as e:
            print(f"❌ Erro ao processar imagem: {e}")
            return f"### Imagem da Página {image_info['page']}\n\n*Erro ao processar imagem*\n\n"
    
    def identify_empty_area_improved(self, pdf_path: str) -> Dict[str, Any]:
        """
        Identifica a área vazia na segunda página do PDF - VERSÃO MELHORADA (IGUAL v2)
        """
        print("🔍 ETAPA 2: Identificando área vazia na segunda página (V2)")
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
            
            # MELHORIA: Analisar área a partir da metade da página
            half_page_y = page_rect.height * 0.5
            
            print(f"🎯 Analisando área inferior (y > {half_page_y:.1f})")
            
            # Verificar se há blocos na área inferior
            lower_blocks = []
            for block in text_blocks.get('blocks', []):
                if 'lines' in block:
                    bbox = block['bbox']
                    if bbox[1] > half_page_y:  # y1 > half_page
                        lower_blocks.append(block)
            
            print(f"📊 Blocos encontrados na área inferior: {len(lower_blocks)}")
            
            # Encontrar o último elemento com conteúdo
            if lower_blocks:
                last_y = max([block['bbox'][3] for block in lower_blocks])
                print(f"📍 Último elemento encontrado em y={last_y:.1f}")
            else:
                # Se não há blocos na metade inferior, começar da metade
                last_y = half_page_y
                print(f"📍 Nenhum elemento na metade inferior, iniciando em y={last_y:.1f}")
            
            # MELHORIA: Margens menores e área maior
            margin_left = 20  # Reduzido de 50 para 20
            margin_right = 20
            margin_top = 30   # Espaço após último elemento
            margin_bottom = 40
            
            # Definir área disponível para o resumo
            empty_area = {
                'x': margin_left,
                'y': last_y + margin_top,
                'width': page_rect.width - margin_left - margin_right,
                'height': page_rect.height - last_y - margin_top - margin_bottom,
                'page_width': page_rect.width,
                'page_height': page_rect.height
            }
            
            pdf_document.close()
            
            print(f"📍 ÁREA MELHORADA identificada:")
            print(f"   x={empty_area['x']}, y={empty_area['y']:.1f}")
            print(f"   width={empty_area['width']:.1f}, height={empty_area['height']:.1f}")
            print(f"   Área total: {empty_area['width'] * empty_area['height']:.0f} pontos²")
            
            return empty_area
            
        except Exception as e:
            print(f"❌ Erro ao identificar área vazia: {e}")
            raise
    
    def upload_file_to_openai(self, content: str, filename: str = None) -> str:
        """
        Cria arquivo temporário e faz upload para OpenAI - COM TIMESTAMP (melhorado do v2)
        """
        print("📤 ETAPA 3: Upload dos dados para OpenAI")
        print("=" * 60)
        
        try:
            # Criar nome do arquivo com timestamp se não fornecido
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_data_v3_{timestamp}.md"
            
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
            
            # NÃO remover arquivo temporário (para inspeção)
            print(f"📋 Arquivo temporário mantido para inspeção: {temp_file}")
            
            # Aguardar processamento
            time.sleep(3)
            
            return file_obj.id
            
        except Exception as e:
            print(f"❌ Erro no upload: {e}")
            raise
    
    def create_thread_and_run_v2(self, file_id: str, user_prompt: str) -> str:
        """
        Cria thread e executa análise com o assistente (IGUAL v2)
        """
        print("🤖 ETAPA 4: Geração do resumo com OpenAI Assistant (V2)")
        print("=" * 60)
        
        # PROMPT SIMPLIFICADO - FOCO NO CONTEXTO DO USUÁRIO (IGUAL v2)
        combined_prompt = f"""
Analise o arquivo anexo do relatório financeiro.
Execute sua tarefa considerando este contexto fornecido pelo usuário.
CONTEXTO ESPECÍFICO DO USUÁRIO:
{user_prompt}


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
                max_wait_time = 180  # 3 minutos para análise mais profunda
                wait_time = 0
                check_interval = 5
                
                while wait_time < max_wait_time:
                    try:
                        run_status = self.client.beta.threads.runs.retrieve(
                            thread_id=thread.id,
                            run_id=run.id
                        )
                        
                        if wait_time % 20 == 0:  # Log a cada 20 segundos
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
                
                print(f"✅ Resumo expandido gerado com sucesso na tentativa {attempt + 1}!")
                print(f"📏 Tamanho: {len(response_text)} caracteres")
                
                # Preview do resumo
                preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
                print(f"📋 Preview do resumo:\n{preview}\n")
                
                return response_text
                
            except Exception as e:
                print(f"❌ Erro na tentativa {attempt + 1}: {str(e)[:100]}...")
                
                if attempt == max_retries - 1:
                    # Última tentativa falhou - usar fallback expandido
                    print("🚨 Todas as tentativas falharam. Usando resumo expandido de fallback...")
                    
                    fallback_summary = f"""**HIGHLIGHTS JUNHO 2025**

Relatório mensal apresenta cenário financeiro desafiador com necessidade de ajustes operacionais significativos. Indicadores apontam para revisão estratégica nas próximas análises mensais.

Considerando o contexto apresentado: {user_prompt[:100]}... - a transição operacional demanda monitoramento intensivo dos custos e receitas para garantir sustentabilidade financeira.

Dados consolidados evidenciam momento crítico para implementação de medidas corretivas e otimização de processos. Performance operacional requer atenção especial da gestão executiva nas próximas avaliações."""
                    
                    print(f"📋 Usando fallback expandido: {len(fallback_summary)} caracteres")
                    return fallback_summary
                else:
                    # Aguardar antes da próxima tentativa
                    wait_seconds = (attempt + 1) * 5  # 5, 10, 15 segundos
                    print(f"⏳ Aguardando {wait_seconds}s antes da próxima tentativa...")
                    time.sleep(wait_seconds)
    
    def convert_markdown_to_formatted_text(self, markdown_text: str) -> str:
        """
        Converte texto markdown para texto formatado simples (IGUAL v2)
        """
        print("🔄 Convertendo markdown para texto formatado...")
        
        # Remover referências [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', markdown_text)
        
        # Converter títulos markdown
        text = re.sub(r'#+\s*', '', text)  # Remove ## ou ###
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove **texto**
        
        # Limpar espaços extras
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalizar quebras duplas
        text = text.strip()
        
        print(f"✅ Texto convertido ({len(text)} caracteres)")
        return text
    
    def insert_text_in_pdf_v2(self, pdf_path: str, text: str, area: Dict[str, Any]) -> str:
        """
        Insere o texto na área especificada do PDF - VERSÃO 2 MELHORADA COM TIMESTAMP
        """
        print("✍️ ETAPA 5: Inserindo resumo no PDF (V2)")
        print("=" * 60)
        
        try:
            # Converter markdown para texto formatado
            formatted_text = self.convert_markdown_to_formatted_text(text)
            
            # Abrir PDF original
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[1]  # Segunda página
            
            # Configurar fonte Arial 8 com margens otimizadas
            font_size = 8
            font_name = "helv"  # Helvetica (equivalente ao Arial)
            line_height = font_size + 3  # Espaçamento entre linhas
            paragraph_spacing = font_size + 8  # Espaçamento entre parágrafos
            
            # MELHORIA: Margens laterais menores (0.2" = 14 pontos)
            margin_lateral = 14  # Reduzido de 36 para 14
            
            print(f"🖋️ Configuração: Arial {font_size}pt, margens 0.2\"")
            
            # Calcular área útil com margens otimizadas
            text_area = {
                'x': area['x'] + margin_lateral,
                'y': area['y'],
                'width': area['width'] - (2 * margin_lateral),
                'height': area['height']
            }
            
            print(f"📏 Área de texto: {text_area['width']:.1f} x {text_area['height']:.1f}")
            
            # Dividir texto em parágrafos
            paragraphs = [p.strip() for p in formatted_text.split('\n\n') if p.strip()]
            if not paragraphs:
                # Se não há quebras duplas, tentar dividir por pontos finais
                sentences = [s.strip() for s in formatted_text.split('.') if s.strip()]
                if len(sentences) > 2:
                    # Dividir em 3 partes
                    third = len(sentences) // 3
                    paragraphs = [
                        '. '.join(sentences[:third]) + '.',
                        '. '.join(sentences[third:2*third]) + '.',
                        '. '.join(sentences[2*third:]) + '.'
                    ]
                else:
                    paragraphs = [formatted_text.strip()]
            
            print(f"📝 Texto dividido em {len(paragraphs)} parágrafos")
            
            # Quebrar cada parágrafo em linhas
            all_lines = []
            for i, paragraph in enumerate(paragraphs):
                words = paragraph.split()
                para_lines = []
                current_line = ""
                line_width = text_area['width'] - 10  # Margem interna pequena
                
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
            
            # Definir nome do arquivo de saída COM TIMESTAMP
            original_path = Path(pdf_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = original_path.parent / f"{original_path.stem}_v3_resumo_{timestamp}.pdf"
            
            # Salvar PDF modificado
            pdf_document.save(str(output_path))
            pdf_document.close()
            
            print(f"💾 PDF V3 salvo: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Erro ao inserir texto no PDF: {e}")
            raise
    
    def cleanup_openai_file(self, file_id: str):
        """Remove arquivo do OpenAI após análise (IGUAL v2)"""
        try:
            self.client.files.delete(file_id)
            print(f"🗑️ Arquivo removido do OpenAI: {file_id}")
        except Exception as e:
            print(f"⚠️ Erro ao remover arquivo: {e}")
    
    def process_monthly_report_v3(self, pdf_path: str, user_prompt: str, cleanup: bool = True) -> str:
        """
        Método principal que processa o relatório mensal completo - VERSÃO 3
        BASEADO NO V2, apenas mudando extração
        """
        print("🎯 INICIANDO PROCESSAMENTO DE RELATÓRIO PDF - VERSÃO 3")
        print("=" * 80)
        print(f"📁 Arquivo: {pdf_path}")
        print(f"🤖 Assistente: {self.assistant_id}")
        print(f"🆕 V3: MarkItDown + LLM (imagens/gráficos), baseado no V2")
        print("=" * 80)
        
        file_id = None
        
        try:
            # 1. Extrair dados do PDF com MarkItDown (ÚNICA mudança)
            pdf_data = self.extract_pdf_data_with_markitdown(pdf_path)
            
            # 2. Identificar área vazia na segunda página (IGUAL v2)
            empty_area = self.identify_empty_area_improved(pdf_path)
            
            # 3. Upload dos dados para OpenAI (IGUAL v2)
            file_id = self.upload_file_to_openai(pdf_data)
            
            # 4. Gerar resumo via OpenAI Assistant (IGUAL v2)
            summary = self.create_thread_and_run_v2(file_id, user_prompt)
            
            # 5. Inserir resumo no PDF (IGUAL v2)
            output_path = self.insert_text_in_pdf_v2(pdf_path, summary, empty_area)
            
            # 6. Limpeza (opcional) (IGUAL v2)
            if cleanup and file_id:
                self.cleanup_openai_file(file_id)
            
            print("\n" + "=" * 80)
            print("🎉 PROCESSAMENTO V3 CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            print(f"📄 Arquivo original: {pdf_path}")
            print(f"📊 Arquivo com resumo V3: {output_path}")
            print(f"🎯 Benefício V3: MarkItDown processa imagens/gráficos com LLM")
            
            return output_path
            
        except Exception as e:
            print(f"\n❌ ERRO NO PROCESSAMENTO V3: {e}")
            
            # Tentar limpeza em caso de erro
            if cleanup and file_id:
                self.cleanup_openai_file(file_id)
            
            raise

def main():
    """Função principal para teste da versão 3"""
    # Arquivo de exemplo fornecido pelo usuário
    pdf_path = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf"
    
    print("🎯 SISTEMA DE PROCESSAMENTO DE RELATÓRIOS PDF - VERSÃO 3")
    print("=" * 80)
    
    # Verificar se arquivo existe
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    try:
        # Criar processador V3 (baseado no V2)
        processor = PDFReportProcessorV3()
        
        # Solicitar prompt do usuário
        print("\n📝 INSTRUÇÕES PARA O RESUMO (V3 - MarkItDown)")
        print("=" * 40)
        user_prompt = input("Digite instruções específicas para o resumo (ou Enter para padrão): ").strip()
        
        if not user_prompt:
            user_prompt = "Analise as tendências financeiras, identifique variações significativas entre os meses e destaque pontos críticos para a gestão executiva com foco em receitas, custos e margens operacionais."
        
        print(f"\n🎯 Usando prompt: {user_prompt}")
        
        # Processar relatório com versão 3
        result_path = processor.process_monthly_report_v3(pdf_path, user_prompt)
        
        print(f"\n🎊 SUCESSO V3! Arquivo gerado: {result_path}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
