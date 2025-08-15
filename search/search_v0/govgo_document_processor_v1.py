"""
govgo_document_processor_v1.py
Módulo de Processamento de Documentos e Queries GovGo V1
=========================================================

Unifica funcionalidades de:
• gvg_document_utils_v3_o.py / v2.py (processamento de documentos)
• gvg_pre_processing_v3.py (processamento inteligente de queries)

🎯 FUNCIONALIDADES:
• Análise e sumarização de documentos PNCP
• Processamento inteligente de consultas
• Separação de termos e condições SQL
• Suporte a Docling v3 e MarkItDown v2
• Integração com OpenAI Assistants V1
"""

import os
import re
import json
import time
import requests
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Processamento de documentos
try:
    import docling
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

try:
    import markitdown
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

# OpenAI
from openai import OpenAI
from dotenv import load_dotenv

# Configurações V1
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL_CHAT = os.getenv('OPENAI_MODEL_CHAT', 'gpt-4o')
OPENAI_ASSISTANT_PREPROCESSING = os.getenv('OPENAI_ASSISTANT_PREPROCESSING', 'asst_argxuo1SK6KE3HS5RGo4VRBV')
OPENAI_ASSISTANT_PDF_PROCESSOR_V1 = os.getenv('OPENAI_ASSISTANT_PDF_PROCESSOR_V1', 'asst_qPkntEzl6JPch7UV08RW52i4')

# Cliente OpenAI
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
    except Exception as e:
        print(f"⚠️ Erro ao inicializar OpenAI: {e}")
        OPENAI_AVAILABLE = False
else:
    OPENAI_AVAILABLE = False

# ============================================================================
# PROCESSAMENTO INTELIGENTE DE QUERIES
# ============================================================================

class SearchQueryProcessor:
    """
    Processador Inteligente de Consultas V1
    
    Funcionalidades:
    • Separação automática de termos de busca e condições SQL
    • Processamento via OpenAI Assistant
    • Detecção de filtros regionais, monetários e temporais
    • Suporte a prompts negativos
    """
    
    def __init__(self):
        self.client = openai_client
        self.assistant_id = OPENAI_ASSISTANT_PREPROCESSING
        self.thread_id = None
        self._create_thread()
    
    def _create_thread(self):
        """Cria thread para o Assistant"""
        if not self.client:
            return
        
        try:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id
        except Exception as e:
            print(f"⚠️ Erro ao criar thread: {e}")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Processa query inteligentemente
        
        Args:
            query: Query original do usuário
            
        Returns:
            Dict com:
            - original_query: Query original
            - search_terms: Termos limpos para busca
            - sql_conditions: Lista de condições SQL
            - explanation: Explicação do processamento
        """
        result = {
            'original_query': query,
            'search_terms': query,
            'sql_conditions': [],
            'explanation': 'Processamento básico - OpenAI não disponível'
        }
        
        if not self.client or not self.thread_id:
            # Processamento básico sem IA
            return self._basic_processing(query)
        
        try:
            # Enviar para Assistant
            message_content = f"""
            Analise esta consulta de busca PNCP e extraia:
            
            CONSULTA: "{query}"
            
            Retorne JSON com:
            {{
                "search_terms": "termos limpos para busca semântica",
                "sql_conditions": ["condição1", "condição2"],
                "explanation": "breve explicação do processamento"
            }}
            
            Extraia condições SQL para:
            - Regiões/Estados/Cidades
            - Valores monetários
            - Datas e períodos
            - Modalidades específicas
            - Órgãos específicos
            
            Mantenha apenas termos essenciais em search_terms.
            """
            
            response = self._call_assistant(message_content)
            if response:
                try:
                    ai_result = json.loads(response)
                    result.update({
                        'search_terms': ai_result.get('search_terms', query),
                        'sql_conditions': ai_result.get('sql_conditions', []),
                        'explanation': ai_result.get('explanation', 'Processado via IA')
                    })
                except json.JSONDecodeError:
                    # Fallback para processamento básico
                    result = self._basic_processing(query)
            else:
                result = self._basic_processing(query)
                
        except Exception as e:
            print(f"⚠️ Erro no processamento inteligente: {e}")
            result = self._basic_processing(query)
        
        return result
    
    def _basic_processing(self, query: str) -> Dict[str, Any]:
        """Processamento básico sem IA"""
        # Detectar filtros básicos
        sql_conditions = []
        search_terms = query
        
        # Detectar UFs
        uf_pattern = r'\b([A-Z]{2})\b'
        ufs_found = re.findall(uf_pattern, query.upper())
        valid_ufs = ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'GO', 'DF', 'PE', 'CE', 'PB', 'AL', 'SE', 'RN', 'PI', 'MA', 'TO', 'MT', 'MS', 'RO', 'AC', 'AM', 'RR', 'PA', 'AP', 'ES']
        
        found_valid_ufs = [uf for uf in ufs_found if uf in valid_ufs]
        if found_valid_ufs:
            uf_list = "','".join(found_valid_ufs)
            sql_conditions.append(f"c.unidade_orgao_uf_sigla IN ('{uf_list}')")
            # Remover UFs dos termos de busca
            for uf in found_valid_ufs:
                search_terms = re.sub(rf'\b{uf}\b', '', search_terms, flags=re.IGNORECASE)
        
        # Detectar valores monetários
        value_patterns = [
            r'acima de R?\$?\s*([0-9.,]+)',
            r'maior que R?\$?\s*([0-9.,]+)',
            r'superior a R?\$?\s*([0-9.,]+)',
            r'> R?\$?\s*([0-9.,]+)'
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.replace(',', '').replace('.', ''))
                    sql_conditions.append(f"c.valorTotalEstimado > {value}")
                    search_terms = re.sub(pattern, '', search_terms, flags=re.IGNORECASE)
                except ValueError:
                    continue
        
        # Limpar termos de busca
        search_terms = re.sub(r'\s+', ' ', search_terms).strip()
        
        return {
            'original_query': query,
            'search_terms': search_terms,
            'sql_conditions': sql_conditions,
            'explanation': f'Processamento básico - {len(sql_conditions)} condições detectadas'
        }
    
    def _call_assistant(self, message_content: str, max_wait_time: int = 30) -> Optional[str]:
        """Chama OpenAI Assistant"""
        if not self.client or not self.thread_id:
            return None
        
        try:
            # Enviar mensagem
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=message_content
            )
            
            # Executar Assistant
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            )
            
            # Aguardar resposta
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    messages = self.client.beta.threads.messages.list(
                        thread_id=self.thread_id,
                        order='desc',
                        limit=1
                    )
                    
                    if messages.data:
                        return messages.data[0].content[0].text.value
                    break
                    
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    break
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erro ao chamar Assistant: {e}")
            return None

# ============================================================================
# PROCESSAMENTO DE DOCUMENTOS
# ============================================================================

class DocumentProcessor:
    """
    Processador de Documentos V1
    
    Funcionalidades:
    • Suporte a Docling v3 (preferencial) e MarkItDown v2 (fallback)
    • Processamento de PDFs, Word, Excel, etc.
    • Sumarização via OpenAI
    • Extração de tabelas avançada (Docling)
    • Processamento de arquivos ZIP
    """
    
    def __init__(self, use_docling: bool = True):
        self.use_docling = use_docling and DOCLING_AVAILABLE
        self.client = openai_client
        self.assistant_id = OPENAI_ASSISTANT_PDF_PROCESSOR_V1
        
        # Configurar processadores
        if self.use_docling and DOCLING_AVAILABLE:
            self.docling_converter = DocumentConverter()
            self.processor_version = "v3 (Docling)"
        elif MARKITDOWN_AVAILABLE:
            self.markitdown_processor = MarkItDown()
            self.processor_version = "v2 (MarkItDown)"
        else:
            self.processor_version = "Nenhum processador disponível"
    
    def process_document(self, url_or_path: str, max_tokens: int = 2000) -> Optional[str]:
        """
        Processa documento de URL ou caminho local
        
        Args:
            url_or_path: URL ou caminho do arquivo
            max_tokens: Limite de tokens para sumarização
            
        Returns:
            Texto processado ou None se erro
        """
        try:
            # Baixar arquivo se for URL
            if url_or_path.startswith(('http://', 'https://')):
                file_path = self._download_file(url_or_path)
                if not file_path:
                    return None
            else:
                file_path = url_or_path
            
            # Processar com Docling ou MarkItDown
            if self.use_docling:
                return self._process_with_docling(file_path, max_tokens)
            else:
                return self._process_with_markitdown(file_path, max_tokens)
        
        except Exception as e:
            print(f"❌ Erro ao processar documento: {e}")
            return None
    
    def _process_with_docling(self, file_path: str, max_tokens: int) -> Optional[str]:
        """Processa com Docling v3"""
        try:
            # Converter documento
            result = self.docling_converter.convert(file_path)
            
            # Extrair texto
            text_content = result.document.export_to_markdown()
            
            # Sumarizar se necessário
            if len(text_content.split()) > max_tokens:
                return self._summarize_content(text_content, max_tokens)
            
            return text_content
            
        except Exception as e:
            print(f"❌ Erro no Docling: {e}")
            return None
    
    def _process_with_markitdown(self, file_path: str, max_tokens: int) -> Optional[str]:
        """Processa com MarkItDown v2"""
        try:
            # Converter documento
            result = self.markitdown_processor.convert(file_path)
            text_content = result.text_content
            
            # Sumarizar se necessário
            if len(text_content.split()) > max_tokens:
                return self._summarize_content(text_content, max_tokens)
            
            return text_content
            
        except Exception as e:
            print(f"❌ Erro no MarkItDown: {e}")
            return None
    
    def _download_file(self, url: str) -> Optional[str]:
        """Baixa arquivo de URL"""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Determinar extensão
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type:
                ext = '.pdf'
            elif 'word' in content_type or 'doc' in content_type:
                ext = '.docx'
            elif 'excel' in content_type or 'sheet' in content_type:
                ext = '.xlsx'
            else:
                ext = '.pdf'  # Padrão
            
            # Salvar em arquivo temporário
            temp_path = os.path.join(
                os.getenv('TEMP_PATH', 'temp'), 
                f"doc_{int(time.time())}{ext}"
            )
            
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return temp_path
            
        except Exception as e:
            print(f"❌ Erro ao baixar arquivo: {e}")
            return None
    
    def _summarize_content(self, content: str, max_tokens: int) -> Optional[str]:
        """Sumariza conteúdo via OpenAI"""
        if not self.client:
            # Truncar simples se OpenAI não disponível
            words = content.split()
            return ' '.join(words[:max_tokens])
        
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_CHAT,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em análise de documentos públicos. Sumarize o conteúdo preservando informações importantes sobre contratos, valores, datas e especificações técnicas."
                    },
                    {
                        "role": "user",
                        "content": f"Sumarize este documento em até {max_tokens} palavras:\n\n{content[:8000]}"
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Erro na sumarização: {e}")
            # Fallback para truncamento simples
            words = content.split()
            return ' '.join(words[:max_tokens])

# ============================================================================
# FUNÇÕES GLOBAIS PARA COMPATIBILIDADE V0
# ============================================================================

# Instâncias globais
_query_processor = None
_document_processor = None

def get_query_processor() -> SearchQueryProcessor:
    """Obter processador de queries global"""
    global _query_processor
    if _query_processor is None:
        _query_processor = SearchQueryProcessor()
    return _query_processor

def get_document_processor(use_docling: bool = True) -> DocumentProcessor:
    """Obter processador de documentos global"""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor(use_docling)
    return _document_processor

def summarize_document(url_or_path: str, max_tokens: int = 2000, 
                      doc_name: str = "", pncp_data: Dict = None) -> Optional[str]:
    """
    Compatibilidade V0 - Sumarizar documento
    
    Args:
        url_or_path: URL ou caminho do documento
        max_tokens: Limite de tokens
        doc_name: Nome do documento (opcional)
        pncp_data: Dados do PNCP (opcional)
        
    Returns:
        Resumo do documento ou None se erro
    """
    processor = get_document_processor()
    result = processor.process_document(url_or_path, max_tokens)
    
    if result and pncp_data:
        # Adicionar contexto do PNCP se disponível
        context = f"\n\n📋 CONTEXTO PNCP:\n"
        context += f"• ID: {pncp_data.get('id', 'N/A')}\n"
        context += f"• Órgão: {pncp_data.get('orgao', 'N/A')}\n"
        context += f"• Local: {pncp_data.get('municipio', 'N/A')}/{pncp_data.get('uf', 'N/A')}\n"
        result += context
    
    return result

def process_pncp_document(url: str, pncp_data: Dict = None) -> Optional[str]:
    """
    Compatibilidade V0 - Processar documento específico do PNCP
    
    Args:
        url: URL do documento no PNCP
        pncp_data: Dados contextuais do contrato
        
    Returns:
        Conteúdo processado ou None se erro
    """
    return summarize_document(url, 2000, "", pncp_data)

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("GovGo Document Processor V1 - Teste")
    
    # Teste do processador de queries
    processor = SearchQueryProcessor()
    test_query = "notebooks para escolas em SP com valor acima de R$ 100.000"
    
    result = processor.process_query(test_query)
    print(f"Query original: {result['original_query']}")
    print(f"Termos de busca: {result['search_terms']}")
    print(f"Condições SQL: {result['sql_conditions']}")
    print(f"Explicação: {result['explanation']}")
    
    # Teste do processador de documentos
    doc_processor = DocumentProcessor()
    print(f"Processador de documentos: {doc_processor.processor_version}")
